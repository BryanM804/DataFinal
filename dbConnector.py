import mysql.connector

# Obviously not secure but this is just for my own use
con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="workoutdb"
)

def getLiftsDF():
    if con and con.is_connected():
        with con.cursor() as cursor:
            results = cursor.execute("SELECT * FROM lifts;")
            lifts = cursor.fetchall()
            for row in lifts:
                print(row)
    else:
        print("Connection error.")