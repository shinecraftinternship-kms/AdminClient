"""Feature store for ML model training and inference.

Extracts and stores structured features from device metrics, heartbeats,
and event data. Designed to feed both:
- Traditional ML models (sklearn, XGBoost)
- Time-series forecasting (Prophet, statsmodels)
- Anomaly detection (Isolation Forest, Autoencoders)

Features are computed per-device and stored in a format ready for
pandas DataFrame / numpy array consumption.
"""

import json
import logging
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional

from django.utils import timezone as tz

logger = logging.getLogger("monitoring")


class FeatureStore:
    """Extracts and caches ML-ready features from device data.

    Features are organized by device and time window, supporting
    both point-in-time and time-series feature generation.
    """

    def __init__(self):
        self._device_features: Dict[int, dict] = {}
        self._time_series: Dict[int, List[dict]] = defaultdict(list)

    def extract_features(self, device_id: int, heartbeat_data: dict,
                         sw_data: Optional[list] = None,
                         hw_data: Optional[list] = None) -> dict:
        """Extract a feature vector from the latest device data.

        Returns a dict of feature_name -> value, ready for model input.
        """
        features = {
            "device_id": device_id,
            "timestamp": tz.now().isoformat(),
        }

        features.update(self._extract_performance_features(heartbeat_data))
        features.update(self._extract_resource_features(heartbeat_data))
        features.update(self._extract_connectivity_features(heartbeat_data))

        if sw_data:
            features.update(self._extract_software_features(sw_data))
        if hw_data:
            features.update(self._extract_hardware_features(hw_data))

        features.update(self._extract_temporal_features(device_id))

        self._device_features[device_id] = features
        self._time_series[device_id].append(features)
        self._trim_time_series(device_id)

        return features

    def get_feature_matrix(self, device_ids: Optional[List[int]] = None,
                           hours: int = 168) -> List[dict]:
        """Get a list of feature dicts suitable for pandas DataFrame.

        Args:
            device_ids: Filter to specific devices (None = all)
            hours: Lookback window in hours

        Returns:
            List of feature dicts, one per device-timepoint.
        """
        cutoff = tz.now() - timedelta(hours=hours)
        result = []

        devices = device_ids or list(self._time_series.keys())
        for did in devices:
            for entry in self._time_series.get(did, []):
                ts = entry.get("timestamp", "")
                try:
                    entry_time = tz.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if entry_time >= cutoff:
                        result.append(entry)
                except (ValueError, TypeError):
                    result.append(entry)

        return result

    def get_latest_features(self, device_id: int) -> Optional[dict]:
        """Get the most recent feature vector for a device."""
        return self._device_features.get(device_id)

    def _extract_performance_features(self, data: dict) -> dict:
        """Extract CPU, RAM, disk performance features."""
        features = {}

        for key in ("cpu_usage_pct", "ram_usage_pct", "disk_usage_pct",
                     "disk_free_gb", "network_bytes_sent", "network_bytes_recv"):
            val = data.get(key)
            if val is not None:
                try:
                    features[key] = float(val)
                except (ValueError, TypeError):
                    features[key] = 0.0

        cpu = features.get("cpu_usage_pct", 0)
        ram = features.get("ram_usage_pct", 0)
        disk = features.get("disk_usage_pct", 0)

        features["resource_pressure"] = (cpu + ram + disk) / 3.0
        features["cpu_high"] = 1 if cpu > 80 else 0
        features["ram_high"] = 1 if ram > 80 else 0
        features["disk_high"] = 1 if disk > 90 else 0
        features["any_resource_critical"] = 1 if (cpu > 95 or ram > 95 or disk > 98) else 0

        return features

    def _extract_resource_features(self, data: dict) -> dict:
        """Extract derived resource features."""
        features = {}

        cpu = float(data.get("cpu_usage_pct", 0) or 0)
        ram = float(data.get("ram_usage_pct", 0) or 0)
        disk = float(data.get("disk_usage_pct", 0) or 0)

        features["cpu_ram_correlation"] = cpu * ram / 100.0
        features["disk_io_pressure"] = disk * (1 + cpu / 100.0)

        uptime = float(data.get("uptime_seconds", 0) or 0)
        features["uptime_hours"] = uptime / 3600.0
        features["needs_reboot"] = 1 if uptime > 720 else 0

        return features

    def _extract_connectivity_features(self, data: dict) -> dict:
        """Extract network connectivity features."""
        features = {}

        is_online = data.get("network_status", "online")
        features["is_online"] = 1 if is_online == "online" else 0
        features["is_disconnected"] = 1 if is_online != "online" else 0

        return features

    def _extract_software_features(self, sw_data: list) -> dict:
        """Extract software inventory features."""
        features = {}

        features["sw_count"] = len(sw_data)

        av_names = ["defender", "antivirus", "mcafee", "norton", "kaspersky",
                     "bitdefender", "avast", "sophos", "crowdstrike"]
        has_av = any(
            any(av in (s.get("name", "") if isinstance(s, dict) else str(s)).lower()
                for av in av_names)
            for s in sw_data
        )
        features["has_antivirus"] = 1 if has_av else 0

        browser_names = ["chrome", "firefox", "edge", "safari", "opera"]
        browser_count = sum(
            1 for s in sw_data
            if any(b in (s.get("name", "") if isinstance(s, dict) else str(s)).lower()
                   for b in browser_names)
        )
        features["browser_count"] = browser_count

        remote_tools = ["teamviewer", "anydesk", "remote desktop", "vnc", "ssh"]
        has_remote = any(
            any(r in (s.get("name", "") if isinstance(s, dict) else str(s)).lower()
                for r in remote_tools)
            for s in sw_data
        )
        features["has_remote_access"] = 1 if has_remote else 0

        return features

    def _extract_hardware_features(self, hw_data: list) -> dict:
        """Extract hardware inventory features."""
        features = {}

        features["hw_component_count"] = len(hw_data)

        types_seen = set()
        for comp in hw_data:
            ct = comp.get("component_type", "") if isinstance(comp, dict) else ""
            if ct:
                types_seen.add(ct)

        features["has_gpu"] = 1 if "gpu" in types_seen else 0
        features["storage_count"] = sum(1 for c in hw_data
                                         if isinstance(c, dict) and c.get("component_type") == "storage")

        return features

    def _extract_temporal_features(self, device_id: int) -> dict:
        """Extract time-based features for seasonality detection."""
        now = tz.now()
        features = {}

        features["hour_of_day"] = now.hour
        features["day_of_week"] = now.weekday()
        features["is_weekend"] = 1 if now.weekday() >= 5 else 0
        features["is_business_hours"] = 1 if 9 <= now.hour <= 17 and now.weekday() < 5 else 0

        history = self._time_series.get(device_id, [])
        features["observation_count"] = len(history)

        if len(history) >= 2:
            prev = history[-2]
            curr = history[-1] if history else {}
            for key in ("cpu_usage_pct", "ram_usage_pct"):
                prev_val = prev.get(key, 0)
                curr_val = curr.get(key, 0)
                features[f"{key}_delta"] = curr_val - prev_val
                features[f"{key}_rate"] = (curr_val - prev_val) / max(1, len(history))

        return features

    def _trim_time_series(self, device_id: int, max_entries: int = 1000):
        """Keep time series bounded."""
        data = self._time_series[device_id]
        if len(data) > max_entries:
            self._time_series[device_id] = data[-max_entries:]

    def export_for_training(self, hours: int = 720) -> dict:
        """Export feature data in a format suitable for model training.

        Returns dict with 'features' (list of dicts) and 'metadata'.
        """
        matrix = self.get_feature_matrix(hours=hours)

        numeric_features = []
        for row in matrix:
            numeric_row = {}
            for k, v in row.items():
                if isinstance(v, (int, float)):
                    numeric_row[k] = v
            numeric_features.append(numeric_row)

        return {
            "features": numeric_features,
            "metadata": {
                "total_samples": len(numeric_features),
                "feature_count": len(numeric_features[0]) if numeric_features else 0,
                "time_range_hours": hours,
                "generated_at": tz.now().isoformat(),
            },
        }


# ── Global singleton ─────────────────────────────────────────────────────────

feature_store = FeatureStore()
