# Lab Practicum 01 — Empirical Parallel Computing

**Silicon Profiling, Multi-Core Scaling Limits, and Concurrency Hazards**
Zeba Academy — Instructor: Sufyan bin Uzayr

---

## Task 1 — Host Silicon Audit & Flynn's Taxonomy Mapping

| Hardware Property | Local Measured Value |
|---|---|
| CPU Model & Architecture | Apple M1 / ARM64 (AArch64) |
| Base & Max Boost Clock | Not measured / not reported |
| Physical Hardware Cores | 8 |
| Logical Cores (SMT/Threads) | 8 |
| L1 Data / Instruction Cache | L1d: 64 KB \| L1i: 128 KB |
| L2 Cache (Per Core / Total) | 4 MB |
| L3 Shared Last-Level Cache | N/A — not reported by `sysctl` |
| SIMD Vector Extensions | ARM NEON |

### Q1.1 — Flynn's Taxonomy Mapping

My Apple M1 can operate in different execution modes of Flynn's Taxonomy depending on the workload.

- **SISD** — A single CPU core executes one instruction stream on one data stream. This can occur during a single-threaded task, such as a sequential program or compiler operation.
- **SIMD** — The Apple M1 uses ARM NEON SIMD vector extensions to perform the same operation on multiple data elements simultaneously. This is useful for vector and matrix calculations and other data-parallel operations.
- **MIMD** — The Apple M1 has 8 physical cores and 8 logical threads, allowing multiple threads to execute different instruction streams on different data simultaneously. This occurs in multi-threaded applications and when the operating system schedules different tasks across multiple cores.

Therefore, the Apple M1 can use SISD for sequential workloads, SIMD for data-parallel workloads, and MIMD for multi-core and multi-threaded workloads.

---

## Task 2 — Multi-Thread Scaling Benchmark & Contention Wall

**Workload:** Prime count up to 3,000,000 (trial division)
**Language & Runtime:** Python 3 / `multiprocessing`

| Threads (N) | Run 1 (s) | Run 2 (s) | Run 3 (s) | Avg Time T_N (s) | Speedup S_N = T1/TN | Efficiency E_N = S_N/N |
|---|---|---|---|---|---|---|
| 1 (Baseline) | 19.558 | 19.481 | 19.469 | 19.503 | 1.00× | 100.0% |
| 2 | 12.652 | 12.439 | 12.404 | 12.498 | 1.56× | 78.0% |
| 4 | 6.864 | 6.844 | 6.843 | 6.850 | 2.85× | 71.2% |
| 8 | 4.473 | 4.447 | 4.451 | 4.457 | 4.38× | 54.7% |
| 16 | 3.918 | 3.965 | 3.999 | 3.960 | 4.92× | 30.8% |
| 32 | 4.055 | 4.052 | 4.019 | 4.042 | 4.83× | 15.1% |

### Q2.1 — Scaling Saturation & Hardware Contention Analysis

The speedup starts to saturate between N=8 and N=16. Between these two points, the speedup barely increases (from 4.38× to 4.92×, only about 12% more, even though the thread count doubled). At N=32, the speedup actually goes down a little, to 4.83×. This shows that adding more threads is not helping anymore — it is starting to hurt.

The main reason is the CPU's core count and design. The Apple M1 has 8 physical cores and 8 logical threads — it does **not** use Hyper-Threading/SMT like many Intel CPUs, so there are no "extra" logical threads sharing a physical core. Instead, the M1 uses a **heterogeneous** design: 4 fast Performance cores and 4 slower, power-efficient Efficiency cores. This explains the shape of the curve well. From N=1 to N=4, the workload runs only on Performance cores, so scaling is close to linear (efficiency 71–100%). From N=4 to N=8, the OS starts adding the slower Efficiency cores, which do less work per unit time, so speedup keeps growing but efficiency drops faster (54.7% at N=8). Once N goes past 8 (the true physical core count), there are no real cores left — the OS scheduler has to time-slice multiple threads onto the same 8 cores, adding context-switching overhead instead of real extra computation. This is why speedup barely moves at N=16 and drops slightly at N=32.

Another factor is cache contention. When 16 or 32 threads run at the same time, they all compete for the shared L2 cache (4 MB, per-cluster on M1). Since each thread needs its own working set for the prime-counting workload, the cache becomes too small to hold all of it, causing more cache misses and slower memory access. This adds to the slowdown seen at N=32.

Thermal throttling is a smaller factor here, but still possible — the M1 is a laptop/fanless-class chip, and running all 8 cores at 100% for the full benchmark duration could cause some clock reduction, especially in the N=16 and N=32 runs where total CPU time is highest.

---

## Task 3 — The Unsynchronized Shared Counter & Race Condition Trap

**Expected total:** 10 × 1,000,000 = 10,000,000

### Part A — Unlocked (racy), 10 runs

