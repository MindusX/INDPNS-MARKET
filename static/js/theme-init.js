// Chargé en <head> (bloquant) pour éviter le flash de thème. Clair par défaut.
(function () {
  try {
    var t = localStorage.getItem("indpns-theme");
    if (t === "dark" || t === "light") document.documentElement.setAttribute("data-theme", t);
  } catch (e) { /* stockage indisponible : thème clair */ }
})();
