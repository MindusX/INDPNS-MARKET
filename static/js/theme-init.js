// Chargé en <head> (bloquant) : évite le flash de thème. Clair par défaut ; marque aussi la page comme "js".
(function () {
  var d = document.documentElement;
  d.classList.remove("no-js");
  try { var t = localStorage.getItem("indpns-theme"); if (t === "dark" || t === "light") d.setAttribute("data-theme", t); } catch (e) {}
})();
