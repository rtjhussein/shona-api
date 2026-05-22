(function () {
  const shell = document.querySelector(".ingestion-shell");
  if (!shell) {
    return;
  }

  const runForm = shell.querySelector("[data-run-form]");
  const statusRegion = shell.querySelector("[data-run-status]");
  const historyRegion = shell.querySelector("[data-run-history]");
  const runFeedback = shell.querySelector("[data-run-feedback]");
  const runSubmit = shell.querySelector("[data-run-submit]");
  const startEndpoint = shell.dataset.startEndpoint;
  const jsonlListEndpoint = shell.dataset.jsonlListEndpoint;
  const statusUrlTemplate = shell.dataset.statusUrlTemplate;
  const jsonlPathInput = shell.querySelector("[data-jsonl-path-input]");
  const jsonlPicker = shell.querySelector("[data-jsonl-picker]");
  const jsonlFileList = shell.querySelector("[data-jsonl-file-list]");
  const jsonlFolder = shell.querySelector("[data-jsonl-folder]");
  const jsonlPickerOpen = shell.querySelector("[data-jsonl-picker-open]");
  const jsonlPickerClose = shell.querySelector("[data-jsonl-picker-close]");
  let pollTimer = null;

  const latestRunningRunId = document.getElementById("latest-running-run-id");
  if (latestRunningRunId) {
    try {
      pollRun(JSON.parse(latestRunningRunId.textContent));
    } catch (error) {
      // Static latest-run content remains visible if auto-resume metadata is malformed.
    }
  }

  bindRunForm();
  bindJsonlPicker();

  function bindRunForm() {
    if (!runForm) {
      return;
    }

    runForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const formData = new FormData(runForm);
      setFormBusy(true);
      renderInlineFeedback("working", "Starting import run...");
      renderMessage("Importing", "Creating JSONL import run...");

      const response = await postForm(startEndpoint, formData);
      if (!response.ok) {
        const message = response.error || "Could not start ingestion.";
        renderInlineFeedback("error", message);
        renderError(message);
        setFormBusy(false);
        return;
      }

      renderInlineFeedback(
        "working",
        `Run ${response.run.batch_id} created. Waiting for import results...`,
      );
      renderRun(response.run);
      upsertHistoryRun(response.run);
      pollRun(response.run.id, { releaseFormWhenDone: true });
    });
  }

  function bindJsonlPicker() {
    if (!jsonlPickerOpen || !jsonlPicker || !jsonlFileList || !jsonlPathInput) {
      return;
    }

    jsonlPickerOpen.addEventListener("click", async function () {
      jsonlPicker.hidden = false;
      jsonlFileList.innerHTML = '<p class="empty-note">Loading JSONL files...</p>';
      try {
        const response = await window.fetch(jsonlListEndpoint, {
          headers: { Accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "Could not load JSONL files.");
        }
        renderJsonlFiles(payload);
      } catch (error) {
        jsonlFileList.innerHTML = `<p class="error-note">${escapeHtml(error.message || "Could not load JSONL files.")}</p>`;
      }
    });

    if (jsonlPickerClose) {
      jsonlPickerClose.addEventListener("click", function () {
        jsonlPicker.hidden = true;
      });
    }
  }

  function renderJsonlFiles(payload) {
    if (jsonlFolder) {
      jsonlFolder.textContent = payload.folder || "";
    }
    if (!payload.files || payload.files.length === 0) {
      jsonlFileList.innerHTML = '<p class="empty-note">No JSONL files found in this folder.</p>';
      return;
    }

    jsonlFileList.innerHTML = payload.files.map(function (file) {
      const status = file.import_status || {
        state: "not_imported",
        label: "Not imported",
        detail: "No import run found for this file.",
      };
      return `
        <button class="jsonl-file-button jsonl-file-${escapeAttribute(status.state)}" type="button" data-jsonl-path="${escapeAttribute(file.path)}">
          <span class="jsonl-file-title">
            <strong>${escapeHtml(file.name)}</strong>
            <span class="jsonl-status-pill jsonl-status-${escapeAttribute(status.state)}">${escapeHtml(status.label)}</span>
          </span>
          <span class="jsonl-file-meta">${escapeHtml(formatBytes(file.size))} - ${escapeHtml(formatDate(file.modified))}</span>
          <span class="jsonl-import-detail">${escapeHtml(status.detail)}</span>
        </button>
      `;
    }).join("");

    jsonlFileList.querySelectorAll("[data-jsonl-path]").forEach(function (button) {
      button.addEventListener("click", function () {
        jsonlPathInput.value = button.dataset.jsonlPath;
        jsonlPicker.hidden = true;
        jsonlPathInput.focus();
      });
    });
  }

  async function postForm(url, formData) {
    try {
      const response = await window.fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken(),
          Accept: "application/json",
        },
        body: formData,
      });
      const payload = await response.json();
      return { ok: response.ok && payload.ok !== false, ...payload };
    } catch (error) {
      return { ok: false, error: "The dashboard server could not be reached." };
    }
  }

  function pollRun(runId, options = {}) {
    window.clearInterval(pollTimer);
    fetchAndRenderRun(runId, options);
    pollTimer = window.setInterval(function () {
      fetchAndRenderRun(runId, options);
    }, 1500);
  }

  async function fetchAndRenderRun(runId, options) {
    const url = statusUrlTemplate.replace("__RUN_ID__", encodeURIComponent(runId));
    try {
      const response = await window.fetch(url, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        finishPollingWithError(payload.error || "Could not load run status.", options);
        return;
      }

      renderRun(payload.run);
      upsertHistoryRun(payload.run);
      if (payload.run.status === "succeeded" || payload.run.status === "failed") {
        window.clearInterval(pollTimer);
        if (payload.run.status === "succeeded") {
          renderInlineFeedback(
            "success",
            `Run ${payload.run.batch_id} finished. Imported ${payload.run.imported_count}; duplicates ${payload.run.duplicate_count}.`,
          );
        } else {
          renderInlineFeedback("error", payload.run.error_message || `Run ${payload.run.batch_id} failed.`);
        }
        if (options.releaseFormWhenDone) {
          setFormBusy(false);
        }
      }
    } catch (error) {
      finishPollingWithError("Lost contact with the dashboard server.", options);
    }
  }

  function finishPollingWithError(message, options) {
    renderInlineFeedback("error", message);
    renderError(message);
    window.clearInterval(pollTimer);
    if (options.releaseFormWhenDone) {
      setFormBusy(false);
    }
  }

  function renderRun(run) {
    statusRegion.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">Latest run</p>
          <h2>${escapeHtml(run.batch_id)}</h2>
        </div>
        <span class="status-pill status-${escapeHtml(run.status)}">${escapeHtml(run.status)}</span>
      </div>
      <div class="metric-grid">
        ${metric("Input", run.page_label)}
        ${metric("Imported", run.imported_count)}
        ${metric("Duplicates", run.duplicate_count)}
        ${metric("Approved", run.publishable_count)}
        ${metric("Published", run.published_count)}
        ${metric("Publish failures", run.failed_publish_count)}
      </div>
      <div class="run-actions">
        <a href="${escapeAttribute(run.review_url)}">Review queue</a>
        <a href="${escapeAttribute(run.published_url)}">Search dictionary</a>
      </div>
      ${run.error_message ? `<p class="error-note">${escapeHtml(run.error_message)}</p>` : ""}
      <details class="log-details">
        <summary>Run log</summary>
        <pre class="log-box">${escapeHtml(run.log_text || "Waiting for output...")}</pre>
      </details>
    `;
  }

  function upsertHistoryRun(run) {
    if (!historyRegion) {
      return;
    }
    const rowHtml = `
      <span>${escapeHtml(run.batch_id)}</span>
      <span>${escapeHtml(run.status)}</span>
      <span>${escapeHtml(run.page_label)}</span>
      <span>${escapeHtml(run.imported_count)}</span>
      <span>${escapeHtml(run.publishable_count)}</span>
      <span>${escapeHtml(run.published_count)}</span>
    `;
    const existing = historyRegion.querySelector(`[data-run-row-id="${cssEscape(String(run.id))}"]`);
    if (existing) {
      existing.innerHTML = rowHtml;
      return;
    }

    const emptyNote = historyRegion.querySelector(".empty-note");
    if (emptyNote) {
      emptyNote.remove();
    }
    const row = document.createElement("div");
    row.className = "run-row";
    row.dataset.runRowId = String(run.id);
    row.innerHTML = rowHtml;
    const header = historyRegion.querySelector(".run-head");
    if (header && header.nextSibling) {
      historyRegion.insertBefore(row, header.nextSibling);
    } else {
      historyRegion.appendChild(row);
    }
  }

  function metric(label, value) {
    return `
      <div>
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    `;
  }

  function renderMessage(title, message) {
    statusRegion.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">Latest run</p>
          <h2>${escapeHtml(title)}</h2>
        </div>
        <span class="status-pill status-running">starting</span>
      </div>
      <p class="empty-note">${escapeHtml(message)}</p>
    `;
  }

  function renderError(message) {
    statusRegion.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">Latest run</p>
          <h2>Action needed</h2>
        </div>
        <span class="status-pill status-failed">failed</span>
      </div>
      <p class="error-note">${escapeHtml(message)}</p>
    `;
  }

  function renderInlineFeedback(kind, message) {
    if (!runFeedback) {
      return;
    }
    runFeedback.hidden = false;
    runFeedback.className = `form-feedback form-feedback-${kind}`;
    runFeedback.textContent = message;
  }

  function setFormBusy(isBusy) {
    if (!runSubmit) {
      return;
    }
    runSubmit.disabled = isBusy;
    runSubmit.textContent = isBusy ? "Importing..." : "Import JSONL";
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/`/g, "&#096;");
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return value.replace(/"/g, '\\"');
  }

  function formatBytes(value) {
    const bytes = Number(value) || 0;
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function formatDate(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  }
})();
