/* app.js — logique de l'interface HistoSpec (sans framework, fetch API) */

const state = {
  sourceId: null,
  refId: null,
  resultId: null,
};

const els = {
  dzSource: document.getElementById("dropzone-source"),
  fileSource: document.getElementById("file-source"),
  imgSource: document.getElementById("img-source"),
  imgSourcePlaceholder: document.getElementById("img-source-placeholder"),
  statsSource: document.getElementById("stats-source"),
  badgeSource: document.getElementById("badge-source"),

  dzRef: document.getElementById("dropzone-ref"),
  fileRef: document.getElementById("file-ref"),
  imgRef: document.getElementById("img-ref"),
  imgRefPlaceholder: document.getElementById("img-ref-placeholder"),
  badgeRef: document.getElementById("badge-ref"),

  imgResult: document.getElementById("img-result"),
  imgResultPlaceholder: document.getElementById("img-result-placeholder"),
  statsResult: document.getElementById("stats-result"),
  downloadLink: document.getElementById("download-link"),
  badgeResult: document.getElementById("badge-result"),

  btnEqualize: document.getElementById("btn-equalize"),
  profileSelect: document.getElementById("profile-select"),
  btnSpecifyProfile: document.getElementById("btn-specify-profile"),
  profileParams: document.getElementById("profile-params"),

  btnSpecifyRef: document.getElementById("btn-specify-ref"),

  threshManualRow: document.getElementById("thresh-manual-row"),
  threshLow: document.getElementById("thresh-low"),
  threshHigh: document.getElementById("thresh-high"),
  btnThreshold: document.getElementById("btn-threshold"),

  morphShape: document.getElementById("morph-shape"),
  morphSize: document.getElementById("morph-size"),

  btnParticles: document.getElementById("btn-particles"),
  particlesResult: document.getElementById("particles-result"),
  particlesChartWrap: document.getElementById("particles-chart-wrap"),
  particlesTableWrap: document.getElementById("particles-table-wrap"),
  particlesTableBody: document.getElementById("particles-table-body"),

  btnUseResult: document.getElementById("btn-use-result"),
  btnReset: document.getElementById("btn-reset"),

  toastContainer: document.getElementById("toast-container"),
  serverStatusDot: document.getElementById("server-status-dot"),
  serverStatusText: document.getElementById("server-status-text"),
};

let chartSource, chartResult, chartProfilePreview, chartGranulometry;

// ---------------------------------------------------------------------
// Notifications (remplace window.alert par des toasts non bloquants)
// ---------------------------------------------------------------------

function toast(message, { title, type = "info", timeout = 4500 } = {}) {
  const el = document.createElement("div");
  el.className = `toast${type === "error" ? " toast-error" : ""}`;
  el.innerHTML = `${title ? `<strong>${title}</strong>` : ""}${message}`;
  els.toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity .2s";
    setTimeout(() => el.remove(), 200);
  }, timeout);
}

function toastError(err) {
  toast(err.message || "Une erreur inconnue est survenue.", { title: "Erreur", type: "error" });
}

/** Affiche un badge « couleur » / « niveaux de gris » à côté d'un titre de
 * panneau, pour signaler clairement quel type d'image est en cours de
 * traitement (les opérations de seuillage / morphologie convertissent
 * toujours vers la luminance, voir toast d'information dédié). */
function setColorBadge(el, isColor) {
  el.textContent = isColor ? "couleur (RVB)" : "niveaux de gris";
  el.classList.remove("hidden", "text-amber", "border-amber/40", "text-slate-500", "border-line");
  if (isColor) {
    el.classList.add("text-amber", "border-amber/40");
  } else {
    el.classList.add("text-slate-500", "border-line");
  }
}

// ---------------------------------------------------------------------
// Utilitaires réseau
// ---------------------------------------------------------------------

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erreur serveur");
  }
  return res.json();
}

async function postQuery(url) {
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erreur serveur");
  }
  return res.json();
}

/** Désactive un bouton et affiche un état "en cours" pendant l'exécution
 * de `fn`, puis restaure son état. Empêche aussi les doubles clics. */
