# isc26-fio-parser
Python script to parse fio storage challenge for ISC26 and calculate final score 
 
Execute as follows after running your fio write and read jobs:

python3 parse_fio_score.py --write seqwrite.json --read seqread.json

Note: seqwrite.json and seqread.json are the output files from the fio run jobs.

Example fio Launch Commands

Write:

fio --client=hosts.txt /mnt/weka/seqwrite.fio \
    --output=seqwrite.json \
    --output-format=json+

Read:

fio --client=hosts.txt /mnt/weka/seqread.fio \
    --output=seqread.json \
    --output-format=json+


Sample output of parse_fio_score.py shown below:

WRITE RESULT
----------------------------------------------------------------------
Source file:              seqwrite.json

fio version:              fio-3.36

Aggregation source:       All clients row

Participating clients:    4

Bandwidth:                74.55 GB/s

Bandwidth:                69.43 GiB/s

IOPS:                     71089

Total IO:                 6717.55 GB

Runtime:                  90.11 sec

Avg completion latency:   6.99 ms

P50 completion latency:   5.91 ms

P95 completion latency:   9.52 ms

P99 completion latency:   13.38 ms

READ RESULT
----------------------------------------------------------------------
Source file:              seqread.json

fio version:              fio-3.36

Aggregation source:       All clients row

Participating clients:    4

Bandwidth:                159.40 GB/s

Bandwidth:                148.46 GiB/s

IOPS:                     152013

Total IO:                 14347.51 GB

Runtime:                  90.01 sec

Avg completion latency:   3.35 ms

P50 completion latency:   3.07 ms

P95 completion latency:   6.16 ms

P99 completion latency:   8.19 ms

FINAL SCORE
----------------------------------------------------------------------
Formula:

Final Score = Aggregate Sequential Write Throughput + Aggregate Sequential Read Throughput

Aggregate Write Throughput: 74.55 GB/s

Aggregate Read Throughput:  159.40 GB/s

Final Score:                233.95 GB/s



Note: You can run the same parser to calculate scaling efficiency if you also have singe-write and single-read json output files:


python3 parse_fio_score.py--write seqwrite.json --read seqread.json --single-write single-seqwrite.json --single-read single-seqread.json


SCALING EFFICIENCY
----------------------------------------------------------------------
Single-client write:       17.01 GB/s

Single-client read:        42.92 GB/s

Single-client score:       59.93 GB/s

Multi-client score:        233.95 GB/s

Participating clients:     4

Scaling factor:            3.90x

Scaling efficiency:        97.60%

Formula:

Scaling Efficiency = Multi-Client Score / (Single-Client Score × Client Count)

