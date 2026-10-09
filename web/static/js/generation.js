/* Page « Générer un quiz » : amélioration progressive (le formulaire marche sans ce script).
   Les textes de leçon sont insérés avec textContent : aucune injection HTML possible. */
(function () {
  "use strict";
  var form = document.getElementById("form-generation");
  var voile = document.getElementById("voile-attente");
  if (!form || !voile) { return; }

  var selectLecon = document.getElementById("lecon");
  var titre = document.getElementById("titre");
  var nombre = document.getElementById("nombre");
  var bouton = document.getElementById("bouton-generer");
  var apercu = document.getElementById("apercu-lecon");
  var lecons = [];
  try {
    lecons = JSON.parse(document.getElementById("donnees-lecons").textContent);
  } catch (e) { lecons = []; }

  /* Boutons − / + : affichés seulement avec JavaScript */
  var MIN = 3, MAX = 20;
  form.querySelectorAll("[data-pas]").forEach(function (b) {
    b.hidden = false;
    b.addEventListener("click", function () {
      var valeur = parseInt(nombre.value, 10);
      if (isNaN(valeur)) { valeur = 10; }
      nombre.value = Math.min(MAX, Math.max(MIN, valeur + parseInt(b.dataset.pas, 10)));
    });
  });

  /* Aperçu de la leçon choisie + titre proposé tant que l'utilisateur n'a rien tapé */
  var titreModifie = titre.value !== "";
  titre.addEventListener("input", function () { titreModifie = true; });

  function ligne(balise, texte, classe) {
    var el = document.createElement(balise);
    el.textContent = texte;
    if (classe) { el.className = classe; }
    return el;
  }

  selectLecon.addEventListener("change", function () {
    var lecon = lecons.find(function (l) { return String(l.pk) === selectLecon.value; });
    apercu.textContent = "";
    if (!lecon) {
      apercu.appendChild(ligne("p", "Choisissez une leçon pour en voir un aperçu.", "muted"));
      return;
    }
    var gras = document.createElement("p");
    gras.appendChild(ligne("strong", lecon.titre));
    apercu.appendChild(gras);
    apercu.appendChild(ligne("p", lecon.matiere + " · " + lecon.niveau + " · " + lecon.nb_car + " caractères", "muted"));
    apercu.appendChild(ligne("p", lecon.apercu, "apercu"));
    if (!titreModifie) { titre.value = ("Quiz — " + lecon.titre).slice(0, 100); }
  });

  /* Écran d'attente : seulement si les contrôles de base sont bons, sinon le serveur
     réaffiche les messages d'erreur sans attente inutile */
  form.addEventListener("submit", function () {
    var valeur = parseInt(nombre.value, 10);
    var ok = selectLecon.value !== "" && titre.value.trim() !== "" &&
      form.querySelector('input[name="types"]:checked') !== null &&
      valeur >= MIN && valeur <= MAX;
    if (!ok) { return; }
    idGeneration.value = nouvelIdentifiant();
    voile.hidden = false;
    bouton.disabled = true;
    if (aideAnnuler) { aideAnnuler.hidden = false; }
    if (annuler) { annuler.focus(); }
  });

  /* Annuler : on arrête d'attendre, on prévient le serveur (il n'enregistrera pas
     le quiz) et on rend le formulaire. L'IA, elle, finit son calcul côté serveur. */
  var idGeneration = document.getElementById("id-generation");
  function nouvelIdentifiant() {
    if (window.crypto && window.crypto.randomUUID) { return window.crypto.randomUUID(); }
    return String(Date.now()) + "-" + String(Math.floor(Math.random() * 1e9));
  }
  var annuler = document.getElementById("bouton-annuler");
  var aideAnnuler = document.getElementById("aide-annuler");
  if (annuler) {
    annuler.addEventListener("click", function () {
      if (window.stop) { window.stop(); }
      var jeton = form.querySelector('input[name="csrfmiddlewaretoken"]');
      var donnees = new FormData();
      donnees.append("id_generation", idGeneration.value);
      fetch(form.dataset.urlAnnuler, {
        method: "POST",
        body: donnees,
        credentials: "same-origin",
        keepalive: true,
        headers: { "X-CSRFToken": jeton ? jeton.value : "" }
      }).catch(function () { /* sans réponse : le quiz sera simplement enregistré */ });
      idGeneration.value = "";
      voile.hidden = true;
      bouton.disabled = false;
      if (aideAnnuler) { aideAnnuler.hidden = true; }
      bouton.focus();
    });
  }

  /* Retour arrière du navigateur : on masque l'attente et on réactive le bouton */
  window.addEventListener("pageshow", function () {
    voile.hidden = true;
    bouton.disabled = false;
  });
})();
