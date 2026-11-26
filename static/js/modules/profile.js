// Profil avancé : aperçu instantané des images, compteur de biographie, identifiant en direct, bouton « Partager ».
// Le serveur revalide TOUT (voir apps/accounts/forms.py + images.py) : ce module n'est qu'une aide à l'utilisateur.
import { toast } from "./favorites.js";

const MAX_BYTES = 5 * 1024 * 1024;
const TYPES = ["image/jpeg", "image/png", "image/webp"];
const t = (el, key, fallback) => (el && el.dataset[key]) || fallback;

function initImages(form) {
  form.querySelectorAll("[data-pf-file]").forEach((input) => {
    const kind = input.dataset.pfFile;
    const box = form.querySelector(`[data-pf-box="${kind}"]`);
    const img = box && box.querySelector("[data-pf-img]");
    const err = form.querySelector(`[data-pf-error="${kind}"]`);
    const remove = form.querySelector(`[data-pf-remove="${kind}"]`);
    let blobUrl = null;
    const showError = (msg) => { if (!err) return; err.textContent = msg || ""; err.hidden = !msg; };

    input.addEventListener("change", () => {
      showError("");
      const f = input.files && input.files[0];
      if (!f) return;
      if (!TYPES.includes(f.type)) { input.value = ""; return showError(t(form, "msgType", "Images must be JPG, PNG or WebP.")); }
      if (f.size > MAX_BYTES) { input.value = ""; return showError(t(form, "msgSize", "Image too large (max 5 MB).")); }
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      blobUrl = URL.createObjectURL(f);
      if (img) img.src = blobUrl;
      box.classList.add("has-image");
      if (remove) remove.checked = false;            // un nouveau fichier annule « Supprimer »
    });

    if (remove) remove.addEventListener("change", () => {
      if (remove.checked) { input.value = ""; showError(""); box.classList.remove("has-image"); }
      else if (img && (img.dataset.orig || blobUrl)) { img.src = img.dataset.orig || blobUrl; box.classList.add("has-image"); }
    });
  });
}

function initText(form) {
  const username = form.querySelector("[data-pf-username]");
  const sanitize = (v) => v.toLowerCase().replace(/^@/, "").replace(/[^a-z0-9_-]/g, "");
  if (username) username.addEventListener("input", () => {
    const before = username.value, pos = username.selectionStart == null ? before.length : username.selectionStart;
    const clean = sanitize(before);
    if (clean === before) return;
    username.value = clean;
    const caret = sanitize(before.slice(0, pos)).length;          // le curseur reste derrière le dernier caractère valide saisi
    try { username.setSelectionRange(caret, caret); } catch (e) { /* champ non sélectionnable */ }
  });

  const bio = form.querySelector("[data-pf-bio]"), count = form.querySelector("[data-pf-count]");
  if (bio && count) {
    const max = Number(bio.getAttribute("maxlength")) || 600;
    const upd = () => {
      const n = bio.value.length;
      count.textContent = `${n} / ${max}`;
      count.classList.toggle("is-near", n >= max * 0.9 && n < max);
      count.classList.toggle("is-max", n >= max);
    };
    bio.addEventListener("input", upd); upd();
  }
}

function initShare() {
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-share]");
    if (!b) return;
    const data = { title: b.dataset.title || document.title, text: b.dataset.text || "", url: b.dataset.url || location.href };
    if (navigator.share) {
      try { await navigator.share(data); } catch (err) { /* partage annulé par l'utilisateur */ }
      return;
    }
    try { await navigator.clipboard.writeText(data.url); toast(b.dataset.done || "Link copied"); } catch (err) { toast("Copy failed"); }
  });
}

export function initProfile() {
  const form = document.querySelector("[data-pf]");
  if (form) { initImages(form); initText(form); }
  initShare();
}
