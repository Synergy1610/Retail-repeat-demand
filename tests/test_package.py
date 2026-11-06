"""Packaging tests: flat allowlist, determinism, and checksum coverage."""

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

import support


def load_packager():
    path = support.ROOT / "scripts" / "package.py"
    spec = importlib.util.spec_from_file_location("portfolio_packager", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packager = load_packager()

    def test_pre_twist_archive_is_flat_and_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.packager.build(
                self.packager.MODELS["pre-twist"], Path(tmp), force=False
            )
            self.assertEqual(
                manifest["files"],
                ["features.py", "solution.py", "starter_model.json"],
            )
            with zipfile.ZipFile(Path(tmp) / "Team-99_v2.1_pre-twist.zip") as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"features.py", "solution.py", "starter_model.json"},
                )
                self.assertIsNone(archive.testzip())

    def test_adapted_archive_includes_the_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.packager.build(
                self.packager.MODELS["adapted"], Path(tmp), force=False
            )
            self.assertIn("feed_adapter.py", manifest["files"])
            with zipfile.ZipFile(Path(tmp) / "Team-99_v2.1_adapted.zip") as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        "feed_adapter.py",
                        "features.py",
                        "solution.py",
                        "starter_model.json",
                    },
                )

    def test_archives_are_deterministic(self):
        hashes = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                manifest = self.packager.build(
                    self.packager.MODELS["pre-twist"], Path(tmp), force=False
                )
                hashes.append(manifest["sha256"])
        self.assertEqual(hashes[0], hashes[1])

    def test_existing_archive_requires_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.packager.build(
                self.packager.MODELS["pre-twist"], Path(tmp), force=False
            )
            with self.assertRaises(ValueError):
                self.packager.build(
                    self.packager.MODELS["pre-twist"], Path(tmp), force=False
                )

    def test_unexpected_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "model"
            source.mkdir()
            for name in ("solution.py", "features.py", "starter_model.json"):
                (source / name).write_text("", encoding="utf-8")
            (source / "notes.txt").write_text("extra", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.packager.collect(
                    source, {"solution.py", "features.py", "starter_model.json"}
                )

    def test_committed_archives_match_sources(self):
        dist = support.ROOT / "dist"
        checksums = dist / "SHA256SUMS"
        if not checksums.exists():
            self.skipTest("dist/SHA256SUMS has not been built yet")

        expected = {}
        for line in checksums.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            expected[name] = digest

        with tempfile.TemporaryDirectory() as tmp:
            for key, name in (
                ("pre-twist", "Team-99_v2.1_pre-twist.zip"),
                ("adapted", "Team-99_v2.1_adapted.zip"),
            ):
                manifest = self.packager.build(
                    self.packager.MODELS[key], Path(tmp), force=False
                )
                self.assertEqual(manifest["sha256"], expected.get(name))


if __name__ == "__main__":
    unittest.main()
