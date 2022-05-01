from pymongo import MongoClient
import os
import logging
import certifi
import re

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logging.info('Started')

db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_url = os.getenv('DB_LINK')

db_cluster = MongoClient(db_url.format(
    db_user, db_pass), tlsCAFile=certifi.where())


dbnames = db_cluster.list_database_names()

for name in dbnames:
    name = str(name)
    pipeline = [{'$match': {'_id': {'$exists': 'true'}}},
                {'$merge': {'into' : {'db': 'Servers', 'coll': name}}}]
    if re.match('[0-9]+', name):
        logging.info(f"Cloning settings for {name}")
        db_cluster[name].settings.aggregate(pipeline)
        logging.info(f"Cloning members for {name}")
        db_cluster[name].members.aggregate(pipeline)
        # after successful run and changing the bot comment out above and comment in below
        # db_cluster.drop_database(name)
        #logging.info(f"Deleting DB: {name}")
