/* Automatic File Organizer & Backup System - Team 19 */
/* Interactive UI Enhancements, File Upload & ZIP Download Management */

document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("file-input");
  const dropzone = document.getElementById("dropzone");
  const selectedFilesBox = document.getElementById("selected-files-box");
  const selectedFilesList = document.getElementById("selected-files-list");
  const uploadBtn = document.getElementById("upload-btn");

  // Highlight dropzone on drag over
  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("dragover");
      });
    });

    // Handle dropped files
    dropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt.files && dt.files.length > 0) {
        fileInput.files = dt.files;
        updateSelectedFilesDisplay(dt.files);
      }
    });

    // Handle standard file selection
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        updateSelectedFilesDisplay(fileInput.files);
      } else {
        selectedFilesBox.style.display = "none";
        selectedFilesList.innerHTML = "";
      }
    });
  }

  function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  }

  function updateSelectedFilesDisplay(files) {
    if (!selectedFilesBox || !selectedFilesList) return;

    selectedFilesList.innerHTML = "";
    Array.from(files).forEach((file) => {
      const li = document.createElement("li");
      const nameSpan = document.createElement("span");
      nameSpan.textContent = file.name;
      nameSpan.className = "selected-file-name";

      const sizeSpan = document.createElement("span");
      sizeSpan.textContent = formatBytes(file.size);
      sizeSpan.className = "selected-file-size";

      li.appendChild(nameSpan);
      li.appendChild(sizeSpan);
      selectedFilesList.appendChild(li);
    });

    selectedFilesBox.style.display = "block";
    if (uploadBtn) {
      uploadBtn.disabled = false;
    }
  }

  function showFlashAlert(message, category = "success") {
    let container = document.querySelector(".alerts-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "alerts-container";
      const header = document.querySelector(".app-header");
      if (header && header.nextSibling) {
        header.parentNode.insertBefore(container, header.nextSibling);
      } else {
        const appContainer = document.querySelector(".app-container");
        if (appContainer) appContainer.prepend(container);
      }
    }
    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${category}`;
    alertDiv.setAttribute("role", "alert");
    alertDiv.innerHTML = `<span>${message}</span>`;
    container.appendChild(alertDiv);
  }

  async function updateDashboardMetrics() {
    try {
      const res = await fetch("/results");
      if (res.ok) {
        const data = await res.json();
        const totalProc = document.getElementById("metric-total-processed");
        if (totalProc && data.total_processed !== undefined) totalProc.textContent = data.total_processed;

        const filesOrg = document.getElementById("metric-files-organized");
        if (filesOrg && data.files_organized !== undefined) filesOrg.textContent = data.files_organized;

        const bkpCount = document.getElementById("metric-backup-count");
        if (bkpCount && data.backup_count !== undefined) bkpCount.textContent = data.backup_count;

        const dupCount = document.getElementById("metric-duplicate-count");
        if (dupCount && data.duplicate_count !== undefined) dupCount.textContent = data.duplicate_count;

        const failCount = document.getElementById("metric-failed-count");
        if (failCount && data.failed_count !== undefined) failCount.textContent = data.failed_count;

        if (data.category_counts) {
          for (const [cat, count] of Object.entries(data.category_counts)) {
            const catId = "cat-card-" + cat.toLowerCase().replace(/[\s_]+/g, "-");
            const card = document.getElementById(catId);
            if (card) {
              const countBadge = card.querySelector(".category-count");
              if (countBadge) countBadge.textContent = count;
            }
          }
        }
      }

      const logRes = await fetch("/logs");
      if (logRes.ok) {
        const logText = await logRes.text();
        const term = document.getElementById("terminal-logs");
        if (term) {
          term.textContent = logText;
          term.scrollTop = term.scrollHeight;
        }
      }
    } catch (_) {}
  }

  // Handle Organize & Download ZIP with loading state, dynamic download, and feedback
  const downloadForm = document.getElementById("organize-download-form");
  const downloadBtn = document.getElementById("organize-download-btn");

  if (downloadForm && downloadBtn) {
    downloadForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const originalHtml = downloadBtn.innerHTML;
      downloadBtn.disabled = true;
      downloadBtn.innerHTML = "Packaging ZIP...";
      downloadBtn.style.opacity = "0.75";

      try {
        const response = await fetch("/organize-download", {
          method: "POST",
        });

        if (!response.ok) {
          let errorText = "Organization failed. Staged files could not be packaged.";
          try {
            const errJson = await response.json();
            if (errJson && errJson.error) {
              errorText = errJson.error;
            }
          } catch (_) {}
          showFlashAlert(errorText, "error");
          return;
        }

        // Trigger file download
        const blob = await response.blob();
        let filename = "LP19_organized_files.zip";
        const disposition = response.headers.get("Content-Disposition");
        if (disposition && disposition.indexOf("filename=") !== -1) {
          const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
          if (match && match[1]) {
            filename = match[1].replace(/['"]/g, "");
          }
        }

        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);

        showFlashAlert("Organization completed successfully. Your ZIP file is downloading.", "success");
        await updateDashboardMetrics();
      } catch (err) {
        showFlashAlert("Error processing ZIP download: " + err.message, "error");
      } finally {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = originalHtml;
        downloadBtn.style.opacity = "1";
      }
    });
  }

  // Button loading states for other forms (Upload, Organize, Backup)
  const otherForms = document.querySelectorAll("form:not(#organize-download-form)");
  otherForms.forEach((form) => {
    form.addEventListener("submit", function () {
      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) {
        submitBtn.setAttribute("data-original-text", submitBtn.innerHTML);
        submitBtn.innerHTML = "Processing...";
        submitBtn.style.opacity = "0.75";
      }
    });
  });

  // Log auto-scroll
  const terminal = document.getElementById("terminal-logs");
  if (terminal) {
    terminal.scrollTop = terminal.scrollHeight;
  }
});
