# TO DO 
# find a better way to deal with file extentions

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from PIL import Image
import os
import requests
import wget
import re
import urllib
import argparse

### TO-DO
# build argparse
# resize trim to get same width
# improve image extension handling
# check if image on pil function

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
        name = imageDiv.img.get("alt")
        yearDiv = str(store.find("span", {"class": "lister-item-year text-muted unbold"}))
        year = re.findall('\(([^)]+)', yearDiv)[-1]
        data.append((year, name))
    print("\nScrape :: Done")
    return data

### search in duckduckgo the movie poster
def searchDuck(data, fullData):
    print("\nSearching DuckDuckGo for images")
    for year, name in data:
        searchKey = "%s %s US Movie Poster" % (year, name)
        with DDGS() as ddgs:
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
                    urllib.request.urlopen(img)
                    fullData.append((year, name, img))
                    break
                except urllib.error.HTTPError as e:
                    print("%s %s" % (e.reason, searchKey))
    print("\nSearch :: Done")
    return fullData

### try to deal with file extentions
def extMeddle(img):
    ext = re.findall("(\.[^.]*)$", img)[0]
    if "jpeg" in ext:
        ext = ext[:5]
    else:
        ext = ext[:4]
    return ext

### build the image disk path
def buildDiskPath(fullData, database):
    print("\nBuilding disk paths")
    for year, name, img in fullData:
        ext = extMeddle(img)
        path = "%s/%s__%s%s" % (directory, year, name.replace(" ", "_").replace(":", ""), ext)
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

response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "lister-item mode-advanced"})

### begin
scrapeImdb(movie_data, data)
searchDuck(data, fullData)
buildDiskPath(fullData, database)
download(database)
conform(database, height)
