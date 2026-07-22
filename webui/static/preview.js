"use strict";

// A self-contained PDF preview bound to one scroll container. Loads a PDF from
// bytes and paints every page with PDF.js into canvases we own, preserving the
// reader's scroll offset and zoom across re-renders — the browser's built-in
// viewer resets to page 1 / top / default zoom on every new blob and exposes no
// way to restore position. Shared by the render view (app.js) and the compose
// view (compose.js) so neither duplicates the painting or zoom machinery.

import * as pdfjsLib from "/vendor/pdfjs/pdf.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc = "/vendor/pdfjs/pdf.worker.mjs";

const PAGE_PAD = 16; // .pdf-scroll horizontal padding, px — must match the CSS
const ZOOM_STEP = 1.2;
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 4;

function clampZoom(z) {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z));
}

// container    the .pdf-scroll element to paint into
// zoomLevelEl  optional <span> to write the current zoom percentage into
export function createPreview({ container, zoomLevelEl }) {
  let pdfDoc = null; // current PDFDocumentProxy, or null before the first render
  let fitWidth = true; // when true, scale tracks the container width on each paint
  let scale = 1; // page-units -> CSS px; recomputed from fitWidth when it is set
  let paintToken = 0; // guards against overlapping paint() calls
  let loadSeq = 0; // guards against overlapping showPdf() calls (out-of-order loads)
  let pageViews = []; // per rendered page: {pageNum, canvas, viewport} for hit-testing

  function updateZoomLabel() {
    if (zoomLevelEl) zoomLevelEl.textContent = Math.round(scale * 100) + "%";
  }

  // Paint every page of pdfDoc into the container. preserveScroll keeps the
  // current scrollTop (an edit); otherwise we start at the top.
  async function paint(preserveScroll) {
    if (!pdfDoc) return;
    const token = ++paintToken;
    const prevTop = preserveScroll ? container.scrollTop : 0;
    const dpr = window.devicePixelRatio || 1;

    const first = await pdfDoc.getPage(1);
    if (token !== paintToken) return;
    if (fitWidth) {
      const base = first.getViewport({ scale: 1 });
      const avail = container.clientWidth - PAGE_PAD * 2;
      // A hidden container reports zero width; keep the prior scale rather than
      // collapsing to the minimum, and refit once it becomes visible again.
      if (avail > 0) scale = clampZoom(avail / base.width);
    }
    updateZoomLabel();

    // Build all canvases at their final size first, swap them in, then restore
    // the scroll offset — so the container height is settled before we paint and
    // the position doesn't drift as pages fill in.
    const jobs = [];
    const frag = document.createDocumentFragment();
    for (let n = 1; n <= pdfDoc.numPages; n++) {
      const page = n === 1 ? first : await pdfDoc.getPage(n);
      if (token !== paintToken) return;
      const viewport = page.getViewport({ scale });
      const canvas = document.createElement("canvas");
      canvas.className = "pdf-page";
      canvas.dataset.page = String(n);
      canvas.width = Math.floor(viewport.width * dpr);
      canvas.height = Math.floor(viewport.height * dpr);
      canvas.style.width = Math.floor(viewport.width) + "px";
      canvas.style.height = Math.floor(viewport.height) + "px";
      frag.appendChild(canvas);
      jobs.push({ page, viewport, canvas });
    }
    if (token !== paintToken) return;
    container.replaceChildren(frag);
    container.scrollTop = prevTop;
    // Record geometry for click hit-testing and caret->preview scrolling.
    pageViews = jobs.map((j, i) => ({ pageNum: i + 1, canvas: j.canvas, viewport: j.viewport }));

    for (const { page, viewport, canvas } of jobs) {
      if (token !== paintToken) return;
      await page.render({
        canvasContext: canvas.getContext("2d"),
        viewport,
        transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
      }).promise;
    }
  }

  return {
    // Load PDF bytes and paint. resetView snaps to the top at fit-to-width
    // (first load, example switch); otherwise the reader's scroll and zoom are
    // kept (an edit). Rejects if the bytes are not a displayable PDF.
    async showPdf(bytes, { resetView = false } = {}) {
      const seq = ++loadSeq;
      const doc = await pdfjsLib.getDocument({ data: bytes }).promise;
      if (seq !== loadSeq) {
        doc.destroy(); // a newer showPdf superseded this load
        return;
      }
      if (pdfDoc) pdfDoc.destroy();
      pdfDoc = doc;
      if (resetView) fitWidth = true;
      await paint(!resetView);
    },
    zoomIn() { fitWidth = false; scale = clampZoom(scale * ZOOM_STEP); return paint(true); },
    zoomOut() { fitWidth = false; scale = clampZoom(scale / ZOOM_STEP); return paint(true); },
    fitToWidth() { fitWidth = true; return paint(true); },
    // Repaint on container resize, but only while fitting to width (otherwise the
    // fixed zoom needs no change). Callers should skip this when the container is
    // hidden — a zero clientWidth would collapse the fit scale.
    onResize() { if (fitWidth) return paint(true); },
    get scale() { return scale; },
    get fitWidth() { return fitWidth; },
    get pageViews() { return pageViews; },
    get container() { return container; },
    hasDoc() { return pdfDoc !== null; },
  };
}