| Run | Measured Output | Error (10⁷ − Act) | Time (s) |
|---|---|---|---|
| 1 | 10,000,000 | 0 | 3.152 |
| 2 | 10,000,000 | 0 | 3.191 |
| 3 | 10,000,000 | 0 | 3.148 |
| 4 | 10,000,000 | 0 | 3.027 |
| 5 | 10,000,000 | 0 | 3.190 |
| 6 | 10,000,000 | 0 | 3.191 |
| 7 | 10,000,000 | 0 | 3.080 |
| 8 | 10,000,000 | 0 | 3.204 |
| 9 | 10,000,000 | 0 | 3.189 |
| 10 | 10,000,000 | 0 | 3.168 |

### Part B — Locked (synchronized)

- Measured Output = 10,000,000 (should exactly equal 10,000,000)
- Time = 10.215 s

### Summary

- Unlocked avg time = 3154.0 ms
- Locked time = 10214.6 ms
- Slowdown factor = 3.24×

### Q3.1 — Read-Modify-Write (RMW) Window

When two threads share the same variable in memory, incrementing it is not one single step. At the machine level, `counter += 1` actually needs three separate steps:

1. **Load** — the CPU core reads the current value from memory into its own register.
2. **Add** — the core adds 1 to the value inside the register.
3. **Store** — the core writes the new value back to memory.

The problem happens when two cores do this at almost the same time. For example, both cores load the same value (say, 500) into their own registers before either one has finished. Each core adds 1, so each one now has 501 in its register. Then both cores store 501 back to memory. The final value is 501, but it should be 502 — one increment is completely lost, even though both threads "ran" successfully.

This is called a race condition, because the final result depends on the exact timing of the two threads, not on the logic of the program. It is not caused by a bug in the code — it is caused by the fact that `+=` is not atomic (not a single, uninterruptible operation) at the hardware level. Without synchronization, there is no way to guarantee that one core's load-add-store sequence finishes completely before another core starts its own.

### Q3.2 — The Synchronization Penalty

Unlocked = 372.8 ms vs Locked = 1232.8 ms (slowdown ≈ 3.31×)

Synchronized code is slower because a Lock/Mutex forces threads to run one at a time when they touch the shared counter — it removes the parallelism completely for that part of the code. Every time a thread wants to increment the counter, it must first acquire the lock. If another thread already holds it, the waiting thread is blocked and has to sleep until the lock is released.

This adds real overhead in two ways:

- **Lock acquire/release cost** — even a simple lock operation takes extra CPU instructions and, in some cases, a system call, compared to a plain memory write.
- **Serialization** — instead of 10 threads doing useful work in parallel, they are forced to queue up and take turns, so the "parallel" part of the program effectively runs like a single thread again for that section.

In short, correctness has a cost: removing the race condition means giving up concurrency on the shared resource, so the program pays for safety with speed.

---

## Task 4 — Empirical Amdahl Verification vs. Gustafson Scaling Horizon

Data taken from Task 2: **T1 = 19.503 s**, **T2 = 12.498 s**

### 1. Parallel Fraction Derivation (p)

```
p = 2 × (T1 − T2) / T1
p = 2 × (19.503 − 12.498) / 19.503
p = 14.010 / 19.503
p ≈ 0.7184
```

### 2. Amdahl Theoretical Speedup Ceiling

Sequential fraction (1 − p) = 1 − 0.7184 = **0.2816**

```
Smax = 1 / (1 − p) = 1 / 0.2816 ≈ 3.55×
```

**Max Theoretical Speedup (N → ∞) ≈ 3.55×**

### 3. Amdahl 64-Core Projection

```
S64 = 1 / [(1 − p) + (p / 64)]
S64 = 1 / [0.2816 + 0.0112]
S64 = 1 / 0.2929 ≈ 3.41×
```

**Projected Speedup on 64 Cores ≈ 3.41×**

### 4. Gustafson Scaled Speedup (Weak Scaling)

```
SGustafson = (1 − p) + (p × 64)
SGustafson = 0.2816 + 45.9776 ≈ 46.26×
```

**Projected Scaled Speedup (64× Problem) ≈ 46.26×**

### Q4.1 — Strong vs. Weak Scaling Analysis

Amdahl's Law and Gustafson's Law give very different answers because they ask different questions.

Amdahl's Law keeps the problem size fixed (strong scaling). It assumes the total amount of work never changes, no matter how many cores you add. In this workload, about 28% of the time (1 − p) is spent on the sequential part, which cannot be parallelized. Even with an infinite number of cores, that 28% still has to run on one core, one step at a time. This is why the speedup hits a hard ceiling — around 3.55× — and adding more cores barely helps after a certain point, because the fixed sequential part becomes the bottleneck.

Gustafson's Law instead keeps the time fixed and lets the problem size grow (weak scaling). The idea is: if you have 64 cores, you don't run the same small problem faster — you solve a problem 64 times bigger in the same amount of time. In this case, the sequential part stays small compared to the much larger parallel part, so the speedup grows almost linearly with the number of cores (≈46×).

In short: Amdahl's Law shows that adding cores has diminishing returns for a fixed-size task, while Gustafson's Law shows that if the task also grows with the hardware, near-linear scaling is possible. Neither law is "wrong" — they just describe two different real-world use cases: making the same job finish faster (Amdahl) versus doing a bigger job in the same time (Gustafson).

# Lab Practicum 02 — Advanced Parallel Programming & Architecture 
