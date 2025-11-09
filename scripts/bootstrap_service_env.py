#!/usr/bin/env python3
"""Bootstrap a per-service virtual environment and install the package in editable mode."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
from pathlib import Path
import venv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a virtual environment for a service under services/ and install it in editable mode."
        )
    )
    parser.add_argument(
        "service",
        help="Name or path of the service directory under services/.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate the virtual environment if it already exists.",
    )
    return parser.parse_args()


def _resolve_service(service_arg: str) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    candidate = Path(service_arg)
    if not candidate.is_absolute():
        candidate = (repo_root / "services" / candidate).resolve()
    if not candidate.is_dir():
        raise SystemExit(f"Service directory not found: {candidate}")
    pyproject = candidate / "pyproject.toml"
    if not pyproject.exists():
        raise SystemExit(
            f"Expected pyproject.toml in {candidate}, found none."
        )
    return candidate


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _activate_help(service_dir: Path) -> str:
    venv_dir = service_dir / ".venv"
    if os.name == "nt":
        return textwrap.dedent(
            f"""
            To activate the environment:
              PowerShell:   {venv_dir}\\Scripts\\Activate.ps1
              Command Prompt: {venv_dir}\\Scripts\\activate.bat
              Git Bash:    source {venv_dir.as_posix()}/Scripts/activate
            """
        ).strip()
    return textwrap.dedent(
        f"""
        To activate the environment run:
          source {venv_dir.as_posix()}/bin/activate
        """
    ).strip()


def main() -> None:
    args = parse_args()
    service_dir = _resolve_service(args.service)
    venv_dir = service_dir / ".venv"

    builder = venv.EnvBuilder(with_pip=True, clear=args.force)
    if venv_dir.exists() and not args.force:
        print(f"Virtual environment already exists at {venv_dir}. Skipping creation.")
    else:
        print(f"Creating virtual environment at {venv_dir} using {sys.executable}...")
        builder.create(venv_dir)

    python_exe = _venv_python(venv_dir)
    if not python_exe.exists():
        raise SystemExit(
            f"Failed to locate python executable inside the virtualenv: {python_exe}"
        )

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [env.get("PYTHONPATH"), str(service_dir.parents[1])])
    )

    print("Upgrading packaging tools...")
    subprocess.check_call(
        [str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        env=env,
    )

    print("Installing the service in editable mode...")
    subprocess.check_call([str(python_exe), "-m", "pip", "install", "-e", str(service_dir)], env=env)

    print("\nDone!")
    print(_activate_help(service_dir))


if __name__ == "__main__":
    main()
