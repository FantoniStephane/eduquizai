from datetime import timedelta
from unittest import mock, skipUnless

from django.db import IntegrityError, connection, transaction
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from pymongo.errors import PyMongoError

from comptes.models import Utilisateur
from quiz.repository import QuizRepository
from quiz.tests import creer_quiz

from .conversion import (
    html_vers_markdown,
    markdown_vers_html,
    markdown_vers_html_editeur,
)
from .forms import CONTENU_MAX, LeconForm
from .models import Lecon

MOT_DE_PASSE = "Tableau-Noir-2026"


def creer_enseignant(email="anne.durand@eduquizai.local", prenom="Anne"):
    """Crée un enseignant de test."""
    return Utilisateur.objects.create_user(
        email, MOT_DE_PASSE, nom="Durand", prenom=prenom
    )


def creer_lecon(utilisateur, **champs):
    """Crée une leçon valide ; chaque champ peut être remplacé."""
    valeurs = {
        "titre": "La Révolution française",
        "matiere": "histoire",
        "niveau_scolaire": "4e",
        "contenu": "## Les causes\n\n- une crise financière",
    }
    valeurs.update(champs)
    return Lecon.objects.create(utilisateur=utilisateur, **valeurs)


class LeconModeleTests(TestCase):
    """Modèle Lecon : propriétaire, tri et intégrité en base (US3)."""

    def setUp(self):
        """Crée une enseignante."""
        self.anne = creer_enseignant()

    def test_lecon_rattachee_a_son_enseignant(self):
        """Une leçon appartient à l'enseignant qui l'a créée."""
        lecon = creer_lecon(self.anne)
        self.assertEqual(lecon.utilisateur, self.anne)
        self.assertEqual(list(self.anne.lecons.all()), [lecon])
        self.assertEqual(str(lecon), "La Révolution française")

    def test_lecons_triees_de_la_plus_recente_a_la_plus_ancienne(self):
        """Les leçons sont triées par date de modification décroissante."""
        ancienne = creer_lecon(self.anne, titre="Ancienne")
        recente = creer_lecon(self.anne, titre="Récente")
        Lecon.objects.filter(pk=ancienne.pk).update(
            date_modification=timezone.now() - timedelta(days=3)
        )
        self.assertEqual(list(Lecon.objects.all()), [recente, ancienne])

    def test_matiere_inconnue_refusee_par_la_base(self):
        """La contrainte CHECK refuse une matière hors de la liste."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            creer_lecon(self.anne, matiere="physique")

    def test_niveau_inconnu_refuse_par_la_base(self):
        """La contrainte CHECK refuse un niveau hors du collège."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            creer_lecon(self.anne, niveau_scolaire="2nde")

    def test_supprimer_un_enseignant_supprime_ses_lecons(self):
        """Suppression en cascade : pas de leçon orpheline (droit à l'effacement)."""
        creer_lecon(self.anne)
        self.anne.delete()
        self.assertFalse(Lecon.objects.exists())


