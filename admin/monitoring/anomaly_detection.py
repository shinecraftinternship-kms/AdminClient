"""Statistical anomaly detection for device metrics.

Provides rule-based and statistical anomaly detection that works
without ML models. Designed as a foundation that ML models can
enhance when available.

Detection methods:
- Z-score: Flags values > N standard deviations from the mean
- IQR: Interquartile range outlier detection
- Moving average: Trend-based anomaly detection
- Threshold: Static threshold rules (CPU > 95%, etc.)
- Compound: Combines multiple signals for higher confidence
"""

import math
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from django.utils import timezone as tz

logger = logging.getLogger("monitoring")


@dataclass
class AnomalyResult:
    """A detected anomaly."""
    metric: str
    device_id: Optional[int] = None
    device_key: Optional[str] = None
    hostname: Optional[str] = None
    anomaly_type: str = "statistical"
    severity: str = "info"
    confidence: float = 0.0
    value: float = 0.0
    expected_range: Tuple[float, float] = (0.0, 0.0)
    description: str = ""
    detected_at: str = ""

    def to_dict(self):
        return {
            "metric": self.metric,
            "device_id": self.device_id,
            "device_key": self.device_key,
            "hostname": self.hostname,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "value": self.value,
            "expected_min": round(self.expected_range[0], 3),
            "expected_max": round(self.expected_range[1], 3),
            "description": self.description,
            "detected_at": self.detected_at,
        }


