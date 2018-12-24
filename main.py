import re
import os
import csv
import zipfile
import urllib.request as ureq
from datetime import datetime

# using bs4 module for parsing html document
import bs4
# using requests module for making web requests
import requests
# using cherrypy module a microframework for website
import cherrypy
# using 'redispy' for database client framework to connect with redis database
import redis
# for templating using jinja2
from jinja2 import Environment
from jinja2 import FileSystemLoader


def get_download_url(url):
    """
    This function fetches the html document and parses through
    it's DOM to extract all links and find url string of the format
    'http://www.bseindia.com/download/BhavCopy/Equity/EQ[date][month][year]_CSV.ZIP
    Then return the url string.
    """
    # making a request to get the webpage
    r = requests.get(url)
    
    # examining the response code
    # getting the html text document
    if r.status_code==200:
        html = r.text

    # creating a beautiful soup object
    # here lxml parser is used which is very fast   
    soup = bs4.BeautifulSoup(html, 'lxml')
    # getting all the link objects list by the html tag 'a'
    links = soup.find_all('a')
    
    # pattern of bhav copy zip file
    # using a f-string
    pattern = f'EQ[1-3][0-9]{datetime.now():%m%y}_CSV.ZIP'
    
    # now parse through all link objects in links
    # getting the url string
    # checking pattern for excluding non-url strings
    # searching for the url pattern by regular expression
    for link in links:
        url = link.get('href')
        if url is not None and url.startswith('http'):
            if re.search(pattern, url) is not None:
                download_url = link.get('href')

    # return the url           
    return download_url


def download_zip_file(download_url):
    '''It downloads the bhav-copy zip file and saves
       it in a unique filename in working directory 
       and returns the filename.First get the 'download_url'
       from running the get_download_url(url) function then pass
       the url string to this function.
    '''
    # parsing the file name from the url string
    zip_file_name = download_url.split('/')[-1]
    # download the ZIP file and save it in working directory
    ureq.urlretrieve(download_url, zip_file_name)
    # return the zip file name
    return zip_file_name

def extract_zip(zip_file_name):
    """It takes the ZIP file name as argument and extracts
       the CSV file in the same working directory.
    """
    # creating a file descriptor to extract
    with zipfile.ZipFile(zip_file_name) as zip_ref:
        # getting the csv file name
        csv_file_name = zip_ref.namelist()[0]
        # extract the CSV file
        # as the zip file contains only one file
        # it's ok to run extractall() method
        zip_ref.extractall()
    # return the csv file name
    return csv_file_name


def prepare_csv_data(csv_file_name):
    """It takes the CSV file name as argument and parse the
       csv file and returns the list of dictionary objects.
    """
    # creating a empty list in which we append the data row
    rows = []
    
    # open the csv file in 'r' mode
    with open(csv_file_name, 'r') as fd:
        # read the csv databy csv.reader() methood
        # it is a generator object
        bhav_copy_reader = csv.reader(fd)
        # getting all the fields name in first row
        # storing it in a list object named fields
        fields = next(bhav_copy_reader)

        # now parse through the each row in bhav_copy_reader
        for row in bhav_copy_reader:
            # append each data row in rows
            rows.append(row)

    # now 'rows' is a list object which contains data in list format
    # to convert it to a dictionary first use the inbuilt zip function
    # to convert it in a tuple format => (field_name, value) then using
    # the dict() to convert it to a dictionary
    # then map the each element of the row against the lambda function
    # which converts it to a dictionary object
    # Using functional style programming to imporve the performance
    bhav_copy_dict = list(map(lambda x: dict(zip(fields, x)), rows))
    return bhav_copy_dict


def strip_name(data_dict):
    """Takes a dictionary as argument and 
    right strips the 'SC_NAME' value for omitting
    the empty space."""

    # FIELDS is a global object and can be accessed from
    # anywhere of the script. The second item in FIELDS
    # is the SC_NAME key
    name = data_dict[FIELDS[1]]
    # stripping any empty space at the end of name
    # it will automatically updatethe dictionary
    data_dict[FIELDS[1]] = name.rstrip(' ')
    return data_dict

def modify_name_field(bhav_copy_dict):
    """Takes the list of dictionary of data strips 
    the names in all data dict and reurns the list."""
    # using list comprehension, map function and lambda function.
    # list comprehension in map function is time efficient than
    # for loop. For iterating through large list functional techniques
    # is more efficient.
    return list(map(lambda x: strip_name(x), bhav_copy_dict))


