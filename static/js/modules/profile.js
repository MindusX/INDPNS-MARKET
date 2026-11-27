// Profil avancé — mêmes mécanismes que Mindus Forge :
//   • photo : recadrage (zoom / glisser / pincement) → JPEG 800 px → envoi AJAX, affichage IMMÉDIAT (aperçu local puis URL versionnée) ;
//   • couverture : réduction côté navigateur (2400 px), envoi AJAX, REPOSITIONNEMENT vertical par glisser-déposer ;
//   • suppression avec confirmation, synchronisation entre onglets (BroadcastChannel), bouton « Partager ».
// Le serveur revalide TOUT (apps/accounts/images.py + profile_api.py) : ce module n'est qu'une aide à l'utilisateur.
import { toast } from "./favorites.js";

const $ = (id) => document.getElementById(id);
let T = {};                       // textes traduits (json_script « pf-i18n »)
let form = null;                  // <form data-pf> de la page d'édition
let state = { hasAvatar: false, hasCover: false, pos: 50, repos: null };
let bc = null;

/* ---------------------------- utilitaires ---------------------------- */
function csrf() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  if (el) return el.value;
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

async function api(method, url, body) {
  const headers = { "X-CSRFToken": csrf(), Accept: "application/json" };
  const opts = { method, headers, credentials: "same-origin" };
  if (body instanceof FormData) opts.body = body;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  try {
    const r = await fetch(url, opts);
    let data = {};
    try { data = await r.json(); } catch (e) { /* réponse non JSON (429, 500…) */ }
    return { success: r.ok && data.success !== false, status: r.status, ...data };
  } catch (e) {
    return { success: false, status: 0, error: T.uploadFailed };
  }
}

const preload = (url, cb) => { const i = new Image(); i.onload = i.onerror = () => cb(); i.src = url; };
const endpoint = (name) => form.dataset[name];

function bcPost(msg) { try { if (bc) bc.postMessage(msg); } catch (e) { /* ignore */ } }

/* Met à jour TOUS les avatars de la page (barre du haut, menu latéral, éditeur…). */
function setAvatarEverywhere(url) {
  document.querySelectorAll("[data-avatar-slot]").forEach((slot) => {
    let img = slot.querySelector("img[data-avatar-img]");
    if (!url) { if (img) img.remove(); return; }
    if (!img) {
      img = document.createElement("img");
      img.setAttribute("data-avatar-img", ""); img.alt = "";
      img.style.cssText = "position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:inherit";
      if (getComputedStyle(slot).position === "static") slot.style.position = "relative";
      slot.appendChild(img);
    }
    img.src = url;
  });
}

function syncButtons() {
  form.querySelectorAll('[data-pf-need="avatar"]').forEach((b) => { b.hidden = !state.hasAvatar; });
  form.querySelectorAll('[data-pf-need="cover"]').forEach((b) => { b.hidden = !state.hasCover; });
  const label = form.querySelector("[data-pf-cover-label]");
  if (label) label.textContent = state.hasCover ? T.changeCover : T.addCover;
}

