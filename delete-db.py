#jason
import psycopg2

conn = psycopg2.connect("dbname=test user=postgres")
cur = conn.cursor()
cur.execute(
    "DROP TABLE songs;")
conn.commit()
cur.close()
conn.close()
