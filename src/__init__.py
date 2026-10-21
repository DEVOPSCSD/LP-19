"""
Automatic File Organizer & Backup System
Team No: 19
Roll Nos: 24P61A67I8, 24P61A67I9, 24P61A67J0
"""

from .classifier import FileClassifier, OTHERS_CATEGORY, DEFAULT_CATEGORIES
from .duplicate_handler import resolve_duplicate_path
from .mover import FileMover, MoveResult
from .logger import setup_logger, get_logger
from .organizer import FileOrganizer

__all__ = [
    "FileOrganizer",
    "FileClassifier",
    "FileMover",
    "MoveResult",
    "resolve_duplicate_path",
    "setup_logger",
    "get_logger",
    "OTHERS_CATEGORY",
    "DEFAULT_CATEGORIES",
]
