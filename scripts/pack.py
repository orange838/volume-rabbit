"""打包插件到 dist/，并剔掉不该随包发布的开发文件。

用法：python scripts/pack.py
需要先安装：pip install class-widgets-sdk
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist"


def pack_command() -> str:
    """定位 cw-plugin-pack（Windows 下要用完整 .exe 路径）。"""
    exe = shutil.which("cw-plugin-pack")
    if exe:
        return exe
    base = Path(sys.executable).parent
    for candidate in (base / "Scripts" / "cw-plugin-pack.exe", base / "cw-plugin-pack.exe"):
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "没找到 cw-plugin-pack，请先执行：pip install class-widgets-sdk"
    )

# 这些前缀 / 文件名不随包发布
DROP_PREFIXES = ("_dev/", ".github/", "__pycache__/", "_vr/__pycache__/", "scripts/")
DROP_EXACT = {".gitignore"}


def strip_archive(src_path: Path, out_path: Path) -> list[str]:
    """从 src_path 读取、剔除开发文件后写到 out_path（直接覆盖）。"""
    dropped: list[str] = []
    with zipfile.ZipFile(src_path) as src:
        keep = []
        for info in src.infolist():
            name = info.filename
            if name in DROP_EXACT or name.startswith(DROP_PREFIXES) or name.endswith(".pyc"):
                dropped.append(name)
                continue
            keep.append((info, src.read(name)))

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info, data in keep:
            dst.writestr(info, data)
    return dropped


def main() -> int:
    manifest = json.loads((ROOT / "cwplugin.json").read_text(encoding="utf-8"))
    plugin_id = manifest["id"]
    version = manifest["version"]

    OUT.mkdir(exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix="cwpack-"))
    made = []
    for fmt, suffix in (("cwplugin", ".cwplugin"), ("zip", ".zip")):
        target = OUT / f"{plugin_id}{suffix}"
        raw = build / f"{plugin_id}{suffix}"
        subprocess.run(
            [pack_command(), str(ROOT), "--format", fmt, "-o", str(raw)],
            check=True,
        )
        dropped = strip_archive(raw, target)
        with zipfile.ZipFile(target) as zf:
            names = zf.namelist()
            inside = json.loads(zf.read("cwplugin.json").decode("utf-8"))
        assert inside["id"] == plugin_id, "包内 id 与 cwplugin.json 不一致"
        assert inside["version"] == version, "包内 version 与 cwplugin.json 不一致"
        assert "main.py" in names, "包内缺少 main.py"
        made.append((target.name, len(names), target.stat().st_size))
        if dropped:
            print(f"  {target.name}: 剔除 {', '.join(dropped)}")

    print(f"\n打包完成（版本 {version}）：")
    for name, count, size in made:
        print(f"  dist/{name}  {count} 个文件  {size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
