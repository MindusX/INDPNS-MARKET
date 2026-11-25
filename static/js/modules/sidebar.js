// Barre latérale centrale (templates/components/sidebar.html).
// Ouverture : [data-sidebar-open] · Fermeture : [data-sidebar-close], clic sur l'arrière-plan, touche Échap.
// Accessibilité : focus déplacé dans le panneau puis rendu au bouton, piège à Tab, inert quand fermé, aria-expanded,
// défilement de l'arrière-plan bloqué. Aucune donnée sensible : le composant ne fait qu'afficher des liens déjà rendus par le serveur.
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

export function initSidebar() {
  const root = document.getElementById("app-sidebar");
  if (!root) return;
  const panel = root.querySelector(".sb-panel");
  const openers = () => document.querySelectorAll("[data-sidebar-open]");
  const root_el = document.documentElement;
  let lastFocus = null;

  const isOpen = () => root.classList.contains("is-open");
  const setExpanded = (v) => openers().forEach((b) => b.setAttribute("aria-expanded", String(v)));
  const visibleFocusables = () => [...panel.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null || el === document.activeElement);

  // Fermé par défaut : le panneau n'est ni atteignable au clavier ni lu par les lecteurs d'écran.
  panel.setAttribute("inert", "");
  panel.setAttribute("aria-hidden", "true");

  function open(trigger) {
    if (isOpen()) return;
    lastFocus = trigger || document.activeElement;
    const gap = window.innerWidth - root_el.clientWidth;
    root_el.style.setProperty("--sb-scrollbar", gap > 0 ? gap + "px" : "0px");
    root_el.classList.add("sb-lock");
    panel.removeAttribute("inert"); panel.removeAttribute("aria-hidden");
    root.classList.add("is-open");
    setExpanded(true);
    // Focus après le démarrage de la transition (visibility passe à visible immédiatement).
    requestAnimationFrame(() => (panel.querySelector(".sb-close") || panel).focus({ preventScroll: true }));
  }

  function close({ restore = true } = {}) {
    if (!isOpen()) return;
    root.classList.remove("is-open");
    root_el.classList.remove("sb-lock");
    root_el.style.removeProperty("--sb-scrollbar");
    panel.setAttribute("inert", ""); panel.setAttribute("aria-hidden", "true");
    setExpanded(false);
    if (restore && lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
    lastFocus = null;
  }

  document.addEventListener("click", (e) => {
    const o = e.target.closest("[data-sidebar-open]");
    if (o) { e.preventDefault(); isOpen() ? close() : open(o); return; }
    if (e.target.closest("[data-sidebar-close]")) { close(); return; }
    // Lien interne vers une ancre de la page courante : on referme pour laisser voir le contenu.
    const a = isOpen() && e.target.closest(".sb-panel a[href]");
    if (a && a.pathname === location.pathname && a.hash) close({ restore: false });
  });

  document.addEventListener("keydown", (e) => {
    if (!isOpen()) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); return; }
    if (e.key !== "Tab") return;
    const items = visibleFocusables();
    if (!items.length) { e.preventDefault(); panel.focus(); return; }
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }, true);

  // Si la fenêtre est redimensionnée ou la page restaurée depuis le cache (bouton « retour »), on repart d'un état fermé.
  window.addEventListener("pageshow", (e) => { if (e.persisted) close({ restore: false }); });
}
