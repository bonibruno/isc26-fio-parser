#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def bytes_to_gb(value: float) -> float:
    return value / 1_000_000_000


def bytes_to_gib(value: float) -> float:
    return value / (1024 ** 3)


def ns_to_ms(value: float) -> float:
    return value / 1_000_000


def get_stats_entries(fio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "client_stats" in fio_data:
        return fio_data["client_stats"]
    if "jobs" in fio_data:
        return fio_data["jobs"]
    return []


def find_all_clients_row(entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for entry in entries:
        if entry.get("jobname") == "All clients":
            return entry
    return None


def get_operation_data(entry: Dict[str, Any], op: str) -> Dict[str, Any]:
    return entry.get(op, {}) or {}


def has_real_io(entry: Dict[str, Any], op: str) -> bool:
    return get_operation_data(entry, op).get("io_bytes", 0) > 0


def weighted_latency_ms(entries: List[Dict[str, Any]], op: str, field: str) -> float:
    total_ios = 0.0
    weighted_sum = 0.0

    for entry in entries:
        data = get_operation_data(entry, op)
        ios = float(data.get("total_ios", 0))
        if ios <= 0:
            continue

        if field == "mean":
            value_ns = float(data.get("clat_ns", {}).get("mean", 0))
        else:
            value_ns = float(data.get("clat_ns", {}).get("percentile", {}).get(field, 0))

        weighted_sum += value_ns * ios
        total_ios += ios

    if total_ios == 0:
        return 0.0

    return ns_to_ms(weighted_sum / total_ios)


def extract_fio_metrics(path: Path, op: str) -> Dict[str, Any]:
    fio_data = load_json(path)
    entries = get_stats_entries(fio_data)

    if not entries:
        raise ValueError(f"No fio jobs or client_stats found in {path}")

    all_clients = find_all_clients_row(entries)

    if all_clients and has_real_io(all_clients, op):
        aggregate_entry = all_clients
        real_client_entries = [
            e for e in entries
            if e.get("jobname") != "All clients" and has_real_io(e, op)
        ]
        aggregation_source = "All clients row"
    else:
        real_client_entries = [e for e in entries if has_real_io(e, op)]
        aggregate_entry = None
        aggregation_source = "Summed client rows"

    if aggregate_entry:
        op_data = get_operation_data(aggregate_entry, op)
        bw_bytes = float(op_data.get("bw_bytes", 0))
        io_bytes = float(op_data.get("io_bytes", 0))
        iops = float(op_data.get("iops", 0))
        runtime_ms = float(op_data.get("runtime", 0))

        latency_entries = real_client_entries if real_client_entries else [aggregate_entry]
    else:
        bw_bytes = sum(float(get_operation_data(e, op).get("bw_bytes", 0)) for e in real_client_entries)
        io_bytes = sum(float(get_operation_data(e, op).get("io_bytes", 0)) for e in real_client_entries)
        iops = sum(float(get_operation_data(e, op).get("iops", 0)) for e in real_client_entries)
        runtime_ms = max((float(get_operation_data(e, op).get("runtime", 0)) for e in real_client_entries), default=0)
        latency_entries = real_client_entries

    return {
        "source_file": str(path),
        "fio_version": fio_data.get("fio version", "unknown"),
        "operation": op,
        "aggregation_source": aggregation_source,
        "client_count": len(real_client_entries) if real_client_entries else 1,
        "bw_bytes_per_sec": bw_bytes,
        "bw_GBps": bytes_to_gb(bw_bytes),
        "bw_GiBps": bytes_to_gib(bw_bytes),
        "iops": iops,
        "io_GB": bytes_to_gb(io_bytes),
        "runtime_sec": runtime_ms / 1000,
        "avg_clat_ms": weighted_latency_ms(latency_entries, op, "mean"),
        "p50_clat_ms": weighted_latency_ms(latency_entries, op, "50.000000"),
        "p95_clat_ms": weighted_latency_ms(latency_entries, op, "95.000000"),
        "p99_clat_ms": weighted_latency_ms(latency_entries, op, "99.000000"),
    }


def print_metrics(title: str, m: Dict[str, Any]) -> None:
    print(f"\n{title}")
    print("-" * 70)
    print(f"Source file:              {m['source_file']}")
    print(f"fio version:              {m['fio_version']}")
    print(f"Aggregation source:       {m['aggregation_source']}")
    print(f"Participating clients:    {m['client_count']}")
    print(f"Bandwidth:                {m['bw_GBps']:.2f} GB/s")
    print(f"Bandwidth:                {m['bw_GiBps']:.2f} GiB/s")
    print(f"IOPS:                     {m['iops']:.0f}")
    print(f"Total IO:                 {m['io_GB']:.2f} GB")
    print(f"Runtime:                  {m['runtime_sec']:.2f} sec")
    print(f"Avg completion latency:   {m['avg_clat_ms']:.2f} ms")
    print(f"P50 completion latency:   {m['p50_clat_ms']:.2f} ms")
    print(f"P95 completion latency:   {m['p95_clat_ms']:.2f} ms")
    print(f"P99 completion latency:   {m['p99_clat_ms']:.2f} ms")


def scaling_efficiency(single_score: float, multi_score: float, client_count: int) -> Optional[float]:
    if single_score <= 0 or client_count <= 0:
        return None
    return multi_score / (single_score * client_count)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse fio JSON results and calculate ISC Storage Challenge score."
    )

    parser.add_argument("--write", required=True, help="Multi-client or single-client seqwrite.json")
    parser.add_argument("--read", required=True, help="Multi-client or single-client seqread.json")

    parser.add_argument("--single-write", help="Optional single-client seqwrite.json baseline")
    parser.add_argument("--single-read", help="Optional single-client seqread.json baseline")

    args = parser.parse_args()

    write = extract_fio_metrics(Path(args.write), "write")
    read = extract_fio_metrics(Path(args.read), "read")

    final_score = write["bw_GBps"] + read["bw_GBps"]

    print_metrics("WRITE RESULT", write)
    print_metrics("READ RESULT", read)

    print("\nFINAL SCORE")
    print("-" * 70)
    print("Formula:")
    print("Final Score = Aggregate Sequential Write Throughput + Aggregate Sequential Read Throughput")
    print()
    print(f"Aggregate Write Throughput: {write['bw_GBps']:.2f} GB/s")
    print(f"Aggregate Read Throughput:  {read['bw_GBps']:.2f} GB/s")
    print(f"Final Score:                {final_score:.2f} GB/s")

    if args.single_write and args.single_read:
        single_write = extract_fio_metrics(Path(args.single_write), "write")
        single_read = extract_fio_metrics(Path(args.single_read), "read")

        single_score = single_write["bw_GBps"] + single_read["bw_GBps"]
        client_count = max(write["client_count"], read["client_count"])
        eff = scaling_efficiency(single_score, final_score, client_count)

        print("\nSCALING EFFICIENCY")
        print("-" * 70)
        print(f"Single-client write:       {single_write['bw_GBps']:.2f} GB/s")
        print(f"Single-client read:        {single_read['bw_GBps']:.2f} GB/s")
        print(f"Single-client score:       {single_score:.2f} GB/s")
        print(f"Multi-client score:        {final_score:.2f} GB/s")
        print(f"Participating clients:     {client_count}")

        if eff is not None:
            print(f"Scaling factor:            {final_score / single_score:.2f}x")
            print(f"Scaling efficiency:        {eff * 100:.2f}%")
        else:
            print("Scaling efficiency:        unavailable")

        print()
        print("Formula:")
        print("Scaling Efficiency = Multi-Client Score / (Single-Client Score × Client Count)")


if __name__ == "__main__":
    main()
