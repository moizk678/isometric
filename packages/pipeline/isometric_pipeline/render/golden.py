"""Regenerate or check the golden SVG exports and PNG previews.

Usage (from the repository root)::

    PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden
    PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden \
        --check

The default mode renders every fixture in ``packages/scene-schema/fixtures/valid``
into ``packages/pipeline/tests/golden/render/{stem}.svg`` and ``{stem}.png``.
``--check`` renders into a temporary directory and exits non-zero if any
committed golden differs.

SVG goldens must match byte for byte. PNG goldens are compared by pixels:
the dimensions must be identical and every RGBA channel of every pixel must be
within ``PNG_CHANNEL_TOLERANCE``, because resvg's anti-aliasing can differ by a
step or two between macOS and Linux builds. The default mode keeps a committed
PNG that is within tolerance so regenerating on another platform causes no churn.
"""

from __future__ import annotations

import argparse
import difflib
import io
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

from ..scene import SceneValidationError, load_scene
from .errors import RenderError
from .preview import rasterize_preview
from .svg import render_svg
from .symbols import load_symbol_library
from .versions import STYLE_PROFILE_VERSION, SYMBOL_LIBRARY_VERSION

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = REPO_ROOT / "packages" / "scene-schema" / "fixtures" / "valid"
GOLDEN_DIR = REPO_ROOT / "packages" / "pipeline" / "tests" / "golden" / "render"
GOLDEN_SUFFIXES = (".svg", ".png")

PNG_CHANNEL_TOLERANCE = 2
"""Largest allowed absolute difference in any RGBA channel of any pixel."""


class GoldenError(RuntimeError):
    """A fixture could not be rendered."""


@dataclass(frozen=True)
class Golden:
    svg: bytes
    png: bytes


def render_fixture(path: Path) -> Golden:
    """Render one scene fixture to its export SVG and scale-1 preview PNG."""
    library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
    try:
        scene = load_scene(path.read_text(encoding="utf-8"), catalog=library)
        result = render_svg(scene, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION)
        preview = rasterize_preview(result.svg, scale=1.0)
    except (SceneValidationError, RenderError) as exc:
        raise GoldenError(f"{path.name}: {exc}") from None
    return Golden(svg=result.svg, png=preview.png)


def fixture_paths(fixtures_dir: Path = FIXTURES_DIR) -> list[Path]:
    paths = sorted(fixtures_dir.glob("*.json"))
    if not paths:
        raise GoldenError(f"no valid fixtures in {fixtures_dir}")
    return paths


def generate_into(out_dir: Path, fixtures_dir: Path = FIXTURES_DIR) -> None:
    """Write every golden under ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in fixture_paths(fixtures_dir):
        golden = render_fixture(path)
        (out_dir / f"{path.stem}.svg").write_bytes(golden.svg)
        (out_dir / f"{path.stem}.png").write_bytes(golden.png)


def png_difference(committed: bytes, generated: bytes) -> str | None:
    """Describe why two PNGs differ beyond the tolerance, or None if they match."""
    try:
        with Image.open(io.BytesIO(committed)) as image:
            actual = image.convert("RGBA")
        with Image.open(io.BytesIO(generated)) as image:
            expected = image.convert("RGBA")
    except OSError as exc:
        return f"cannot decode PNG: {exc}"
    if actual.size != expected.size:
        return f"size {actual.size} != {expected.size}"
    extrema = ImageChops.difference(actual, expected).getextrema()
    delta = max(high for _, high in extrema)
    if delta > PNG_CHANNEL_TOLERANCE:
        return f"max channel delta {delta} > tolerance {PNG_CHANNEL_TOLERANCE}"
    return None


def _golden_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.suffix in GOLDEN_SUFFIXES
    }


def stale_files(committed_dir: Path, generated_dir: Path) -> dict[str, str]:
    """Map each differing golden file name to a description of the difference."""
    stale: dict[str, str] = {}
    expected_names = _golden_names(generated_dir)
    for name in sorted(_golden_names(committed_dir) - expected_names):
        stale[name] = f"{name}: no fixture renders to this golden\n"
    for name in sorted(expected_names):
        committed_path = committed_dir / name
        if not committed_path.is_file():
            stale[name] = f"{name}: missing\n"
            continue
        expected = (generated_dir / name).read_bytes()
        actual = committed_path.read_bytes()
        if name.endswith(".png"):
            problem = png_difference(actual, expected)
            if problem is not None:
                stale[name] = f"{name}: {problem}\n"
        elif actual != expected:
            stale[name] = (
                "".join(
                    difflib.unified_diff(
                        actual.decode("utf-8", "replace").splitlines(keepends=True),
                        expected.decode("utf-8", "replace").splitlines(keepends=True),
                        fromfile=f"committed/{name}",
                        tofile=f"generated/{name}",
                    )
                )
                or f"{name}: bytes differ\n"
            )
    return stale


def write(golden_dir: Path = GOLDEN_DIR, fixtures_dir: Path = FIXTURES_DIR) -> None:
    """Regenerate the committed goldens in place and delete orphaned ones."""
    with tempfile.TemporaryDirectory(prefix="render-golden-") as tmp:
        generated_dir = Path(tmp)
        generate_into(generated_dir, fixtures_dir)
        golden_dir.mkdir(parents=True, exist_ok=True)
        expected_names = _golden_names(generated_dir)
        for name in _golden_names(golden_dir) - expected_names:
            (golden_dir / name).unlink()
        for name in sorted(expected_names):
            generated = (generated_dir / name).read_bytes()
            target = golden_dir / name
            if (
                name.endswith(".png")
                and target.is_file()
                and png_difference(target.read_bytes(), generated) is None
            ):
                continue
            target.write_bytes(generated)


def check(
    golden_dir: Path = GOLDEN_DIR, fixtures_dir: Path = FIXTURES_DIR
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="render-golden-") as tmp:
        generated_dir = Path(tmp)
        generate_into(generated_dir, fixtures_dir)
        return stale_files(golden_dir, generated_dir)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m isometric_pipeline.render.golden", description=__doc__
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed golden SVG or PNG files are out of date",
    )
    args = parser.parse_args(argv)
    try:
        if not args.check:
            write()
            return 0
        stale = check()
    except GoldenError as exc:
        print(f"render golden generation failed: {exc}", file=sys.stderr)
        return 2
    if not stale:
        return 0
    for diff in stale.values():
        sys.stderr.write(diff if diff.endswith("\n") else diff + "\n")
    names = ", ".join(stale)
    print(
        f"stale render goldens: {names}\n"
        "run: PYTHONPATH=packages/pipeline .venv/bin/python "
        "-m isometric_pipeline.render.golden",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
