import tempfile
import unittest
from pathlib import Path

from repro_doctor.errors import InputError
from repro_doctor.inputs import ensure_output_is_safe, isolated_snapshot


class InputTests(unittest.TestCase):
    def test_local_snapshot_isolated_and_git_metadata_is_omitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "app.py").write_text("print('before')\n", encoding="utf-8")
            (source / ".git").mkdir()
            (source / ".git" / "config").write_text("private\n", encoding="utf-8")

            with isolated_snapshot(str(source)) as snapshot:
                self.assertEqual(snapshot.kind, "local")
                self.assertEqual((snapshot.root / "app.py").read_text(), "print('before')\n")
                self.assertFalse((snapshot.root / ".git").exists())
                (snapshot.root / "app.py").write_text("changed\n", encoding="utf-8")

            self.assertEqual((source / "app.py").read_text(), "print('before')\n")

    def test_github_url_uses_replaceable_clone_runner(self):
        calls = []

        def fake_clone(url, destination):
            calls.append((url, destination))
            destination.mkdir()
            (destination / "main.py").write_text("print('clone')\n", encoding="utf-8")

        with isolated_snapshot(
            "https://github.com/example/project.git",
            clone_runner=fake_clone,
        ) as snapshot:
            self.assertEqual(snapshot.kind, "github")
            self.assertEqual((snapshot.root / "main.py").read_text(), "print('clone')\n")
        self.assertEqual(calls[0][0], "https://github.com/example/project.git")

    def test_rejects_non_github_url_and_output_inside_source(self):
        with self.assertRaises(InputError) as error:
            with isolated_snapshot("https://gitlab.com/example/project.git"):
                pass
        self.assertIn("GitHub HTTPS", str(error.exception))

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            with self.assertRaises(InputError) as error:
                ensure_output_is_safe(str(source), source / "output")
            self.assertIn("outside", str(error.exception))
