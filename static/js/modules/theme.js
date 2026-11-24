export function initTheme() {
  const root = document.documentElement;
  const btns = document.querySelectorAll("[data-theme-toggle]");
  const csrf = document.querySelector("meta[name=csrf-token]")?.content;
  const sync = () => btns.forEach((b) => b.setAttribute("aria-pressed", String(root.getAttribute("data-theme") === "dark")));
  const apply = (t) => { root.setAttribute("data-theme", t); try { localStorage.setItem("indpns-theme", t); } catch (e) {} sync(); };
  btns.forEach((b) => b.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    apply(next);
    if (b.dataset.saveUrl && csrf) fetch(b.dataset.saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" }, body: "theme=" + next }).catch(() => {});
  }));
  sync();
}
