export function initGallery() {
  const main = document.querySelector("[data-gallery-main]");
  if (!main) return;
  const thumbs = [...document.querySelectorAll("[data-gallery-thumb]")];
  thumbs.forEach((t, i) => { if (i === 0) t.classList.add("active"); t.addEventListener("click", () => { main.src = t.dataset.full || t.src; thumbs.forEach((x) => x.classList.toggle("active", x === t)); }); });
  let box = document.querySelector(".lightbox");
  if (!box) {
    box = document.createElement("div"); box.className = "lightbox"; box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
    box.innerHTML = '<button class="icon-btn btn" type="button" aria-label="Close">✕</button><img alt="">'; document.body.appendChild(box);
    box.addEventListener("click", (e) => { if (e.target !== box.querySelector("img")) box.classList.remove("open"); });
  }
  main.parentElement.addEventListener("click", () => { box.querySelector("img").src = main.src; box.classList.add("open"); });
}
