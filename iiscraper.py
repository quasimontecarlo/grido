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
# build argparse // basic function done, need to implement a more robust solution
# resize trim to get same width
# improve image extension handling, this should be done just need to check for bugs 
# check if image on pil function, this is done, handled with urllib before than

### cli arguments build
parser = argparse.ArgumentParser(
        prog = "iiscraper",
        description = "this tools scrapes imdb advanced user search link, scrapes movie titles and year and searches images in duckduckgo, downloads them, and resizes them",
        epilog = "your life must be good now that my job is over")
parser.add_argument("-u", "--url", default = os.environ.get('IMDBURL'), help = "the url link to imdb, default value $IMDBURL env variable")
parser.add_argument("-o", "--out", default = os.environ.get('IMDBFOLDER'), help = "the output location on disk where the images will be saved, default value $IMDBFOLDER env variable")
parser.add_argument("-s", "--size", default = 400, help = "the height size in pxls, with will be calculated respectin the original aspect, default value 400")



### from imdb user search buid a list of tuples database of movies/year
def scrapeImdb(movie_data, data):
    for store in movie_data:
        imageDiv = store.find("div", {"class": "lister-item-image float-left"})
        img = imageDiv.img.get("loadlate")
        name = imageDiv.img.get("alt").replace("!","")
        yearDiv = str(store.find("span", {"class": "lister-item-year text-muted unbold"}))
        year = re.findall('\(([^)]+)', yearDiv)
        ## this year meddling is ugly but necessary to deal with the inconsistency of how years are stored in imdb
        if year:
            year = re.findall('\d{4}', year[-1])
            if len(year) > 1:
                year = "%s_%s" % (year[0], year[-1])
            else:
                year = year[-1]
        else:
            year = "Unreleased"

        data.append((year, name))
    print("\nScrape :: Done")
    return data

### search in duckduckgo the movie poster
def searchDuck(data, fullData):
    print("\nSearching DuckDuckGo for images")
    for year, name in data:
        searchKey = "%s %s US Movie Poster" % (year, name)
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
    for img, path in database:
        i = Image.open(path)
        hpercent = (baseheigth/float(i.size[1]))
        wsize = int((float(i.size[0])*float(hpercent)))
        i = i.resize((wsize, baseheigth), Image.Resampling.LANCZOS)
        i.save(path)
        print("\nResize %s :: Done" % path)

### define base vars
args = parser.parse_args()
data = []
fullData = []
database = []
url = args.url
directory = args.out
height = args.size
ue = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

### check if url and dir are none and require them, basically checking if env variable is missing
if not url or not directory:
    print("\ncouldn't find url or directory env variables please either set them or use the provided flags\n")
    exit()

response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "lister-item mode-advanced"})

### begin
scrapeImdb(movie_data, data)
searchDuck(data, fullData)
buildDiskPath(fullData, database)
download(database)
conform(database, height)
