import os
import csv
import zipfile
import urllib.request as ureq
import cherrypy
import redis
from jinja2 import Environment
from jinja2 import FileSystemLoader

url = "https://www.bseindia.com/download/BhavCopy/Equity/EQ121218_CSV.ZIP"
FILE_NAME = url.split('/')[-1]

conn = redis.Redis()

csv_zip = ureq.urlretrieve(url, FILE_NAME)

with zipfile.ZipFile(FILE_NAME) as zip_ref:
    csv_file_name = zip_ref.namelist()[0]
    zip_ref.extractall()

fields = []
rows = []
required_fields = ['SC_CODE', 'SC_NAME', 'OPEN', 'HIGH', 'LOW', 'CLOSE']

with open(csv_file_name, 'r') as fd:
    bhav_reader = csv.reader(fd)
    fields = next(bhav_reader)

    for row in bhav_reader:
        rows.append(row)

bhav_equity_data = list(map(lambda x: dict(zip(fields, x)), rows))

class DisplayStocks(object):
    @cherrypy.expose
    def index(self):
        return open('public/index.html')
