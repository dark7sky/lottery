from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or refresh the local DH Lottery Python runtime."
    )
    parser.add_argument(
        "--repo-root",
        default=str(repo_root_from_here()),
        help="Repository root that contains dhlottery.py and requirements.txt.",
    )
    parser.add_argument(
        "--venv-dir",
        help="Optional virtualenv directory. Defaults to <repo>/venv.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter to use for creating the virtualenv.",
    )
    parser.add_argument(
        "--skip-playwright-install",
        action="store_true",
        help="Skip 'python -m playwright install chromium'.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    venv_dir = Path(args.venv_dir).resolve() if args.venv_dir else repo_root / "venv"
    venv_python = resolve_venv_python(venv_dir)
    requirements = repo_root / "requirements.txt"

    if not requirements.exists():
        raise RuntimeError(f"requirements.txt not found under: {repo_root}")

    if not venv_python.exists():
        run([args.python, "-m", "venv", str(venv_dir)], cwd=repo_root)

    run([str(venv_python), "-m", "pip", "install", "-r", str(requirements)], cwd=repo_root)

    if not args.skip_playwright_install:
        run([str(venv_python), "-m", "playwright", "install", "chromium"], cwd=repo_root)

    print(f"Runtime ready: {venv_python}")


if __name__ == "__main__":
    main()
