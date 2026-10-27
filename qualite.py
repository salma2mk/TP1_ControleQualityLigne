
import re
import math
from donnees import LOT_A


# Paramètres du contrôle qualité
NOMINAL = 25.00
TOLERANCE = 0.05


# --- Étape 1 : lire et valider ----------------------------------

def lire_mesure(texte: str) -> float:
    """Convertit une mesure comme '25,03 mm' en 25.03."""

    # Supprimer les espaces autour du texte
    texte = texte.strip()

    # Vérifier le format numérique et l'unité facultative
    motif = r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)\s*(?:mm)?"

    if not re.fullmatch(motif, texte):
        raise ValueError(f"mesure invalide : {texte!r}")

    # Enlever l'unité mm et remplacer la virgule
    nombre = texte.removesuffix("mm").strip()
    nombre = nombre.replace(",", ".")

    mesure = float(nombre)

    # La mesure doit être positive et finie
    if not math.isfinite(mesure) or mesure <= 0:
        raise ValueError(f"mesure invalide : {texte!r}")

    return mesure



def valider_code(code: str) -> bool:
    """Vrai si le code respecte le format AAA-9999."""

    if len(code) != 8:
        return False

    lettres = code[:3]
    tiret = code[3]
    chiffres = code[4:]

    if not lettres.isalpha():
        return False

    if not lettres.isupper():
        return False

    if not lettres.isascii():
        return False

    if tiret != "-":
        return False

    if not chiffres.isdigit():
        return False

    if not chiffres.isascii():
        return False

    return True



# --- Étape 2 : décider ------------------------------------------

def ecart(mesure: float, nominal: float = NOMINAL) -> float:
    """Calcule l'écart à la cote nominale."""

    return round(mesure - nominal, 3)


def verdict(
    mesure: float,  
    nominal: float = NOMINAL,
    tolerance: float = TOLERANCE
) -> str:
    """Détermine si la pièce est conforme ou non."""

    difference = ecart(mesure, nominal)

    if -tolerance <= difference <= tolerance:
        return "conforme"

    elif difference > tolerance:
        return "à reprendre"

    else:
        return "rebut"


# --- Étape 3 : analyser une ligne --------------------------------

def analyser_ligne(
    ligne: str,
    *,
    nominal: float = NOMINAL,
    tolerance: float = TOLERANCE
) -> tuple[str, float, str]:
    """Analyse 'AXE-0042 ; 25,03 mm'."""

    champs = ligne.split(";")

    if len(champs) != 2:
        raise ValueError("la ligne doit contenir deux champs")

    code = champs[0].strip()
    texte_mesure = champs[1].strip()

    if not valider_code(code):
        raise ValueError(f"code invalide : {code!r}")

    mesure = lire_mesure(texte_mesure)

    resultat = verdict(mesure, nominal, tolerance)

    return code, mesure, resultat


# --- Étape 4 : analyser un lot -----------------------------------

def analyser_lot(
    lignes: list[str],
    **reglages
) -> tuple[list[tuple[str, float, str]], list[str]]:
    """Analyse un lot sans s'arrêter sur les erreurs."""

    resultats = []
    erreurs = []

    for numero, ligne in enumerate(lignes, start=1):

        ligne = ligne.strip()

        # Ignorer les lignes vides et commentaires
        if not ligne or ligne.startswith("#"):
            continue

        try:
            resultat = analyser_ligne(ligne, **reglages)
            resultats.append(resultat)

        except ValueError as erreur:
            erreurs.append(f"ligne {numero} : {erreur}")

    return resultats, erreurs


def compter_verdicts(
    resultats: list[tuple[str, float, str]]
) -> tuple[int, int, int]:
    """Compte les pièces par catégorie."""

    conformes = 0
    reprises = 0
    rebuts = 0

    for code, mesure, resultat in resultats:

        if resultat == "conforme":
            conformes += 1

        elif resultat == "à reprendre":
            reprises += 1

        elif resultat == "rebut":
            rebuts += 1

    return conformes, reprises, rebuts


# --- Étape 5 : statistiques et capabilité -------------------------

def moyenne(*valeurs: float) -> float:
    """Calcule la moyenne de plusieurs valeurs."""

    if len(valeurs) == 0:
        raise ValueError("aucune valeur fournie")

    return sum(valeurs) / len(valeurs)


def ecart_type(*valeurs: float) -> float:
    """Calcule l'écart type d'échantillon."""

    n = len(valeurs)

    if n < 2:
        raise ValueError("au moins deux valeurs nécessaires")

    m = moyenne(*valeurs)

    somme = sum((x - m) ** 2 for x in valeurs)

    return math.sqrt(somme / (n - 1))


