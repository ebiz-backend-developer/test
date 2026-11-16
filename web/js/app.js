/* Shared helpers for SchoolMS Task 3 pages. */
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fillList(id, items) {
  document.getElementById(id).innerHTML =
    (items || []).map(x => `<li>${esc(x)}</li>`).join('');
}

async function loadList(url, unused, cb) {
  const res = await fetch(url);
  cb(await res.json());
}
