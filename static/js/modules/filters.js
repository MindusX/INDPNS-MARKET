export function initFilters() {
  document.querySelectorAll("form[data-autosubmit]").forEach((f) => {
    f.querySelectorAll("select, input[type=radio], input[type=checkbox]").forEach((el) => el.addEventListener("change", () => { document.dispatchEvent(new Event("indpns:navigate")); f.submit(); }));
  });
  // vue grille / liste mémorisée
  const grid = document.querySelector("[data-product-grid]");
  const btns = document.querySelectorAll("[data-view]");
  if (grid && btns.length) {
    const set = (v) => { grid.classList.toggle("list", v === "list"); btns.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === v))); try { localStorage.setItem("indpns-view", v); } catch (e) {} };
    let v = "grid"; try { v = localStorage.getItem("indpns-view") || "grid"; } catch (e) {}
    set(v); btns.forEach((b) => b.addEventListener("click", () => set(b.dataset.view)));
  }
}
