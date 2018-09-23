from bottle import response, request, abort, run, default_app, cached_property
from datetime import datetime
from typing import List, Union, Set, Tuple
from collections import OrderedDict
from operator import attrgetter
import uuid
import re
import inflect
import simplejson as json
import shelve
import atexit
from functools import partial
from pydantic import BaseModel, ValidationError
from pydantic.json import pydantic_encoder

inflect_engine = inflect.engine()


def generate_table_name(name):
    """
    Generate a lower case, plural, snake case name of the model name.
    e.g: BigCompany will become big_companies
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)  # CamelCase to snake_case
    snake_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return inflect_engine.plural(snake_name)  # make plural


class Query(BaseModel):
    """
    Defines the query interface that the database handler must support
    It is also used to generate a web API for the DataBaseModel
    """
    filter: str = ''     # Generic filter term: filter=name~=john,age>10,sex!=male
    sort: str = ''       # Multi field sorting: sort=age,-name
    offset = 0           # Paging offset: offset=0
    limit = 25           # Page limit: limit=25
    fields_: str = ''   # Fields to return: fields=name,sex

    class Config:
        fields = {
            'filter':   {'description': 'Generic filter term. e.g.: filter=name~=john,age>10,sex!=male'},
            'sort':     {'description': 'Multi field sorting. e.g.: sort=age,-name'},
            'offset':   {'description': 'Paging offset. e.g.: offset=0'},
            'limit':    {'description': 'Page limit. e.g.: limit=25'},
            'fields_':  {'description': 'Fields to return. e.g.: fields=name,sex',
                         'alias': 'fields'}  # prevent conflicts with the "fields" attribute of BaseModel
        }


class DataBaseModelMount(type(BaseModel)):
    """
    This metaclass will register classes that inherit from DataBaseModel.
    See http://martyalchin.com/2008/jan/10/simple-plugin-framework/
    Also a default table name for the class is generated
    """

    def __init__(cls, name, bases, attrs):
        """
        The first time, the mount point itself is executed and the _models list does not yet exist.
        So therefore this new class shouldn't be registered as a model.
        Instead, it sets up a _models list where plugins can be registered later.
        If the _models list exists then this must be a new class that inherits from the BaseModel class.
        This new class is registered by appending it to the _models list.
        """

        if not hasattr(cls, "_models"):
            cls._models : List[DataBaseModel] = []    # list of all web models
            cls.database_handler = None                      # database handler for all the database models
        else:
            cls._models.append(cls)                   # register the new database model class

    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        x._table = generate_table_name(name)  # set default database table name to save instances of this class in
        return x


class DataBaseModel(BaseModel, metaclass=DataBaseModelMount):
    """
    This is the class to inherit from when you need a database interface to your model.
    The class inherits from BaseModel and the class TYPE is set to DataBaseModelMount.
    The class defines functions to create, delete, and search for instances of a class in a database.
    """

    id: int = None  # A database model instance MUST have a unique ID

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save()  # directly save and generate an unique ID after init

    def save(self):
        cls = self.__class__
        cls.database_handler.set(cls._table, self)

    def _ref(self):
        return f"{self._table}/{self.id}"

    @classmethod
    def _get_value(cls, v, by_alias=False):
        if isinstance(v, DataBaseModel):
            return v._ref()
        elif isinstance(v, BaseModel):
            return v.dict(by_alias=by_alias)
        elif isinstance(v, list):
            return [cls._get_value(v_, by_alias=by_alias) for v_ in v]
        elif isinstance(v, dict):
            return {k_: cls._get_value(v_, by_alias=by_alias) for k_, v_ in v.items()}
        elif isinstance(v, set):
            return {cls._get_value(v_, by_alias=by_alias) for v_ in v}
        elif isinstance(v, tuple):
            return tuple(cls._get_value(v_, by_alias=by_alias) for v_ in v)
        else:
            return v

    @classmethod
    def get_instance(cls, id: int, fields: str= '') -> dict:
        """
        Retrieve an instance of this class from the database using it's unique ID.
        Optionally a comma separated list of fields to return can be specified.
        :return: Dictionary with the instance field values or a KeyError if the object was not found
        """
        if fields:
            fields = {field.strip() for field in fields.split(',')} & set(cls.__fields__)
        else:
            fields = set()
        return cls.database_handler.get(cls._table, id, fields)

    @classmethod
    def set_instance(cls, model: dict) -> dict:
        """
        Create a new instance (id = '') of this class
        Or overwrite an existing instance (id != '').
        A key error will be thrown if the model has a id (other than '') that is not found in the database.
        """
        if model:
            return cls.database_handler.set(cls._table, cls(**model))
        else:
            return {}

    @classmethod
    def delete_instance(cls, id: int) -> dict:
        return cls.database_handler.delete(cls._table, id)

    @classmethod
    def search_instances(cls, query: dict) -> Tuple[List[dict], dict]:
        """
        Get a list of instances of this class from the database.
        Use the query structure to define which objects to return,
        how to sort them and which fields should be returned.

        :param query:  A dictionary with url query parameters
        :return:       A tuple with a list of results and a dictionary with query meta data
        """

        qry = Query(**query).dict(by_alias=True)     # Throws a Validation error if NOK
        filter_regex = re.compile("(.*?)([~=<>!]{1,2})(.*)")
        filter_list, sort_list = [], []

        if query:
            # Parse the filter string in the request
            for item in qry['filter'].split(','):
                item = filter_regex.match(item.strip())
                if item:  # match?
                    field, operator, val = item.groups()  # field name, operator, test value
                    # val = cls.__validators__(field, val)  # convert test value to field type
                    filter_list.append({'field': field, 'operator': operator, 'value': val})

            # Search in the query string for field names, add to filter list with == operator
            for field in (set(cls.__fields__) & set(query.keys())):
                # val = cls.__fields__(field, query[field])  # convert test value to field type
                filter_list.append({'field': field, 'operator': "==", 'value': query[field]})

            # Parse the sort string
            for item in qry["sort"].split(','):  # Sort
                item = item.strip()
                reverse = item.startswith('-')  # desc?
                if reverse:
                    item = item[1:]
                if item in set(cls.__fields__):
                    sort_list.append({'field': item, 'reverse': reverse})

            # Parse the fields string
            valid_fields = {field.strip() for field in qry['fields'].split(',')} & set(cls.__fields__)
            qry['fields'] = valid_fields

        meta = qry.copy()
        qry['filter'], qry['sort'] = filter_list, sort_list
        data, total = cls.database_handler.search(cls._table, qry)
        meta['total'] = total
        return data, meta

# Example of simple database interface implementation

class SimpleDatabase:
    """
    Simple database based using memory or shelve if a filename is supplied.
    Data is loaded into memory during init and is stored back to disc on close.
    """

    def __init__(self, filename = ''):
        if filename:
            self.db = shelve.DbfilenameShelf(filename=filename, writeback=True)
            atexit.register(self.db.close)
        else:
            self.db = {}
        self.cache = {}
        if '_ids' not in self.db:
            self.db['_ids'] = {}
        self.ops_lut = {"==": (lambda x,y: x==type(x)(y)), "!=": (lambda x,y: x!=type(x)(y)),
                        "<": (lambda x,y: x<type(x)(y)), ">": (lambda x, y: x > type(x)(y)),
                        "<=": (lambda x, y: x <= type(x)(y)), ">=": (lambda x, y: x >= type(x)(y)),
                        "~=": (lambda x, y: y.lower() in x.lower())}

    def __del__(self):
        if hasattr(self.db, "close"):
            self.db.close()

    def get(self, table: str, id: int, fields: Set = None) -> dict:
        inst = self.db[table][id]
        if fields:
            return inst.dict(include=fields)
        else:
            return inst.dict()

    def set(self, table: str, model: DataBaseModel) -> dict:
        if table not in self.db:
            self.db[table] = OrderedDict()
            self.db['_ids'][table] = 1
        if model.id is not None:
            if model.id not in self.db[table]:
                raise ValueError(f"{model.__class__.__name__} with id: {model.id} unknown")
        else:
            model.id = self.db['_ids'][table]
            self.db['_ids'][table] = self.db['_ids'][table] + 1
        self.db[table][model.id] = model
        self.cache = {}
        return model.dict()

    def delete(self, table: str, id: int):
        res = self.get(table, id)  # test if the instance exists
        del self.db[table][id]
        self.cache = {}

    def search(self, table: str, query: dict) -> Tuple[List[dict], int]:

        cache_key = table + json.dumps(query["filter"]) + json.dumps(query["sort"])
        if cache_key in self.cache:
            res_list = self.cache[cache_key]              # Cache hit
        else:
            if table not in self.db:
                self.db[table] = OrderedDict()
            res_list = [item for item in self.db[table].values()]  # All items in table
            for item in query["filter"]:                     # Filter
                operator = self.ops_lut[item["operator"]]
                res_list = [res for res in res_list if operator(getattr(res, item["field"]), item["value"])]  # filter list

            for item in reversed(query["sort"]):  # Sort
                res_list.sort(key=attrgetter(item["field"]), reverse=item["reverse"])

            self.cache[cache_key] = res_list

        total = len(res_list)      # Total count after filtering

        if query["limit"] > 0:
            res_list = res_list[query["offset"]:query["offset"] + query["limit"]]

        if query["fields"]:  # Limit fields + convert
            res_list = [inst.dict(include=query["fields"]) for inst in res_list]
        else:
            res_list = [inst.dict() for inst in res_list]
        return res_list, total


# Web API generator


def create_rest_api(app, request, response, prefix="/api/v1/"):

    def set_headers():
        response.content_type = 'application/json; charset=utf-8'   # make it JSON
        response.headers['Access-Control-Allow-Origin'] = '*'       # enable CORS

    def get_object(model, id):
        set_headers()
        fields = request.query.fields or ''
        path = id.split('/')
        try:
            model = model.get_instance(path[0], fields)
            for i, val in enumerate(path[1:]):
                if val == '': continue
                try:
                    model = model[int(val) if i % 2 else val]  # even items are positions in a list so make them integers
                except Exception as e:
                    abort(422, 'URL path NOK: /' + "/".join(path[:i+1]) + f"/{val} <-- NOK " +str(e))  # 422 Unprocessable
            return json.dumps({'data': model}, default=pydantic_encoder)
        except ValidationError as e:
            abort(422, str(e))  # 422 Unprocessable Entity - Used for validation errors
        except KeyError as e:
            abort(404, str(e))  # 404 Not found

    def set_object(model):
        try:
            set_headers()
            return {'data': model.set_instance(request.json)}
        except ValidationError as e:
            abort(422, str(e))  # 422 Unprocessable Entity - Used for validation errors
        except KeyError as e:
            abort(404, str(e))  # 404 Not found

    def delete_object(model, id):
        try:
            set_headers()
            model.delete_instance(id)
            response.code = 204  # No content, resource was successfully deleted
        except KeyError as e:
            abort(404, str(e))   # 404 Not found

    def get_objects(model):
        try:
            set_headers()
            data, meta = model.search_instances(request.query)
            response.headers['X-Total-Count'] = str(meta['total'])
            # urlparts, qry, links = list(request.urlparts), request.query.copy(), []
            # urlparts[3] = "&".join([f"{key}={val}" for key, val in qry.items()])
            # if meta['offset'] > 0:
            #     links.append({'rel': 'prev', 'href': href + meta['limit']})
            return json.dumps({'data': data}, default=pydantic_encoder)
        except ValidationError as e:
            abort(400, str(e))  # 400 Bad Request

    def get_openapi_schema_json():
        set_headers()
        schema_str = json.dumps(openapi_schema(prefix), default=pydantic_encoder)
        return schema_str

    # def get_openapi_schema_yaml():
    #     set_headers()
    #     response.content_type = 'text/yaml'
    #     return yaml.dump(openapi_schema(prefix), default_flow_style=False)

    for model in DataBaseModel._models:
        path = prefix + model._table
        app.route(path, "GET", callback=partial(get_objects, model=model))
        app.route(path + "/", "GET", callback=partial(get_objects, model=model))
        app.route(path + "/<id:path>", "GET", callback=partial(get_object, model=model))
        app.route(path, "POST", callback=partial(set_object,model=model))
        app.route(path + "/", "POST", callback=partial(set_object, model=model))
        app.route(path + "/<id>", "PUT", callback=partial(set_object, model=model))
        app.route(path + "/<id>", "DELETE", callback=partial(delete_object, model=model))

    app.route(prefix + "openapi.json", "GET", callback=get_openapi_schema_json)
    # app.route(prefix + "openapi.yaml", "GET", callback=get_openapi_schema_yaml)


def openapi_schema(prefix: str):
    """
    Produces an open api 3 schema of the rest api actions anf the models

    :param prefix:  URL prefix
    :return:        dict
    """
    schema = { "openapi": "3.0.0",
               "info" :{"title":"API", "version":"1.0.0"},
               "servers": [{"url": prefix}],
               "paths": {},
               "components":{"schemas":{}}}
    query_schema = []
    for name, props in to_json_schema(Query.schema()["properties"]).items():
        query_schema.append({"name": name, "in": "query", "description": props["description"],
                             "required": props["required"], "schema": {"type": props["type"],
                                                                       "default": props["default"]}})
    for model in DataBaseModel._models:  # Loop over all web models
        model_plural = inflect_engine.plural(model.__name__.lower())  # plural name of model
        schema['components']["schemas"][model.__name__.lower()] = to_json_schema(model.schema())
        schema['components']["schemas"][model_plural] = {"type": "array", "items": {"$ref": "#/components/schemas/" + model.__name__.lower()}}
        path = prefix + model._table
        schema['paths'][path] = {"get": {"summary": f"List of {model_plural}",
                                         "parameters": query_schema,
                                         "responses": {"200" : {"description": f"List of {model_plural}"},
                                                       "404": {"description": "No matching record found for the given criteria"}
                                                       }
                                         }
                                 }
        schema['paths'][path + "/{id}"] = {"get": {"summary": f"Get {model.__name__} by ID",
                                                   "parameters": {}}}
    return schema


def to_json_schema(obj):
    type_lut = {'str': 'string', 'int': 'integer', 'bool': 'boolean', 'float': 'number', 'list': 'array'}
    format_lut = {'datetime': 'date-time', 'EmailStr': 'email', 'UrlStr': 'uri'}

    if 'item_type' in obj:
        obj['items'] = {"type": obj['item_type']}
        del obj['item_type']
    if 'type' in obj:
        if obj['type'] in type_lut:
            obj['type'] = type_lut[obj['type']]
        elif obj['type'] in format_lut:
            obj['format'] = format_lut[obj['type']]
            obj['type'] = 'string'
    for key in obj:
        if isinstance(obj[key], dict):
            obj[key] = to_json_schema(obj[key])
    return obj




DataBaseModel.database_handler = SimpleDatabase()

# Define your model as python class (include python typing hints)
class Dude(BaseModel):
    name: str = "test"

class User(DataBaseModel):
    name = 'John Doe'
    signup_ts: datetime = None
    friends: List[Dude] = [Dude()]
    age: int = 3

class Company(DataBaseModel):
    name = 'hhh'
    employees: List[User] = [User()]


User()
User(name="thijs")
User(name="maret")
User(name="paul", signup_ts="2018-10-02T12:56")
User(name="paul")
Company()
Company(name='asml')
Company(name='ulti')

create_rest_api(app=default_app(), request=request, response=response, prefix="/")


if __name__ == '__main__':
    run()
