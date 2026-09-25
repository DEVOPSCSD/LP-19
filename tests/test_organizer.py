"""
Automated tests for the FileOrganizer class.

These tests are fully isolated from the real project's `data/input/`
folder. Each test builds its own temporary input directory and its own
temporary `categories.json` config file using pytest's built-in
`tmp_path` fixture, so tests never touch real data and never interfere
with each other.

Run from the project root with:
    pytest
or, for more detail:
    pytest -v
"""

import json
import sys
from pathlib import Path

import pytest

# Make sure "src" is importable when tests are run from the project root
# (pytest adds the rootdir to sys.path automatically in most setups, but
# this makes the test file runnable/robust on its own too).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.organizer import FileOrganizer  # noqa: E402


# A fixed set of category mappings used by every test, so tests do not
# depend on (or accidentally break due to) edits made to the real
# config/categories.json file.
TEST_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "Documents": [".doc", ".docx", ".txt", ".odt"],
    "PDFs": [".pdf"],
    "Code": [".py", ".java", ".cpp", ".c", ".js", ".html", ".css", ".json", ".xml"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
    "Music": [".mp3", ".wav", ".flac", ".aac"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
}


@pytest.fixture
def organizer(tmp_path):
    """Build a FileOrganizer wired to a fresh, isolated temp directory.

    Creates:
        tmp_path/config/categories.json
        tmp_path/data/input/            (empty, ready for test files)

    Returns a ready-to-use FileOrganizer instance.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "categories.json"
    config_path.write_text(json.dumps(TEST_CATEGORIES), encoding="utf-8")

    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)

    return FileOrganizer(input_dir=input_dir, config_path=config_path)


def make_file(input_dir: Path, name: str, content: str = "dummy content") -> Path:
    """Create a small dummy file with the given name inside input_dir."""
    file_path = input_dir / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ----------------------------------------------------------------------
# Extension -> category tests
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "file_name, expected_category",
    [
        ("photo.jpg", "Images"),
        ("photo.png", "Images"),
        ("notes.txt", "Documents"),
        ("report.pdf", "PDFs"),
        ("script.py", "Code"),
        ("movie.mp4", "Videos"),
        ("song.mp3", "Music"),
        ("backup.zip", "Archives"),
        ("mystery.xyz", "Others"),
    ],
)
def test_file_is_moved_to_expected_category(organizer, file_name, expected_category):
    make_file(organizer.input_dir, file_name)

    results = organizer.organize()

    expected_path = organizer.input_dir / expected_category / file_name
    assert expected_path.is_file()
    assert results[expected_category] == [file_name]


# ----------------------------------------------------------------------
# Duplicate filename handling
# ----------------------------------------------------------------------
def test_duplicate_filename_is_renamed_not_overwritten(organizer):
    # Pre-existing file already sitting in the destination category.
    images_dir = organizer.input_dir / "Images"
    images_dir.mkdir()
    existing_file = images_dir / "photo.jpg"
    existing_file.write_text("ORIGINAL CONTENT", encoding="utf-8")

    # A new, different photo.jpg arrives in the input directory.
    make_file(organizer.input_dir, "photo.jpg", content="NEW CONTENT")

    results = organizer.organize()

    # The original file must be untouched.
    assert existing_file.read_text(encoding="utf-8") == "ORIGINAL CONTENT"

    # The new file must have been renamed, not overwritten.
    renamed_file = images_dir / "photo_1.jpg"
    assert renamed_file.is_file()
    assert renamed_file.read_text(encoding="utf-8") == "NEW CONTENT"

    assert results["Images"] == ["photo_1.jpg"]


def test_multiple_duplicates_increment_the_counter(organizer):
    images_dir = organizer.input_dir / "Images"
    images_dir.mkdir()
    (images_dir / "photo.jpg").write_text("0", encoding="utf-8")
    (images_dir / "photo_1.jpg").write_text("1", encoding="utf-8")

    make_file(organizer.input_dir, "photo.jpg", content="2")

    organizer.organize()

    assert (images_dir / "photo_2.jpg").is_file()
    assert (images_dir / "photo_2.jpg").read_text(encoding="utf-8") == "2"


# ----------------------------------------------------------------------
# Case-insensitive extension handling
# ----------------------------------------------------------------------
def test_uppercase_extension_is_detected_case_insensitively(organizer):
    make_file(organizer.input_dir, "PHOTO.JPG")

    results = organizer.organize()

    assert (organizer.input_dir / "Images" / "PHOTO.JPG").is_file()
    assert results["Images"] == ["PHOTO.JPG"]


# ----------------------------------------------------------------------
# Empty input folder
# ----------------------------------------------------------------------
def test_empty_input_folder_does_not_crash(organizer):
    # No files created at all.
    results = organizer.organize()

    assert results == {}


# ----------------------------------------------------------------------
# Extra safety checks (bonus coverage beyond the required list)
# ----------------------------------------------------------------------
def test_no_files_are_deleted(organizer):
    make_file(organizer.input_dir, "notes.txt")

    organizer.organize()

    # The file must still exist somewhere under the input directory,
    # just relocated into its category folder rather than deleted.
    all_files = list(organizer.input_dir.rglob("*.txt"))
    assert len(all_files) == 1


def test_subdirectories_are_never_recursed_into(organizer):
    nested_dir = organizer.input_dir / "SomeSubdir"
    nested_dir.mkdir()
    nested_file = nested_dir / "should_not_move.txt"
    nested_file.write_text("leave me alone", encoding="utf-8")

    results = organizer.organize()

    # The nested file must remain exactly where it was.
    assert nested_file.is_file()
    assert results == {}


def test_missing_config_file_raises_file_not_found_error(tmp_path):
    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)
    missing_config_path = tmp_path / "config" / "categories.json"  # never created

    with pytest.raises(FileNotFoundError):
        FileOrganizer(input_dir=input_dir, config_path=missing_config_path)


def test_missing_input_dir_raises_not_a_directory_error(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "categories.json"
    config_path.write_text(json.dumps(TEST_CATEGORIES), encoding="utf-8")

    missing_input_dir = tmp_path / "data" / "input"  # never created

    with pytest.raises(NotADirectoryError):
        FileOrganizer(input_dir=missing_input_dir, config_path=config_path)
