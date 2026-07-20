"""Predictive analytics hooks for proactive device management.

Uses trend analysis and statistical extrapolation (no external ML
dependencies) to predict:
- Disk full time (when will disk reach 100%?)
- Device failure risk score
- Maintenance window recommendations
- Capacity planning forecasts

These hooks can be enhanced with ML models when available. The
current implementation uses linear regression and exponential
smoothing on the feature store time series.
"""

import math
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from django.utils import timezone as tz

logger = logging.getLogger("monitoring")


@dataclass
class Prediction:
    """A single prediction result."""
    metric: str
    device_id: Optional[int] = None
    device_key: Optional[str] = None
    hostname: Optional[str] = None
    prediction_type: str = ""
    value: float = 0.0
    unit: str = ""
    confidence: float = 0.0
    timeframe_hours: float = 0.0
    description: str = ""
    recommended_action: str = ""
    predicted_at: str = ""

    def to_dict(self):
        return {
            "metric": self.metric,
            "device_id": self.device_id,
            "device_key": self.device_key,
            "hostname": self.hostname,
            "prediction_type": self.prediction_type,
            "value": round(self.value, 2),
            "unit": self.unit,
            "confidence": round(self.confidence, 3),
            "timeframe_hours": round(self.timeframe_hours, 1),
            "description": self.description,
            "recommended_action": self.recommended_action,
            "predicted_at": self.predicted_at,
        }


