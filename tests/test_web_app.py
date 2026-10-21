"""
Tests for Flask Web Interface (Stage W1)
-----------------------------------------
Verifies routes and behavior of src/web_app.py:
    - GET / (dashboard display)
    - POST /upload (file upload, safe duplicate handling, sanitization)
    - POST /organize (file categorization into controlled folders)
    - POST /backup (backup prior to organization, failure halt)
    - GET /results (operation summary as JSON)
    - GET /logs (view recent application logs)
"""

import io
from pathlib import Path
import zipfile
import pytest

from src.backup import BackupResult
from src.web_app import create_app


@pytest.fixture
def app_and_paths(tmp_path):
    """Create an isolated test application with sandboxed directories."""
    input_dir = tmp_path / "web_input"
    backup_dir = tmp_path / "web_backup"
    log_file = tmp_path / "logs" / "web_app.log"
    config_path = tmp_path / "categories.json"

    input_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Use standard default category configuration
    config_content = """{
        "Documents": [".txt", ".pdf", ".docx"],
        "Images": [".jpg", ".jpeg", ".png", ".gif"],
        "Spreadsheets": [".csv", ".xlsx"]
    }"""
    config_path.write_text(config_content, encoding="utf-8")

    app = create_app({
        "TESTING": True,
        "WEB_INPUT_DIR": input_dir,
        "WEB_BACKUP_DIR": backup_dir,
        "WEB_LOG_FILE": log_file,
        "CONFIG_PATH": config_path,
    })

    return {
        "app": app,
        "client": app.test_client(),
        "input_dir": input_dir,
        "backup_dir": backup_dir,
        "log_file": log_file,
        "config_path": config_path,
    }


def test_dashboard_loads_successfully(app_and_paths):
    """GET / should render the dashboard with status 200."""
    client = app_and_paths["client"]
    response = client.get("/")
    assert response.status_code == 200
    assert b"Automatic File Organizer" in response.data
    assert b"Team 19" in response.data


def test_dashboard_displays_staged_and_categorized_files(app_and_paths):
    """GET / should list loose files and existing categories."""
    input_dir = app_and_paths["input_dir"]
    client = app_and_paths["client"]

    # Create a loose file
    (input_dir / "loose_document.pdf").write_text("dummy", encoding="utf-8")

    # Create an existing category folder with a file
    cat_dir = input_dir / "Documents"
    cat_dir.mkdir(parents=True, exist_ok=True)
    (cat_dir / "organized_1.pdf").write_text("dummy", encoding="utf-8")

    response = client.get("/")
    assert response.status_code == 200
    assert b"loose_document.pdf" in response.data
    assert b"Documents/" in response.data


def test_upload_single_file(app_and_paths):
    """POST /upload should save uploaded file to the staging directory."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    data = {
        "files": (io.BytesIO(b"file content here"), "sample_doc.txt")
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert (input_dir / "sample_doc.txt").is_file()
    assert (input_dir / "sample_doc.txt").read_bytes() == b"file content here"


def test_upload_multiple_files(app_and_paths):
    """POST /upload should save multiple files successfully."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    data = {
        "files": [
            (io.BytesIO(b"pdf data"), "report.pdf"),
            (io.BytesIO(b"image data"), "avatar.png"),
        ]
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert (input_dir / "report.pdf").is_file()
    assert (input_dir / "avatar.png").is_file()


def test_upload_duplicate_renames_safely(app_and_paths):
    """POST /upload should not overwrite existing files, appending _1, _2 suffixes."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    # Pre-existing file
    (input_dir / "data.csv").write_text("original", encoding="utf-8")

    # Upload duplicate file
    data = {
        "files": (io.BytesIO(b"duplicate data"), "data.csv")
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    # Original should be preserved
    assert (input_dir / "data.csv").read_text(encoding="utf-8") == "original"
    # New copy should be data_1.csv
    assert (input_dir / "data_1.csv").is_file()
    assert (input_dir / "data_1.csv").read_bytes() == b"duplicate data"


def test_upload_sanitizes_filename(app_and_paths):
    """POST /upload must sanitize filenames and prevent path traversal."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    data = {
        "files": (io.BytesIO(b"safe"), "../../../traversal_test.txt")
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    # werkzeug secure_filename turns ../../../traversal_test.txt into traversal_test.txt
    assert (input_dir / "traversal_test.txt").is_file()
    # Ensure it didn't write to parent directory
    assert not (input_dir.parent / "traversal_test.txt").exists()


