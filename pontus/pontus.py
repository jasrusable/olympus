import pymongo
from gridfs import GridFS
from bson import ObjectId
import acoustid
from pprint import pprint

db = pymongo.Connection('localhost', 27017)['test']

while(True):
    queue_entry = db.queue.find_and_modify(
        query={"stage": "metadata"},
        sort={"priority": -1},
        update={"$set": {"stage": "metadata_inprogress"}},
        new=True
    )
    if (queue_entry):
        audio_file = db.fs.files.find_one(
                '_id': ObjectId(queue_entry['file_id'])})
        fingerprint = audio_file['fingerprint']
        duration = audio_file['duration']

        results = acoustid.lookup('cSpUJKpD', fingerprint, duration)['results']
        music_brainz_id = results[0]['recordings'][0]['id']
        title = results[0]['recordings'][0]['title']

        db.songs.insert(
                {'music_brainz_id': music_brainz_id,
                    'music_brainz_title': title})
