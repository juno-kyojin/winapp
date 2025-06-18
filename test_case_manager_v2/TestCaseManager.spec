block_cipher = None

a = Analysis(
    ['src\\main.py'],
    pathex=['C:\\Users\\tobie\\Desktop\\winapp\\test_case_manager_v2'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('data\\templates', 'data\\templates'),
        ('data\\config', 'data\\config'),
        ('data\\database', 'data\\database'),
    ],
    hiddenimports=[
        'tkinter',
        'paramiko',
        'requests',
        'core',
        'core.config',
        'core.constants',
        'core.exceptions',
        'gui',
        'gui.main_window',
        'gui.widgets',
        'gui.widgets.queue_manager',
        'utils',
        'utils.file_utils',
        'utils.formatters',
        'utils.logger',
        'utils.validators',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TestCaseManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    onefile=True,
)