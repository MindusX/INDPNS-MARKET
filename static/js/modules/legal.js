// Pages juridiques : sommaire « Sur cette page » généré à partir des <h2 id> de l'article + repère de section active.
export function initLegal() {
  const article = document.querySelector(".legal-article");
  const host = document.querySelector("[data-legal-toc]");
  if (!article || !host) return;
  const heads = [...article.querySelectorAll("h2[id], h3[id]")];
  if (heads.filter((h) => h.tagName === "H2").length < 3) { host.closest(".legal-toc")?.remove(); return; }
  if (matchMedia("(max-width: 960px)").matches) host.removeAttribute("open");
  const list = host.querySelector("ol") || host.appendChild(document.createElement("ol"));
  const links = new Map();
  heads.forEach((h) => {
    const li = document.createElement("li"); li.className = h.tagName.toLowerCase(); const a = document.createElement("a");
    a.href = "#" + h.id; a.textContent = h.textContent.trim();
    li.appendChild(a); list.appendChild(li); links.set(h.id, a);
  });
  if (!("IntersectionObserver" in window)) return;
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting) return;
    links.forEach((a) => a.removeAttribute("aria-current"));
    links.get(e.target.id)?.setAttribute("aria-current", "true");
  }), { rootMargin: "-20% 0px -70% 0px" });
  heads.forEach((h) => io.observe(h));
}
