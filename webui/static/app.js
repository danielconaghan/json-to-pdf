"use strict";

// Render view: edit the document JSON on the left, see the real rendered PDF on
// the right. Every edit debounces into POST /api/preview-mapped; the returned
// PDF is painted by the shared preview controller (preview.js) into a scroll
// container we own, and the returned element-to-page map drives editor<->preview
// sync. Download hits POST /api/render.

import { createPreview } from "/preview.js";
import {
  buildContentRanges,
  caretElementIndex,
  topLevelKeyAtCaret,
  bandForPoint,
  firstBandForIndex,
} from "/sync.js";

const editor = document.getElementById("editor");
const preview = document.getElementById("preview");
const renderView = document.getElementById("render-view");
const editorStatus = document.getElementById("editor-status");
const previewStatus = document.getElementById("preview-status");
const errorBanner = document.getElementById("error-banner");
const exampleSelect = document.getElementById("example-select");
const formatBtn = document.getElementById("format-btn");
const downloadBtn = document.getElementById("download-btn");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const zoomFitBtn = document.getElementById("zoom-fit");
const zoomLevel = document.getElementById("zoom-level");

const previewCtl = createPreview({ container: preview, zoomLevelEl: zoomLevel });

const DEBOUNCE_MS = 600;
const STARTER = {
  document: { title: "My Report" },
  cover: {
    title: "My Report",
    subtitle: "Draft",
    author: "Acme",
    date: "1 July 2026",
  },
  content: [
    { type: "heading", level: 1, text: "Introduction" },
    { type: "paragraph", text: "Edit the JSON on the left — the preview updates automatically." },
  ],
};

let debounceTimer = null;
let renderSeq = 0; // guards against out-of-order network responses
let resizeTimer = null;

let sourceMap = []; // element-to-page bands from the last /api/preview-mapped
let caretTimer = null; // debounces editor caret -> preview sync
let syncingFromClick = false; // suppresses the caret handler while we set a selection

// ---- editor state helpers ----------------------------------------------

function setEditorStatus(text, kind) {
  editorStatus.textContent = text;
  editorStatus.className = "status" + (kind ? " " + kind : "");
}

function setPreviewStatus(text, kind) {
  previewStatus.textContent = text;
  previewStatus.className = "status" + (kind ? " " + kind : "");
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.hidden = false;
}

function clearError() {
  errorBanner.hidden = true;
  errorBanner.textContent = "";
}

/** Parse the editor contents; returns {config} or {error}. */
function parseEditor() {
  const text = editor.value.trim();
  if (!text) return { error: "Document is empty." };
  try {
    const config = JSON.parse(text);
    if (config === null || typeof config !== "object" || Array.isArray(config)) {
      return { error: "Top-level JSON must be an object." };
    }
    return { config };
  } catch (e) {
    return { error: "Invalid JSON: " + e.message };
  }
}

// ---- rendering ----------------------------------------------------------

// resetView=true snaps to the top at 100% fit (first load, example switch);
// false keeps the reader's current scroll offset and zoom (an edit).
async function renderPreview(resetView) {
  const parsed = parseEditor();
  if (parsed.error) {
    setEditorStatus(parsed.error, "err");
    downloadBtn.disabled = true;
    return;
  }
  setEditorStatus("Valid JSON", "ok");

  const seq = ++renderSeq;
  setPreviewStatus("Rendering…");

  let resp;
  try {
    resp = await fetch("/api/preview-mapped", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: parsed.config }),
    });
  } catch (e) {
    if (seq !== renderSeq) return;
    setPreviewStatus("", "err");
    showError("Could not reach the render server: " + e.message);
    return;
  }

  if (seq !== renderSeq) return; // a newer render superseded this one

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      detail = (await resp.json()).error || detail;
    } catch (_) { /* non-JSON error body */ }
    setPreviewStatus("Render failed", "err");
    showError(detail);
    downloadBtn.disabled = true;
    return;
  }

  // /api/preview-mapped returns {pdf: base64, map: [bands]}: the PDF plus the
  // element-to-page map that drives editor<->preview sync.
  const payload = await resp.json();
  if (seq !== renderSeq) return;
  const bytes = Uint8Array.from(atob(payload.pdf), (ch) => ch.charCodeAt(0));

  try {
    await previewCtl.showPdf(bytes, { resetView });
    sourceMap = payload.map || [];
  } catch (e) {
    if (seq !== renderSeq) return;
    setPreviewStatus("Preview failed", "err");
    showError("Could not display the PDF: " + e.message);
    return;
  }

  clearError();
  setPreviewStatus("Up to date", "ok");
  downloadBtn.disabled = false;
}