class PredictiveEngine:
    """Predictive analytics engine using statistical methods.

    Analyzes time-series data from the feature store to generate
    actionable predictions for device management.
    """

    def __init__(self):
        self._predictions_cache: Dict[int, List[Prediction]] = {}

    def predict_disk_full(self, device_id: int, disk_history: List[float],
                          current_pct: float, device_key: str = "",
                          hostname: str = "") -> Optional[Prediction]:
        """Predict when disk will reach capacity.

        Uses linear regression on disk usage history.
        """
        if len(disk_history) < 5:
            return None

        now = tz.now()
        n = len(disk_history)
        x_vals = list(range(n))
        y_vals = disk_history

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        den = sum((x - x_mean) ** 2 for x in x_vals)

        if den == 0:
            return None

        slope = num / den
        intercept = y_mean - slope * x_mean

        if slope <= 0:
            return Prediction(
                metric="disk_usage_pct",
                device_id=device_id,
                device_key=device_key,
                hostname=hostname,
                prediction_type="disk_full",
                value=current_pct,
                unit="%",
                confidence=0.3,
                timeframe_hours=0,
                description="Disk usage is stable or decreasing",
                recommended_action="No action needed",
                predicted_at=now.isoformat(),
            )

        hours_to_full = (100 - current_pct) / slope if slope > 0 else float("inf")
        confidence = min(0.9, 0.3 + 0.05 * min(n, 12))

        if hours_to_full < 24:
            action = "URGENT: Free disk space immediately or add storage"
            desc = f"Disk will reach capacity in ~{hours_to_full:.0f} hours"
        elif hours_to_full < 168:
            action = "Schedule disk cleanup or storage expansion within the week"
            desc = f"Disk will reach capacity in ~{hours_to_full / 24:.1f} days"
        elif hours_to_full < 720:
            action = "Plan storage expansion within the month"
            desc = f"Disk will reach capacity in ~{hours_to_full / 24:.0f} days"
        else:
            action = "Monitor — disk capacity is adequate for now"
            desc = f"Disk capacity sufficient for ~{hours_to_full / 24:.0f} days"

        return Prediction(
            metric="disk_usage_pct",
            device_id=device_id,
            device_key=device_key,
            hostname=hostname,
            prediction_type="disk_full",
            value=current_pct,
            unit="%",
            confidence=confidence,
            timeframe_hours=hours_to_full,
            description=desc,
            recommended_action=action,
            predicted_at=now.isoformat(),
        )

    def predict_failure_risk(self, device_id: int, metrics_history: List[dict],
                             current_metrics: dict,
                             device_key: str = "", hostname: str = "") -> Optional[Prediction]:
        """Compute a device failure risk score.

        Based on: resource pressure, age, connectivity, alert history.
        """
        if not current_metrics:
            return None

        now = tz.now()
        risk_score = 0.0
        factors = []

        cpu = float(current_metrics.get("cpu_usage_pct", 0) or 0)
        ram = float(current_metrics.get("ram_usage_pct", 0) or 0)
        disk = float(current_metrics.get("disk_usage_pct", 0) or 0)

        resource_pressure = (cpu + ram + disk) / 300.0
        risk_score += resource_pressure * 30
        if resource_pressure > 0.85:
            factors.append("high resource pressure")

        uptime = float(current_metrics.get("uptime_seconds", 0) or 0)
        uptime_days = uptime / 86400
        if uptime_days > 30:
            risk_score += min(15, uptime_days * 0.5)
            factors.append(f"uptime {uptime_days:.0f} days")

        if len(metrics_history) >= 10:
            recent = metrics_history[-10:]
            volatility = self._compute_volatility([m.get("cpu_usage_pct", 0) for m in recent])
            if volatility > 20:
                risk_score += volatility * 0.3
                factors.append("volatile CPU")

        health_scores = [m.get("health_score", 80) for m in metrics_history[-20:]]
        if health_scores:
            avg_health = sum(health_scores) / len(health_scores)
            health_risk = max(0, (80 - avg_health) / 80)
            risk_score += health_risk * 25
            if health_risk > 0.3:
                factors.append("declining health score")

        risk_score = min(100, max(0, risk_score))

        if risk_score > 70:
            level = "critical"
            action = "Schedule immediate maintenance check"
        elif risk_score > 40:
            level = "warning"
            action = "Monitor closely and schedule preventive maintenance"
        else:
            level = "low"
            action = "No immediate action needed"

        return Prediction(
            metric="failure_risk",
            device_id=device_id,
            device_key=device_key,
            hostname=hostname,
            prediction_type="failure_risk",
            value=risk_score,
            unit="score",
            confidence=min(0.8, 0.3 + 0.05 * len(metrics_history)),
            timeframe_hours=168,
            description=f"Failure risk score: {risk_score:.0f}/100 ({level}). Factors: {', '.join(factors) or 'none'}",
            recommended_action=action,
            predicted_at=now.isoformat(),
        )

    def predict_capacity_needs(self, device_id: int, disk_history: List[float],
                               ram_history: List[float],
                               device_key: str = "", hostname: str = "") -> List[Prediction]:
        """Predict capacity needs for the next 30/60/90 days."""
        predictions = []
        now = tz.now()

        for metric_name, history, label in [
            ("disk_usage_pct", disk_history, "Disk"),
            ("ram_usage_pct", ram_history, "RAM"),
        ]:
            if len(history) < 5:
                continue

            n = len(history)
            x_vals = list(range(n))
            x_mean = sum(x_vals) / n
            y_mean = sum(history) / n
            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, history))
            den = sum((x - x_mean) ** 2 for x in x_vals)
            slope = num / den if den > 0 else 0

            current = history[-1]

            for days, label_t in [(30, "30 days"), (60, "60 days"), (90, "90 days")]:
                hours = days * 24
                steps = hours / max(1, (len(history) and 1))
                predicted = current + slope * steps
                predicted = min(100, max(0, predicted))

                if predicted > 95:
                    action = f"Add {label.lower()} capacity before {label_t}"
                elif predicted > 80:
                    action = f"Plan {label.lower()} expansion within {label_t}"
                else:
                    action = f"{label} capacity adequate for {label_t}"

                predictions.append(Prediction(
                    metric=metric_name,
                    device_id=device_id,
                    device_key=device_key,
                    hostname=hostname,
                    prediction_type="capacity_forecast",
                    value=predicted,
                    unit="%",
                    confidence=min(0.7, 0.3 + 0.01 * len(history)),
                    timeframe_hours=hours,
                    description=f"{label} predicted at {predicted:.1f}% in {label_t}",
                    recommended_action=action,
                    predicted_at=now.isoformat(),
                ))

        return predictions

    def _compute_volatility(self, values: List[float]) -> float:
        """Compute the standard deviation of a list of values."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)


# ── Global singleton ─────────────────────────────────────────────────────────

predictive_engine = PredictiveEngine()
