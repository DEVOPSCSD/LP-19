"""
Tests for File Classification Logic
------------------------------------
Verifies file extension classification and category selection.
"""

import json
from pathlib import Path
import pytest

from src.classifier import FileClassifier, OTHERS_CATEGORY, DEFAULT_CATEGORIES


def test_default_categories_loaded_correctly():
    classifier = FileClassifier()
    assert classifier.get_category("photo.jpg") == "Images"
    assert classifier.get_category("document.pdf") == "PDFs"
    assert classifier.get_category("main.py") == "Source_Code"


@pytest.mark.parametrize(
    "filename, expected_category",
    [
        # Images
        ("photo.jpg", "Images"),
        ("image.jpeg", "Images"),
        ("graphic.png", "Images"),
        ("animation.gif", "Images"),
        ("banner.webp", "Images"),
        # Documents
        ("resume.doc", "Documents"),
        ("contract.docx", "Documents"),
        ("notes.txt", "Documents"),
        ("letter.odt", "Documents"),
        # PDFs
        ("paper.pdf", "PDFs"),
        ("annual_report.PDF", "PDFs"),
        # Videos
        ("clip.mp4", "Videos"),
        ("film.avi", "Videos"),
        ("show.mkv", "Videos"),
        ("recording.mov", "Videos"),
        # Audio
        ("track.mp3", "Audio"),
        ("voice.wav", "Audio"),
        ("music.flac", "Audio"),
        # Source_Code
        ("script.py", "Source_Code"),
        ("App.java", "Source_Code"),
        ("program.c", "Source_Code"),
        ("system.cpp", "Source_Code"),
        ("index.js", "Source_Code"),
        ("index.html", "Source_Code"),
        ("styles.css", "Source_Code"),
        # Archives
        ("bundle.zip", "Archives"),
        ("backup.rar", "Archives"),
        ("package.7z", "Archives"),
        # Others (unsupported extensions)
        ("random.xyz", "Others"),
        ("data.bin", "Others"),
        ("mystery.unknown", "Others"),
        ("no_extension_file", "Others"),
    ],
)
def test_all_required_extensions_classified(filename, expected_category):
    classifier = FileClassifier()
    assert classifier.get_category(filename) == expected_category


def test_case_insensitive_classification():
    classifier = FileClassifier()
    assert classifier.get_category("PHOTO.JPG") == "Images"
    assert classifier.get_category("README.TXT") == "Documents"
    assert classifier.get_category("MAIN.PY") == "Source_Code"
    assert classifier.get_category("Song.Mp3") == "Audio"


def test_custom_config_loading(tmp_path):
    custom_categories = {
        "CustomDocs": [".custom", ".doc"],
        "CustomMedia": [".med"],
    }
    config_file = tmp_path / "custom_categories.json"
    config_file.write_text(json.dumps(custom_categories), encoding="utf-8")

    classifier = FileClassifier(config_path=config_file)
    assert classifier.get_category("file.custom") == "CustomDocs"
    assert classifier.get_category("file.med") == "CustomMedia"
    assert classifier.get_category("file.pdf") == OTHERS_CATEGORY


def test_missing_config_file_raises_not_found(tmp_path):
    missing_path = tmp_path / "non_existent.json"
    with pytest.raises(FileNotFoundError):
        FileClassifier(config_path=missing_path)
