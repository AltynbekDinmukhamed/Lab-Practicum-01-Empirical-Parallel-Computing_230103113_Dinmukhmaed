"""
Lab Practicum 01 - Task 3: Unsynchronized Shared Counter & Race Condition Trap
Spawns 10 threads, each incrementing a shared global counter 1,000,000 times.
Part A: no lock (race condition -> corrupted results)
Part B: with a Lock (correct results, but slower)

Usage:
    python task3_race_condition.py

Requires: Python 3.8+ (standard library only)
"""

import sys
import threading
import time

# Force CPython's GIL to switch between threads MUCH more often than the
# default (~5ms). Without this, the GIL rarely interrupts a thread in the
# middle of "counter[0] += 1", so the race almost never shows up in practice
# even though it is theoretically possible. Setting a tiny switch interval
# makes the interleaving (and therefore the corruption) actually observable.
sys.setswitchinterval(0.0000001)

NUM_THREADS = 10
INCREMENTS_PER_THREAD = 1_000_000
EXPECTED_TOTAL = NUM_THREADS * INCREMENTS_PER_THREAD
NUM_RUNS = 10


# ---------- Part A: unsynchronized (racy) counter ----------

def worker_unsafe(counter_box):
    for _ in range(INCREMENTS_PER_THREAD):
        counter_box[0] += 1   # NOT atomic: read -> add -> write, can be interleaved


def run_unsafe_once():
    counter_box = [0]  # mutable container so threads share the same value
    threads = [threading.Thread(target=worker_unsafe, args=(counter_box,))
               for _ in range(NUM_THREADS)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    return counter_box[0], elapsed


# ---------- Part B: synchronized (locked) counter ----------

def worker_safe(counter_box, lock):
    for _ in range(INCREMENTS_PER_THREAD):
        with lock:
            counter_box[0] += 1


def run_safe_once():
    counter_box = [0]
    lock = threading.Lock()
    threads = [threading.Thread(target=worker_safe, args=(counter_box, lock))
               for _ in range(NUM_THREADS)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    return counter_box[0], elapsed


def main():
    print(f"Expected total (10 x 1,000,000) = {EXPECTED_TOTAL:,}\n")

    # --- Part A: 10 runs, no lock ---
    print("=== PART A: UNLOCKED (racy) — 10 runs ===")
    print(f"{'Run':>4} | {'Measured Output':>16} | {'Error (10^7 - Act)':>20} | {'Time (s)':>9}")
    print("-" * 60)
    unsafe_times = []
    for run_idx in range(1, NUM_RUNS + 1):
        result, elapsed = run_unsafe_once()
        error = EXPECTED_TOTAL - result
        unsafe_times.append(elapsed)
        print(f"{run_idx:>4} | {result:>16,} | {error:>20,} | {elapsed:>9.3f}")

    avg_unsafe_time = sum(unsafe_times) / len(unsafe_times)

    # --- Part B: 1 run (or a few), with lock, to compare timing ---
    print("\n=== PART B: LOCKED (synchronized) ===")
    result_safe, elapsed_safe = run_safe_once()
    print(f"Measured Output = {result_safe:,}  (should exactly equal {EXPECTED_TOTAL:,})")
    print(f"Time = {elapsed_safe:.3f} s")

    print("\n=== SUMMARY FOR Q3.2 ===")
    print(f"Unlocked avg time = {avg_unsafe_time * 1000:.1f} ms")
    print(f"Locked   time     = {elapsed_safe * 1000:.1f} ms")
    print(f"Slowdown factor   = {elapsed_safe / avg_unsafe_time:.2f}x")


if __name__ == "__main__":
    main()
