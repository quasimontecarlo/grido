from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from PIL import Image, ImageDraw, ImageFont
from datetime import date
from socket import timeout
import os
import requests
import wget
import re
import urllib
import argparse
import logging
import random

### TO-DO
# might want to eventually create a json database and handle storing the info
# explore the possibility of mergin all images together in a grid like system

### cli arguments build
parser = argparse.ArgumentParser(
        prog = "iiscraper",
        description = "this tools scrapes imdb advanced user search link, scrapes movie titles and year and searches images in duckduckgo, downloads them, and resizes them",
        epilog = "your life must be good now that my job is over")
parser.add_argument("-u", "--url", default = os.environ.get('IMDBURL'), help = "the url link to imdb, default value $IMDBURL env variable")
parser.add_argument("-o", "--out", default = os.environ.get('IMDBFOLDER'), help = "the output location on disk where the images will be saved, default value $IMDBFOLDER env variable")
parser.add_argument("-s", "--size", default = 200, help = "the height size in pxls, with will be calculated respectin the original aspect, default value 400")
parser.add_argument("-l", "--list", action = "store_true", help = "if enabled provides the list of movies found")
parser.add_argument("-c", "--crop", action = "store_true", help = "if enabled crops the width to the min width of the images found")
parser.add_argument("-d", "--deform", action = "store_true", help = "if enabled deforms the width to the median width of the images found")
parser.add_argument("-g", "--grid", action = "store_true", help = "if enabled creates a new image of a grid with all the images found inside")
parser.add_argument("-gs", "--gridSize", default = "1920x1080",help = "control the grid image size, default 1920x1080, to make it work please use format $Wx$H")
parser.add_argument("-gnl", "--gridNewLine", default = 7, type = int, help = "control when the movie list text goes to a new line, the value indicates after how many items there's a new line?, the value needs to be an integer")
parser.add_argument("-b", "--bypass", action = "store_true", help = "if enabled bypass search and goes directly to the folder to resize")
parser.add_argument("-ko", "--keepOriginals", action = "store_true", help = "if enabled stores the original images in a subfolder that the script will create")

### from imdb user search buid a list of tuples database of movies/year
def scrapeImdb(movie_data, data):
    for store in movie_data:
        try:
            names = store.findAll("h3", {"class": "ipc-title__text"})
            year = store.find("span", {"class": "dli-title-metadata-item"}).text
            name = re.match("[^ ]* (.*)", names[0].text).group(1)
            if len(names) > 1:
                episode = names[-1].text
            else:
                episode = None
        except:
            print("webpage must have changed, please raise a github issue")
            exit()
        if year:
            year = re.findall('\d{4}',year)
            if len(year) > 1:
                year = "%s_%s" % (year[0], year[-1])
            elif len(year) < 1:
                year = "Unreleased"
            else:
                year = year[-1]
        else:
            year = "Unreleased"
        data.append((year, name))
        filmData.append((year, name, episode))
    print("\nScrape :: Done")
    return data

### search in duckduckgo the movie poster
def searchDuck(data, fullData):
    print("\nSearching DuckDuckGo for images")
    for year, name in data:
        searchKey = "%s %s US Poster" % (year, name.replace("!",""))
        with DDGS(timeout = 20) as ddgs:
            keywords = searchKey
            ddgs_images_gen = ddgs.images(
                keywords,
                region="us-en",
                safesearch="moderate",
                size="Large",
                type_image="photo",
                layout="Tall",
                )
            for r in ddgs_images_gen:
                try:
                    img = r["image"]
                    i = urllib.request.urlopen(img, timeout=20)
                    imgType = i.headers["Content-Type"]
                    if "image" in imgType:
                        ext = imgType.split("/")[-1]
                        fullData.append((year, name, img, ext))
                        print("found movie poster for %s" % name)
                    break
                except urllib.error.HTTPError as e:
                    logging.error("broken link | reason HTTP Error %s %s | on %s | will try next result" % (str(e.code), e.reason, name))
                except urllib.error.URLError as e:
                    if isinstance(e.reason, timeout):
                        logging.error("broken link | reason URL Error %s | on %s | will try next result" % (e.reason, name))
                    else:
                        logging.error("broken link | reason URL Error %s | on %s | will try next result" % (e.reason, name))
                except urllib.error.ContentTooShortError as e:
                    logging.error("broken link | reason Content Too Short Error | on %s | will try next result" % name)
                except timeout as e:
                    logging.error("broken link | reason Socket Timeout | on %s | will try the next result" % name)
    print("\nSearch :: Done")
    return fullData