class ConversionTests(SimpleTestCase):
    """Markdown, format de référence du contenu, et nettoyage du HTML (XSS)."""

    HTML_EDITEUR = (
        "<div>Introduction.</div><h1>Les causes</h1>"
        "<ul><li>une crise ;</li><li>des inégalités ;</li></ul>"
        "<div>Le 14&nbsp;juillet, <strong>la Bastille</strong> <em>tombe</em>.</div>"
    )
    MARKDOWN = (
        "Introduction.\n\n## Les causes\n\n- une crise ;\n- des inégalités ;"
        "\n\nLe 14 juillet, **la Bastille** *tombe*."
    )

    def test_html_de_l_editeur_converti_en_markdown(self):
        """Titre, puces, gras et italique de l'éditeur deviennent du Markdown."""
        self.assertEqual(html_vers_markdown(self.HTML_EDITEUR), self.MARKDOWN)

    def test_aller_retour_sans_perte(self):
        """Markdown → éditeur → Markdown : le contenu enregistré ne change pas."""
        html = markdown_vers_html_editeur(self.MARKDOWN)
        self.assertEqual(html_vers_markdown(html), self.MARKDOWN)

    def test_editeur_recoit_des_titres_h1(self):
        """Trix ne connaît qu'un niveau de titre : les « ## » deviennent des h1."""
        html = markdown_vers_html_editeur("## Les causes")
        self.assertEqual(html, "<h1>Les causes</h1>")

    def test_affichage_sans_second_h1(self):
        """À l'affichage, « # titre » devient un h2 (h1 réservé au titre de page)."""
        self.assertEqual(markdown_vers_html("# Titre"), "<h2>Titre</h2>")

    def test_script_et_image_piegee_supprimes_a_l_enregistrement(self):
        """Le HTML dangereux est retiré avant la conversion en Markdown."""
        markdown = html_vers_markdown(
            '<div>Avant<script>alert(1)</script><img src=x onerror="alert(1)">'
            "Après</div>"
        )
        self.assertEqual(markdown, "AvantAprès")

    def test_lien_javascript_neutralise(self):
        """Un lien javascript: perd son adresse ; un lien https est conservé."""
        self.assertNotIn(
            "javascript", html_vers_markdown('<a href="javascript:alert(1)">clic</a>')
        )
        html = markdown_vers_html("[site](https://eduscol.education.fr)")
        self.assertIn('href="https://eduscol.education.fr"', html)
        self.assertIn('rel="noopener noreferrer"', html)

    def test_html_du_markdown_nettoye_a_l_affichage(self):
        """Du HTML glissé dans le Markdown est filtré à l'affichage."""
        html = markdown_vers_html(
            'Texte <script>alert(1)</script> <p onclick="x()">clic</p>'
        )
        self.assertNotIn("<script", html)
        self.assertNotIn("onclick", html)

    def test_asterisque_tapee_par_l_enseignant_conservee(self):
        """Un « * » tapé dans le texte n'est pas pris pour de l'italique."""
        markdown = html_vers_markdown("<div>Note : 5 * 3 = 15</div>")
        self.assertEqual(markdown_vers_html(markdown), "<p>Note : 5 * 3 = 15</p>")


