/* School MVP UI: one screen per core module + overview. No build step. */
const $ = (s) => document.querySelector(s);
const roleSel = $("#role"), view = $("#view"), errBox = $("#error");
const TABS = [
  ["overview", "Overview"], ["admissions", "Admissions"], ["attendance", "Attendance"],
  ["grades", "Grades"], ["timetable", "Timetable"], ["fees", "Fees"],
  ["comms", "Communication"], ["milestones", "Milestones"],
];
let active = "overview";

function role() { return roleSel.value; }
function showErr(msg) {
  errBox.hidden = !msg; errBox.textContent = msg || "";
}
async function api(method, path, body) {
  const res = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json", "X-Role": role() },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
  return data;
}
const esc = (v) => String(v ?? "").replace(/[&<>"]/g,
  (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
function table(cols, rows, render) {
  return "<table><tr>" + cols.map((c) => `<th>${esc(c)}</th>`).join("") + "</tr>" +
    rows.map(render).join("") + "</table>";
}
function field(name, label, val = "", type = "text") {
  return `<label class="f">${esc(label)}<input name="${name}" type="${type}" value="${esc(val)}"></label>`;
}
function wireForm(id, fn) {
  $(id).addEventListener("submit", async (e) => {
    e.preventDefault(); showErr("");
    const data = Object.fromEntries(new FormData(e.target).entries());
    try { await fn(data); await render(); }
    catch (e2) { showErr(e2.message); }
  });
}

/* ---------------- overview: scope, roles, modules, stack ---------------- */
async function vOverview() {
  const [scope, mods, stack] = await Promise.all([
    api("GET", "/scope"), api("GET", "/modules"), api("GET", "/stack")]);
  const mvp = mods.modules.filter((m) => m.mvp);
  view.innerHTML = `
    <div class="card"><h2>${esc(scope.scope.product)}</h2>
      <p><b>In scope (MVP):</b> ${scope.scope.in_scope.map(esc).join(" · ")}</p>
      <p><b>Out of scope:</b> ${scope.scope.out_of_scope.map(esc).join(" · ")}</p></div>
    <div class="card"><h2>Core modules (${mvp.length} in MVP)</h2>
      ${table(["Module", "Priority", "MVP slice"],
        mods.modules,
        (m) => `<tr><td><b>${esc(m.name)}</b><br><span class="badge">${esc(m.summary)}</span></td>` +
          `<td><span class="pill ${m.priority.toLowerCase()}">${m.priority}</span>${m.mvp ? '<span class="pill">MVP</span>' : ""}</td>` +
          `<td>${m.mvp_features.map(esc).join("<br>")}</td></tr>`)}</div>
    <div class="card"><h2>User roles</h2>
      <div class="grid">${Object.entries(scope.roles).map(([r, d]) =>
        `<div class="card"><b>${esc(r)}</b><br><span class="badge">${esc(d.description)}</span>` +
        `<br>${d.permissions.map((p) => `<span class="pill">${esc(p)}</span>`).join(" ")}</div>`).join("")}</div></div>
    <div class="card"><h2>Tech stack</h2>
      ${Object.entries(stack.stack).map(([k, v]) => `<p><b>${esc(k)}:</b> ${esc(v)}</p>`).join("")}</div>`;
}

/* ---------------- admissions ---------------- */
async function vAdmissions() {
  const apps = await api("GET", "/applications");
  view.innerHTML = `
    <div class="card"><h2>New application</h2>
      <form id="fApply" class="inline">
        ${field("student_name", "Student name")}${field("guardian_name", "Guardian")}
        ${field("grade_applying", "Grade", "JSS1")}
        <button class="go">Submit</button></form></div>
    <div class="card"><h2>Applications (${apps.length})</h2>
      ${table(["ID", "Student", "Grade", "Status", "Decision"],
        apps,
        (a) => `<tr><td>${a.id}</td><td>${esc(a.student_name)}<br><span class="badge">${esc(a.guardian_name)}</span></td>` +
          `<td>${esc(a.grade_applying)}</td><td><span class="pill ${esc(a.status)}">${esc(a.status)}</span></td>` +
          `<td><select data-dec="${a.id}">
            <option>under_review</option><option>admitted</option>
            <option>waitlisted</option><option>rejected</option></select>
            <button class="go" data-act="${a.id}">Decide</button></td></tr>`)}</div>`;
  wireForm("#fApply", (d) => api("POST", "/applications", d));
  view.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", async () => {
    showErr("");
    const sel = view.querySelector(`[data-dec="${b.dataset.act}"]`);
    try { await api("POST", `/applications/${b.dataset.act}/decide`, { decision: sel.value }); await render(); }
    catch (e) { showErr(e.message); }
  }));
}

