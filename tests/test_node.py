import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from repro_doctor.artifacts import generate_artifacts
from repro_doctor.detect import detect_node, detect_repository
from repro_doctor.errors import UnsupportedRepositoryError
from repro_doctor.pipeline import process_repository


FIXTURES = Path(__file__).parent / "fixtures"


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class NodeDetectionTests(unittest.TestCase):
    def test_detects_npm_fixture_and_preserves_existing_lockfile(self):
        profile = detect_node(FIXTURES / "node-npm")

        self.assertEqual(profile.stack, "node")
        self.assertEqual(profile.package_manager, "npm")
        self.assertEqual(profile.package_manager_source, "package.json packageManager")
        self.assertEqual(profile.package_manager_spec, "npm@10.8.2")
        self.assertEqual(profile.lockfile, "package-lock.json")
        self.assertEqual(profile.runtime, "20.11.1")
        self.assertEqual(profile.runtime_source, ".nvmrc")
        self.assertEqual(profile.test_command, "npm test")
        self.assertFalse(profile.typescript)

    def test_detects_typescript_fixture_with_engine_and_no_lockfile(self):
        profile = detect_node(FIXTURES / "node-typescript")

        self.assertEqual(profile.package_manager, "npm")
        self.assertEqual(profile.package_manager_source, "npm default")
        self.assertIsNone(profile.package_manager_spec)
        self.assertIsNone(profile.lockfile)
        self.assertEqual(profile.runtime, "18.17.0")
        self.assertEqual(profile.runtime_source, "package.json engines.node")
        self.assertEqual(profile.test_command, "npm run test:ci")
        self.assertTrue(profile.typescript)
        self.assertIn("tests/index.test.ts", profile.test_files)
        self.assertIn("tsconfig.json", profile.signals)

    def test_selects_pnpm_and_yarn_from_lockfiles(self):
        for manager, lockfile in (("pnpm", "pnpm-lock.yaml"), ("yarn", "yarn.lock")):
            with self.subTest(manager=manager):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    (root / "package.json").write_text(
                        '{"name":"manager-fixture","scripts":{"test":"node --test"}}\n',
                        encoding="utf-8",
                    )
                    (root / lockfile).write_text("lockfile\n", encoding="utf-8")
                    profile = detect_node(root)

                    self.assertEqual(profile.package_manager, manager)
                    self.assertEqual(profile.lockfile, lockfile)
                    self.assertEqual(profile.test_command, f"{manager} test")

    def test_explicit_package_manager_wins_over_lockfile_signal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text(
                '{"name":"explicit-fixture","packageManager":"pnpm@9.15.0",'
                '"scripts":{"test:ci":"node --test"}}\n',
                encoding="utf-8",
            )
            (root / "pnpm-lock.yaml").write_text("lockfile\n", encoding="utf-8")

            profile = detect_repository(root)

            self.assertEqual(profile.package_manager, "pnpm")
            self.assertEqual(profile.package_manager_spec, "pnpm@9.15.0")
            self.assertEqual(profile.test_command, "pnpm run test:ci")

    def test_uses_node_22_when_runtime_is_undeclared(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text(
                '{"name":"default-runtime","scripts":{"test":"node --test"}}\n',
                encoding="utf-8",
            )

            profile = detect_node(root)

            self.assertEqual(profile.runtime, "22")
            self.assertEqual(profile.runtime_source, "phase-2 default")

    def test_rejects_conflicting_lockfile_signals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text(
                '{"name":"ambiguous-fixture","scripts":{"test":"node --test"}}\n',
                encoding="utf-8",
            )
            (root / "package-lock.json").write_text("{}\n", encoding="utf-8")
            (root / "yarn.lock").write_text("lockfile\n", encoding="utf-8")

            with self.assertRaises(UnsupportedRepositoryError) as error:
                detect_node(root)

            self.assertIn("ambiguous package manager", str(error.exception))


class NodeArtifactTests(unittest.TestCase):
    def test_generates_npm_artifacts_for_existing_lockfile(self):
        root = FIXTURES / "node-npm"
        profile = detect_node(root)

        artifacts = {artifact.path: artifact.content for artifact in generate_artifacts(root, profile)}

        self.assertIn("FROM node:20.11.1-slim", artifacts["Dockerfile"])
        self.assertIn("RUN npm ci", artifacts["Dockerfile"])
        self.assertNotIn("dependencies.repro-doctor.md", artifacts)
        self.assertNotIn(".nvmrc", artifacts)
        self.assertIn("npm test", artifacts["Makefile"])
        self.assertIn("Package manager: npm", artifacts["README.repro-doctor.md"])

    def test_generates_typescript_artifacts_for_no_lockfile(self):
        root = FIXTURES / "node-typescript"
        profile = detect_node(root)

        artifacts = {artifact.path: artifact.content for artifact in generate_artifacts(root, profile)}

        self.assertIn("FROM node:18.17.0-slim", artifacts["Dockerfile"])
        self.assertIn("RUN npm install", artifacts["Dockerfile"])
        self.assertIn(".nvmrc", artifacts)
        self.assertEqual(artifacts[".nvmrc"], "18.17.0\n")
        self.assertIn("dependencies.repro-doctor.md", artifacts)
        self.assertIn("npm run test:ci", artifacts["Makefile"])
        self.assertIn("TypeScript", artifacts["README.repro-doctor.md"])


class NodePipelineTests(unittest.TestCase):
    def test_pipeline_keeps_fixture_unchanged_and_emits_applyable_patch(self):
        source = FIXTURES / "node-typescript"
        before_digest = _tree_digest(source)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            result = process_repository(str(source), output)

            self.assertEqual(before_digest, _tree_digest(source))
            self.assertEqual(result.profile.stack, "node")
            self.assertIn("Dockerfile", result.changed_files)
            self.assertIn(".nvmrc", result.changed_files)
            self.assertIn("dependencies.repro-doctor.md", result.changed_files)
            self.assertIn("Stack: Node.js / TypeScript", result.report_path.read_text())

            applied = Path(temporary) / "applied"
            shutil.copytree(source, applied)
            checked = shutil.which("git")
            self.assertIsNotNone(checked)

            check = subprocess.run(
                [checked, "apply", "--check", str(result.patch_path)],
                cwd=applied,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