/* ---------------------------- PHOTO : recadrage + envoi ---------------------------- */
function openCrop(file) {
  if (!file) return;
  if (!/^image\//.test(file.type)) { toast(T.invalidImage); return; }
  const url = URL.createObjectURL(file), img = new Image();
  img.onerror = () => { URL.revokeObjectURL(url); toast(T.invalidImage); };
  img.onload = () => {
    const nw = img.naturalWidth, nh = img.naturalHeight;
    if (!nw || !nh) { URL.revokeObjectURL(url); toast(T.invalidImage); return; }

    const bg = document.createElement("div");
    bg.className = "pf-modal-bg";
    bg.innerHTML = '<div class="pf-modal" role="dialog" aria-modal="true"><h3 class="pf-modal-title"></h3>' +
      '<div class="pf-crop"><img alt=""></div>' +
      '<div class="pf-zoom"><span aria-hidden="true">−</span><input type="range" min="1" max="4" step="0.01" value="1"><span aria-hidden="true">+</span></div>' +
      '<div class="pf-modal-foot"><button type="button" class="btn" data-x="cancel"></button><button type="button" class="btn btn-primary" data-x="save"></button></div></div>';
    bg.querySelector(".pf-modal-title").textContent = T.cropTitle;
    bg.querySelector("[data-x=cancel]").textContent = T.cancel;
    bg.querySelector("[data-x=save]").textContent = T.savePhoto;
    document.body.appendChild(bg);
    document.documentElement.classList.add("pf-modal-open");

    const box = bg.querySelector(".pf-crop"), pic = box.querySelector("img"), zoom = bg.querySelector("input[type=range]");
    zoom.setAttribute("aria-label", T.zoom);
    pic.src = url; pic.style.width = nw + "px"; pic.style.height = nh + "px";
    const V = box.clientWidth, base = V / Math.min(nw, nh);
    let z = 1, tx = (V - nw * base) / 2, ty = (V - nh * base) / 2;
    const paint = () => {
      const s = base * z;
      tx = Math.min(0, Math.max(V - nw * s, tx)); ty = Math.min(0, Math.max(V - nh * s, ty));
      pic.style.transform = `translate(${tx}px,${ty}px) scale(${s})`;
    };
    const setZoom = (nz) => {
      nz = Math.max(1, Math.min(4, nz));
      const s0 = base * z, cx = (V / 2 - tx) / s0, cy = (V / 2 - ty) / s0;
      z = nz; const s1 = base * z; tx = V / 2 - cx * s1; ty = V / 2 - cy * s1; zoom.value = z; paint();
    };
    paint();
    zoom.addEventListener("input", () => setZoom(parseFloat(zoom.value)));
    box.addEventListener("wheel", (e) => { e.preventDefault(); setZoom(z * (e.deltaY < 0 ? 1.08 : 0.93)); }, { passive: false });
    const pts = {}; let dist0 = 0, z0 = 1;
    box.addEventListener("pointerdown", (e) => {
      try { box.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ }
      pts[e.pointerId] = { x: e.clientX, y: e.clientY };
      const ids = Object.keys(pts);
      if (ids.length === 2) { const a = pts[ids[0]], b = pts[ids[1]]; dist0 = Math.hypot(a.x - b.x, a.y - b.y); z0 = z; }
    });
    box.addEventListener("pointermove", (e) => {
      const p = pts[e.pointerId]; if (!p) return;
      const ids = Object.keys(pts);
      if (ids.length === 1) { tx += e.clientX - p.x; ty += e.clientY - p.y; p.x = e.clientX; p.y = e.clientY; paint(); }
      else if (ids.length === 2) {
        p.x = e.clientX; p.y = e.clientY;
        const a = pts[ids[0]], b = pts[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (dist0 > 0) setZoom(z0 * d / dist0);
      }
    });
    const endPtr = (e) => { delete pts[e.pointerId]; };
    box.addEventListener("pointerup", endPtr); box.addEventListener("pointercancel", endPtr);

    const close = () => { bg.remove(); URL.revokeObjectURL(url); document.documentElement.classList.remove("pf-modal-open"); document.removeEventListener("keydown", onKey); };
    const onKey = (e) => { if (e.key === "Escape") close(); };
    document.addEventListener("keydown", onKey);
    bg.addEventListener("click", (e) => { if (e.target === bg) close(); });
    bg.querySelector("[data-x=cancel]").addEventListener("click", close);
    bg.querySelector("[data-x=save]").addEventListener("click", () => {
      const s = base * z, out = document.createElement("canvas"); out.width = out.height = 800;
      const ctx = out.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, 800, 800);
      ctx.drawImage(img, -tx / s, -ty / s, V / s, V / s, 0, 0, 800, 800);
      out.toBlob((blob) => { close(); if (blob) uploadAvatar(blob); }, "image/jpeg", 0.92);
    });
    bg.querySelector("[data-x=save]").focus();
  };
  img.src = url;
}

async function uploadAvatar(blob) {
  const box = $("pf-avatar-box"), local = URL.createObjectURL(blob);
  const prev = box && box.querySelector("img[data-avatar-img]") ? box.querySelector("img[data-avatar-img]").getAttribute("src") : "";
  setAvatarEverywhere(local);                                   // 1) AFFICHAGE IMMÉDIAT (aperçu local)
  if (box) box.classList.add("pf-uploading");
  const fd = new FormData(); fd.append("file", blob, "avatar.jpg");
  const res = await api("POST", endpoint("apiAvatarUpload"), fd);
  if (box) box.classList.remove("pf-uploading");
  if (!res.success) {
    setAvatarEverywhere(prev); URL.revokeObjectURL(local);
    toast(res.error || T.uploadFailed); return;
  }
  state.hasAvatar = true; syncButtons();
  preload(res.url, () => { setAvatarEverywhere(res.url); URL.revokeObjectURL(local); });   // 2) URL versionnée du serveur
  bcPost({ type: "avatar", url: res.url });
  toast(T.photoUpdated);
}

async function removeAvatar() {
  if (!window.confirm(T.confirmRemoveAvatar)) return;
  const res = await api("DELETE", endpoint("apiAvatarDelete"));
  if (!res.success) { toast(res.error || T.error); return; }
  state.hasAvatar = false; syncButtons(); setAvatarEverywhere("");
  bcPost({ type: "avatar", url: "" }); toast(T.photoRemoved);
}

/* ---------------------------- COUVERTURE : aperçu, envoi, repositionnement ---------------------------- */
function downscale(file, maxW) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file), img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const w = img.naturalWidth, h = img.naturalHeight;
      if (!w || !h || (w <= maxW && file.size < 1500000 && /^image\/(jpeg|webp)$/.test(file.type))) return resolve(file);
      const sc = Math.min(1, maxW / w), c = document.createElement("canvas");
      c.width = Math.round(w * sc); c.height = Math.round(h * sc);
      const ctx = c.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height); ctx.drawImage(img, 0, 0, c.width, c.height);
      c.toBlob((b) => resolve(b || file), "image/jpeg", 0.9);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