/* ---------------- attendance ---------------- */
async function vAttendance() {
  const today = new Date().toISOString().slice(0, 10);
  const students = await api("GET", "/students");
  let roster = [];
  try { roster = await api("GET", `/attendance?class_date=${today}`); } catch (e) { /* empty db */ }
  view.innerHTML = `
    <div class="card"><h2>Add student</h2>
      <form id="fStu" class="inline">${field("full_name", "Full name")}${field("class_name", "Class", "JSS1")}
      <button class="go">Add</button></form></div>
    <div class="card"><h2>Mark attendance — ${today}</h2>
      ${table(["Student", "Class", "Status", "Mark"],
        roster.length ? roster : students.map((s) => ({ ...s, student_id: s.id, status: "—" })),
        (r) => `<tr><td>${esc(r.full_name)}</td><td>${esc(r.class_name)}</td>` +
          `<td><span class="pill ${esc(r.status)}">${esc(r.status || "—")}</span></td><td>` +
          ["present", "absent", "late", "excused"].map((s) =>
            `<button class="go" data-stu="${r.student_id ?? r.id}" data-st="${s}">${s}</button>`).join(" ") +
          `</td></tr>`)}</div>
    <div class="card"><h2>Summary</h2>
      <form id="fSum" class="inline">${field("student_id", "Student ID", "", "number")}
      <button class="go">Show</button></form><div id="sumOut"></div></div>`;
  wireForm("#fStu", (d) => api("POST", "/students", d));
  view.querySelectorAll("[data-stu]").forEach((b) => b.addEventListener("click", async () => {
    showErr("");
    try { await api("POST", "/attendance", { student_id: +b.dataset.stu, class_date: today, status: b.dataset.st }); await render(); }
    catch (e) { showErr(e.message); }
  }));
  wireForm("#fSum", async (d) => {
    const s = await api("GET", `/attendance?student_id=${d.student_id}`);
    $("#sumOut").innerHTML = `<p>Rate: <b>${(s.attendance_rate * 100).toFixed(1)}%</b> ` +
      Object.entries(s.counts).map(([k, v]) => `<span class="pill ${k}">${k}: ${v}</span>`).join(" ") + "</p>";
  });
}

/* ---------------- grades ---------------- */
async function vGrades() {
  const list = await api("GET", "/assessments");
  view.innerHTML = `
    <div class="card"><h2>New assessment</h2>
      <form id="fAss" class="inline">${field("title", "Title")}${field("subject", "Subject", "Mathematics")}
      ${field("max_score", "Max score", "100", "number")}<button class="go">Create</button></form></div>
    <div class="card"><h2>Record score</h2>
      <form id="fScore" class="inline">${field("assessment_id", "Assessment ID", "", "number")}
      ${field("student_name", "Student")}${field("score", "Score", "", "number")}
      <button class="go">Record</button></form></div>
    <div class="card"><h2>Assessments</h2>
      ${table(["ID", "Title", "Subject", "Max"],
        list, (a) => `<tr><td>${a.id}</td><td>${esc(a.title)}</td><td>${esc(a.subject)}</td><td>${a.max_score}</td></tr>`)}</div>
    <div class="card"><h2>Student average</h2>
      <form id="fAvg" class="inline">${field("student_name", "Student")}<button class="go">Show</button></form>
      <div id="avgOut"></div></div>`;
  wireForm("#fAss", (d) => api("POST", "/assessments", { ...d, max_score: +d.max_score }));
  wireForm("#fScore", (d) => api("POST", "/scores", { ...d, assessment_id: +d.assessment_id, score: +d.score }));
  wireForm("#fAvg", async (d) => {
    const a = await api("GET", `/scores?student_name=${encodeURIComponent(d.student_name)}`);
    const sc = await Promise.all(list.map((x) => api("GET", `/scores?assessment_id=${x.id}`).catch(() => [])));
    $("#avgOut").innerHTML = `<p><b>${esc(a.student_name)}</b>: ${a.average_pct}% across ${a.assessments} assessment(s)</p>`;
  });
}

