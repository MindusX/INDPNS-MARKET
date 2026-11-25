// Barre latérale PUBLIQUE (templates/components/public_sidebar.html) — pages sans connexion + authentification.
// Ouverture : [data-psb-open] · Fermeture : [data-psb-close], Échap, clic sur un lien interne.
// Accessibilité : focus déplacé dans le panneau puis rendu au bouton, piège à Tab, inert quand fermé, aria-expanded,
// défilement de la page bloqué. Le tableau de bord n'inclut pas ce composant : ce module n'y fait rien.
// Aucune donnée sensible : le composant ne fait qu'afficher des liens déjà rendus par le serveur.
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

export function initPublicSidebar() {
  const root = document.getElementById("public-sidebar");
  if (!root) return;
  const html = document.documentElement;
  const openers = () => document.querySelectorAll("[data-psb-open]");
  let lastFocus = null;

  const isOpen = () => root.classList.contains("is-open");
  const setExpanded = (v) => openers().forEach((b) => b.setAttribute("aria-expanded", String(v)));
  const focusables = () => [...root.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null || el === document.activeElement);

  root.setAttribute("inert", "");

  function open(trigger) {
    if (isOpen()) return;
    lastFocus = trigger || document.activeElement;
    const gap = window.innerWidth - html.clientWidth;
    html.style.setProperty("--psb-scrollbar", gap > 0 ? gap + "px" : "0px");
    html.classList.add("psb-lock");
    root.removeAttribute("inert");
    root.classList.add("is-open");
    setExpanded(true);
    requestAnimationFrame(() => (root.querySelector(".psb-close") || root).focus({ preventScroll: true }));
  }

  function close({ restore = true } = {}) {
    if (!isOpen()) return;
    root.classList.remove("is-open");
    html.classList.remove("psb-lock");
    html.style.removeProperty("--psb-scrollbar");
    root.setAttribute("inert", "");
    setExpanded(false);
    if (restore && lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
    lastFocus = null;
  }

  document.addEventListener("click", (e) => {
    const o = e.target.closest("[data-psb-open]");
    if (o) { e.preventDefault(); isOpen() ? close() : open(o); return; }
    if (e.target.closest("[data-psb-close]")) { close(); return; }
    // Lien interne vers une ancre de la page courante : on referme pour laisser voir le contenu.
    const a = isOpen() && e.target.closest("#public-sidebar a[href]");
    if (a && a.pathname === location.pathname && a.hash) close({ restore: false });
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
