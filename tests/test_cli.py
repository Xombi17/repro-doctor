import contextlib
import io
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

from repro_doctor.cli import build_parser, main
from repro_doctor.errors import AgentTimeoutError
from repro_doctor.models import CommandResult, FailureInfo, VerificationResult


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
                code = main(
                    [
                        str(source),
                        "--mode",
                        "local",
                        "--skip-verification",
                        "--output-dir",
                        str(output),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("Patch:", stdout.getvalue())
            self.assertTrue((output / "repro-doctor.patch").exists())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        str(root / "missing"),
                        "--output-dir",
                        str(root / "missing-output"),
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("input path does not exist", stderr.getvalue())

    def test_agent_is_the_explicit_default_and_help_exposes_modes_and_timeout(self):
        args = build_parser().parse_args(["repository"])

        self.assertEqual(args.mode, "agent")
        self.assertEqual(args.agent_timeout, 120.0)
        self.assertFalse(args.skip_verification)
        help_text = build_parser().format_help()
        self.assertIn("--mode {agent,local}", help_text)
        self.assertIn("--agent-timeout AGENT_TIMEOUT", help_text)
        self.assertIn("--skip-verification", help_text)

    def test_agent_timeout_is_forwarded_and_reported(self):
        stderr = io.StringIO()
        with patch(
            "repro_doctor.cli.process_repository",
            side_effect=AgentTimeoutError("stack-detector timed out after 0.25s"),
        ) as process:
            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "repository",
                        "--mode",
                        "agent",
                        "--agent-timeout",
                        "0.25",
                    ]
                )

        self.assertEqual(code, 2)
        self.assertIn("timed out", stderr.getvalue())
        self.assertEqual(process.call_args.kwargs["mode"], "agent")
        self.assertEqual(process.call_args.kwargs["agent_timeout"], 0.25)
        self.assertTrue(process.call_args.kwargs["verify"])

    def test_verification_failure_returns_nonzero_after_outputs_exist(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            patch_path = root / "repro-doctor.patch"
            report_path = root / "repro-doctor-report.md"
            patch_path.write_bytes(b"generated patch")
            report_path.write_text("generated report", encoding="utf-8")
            verification = VerificationResult(
                status="failed",
                image_tag="test-image",
                build_result=CommandResult(("docker", "build"), 1, stderr="bad build"),
                failure=FailureInfo(
                    stage="build",
                    classification="build",
                    command=("docker", "build"),
                    output="bad build",
                ),
            )
            fake_result = SimpleNamespace(
                profile=SimpleNamespace(stack="python", confidence="high"),
                patch_path=patch_path,
                report_path=report_path,
                changed_files=("Dockerfile",),
                verification=verification,
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("repro_doctor.cli.process_repository", return_value=fake_result):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = main(["repository"])

            self.assertEqual(code, 1)
            self.assertTrue(patch_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn("Verification: failed", stdout.getvalue())
            self.assertIn("Verification failure: build/build", stderr.getvalue())
