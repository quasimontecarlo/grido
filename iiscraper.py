# TO DO 
# find a better way to deal with file extentions
# deal with 404 image not found

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import os
import requests
import wget
import pathlib
import re

data = []
url = "https://www.imdb.com/search/title/?role=nm7053849&sort=release_date,desc"
ue = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "lister-item mode-advanced"})

#print(movie_data)

def findBaseDir():

    if os.environ["TERM"] == "st-256color":
        return "/home/crltt/"
    else:
        return "/Users/crltt/Library/CloudStorage/"

directory = "%sDropbox/wrk/prjts/presentations/source/imgs" % findBaseDir()

print(directory)
quit()

for store in movie_data:
    imageDiv = store.find("div", {"class": "lister-item-image float-left"})
    img = imageDiv.img.get("loadlate")
    name = imageDiv.img.get("alt")
    yearDiv = str(store.find("span", {"class": "lister-item-year text-muted unbold"}))
    year = re.findall('\(([^)]+)', yearDiv)[-1]
    data.append((year, name))
#print(data)


for year, name in data:
    searchKey = "%s %s movie poster" % (year, name)
    #print(searchKey)
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
            img = r
            break
    img = img["image"]
    ext = re.findall("(\.[^.]*)$", img)[0][:4]
    path = "%s/%s__%s%s" % (directory, year, name.replace(" ", "_").replace(":", ""), ext)
    wget.download(img, path)
    print("\nDownloading this :\n%s\n\nHere :\n%s\n\n" % (img, path))
    #break
