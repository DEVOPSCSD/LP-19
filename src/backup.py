"""
Automatic File Organizer & Backup System
------------------------------------------
Stage 2: Backup Phase (Member 2)

This module copies every loose file from the input directory into a backup
directory BEFORE the organizer moves anything. Workflow:

    Input files -> Backup files -> Organize files (existing Stage 1 organizer)

Design notes:
    * Only files directly inside the input directory are backed up. This
      matches the organizer, which also ignores sub-directories.
    * Originals are never touched: files are copied (not moved) and keep
      their timestamps (shutil.copy2).
    * Existing backups are never overwritten. On a name collision the new
      copy is saved as `name_1.ext`, `name_2.ext`, ... (same pattern the
      Stage 1 organizer uses).
    * File type does not matter: unknown extensions are backed up like
      everything else.
    * A failure on one file is logged and does not stop the remaining files.
    * Successful backups and errors are written to a log file.
    * Standard library only.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

LOGGER_NAME = "file_organizer.backup"

# Keep the library quiet when no log file is configured.
logging.getLogger(LOGGER_NAME).addHandler(logging.NullHandler())


@dataclass
class BackupResult:
    """Outcome of a backup run.

    Attributes:
        backed_up: (original_path, backup_path) for each file copied.
        failed: (original_path, error_message) for each file that failed.
    """

    backed_up: List[Tuple[Path, Path]] = field(default_factory=list)
    failed: List[Tuple[Path, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True when no file failed to back up."""
        return not self.failed


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def discover_files(input_dir: Path) -> List[Path]:
    """Return the files directly inside `input_dir`, sorted by name.

    Raises:
        NotADirectoryError: if `input_dir` does not exist or is not a folder.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")
    return [entry for entry in sorted(input_dir.iterdir()) if entry.is_file()]


def resolve_backup_path(backup_dir: Path, file_name: str) -> Path:
    """Return a path in `backup_dir` that does not exist yet.

    report.pdf -> report.pdf, then report_1.pdf, report_2.pdf, ...
    """
    candidate = backup_dir / file_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        candidate = backup_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _open_logger(log_file: Optional[Path]):
    """Create the backup logger. Returns (logger, handler_or_None)."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = None
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
    return logger, handler


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def backup_files(
    input_dir: Path,
    backup_dir: Path,
    log_file: Optional[Path] = None,
) -> BackupResult:
    """Copy every file in `input_dir` into `backup_dir`.

    Args:
        input_dir: Directory whose loose files should be backed up.
        backup_dir: Destination directory (created automatically).
        log_file: Optional log file path (e.g. logs/backup.log). Its parent
            folder is created automatically.

    Returns:
        A BackupResult listing the files backed up and any that failed.

    Raises:
        NotADirectoryError: if `input_dir` is missing.
        OSError: if the backup directory cannot be created.
    """
    input_dir = Path(input_dir)
    backup_dir = Path(backup_dir)
    result = BackupResult()

    logger, handler = _open_logger(log_file)
    try:
        if not input_dir.is_dir():
            logger.error("Input directory not found: %s", input_dir)
            raise NotADirectoryError(f"Input directory not found: {input_dir}")

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            logger.error("Could not create backup directory %s: %s",
                         backup_dir, error)
            raise

        files = discover_files(input_dir)
        if not files:
            logger.info("No files found to back up in %s", input_dir)
            return result

        logger.info("Starting backup of %d file(s) from %s", len(files), input_dir)

        for source in files:
            try:
                destination = resolve_backup_path(backup_dir, source.name)
                shutil.copy2(source, destination)
            except (OSError, shutil.Error) as error:
                result.failed.append((source, str(error)))
                logger.error("FAILED to back up %s: %s", source.name, error)
                continue

            result.backed_up.append((source, destination))
            logger.info("Backed up %s -> %s", source.name, destination)

        logger.info("Backup finished: %d succeeded, %d failed",
                    len(result.backed_up), len(result.failed))
        return result
    finally:
        if handler is not None:
            logger.removeHandler(handler)
            handler.close()