function scheduleRender() {
  const parsed = parseEditor();
  setEditorStatus(parsed.error || "Valid JSON", parsed.error ? "err" : "ok");
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => renderPreview(false), DEBOUNCE_MS);
}

// ---- download -----------------------------------------------------------

async function download() {
  const parsed = parseEditor();
  if (parsed.error) return;

  const title = (parsed.config.document && parsed.config.document.title) || "document";
  const filename = title.replace(/[^\w.-]+/g, "_");

  downloadBtn.disabled = true;
  const original = downloadBtn.textContent;
  downloadBtn.textContent = "Rendering…";
  try {
    const resp = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: parsed.config, filename }),
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try { detail = (await resp.json()).error || detail; } catch (_) {}
      showError(detail);
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename + ".pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } finally {
    downloadBtn.textContent = original;
    downloadBtn.disabled = false;
  }
}

// ---- examples -----------------------------------------------------------

async function loadExampleList() {
  try {
    const resp = await fetch("/api/examples");
    if (!resp.ok) return;
    const names = await resp.json();
    for (const name of names) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      exampleSelect.appendChild(opt);
    }
  } catch (_) { /* offline example list is non-fatal */ }
}

async function loadExample(name) {
  if (!name) return;
  try {
    const resp = await fetch("/api/examples/" + encodeURIComponent(name));
    if (!resp.ok) {
      showError("Could not load example: " + name);
      return;
    }
    const config = await resp.json();
    editor.value = JSON.stringify(config, null, 2);
    renderPreview(true);
  } catch (e) {
    showError("Could not load example: " + e.message);
  }
}

function formatJson() {
  const parsed = parseEditor();
  if (parsed.error) {
    setEditorStatus(parsed.error, "err");
    return;
  }
  editor.value = JSON.stringify(parsed.config, null, 2);
  setEditorStatus("Formatted", "ok");
}

// ---- editor <-> preview sync -------------------------------------------

// Click a rendered element -> select its JSON. Convert the click point to a
// bottom-origin PDF coordinate, ask the map which content element was drawn
// there, then select that element's text in the editor.
function handlePdfClick(e) {
  const canvas = e.target.closest(".pdf-page");
  if (!canvas || !sourceMap.length) return;
  const pageNum = Number(canvas.dataset.page);
  const pv = previewCtl.pageViews.find((p) => p.pageNum === pageNum);
  if (!pv) return;

  const rect = canvas.getBoundingClientRect();
  const offsetY = e.clientY - rect.top; // CSS px from the page's top edge
  const y = (pv.viewport.height - offsetY) / previewCtl.scale; // -> bottom-origin PDF points
  const index = bandForPoint(sourceMap, pageNum, y);
  if (index < 0) return;

  selectContentElement(index);
  const band = firstBandForIndex(sourceMap, index);
  if (band) flashBand(band);
}

// Move the caret into a content element -> reveal it in the preview. Uses the
// live editor text (so it tracks edits) against the last render's map.
function syncPreviewToCaret() {
  if (syncingFromClick) {
    syncingFromClick = false; // consume the selection we just set from a click
    return;
  }
  if (!previewCtl.pageViews.length) return;
  const text = editor.value;
  const caret = editor.selectionStart;

  const index = caretElementIndex(buildContentRanges(text), caret);
  if (index >= 0) {
    const band = firstBandForIndex(sourceMap, index);
    if (band) {
      scrollPreviewToBand(band);
      flashBand(band);
    }
    return;
  }

  // The cover isn't a content element — it's page 1, drawn by a page template.
  // Editing its JSON should still pull the preview to it.
  if (topLevelKeyAtCaret(text, caret) === "cover") {
    const pv = previewCtl.pageViews.find((p) => p.pageNum === 1);
    if (pv) {
      const coverBand = { page: 1, y0: 0, y1: pv.viewport.height / previewCtl.scale };
      scrollPreviewToBand(coverBand);
      flashBand(coverBand);
    }
  }
}

