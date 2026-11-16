/* Shared Design Hub client: auth header, nav, role switcher, helpers. */
(function () {
  "use strict";

  var NAV = [
    ["dashboard.html", "Dashboard"],
    ["scope.html", "Scope & Roles"],
    ["modules.html", "Modules & MVP"],
    ["tech.html", "Tech Stack"],
    ["milestones.html", "Milestones"],
    ["flows.html", "UX Flows"],
    ["wireframes.html", "Wireframes"]
  ];

  function currentUser() {
    return localStorage.getItem("hub.user") || "priya";
  }

  function api(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    opts.headers["X-User"] = currentUser();
    if (opts.body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(path, opts).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.error) || ("HTTP " + res.status));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function notice(el, msg, kind) {
    el.className = "notice " + (kind || "");
    el.textContent = msg;
    el.hidden = false;
  }

  function mountChrome(active) {
    var top = document.querySelector(".topbar");
    if (top && !top.querySelector(".rolebox select")) {
      var box = document.createElement("div");
      box.className = "rolebox";
      box.innerHTML = '<label for="roleuser">Acting as</label><select id="roleuser"></select>';
      top.appendChild(box);
      var sel = box.querySelector("select");
      api("/api/users").then(function (users) {
        users.forEach(function (u) {
          var opt = document.createElement("option");
          opt.value = u.username;
          opt.textContent = u.display_name + " (" + u.role + ")";
          sel.appendChild(opt);
        });
        sel.value = currentUser();
        sel.addEventListener("change", function () {
          try {
            localStorage.setItem("hub.user", sel.value);
          } catch (e) {
            notice(document.getElementById("savewarn") || document.body,
              "Could not save role choice: browser storage failed.", "error");
            return;
          }
          location.reload();
        });
      }).catch(function () { /* users list is optional chrome */ });
    }
    document.querySelectorAll("[data-nav]").forEach(function (nav) {
      nav.innerHTML = "";
      NAV.forEach(function (item) {
        var a = document.createElement("a");
        a.href = item[0];
        a.textContent = item[1];
        if (active === item[0]) a.className = "active";
        nav.appendChild(a);
      });
    });
  }

  function badge(text, cls) {
    return '<span class="badge ' + (cls || "") + '">' + esc(text) + "</span>";
  }

  window.Hub = {
    api: api, esc: esc, notice: notice, mountChrome: mountChrome,
    badge: badge, currentUser: currentUser
  };
})();
