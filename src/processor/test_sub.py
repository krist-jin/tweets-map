#!/usr/bin/python
#-*-coding:utf-8 -*-

import threading, logging, time
import pickle
import uniout

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer

def main():
    client = KafkaClient("localhost:9092")
    consumer = SimpleConsumer(client, "test-group", "twitter_raw")
    consumer.seek(0,2)

    for message in consumer:
        # data_deserialized = str.decode(message.message.value)
        data_depickled = pickle.loads(message.message.value.decode('utf-8'))
        # print str(data_depickled).decode('string_escape')
        print data_depickled
        # print message.offset, message.message.value

if __name__ == "__main__":
    # logging.basicConfig(
    #     format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
    #     level=logging.DEBUG
    #     )
    main()