// Select content[index]'s text in the editor and scroll it into view. Sets a
// guard so the resulting selection event doesn't bounce back to the preview.
function selectContentElement(index) {
  const ranges = buildContentRanges(editor.value);
  if (index >= ranges.length) return;
  const { start, end } = ranges[index];
  syncingFromClick = true;
  editor.focus();
  editor.setSelectionRange(start, end);
  scrollEditorToSelection(start);
}

// Textareas don't scroll to a programmatic selection on their own; approximate
// it by counting lines and centring the caret's line in the viewport.
function scrollEditorToSelection(pos) {
  const line = editor.value.slice(0, pos).split("\n").length - 1;
  const cs = getComputedStyle(editor);
  let lineHeight = parseFloat(cs.lineHeight);
  if (Number.isNaN(lineHeight)) lineHeight = parseFloat(cs.fontSize) * 1.4;
  const target = line * lineHeight - editor.clientHeight / 2 + lineHeight;
  editor.scrollTop = Math.max(0, target);
}

// Scroll the preview so a band sits about a third from the top.
function scrollPreviewToBand(band) {
  const pv = previewCtl.pageViews.find((p) => p.pageNum === band.page);
  if (!pv) return;
  const topInPage = pv.viewport.height - band.y1 * previewCtl.scale; // element's top edge, CSS px
  const target = pv.canvas.offsetTop + topInPage - preview.clientHeight / 3;
  preview.scrollTop = Math.max(0, target);
}

// Briefly outline a band in the preview. One highlight lives at a time; it
// removes itself when its fade animation ends.
let highlightEl = null;
function flashBand(band) {
  const pv = previewCtl.pageViews.find((p) => p.pageNum === band.page);
  if (!pv) return;
  if (highlightEl) highlightEl.remove();
  const el = document.createElement("div");
  el.className = "sync-highlight";
  el.style.left = pv.canvas.offsetLeft + "px";
  el.style.top = pv.canvas.offsetTop + (pv.viewport.height - band.y1 * previewCtl.scale) + "px";
  el.style.width = pv.viewport.width + "px";
  el.style.height = Math.max(2, (band.y1 - band.y0) * previewCtl.scale) + "px";
  el.addEventListener("animationend", () => {
    el.remove();
    if (highlightEl === el) highlightEl = null;
  });
  preview.appendChild(el);
  highlightEl = el;
}

// ---- wiring -------------------------------------------------------------

editor.addEventListener("input", scheduleRender);
formatBtn.addEventListener("click", formatJson);
downloadBtn.addEventListener("click", download);
exampleSelect.addEventListener("change", (e) => loadExample(e.target.value));

zoomInBtn.addEventListener("click", () => previewCtl.zoomIn());
zoomOutBtn.addEventListener("click", () => previewCtl.zoomOut());
zoomFitBtn.addEventListener("click", () => previewCtl.fitToWidth());

// Click a rendered element to jump to its JSON.
preview.addEventListener("click", handlePdfClick);

// Move the caret in the editor to reveal the matching element in the preview.
// Debounced so navigating (or typing) doesn't fire a scroll on every keystroke.
const scheduleCaretSync = () => {
  clearTimeout(caretTimer);
  caretTimer = setTimeout(syncPreviewToCaret, 250);
};
editor.addEventListener("keyup", scheduleCaretSync);
editor.addEventListener("click", scheduleCaretSync);

// When fitting to width, a window resize changes the target scale, so repaint —
// but skip it while the render view is hidden (a zero-width container would
// collapse the fit scale; the compose view repaints itself when shown).
window.addEventListener("resize", () => {
  if (renderView.hidden) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => previewCtl.onResize(), 150);
});

// Allow tab to indent inside the textarea instead of leaving it.
editor.addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    e.preventDefault();
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    editor.value = editor.value.slice(0, start) + "  " + editor.value.slice(end);
    editor.selectionStart = editor.selectionEnd = start + 2;
  }
});

editor.value = JSON.stringify(STARTER, null, 2);
loadExampleList();
renderPreview(true);