class AnomalyDetector:
    """Multi-method anomaly detection engine.

    Maintains per-device metric history and detects anomalies using
    configurable thresholds and statistical methods.
    """

    def __init__(self, z_threshold=2.5, iqr_multiplier=1.5, lookback_hours=168):
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.lookback_hours = lookback_hours
        self._metric_history: Dict[int, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._timestamps: Dict[int, List] = defaultdict(list)

    def ingest(self, device_id: int, metrics: dict, timestamp: Optional[float] = None):
        """Ingest a metrics snapshot for a device."""
        ts = timestamp or tz.now().timestamp()
        self._timestamps[device_id].append(ts)

        for key in ("cpu_usage_pct", "ram_usage_pct", "disk_usage_pct", "disk_free_gb"):
            val = metrics.get(key)
            if val is not None:
                try:
                    self._metric_history[device_id][key].append(float(val))
                except (ValueError, TypeError):
                    pass

        self._trim_history(device_id)

    def detect(self, device_id: int, current_metrics: dict,
               hostname: str = "", device_key: str = "") -> List[AnomalyResult]:
        """Run all detection methods against current metrics.

        Returns list of anomalies found.
        """
        anomalies = []
        now = tz.now().isoformat()

        anomalies.extend(self._detect_threshold(current_metrics, device_id, hostname, device_key, now))
        anomalies.extend(self._detect_zscore(current_metrics, device_id, hostname, device_key, now))
        anomalies.extend(self._detect_iqr(current_metrics, device_id, hostname, device_key, now))
        anomalies.extend(self._detect_trend(current_metrics, device_id, hostname, device_key, now))

        return anomalies

    def _detect_threshold(self, metrics: dict, device_id, hostname, device_key, now) -> List[AnomalyResult]:
        """Static threshold-based detection."""
        anomalies = []
        rules = [
            ("cpu_usage_pct", 95, "critical", "CPU usage critically high"),
            ("cpu_usage_pct", 85, "warning", "CPU usage elevated"),
            ("ram_usage_pct", 95, "critical", "RAM usage critically high"),
            ("ram_usage_pct", 85, "warning", "RAM usage elevated"),
            ("disk_usage_pct", 98, "critical", "Disk nearly full"),
            ("disk_usage_pct", 90, "warning", "Disk usage high"),
            ("disk_free_gb", 2, "critical", "Disk free space critically low"),
            ("disk_free_gb", 5, "warning", "Disk free space low"),
        ]

        for metric_name, threshold, severity, desc in rules:
            val = metrics.get(metric_name)
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            triggered = False
            if metric_name == "disk_free_gb":
                triggered = val <= threshold
            else:
                triggered = val >= threshold

            if triggered:
                anomalies.append(AnomalyResult(
                    metric=metric_name,
                    device_id=device_id,
                    device_key=device_key,
                    hostname=hostname,
                    anomaly_type="threshold",
                    severity=severity,
                    confidence=0.95,
                    value=val,
                    expected_range=(0, threshold),
                    description=desc,
                    detected_at=now,
                ))

        return anomalies

    def _detect_zscore(self, metrics: dict, device_id, hostname, device_key, now) -> List[AnomalyResult]:
        """Z-score anomaly detection."""
        anomalies = []
        history = self._metric_history.get(device_id, {})

        for metric_name in ("cpu_usage_pct", "ram_usage_pct", "disk_usage_pct"):
            val = metrics.get(metric_name)
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            data = history.get(metric_name, [])
            if len(data) < 10:
                continue

            mean = sum(data) / len(data)
            variance = sum((x - mean) ** 2 for x in data) / len(data)
            std = math.sqrt(variance) if variance > 0 else 0.001

            z = abs(val - mean) / std

            if z > self.z_threshold:
                severity = "critical" if z > 4 else "warning" if z > 3 else "info"
                confidence = min(0.99, 0.5 + (z - self.z_threshold) * 0.1)
                expected_min = mean - self.z_threshold * std
                expected_max = mean + self.z_threshold * std

                anomalies.append(AnomalyResult(
                    metric=metric_name,
                    device_id=device_id,
                    device_key=device_key,
                    hostname=hostname,
                    anomaly_type="statistical",
                    severity=severity,
                    confidence=confidence,
                    value=val,
                    expected_range=(max(0, expected_min), min(100, expected_max)),
                    description=f"{metric_name} is {z:.1f} std devs from mean ({mean:.1f}%)",
                    detected_at=now,
                ))

        return anomalies

    def _detect_iqr(self, metrics: dict, device_id, hostname, device_key, now) -> List[AnomalyResult]:
        """Interquartile range outlier detection."""
        anomalies = []
        history = self._metric_history.get(device_id, {})

        for metric_name in ("cpu_usage_pct", "ram_usage_pct", "disk_usage_pct"):
            val = metrics.get(metric_name)
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            data = sorted(history.get(metric_name, []))
            if len(data) < 20:
                continue

            q1 = data[len(data) // 4]
            q3 = data[3 * len(data) // 4]
            iqr = q3 - q1

            lower = q1 - self.iqr_multiplier * iqr
            upper = q3 + self.iqr_multiplier * iqr

            if val < lower or val > upper:
                anomalies.append(AnomalyResult(
                    metric=metric_name,
                    device_id=device_id,
                    device_key=device_key,
                    hostname=hostname,
                    anomaly_type="iqr_outlier",
                    severity="info",
                    confidence=0.7,
                    value=val,
                    expected_range=(max(0, lower), min(100, upper)),
                    description=f"{metric_name} outside IQR bounds [{lower:.1f}, {upper:.1f}]",
                    detected_at=now,
                ))

        return anomalies

    def _detect_trend(self, metrics: dict, device_id, hostname, device_key, now) -> List[AnomalyResult]:
        """Moving average trend detection."""
        anomalies = []
        history = self._metric_history.get(device_id, {})

        for metric_name in ("cpu_usage_pct", "ram_usage_pct", "disk_usage_pct"):
            val = metrics.get(metric_name)
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            data = history.get(metric_name, [])
            if len(data) < 20:
                continue

            short_window = data[-5:]
            long_window = data[-20:]

            short_avg = sum(short_window) / len(short_window)
            long_avg = sum(long_window) / len(long_window)

            if long_avg > 0:
                change_pct = (short_avg - long_avg) / long_avg * 100
            else:
                change_pct = 0

            if abs(change_pct) > 50:
                direction = "rising" if change_pct > 0 else "falling"
                anomalies.append(AnomalyResult(
                    metric=metric_name,
                    device_id=device_id,
                    device_key=device_key,
                    hostname=hostname,
                    anomaly_type="trend",
                    severity="warning" if direction == "rising" else "info",
                    confidence=0.6,
                    value=val,
                    expected_range=(long_avg * 0.5, long_avg * 1.5),
                    description=f"{metric_name} {direction} sharply ({change_pct:+.0f}% vs baseline)",
                    detected_at=now,
                ))

        return anomalies

    def _trim_history(self, device_id: int):
        """Remove old data points beyond the lookback window."""
        cutoff = tz.now().timestamp() - (self.lookback_hours * 3600)
        timestamps = self._timestamps.get(device_id, [])
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
            for metric_data in self._metric_history.get(device_id, {}).values():
                if metric_data:
                    metric_data.pop(0)

    def get_baseline(self, device_id: int, metric_name: str) -> Optional[dict]:
        """Get baseline statistics for a device metric."""
        data = self._metric_history.get(device_id, {}).get(metric_name, [])
        if len(data) < 5:
            return None

        sorted_data = sorted(data)
        n = len(sorted_data)
        return {
            "mean": sum(sorted_data) / n,
            "median": sorted_data[n // 2],
            "min": sorted_data[0],
            "max": sorted_data[-1],
            "std": math.sqrt(sum((x - sum(sorted_data)/n)**2 for x in sorted_data) / n),
            "p95": sorted_data[int(n * 0.95)],
            "p99": sorted_data[int(n * 0.99)],
            "sample_count": n,
        }


# ── Global singleton ─────────────────────────────────────────────────────────

anomaly_detector = AnomalyDetector()
