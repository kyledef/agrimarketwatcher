from . import fetcher
from . import fisheries
# import fire
# import predict
from . import fcm
from pymongo import MongoClient
import datetime
import copy
import logging

MIN_DIFF = 1.0


def connect2DB():
    try:
        client = MongoClient("mongodb://agriapp:simplePassword@ds043057.mongolab.com:43057/heroku_app24455461")
        db = client.get_default_database()
        return db
    except Exception as e:
        print(str(e))
        return None


def formatMessage(curr_rec, prev_rec, msg_type="daily"):
    if msg_type == "daily":
        message = {
            'commodity': curr_rec['commodity'],
            'date': curr_rec['date'].strftime('%Y-%m-%dT%H:%M:%S'),
            'price': curr_rec['price'],
            "previous": prev_rec['price']
        }
    else:
        message = {
            'commodity': curr_rec['commodity'],
            'date': curr_rec['date'].strftime('%Y-%m-%dT%H:%M:%S'),
            'mean': curr_rec['mean'],
            "previous": prev_rec['mean']
        }

    return message


def updateGeneralDataSet(curr, prev, typeR="daily"):
    print("Updating General Dataset")
    db = connect2DB()
    if db:
        if typeR == "daily":
            dateRec = db.daily.find().sort("date", -1).limit(1)
            print("Previous Date: ", dateRec[0]['date'], " Current Date: ", curr['date'])
            print("Current Date " + str(len(curr)))

            if dateRec[0]['date'] != curr['date']:
                db.daily.insert(curr)
                print("from ", dateRec[0]['date'], " to", curr['date'])
        else:  # monthly
            dateRec = db.monthly.find().sort("date", -1).limit(1)
            if dateRec[0]['date'] != curr['date']:
                db.monthly.insert(curr)
                print("from ", dateRec[0]['date'], " to ", curr['date'])


def handleDifference(before, current, typeR="daily"):
    db = connect2DB()
    if before is not None and current is not None:
        print("Before " + before[0]['date'].ctime())
        print("Current " + current[0]['date'].ctime())
        if before[0]['date'].ctime() != current[0]['date'].ctime():
            for b in before:
                for c in current:
                    if b['commodity'] == c['commodity']:
                        if typeR == "daily":
                            if abs(b['price'] - c['price']) > MIN_DIFF:
                                print("price for ", b['commodity'], " changed")
                                # Add new record to the general dataset
                                # updateGeneralDataSet(c, b, typeR)
                                # Send Push notification of change record
                                change = "increased"
                                if b['price'] >= c['price']:
                                    change = "decreased"
                                message = c['commodity'] + " has " + change + " to $" + str(c['price']) + " per " + c['unit']
                                name = b['commodity'].replace(" ", "")
                                idx = name.find("(")
                                fcm.notify(message, name)
                            else:
                                print("price for ", b['commodity'], " remained the same")
                            # Attempt to predict crops (NB disabled for time being)
                            # pred = predict.run(c['commodity'])
                            # if pred != -1:
                            #     newRec = {"name" : c['commodity'], "price" : pred}
                            #     db.predictions.insert(newRec)
                            # breaktypeR

            if typeR == "daily":
                fetcher.storeMostRecentDaily(db, current)
                fetcher.storeDaily(db, current)
                # fire.sendFire(current)
                # fire.sendRecent(current)
            if typeR == "monthly":
                print(current)
                fetcher.storeMostRecentMonthly(db, current)
                fetcher.storeMonthly(db, current)
        else:
            logging.info("no new record found")
    else:
        logging.info("Doesn't exist")


def run():
    db = connect2DB()
    if db:
        # Attempt to retrieve Crops Information
        try:
            recsCurrent = fetcher.getMostRecent()
            if recsCurrent:
                handleDifference(list(db.recentMonthly.find()), recsCurrent['monthly'], "monthly")
                handleDifference(list(db.dailyRecent.find()), recsCurrent['daily'], "daily")
        except Exception as e:
            logging.error(e)

        # Attempt to retrieve Fishing Information
        try:
            fisheries.getMostRecentFish()
        except Exception as e:
            logging.error(e)


def daily_converter(rec):
    rec['date'] = rec['date'] + datetime.timedelta(days=10)
    rec['price'] += 1
    return rec


def conversionTesting():
    db = connect2DB()
    if db:
        recsD = list(db.dailyRecent.find())
        recs2 = copy.deepcopy(recsD)
        recs2 = list(map(daily_converter, recs2))

        print(len(recsD))
        print(recsD[0]['price'])
        print(len(recs2))
        print(recs2[0]['price'])

        handleDifference(recsD, recs2)


if __name__ == "__main__":
    print("Attempting To Run the server")
    run()