def stock_names(bhav_copy_dict):
    return list(map(lambda x: x['SC_NAME'], bhav_copy_dict))


def prepare_database(pipeline, bhav_copy_dict):
    '''Takes a pipeline object of redis client and 
       as list of data dictionary as argument and 
       sets a hash object in redis. Finally executes the
       pipeline. Here "SC_NAME" field value is used as primary
       key. as stock names are unique identifier.'''
    
    key = 'SC_NAME'
    # iterate through the list and set the value
    for stock in bhav_copy_dict:
        pipeline.hmset(stock[key], stock)
    # executes all the command at once
    pipeline.execute()


def prepare_template(template_dir):
    '''Takes a template directory name as argument
       and returns a template object on 'index.html' file
       which will be served.
    '''
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    template = env.get_template('index.html')
    return template


def auto_complete_list(search_str, names):
    '''Search through stocks names list for matching. 
       If any match found then append to a empty list 
       and return the list'''
    # converting it to a uppercase
    search_str = search_str.upper()
    # initiating a empty search list
    search_list = []
    # iterate through the entire list of stock_names
    # checks if the string name has a start match
    for name in names:
        if name.startswith(search_str):
            # if match found then append the name in the search_list
            search_list.append(name)
    return search_list

def get_from_db(key):
    return conn.hgetall(key)

# creating a DisplayStocks class which will be used to start cherrypy server
class DispalyStocks(object):
    # the home page which will be displayed at page loading
    @cherrypy.expose
    def index(self, count=10):
        return template.render(fields=FIELDS, count=count, stock_data=list(map(lambda x: get_from_db(x), sc_names[:count])))

    # search stock method which takes a string argument
    # by GET method 
    @cherrypy.expose
    def search_stock(self, name=''):
        '''This method takes a text string from user input by GET method
           then search the pattern in the stock names. If any match or 
           matches found then retrieve the data from the database and
           renders in a html document and sends to user.
        '''
        # checking if the search string is not empty
        if len(name)==0:
            return "Give a stock name"
        else:
            # if search string is not empty then search 
            # for similar pattern in stock names
            search_list = auto_complete_list(name, sc_names)
            # now check if search_list is not empty
            if len(search_list) != 0:
                cnt = len(search_list)
                return template.render(fields=FIELDS, count=cnt, stock_data=list(map(lambda x: get_from_db(x), search_list[:cnt])))
            # if search list is empty then return "Nothing found"
            else:
                return "Nothing Found"


if __name__ == "__main__":
    # given url from which page zip file url to be extracted
    url =  "http://www.bseindia.com/markets/equity/EQReports/BhavCopyDebt.aspx?expandable=3"
    # fields which have to render as table in html document
    FIELDS = ['SC_CODE', 'SC_NAME', 'OPEN', 'HIGH', 'LOW', 'CLOSE']
    # creating a redis client object with setting decode_responses as true
    # otherwise redis client returns data as byte object
    conn = redis.StrictRedis(decode_responses=True)
    # creating a pipeline as it is more efficient for running
    # redis commands through redis client
    # it stacks all the commands in a row then finally executes
    # at once sequentially.
    pipeline = conn.pipeline()

    # getting the url for zip file download
    dwnld_url = get_download_url(url)
    # downloading and saving the zip file and getting the file name
    zip_fname = download_zip_file(dwnld_url)
    # extracting the zip file and getting the csv file name
    csv_fname = extract_zip(zip_fname)
    # parsing the csv file and getting a list of dictionaries
    bhav_copy_dct = prepare_csv_data(csv_fname)
    # modifying the 'SC_NAME' field  value in each dictionary
    # as the value contains empty space
    bhav_copy_dct  = modify_name_field(bhav_copy_dct)
    # getting all the stock names for setting as keys in redis hash
    # as stock names are unique it can be used for hash keys
    sc_names = stock_names(bhav_copy_dct)
    # now set the data into the database
    prepare_database(pipeline, bhav_copy_dct)
    # getting the template object for rendering
    template = prepare_template('public')
    # configuration dictionary for cherrypy
    # setting the static directory root path and the public path
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
    # updating the host port information as we are going to host at amazon ec2 instance
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 80})
    # start the cherrypy server
    cherrypy.quickstart(DispalyStocks(), '/', conf)