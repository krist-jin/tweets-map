import redis
import pickle
from collections import Counter
redis = redis.StrictRedis(host='localhost', port=6379, db=0)

pubsub = redis.pubsub()
pubsub.subscribe('word_stats')
message = pubsub.listen()
counter = Counter()

while True:
    pickled_stats = message.next().get('data')
    if not pickled_stats:
        continue
    try:
        stats = pickle.loads(pickled_stats)
    except TypeError, e:
        continue
    counter += Counter(dict(stats))  # list to dict then to Counter then add
    print counter.most_common(20)