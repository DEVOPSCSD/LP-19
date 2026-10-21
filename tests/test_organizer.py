"""
Automated Integration Tests for the FileOrganizer System.
-----------------------------------------------------------
Tests the full organization pipeline using isolated pytest `tmp_path` fixtures.
"""

import json
from pathlib import Path
import pytest

from src.organizer import FileOrganizer
from src.classifier import DEFAULT_CATEGORIES


@pytest.fixture
def organizer(tmp_path):
    """Build a FileOrganizer wired to a fresh, isolated temp directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "categories.json"
    config_path.write_text(json.dumps(DEFAULT_CATEGORIES), encoding="utf-8")

    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)

    log_file = tmp_path / "logs" / "test_organizer.log"

    return FileOrganizer(
        source_dir=input_dir,
        config_path=config_path,
        log_file=log_file,
    )


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
        ("script.py", "Source_Code"),
        ("movie.mp4", "Videos"),
        ("song.mp3", "Audio"),
        ("backup.zip", "Archives"),
        ("mystery.xyz", "Others"),
    ],
)
def test_file_is_moved_to_expected_category(organizer, file_name, expected_category):
    make_file(organizer.source_dir, file_name)

    results = organizer.organize()

    expected_path = organizer.source_dir / expected_category / file_name
    assert expected_path.is_file()
    assert results[expected_category] == [file_name]


# ----------------------------------------------------------------------
# Duplicate filename handling
# ----------------------------------------------------------------------
def test_duplicate_filename_is_renamed_not_overwritten(organizer):
    images_dir = organizer.source_dir / "Images"
    images_dir.mkdir()
    existing_file = images_dir / "photo.jpg"
    existing_file.write_text("ORIGINAL CONTENT", encoding="utf-8")

    make_file(organizer.source_dir, "photo.jpg", content="NEW CONTENT")

    results = organizer.organize()

    # Original file is preserved
    assert existing_file.read_text(encoding="utf-8") == "ORIGINAL CONTENT"

    # New file is renamed
    renamed_file = images_dir / "photo_1.jpg"
    assert renamed_file.is_file()
    assert renamed_file.read_text(encoding="utf-8") == "NEW CONTENT"
    assert results["Images"] == ["photo_1.jpg"]


def test_multiple_duplicates_increment_the_counter(organizer):
    images_dir = organizer.source_dir / "Images"
    images_dir.mkdir()
    (images_dir / "photo.jpg").write_text("0", encoding="utf-8")
    (images_dir / "photo_1.jpg").write_text("1", encoding="utf-8")

    make_file(organizer.source_dir, "photo.jpg", content="2")

    organizer.organize()

    assert (images_dir / "photo_2.jpg").is_file()
    assert (images_dir / "photo_2.jpg").read_text(encoding="utf-8") == "2"


# ----------------------------------------------------------------------
# Case-insensitivity & Empty Directories
# ----------------------------------------------------------------------
def test_uppercase_extension_is_detected_case_insensitively(organizer):
    make_file(organizer.source_dir, "PHOTO.JPG")

    results = organizer.organize()

    assert (organizer.source_dir / "Images" / "PHOTO.JPG").is_file()
    assert results["Images"] == ["PHOTO.JPG"]


def test_empty_input_folder_does_not_crash(organizer):
    results = organizer.organize()
    assert results == {}


def test_no_files_are_deleted(organizer):
    make_file(organizer.source_dir, "notes.txt")

    organizer.organize()

    all_files = list(organizer.source_dir.rglob("*.txt"))
    assert len(all_files) == 1


def test_subdirectories_are_never_recursed_into(organizer):
    nested_dir = organizer.source_dir / "SomeSubdir"
    nested_dir.mkdir()
    nested_file = nested_dir / "should_not_move.txt"
    nested_file.write_text("leave me alone", encoding="utf-8")

    results = organizer.organize()

    assert nested_file.is_file()
    assert results == {}


# ----------------------------------------------------------------------
# Error Handling & Resilience
# ----------------------------------------------------------------------
def test_missing_config_file_raises_file_not_found_error(tmp_path):
    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True)
    missing_config_path = tmp_path / "config" / "categories.json"

    with pytest.raises(FileNotFoundError):
        FileOrganizer(source_dir=input_dir, config_path=missing_config_path)


def test_missing_input_dir_raises_not_a_directory_error(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "categories.json"
    config_path.write_text(json.dumps(DEFAULT_CATEGORIES), encoding="utf-8")

    missing_input_dir = tmp_path / "data" / "input"

    with pytest.raises(NotADirectoryError):
        FileOrganizer(source_dir=missing_input_dir, config_path=config_path)


def test_continues_processing_when_one_file_fails(organizer, monkeypatch):
    """Verifies that an error on one file does not halt processing of subsequent files."""
    make_file(organizer.source_dir, "good1.txt")
    make_file(organizer.source_dir, "faulty.pdf")
    make_file(organizer.source_dir, "good2.jpg")

    from src.mover import FileMover, MoveResult
    original_move = FileMover.move_file

    def flaky_move(source_path, destination_dir):
        if Path(source_path).name == "faulty.pdf":
            return MoveResult(
                success=False,
                source_path=Path(source_path),
                error_message="Simulated disk error on faulty.pdf",
            )
        return original_move(source_path, destination_dir)

    monkeypatch.setattr("src.mover.FileMover.move_file", staticmethod(flaky_move))

    results = organizer.organize()

    # The two valid files should have been organized successfully despite the faulty one
    assert "Documents" in results and "good1.txt" in results["Documents"]
    assert "Images" in results and "good2.jpg" in results["Images"]
    assert (organizer.source_dir / "faulty.pdf").exists()  # Faulty file was left safely


# ----------------------------------------------------------------------
# Logging Verification
# ----------------------------------------------------------------------
def test_logging_records_required_events(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    log_file = tmp_path / "test.log"

    # Pre-create duplicate in destination
    images_dir = input_dir / "Images"
    images_dir.mkdir()
    (images_dir / "img.png").write_text("old", encoding="utf-8")

    # Add files to input
    make_file(input_dir, "img.png", "new")
    make_file(input_dir, "doc.txt", "doc content")

    organizer = FileOrganizer(source_dir=input_dir, log_file=log_file)
    organizer.organize()

    assert log_file.is_file()
    log_content = log_file.read_text(encoding="utf-8")

    # Verify each required log event
    assert "Automatic File Organizer Started" in log_content
    assert "Scanning directory" in log_content
    assert "Files detected:" in log_content
    assert "File successfully moved:" in log_content
    assert "Duplicate filename handled:" in log_content
    assert "Application Completed" in log_content
