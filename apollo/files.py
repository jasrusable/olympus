#TODO: set up gridfs as an option in the site-config
from gridfs import GridFS
from pymongo import MongoClient
import bson

db = MongoClient()['test']
fs = GridFS(db)

# Read chunk size.
READ_CHUNK_SIZE = 8192
def check_file(audio_file):
    if not audio_file or not audio_file.filename:
        return "No file selected."
    if not audio_file.filename.endswith(".mp3"):
        return "Please select an mp3."

def handle_upload(_file, _fs):
    # Ask for a new GridIn file.
    gridin = _fs.new_file(filename = _file.filename)

    print("handling")
    # Write to the GridIn file in chunks.
    while(True):
        data = _file.file.read(READ_CHUNK_SIZE)
        if not data:
            break
        gridin.write(data)

    gridin.close()

    return gridin._id

#TODO: find out what the generic word for 'handler' is
def gridfs_download(f):
    def decorate(handler):
        file_id = f(handler)

        gridout = fs.get(bson.ObjectId(file_id))
        return gridout.read()
    return decorate
