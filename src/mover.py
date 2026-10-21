"""
File Mover Module
-----------------
Handles moving files into their target category folders safely.
Key safety rules:
    - Automatically creates destination directory if it doesn't exist.
    - Prevents overwriting using resolve_duplicate_path.
    - Catches file-level exceptions (PermissionError, FileNotFoundError, OSError)
      and returns structured results so processing can continue for other files.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .duplicate_handler import resolve_duplicate_path


@dataclass
class MoveResult:
    """Represents the outcome of moving a single file.

    Attributes:
        success: True if the file was moved successfully, False otherwise.
        source_path: The original path of the file.
        destination_path: The final path of the file after moving (if successful).
        was_renamed: True if duplicate handling generated a new filename.
        error_message: Error description if the move failed.
    """

    success: bool
    source_path: Path
    destination_path: Optional[Path] = None
    was_renamed: bool = False
    error_message: Optional[str] = None


class FileMover:
    """Manages safe file transfer into target category directories."""

    @staticmethod
    def move_file(
        source_path: Union[str, Path], destination_dir: Union[str, Path]
    ) -> MoveResult:
        """Move a file to destination_dir safely without overwriting.

        Args:
            source_path: Path of file to move.
            destination_dir: Directory where the file should be placed.

        Returns:
            MoveResult indicating success, final destination, whether renamed,
            or error details if failed.
        """
        src = Path(source_path)
        dest_dir = Path(destination_dir)

        # 1. Validate that the source exists and is a regular file
        if not src.exists():
            return MoveResult(
                success=False,
                source_path=src,
                error_message=f"Source file does not exist: {src}",
            )

        if not src.is_file():
            return MoveResult(
                success=False,
                source_path=src,
                error_message=f"Source path is not a file: {src}",
            )

        try:
            # 2. Ensure destination directory exists
            dest_dir.mkdir(parents=True, exist_ok=True)

            # 3. Resolve destination path to avoid overwriting existing files
            target_path, was_renamed = resolve_duplicate_path(dest_dir, src.name)

            # 4. Perform the file move
            shutil.move(str(src), str(target_path))

            return MoveResult(
                success=True,
                source_path=src,
                destination_path=target_path,
                was_renamed=was_renamed,
            )

        except PermissionError as exc:
            return MoveResult(
                success=False,
                source_path=src,
                error_message=f"Permission denied while moving {src.name}: {exc}",
            )
        except OSError as exc:
            return MoveResult(
                success=False,
                source_path=src,
                error_message=f"OS error while moving {src.name}: {exc}",
            )
        except Exception as exc:  # pylint: disable=broad-except
            return MoveResult(
                success=False,
                source_path=src,
                error_message=f"Unexpected error while moving {src.name}: {exc}",
            )
