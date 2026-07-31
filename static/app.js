"use strict";

const state = { reference: null, filters: {} };

const CATEGORY_CLASS = {
  "Crimes Against Persons": "persons",
  "Crimes Against Property": "property",
  "Crimes Against Society": "society",
};

function categoryPill(cat) {
  const cls = CATEGORY_CLASS[cat] || "status";
  return `<span class="pill ${cls}">${cat.replace("Crimes Against ", "")}</span>`;
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

// ---- Navigation ----------------------------------------------------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => switchView(tab.dataset.view));
});

function switchView(view) {
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  document.getElementById(`view-${view}`).classList.remove("hidden");
  if (view === "dashboard") loadDashboard();
  if (view === "incidents") loadIncidents();
}

// ---- Dashboard -----------------------------------------------------------
async function loadDashboard() {
  const s = await api("/api/stats");
  const cards = [
    ["Total Incidents", s.total_incidents],
    ["Open / Active", s.open_incidents],
    ["Offenders", s.total_offenders],
    ["Arrests", s.total_arrests],
  ];
  document.getElementById("stat-cards").innerHTML = cards
    .map(([lbl, num]) => `<div class="card"><div class="num">${num}</div><div class="lbl">${lbl}</div></div>`)
    .join("");
  renderBars("chart-category", s.by_category);
  renderBars("chart-status", s.by_status);
  renderBars("chart-division", s.by_division);
}

function renderBars(elId, obj) {
  const entries = Object.entries(obj);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  document.getElementById(elId).innerHTML = entries
    .map(([k, v]) => `
      <div class="bar-row">
        <div title="${k}">${k}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${(v / max) * 100}%"></div></div>
        <div class="bar-val">${v}</div>
      </div>`)
    .join("");
}

// ---- Incidents list ------------------------------------------------------
async function loadIncidents() {
  const params = new URLSearchParams(state.filters);
  const rows = await api(`/api/incidents?${params.toString()}`);
  const tbody = document.querySelector("#incident-table tbody");
  tbody.innerHTML = rows
    .map((r) => `
      <tr data-id="${r.id}">
        <td>${r.incident_number}</td>
        <td>${r.offense_code} — ${r.offense}</td>
        <td>${categoryPill(r.category)}</td>
        <td><span class="pill status">${r.status}</span></td>
        <td>${r.county}</td>
        <td>${r.division}</td>
        <td>${r.reported_date}</td>
      </tr>`)
    .join("");
  tbody.querySelectorAll("tr").forEach((tr) =>
    tr.addEventListener("click", () => openIncident(tr.dataset.id)));
  document.getElementById("incident-count").textContent = `${rows.length} incident(s)`;
}

function bindFilters() {
  const map = { "f-q": "q", "f-category": "category", "f-status": "status",
                "f-division": "division", "f-county": "county" };
  Object.entries(map).forEach(([id, key]) => {
    const el = document.getElementById(id);
    const evt = el.tagName === "INPUT" ? "input" : "change";
    el.addEventListener(evt, () => {
      const v = el.value.trim();
      if (v) state.filters[key] = v; else delete state.filters[key];
      loadIncidents();
    });
  });
  document.getElementById("f-reset").addEventListener("click", () => {
    state.filters = {};
    ["f-q", "f-category", "f-status", "f-division", "f-county"].forEach(
      (id) => (document.getElementById(id).value = ""));
    loadIncidents();
  });
}

