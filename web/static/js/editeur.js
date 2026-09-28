// Éditeur de leçon (maquette 04) : active l'éditeur Trix avec les boutons
// de la maquette (gras, italique, titre, puces) et met à jour le compteur.
// Sans JavaScript, la zone de texte simple reste affichée.
const zone = document.getElementById("contenu-lecon");
const editeur = document.getElementById("editeur-lecon");
const barre = document.getElementById("barre-lecon");
const compteur = document.getElementById("compteur-contenu");
const MAX = 20000;

// Pas de fichiers ni d'images dans une leçon : Trix les refuse
document.addEventListener("trix-file-accept", (evenement) => evenement.preventDefault());

if (zone && editeur && barre && compteur) {
  // Compteur : texte visible (sans la mise en forme), en rouge au-delà de 95 %
  const majCompteur = () => {
    const n = editeur.editor.getDocument().toString().length - 1;
    compteur.textContent = `${n.toLocaleString("fr-FR")} / ${MAX.toLocaleString("fr-FR")} caractères`;
    compteur.classList.toggle("compteur-alerte", n > MAX * 0.95);
  };

  // Affiche Trix et sa barre à la place de la zone de texte
  const activer = () => {
    zone.hidden = true;
    editeur.hidden = false;
    barre.hidden = false;
    majCompteur();
  };
  // Trix peut être prêt avant ce script : on vérifie avant d'attendre l'événement
  if (editeur.editor) {
    activer();
  } else {
    editeur.addEventListener("trix-initialize", activer);
  }
  editeur.addEventListener("trix-change", majCompteur);
}
