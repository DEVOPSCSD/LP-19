# Automatic File Organizer & Backup System

## Project Purpose

This project is a college DevOps project. Its long-term goal is to build a
full pipeline around a simple, practical tool: a file organizer that later
grows to include automated backups, containerization, and a CI/CD pipeline.

This repository currently contains **Stage 1** of the project.

## Stage 1 Description

Stage 1 implements the core application logic: a Python program that scans
a folder, identifies files by their extension, and sorts them into category
sub-folders. This stage focuses purely on correct, safe, dependency-free
file organizing — no automation infrastructure yet.

## Features Implemented in Stage 1

- Scans `data/input/` for files.
- Classifies files into categories based on file extension (case-insensitive).
- Reads category-to-extension mappings from an external JSON config file
  (`config/categories.json`), so categories can be edited without touching code.
- Automatically creates category folders as needed:
  - `Images`, `Documents`, `PDFs`, `Code`, `Videos`, `Music`, `Archives`, `Others`
- Routes unrecognized extensions to `Others/`.
- Never overwrites an existing file — duplicate names are automatically
  renamed (`photo_1.jpg`, `photo_2.jpg`, ...).
- Never deletes any file.
- Only processes files directly inside `data/input/`; it does not recurse
  into sub-folders, so it will not re-organize its own category folders.
- Uses project-relative paths only (no hardcoded machine-specific paths),
  so the same code will work locally, in Docker, and in Jenkins later
  without modification.

## Technologies Currently Used

- Python 3.10+
- Standard library only: `pathlib`, `json`, `shutil`

No web frameworks, databases, or cloud services are used in this stage.

## Project Structure

```
automatic-file-organizer/
│
├── src/
│   ├── __init__.py
│   └── organizer.py       # FileOrganizer class + entry point
│
├── config/
│   └── categories.json    # Extension -> category mappings
│
├── data/
│   └── input/              # Drop files here to be organized
│
├── tests/
│   ├── __init__.py
│   └── test_organizer.py  # Automated tests (pytest)
│
├── requirements-dev.txt   # Test dependencies (pytest)
└── README.md
```

## Installation Requirements

- Python 3.10 or newer.
- No external packages are required for Stage 1 (standard library only).

## How to Run the Application

1. Extract the project and open a terminal in the project root
   (the `automatic-file-organizer/` folder).
2. Place some files directly inside `data/input/` (see "Example Input
   Files" below).
3. Run:

   ```bash
   python src/organizer.py
   ```

4. The script will print a summary of what was organized and where.

The script determines the project root automatically from its own file
location, so it can be run from any working directory, e.g.:

```bash
python /full/path/to/automatic-file-organizer/src/organizer.py
```

## Example Input Files

Try placing files such as these into `data/input/` before running the
script:

```
data/input/
├── vacation.jpg
├── notes.txt
├── invoice.pdf
├── script.py
├── movie.mp4
├── song.mp3
├── backup.zip
└── mystery.xyz
```

## Expected Output

After running `python src/organizer.py`, the files above would be moved
into:

```
data/input/
├── Images/
│   └── vacation.jpg
├── Documents/
│   └── notes.txt
├── PDFs/
│   └── invoice.pdf
├── Code/
│   └── script.py
├── Videos/
│   └── movie.mp4
├── Music/
│   └── song.mp3
├── Archives/
│   └── backup.zip
└── Others/
    └── mystery.xyz
```

The console output will list each category and the files moved into it.

## Duplicate-File Behavior

If a file with the same name already exists in the destination category
folder, the new file is **not** overwritten. Instead, it is renamed by
appending an incrementing number before the extension:

```
photo.jpg   -> already exists in Images/
photo.jpg   -> renamed to photo_1.jpg
photo.jpg   -> renamed to photo_2.jpg
```

## Unknown-File Behavior

Any file whose extension is not listed in `config/categories.json` is
moved into the `Others/` category folder instead of being skipped or
causing an error.

## Running the Tests

Automated tests live in `tests/test_organizer.py` and use `pytest`. They
run against isolated temporary directories, so they never touch the real
`data/input/` folder.

1. Install the test dependency:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. From the project root, run:

   ```bash
   pytest
   ```

   For more detail:

   ```bash
   pytest -v
   ```

### What is covered

| Test                     | Expected result                  |
|---------------------------|-----------------------------------|
| `.jpg` file               | `Images/`                        |
| `.png` file                | `Images/`                        |
| `.txt` file                | `Documents/`                     |
| `.pdf` file                | `PDFs/`                          |
| `.py` file                 | `Code/`                          |
| `.mp4` file                | `Videos/`                        |
| `.mp3` file                | `Music/`                         |
| `.zip` file                | `Archives/`                      |
| `.xyz` file (unknown)      | `Others/`                        |
| Duplicate `photo.jpg`      | Renamed to `photo_1.jpg`, no overwrite |
| Second duplicate           | Renamed to `photo_2.jpg`          |
| Uppercase `.JPG`           | Still detected as `Images/`       |
| Empty input folder         | Returns with no crash             |
| Files inside a sub-folder  | Left untouched (no recursion)     |
| Missing config file        | Raises `FileNotFoundError`        |
| Missing input directory    | Raises `NotADirectoryError`       |

## Future Stages

The following are planned for later stages and are **not** implemented yet:

- Automated testing with PyTest
- Backup system
- Logging
- Docker
- Git/GitHub workflow integration
- Jenkins
- CI/CD pipeline