async function withLoading(button, fn) {
  if (button.dataset.busy === "1") return;
  const originalText = button.innerHTML;
  button.dataset.busy = "1";
  button.disabled = true;
  button.classList.add("is-loading");
  button.innerHTML = "Traitement…";
  try {
    await fn();
  } catch (e) {
    toastError(e);
  } finally {
    button.dataset.busy = "0";
    button.disabled = false;
    button.classList.remove("is-loading");
    button.innerHTML = originalText;
    syncButtonAvailability();
  }
}

// ---------------------------------------------------------------------
// État des boutons / placeholders
// ---------------------------------------------------------------------

function syncButtonAvailability() {
  const hasSource = !!state.sourceId;
  [els.btnEqualize, els.btnSpecifyProfile, els.btnThreshold, els.btnParticles]
    .forEach(b => { b.disabled = !hasSource; });
  document.querySelectorAll("[data-morph]").forEach(b => { b.disabled = !hasSource; });
  els.btnSpecifyRef.disabled = !(hasSource && state.refId);
  els.btnUseResult.disabled = !state.resultId;
}

// ---------------------------------------------------------------------
// Statistiques & histogrammes
// ---------------------------------------------------------------------

function fmtStats(stats) {
  const labels = {
    mean: "Moyenne", std: "Écart-type", min: "Min", max: "Max",
    median: "Médiane", integrated_density: "Densité intégrée",
    skewness: "Dissymétrie", kurtosis: "Aplatissement", entropy: "Entropie",
  };
  return Object.entries(stats).map(([k, v]) =>
    `<span>${labels[k] || k}</span><b>${v}</b>`
  ).join("");
}

function chartColors() {
  return {
    grid: "#1c2333",
    ticks: "#7c8aa3",
  };
}

function makeHistChart(canvasId, levels, counts, color) {
  const c = chartColors();
  const ctx = document.getElementById(canvasId).getContext("2d");
  return new Chart(ctx, {
    type: "bar",
    data: {
      labels: levels,
      datasets: [{
        label: "Nombre de pixels",
        data: counts,
        backgroundColor: color,
        borderWidth: 0,
        barPercentage: 1.0,
        categoryPercentage: 1.0,
      }],
    },
    options: {
      responsive: true,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: c.ticks, font: { family: "JetBrains Mono", size: 10 } }, grid: { display: false } },
        y: { ticks: { color: c.ticks, font: { family: "JetBrains Mono", size: 10 } }, grid: { color: c.grid } },
      },
    },
  });
}

async function refreshHistogramChart(imageId, whichChart) {
  const res = await fetch(`/api/histogram/${imageId}`);
  if (!res.ok) throw new Error("Impossible de charger l'histogramme.");
  const data = await res.json();
  if (whichChart === "source") {
    if (chartSource) chartSource.destroy();
    chartSource = makeHistChart("chart-source", data.levels, data.counts, "#e7a94c");
    els.statsSource.innerHTML = fmtStats(data.stats);
  } else {
    if (chartResult) chartResult.destroy();
    chartResult = makeHistChart("chart-result", data.levels, data.counts, "#4fc9b8");
    els.statsResult.innerHTML = fmtStats(data.stats);
  }
}

// ---------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------

