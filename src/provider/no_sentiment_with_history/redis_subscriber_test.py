import redis
import pickle
import time
from collections import Counter, deque
redis = redis.StrictRedis(host='localhost', port=6379, db=0)

pubsub = redis.pubsub()
pubsub.subscribe('word_stats')
message = pubsub.listen()
result = Counter()
active_counters = deque()

TIME_WINDOW = 1 * 60 * 60

while True:
    pickled_stats = message.next().get('data')
    if not pickled_stats:
        continue
    try:
        stats = pickle.loads(pickled_stats)
    except TypeError, e:
        continue
    this_counter = Counter(dict(stats))
    current_time = int(time.time())
    active_counters.append((this_counter, current_time))
    result += this_counter  # add current counter to the result
    while current_time - active_counters[0][1] > TIME_WINDOW:  # if old counter expire
        result -= active_counters.popleft()[0]  # minus old counter
    print result.most_common(20)