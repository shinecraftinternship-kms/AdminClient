from dataclasses import dataclass, field
from typing import Optional


def serialize(obj):
    from dataclasses import asdict
    return asdict(obj)


@dataclass
class RegistrationRequest:
    registration_key: str
    hostname: str
    platform: str
    client_version: str = ""


@dataclass
class PingRequest:
    registration_key: str
    hostname: str
    client_version: str = ""


@dataclass
class ScanData:
    registration_key: str
    hostname: str
    scan_type: str
    processor: dict = field(default_factory=dict)
    ram: dict = field(default_factory=dict)
    storage: dict = field(default_factory=dict)
    gpu: list = field(default_factory=list)
    motherboard: dict = field(default_factory=dict)
    os_info: dict = field(default_factory=dict)
    accounts: list = field(default_factory=list)
    network: dict = field(default_factory=dict)
    peripherals: dict = field(default_factory=dict)
    software: list = field(default_factory=list)
    updates: list = field(default_factory=list)
    antivirus: dict = field(default_factory=dict)


@dataclass
class ManualUpdate:
    hostname: Optional[str] = None
    purchase_cost: Optional[float] = None
    purchase_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None
    warranty_expiry: Optional[str] = None
    notes: Optional[str] = None
    group: Optional[int] = None
    tags: Optional[str] = None


@dataclass
class AddonDevice:
    name: str
    description: str = ""
    serial_number: str = ""
    purchase_cost: Optional[float] = None
    category: str = ""


@dataclass
class ScanConfig:
    interval_seconds: int = 3600
    enabled: bool = True


@dataclass
class ClientInfo:
    registration_key: str
    hostname: str
    platform: str
    status: str
    approved: bool
    last_seen: Optional[str] = None
    group: Optional[str] = None
    tags: list = field(default_factory=list)
    client_version: str = ""
    cpu_model: str = ""
    ram_info: str = ""


@dataclass
class ActivityEntry:
    action: str
    client_hostname: str = ""
    details: str = ""
    created_at: str = ""


@dataclass
class GroupInfo:
    name: str
    description: str = ""


@dataclass
class AppSettings:
    auto_approve: bool = False
    stale_threshold_seconds: int = 7200
    scan_all_interval: int = 86400
