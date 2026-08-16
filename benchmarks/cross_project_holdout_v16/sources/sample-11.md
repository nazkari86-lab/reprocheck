# API-013 — Owner-scoped route latency benchmark

Acceptance budget (API-013): **list/detail p95 ≤ 300 ms**, **mutations p95 ≤ 500 ms** at the
documented production-like test size.

Harness: [`scripts/bench-owner-scoped-routes.ts`](../scripts/bench-owner-scoped-routes.ts),
run with `npm run bench:routes`.

---

## How to run it

```bash
# 1. Create a DEDICATED throwaway database. The harness refuses to run against
#    anything whose database name does not contain "bench".
psql -c 'CREATE DATABASE job_tracker_bench;'

# 2. Migrate it.
DATABASE_URL=postgresql://user:pw@localhost:5432/job_tracker_bench npx drizzle-kit migrate

# 3. Seed + measure.
BENCH_DATABASE_URL=postgresql://user:pw@localhost:5432/job_tracker_bench \
  npm run bench:routes -- --out /tmp/bench.md
```

Flags: `--out <path>`, `--no-seed`, `--samples <n>` (default 200 for reads; mutations use
`n/2`), `--warmup <n>` (default 25, discarded).

Exit code is `0` when every operation is inside its budget and `2` when any p95 breaches,
so the harness can gate a pipeline.

### Safety guards

The script seeds by `TRUNCATE … RESTART IDENTITY CASCADE`, so it refuses to start unless
**all** of the following hold:

1. `BENCH_DATABASE_URL` is set explicitly — it never falls back to `DATABASE_URL`.
2. That URL's database name matches `/bench/i`.
3. It differs from `DATABASE_URL`, so the app database can never be the target.
4. `NODE_ENV !== 'production'`.

No credentials are read from or written to the repository; the connection string is
supplied by the operator's environment for the duration of the run.

## What is measured

The harness imports and calls the **real route handlers** — no HTTP server and no mocks
below the auth boundary. `resolveRequestUser` → `requireUser` → `resolveUser` → `withUser`
all execute, including the per-request `set_config('app.user_id', …)` that arms RLS, so
each sample covers auth resolution, owner resolution, the transaction, and the queries.

It does **not** include Next.js HTTP/serialization overhead or network RTT. Those are
roughly constant per request and were not the risk this criterion was written for (the
risk was an owner predicate degrading into a full scan of a shared table); the measured
headroom below is large enough that the excluded overhead cannot move the verdict.

Identity comes from the local-only `AUTH_DEV_ALLOW_SAME_ORIGIN` same-origin dev path in
`src/lib/auth.ts`, which is hard-disabled when `NODE_ENV=production`. Requests are driven
as **bench user 1**, the user with the largest tracker — the worst case.

## Dataset

The seeded shape deliberately makes the owner predicate do real work: the shared catalog
is an order of magnitude larger than any single user's tracker, and three users overlap on
it, so a missing or wrong owner predicate would show up as both wrong rows and a worse plan.

| table | rows |
| --- | ---: |
| `users` | 3 |
| `companies` | 400 |
| `jobs` | 5,000 (all active) |
| `user_job_state` | 2,200 total — 1,200 / 800 / 200 per user |
| ↳ of which `is_hidden` | 600 |
| `job_skills` | 15,000 (3 skills per job) |
| `user_job_contacts` | 500 (user 1) |
| `user_job_status_history` | 2,000 (user 1) |

---

## Results — 2026-08-05

Executed against PostgreSQL 18 (`postgres:18-alpine`, the workspace `docker-compose.yml`
`postgres-db` service) on a scratch `job_tracker_bench` database on the same server. The
application database was never touched.