async function uploadFile(file, target) {
  const form = new FormData();
  form.append("file", file);
  let res;
  try {
    res = await fetch("/api/images/upload", { method: "POST", body: form });
  } catch (e) {
    toast("Le serveur ne répond pas.", { title: "Échec de l'upload", type: "error" });
    return;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Fichier invalide." }));
    toast(err.detail, { title: "Échec de l'upload", type: "error" });
    return;
  }
  const data = await res.json();

  if (target === "source") {
    state.sourceId = data.image_id;
    state.resultId = null;
    els.imgSource.src = `/api/images/${data.image_id}/png`;
    els.imgSource.classList.remove("hidden");
    els.imgSourcePlaceholder.classList.add("hidden");
    els.statsSource.innerHTML = fmtStats(data.stats);
    setColorBadge(els.badgeSource, data.is_color);
    els.imgResult.classList.add("hidden");
    els.imgResultPlaceholder.classList.remove("hidden");
    els.statsResult.innerHTML = "";
    els.badgeResult.classList.add("hidden");
    els.downloadLink.style.display = "none";
    await refreshHistogramChart(data.image_id, "source");
    toast(`${data.filename} (${data.width}×${data.height}px, ${data.is_color ? "couleur" : "niveaux de gris"})`, { title: "Image source chargée" });
  } else {
    state.refId = data.image_id;
    els.imgRef.src = `/api/images/${data.image_id}/png`;
    els.imgRef.classList.remove("hidden");
    els.imgRefPlaceholder.classList.add("hidden");
    setColorBadge(els.badgeRef, data.is_color);
    toast(`${data.filename} (${data.width}×${data.height}px, ${data.is_color ? "couleur" : "niveaux de gris"})`, { title: "Image de référence chargée" });
  }
  syncButtonAvailability();
}

function wireDropzone(dzEl, inputEl, target) {
  dzEl.addEventListener("click", () => inputEl.click());
  dzEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputEl.click(); }
  });
  inputEl.addEventListener("change", () => {
    if (inputEl.files[0]) uploadFile(inputEl.files[0], target);
  });
  ["dragover", "dragleave", "drop"].forEach(evt => {
    dzEl.addEventListener(evt, (e) => {
      e.preventDefault();
      dzEl.classList.toggle("dropzone-active", evt === "dragover");
    });
  });
  dzEl.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file, target);
  });
}

wireDropzone(els.dzSource, els.fileSource, "source");
wireDropzone(els.dzRef, els.fileRef, "ref");

// ---------------------------------------------------------------------
// Résultat commun
// ---------------------------------------------------------------------

async function showResult(resp, successLabel) {
  state.resultId = resp.result_image_id;
  els.imgResult.src = `/api/images/${resp.result_image_id}/png`;
  els.imgResult.classList.remove("hidden");
  els.imgResultPlaceholder.classList.add("hidden");
  els.statsResult.innerHTML = fmtStats(resp.stats_after);
  setColorBadge(els.badgeResult, resp.is_color);
  els.downloadLink.href = `/api/images/${resp.result_image_id}/png`;
  els.downloadLink.download = `histospec_${resp.operation}.png`;
  els.downloadLink.style.display = "inline-block";
  await refreshHistogramChart(resp.result_image_id, "result");
  syncButtonAvailability();
  if (resp.params && resp.params.note) {
    toast(resp.params.note, { title: "Info" });
  }
  if (successLabel) {
    const suffix = resp.is_color && resp.params && resp.params.channels ? ` (${resp.params.channels})` : "";
    toast(successLabel + suffix, { title: "Traitement appliqué" });
  }
}

// ---------------------------------------------------------------------
// Égalisation
// ---------------------------------------------------------------------

els.btnEqualize.addEventListener("click", () => withLoading(els.btnEqualize, async () => {
  const resp = await postQuery(`/api/histogram/equalize?image_id=${state.sourceId}`);
  await showResult(resp, "Histogramme égalisé (distribution uniforme).");
}));

// ---------------------------------------------------------------------
// Spécification par profil théorique
// ---------------------------------------------------------------------

const PROFILE_FIELDS = {
  gaussian: [
    { key: "mean", label: "Moyenne", value: 128 },
    { key: "std", label: "Écart-type", value: 40 },
  ],
  exponential: [
    { key: "rate", label: "Taux", value: 0.02, step: 0.005 },
    { key: "invert", label: "Inverser (tons clairs)", type: "checkbox", value: false },
  ],
  bimodal: [
    { key: "m1", label: "Moy. 1", value: 60 },
    { key: "s1", label: "Écart 1", value: 20 },
    { key: "m2", label: "Moy. 2", value: 190 },
    { key: "s2", label: "Écart 2", value: 20 },
    { key: "w1", label: "Poids 1", value: 0.5, step: 0.05 },
  ],
  uniform: [],
};

