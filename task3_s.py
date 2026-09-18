
import threading
import time

TOTAL_OPS = 2_000_000
NUM_THREADS = 4

def bench_lockless():
    ops_per_thread = TOTAL_OPS // NUM_THREADS
    local_results = [0] * NUM_THREADS

    def work(thread_id):
        local_count = 0
        for _ in range(ops_per_thread):
            local_count += 1
        local_results[thread_id] = local_count 

    threads = [threading.Thread(target=work, args=(i,)) for i in range(NUM_THREADS)]
    start = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.perf_counter() - start

    total = sum(local_results)
    return total, elapsed

if __name__ == "__main__":
    val_lockless, t_lockless = bench_lockless()
    print(f"Lockless: Value = {val_lockless:,} / {TOTAL_OPS:,} | Time: {t_lockless:.4f}s")
