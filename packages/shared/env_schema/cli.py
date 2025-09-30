"""Command-line helpers to validate environment profile documents."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Sequence

from . import ValidationError, validate_environment_profile_file


def _iter_candidate_paths(inputs: Sequence[str] | None) -> Iterable[Path]:
    if not inputs:
        env_dir = Path("environments")
        if not env_dir.exists():
            return []
        return sorted(
            path
            for pattern in ("*.yaml", "*.yml", "*.json")
            for path in env_dir.glob(pattern)
            if path.is_file()
        )
    resolved: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            resolved.extend(
                sorted(
                    candidate
                    for pattern in ("*.yaml", "*.yml", "*.json")
                    for candidate in path.rglob(pattern)
                    if candidate.is_file()
                )
            )
        else:
            resolved.append(path)
    return resolved


def run_validation(paths: Sequence[str] | None = None) -> int:
    """Validate the provided *paths* and return an exit code."""
    candidates = list(_iter_candidate_paths(paths))
    if not candidates:
        print("No environment profiles found.", file=sys.stderr)
        return 1

    ok = True
    for path in candidates:
        try:
            validate_environment_profile_file(path)
        except ValidationError as exc:
            ok = False
            print(f"✗ {path}: {exc.message}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"✗ {path}: unexpected error: {exc}", file=sys.stderr)
        else:
            print(f"✓ {path}")
    return 0 if ok else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate DevOps agent environment profile documents.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help=(
            "Specific files or directories to validate. "
            "Defaults to scanning the environments/ directory."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_validation(args.paths)


if __name__ == "__main__":  # pragma: no cover - direct execution path
    sys.exit(main())