class LeconFormTests(TestCase):
    """Formulaire de leçon : champs obligatoires, limites, conversion (US3)."""

    def donnees(self, **champs):
        """Données valides du formulaire ; chaque champ peut être remplacé."""
        valeurs = {
            "titre": "La Révolution française",
            "matiere": "histoire",
            "niveau_scolaire": "4e",
            "contenu": "<div>La <strong>Bastille</strong> est prise.</div>",
        }
        valeurs.update(champs)
        return valeurs

    def test_formulaire_valide_enregistre_du_markdown(self):
        """Le HTML de l'éditeur est enregistré en Markdown."""
        formulaire = LeconForm(self.donnees())
        self.assertTrue(formulaire.is_valid())
        self.assertEqual(
            formulaire.cleaned_data["contenu"], "La **Bastille** est prise."
        )

    def test_champs_obligatoires(self):
        """Titre, matière, niveau et contenu vides : quatre erreurs en français."""
        formulaire = LeconForm(
            self.donnees(titre="", matiere="", niveau_scolaire="", contenu="")
        )
        self.assertFalse(formulaire.is_valid())
        self.assertEqual(formulaire.errors["titre"], ["Le titre est obligatoire."])
        self.assertEqual(formulaire.errors["matiere"], ["Choisissez une matière."])
        self.assertEqual(
            formulaire.errors["niveau_scolaire"], ["Choisissez un niveau scolaire."]
        )
        self.assertEqual(
            formulaire.errors["contenu"], ["Le contenu de la leçon est obligatoire."]
        )

    def test_titre_fait_uniquement_d_espaces_refuse(self):
        """Un titre composé d'espaces est considéré comme vide."""
        self.assertIn("titre", LeconForm(self.donnees(titre="   ")).errors)

    def test_contenu_vide_une_fois_nettoye_refuse(self):
        """Un contenu réduit à rien après nettoyage (script seul) est refusé."""
        formulaire = LeconForm(self.donnees(contenu="<script>alert(1)</script>"))
        self.assertIn("contenu", formulaire.errors)

    def test_titre_de_100_caracteres_accepte(self):
        """Cas limite : exactement 100 caractères, la taille de la colonne."""
        self.assertTrue(LeconForm(self.donnees(titre="x" * 100)).is_valid())

    def test_titre_de_plus_de_100_caracteres_refuse(self):
        """Le titre est limité à 100 caractères, comme la colonne en base."""
        self.assertIn("titre", LeconForm(self.donnees(titre="x" * 101)).errors)

    def test_contenu_limite_a_20000_caracteres(self):
        """20 000 caractères passent, 20 001 sont refusés."""
        self.assertTrue(LeconForm(self.donnees(contenu="x" * CONTENU_MAX)).is_valid())
        formulaire = LeconForm(self.donnees(contenu="x" * (CONTENU_MAX + 1)))
        self.assertIn("contenu", formulaire.errors)

    def test_matiere_inconnue_refusee(self):
        """Une matière hors de la liste est refusée dès le formulaire."""
        self.assertIn("matiere", LeconForm(self.donnees(matiere="physique")).errors)

    def test_texte_saisi_sans_javascript_garde_tel_quel(self):
        """Sans éditeur (JavaScript désactivé), le texte simple est conservé."""
        formulaire = LeconForm(self.donnees(contenu="Ligne 1\n\n## Titre"))
        self.assertTrue(formulaire.is_valid())
        self.assertEqual(formulaire.cleaned_data["contenu"], "Ligne 1\n\n## Titre")

    def test_proprietaire_absent_du_formulaire(self):
        """Le champ utilisateur n'est pas modifiable par le formulaire."""
        self.assertNotIn("utilisateur", LeconForm().fields)

    def test_modification_recharge_le_contenu_mis_en_forme(self):
        """En modification, le Markdown enregistré est rechargé en HTML."""
        lecon = creer_lecon(creer_enseignant(), contenu="## Les causes")
        formulaire = LeconForm(instance=lecon)
        self.assertEqual(formulaire.initial["contenu"], "<h1>Les causes</h1>")


