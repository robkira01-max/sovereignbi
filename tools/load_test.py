#!/usr/bin/env python3
"""19 — Test de charge MizanBI : simule N visiteurs simultanés.

Usage:
    python tools/load_test.py --url http://localhost:9001 --users 10 --duration 30
"""
import argparse
import statistics
import threading
import time
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Result:
    ok: int = 0
    err: int = 0
    latencies: list[float] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, ok: bool, latency: float) -> None:
        with self.lock:
            if ok:
                self.ok += 1
            else:
                self.err += 1
            self.latencies.append(latency)


def _worker(base_url: str, api_key: str, result: Result, stop_event: threading.Event) -> None:
    endpoints = ["/health", "/ready", "/cache/stats"]
    headers = {"X-Api-Key": api_key}
    idx = 0
    while not stop_event.is_set():
        url = base_url + endpoints[idx % len(endpoints)]
        idx += 1
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                ok = resp.status < 500
        except Exception:
            ok = False
        result.record(ok, time.perf_counter() - t0)
        time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:9001")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--api-key", default="viewer")
    args = parser.parse_args()

    result = Result()
    stop = threading.Event()
    threads = [threading.Thread(target=_worker, args=(args.url, args.api_key, result, stop), daemon=True)
               for _ in range(args.users)]

    print(f"[load_test] {args.users} utilisateurs × {args.duration}s sur {args.url}")
    for t in threads:
        t.start()
    time.sleep(args.duration)
    stop.set()
    for t in threads:
        t.join(timeout=2)

    lat = result.latencies
    total = result.ok + result.err
    rps = total / args.duration if args.duration else 0
    print(f"\n[load_test] {total} requêtes — {result.ok} OK / {result.err} erreurs — {rps:.1f} req/s")
    if lat:
        print(f"  p50={statistics.median(lat)*1000:.0f}ms  p95={sorted(lat)[int(len(lat)*0.95)]*1000:.0f}ms  max={max(lat)*1000:.0f}ms")


if __name__ == "__main__":
    main()
