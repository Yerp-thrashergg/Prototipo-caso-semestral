/* Botón de modo claro / oscuro.*/
(function () {
  var boton = document.getElementById("btn-tema");
  if (!boton) { return; }

  function mostrar() {
    var oscuro = document.documentElement.getAttribute("data-tema") === "dark";
    boton.textContent = oscuro ? "Modo claro" : "Modo oscuro";
    boton.setAttribute("aria-pressed", oscuro ? "true" : "false");
  }

  boton.addEventListener("click", function () {
    var nuevo = document.documentElement.getAttribute("data-tema") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-tema", nuevo);
    try { localStorage.setItem("tema", nuevo); } catch (e) {}
    mostrar();
  });

  mostrar();
})();
