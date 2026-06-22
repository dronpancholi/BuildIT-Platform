"""Stub implementation of prometheus_client for testing.
Provides minimal Counter, Gauge, Histogram, and Info classes that record values
in-memory. This avoids pulling in the heavy external dependency while satisfying
imports used throughout the codebase and test suite.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

class _MetricValue:
    def __init__(self) -> None:
        self._val = 0
        self._sum_val = 0

    def inc(self, amount: int = 1) -> None:
        self._val += amount

    def observe(self, amount: float) -> None:
        # Increment count and add to sum
        self._val += 1
        self._sum_val += amount

    def set(self, value: Any) -> None:
        self._val = value

    @property
    def _value_obj(self):
        # Simple wrapper with get()
        class _Val:
            def __init__(self, parent: _MetricValue):
                self._parent = parent
            def get(self) -> int:
                return self._parent._val
        return _Val(self)

    @property
    def _sum_obj(self):
        class _Sum:
            def __init__(self, parent: _MetricValue):
                self._parent = parent
            def get(self) -> float:
                return self._parent._sum_val
        return _Sum(self)

    # Compatibility attributes used in tests
    @property
    def _value(self):
        return self._value_obj

    @property
    def _sum(self):
        return self._sum_obj


# Global registry of all metric instances
_REGISTRY: List[Any] = []

class _BaseMetric:
    def __init__(self, name: str, documentation: str, *labelnames: str, **kwargs: Any) -> None:
        self._metrics: Dict[Tuple[Tuple[str, Any], ...], _MetricValue] = {}
        self._name = name
        self._documentation = documentation
        self._labelnames = labelnames
        # default metric for calls without labels
        self._default = _MetricValue()
        self._metrics[()] = self._default
        _REGISTRY.append(self)

    def _key_from_labels(self, labels: Dict[str, Any] | None) -> Tuple[Tuple[str, Any], ...]:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def labels(self, **labels: Any) -> _MetricValue:
        key = self._key_from_labels(labels)
        if key not in self._metrics:
            self._metrics[key] = _MetricValue()
        return self._metrics[key]

    def inc(self, amount: int = 1, labels: Dict[str, Any] | None = None) -> None:
        metric = self.labels(**(labels or {}))
        metric.inc(amount)

    def set(self, value: Any, labels: Dict[str, Any] | None = None) -> None:
        metric = self.labels(**(labels or {}))
        metric.set(value)


class Counter(_BaseMetric):
    pass

class Gauge(_BaseMetric):
    pass

class Histogram(_BaseMetric):
    def observe(self, amount: float, labels: Dict[str, Any] | None = None) -> None:
        metric = self.labels(**(labels or {}))
        metric.observe(amount)

class Info(_BaseMetric):
    # Info behaves like a gauge storing arbitrary info; for tests we only need init.
    pass


CONTENT_TYPE_LATEST = 'text/plain; version=0.0.4; charset=utf-8'


def generate_latest(registry=None):
    """Generate a minimal Prometheus text-format snapshot from stub metrics."""
    lines = []
    sources = registry if registry is not None else _REGISTRY
    for metric in sources:
        if not isinstance(metric, _BaseMetric):
            continue
        lines.append(f"# HELP {metric._name} {metric._documentation}")
        lines.append(f"# TYPE {metric._name} {type(metric).__name__.lower()}")
        for key, mv in metric._metrics.items():
            label_str = ""
            if key:
                parts = ",".join(f'{k}="{v}"' for k, v in key)
                label_str = "{" + parts + "}"
            if isinstance(metric, (Counter, Gauge)):
                lines.append(f"{metric._name}{label_str} {mv._val}")
            elif isinstance(metric, Histogram):
                lines.append(f"{metric._name}_count{label_str} {mv._val}")
                lines.append(f"{metric._name}_sum{label_str} {mv._sum_val}")
                lines.append(f"{metric._name}_bucket{label_str}{{le=\"+Inf\"}} {mv._val}")
    return "\n".join(lines).encode("utf-8")
