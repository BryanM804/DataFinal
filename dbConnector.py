import mysql.connector
import pandas as pd

# Obviously not secure but this is just for my own use
con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="workoutdb"
)

def getLiftsDF():
    if con and con.is_connected():
        query = "SELECT * FROM lifts"
        df = pd.read_sql(query, con=con)
        return df
    else:
        print("Connection error.")

def runQuery(query):
    if con and con.is_connected():
        df = pd.read_sql(query, con)
        return df
    else:
        print("Connection error.")