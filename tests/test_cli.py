import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from repro_doctor.cli import main


class CliTests(unittest.TestCase):
    def test_success_and_actionable_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
            output = root / "output"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main([str(source), "--output-dir", str(output)])
            self.assertEqual(code, 0)
            self.assertIn("Patch:", stdout.getvalue())
            self.assertTrue((output / "repro-doctor.patch").exists())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([str(root / "missing")])
            self.assertEqual(code, 2)
            self.assertIn("input path does not exist", stderr.getvalue())