def test_upload_empty_submission(app_and_paths):
    """POST /upload with no files selected should redirect gracefully."""
    client = app_and_paths["client"]
    response = client.post("/upload", data={}, follow_redirects=True)
    assert response.status_code == 200
    assert b"No files found in upload request." in response.data or b"No file was selected" in response.data


def test_organize_files(app_and_paths):
    """POST /organize should move staged files into category folders."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    # Stage loose files
    (input_dir / "doc.txt").write_text("text doc", encoding="utf-8")
    (input_dir / "photo.png").write_text("png image", encoding="utf-8")
    (input_dir / "sheet.csv").write_text("csv sheet", encoding="utf-8")

    response = client.post("/organize", follow_redirects=True)
    assert response.status_code == 200

    # Verify loose files were moved into category folders
    assert not (input_dir / "doc.txt").exists()
    assert (input_dir / "Documents" / "doc.txt").is_file()
    assert (input_dir / "Images" / "photo.png").is_file()
    assert (input_dir / "Spreadsheets" / "sheet.csv").is_file()


def test_backup_and_organize_workflow(app_and_paths):
    """POST /backup should copy files to backup folder before organizing."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]
    backup_dir = app_and_paths["backup_dir"]

    (input_dir / "invoice.pdf").write_text("invoice content", encoding="utf-8")
    (input_dir / "banner.jpg").write_text("banner content", encoding="utf-8")

    response = client.post("/backup", follow_redirects=True)
    assert response.status_code == 200

    # Backups must exist in backup_dir
    assert (backup_dir / "invoice.pdf").is_file()
    assert (backup_dir / "banner.jpg").is_file()

    # Files must also be organized in input_dir
    assert (input_dir / "Documents" / "invoice.pdf").is_file()
    assert (input_dir / "Images" / "banner.jpg").is_file()


def test_backup_organize_endpoint(app_and_paths):
    """POST /backup-organize should back up and organize files."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]
    backup_dir = app_and_paths["backup_dir"]

    (input_dir / "doc_new.txt").write_text("sample document", encoding="utf-8")
    (input_dir / "photo_new.jpg").write_text("sample photo", encoding="utf-8")

    response = client.post("/backup-organize", follow_redirects=True)
    assert response.status_code == 200

    # Verify backups created
    assert (backup_dir / "doc_new.txt").is_file()
    assert (backup_dir / "photo_new.jpg").is_file()

    # Verify organized
    assert (input_dir / "Documents" / "doc_new.txt").is_file()
    assert (input_dir / "Images" / "photo_new.jpg").is_file()


def test_backup_failure_aborts_organization(app_and_paths, monkeypatch):
    """If backup fails, organization must not proceed, keeping loose files intact."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    test_file = input_dir / "critical.txt"
    test_file.write_text("do not move if backup fails", encoding="utf-8")

    def mock_failed_backup(*args, **kwargs):
        res = BackupResult()
        res.failed.append((test_file, "Simulated disk failure"))
        return res

    monkeypatch.setattr("src.web_app.backup_files", mock_failed_backup)

    response = client.post("/backup", follow_redirects=True)
    assert response.status_code == 200
    assert b"Backup failed" in response.data

    # File must still be intact as a loose file, NOT organized into Documents
    assert test_file.is_file()
    assert not (input_dir / "Documents" / "critical.txt").exists()


def test_get_results_endpoint(app_and_paths):
    """GET /results should return latest operation summary as JSON."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    # Initial state
    res = client.get("/results")
    assert res.status_code == 200
    data = res.get_json()
    assert data["operation"] == "None"
    assert "total_processed" in data
    assert "files_organized" in data
    assert "backup_count" in data
    assert "duplicate_count" in data
    assert "failed_count" in data
    assert "category_counts" in data

    # After organize
    (input_dir / "test.txt").write_text("test", encoding="utf-8")
    client.post("/organize")

    res_after = client.get("/results")
    assert res_after.status_code == 200
    data_after = res_after.get_json()
    assert data_after["operation"] == "Organize"
    assert data_after["total_moved"] == 1
    assert data_after["files_organized"] == 1
    assert "Documents" in data_after["details"]
    assert "Documents" in data_after["category_counts"]


def test_get_logs_endpoint(app_and_paths):
    """GET /logs should return raw text content of application log file."""
    client = app_and_paths["client"]
    log_file = app_and_paths["log_file"]

    # Without log file
    res = client.get("/logs")
    assert res.status_code == 200
    assert "No logs recorded yet." in res.data.decode("utf-8")

    # With log content
    log_file.write_text("2026-10-13 | INFO | Organizer executed successfully.\n", encoding="utf-8")
    res2 = client.get("/logs")
    assert res2.status_code == 200
    assert "Organizer executed successfully." in res2.data.decode("utf-8")


def test_organize_download_single_file(app_and_paths):
    """Test 1: POST /organize-download returns a valid downloadable ZIP with organized folders."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    # Stage a test document
    (input_dir / "notes.txt").write_text("sample notes content", encoding="utf-8")

    response = client.post("/organize-download")
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "LP19_organized_files.zip" in response.headers.get("Content-Disposition", "")

    # Validate ZIP integrity and structure
    zf = zipfile.ZipFile(io.BytesIO(response.data))
    namelist = zf.namelist()
    assert "Organized/Documents/notes.txt" in namelist
    assert zf.read("Organized/Documents/notes.txt") == b"sample notes content"