async function startCover(file) {
  if (!file) return;
  if (!/^image\//.test(file.type)) { toast(T.invalidImage); return; }
  const cover = $("pf-cover"); let img = $("pf-cover-img");
  const local = URL.createObjectURL(file), prevSrc = img ? img.getAttribute("src") : null, prevPos = img ? img.style.objectPosition : "", created = !img;
  if (!img) {
    img = document.createElement("img"); img.className = "pf-cover-img"; img.id = "pf-cover-img"; img.alt = ""; img.draggable = false;
    cover.insertBefore(img, cover.firstChild);
  }
  img.style.objectPosition = "50% 50%"; img.src = local;           // AFFICHAGE IMMÉDIAT
  cover.classList.add("pf-uploading");
  const revert = (msg) => {
    cover.classList.remove("pf-uploading"); URL.revokeObjectURL(local);
    if (created) img.remove(); else { img.src = prevSrc; img.style.objectPosition = prevPos; }
    toast(msg || T.uploadFailed);
  };
  const blob = await downscale(file, 2400);
  const fd = new FormData(); fd.append("file", blob, "cover.jpg");
  const res = await api("POST", endpoint("apiCoverUpload"), fd);
  if (!res.success) { revert(res.error); return; }
  cover.classList.remove("pf-uploading");
  state.hasCover = true; state.pos = 50; syncButtons();
  preload(res.url, () => { img.src = res.url; URL.revokeObjectURL(local); });
  bcPost({ type: "cover", url: res.url });
  toast(T.coverUpdated);
}

function startRepos() {
  const cover = $("pf-cover"), img = $("pf-cover-img");
  if (!img || state.repos) return;
  const overflow = cover.clientWidth * (img.naturalHeight / img.naturalWidth) - cover.clientHeight;
  if (!(overflow > 2)) { toast(T.noReposition); return; }
  const orig = state.pos == null ? 50 : state.pos;
  let pos = orig, startY = 0, startPos = 0, dragging = false;
  cover.classList.add("repos");
  const bar = document.createElement("div"); bar.className = "pf-repos-bar";
  bar.innerHTML = '<span class="pf-repos-hint"></span><span class="pf-repos-btns"><button type="button" class="btn btn-sm" data-x="cancel"></button><button type="button" class="btn btn-sm btn-primary" data-x="save"></button></span>';
  bar.querySelector(".pf-repos-hint").textContent = T.dragHint;
  bar.querySelector("[data-x=cancel]").textContent = T.cancel;
  bar.querySelector("[data-x=save]").textContent = T.save;
  cover.appendChild(bar);
  const down = (e) => { dragging = true; startY = e.clientY; startPos = pos; cover.classList.add("drag"); try { img.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ } e.preventDefault(); };
  const move = (e) => { if (!dragging) return; pos = Math.max(0, Math.min(100, startPos - ((e.clientY - startY) / overflow) * 100)); img.style.objectPosition = "50% " + pos + "%"; };
  const up = () => { dragging = false; cover.classList.remove("drag"); };
  img.addEventListener("pointerdown", down); img.addEventListener("pointermove", move);
  img.addEventListener("pointerup", up); img.addEventListener("pointercancel", up);
  const stop = (finalPos) => {
    img.removeEventListener("pointerdown", down); img.removeEventListener("pointermove", move);
    img.removeEventListener("pointerup", up); img.removeEventListener("pointercancel", up);
    cover.classList.remove("repos", "drag"); bar.remove(); img.style.objectPosition = "50% " + finalPos + "%"; state.repos = null;
  };
  state.repos = { stop, orig };
  bar.querySelector("[data-x=cancel]").addEventListener("click", () => stop(orig));
  bar.querySelector("[data-x=save]").addEventListener("click", async (e) => {
    const v = Math.round(pos); e.currentTarget.disabled = true;
    const res = await api("PUT", endpoint("apiCoverPosition"), { position_y: v });
    if (res.success) { state.pos = v; stop(v); toast(T.positionSaved); }
    else { e.currentTarget.disabled = false; toast(res.error || T.error); }
  });
}

async function removeCover() {
  if (!window.confirm(T.confirmRemoveCover)) return;
  const res = await api("DELETE", endpoint("apiCoverDelete"));
  if (!res.success) { toast(res.error || T.error); return; }
  const img = $("pf-cover-img"); if (img) img.remove();
  state.hasCover = false; state.pos = 50; syncButtons();
  bcPost({ type: "cover", url: "" }); toast(T.coverRemoved);
}

function initMedia() {
  state.hasAvatar = form.dataset.hasAvatar === "1";
  state.hasCover = form.dataset.hasCover === "1";
  state.pos = Number(form.dataset.coverPos || 50);
  const pick = (id, handler) => {
    const input = $(id);
    input.addEventListener("change", () => { const f = input.files && input.files[0]; input.value = ""; handler(f); });
    return input;
  };
  const avatarInput = pick("pf-file-avatar", openCrop), coverInput = pick("pf-file-cover", startCover);
  const actions = {
    "avatar-pick": () => avatarInput.click(), "cover-pick": () => coverInput.click(),
    "avatar-remove": removeAvatar, "cover-remove": removeCover, "cover-repos": startRepos,
  };
  form.addEventListener("click", (e) => {
    const b = e.target.closest("[data-pf-act]");
    if (b && actions[b.dataset.pfAct]) { e.preventDefault(); actions[b.dataset.pfAct](); }
  });
  // Si l'image enregistrée est introuvable : on affiche l'initiale / le dégradé plutôt que l'icône « image cassée ».
  const cov = $("pf-cover-img");
  if (cov) cov.addEventListener("error", () => { cov.remove(); state.hasCover = false; syncButtons(); });
  const av = form.querySelector("#pf-avatar-box img[data-avatar-img]");
  if (av) av.addEventListener("error", () => { av.remove(); });
  syncButtons();
}

/* ---------------------------- texte, partage, synchronisation d'onglets ---------------------------- */
function initText() {
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
  try { if ("BroadcastChannel" in window) bc = new BroadcastChannel("indpns-profile"); } catch (e) { bc = null; }
  if (bc) bc.onmessage = (e) => {                               // un autre onglet a changé la photo : on met à jour celui-ci
    const d = e.data || {};
    if (d.type === "avatar") setAvatarEverywhere(d.url);
    else if (d.type === "cover") { const c = $("pf-cover-img"); if (c && d.url) c.src = d.url; }
  };
  initShare();
  form = document.querySelector("[data-pf]");
  if (!form) return;
  try { T = JSON.parse(($("pf-i18n") || {}).textContent || "{}"); } catch (e) { T = {}; }
  initMedia(); initText();
}
