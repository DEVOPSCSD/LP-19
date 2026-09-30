"""
Automated tests for the Stage 2 backup phase (src/backup.py) and its
integration with the Stage 1 organizer.

Every test uses pytest's `tmp_path`, so the real data/input folder is never
touched.

Run from the project root with:
    python -m pytest -v
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import organizer as organizer_module  # noqa: E402
from src.backup import backup_files  # noqa: E402

TEST_CATEGORIES = {
    "Images": [".jpg", ".png"],
    "Documents": [".txt"],
    "PDFs": [".pdf"],
}


@pytest.fixture
def dirs(tmp_path):
    """Return (input_dir, backup_dir, log_file) inside a temp folder."""
    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)
    return input_dir, tmp_path / "backup", tmp_path / "logs" / "backup.log"


def make_file(folder: Path, name: str, content: str = "dummy") -> Path:
    path = folder / name
    path.write_text(content, encoding="utf-8")
    return path


# ----------------------------------------------------------------------
# Backup directory
# ----------------------------------------------------------------------
def test_backup_directory_is_created_automatically(dirs):
    input_dir, backup_dir, _ = dirs
    assert not backup_dir.exists()

    backup_files(input_dir, backup_dir)

    assert backup_dir.is_dir()


# ----------------------------------------------------------------------
# Copying
# ----------------------------------------------------------------------
def test_single_file_is_backed_up_and_original_preserved(dirs):
    input_dir, backup_dir, _ = dirs
    original = make_file(input_dir, "notes.txt", "hello")

    result = backup_files(input_dir, backup_dir)

    assert result.success
    assert len(result.backed_up) == 1
    assert (backup_dir / "notes.txt").read_text(encoding="utf-8") == "hello"
    assert original.is_file()
    assert original.read_text(encoding="utf-8") == "hello"


def test_multiple_files_are_backed_up(dirs):
    input_dir, backup_dir, _ = dirs
    names = ["a.txt", "b.pdf", "c.jpg"]
    for name in names:
        make_file(input_dir, name, name)

    result = backup_files(input_dir, backup_dir)

    assert len(result.backed_up) == 3
    assert sorted(p.name for p in backup_dir.iterdir()) == names
    for name in names:
        assert (input_dir / name).is_file()


def test_unknown_file_type_is_backed_up(dirs):
    input_dir, backup_dir, _ = dirs
    make_file(input_dir, "mystery.xyz", "???")
    make_file(input_dir, "no_extension", "plain")

    result = backup_files(input_dir, backup_dir)

    assert result.success
    assert (backup_dir / "mystery.xyz").read_text(encoding="utf-8") == "???"
    assert (backup_dir / "no_extension").is_file()


def test_subdirectories_are_not_backed_up(dirs):
    input_dir, backup_dir, _ = dirs
    sub = input_dir / "Sub"
    sub.mkdir()
    make_file(sub, "nested.txt")

    result = backup_files(input_dir, backup_dir)

    assert result.backed_up == []
    assert list(backup_dir.iterdir()) == []


# ----------------------------------------------------------------------
# Duplicate protection
# ----------------------------------------------------------------------
def test_existing_backup_is_never_overwritten(dirs):
    input_dir, backup_dir, _ = dirs
    backup_dir.mkdir()
    (backup_dir / "report.pdf").write_text("OLD BACKUP", encoding="utf-8")
    make_file(input_dir, "report.pdf", "NEW FILE")

    result = backup_files(input_dir, backup_dir)

    assert (backup_dir / "report.pdf").read_text(encoding="utf-8") == "OLD BACKUP"
    assert (backup_dir / "report_1.pdf").read_text(encoding="utf-8") == "NEW FILE"
    assert result.backed_up[0][1].name == "report_1.pdf"


def test_duplicate_counter_keeps_incrementing(dirs):
    input_dir, backup_dir, _ = dirs
    backup_dir.mkdir()
    (backup_dir / "report.pdf").write_text("0", encoding="utf-8")
    (backup_dir / "report_1.pdf").write_text("1", encoding="utf-8")
    make_file(input_dir, "report.pdf", "2")

    backup_files(input_dir, backup_dir)

    assert (backup_dir / "report_2.pdf").read_text(encoding="utf-8") == "2"


def test_running_backup_twice_keeps_both_copies(dirs):
    input_dir, backup_dir, _ = dirs
    make_file(input_dir, "notes.txt", "v1")

    backup_files(input_dir, backup_dir)
    backup_files(input_dir, backup_dir)

    assert (backup_dir / "notes.txt").is_file()
    assert (backup_dir / "notes_1.txt").is_file()


# ----------------------------------------------------------------------
# Empty / missing directories
# ----------------------------------------------------------------------
def test_empty_input_directory_is_handled_gracefully(dirs):
    input_dir, backup_dir, _ = dirs

    result = backup_files(input_dir, backup_dir)

    assert result.backed_up == []
    assert result.failed == []
    assert result.success


def test_missing_input_directory_raises_not_a_directory_error(tmp_path):
    with pytest.raises(NotADirectoryError):
        backup_files(tmp_path / "does_not_exist", tmp_path / "backup")


def test_missing_input_directory_does_not_create_backup_dir(tmp_path):
    backup_dir = tmp_path / "backup"
    with pytest.raises(NotADirectoryError):
        backup_files(tmp_path / "does_not_exist", backup_dir)
    assert not backup_dir.exists()


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def test_successful_backup_is_logged(dirs):
    input_dir, backup_dir, log_file = dirs
    make_file(input_dir, "notes.txt")

    backup_files(input_dir, backup_dir, log_file)

    assert log_file.is_file()
    text = log_file.read_text(encoding="utf-8")
    assert "Backed up notes.txt" in text
    assert "INFO" in text


def test_missing_input_directory_is_logged(tmp_path):
    log_file = tmp_path / "logs" / "backup.log"
    with pytest.raises(NotADirectoryError):
        backup_files(tmp_path / "nope", tmp_path / "backup", log_file)

    text = log_file.read_text(encoding="utf-8")
    assert "ERROR" in text
    assert "Input directory not found" in text


def test_log_is_appended_across_runs(dirs):
    input_dir, backup_dir, log_file = dirs
    make_file(input_dir, "notes.txt")

    backup_files(input_dir, backup_dir, log_file)
    backup_files(input_dir, backup_dir, log_file)

    assert log_file.read_text(encoding="utf-8").count("Backed up notes.txt") == 2


# ----------------------------------------------------------------------
# Copy errors
# ----------------------------------------------------------------------
def test_copy_error_is_reported_logged_and_other_files_still_backed_up(
    dirs, monkeypatch
):
    input_dir, backup_dir, log_file = dirs
    make_file(input_dir, "a_good.txt")
    make_file(input_dir, "b_bad.txt")
    make_file(input_dir, "c_good.txt")

    real_copy2 = shutil.copy2

    def flaky_copy2(src, dst, *args, **kwargs):
        if Path(src).name == "b_bad.txt":
            raise PermissionError("simulated permission error")
        return real_copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr("src.backup.shutil.copy2", flaky_copy2)

    result = backup_files(input_dir, backup_dir, log_file)

    assert not result.success
    assert [p.name for p, _ in result.failed] == ["b_bad.txt"]
    assert sorted(p.name for p, _ in result.backed_up) == ["a_good.txt", "c_good.txt"]
    assert (input_dir / "b_bad.txt").is_file()  # original untouched
    text = log_file.read_text(encoding="utf-8")
    assert "FAILED to back up b_bad.txt" in text
    assert "simulated permission error" in text


def test_backup_directory_creation_failure_raises(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    blocker = tmp_path / "backup"
    blocker.write_text("I am a file, not a folder", encoding="utf-8")

    with pytest.raises(OSError):
        backup_files(input_dir, blocker)


# ----------------------------------------------------------------------
# Integration with the Stage 1 organizer: backup -> organize
# ----------------------------------------------------------------------
@pytest.fixture
def fake_project(tmp_path, monkeypatch):
    """A temp project root wired into organizer.main()."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "categories.json").write_text(
        json.dumps(TEST_CATEGORIES), encoding="utf-8"
    )
    (tmp_path / "data" / "input").mkdir(parents=True)
    monkeypatch.setattr(organizer_module, "get_project_root", lambda: tmp_path)
    return tmp_path


