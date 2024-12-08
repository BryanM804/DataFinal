import dbConnector
import time
import pandas as pd
import matplotlib

DEBUG = True

users = dbConnector.runQuery("SELECT DISTINCT userID FROM lifts;")["userID"]
dfs = []
for user in users:
    dfs.append(dbConnector.runQuery(f"SELECT * FROM lifts WHERE userID='{user}';"))
    print(f"Created data frame for user {user}")

# Since we want to compare statistics on users separately I gave each user their own data frame to operate on

# Data Cleaning

# Due to the method I used to collect the data essentially all of the values are clean
# The only thing that can be cleaner is the times for sets

for df in dfs:
    df["time"] = df["time"].replace("12:00:00 PM", None)

# Some of the times are set to noon from when I was fixing dates one time
# I am also 100% CERTAIN that no existing sets were recorded at 12:00:00 exactly
# otherwise this would not be smart and you would want to create some way of detecting whether a time is valid

# Find the time between each set for each user, if the time is less than 20 seconds it means the user was inputting them
# all at once after they took place so the time is irrelavant

count = 0

for df in dfs:
    prev_time = df["time"][0]
    prev_date = df["date"][0]

    for i in range(len(df["time"])):
        c_date = df["date"][i]
        c_time = df["time"][i]

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
                if DEBUG: print(f"{c_date} {c_time} - {prev_date} {prev_time} less than 20 seconds, removing {df["time"][i - 1]} and {df["time"][i]} for user {df["userID"][0]}")
                df.loc[i - 1, "time"] = None
                df.loc[i, "time"] = None
                count += 1
            
            prev_time = c_time
        else:
            prev_date = c_date
            prev_time = c_time

print(f"Removed {count} bad values.")

# Remove outliers
# Sometimes there are occurrences where people may log things that are far off of their regular sets like a 1 rep max set or
# just a 1 off set of something. We don't want those in our data
outliers = 0

for df in dfs:
    mean = pd.to_numeric(df["settotal"]).mean()
    std = pd.to_numeric(df["settotal"]).std()
    print(f"{df["userID"][0]} outliers: ")
    for x, v in df["settotal"].items():
        z = (float(v) - mean)/std
        # Since the set totals should be going up over time I considered an outlier
        # to be pretty far off of normal so that we don't remove any data that is just old 
        if z > 4.0 or z < -4.0:
            print(z)
            df.loc[x, "settotal"] = None
            outliers += 1

print(f"Removed {outliers} outliers")

