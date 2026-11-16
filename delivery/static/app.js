/* Delivery dashboard: read-only views plus role-gated actions. */
const state = { role: localStorage.getItem("delivery-role") || "stakeholder" };

function headers() {
  return { "Content-Type": "application/json", "X-Role": state.role };
}

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `request failed (${res.status})`);
  return data;
}

function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = isError ? "error" : "";
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 4000);
}

function tag(text) {
  return `<span class="tag ${text}">${text}</span>`;
}

async function loadRoles() {
  const { roles } = await api("/api/roles");
  const sel = document.getElementById("role");
  sel.innerHTML = roles.map((r) => `<option value="${r.name}">${r.name}</option>`).join("");
  sel.value = state.role;
  sel.onchange = () => {
    state.role = sel.value;
    localStorage.setItem("delivery-role", state.role);
    refresh();
  };
  document.querySelector("#roles tbody").innerHTML = roles
    .map((r) => `<tr><td><strong>${r.name}</strong></td><td>${r.description}</td></tr>`).join("");
}

async function loadScope() {
  const { scope } = await api("/api/scope");
  if (!scope) return;
  document.getElementById("vision").textContent = scope.vision;
  for (const [id, items] of [["in-scope", scope.in_scope], ["out-scope", scope.out_of_scope],
      ["assumptions", scope.assumptions], ["constraints", scope.constraints]]) {
    document.getElementById(id).innerHTML = items.map((i) => `<li>${i}</li>`).join("");
  }
}

async function loadModules() {
  const readiness = await api("/api/mvp");
  const pct = readiness.percent;
  document.querySelector("#mvp-bar div").style.width = `${pct}%`;
  document.getElementById("mvp-text").textContent =
    `${readiness.done_points}/${readiness.total_points} MVP points done (${pct}%) across ${readiness.total_modules} modules.`;
  const { modules } = await api("/api/modules");
  const next = { backlog: "planned", planned: "in_progress", in_progress: "done", done: "in_progress" };
  document.querySelector("#modules tbody").innerHTML = modules.map((m) => `<tr>
    <td><strong>${m.name}</strong><br><small>${m.description}</small></td>
    <td>${tag(m.priority)}</td><td>${m.mvp ? "yes" : "no"}</td><td>${m.effort_points}</td>
    <td>${tag(m.status)}</td><td>${m.depends_on.join(", ") || "—"}</td>
    <td><button class="action" data-advance="${m.id}" data-to="${next[m.status]}">→ ${next[m.status]}</button></td>
  </tr>`).join("");
  document.querySelectorAll("[data-advance]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await api(`/api/modules/${btn.dataset.advance}`, {
          method: "PATCH", body: JSON.stringify({ status: btn.dataset.to }),
        });
        toast("Module updated");
        loadModules();
      } catch (e) { toast(e.message, true); }
    };
  });
  const { order } = await api("/api/build-order");
  document.getElementById("build-order").innerHTML = order.map((n) => `<li>${n}</li>`).join("");
}

async function loadArch() {
  const summary = await api("/api/stack");
  document.getElementById("stack-state").textContent = summary.decided
    ? "Stack decided: every category has a selected option."
    : `Pending categories: ${summary.pending_categories.join(", ")}`;
  document.querySelector("#stack tbody").innerHTML = Object.entries(summary.stack)
    .map(([cat, d]) => `<tr><td><strong>${cat}</strong></td><td>${d.option_name}</td><td>${d.rationale}</td></tr>`).join("");
  const { decisions } = await api("/api/architecture");
  document.querySelector("#arch tbody").innerHTML = decisions.map((d) => `<tr>
    <td>${d.category}</td><td>${d.option_name}</td><td>${tag(d.status)}</td>
    <td>${d.status === "proposed" ? `<button class="action" data-select="${d.id}">select</button>` : ""}</td>
  </tr>`).join("");
  document.querySelectorAll("[data-select]").forEach((btn) => {
    btn.onclick = async () => {
      const rationale = prompt("Rationale for selecting this option:");
      if (!rationale) return;
      try {
        await api(`/api/architecture/${btn.dataset.select}/select`, {
          method: "POST", body: JSON.stringify({ rationale }),
        });
        toast("Option selected");
        loadArch();
      } catch (e) { toast(e.message, true); }
    };
  });
}