| operation | n | p50 (ms) | p95 (ms) | p99 (ms) | budget p95 | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| `GET /api/jobs?scope=tracked` | 200 | 15.9 | 18.5 | 20.2 | 300 ms | PASS |
| `GET /api/jobs?scope=catalog` | 200 | 16.0 | 21.5 | 24.0 | 300 ms | PASS |
| `GET /api/jobs?scope=hidden` | 200 | 15.9 | 19.8 | 21.6 | 300 ms | PASS |
| `GET /api/jobs?scope=tracked&stage=applied&sort_by=priority` | 200 | 15.2 | 17.7 | 20.2 | 300 ms | PASS |
| `GET /api/jobs/[id]` | 200 | 15.9 | 21.0 | 24.6 | 300 ms | PASS |
| `PATCH /api/jobs/[id]/state` | 100 | 10.9 | 19.0 | 25.5 | 500 ms | PASS |
| `PATCH /api/jobs/[id]/state` (stage change → history row) | 100 | 11.6 | 15.4 | 16.2 | 500 ms | PASS |
| `GET /api/jobs/[id]/contacts` | 200 | 7.1 | 9.7 | 11.1 | 300 ms | PASS |
| `POST /api/jobs/[id]/contacts` | 100 | 12.2 | 14.3 | 15.2 | 500 ms | PASS |
| `PATCH /api/jobs/[id]/contacts/[contactId]` | 100 | 8.7 | 10.5 | 11.0 | 500 ms | PASS |
| `DELETE /api/jobs/[id]/contacts/[contactId]` | 100 | 6.7 | 10.5 | 11.2 | 500 ms | PASS |

**Every operation is inside budget with >14× headroom on reads and >25× on mutations.**

---

## Query plans — `EXPLAIN (ANALYZE, BUFFERS)`

### `GET /api/jobs?scope=tracked` — owner inner join

```
Limit  (cost=334.18..334.25 rows=25 width=14) (actual time=0.848..0.851 rows=25.00 loops=1)
  Buffers: shared hit=208
  ->  Sort  (cost=334.18..336.37 rows=873 width=14) (actual time=0.847..0.849 rows=25.00 loops=1)
        Sort Key: j.date_found DESC NULLS LAST, j.id DESC
        Sort Method: top-N heapsort  Memory: 26kB
        Buffers: shared hit=208
        ->  Hash Join  (cost=67.41..309.55 rows=873 width=14) (actual time=0.177..0.803 rows=600.00 loops=1)
              Hash Cond: (j.id = s.job_id)
              Buffers: shared hit=208
              ->  Seq Scan on jobs j  (cost=0.00..229.00 rows=5000 width=12) (actual time=0.008..0.438 rows=5000.00 loops=1)
                    Filter: (is_active AND (deleted_at IS NULL))
                    Buffers: shared hit=179
              ->  Hash  (cost=56.50..56.50 rows=873 width=10) (actual time=0.159..0.159 rows=600.00 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 34kB
                    Buffers: shared hit=29
                    ->  Seq Scan on user_job_state s  (cost=0.00..56.50 rows=873 width=10) (actual time=0.012..0.104 rows=600.00 loops=1)
                          Filter: ((NOT is_hidden) AND (user_id = 1))
                          Rows Removed by Filter: 1600
                          Buffers: shared hit=29
Planning Time: 0.324 ms
Execution Time: 0.890 ms
```

### `GET /api/jobs?scope=tracked&stage=applied` — `user_job_state_user_stage_idx`

```
Limit  (cost=283.63..283.69 rows=25 width=6) (actual time=0.696..0.699 rows=25.00 loops=1)
  Buffers: shared hit=197
  ->  Sort  (cost=283.63..283.90 rows=109 width=6) (actual time=0.695..0.697 rows=25.00 loops=1)
        Sort Key: s.priority DESC NULLS LAST, j.id DESC
        Sort Method: top-N heapsort  Memory: 26kB
        ->  Hash Join  (cost=38.42..280.56 rows=109 width=6) (actual time=0.086..0.679 rows=138.00 loops=1)
              Hash Cond: (j.id = s.job_id)
              ->  Seq Scan on jobs j  (cost=0.00..229.00 rows=5000 width=4) (actual time=0.010..0.454 rows=5000.00 loops=1)
                    Filter: (is_active AND (deleted_at IS NULL))
              ->  Hash  (cost=37.06..37.06 rows=109 width=6) (actual time=0.061..0.062 rows=138.00 loops=1)
                    ->  Bitmap Heap Scan on user_job_state s  (cost=5.81..37.06 rows=109 width=6) (actual time=0.025..0.048 rows=138.00 loops=1)
                          Recheck Cond: ((user_id = 1) AND (interview_stage = 'applied'::interview_stage_enum))
                          Filter: (NOT is_hidden)
                          Heap Blocks: exact=16
                          ->  Bitmap Index Scan on user_job_state_user_stage_idx  (cost=0.00..5.78 rows=150 width=0) (actual time=0.017..0.017 rows=175.00 loops=1)
                                Index Cond: ((user_id = 1) AND (interview_stage = 'applied'::interview_stage_enum))
                                Buffers: shared hit=2
Planning Time: 0.329 ms
Execution Time: 0.747 ms
```

