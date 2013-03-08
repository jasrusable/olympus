import cherrypy
import mako_tool

from auth import AuthController, require, member_of, name_is, check_credentials
from files import handle_upload, check_file, gridfs_download

import pymongo
from gridfs import GridFS

import psycopg2

class Root(object):
    login = AuthController.login
    logout = AuthController.logout

    def __init__(self):
        self.db = pymongo.Connection('localhost', 27017)['test']
        self.fs = GridFS(self.db)
        self.conn = psycopg2.connect('dbname=test user=avoid3d')
        self.cursor = self.conn.cursor()

    @cherrypy.expose
    @cherrypy.tools.mako(filename="index.tmpl")
    def index(self):
        """Home Page."""
        cursor = self.cursor
        cursor.execute("SELECT * from songs;")
        songs = cursor.fetchmany(10)
        return {'songs':songs}

    @require()
    @cherrypy.expose
    @cherrypy.tools.mako(filename="uploaded.tmpl")
    def uploaded(self):
        """Songs uploaded by the current user."""
        cursor = self.cursor
        cursor.execute(
                "SELECT * from songs WHERE uploaded_by = %s",
                (cherrypy.session['_username'],))
        songs = cursor.fetchmany(10)
        return {'songs':songs}

    @cherrypy.expose
    @gridfs_download
    def test(self):
        return '5138d7dd931ed25f326c8df7'

    @cherrypy.expose
    @require()
    @cherrypy.tools.mako(filename="upload.tmpl")
    def upload(self, audio_file=None):
        """Upload a song."""
        error_msg = check_file(audio_file)
        if (error_msg):
            return {'error_msg': error_msg}
        file_id = handle_upload(audio_file, self.fs)
        self.db.queue.insert(
                {'stage': 'fingerprint',
                    'username': cherrypy.session['_username'],
                    'priority': 4,
                    'file_id': file_id})
        return {}