function renderProfileParams() {
  const profile = els.profileSelect.value;
  const fields = PROFILE_FIELDS[profile] || [];
  els.profileParams.innerHTML = fields.map(f => {
    if (f.type === "checkbox") {
      return `
        <label class="param-checkbox col-span-full">
          <input type="checkbox" data-key="${f.key}" data-type="checkbox" ${f.value ? "checked" : ""} class="accent-amber" />
          ${f.label}
        </label>`;
    }
    return `
      <label class="field-label">${f.label}
        <input type="number" data-key="${f.key}" value="${f.value}" step="${f.step || 1}" class="field w-full mt-1" />
      </label>`;
  }).join("");
  previewProfile();
}

function readProfileParams() {
  const inputs = els.profileParams.querySelectorAll("input[data-key]");
  const params = {};
  inputs.forEach(i => {
    params[i.dataset.key] = i.dataset.type === "checkbox" ? i.checked : parseFloat(i.value);
  });
  return params;
}

async function previewProfile() {
  const profile = els.profileSelect.value;
  const params = readProfileParams();
  const qs = new URLSearchParams(params).toString();
  try {
    const res = await fetch(`/api/histogram/profile/${profile}?${qs}`);
    if (!res.ok) return;
    const data = await res.json();
    if (chartProfilePreview) chartProfilePreview.destroy();
    chartProfilePreview = makeHistChart("chart-profile-preview", data.levels, data.counts, "#7c8aa3");
  } catch (e) { /* aperçu non bloquant */ }
}

els.profileSelect.addEventListener("change", renderProfileParams);
els.profileParams.addEventListener("input", previewProfile);
els.profileParams.addEventListener("change", previewProfile);
renderProfileParams();

els.btnSpecifyProfile.addEventListener("click", () => withLoading(els.btnSpecifyProfile, async () => {
  if (!state.sourceId) throw new Error("Charger d'abord une image source.");
  const body = { image_id: state.sourceId, profile: els.profileSelect.value, ...readProfileParams() };
  const resp = await postJSON("/api/histogram/specify/profile", body);
  await showResult(resp, `Histogramme spécifié selon un profil ${els.profileSelect.value}.`);
}));

// ---------------------------------------------------------------------
// Spécification par image de référence
// ---------------------------------------------------------------------

els.btnSpecifyRef.addEventListener("click", () => withLoading(els.btnSpecifyRef, async () => {
  if (!state.refId) throw new Error("Charger d'abord une image de référence.");
  const resp = await postJSON("/api/histogram/specify/reference", {
    image_id: state.sourceId, reference_image_id: state.refId,
  });
  await showResult(resp, "Histogramme spécifié à partir de l'image de référence.");
}));

// ---------------------------------------------------------------------
// Seuillage
// ---------------------------------------------------------------------

document.querySelectorAll('input[name="thresh-mode"]').forEach(r => {
  r.addEventListener("change", () => {
    els.threshManualRow.style.display =
      document.querySelector('input[name="thresh-mode"]:checked').value === "manual" ? "flex" : "none";
  });
});

els.btnThreshold.addEventListener("click", () => withLoading(els.btnThreshold, async () => {
  const mode = document.querySelector('input[name="thresh-mode"]:checked').value;
  const low = parseInt(els.threshLow.value, 10);
  const high = parseInt(els.threshHigh.value, 10);
  if (mode === "manual" && low > high) throw new Error("La borne basse doit être ≤ à la borne haute.");
  const resp = await postJSON("/api/histogram/threshold", {
    image_id: state.sourceId, mode, low, high,
  });
  const detail = mode === "otsu"
    ? `Seuil calculé automatiquement : ${resp.params.computed_threshold}.`
    : `Seuillage manuel [${low}, ${high}].`;
  await showResult(resp, detail);
}));

// ---------------------------------------------------------------------
// Morphologie mathématique
// ---------------------------------------------------------------------

const MORPH_LABELS = {
  erode: "Érosion", dilate: "Dilatation", opening: "Ouverture", closing: "Fermeture",
  gradient: "Gradient morphologique", tophat: "Chapeau haut de forme", skeleton: "Squelette",
};

