import time
from helloloom import is_prime
start=time.perf_counter()
for i in range(20000): is_prime(1000003+i%97)
print(20000/(time.perf_counter()-start))
