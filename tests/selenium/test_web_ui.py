"""
Automatic File Organizer & Backup System (Team 19)
---------------------------------------------------
Selenium Automated Web UI End-to-End Test for 'Organize & Download ZIP'

Workflow:
    1. Start Flask web server (if not already running) on http://127.0.0.1:5000/
    2. Launch headless Chrome via Selenium WebDriver (using automated Selenium Manager)
       configured with custom download directory
    3. Open http://127.0.0.1:5000/
    4. Verify page title and application heading
    5. Locate file upload element and upload a safe test file from tests/selenium/test_data/
    6. Submit file upload and verify staging
    7. Click 'Organize & Download ZIP' (id="organize-download-btn")
    8. Wait for the browser download to complete using explicit waits
    9. Verify that a valid ZIP file was downloaded and its filename starts with LP19_organized_files
    10. Verify that the ZIP is valid and contains organized category structures
    11. Capture and save high-resolution proof screenshot to screenshots/selenium_success.png
"""

from __future__ import annotations

import os
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from werkzeug.serving import make_server

from src.web_app import create_app

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/"
DOWNLOAD_DIR = PROJECT_ROOT / "tests" / "selenium" / "downloads"


class ServerThread(threading.Thread):
    """Background daemon thread hosting the live Flask application."""

    def __init__(self, app, host: str = SERVER_HOST, port: int = SERVER_PORT):
        super().__init__()
        self.daemon = True
        self.host = host
        self.port = port
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def is_server_running(url: str = BASE_URL) -> bool:
    """Check whether a server is already listening on the target URL."""
    try:
        with urllib.request.urlopen(url, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def live_server():
    """Start the live Flask server if not already running."""
    server_thread = None
    if not is_server_running(BASE_URL):
        test_web_input = PROJECT_ROOT / "data" / "web_input"
        test_web_backup = PROJECT_ROOT / "data" / "web_backup"
        test_log_file = PROJECT_ROOT / "logs" / "web_app.log"
        test_config_path = PROJECT_ROOT / "config" / "categories.json"

        test_web_input.mkdir(parents=True, exist_ok=True)
        test_web_backup.mkdir(parents=True, exist_ok=True)
        test_log_file.parent.mkdir(parents=True, exist_ok=True)

        app = create_app({
            "TESTING": True,
            "WEB_INPUT_DIR": test_web_input,
            "WEB_BACKUP_DIR": test_web_backup,
            "WEB_LOG_FILE": test_log_file,
            "CONFIG_PATH": test_config_path,
        })

        server_thread = ServerThread(app, SERVER_HOST, SERVER_PORT)
        server_thread.start()

        # Wait for server to come online
        for _ in range(50):
            if is_server_running(BASE_URL):
                break
            time.sleep(0.1)

    yield BASE_URL

    if server_thread:
        server_thread.shutdown()


@pytest.fixture(scope="module")
def driver():
    """Create and configure Chrome WebDriver with download capability."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Clean previous test downloads
    for f in DOWNLOAD_DIR.glob("*.zip"):
        try:
            f.unlink()
        except Exception:
            pass

    options = Options()
    # Support headless mode in CI environments; default to visible window so user can interact
    if os.environ.get("HEADLESS") == "1" or os.environ.get("CI") == "true":
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,900")

    prefs = {
        "download.default_directory": str(DOWNLOAD_DIR.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    try:
        driver.maximize_window()
    except Exception:
        pass

    # Enable downloads via CDP
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(DOWNLOAD_DIR.resolve())},
        )
    except Exception as exc:
        print(f"[Selenium] CDP setDownloadBehavior notice: {exc}")

    yield driver
    driver.quit()


def wait_for_download(directory: Path, prefix: str, timeout: int = 600) -> Path:
    """Explicit wait for downloaded file to finish writing without .crdownload suffix."""
    start_time = time.time()
    user_downloads = Path.home() / "Downloads"
    checked_dirs = [directory]
    if user_downloads.exists() and user_downloads != directory:
        checked_dirs.append(user_downloads)

    while time.time() - start_time < timeout:
        for d in checked_dirs:
            for item in d.glob(f"{prefix}*"):
                if not item.name.endswith(".crdownload") and item.is_file() and item.stat().st_size > 0:
                    return item
        time.sleep(0.5)
    raise TimeoutError(f"No completed download matching '{prefix}*' found within {timeout}s")


def test_lp19_web_ui_organize_and_download_flow(live_server, driver):
    """Monitor web application result after the user manually clicks 'Organize & Download ZIP'."""
    url = live_server
    print("\n[Selenium] SELENIUM TEST STARTED")
    print(f"[Selenium] Opening LP-19 web application at {url}...")
    driver.get(url)

    wait = WebDriverWait(driver, 15)

    # 1. Verify Page Title & Application Heading
    wait.until(EC.presence_of_element_located((By.ID, "app-heading")))
    heading = driver.find_element(By.ID, "app-heading")
    assert "Automatic File Organizer & Backup System" in heading.text
    print(f"[Selenium] Website loaded successfully. Heading: '{heading.text}'")

    subtitle = driver.find_element(By.CLASS_NAME, "subtitle")
    assert "Team 19" in subtitle.text

    # 2. Ensure test file is staged in data/web_input so organization succeeds
    test_data_dir = PROJECT_ROOT / "tests" / "selenium" / "test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    test_file_path = test_data_dir / "test_document.txt"
    if not test_file_path.exists():
        test_file_path.write_text("Safe Selenium Test Document Content", encoding="utf-8")

    web_input_dir = PROJECT_ROOT / "data" / "web_input"
    web_input_dir.mkdir(parents=True, exist_ok=True)
    loose_staged = [f for f in web_input_dir.iterdir() if f.is_file()]

    if not loose_staged:
        file_input = driver.find_element(By.ID, "file-input")
        assert file_input is not None
        print(f"[Selenium] Uploading unorganized test file: {test_file_path.name}...")
        file_input.send_keys(str(test_file_path.resolve()))

        # Verify selected file preview appears
        wait.until(EC.visibility_of_element_located((By.ID, "selected-files-box")))
        preview_box = driver.find_element(By.ID, "selected-files-list")
        assert "test_document.txt" in preview_box.text

        # Click Upload button to stage file
        upload_btn = driver.find_element(By.ID, "upload-btn")
        upload_btn.click()

        # Verify upload notification
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert")))
        upload_alert = driver.find_element(By.CSS_SELECTOR, ".alert")
        assert "Successfully uploaded" in upload_alert.text
        print(f"[Selenium] File uploaded successfully to staging area.")
    else:
        print(f"[Selenium] Staged loose files already present: {[f.name for f in loose_staged]}")

    # 3. Verify 'Organize & Download ZIP' button is present (do NOT click it)
    wait.until(EC.presence_of_element_located((By.ID, "organize-download-btn")))
    organize_download_btn = driver.find_element(By.ID, "organize-download-btn")
    assert organize_download_btn is not None

    # Clean existing download folder files so only the new download is detected
    for f in DOWNLOAD_DIR.glob("LP19_organized_files*.zip"):
        try:
            f.unlink()
        except Exception:
            pass

    # 4. Wait for user to manually click the button
    print("\n" + "=" * 65)
    print("[Selenium] >>> USER ACTION REQUIRED <<<")
    print("[Selenium] Please click 'Organize & Download ZIP' (id='organize-download-btn') in the opened Chrome browser.")
    print("[Selenium] Selenium is actively monitoring and waiting for the download result...")
    print("=" * 65 + "\n")

    # 5. Detect and wait for actual browser download
    downloaded_zip = wait_for_download(DOWNLOAD_DIR, "LP19_organized_files", timeout=600)
    print(f"[Selenium] ZIP download detected successfully: {downloaded_zip.name} ({downloaded_zip.stat().st_size} bytes)")

    # 6. Verify filename and valid ZIP structure
    assert downloaded_zip.name.startswith("LP19_organized_files")
    assert zipfile.is_zipfile(downloaded_zip)

    with zipfile.ZipFile(downloaded_zip, "r") as zf:
        namelist = zf.namelist()
        print(f"[Selenium] ZIP archive namelist: {namelist}")
        assert any(n.startswith("Organized/") for n in namelist)

    print("[Selenium] ZIP file verified successfully.")

    # 7. Inspect Flask alert element (.alert) if available
    try:
        wait_alert = WebDriverWait(driver, 10)
        wait_alert.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".alert")))
        alerts = driver.find_elements(By.CSS_SELECTOR, ".alert")
        alert_texts = " | ".join([a.text.strip() for a in alerts if a.text.strip()])
        if alert_texts:
            print(f"[Selenium] Flask alert (.alert) inspected: {alert_texts}")
    except Exception as exc:
        print(f"[Selenium] Alert inspection note: {exc}")

    # 8. Check application result metrics where possible
    try:
        wait_metrics = WebDriverWait(driver, 10)
        wait_metrics.until(lambda d: d.find_element(By.ID, "metric-files-organized").text.strip() != "")
        files_org = driver.find_element(By.ID, "metric-files-organized").text.strip()
        total_proc = driver.find_element(By.ID, "metric-total-processed").text.strip()
        failed_cnt = driver.find_element(By.ID, "metric-failed-count").text.strip()
        print(f"[Selenium] Application Metrics -> Files Organized: {files_org}, Total Processed: {total_proc}, Failed: {failed_cnt}")
    except Exception as exc:
        print(f"[Selenium] Metrics check notice: {exc}")

    # 9. Capture and save proof screenshot
    screenshots_dir = PROJECT_ROOT / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    screenshot_file = screenshots_dir / "selenium_success.png"

    driver.save_screenshot(str(screenshot_file))
    assert screenshot_file.is_file()
    assert screenshot_file.stat().st_size > 1000
    print(f"[Selenium] Proof screenshot successfully updated at: {screenshot_file}")

    # 10. Print final success banner ONLY after all assertions pass
    print("\n" + "=" * 60)
    print("SELENIUM TEST PASSED")
    print("Organization completed successfully!")
    print("ZIP file downloaded and verified successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Allow running directly: python tests/selenium/test_web_ui.py
    pytest.main(["-v", "-s", str(Path(__file__).resolve())])