def test_organize_download_multiple_categories(tmp_path):
    """Test 2: Verify multiple categories (.txt, .pdf, .jpg, .mp3, .py) appear in correct folders."""
    input_dir = tmp_path / "web_input"
    backup_dir = tmp_path / "web_backup"
    log_file = tmp_path / "logs" / "web_app.log"
    config_path = tmp_path / "categories.json"

    input_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    config_content = """{
        "Documents": [".txt", ".docx"],
        "PDFs": [".pdf"],
        "Images": [".jpg", ".jpeg", ".png"],
        "Audio": [".mp3", ".wav"],
        "Source_Code": [".py", ".java"]
    }"""
    config_path.write_text(config_content, encoding="utf-8")

    app = create_app({
        "TESTING": True,
        "WEB_INPUT_DIR": input_dir,
        "WEB_BACKUP_DIR": backup_dir,
        "WEB_LOG_FILE": log_file,
        "CONFIG_PATH": config_path,
    })
    client = app.test_client()

    # Stage test files covering each category
    (input_dir / "doc.txt").write_text("text doc", encoding="utf-8")
    (input_dir / "report.pdf").write_text("pdf document", encoding="utf-8")
    (input_dir / "photo.jpg").write_text("jpg image", encoding="utf-8")
    (input_dir / "music.mp3").write_text("audio track", encoding="utf-8")
    (input_dir / "script.py").write_text("python script", encoding="utf-8")

    response = client.post("/organize-download")
    assert response.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(response.data))
    namelist = zf.namelist()
    assert "Organized/Documents/doc.txt" in namelist
    assert "Organized/PDFs/report.pdf" in namelist
    assert "Organized/Images/photo.jpg" in namelist
    assert "Organized/Audio/music.mp3" in namelist
    assert "Organized/Source_Code/script.py" in namelist


def test_organize_download_empty_input(app_and_paths):
    """Test 3: POST /organize-download on empty staging directory returns error 400."""
    client = app_and_paths["client"]
    response = client.post("/organize-download")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No loose files" in data["error"]


def test_organize_download_includes_backup(app_and_paths):
    """Test 4: Verify that downloaded ZIP contains both Organized/ and Backup/ archives."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]
    backup_dir = app_and_paths["backup_dir"]

    (input_dir / "important.txt").write_text("vital data", encoding="utf-8")

    response = client.post("/organize-download")
    assert response.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(response.data))
    namelist = zf.namelist()
    assert "Organized/Documents/important.txt" in namelist
    assert "Backup/important.txt" in namelist
    assert (backup_dir / "important.txt").is_file()


def test_organize_download_duplicate_handling(app_and_paths):
    """Test 5: Verify that duplicate filenames receive suffixes and both are preserved in ZIP."""
    client = app_and_paths["client"]
    input_dir = app_and_paths["input_dir"]

    # Upload first file
    client.post(
        "/upload",
        data={"files": (io.BytesIO(b"original content"), "contract.docx")},
        content_type="multipart/form-data",
    )
    # Upload duplicate file (will be renamed contract_1.docx by existing duplicate handler)
    client.post(
        "/upload",
        data={"files": (io.BytesIO(b"second revision"), "contract.docx")},
        content_type="multipart/form-data",
    )

    response = client.post("/organize-download")
    assert response.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(response.data))
    namelist = zf.namelist()
    assert "Organized/Documents/contract.docx" in namelist
    assert "Organized/Documents/contract_1.docx" in namelist


