/* Modification d'un quiz : suppression d'une question.
   Amélioration progressive : les boutons « Supprimer la question » sont cachés
   sans JavaScript. Supprimer coche le champ caché q<i>-supprimer et masque la
   question ; la suppression n'est enregistrée qu'avec « Enregistrer ». */
(function () {
  "use strict";
  var form = document.getElementById("form-modification");
  if (!form) { return; }
  var sommaire = document.getElementById("sommaire");

  function questionsVisibles() {
    return Array.prototype.filter.call(
      form.querySelectorAll("fieldset.q-edit"),
      function (q) { return !q.hidden; }
    );
  }

  /* Renumérote les questions restantes et reconstruit le sommaire */
  function renumeroter() {
    var visibles = questionsVisibles();
    /* Une question masquée n'a plus d'ancre : pas d'identifiant en double */
    Array.prototype.forEach.call(form.querySelectorAll("fieldset.q-edit[hidden]"), function (q) {
      q.removeAttribute("id");
    });
    visibles.forEach(function (q, i) {
      var n = i + 1;
      q.id = "q" + n;
      q.querySelector(".num").textContent = n;
      q.querySelector("legend").textContent = "Question " + n;
      var bouton = q.querySelector("[data-supprimer-question]");
      bouton.setAttribute("aria-label", "Supprimer la question " + n);
      /* Une question au moins doit rester */
      bouton.hidden = visibles.length === 1;
    });
    if (sommaire) {
      sommaire.textContent = "";
      visibles.forEach(function (q, i) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = "#q" + (i + 1);
        a.textContent = String(i + 1);
        li.appendChild(a);
        sommaire.appendChild(li);
      });
    }
  }

  form.addEventListener("click", function (evenement) {
    var bouton = evenement.target.closest("[data-supprimer-question]");
    if (!bouton) { return; }
    var question = bouton.closest("fieldset.q-edit");
    if (questionsVisibles().length <= 1) { return; }
    question.querySelector("[data-supprimer]").value = "1";
    question.hidden = true;
    renumeroter();
    var suivante = questionsVisibles()[0];
    if (suivante) { suivante.querySelector("textarea").focus(); }
  });

  renumeroter();
})();
