import psycopg2

conn = psycopg2.connect("dbname=test user=postgres")
cur = conn.cursor()
cur.execute(
    "CREATE TABLE songs " + 
    "(id serial PRIMARY KEY, title varchar, music_brainz_id varchar, uploaded_by varchar);")
conn.commit()
cur.close()
conn.close()
