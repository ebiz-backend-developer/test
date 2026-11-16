const $ = (s) => document.querySelector(s);
const key = () => ($('#apiKey').value || localStorage.getItem('apiKey') || '').trim();
const headers = () => ({ 'Content-Type': 'application/json', 'X-API-Key': key() });

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}
const err = (e) => alert('Error: ' + e.message);

async function connect() {
  localStorage.setItem('apiKey', key());
  try {
    const me = await api('/api/v1/me');
    $('#whoami').textContent = `${me.name} (${me.role})`;
    await refreshAll();
  } catch (e) { $('#whoami').textContent = 'invalid key'; err(e); }
}

async function refreshAll() {
  await Promise.allSettled([loadStatus(), loadPayments(), loadTemplates(), loadMessages(), loadAnalytics(), loadReports(), loadPlan()]);
}

async function loadStatus() {
  const s = await api('/api/v1/status');
  $('#statusCards').innerHTML =
    `<div class="card"><b>Payments</b><br>${s.payment_providers.join(', ')}</div>` +
    `<div class="card"><b>Messaging</b><br>${s.notification_gateways.join(', ')}</div>` +
    `<div class="card"><b>Reports</b><br>${s.report_types.join(', ')}</div>`;
}

async function loadPayments() {
  try {
    const { payments } = await api('/api/v1/payments');
    const tb = $('#payTable tbody');
    tb.textContent = '';
    payments.slice(0, 20).forEach((p) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${p.public_id}</td><td>${p.customer_email}</td><td>${p.amount_cents} ${p.currency}</td><td>${p.provider}</td><td>${p.status}</td>`;
      const td = document.createElement('td');
      if (p.status === 'requires_confirmation') {
        const b = document.createElement('button'); b.textContent = 'Confirm';
        b.onclick = async () => { try { await api(`/api/v1/payments/intents/${p.public_id}/confirm`, { method: 'POST' }); await loadPayments(); } catch (e) { err(e); } };
        td.appendChild(b);
      }
      if (p.status === 'succeeded' || p.status === 'partially_refunded') {
        const b = document.createElement('button'); b.textContent = 'Refund';
        b.onclick = async () => {
          const amt = prompt('Refund amount (cents)?', String(p.amount_cents));
          if (!amt) return;
          try { await api(`/api/v1/payments/${p.public_id}/refund`, { method: 'POST', body: JSON.stringify({ amount_cents: +amt, reason: 'dashboard' }) }); await loadPayments(); } catch (e) { err(e); }
        };
        td.appendChild(b);
      }
      tr.appendChild(td); tb.appendChild(tr);
    });
  } catch (e) { /* role may not allow */ }
}

$('#payForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const body = { customer_email: f.get('customer_email'), amount_cents: +f.get('amount_cents'), currency: f.get('currency'), provider: f.get('provider'), payment_method: f.get('payment_method') };
  try {
    const p = await api('/api/v1/payments/intents', { method: 'POST', body: JSON.stringify(body) });
    await api(`/api/v1/payments/intents/${p.public_id}/confirm`, { method: 'POST' });
    await loadPayments();
  } catch (ex) { err(ex); }
});

async function loadTemplates() {
  try {
    const { templates } = await api('/api/v1/notify/templates');
    const sel = $('#msgForm select[name=template_name]');
    sel.innerHTML = '<option value="">(no template)</option>' + templates.map((t) => `<option>${t.name}</option>`).join('');
  } catch (e) { /* role may not allow */ }
}

async function loadMessages() {
  try {
    const { messages } = await api('/api/v1/notify/messages');
    const tb = $('#msgTable tbody'); tb.innerHTML = '';
    messages.slice(0, 20).forEach((m) => {
      tb.innerHTML += `<tr><td>${m.public_id}</td><td>${m.channel}</td><td>${m.recipient}</td><td>${m.template_name}</td><td>${m.status}</td></tr>`;
    });
  } catch (e) { /* role may not allow */ }
}

$('#msgForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const vars = {};
  (f.get('body') || '').split(',').forEach((kv) => { const i = kv.indexOf('='); if (i > 0) vars[kv.slice(0, i).trim()] = kv.slice(i + 1).trim(); });
  const hasVars = Object.keys(vars).length > 0;
  const body = { channel: f.get('channel'), recipient: f.get('recipient'), template_name: f.get('template_name') || null, body: hasVars ? '' : f.get('body'), variables: vars };
  try { await api('/api/v1/notify/send', { method: 'POST', body: JSON.stringify(body) }); await loadMessages(); }
  catch (ex) { err(ex); }
});

$('#evtForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try { await api('/api/v1/analytics/events', { method: 'POST', body: JSON.stringify({ name: f.get('name'), user_ref: f.get('user_ref') }) }); await loadAnalytics(); }
  catch (ex) { err(ex); }
});
async function loadAnalytics() {
  try { $('#analyticsOut').textContent = JSON.stringify(await api('/api/v1/analytics/summary'), null, 2); }
  catch (e) { $('#analyticsOut').textContent = 'not authorized for this role'; }
}
$('#refreshAnalytics').onclick = loadAnalytics;

$('#rptForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try { await api('/api/v1/reports/run', { method: 'POST', body: JSON.stringify({ report_type: f.get('report_type'), format: f.get('format'), params: {} }) }); await loadReports(); }
  catch (ex) { err(ex); }
});
async function loadReports() {
  try {
    const { runs } = await api('/api/v1/reports');
    const tb = $('#rptTable tbody'); tb.innerHTML = '';
    runs.slice(0, 20).forEach((r) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.public_id}</td><td>${r.report_type}</td><td>${r.format}</td><td>${r.row_count}</td><td>${r.created_at}</td>`;
      const td = document.createElement('td');
      const a = document.createElement('a'); a.textContent = 'download'; a.href = `/api/v1/reports/${r.public_id}/download?api_key=${encodeURIComponent(key())}`;
      a.onclick = async (ev) => {
        ev.preventDefault();
        const res = await fetch(`/api/v1/reports/${r.public_id}/download`, { headers: { 'X-API-Key': key() } });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const l = document.createElement('a'); l.href = url; l.download = `${r.public_id}.${r.format}`; l.click();
        URL.revokeObjectURL(url);
      };
      td.appendChild(a); tr.appendChild(td); tb.appendChild(tr);
    });
  } catch (e) { /* role may not allow */ }
}
$('#refreshReports').onclick = loadReports;

