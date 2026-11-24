export function toast(msg) {
  let host = document.querySelector(".toast-host");
  if (!host) { host = document.createElement("div"); host.className = "toast-host"; host.setAttribute("role", "status"); document.body.appendChild(host); }
  const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; host.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
export function initFavorites() {
  const csrf = document.querySelector("meta[name=csrf-token]")?.content;
  document.querySelectorAll("[data-fav-url]").forEach((btn) => btn.addEventListener("click", async (e) => {
    e.preventDefault();
    if (btn.dataset.auth !== "1") { window.location = btn.dataset.loginUrl; return; }
    btn.disabled = true;
    try {
      const r = await fetch(btn.dataset.favUrl, { method: "POST", headers: { "X-CSRFToken": csrf, "x-requested-with": "fetch" } });
      if (!r.ok) throw new Error();
      const d = await r.json();
      btn.classList.toggle("active", d.favorite); btn.setAttribute("aria-pressed", String(d.favorite));
      toast(d.favorite ? (btn.dataset.added || "Added to favorites") : (btn.dataset.removed || "Removed from favorites"));
    } catch (err) { toast(btn.dataset.error || "Something went wrong"); }
    btn.disabled = false;
  }));
}
