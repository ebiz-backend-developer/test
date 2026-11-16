/* Shared helpers: role switcher, API client, toast. No dependencies. */
const store = {
  get role() { return localStorage.getItem("rr.role") || "principal"; },
  set role(v) { localStorage.setItem("rr.role", v); },
  get user() { return localStorage.getItem("rr.user") || "Ada Principal"; },
  set user(v) { localStorage.setItem("rr.user", v); },
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Role": store.role,
      "X-User": store.user,
      ...(options.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `request failed (${res.status})`);
  return data;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function pill(text) {
  const cls = String(text).toLowerCase().replace(/[^a-z0-9]+/g, "_");
  return `<span class="pill ${cls}">${esc(text)}</span>`;
}

let toastTimer = null;
function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

async function initRolebar() {
  const roleSel = document.getElementById("role-select");
  const userInput = document.getElementById("user-input");
  if (!roleSel) return;
  let roles = [];
  try {
    roles = await api("/api/roles");
  } catch (err) {
    toast("API unreachable: " + err.message, true);
    return;
  }
  roleSel.innerHTML = roles.map((r) =>
    `<option value="${esc(r.code)}">${esc(r.title)} (${esc(r.code)})</option>`).join("");
  roleSel.value = store.role;
  userInput.value = store.user;
  roleSel.addEventListener("change", () => { store.role = roleSel.value; toast("Acting as " + roleSel.value); });
  userInput.addEventListener("change", () => { store.user = userInput.value || "anonymous"; });
  const perms = document.getElementById("role-perms");
  const showPerms = () => {
    const mine = roles.find((r) => r.code === roleSel.value);
    if (perms && mine) perms.textContent = "Can: " + (mine.permissions.join(", ") || "read-only");
  };
  roleSel.addEventListener("change", showPerms);
  showPerms();
}

document.addEventListener("DOMContentLoaded", initRolebar);