// ---- Incident detail modal ----------------------------------------------
async function openIncident(id) {
  const i = await api(`/api/incidents/${id}`);
  const offenders = i.offenders.length
    ? `<table class="mini"><thead><tr><th>Name</th><th>SID</th><th>Sex</th><th>Race</th><th>Status</th></tr></thead><tbody>${
        i.offenders.map((o) => `<tr><td>${o.first_name} ${o.last_name}</td><td>${o.sid}</td><td>${o.sex}</td><td>${o.race}</td><td>${o.status}</td></tr>`).join("")
      }</tbody></table>`
    : "<p class='count'>No offenders recorded.</p>";
  const arrests = i.arrests.length
    ? `<table class="mini"><thead><tr><th>Date</th><th>Type</th><th>Arresting Agency</th></tr></thead><tbody>${
        i.arrests.map((a) => `<tr><td>${a.arrest_date}</td><td>${a.arrest_type}</td><td>${a.arresting_agency}</td></tr>`).join("")
      }</tbody></table>`
    : "<p class='count'>No arrests recorded.</p>";
  document.getElementById("modal-content").innerHTML = `
    <h2>${i.incident_number}</h2>
    <div>${categoryPill(i.category)} <span class="pill status">${i.status}</span> <span class="pill status">Group ${i.grp}</span></div>
    <dl class="kv">
      <dt>Offense</dt><dd>${i.offense_code} — ${i.offense}</dd>
      <dt>Occurred</dt><dd>${i.occurred_date}</dd>
      <dt>Reported</dt><dd>${i.reported_date}</dd>
      <dt>Location</dt><dd>${i.city}, ${i.county} County</dd>
      <dt>Agency</dt><dd>${i.agency}</dd>
      <dt>Division</dt><dd>${i.division}</dd>
    </dl>
    <p>${i.narrative || ""}</p>
    <div class="subhead">Offenders</div>${offenders}
    <div class="subhead">Arrests</div>${arrests}`;
  document.getElementById("modal").classList.remove("hidden");
}
document.getElementById("modal-close").addEventListener("click", () =>
  document.getElementById("modal").classList.add("hidden"));
document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") e.target.classList.add("hidden");
});

// ---- New incident form ---------------------------------------------------
function populateReference() {
  const ref = state.reference;
  const optize = (arr, val, txt) =>
    arr.map((x) => `<option value="${val(x)}">${txt(x)}</option>`).join("");

  // Filters
  const cats = [...new Set(ref.offenses.map((o) => o.category))];
  document.getElementById("f-category").insertAdjacentHTML("beforeend",
    optize(cats, (c) => c, (c) => c));
  document.getElementById("f-status").insertAdjacentHTML("beforeend",
    optize(ref.statuses, (s) => s, (s) => s));
  document.getElementById("f-division").insertAdjacentHTML("beforeend",
    optize(ref.divisions, (d) => d, (d) => d));
  document.getElementById("f-county").insertAdjacentHTML("beforeend",
    optize(ref.counties, (c) => c.county, (c) => c.county));

  // New-incident form
  document.getElementById("n-offense").innerHTML =
    optize(ref.offenses, (o) => o.code,
      (o) => `${o.code} — ${o.description} (${o.category.replace("Crimes Against ", "")})`);
  document.getElementById("n-status").innerHTML =
    optize(ref.statuses, (s) => s, (s) => s);
  document.getElementById("n-division").innerHTML =
    `<option value="">Select division…</option>` + optize(ref.divisions, (d) => d, (d) => d);
  document.getElementById("n-county").innerHTML =
    `<option value="">Select county…</option>` + optize(ref.counties, (c) => c.county, (c) => c.county);
}

document.getElementById("incident-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form).entries());
  const msg = document.getElementById("form-msg");
  msg.className = "";
  msg.textContent = "Submitting…";
  try {
    const created = await api("/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    msg.className = "ok";
    msg.textContent = `Created ${created.incident_number}`;
    form.reset();
    setDefaultDates();
  } catch (err) {
    msg.className = "err";
    msg.textContent = err.message;
  }
});

function setDefaultDates() {
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("n-reported").value = today;
}

// ---- Boot ----------------------------------------------------------------
(async function init() {
  state.reference = await api("/api/reference");
  populateReference();
  bindFilters();
  setDefaultDates();
  loadDashboard();
})();
