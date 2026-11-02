"""Tests de la page de génération d'un quiz (tâche 29, maquettes 07 et 07b).

L'appel au microservice IA est remplacé par un faux : aucun modèle n'est lancé.
"""

from unittest import mock

import requests
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon

from .repository import QuizRepository
from .tests import questions_valides


def reponse_ia(statut=200, questions=None):
    """Fausse réponse du microservice IA."""
    reponse = mock.Mock()
    reponse.status_code = statut
    reponse.json.return_value = {
        "questions": questions if questions is not None else questions_valides()
    }
    return reponse


class QuizGenerationTests(TestCase):
    """Génération : formulaire, propriétaire, erreurs de l'IA, panne MongoDB."""

    def setUp(self):
        """Deux enseignants, une leçon chacun, un dépôt vidé après chaque test."""
        self.anne = creer_enseignant()
        self.paul = creer_enseignant("paul.martin@eduquizai.local", prenom="Paul")
        self.lecon_anne = creer_lecon(self.anne, titre="Les fractions")
        self.lecon_paul = creer_lecon(self.paul, titre="La photosynthèse")
        self.repository = QuizRepository()
        self.addCleanup(self.repository.collection.delete_many, {})
        cache.clear()
        self.addCleanup(cache.clear)
        self.client.force_login(self.anne)
        self.url = reverse("quiz:generer")

    def donnees(self, **champs):
        """Données valides du formulaire ; chaque champ peut être remplacé."""
        valeurs = {
            "lecon": self.lecon_anne.pk,
            "titre": "Quiz sur les fractions",
            "difficulte": "moyen",
            "types": ["qcm", "vrai_faux"],
            "nombre": 5,
        }
        valeurs.update(champs)
        return valeurs

    def generer(self, donnees=None, **appel):
        """Envoie le formulaire avec un faux microservice ; retourne (réponse, faux)."""
        appel.setdefault("return_value", reponse_ia())
        with mock.patch("quiz.client_ia.requests.post", **appel) as faux:
            reponse = self.client.post(self.url, donnees or self.donnees())
        return reponse, faux

    def quiz_enregistres(self):
        """Quiz d'Anne présents dans MongoDB."""
        return self.repository.lister(self.anne.pk)

    def test_page_reservee_aux_enseignants_connectes(self):
        """Sans connexion, la page redirige vers la connexion."""
        self.client.logout()
        reponse = self.client.get(self.url)
        self.assertRedirects(
            reponse,
            f"{reverse('comptes:connexion')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_affichage_du_formulaire(self):
        """Le formulaire affiche les valeurs par défaut et les leçons."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Les fractions")
        self.assertContains(reponse, 'value="10"')
        self.assertContains(
            reponse, 'id="diff-moyen" name="difficulte" value="moyen" checked'
        )

    def test_boutons_distincts_et_annulation(self):
        """Le bouton d'envoi a son propre libellé ; l'attente propose d'annuler."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Lancer la génération")
        self.assertNotContains(reponse, "✦ Générer le quiz")
        self.assertContains(reponse, 'id="bouton-annuler"')

    def test_lecons_des_autres_absentes(self):
        """Faille IDOR : les leçons de Paul ne sont pas proposées à Anne."""
        self.assertNotContains(self.client.get(self.url), "La photosynthèse")

    def test_lecon_preselectionnee_par_l_adresse(self):
        """?lecon=<id> présélectionne la leçon et propose un titre."""
        reponse = self.client.get(f"{self.url}?lecon={self.lecon_anne.pk}")
        self.assertContains(reponse, f'value="{self.lecon_anne.pk}" selected')
        self.assertContains(reponse, "Quiz — Les fractions")

    def test_lecon_d_un_autre_non_preselectionnee(self):
        """?lecon= avec la leçon d'un autre enseignant est ignoré."""
        reponse = self.client.get(f"{self.url}?lecon={self.lecon_paul.pk}")
        self.assertNotContains(reponse, "Quiz — La photosynthèse")
        self.assertNotContains(reponse, "selected")

    def test_generation_reussie_cree_un_brouillon(self):
        """Une génération réussie enregistre un brouillon lié à la leçon."""
        reponse, _ = self.generer()
        self.assertRedirects(
            reponse, reverse("quiz:liste"), fetch_redirect_response=False
        )
        quiz = self.quiz_enregistres()
        self.assertEqual(len(quiz), 1)
        self.assertEqual(quiz[0]["statut"], "brouillon")
        self.assertEqual(quiz[0]["titre"], "Quiz sur les fractions")
        self.assertEqual(quiz[0]["id_lecon"], self.lecon_anne.pk)
        self.assertEqual(quiz[0]["id_utilisateur"], self.anne.pk)
        self.assertEqual(len(quiz[0]["questions"]), len(questions_valides()))

    def test_message_de_succes(self):
        """Le message de succès invite à relire le brouillon."""
        reponse, _ = self.generer()
        suivi = self.client.get(reponse["Location"])
        self.assertContains(suivi, "généré en brouillon")

    def test_appel_authentifie_avec_les_bons_parametres(self):
        """Le microservice reçoit le jeton, le texte de la leçon et les réglages."""
        _, faux = self.generer()
        faux.assert_called_once()
        _, appel = faux.call_args
        self.assertTrue(appel["headers"]["Authorization"].startswith("Bearer "))
        self.assertEqual(appel["json"]["contenu"], self.lecon_anne.contenu)
        self.assertEqual(appel["json"]["difficulte"], "moyen")
        self.assertEqual(appel["json"]["types"], ["qcm", "vrai_faux"])
        self.assertEqual(appel["json"]["nombre"], 5)

    def test_types_envoyes_dans_l_ordre_de_l_interface(self):
        """L'ordre des types ne dépend pas de celui de la requête."""
        _, faux = self.generer(self.donnees(types=["ouverte", "qcm"]))
        self.assertEqual(faux.call_args.kwargs["json"]["types"], ["qcm", "ouverte"])

    def test_lecon_d_un_autre_refusee(self):
        """Faille IDOR : générer sur la leçon de Paul est refusé sans appel à l'IA."""
        reponse, faux = self.generer(self.donnees(lecon=self.lecon_paul.pk))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Cette leçon n&#x27;existe pas.")
        faux.assert_not_called()
        self.assertEqual(self.quiz_enregistres(), [])

    def test_donnees_invalides_sans_appel_a_l_ia(self):
        """Chaque réglage invalide est refusé, sans appel au microservice."""
        cas = {
            "lecon": "",
            "titre": "   ",
            "difficulte": "impossible",
            "types": [],
            "nombre": 2,
        }
        for champ, valeur in cas.items():
            with self.subTest(champ=champ):
                reponse, faux = self.generer(self.donnees(**{champ: valeur}))
                self.assertEqual(reponse.status_code, 200)
                self.assertIn(champ, reponse.context["form"].errors)
                faux.assert_not_called()
        self.assertEqual(self.quiz_enregistres(), [])

    def test_nombre_hors_limites(self):
        """Le nombre de questions est limité de 3 à 20."""
        for nombre in (2, 21, "abc"):
            with self.subTest(nombre=nombre):
                reponse, faux = self.generer(self.donnees(nombre=nombre))
                self.assertIn("nombre", reponse.context["form"].errors)
                faux.assert_not_called()

    def test_erreurs_du_microservice(self):
        """Chaque erreur de l'IA affiche son message et conserve la saisie."""
        for statut, message in {
            400: "réglages de génération sont invalides",
            502: "pas produit de quiz valide",
            503: "indisponible pour le moment",
            504: "pas répondu à temps",
        }.items():
            with self.subTest(statut=statut):
                reponse, _ = self.generer(return_value=reponse_ia(statut))
                self.assertEqual(reponse.status_code, 200)
                self.assertContains(reponse, message)
                self.assertContains(reponse, "Quiz sur les fractions")
        self.assertEqual(self.quiz_enregistres(), [])

    def test_microservice_injoignable(self):
        """Sans réponse du microservice, le message est clair et rien n'est créé."""
        reponse, _ = self.generer(side_effect=requests.ConnectionError())
        self.assertContains(reponse, "indisponible pour le moment")
        self.assertEqual(self.quiz_enregistres(), [])

    def test_delai_depasse(self):
        """Un délai dépassé affiche le message dédié."""
        reponse, _ = self.generer(side_effect=requests.Timeout())
        self.assertContains(reponse, "pas répondu à temps")
        self.assertEqual(self.quiz_enregistres(), [])

    def test_erreurs_rares_du_microservice(self):
        """Autre erreur réseau, réponse illisible ou vide : message générique."""
        illisible = reponse_ia()
        illisible.json.side_effect = ValueError("pas du JSON")
        cas = {
            "autre erreur réseau": {"side_effect": requests.RequestException()},
            "réponse illisible": {"return_value": illisible},
            "aucune question": {"return_value": reponse_ia(questions=[])},
        }
        for nom, appel in cas.items():
            with self.subTest(cas=nom):
                with self.assertLogs("quiz.client_ia", level="WARNING"):
                    reponse, _ = self.generer(**appel)
                self.assertEqual(reponse.status_code, 200)
                self.assertContains(reponse, "La génération a échoué")
        self.assertEqual(self.quiz_enregistres(), [])

    def test_quiz_invalide_de_l_ia_refuse(self):
        """Des questions mal formées ne sont jamais enregistrées."""
        mauvaises = [{"type_question": "qcm", "texte": "", "choix": []}]
        with self.assertLogs("quiz.views", level="ERROR"):
            reponse, _ = self.generer(return_value=reponse_ia(questions=mauvaises))
        self.assertContains(reponse, "pas utilisable")
        self.assertEqual(self.quiz_enregistres(), [])

    def test_mongodb_indisponible(self):
        """Si MongoDB tombe, la page répond avec un message, pas une erreur 500."""
        with (
            mock.patch.object(
                QuizRepository, "creer", side_effect=PyMongoError("hors service")
            ),
            self.assertLogs("quiz.views", level="ERROR"),
        ):
            reponse, _ = self.generer()
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "n&#x27;a pas pu être enregistré")

    def test_encart_ia_locale(self):
        """L'encart et l'attente s'adaptent au fournisseur (Ollama local ou Mistral)."""
        with mock.patch.dict("quiz.views.settings.IA", {"FOURNISSEUR": "ollama"}):
            reponse = self.client.get(self.url)
        self.assertContains(reponse, "IA tourne en local")
        self.assertContains(reponse, "une à deux minutes")
        with mock.patch.dict("quiz.views.settings.IA", {"FOURNISSEUR": "mistral"}):
            reponse = self.client.get(self.url)
        self.assertNotContains(reponse, "IA tourne en local")
        self.assertNotContains(reponse, "une à deux minutes")
        self.assertContains(reponse, "API Mistral")
        self.assertContains(reponse, "quelques secondes")

    def test_apercu_sans_injection(self):
        """Le titre d'une leçon est échappé dans la page (protection XSS)."""
        creer_lecon(self.anne, titre="<script>alert(1)</script>")
        reponse = self.client.get(self.url)
        self.assertNotContains(reponse, "<script>alert(1)</script>")

    def test_generation_annulee_non_enregistree(self):
        """Une génération annulée pendant l'attente ne crée aucun quiz."""
        self.client.post(
            reverse("quiz:annuler_generation"), {"id_generation": "abc-123"}
        )
        reponse, faux = self.generer(self.donnees(id_generation="abc-123"))
        faux.assert_called_once()
        self.assertContains(reponse, "aucun quiz enregistré")
        self.assertEqual(self.quiz_enregistres(), [])

    def test_annulation_d_un_autre_enseignant_sans_effet(self):
        """Faille IDOR : l'annulation de Paul ne touche pas la génération d'Anne."""
        self.client.force_login(self.paul)
        self.client.post(
            reverse("quiz:annuler_generation"), {"id_generation": "abc-123"}
        )
        self.client.force_login(self.anne)
        self.generer(self.donnees(id_generation="abc-123"))
        self.assertEqual(len(self.quiz_enregistres()), 1)

    def test_annulation_reservee_aux_connectes_en_post(self):
        """L'annulation exige la connexion et la méthode POST."""
        url = reverse("quiz:annuler_generation")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(url, {"id_generation": "x"}).status_code, 302)

    def test_annulation_identifiant_invalide(self):
        """Un identifiant absent ou mal formé est refusé."""
        url = reverse("quiz:annuler_generation")
        for valeur in ("", "a b", "<script>"):
            with self.subTest(valeur=valeur):
                reponse = self.client.post(url, {"id_generation": valeur})
                self.assertEqual(reponse.status_code, 400)

    def test_identifiant_de_generation_invalide_refuse(self):
        """Un identifiant de génération mal formé bloque la génération."""
        reponse, faux = self.generer(self.donnees(id_generation="<x>"))
        self.assertIn("id_generation", reponse.context["form"].errors)
        faux.assert_not_called()
