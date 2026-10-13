"""Проверка выбора Windows wheel и безопасной установки без запуска DLL в Linux."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools import install_dependencies as installer


class InstallerTests(unittest.TestCase):
    def test_offline_wheel_only_matches_cpython311_windows64(self):
        self.assertEqual(installer.matching_wheel((3, 11), "win-amd64", "cpython").name,
                         installer.FILENAME)
        for version, platform, impl in (((3, 12), "win-amd64", "cpython"),
                                        ((3, 11), "win32", "cpython"),
                                        ((3, 11), "linux-x86_64", "cpython"),
                                        ((3, 11), "win-amd64", "pypy")):
            self.assertIsNone(installer.matching_wheel(version, platform, impl))

    def test_shipped_wheel_matches_official_pypi_manifest(self):
        checksum = installer.verify_wheel(installer.WHEELS / installer.FILENAME)
        self.assertEqual(checksum, "91476902426facd4bb0dad4dc3b2573bc82c95c71b135e0daaea072ed528d299")

    def test_corrupt_wheel_stops_install_without_online_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            wheel = Path(folder) / installer.FILENAME
            wheel.write_bytes(b"bad wheel")
            manifest = Path(folder) / "manifest.json"
            manifest.write_text(json.dumps({"package": "pygame", "version": "2.6.1", "wheels": [{
                "filename": wheel.name, "size": 9, "sha256": hashlib.sha256(b"real file").hexdigest()}]}))
            with patch.object(installer, "WHEELS", Path(folder)), \
                    patch.object(installer, "matching_wheel", return_value=wheel), \
                    patch.object(importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError), \
                    patch.object(subprocess, "run") as run:
                self.assertEqual(installer.install(), 2)
                run.assert_not_called()

    def test_offline_command_enforces_hash_and_removes_temporary_requirements(self):
        captured = {}
        def run(command, **kwargs):
            self.assertIn("--no-index", command)
            self.assertIn("--no-deps", command)
            self.assertIn("--no-cache-dir", command)
            self.assertIn("--require-hashes", command)
            self.assertNotIn("--trusted-host", command)
            path = Path(command[command.index("-r") + 1])
            text = path.read_text()
            self.assertIn(installer.FILENAME, text)
            self.assertIn("--hash=sha256:914769", text)
            self.assertTrue(text.startswith("file:"))
            captured["path"] = path
            return subprocess.CompletedProcess(command, 0)
        with patch.object(installer, "matching_wheel", return_value=installer.WHEELS / installer.FILENAME), \
                patch.object(importlib.metadata, "version", return_value="2.1.2"), \
                patch.object(subprocess, "run", side_effect=run):
            self.assertEqual(installer.install(), 0)
        self.assertFalse(captured["path"].exists())

    def test_matching_installed_version_skips_pip(self):
        with patch.object(importlib.metadata, "version", return_value="2.6.1"), \
                patch.object(subprocess, "run") as run:
            self.assertEqual(installer.install(), 0)
            run.assert_not_called()

    def test_offline_flag_never_falls_back_to_network(self):
        with patch.object(installer, "matching_wheel", return_value=None), \
                patch.object(importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError), \
                patch.object(subprocess, "run") as run:
            self.assertEqual(installer.install(offline_only=True), 2)
            run.assert_not_called()

    def test_other_runtime_uses_https_with_os_trust_and_keeps_pip_status(self):
        with patch.object(installer, "matching_wheel", return_value=None), \
                patch.object(importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError), \
                patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
            self.assertEqual(installer.install(), 1)
            command = run.call_args.args[0]
            self.assertIn("--use-feature=truststore", command)
            self.assertNotIn("--trusted-host", command)


if __name__ == "__main__":
    unittest.main()
