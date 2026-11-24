let deferred = null;
export function initPWA() {
  if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("/service-worker.js").catch(() => {}));
  const btns = document.querySelectorAll("[data-pwa-install]");
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; btns.forEach((b) => (b.hidden = false)); });
  btns.forEach((b) => b.addEventListener("click", async () => { if (!deferred) return; deferred.prompt(); await deferred.userChoice; deferred = null; btns.forEach((x) => (x.hidden = true)); }));
}
