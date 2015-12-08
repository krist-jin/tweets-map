import redis
import pickle
import time
from collections import Counter, deque, defaultdict
redis = redis.StrictRedis(host='localhost', port=6379, db=0)

pubsub = redis.pubsub()
pubsub.subscribe('word_stats')
message = pubsub.listen()

# result = Counter()
# active_counters = deque()
result = defaultdict(Counter)
active_counters = defaultdict(deque)

TIME_WINDOW = 10

while True:
    pickled_stats = message.next().get('data')
    if not pickled_stats:
        continue
    try:
        stats = pickle.loads(pickled_stats)
    except TypeError, e:
        continue
    for (country_code, this_counter) in stats:
        current_time = int(time.time())
        active_counters[country_code].append((this_counter, current_time))
        result[country_code] += this_counter  # add current counter to the result
        while current_time - active_counters[country_code][0][1] > TIME_WINDOW:  # if old counter expire
            result[country_code] -= active_counters[country_code].popleft()[0]  # minus old counter
        print country_code, result[country_code].most_common(20)
    print