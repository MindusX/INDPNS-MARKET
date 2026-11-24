export function initFilters() {
  document.querySelectorAll("form[data-autosubmit] select, form[data-autosubmit] input[type=radio], form[data-autosubmit] input[type=checkbox]")
    .forEach((el) => el.addEventListener("change", () => el.form.submit()));
}
