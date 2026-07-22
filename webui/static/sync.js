"use strict";

// Pure logic for the two-way link between the JSON editor and the PDF preview.
// No DOM here — app.js owns the wiring and the geometry that needs live element
// measurements. These functions turn editor text and the server's position map
// (see pdfgen/sourcemap.py) into the indices and bands the glue needs.
//
// The unit of correspondence is a top-level content[] element: a click anywhere
// in a rendered paragraph maps to that whole paragraph's JSON, and vice versa —
// matching the JSON's own atoms and the server's element-level map.

// Locate each top-level content[] element in the raw editor text, returning
// {start, end} character offsets in element order. Works on any formatting (the
// user edits freely), so it scans structurally rather than trusting indentation.
// Returns [] when a top-level "content" array can't be found.
export function buildContentRanges(text) {
  const ranges = [];
  const stack = []; // frames: { type: "object"|"array", pendingKey }
  let inString = false;
  let esc = false;
  let strStart = -1;
  let lastString = null; // most recently closed string literal
  let contentDepth = -1; // stack length at which the content array sits; -1 if not open
  let elemStart = -1; // start offset of the element currently being scanned

  const top = () => stack[stack.length - 1];
  const inContent = () =>
    contentDepth !== -1 &&
    stack.length === contentDepth &&
    top() &&
    top().type === "array";

  const pushRange = (start, end) => {
    while (end > start && /\s/.test(text[end - 1])) end--; // drop trailing whitespace
    if (end > start) ranges.push({ start, end });
  };

  for (let i = 0; i < text.length; i++) {
    const c = text[i];

    if (inString) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') {
        inString = false;
        lastString = text.slice(strStart + 1, i);
      }
      continue;
    }

    // First meaningful char directly inside the content array opens an element.
    if (inContent() && elemStart < 0 && c !== "," && c !== "]" && !/\s/.test(c)) {
      elemStart = i;
    }

    if (c === '"') {
      inString = true;
      esc = false;
      strStart = i;
      continue;
    }

    if (c === ":") {
      if (top() && top().type === "object") top().pendingKey = lastString;
      continue;
    }

    if (c === ",") {
      if (inContent() && elemStart >= 0) {
        pushRange(elemStart, i);
        elemStart = -1;
      }
      continue;
    }

    if (c === "{" || c === "[") {
      const type = c === "{" ? "object" : "array";
      const parent = top();
      const isContent =
        type === "array" &&
        parent &&
        parent.type === "object" &&
        stack.length === 1 && // parent is the root object
        parent.pendingKey === "content";
      stack.push({ type, pendingKey: null });
      if (isContent) contentDepth = stack.length;
      continue;
    }

    if (c === "}" || c === "]") {
      if (inContent()) {
        if (elemStart >= 0) {
          pushRange(elemStart, i);
          elemStart = -1;
        }
        contentDepth = -1; // the content array just closed
      }
      if (stack.length) stack.pop();
      continue;
    }
  }

  return ranges;
}

// The top-level object key whose region the caret sits in (e.g. "cover",
// "content", "document"), or null if the caret is outside the root object or
// ahead of the first key. A key's region runs from that key up to the next
// top-level key, so the caret anywhere inside a value — or on its key — resolves
// to it. Used to sync sections that aren't content[] elements (the cover is
// drawn by a page template, not a flowable, so it has no band index).
export function topLevelKeyAtCaret(text, caret) {
  const marks = []; // { key, at } for each key at the root object's depth
  const stack = []; // container types: "object" | "array"
  let inString = false;
  let esc = false;
  let strStart = -1;
  let lastString = null;
  let lastStringStart = -1;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];

    if (inString) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') {
        inString = false;
        lastString = text.slice(strStart + 1, i);
        lastStringStart = strStart;
      }
      continue;
    }

    if (c === '"') {
      inString = true;
      esc = false;
      strStart = i;
    } else if (c === ":") {
      // A colon at the root object's depth closes a top-level key.
      if (stack.length === 1 && stack[0] === "object") {
        marks.push({ key: lastString, at: lastStringStart });
      }
    } else if (c === "{" || c === "[") {
      stack.push(c === "{" ? "object" : "array");
    } else if (c === "}" || c === "]") {
      if (stack.length) stack.pop();
    }
  }

  let current = null;
  for (const m of marks) {
    if (m.at <= caret) current = m.key;
    else break;
  }
  return current;
}

// Which content element the caret sits in, or -1 if it's outside every element
// (in whitespace between them, or outside the content array entirely).
export function caretElementIndex(ranges, caret) {
  for (let i = 0; i < ranges.length; i++) {
    if (caret >= ranges[i].start && caret <= ranges[i].end) return i;
  }
  return -1;
}

// The content index drawn at a point on a page, or -1 if the point hit no
// element. bands are the server's records; page is 1-based; y is a
// bottom-origin PDF-point coordinate. When bands overlap, the smallest wins so
// a click resolves to the most specific element.
export function bandForPoint(bands, page, y) {
  let best = null;
  for (const b of bands) {
    if (b.page !== page || y < b.y0 || y > b.y1) continue;
    if (best === null || b.y1 - b.y0 < best.y1 - best.y0) best = b;
  }
  return best ? best.index : -1;
}

// The topmost band for a content element (earliest page, highest on it), or
// null if the element never made it into the map (e.g. it produced no drawn
// flowable). Bottom-origin y means the larger y1 is visually higher.
export function firstBandForIndex(bands, index) {
  let best = null;
  for (const b of bands) {
    if (b.index !== index) continue;
    if (best === null || b.page < best.page || (b.page === best.page && b.y1 > best.y1)) {
      best = b;
    }
  }
  return best;
}
