
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <omp.h>

#define MOD 1000000007ULL
#define MAX_THREADS_CAP 256

#define CACHE_LINE 128

static inline uint32_t collatz_steps(uint64_t n) {
    uint32_t steps = 0;
    while (n > 1) {
        if ((n & 1ULL) == 0ULL) n >>= 1;
        else n = 3ULL * n + 1ULL;
        steps++;
    }
    return steps;
}

typedef struct {
    int count;
    char pad[CACHE_LINE - sizeof(int)];
} PaddedCounter;

static void run_seq(uint64_t N) {
    uint32_t max_steps = 0;
    uint64_t sum_mod = 0;
    uint64_t hits_over_100 = 0;

    double t0 = omp_get_wtime();
    for (uint64_t i = 1; i <= N; i++) {
        uint32_t s = collatz_steps(i);
        if (s > max_steps) max_steps = s;
        sum_mod = (sum_mod + s) % MOD;
        if (s > 100) hits_over_100++;
    }
    double t1 = omp_get_wtime();

    printf("[seq] N=%llu time=%.6f s max_steps=%u sum_mod=%llu hits_over_100=%llu\n",
           (unsigned long long)N, t1 - t0, max_steps,
           (unsigned long long)sum_mod, (unsigned long long)hits_over_100);
}

static void run_par(uint64_t N, int threads) {
    omp_set_num_threads(threads);
    uint32_t max_steps = 0;
    uint64_t sum_mod = 0;
    uint64_t hits_over_100 = 0;

    double t0 = omp_get_wtime();
    #pragma omp parallel for schedule(runtime) \
        reduction(max:max_steps) reduction(+:sum_mod) reduction(+:hits_over_100)
    for (uint64_t i = 1; i <= N; i++) {
        uint32_t s = collatz_steps(i);
        if (s > max_steps) max_steps = s;
        sum_mod = (sum_mod + s) % MOD;
        if (s > 100) hits_over_100++;
    }

    sum_mod %= MOD;
    double t1 = omp_get_wtime();

    printf("[par] N=%llu threads=%d time=%.6f s max_steps=%u sum_mod=%llu hits_over_100=%llu\n",
           (unsigned long long)N, threads, t1 - t0, max_steps,
           (unsigned long long)sum_mod, (unsigned long long)hits_over_100);
}

static void run_false_sharing(uint64_t N, int threads) {
    omp_set_num_threads(threads);
    static int hit_count[MAX_THREADS_CAP];
    memset(hit_count, 0, sizeof(hit_count));

    double t0 = omp_get_wtime();
    #pragma omp parallel for schedule(runtime)
    for (uint64_t i = 1; i <= N; i++) {
        uint32_t s = collatz_steps(i);
        if (s > 100) hit_count[omp_get_thread_num()]++;
    }
    double t1 = omp_get_wtime();

    long total = 0;
    for (int t = 0; t < threads; t++) total += hit_count[t];

    printf("[fs] N=%llu threads=%d time=%.6f s hits_over_100=%ld\n",
           (unsigned long long)N, threads, t1 - t0, total);
}

/* Variant 2a: OpenMP reduction (compiler avoids false sharing) */
static void run_reduction_fix(uint64_t N, int threads) {
    omp_set_num_threads(threads);
    long total_hits = 0;

    double t0 = omp_get_wtime();
    #pragma omp parallel for schedule(runtime) reduction(+:total_hits)
    for (uint64_t i = 1; i <= N; i++) {
        uint32_t s = collatz_steps(i);
        if (s > 100) total_hits++;
    }
    double t1 = omp_get_wtime();

    printf("[fsfix] N=%llu threads=%d time=%.6f s hits_over_100=%ld\n",
           (unsigned long long)N, threads, t1 - t0, total_hits);
}

/* Variant 2b: manual per-thread cache-line-padded counters */
static void run_padded_fix(uint64_t N, int threads) {
    omp_set_num_threads(threads);
    static PaddedCounter hit_count[MAX_THREADS_CAP];
    memset(hit_count, 0, sizeof(hit_count));

    double t0 = omp_get_wtime();
    #pragma omp parallel for schedule(runtime)
    for (uint64_t i = 1; i <= N; i++) {
        uint32_t s = collatz_steps(i);
        if (s > 100) hit_count[omp_get_thread_num()].count++;
    }
    double t1 = omp_get_wtime();

    long total = 0;
    for (int t = 0; t < threads; t++) total += hit_count[t].count;

    printf("[padded] N=%llu threads=%d time=%.6f s hits_over_100=%ld\n",
           (unsigned long long)N, threads, t1 - t0, total);
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr,
            "Usage: %s <N> <seq|par|fs|fsfix|padded> [threads]\n", argv[0]);
        return 1;
    }

    uint64_t N = strtoull(argv[1], NULL, 10);
    const char *mode = argv[2];
    int threads = (argc >= 4) ? atoi(argv[3]) : omp_get_max_threads();

    if (strcmp(mode, "seq") == 0) {
        run_seq(N);
    } else if (strcmp(mode, "par") == 0) {
        run_par(N, threads);
    } else if (strcmp(mode, "fs") == 0) {
        run_false_sharing(N, threads);
    } else if (strcmp(mode, "fsfix") == 0) {
        run_reduction_fix(N, threads);
    } else if (strcmp(mode, "padded") == 0) {
        run_padded_fix(N, threads);
    } else {
        fprintf(stderr, "Unknown mode: %s\n", mode);
        return 1;
    }

    return 0;
}
