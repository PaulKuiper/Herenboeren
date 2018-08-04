# Herenboeren
Web app to manage herenboeren farms

# Technology choises
The web app needs to be flexible for new use cases and be able to
run on mobile devices (keeping notes in the field).

## Development tools
For development of the software PyCharm will be used.
For deployment Docker will be used.
For testing we use Jtest (javescript) and nose (python).
For continuous integration testing we use CircleCI
Version control is done on Github.

## Web front end
For the web front end we will use the stencil compiler to make webcomponents.
This also means typescript is used everywhere.

For the interface ionic v4 is used together with capacitor (to access mobile APIs)
to enable a good mobile experience.

For mapping leaflet.js is used, for other visuals D3.js.
Routing is done with stencil router and state mangement with mobx.
For internationalisation we use i18nnext.

## Web server and data crunching
For the backend we use Python 3.6 with the micro webframework
bottle.py and Gevent for efficient multi-threading.
NgInx will be used to serve the static webpages, enable
secure (SHH) reverse proxying to the Python webserver (http and websockets).

## Databases
We need to be able to answer questions like:
 - which plant was planted on which field and when
 - a plant of this family is not allowed on this field anymore for so and so long
 - we need good free text search to search through our notes, plant descriptions etc.
 - we need to store historical weather data and other metrics
 - we need to store geographical (GEOjson) data (field layouts etc.)
 - we need to store documents and images (attached to nodes)
 - we need to be able to easily extend the data model

All these types of data structures have highly specialised database:
- a graph database like Neo4j is very good at relational data
- a search database like ElasticSearch  is good in free text search and suggestions
- a time series database like InfluxDB is good at storing time series and event data
- the file system is best at storing images and files

We are clearly in need of a multi model database, therefore the
best database fit for this project seems to be: MongoDB