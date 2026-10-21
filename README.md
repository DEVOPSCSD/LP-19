# Automatic File Organizer & Backup System

**College DevOps Project**  
**Team No:** 19  
**Student Roll Nos:**
- `24P61A67I8`
- `24P61A67I9`
- `24P61A67J0`

---

## 1. Project Overview

The **Automatic File Organizer & Backup System** (Team 19) is an enterprise-grade, safety-first Python software engineering and DevOps project. It automatically scans loose, unorganized files in a target directory and safely categorizes them into dedicated folders based on their file extensions.

To provide maximum flexibility and accessibility, the system supports two operational modes built on the exact same core business logic:
1. **Command-Line Interface (CLI):** Fast, headless batch processing via `src/main.py`.
2. **Browser-Based Web Interface:** Modern, responsive Flask dashboard via `src/web_app.py` allowing users to upload files, choose organization strategies, inspect category counts, and monitor application logs in real time.

### Core Architectural Guarantees:
- **Zero Overwriting:** Name collisions are resolved sequentially (e.g., `invoice.pdf` $\rightarrow$ `invoice_1.pdf` $\rightarrow$ `invoice_2.pdf`).
- **Zero Accidental Deletions:** Moving is executed safely using atomic filesystem operations.
- **Fail-Safe Backup:** When backup mode is selected, loose files are copied to a designated backup repository before any file moving occurs. If backup fails for any file, organization immediately aborts.
- **Non-Recursive Isolation:** Category subfolders are never recursed into, preventing nested organization cycles.
- **Single Source of Truth:** The Flask web interface directly reuses `src/organizer.py` and `src/backup.py` without duplicating file classification or movement algorithms.

---

## 2. System Architecture

```
                               +------------------------------------------+
                               |           User / Web Browser             |
                               |         http://127.0.0.1:5000/           |
                               +--------------------+---------------------+
                                                    |
                                                    | HTTP (Upload / Actions)
                                                    v
                               +------------------------------------------+
                               |            Flask Web Backend             |
                               |             (src/web_app.py)             |
                               +--------------------+---------------------+
                                                    |
                                                    | Invokes Core Engine
                                                    v
+-------------------------------+      +----------------------------------+
|          CLI Entrypoint       | ---> |       FileOrganizer Engine       |
|         (src/main.py)         |      |        (src/organizer.py)        |
+-------------------------------+      +--+---------+----------+-------+--+
                                          |         |          |       |
                 +------------------------+         |          |       +------------------------+
                 |                                  |          |                                |
                 v                                  v          v                                v
+----------------------------------+   +------------+----+   +-+----------------+   +-----------+------+
|          FileClassifier          |   |    FileMover    |   | DuplicateHandler |   |   Backup Manager |
|        (src/classifier.py)       |   |  (src/mover.py) |   |  (duplicate_     |   |   (src/backup.py)|
|   Maps ext to category folders   |   | Safe filesystem |   |   handler.py)    |   | Copies loose     |
|   from config/categories.json    |   | file relocation |   | Appends _1, _2   |   | files before move|
+----------------------------------+   +-----------------+   +------------------+   +------------------+
                 |                                  |                  |                        |
                 +----------------------------------+------------------+------------------------+
                                                    |
                                                    v
                               +------------------------------------------+
                               |         Host / Container Storage         |
                               |  data/web_input/  data/web_backup/ logs/ |
                               +------------------------------------------+
```

---

## 3. Initial File Categories

