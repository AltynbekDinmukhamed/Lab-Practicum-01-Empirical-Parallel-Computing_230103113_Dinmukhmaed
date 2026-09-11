"""
Lab Practicum 01 - Task 2: Multi-Thread Scaling Benchmark
Workload: Prime counting via trial division, split across N worker processes
(using processes instead of threads sidesteps Python's GIL and gives a
genuine CPU-bound, multi-core benchmark, which is what the lab wants).

Usage:
    python task2_benchmark.py

Requires: Python 3.8+ (standard library only, no installs needed)
"""

import time
import multiprocessing as mp

# ---- Workload parameters ----
UPPER_BOUND = 3_000_000   # tune this up/down depending on your CPU speed
                           # (target: N=1 run takes roughly 5-15 seconds)
THREAD_COUNTS = [1, 2, 4, 8, 16, 32]
RUNS_PER_N = 3


def count_primes_in_range(args):
    """Count primes in [start, end) using simple trial division. CPU-bound."""
    start, end = args
    if start < 2:
        start = 2
    count = 0
    for n in range(start, end):
        if n < 2:
            continue
        is_prime = True
        i = 2
        while i * i <= n:
            if n % i == 0:
                is_prime = False
                break
            i += 1
        if is_prime:
            count += 1
    return count


def make_chunks(upper_bound, n_chunks):
    """Split [0, upper_bound) into n_chunks contiguous ranges."""
    chunk_size = upper_bound // n_chunks
    chunks = []
    start = 0
    for i in range(n_chunks):
        end = upper_bound if i == n_chunks - 1 else start + chunk_size
        chunks.append((start, end))
        start = end
    return chunks


def run_once(n_workers, upper_bound):
    """Run the workload split across n_workers processes; return wall time (s)."""
    chunks = make_chunks(upper_bound, n_workers)
    t0 = time.perf_counter()
    if n_workers == 1:
        total = count_primes_in_range(chunks[0])
    else:
        with mp.Pool(processes=n_workers) as pool:
            results = pool.map(count_primes_in_range, chunks)
        total = sum(results)
    elapsed = time.perf_counter() - t0
    return elapsed, total


def main():
    print(f"Workload: prime count up to {UPPER_BOUND:,} (trial division)")
    print(f"{'N':>4} | {'Run1(s)':>8} | {'Run2(s)':>8} | {'Run3(s)':>8} | {'Avg(s)':>8}")
    print("-" * 50)

    baseline_avg = None
    results_table = []

    for n in THREAD_COUNTS:
        times = []
        for r in range(RUNS_PER_N):
            elapsed, total = run_once(n, UPPER_BOUND)
            times.append(elapsed)
        avg = sum(times) / len(times)
        if baseline_avg is None:
            baseline_avg = avg
        speedup = baseline_avg / avg
        efficiency = speedup / n * 100

        results_table.append((n, times, avg, speedup, efficiency))
        print(f"{n:>4} | {times[0]:>8.3f} | {times[1]:>8.3f} | {times[2]:>8.3f} | {avg:>8.3f}"
              f"   Speedup={speedup:.2f}x  Eff={efficiency:.1f}%")

    print("\nCopy these numbers directly into the Task 2 table.")
    print(f"(Sanity check: prime count = {results_table[0][1] and 'see run output above'})")


if __name__ == "__main__":
    main()
