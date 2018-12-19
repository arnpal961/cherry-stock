import re
import os
import csv
import zipfile
import urllib.request as ureq
from datetime import datetime
import bs4
import requests
import cherrypy
import redis
from jinja2 import Environment
from jinja2 import FileSystemLoader


def get_download_url(url):
    r = requests.get(url)
    
    if r.status_code==200:
        html = r.text
        
    soup = bs4.BeautifulSoup(html, 'lxml')
    links = soup.find_all('a')
    
    pattern = f'EQ[1-3][0-9]{datetime.now():%m%y}_CSV.ZIP'
    
    for link in links:
        url = link.get('href')
        if url is not None and url.startswith('http'):
            if re.search(pattern, url) is not None:
                download_url = link.get('href')
                
    return download_url


def download_zip_file(download_url):
    zip_file_name = download_url.split('/')[-1]
    ureq.urlretrieve(download_url, zip_file_name)
    return zip_file_name

def extract_zip(zip_file_name):
    with zipfile.ZipFile(zip_file_name) as zip_ref:
        csv_file_name = zip_ref.namelist()[0]
        zip_ref.extractall()
    return csv_file_name


def prepare_csv_data(csv_file_name):
    rows = []
    
    with open(csv_file_name, 'r') as fd:
        bhav_copy_reader = csv.reader(fd)
        fields = next(bhav_copy_reader)

        for row in bhav_copy_reader:
            rows.append(row)
    bhav_copy_dict = list(map(lambda x: dict(zip(fields, x)), rows))
    return bhav_copy_dict


def strip_name(data_dict):
    name = data_dict[FIELDS[1]]
    data_dict[FIELDS[1]] = name.rstrip(' ')
    return data_dict

def modify_name_field(bhav_copy_dict):
    return list(map(lambda x: strip_name(x), bhav_copy_dict))


def stock_names(bhav_copy_dict):
    return list(map(lambda x: x['SC_NAME'], bhav_copy_dict))


def prepare_database(pipeline, bhav_copy_dict):
    key = 'SC_NAME'
    for stock in bhav_copy_dict:
        pipeline.hmset(stock[key], stock)
    pipeline.execute()


def prepare_template(template_dir):
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    template = env.get_template('index.html')
    return template


def auto_complete_list(search_str, names):
    search_str = search_str.upper()
    search_list = []
    for name in names:
        if name.startswith(search_str):
            search_list.append(name)
    return search_list

def get_from_db(key):
    return conn.hgetall(key)


class DispalyStocks(object):
    @cherrypy.expose
    def index(self, count=10):
        return template.render(fields=FIELDS, count=count, stock_data=list(map(lambda x: get_from_db(x), sc_names[:count])))

    @cherrypy.expose
    def search_stock(self, name=''):
        if len(name)==0:
            return "Give a stock name"
        else:
            search_list = auto_complete_list(name, sc_names)
            if len(search_list) != 0:
                cnt = len(search_list)
                return template.render(fields=FIELDS, count=cnt, stock_data=list(map(lambda x: get_from_db(x), search_list[:cnt])))
            else:
                return "Nothing Found"


if __name__ == "__main__":

    url =  "http://www.bseindia.com/markets/equity/EQReports/BhavCopyDebt.aspx?expandable=3"
    FIELDS = ['SC_CODE', 'SC_NAME', 'OPEN', 'HIGH', 'LOW', 'CLOSE']
    conn = redis.StrictRedis(decode_responses=True)
    pipeline = conn.pipeline()

    dwnld_url = get_download_url(url)
    zip_fname = download_zip_file(dwnld_url)
    csv_fname = extract_zip(zip_fname)
    bhav_copy_dct = prepare_csv_data(csv_fname)
    bhav_copy_dct  = modify_name_field(bhav_copy_dct)
    sc_names = stock_names(bhav_copy_dct)
    prepare_database(pipeline, bhav_copy_dct)
    template = prepare_template('public')

    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './public'
        }
    }
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 80})
    cherrypy.quickstart(DispalyStocks(), '/', conf)