async function loadPlan() {
  try {
    const { modules } = await api('/api/v1/planning/modules?mvp_only=true');
    $('#modTable tbody').innerHTML = modules.map((m) => `<tr><td>${m.name}</td><td>${m.priority}</td><td>${m.status}</td></tr>`).join('');
    const { milestones } = await api('/api/v1/planning/milestones');
    const tb = $('#msTable tbody'); tb.innerHTML = '';
    milestones.forEach((m) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${m.id}</td><td>${m.title}</td><td>${m.status}</td>`;
      const td = document.createElement('td');
      if (m.status === 'proposed') {
        const b = document.createElement('button'); b.textContent = 'Approve';
        b.onclick = async () => { try { await api(`/api/v1/planning/milestones/${m.id}/approve`, { method: 'POST' }); await loadPlan(); } catch (e) { err(e); } };
        td.appendChild(b);
      } else if (m.status === 'approved') {
        const b = document.createElement('button'); b.textContent = 'Complete';
        b.onclick = async () => { try { await api(`/api/v1/planning/milestones/${m.id}/complete`, { method: 'POST' }); await loadPlan(); } catch (e) { err(e); } };
        td.appendChild(b);
      }
      tr.appendChild(td); tb.appendChild(tr);
    });
  } catch (e) { /* needs auth */ }
}

$('#rolePreset').onchange = (e) => { if (e.target.value) { $('#apiKey').value = e.target.value; connect(); } };
$('#connectBtn').onclick = connect;
$('#apiKey').value = localStorage.getItem('apiKey') || '';
if ($('#apiKey').value) connect(); else loadStatus().catch(() => {});
