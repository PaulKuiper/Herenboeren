#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Core framework

The framework finds and loads web app plugins in the underlying ./plugins folder
The framework then start a webserver to handle http requests
The framework then opens a webbrowser (@ localhost:8080/)

"""

from gevent import monkey   # enable gevent micro threading
monkey.patch_all()          # overwrite standard system functions with gevent version
                            # When debugging with PyCharm: Enable the "Gevent compatible" option !!

import sys
from os import listdir
from os.path import join, dirname, realpath, isdir
from fnmatch import fnmatch
from bottle import default_app, run, get, static_file, route
from logging import getLogger
from importlib import import_module

logger = getLogger()

__author__ = "Paul Kuiper"
__email__ = "pkuiper@gmail.com"
__status__ = "Prototype"
__version__ = "0.1.0"

# ***********************************************
#   Plugin discovery and mounting functions
# ***********************************************

def import_plugins(path=None, pattern="*.py"):
    """
    Finds all python files in the plugins sub directory and its sub-directories and then import them as bottle app.
    If the module contains a global called 'mount_url' then the bottle app will be mounted on the specified url.

    :param path:     The directory (and its sub directories) that will be searched for plugins. Default: ./plugins
    :param pattern:  The file pattern that will be searched for a plugin (e.g. "*_plugin.py"). Default: *.py

    """
    root = dirname(realpath(__file__))      # root directory of this file
    path = path or join(root, "plugins")    # default plugins root directory
    plugins = default_app().config['server_plugins'] = []

    for fn in listdir(path):
        if isdir(fn):
            import_plugins(join(path, fn), pattern)     # plugin sub directory, search here
        if fnmatch(fn, pattern):            # found a plugin
            module = fn[:-3]                # python module name (strip .py extenion and dir)
            url = None    # create a new Bottle app
            default_app.push()              # install all routes during the import on a new default app
            try:
                sys.path.append(path)                    # temporarily add this path to the python system path
                m = import_module(module)                # import the python module (strip .py extenion)
                url = getattr(m, "mount_url", f"/{module}/")  # fetch the url mount point for this plugin
                print(f"mounted: {module}")
            except ImportError as e:
                err_msg = "Could not import plugin module:" + fn + "\n" + str(e)
                logger.exception(err_msg)           # skip files that do not import properly
            finally:
                del sys.path[-1]                    # clean up system path after the import
            plugin = default_app.pop()              # pop the default app with the new routes
            if url and len(plugin.routes):
                if url == "/":
                    default_app().merge(plugin)         # merge the plugin with the root app
                else:
                    default_app().mount(url, plugin)    # mount the plugin onto the root app
                plugins.append({'module': module, 'url': url, 'app': plugin})
            else:
                plugins.append({'module': module, 'error': err_msg})


# ***********************************************
#   Refer all calls to the static files
# ***********************************************
if __name__ == '__main__':
    import_plugins()                                        # load plugins from the plugins folder
    print('Open a webbrowser at: http://localhost:8080/')   # user instructions
    run(debug=True)                                         # run the webserver