### build the image disk path
def buildDiskPath(fullData, database):
    print("\nBuilding disk paths")
    for year, name, img, ext in fullData:
        ## need to meddle with the variables to generate a pleasing file name and deal with random edge cases
        year = year.replace("– ", "").replace("–", "_").replace(" ", "")
        name = name.replace(" ", "_").replace(":", "").replace("/", "-")
        path = "%s/%s__%s.%s" % (directory, year, name, ext)
        database.append((img, path))
    print("\nBuild :: Done")
    return database

### use wget to dowload the imges
def download(database):
    print("\nDownloading images")
    for img, path in database:
        wget.download(img, path)
        print("\nDownloading this :\n%s\n\nHere :\n%s\n\n" % (img, path))
    print("\nDownload :: Done")
    if args.keepOriginals:
        of = "%s/originals" % os.path.dirname(database[0][-1])
        os.system("mkdir %s" % of)
        for img, path in database:
            os.system("cp %s %s/%s" % (path, of, os.path.basename(path)))
        print("\nSince you asked I've copied the originals here %s to keep em safe\n" % of)

### use PIL to conform the image size
def conform(database, height, who):
    print("\nResizing images")
    ## dealing with PIL versions changes
    if not hasattr(Image, "Resampling"):
        Image.Resampling = Image
    baseheigth = height
    widths = []
    # resize based on height
    for img, path in database:
        i = Image.open(path)
        hpercent = (baseheigth/float(i.size[1]))
        wsize = int((float(i.size[0])*float(hpercent)))
        widths.append(wsize)
        i = i.resize((wsize, baseheigth), Image.Resampling.LANCZOS)
        i.save(path)
        print("\nResize %s :: Done" % path)
    # resize with cropped to min width
    if crop:
        lcd = sorted(widths)[0]
        crops = []
        for w in widths:
            x = (w - lcd)/2
            crops.append(x)
        index = 0
        for img, path in database:
            i = Image.open(path)
            i = i.crop((crops[index], 0.0, i.size[0]-crops[index], i.size[1]))
            i.save(path)
            index += 1
            mw = lcd
            print("\nCrop  %s :: Done" % path)
    # resize altering the aspect ratio of the original images to the median width
    if deform:
        sw = sorted(widths)
        wn = len(sw)
        mw = int((sw[int(wn/2)] + sw[(int(wn/2))+1]) / 2)
        for img, path in database:
            i = Image.open(path)
            i = i.resize((mw, i.size[1]), Image.Resampling.LANCZOS)
            i.save(path)
            print("\nDeform %s :: Done" % path)
    if grid:
        if deform or crop:
            margin = height/10
            border = height
            w = gridWidth - border
            h = gridHeight - border
            wn = int(w / (mw+margin))
            hn = int(h / (height+margin))
            index = 0
            pointsx = []
            pointsy = []
            gc = Image.new("RGBA", (gridWidth, gridHeight), (255, 255, 255, 0,))
            database = sortuple(database)
            for j in range(int(border), int(h-height), int(height+margin)):
                for k in range(int(border), int(w-mw), int(mw+margin)):
                    if index < len(database): 
                        gc.paste(Image.open(database[index][-1]), (int(k), int(j)))
                        pointsx.append(int(k))
                        pointsy.append(int(j))
                        index += 1
             
            pointsx = sorted(pointsx)
            pointsy = sorted(pointsy)
            gcc = gc.crop((pointsx[0], pointsy[0], pointsx[-1]+mw, pointsy[-1]+height))
            npx = (gridWidth - gcc.size[0])/2
            npy = (gridHeight - gcc.size[-1])/2
            fg = Image.new("RGBA", (gridWidth, gridHeight), (255, 255, 255, 0))
            fg.paste(gcc, (int(npx),int(npy)))
            if who:
                draw = ImageDraw.Draw(fg)
                bfont = ImageFont.truetype("font/alte_din_gepraegt.ttf", 60)
                rfont = ImageFont.truetype("font/alte_din_regular.ttf", 14)
                mn = ""
                counter = 1
                for n in database:
                    iname =  "%s-%s | " % (os.path.splitext(os.path.basename(n[-1]))[0].split("__")[0].replace("_", "/"), os.path.splitext(os.path.basename(n[-1]))[0].split("__")[-1].replace("_"," "))
                    if counter % args.gridNewLine == 0:
                        mn = mn + "\n" + iname
                    else:
                        mn = mn + iname
                    counter += 1
                draw.text((int(npx), int(npy)/2), "%s Filmography" % who, (30,30,30), font = bfont)
                draw.multiline_text((int(npx), int((gcc.size[-1]+npy)+(npy/4))), "[from top/left] %s" % mn, (30,30,30), font = rfont)
            fg.save("%s/%s_grid.png" % (os.path.dirname(database[0][-1]), date.today().strftime("%Y")), quality=100)
            print("\nGrid :: Done")
        else:
            print("\ngrid can only be used in conjunction with either crop or deform, please add either -c or -d flag\n")

