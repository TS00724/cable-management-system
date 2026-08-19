#!/usr/bin/env python3
from __future__ import annotations

import base64
import bz2
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import lzma
import zlib

ROOT = Path(__file__).resolve().parents[1]
PARTS = sorted((ROOT / ".payload").glob("part-*"))


def b64(data: bytes) -> bytes | None:
    compact = re.sub(rb"\s+", b"", data)
    if not compact:
        return None
    compact += b"=" * ((4 - len(compact) % 4) % 4)
    try:
        return base64.b64decode(compact, validate=False)
    except Exception:
        return None


def expand(seed: list[bytes]) -> list[bytes]:
    queue = list(seed)
    out: list[bytes] = []
    seen: set[str] = set()
    while queue and len(out) < 96:
        data = queue.pop(0)
        digest = hashlib.sha256(data).hexdigest()
        if not data or digest in seen:
            continue
        seen.add(digest)
        out.append(data)
        decoded = b64(data)
        if decoded and decoded != data:
            queue.append(decoded)
        for fn in (gzip.decompress, bz2.decompress, lzma.decompress, zlib.decompress):
            try:
                candidate = fn(data)
            except Exception:
                continue
            if candidate and candidate != data:
                queue.append(candidate)
        try:
            value = json.loads(data.decode("utf-8"))
            if isinstance(value, str):
                queue.append(value.encode())
            elif isinstance(value, dict):
                for key in ("content", "data", "patch", "payload", "archive", "archive_base64", "patch_base64"):
                    item = value.get(key)
                    if isinstance(item, str):
                        queue.append(item.encode())
                        item_decoded = b64(item.encode())
                        if item_decoded:
                            queue.append(item_decoded)
                if isinstance(value.get("files"), list):
                    queue.append(json.dumps({"files": value["files"]}).encode())
            elif isinstance(value, list):
                strings = [item for item in value if isinstance(item, str)]
                if strings:
                    queue.append("".join(strings).encode())
        except Exception:
            pass
        try:
            text = data.decode("utf-8")
            fenced = re.sub(r"^```(?:text|diff|patch|base64|json)?\s*|\s*```$", "", text.strip(), flags=re.S | re.I).encode()
            if fenced != data:
                queue.append(fenced)
            marker = re.sub(r"^\s*(?:PATCH|PAYLOAD)[ _-]*PART[^\n]*\n", "", text, count=1, flags=re.I).encode()
            if marker != data:
                queue.append(marker)
        except Exception:
            pass
    return out


def safe_target(path: str) -> Path:
    target = (ROOT / path).resolve()
    if target == ROOT or ROOT not in target.parents:
        raise RuntimeError(f"unsafe payload path: {path}")
    return target


def apply_manifest(data: bytes) -> bool:
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return False
    files = obj.get("files") if isinstance(obj, dict) else None
    if not isinstance(files, list):
        return False
    wrote = 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        target = safe_target(item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        content = item.get("content", "")
        if item.get("encoding") == "base64" and isinstance(content, str):
            target.write_bytes(base64.b64decode(content))
        elif isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            continue
        wrote += 1
    return wrote > 0


def overlay(source: Path) -> bool:
    children = [p for p in source.iterdir() if p.name not in {".git", ".payload", "__MACOSX"}]
    while len(children) == 1 and children[0].is_dir() and not (children[0] / "pyproject.toml").exists() and not (children[0] / "apps").exists():
        source = children[0]
        children = [p for p in source.iterdir() if p.name not in {".git", ".payload", "__MACOSX"}]
    if not children:
        return False
    for child in children:
        destination = ROOT / child.name
        if child.is_dir():
            shutil.copytree(child, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", ".next", "__pycache__"))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)
    return True


def apply_archive(data: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="webui-") as raw:
        temp = Path(raw)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    target = (temp / info.filename).resolve()
                    if target != temp and temp not in target.parents:
                        raise RuntimeError("unsafe zip member")
                archive.extractall(temp)
            return overlay(temp)
        except (zipfile.BadZipFile, OSError):
            pass
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
                for member in archive.getmembers():
                    target = (temp / member.name).resolve()
                    if target != temp and temp not in target.parents:
                        raise RuntimeError("unsafe tar member")
                archive.extractall(temp, filter="data")
            return overlay(temp)
        except (tarfile.TarError, OSError, TypeError):
            return False


def apply_patch(data: bytes) -> bool:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if "diff --git " not in text and not ("--- a/" in text and "+++ b/" in text):
        return False
    patch = Path(tempfile.mkstemp(prefix="webui-", suffix=".patch")[1])
    patch.write_bytes(data)
    try:
        for command in (["git", "apply", "--binary", "--whitespace=nowarn", str(patch)], ["git", "apply", "--3way", "--binary", "--whitespace=nowarn", str(patch)]):
            if subprocess.run(command, cwd=ROOT).returncode == 0:
                return True
        return False
    finally:
        patch.unlink(missing_ok=True)


def main() -> int:
    if len(PARTS) != 3:
        raise RuntimeError(f"expected 3 payload parts, found {len(PARTS)}")
    parts = [p.read_bytes() for p in PARTS]
    seeds = [b"".join(parts), *parts]
    decoded = [b64(part) for part in parts]
    if all(item is not None for item in decoded):
        seeds.append(b"".join(item for item in decoded if item is not None))
    candidates = expand(seeds)
    print(f"payload candidates: {len(candidates)}")
    for index, candidate in enumerate(candidates, 1):
        print(f"candidate {index}: {len(candidate)} bytes sha256={hashlib.sha256(candidate).hexdigest()}")
        if apply_manifest(candidate) or apply_archive(candidate) or apply_patch(candidate):
            print(f"payload applied from candidate {index}")
            return 0
    raise RuntimeError("unable to identify or apply uploaded WebUI payload")


if __name__ == "__main__":
    sys.exit(main())
