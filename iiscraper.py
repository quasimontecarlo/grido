from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from PIL import Image
import os
import requests
import wget
import re
import urllib
import argparse

from pprint import pprint
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
parser.add_argument("-s", "--size", default = 400, help = "the height size in pxls, with will be calculated respectin the original aspect, default value 400")
parser.add_argument("-l", "--list", action = "store_true", help = "if enabled provides the list of movies found")
parser.add_argument("-c", "--crop", action = "store_true", help = "if enabled crops the width to the min width of the images found")
parser.add_argument("-d", "--deform", action = "store_true", help = "if enabled deforms the width to the median width of the images found")

### from imdb user search buid a list of tuples database of movies/year
def scrapeImdb(movie_data, data):
    for store in movie_data:
        mainDiv = store.find("div", {"class": "lister-item-content"})
        childDiv = mainDiv.contents[1]
        name = childDiv.contents[3].text.strip()
        year = childDiv.contents[5].text
        try:
            episode = childDiv.contents[11].text
        except:
            episode = None
        ## little utility to find indexes, left here cause I might needed in the future 
        #depth = 0
        #for c in mainDiv.contents[1]:
        #    print(depth, c)
        #    depth +=1
        #print(mainDiv[0].find("a"))
        #year = re.findall('\(([^)]+)', yearDiv)
        if year:
            year = re.findall('\d{4}', year)
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
                layout="Tall")
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
                    print("broken link moving with this reason HTTP Error %s %s, finding next image for %s" % (str(e.code), e.reason, name))
                except urllib.error.URLError as e:
                    print("broken link moving with this reason URL Error %s, finding next image for %s" % (e.reason, name))
                except urllib.error.ContentTooShortError as e:
                    print("broken link moving with this reason Content Too Short Error, finding next image for %s" % (name))
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

### use PIL to conform the image size
def conform(database, height):
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

### define base vars
args = parser.parse_args()
data = []
filmData = []
fullData = []
database = []
url = args.url
directory = args.out
height = args.size
crop = args.crop
deform = args.deform
ue = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

### check if url and dir are none and require them, basically checking if env variable is missing
if not url or not directory:
    print("\ncouldn't find url or directory env variables please either set them or use the provided flags\n")
    exit()

### connect to the web with bs
response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "lister-item mode-advanced"})
who = re.findall("^[^\(]+", soup.title.string)[0].replace("With ", "").replace("\n","")

### begin
scrapeImdb(movie_data, data)
if args.list:
    filmography(who, filmData)
data = unduplicate(data)
searchDuck(data, fullData)
buildDiskPath(fullData, database)
download(database)
conform(database, height)
