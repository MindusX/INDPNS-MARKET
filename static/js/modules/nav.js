export function initNav() {
  const drawer = document.getElementById("drawer");
  const open = () => { drawer?.classList.add("open"); document.body.style.overflow = "hidden"; };
  const close = () => { drawer?.classList.remove("open"); document.body.style.overflow = ""; };
  document.querySelectorAll("[data-drawer-open]").forEach((b) => b.addEventListener("click", open));
  document.querySelectorAll("[data-drawer-close]").forEach((b) => b.addEventListener("click", close));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { close(); document.querySelectorAll(".dropdown.open").forEach((d) => d.classList.remove("open")); } });
  document.querySelectorAll(".dropdown > [data-dropdown]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const dd = btn.parentElement;
      const was = dd.classList.contains("open");
      document.querySelectorAll(".dropdown.open").forEach((d) => d.classList.remove("open"));
      if (!was) dd.classList.add("open");
      btn.setAttribute("aria-expanded", String(!was));
    });
  });
  document.addEventListener("click", () => document.querySelectorAll(".dropdown.open").forEach((d) => d.classList.remove("open")));
  // Sidebar rétractable (dashboard)
  const dash = document.querySelector(".dash");
  const tgl = document.querySelector("[data-sidebar-toggle]");
  if (dash && tgl) {
    try { if (localStorage.getItem("indpns-sidebar") === "1") dash.classList.add("collapsed"); } catch (e) {}
    tgl.addEventListener("click", () => {
      dash.classList.toggle("collapsed");
      try { localStorage.setItem("indpns-sidebar", dash.classList.contains("collapsed") ? "1" : "0"); } catch (e) {}
    });
  }
}
