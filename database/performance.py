import json
import math
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from statistics import median

from database.db import get_database_path


SCHEMA = """
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT,
    operation TEXT NOT NULL,
    phase TEXT NOT NULL,
    metric_kind TEXT NOT NULL CHECK(metric_kind IN ('processing', 'interaction')),
    duration_ms REAL NOT NULL CHECK(duration_ms >= 0),
    outcome TEXT NOT NULL CHECK(outcome IN ('success', 'failed', 'cancelled')),
    item_count INTEGER,
    unit_count INTEGER,
    error_category TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_performance_created
    ON performance_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_performance_phase
    ON performance_metrics(operation, phase, created_at);
"""

_initialized_path = None


def _connect():
    connection = sqlite3.connect(get_database_path(), timeout=1.0)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_performance_database():
    global _initialized_path
    database_path = str(get_database_path())
    if _initialized_path == database_path:
        return
    with closing(_connect()) as connection, connection:
        connection.executescript(SCHEMA)
    _initialized_path = database_path


def record_metrics(metrics):
    """Persist a group of non-sensitive metrics in one short transaction."""
    try:
        initialize_performance_database()
        created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        values = []
        for metric in metrics:
            values.append((
                metric.get("attempt_id"), metric["operation"], metric["phase"],
                metric.get("metric_kind", "processing"),
                max(0.0, float(metric["duration_ms"])),
                metric.get("outcome", "success"), metric.get("item_count"),
                metric.get("unit_count"), metric.get("error_category"),
                json.dumps(metric.get("metadata") or {}, separators=(",", ":"),
                           sort_keys=True),
                metric.get("created_at", created_at),
            ))
        with closing(_connect()) as connection, connection:
            connection.executemany(
                """INSERT INTO performance_metrics
                   (attempt_id, operation, phase, metric_kind, duration_ms, outcome,
                    item_count, unit_count, error_category, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                values,
            )
        return True
    except (OSError, sqlite3.Error, TypeError, ValueError, KeyError):
        return False


def record_metric(operation, phase, duration_ms, *, metric_kind="processing",
                  outcome="success", attempt_id=None, item_count=None,
                  unit_count=None, error_category=None, metadata=None):
    """Persist a non-sensitive timing metric without affecting the POS on failure."""
    return record_metrics([{
        "attempt_id": attempt_id, "operation": operation, "phase": phase,
        "metric_kind": metric_kind, "duration_ms": duration_ms, "outcome": outcome,
        "item_count": item_count, "unit_count": unit_count,
        "error_category": error_category, "metadata": metadata,
    }])


@contextmanager
def measure_metric(operation, phase, *, metric_kind="processing",
                   attempt_id=None, item_count=None, unit_count=None, metadata=None):
    started = time.perf_counter()
    outcome = "success"
    error_category = None
    try:
        yield
    except Exception as error:
        outcome = "failed"
        error_category = type(error).__name__
        raise
    finally:
        record_metric(
            operation, phase, (time.perf_counter() - started) * 1000,
            metric_kind=metric_kind, outcome=outcome, attempt_id=attempt_id,
            item_count=item_count, unit_count=unit_count,
            error_category=error_category, metadata=metadata,
        )


class CheckoutPerformance:
    def __init__(self, item_count, unit_count):
        self.attempt_id = uuid.uuid4().hex
        self.item_count = int(item_count)
        self.unit_count = int(unit_count)
        self.started = time.perf_counter()
        self.processing_ms = 0.0
        self.interaction_ms = 0.0
        self.finished = False
        self.pending_metrics = []

    def _append(self, phase, duration_ms, metric_kind="processing",
                outcome="success", error_category=None, metadata=None):
        self.pending_metrics.append({
            "operation": "checkout", "phase": phase,
            "duration_ms": duration_ms, "metric_kind": metric_kind,
            "outcome": outcome, "attempt_id": self.attempt_id,
            "item_count": self.item_count, "unit_count": self.unit_count,
            "error_category": error_category, "metadata": metadata,
        })

    @contextmanager
    def measure(self, phase, metric_kind="processing", metadata=None):
        started = time.perf_counter()
        outcome = "success"
        error_category = None
        try:
            yield
        except Exception as error:
            outcome = "failed"
            error_category = type(error).__name__
            raise
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            if metric_kind == "interaction":
                self.interaction_ms += elapsed
            else:
                self.processing_ms += elapsed
            self._append(phase, elapsed, metric_kind, outcome, error_category, metadata)

    def record_phase(self, phase, duration_ms, *, metric_kind="processing",
                     outcome="success", error_category=None, metadata=None,
                     include_in_total=False):
        """Record a measured subphase, optionally excluding overlapping time from totals."""
        duration_ms = max(0.0, float(duration_ms))
        if include_in_total:
            if metric_kind == "interaction":
                self.interaction_ms += duration_ms
            else:
                self.processing_ms += duration_ms
        self._append(phase, duration_ms, metric_kind, outcome, error_category, metadata)

    def finish(self, outcome, error_category=None):
        if self.finished:
            return
        self.finished = True
        total_ms = (time.perf_counter() - self.started) * 1000
        self._append("processing_total", self.processing_ms, "processing",
                     outcome, error_category)
        self._append("interaction_total", self.interaction_ms, "interaction",
                     outcome, error_category)
        self._append("total_system_checkout", total_ms, "interaction",
                     outcome, error_category,
                     {"measurement_scope": "wall_clock"})
        record_metrics(self.pending_metrics)
        self.pending_metrics.clear()


def _percentile(values, percentile):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil((percentile / 100) * len(ordered)) - 1)
    return float(ordered[index])


def _statistics(values):
    values = [float(value) for value in values]
    if not values:
        return {key: 0.0 for key in ("avg", "min", "max", "median", "p95")}
    return {
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "median": float(median(values)),
        "p95": _percentile(values, 95),
    }


def get_performance_statistics(days=30):
    initialize_performance_database()
    days = max(1, min(int(days), 3650))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with closing(_connect()) as connection:
        rows = connection.execute(
            """SELECT operation, phase, metric_kind, duration_ms, outcome
               FROM performance_metrics
               WHERE created_at >= ?
               ORDER BY operation, phase, id""", (since,),
        ).fetchall()

    grouped = {}
    for row in rows:
        key = (row["operation"], row["phase"], row["metric_kind"])
        group = grouped.setdefault(key, {"values": [], "success": 0,
                                         "failed": 0, "cancelled": 0})
        group["values"].append(row["duration_ms"])
        group[row["outcome"]] += 1

    phases = []
    for (operation, phase, metric_kind), group in grouped.items():
        phases.append({
            "operation": operation,
            "phase": phase,
            "metric_kind": metric_kind,
            "count": len(group["values"]),
            "success": group["success"],
            "failed": group["failed"],
            "cancelled": group["cancelled"],
            **_statistics(group["values"]),
        })

    totals = [row for row in rows
              if row["operation"] == "checkout"
              and row["phase"] == "total_system_checkout"]
    processing_totals = [row for row in rows
                         if row["operation"] == "checkout"
                         and row["phase"] == "processing_total"]
    successful = sum(row["outcome"] == "success" for row in totals)
    failed = sum(row["outcome"] == "failed" for row in totals)
    cancelled = sum(row["outcome"] == "cancelled" for row in totals)
    return {
        "days": days,
        "attempts": len(totals),
        "successful": successful,
        "failed": failed,
        "cancelled": cancelled,
        "success_rate": (successful / len(totals) * 100) if totals else 0.0,
        "checkout": _statistics([row["duration_ms"] for row in processing_totals]),
        "wall_clock": _statistics([row["duration_ms"] for row in totals]),
        "phases": phases,
    }
