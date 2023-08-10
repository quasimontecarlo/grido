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

### check terminal env to evaluate system and change basepath
def findBaseDir():

    if os.environ["TERM"] == "st-256color":
        return "/home/crltt/"
    else:
        return "/Users/crltt/Library/CloudStorage/"

### from imdb user search buid a list of tuples database of movies/year
def scrapeImdb(movie_data, data):
    print("\nScraping IMDB for user infos")
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
                region="wt-wt",
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
def conform(database):
    print("\nResizing images")
    baseheigth = 400
    for img, path in database:
        i = Image.open(path)
        hpercent = (baseheigth/float(i.size[1]))
        wsize = int((float(i.size[0])*float(hpercent)))
        i = i.resize((wsize, baseheigth), Image.Resampling.LANCZOS)
        i.save(path)
        print("\nResize %s :: Done" % path)

### define base vars
data = []
fullData = []
database = []
url = "https://www.imdb.com/search/title/?role=nm7053849&sort=release_date,desc"
ue = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "lister-item mode-advanced"})
directory = "%sDropbox/wrk/prjts/presentations/source/imgs" % findBaseDir()

### begin
scrapeImdb(movie_data, data)
searchDuck(data, fullData)
buildDiskPath(fullData, database)
download(database)
conform(database)
