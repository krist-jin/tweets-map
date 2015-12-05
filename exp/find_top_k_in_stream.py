import numpy
import operator
import redis
from collections import defaultdict
 
 
# 5k is pretty safe for our test, read the paper on SpaceSaving for more info on 
# how to tune K for your use case
K = 5000
T = 20
N = 10000
numpy.random.seed(0)
myset = "top_k_in_stream"
 
r = redis.StrictRedis()
 
#clear out the data in our set, just in case
r.zremrangebyrank(myset, 0, -1)
 
hitters_script= """
local myset = ARGV[1]
local mykey = ARGV[3]
local set_length = tonumber(ARGV[2])
 
if redis.call('ZRANK', myset, mykey) then
    redis.call('ZINCRBY', myset, 1.0, mykey)
elseif redis.call('ZCARD', myset) < set_length then
    redis.call('ZADD', myset, 1.0, mykey)
else
    local value = redis.call('ZRANGE', myset,0,0, 'withscores')
    redis.call('ZREM', myset, value[1])
    redis.call('ZADD', myset, value[2] + 1.0, mykey)
end"""
 
hitters = r.register_script(hitters_script)
 
# generate some normally distributed data set for testing
# in practice, this would be some stream of values that you want
# to track (like ip addresses or user ids)
some_stream_of_data = [abs(int(x * 100)) for x in numpy.random.normal(0, .1, N)]
 
actuals = defaultdict(int)
for item in some_stream_of_data:
    #keep the actual value for comparison
    actuals[str(item)] += 1
 
    #send it to redis
    hitters(args=[myset, K, item])
 
#grab the top 20 hitters in the set
top_hitters = r.zrevrange(myset,0 ,T , withscores=True)
 
#just iterate through and see how the heavy hitters compare with actual data
for (key, value) in top_hitters:
    print key,value
    # difference = value - actuals[key]
    # print "Value %s was %s greater than the actual value of %s" % (key, difference, actuals[key])