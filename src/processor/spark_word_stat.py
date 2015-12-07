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
from operator import add, sub

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

BLACK_LIST_WORDS = set(["https", "amp"])
MINIMUM_WORD_LENGTH = 3
PERMIT_TAG = "NOUN"

def publishToRedis(wordStats):
    stats = wordStats.collect()
    if stats:
        pickled_stats = pickle.dumps(stats)
        redis.publish("word_stats", pickled_stats)

def wordFilter(word_and_tag):
    word, tag = word_and_tag
    return (len(word)>=MINIMUM_WORD_LENGTH) and (tag==PERMIT_TAG) and (word not in BLACK_LIST_WORDS)

def getWordStats(raw_tweet):
    eng_data = raw_tweet.filter(lambda x: x['lang']=='en')  # keep only english
    eng_lines = eng_data.map(lambda x: x['text'].decode('utf-8'))  # fetch the text
    words = eng_lines.flatMap(lambda line: re.compile('\w+').findall(line))  # only extract words (naive tokenizer)
    tagged = words.map(lambda word: nltk.tag._pos_tag([word.lower()], 'universal', tagger)[0])
    # tagged = eng_lines.flatMap(lambda line: nltk.word_tokenize(line))  # tokenize with nltk (has encoding error)
    nouns = tagged.filter(wordFilter).map(lambda pair: pair[0])
    wordStats = nouns.map(lambda noun: (noun, 1)).reduceByKey(add)
    # wordStats = nouns.countByValue()  # does not work because of bugs in PySpark?
    # wordStats = nouns.map(lambda noun: (noun, 1)).reduceByKeyAndWindow(add, sub, WINDOW_WIDTH, UPDATE_INTERVAL)  # does not work because it needs checkpoint, but checkpoint hates redis.publish
    wordStats.foreachRDD(publishToRedis)  # publish to redis
    wordStats.pprint()

def printTweetWithSomeWord(raw_tweet, word):
    eng_data = raw_tweet.filter(lambda x: x['lang']=='en')  # keep only english
    eng_lines = eng_data.map(lambda x: x['text'].decode('utf-8'))  # fetch the text
    words_lists = eng_lines.map(lambda line: re.compile('\w+').findall(line))  # only extract words (naive tokenizer)
    tweetsContainSomeWord = words_lists.filter(lambda x: word in x)
    tweetsContainSomeWord.pprint()

def main():
    ssc = StreamingContext(SparkContext(appName="PythonStreamingKafkaWordCount"), 1)
    # ssc.checkpoint('/tmp/sparkstreamingcheckpoint')  # it hates redis.publish
    zkQuorum = "localhost:2181"
    topic = "twitter_raw"
    kvs = KafkaUtils.createStream(ssc, zkQuorum, "spark-streaming-consumer", {topic: 1})
    raw_tweet = kvs.map(lambda bytes_data: pickle.loads(bytes_data[1].decode('utf-8')))  # depickle

    getWordStats(raw_tweet)
    # printTweetWithSomeWord(raw_tweet, "amp")

    ssc.start()
    ssc.awaitTermination()

if __name__ == "__main__":
    main()