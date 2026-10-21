"""
Tests for Duplicate Filename Handling Logic
--------------------------------------------
Verifies that existing files are never overwritten and sequential suffixes are appended.
"""

from pathlib import Path
from src.duplicate_handler import resolve_duplicate_path


def test_first_arrival_not_renamed(tmp_path):
    dest_dir = tmp_path / "PDFs"
    dest_dir.mkdir()

    resolved_path, was_renamed = resolve_duplicate_path(dest_dir, "report.pdf")
    assert resolved_path.name == "report.pdf"
    assert was_renamed is False


def test_single_duplicate_gets_suffix_1(tmp_path):
    dest_dir = tmp_path / "PDFs"
    dest_dir.mkdir()
    (dest_dir / "report.pdf").write_text("existing", encoding="utf-8")

    resolved_path, was_renamed = resolve_duplicate_path(dest_dir, "report.pdf")
    assert resolved_path.name == "report_1.pdf"
    assert was_renamed is True


def test_multiple_duplicates_increment_correctly(tmp_path):
    dest_dir = tmp_path / "PDFs"
    dest_dir.mkdir()
    (dest_dir / "report.pdf").write_text("0", encoding="utf-8")
    (dest_dir / "report_1.pdf").write_text("1", encoding="utf-8")

    resolved_path, was_renamed = resolve_duplicate_path(dest_dir, "report.pdf")
    assert resolved_path.name == "report_2.pdf"
    assert was_renamed is True

    # Simulate creating report_2.pdf as well
    (dest_dir / "report_2.pdf").write_text("2", encoding="utf-8")
    resolved_path3, was_renamed3 = resolve_duplicate_path(dest_dir, "report.pdf")
    assert resolved_path3.name == "report_3.pdf"
    assert was_renamed3 is True


def test_duplicate_without_extension(tmp_path):
    dest_dir = tmp_path / "Others"
    dest_dir.mkdir()
    (dest_dir / "README").write_text("v1", encoding="utf-8")

    resolved_path, was_renamed = resolve_duplicate_path(dest_dir, "README")
    assert resolved_path.name == "README_1"
    assert was_renamed is True
