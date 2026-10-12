"""Jeu de données de démonstration (commande ``donnees_demo``).

Quatre leçons de collège et trois quiz, dans les formats enregistrés par
l'application : contenu des leçons en Markdown, quiz conformes aux règles de
validation (QCM à 4 choix, vrai/faux, question ouverte). Une leçon reste sans
quiz pour montrer la génération et la suppression d'une leçon.
"""

ENSEIGNANTE = {
    "email": "anne.durand@eduquizai.local",
    "nom": "Durand",
    "prenom": "Anne",
}


def _qcm(texte, choix, bonne, explication):
    """Question à choix multiples ; ``bonne`` est le numéro du bon choix."""
    return {
        "type_question": "qcm",
        "texte": texte,
        "explication": explication,
        "choix": [
            {"texte": libelle, "est_correct": numero == bonne}
            for numero, libelle in enumerate(choix)
        ],
    }


def _vrai_faux(texte, vrai, explication):
    """Affirmation à juger vraie ou fausse."""
    return {
        "type_question": "vrai_faux",
        "texte": texte,
        "explication": explication,
        "choix": [
            {"texte": "Vrai", "est_correct": vrai},
            {"texte": "Faux", "est_correct": not vrai},
        ],
    }


def _ouverte(texte, reponse, explication):
    """Question ouverte avec la réponse attendue."""
    return {
        "type_question": "ouverte",
        "texte": texte,
        "explication": explication,
        "reponse_attendue": reponse,
        "choix": [],
    }


LECONS = [
    {
        "cle": "revolution",
        "titre": "La Révolution française",
        "matiere": "histoire",
        "niveau_scolaire": "4e",
        "contenu": (
            "## Les causes\n\n"
            "En 1789, le royaume de France traverse une grave crise financière : "
            "l'État est endetté et les impôts pèsent surtout sur le tiers état. "
            "Les idées des philosophes des Lumières, comme Montesquieu ou "
            "Rousseau, remettent en cause la monarchie absolue.\n\n"
            "## Les grandes étapes de 1789\n\n"
            "- Le 5 mai 1789, Louis XVI réunit les états généraux à Versailles.\n"
            "- Le 20 juin 1789, les députés du tiers état prêtent le serment du "
            "Jeu de paume.\n"
            "- Le 14 juillet 1789, les Parisiens prennent la Bastille, une prison "
            "symbole du pouvoir royal.\n"
            "- Dans la nuit du 4 août 1789, l'Assemblée abolit les privilèges.\n"
            "- Le 26 août 1789, elle adopte la Déclaration des droits de l'homme "
            "et du citoyen.\n\n"
            "## La fin de la monarchie\n\n"
            "La monarchie est abolie le 21 septembre 1792 et la Première "
            "République est proclamée. Louis XVI est exécuté le 21 janvier 1793."
        ),
    },
    {
        "cle": "volcans",
        "titre": "Les volcans",
        "matiere": "svt",
        "niveau_scolaire": "5e",
        "contenu": (
            "## Qu'est-ce qu'un volcan ?\n\n"
            "Un volcan est un relief formé par l'accumulation de matériaux issus "
            "d'une remontée de magma. Le magma est une roche fondue qui se forme "
            "en profondeur. Lorsqu'il arrive à la surface, il prend le nom de "
            "lave.\n\n"
            "## Deux types d'éruptions\n\n"
            "- Les éruptions effusives produisent des coulées de lave fluide. "
            "C'est le cas au Piton de la Fournaise, à La Réunion.\n"
            "- Les éruptions explosives projettent des cendres et des blocs de "
            "roche. La lave, très visqueuse, peut former un dôme.\n\n"
            "## Où trouve-t-on des volcans ?\n\n"
            "La plupart des volcans se trouvent à la limite des plaques "
            "tectoniques. L'Etna, en Sicile, est l'un des volcans les plus actifs "
            "d'Europe."
        ),
    },
    {
        "cle": "pythagore",
        "titre": "Le théorème de Pythagore",
        "matiere": "mathematiques",
        "niveau_scolaire": "4e",
        "contenu": (
            "## L'énoncé\n\n"
            "Dans un triangle rectangle, le carré de la longueur de l'hypoténuse "
            "est égal à la somme des carrés des longueurs des deux autres côtés. "
            "L'hypoténuse est le côté opposé à l'angle droit : c'est le plus long "
            "côté du triangle.\n\n"
            "## Exemple\n\n"
            "Si ABC est rectangle en A, avec AB = 3 cm et AC = 4 cm, alors "
            "BC² = 3² + 4² = 9 + 16 = 25, donc BC = 5 cm.\n\n"
            "## La réciproque\n\n"
            "Si, dans un triangle, le carré du plus long côté est égal à la somme "
            "des carrés des deux autres côtés, alors ce triangle est rectangle."
        ),
    },
    {
        "cle": "present_perfect",
        "titre": "Le present perfect",
        "matiere": "anglais",
        "niveau_scolaire": "3e",
        "contenu": (
            "## La formation\n\n"
            "Le present perfect se forme avec l'auxiliaire have (ou has à la "
            "troisième personne du singulier) suivi du participe passé du verbe. "
            "Exemple : I have visited London.\n\n"
            "## Les emplois\n\n"
            "- Une action passée qui a un lien avec le présent : I have lost my "
            "keys.\n"
            "- Une expérience, sans date précise : She has never seen the sea.\n"
            "- Avec since et for, pour une action qui dure encore : We have lived "
            "here for ten years.\n\n"
            "## À retenir\n\n"
            "On n'utilise pas le present perfect avec une date précise du passé "
            "(yesterday, in 2010) : on emploie alors le prétérit."
        ),
    },
]