Classification is case-insensitive and configured in [`config/categories.json`](file:///C:/Users/vaibh/OneDrive/Desktop/LP-19/config/categories.json):

| Category | Extensions Handled | Example Files |
| :--- | :--- | :--- |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` | `photo.png`, `avatar.jpg` |
| **Documents** | `.doc`, `.docx`, `.txt`, `.odt` | `notes.txt`, `resume.docx` |
| **PDFs** | `.pdf` | `annual_report.pdf`, `manual.pdf` |
| **Videos** | `.mp4`, `.avi`, `.mkv`, `.mov` | `tutorial.mp4`, `movie.mkv` |
| **Audio** | `.mp3`, `.wav`, `.flac` | `song.mp3`, `podcast.wav` |
| **Source_Code** | `.py`, `.java`, `.c`, `.cpp`, `.js`, `.html`, `.css` | `script.py`, `app.java` |
| **Archives** | `.zip`, `.rar`, `.7z` | `backup.zip`, `data.7z` |
| **Others** | All unsupported or missing extensions | `mystery.xyz`, `payload.bin` |

---

## 4. Project Structure

```
LP-19/
|-- config/
|   `-- categories.json          # Extension-to-category mapping configuration
|-- data/
|   |-- input/                   # Default source directory for CLI loose files
|   |-- web_input/               # Controlled staging directory for web uploads
|   `-- web_backup/              # Backup directory for web operations
|-- logs/
|   |-- organizer.log            # CLI application runtime log file
|   `-- web_app.log              # Web interface runtime log file
|-- screenshots/
|   `-- selenium_success.png     # Automated Selenium test proof screenshot
|-- src/
|   |-- __init__.py              # Package exports
|   |-- backup.py                # Standalone backup engine
|   |-- classifier.py            # File classification logic & config loading
|   |-- duplicate_handler.py     # Safe duplicate renaming (_1, _2)
|   |-- logger.py                # Structured console & file logging
|   |-- main.py                  # CLI application entry point
|   |-- mover.py                 # Atomic file relocation & permissions handling
|   |-- organizer.py             # Core FileOrganizer orchestration class
|   `-- web_app.py               # Flask web dashboard application
|-- static/
|   |-- style.css                # Professional college-project styling
|   `-- script.js                # Drag & drop upload and dynamic preview
|-- templates/
|   `-- index.html               # Web dashboard HTML template
|-- tests/
|   |-- __init__.py
|   |-- test_backup.py           # Unit tests for backup engine
|   |-- test_classifier.py       # Unit tests for classification rules
|   |-- test_cli.py              # Tests for CLI entry point and flags
|   |-- test_duplicate_handler.py# Tests for collision handling
|   |-- test_mover.py            # Tests for safe file movement
|   |-- test_organizer.py        # Integration tests for FileOrganizer
|   |-- test_web_app.py          # PyTest suite for Flask web endpoints
|   `-- selenium/
|       |-- __init__.py
|       |-- test_web_ui.py       # Selenium end-to-end browser test
|       `-- test_data/
|           `-- test_document.txt# Isolated safe test document
|-- docker-entrypoint.sh         # Smart container dispatcher (Web vs CLI)
|-- Dockerfile                   # Multi-purpose containerization setup
|-- Jenkinsfile                  # CI/CD declarative pipeline
|-- requirements.txt             # Runtime dependencies (Flask)
|-- requirements-dev.txt         # Dev/test dependencies (pytest, selenium)
`-- README.md                    # Project documentation
```

---

## 5. Requirements & Installation

- **Python Version:** Python 3.10 or newer (tested on Python 3.13)
- **Web Browser (for Selenium):** Google Chrome (handled via Selenium Manager)

### Setup Virtual Environment & Dependencies
```powershell
# 1. Clone repository
git clone <repository-url>
cd LP-19

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install runtime and development dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

---

## 6. Web Application Usage

### Starting the Flask Web Application
To start the web server locally:
```powershell
python src/web_app.py
```
By default, the application binds to `0.0.0.0` on port `5000`.

### Accessing the Web Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

### Web User Workflow
1. **Upload Files:**
   - Drag and drop files onto the staging dropzone or click to select multiple files.
   - The interface displays the selected file names and sizes before upload.
   - Click **Upload to Staging Folder**. Files are securely staged in `data/web_input/` with duplicate collision avoidance (`_1`, `_2`).
2. **Execute Organization Strategy:**
   - **Organize Files:** Moves loose files in `data/web_input/` directly into category folders (`Images/`, `Documents/`, etc.).
   - **Backup & Organize:** Creates copies of all loose files in `data/web_backup/` first, and proceeds to organize only when backup succeeds.
3. **Inspect Results:**
   - **Metric Counters:** Total Files Processed, Files Organized, Backup Count, Duplicate Count, and Failed Count.
   - **Category Results Cards:** Real-time counts for *Images*, *Documents*, *PDFs*, *Videos*, *Audio*, *Source Code*, *Archives*, and *Others*.
4. **Recent Activity & Logs:**
   - Real-time terminal log viewer embedded in the dashboard.
   - Link to `GET /logs` for raw text log download.

### Web API Endpoints
| HTTP Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Renders the web dashboard with staged files, categories, metrics, and logs |
| `POST` | `/upload` | Staging file upload handler (`multipart/form-data`) |
| `POST` | `/organize` | Triggers file classification and movement into category folders |
| `POST` | `/backup-organize` | Creates backup in `data/web_backup/` then organizes loose files |
| `POST` | `/backup` | Backward-compatible alias for `/backup-organize` |
| `POST` | `/organize-download` | Backs up, organizes staged files, packages into a clean ZIP archive, and downloads `LP19_organized_files.zip` |
| `GET` | `/results` | Returns JSON summary of the latest operation metrics |
| `GET` | `/logs` | Returns raw text content of `logs/web_app.log` |

---

## Organize & Download ZIP

The **Organize & Download ZIP** feature allows users to upload files, organize them into category folders with safety backups, and instantly download the structured result as a single clean ZIP archive directly through their browser.

### Workflow:
1. **Open the web application:** Navigate to `http://127.0.0.1:5000/`.
2. **Upload unorganized files:** Drag & drop or select files in the staging area and click **Upload to Staging Folder**.
3. **Click "Organize & Download ZIP":** Click the **📦 Organize & Download ZIP** button (`id="organize-download-btn"`).
4. **The application organizes the files:** Files are classified and moved into dedicated category folders (`Images/`, `Documents/`, `PDFs/`, etc.) with automatic duplicate renaming (`_1`, `_2`).
5. **Backup copies are created when applicable:** Original uploaded files are safely backed up before file movement begins (fail-safe protection: if backup fails, organization aborts).
6. **A ZIP file is generated:** A clean, temporary ZIP package containing both the organized folder hierarchy and backup copies is assembled in-memory.
7. **The browser downloads `LP19_organized_files.zip`:** The browser initiates an automatic download of `LP19_organized_files.zip`.

### Sample Downloaded ZIP Structure:
```
LP19_organized_files.zip
|-- Organized/
|   |-- Images/
|   |   `-- photo.jpg
|   |-- Documents/
|   |   `-- notes.txt
|   |-- PDFs/
|   |   `-- report.pdf
|   |-- Audio/
|   |   `-- song.mp3
|   |-- Videos/
|   |   `-- movie.mp4
|   |-- Source_Code/
|   |   `-- program.py
|   |-- Archives/
|   |   `-- archive.zip
|   `-- Others/
|       `-- unknown.xyz
`-- Backup/
    |-- photo.jpg
    |-- notes.txt
    |-- report.pdf
    |-- song.mp3
    `-- program.py
```

> **Note:** The ZIP archive contains strictly user files and backup copies. Internal files such as `.git`, `__pycache__`, virtual environments, logs, and temporary files are excluded.

### API Endpoint:
- **Endpoint:** `POST /organize-download`
- **Request:** Triggers organization and ZIP download of staged files.
- **Response:** `200 OK` with `Content-Type: application/zip`, `Content-Disposition: attachment; filename=LP19_organized_files.zip`.
- **Validation:** Returns `400 Bad Request` if no loose files are present in the staging directory.
- **Fail-Safe:** Aborts immediately if backup copy fails, preserving all original files.

---

## 7. Command-Line Interface (CLI) Usage

The existing CLI functionality is completely preserved.

### Organize Only (Without Backup)
```powershell
python src/main.py --source "data/input"
```

### Backup First, Then Organize
```powershell
python src/main.py --source "data/input" --backup
```

### Custom Directories
```powershell
python src/main.py --source "data/input" --backup --backup-dir "custom_backup" --log "logs/custom.log"
```

### View CLI Help
```powershell
python src/main.py --help
```

---

## 8. Automated Testing

### 1. PyTest Test Suite
Run all unit and integration tests (100+ tests):
```powershell
python -m pytest -v
```

### 2. Selenium Automated UI Browser Testing
The Selenium test verifies the actual running Flask webpage end-to-end:
```powershell
python -m pytest tests/selenium/test_web_ui.py -v
```
*(Or execute directly)*:
```powershell
python tests/selenium/test_web_ui.py
```

#### Selenium Test Workflow:
1. Spawns background live Flask server on `http://127.0.0.1:5000/`.
2. Launches headless Chrome via Selenium WebDriver (using automated Selenium Manager).
3. Navigates to `http://127.0.0.1:5000/` and verifies application header and subtitle.
4. Uploads safe test document from `tests/selenium/test_data/test_document.txt`.
5. Clicks **📦 Organize & Download ZIP** (`id="organize-download-btn"`).
6. Uses explicit waits (`wait_for_download`) to confirm the ZIP file completes downloading.
7. Verifies the downloaded ZIP filename begins with `LP19_organized_files` and is a valid ZIP archive.
8. Verifies that the ZIP contents include `Organized/` category folders and `Backup/`.
9. Confirms UI success feedback (`Organization completed successfully. Your ZIP file is downloading.`).
8. Captures and saves high-resolution verification screenshot to:
   ```
   screenshots/selenium_success.png
   ```

---

## 9. Docker Containerization

The application is containerized using `python:3.12-slim` with a smart entrypoint script ([`docker-entrypoint.sh`](file:///C:/Users/vaibh/OneDrive/Desktop/LP-19/docker-entrypoint.sh)).

### 1. Build Docker Image
```powershell
docker build -t lp19-file-organizer .
```

### 2. Run Web Application in Docker (Default)
To run the Flask web application exposing port 5000:
```powershell
docker run --rm -p 5000:5000 `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/backup:/app/backup" `
  -v "${PWD}/logs:/app/logs" `
  lp19-file-organizer
```
Access in your browser: `http://127.0.0.1:5000/`.

### 3. Run CLI in Docker (Backward Compatible)
Passing CLI arguments automatically routes to `src/main.py`:
```powershell
# View CLI help
docker run --rm lp19-file-organizer --help

# Organize with backup
docker run --rm `
  -v "${PWD}/data/input:/app/data/input" `
  -v "${PWD}/backup:/app/backup" `
  -v "${PWD}/logs:/app/logs" `
  lp19-file-organizer --backup
```

---

## 10. Jenkins CI/CD Pipeline

The declarative [`Jenkinsfile`](file:///C:/Users/vaibh/OneDrive/Desktop/LP-19/Jenkinsfile) orchestrates the complete software delivery lifecycle:

```
+---------------+     +-------------------+     +-------------------------+
| Stage 1:      | --> | Stage 2:          | --> | Stage 3:                |
| Checkout SCM  |     | Environment Setup |     | Automated PyTest (100+) |
+---------------+     +-------------------+     +------------+------------+
                                                             |
+------------------------------------------------------------+
|
v
+---------------+     +---------------------------------------------------+     +------------------+
| Stage 4:      | --> | Stage 5:                                          | --> | Post-Build:      |
| Docker Build  |     | Docker Verification & Web Container Smoke Test    |     | Publish Reports  |
+---------------+     | (CLI smoke test, port 5000 check, Selenium if UI) |     | & Clean Artifacts|
                      +---------------------------------------------------+     +------------------+
```

### Pipeline Stages:
1. **Checkout:** Checks out Git repository.
2. **Environment Setup:** Installs `requirements.txt` and `requirements-dev.txt`.
3. **Automated Testing:** Runs `pytest` generating `test-results.xml`. If any test fails, pipeline halts immediately before building Docker images.
4. **Docker Build:** Builds `lp19-file-organizer:${BUILD_NUMBER}` and `latest`.
5. **Docker Verification & Web Container:**
   - Runs `--help` CLI validation in container.
   - Runs synthetic volume-mount organize & backup smoke test.
   - Launches web container in background on port `5000` and validates HTTP response.
   - Conditionally executes Selenium tests if Google Chrome is available on the CI runner.
   - Cleans up and stops test web container.
6. **Post-Build:** Publishes JUnit XML test reports across all stages.
