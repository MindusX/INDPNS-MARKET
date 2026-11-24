export function initPricing() {
  const btns = document.querySelectorAll("[data-billing]");
  btns.forEach((b) => b.addEventListener("click", () => {
    btns.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    document.querySelectorAll("[data-price-monthly]").forEach((el) => (el.hidden = b.dataset.billing !== "monthly"));
    document.querySelectorAll("[data-price-yearly]").forEach((el) => (el.hidden = b.dataset.billing !== "yearly"));
  }));
}