class LeconVuesTests(TestCase):
    """Pages des leçons : parcours complet et contrôle d'accès (US3, US7, US12)."""

    def setUp(self):
        """Anne est connectée ; Paul, un collègue, possède aussi une leçon."""
        self.anne = creer_enseignant()
        self.paul = creer_enseignant("paul.martin@eduquizai.local", "Paul")
        self.lecon = creer_lecon(self.anne)
        self.lecon_de_paul = creer_lecon(self.paul, titre="Leçon de Paul")
        self.client.force_login(self.anne)

    def donnees(self, **champs):
        """Données valides du formulaire de leçon."""
        valeurs = {
            "titre": "Les volcans",
            "matiere": "svt",
            "niveau_scolaire": "5e",
            "contenu": "<div>Un volcan est une ouverture.</div>",
        }
        valeurs.update(champs)
        return valeurs

    def test_pages_reservees_aux_utilisateurs_connectes(self):
        """Un visiteur non connecté est renvoyé vers la connexion (5 pages)."""
        self.client.logout()
        pk = self.lecon.pk
        for nom, args in [
            ("liste", []),
            ("creer", []),
            ("detail", [pk]),
            ("modifier", [pk]),
            ("supprimer", [pk]),
        ]:
            with self.subTest(page=nom):
                url = reverse(f"lecons:{nom}", args=args)
                reponse = self.client.get(url)
                self.assertRedirects(
                    reponse, f"{reverse('comptes:connexion')}?next={url}"
                )

    def test_creation_rattache_la_lecon_a_l_utilisateur_connecte(self):
        """Créer une leçon : Anne en est propriétaire, même si Paul est envoyé."""
        reponse = self.client.post(
            reverse("lecons:creer"), self.donnees(utilisateur=self.paul.pk)
        )
        self.assertRedirects(reponse, reverse("lecons:liste"))
        lecon = Lecon.objects.get(titre="Les volcans")
        self.assertEqual(lecon.utilisateur, self.anne)
        self.assertEqual(lecon.contenu, "Un volcan est une ouverture.")

    def test_creation_avec_erreur_reaffiche_le_formulaire(self):
        """Un titre vide réaffiche le formulaire avec le message d'erreur."""
        reponse = self.client.post(reverse("lecons:creer"), self.donnees(titre=""))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Le titre est obligatoire.")
        self.assertFalse(Lecon.objects.filter(titre="").exists())

    def test_liste_ne_montre_que_mes_lecons(self):
        """La liste d'Anne ne contient jamais la leçon de Paul."""
        reponse = self.client.get(reverse("lecons:liste"))
        self.assertContains(reponse, "La Révolution française")
        self.assertNotContains(reponse, "Leçon de Paul")

    def test_liste_recherche_et_filtres(self):
        """Recherche dans le titre (sans tenir compte des majuscules) et filtres."""
        creer_lecon(self.anne, titre="Les fractions", matiere="mathematiques")
        url = reverse("lecons:liste")
        reponse = self.client.get(url, {"q": "révolution"})
        self.assertEqual(list(reponse.context["lecons"]), [self.lecon])
        reponse = self.client.get(url, {"matiere": "mathematiques", "niveau": "4e"})
        self.assertEqual(
            [lecon.titre for lecon in reponse.context["lecons"]], ["Les fractions"]
        )

    @skipUnless(connection.vendor == "postgresql", "comparaison Unicode de PostgreSQL")
    def test_recherche_insensible_aux_majuscules_accentuees(self):
        """« RÉVOLUTION » trouve « Révolution » (PostgreSQL, comme en production)."""
        reponse = self.client.get(reverse("lecons:liste"), {"q": "RÉVOLUTION"})
        self.assertEqual(list(reponse.context["lecons"]), [self.lecon])

    def test_page_de_liste_inexistante_donne_404(self):
        """Un numéro de page trop grand ou invalide donne une 404, pas une erreur."""
        for page in ("99", "abc"):
            with self.subTest(page=page):
                reponse = self.client.get(reverse("lecons:liste"), {"page": page})
                self.assertEqual(reponse.status_code, 404)

    def test_liste_filtre_inconnu_ignore(self):
        """Une valeur de filtre inventée est ignorée : toutes mes leçons."""
        reponse = self.client.get(reverse("lecons:liste"), {"matiere": "physique"})
        self.assertEqual(reponse.context["paginator"].count, 1)

    def test_liste_paginee_par_six(self):
        """Six leçons par page ; les filtres restent dans les liens de page."""
        for numero in range(7):
            creer_lecon(self.anne, titre=f"Leçon {numero}")
        reponse = self.client.get(reverse("lecons:liste"), {"q": "leçon"})
        self.assertEqual(len(reponse.context["lecons"]), 6)
        self.assertContains(reponse, "?q=le%C3%A7on&amp;page=2")

    def test_detail_affiche_le_contenu_mis_en_forme(self):
        """Le Markdown enregistré est affiché en HTML."""
        reponse = self.client.get(reverse("lecons:detail", args=[self.lecon.pk]))
        # Titres du contenu en h3, sous la section « Contenu de la leçon » (h2)
        self.assertContains(reponse, "<h3>Les causes</h3>", html=True)

    def test_modification_de_ma_lecon(self):
        """Anne modifie sa leçon et revient au détail avec un message."""
        url = reverse("lecons:modifier", args=[self.lecon.pk])
        reponse = self.client.post(url, self.donnees(), follow=True)
        self.assertRedirects(reponse, reverse("lecons:detail", args=[self.lecon.pk]))
        self.assertContains(reponse, "Les modifications ont été enregistrées.")
        self.lecon.refresh_from_db()
        self.assertEqual(self.lecon.titre, "Les volcans")
        self.assertEqual(self.lecon.utilisateur, self.anne)

    def test_suppression_de_ma_lecon(self):
        """La confirmation (GET) ne supprime rien ; la validation (POST) supprime."""
        url = reverse("lecons:supprimer", args=[self.lecon.pk])
        self.assertContains(self.client.get(url), "Supprimer définitivement")
        self.assertTrue(Lecon.objects.filter(pk=self.lecon.pk).exists())
        reponse = self.client.post(url, follow=True)
        self.assertRedirects(reponse, reverse("lecons:liste"))
        self.assertContains(reponse, "a été supprimée.")
        self.assertFalse(Lecon.objects.filter(pk=self.lecon.pk).exists())

    def test_detail_liste_les_quiz_de_la_lecon(self):
        """Le détail liste les quiz de la leçon avec leur statut, pas ceux d'autrui."""
        repository = QuizRepository()
        self.addCleanup(repository.collection.delete_many, {})
        creer_quiz(
            repository,
            id_utilisateur=self.anne.pk,
            id_lecon=self.lecon.pk,
            titre="Quiz brouillon",
        )
        id_valide = creer_quiz(
            repository,
            id_utilisateur=self.anne.pk,
            id_lecon=self.lecon.pk,
            titre="Quiz relu",
        )
        repository.valider(id_valide, self.anne.pk)
        creer_quiz(
            repository,
            id_utilisateur=self.anne.pk,
            id_lecon=self.lecon.pk + 1000,
            titre="Quiz d'une autre leçon",
        )
        creer_quiz(
            repository,
            id_utilisateur=self.paul.pk,
            id_lecon=self.lecon.pk,
            titre="Quiz de Paul",
        )
        reponse = self.client.get(reverse("lecons:detail", args=[self.lecon.pk]))
        self.assertContains(reponse, "Quiz brouillon")
        self.assertContains(reponse, "Quiz relu")
        self.assertContains(reponse, reverse("quiz:detail", args=[id_valide]))
        self.assertContains(reponse, "3 questions")
        self.assertContains(reponse, "badge-valide")
        self.assertContains(reponse, "badge-brouillon")
        self.assertNotContains(reponse, "autre leçon")
        self.assertNotContains(reponse, "Quiz de Paul")
        self.assertNotContains(reponse, "Aucun quiz n")

    def test_liste_nombre_de_quiz_et_actions(self):
        """Colonne Quiz (sans les quiz d'autrui) et liens voir, modifier, supprimer."""
        repository = QuizRepository()
        self.addCleanup(repository.collection.delete_many, {})
        for _ in range(2):
            creer_quiz(repository, id_utilisateur=self.anne.pk, id_lecon=self.lecon.pk)
        creer_quiz(repository, id_utilisateur=self.paul.pk, id_lecon=self.lecon.pk)
        sans_quiz = creer_lecon(self.anne, titre="Les fractions")
        reponse = self.client.get(reverse("lecons:liste"))
        nombres = {lecon.pk: lecon.nb_quiz for lecon in reponse.context["lecons"]}
        self.assertEqual(nombres, {self.lecon.pk: 2, sans_quiz.pk: 0})
        for nom in ("detail", "modifier", "supprimer"):
            with self.subTest(action=nom):
                self.assertContains(
                    reponse, reverse(f"lecons:{nom}", args=[self.lecon.pk])
                )
        self.assertContains(reponse, "Supprimer la leçon La Révolution française")

    def test_liste_si_mongodb_ne_repond_pas(self):
        """Panne MongoDB : la liste s'affiche, la colonne Quiz indique « — »."""
        with mock.patch.object(
            QuizRepository, "compter_par_lecons", side_effect=PyMongoError
        ):
            reponse = self.client.get(reverse("lecons:liste"))
        self.assertEqual(reponse.status_code, 200)
        self.assertIsNone(reponse.context["lecons"][0].nb_quiz)
        self.assertContains(reponse, '<td data-l="Quiz">—</td>', html=True)

    def test_detail_sans_quiz(self):
        """Une leçon sans quiz affiche le message habituel."""
        reponse = self.client.get(reverse("lecons:detail", args=[self.lecon.pk]))
        self.assertContains(reponse, "Aucun quiz n")

    def test_detail_si_mongodb_ne_repond_pas(self):
        """Panne MongoDB : la leçon s'affiche, avec un message à la place des quiz."""
        url = reverse("lecons:detail", args=[self.lecon.pk])
        with mock.patch.object(QuizRepository, "lister", side_effect=PyMongoError):
            reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, self.lecon.titre)
        self.assertContains(reponse, "momentanément indisponibles")

    def test_suppression_bloquee_si_la_lecon_a_des_quiz(self):
        """Une leçon qui a servi à générer un quiz n'est pas supprimée."""
        repository = QuizRepository()
        self.addCleanup(repository.collection.delete_many, {})
        creer_quiz(repository, id_utilisateur=self.anne.pk, id_lecon=self.lecon.pk)
        url = reverse("lecons:supprimer", args=[self.lecon.pk])
        confirmation = self.client.get(url)
        self.assertContains(confirmation, "Impossible de supprimer la leçon")
        self.assertNotContains(confirmation, "Supprimer définitivement")
        reponse = self.client.post(url, follow=True)
        self.assertRedirects(reponse, reverse("lecons:detail", args=[self.lecon.pk]))
        self.assertContains(reponse, "supprimez-les avant de supprimer la leçon")
        self.assertTrue(Lecon.objects.filter(pk=self.lecon.pk).exists())

    def test_suppression_refusee_si_mongodb_ne_repond_pas(self):
        """Sans réponse de MongoDB, la leçon est conservée par précaution."""
        url = reverse("lecons:supprimer", args=[self.lecon.pk])
        with mock.patch.object(
            QuizRepository, "compter_par_lecon", side_effect=PyMongoError
        ):
            self.assertContains(self.client.get(url), "ne peuvent pas être vérifiés")
            reponse = self.client.post(url, follow=True)
        self.assertContains(reponse, "Réessayez plus tard.")
        self.assertTrue(Lecon.objects.filter(pk=self.lecon.pk).exists())

    def test_lecon_d_un_autre_enseignant_introuvable(self):
        """Faille IDOR : la leçon de Paul donne une 404, en lecture comme en envoi."""
        pk = self.lecon_de_paul.pk
        for nom in ("detail", "modifier", "supprimer"):
            with self.subTest(page=nom, methode="GET"):
                url = reverse(f"lecons:{nom}", args=[pk])
                self.assertEqual(self.client.get(url).status_code, 404)
        for nom in ("modifier", "supprimer"):
            with self.subTest(page=nom, methode="POST"):
                url = reverse(f"lecons:{nom}", args=[pk])
                reponse = self.client.post(url, self.donnees(titre="Piraté"))
                self.assertEqual(reponse.status_code, 404)
        self.lecon_de_paul.refresh_from_db()
        self.assertEqual(self.lecon_de_paul.titre, "Leçon de Paul")


class LeconCsrfTests(TestCase):
    """Protection CSRF : sans jeton, aucune modification n'est possible."""

    def test_envoi_sans_jeton_csrf_refuse(self):
        """Création, modification et suppression sans jeton : erreur 403."""
        anne = creer_enseignant()
        lecon = creer_lecon(anne)
        client = Client(enforce_csrf_checks=True)
        client.force_login(anne)
        for nom, args in [
            ("creer", []),
            ("modifier", [lecon.pk]),
            ("supprimer", [lecon.pk]),
        ]:
            with self.subTest(page=nom):
                url = reverse(f"lecons:{nom}", args=args)
                self.assertEqual(client.post(url, {}).status_code, 403)
        self.assertTrue(Lecon.objects.filter(pk=lecon.pk).exists())
