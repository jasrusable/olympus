import cherrypy
import os
from mako.template import Template
from mako.lookup import TemplateLookup

import pymongo
from gridfs import GridFS

class Root(object):
    def __init__(self):
        self.templateLookup = TemplateLookup(directories = ['./templates'])
        self.db = pymongo.Connection('localhost', 27017)['test']
        self.fs = GridFS(self.db)

    @cherrypy.expose
    def index(self):
        """Home Page."""
        songs = self.db.songs.find()
        print(songs)
        return self.templateLookup.get_template('./index.tmpl').render(songs=songs)

    @cherrypy.expose
    def upload(self, audio_file=None):
        """Upload a song."""
        if (audio_file):
            print("Filename", audio_file.filename)
            new_file = self.fs.new_file(filename = audio_file.filename)

            # CherryPy reads the uploaded file into a temporary file;
            # myFile.file.read reads from that.
            size = 0
            while True:
                data = audio_file.file.read(8192)
                if not data:
                    break
                new_file.write(data)

            new_file.close()
            self.db.queue.insert({'stage': 'fingerprint', 'priority': 4, 'file_id': new_file._id})
            print("hello world", new_file._id)
            print(self.fs.list())
        return self.templateLookup.get_template('./upload.tmpl').render()


root = Root()


# Site-wide config, logging...
cherrypy.config.update({'environment': 'production',
                        'log.error_file': 'site.log',
                        'log.screen': True})

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






















