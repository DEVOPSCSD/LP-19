"""
Automatic File Organizer & Backup System
------------------------------------------
Stage 1: Core File Organizer

This module scans the `data/input/` directory, identifies files by their
extension, and moves them into category sub-folders (Images, Documents,
PDFs, Code, Videos, Music, Archives, Others).

Design notes:
    * Only files directly inside `data/input/` are processed. Category
      folders (and any other sub-directories) are never scanned, so the
      organizer will not accidentally re-organize its own output.
    * Existing files are never overwritten. If a name collision occurs,
      the incoming file is renamed using a `name_1`, `name_2`, ... pattern.
    * No files are ever deleted.
    * All paths are computed relative to the project root, so this script
      works the same way regardless of the directory it is launched from,
      and regardless of whether it later runs locally, in Docker, or in a
      Jenkins pipeline.

Run from the project root with:
    python src/organizer.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List


# Name of the fallback category for extensions that are not configured.
OTHERS_CATEGORY = "Others"


class FileOrganizer:
    """Organizes files inside an input directory into category folders.

    Attributes:
        input_dir: Directory containing the files to organize.
        config_path: Path to the JSON file describing category -> extension
            mappings.
        category_map: A dict mapping a lowercase file extension (including
            the leading dot) to its category name, built from the config
            file.
    """

    def __init__(self, input_dir: Path, config_path: Path) -> None:
        self.input_dir = input_dir
        self.config_path = config_path
        self.category_map: Dict[str, str] = {}

        self._validate_config_exists()
        self._validate_input_dir_exists()
        self._load_categories()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_config_exists(self) -> None:
        if not self.config_path.is_file():
            raise FileNotFoundError(
                f"Category configuration file not found: {self.config_path}"
            )

    def _validate_input_dir_exists(self) -> None:
        if not self.input_dir.is_dir():
            raise NotADirectoryError(
                f"Input directory not found: {self.input_dir}"
            )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _load_categories(self) -> None:
        """Load category -> extension mappings from the config file.

        The JSON file is expected to look like:
            {
                "Images": [".jpg", ".png"],
                "Documents": [".docx", ".txt"]
            }

        This is flattened into an extension -> category lookup table
        (self.category_map) for fast, case-insensitive access.
        """
        with self.config_path.open("r", encoding="utf-8") as config_file:
            raw_config: Dict[str, List[str]] = json.load(config_file)

        for category, extensions in raw_config.items():
            for extension in extensions:
                self.category_map[extension.lower()] = category

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    def get_category(self, file_path: Path) -> str:
        """Return the category name for a given file based on its extension."""
        extension = file_path.suffix.lower()
        return self.category_map.get(extension, OTHERS_CATEGORY)

    def _resolve_destination(self, destination_dir: Path, file_name: str) -> Path:
        """Return a safe destination path that will not overwrite a file.

        If `file_name` already exists in `destination_dir`, a numeric
        suffix is appended before the extension (e.g. photo_1.jpg,
        photo_2.jpg, ...) until a free name is found.
        """
        candidate = destination_dir / file_name
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while True:
            new_candidate = destination_dir / f"{stem}_{counter}{suffix}"
            if not new_candidate.exists():
                return new_candidate
            counter += 1

    def _iter_input_files(self):
        """Yield only the files directly inside the input directory.

        Sub-directories (including previously created category folders)
        are skipped so the organizer never recurses into its own output.
        """
        for entry in sorted(self.input_dir.iterdir()):
            if entry.is_file():
                yield entry

    def organize(self) -> Dict[str, List[str]]:
        """Organize all files currently in the input directory.

        Returns:
            A dictionary mapping each category name to the list of file
            names that were moved into it during this run.
        """
        results: Dict[str, List[str]] = {}

        for file_path in self._iter_input_files():
            category = self.get_category(file_path)
            destination_dir = self.input_dir / category
            destination_dir.mkdir(exist_ok=True)

            destination_path = self._resolve_destination(
                destination_dir, file_path.name
            )

            shutil.move(str(file_path), str(destination_path))

            results.setdefault(category, []).append(destination_path.name)

        return results


# ----------------------------------------------------------------------
# Path helpers
# ----------------------------------------------------------------------
def get_project_root() -> Path:
    """Determine the project root regardless of the current working directory.

    The project root is defined as the parent directory of `src/`, i.e.
    two levels up from this file (src/organizer.py -> project root).
    """
    return Path(__file__).resolve().parent.parent


def print_report(results: Dict[str, List[str]]) -> None:
    """Print a simple, human-readable summary of the organizing run."""
    if not results:
        print("No files found to organize. data/input/ has no loose files.")
        return

    total_files = sum(len(files) for files in results.values())
    print(f"Organized {total_files} file(s) into {len(results)} categor"
          f"{'y' if len(results) == 1 else 'ies'}:\n")

    for category, files in sorted(results.items()):
        print(f"  {category}/ ({len(files)})")
        for file_name in files:
            print(f"    - {file_name}")


def main() -> None:
    project_root = get_project_root()
    input_dir = project_root / "data" / "input"
    config_path = project_root / "config" / "categories.json"

    organizer = FileOrganizer(input_dir=input_dir, config_path=config_path)
    results = organizer.organize()
    print_report(results)


if __name__ == "__main__":
    main()
