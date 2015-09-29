#!/usr/bin/python
#-*-coding:utf-8 -*-

import threading, logging, time
import pickle
import uniout

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer

import mongo_credentials
from pymongo import MongoClient

def main():
    kafka_client = KafkaClient("localhost:9092")
    consumer = SimpleConsumer(kafka_client, "test-group", "twitter_raw")
    consumer.seek(0,2)

    mongo_client = MongoClient(mongo_credentials.connection_string)

    tweets_db = mongo_client.tweets
    filtered_tweets_collection = tweets_db.filtered_tweets_collection
    # raw_tweet_objects_collection = tweets_db.raw_tweets_collection
    # raw_tweets_collection = tweets_db.raw_tweets_collection
    # raw_user_collection = tweets_db.raw_user_collection
    # raw_author_collection = tweets_db.raw_author_collection
    count = 0
    for message in consumer:
        try:
            print count
            count+=1
            filtered_tweet_string = message.message.value.decode('utf-8')
            data_depickled = pickle.loads(filtered_tweet_string)
            filtered_tweets_collection.insert_one(data_depickled)
            # print data_depickled
            # break
            # print message.offset, message.message.value
        except Exception, e:
            print filtered_tweet_string
            raise e
            continue

if __name__ == "__main__":
    # logging.basicConfig(
    #     format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
    #     level=logging.DEBUG
    #     )
    main()