"""Métriques Prometheus — collecteur léger sans dépendance obligatoire."""
from __future__ import annotations

import time
from threading import Lock
from typing import Any


class Counter:
    def __init__(self, name: str, help: str, labels: list[str] = []) -> None:
        self.name = name
        self.help = help
        self.labels = labels
        self._values: dict[tuple, float] = {}
        self._lock = Lock()

    def inc(self, value: float = 1.0, **label_values) -> None:
        key = tuple(label_values.get(l, "") for l in self.labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def get(self, **label_values) -> float:
        key = tuple(label_values.get(l, "") for l in self.labels)
        return self._values.get(key, 0.0)

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        for key, val in self._values.items():
            label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, key))
            suffix = "{" + label_str + "}" if label_str else ""
            lines.append(f"{self.name}{suffix} {val}")
        return "\n".join(lines)


class Gauge:
    def __init__(self, name: str, help: str) -> None:
        self.name = name
        self.help = help
        self._value: float = 0.0
        self._lock = Lock()

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def get(self) -> float:
        return self._value

    def render(self) -> str:
        return (
            f"# HELP {self.name} {self.help}\n"
            f"# TYPE {self.name} gauge\n"
            f"{self.name} {self._value}"
        )


class Histogram:
    BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(self, name: str, help: str) -> None:
        self.name = name
        self.help = help
        self._sum = 0.0
        self._count = 0
        self._buckets: dict[float, int] = {b: 0 for b in self.BUCKETS}
        self._lock = Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._count += 1
            for b in self.BUCKETS:
                if value <= b:
                    self._buckets[b] += 1

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} histogram"]
        for b, count in self._buckets.items():
            lines.append(f'{self.name}_bucket{{le="{b}"}} {count}')
        lines.append(f'{self.name}_bucket{{le="+Inf"}} {self._count}')
        lines.append(f"{self.name}_sum {self._sum}")
        lines.append(f"{self.name}_count {self._count}")
        return "\n".join(lines)


# Global registry
asks_total = Counter("sovereignbi_asks_total", "Total /ask requests", labels=["status"])
uploads_total = Counter("sovereignbi_uploads_total", "Total /upload requests")
cache_hits_total = Counter("sovereignbi_cache_hits_total", "Cache hits")
cache_misses_total = Counter("sovereignbi_cache_misses_total", "Cache misses")
active_tables = Gauge("sovereignbi_active_tables", "Number of tables loaded")
ask_duration_seconds = Histogram("sovereignbi_ask_duration_seconds", "Duration of /ask calls")

_ALL_METRICS = [
    asks_total, uploads_total, cache_hits_total, cache_misses_total,
    active_tables, ask_duration_seconds,
]


def render_all() -> str:
    return "\n\n".join(m.render() for m in _ALL_METRICS) + "\n"