/* ---------------- timetable ---------------- */
async function vTimetable() {
  const slots = await api("GET", "/slots");
  view.innerHTML = `
    <div class="card"><h2>New slot</h2>
      <form id="fSlot" class="inline">
        <label class="f">Weekday<select name="weekday">${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => `<option>${d}</option>`).join("")}</select></label>
        ${field("starts_at", "Starts", "08:00", "time")}${field("ends_at", "Ends", "09:00", "time")}
        ${field("class_name", "Class", "JSS1")}${field("subject", "Subject", "English")}
        ${field("teacher", "Teacher", "Ms Bello")}${field("room", "Room", "R1")}
        <button class="go">Add</button></form>
      <p class="badge">Room/teacher/class clashes are rejected automatically.</p></div>
    <div class="card"><h2>Weekly timetable (${slots.length} slots)</h2>
      ${table(["Day", "Time", "Class", "Subject", "Teacher", "Room", ""],
        slots, (s) => `<tr><td>${s.weekday}</td><td>${esc(s.starts_at)}–${esc(s.ends_at)}</td>` +
          `<td>${esc(s.class_name)}</td><td>${esc(s.subject)}</td><td>${esc(s.teacher)}</td>` +
          `<td>${esc(s.room)}</td><td><button class="go" data-del="${s.id}">Delete</button></td></tr>`)}</div>`;
  wireForm("#fSlot", (d) => api("POST", "/slots", d));
  view.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    showErr("");
    try { await api("DELETE", `/slots/${b.dataset.del}`); await render(); }
    catch (e) { showErr(e.message); }
  }));
}

/* ---------------- fees ---------------- */
async function vFees() {
  const invoices = await api("GET", "/invoices");
  view.innerHTML = `
    <div class="card"><h2>Issue invoice</h2>
      <form id="fInv" class="inline">${field("student_name", "Student")}${field("term", "Term", "2026-T1")}
      ${field("amount", "Amount", "", "number")}<button class="go">Issue</button></form></div>
    <div class="card"><h2>Record payment</h2>
      <form id="fPay" class="inline">${field("invoice_id", "Invoice ID", "", "number")}
      ${field("amount", "Amount", "", "number")}
      <label class="f">Method<select name="method"><option>cash</option><option>transfer</option><option>card</option></select></label>
      <button class="go">Record</button></form></div>
    <div class="card"><h2>Invoices</h2>
      ${table(["ID", "Student", "Term", "Billed", "Paid", "Balance", "Status"],
        invoices, (i) => `<tr><td>${i.id}</td><td>${esc(i.student_name)}</td><td>${esc(i.term)}</td>` +
          `<td>${i.amount}</td><td>${i.paid}</td><td>${i.balance}</td>` +
          `<td><span class="pill ${i.status}">${i.status}</span></td></tr>`)}</div>
    <div class="card"><h2>Student balance</h2>
      <form id="fBal" class="inline">${field("student_name", "Student")}<button class="go">Show</button></form>
      <div id="balOut"></div></div>`;
  wireForm("#fInv", (d) => api("POST", "/invoices", { ...d, amount: +d.amount }));
  wireForm("#fPay", (d) => api("POST", "/payments", { ...d, invoice_id: +d.invoice_id, amount: +d.amount }));
  wireForm("#fBal", async (d) => {
    const b = await api("GET", `/balance?student_name=${encodeURIComponent(d.student_name)}`);
    $("#balOut").innerHTML = `<p><b>${esc(b.student_name)}</b>: billed ${b.billed}, paid ${b.paid}, ` +
      `balance <b>${b.balance}</b> (${b.invoices} invoice(s))</p>`;
  });
}

