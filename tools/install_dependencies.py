"""Подготовить Pygame: проверенный локальный wheel или HTTPS с проверкой TLS.

Wheel для Windows x64 / CPython 3.11 поставляется с проектом. Его SHA-256
взята из официальной метаинформации PyPI; файл проверяется перед установкой.
Другие платформы используют pip с системным хранилищем доверенных сертификатов.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import sysconfig
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WHEELS = ROOT / "vendor" / "wheels"
VERSION = "2.6.1"
FILENAME = "pygame-2.6.1-cp311-cp311-win_amd64.whl"


def matching_wheel(version=None, platform_tag=None, implementation=None):
    version = tuple(version or sys.version_info[:2])
    platform_tag = platform_tag or sysconfig.get_platform()
    implementation = implementation or sys.implementation.name
    if version == (3, 11) and platform_tag == "win-amd64" and implementation == "cpython":
        return WHEELS / FILENAME
    return None


def verify_wheel(path, manifest_path=None):
    """Повреждённый пакет не устанавливаем и не заменяем ожидаемую сумму."""
    manifest_path = Path(manifest_path) if manifest_path else WHEELS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package") != "pygame" or manifest.get("version") != VERSION:
        raise ValueError("Invalid package manifest")
    entry = next((item for item in manifest["wheels"] if item["filename"] == path.name), None)
    if entry is None:
        raise ValueError("Wheel not listed in manifest")
    data = path.read_bytes()
    if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError("Pygame wheel checksum mismatch. Download the complete archive again.")
    return entry["sha256"]


def install(offline_only=False):
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.")
        return 2
    try:
        installed = importlib.metadata.version("pygame")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    if installed == VERSION:
        print(f"Pygame {VERSION} is already installed.")
        return 0
    local = matching_wheel()
    try:
        if local is not None:
            checksum = verify_wheel(local)
            print(f"Installing bundled Pygame {VERSION}; SHA-256 verified. No network needed.", flush=True)
            # Закрываем файл до pip: в Windows открытый NamedTemporaryFile
            # нельзя безопасно перечитать из другого процесса.
            requirement = f"{local.as_uri()} --hash=sha256:{checksum}\n"
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as file:
                file.write(requirement)
                requirements_path = Path(file.name)
            try:
                command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                           "--no-index", "--no-deps", "--no-cache-dir", "--require-hashes",
                           "-r", str(requirements_path)]
                return subprocess.run(command, cwd=ROOT).returncode
            finally:
                requirements_path.unlink(missing_ok=True)
        if offline_only:
            print("Bundled offline package requires Windows x64 and CPython 3.11.")
            return 2
        print("Installing via HTTPS using OS certificate trust (TLS verification stays enabled).", flush=True)
        command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                   "--use-feature=truststore", "-r", str(ROOT / "requirements.txt")]
        return subprocess.run(command, cwd=ROOT).returncode
    except (OSError, ValueError, KeyError) as error:
        print(f"Dependency setup failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Не обращаться к сети")
    sys.exit(install(parser.parse_args().offline))
