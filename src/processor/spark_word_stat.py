#!/usr/bin/python
#-*-coding:utf-8 -*-

import sys
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )  # add src to path
import config.processor_config as config

from utils.priority_dict import PriorityDict
import threading, logging, time
import pickle
import uniout
import redis
import re
from operator import add, sub
from collections import Counter

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

import nltk
from nltk.tag.perceptron import PerceptronTagger

import pycountry

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
        redis.publish("word_count_and_stats", pickled_stats)

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
    # wordStats = nouns.countByValueAndWindow(60, 5)  # does not work because of bugs in PySpark?
    # wordStats = nouns.map(lambda noun: (noun, 1)).reduceByKeyAndWindow(add, sub, WINDOW_WIDTH, UPDATE_INTERVAL)  # does not work because it needs checkpoint, but checkpoint hates redis.publish
    wordStats.foreachRDD(publishToRedis)  # publish to redis
    wordStats.pprint()

def getCountryStats(raw_tweet):
    def getCountryName(x):
        # return (x['place']['country_code'], 1)
        try:
            country_code = x['place']['country_code']
            return (pycountry.countries.get(alpha2=country_code).name, 1)
        except Exception, e:
            return ("unknown", 1)

    countryStats = raw_tweet.filter(lambda x: x['lang']=='en')  \
                            .map(lambda x: getCountryName(x))  \
                            .reduceByKey(add)
    countryStats.foreachRDD(publishToRedis)  # publish to redis
    countryStats.pprint()

def mapFunction(raw_tweet):  # from raw_tweet to counter
    country_code = raw_tweet['place']['country_code']
    words = re.compile('\w+').findall(raw_tweet['text'].decode('utf-8'))
    lower_words = [word.lower() for word in words]
    word_tag_pairs = nltk.tag._pos_tag(lower_words, 'universal', tagger)
    filtered_words = [word_tag[0] for word_tag in word_tag_pairs if wordFilter(word_tag)]
    this_counter = Counter(filtered_words)
    total_word_count = len(words)
    return (country_code, (total_word_count, this_counter))

def getWordStatsByCountry(raw_tweet, countries):
    countries_counter = (
        raw_tweet.filter(lambda x: x['lang']=='en' and x['place']['country_code'] in countries)  # keep only English and selected countries
                 .map(mapFunction)  # get counter for each country
                 .reduceByKey(lambda x,y: (x[0]+y[0], x[1]+y[1]))  # combine counters with same key
    )
    countries_counter.foreachRDD(publishToRedis)  # publish to redis
    countries_counter.pprint()


def printTweetWithSomeWord(raw_tweet, word):
    eng_data = raw_tweet.filter(lambda x: x['lang']=='en')  # keep only english
    eng_lines = eng_data.map(lambda x: (x['id'], x['text'].decode('utf-8')))  # fetch the text
    words_lists = eng_lines.map(lambda line: ("https://twitter.com/statuses/"+str(line[0]), re.compile('\w+').findall(line[1])))  # only extract words (naive tokenizer)
    tweetsContainSomeWord = words_lists.filter(lambda x: word in x[1])
    tweetsContainSomeWord.pprint()

def main():
    ssc = StreamingContext(SparkContext(appName="PythonStreamingKafkaWordCount"), 1)
    # ssc.checkpoint('/tmp/sparkstreamingcheckpoint')  # it hates redis.publish
    zkQuorum = "localhost:2181"
    topic = "twitter_raw"
    kvs = KafkaUtils.createStream(ssc, zkQuorum, "spark-streaming-consumer", {topic: 1})
    raw_tweet = kvs.map(lambda bytes_data: pickle.loads(bytes_data[1].decode('utf-8')))  # depickle

    # getWordStats(raw_tweet)
    # printTweetWithSomeWord(raw_tweet, "job")
    # getCountryStats(raw_tweet)
    getWordStatsByCountry(raw_tweet, config.COUNTRY_SET)

    ssc.start()
    ssc.awaitTermination()

if __name__ == "__main__":
    main()