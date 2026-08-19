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


def json_payload(data: bytes) -> list[bytes]:
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return []
    out: list[bytes] = []
    if isinstance(obj, str):
        out.append(obj.encode())
    elif isinstance(obj, dict):
        for key in ("content", "data", "patch", "payload", "archive", "archive_base64", "patch_base64"):
            value = obj.get(key)
            if isinstance(value, str):
                out.append(value.encode())
                decoded = b64(value.encode())
                if decoded is not None:
                    out.append(decoded)
        files = obj.get("files")
        if isinstance(files, list):
            out.append(json.dumps({"files": files}).encode())
    elif isinstance(obj, list):
        strings = [v for v in obj if isinstance(v, str)]
        if strings:
            joined = "".join(strings).encode()
            out.append(joined)
            decoded = b64(joined)
            if decoded is not None:
                out.append(decoded)
    return out


def expand_candidates(seed: list[bytes]) -> list[bytes]:
    queue = list(seed)
    result: list[bytes] = []
    seen: set[str] = set()
    while queue and len(result) < 96:
        data = queue.pop(0)
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen or not data:
            continue
        seen.add(digest)
        result.append(data)
        decoded = b64(data)
        if decoded is not None and decoded != data:
            queue.append(decoded)
        queue.extend(json_payload(data))
        for fn in (gzip.decompress, bz2.decompress, lzma.decompress, zlib.decompress):
            try:
                candidate = fn(data)
            except Exception:
                continue
            if candidate and candidate != data:
                queue.append(candidate)
        try:
            text = data.decode("utf-8")
        except Exception:
            continue
        fenced = re.sub(r"^```(?:text|diff|patch|base64|json)?\s*|\s*```$", "", text.strip(), flags=re.S | re.I).encode()
        if fenced != data:
            queue.append(fenced)
        marker = re.sub(r"^\s*(?:PATCH|PAYLOAD)[ _-]*PART[^\n]*\n", "", text, count=1, flags=re.I).encode()
        if marker != data:
            queue.append(marker)
    return result


def safe_target(path: str) -> Path:
    target = (ROOT / path).resolve()
    if target == ROOT or ROOT not in target.parents:
        raise RuntimeError(f"unsafe payload path: {path}")
    return target


def apply_json_manifest(data: bytes) -> bool:
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
        value = item.get("content", "")
        if item.get("encoding") == "base64" and isinstance(value, str):
            target.write_bytes(base64.b64decode(value))
        elif isinstance(value, str):
            target.write_text(value, encoding="utf-8")
        else:
            continue
        wrote += 1
    return wrote > 0


def overlay_tree(source: Path) -> bool:
    children = [p for p in source.iterdir() if p.name not in {".git", ".payload", "__MACOSX"}]
    while len(children) == 1 and children[0].is_dir() and not (children[0] / "package.json").exists() and not (children[0] / "pyproject.toml").exists():
        source = children[0]
        children = [p for p in source.iterdir() if p.name not in {".git", ".payload", "__MACOSX"}]
    if not children:
        return False
    for child in children:
        dest = ROOT / child.name
        if child.is_dir():
            shutil.copytree(child, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", ".next", "__pycache__"))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, dest)
    return True


def apply_archive(data: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="webui-payload-") as tmp_raw:
        tmp = Path(tmp_raw)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    safe = (tmp / info.filename).resolve()
                    if safe != tmp and tmp not in safe.parents:
                        raise RuntimeError("unsafe zip entry")
                archive.extractall(tmp)
            return overlay_tree(tmp)
        except (zipfile.BadZipFile, OSError):
            pass
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
                for member in archive.getmembers():
                    safe = (tmp / member.name).resolve()
                    if safe != tmp and tmp not in safe.parents:
                        raise RuntimeError("unsafe tar entry")
                archive.extractall(tmp, filter="data")
            return overlay_tree(tmp)
        except (tarfile.TarError, OSError, TypeError):
            return False


def apply_patch(data: bytes) -> bool:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    looks_like_patch = "diff --git " in text or ("--- a/" in text and "+++ b/" in text)
    looks_like_mail = text.startswith("From ") and "Subject:" in text and "diff --git " in text
    if not looks_like_patch and not looks_like_mail:
        return False
    patch = Path(tempfile.mkstemp(prefix="webui-", suffix=".patch")[1])
    patch.write_bytes(data)
    try:
        if looks_like_mail:
            proc = subprocess.run(["git", "am", "--3way", str(patch)], cwd=ROOT)
            if proc.returncode == 0:
                return True
            subprocess.run(["git", "am", "--abort"], cwd=ROOT, check=False)
        for args in (["git", "apply", "--binary", "--whitespace=nowarn", str(patch)], ["git", "apply", "--3way", "--binary", "--whitespace=nowarn", str(patch)]):
            proc = subprocess.run(args, cwd=ROOT)
            if proc.returncode == 0:
                return True
        return False
    finally:
        patch.unlink(missing_ok=True)


def main() -> int:
    if len(PARTS) != 3:
        raise RuntimeError(f"expected 3 payload parts, found {len(PARTS)}")
    raw_parts = [p.read_bytes() for p in PARTS]
    seeds = [b"".join(raw_parts)] + raw_parts
    decoded_parts = [b64(part) for part in raw_parts]
    if all(part is not None for part in decoded_parts):
        seeds.append(b"".join(part for part in decoded_parts if part is not None))
    candidates = expand_candidates(seeds)
    print(f"payload candidates: {len(candidates)}")
    for index, candidate in enumerate(candidates, start=1):
        print(f"candidate {index}: {len(candidate)} bytes sha256={hashlib.sha256(candidate).hexdigest()}")
        if apply_json_manifest(candidate) or apply_archive(candidate) or apply_patch(candidate):
            print(f"payload applied from candidate {index}")
            return 0
    raise RuntimeError("unable to identify or apply uploaded WebUI payload")


if __name__ == "__main__":
    sys.exit(main())
