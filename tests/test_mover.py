"""
Tests for File Movement Logic
------------------------------
Verifies safe file movement, directory creation, duplicate avoidance, and error resilience.
"""

from pathlib import Path
import pytest
from src.mover import FileMover


def test_destination_directory_created_automatically(tmp_path):
    source_file = tmp_path / "notes.txt"
    source_file.write_text("content", encoding="utf-8")

    dest_dir = tmp_path / "Documents"
    assert not dest_dir.exists()

    result = FileMover.move_file(source_file, dest_dir)

    assert result.success is True
    assert dest_dir.is_dir()
    assert (dest_dir / "notes.txt").exists()
    assert not source_file.exists()


def test_file_moved_without_overwriting_existing(tmp_path):
    dest_dir = tmp_path / "Images"
    dest_dir.mkdir()
    existing_file = dest_dir / "photo.jpg"
    existing_file.write_text("old image", encoding="utf-8")

    new_file = tmp_path / "photo.jpg"
    new_file.write_text("new image", encoding="utf-8")

    result = FileMover.move_file(new_file, dest_dir)

    assert result.success is True
    assert result.was_renamed is True
    assert result.destination_path.name == "photo_1.jpg"
    # Ensure existing file was preserved intact
    assert existing_file.read_text(encoding="utf-8") == "old image"
    assert (dest_dir / "photo_1.jpg").read_text(encoding="utf-8") == "new image"


def test_moving_non_existent_file_returns_failure(tmp_path):
    dest_dir = tmp_path / "Documents"
    missing_file = tmp_path / "missing.txt"

    result = FileMover.move_file(missing_file, dest_dir)

    assert result.success is False
    assert "does not exist" in result.error_message


def test_moving_directory_instead_of_file_returns_failure(tmp_path):
    subfolder = tmp_path / "Subfolder"
    subfolder.mkdir()
    dest_dir = tmp_path / "Others"

    result = FileMover.move_file(subfolder, dest_dir)

    assert result.success is False
    assert "not a file" in result.error_message


def test_permission_error_is_caught_gracefully(tmp_path, monkeypatch):
    source_file = tmp_path / "locked.txt"
    source_file.write_text("data", encoding="utf-8")
    dest_dir = tmp_path / "Documents"

    def mock_move(src, dst):
        raise PermissionError("Access denied by OS")

    monkeypatch.setattr("shutil.move", mock_move)

    result = FileMover.move_file(source_file, dest_dir)

    assert result.success is False
    assert "Permission denied" in result.error_message
    assert source_file.exists()
