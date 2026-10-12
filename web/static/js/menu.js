// Ouvre et ferme la navigation principale sur petit écran (bouton « menu »).
const boutonMenu = document.querySelector(".menu-mobile");
const entete = document.getElementById("entete");

if (boutonMenu && entete) {
  boutonMenu.addEventListener("click", () => {
    const ouvert = entete.classList.toggle("menu-ouvert");
    boutonMenu.setAttribute("aria-expanded", String(ouvert));
    boutonMenu.setAttribute("aria-label", ouvert ? "Fermer le menu" : "Ouvrir le menu");
  });
}
