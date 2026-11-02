const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let csrf = "",
  currentUser = null;
async function api(path, method = "GET", body) {
  const r = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const d = await r.json();
  if (!r.ok) throw Error(d.error || "Something went wrong. Please try again.");
  if (d.csrf) csrf = d.csrf;
  if (Object.hasOwn(d, "user")) currentUser = d.user;
  return d;
}
async function sessionReady() {
  return api("/session");
}
function toast(s) {
  let el = $(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("role", "status");
    document.body.append(el);
  }
  el.textContent = s;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 3500);
}
function authDialog(after = () => location.reload()) {
  let d = $("#auth-dialog");
  if (!d) {
    d = document.createElement("dialog");
    d.id = "auth-dialog";
    document.body.append(d);
  }
  let register = false;
  function paint() {
    d.innerHTML = `<div class="dialog-head"><h2>${register ? "Create an account" : "Welcome back"}</h2><button class="icon-button" aria-label="Close">×</button></div><form id="auth-form">${register ? '<label>Name<input name="name" required maxlength="80" autocomplete="name"></label>' : ""}<label>Email<input name="email" type="email" required autocomplete="email"></label><label>Password<input name="password" type="password" required minlength="${register ? 8 : 1}" maxlength="128" autocomplete="${register ? "new-password" : "current-password"}"></label><p class="error" role="alert"></p><button type="submit" class="button primary" style="width:100%">${register ? "Create account" : "Sign in"}</button></form><button id="auth-switch" class="text-button" style="margin-top:18px">${register ? "Already have an account? Sign in" : "New here? Create an account"}</button>`;
    d.querySelector(".icon-button").onclick = () => d.close();
    $("#auth-switch").onclick = () => {
      register = !register;
      paint();
    };
    $("#auth-form").onsubmit = async (e) => {
      e.preventDefault();
      const b = e.target.querySelector("[type=submit]");
      b.disabled = true;
      try {
        await api(
          register ? "/register" : "/login",
          "POST",
          Object.fromEntries(new FormData(e.target)),
        );
        d.close();
        after();
      } catch (err) {
        e.target.querySelector(".error").textContent = err.message;
      } finally {
        b.disabled = false;
      }
    };
  }
  paint();
  d.showModal();
}
function dateLabel(s) {
  if (!s) return "No date";
  return new Date(s.slice(0, 10) + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}
