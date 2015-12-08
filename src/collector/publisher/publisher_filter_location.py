#!/usr/bin/python
#-*-coding:utf-8 -*-

"""
The following need to be specified in './twitter_credentials.py'
CONSUMER_KEY
CONSUMER_SECRET
ACCESS_TOKEN
ACCESS_TOKEN_SECRET
"""

import tweepy
from twitter_credentials import *
from kafka import SimpleProducer, KafkaClient
import sys
import time
import cPickle as pickle
import uniout

reload(sys)
sys.setdefaultencoding("utf-8")

counter = 0

TOPIC = b'twitter_raw'
kafka = KafkaClient('localhost:9092')
producer = SimpleProducer(kafka)

class Listener(tweepy.StreamListener):
    def on_status(self, raw_tweet):  # diff between on_data and on_status: http://stackoverflow.com/questions/31054656/what-is-the-difference-between-on-data-and-on-status-in-the-tweepy-library
        if raw_tweet: # ignore blank lines
            global counter
            print counter
            counter += 1
            # time.sleep(1)
            # print raw_tweet; return False
            try:
                bytes_data = self.data_filter(raw_tweet)
                # bytes_data = pickle.dumps(raw_tweet).encode('utf-8', 'ignore')  # collect original tweets
                producer.send_messages(TOPIC, bytes_data)  # return value is the possible error message
                return True
            except Exception, e:
                print e
            

    def on_error(self, status_code):
        print 'Encountered error with status code:' + repr(status_code)
        return False  # return False in on_data to disconnect the stream

    def on_disconnect(self, notice):
        print "disconnect! " + str(notice)
        return False

    def data_filter(self, raw_tweet):
        filtered_tweet = {
            "id": raw_tweet.id,
            "text": raw_tweet.text.encode('utf-8'),
            "user": {
                "id": raw_tweet.user.id,
                # "screen_name": raw_tweet.user.screen_name,
                "name": raw_tweet.user.name,
                "profile_image_url": raw_tweet.user.profile_image_url,
                "followers_count": raw_tweet.user.followers_count,
                "friends_count": raw_tweet.user.friends_count,
                "statuses_count": raw_tweet.user.statuses_count,
                # "description": raw_tweet.user.description,
                # "lang": raw_tweet.user.lang,
                # "favourites_count": raw_tweet.user.favourites_count,
                "created_at": raw_tweet.user.created_at,  # in GMT
            },
            "lang": raw_tweet.lang,
            "created_at": raw_tweet.created_at,  # in GMT
            "place": {
                "country_code": raw_tweet.place.country_code,
                "coordinates": [raw_tweet.coordinates["coordinates"]] if raw_tweet.coordinates else raw_tweet.place.bounding_box.coordinates[0]  #[[110.48865, -6.94855]] or [[-73.338573, 41.117308], [-73.338573, 41.231989], [-73.21772, 41.231989], [-73.21772, 41.117308]]
            },
            "source": raw_tweet.source,  # android/ios/etc.
        }
        bytes_data = pickle.dumps(filtered_tweet).encode('utf-8', 'ignore')
        return bytes_data

if __name__ == '__main__':
    while True:
        for i in xrange(len(TWITTER_KEYS)):
            print "using key", str(i)
            TWITTER_KEY = TWITTER_KEYS[i]
            auth = tweepy.OAuthHandler(TWITTER_KEY["CONSUMER_KEY"], TWITTER_KEY["CONSUMER_SECRET"])
            auth.set_access_token(TWITTER_KEY["ACCESS_TOKEN"], TWITTER_KEY["ACCESS_TOKEN_SECRET"])

            try:
                streaming_api = tweepy.streaming.Stream(auth, Listener(), timeout=60)

                # Geo box that covers the entire earth to ensure we only get geo-located tweets
                # if not streaming_api.filter(locations=[ -180,-90,180,90 ]):
                streaming_api.filter(locations=[ -180,-90,180,90 ])
                print "twitter streaming ends!"
                continue
            except KeyboardInterrupt:
                print "\nBye!"
                sys.exit(0)
            except Exception, e:
                print e
                continue
        print "run out of keys! Pause for 3 mins to cool down..."
        time.sleep(180)
