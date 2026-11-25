// Menu plein écran (templates/components/full_menu.html) — pages publiques et d'authentification.
// Ouverture : [data-sidebar-open] (le bouton menu de la barre horizontale) · Fermeture : [data-fullmenu-close], Échap, clic sur un lien.
// Accessibilité : focus déplacé dans le menu puis rendu au bouton, piège à Tab, inert quand fermé, aria-expanded, défilement de la page bloqué.
// Sur le tableau de bord, #full-menu n'existe pas : ce module ne fait rien et sidebar.js garde la main.
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

export function initFullMenu() {
  const root = document.getElementById("full-menu");
  if (!root) return;
  const html = document.documentElement;
  const openers = () => document.querySelectorAll("[data-sidebar-open]");
  let lastFocus = null;

  const isOpen = () => root.classList.contains("is-open");
  const setExpanded = (v) => openers().forEach((b) => b.setAttribute("aria-expanded", String(v)));
  const focusables = () => [...root.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null || el === document.activeElement);

  openers().forEach((b) => b.setAttribute("aria-controls", "full-menu"));
  root.setAttribute("inert", "");

  function open(trigger) {
    if (isOpen()) return;
    lastFocus = trigger || document.activeElement;
    const gap = window.innerWidth - html.clientWidth;
    html.style.setProperty("--fm-scrollbar", gap > 0 ? gap + "px" : "0px");
    html.classList.add("fm-lock");
    root.removeAttribute("inert");
    root.classList.add("is-open");
    setExpanded(true);
    requestAnimationFrame(() => (root.querySelector(".fm-close") || root).focus({ preventScroll: true }));
  }

  function close({ restore = true } = {}) {
    if (!isOpen()) return;
    root.classList.remove("is-open");
    html.classList.remove("fm-lock");
    html.style.removeProperty("--fm-scrollbar");
    root.setAttribute("inert", "");
    setExpanded(false);
    if (restore && lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
    lastFocus = null;
  }

  document.addEventListener("click", (e) => {
    const o = e.target.closest("[data-sidebar-open]");
    if (o) { e.preventDefault(); isOpen() ? close() : open(o); return; }
    if (e.target.closest("[data-fullmenu-close]")) { close(); return; }
    const a = isOpen() && e.target.closest("#full-menu a[href]");
    if (a) close({ restore: false });
  });

  document.addEventListener("keydown", (e) => {
    if (!isOpen()) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); return; }
    if (e.key !== "Tab") return;
    const items = focusables();
    if (!items.length) { e.preventDefault(); root.focus(); return; }
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === root)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }, true);

  // Page restaurée depuis le cache (bouton « retour ») : on repart d'un état fermé.
  window.addEventListener("pageshow", (e) => { if (e.persisted) close({ restore: false }); });
}
