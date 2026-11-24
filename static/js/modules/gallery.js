export function initGallery() {
  const main = document.querySelector("[data-gallery-main]");
  if (!main) return;
  document.querySelectorAll("[data-gallery-thumb]").forEach((t) => t.addEventListener("click", () => { main.src = t.dataset.full || t.src; }));
}
