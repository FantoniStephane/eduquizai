/* Détail d'un quiz : fenêtre de confirmation avant la validation.
   Amélioration progressive : sans ce script, le formulaire valide directement. */
(function () {
  "use strict";
  var form = document.getElementById("form-validation");
  var voile = document.getElementById("voile-validation");
  var principal = document.getElementById("contenu");
  var annuler = document.getElementById("valid-annuler");
  var confirmer = document.getElementById("valid-confirmer");
  if (!form || !voile || !annuler || !confirmer) { return; }
  var declencheur = form.querySelector("button");

  function ouvrir() {
    voile.hidden = false;
    if (principal) { principal.setAttribute("aria-hidden", "true"); }
    annuler.focus();
  }

  function fermer() {
    voile.hidden = true;
    if (principal) { principal.removeAttribute("aria-hidden"); }
    confirmer.disabled = false;
    declencheur.focus();
  }

  form.addEventListener("submit", function (evenement) {
    evenement.preventDefault();
    ouvrir();
  });

  annuler.addEventListener("click", fermer);

  confirmer.addEventListener("click", function () {
    confirmer.disabled = true;
    form.submit();
  });

  /* Échap ferme la fenêtre ; Tab reste entre les deux boutons */
  voile.addEventListener("keydown", function (evenement) {
    if (evenement.key === "Escape") {
      fermer();
    } else if (evenement.key === "Tab") {
      var cible = evenement.shiftKey ? annuler : confirmer;
      var autre = evenement.shiftKey ? confirmer : annuler;
      if (document.activeElement === cible) {
        evenement.preventDefault();
        autre.focus();
      }
    }
  });

  /* Retour arrière du navigateur : la fenêtre ne doit pas rester ouverte */
  window.addEventListener("pageshow", function () {
    if (!voile.hidden) { fermer(); }
  });
})();
