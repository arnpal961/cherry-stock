# cherry-stock
**This project basically implements a cherrypy webserver to search and list stock data. It downloads the data from a given url, parses it stores it in a redis database. When user search a stock it looks into the database fetches it and returns the redered html as a table structure.**

**Project directory structure**
--
```
|-- LICENSE
|-- README.md
|-- main.py
`-- public
    |-- css
    |   `-- style.css
    `-- index.html
```

**External libraries used**
--
```
bs4
requests
cherrypy
redis
jinja2
```
 **Description of each external libraries**
--
* `bs4` is BeautifulSoup module for parsing and traversing through html dom.

* `requests` is used for making web requests and fetching html document .

* `cherrypy` is the micro web framework which runs the server.

* `redis` is the python redis client for connecting to **redis** database.

* `jinja2` is the python templating library.

**Explanation of each functions and class in `main.py`**
--
* `get_download_url(url)`: It takes the original given `url` as argument fetch the webpage extracts all the links in the page then filters the link referred to **bhav copy zip file**. It returns the download link.

* `download_zip_file(download_url)`: It takes the `download_url` as argument downloads and saves it in working directory and returns ZIP file name.
* `extract_zip(zip_file_name)`: Takes the `zip_file_name` as argument and extracts the CSV file in it and returns the CSV file name.
* `prepare_csv_data(csv_file_name)`: Takes the `csv_file_name` as argument reads the csv file prepares the data and returns a list of dictionary which holds the data. The return type is `[{key1:'val11',..},{key1:'val12',..},...{key1:'val1n',..}]`.
  
* `strip_name(data_dict)`: Basically the `SC_NAME` field contains the name of each **Stock** which has more than one empty spaces at last. This function takes an individual `data_dict` as argument then gets the value of the key `'SC_NAME' ` then strips the empty space and returns the dictionary.
* `modify_name_field(bhav_copy_dict)`: Here it takes the entire list of data dictionary updates the `'SC_NAME'` field by the help of `strip_name()` function and returns it.
* `stock_names(bhav_copy_dict)`: Creates a list of all stock names from the `bhav_copy_dict` passed, ehich will be used for setting hash keys and searching purposes.
* `prepare_database(pipeline, bhav_copy_dict)`: It takes an `pipeline ` object and the list of dictionary as input sets the data in redis database server.
* `prepare_template(template_dir)`: This function takes the `template_dir` as arguments where all the static files are stored and creates a template object of `index.html` and returns it.
  
* `auto_complete_list(search_str, names)`: Takes the `search_str` and list of stock names as input, search for starting pattern in each item of the list. If any match or matches found returns the append it to a list and returns it.
* `get_from_db(key)`: Here `type(url) = str`. Takes the `hash key` as the arguments fetches the data from database and returns it. It also uses a connection object which is globally availavle.
* `DisplayStocks()`: This is the main class. A instance of this will be provided as a argument in `cherrypy.quickstart()` function. It has two main methods explained below.
   * `index(count=10)`: This method controls the logic how the home page will be displayed.The `count` argument passed to show the number of stocks data to be rendered. It is controlled by serverside logic. Need to implement client side logic to control the number of stocks to be displayed.
   * `search_stock(name='')`: It  takes a 'string' as an user argument from client side and search through the `stock_names` list, if found any matches retrieves the data from database renders the html and returns it to client.
  

### **Explanation of arguments used in `template.render()`**

Basically it renders the `index.html` document in `public/` folder. The `template.render()`  function takes 3 arguments to render a dynamic html document. First argument is a `fields` list, the second is `count` and the third is the list of data in dictionary format named `stock_data`.

```
<tr>
 {% for field in fields %}
    <th>{{field}}</th>
        {% endfor %}
</tr>
```
Here in the above first we render the table header with required fields. For this reason we use a `for-loop` block. For this we need `fields` as first argument passed in the `template.render()` function.
```
{% for data in stock_data[:count] %}
    <tr>
        {% for field in fields %}
            <td>{{data[field]}}</td>
        {% endfor %}
    </tr>
 {% endfor %}
```
In the above case we need three arguments. First is the `stock_data` and the `count` number. The `stock_data` is a `list` of `dictionary` object which holds the data. The `fields` argument is the same as above.
The first `for loop` iterates through the each item in `stock_data[:count]` and then the second `for loop` iterates through the each `field` in `fields` and renders the html table.

**Explanation of `template.render()`**
```
template.render(fields=FIELDS, count=cnt, stock_data=list(map(lambda x: get_from_db(x), search_list[:cnt])))
```
This function takes three arguments already mentioned above.

`get_from_db(x)` function takes the **hash key** value as the argument
retrieve data from database. Here in this function we also use a **global** client named `conn`.

`search_list` is the `list` object contains the value of `SC_NAME` fields. The `map()` function maps each item of search_list to `get_from_db()` function and returns a `python generator` object. Then use the `list()` function to iterate through each mapping and retrieves the data.

## **Drawbacks and What can be Improved**
* First of all it only displays the first 10 entries of stock data.
  
* The search pattern only search through the start of the string which can be more improved using regular expression and searching through the entire name string.
* It connects to a local database. A more sophisticated and secure way is creating a **AMAZON ELASTIC SEARCH REDIS DATABASE** or **HEROKU-REDIS database** then connect it through python client.
* This application is hosted in an **Amazon-ec2** instance. It's better to use **Amazon Elastic Benstalk** or **Heroku App** which is more reliable and secure.
* Proper methods to be implement to handle *errors and exceptions*.
* There should be `automatic_refresh` function which handles and refresh the data after every certain period.