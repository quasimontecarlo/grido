from bs4 import BeautifulSoup
from icrawler.builtin import GoogleImageCrawler
import os
import requests
import wget
import pathlib
import re

data = []
url = "https://www.imdb.com/search/title/?role=nm7053849&sort=release_date,desc"
ue = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
directory = "/Users/crltt/Library/CloudStorage/Dropbox/wrk/prjts/presentations/source/imgs"
response = requests.get(url, headers=ue)
soup = BeautifulSoup(response.content, "html.parser")
movie_data = soup.findAll("div", attrs={"class": "lister-item mode-advanced"})

#print(movie_data)

for store in movie_data:
    imageDiv = store.find("div", {"class": "lister-item-image float-left"})
    img = imageDiv.img.get("loadlate")
    ext = pathlib.Path(img).suffix
    name = imageDiv.img.get("alt")
    yearDiv = str(store.find("span", {"class": "lister-item-year text-muted unbold"}))
    year = re.findall('\(([^)]+)', yearDiv)[-1]
    data.append((year, name))
    path = "%s%s__%s%s" % (directory, year, name, ext)
    #wget.download(img, path)
    #print("\nDownloading this :\n%s\n\nHere :\n%s\n\n" % (img, path))

print(data)


gc = GoogleImageCrawler(storage={"root_dir": directory})
filters = dict(
        size="large")

for year, name in data:
    searchKey = "%s %s movie poster" % (year, name)
    #print(searchKey)
    gc.crawl(keyword=searchKey, filters=filters, min_size=(200,200), max_num=1)
    os.rename("%s/000001.jpg" %directory, "%s/%s__%s.jpg" %(directory, year, name.replace(":", "").replace(" ", "_")))
