"""
Automated Tests for the CLI and --backup Option
------------------------------------------------
Verifies command-line behavior with and without the --backup flag.
"""

import sys
from pathlib import Path
import pytest

from src import main as main_cli


def make_file(folder: Path, name: str, content: str = "sample") -> Path:
    """Helper to create a test file."""
    p = folder / name
    p.write_text(content, encoding="utf-8")
    return p


def test_cli_without_backup_organizes_only(tmp_path, monkeypatch):
    """Running without --backup should organize files and NOT create a backup."""
    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)
    backup_dir = tmp_path / "backup"
    log_file = tmp_path / "logs" / "organizer.log"

    make_file(input_dir, "notes.txt", "my notes")
    make_file(input_dir, "pic.jpg", "my pic")

    test_args = [
        "main.py",
        "--source",
        str(input_dir),
        "--backup-dir",
        str(backup_dir),
        "--log",
        str(log_file),
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    main_cli.run()

    # Files must be organized
    assert (input_dir / "Documents" / "notes.txt").is_file()
    assert (input_dir / "Images" / "pic.jpg").is_file()
    assert not (input_dir / "notes.txt").exists()

    # Backup directory must NOT exist
    assert not backup_dir.exists()


def test_cli_with_backup_creates_backup_and_organizes(tmp_path, monkeypatch):
    """Running with --backup creates backup files first, then organizes them."""
    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)
    backup_dir = tmp_path / "backup"
    log_file = tmp_path / "logs" / "organizer.log"

    make_file(input_dir, "notes.txt", "hello notes")
    make_file(input_dir, "photo.png", "hello photo")

    test_args = [
        "main.py",
        "--source",
        str(input_dir),
        "--backup",
        "--backup-dir",
        str(backup_dir),
        "--log",
        str(log_file),
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    main_cli.run()

    # 1. Backups must exist with original content
    assert backup_dir.is_dir()
    assert (backup_dir / "notes.txt").read_text(encoding="utf-8") == "hello notes"
    assert (backup_dir / "photo.png").is_file()

    # 2. Files must also be organized
    assert (input_dir / "Documents" / "notes.txt").is_file()
    assert (input_dir / "Images" / "photo.png").is_file()
    assert not (input_dir / "notes.txt").exists()


def test_cli_with_backup_failure_aborts_organization(tmp_path, monkeypatch):
    """If backup fails when --backup is passed, organization must NOT run."""
    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)
    backup_dir = tmp_path / "backup"
    log_file = tmp_path / "logs" / "organizer.log"

    make_file(input_dir, "critical_doc.txt", "do not lose me")

    def failing_copy(src, dst, *args, **kwargs):
        raise PermissionError("Simulated backup failure")

    monkeypatch.setattr("src.backup.shutil.copy2", failing_copy)

    test_args = [
        "main.py",
        "--source",
        str(input_dir),
        "--backup",
        "--backup-dir",
        str(backup_dir),
        "--log",
        str(log_file),
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exit_info:
        main_cli.run()

    assert exit_info.value.code == 1

    # Critical file must remain untouched in input directory
    assert (input_dir / "critical_doc.txt").is_file()
    # No category directory should have been organized
    assert not (input_dir / "Documents").exists()


def test_cli_missing_source_directory_exits_with_error(tmp_path, monkeypatch):
    """CLI should exit with code 1 when the source directory does not exist."""
    missing_dir = tmp_path / "does_not_exist"

    test_args = ["main.py", "--source", str(missing_dir)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exit_info:
        main_cli.run()

    assert exit_info.value.code == 1
