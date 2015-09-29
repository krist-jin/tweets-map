#!/usr/bin/python
#-*-coding:utf-8 -*-

from flask import Flask, render_template, Response
from flask.ext.socketio import SocketIO, emit

import sys
import json
import redis
import uniout
import pickle

reload(sys)  
sys.setdefaultencoding('utf8')
application = Flask(__name__)
application.debug = True
redis = redis.StrictRedis(host='localhost', port=6379, db=0)
socketio = SocketIO(application)

@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
def index():
    return render_template('map.html')

@application.route('/test', methods=['GET'])
def test():
    pubsub = redis.pubsub()
    pubsub.subscribe('tweets_processed')
    tweets = pubsub.listen()
    num=0
    while True:
        print "test:",num
        num+=1
        message = tweets.next()
        processed_tweet = message.get('data')
        if not processed_tweet:
            continue
        try:
            processed_tweet_dict = pickle.loads(processed_tweet)
        except TypeError, e:
            continue
        if not isinstance(processed_tweet_dict, dict):
            continue
        # print processed_tweet_dict['id']
        data_filter(processed_tweet_dict)

@socketio.on('keyword')
def handle_realtime_connect(keyword):
    print('received keyword: ' + keyword)
    # emit('data_transfer', "json.dumps(data)", broadcast=True)
    pubsub = redis.pubsub()
    pubsub.subscribe('tweets_processed')
    tweets = pubsub.listen()
    while True:
        try:
            message = tweets.next()

            processed_tweet = message.get('data')
            if not processed_tweet:
                continue
            try:
                processed_tweet_dict = pickle.loads(processed_tweet)
            except TypeError, e:
                continue
            if not isinstance(processed_tweet_dict, dict):
                continue
            try:
                data = data_filter(processed_tweet_dict)
            except Exception, e:
                continue

            if data["text"] and data["lon"] and data["lat"]:
                if keyword in data["text"]:
                    emit('data_transfer', json.dumps(data))

        except Exception, e:
            emit('die', e, broadcast=True)
            pubsub.unsubscribe('tweets_processed')
            print e
            return

def data_filter(tweet):
    raw_coordinates = tweet.get('place').get('coordinates')
    if len(raw_coordinates)==1:
        coordinates = raw_coordinates[0]
        lon,lat = coordinates[0],coordinates[1]
    elif len(raw_coordinates)==4:
        left_down,up_right = raw_coordinates[0],raw_coordinates[2]
        lon,lat = (left_down[0]+up_right[0])/2.0,(left_down[1]+up_right[1])/2.0
    else:
        raise Exception("Coordinates format error")
    data = {
        "text": tweet.get('text'),
        "lon": lon,
        "lat": lat
    }
    # print data
    return data

@socketio.on('disconnect')
def handle_realtime_disconnect():
    print('socket disconnect!')


if __name__ == '__main__':
    socketio.run(application, host='0.0.0.0', port=80)
