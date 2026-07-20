import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from AdminClient.admin.scanner import (
    run_command, run_powershell, read_file, get_hostname, detect_platform,
    collect_all, _get_processor, _get_ram, _get_storage, _get_motherboard,
    _get_os_info, _get_network, _get_gpu, _get_accounts, _get_software,
    _get_updates, _get_peripherals, _get_antivirus,
)
