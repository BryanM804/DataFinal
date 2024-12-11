import dbConnector
import time
import sys
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

DEBUG = True

movement = sys.argv[1] if len(sys.argv) >= 2 else None
method = sys.argv[2] if len(sys.argv) >= 3 else None

if (movement == "L"):
    for m in dbConnector.getExerciseList()["movement"]:
        print(m)
    exit()

if (movement == None or method == None):
    analysis_methods = ["day_average", "adjusted_average", "best"]

    print("Missing arguments, please run with a movement and analysis method as arguments.")
    print("Or run with 'L' for a list of valid movements.")
    print("Valid analysis methods: ")
    for m in analysis_methods:
        print(m)
    print("Run with H <analysis_method> for more details")
    exit()

if not dbConnector.checkMovementList(movement):
    print(f"{movement} is not a valid movement, please check the movement list with 'L'")
    exit()

users = dbConnector.runQuery("SELECT DISTINCT userID FROM lifts;")["userID"]
dfs = []
for user in users:
    dfs.append(dbConnector.runQuery(f"SELECT * FROM lifts WHERE userID='{user}';"))
    print(f"Created data frame for user {user}")

# Since we want to compare statistics on users separately I gave each user their own data frame to operate on

# Data Cleaning

dfs = [x for x in dfs if movement in x["movement"].values]
# Don't need the users with no data

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
        if z > 3.0 or z < -3.0:
            print(z)
            df.loc[x, "settotal"] = None
            outliers += 1

print(f"Removed {outliers} outliers")

# Data Visualization

i = 0
j = 0
x = math.ceil(math.sqrt(len(dfs)))
fig, axes = plt.subplots(x, x)

# These are for the linear regression later
xvals = []
yvals = []
my_y_fit = 0

if method == "day_average":
    for df in dfs:
        # Get the average of all the sets of movement for each day for each user and plot them
        prev_date = df["date"][0]
        user = df["userID"][0]
        count = 0
        avgs = []
        dates = []
        sum = 0
        
        for set in df.itertuples():
            if set.movement != movement:
                continue

            if set.date == prev_date:
                if set.settotal != None:
                    sum += set.settotal
                    count += 1
            else:
                if count > 0:
                    avgs.append(sum/count)
                    dates.append(prev_date)
                prev_date = set.date
                count = 0
                sum = 0
        if DEBUG: print(f"User: {user}, Dates: {dates} Avgs: {avgs}")
        if len(avgs) > 1:
            username = dbConnector.getDisplayName(df["userID"][0])
            xs = [x for x in range(len(dates))]
            xs = np.array(xs)
            slope, intercept = np.polyfit(xs, avgs, 1)
            y_fit = slope * xs + intercept

            if username == "brymul":
                xvals = [[x] for x in range(len(xs))]
                yvals = avgs
                my_y_fit = y_fit

            axes[i, j].scatter(dates, avgs, color="blue", label="Set Averages Per Day")
            axes[i, j].plot(dates, y_fit, color="orange")
            axes[i, j].set_xlabel("Date")
            axes[i, j].set_ylabel("Average Set Total")
            axes[i, j].legend()
            axes[i, j].set_title(username)
        j = j if i + 1 < x else j + 1
        i = i + 1 if i + 1 < x else 0
elif method == "adjusted_average":
    for df in dfs:
        # Adjust the average of the day average data based on how many previous sets the user did
        prev_date = df["date"][0]
        user = df["userID"][0]
        avgs = []
        dates = []
        sum, count, allcount = 0, 0, 0

        for set in df.itertuples():
            if set.date == prev_date:
                allcount += 1
                if set.movement == movement and set.settotal != None:
                    sum += set.settotal
                    count += 1
            else:
                if count > 0:
                    avg = sum/count
                    avg += 100 * ((allcount - count) / 4)
                    if DEBUG: print(f"Adding {((allcount - count) / 4) * 100} to avg, allcount at {allcount} sets")
                    avgs.append(avg)
                    dates.append(prev_date)
                prev_date = set.date
                allcount = 0
                count = 0
                sum = 0
        if DEBUG: print(f"User: {user}, Dates: {dates} Avgs: {avgs}")
        if len(avgs) > 1:
            username = dbConnector.getDisplayName(df["userID"][0])
            xs = [x for x in range(len(dates))]
            xs = np.array(xs)
            slope, intercept = np.polyfit(xs, avgs, 1)
            y_fit = slope * xs + intercept

            if username == "brymul":
                xvals = [[x] for x in range(len(xs))]
                yvals = avgs
                my_y_fit = y_fit

            axes[i, j].scatter(dates, avgs, color="blue", label="Adjusted Day Averages")
            axes[i, j].plot(dates, y_fit, color="orange")
            axes[i, j].set_xlabel("Date")
            axes[i, j].set_ylabel("(Adjusted) Average Set Total")
            axes[i, j].legend()
            axes[i, j].set_title(username)
        j = j if i + 1 < x else j + 1
        i = i + 1 if i + 1 < x else 0
elif method == "best":
    for df in dfs:
        # Get the best set total of the movement for each day for each user and plot them
        prev_date = df["date"][0]
        user = df["userID"][0]
        maxes = []
        dates = []

        max = 0
        for set in df.itertuples():
            if prev_date != set.date:
                if max > 0:
                    maxes.append(max)
                    dates.append(prev_date)
                prev_date = set.date
                max = 0
                continue

            if set.movement == movement and set.settotal > max:
                max = set.settotal
        if DEBUG: print(f"User: {user}, Maxes: {maxes}, Dates: {dates}")
        if len(maxes) > 1:
            username = dbConnector.getDisplayName(df["userID"][0])
            xs = [x for x in range(len(dates))]
            xs = np.array(xs)
            slope, intercept = np.polyfit(xs, maxes, 1)
            y_fit = slope * xs + intercept

            if username == "brymul":
                xvals = [[x] for x in range(len(xs))]
                yvals = maxes
                my_y_fit = y_fit

            axes[i, j].scatter(dates, maxes, color="blue", label="Best Totals")
            axes[i, j].plot(dates, y_fit, color="red")
            axes[i, j].set_xlabel("Date")
            axes[i, j].set_ylabel("Best Set Total")
            axes[i, j].legend()
            axes[i, j].set_title(username)
        j = j if i + 1 < x else j + 1
        i = i + 1 if i + 1 < x else 0
print("Showing graphs...")
plt.show()

# Prediction Using Linear Regression

# Since my user has by far the most data that is the one I will use for this part
# By this point whichever metric the user has chosen should have populated xvals and yvals with my data

# Test size controls the split of the data 0.2=20%
xtrain, xtest, ytrain, ytest = train_test_split(xvals, yvals, test_size=0.2)

print(f"training x: {xtrain}, training y: {ytrain}")
print(f"testing x: {xtest}, testing y: {ytest}")

model = LinearRegression()
model.fit(xtrain, ytrain)

ypredict = model.predict(xtest)
mserror = mean_squared_error(ytest, ypredict)
r2score = r2_score(ytest, ypredict)

print(f"Mean sqaured error: {mserror}")
print(f"R squared score: {r2score}")

predict_line = model.predict(xvals)

plt.scatter(xvals, yvals, color="blue")
plt.plot(xvals, predict_line, color="orange", label="Predicted")
plt.plot(xvals, my_y_fit, color="red", label="Best Fit")
plt.legend()
plt.show()