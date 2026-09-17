"""Teste la cle d'API telle que l'application la voit, et rien d'autre.

Quand la generation echoue, deux questions se confondent : la cle est-elle
mauvaise, ou l'application la lit-elle mal ? Ce script les separe. Il lit la
configuration par le meme chemin que l'application, decrit ce qu'il trouve
sans jamais afficher le secret, puis fait un appel minimal.

    python -m scripts.tester_cle

Cout : un appel d'un token, soit une fraction de centime.
"""

import sys

from app.config import reglages
from app.modele import AppelModeleEchoue, motif_lisible

PREFIXE_ATTENDU = "sk-ant-"
PLACEHOLDER = "sk-ant-..."


def _masquer(cle: str) -> str:
    """Assez pour reconnaitre sa cle, pas assez pour s'en servir."""
    if len(cle) <= 12:
        return "(trop courte pour etre masquee)"
    return f"{cle[:11]}...{cle[-4:]}"


def diagnostiquer(brut: str) -> list[str]:
    """Les defauts visibles sans appeler l'API. Retourne les problemes trouves."""
    problemes: list[str] = []

    if not brut:
        problemes.append(
            "La cle est vide. Le fichier .env n'a pas de ligne "
            "ANTHROPIC_API_KEY, ou elle est vide."
        )
        return problemes

    if brut == PLACEHOLDER or brut.startswith(PLACEHOLDER):
        problemes.append(
            "La cle est encore l'exemple du fichier .env.example. Il faut la "
            "remplacer par la vraie cle."
        )
        return problemes

    # Les trois accidents de copier-coller les plus courants.
    if brut != brut.strip():
        problemes.append(
            "La cle commence ou finit par une espace. Supprime-la dans le .env."
        )
    if brut.startswith(('"', "'")) or brut.endswith(('"', "'")):
        problemes.append(
            "La cle est entouree de guillemets. Ils n'ont pas a y etre : "
            "ecris la cle nue apres le signe =."
        )
    if not brut.strip().strip("\"'").startswith(PREFIXE_ATTENDU):
        problemes.append(
            f"La cle ne commence pas par « {PREFIXE_ATTENDU} ». Ce n'est "
            "peut-etre pas une cle d'API Anthropic, ou le debut manque."
        )

    return problemes


def main() -> int:
    configuration = reglages()
    brut = configuration.anthropic_api_key

    print("=" * 62)
    print("  Diagnostic de la cle d'API")
    print("=" * 62)
    print()
    print(f"  Mode              : {configuration.mode_modele}")
    print(f"  Modele de generation : {configuration.modele_generation}")
    print(f"  Longueur de la cle : {len(brut)} caracteres")
    print(f"  Cle lue           : {_masquer(brut) if brut else '(aucune)'}")
    print()

    if configuration.mode_modele != "api":
        print(f"  MODE_MODELE vaut « {configuration.mode_modele} » et non « api ».")
        print("  Aucun appel ne sera emis. Corrige la ligne MODE_MODELE du .env.")
        return 1

    problemes = diagnostiquer(brut)
    if problemes:
        print("  PROBLEME DETECTE SANS MEME APPELER L'API :")
        for probleme in problemes:
            print(f"    - {probleme}")
        print()
        return 1

    print("  La cle a la bonne forme. Test d'un appel reel...")
    print()

    # Import tardif : sans lui, un probleme de forme couterait quand meme
    # la construction du client.
    from anthropic import AnthropicError

    from app.modele import client

    try:
        reponse = client().messages.create(
            model=configuration.modele_generation,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
    except AnthropicError as erreur:
        print("  ECHEC. Voici ce que repond Anthropic :")
        print()
        print(f"    {motif_lisible(erreur, configuration.modele_generation)}")
        print()
        print("  Message technique complet, a copier en cas de doute :")
        print(f"    {type(erreur).__name__} : {erreur}")
        print()
        return 1
    except AppelModeleEchoue as erreur:
        print(f"  ECHEC : {erreur}")
        print()
        return 1

    print("  SUCCES. La cle fonctionne et le modele repond.")
    print(f"  Jetons consommes : {reponse.usage.input_tokens} en entree, "
          f"{reponse.usage.output_tokens} en sortie.")
    print()
    print("  Si la generation echoue malgre ca, le probleme n'est pas la cle.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