document.querySelectorAll("[data-morph]").forEach(btn => {
  btn.addEventListener("click", () => withLoading(btn, async () => {
    const resp = await postJSON("/api/morphology/apply", {
      image_id: state.sourceId,
      operation: btn.dataset.morph,
      shape: els.morphShape.value,
      size: parseInt(els.morphSize.value, 10),
    });
    await showResult(resp, `${MORPH_LABELS[btn.dataset.morph] || btn.dataset.morph} appliquée.`);
  }));
});

// ---------------------------------------------------------------------
// Mesures / granulométrie
// ---------------------------------------------------------------------

function renderParticlesTable(particles, truncated) {
  if (!particles.length) {
    els.particlesTableWrap.classList.add("hidden");
    return;
  }
  els.particlesTableBody.innerHTML = particles.map(p => `
    <tr class="odd:bg-panel2/40">
      <td class="px-2 py-1 text-slate-500">${p.label}</td>
      <td class="px-2 py-1">${p.area}</td>
      <td class="px-2 py-1">${p.equivalent_diameter}</td>
      <td class="px-2 py-1">${p.circularity}</td>
    </tr>
  `).join("") + (truncated ? `
    <tr><td colspan="4" class="px-2 py-1 text-slate-600 italic">liste tronquée à 500 particules (synthèse sur l'ensemble)</td></tr>
  ` : "");
  els.particlesTableWrap.classList.remove("hidden");
}

function renderGranulometryChart(summary) {
  if (!summary.diameter_classes || !summary.diameter_classes.length) {
    els.particlesChartWrap.classList.add("hidden");
    return;
  }
  els.particlesChartWrap.classList.remove("hidden");
  if (chartGranulometry) chartGranulometry.destroy();
  chartGranulometry = makeHistChart(
    "chart-granulometry", summary.diameter_classes, summary.diameter_counts, "#e2687e"
  );
}

els.btnParticles.addEventListener("click", () => withLoading(els.btnParticles, async () => {
  const data = await postJSON("/api/measurements/particles", {
    image_id: state.sourceId, connectivity: 8, min_area: 4, n_classes: 8,
  });
  const s = data.summary;
  els.particlesResult.innerHTML = `
    <span>Nb. particules</span><b>${s.n_particles}</b>
    <span>Compacité</span><b>${s.compacity}</b>
    <span>Diamètre moyen</span><b>${s.mean_diameter}px</b>
  `;
  renderGranulometryChart(s);
  renderParticlesTable(data.particles, data.truncated);
  toast(`${s.n_particles} particule(s) détectée(s).`, { title: "Analyse terminée" });
}));

// ---------------------------------------------------------------------
// Chaînage / reset
// ---------------------------------------------------------------------

els.btnUseResult.addEventListener("click", () => withLoading(els.btnUseResult, async () => {
  if (!state.resultId) return;
  state.sourceId = state.resultId;
  state.resultId = null;
  els.imgSource.src = `/api/images/${state.sourceId}/png`;
  els.imgSource.classList.remove("hidden");
  els.imgSourcePlaceholder.classList.add("hidden");
  els.badgeSource.className = els.badgeResult.className; // même statut couleur / niveaux de gris
  els.badgeSource.textContent = els.badgeResult.textContent;
  els.imgResult.classList.add("hidden");
  els.imgResultPlaceholder.classList.remove("hidden");
  els.statsResult.innerHTML = "";
  els.badgeResult.classList.add("hidden");
  els.downloadLink.style.display = "none";
  await refreshHistogramChart(state.sourceId, "source");
  toast("Le résultat devient la nouvelle image source.", { title: "Chaînage" });
}));

els.btnReset.addEventListener("click", () => window.location.reload());

// ---------------------------------------------------------------------
// Statut serveur (petit ping /health au chargement)
// ---------------------------------------------------------------------

(async function pingServer() {
  try {
    const res = await fetch("/health");
    if (res.ok) {
      els.serverStatusText.textContent = "serveur en ligne";
    } else {
      throw new Error();
    }
  } catch (e) {
    els.serverStatusDot.classList.replace("bg-teal", "bg-rose");
    els.serverStatusText.textContent = "serveur indisponible";
  }
})();

syncButtonAvailability();
