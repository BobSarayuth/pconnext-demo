# Performance Tests

## scgdigital-ai
```bash
scenarios: (100.00%) 1 scenario, 8 max VUs, 30m30s max duration (incl. graceful stop):
* default: 8 looping VUs for 30m0s (gracefulStop: 30s)

█ THRESHOLDS

  http_req_duration
  ✗ 'p(95)<30000' p(95)=44.54s

  success_rate
  ✓ 'rate>0.95' rate=98.52%


█ TOTAL RESULTS

  checks_total.......................: 816    0.445902/s
  checks_succeeded...................: 98.77% 806 out of 816
  checks_failed......................: 1.22%  10 out of 816

  ✗ status is 200
    ↳  98% — ✓ 402 / ✗ 6
  ✗ response has valid format
    ↳  99% — ✓ 404 / ✗ 4

  CUSTOM
  response_time...........................................................: avg=33791.073529 min=3513   med=32554  max=60001  p(90)=43195  p(95)=44542.3
  success_rate............................................................: 98.52% 402 out of 408

  HTTP
  http_req_duration.......................................................: avg=33.79s       min=3.51s  med=32.55s max=1m0s   p(90)=43.19s p(95)=44.54s
    { expected_response:true }............................................: avg=33.39s       min=3.51s  med=32.43s max=57.58s p(90)=42.86s p(95)=44.09s
  http_req_failed.........................................................: 1.47%  6 out of 408
  http_reqs...............................................................: 408    0.222951/s

  EXECUTION
  iteration_duration......................................................: avg=1m40s        min=36.78s med=1m39s  max=2m39s  p(90)=2m22s  p(95)=2m30s
  iterations..............................................................: 140    0.076503/s
  vus.....................................................................: 7      min=7          max=8
  vus_max.................................................................: 8      min=8          max=8

  NETWORK
  data_received...........................................................: 1.3 MB 706 B/s
  data_sent...............................................................: 174 kB 95 B/s

running (30m30.0s), 0/8 VUs, 140 complete and 7 interrupted iterations
default ✓ [======================================] 8 VUs  30m0s
ERRO[1830] thresholds on metrics 'http_req_duration' have been crossed
```

## chat-ui
```bash
scenarios: (100.00%) 1 scenario, 10 max VUs, 30m30s max duration (incl. graceful stop):
* default: 10 looping VUs for 30m0s (gracefulStop: 30s)

█ THRESHOLDS

  http_req_duration
  ✗ 'p(95)<30000' p(95)=1m0s

  success_rate
  ✗ 'rate>0.95' rate=94.60%


█ TOTAL RESULTS

  checks_total.......................: 816    0.445902/s
  checks_succeeded...................: 94.60% 772 out of 816
  checks_failed......................: 5.39%  44 out of 816

  ✗ status is 200
    ↳  94% — ✓ 386 / ✗ 22
  ✗ response has valid format
    ↳  94% — ✓ 386 / ✗ 22

  CUSTOM
  response_time...........................................................: avg=44259.083333 min=5324   med=43194  max=60001  p(90)=53681.8 p(95)=60000
  success_rate............................................................: 94.60% 386 out of 408

  HTTP
  http_req_duration.......................................................: avg=44.25s       min=5.32s  med=43.19s max=1m0s   p(90)=53.68s  p(95)=1m0s
    { expected_response:true }............................................: avg=43.36s       min=5.32s  med=42.45s max=59.83s p(90)=51.29s  p(95)=53.56s
  http_req_failed.........................................................: 5.39%  22 out of 408
  http_reqs...............................................................: 408    0.222951/s

  EXECUTION
  iteration_duration......................................................: avg=2m11s        min=44.24s med=2m9s   max=3m24s  p(90)=3m11s   p(95)=3m14s
  iterations..............................................................: 132    0.072131/s
  vus.....................................................................: 9      min=9          max=10
  vus_max.................................................................: 10     min=10         max=10

  NETWORK
  data_received...........................................................: 1.4 MB 763 B/s
  data_sent...............................................................: 172 kB 94 B/s


running (30m30.0s), 00/10 VUs, 132 complete and 9 interrupted iterations
default ✓ [======================================] 10 VUs  30m0s
ERRO[1830] thresholds on metrics 'http_req_duration, success_rate' have been crossed
```
