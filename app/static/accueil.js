// JavaScript natif : le sujet de demonstration du projet est le back-end.
(() => {
  const filtres = {
    public: document.getElementById("filtre-public"),
    moment: document.getElementById("filtre-moment"),
    materiel: document.getElementById("filtre-materiel"),
  };
  const conteneurFormats = document.getElementById("formats");
  const formulaire = document.getElementById("formulaire");
  const champNbItems = document.getElementById("nb_items");
  const bouton = document.getElementById("lancer");
  const message = document.getElementById("message");

  let formatChoisi = null;

  function afficher(texte, classe = "attenue") {
    message.className = `message ${classe}`;
    message.textContent = texte;
  }

  function carteFormat(format) {
    const carte = document.createElement("button");
    carte.type = "button";
    carte.className = "carte format";
    carte.dataset.code = format.code;
    carte.dataset.nb = format.nb_items_defaut;
    carte.setAttribute("aria-pressed", "false");
    carte.innerHTML = `
      <h3></h3><p></p>
      <div class="etiquettes">
        <span class="etiquette"></span>
        <span class="etiquette"></span>
        <span class="etiquette"></span>
      </div>`;
    // textContent et non innerHTML : le contenu vient de la base, on ne
    // l'injecte pas comme du HTML.
    carte.querySelector("h3").textContent = format.nom;
    carte.querySelector("p").textContent = format.regle_animateur;
    const etiquettes = carte.querySelectorAll(".etiquette");
    etiquettes[0].textContent = format.primitive;
    etiquettes[1].textContent = format.moment;
    etiquettes[2].textContent = format.materiel;
    return carte;
  }

  function choisir(carte) {
    conteneurFormats
      .querySelectorAll(".format")
      .forEach((autre) => autre.setAttribute("aria-pressed", "false"));
    carte.setAttribute("aria-pressed", "true");
    formatChoisi = carte.dataset.code;
    champNbItems.placeholder = `${carte.dataset.nb} par défaut`;
    bouton.disabled = false;
    afficher(`Format choisi : ${carte.querySelector("h3").textContent}`);
  }

  conteneurFormats.addEventListener("click", (evenement) => {
    const carte = evenement.target.closest(".format");
    if (carte) choisir(carte);
  });

  async function rechargerFormats() {
    const parametres = new URLSearchParams();
    for (const [nom, champ] of Object.entries(filtres)) {
      if (champ.value) parametres.set(nom, champ.value);
    }

    const reponse = await fetch(`/api/formats?${parametres}`);
    const formats = await reponse.json();

    conteneurFormats.replaceChildren(...formats.map(carteFormat));
    formatChoisi = null;
    bouton.disabled = true;

    if (formats.length === 0) {
      afficher("Aucun format ne correspond à ces filtres.", "erreur");
    } else {
      afficher("Choisis un format ci-dessus.");
    }
  }

  Object.values(filtres).forEach((champ) =>
    champ.addEventListener("change", rechargerFormats)
  );

  formulaire.addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    if (!formatChoisi) return;

    const donnees = new FormData(formulaire);
    const corps = {
      format_code: formatChoisi,
      theme: donnees.get("theme"),
      public: donnees.get("public"),
    };
    if (donnees.get("nb_items")) corps.nb_items = Number(donnees.get("nb_items"));
    if (donnees.get("code")) corps.code = donnees.get("code");

    bouton.disabled = true;
    afficher("Génération, validation déterministe puis juge… compte une trentaine de secondes.");

    try {
      const reponse = await fetch("/api/jeux", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corps),
      });
      const resultat = await reponse.json();

      if (!reponse.ok) {
        const detail = resultat.detail;
        afficher(
          typeof detail === "string" ? detail : detail.message || "Génération refusée.",
          "erreur"
        );
        // Les motifs de rejet sont affiches : c'est la partie interessante.
        if (detail && Array.isArray(detail.rejets)) {
          const liste = document.createElement("ul");
          for (const rejet of detail.rejets.slice(0, 12)) {
            const ligne = document.createElement("li");
            ligne.textContent = `[${rejet.niveau}] ${rejet.motif}`;
            liste.appendChild(ligne);
          }
          message.appendChild(liste);
        }
        return;
      }

      window.location.href = `/jeu/${resultat.id}`;
    } catch (erreur) {
      afficher(`Erreur réseau : ${erreur.message}`, "erreur");
    } finally {
      bouton.disabled = false;
    }
  });
})();
