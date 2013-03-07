import cherrypy
import os

from interface import Root
current_dir = os.path.dirname(os.path.abspath(__file__))

#TODO: Temporary Hack
from cherrypy.process import servers
def fake_wait_for_occupied_port(host, port): return
servers.wait_for_occupied_port = fake_wait_for_occupied_port

root = Root()

config = {
# Site-wide config, logging...
    'global':
        {'server.socket_host': "127.0.0.1",
        'server.socket_port': 8080,
        'server.environment': 'development',
        'log.error_file': 'site.log',
        'log.screen': True,
        'tools.sessions.on': True,
        'tools.auth.on': True,
        'tools.sessions.timeout': 60,
        'tools.mako.collection_size': 500,
        'tools.mako.directories': "./templates",
        },
#TODO: serve no static files (maybe)
# Static file serving (maybe temporary)
    '/static':
        {'tools.staticdir.on': True,
        'tools.staticdir.dir': os.path.join(current_dir, 'static/'),
        }
    }

cherrypy.quickstart(root, '/', config=config)
