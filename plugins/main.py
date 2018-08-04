from os.path import join, dirname, realpath
from collections import OrderedDict
from bottle import route, get, static_file, default_app

root = join(dirname(dirname(realpath(__file__))), 'www')  # root directory of the static web files


@route('/build/<path:path>')
def build_url(path):
    return static_file(path, root=root + '/build')

@route('/assets/<path:path>')
def assets_url(path):
    return static_file(path, root=root +'/assets')


@route('/')
@route('/<path:path>')
def root_url(path=None):
    return static_file("index.html", root=root)



@get(['/plugins', '/plugins/'])
def list_plugins():
    res = OrderedDict()
    plugins = default_app().config['server_plugins'].copy()
    plugins.append({'module':'all', 'app': default_app()})
    for p in plugins:
        if 'app' in p and 'module' in p:
            res[p['module']] = {}
            for action in ['GET', 'POST', 'UPDATE', 'DELETE']:
                if action in p['app'].router.static or action in p['app'].router.dyna_routes:
                    res[p['module']][action] = [r[0].rule for r in p['app'].router.static.get(action,{}).values()]
                    res[p['module']][action].extend([r[2].rule for r in p['app'].router.dyna_routes.get(action, [])])
        else:
            res[p['module']] = p['error']
    return res
