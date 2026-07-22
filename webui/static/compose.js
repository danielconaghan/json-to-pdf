"use strict";

// Compose view: author a template, a values map, and a translations map on the
// left; see the composed document JSON and its rendered PDF on the right. Every
// edit debounces into POST /api/compose/render, which returns both the composed
// config and the PDF (see webui/server.py) so they always agree. The PDF is
// painted by the shared preview controller (preview.js); the composed JSON is
// shown read-only. There is no editor<->preview click-sync here — the left side
// is three separate inputs, not one addressable content[] stream.

import { createPreview } from "/preview.js";

const DEBOUNCE_MS = 600;

// The three inputs, each with its own JSON-validity status.
const INPUTS = [
  { key: "template", editorId: "tpl-editor", statusId: "tpl-status", label: "Template" },
  { key: "values", editorId: "values-editor", statusId: "values-status", label: "Values" },
  { key: "translations", editorId: "translations-editor", statusId: "translations-status", label: "Translations" },
];

let started = false;

export function initComposeView() {
  if (started) return; // one-time wiring; the view is lazy-initialised on first show
  started = true;

  const fields = INPUTS.map((spec) => ({
    ...spec,
    editor: document.getElementById(spec.editorId),
    status: document.getElementById(spec.statusId),
  }));
  const jsonOut = document.getElementById("compose-json");
  const previewBox = document.getElementById("compose-preview");
  const errorBanner = document.getElementById("compose-error");
  const composeStatus = document.getElementById("compose-status");
  const tabPdf = document.getElementById("compose-tab-pdf");
  const tabJson = document.getElementById("compose-tab-json");
  const pdfPane = document.getElementById("compose-pdf-pane");
  const jsonPane = document.getElementById("compose-json-pane");

  const previewCtl = createPreview({
    container: previewBox,
    zoomLevelEl: document.getElementById("compose-zoom-level"),
  });

  let debounceTimer = null;
  let composeSeq = 0; // guards against out-of-order network responses
  let resizeTimer = null;

  function setStatus(el, text, kind) {
    el.textContent = text;
    el.className = "status" + (kind ? " " + kind : "");
  }

  function showError(message) {
    errorBanner.textContent = message;
    errorBanner.hidden = false;
  }

  function clearError() {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
  }

  // Parse every input; set each field's status. Returns the assembled request
  // body {template, values, translations}, or null if any input is invalid.
  function parseInputs() {
    const body = {};
    let ok = true;
    for (const f of fields) {
      const text = f.editor.value.trim();
      if (!text) {
        setStatus(f.status, "Empty", "err");
        ok = false;
        continue;
      }
      try {
        const value = JSON.parse(text);
        if (value === null || typeof value !== "object" || Array.isArray(value)) {
          setStatus(f.status, "Must be an object", "err");
          ok = false;
          continue;
        }
        setStatus(f.status, "Valid JSON", "ok");
        body[f.key] = value;
      } catch (e) {
        setStatus(f.status, "Invalid JSON", "err");
        ok = false;
      }
    }
    return ok ? body : null;
  }

  // resetView snaps the PDF to fit-to-width top (seed load); false keeps the
  // reader's scroll/zoom across recompositions.
  async function runCompose(resetView) {
    const body = parseInputs();
    if (!body) {
      composeStatus.textContent = "";
      return;
    }

    const seq = ++composeSeq;
    composeStatus.textContent = "Composing…";
    composeStatus.className = "status";

    let resp;
    try {
      resp = await fetch("/api/compose/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (e) {
      if (seq !== composeSeq) return;
      setStatus(composeStatus, "", "err");
      showError("Could not reach the server: " + e.message);
      return;
    }

    if (seq !== composeSeq) return; // a newer compose superseded this one

    if (!resp.ok) {
      let detail = resp.statusText;
      try { detail = (await resp.json()).error || detail; } catch (_) { /* non-JSON */ }
      setStatus(composeStatus, "Compose failed", "err");
      showError(detail); // ComposeError names the offending node/key
      return;
    }

    // {config: composed, pdf: base64} — the composed JSON and its PDF together.
    const payload = await resp.json();
    if (seq !== composeSeq) return;
    jsonOut.textContent = JSON.stringify(payload.config, null, 2);
    const bytes = Uint8Array.from(atob(payload.pdf), (ch) => ch.charCodeAt(0));

    try {
      await previewCtl.showPdf(bytes, { resetView });
    } catch (e) {
      if (seq !== composeSeq) return;
      setStatus(composeStatus, "Preview failed", "err");
      showError("Could not display the PDF: " + e.message);
      return;
    }

    clearError();
    setStatus(composeStatus, "Up to date", "ok");
  }

  function scheduleCompose() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => runCompose(false), DEBOUNCE_MS);
  }

  // ---- PDF / JSON sub-tabs ----------------------------------------------

  function showTab(which) {
    const pdf = which === "pdf";
    pdfPane.hidden = !pdf;
    jsonPane.hidden = pdf;
    tabPdf.classList.toggle("active", pdf);
    tabJson.classList.toggle("active", !pdf);
    tabPdf.setAttribute("aria-selected", String(pdf));
    tabJson.setAttribute("aria-selected", String(!pdf));
    // A manually-set zoom is remembered across tab switches — the canvases keep
    // their pixel size while hidden, so switching back shows them unchanged. Only
    // re-fit when the preview is in fit-to-width mode (which may have been painted
    // at a stale width while hidden, e.g. after a resize on the JSON tab).
    if (pdf && previewCtl.hasDoc() && previewCtl.fitWidth) previewCtl.fitToWidth();
  }

  // ---- wiring -----------------------------------------------------------

  for (const f of fields) {
    f.editor.addEventListener("input", scheduleCompose);
    // Allow tab to indent inside the textarea instead of leaving it.
    f.editor.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = f.editor.selectionStart;
        const end = f.editor.selectionEnd;
        f.editor.value = f.editor.value.slice(0, start) + "  " + f.editor.value.slice(end);
        f.editor.selectionStart = f.editor.selectionEnd = start + 2;
      }
    });
  }

  document.getElementById("compose-zoom-in").addEventListener("click", () => previewCtl.zoomIn());
  document.getElementById("compose-zoom-out").addEventListener("click", () => previewCtl.zoomOut());
  document.getElementById("compose-zoom-fit").addEventListener("click", () => previewCtl.fitToWidth());
  tabPdf.addEventListener("click", () => showTab("pdf"));
  tabJson.addEventListener("click", () => showTab("json"));

  window.addEventListener("resize", () => {
    if (document.getElementById("compose-view").hidden || pdfPane.hidden) return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => previewCtl.onResize(), 150);
  });

  showTab("pdf");
  seedFromExample(fields).then(() => runCompose(true));
}

// Fill the three inputs from the bundled worked example the first time the view
// opens, so it demonstrates itself. A missing example is non-fatal — the user
// can still type their own inputs.
async function seedFromExample(fields) {
  try {
    const resp = await fetch("/api/compose/example");
    if (!resp.ok) return;
    const example = await resp.json();
    for (const f of fields) {
      if (example[f.key] !== undefined) {
        f.editor.value = JSON.stringify(example[f.key], null, 2);
      }
    }
  } catch (_) { /* offline seed is non-fatal */ }
}
