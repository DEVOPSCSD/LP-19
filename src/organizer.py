"""
Automatic File Organizer
------------------------
Core orchestration module for the Automatic File Organizer system.

Coordinates:
    - File classification (src/classifier.py)
    - Safe file movement without overwrite (src/mover.py)
    - Duplicate filename handling (src/duplicate_handler.py)
    - Application event logging (src/logger.py)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from .backup import backup_files
from .classifier import FileClassifier, OTHERS_CATEGORY
from .duplicate_handler import resolve_duplicate_path
from .logger import setup_logger, get_logger
from .mover import FileMover, MoveResult


class FileOrganizer:
    """Organizes loose files in a configurable directory into category folders.

    Attributes:
        source_dir: Directory containing files to organize (also aliased as input_dir).
        config_path: Optional path to JSON categories config.
        classifier: FileClassifier instance for category detection.
        logger: Logger for recording organization events.
    """

    def __init__(
        self,
        source_dir: Optional[Union[str, Path]] = None,
        config_path: Optional[Union[str, Path]] = None,
        logger: Optional[logging.Logger] = None,
        log_file: Optional[Union[str, Path]] = None,
        input_dir: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> None:
        target_dir = source_dir if source_dir is not None else input_dir
        if target_dir is None:
            target_dir = get_project_root() / "data" / "input"
        self.source_dir = Path(target_dir)
        self.input_dir = self.source_dir  # Alias for backward compatibility
        self.config_path = Path(config_path) if config_path else None

        # Setup logging
        if logger is not None:
            self.logger = logger
        elif log_file is not None:
            self.logger = setup_logger(log_file=log_file)
        else:
            self.logger = get_logger()

        # Validate inputs
        self._validate_config_exists()
        self._validate_source_dir_exists()

        # Initialize modular classifier
        self.classifier = FileClassifier(config_path=self.config_path)
        # Expose category_map for backward compatibility with existing tests
        self.category_map = self.classifier.category_map

        # Statistics from latest run
        self.last_stats: Dict[str, Any] = {
            "total_processed": 0,
            "files_organized": 0,
            "backup_count": 0,
            "duplicate_count": 0,
            "failed_count": 0,
            "category_counts": {},
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_config_exists(self) -> None:
        """Validate config file exists if explicitly specified."""
        if self.config_path is not None and not self.config_path.is_file():
            self.logger.error("Configuration file not found: %s", self.config_path)
            raise FileNotFoundError(
                f"Category configuration file not found: {self.config_path}"
            )

    def _validate_source_dir_exists(self) -> None:
        """Validate source directory exists and is a folder."""
        if not self.source_dir.is_dir():
            self.logger.error("Source directory not found: %s", self.source_dir)
            raise NotADirectoryError(
                f"Input directory not found: {self.source_dir}"
            )

    def _validate_input_dir_exists(self) -> None:
        """Backward-compatible alias for _validate_source_dir_exists."""
        self._validate_source_dir_exists()

    # ------------------------------------------------------------------
    # Category detection
    # ------------------------------------------------------------------
    def get_category(self, file_path: Union[str, Path]) -> str:
        """Determine category for given file path using the classifier."""
        return self.classifier.get_category(file_path)

    def _resolve_destination(self, destination_dir: Path, file_name: str) -> Path:
        """Backward-compatible wrapper for duplicate path resolution."""
        path, _ = resolve_duplicate_path(destination_dir, file_name)
        return path

    # ------------------------------------------------------------------
    # Directory Scanning
    # ------------------------------------------------------------------
    def _iter_input_files(self) -> Iterator[Path]:
        """Yield only top-level files in source_dir.

        Subdirectories (such as previously created category folders) are
        skipped so the organizer never recursively reorganizes existing folders.
        """
        try:
            entries = sorted(self.source_dir.iterdir())
        except OSError as exc:
            self.logger.error("Failed to read source directory %s: %s", self.source_dir, exc)
            return

        for entry in entries:
            try:
                if entry.is_file():
                    yield entry
            except OSError as exc:
                self.logger.error("Error accessing entry %s: %s", entry.name, exc)
                continue

    # ------------------------------------------------------------------
    # Core Organization Flow
    # ------------------------------------------------------------------
    def organize(self) -> Dict[str, List[str]]:
        """Scan source directory and move loose files into category folders.

        Records:
            - Application start
            - Directory scan
            - Files detected
            - Files moved
            - Duplicate filename handling
            - Errors
            - Application completion

        Returns:
            Dictionary mapping category names to list of organized file names.
        """
        self.logger.info("=== Automatic File Organizer Started ===")
        self.logger.info("Scanning directory: %s", self.source_dir.resolve())

        # Collect loose files
        detected_files = list(self._iter_input_files())
        self.logger.info("Files detected: %d loose file(s)", len(detected_files))

        results: Dict[str, List[str]] = {}
        failed_count = 0
        renamed_count = 0

        if not detected_files:
            self.logger.info("No loose files found to organize.")
            self.logger.info("=== Application Completed ===")
            return results

        # Process each file individually to ensure resilience
        for file_path in detected_files:
            try:
                category = self.get_category(file_path)
                category_dir = self.source_dir / category

                move_result: MoveResult = FileMover.move_file(
                    source_path=file_path, destination_dir=category_dir
                )

                if move_result.success and move_result.destination_path:
                    final_name = move_result.destination_path.name
                    if move_result.was_renamed:
                        renamed_count += 1
                        self.logger.info(
                            "Duplicate filename handled: '%s' renamed to '%s' in '%s/'",
                            file_path.name,
                            final_name,
                            category,
                        )
                    self.logger.info(
                        "File successfully moved: '%s' -> '%s/%s'",
                        file_path.name,
                        category,
                        final_name,
                    )
                    results.setdefault(category, []).append(final_name)
                else:
                    failed_count += 1
                    self.logger.error(
                        "Failed to move file '%s': %s",
                        file_path.name,
                        move_result.error_message,
                    )

            except Exception as exc:  # pylint: disable=broad-except
                failed_count += 1
                self.logger.error(
                    "Unexpected exception while processing '%s': %s",
                    file_path.name,
                    exc,
                )
                continue

        total_moved = sum(len(files) for files in results.values())
        
        # Populate comprehensive stats
        category_counts: Dict[str, int] = {}
        standard_categories = [
            "Images", "Documents", "PDFs", "Videos", "Audio", "Source Code", "Archives", "Others"
        ]
        for cat in standard_categories:
            alt_cat = cat.replace(" ", "_")
            count = len(results.get(cat, [])) + (len(results.get(alt_cat, [])) if alt_cat != cat else 0)
            category_counts[cat] = count

        for cat, files in results.items():
            clean_cat = cat.replace("_", " ")
            if clean_cat not in category_counts:
                category_counts[clean_cat] = len(files)

        self.last_stats = {
            "total_processed": len(detected_files),
            "files_organized": total_moved,
            "backup_count": 0,
            "duplicate_count": renamed_count,
            "failed_count": failed_count,
            "category_counts": category_counts,
        }

        self.logger.info(
            "=== Application Completed | Moved: %d, Duplicates Renamed: %d, Failed: %d ===",
            total_moved,
            renamed_count,
            failed_count,
        )
        return results

    def organize_with_backup(
        self,
        backup_dir: Union[str, Path],
        backup_log: Optional[Union[str, Path]] = None,
    ) -> Dict[str, List[str]]:
        """Back up all loose files first, and only organize if backup succeeds.

        Args:
            backup_dir: Destination directory for backups.
            backup_log: Optional log file for backup activity.

        Returns:
            Dictionary mapping category names to list of organized file names.

        Raises:
            SystemExit: If one or more files fail to back up.
        """
        dest_backup_dir = Path(backup_dir)
        self.logger.info("Backup requested before organization.")
        self.logger.info("Backup destination: %s", dest_backup_dir.resolve())

        backup_result = backup_files(
            input_dir=self.source_dir,
            backup_dir=dest_backup_dir,
            log_file=Path(backup_log) if backup_log else None,
        )
        print(f"Backed up {len(backup_result.backed_up)} file(s) to {dest_backup_dir}")

        if not backup_result.success:
            for file_path, message in backup_result.failed:
                print(f"  BACKUP FAILED: {file_path.name} ({message})")
            print(
                "Organizing cancelled: some files could not be backed up. "
                f"See {backup_log or 'backup log'}"
            )
            self.logger.error(
                "Organizing cancelled: %d file(s) failed to back up.",
                len(backup_result.failed),
            )
            sys.exit(1)

        self.logger.info(
            "Backup succeeded (%d file(s) backed up). Proceeding to organize files.",
            len(backup_result.backed_up),
        )
        results = self.organize()
        self.last_stats["backup_count"] = len(backup_result.backed_up)
        return results


# ----------------------------------------------------------------------
# Helper Utilities
# ----------------------------------------------------------------------
def get_project_root() -> Path:
    """Determine the project root directory relative to this script."""
    return Path(__file__).resolve().parent.parent


def print_report(results: Dict[str, List[str]]) -> None:
    """Print human-readable summary of organized files."""
    if not results:
        print("\nNo files found to organize. The directory has no loose files.\n")
        return

    total_files = sum(len(files) for files in results.values())
    print(f"\n==========================================")
    print(f"      File Organization Summary")
    print(f"==========================================")
    print(f"Total files organized: {total_files} into {len(results)} category/categories:\n")

    for category, files in sorted(results.items()):
        print(f"  [{category}] ({len(files)} files)")
        for file_name in files:
            print(f"    - {file_name}")
    print("==========================================\n")


def main(
    source_dir: Optional[Union[str, Path]] = None,
    config_path: Optional[Union[str, Path]] = None,
    backup: bool = True,
    backup_dir: Optional[Union[str, Path]] = None,
    backup_log: Optional[Union[str, Path]] = None,
    log_file: Optional[Union[str, Path]] = None,
    input_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> Dict[str, List[str]]:
    """Entry point for running file organizer programmatically or via CLI."""
    project_root = get_project_root()
    default_input_dir = project_root / "data" / "input"
    resolved_source = source_dir if source_dir is not None else input_dir
    target_dir = Path(resolved_source) if resolved_source else default_input_dir
    target_config = Path(config_path) if config_path else (project_root / "config" / "categories.json")
    target_backup_dir = Path(backup_dir) if backup_dir else (project_root / "backup")
    target_backup_log = Path(backup_log) if backup_log else (project_root / "logs" / "backup.log")
    target_log_file = Path(log_file) if log_file else (project_root / "logs" / "organizer.log")

    # Ensure input directory exists for quick runs
    target_dir.mkdir(parents=True, exist_ok=True)

    organizer = FileOrganizer(
        source_dir=target_dir,
        config_path=target_config,
        log_file=target_log_file,
    )

    if backup:
        results = organizer.organize_with_backup(
            backup_dir=target_backup_dir,
            backup_log=target_backup_log,
        )
    else:
        results = organizer.organize()

    print_report(results)
    return results


if __name__ == "__main__":
    main()