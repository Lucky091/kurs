"""Настройки и SQLite в пользовательской папке, независимо от рабочей папки."""

import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


DEFAULT_SETTINGS = {
    "music_volume": .3,
    "effects_volume": .6,
    "camera_shake": True,
    "particles": 1.0,
    "fullscreen": False,
}


def data_directory() -> Path:
    """Папка доступна обычному пользователю, права администратора не нужны."""
    override = os.environ.get("STAR_FRONTIER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    return base / "StarFrontier"


def sanitized_settings(settings: object) -> dict:
    result = DEFAULT_SETTINGS.copy()
    if not isinstance(settings, dict):
        return result
    for key in ("music_volume", "effects_volume", "particles"):
        value = settings.get(key)
        # bool является подклассом int, но True вместо громкости — повреждение.
        if type(value) in (int, float) and math.isfinite(value):
            result[key] = max(0.0, min(1.0, float(value)))
    for key in ("camera_shake", "fullscreen"):
        if type(settings.get(key)) is bool:
            result[key] = settings[key]
    return result


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else data_directory() / "settings.json"

    def load(self) -> dict:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                return sanitized_settings(json.load(file))
        except (OSError, ValueError, UnicodeError):
            return DEFAULT_SETTINGS.copy()

    def save(self, settings: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Замена готового файла атомарна: прерывание записи не портит настройки.
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent,
                                             suffix=".tmp", delete=False) as file:
                temporary_path = Path(file.name)
                json.dump(sanitized_settings(settings), file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


class LeaderboardDB:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else data_directory() / "leaderboard.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                score INTEGER NOT NULL CHECK(score >= 0),
                wave INTEGER NOT NULL CHECK(wave >= 1),
                played_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        self.connection.commit()

    def save_score(self, run_id: str, name: str, score: int, wave: int) -> bool:
        cleaned_name = " ".join(str(name).split())[:24] or "Пилот"
        # UNIQUE гарантирует идемпотентность даже при повторном нажатии кнопки.
        with self.connection:
            cursor = self.connection.execute(
                "INSERT OR IGNORE INTO scores (run_id, name, score, wave) VALUES (?, ?, ?, ?)",
                (str(run_id), cleaned_name, max(0, int(score)), max(1, int(wave))),
            )
        return cursor.rowcount == 1

    def top_scores(self, limit: int = 10) -> list[dict]:
        limit = max(0, min(1000, int(limit)))
        rows = self.connection.execute(
            "SELECT name, score, wave, played_at FROM scores "
            "ORDER BY score DESC, wave DESC, id ASC LIMIT ?", (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()
