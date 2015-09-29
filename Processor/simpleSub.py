#!/usr/bin/python
#-*-coding:utf-8 -*-

import sys
import threading, logging, time
import pickle
import uniout
import redis

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer

reload(sys)  
sys.setdefaultencoding('utf8')
redis = redis.StrictRedis(host='localhost', port=6379, db=0)

def main():
    client = KafkaClient("localhost:9092")
    consumer = SimpleConsumer(client, "test-group", "twitter_raw")
    consumer.seek(0,2)

    num = 0
    for message in consumer:
        print "redis publish:", num
        num+=1
        try:
            data_depickled = pickle.loads(message.message.value.decode('utf-8'))
        except Exception, e:
            continue

        ### process data here ###

        data_pickled = pickle.dumps(data_depickled)
        redis.publish('tweets_processed', data_pickled)

if __name__ == "__main__":
    main()