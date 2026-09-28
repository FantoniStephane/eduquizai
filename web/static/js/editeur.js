// Éditeur de leçon (maquette 04) : barre de mise en forme Markdown
// et compteur de caractères mis à jour pendant la frappe.
const zone = document.getElementById("contenu-lecon");
const barre = document.querySelector(".barre-outils");
const compteur = document.getElementById("compteur-contenu");

if (zone && barre && compteur) {
  const max = zone.maxLength;

  // Compteur : « 612 / 20 000 caractères », en rouge au-delà de 95 %
  const majCompteur = () => {
    const n = zone.value.length;
    compteur.textContent = `${n.toLocaleString("fr-FR")} / ${max.toLocaleString("fr-FR")} caractères`;
    compteur.classList.toggle("compteur-alerte", n > max * 0.95);
  };
  zone.addEventListener("input", majCompteur);
  majCompteur();

  // Remplace le texte entre debut et fin. insertText garde l'historique
  // du navigateur (Ctrl+Z annule la mise en forme) ; setRangeText sert de secours.
  const remplacer = (texte, debut, fin) => {
    zone.focus();
    zone.setSelectionRange(debut, fin);
    if (!document.execCommand("insertText", false, texte)) {
      zone.setRangeText(texte, debut, fin, "end");
    }
  };

  // Entoure la sélection (gras, italique) ; sans sélection, insère un exemple
  const entourer = (marque, texteParDefaut) => {
    const { selectionStart: debut, selectionEnd: fin, value } = zone;
    const selection = value.slice(debut, fin) || texteParDefaut;
    remplacer(marque + selection + marque, debut, fin);
    zone.setSelectionRange(debut + marque.length, debut + marque.length + selection.length);
  };

  // Ajoute un préfixe au début de chaque ligne sélectionnée (titre, liste),
  // ou le retire si toutes les lignes l'ont déjà (second clic = annuler)
  const prefixer = (prefixe) => {
    const { selectionStart: debut, selectionEnd: fin, value } = zone;
    const debutLigne = value.lastIndexOf("\n", debut - 1) + 1;
    const lignes = value.slice(debutLigne, fin).split("\n");
    const dejaFait = lignes.every((ligne) => ligne.startsWith(prefixe));
    const texte = lignes
      .map((ligne) => (dejaFait ? ligne.slice(prefixe.length) : prefixe + ligne))
      .join("\n");
    remplacer(texte, debutLigne, fin);
    // Sélection de départ : on garde les lignes sélectionnées ; simple curseur : il reste en place
    const finTexte = debutLigne + texte.length;
    zone.setSelectionRange(debut === fin ? finTexte : debutLigne, finTexte);
  };

  const actions = {
    gras: () => entourer("**", "texte en gras"),
    italique: () => entourer("*", "texte en italique"),
    titre: () => prefixer("## "),
    liste: () => prefixer("- "),
  };

  barre.hidden = false;
  barre.addEventListener("click", (evenement) => {
    const bouton = evenement.target.closest("button[data-action]");
    if (!bouton) return;
    actions[bouton.dataset.action]();
    majCompteur();
  });
}
