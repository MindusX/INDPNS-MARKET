let deferred = null;
export function initPWA() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/service-worker.js").catch(() => {}));
  }
  const btn = document.querySelector("[data-pwa-install]");
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; if (btn) btn.hidden = false; });
  btn?.addEventListener("click", async () => { if (!deferred) return; deferred.prompt(); await deferred.userChoice; deferred = null; btn.hidden = true; });
}
