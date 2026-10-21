"""
File Classifier Module
----------------------
Handles file classification based on file extensions.
Maps extensions (e.g. .jpg, .docx, .py) to appropriate category folders.
Unsupported extensions are automatically classified as 'Others'.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

# Default categories and extensions as required by the project specification
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "Documents": [".doc", ".docx", ".txt", ".odt"],
    "PDFs": [".pdf"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov"],
    "Audio": [".mp3", ".wav", ".flac"],
    "Source_Code": [".py", ".java", ".c", ".cpp", ".js", ".html", ".css"],
    "Archives": [".zip", ".rar", ".7z"],
}

OTHERS_CATEGORY = "Others"


class FileClassifier:
    """Classifies files into categories based on their extensions.

    Attributes:
        config_path: Optional path to a JSON configuration file.
        category_map: Mapping of lowercase file extension to category name.
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        self.config_path = Path(config_path) if config_path else None
        self.category_map: Dict[str, str] = {}
        self._categories: Dict[str, List[str]] = {}

        if self.config_path is not None:
            self._load_from_config(self.config_path)
        else:
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load the default category mapping."""
        self._categories = DEFAULT_CATEGORIES
        self._build_lookup_map(self._categories)

    def _load_from_config(self, config_path: Path) -> None:
        """Load category mappings from a JSON configuration file."""
        if not config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as f:
            raw_data: Dict[str, List[str]] = json.load(f)

        self._categories = raw_data
        self._build_lookup_map(raw_data)

    def _build_lookup_map(self, categories: Dict[str, List[str]]) -> None:
        """Populate extension -> category lookup table for O(1) matching."""
        self.category_map.clear()
        for category, extensions in categories.items():
            for ext in extensions:
                cleaned_ext = ext.strip().lower()
                if not cleaned_ext.startswith("."):
                    cleaned_ext = f".{cleaned_ext}"
                self.category_map[cleaned_ext] = category

    def get_category(self, file_path_or_name: Union[str, Path]) -> str:
        """Identify the category for a given file name or path.

        Args:
            file_path_or_name: Path or file name to classify.

        Returns:
            The matched category name (e.g. 'Images', 'Documents', 'Source_Code')
            or 'Others' if the extension is not recognized.
        """
        path_obj = Path(file_path_or_name)
        extension = path_obj.suffix.lower()

        if not extension:
            return OTHERS_CATEGORY

        return self.category_map.get(extension, OTHERS_CATEGORY)

    def get_supported_categories(self) -> List[str]:
        """Return list of all recognized categories including 'Others'."""
        categories = list(self._categories.keys())
        if OTHERS_CATEGORY not in categories:
            categories.append(OTHERS_CATEGORY)
        return categories
