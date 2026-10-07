"""Scheduler cron léger — daemon thread, vérification toutes les 60 secondes."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable


class CronScheduler:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    def add_job(self, job_id: str, cron_expr: str, func: Callable, *args: Any) -> None:
        with self._lock:
            self._jobs[job_id] = {"cron_expr": cron_expr, "func": func, "args": args}

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def job_count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="cron-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            with self._lock:
                jobs = list(self._jobs.values())
            for job in jobs:
                try:
                    if self.should_run(job["cron_expr"], None):
                        job["func"](*job["args"])
                except Exception:
                    pass
            time.sleep(60)

    @staticmethod
    def should_run(cron_expr: str, last_run_at: str | None) -> bool:
        """Vérifie si la tâche doit tourner maintenant.

        Formats supportés :
        - "every:<N>"  → toutes les N secondes (tests & fréquences courtes)
        - "@hourly"    → toutes les heures (minute == 0)
        - "@daily"     → tous les jours à minuit UTC
        - "HH MM * * *" standard (champ heure + minute seulement)
        """
        now = datetime.now(tz=timezone.utc)

        if cron_expr.startswith("every:"):
            interval = int(cron_expr.split(":")[1])
            if last_run_at is None:
                return True
            from datetime import datetime as dt
            last = dt.fromisoformat(last_run_at)
            return (now - last).total_seconds() >= interval

        if cron_expr == "@hourly":
            if last_run_at is None:
                return True
            from datetime import datetime as dt
            last = dt.fromisoformat(last_run_at)
            return (now - last).total_seconds() >= 3600

        if cron_expr == "@daily":
            if last_run_at is None:
                return True
            from datetime import datetime as dt
            last = dt.fromisoformat(last_run_at)
            return (now - last).total_seconds() >= 86400

        # Standard "M H * * *" — seuls M et H sont interprétés
        parts = cron_expr.split()
        if len(parts) >= 2:
            try:
                target_min = int(parts[0])
                target_hour = int(parts[1])
                if now.hour == target_hour and now.minute == target_min:
                    if last_run_at is None:
                        return True
                    from datetime import datetime as dt
                    last = dt.fromisoformat(last_run_at)
                    return (now - last).total_seconds() >= 3600
            except ValueError:
                pass

        return False
