Project: HelloLOOM
Vision: Build a Python command-line utility that takes one integer argument and prints whether it is prime.
Success criteria: Unit tests pass, benchmark throughput is greater than 10,000 primality checks/second, and project README is present.
Constraints: Pure Python only, no external dependencies, concise implementation.
Input/Output contract: `python helloloom.py 13` prints `prime`; `python helloloom.py 21` prints `not-prime`.
Required files: helloloom.py, test_helloloom.py, benchmark.py, README.md.
Benchmark method: Run repeated primality checks and print checks per second as a single numeric line.
