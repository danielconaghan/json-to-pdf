"use strict";

// Topbar Render/Compose toggle. Kept out of app.js and compose.js so neither
// owns the other's concern: this just flips which <section class="view"> is
// visible and lazily initialises the compose view the first time it is shown
// (its PDF preview can only fit-to-width once its container is on screen).

import { initComposeView } from "/compose.js";

const renderBtn = document.getElementById("mode-render");
const composeBtn = document.getElementById("mode-compose");
const renderView = document.getElementById("render-view");
const composeView = document.getElementById("compose-view");
const renderControls = document.getElementById("render-controls");

function activate(mode) {
  const compose = mode === "compose";
  renderView.hidden = compose;
  composeView.hidden = !compose;
  renderControls.hidden = compose; // Example/Format/Download are render-only
  renderBtn.classList.toggle("active", !compose);
  composeBtn.classList.toggle("active", compose);
  renderBtn.setAttribute("aria-selected", String(!compose));
  composeBtn.setAttribute("aria-selected", String(compose));
  if (compose) initComposeView();
}

renderBtn.addEventListener("click", () => activate("render"));
composeBtn.addEventListener("click", () => activate("compose"));
