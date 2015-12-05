import numpy
import heapq
from collections import defaultdict


T = 20
N = 1000000
numpy.random.seed(0)
some_stream_of_data = [abs(int(x * 100)) for x in numpy.random.normal(0, .1, N)]

heap = []

count_table = defaultdict(int)

for num in some_stream_of_data:
    count_table[num] += 1

for num, count in count_table.items():
    if len(heap) < T:
        heapq.heappush(heap, (count, num))
    else:
        if count > heap[0][0]:
            heapq.heapreplace(heap, (count, num))
# print sorted(heap, key=lambda item: -item[0])
