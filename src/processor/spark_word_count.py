#!/usr/bin/python
#-*-coding:utf-8 -*-

import sys
import threading, logging, time
import pickle
import uniout
import redis

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from operator import add

reload(sys)  
sys.setdefaultencoding('utf8')
redis = redis.StrictRedis(host='localhost', port=6379, db=0)

def publishToRedis(count):
    result = count.collect()
    if result:
        redis.publish("word_count", result[0])

def main():
    sc = SparkContext(appName="PythonStreamingKafkaWordCount")
    ssc = StreamingContext(sc, 1)

    zkQuorum = "localhost:2181"
    topic = "twitter_raw"
    kvs = KafkaUtils.createStream(ssc, zkQuorum, "spark-streaming-consumer", {topic: 1})
    lines = kvs.map(lambda x: pickle.loads(x[1].decode('utf-8'))['text'])  # fetch the text
    count = lines.map(lambda line: len(line.split())).reduce(add)  # split into words and count
    count.foreachRDD(publishToRedis)  # publish to redis
    count.pprint()

    ssc.start()
    ssc.awaitTermination()

if __name__ == "__main__":
    main()