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
        # print data_depickled
        # {  
        #    'text':'@_LulaMoore me hamas perra',
        #    'created_at':datetime.datetime(2015, 10, 9, 23, 36, 49),
        #    'source':u'Twitter Web Client',
        #    'lang:':u'es',
        #    'place':{  
        #       'country_code':u'AR',
        #       'coordinates':[  
        #          [  
        #             -68.176283,
        #             -38.984724
        #          ],
        #          [  
        #             -68.176283,
        #             -38.921051
        #          ],
        #          [  
        #             -68.015162,
        #             -38.921051
        #          ],
        #          [  
        #             -68.015162,
        #             -38.984724
        #          ]
        #       ]
        #    },
        #    'user':{  
        #       'statuses_count':15067,
        #       'name':u'Dama negra *\uffe6*',
        #       'friends_count':390,
        #       'created_at':datetime.datetime(2014, 3, 15,2,37, 10),
        #       'profile_image_url': u'http://pbs.twimg.com/profile_images/652333268256313344/x9K9Nlys_normal.jpg',
        #       'followers_count':384,
        #       'id':2390242428
        #    },
        #    'id':652628813935980544
        # }

        ### process data here ###
        text = data_depickled['text']
        # word_count = len(text.split())
        # data_depickled['word_count'] = word_count
        data_pickled = pickle.dumps(data_depickled)
        redis.publish('tweets_processed', data_pickled)

if __name__ == "__main__":
    main()