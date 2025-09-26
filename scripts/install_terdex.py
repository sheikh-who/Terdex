"""Single-file installer for the Terdex CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def install(package_path: Path, *, extras: list[str]) -> int:
    base = str(package_path)
    if extras:
        extra_str = ",".join(extras)
        base = f"{base}[{extra_str}]"
    cmd = [sys.executable, "-m", "pip", "install", base]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the Terdex CLI")
    parser.add_argument(
        "--with-ollama",
        action="store_true",
        help="Install the Ollama integration extras",
    )
    parser.add_argument(
        "--with-color",
        action="store_true",
        help="Install colorized confetti support via colorama",
    )
    args = parser.parse_args(argv)

    extras: list[str] = []
    if args.with_ollama:
        extras.append("ollama")
    if args.with_color:
        extras.append("color")

    package_path = Path(__file__).resolve().parent.parent
    return install(package_path, extras=extras)


if __name__ == "__main__":
    raise SystemExit(main())

