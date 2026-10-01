#!/bin/bash
# MFS0-E3 formal matrix, one pass (logs per command in results/formal_logs/)
export PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 E3_WORKERS=3
unset E3_RES E3_PREREG
mkdir -p results/formal_logs
for c in A X L S repro report; do
  echo "=== $c start $(date '+%F %T')" >> results/formal_logs/progress.log
  python -B run_e3.py $c > results/formal_logs/$c.log 2>&1
  rc=$?
  echo "=== $c end $(date '+%F %T') rc=$rc" >> results/formal_logs/progress.log
  if [ $rc -ne 0 ] && [ "$c" != "report" ]; then echo "ABORT at $c" >> results/formal_logs/progress.log; exit $rc; fi
done
