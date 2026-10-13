"""Собрать переносимый исходный проект с ресурсами, без кешей и сохранений."""
from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "artifacts"}


def build(destination):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if not path.is_file() or any(part in EXCLUDED for part in relative.parts):
                continue
            if path.suffix in {".pyc", ".zip"} or ".sqlite3" in path.name or path.name == "settings.json":
                continue
            archive.write(path, Path("StarFrontier") / relative)
            count += 1
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None, "Ошибка CRC в архиве"
    print(f"{destination}: {count} файлов, {destination.stat().st_size:,} байт")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", type=Path,
                        default=ROOT.parent / "artifacts" / "star-frontier.zip")
    build(parser.parse_args().destination)
