# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\main.py'],
    pathex=['C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client'],
    binaries=[],
    datas=[('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\client_config.json', 'client'), ('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\client_key.json', 'client'), ('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\requirements.txt', 'client'), ('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\scans\\scan_20260522_101203.json', 'client\\scans'), ('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\scans\\scan_20260522_101233.json', 'client\\scans'), ('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\scans\\scan_20260522_101303.json', 'client\\scans'), ('C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\scans\\scan_20260522_101333.json', 'client\\scans')],
    hiddenimports=['websockets', 'watchdog', 'watchdog.observers', 'watchdog.events', 'client.runtime', 'client.key_manager', 'client.config', 'client.communicator', 'client.scanner', 'client.discovery', 'client.metrics', 'client.fingerprint', 'client.events', 'client.events.dispatcher', 'client.events.usb_monitor', 'client.events.file_monitor', 'client.events.process_monitor', 'client.events.software_monitor'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='client_scanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:\\new intern project\\system_scanner_pro\\admin-client  main\\AdminClient\\client\\version-info.txt',
)
