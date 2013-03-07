import cherrypy
import os
from mako.template import Template
from mako.lookup import TemplateLookup

from auth import AuthController, require, member_of, name_is, check_credentials
from files import handle_upload

import pymongo
from gridfs import GridFS

def check_file(audio_file):
    if not audio_file or not audio_file.filename:
        return "No file selected."
    if not audio_file.filename.endswith(".mp3"):
        return "Please select an mp3."

class Root(object):
    def __init__(self):
        self.templateLookup = TemplateLookup(directories = ['./templates'])
        self.db = pymongo.Connection('localhost', 27017)['test']
        self.fs = GridFS(self.db)

    @cherrypy.expose
    def index(self):
        """Home Page."""
        count = cherrypy.session.get('count', 0) + 1
        songs = self.db.songs.find({'username': 'joe'})
        template = self.templateLookup.get_template('./index.tmpl')
        return template.render(
                songs=songs,
                )

    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        """Login Page."""
        if username is None or password is None:
            template = self.templateLookup.get_template('./login.tmpl')
            return template.render(from_page=from_page)

        error_msg = check_credentials(username, password)
        if error_msg:
            template = self.templateLookup.get_template('./login.tmpl')
            return template.render(from_page=from_page, error_msg=error_msg)
        else:
            # successful auth
            cherrypy.session['_username'] = cherrypy.request.login = username
            raise cherrypy.HTTPRedirect(from_page)

    @cherrypy.expose
    @require()
    def upload(self, audio_file=None):
        """Upload a song."""
        error_msg = check_file(audio_file)
        if (error_msg):
            template = self.templateLookup.get_template('./upload.tmpl')
            return template.render(error_msg=error_msg)

        file_id = handle_upload(audio_file, self.fs)

        self.db.queue.insert(
                {'stage': 'fingerprint',
                    'username': cherrypy.session['_username'],
                    'priority': 4,
                    'file_id': file_id})

        return self.templateLookup.get_template('./upload.tmpl').render()

root = Root()

# Site-wide config, logging...
cherrypy.config.update({'environment': 'production',
                        'log.error_file': 'site.log',
                        'log.screen': True,
                        'tools.sessions.on': True,
                        'tools.auth.on': True,
                        'tools.sessions.timeout': 60,})

current_dir = os.path.dirname(os.path.abspath(__file__))

# Temporary Hack
from cherrypy.process import servers
def fake_wait_for_occupied_port(host, port): return
servers.wait_for_occupied_port = fake_wait_for_occupied_port

config = {'global':
            {'server.socket_host': "127.0.0.1",
            'server.socket_port': 8080 
            },
    '/static':
            {'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'static/'),
            }
        }

cherrypy.quickstart(root, '/', config=config)






















