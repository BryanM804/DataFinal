import dbConnector
import time
import pandas as pd
import matplotlib

DEBUG = True

# The only table from the database we really care about
df = dbConnector.getLiftsDF()

# Data Cleaning

# Due to the method I used to collect the data essentially all of the values are clean
# The only thing that can be cleaner is the times for sets

df["time"] = df["time"].replace("12:00:00 PM", None)
# Some of the times are set to noon from when I was fixing dates one time
# I am also 100% CERTAIN that no existing sets were recorded at 12:00:00 exactly
# otherwise this would not be smart and you would want to create some way of detecting whether a time is valid

# Find the time between each set, if the time is less than 20 seconds it means the user was inputting them
# all at once after they took place so the time is irrelavant
users = dbConnector.runQuery("SELECT DISTINCT userID FROM lifts;")

for user in users["userID"]:
    prev_time = df["time"][0]
    prev_date = df["date"][0]

    for i in range(len(df["time"])):
        c_date = df["date"][i]
        c_time = df["time"][i]

        if not user == df["userID"][i]:
            continue

        if c_time == None or prev_time == None:
            prev_time = c_time
            prev_date = c_date
            continue
        
        if c_date == prev_date:
            # Convert the times into seconds since epoch
            pt = time.strptime("2020 "+prev_time, "%Y %I:%M:%S %p")
            t = time.strptime("2020 "+c_time, "%Y %I:%M:%S %p")
            pt = time.mktime(pt)
            t = time.mktime(t)
            
            if t - pt < 20:
                if DEBUG: print(f"{c_date} {c_time} - {prev_date} {prev_time} less than 20 seconds, removing {df["time"][i - 1]} and {df["time"][i]} for user {user}")
                df.loc[i - 1, "time"] = None
                df.loc[i, "time"] = None
            
            prev_time = c_time
        else:
            prev_date = c_date
            prev_time = c_time

# Squeaky Clean

