// Un bouton plutot qu'un Ctrl+P : l'animateur qui ouvre l'outil pour la
// premiere fois n'a aucune raison de deviner que la page est mise en forme
// pour l'impression. La feuille de style fait le travail, ce fichier ne
// fait que proposer le geste.
const bouton = document.getElementById("imprimer");
if (bouton) {
  bouton.addEventListener("click", () => window.print());
}
