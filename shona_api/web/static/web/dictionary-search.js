(function () {
  const shell = document.querySelector(".dictionary-shell");
  if (!shell) {
    return;
  }

  const form = shell.querySelector("[data-search-form]");
  const queryInput = shell.querySelector("[data-query-input]");
  const resultsRegion = shell.querySelector("[data-results-region]");
  const apiKeyPanel = shell.querySelector("[data-api-key-panel]");
  const apiKeyInput = shell.querySelector("[data-api-key-input]");
  const saveKeyButton = shell.querySelector("[data-save-key]");
  const clearKeyButton = shell.querySelector("[data-clear-key]");
  const searchEndpoint = shell.dataset.searchEndpoint;
  const entryUrlTemplate = shell.dataset.entryUrlTemplate;
  const apiKeyStorage = shell.dataset.apiKeyStorage;

  const savedKey = window.localStorage.getItem(apiKeyStorage);
  if (savedKey) {
    apiKeyInput.value = savedKey;
  }

  saveKeyButton.addEventListener("click", function () {
    const key = apiKeyInput.value.trim();
    if (key) {
      window.localStorage.setItem(apiKeyStorage, key);
      renderState("Saved", "API key saved for this browser.");
    }
  });

  clearKeyButton.addEventListener("click", function () {
    apiKeyInput.value = "";
    window.localStorage.removeItem(apiKeyStorage);
    renderState("Cleared", "API key removed from this browser.");
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const query = queryInput.value.trim();
    const apiKey = apiKeyInput.value.trim();

    if (!query) {
      renderState("Search term needed", "Enter a Shona lemma or form to search.");
      queryInput.focus();
      return;
    }

    if (!apiKey) {
      apiKeyPanel.open = true;
      renderError(
        "API key required",
        "Add an API key to search the public API."
      );
      apiKeyInput.focus();
      return;
    }

    await search(query, apiKey);
  });

  async function search(query, apiKey) {
    const url = new URL(searchEndpoint, window.location.origin);
    url.searchParams.set("q", query);

    renderState("Searching", "Checking the public dictionary API...");
    resultsRegion.setAttribute("aria-busy", "true");

    try {
      const response = await window.fetch(url.toString(), {
        headers: {
          Authorization: `Api-Key ${apiKey}`,
          Accept: "application/json",
        },
      });
      const payload = await response.json();

      if (!response.ok) {
        renderApiError(response.status, payload);
        return;
      }

      renderResults(payload.data);
    } catch (error) {
      renderError(
        "Search unavailable",
        "The dictionary API could not be reached. Check the server and try again."
      );
    } finally {
      resultsRegion.setAttribute("aria-busy", "false");
    }
  }

  function renderApiError(status, payload) {
    const apiError = payload && payload.error ? payload.error : {};
    const detail = payload && payload.detail ? payload.detail : "";
    const message = apiError.message || detail;
    if (status === 401 || status === 403) {
      apiKeyPanel.open = true;
      renderError("API key rejected", message || "Check the API key and try again.");
      return;
    }

    renderError(
      apiError.code || "Search error",
      message || "The public API returned an error."
    );
  }

  function renderResults(data) {
    if (!data || !Array.isArray(data.results)) {
      renderError("Unexpected response", "The public API response could not be rendered.");
      return;
    }

    if (data.count === 0) {
      const message =
        data.zero_result && data.zero_result.message
          ? data.zero_result.message
          : "No reviewed lemma or form matched the query.";
      renderState("No matches", `${message} Query: "${data.query.raw}".`);
      return;
    }

    resultsRegion.innerHTML = `
      <div class="results-summary">
        <div>
          <h2>${data.count} ${pluralize(data.count, "result", "results")}</h2>
          <p>Query: "${escapeHtml(data.query.raw)}"</p>
        </div>
        <span class="meta-chip mono">${escapeHtml(data.query.normalizer)}</span>
      </div>
      <ol class="result-list">
        ${data.results.map(renderResult).join("")}
      </ol>
    `;
  }

  function renderResult(result) {
    const lemma = result.lemma || {};
    const pos = lemma.part_of_speech_label || lemma.part_of_speech_code || "Unspecified part of speech";
    const kind = humanize(lemma.headword_kind);
    const dialects = Array.isArray(lemma.dialects) ? lemma.dialects : [];
    const form = result.form;

    return `
      <li class="result-card">
        <div class="result-header">
          <div>
            <h3 class="headword">
              <a class="headword-link" href="${escapeAttribute(entryUrl(lemma.public_id))}">
                ${escapeHtml(lemma.headword || "Untitled lemma")}
              </a>
            </h3>
            <p class="result-subtitle">${escapeHtml(pos)}</p>
          </div>
          <div class="badge-row">
            <span class="badge">${escapeHtml(humanize(result.match_type))}</span>
            <span class="badge">${escapeHtml(humanize(result.result_type))}</span>
          </div>
        </div>
        ${form ? renderFormMatch(form) : ""}
        <div class="meta-row">
          <span class="meta-chip">${escapeHtml(kind)}</span>
          <span class="meta-chip mono">${escapeHtml(lemma.public_id || "")}</span>
          ${renderDialectChips(dialects)}
          ${renderCountChip("syllables", lemma.syllable_count)}
          ${renderCountChip("graphemes", lemma.grapheme_count)}
        </div>
      </li>
    `;
  }

  function renderFormMatch(form) {
    return `
      <p class="matched-form">
        Matched form <strong>${escapeHtml(form.form_text || "")}</strong>
        <span class="meta-chip">${escapeHtml(humanize(form.form_kind))}</span>
      </p>
    `;
  }

  function renderDialectChips(dialects) {
    return dialects
      .map(function (dialect) {
        return `<span class="meta-chip">${escapeHtml(dialect)}</span>`;
      })
      .join("");
  }

  function renderCountChip(label, count) {
    if (typeof count !== "number" || count < 1) {
      return "";
    }
    return `<span class="meta-chip">${count} ${escapeHtml(label)}</span>`;
  }

  function renderState(title, message) {
    resultsRegion.innerHTML = `
      <div class="state-card" data-state-card>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }

  function renderError(title, message) {
    resultsRegion.innerHTML = `
      <div class="state-card state-card--error" data-state-card>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }

  function pluralize(count, singular, plural) {
    return count === 1 ? singular : plural;
  }

  function entryUrl(publicId) {
    if (!entryUrlTemplate || !publicId) {
      return "#";
    }
    return entryUrlTemplate.replace("__PUBLIC_ID__", encodeURIComponent(publicId));
  }

  function humanize(value) {
    if (!value) {
      return "";
    }
    return String(value).replace(/_/g, " ");
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
