#!/usr/bin/python
#-*-coding:utf-8 -*-
import sys
from os import path
sys.path.append( path.dirname( path.dirname( path.dirname( path.abspath(__file__) ) ) ) )  # add src to path

from flask import Flask, render_template, Response
from flask.ext.socketio import SocketIO, emit

import os
import sys
import json
import redis
import uniout
import pickle
import time
from collections import Counter, deque, defaultdict

reload(sys)  
sys.setdefaultencoding('utf8')
STATIC_FOLDER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), './static')
application = Flask(__name__, static_folder=STATIC_FOLDER_DIR, template_folder="../d3-bubble/static/templates")
application.debug = True
redis = redis.StrictRedis(host='localhost', port=6379, db=0)
socketio = SocketIO(application)

TIME_WINDOW = 3600


@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
def index():
    # return render_template('independent.html')  # without slider
    return render_template('wrapper.html')  # with slider

@application.route('/config', methods=['GET'])
def get_init_config():
    # country_set = config.COUNTRY_SET
    country_set = set(['US', 'GB'])
    return json.dumps({"selected_countries": list(country_set)})

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
                data = pickle.loads(processed_tweet)
            except TypeError, e:
                continue
            if not isinstance(data, dict):
                continue

            if data["text"] and data["lon"] and data["lat"]:
                if keyword in data["text"]:
                    emit('data_transfer', json.dumps(data))

        except Exception, e:
            emit('die1', e, broadcast=True)
            pubsub.unsubscribe('tweets_processed')
            print e
            return

@socketio.on('word_count_and_stats_c2s')
def getWordCountAndStats(msg):
    pubsub = redis.pubsub()
    pubsub.subscribe('word_count_and_stats')
    message = pubsub.listen()
    result = defaultdict(Counter)
    active_counters = defaultdict(deque)
    
    while True:
        try:
            emitted_table = {}
            data = message.next().get('data')  # (country_code, (total_word_count, Counter))
            if not data:
                continue
            try:
                ctc = pickle.loads(data)
            except TypeError, e:
                continue
            for (country_code, (this_total_word_count, this_counter)) in ctc:
                current_time = int(time.time())
                active_counters[country_code].append((this_counter, current_time))
                result[country_code] += this_counter  # add current counter to the result
                while current_time - active_counters[country_code][0][1] > TIME_WINDOW:  # if old counter expire
                    result[country_code] -= active_counters[country_code].popleft()[0]  # minus old counter
                emitted_table[country_code] = (this_total_word_count, result[country_code].most_common(20))
            emit('word_count_and_stats_s2c', json.dumps(emitted_table))
            # print data
        except Exception, e:
            emit('die2', e, broadcast=True)
            pubsub.unsubscribe('word_count_and_stats')
            print e
            return

@socketio.on('disconnect')
def handle_realtime_disconnect():
    print('socket disconnect!')


if __name__ == '__main__':
    socketio.run(application, host='0.0.0.0', port=80)
