# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules


project_root = Path.cwd()
argus_root = project_root / "Argus"
model_root = argus_root / "output" / "artifacts" / "ocr_calibration" / "models"

datas = [
    (str(argus_root / "config.yaml"), "Argus"),
]
datas += [
    (
        str(project_root / ".venv" / "Lib" / "site-packages" / "rapidocr" / "config.yaml"),
        "rapidocr",
    ),
    (
        str(project_root / ".venv" / "Lib" / "site-packages" / "rapidocr" / "default_models.yaml"),
        "rapidocr",
    ),
]
datas += [
    (str(model_path), "Argus/output/artifacts/ocr_calibration/models")
    for model_path in model_root.glob("*.onnx")
]

hiddenimports = collect_submodules("rapidocr")
hiddenimports += collect_submodules("onnxruntime")

binaries = collect_dynamic_libs("onnxruntime")

a = Analysis(
    ["Argus/ff_desktop.py"],
    pathex=[str(argus_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="FF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FF",
    contents_directory=".",
)
