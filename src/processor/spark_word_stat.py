#!/usr/bin/python
#-*-coding:utf-8 -*-

import sys
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )  # add src to path

from utils.priority_dict import PriorityDict
import threading, logging, time
import pickle
import uniout
import redis
import re

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

import nltk
from nltk.tag.perceptron import PerceptronTagger

reload(sys)  
sys.setdefaultencoding('utf8')
redis = redis.StrictRedis(host='localhost', port=6379, db=0)
tagger = PerceptronTagger()

def publishToRedis(wordStats):
    stats = wordStats.collect()
    if stats:
        pickled_stats = pickle.dumps(stats)
        redis.publish("word_stats", pickled_stats)

def main():
    sc = SparkContext(appName="PythonStreamingKafkaWordCount")
    ssc = StreamingContext(sc, 1)

    zkQuorum = "localhost:2181"
    topic = "twitter_raw"
    kvs = KafkaUtils.createStream(ssc, zkQuorum, "spark-streaming-consumer", {topic: 1})
    data = kvs.map(lambda bytes_data: pickle.loads(bytes_data[1].decode('utf-8')))  # depickle
    eng_data = data.filter(lambda x: x['lang']=='en')  # keep only english
    eng_lines = eng_data.map(lambda x: x['text'].decode('utf-8'))  # fetch the text
    words = eng_lines.flatMap(lambda line: re.compile('\w+').findall(line))  # only extract words (naive tokenizer)
    tagged = words.map(lambda word: nltk.tag._pos_tag([word.lower()], 'universal', tagger)[0])
    # words_lists = eng_lines.map(lambda line: re.compile('\w+').findall(line))  # only extract words (naive tokenizer)
    # tweetsContainSomeWords = words_lists.filter(lambda tweet: "que" in tweet)
    # tagged = words_lists.flatMap(lambda words: nltk.tag._pos_tag(words, 'universal', tagger))
    # tagged = eng_lines.flatMap(lambda line: nltk.word_tokenize(line))
    nouns = tagged.filter(lambda pair: len(pair[0])>2 and pair[1]=="NOUN").map(lambda pair: pair[0])
    pairs = nouns.map(lambda noun: (noun, 1))
    wordStats = pairs.reduceByKey(lambda x, y: x + y)
    wordStats.foreachRDD(publishToRedis)  # publish to redis
    wordStats.pprint()
    # tweetsContainSomeWords.pprint()

    ssc.start()
    ssc.awaitTermination()

if __name__ == "__main__":
    main()