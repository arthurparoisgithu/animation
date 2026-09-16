// Mode projection : l'animateur est devant son groupe, il pilote au clavier.
(() => {
  const donnees = JSON.parse(document.getElementById("donnees").textContent);
  const { primitive, items } = donnees;

  const scene = document.getElementById("scene");
  const position = document.getElementById("position");

  let index = 0;
  let revele = false;

  function element(balise, classe, texte) {
    const noeud = document.createElement(balise);
    if (classe) noeud.className = classe;
    if (texte !== undefined) noeud.textContent = texte;
    return noeud;
  }

  const rendus = {
    question(item) {
      const noeuds = [element("p", "enonce", item.question)];

      const liste = element("ul", "propositions");
      item.propositions.forEach((proposition) => {
        const ligne = element("li", null, proposition);
        // La bonne reponse n'est mise en evidence qu'apres revelation.
        if (revele && proposition === item.bonne_reponse) {
          ligne.classList.add("revelee");
        }
        liste.appendChild(ligne);
      });
      noeuds.push(liste);

      const anecdote = element("p", "revelation", item.anecdote);
      anecdote.hidden = !revele;
      noeuds.push(anecdote);
      return noeuds;
    },

    enigme(item) {
      const noeuds = [element("p", "enonce", item.enonce)];
      noeuds.push(element("p", "secondaire", `Indice : ${item.indice}`));
      const solution = element("p", "revelation", item.solution);
      solution.hidden = !revele;
      noeuds.push(solution);
      return noeuds;
    },

    vrai_faux(item) {
      const noeuds = [element("p", "enonce", item.affirmation)];
      const verdict = element("p", "revelation", item.verdict.toUpperCase());
      verdict.hidden = !revele;
      noeuds.push(verdict);
      const explication = element("p", "secondaire", item.explication);
      explication.hidden = !revele;
      noeuds.push(explication);
      return noeuds;
    },
  };

  function afficher() {
    scene.replaceChildren(...rendus[primitive](items[index]));
    position.textContent = `${index + 1} / ${items.length}`;
  }

  function aller(pas) {
    const suivant = index + pas;
    if (suivant < 0 || suivant >= items.length) return;
    index = suivant;
    revele = false; // on ne garde jamais la reponse affichee en changeant d'item
    afficher();
  }

  document.addEventListener("keydown", (evenement) => {
    switch (evenement.key) {
      case "ArrowRight":
      case "PageDown":
        aller(1);
        break;
      case "ArrowLeft":
      case "PageUp":
        aller(-1);
        break;
      case " ":
      case "ArrowDown":
        evenement.preventDefault();
        revele = !revele;
        afficher();
        break;
      case "f":
      case "F":
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen();
        break;
      case "Escape":
        if (!document.fullscreenElement) window.location.href = document.referrer || "/";
        break;
      default:
        break;
    }
  });

  // Au vidéoprojecteur, l'animateur n'a pas toujours un clavier sous la main.
  scene.addEventListener("click", () => {
    revele = !revele;
    afficher();
  });

  afficher();
})();