def capabilite(
    mesures: list[float],
    *,
    nominal: float = NOMINAL,
    tolerance: float = TOLERANCE
) -> tuple[float, float]:
    """Calcule les indices Cp et Cpk."""

    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValueError("tolérance invalide")

    if not math.isfinite(nominal):
        raise ValueError("nominal invalide")

    m = moyenne(*mesures)
    sigma = ecart_type(*mesures)

    # Cas où toutes les mesures sont identiques
    if sigma == 0:
        raise ValueError("capabilité indéfinie : écart type nul")

    limite_sup = nominal + tolerance
    limite_inf = nominal - tolerance

    cp = (limite_sup - limite_inf) / (6 * sigma)

    cpk = min(
        limite_sup - m,
        m - limite_inf
    ) / (3 * sigma)

    return round(cp, 2), round(cpk, 2)


# --- Étape 6 : rapport -------------------------------------------

def rapport(
    lignes: list[str],
    *,
    nominal: float = NOMINAL,
    tolerance: float = TOLERANCE
) -> str:
    """Construit un rapport complet de contrôle qualité."""

    resultats, erreurs = analyser_lot(
        lignes,
        nominal=nominal,
        tolerance=tolerance
    )

    conformes, reprises, rebuts = compter_verdicts(resultats)

    rapport_lignes = [
        "===== RAPPORT DE CONTROLE QUALITE =====",
        f"Nominal : {nominal:.3f} mm",
        f"Tolerance : +/- {tolerance:.3f} mm",
        "",
        "--- Pieces analysees ---"
    ]

    for code, mesure, resultat in resultats:
        rapport_lignes.append(
            f"{code} | {mesure:.3f} mm | {resultat}"
        )

    rapport_lignes.extend([
        "",
        "--- Bilan ---",
        f"Conformes : {conformes}",
        f"A reprendre : {reprises}",
        f"Rebuts : {rebuts}",
        f"Erreurs : {len(erreurs)}"
    ])

    if resultats:
        mesures = [mesure for _, mesure, _ in resultats]

        rapport_lignes.append(
            f"Moyenne : {moyenne(*mesures):.3f} mm"
        )

        if len(mesures) >= 2:
            sigma = ecart_type(*mesures)
            rapport_lignes.append(
                f"Ecart type : {sigma:.4f} mm"
            )

            if sigma > 0:
                cp, cpk = capabilite(
                    mesures,
                    nominal=nominal,
                    tolerance=tolerance
                )

                rapport_lignes.append(f"Cp : {cp:.2f}")
                rapport_lignes.append(f"Cpk : {cpk:.2f}")
            else:
                rapport_lignes.append(
                    "Cp et Cpk : non definis (sigma nul)"
                )

    if erreurs:
        rapport_lignes.append("")
        rapport_lignes.append("--- Erreurs ---")
        rapport_lignes.extend(erreurs)

    return "\n".join(rapport_lignes)


# --- Étape 8 : histogramme ---------------------------------------

def histogramme(
    mesures: list[float],
    *,
    debut: float,
    pas: float,
    nb_classes: int
) -> str:
    """Construit un histogramme textuel."""

    if pas <= 0 or not math.isfinite(pas):
        raise ValueError("le pas doit être positif et fini")

    if nb_classes <= 0 or type(nb_classes) is not int:
        raise ValueError("nombre de classes invalide")

    if not math.isfinite(debut):
        raise ValueError("début invalide")

    lignes = []

    for i in range(nb_classes):

        borne_inf = debut + i * pas
        borne_sup = debut + (i + 1) * pas

        effectif = sum(
            1 for mesure in mesures
            if borne_inf <= mesure < borne_sup
        )

        etoiles = "*" * effectif

        lignes.append(
            f"[{borne_inf:.3f}, {borne_sup:.3f}[ : {etoiles}"
        )

    return "\n".join(lignes)


# --- Étape 7 : tester le programme -------------------------------

if __name__ == "__main__":

    lignes = [
        "# Lot de contrôle",
        "AXE-0042 ; 25,03 mm",
        "VIS-0001 ; 24,92 mm",
        "TUB-0123 ; 25,08 mm",
        "BAG-0004 ; 25,00 mm",
        "ERR-0005 ; abc",
        "",
        "AXE-0043 ; 25,02 mm"
    ]

    print(rapport(LOT_A))

    resultats, erreurs = analyser_lot(LOT_A)

    mesures = [mesure for _, mesure, _ in resultats]

    print("\n===== HISTOGRAMME =====")

    print(histogramme(
        mesures,
        debut=24.90,
        pas=0.05,
        nb_classes=5
    ))
