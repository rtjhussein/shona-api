(function () {
  const shell = document.querySelector(".entry-shell");
  if (!shell) {
    return;
  }

  const entryRegion = shell.querySelector("[data-entry-region]");
  const relatedRegion = shell.querySelector("[data-related-region]");
  const jsonPanel = shell.querySelector("[data-json-panel]");
  const jsonOutput = shell.querySelector("[data-json-output]");
  const apiKeyPanel = shell.querySelector("[data-api-key-panel]");
  const apiKeyInput = shell.querySelector("[data-api-key-input]");
  const saveKeyButton = shell.querySelector("[data-save-key]");
  const clearKeyButton = shell.querySelector("[data-clear-key]");
  const apiKeyStorage = shell.dataset.apiKeyStorage;
  const lemmaPublicId = shell.dataset.lemmaPublicId;
  const endpoints = {
    lemma: shell.dataset.lemmaEndpoint,
    tsumo: shell.dataset.tsumoEndpoint,
    madimikira: shell.dataset.madimikiraEndpoint,
  };

  const savedKey = window.localStorage.getItem(apiKeyStorage);
  if (savedKey) {
    apiKeyInput.value = savedKey;
    loadEntry(savedKey);
  } else {
    apiKeyPanel.open = true;
    renderError(
      "API key required",
      "Add an API key to load this entry from the public API."
    );
  }

  saveKeyButton.addEventListener("click", function () {
    const key = apiKeyInput.value.trim();
    if (!key) {
      apiKeyInput.focus();
      return;
    }
    window.localStorage.setItem(apiKeyStorage, key);
    loadEntry(key);
  });

  clearKeyButton.addEventListener("click", function () {
    apiKeyInput.value = "";
    window.localStorage.removeItem(apiKeyStorage);
    apiKeyPanel.open = true;
    renderError(
      "API key cleared",
      "Add an API key to load this entry from the public API."
    );
  });

  async function loadEntry(apiKey) {
    renderState("Loading", "Fetching the public lemma API.");
    shell.querySelector(".entry-results").setAttribute("aria-busy", "true");

    try {
      const lemmaPayload = await fetchJson(endpoints.lemma, apiKey);
      const entryData = lemmaPayload.data;
      const relatedPayload = await fetchRelated(apiKey, entryData.lemma.public_id);

      renderEntry(entryData, lemmaPayload);
      renderRelated(relatedPayload.related, relatedPayload.errors);
      renderRawJson({
        lemma_response: lemmaPayload,
        related_figures: relatedPayload.related,
      });
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        apiKeyPanel.open = true;
        renderError("API key rejected", error.message || "Check the API key and try again.");
        return;
      }
      renderError(error.title || "Entry unavailable", error.message);
    } finally {
      shell.querySelector(".entry-results").setAttribute("aria-busy", "false");
    }
  }

  async function fetchRelated(apiKey, publicId) {
    const settled = await Promise.allSettled([
      fetchJson(endpoints.tsumo, apiKey),
      fetchJson(endpoints.madimikira, apiKey),
    ]);
    const related = [];
    const errors = [];

    settled.forEach(function (result, index) {
      const subtype = index === 0 ? "tsumo" : "madimikira";
      if (result.status === "rejected") {
        errors.push(subtype);
        return;
      }
      const results =
        result.value && result.value.data && Array.isArray(result.value.data.results)
          ? result.value.data.results
          : [];
      results.forEach(function (expression) {
        const linked = Array.isArray(expression.linked_lemmas)
          ? expression.linked_lemmas
          : [];
        const matches = linked.some(function (lemma) {
          return lemma.public_id === publicId;
        });
        if (matches) {
          related.push(expression);
        }
      });
    });

    return { related, errors };
  }

  async function fetchJson(endpoint, apiKey) {
    const response = await window.fetch(endpoint, {
      headers: {
        Authorization: `Api-Key ${apiKey}`,
        Accept: "application/json",
      },
    });
    const payload = await response.json();

    if (!response.ok) {
      const apiError = payload && payload.error ? payload.error : {};
      const detail = payload && payload.detail ? payload.detail : "";
      const error = new Error(
        apiError.message || detail || "The public API returned an error."
      );
      error.status = response.status;
      error.title = apiError.code || "API error";
      throw error;
    }

    return payload;
  }

  function renderEntry(data, envelope) {
    const lemma = data.lemma || {};
    const senses = Array.isArray(data.senses) ? data.senses : [];
    const tones = Array.isArray(data.tone_records) ? data.tone_records : [];
    const forms = Array.isArray(data.forms) ? data.forms : [];
    const nounClass = lemma.noun_class;
    const pos =
      lemma.part_of_speech_label || lemma.part_of_speech_code || "Unspecified part of speech";

    entryRegion.innerHTML = `
      <article class="entry-card">
        <div class="entry-heading">
          <div>
            <p class="eyebrow">${escapeHtml(pos)}</p>
            <h2 class="entry-headword">${escapeHtml(lemma.headword || "Untitled lemma")}</h2>
          </div>
          <span class="meta-chip mono">${escapeHtml(lemma.public_id || lemmaPublicId)}</span>
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
        ${renderNounClass(nounClass)}
        ${renderToneRecords(tones)}
        ${renderForms(forms)}
        ${renderMetadata(lemma, envelope)}
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
                <p>${escapeHtml(sense.definition || "")}</p>
                ${renderExamples(sense.examples)}
                <div class="meta-row">
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
            return `<li>${escapeHtml(exampleText(example))}</li>`;
          })
          .join("")}
      </ul>
    `;
  }

  function renderNounClass(nounClass) {
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
    ];
    return section("Noun Class", renderKeyValueList(details));
  }

  function renderToneRecords(tones) {
    if (!tones.length) {
      return "";
    }

    return section(
      "Tone",
      `<ul class="compact-list">
        ${tones
          .map(function (tone) {
            return `
              <li>
                <strong>${escapeHtml(tone.pattern)}</strong>
                <span>${escapeHtml(humanize(tone.notation_system))}</span>
                ${tone.note ? `<p>${escapeHtml(tone.note)}</p>` : ""}
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
      "Forms",
      `<ul class="compact-list">
        ${forms
          .map(function (form) {
            return `
              <li>
                <strong>${escapeHtml(form.form_text)}</strong>
                <span>${escapeHtml(humanize(form.form_kind))}</span>
                <div class="meta-row">${renderArrayChips(form.grammar)}</div>
                ${renderDerivedFormEvidence(form)}
              </li>
            `;
          })
          .join("")}
      </ul>`
    );
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

  function renderMetadata(lemma, envelope) {
    const details = [
      ["Data release", envelope.data_release],
      ["Rule set", envelope.rule_set_version],
      ["Learner level", humanize(lemma.learner_level)],
      ["Curriculum stage", humanize(lemma.curriculum_stage)],
      ["Frequency tier", humanize(lemma.frequency_tier)],
      ["Review state", humanize(lemma.review_state)],
      ["Source", lemma.first_appearance_source_key],
      ["Locator", lemma.first_appearance_locator],
    ];
    return section("Metadata", renderKeyValueList(details));
  }

  function renderRelated(related, errors) {
    if (!related.length && !errors.length) {
      relatedRegion.innerHTML = `
        <section class="entry-card related-card">
          <h2>Related</h2>
          <p class="muted">No linked tsumo or madimikira are exposed for this entry.</p>
        </section>
      `;
      return;
    }

    relatedRegion.innerHTML = `
      <section class="entry-card related-card">
        <h2>Related</h2>
        ${errors.length ? `<p class="muted">Some related public API lists could not be loaded: ${escapeHtml(errors.join(", "))}.</p>` : ""}
        ${
          related.length
            ? `<ul class="related-list">${related.map(renderRelatedItem).join("")}</ul>`
            : '<p class="muted">No linked records were found.</p>'
        }
      </section>
    `;
  }

  function renderRelatedItem(expression) {
    return `
      <li>
        <div class="related-header">
          <strong>${escapeHtml(expression.text || "")}</strong>
          <span class="badge">${escapeHtml(humanize(expression.subtype))}</span>
        </div>
        ${expression.meaning ? `<p>${escapeHtml(expression.meaning)}</p>` : ""}
        ${expression.english_rendering ? `<p class="muted">${escapeHtml(expression.english_rendering)}</p>` : ""}
        <div class="meta-row">${renderArrayChips(expression.cultural_themes)}</div>
      </li>
    `;
  }

  function renderRawJson(payload) {
    jsonOutput.textContent = JSON.stringify(payload, null, 2);
    jsonPanel.hidden = false;
  }

  function renderState(title, message) {
    entryRegion.innerHTML = `
      <div class="state-card">
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
    relatedRegion.innerHTML = "";
    jsonPanel.hidden = true;
  }

  function renderError(title, message) {
    entryRegion.innerHTML = `
      <div class="state-card state-card--error">
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message || "The entry could not be loaded.")}</p>
      </div>
    `;
    relatedRegion.innerHTML = "";
    jsonPanel.hidden = true;
  }

  function section(title, body) {
    return `
      <section class="entry-section">
        <h3>${escapeHtml(title)}</h3>
        ${body}
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

  function exampleText(example) {
    if (typeof example === "string") {
      return example;
    }
    if (example && typeof example === "object") {
      return example.text || example.shona || example.translation || JSON.stringify(example);
    }
    return "";
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
})();
