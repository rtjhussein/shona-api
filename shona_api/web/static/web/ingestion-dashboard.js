(function () {
  const shell = document.querySelector(".ingestion-shell");
  if (!shell) {
    return;
  }

  const runForm = shell.querySelector("[data-run-form]");
  const keyForm = shell.querySelector("[data-key-form]");
  const statusRegion = shell.querySelector("[data-run-status]");
  const startEndpoint = shell.dataset.startEndpoint;
  const saveKeyEndpoint = shell.dataset.saveKeyEndpoint;
  const statusUrlTemplate = shell.dataset.statusUrlTemplate;
  let pollTimer = null;
  const latestRunningRunId = document.getElementById("latest-running-run-id");
  if (latestRunningRunId) {
    try {
      pollRun(JSON.parse(latestRunningRunId.textContent));
    } catch (error) {
      // Static latest-run content remains visible if auto-resume metadata is malformed.
    }
  }

  runForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const formData = new FormData(runForm);
    renderMessage("Starting", "Creating ingestion run...");

    const response = await postForm(startEndpoint, formData);
    if (!response.ok) {
      renderError(response.error || "Could not start ingestion.");
      return;
    }
    renderRun(response.run);
    pollRun(response.run.id);
  });

  keyForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const formData = new FormData(keyForm);
    const response = await postForm(saveKeyEndpoint, formData);
    if (!response.ok) {
      renderError(response.error || "Could not save Gemini key.");
      return;
    }
    keyForm.reset();
    renderMessage("Key saved", "Refresh the page to see updated readiness checks.");
  });

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

  function pollRun(runId) {
    window.clearInterval(pollTimer);
    pollTimer = window.setInterval(async function () {
      const url = statusUrlTemplate.replace("__RUN_ID__", encodeURIComponent(runId));
      try {
        const response = await window.fetch(url, { headers: { Accept: "application/json" } });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          renderError(payload.error || "Could not load run status.");
          window.clearInterval(pollTimer);
          return;
        }
        renderRun(payload.run);
        if (payload.run.status === "succeeded" || payload.run.status === "failed") {
          window.clearInterval(pollTimer);
        }
      } catch (error) {
        renderError("Lost contact with the dashboard server.");
        window.clearInterval(pollTimer);
      }
    }, 2500);
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
        ${metric("Pages", run.page_label)}
        ${metric("Imported", run.imported_count)}
        ${metric("Duplicates", run.duplicate_count)}
        ${metric("Publishable", run.publishable_count)}
        ${metric("Published", run.published_count)}
        ${metric("Publish failures", run.failed_publish_count)}
      </div>
      <div class="run-actions">
        <a href="${escapeAttribute(run.review_url)}">Review queue</a>
        <a href="${escapeAttribute(run.published_url)}">Search dictionary</a>
      </div>
      ${run.error_message ? `<p class="error-note">${escapeHtml(run.error_message)}</p>` : ""}
      <pre class="log-box">${escapeHtml(run.log_text || "Waiting for output...")}</pre>
    `;
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
          <p class="eyebrow">Current run</p>
          <h2>${escapeHtml(title)}</h2>
        </div>
      </div>
      <p class="empty-note">${escapeHtml(message)}</p>
    `;
  }

  function renderError(message) {
    statusRegion.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">Current run</p>
          <h2>Action needed</h2>
        </div>
        <span class="status-pill status-failed">failed</span>
      </div>
      <p class="error-note">${escapeHtml(message)}</p>
    `;
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
})();