def test_main_backs_up_files_then_organizes_them(fake_project):
    input_dir = fake_project / "data" / "input"
    make_file(input_dir, "notes.txt", "hello")
    make_file(input_dir, "mystery.xyz", "???")

    organizer_module.main()

    # Backups hold the originals.
    assert (fake_project / "backup" / "notes.txt").read_text(encoding="utf-8") == "hello"
    assert (fake_project / "backup" / "mystery.xyz").is_file()
    # Stage 1 organizing still happened.
    assert (input_dir / "Documents" / "notes.txt").is_file()
    assert (input_dir / "Others" / "mystery.xyz").is_file()
    assert not (input_dir / "notes.txt").exists()
    # Logged.
    assert "Backed up notes.txt" in (
        fake_project / "logs" / "backup.log"
    ).read_text(encoding="utf-8")


def test_main_does_not_organize_when_a_backup_fails(fake_project, monkeypatch, capsys):
    input_dir = fake_project / "data" / "input"
    make_file(input_dir, "notes.txt")

    def always_fail(src, dst, *args, **kwargs):
        raise PermissionError("disk is read-only")

    monkeypatch.setattr("src.backup.shutil.copy2", always_fail)

    with pytest.raises(SystemExit) as exit_info:
        organizer_module.main()

    assert exit_info.value.code == 1
    assert (input_dir / "notes.txt").is_file()        # not moved
    assert not (input_dir / "Documents").exists()     # nothing organized
    assert "BACKUP FAILED" in capsys.readouterr().out


def test_main_with_empty_input_directory_does_not_crash(fake_project):
    organizer_module.main()

    assert (fake_project / "backup").is_dir()