QUIZ = [
    {
        "lecon": "revolution",
        "titre": "Quiz — La Révolution française",
        "difficulte": "moyen",
        "valide": True,
        "questions": [
            _qcm(
                "Quel jour les Parisiens prennent-ils la Bastille ?",
                [
                    "Le 5 mai 1789",
                    "Le 20 juin 1789",
                    "Le 14 juillet 1789",
                    "Le 4 août 1789",
                ],
                2,
                "La Bastille, symbole du pouvoir royal, est prise le 14 juillet 1789.",
            ),
            _vrai_faux(
                "Les privilèges sont abolis dans la nuit du 4 août 1789.",
                True,
                "L'Assemblée abolit les privilèges dans la nuit du 4 août 1789.",
            ),
            _qcm(
                "Quel texte l'Assemblée adopte-t-elle le 26 août 1789 ?",
                [
                    "Le serment du Jeu de paume",
                    "La Déclaration des droits de l'homme et du citoyen",
                    "La Constitution de la Ve République",
                    "Le Code civil",
                ],
                1,
                "La Déclaration des droits de l'homme et du citoyen est adoptée "
                "le 26 août 1789.",
            ),
            _vrai_faux(
                "La Première République est proclamée en 1789.",
                False,
                "Elle est proclamée en septembre 1792, après l'abolition de la "
                "monarchie.",
            ),
            _ouverte(
                "Citez une cause de la Révolution française.",
                "La crise financière du royaume ou les idées des Lumières.",
                "La leçon cite la crise financière de l'État et les idées des "
                "philosophes des Lumières.",
            ),
        ],
    },
    {
        "lecon": "volcans",
        "titre": "Quiz — Les volcans",
        "difficulte": "facile",
        "valide": False,
        "questions": [
            _qcm(
                "Comment appelle-t-on le magma lorsqu'il arrive à la surface ?",
                ["La cendre", "La lave", "Le dôme", "Le basalte"],
                1,
                "En arrivant à la surface, le magma prend le nom de lave.",
            ),
            _vrai_faux(
                "Les éruptions effusives produisent des coulées de lave fluide.",
                True,
                "C'est le cas au Piton de la Fournaise, à La Réunion.",
            ),
            _qcm(
                "Où se trouvent la plupart des volcans ?",
                [
                    "Au centre des continents",
                    "À la limite des plaques tectoniques",
                    "Uniquement sur les îles",
                    "Près des pôles",
                ],
                1,
                "La plupart des volcans se trouvent à la limite des plaques "
                "tectoniques.",
            ),
            _ouverte(
                "Citez un volcan parmi les plus actifs d'Europe.",
                "L'Etna, en Sicile.",
                "La leçon présente l'Etna comme l'un des volcans les plus actifs "
                "d'Europe.",
            ),
        ],
    },
    {
        "lecon": "pythagore",
        "titre": "Quiz — Le théorème de Pythagore",
        "difficulte": "moyen",
        "valide": False,
        "questions": [
            _qcm(
                "Comment s'appelle le côté opposé à l'angle droit ?",
                ["La médiane", "La hauteur", "L'hypoténuse", "La bissectrice"],
                2,
                "L'hypoténuse est le côté opposé à l'angle droit, le plus long du "
                "triangle.",
            ),
            _qcm(
                "ABC est rectangle en A, AB = 3 cm et AC = 4 cm. Combien mesure BC ?",
                ["5 cm", "7 cm", "12 cm", "25 cm"],
                0,
                "BC² = 3² + 4² = 25, donc BC = 5 cm.",
            ),
            _vrai_faux(
                "La réciproque du théorème permet de prouver qu'un triangle est "
                "rectangle.",
                True,
                "Si le carré du plus long côté est égal à la somme des carrés des "
                "deux autres, le triangle est rectangle.",
            ),
        ],
    },
]
