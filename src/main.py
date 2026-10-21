"""
Automatic File Organizer & Backup System
------------------------------------------
Team No: 19
Roll Nos: 24P61A67I8, 24P61A67I9, 24P61A67J0

Application Entry Point (CLI)
Usage:
    # Organize files without backup
    python src/main.py --source "data/input"

    # Create backup first, then organize files
    python src/main.py --source "data/input" --backup

    # Optional custom paths
    python src/main.py --source "data/input" --backup --backup-dir "custom_backup"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports if executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.organizer import get_project_root, main


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the file organizer application."""
    parser = argparse.ArgumentParser(
        description="Automatic File Organizer (Team 19 - College DevOps Project)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default=str(get_project_root() / "data" / "input"),
        help="Path to the directory to organize.",
    )
    parser.add_argument(
        "--backup",
        "-b",
        action="store_true",
        default=False,
        help="Create a backup of files before organizing them.",
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=None,
        help="Custom backup directory (default: 'backup' in project root).",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=str(get_project_root() / "config" / "categories.json"),
        help="Path to categories JSON configuration file.",
    )
    parser.add_argument(
        "--log",
        "-l",
        type=str,
        default=str(get_project_root() / "logs" / "organizer.log"),
        help="Path to output log file.",
    )
    return parser.parse_args()


def run() -> None:
    """Main CLI execution flow."""
    args = parse_arguments()
    source_path = Path(args.source)
    config_path = Path(args.config)
    log_file = Path(args.log)
    backup_enabled = args.backup
    project_root = get_project_root()
    backup_dir = Path(args.backup_dir) if args.backup_dir else (project_root / "backup")
    backup_log = project_root / "logs" / "backup.log"

    print("\n=======================================================")
    print("      Automatic File Organizer System (Team 19)")
    print("=======================================================")
    print(f"Target Directory : {source_path}")
    print(f"Config File      : {config_path}")
    print(f"Log File         : {log_file}")
    print(f"Backup Mode      : {'ENABLED' if backup_enabled else 'DISABLED'}")
    if backup_enabled:
        print(f"Backup Location  : {backup_dir}")
    print("=======================================================\n")

    if not source_path.exists():
        print(f"Error: Source directory '{source_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        main(
            source_dir=source_path,
            config_path=config_path,
            backup=backup_enabled,
            backup_dir=backup_dir,
            backup_log=backup_log,
            log_file=log_file,
        )
    except SystemExit as exc:
        sys.exit(exc.code)
    except Exception as exc:
        print(f"Execution Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