### `GET /api/jobs/[id]` — owner state lookup

```
Limit  (cost=0.28..8.30 rows=1 width=30) (actual time=0.023..0.024 rows=1.00 loops=1)
  ->  Index Scan using user_job_state_job_id_idx on user_job_state  (cost=0.28..8.30 rows=1 width=30) (actual time=0.022..0.023 rows=1.00 loops=1)
        Index Cond: (job_id = 3)
        Filter: (user_id = 1)
        Buffers: shared hit=3
Planning Time: 0.094 ms
Execution Time: 0.062 ms
```

### `GET /api/jobs/[id]` — owner contacts lookup

```
Sort  (cost=8.30..8.31 rows=1 width=61) (actual time=0.041..0.041 rows=1.00 loops=1)
  Sort Key: created_at
  ->  Index Scan using user_job_contacts_job_id_idx on user_job_contacts  (cost=0.28..8.29 rows=1 width=61) (actual time=0.023..0.033 rows=1.00 loops=1)
        Index Cond: (job_id = 3)
        Filter: (user_id = 1)
        Buffers: shared hit=6
Planning Time: 0.082 ms
Execution Time: 0.082 ms
```

---

## Honest reading of the plans

The acceptance criterion asks that "query plans use owner-first indexes". What the plans
actually show, at this dataset size:

- **Owner-first indexes are used where they are selective.** With a personal filter
  (`stage=applied`), the planner picks `user_job_state_user_stage_idx` with
  `Index Cond: (user_id = 1 AND interview_stage = …)` — exactly the owner-first access
  path the composite indexes were added for.
- **The unfiltered `scope=tracked` list uses a seq scan + hash join, not the composite
  PK.** This is a *correct* planner choice, not a missing index: at 2,200 `user_job_state`
  rows the whole relation is 29 shared buffers, and 600 of them qualify, so an index scan
  would cost more than reading the table. The owner predicate is still applied
  (`Filter: ((NOT is_hidden) AND (user_id = 1))`) and the result is correct; only the
  access method differs. Re-measure at ≥10× this size before concluding anything about
  index usage on the unfiltered path.
- **Single-row detail lookups resolve through `user_job_state_job_id_idx`** with `user_id`
  as a recheck filter, rather than through the `(user_id, job_id)` primary key. Also a
  cost decision — `job_id` alone already narrows to ≤3 rows (one per user). Correctness is
  unaffected because the owner predicate is still evaluated, and both RLS and the explicit
  application predicate remain in force.
- **Every plan reads from `shared hit`** — the working set is fully cached, so these
  numbers are a lower bound. A cold-cache or larger-than-RAM dataset would be slower; the
  headroom (>14×) is wide enough that this does not put the budget at risk, but a
  production-scale re-measure is the honest way to confirm it.

## Follow-ups (not blocking API-013)

- Re-run at 50k–100k catalog jobs to confirm the planner switches the unfiltered
  `scope=tracked` path onto the owner-first index rather than degrading.
- Measure through the HTTP layer (a running `next start`) if end-to-end wall-clock —
  rather than handler time — ever becomes the budget of record.
- Cold-cache variant (`pg_prewarm` off / restarted server) for a pessimistic bound.
