# ISC26 Storage Challenge FIO Parser

This repository contains reference fio job files and a scoring parser for the ISC26 Student Cluster Competition Storage Challenge.

The parser extracts throughput, IOPS, latency, total I/O, and final score from fio JSON output files generated during the competition.

---

# Repository Contents

```text
.
├── parse_fio_score.py
├── seqwrite.fio
├── seqread.fio
└── README.md
```

---

# Storage Challenge Overview

The ISC26 Storage Challenge measures the performance of a shared storage system using industry-standard fio workloads.

Teams execute:

1. Sequential Write Benchmark
2. Sequential Read Benchmark

The final score is calculated using aggregate throughput across all participating clients.

```text
Final Score =
Aggregate Sequential Write Throughput +
Aggregate Sequential Read Throughput
```

Higher scores are better.

---

# FIO Requirements

Required fio settings:

```ini
ioengine=libaio
direct=1
```

The challenge assumes:

* Shared storage filesystem
* Multiple client nodes
* Persistent NVMe-backed storage
* POSIX-compatible filesystem

Examples:

* WEKA
* Lustre
* BeeGFS
* NFS
* SMB
* GPFS / IBM Storage Scale

---

# Example hosts.txt

One client address per line:

```text
172.31.18.70
172.31.18.71
172.31.18.72
172.31.18.73
```

Do not place host aliases or multiple fields on each line.

Correct:

```text
172.31.18.70
172.31.18.71
```

Incorrect:

```text
172.31.18.70 weka70
172.31.18.71 weka71
```

---

# Starting fio Servers

Start a fio server on each client node:

```bash
fio --server --daemonize=/tmp/fio-server.log
```

Verify:

```bash
ps -ef | grep fio
```

---

# Sequential Write Benchmark

Reference job file:

## seqwrite.fio

```ini
[global]
directory=/mnt/weka
filename_format=fiofile.$jobnum
unique_filename=1

name=seqtest
rw=write

size=50G
bs=1M

numjobs=4
iodepth=32

runtime=90
ramp_time=15
time_based=1

group_reporting=1

ioengine=libaio
direct=1

refill_buffers=1

[seqtest]
```

Run:

```bash
fio --client=hosts.txt /mnt/weka/seqwrite.fio \
  --output=seqwrite.json \
  --output-format=json+
```

---

# Sequential Read Benchmark

Reference job file:

## seqread.fio

```ini
[global]
directory=/mnt/weka
filename_format=fiofile.$jobnum
unique_filename=1

name=seqtest
rw=read

size=50G
bs=1M

numjobs=4
iodepth=32

runtime=90
ramp_time=15
time_based=1

group_reporting=1

ioengine=libaio
direct=1

[seqtest]
```

Run:

```bash
fio --client=hosts.txt /mnt/weka/seqread.fio \
  --output=seqread.json \
  --output-format=json+
```

---

# Official Score Calculation

The parser uses aggregate throughput from the fio JSON output.

For fio client/server mode, the JSON contains:

```text
client_stats[]
```

including a summary row:

```text
jobname = "All clients"
```

The parser uses this row as the authoritative aggregate result.

Do not sum the "All clients" row together with individual client rows or throughput will be double-counted.

Formula:

```text
Final Score =
Aggregate Sequential Write Throughput +
Aggregate Sequential Read Throughput
```

Example:

```text
Write = 74.55 GB/s
Read  = 159.40 GB/s

Final Score = 233.95 GB/s
```

---

# Running the Parser

## Multi-Client Results

```bash
python3 parse_fio_score.py \
  --write seqwrite.json \
  --read seqread.json
```

Example output:

```text
WRITE RESULT
----------------------------------------------------------------------
Aggregate Write Throughput: 74.55 GB/s

READ RESULT
----------------------------------------------------------------------
Aggregate Read Throughput: 159.40 GB/s

FINAL SCORE
----------------------------------------------------------------------
Final Score: 233.95 GB/s
```

---

# Optional Scaling Efficiency Analysis

The parser can also compare multi-client performance against a single-client baseline.

This metric is informational only and is not used for official scoring.

Generate single-client results:

```bash
fio /mnt/weka/seqwrite.fio \
  --output=single-seqwrite.json \
  --output-format=json+

fio /mnt/weka/seqread.fio \
  --output=single-seqread.json \
  --output-format=json+
```

Run parser:

```bash
python3 parse_fio_score.py \
  --write seqwrite.json \
  --read seqread.json \
  --single-write single-seqwrite.json \
  --single-read single-seqread.json
```

Formula:

```text
Scaling Efficiency =
Multi-Client Score /
(Single-Client Score × Number of Clients)
```

Example:

```text
Single-client score: 59.93 GB/s
Multi-client score: 233.95 GB/s
Clients: 4

Scaling factor:     3.90x
Scaling efficiency: 97.60%
```

---

# Scaling Efficiency Ratings

| Efficiency | Rating    |
| ---------- | --------- |
| ≥95%       | Excellent |
| 85–95%     | Very Good |
| 70–85%     | Good      |
| 50–70%     | Moderate  |
| <50%       | Poor      |

---

# Validation Commands

Verify storage:

```bash
mount | grep /mnt/weka
```

```bash
df -h /mnt/weka
```

Verify NVMe devices:

```bash
lsblk
```

```bash
nvme list
```

Verify fio version:

```bash
fio --version
```

---

# Notes

* Shared backend storage must be used.
* Local client block devices should not be used directly for benchmark files.
* Storage must be persistent and NVMe-backed.
* Memory-backed filesystems are prohibited.
* The parser automatically detects fio aggregate summary rows.
* The parser supports both single-client and multi-client JSON output.

Good luck at ISC26!
