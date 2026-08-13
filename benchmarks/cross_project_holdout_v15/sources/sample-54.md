sysbench 1.0.20 (using system LuaJIT 2.1.0-beta3)

Running the test with following options:
Number of threads: 1
Initializing random number generator from current time


Extra file open flags: (none)
128 files, 8MiB each
1GiB total file size
Block size 16KiB
Number of IO requests: 0
Read/Write ratio for combined random IO test: 1.50
Periodic FSYNC enabled, calling fsync() each 100 requests.
Calling fsync() at the end of test, Enabled.
Using synchronous I/O mode
Doing random r/w test
Initializing worker threads...

Threads started!


File operations:
    reads/s:                      447.81
    writes/s:                     298.54
    fsyncs/s:                     958.51

Throughput:
    read, MiB/s:                  7.00
    written, MiB/s:               4.66

General statistics:
    total time:                          30.1454s
    total number of events:              51268

Latency (ms):
         min:                                    0.00
         avg:                                    0.58
         max:                                   70.02
         95th percentile:                        1.64
         sum:                                29915.68

Threads fairness:
    events (avg/stddev):           51268.0000/0.00
    execution time (avg/stddev):   29.9157/0.00

