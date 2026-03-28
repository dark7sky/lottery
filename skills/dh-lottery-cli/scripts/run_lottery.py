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


def runtime_is_ready(python_executable: Path) -> bool:
    if not python_executable.exists():
        return False

    result = subprocess.run(
        [
            str(python_executable),
            "-c",
            "import dotenv, playwright; print('ok')",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def ensure_runtime(repo_root: Path, venv_dir: Path) -> Path:
    venv_python = resolve_venv_python(venv_dir)
    if runtime_is_ready(venv_python):
        return venv_python

    ensure_script = Path(__file__).resolve().with_name("ensure_runtime.py")
    subprocess.run(
        [
            sys.executable,
            str(ensure_script),
            "--repo-root",
            str(repo_root),
            "--venv-dir",
            str(venv_dir),
        ],
        check=True,
        cwd=repo_root,
    )
    return resolve_venv_python(venv_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap the local runtime if needed and run dhlottery.py."
    )
    parser.add_argument(
        "--repo-root",
        default=str(repo_root_from_here()),
        help="Repository root that contains dhlottery.py.",
    )
    parser.add_argument(
        "--venv-dir",
        help="Optional virtualenv directory. Defaults to <repo>/venv.",
    )
    parser.add_argument(
        "--env-file",
        help="Optional dotenv path forwarded to dhlottery.py.",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Forward --no-dotenv to dhlottery.py.",
    )
    parser.add_argument(
        "--games",
        type=int,
        help="Override the number of games for this run.",
    )
    parser.add_argument(
        "--interval-days",
        type=int,
        help="Override interval_days in the runtime config.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run the browser in headed mode.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate config without placing a purchase.",
    )
    parser.add_argument(
        "--request-id",
        default="openclaw-skill",
        help="Request identifier forwarded to dhlottery.py.",
    )
    parser.add_argument(
        "--trigger",
        default="manual",
        choices=("manual", "scheduled"),
        help="Trigger label forwarded to dhlottery.py.",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Do not create or repair the local runtime before launching.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    venv_dir = Path(args.venv_dir).resolve() if args.venv_dir else repo_root / "venv"
    launcher_python = (
        resolve_venv_python(venv_dir)
        if args.skip_bootstrap
        else ensure_runtime(repo_root, venv_dir)
    )

    command = [
        str(launcher_python),
        str(repo_root / "dhlottery.py"),
        "--request-id",
        args.request_id,
        "--trigger",
        args.trigger,
    ]
    if args.env_file:
        command.extend(["--env-file", args.env_file])
    if args.no_dotenv:
        command.append("--no-dotenv")
    if args.games is not None:
        command.extend(["--games", str(args.games)])
    if args.interval_days is not None:
        command.extend(["--interval-days", str(args.interval_days)])
    if args.headed:
        command.append("--headed")
    if args.check_config:
        command.append("--check-config")

    subprocess.run(command, cwd=repo_root, check=True)


if __name__ == "__main__":
    main()
