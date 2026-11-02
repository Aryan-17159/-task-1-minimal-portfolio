let projects = [];
async function load() {
  await sessionReady();
  try {
    projects = await api("/projects");
    $("#projects").innerHTML = projects.length
      ? projects
          .map(
            (p, i) =>
              `<button class="project" data-project="${p.id}"><span class="project-index">${String(i + 1).padStart(2, "0")}</span><div><h3>${esc(p.title)}</h3><p>${esc(p.summary)}</p><span class="technologies">${p.tags.map(esc).join(" · ")}</span></div><span class="arrow">→</span></button>`,
          )
          .join("")
      : '<p class="loading">New work will be added here.</p>';
  } catch (e) {
    $("#projects").innerHTML =
      '<p class="error">Could not load work. Please reload the page.</p>';
  }
}
$("#projects").onclick = (e) => {
  const b = e.target.closest("[data-project]");
  if (!b) return;
  const p = projects.find((p) => p.id === Number(b.dataset.project));
  $("#project-title").textContent = p.title;
  $("#project-detail").textContent = p.detail;
  $("#project-tags").innerHTML = p.tags
    .map((t) => `<span>${esc(t)}</span>`)
    .join("");
  $("#project-dialog").showModal();
};
$("#project-dialog .icon-button").onclick = () => $("#project-dialog").close();
$("#contact-form").onsubmit = async (e) => {
  e.preventDefault();
  const b = e.target.querySelector("button"),
    status = $("#contact-status");
  b.disabled = true;
  status.textContent = "";
  try {
    await api("/contact", "POST", Object.fromEntries(new FormData(e.target)));
    status.className = "success";
    status.textContent = "Thank you. Your message has been received.";
    e.target.reset();
  } catch (e) {
    status.className = "error";
    status.textContent = e.message;
  } finally {
    b.disabled = false;
  }
};
const observer = new IntersectionObserver(
  (entries) =>
    entries.forEach((e) => {
      if (e.isIntersecting) {
        $$("nav a").forEach((a) =>
          a.classList.toggle("active", a.hash === "#" + e.target.id),
        );
      }
    }),
  { rootMargin: "-10% 0px -65% 0px" },
);
$$("main section").forEach((s) => observer.observe(s));
$("#year").textContent = new Date().getFullYear();
$("#local-time").textContent = new Date().toLocaleTimeString("en-GB", {
  timeZone: "Asia/Kolkata",
  hour: "2-digit",
  minute: "2-digit",
});
load().catch(() => toast("Connection unavailable. Please reload."));
