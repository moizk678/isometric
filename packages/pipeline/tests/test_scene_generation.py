import contextlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from isometric_pipeline.scene import generate

TSC = generate.PACKAGE_DIR / "node_modules" / ".bin" / "tsc"


def _copy_package(generated_dir: Path, target: Path) -> None:
    for relative in generate.GENERATED_FILES:
        (target / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated_dir / relative, target / relative)
    shutil.copytree(
        generate.PACKAGE_DIR / generate.VALID_FIXTURES,
        target / generate.VALID_FIXTURES,
    )


class SceneGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="scene-generation-")
        cls.generated = Path(cls._tmp.name) / "generated"
        generate.generate_into(
            cls.generated, generate.PACKAGE_DIR / generate.VALID_FIXTURES
        )

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _stale_copy(self, relative: Path, edit) -> Path:
        target = Path(tempfile.mkdtemp(dir=self._tmp.name))
        _copy_package(self.generated, target)
        path = target / relative
        path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")
        return target

    def test_committed_files_are_current(self):
        self.assertEqual(generate.stale_files(generate.PACKAGE_DIR, self.generated), {})

    def test_schema_is_sorted_and_deterministic(self):
        text = generate.schema_text()
        self.assertEqual(text, generate.schema_text())
        reparsed = json.dumps(
            json.loads(text), sort_keys=True, indent=2, ensure_ascii=False
        )
        self.assertEqual(text, reparsed + "\n")

    def test_every_valid_fixture_is_exported(self):
        text = (self.generated / generate.FIXTURES_FILE).read_text(encoding="utf-8")
        exported = re.findall(r"^export const (\w+): DrawingScene = \{$", text, re.M)
        stems = sorted(
            path.stem
            for path in (generate.PACKAGE_DIR / generate.VALID_FIXTURES).glob("*.json")
        )
        self.assertEqual(exported, [generate._camel_name(stem) for stem in stems])
        self.assertIn("connectedRoute", exported)

    def test_fixture_failing_invariants_is_not_exported(self):
        fixtures = Path(tempfile.mkdtemp(dir=self._tmp.name))
        source = generate.PACKAGE_DIR / generate.VALID_FIXTURES / "connected-route.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        pipe = next(obj for obj in data["objects"] if obj["type"] == "pipe_segment")
        pipe["primitive"]["start"]["x"] += 25.0
        (fixtures / "connected-route.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(generate.GenerationError, "PIPE_ENDPOINT_MISMATCH"):
            generate.fixtures_text(fixtures)

    def test_stale_copy_is_detected(self):
        for relative in generate.GENERATED_FILES:
            with self.subTest(file=str(relative)):
                target = self._stale_copy(relative, lambda text: text + "// stale\n")
                self.assertEqual(
                    list(generate.stale_files(target, self.generated)), [relative]
                )

    def test_missing_file_is_detected(self):
        target = Path(tempfile.mkdtemp(dir=self._tmp.name))
        _copy_package(self.generated, target)
        (target / generate.TYPES_FILE).unlink()
        self.assertEqual(
            list(generate.stale_files(target, self.generated)), [generate.TYPES_FILE]
        )

    def test_check_exits_nonzero_for_stale_package(self):
        target = self._stale_copy(
            generate.TYPES_FILE,
            lambda text: text.replace('"pipe_segment"', '"pipe"', 1),
        )
        shutil.copyfile(generate.PACKAGE_DIR / "package.json", target / "package.json")
        stderr = io.StringIO()
        with (
            mock.patch.object(generate, "PACKAGE_DIR", target),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(generate.main(["--check"]), 1)
        self.assertIn(str(generate.TYPES_FILE), stderr.getvalue())
        self.assertIn('-  type: "pipe";', stderr.getvalue())

    @unittest.skipUnless(TSC.exists(), "scene-schema node_modules not installed")
    def test_generated_types_reject_wrong_discriminator(self):
        fixture = json.loads(
            (
                generate.PACKAGE_DIR / generate.VALID_FIXTURES / "valve-inline.json"
            ).read_text(encoding="utf-8")
        )
        junction = next(obj for obj in fixture["objects"] if obj["type"] == "junction")
        types_module = json.dumps(str(self.generated / "src" / "drawing-scene.js"))
        cases = {
            "good": junction,
            "bad_wrong_type": {**junction, "type": "pipe_segment"},
            "bad_unknown_type": {**junction, "type": "valve"},
            "bad_extra_field": {**junction, "confidence": 1},
        }
        scratch = Path(tempfile.mkdtemp(dir=self._tmp.name))
        (scratch / "package.json").write_text('{"type": "module"}\n')
        (scratch / "tsconfig.json").write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "strict": True,
                        "noEmit": True,
                        "module": "NodeNext",
                        "moduleResolution": "NodeNext",
                        "target": "ES2022",
                        "skipLibCheck": True,
                    },
                    "include": ["*.ts"],
                }
            )
        )
        for name, value in cases.items():
            (scratch / f"{name}.ts").write_text(
                f"import type {{DrawingScene}} from {types_module};\n"
                f'export const value: DrawingScene["objects"][number] = '
                f"{json.dumps(value)};\n"
            )
        widened = (
            f"import type {{DrawingScene}} from {types_module};\n"
            'const kind: string = "junction";\n'
            f'export const value: DrawingScene["objects"][number] = '
            f"{{...{json.dumps(junction)}, type: kind}};\n"
        )
        (scratch / "bad_widened_type.ts").write_text(widened)

        result = subprocess.run(
            [str(TSC), "-p", "tsconfig.json"],
            cwd=scratch,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        failed = set(re.findall(r"^(\w+)\.ts\(\d+,\d+\): error TS", output, re.M))
        self.assertEqual(
            failed,
            {
                "bad_wrong_type",
                "bad_unknown_type",
                "bad_extra_field",
                "bad_widened_type",
            },
            output,
        )


if __name__ == "__main__":
    unittest.main()
