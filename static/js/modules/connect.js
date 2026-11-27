// Moyens de paiement + vérification d'identité : confirmations, aperçu des photos de documents, contrôles côté navigateur.
// Le serveur revalide TOUT (apps/sellers/kyc_forms.py + kyc_images.py) : ce module n'est qu'une aide à l'utilisateur.
const MAX_BYTES = 10 * 1024 * 1024;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

function initConfirm() {
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-confirm]");
    if (b && !window.confirm(b.dataset.confirm)) { e.preventDefault(); e.stopImmediatePropagation(); }
  }, true);
}

function initKycForm(form) {
  const docType = form.querySelector('[name="doc_type"]');
  const backWrap = form.querySelector("[data-kyc-back]");
  const submit = form.querySelector("[data-kyc-submit]");
  const urls = {};

  const setError = (kind, msg) => {
    const el = form.querySelector(`[data-kyc-error="${kind}"]`);
    if (el) { el.textContent = msg || ""; el.hidden = !msg; }
  };
  const reset = (kind, input) => {
    input.value = "";
    const zone = form.querySelector(`[data-kyc-zone="${kind}"]`);
    if (!zone) return;
    zone.classList.remove("has-file");
    const img = zone.querySelector(".cx-thumb");
    if (img) { img.hidden = true; img.removeAttribute("src"); }
    if (urls[kind]) { URL.revokeObjectURL(urls[kind]); delete urls[kind]; }
  };

  form.querySelectorAll("[data-kyc-file]").forEach((input) => {
    const kind = input.dataset.kycFile;
    input.addEventListener("change", () => {
      setError(kind, "");
      const f = input.files && input.files[0];
      if (!f) { reset(kind, input); return; }
      if (!TYPES.includes(f.type)) { reset(kind, input); setError(kind, form.dataset.msgType); return; }
      if (f.size > MAX_BYTES) { reset(kind, input); setError(kind, form.dataset.msgSize); return; }
      const zone = form.querySelector(`[data-kyc-zone="${kind}"]`), img = zone && zone.querySelector(".cx-thumb");
      if (urls[kind]) URL.revokeObjectURL(urls[kind]);
      urls[kind] = URL.createObjectURL(f);
      if (img) { img.src = urls[kind]; img.hidden = false; }
      if (zone) zone.classList.add("has-file");
    });
  });

  // Passeport : pas de verso.
  const toggleBack = () => {
    if (!docType || !backWrap) return;
    const passport = docType.value === "passport";
    backWrap.hidden = passport;
    if (passport) { const inp = backWrap.querySelector("input[type=file]"); if (inp) reset("back", inp); setError("back", ""); }
  };
  if (docType) { docType.addEventListener("change", toggleBack); toggleBack(); }

  form.addEventListener("submit", (e) => {
    if (form.dataset.sending) { e.preventDefault(); return; }          // anti double envoi
    form.dataset.sending = "1";
    if (submit) { submit.disabled = true; submit.textContent = submit.dataset.sending || form.dataset.sending || "…"; }
  });
}

export function initConnect() {
  initConfirm();
  const form = document.querySelector("[data-kyc-form]");
  if (form) {
    const label = form.getAttribute("data-sending") || "";
    form.removeAttribute("data-sending");                              // sert de libellé : on le recopie sur le bouton
    const submit = form.querySelector("[data-kyc-submit]");
    if (submit) submit.dataset.sending = label;
    initKycForm(form);
  }
}
