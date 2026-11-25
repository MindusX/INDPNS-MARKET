export function initNav() {
  const closeMenus = () => document.querySelectorAll(".dropdown.open").forEach((d) => { d.classList.remove("open"); d.querySelector("[data-dropdown]")?.setAttribute("aria-expanded", "false"); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { closeMenus(); document.querySelector(".lightbox.open")?.classList.remove("open"); }
    if (e.key === "/" && !document.documentElement.classList.contains("sb-lock") && !/input|textarea|select/i.test(document.activeElement?.tagName || "")) { const s = document.getElementById("nav-q") || document.getElementById("dq"); if (s) { e.preventDefault(); s.focus(); } }
  });
  document.querySelectorAll(".dropdown > [data-dropdown]").forEach((btn) => btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const dd = btn.parentElement, was = dd.classList.contains("open");
    closeMenus();
    if (!was) { dd.classList.add("open"); btn.setAttribute("aria-expanded", "true"); }
  }));
  document.addEventListener("click", (e) => { if (!e.target.closest(".dropdown")) closeMenus(); });
  const nav = document.querySelector(".navbar");
  if (nav) { const f = () => nav.classList.toggle("scrolled", window.scrollY > 4); f(); window.addEventListener("scroll", f, { passive: true }); }
  const dash = document.querySelector(".dash"), tgl = document.querySelector("[data-sidebar-toggle]");
  if (dash && tgl) {
    try { if (localStorage.getItem("indpns-sidebar") === "1") dash.classList.add("collapsed"); } catch (e) {}
    tgl.addEventListener("click", () => { dash.classList.toggle("collapsed"); try { localStorage.setItem("indpns-sidebar", dash.classList.contains("collapsed") ? "1" : "0"); } catch (e) {} });
  }
  document.querySelectorAll("[data-filters-toggle]").forEach((b) => b.addEventListener("click", () => document.getElementById("filters")?.classList.toggle("open")));
  // Pied de page : colonnes repliées par défaut sur mobile (ouvertes sur ordinateur)
  if (matchMedia("(max-width: 720px)").matches) document.querySelectorAll(".fcol[open]").forEach((d) => d.removeAttribute("open"));
}
