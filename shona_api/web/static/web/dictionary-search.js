(function () {
  const shell = document.querySelector(".dictionary-shell");
  if (!shell) {
    return;
  }

  const form = shell.querySelector("[data-search-form]");
  const queryInput = shell.querySelector("[data-query-input]");
  const resultsRegion = shell.querySelector("[data-results-region]");
  const detailsRegion = shell.querySelector("[data-details-region]");
  const apiKeyPanel = shell.querySelector("[data-api-key-panel]");
  const apiKeyInput = shell.querySelector("[data-api-key-input]");
  const saveKeyButton = shell.querySelector("[data-save-key]");
  const clearKeyButton = shell.querySelector("[data-clear-key]");
  const createLocalKeyButton = shell.querySelector("[data-create-local-key]");
  const searchEndpoint = shell.dataset.searchEndpoint;
  const entryUrlTemplate = shell.dataset.entryUrlTemplate;
  const apiKeyStorage = shell.dataset.apiKeyStorage;
  const localApiKeyEndpoint = shell.dataset.localApiKeyEndpoint;

  // Cache matched lemmas and details in memory for instant split-pane browsing
  let cachedLemmas = {};
  let selectedLemmaId = null;

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

  if (createLocalKeyButton) {
    createLocalKeyButton.addEventListener("click", createLocalKey);
  }

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

  // Capture clicks on search results and select lemmas in split-pane
  resultsRegion.addEventListener("click", function (event) {
    const card = event.target.closest("[data-lemma-id]");
    if (card) {
      event.preventDefault();
      const lemmaId = card.dataset.lemmaId;
      selectLemma(lemmaId);
    }
  });

  async function search(query, apiKey) {
    const url = new URL(searchEndpoint, window.location.origin);
    url.searchParams.set("q", query);

    renderState("Searching", "Checking the public dictionary API...");
    resultsRegion.setAttribute("aria-busy", "true");
    cachedLemmas = {}; // Reset cache

    try {
      const response = await window.fetch(url.toString(), {
        headers: {
          Authorization: `Api-Key ${apiKey}`,
          Accept: "application/json",
        },
      });
      const payload = await parseJsonResponse(response);

      if (!response.ok) {
        renderApiError(response.status, payload);
        return;
      }

      const data = payload.data;

      // Cache all direct search result lemmas
      if (data && Array.isArray(data.results)) {
        data.results.forEach(function (res) {
          if (res.lemma && res.lemma.public_id) {
            cachedLemmas[res.lemma.public_id] = res.lemma;
          }
        });
      }

      // Cache all analyzed morphologically-matched lemmas
      if (data && data.morphology && Array.isArray(data.morphology.analyses)) {
        data.morphology.analyses.forEach(function (analysis) {
          if (analysis.lemma_details && analysis.lemma_details.public_id) {
            cachedLemmas[analysis.lemma_details.public_id] = analysis.lemma_details;
          }
        });
      }

      renderResults(data);

      // Auto-select the first available lemma to avoid empty state
      let firstLemmaId = null;
      if (data && data.morphology && Array.isArray(data.morphology.analyses) && data.morphology.analyses.length > 0) {
        firstLemmaId = data.morphology.analyses[0].lemma.public_id;
      } else if (data && Array.isArray(data.results) && data.results.length > 0) {
        firstLemmaId = data.results[0].lemma.public_id;
      }

      if (firstLemmaId) {
        selectLemma(firstLemmaId);
      } else {
        renderDetailsEmpty();
      }

    } catch (error) {
      let message = "The dictionary API could not be reached. Check that the Django server is running.";
      if (error && error.message === "INVALID_JSON") {
        message = error.status >= 500
          ? `The dictionary API crashed with HTTP ${error.status}. ${error.body || ""}`.trim()
          : `The dictionary API returned a non-JSON HTTP ${error.status} response.`;
      }
      renderError("Search unavailable", message);
      renderDetailsEmpty();
    } finally {
      resultsRegion.setAttribute("aria-busy", "false");
    }
  }

  function selectLemma(lemmaId) {
    selectedLemmaId = lemmaId;
    
    // Update active highlight classes in search result list
    resultsRegion.querySelectorAll("[data-lemma-id]").forEach(function (card) {
      if (card.dataset.lemmaId === lemmaId) {
        card.classList.add("result-card--active");
      } else {
        card.classList.remove("result-card--active");
      }
    });

    const lemmaData = cachedLemmas[lemmaId];
    if (lemmaData) {
      renderDetails(lemmaData);
    } else {
      renderDetailsError("No local data found for this lemma.");
    }
  }

  async function createLocalKey() {
    if (!localApiKeyEndpoint) {
      renderError("Key helper unavailable", "The local API key endpoint is not configured.");
      return;
    }
    try {
      const formData = new FormData();
      formData.set("name", "Reference web local key");
      const response = await window.fetch(localApiKeyEndpoint, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken(),
          Accept: "application/json",
        },
        body: formData,
      });
      const payload = await parseJsonResponse(response);
      if (!response.ok || !payload.ok) {
        renderError("Could not create key", payload.error || "The server rejected the request.");
        return;
      }
      apiKeyInput.value = payload.raw_key;
      window.localStorage.setItem(apiKeyStorage, payload.raw_key);
      renderState("Local key created", "A new local API key was saved for this browser.");
    } catch (error) {
      renderError("Could not create key", "The dashboard server could not be reached.");
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
    if (status === 429) {
      renderError("Rate limit reached", message || "Wait a moment and try again.");
      return;
    }

    renderError(
      apiError.code || "Search error",
      message || "The public API returned an error."
    );
  }

  async function parseJsonResponse(response) {
    try {
      return await response.json();
    } catch (error) {
      let text = "";
      try {
        text = await response.text();
      } catch (textError) {
        text = "";
      }
      const invalidJson = new Error("INVALID_JSON");
      invalidJson.status = response.status;
      invalidJson.body = text.slice(0, 240);
      throw invalidJson;
    }
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function renderResults(data) {
    if (!data || !Array.isArray(data.results)) {
      renderError("Unexpected response", "The public API response could not be rendered.");
      return;
    }

    const hasResults = data.results.length > 0;
    const hasMorphology = data.morphology && Array.isArray(data.morphology.analyses) && data.morphology.analyses.length > 0;

    if (!hasResults && !hasMorphology) {
      renderZeroResult(data);
      return;
    }

    let morphologyHtml = "";
    if (hasMorphology) {
      morphologyHtml = `
        <div class="morphology-container">
          <div class="morphology-badge">🔍 Inflected Verb Breakdown</div>
          ${data.morphology.analyses.map(function (analysis) {
            return renderMorphologyAnalysis(analysis, data.morphology.query);
          }).join("")}
        </div>
      `;
    }

    let resultsListHtml = "";
    if (hasResults) {
      resultsListHtml = `
        <div class="results-summary">
          <div>
            <h2>${data.count} ${pluralize(data.count, "result", "results")}</h2>
            <p>Query: "${escapeHtml(data.query.raw)}"</p>
          </div>
          <span class="meta-chip mono">${escapeHtml(data.query.normalizer)}</span>
        </div>
        <ol class="result-list">
          ${data.results.map(renderResultCard).join("")}
        </ol>
      `;
    } else {
      resultsListHtml = `
        <div class="results-summary">
          <p>No direct entries matched "${escapeHtml(data.query.raw)}", but an inflected breakdown was successfully analyzed.</p>
        </div>
      `;
    }

    resultsRegion.innerHTML = morphologyHtml + resultsListHtml;
  }

  function renderZeroResult(data) {
    const zeroResult = data.zero_result || {};
    const enrichment = zeroResult.morphology_enrichment || {};
    const futureLanes = enrichment.detail && Array.isArray(enrichment.detail.future_lanes)
      ? enrichment.detail.future_lanes
      : [];
    const message = zeroResult.message || "No reviewed lemma or form matched the query.";
    const laneHtml = futureLanes.length
      ? `
        <ul class="unsupported-lane-list">
          ${futureLanes.map(renderUnsupportedLane).join("")}
        </ul>
      `
      : "";

    resultsRegion.innerHTML = `
      <div class="state-card state-card--empty" data-state-card>
        <h2>No matches</h2>
        <p>${escapeHtml(message)} Query: "${escapeHtml(data.query.raw)}".</p>
        ${laneHtml}
      </div>
    `;
  }

  function renderUnsupportedLane(lane) {
    const ruleCards = Array.isArray(lane.rule_card_ids) && lane.rule_card_ids.length
      ? `<span class="meta-chip mono">${escapeHtml(lane.rule_card_ids.join(", "))}</span>`
      : "";
    return `
      <li>
        <strong>${escapeHtml(humanize(lane.code))}</strong>
        <span>${escapeHtml(lane.message || "")}</span>
        ${ruleCards}
      </li>
    `;
  }

  function renderMorphologyAnalysis(analysis, query) {
    const lemma = analysis.lemma || {};
    const slots = analysis.slots || {};
    
    // Render individual slot pills dynamically
    let slotsHtml = "";
    
    if (slots.infinitive_prefix && slots.infinitive_prefix.surface) {
      slotsHtml += renderSlotPill(
        "infinitive",
        slots.infinitive_prefix.surface,
        "infinitive / prefix",
        slots.infinitive_prefix.label
      );
    }
    if (slots.polarity && slots.polarity.surface) {
      slotsHtml += renderSlotPill("polarity", slots.polarity.surface, "polarity / negative", slots.polarity.label);
    }
    if (slots.subject && slots.subject.surface) {
      const details = slots.subject.class_number ? `Noun Class ${slots.subject.class_number}` : `${slots.subject.person} person ${slots.subject.number}`;
      slotsHtml += renderSlotPill("subject", slots.subject.surface, "subject / concord", `${slots.subject.label} (${details})`);
    }
    if (slots.tense_aspect && slots.tense_aspect.surface) {
      slotsHtml += renderSlotPill("tense", slots.tense_aspect.surface, "tense / aspect", slots.tense_aspect.label);
    }
    if (slots.object && slots.object.surface) {
      const details = slots.object.class_number ? `Noun Class ${slots.object.class_number}` : `${slots.object.person} person ${slots.object.number}`;
      slotsHtml += renderSlotPill("object", slots.object.surface, "object / concord", `${slots.object.label} (${details})`);
    }
    if (slots.verb_stem && slots.verb_stem.surface) {
      slotsHtml += renderSlotPill("stem", slots.verb_stem.surface, "verb stem", `Stem: ${lemma.headword || lemma.normalized_headword}`);
    }
    if (slots.final_vowel && slots.final_vowel.surface) {
      slotsHtml += renderSlotPill("final_vowel", slots.final_vowel.surface, "final vowel", `Mood marker: ${slots.final_vowel.value}`);
    }

    return `
      <div class="morphology-card" data-lemma-id="${escapeAttribute(lemma.public_id)}">
        <div class="morph-word-row">
          <span class="morph-word-raw">${escapeHtml(query ? query.normalized : "")}</span>
          <span class="confidence-tag">confidence ${Math.round(analysis.confidence * 100)}%</span>
        </div>
        <p class="morph-analysis-type">${escapeHtml(morphologyAnalysisLabel(analysis))}</p>
        <div class="morph-slots-row">
          ${slotsHtml}
        </div>
        <div class="morph-details-teaser">
          Linked stem: <strong>${escapeHtml(lemma.headword)}</strong> (${escapeHtml(lemma.part_of_speech_code || "verb")}).
          <span class="morph-action-link">View stem details &rarr;</span>
        </div>
      </div>
    `;
  }

  function morphologyAnalysisLabel(analysis) {
    if (analysis.analysis_type === "infinitive") {
      return "ku- infinitive linked to a reviewed verb stem";
    }
    return "inflected verb breakdown";
  }

  function renderSlotPill(type, surface, slotTypeLabel, description) {
    return `
      <div class="slot-pill slot-pill--${type}" title="${escapeAttribute(description)}">
        <span class="slot-surface">${escapeHtml(surface)}</span>
        <span class="slot-label">${escapeHtml(slotTypeLabel)}</span>
      </div>
    `;
  }

  function renderResultCard(result) {
    const lemma = result.lemma || {};
    const pos = lemma.part_of_speech_label || lemma.part_of_speech_code || "Unspecified part of speech";
    const kind = humanize(lemma.headword_kind);
    const form = result.form;

    // Grab first definition preview
    let defPreview = "";
    if (Array.isArray(lemma.senses) && lemma.senses.length > 0) {
      defPreview = lemma.senses[0].definition || "";
      if (defPreview.length > 80) {
        defPreview = defPreview.slice(0, 80) + "...";
      }
    }

    return `
      <li class="result-card" data-lemma-id="${escapeAttribute(lemma.public_id)}">
        <div class="result-header">
          <div>
            <h3 class="headword">
              <a class="headword-link" href="#">
                ${escapeHtml(lemma.headword || "Untitled lemma")}
              </a>
            </h3>
            <p class="result-subtitle">${escapeHtml(pos)}</p>
          </div>
          <div class="badge-row">
            <span class="badge">${escapeHtml(humanize(result.match_type))}</span>
          </div>
        </div>
        ${defPreview ? `<p class="result-definition-teaser">${escapeHtml(defPreview)}</p>` : ""}
        ${form ? renderFormMatch(form) : ""}
        <div class="meta-row">
          <span class="meta-chip">${escapeHtml(kind)}</span>
          <span class="meta-chip mono">${escapeHtml(lemma.public_id || "")}</span>
        </div>
      </li>
    `;
  }

  function renderFormMatch(form) {
    return `
      <div class="matched-form-block">
        <p class="matched-form">
          Matched form <strong>${escapeHtml(form.form_text || "")}</strong>
          <span class="meta-chip">${escapeHtml(humanize(form.form_kind))}</span>
        </p>
        ${renderDerivedFormEvidence(form)}
      </div>
    `;
  }

  function renderDerivedFormEvidence(form) {
    const evidence = form && form.derived_form_evidence;
    if (!evidence || typeof evidence !== "object") {
      return "";
    }

    const rows = [
      ["Marker", evidence.marker],
      ["Relation", evidence.relation ? humanize(evidence.relation) : ""],
      ["Source note", evidence.source_note],
      ["Raw source", evidence.raw_source],
    ]
      .filter(function (row) {
        return row[1] !== null && row[1] !== undefined && row[1] !== "";
      })
      .map(function (row) {
        return `
          <div class="derived-evidence-row">
            <dt>${escapeHtml(row[0])}</dt>
            <dd>${escapeHtml(row[1])}</dd>
          </div>
        `;
      })
      .join("");

    return rows ? `<dl class="derived-evidence">${rows}</dl>` : "";
  }

  // --- Dynamic Detail Pane Rendering ---

  function renderDetailsEmpty() {
    detailsRegion.innerHTML = `
      <div class="state-card state-card--empty">
        <h2>Lexical Details</h2>
        <p>Select a search result to view its full dictionary entries, noun classes, and tone rules here.</p>
      </div>
    `;
  }

  function renderDetailsError(message) {
    detailsRegion.innerHTML = `
      <div class="state-card state-card--error">
        <h2>Error Loading Details</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }

  function renderDetails(lemma) {
    const senses = Array.isArray(lemma.senses) ? lemma.senses : [];
    const tones = Array.isArray(lemma.tone_records) ? lemma.tone_records : [];
    const forms = Array.isArray(lemma.forms) ? lemma.forms : [];
    const nounClass = lemma.noun_class;
    const pos = lemma.part_of_speech_label || lemma.part_of_speech_code || "Unspecified part of speech";

    detailsRegion.innerHTML = `
      <article class="entry-card animate-fade-in">
        <div class="entry-heading">
          <div>
            <p class="eyebrow">${escapeHtml(pos)}</p>
            <h2 class="entry-headword">${escapeHtml(lemma.headword || "Untitled lemma")}</h2>
          </div>
          <span class="meta-chip mono">${escapeHtml(lemma.public_id)}</span>
        </div>
        <div class="meta-row entry-meta">
          ${chip(humanize(lemma.headword_kind))}
          ${renderArrayChips(lemma.dialects)}
          ${renderCountChip("syllables", lemma.syllable_count)}
          ${renderCountChip("graphemes", lemma.grapheme_count)}
          ${nounClass ? chip(`class ${nounClass.class_number}`) : ""}
          ${tones.length ? chip(`${tones.length} tone ${pluralize(tones.length, "record", "records")}`) : ""}
        </div>
        ${renderDefinitions(senses)}
        ${renderNounClassTable(nounClass)}
        ${renderToneRecords(tones)}
        ${renderForms(forms)}
        ${renderMetadata(lemma)}
        
        <!-- Raw JSON details block for developers -->
        <details class="raw-json-panel">
          <summary>Raw JSON Payload</summary>
          <pre class="raw-json mono">${escapeHtml(JSON.stringify(lemma, null, 2))}</pre>
        </details>
      </article>
    `;
  }

  function renderDefinitions(senses) {
    if (!senses.length) {
      return section("Definitions", '<p class="muted">No definitions are exposed yet.</p>');
    }

    return section(
      "Definitions",
      `<ol class="definition-list">
        ${senses
          .map(function (sense) {
            return `
              <li>
                <p class="definition-text">${escapeHtml(sense.definition || "")}</p>
                ${renderExamples(sense.examples)}
                <div class="meta-row mt-2">
                  ${renderArrayChips(sense.grammar)}
                  ${renderArrayChips(sense.dialects)}
                </div>
              </li>
            `;
          })
          .join("")}
      </ol>`
    );
  }

  function renderExamples(examples) {
    if (!Array.isArray(examples) || !examples.length) {
      return "";
    }

    return `
      <ul class="example-list">
        ${examples
          .map(function (example) {
            return renderExample(example);
          })
          .join("")}
      </ul>
    `;
  }

  function renderExample(example) {
    const shona = exampleTextPart(example, "shona");
    const english = exampleTextPart(example, "english");
    const sourceNote = exampleTextPart(example, "source_note");

    return `
      <li class="example-item">
        ${shona ? `<p class="example-shona">${escapeHtml(shona)}</p>` : ""}
        ${english ? `<p class="example-english">${escapeHtml(english)}</p>` : ""}
        ${sourceNote ? `<p class="example-source">${escapeHtml(sourceNote)}</p>` : ""}
      </li>
    `;
  }

  function renderNounClassTable(nounClass) {
    if (!nounClass) {
      return "";
    }

    const details = [
      ["Label", nounClass.label],
      ["Nominal prefix", nounClass.nominal_prefix],
      ["Default plural", nounClass.default_plural_class_number],
      ["Subject concord", nounClass.subject_concord],
      ["Object concord", nounClass.object_concord],
      ["Possessive concord", nounClass.possessive_concord],
      ["Adjectival concord", nounClass.adjectival_concord],
      ["Relative concord", nounClass.relative_concord],
      ["Associative concord", nounClass.associative_concord],
      ["Proximal demonstrative", nounClass.demonstrative_proximal],
      ["Medial demonstrative", nounClass.demonstrative_medial],
      ["Distal demonstrative", nounClass.demonstrative_distal],
    ];
    return section("Noun Class & Concord Morphology", renderKeyValueList(details));
  }

  function renderToneRecords(tones) {
    if (!tones.length) {
      return "";
    }

    return section(
      "Tone Rules",
      `<ul class="compact-list">
        ${tones
          .map(function (tone) {
            return `
              <li>
                <div class="tone-pattern-row">
                  <strong class="tone-pattern font-bold">[${escapeHtml(tone.pattern)}]</strong>
                  <span class="tone-system">${escapeHtml(humanize(tone.notation_system))}</span>
                </div>
                ${tone.note ? `<p class="tone-note">${escapeHtml(tone.note)}</p>` : ""}
              </li>
            `;
          })
          .join("")}
      </ul>`
    );
  }

  function renderForms(forms) {
    if (!forms.length) {
      return "";
    }

    return section(
      "Forms & Conjugations",
      `<ul class="compact-list">
        ${forms
          .map(function (form) {
            return `
              <li>
                <strong>${escapeHtml(form.form_text)}</strong>
                <span>${escapeHtml(humanize(form.form_kind))}</span>
                <div class="meta-row mt-1">${renderArrayChips(form.grammar)}</div>
                ${renderDerivedFormEvidence(form)}
              </li>
            `;
          })
          .join("")}
      </ul>`
    );
  }

  function renderMetadata(lemma) {
    const details = [
      ["Learner level", humanize(lemma.learner_level)],
      ["Curriculum stage", humanize(lemma.curriculum_stage)],
      ["Frequency tier", humanize(lemma.frequency_tier)],
      ["Review state", humanize(lemma.review_state)],
      ["First appearance source", lemma.first_appearance_source_key],
      ["Locator reference", lemma.first_appearance_locator],
    ];
    return section("Metadata Profile", renderKeyValueList(details));
  }

  function section(title, body) {
    return `
      <section class="entry-section">
        <h3>${escapeHtml(title)}</h3>
        <div class="section-body">${body}</div>
      </section>
    `;
  }

  function renderKeyValueList(items) {
    const rows = items
      .filter(function (item) {
        return item[1] !== null && item[1] !== undefined && item[1] !== "";
      })
      .map(function (item) {
        return `
          <div class="kv-row">
            <dt>${escapeHtml(item[0])}</dt>
            <dd>${escapeHtml(item[1])}</dd>
          </div>
        `;
      })
      .join("");

    return rows ? `<dl class="kv-list">${rows}</dl>` : '<p class="muted">No metadata exposed.</p>';
  }

  function renderArrayChips(values) {
    if (!Array.isArray(values)) {
      return "";
    }
    return values.map(function (value) {
      return chip(value);
    }).join("");
  }

  function renderCountChip(label, count) {
    if (typeof count !== "number" || count < 1) {
      return "";
    }
    return chip(`${count} ${label}`);
  }

  function chip(value) {
    if (!value) {
      return "";
    }
    return `<span class="meta-chip">${escapeHtml(value)}</span>`;
  }

  function exampleTextPart(example, key) {
    if (typeof example === "string") {
      return key === "shona" ? example : "";
    }
    if (example && typeof example === "object") {
      return example[key] || "";
    }
    return "";
  }

  // --- General Helpers ---

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
