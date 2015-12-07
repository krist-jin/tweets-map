from sys      import argv, exit
from operator import add, sub
import cPickle as pickle
import logging

from pyspark           import SparkContext
from pyspark.streaming import StreamingContext

import redis
redis = redis.StrictRedis(host='localhost', port=6379, db=0)

logging.basicConfig(filename="test.log",
                    level=logging.INFO, format='%(asctime)s --- %(message)s')

def publishToRedis(wordStats):
    stats = wordStats.collect()
    # logging.info(type(stats))
    if stats:
        pickled_stats = pickle.dumps(stats)
        redis.publish("word_stats", pickled_stats)

if __name__ == "__main__":
    if len(argv) != 3:
        print "Please pass host and port number as arguments."
        exit(-1)
    sc = SparkContext()
    ssc = StreamingContext(sc, 1)
    # ssc.checkpoint('/tmp/sparkstreamingcheckpoint')

    lines = ssc.socketTextStream(argv[1], int(argv[2]))
    sums = lines.map( lambda c: (c, 1) ).reduceByKey(add)
      # .reduceByKeyAndWindow(add, sub, 30, 5)
    sums.foreachRDD(publishToRedis)  # publish to redis
    sums.pprint()

    ssc.start()
    ssc.awaitTermination()