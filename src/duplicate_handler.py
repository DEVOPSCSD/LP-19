"""
Duplicate Handler Module
------------------------
Handles duplicate filename collisions safely.
Ensures existing files are never overwritten by generating sequential names:
    report.pdf -> report_1.pdf -> report_2.pdf
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union


def resolve_duplicate_path(
    destination_dir: Union[str, Path], filename: str
) -> Tuple[Path, bool]:
    """Determine a collision-free destination file path.

    If a file with `filename` already exists in `destination_dir`, numeric
    suffixes (_1, _2, _3, ...) are appended before the file extension until
    an unused file path is found.

    Args:
        destination_dir: Target directory path where the file will be placed.
        filename: Original file name (e.g. 'report.pdf').

    Returns:
        A tuple of:
            - resolved_path (Path): Non-conflicting file path in destination_dir.
            - was_renamed (bool): True if the file name had to be changed to
              avoid collision, False if original filename was available.

    Examples:
        - If 'report.pdf' does not exist -> ('.../report.pdf', False)
        - If 'report.pdf' exists -> ('.../report_1.pdf', True)
        - If 'report.pdf' and 'report_1.pdf' exist -> ('.../report_2.pdf', True)
    """
    dest_dir = Path(destination_dir)
    original_target = dest_dir / filename

    if not original_target.exists():
        return original_target, False

    stem = original_target.stem
    suffix = original_target.suffix

    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate, True
        counter += 1
