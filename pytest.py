# test_conn.py
import mysql.connector, sys

CONF = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "Kavish@76",
    "database": "query_optimizatio2",
    "allow_local_infile": True
}

try:
    cnx = mysql.connector.connect(**CONF)
    print("Connected! Server version:", cnx.get_server_info())
    cur = cnx.cursor()
    cur.execute("SELECT DATABASE();")
    print("Current DB:", cur.fetchone()[0])
    cur.close()
    cnx.close()
except mysql.connector.Error as err:
    print("Connect failed:", err)
    sys.exit(1)
except Exception as e:
    print("Unexpected error:", e)
    sys.exit(1)