### print a list of all items found
def filmography(who, data):
    print("\n")
    data = unduplicate(data)
    print("%s Filmography\n%s Items\n" % (who, len(data)))
    for year, name, episode in data:
        if episode:
            print("%s | %s | Episode: %s" % (year, name, episode))
        else:
            print("%s | %s" % (year, name))
    print("\n")

### remove duplicates helper
def unduplicate(l):
    return list(dict.fromkeys(l))

### bypass function, builds a database of images already found
def by(path):
    files = [("", os.path.join(path,f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) and f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))]
    return files

def sortuple(lt):
    lst = len(lt)
    for i in range(0, lst):
        for j in range(0, lst-i-1):
            if (lt[j][1] < lt[j+1][1]):
                temp = lt[j]
                lt[j] = lt[j+1]
                lt[j+1] = temp
    return lt

### define base vars
args = parser.parse_args()
data = []
filmData = []
fullData = []
database = []
bypass = args.bypass
url = args.url
directory = args.out
height = int(args.size)
crop = args.crop
deform = args.deform
grid = args.grid

### adding a list of a lot of user agent to avoid getting refused after multiple attempts
uel = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.69", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.1", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.3", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.1", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.3", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.61", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"]

gs = re.findall('\d{4}', args.gridSize)
gridWidth = int(gs[0])
gridHeight = int(gs[-1])

ue = {'User-Agent': random.choice(uel)}

### check if url and dir are none and require them, basically checking if env variable is missing
if url and directory:
    print("\nStarting my search in %s\nand will output to %s" % (url, directory))
else:
    print("\ncouldn't find url or directory env variables please either set them or use the provided flags\n")
    exit()

### connect to the web with bs
response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "ipc-metadata-list-summary-item__tc"})
#who = re.findall("^[^\(]+", soup.title.string)[0].replace("With ", "").replace("\n","")
who = soup.find("span", attrs={"class": "ipc-chip__text"}).string
### this is a cheap way go around a weird bug which seems to me related to bs and imdb booting me off the site i guess for many attempts ?
if who == "Advanced search":
    print("\nConnection refused, please try again\n")
    exit()
if len(movie_data) == 0:
    print("\nCouldn't find what I was looking for, check the link provided")
    exit()

directory ="%s/%s" % (directory, who.replace(" ", "_").lower())
if not os.path.isdir(directory):
    os.system("mkdir %s" % directory)
else:
    print("\ndirectory exists, skipping creation")

### if b flag then don't search
if bypass:
    database = by(directory)
    if len(database) >= 1:
        conform(database, height, who)
    else:
        print("\ni can't find the images required in the supplied directory, please check if the desired images are in the folder\n")
    exit()

### begin
scrapeImdb(movie_data, data)
if args.list:
    filmography(who, filmData)
data = unduplicate(data)
searchDuck(data, fullData)
buildDiskPath(fullData, database)
download(database)
conform(database, height, who)
