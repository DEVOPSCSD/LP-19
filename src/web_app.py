"""
Automatic File Organizer & Backup System
------------------------------------------
Web Interface Application (Stage W1)

A Flask-based web backend providing a browser dashboard for the Automatic
File Organizer and Backup System. Operates strictly within controlled staging
and backup directories (data/web_input and data/web_backup) to prevent
unauthorized or arbitrary file system traversal.

Routes:
    GET  /          - Dashboard showing staged files, categories, and logs
    POST /upload    - Secure upload of one or more files to staging folder
    POST /organize  - Organizes staged files into category folders
    POST /backup    - Backs up loose files then organizes them
    GET  /results   - JSON summary of the latest operation
    GET  /logs      - View raw application log contents
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

try:
    from .backup import backup_files
    from .duplicate_handler import resolve_duplicate_path
    from .organizer import FileOrganizer
except ImportError:
    from src.backup import backup_files
    from src.duplicate_handler import resolve_duplicate_path
    from src.organizer import FileOrganizer


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure the Flask application instance."""
    project_root = Path(__file__).resolve().parent.parent
    template_dir = project_root / "templates"
    static_dir = project_root / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.secret_key = os.environ.get(
        "FLASK_SECRET_KEY", "team19-devops-file-organizer-secret-key"
    )

    # Controlled default paths
    default_input_dir = project_root / "data" / "web_input"
    default_backup_dir = project_root / "data" / "web_backup"
    default_log_file = project_root / "logs" / "web_app.log"
    default_config_path = project_root / "config" / "categories.json"

    app.config.update(
        WEB_INPUT_DIR=default_input_dir,
        WEB_BACKUP_DIR=default_backup_dir,
        WEB_LOG_FILE=default_log_file,
        CONFIG_PATH=default_config_path,
        LATEST_RESULTS=None,
    )

    if test_config:
        app.config.update(test_config)

    # Ensure required directories exist
    web_input_dir = Path(app.config["WEB_INPUT_DIR"])
    web_backup_dir = Path(app.config["WEB_BACKUP_DIR"])
    web_log_file = Path(app.config["WEB_LOG_FILE"])

    web_input_dir.mkdir(parents=True, exist_ok=True)
    web_backup_dir.mkdir(parents=True, exist_ok=True)
    web_log_file.parent.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    # Configure logger handler for web requests
    if not any(isinstance(h, logging.FileHandler) for h in app.logger.handlers):
        file_handler = logging.FileHandler(web_log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

    @app.route("/", methods=["GET"])
    def dashboard():
        """Render main dashboard with loose files, organized folders, and logs."""
        current_input_dir = Path(app.config["WEB_INPUT_DIR"])
        current_log_file = Path(app.config["WEB_LOG_FILE"])

        loose_files = []
        categories: Dict[str, list] = {}

        if current_input_dir.is_dir():
            try:
                for entry in sorted(current_input_dir.iterdir()):
                    if entry.is_file():
                        loose_files.append({
                            "name": entry.name,
                            "size": entry.stat().st_size,
                        })
                    elif entry.is_dir():
                        cat_files = [
                            f.name for f in sorted(entry.iterdir()) if f.is_file()
                        ]
                        categories[entry.name] = cat_files
            except OSError as exc:
                app.logger.error("Error reading web_input directory: %s", exc)

        recent_logs = ""
        if current_log_file.is_file():
            try:
                lines = current_log_file.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
                recent_logs = "\n".join(lines[-50:])
            except Exception as exc:
                recent_logs = f"Error reading log file: {exc}"

        standard_categories = [
            "Images", "Documents", "PDFs", "Videos", "Audio", "Source Code", "Archives", "Others"
        ]

        return render_template(
            "index.html",
            loose_files=loose_files,
            categories=categories,
            latest_results=app.config.get("LATEST_RESULTS"),
            recent_logs=recent_logs,
            standard_categories=standard_categories,
        )

    @app.route("/upload", methods=["POST"])
    def upload_files():
        """Handle file upload into the controlled staging folder."""
        current_input_dir = Path(app.config["WEB_INPUT_DIR"])
        current_input_dir.mkdir(parents=True, exist_ok=True)

        if "files" not in request.files:
            flash("No files found in upload request.", "error")
            return redirect(url_for("dashboard"))

        uploaded_files = request.files.getlist("files")
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            flash("No file was selected for upload.", "error")
            return redirect(url_for("dashboard"))

        uploaded_count = 0
        for file in uploaded_files:
            if not file or not file.filename:
                continue

            clean_filename = secure_filename(file.filename)
            if not clean_filename:
                continue

            destination_path, renamed = resolve_duplicate_path(
                current_input_dir, clean_filename
            )
            try:
                file.save(str(destination_path))
                uploaded_count += 1
                if renamed:
                    app.logger.info(
                        "Uploaded duplicate file renamed: %s -> %s",
                        clean_filename,
                        destination_path.name,
                    )
                else:
                    app.logger.info("Uploaded file staged: %s", destination_path.name)
            except Exception as exc:
                app.logger.error("Failed to save uploaded file %s: %s", clean_filename, exc)

        if uploaded_count > 0:
            flash(
                f"Successfully uploaded {uploaded_count} file(s) to staging area.",
                "success",
            )
        else:
            flash("No valid files could be uploaded.", "error")

        return redirect(url_for("dashboard"))

    @app.route("/organize", methods=["POST"])
    def organize():
        """Organize staged loose files into category subdirectories."""
        current_input_dir = Path(app.config["WEB_INPUT_DIR"])
        current_log_file = Path(app.config["WEB_LOG_FILE"])
        cfg_path = Path(app.config["CONFIG_PATH"])

        current_input_dir.mkdir(parents=True, exist_ok=True)

        try:
            organizer = FileOrganizer(
                source_dir=current_input_dir,
                config_path=cfg_path if cfg_path.is_file() else None,
                log_file=current_log_file,
            )
            results = organizer.organize()
            total_moved = sum(len(files) for files in results.values())
            stats = getattr(organizer, "last_stats", {})

            summary = {
                "operation": "Organize",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "backup_created": False,
                "backup_count": 0,
                "backed_up_count": 0,
                "total_processed": stats.get("total_processed", total_moved),
                "files_organized": stats.get("files_organized", total_moved),
                "total_moved": total_moved,
                "duplicate_count": stats.get("duplicate_count", 0),
                "failed_count": stats.get("failed_count", 0),
                "category_counts": stats.get(
                    "category_counts",
                    {cat: len(files) for cat, files in results.items()}
                ),
                "details": results,
            }
            app.config["LATEST_RESULTS"] = summary

            flash(
                f"Successfully organized {total_moved} file(s) into {len(results)} category/categories.",
                "success",
            )
        except Exception as exc:
            app.logger.error("Organization operation failed: %s", exc)
            flash(f"Organization failed: {exc}", "error")

        return redirect(url_for("dashboard"))

    @app.route("/backup-organize", methods=["POST"])
    @app.route("/backup", methods=["POST"])
    def backup():
        """Back up loose files first, then organize them."""
        current_input_dir = Path(app.config["WEB_INPUT_DIR"])
        current_backup_dir = Path(app.config["WEB_BACKUP_DIR"])
        current_log_file = Path(app.config["WEB_LOG_FILE"])
        cfg_path = Path(app.config["CONFIG_PATH"])

        current_input_dir.mkdir(parents=True, exist_ok=True)
        current_backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Back up files before moving
            backup_result = backup_files(
                input_dir=current_input_dir,
                backup_dir=current_backup_dir,
                log_file=current_log_file,
            )

            if not backup_result.success:
                err_msg = (
                    f"Backup failed for {len(backup_result.failed)} file(s). "
                    "Organization cancelled to prevent data loss."
                )
                app.logger.error(err_msg)
                flash(err_msg, "error")
                return redirect(url_for("dashboard"))

            backed_up_count = len(backup_result.backed_up)

            # 2. Proceed to organize files
            organizer = FileOrganizer(
                source_dir=current_input_dir,
                config_path=cfg_path if cfg_path.is_file() else None,
                log_file=current_log_file,
            )
            results = organizer.organize()
            total_moved = sum(len(files) for files in results.values())
            stats = getattr(organizer, "last_stats", {})

            summary = {
                "operation": "Backup & Organize",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "backup_created": True,
                "backup_count": backed_up_count,
                "backed_up_count": backed_up_count,
                "total_processed": stats.get("total_processed", total_moved),
                "files_organized": stats.get("files_organized", total_moved),
                "total_moved": total_moved,
                "duplicate_count": stats.get("duplicate_count", 0),
                "failed_count": stats.get("failed_count", 0),
                "category_counts": stats.get(
                    "category_counts",
                    {cat: len(files) for cat, files in results.items()}
                ),
                "details": results,
            }
            app.config["LATEST_RESULTS"] = summary

            flash(
                f"Successfully backed up {backed_up_count} file(s) and organized {total_moved} file(s).",
                "success",
            )
        except Exception as exc:
            app.logger.error("Backup & Organize operation failed: %s", exc)
            flash(f"Backup & Organize failed: {exc}", "error")

        return redirect(url_for("dashboard"))

    @app.route("/organize-download", methods=["POST"])
    def organize_and_download():
        """Organize staged loose files, create a backup, and return a downloadable ZIP."""
        current_input_dir = Path(app.config["WEB_INPUT_DIR"])
        current_backup_dir = Path(app.config["WEB_BACKUP_DIR"])
        current_log_file = Path(app.config["WEB_LOG_FILE"])
        cfg_path = Path(app.config["CONFIG_PATH"])

        current_input_dir.mkdir(parents=True, exist_ok=True)
        current_backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. Validate that loose files exist
        loose_files = [p for p in sorted(current_input_dir.iterdir()) if p.is_file()]
        if not loose_files:
            app.logger.warning("Organize & Download requested, but no loose files are staged.")
            return jsonify({
                "error": "No loose files found in staging directory to organize.",
                "message": "Please upload files before organizing."
            }), 400

        try:
            # 2. Backup loose files first (fail-safe)
            backup_result = backup_files(
                input_dir=current_input_dir,
                backup_dir=current_backup_dir,
                log_file=current_log_file,
            )

            if not backup_result.success:
                err_msg = (
                    f"Backup failed for {len(backup_result.failed)} file(s). "
                    "Organization and ZIP creation cancelled to prevent data loss."
                )
                app.logger.error(err_msg)
                return jsonify({"error": err_msg}), 500

            backed_up_count = len(backup_result.backed_up)

            # 3. Organize loose files into category subdirectories
            organizer = FileOrganizer(
                source_dir=current_input_dir,
                config_path=cfg_path if cfg_path.is_file() else None,
                log_file=current_log_file,
            )
            results = organizer.organize()
            total_moved = sum(len(files) for files in results.values())
            stats = getattr(organizer, "last_stats", {})

            # 4. Update latest operation results
            summary = {
                "operation": "Organize & Download ZIP",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "backup_created": True,
                "backup_count": backed_up_count,
                "backed_up_count": backed_up_count,
                "total_processed": stats.get("total_processed", total_moved),
                "files_organized": stats.get("files_organized", total_moved),
                "total_moved": total_moved,
                "duplicate_count": stats.get("duplicate_count", 0),
                "failed_count": stats.get("failed_count", 0),
                "category_counts": stats.get(
                    "category_counts",
                    {cat: len(files) for cat, files in results.items()}
                ),
                "details": results,
                "zip_created": True,
                "download_filename": "LP19_organized_files.zip",
            }
            app.config["LATEST_RESULTS"] = summary

            # 5. Build in-memory ZIP package
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                # Add organized files
                for category, file_list in results.items():
                    for fname in file_list:
                        file_path = current_input_dir / category / fname
                        if file_path.is_file():
                            zf.write(file_path, arcname=f"Organized/{category}/{fname}")

                # Add backup files from this run
                for _, bkp_path in backup_result.backed_up:
                    if bkp_path.is_file():
                        zf.write(bkp_path, arcname=f"Backup/{bkp_path.name}")

            zip_buffer.seek(0)
            app.logger.info("Successfully generated ZIP archive LP19_organized_files.zip")

            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name="LP19_organized_files.zip",
            )

        except Exception as exc:
            app.logger.error("Organize & Download ZIP operation failed: %s", exc)
            return jsonify({"error": f"Operation failed: {exc}"}), 500

    @app.route("/results", methods=["GET"])
    def get_results():
        """Return the results of the latest organize or backup operation as JSON."""
        latest = app.config.get("LATEST_RESULTS")
        if latest is None:
            return jsonify({
                "operation": "None",
                "timestamp": None,
                "backup_created": False,
                "backup_count": 0,
                "backed_up_count": 0,
                "total_processed": 0,
                "files_organized": 0,
                "total_moved": 0,
                "duplicate_count": 0,
                "failed_count": 0,
                "category_counts": {
                    "Images": 0,
                    "Documents": 0,
                    "PDFs": 0,
                    "Videos": 0,
                    "Audio": 0,
                    "Source Code": 0,
                    "Archives": 0,
                    "Others": 0,
                },
                "details": {},
            }), 200
        return jsonify(latest), 200

    @app.route("/logs", methods=["GET"])
    def get_logs():
        """Return raw contents of the application log file."""
        current_log_file = Path(app.config["WEB_LOG_FILE"])
        if current_log_file.is_file():
            try:
                content = current_log_file.read_text(
                    encoding="utf-8", errors="replace"
                )
            except Exception as exc:
                content = f"Error reading log file: {exc}"
        else:
            content = "No logs recorded yet."

        return Response(content, mimetype="text/plain")

    return app


if __name__ == "__main__":
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    application = create_app()
    application.run(host=host, port=port, debug=False)

