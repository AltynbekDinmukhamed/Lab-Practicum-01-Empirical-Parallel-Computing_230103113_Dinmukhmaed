# Q1: False Sharing Root Cause

My CPU (Apple M1) has a cache line size of 128 bytes, not the typical 64 bytes.
This is important for Experiment A.

In Variant 1, all threads write to the same small array hit_count[]. Because
the array is small, many threads' counters fit on the same 128-byte cache
line. This is the problem: when one thread updates its counter, the MESI
protocol marks the whole cache line as "Modified" on that core and
invalidates the copy on all other cores. Then when another thread updates
its own counter (a different variable, but on the same line), its core must
reload the line first. This creates extra traffic between cores, even
though the threads are not really sharing data.

In my results, the penalty was small: naive = 0.4726 s, reduction = 0.4595 s
(~2.7% faster). I think this is because Apple M1 has a fast connection
between cores and a shared 4MB L2 cache, so cache-line invalidation is
cheap compared to other CPUs like Intel/AMD.

# Q2: SMT / Physical Core Ceiling

My M1 has no Hyperthreading (SMT). hw.logicalcpu and hw.physicalcpu are
both 8, split into 4 Performance cores and 4 Efficiency cores.

Speedup did not scale linearly at k=8. From k=1 to k=4, speedup went from
1.0x to 3.55x (almost linear). But from k=4 to k=8, speedup only grew to
4.49x, not 2x more. My guess: the first 4 threads use the fast P-cores,
but threads 5-8 must use the slower E-cores. So k=8 is not "8 equal
cores," it is 4 fast + 4 slow cores, and the fast threads must wait for
the slow ones at the barrier. This is similar to SMT contention, but the
reason is different (heterogeneous cores, not shared pipeline).

# Q3: Empirical vs Theoretical Gap

From k=2, I calculated p = 0.92.

At k=4, my empirical speedup (3.55x) was actually better than the
theoretical prediction (3.23x). At k=8, empirical speedup (4.49x) was
worse than theory (5.13x). This shows Amdahl's Law is not always a safe
upper bound in real measurements -- it only assumes perfect conditions.

Two real factors Amdahl's Law does not include:
1. Heterogeneous cores -- at k=8, four threads run on slower E-cores, so
   more threads does not mean more equal power.
2. Growing overhead -- more threads means more synchronization at the
   barrier and more OS scheduling noise. Amdahl treats (1-p) as constant,
   but in reality this overhead grows with k.

# Q4: Scheduling Trade-Off

| Schedule            | Time (s) |
|----------------------|----------|
| static (default)     | 0.4772   |
| static, 1000          | 0.3916   |
| dynamic, 100           | 0.3878   |
| dynamic, 10000        | 0.4808   |
| guided               | 0.3860   |

dynamic(100) and guided were the fastest. static (default) and
dynamic(10000) were the slowest, because their chunks are too big.
Collatz numbers have very different step counts (n=26 needs 10 steps,
n=27 needs 111 steps), so one thread can get an unlucky big chunk with
many "expensive" numbers, and other threads wait for it.

I did not find a chunk size where queue contention made things worse --
dynamic(100) was still the fastest option I tested. I think contention
would only appear with a much smaller chunk, like dynamic(10), where the
overhead of asking for new work becomes bigger than the work itself.