/* ---------------- communication ---------------- */
async function vComms() {
  const msgs = await api("GET", "/messages");
  view.innerHTML = `
    <div class="card"><h2>Send message</h2>
      <form id="fMsg" class="inline">${field("sender", "Sender", role())}
      <label class="f">Audience<select name="audience"><option>all</option><option>teachers</option>
      <option>students</option><option>parents</option></select></label>
      ${field("subject", "Subject")}${field("body", "Body")}
      <button class="go">Send</button></form></div>
    <div class="card"><h2>Inbox (${msgs.length})</h2>
      ${table(["From", "Audience", "Subject", "Body"],
        msgs, (m) => `<tr><td>${esc(m.sender)}<br><span class="badge">${esc(m.sender_role)} · ${esc(m.created_at)}</span></td>` +
          `<td>${esc(m.audience)}</td><td><b>${esc(m.subject)}</b></td><td>${esc(m.body)}</td></tr>`)}</div>`;
  wireForm("#fMsg", (d) => api("POST", "/messages", d));
}

/* ---------------- milestones ---------------- */
async function vMilestones() {
  const { milestones } = await api("GET", "/milestones");
  view.innerHTML = `<div class="card"><h2>Delivery milestones</h2>
    <p class="badge">Flow: planned → approved → in_progress → done. Approval needs the admin role.</p>
    ${table(["ID", "Name", "Modules", "Status", "Action"],
      milestones,
      (m) => `<tr><td>${m.id}</td><td><b>${esc(m.name)}</b><br><span class="badge">${esc(m.acceptance)}</span></td>` +
        `<td>${m.modules.map((x) => `<span class="pill">${esc(x)}</span>`).join(" ")}</td>` +
        `<td><span class="pill ${m.status}">${m.status}</span></td>` +
        `<td>${m.status === "planned" ? `<button class="go" data-ap="${m.id}">Approve</button>` : ""}` +
        `${m.status === "approved" ? `<button class="go" data-ad="${m.id}" data-to="in_progress">Start</button>` : ""}` +
        `${m.status === "in_progress" ? `<button class="go" data-ad="${m.id}" data-to="done">Finish</button>` : ""}</td></tr>`)}</div>`;
  view.querySelectorAll("[data-ap]").forEach((b) => b.addEventListener("click", async () => {
    showErr("");
    try { await api("POST", `/milestones/${b.dataset.ap}/approve`); await render(); }
    catch (e) { showErr(e.message); }
  }));
  view.querySelectorAll("[data-ad]").forEach((b) => b.addEventListener("click", async () => {
    showErr("");
    try { await api("POST", `/milestones/${b.dataset.ad}/status`, { status: b.dataset.to }); await render(); }
    catch (e) { showErr(e.message); }
  }));
}

const VIEWS = { overview: vOverview, admissions: vAdmissions, attendance: vAttendance,
  grades: vGrades, timetable: vTimetable, fees: vFees, comms: vComms, milestones: vMilestones };

async function render() {
  showErr("");
  try { await VIEWS[active](); }
  catch (e) { showErr(e.message); }
}
async function refreshPerms() {
  try {
    const s = await api("GET", "/scope");
    $("#perms").textContent = "permissions: " + (s.roles[role()]?.permissions.join(", ") || "—");
  } catch (e) { $("#perms").textContent = ""; }
}

$("#tabs").innerHTML = TABS.map(([id, label]) =>
  `<button data-tab="${id}" class="${id === active ? "active" : ""}">${label}</button>`).join("");
document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
  active = b.dataset.tab;
  document.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("active", x === b));
  render();
}));
roleSel.addEventListener("change", async () => { await refreshPerms(); await render(); });
refreshPerms(); render();