async function loadTimeline() {
  const { phases } = await api("/api/timeline");
  document.getElementById("timeline").innerHTML = phases.map((p) => `
    <div class="phase"><h3>${p.phase} (${p.approved}/${p.count} approved)</h3>
    <ul>${p.milestones.map((m) => `<li><strong>${m.name}</strong> ${tag(m.status)}
      <small>${m.start_date} → ${m.end_date} · owner: ${m.owner_role}</small><br>${m.description}</li>`).join("") || "<li>No milestones yet</li>"}</ul>
    </div>`).join("");
}

async function loadRisks() {
  const { risks } = await api("/api/risks");
  const { milestones } = await api("/api/milestones");
  const names = Object.fromEntries(milestones.map((m) => [m.id, m.name]));
  document.querySelector("#risks tbody").innerHTML = risks.map((r) => `<tr>
    <td>${r.title}</td><td>${r.likelihood}</td><td>${r.impact}</td>
    <td><strong>${r.exposure}</strong></td><td>${tag(r.status)}</td>
    <td>${r.milestone_id ? names[r.milestone_id] || r.milestone_id : "—"}</td>
    <td>${r.mitigation || "—"}</td></tr>`).join("");
}

async function loadApprovals() {
  const { milestones } = await api("/api/milestones");
  const rows = [];
  for (const m of milestones) {
    const health = await api(`/api/milestones/${m.id}/health`);
    const { criteria } = await api(`/api/milestones/${m.id}/criteria`);
    rows.push(`<tr><td><strong>${m.name}</strong></td><td>${m.phase}</td><td>${tag(m.status)}</td>
      <td>${tag(health.health)}</td><td>${health.criteria_met}/${health.criteria_total} met</td>
      <td><button class="action" data-review="${m.id}">review</button></td></tr>`);
    m._criteria = criteria;
    m._health = health;
  }
  document.querySelector("#approvals tbody").innerHTML = rows.join("");
  const byId = Object.fromEntries(milestones.map((m) => [m.id, m]));
  document.querySelectorAll("[data-review]").forEach((btn) => {
    btn.onclick = () => showReview(byId[btn.dataset.review]);
  });
}

function showReview(m) {
  const detail = document.getElementById("approval-detail");
  detail.innerHTML = `<h3>${m.name}</h3>
    <p>Health: ${tag(m._health.health)} · open high risks: ${m._health.open_high_risks}</p>
    <ul>${m._criteria.map((c) => `<li>${tag(c.status)} ${c.description}
      <small>(${c.verification_method || "no verification method"})</small>
      ${c.status === "pending" ? `<button class="action" data-met="${c.id}">mark met</button>` : ""}</li>`).join("")}</ul>
    <p><button class="action" id="approve">approve</button>
    <button class="action" id="request-changes">request changes</button>
    <button class="action" id="reject">reject</button></p>`;
  detail.querySelectorAll("[data-met]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await api(`/api/criteria/${btn.dataset.met}`, { method: "PATCH", body: JSON.stringify({ status: "met" }) });
        toast("Criterion met");
        refresh();
      } catch (e) { toast(e.message, true); }
    };
  });
  const decide = async (decision) => {
    let comment = "";
    if (decision !== "approved") {
      comment = prompt("Comment (required):") || "";
      if (!comment) return;
    }
    try {
      const { approval } = await api(`/api/milestones/${m.id}/approvals`, {
        method: "POST", body: JSON.stringify({ decision, comment }),
      });
      toast(`Milestone ${approval.milestone_status}`);
      refresh();
    } catch (e) { toast(e.message, true); }
  };
  detail.querySelector("#approve").onclick = () => decide("approved");
  detail.querySelector("#request-changes").onclick = () => decide("changes_requested");
  detail.querySelector("#reject").onclick = () => decide("rejected");
}

async function refresh() {
  try {
    const { ok } = await api("/api/health");
    const pill = document.getElementById("health");
    pill.textContent = ok ? `API ok · ${state.role}` : "API error";
    pill.className = ok ? "pill" : "pill bad";
  } catch {
    const pill = document.getElementById("health");
    pill.textContent = "API unreachable";
    pill.className = "pill bad";
    return;
  }
  await Promise.all([loadScope(), loadModules(), loadArch(), loadTimeline(), loadRisks()]);
  await loadRoles();
  await loadApprovals();
}

document.querySelectorAll("#tabs button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  };
});

refresh();
