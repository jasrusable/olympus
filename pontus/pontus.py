import pymongo
from gridfs import GridFS
from bson import ObjectId
import acoustid
from pprint import pprint

import psycopg2

db = pymongo.Connection('localhost', 27017)['test']

conn = psycopg2.connect("dbname=test user=postgres")

def lookup(audio_file):
    fingerprint = audio_file['fingerprint']
    duration = audio_file['duration']

    return acoustid.lookup('cSpUJKpD', fingerprint, duration)['results']

while(True):
    queue_entry = db.queue.find_and_modify(
        query={"stage": "metadata"},
        sort={"priority": -1},
        update={"$set": {"stage": "metadata_inprogress"}},
        new=True
    )
    if (queue_entry):
        # Obtain the GridOut object.
        audio_file = db.fs.files.find_one(
                {'_id': ObjectId(queue_entry['file_id'])})

        results = lookup(audio_file)
        print(results)

#TODO: this is temporary
        music_brainz_id = results[0]['recordings'][0]['id']
        title = results[0]['recordings'][0]['title']
        uploaded_by = queue_entry['username']

        cur = conn.cursor()

        cur.execute(
            "INSERT INTO songs " + 
                "(music_brainz_id, title, uploaded_by)" + 
            "VALUES (%s, %s, %s);",
                (music_brainz_id, title, uploaded_by,))

        conn.commit()
