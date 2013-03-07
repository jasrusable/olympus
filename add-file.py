#!/usr/bin/python
import pymongo
from gridfs import GridFS

db = pymongo.Connection('localhost', 27017)['test']
fs = GridFS(db)

filename = "test.mp3"

audio_file = open("test.mp3", "rb")

new_file = fs.new_file(filename=filename)

# CherryPy reads the uploaded file into a temporary file;
# myFile.file.read reads from that.
size = 0
while True:
    data = audio_file.read(8192)
    if not data:
        break
    new_file.write(data)

new_file.close()
db.queue.insert({'stage': 'fingerprint', 'priority': 4, 'file_id': new_file._id})
