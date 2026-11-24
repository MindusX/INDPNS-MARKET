import { toast } from "./favorites.js";

export function initUI() {
  // Apparition progressive (respecte prefers-reduced-motion)
  const els = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px" });
    els.forEach((el) => io.observe(el));
  } else els.forEach((el) => el.classList.add("in"));

  // Barre de progression de navigation
  const bar = document.createElement("div"); bar.className = "nav-progress"; document.body.appendChild(bar);
  const start = () => { bar.style.opacity = "1"; bar.style.width = "70%"; };
  document.addEventListener("indpns:navigate", start);
  document.addEventListener("click", (e) => { const a = e.target.closest("a[href]"); if (a && a.origin === location.origin && !a.target && !e.metaKey && !e.ctrlKey && !a.hash && !a.hasAttribute("download")) start(); });
  window.addEventListener("pageshow", () => { bar.style.width = "0"; bar.style.opacity = "0"; });

  // Boutons de formulaire : état de chargement
  document.querySelectorAll("form").forEach((f) => f.addEventListener("submit", () => {
    const b = f.querySelector("button[type=submit].btn-primary, button[type=submit][data-loading]");
    if (b && f.checkValidity()) setTimeout(() => b.classList.add("is-loading"), 0);
  }));
  window.addEventListener("pageshow", () => document.querySelectorAll(".is-loading").forEach((b) => b.classList.remove("is-loading")));

  // Messages fermables
  document.querySelectorAll(".message").forEach((m) => {
    const x = document.createElement("button"); x.type = "button"; x.setAttribute("aria-label", "Dismiss"); x.textContent = "×"; x.addEventListener("click", () => m.remove()); m.appendChild(x);
    if (m.classList.contains("success")) setTimeout(() => m.remove(), 6000);
  });

  // Mot de passe : afficher/masquer + jauge de robustesse
  document.querySelectorAll("input[type=password]").forEach((inp) => {
    const wrap = document.createElement("div"); wrap.className = "pw-field"; inp.parentNode.insertBefore(wrap, inp); wrap.appendChild(inp);
    const b = document.createElement("button"); b.type = "button"; b.className = "pw-toggle"; b.setAttribute("aria-label", "Show password");
    b.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
    b.addEventListener("click", () => { const show = inp.type === "password"; inp.type = show ? "text" : "password"; b.setAttribute("aria-label", show ? "Hide password" : "Show password"); });
    wrap.appendChild(b);
    if (/password1|new_password1/.test(inp.name)) {
      const m = document.createElement("div"); m.className = "pw-meter"; m.innerHTML = "<span></span>"; wrap.after(m);
      inp.addEventListener("input", () => {
        const v = inp.value; let s = 0;
        if (v.length >= 10) s++; if (v.length >= 14) s++; if (/[a-z]/.test(v) && /[A-Z]/.test(v)) s++; if (/\d/.test(v)) s++; if (/[^A-Za-z0-9]/.test(v)) s++;
        const bar = m.firstChild; bar.style.width = (v ? Math.max(12, s * 20) : 0) + "%"; bar.style.background = s < 2 ? "var(--color-danger)" : s < 4 ? "var(--color-warning)" : "var(--color-success)";
      });
    }
  });

  // Copier le lien
  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy || location.href); toast(b.dataset.done || "Link copied"); } catch (e) { toast("Copy failed"); }
  }));

  // Onglets de la page produit : scroll-spy
  const tabs = [...document.querySelectorAll(".tabs a[href^='#']")];
  if (tabs.length && "IntersectionObserver" in window) {
    const map = new Map(tabs.map((t) => [t.getAttribute("href").slice(1), t]));
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { tabs.forEach((t) => t.classList.remove("active")); map.get(e.target.id)?.classList.add("active"); } }), { rootMargin: "-30% 0px -60% 0px" });
    map.forEach((_t, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
  }

  // Statut du site (footer) + retour en haut
  const st = document.querySelector("[data-status]");
  if (st) fetch("/healthz", { cache: "no-store" }).then((r) => { st.dataset.state = r.ok ? "ok" : "error"; st.querySelector(".stext").textContent = r.ok ? st.dataset.ok : st.dataset.err; }).catch(() => { st.dataset.state = "error"; st.querySelector(".stext").textContent = st.dataset.err; });
  document.querySelector("[data-totop]")?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  document.querySelectorAll("[data-year]").forEach((y) => (y.textContent = new Date().getFullYear()));
}
