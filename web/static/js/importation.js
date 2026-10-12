// Import d'un fichier texte (maquette 04c) : envoie le fichier .txt ou .docx au
// serveur, qui renvoie le texte mis en forme, puis le charge dans l'éditeur Trix.
// Amélioration progressive : le bouton n'apparaît qu'avec JavaScript, quand
// l'éditeur est actif. Le serveur contrôle le fichier ; ici, seulement un
// contrôle de confort.
(function () {
  "use strict";
  var ouvrir = document.getElementById("ouvrir-import");
  var voile = document.getElementById("voile-import");
  var editeur = document.getElementById("editeur-lecon");
  var formulaire = document.getElementById("form-import");
  if (!ouvrir || !voile || !editeur || !formulaire) { return; }

  var principal = document.getElementById("contenu");
  var champ = document.getElementById("fichier");
  var depot = document.getElementById("depot");
  var choisir = document.getElementById("choisir-fichier");
  var choisi = document.getElementById("fichier-choisi");
  var choisiTexte = document.getElementById("fichier-choisi-texte");
  var erreur = document.getElementById("erreur-import");
  var erreurTexte = document.getElementById("erreur-import-texte");
  var annuler = document.getElementById("import-annuler");
  var valider = document.getElementById("import-valider");
  var TAILLE_MAX = 5 * 1024 * 1024;

  function afficherErreur(message) {
    erreurTexte.textContent = message;
    erreur.hidden = false;
  }

  function reinitialiser() {
    formulaire.reset();
    choisi.hidden = true;
    erreur.hidden = true;
    valider.disabled = true;
    valider.textContent = "Importer le texte";
  }

  function fermer() {
    voile.hidden = true;
    if (principal) { principal.removeAttribute("aria-hidden"); }
    reinitialiser();
    ouvrir.focus();
  }

  function ouvrirFenetre() {
    reinitialiser();
    voile.hidden = false;
    if (principal) { principal.setAttribute("aria-hidden", "true"); }
    choisir.focus();
  }

  // Le bouton est utile seulement quand Trix a remplacé la zone de texte
  function activer() { ouvrir.hidden = false; }
  if (editeur.editor) {
    activer();
  } else {
    editeur.addEventListener("trix-initialize", activer);
  }

  function taille(octets) {
    return octets < 1024 * 1024
      ? Math.max(1, Math.round(octets / 1024)) + " Ko"
      : (octets / (1024 * 1024)).toFixed(1).replace(".", ",") + " Mo";
  }

  // Contrôle de confort : le vrai contrôle est fait par le serveur
  function fichierChoisi() {
    erreur.hidden = true;
    var fichier = champ.files && champ.files[0];
    if (!fichier) {
      choisi.hidden = true;
      valider.disabled = true;
      return;
    }
    var nom = fichier.name.toLowerCase();
    if (!/\.(txt|docx)$/.test(nom)) {
      choisi.hidden = true;
      valider.disabled = true;
      afficherErreur("Format non accepté : choisissez un fichier .docx ou .txt.");
      return;
    }
    if (fichier.size > TAILLE_MAX) {
      choisi.hidden = true;
      valider.disabled = true;
      afficherErreur("Le fichier dépasse la taille maximale de 5 Mo.");
      return;
    }
    choisiTexte.textContent = "";
    var gras = document.createElement("strong");
    gras.textContent = fichier.name;
    choisiTexte.appendChild(gras);
    choisiTexte.appendChild(document.createTextNode(" · " + taille(fichier.size) + " · prêt à importer"));
    choisi.hidden = false;
    valider.disabled = false;
  }

  ouvrir.addEventListener("click", ouvrirFenetre);
  annuler.addEventListener("click", fermer);
  champ.addEventListener("change", fichierChoisi);

  // « Choisir un fichier » au clavier (Entrée ou Espace)
  choisir.addEventListener("keydown", function (evenement) {
    if (evenement.key === "Enter" || evenement.key === " ") {
      evenement.preventDefault();
      champ.click();
    }
  });

  // Glisser-déposer
  ["dragenter", "dragover"].forEach(function (nom) {
    depot.addEventListener(nom, function (evenement) {
      evenement.preventDefault();
      depot.classList.add("survol");
    });
  });
  ["dragleave", "drop"].forEach(function (nom) {
    depot.addEventListener(nom, function (evenement) {
      evenement.preventDefault();
      depot.classList.remove("survol");
    });
  });
  depot.addEventListener("drop", function (evenement) {
    var fichiers = evenement.dataTransfer && evenement.dataTransfer.files;
    if (fichiers && fichiers.length) {
      champ.files = fichiers;
      fichierChoisi();
    }
  });

  formulaire.addEventListener("submit", function (evenement) {
    evenement.preventDefault();
    var fichier = champ.files && champ.files[0];
    if (!fichier) { return; }
    var jeton = document.querySelector("input[name=csrfmiddlewaretoken]");
    var donnees = new FormData();
    donnees.append("fichier", fichier);
    valider.disabled = true;
    valider.textContent = "Import en cours…";
    erreur.hidden = true;
    fetch(ouvrir.dataset.url, {
      method: "POST",
      body: donnees,
      credentials: "same-origin",
      headers: { "X-CSRFToken": jeton ? jeton.value : "" }
    })
      .then(function (reponse) {
        return reponse.json().then(
          function (corps) { return { ok: reponse.ok, corps: corps }; },
          function () { return { ok: false, corps: {} }; }
        );
      })
      .then(function (resultat) {
        if (resultat.ok && typeof resultat.corps.html === "string") {
          editeur.editor.loadHTML(resultat.corps.html);
          voile.hidden = true;
          if (principal) { principal.removeAttribute("aria-hidden"); }
          reinitialiser();
          editeur.focus();
        } else {
          valider.textContent = "Importer le texte";
          valider.disabled = false;
          afficherErreur(resultat.corps.erreur || "L'import a échoué. Réessayez.");
        }
      })
      .catch(function () {
        valider.textContent = "Importer le texte";
        valider.disabled = false;
        afficherErreur("L'import a échoué. Vérifiez votre connexion et réessayez.");
      });
  });

  // Échap ferme la fenêtre ; Tab reste dans la fenêtre
  voile.addEventListener("keydown", function (evenement) {
    if (evenement.key === "Escape") {
      fermer();
    } else if (evenement.key === "Tab") {
      var focalisables = Array.prototype.filter.call(
        voile.querySelectorAll("button, [tabindex='0']"),
        function (element) { return !element.disabled && !element.hidden; }
      );
      var premier = focalisables[0];
      var dernier = focalisables[focalisables.length - 1];
      if (evenement.shiftKey && document.activeElement === premier) {
        evenement.preventDefault();
        dernier.focus();
      } else if (!evenement.shiftKey && document.activeElement === dernier) {
        evenement.preventDefault();
        premier.focus();
      }
    }
  });

  // Retour arrière du navigateur : la fenêtre ne doit pas rester ouverte
  window.addEventListener("pageshow", function () {
    if (!voile.hidden) { fermer(); }
  });
})();
