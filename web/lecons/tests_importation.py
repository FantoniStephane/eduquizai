"""Tests de l'import d'un fichier texte dans une leçon (tâche 32, maquette 04c)."""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from .forms import CONTENU_MAX
from .importation import (
    TAILLE_MAX,
    ImportInvalideError,
    extraire_texte,
)
from .tests import creer_enseignant

ESPACE_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
    'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
)
RELATIONS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
    'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)
STYLES = (
    f'<?xml version="1.0" encoding="UTF-8"?><w:styles {ESPACE_W}>'
    '<w:style w:type="paragraph" w:styleId="Titre1"><w:name w:val="heading 1"/>'
    "</w:style></w:styles>"
)
DOCUMENT = (
    f'<?xml version="1.0" encoding="UTF-8"?><w:document {ESPACE_W}><w:body>'
    "<w:p><w:r><w:t>Introduction de la leçon.</w:t></w:r></w:p>"
    '<w:p><w:pPr><w:pStyle w:val="Titre1"/></w:pPr>'
    "<w:r><w:t>Les causes</w:t></w:r></w:p>"
    "<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Important</w:t></w:r>"
    '<w:r><w:t xml:space="preserve"> et </w:t></w:r>'
    "<w:r><w:rPr><w:i/></w:rPr><w:t>nuancé</w:t></w:r></w:p>"
    "</w:body></w:document>"
)


def creer_docx(document=DOCUMENT, supplements=None):
    """Document Word minimal (titre, gras, italique), construit à la main."""
    contenu = io.BytesIO()
    with zipfile.ZipFile(contenu, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", TYPES)
        archive.writestr("_rels/.rels", RELATIONS)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", STYLES)
        for nom, octets in (supplements or {}).items():
            archive.writestr(nom, octets)
    return contenu.getvalue()


class ExtractionTests(SimpleTestCase):
    """Contrôles du fichier et conversion du texte."""

    def refuse(self, nom, octets):
        """Message d'erreur affiché pour un fichier refusé."""
        with self.assertRaises(ImportInvalideError) as cadre:
            extraire_texte(nom, octets)
        return str(cadre.exception)

    def test_docx_converti_en_markdown(self):
        """Titre, gras et italique d'un .docx sont gardés en Markdown."""
        texte = extraire_texte("cours.docx", creer_docx())
        self.assertIn("Introduction de la leçon.", texte)
        self.assertIn("## Les causes", texte)
        self.assertIn("**Important** et *nuancé*", texte)

    def test_txt_utf8_avec_bom_et_fins_de_ligne_windows(self):
        """Un .txt UTF-8 (même avec BOM et retours Windows) est lu correctement."""
        octets = "Été\r\n\r\nSuite".encode("utf-8-sig")
        self.assertEqual(extraire_texte("a.TXT", octets), "Été\n\nSuite")

    def test_txt_encodage_windows(self):
        """Un .txt enregistré en ANSI (Bloc-notes) est lu aussi."""
        self.assertEqual(
            extraire_texte("a.txt", "À l'école".encode("cp1252")), "À l'école"
        )

    def test_extension_refusee(self):
        """Seuls .txt et .docx sont acceptés, quel que soit le contenu."""
        for nom in ("a.pdf", "a.doc", "a.docm", "a.exe", "a.txt.exe", "sans_extension"):
            with self.subTest(nom):
                self.assertIn("Format non accepté", self.refuse(nom, b"texte"))

    def test_fichier_vide_ou_sans_texte(self):
        """Un fichier vide ou fait d'espaces est refusé."""
        self.assertIn("vide", self.refuse("a.txt", b""))
        self.assertIn("aucun texte", self.refuse("a.txt", b"  \n  "))

    def test_taille_maximale(self):
        """Au-delà de 5 Mo, le fichier est refusé."""
        self.assertIn("5 Mo", self.refuse("a.txt", b"x" * (TAILLE_MAX + 1)))

    def test_texte_trop_long(self):
        """Plus de 20 000 caractères : refus clair, jamais de coupure silencieuse."""
        message = self.refuse("a.txt", ("x" * (CONTENU_MAX + 1)).encode())
        self.assertIn("20 000 caractères", message)
        self.assertEqual(
            len(extraire_texte("a.txt", ("x" * CONTENU_MAX).encode())), CONTENU_MAX
        )

    def test_txt_binaire_ou_archive_deguisee(self):
        """Un binaire ou un .docx renommé en .txt n'est pas lu comme du texte."""
        self.assertIn("pas un fichier texte", self.refuse("a.txt", b"ab\x00cd"))
        self.assertIn("pas un fichier texte", self.refuse("a.txt", creer_docx()))

    def test_encodage_inconnu(self):
        """Des octets illisibles dans les deux encodages sont refusés."""
        self.assertIn("encodage", self.refuse("a.txt", b"\x81\x8d\x8f"))

    def test_faux_docx(self):
        """Un texte ou une archive quelconque renommés en .docx sont refusés."""
        self.assertIn("pas un document Word", self.refuse("a.docx", b"du texte"))
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_:
            zip_.writestr("autre.txt", "x")
        self.assertIn("pas un document Word", self.refuse("a.docx", archive.getvalue()))

    def test_bombe_zip(self):
        """Un .docx très gros une fois décompressé est refusé."""
        octets = creer_docx(
            supplements={"word/media/gros.bin": b"0" * (51 * 1024 * 1024)}
        )
        self.assertLess(len(octets), TAILLE_MAX)
        self.assertIn("trop volumineux", self.refuse("a.docx", octets))

    def test_script_neutralise(self):
        """Une balise script tapée dans le texte est retirée à l'affichage."""
        from .conversion import markdown_vers_html_editeur

        texte = extraire_texte("a.txt", b"Bonjour <script>alert(1)</script> fin")
        self.assertNotIn("<script", markdown_vers_html_editeur(texte))


class VueImportTests(TestCase):
    """Point d'entrée /lecons/importer/ : connexion, CSRF, POST, réponses."""

    def setUp(self):
        """Une enseignante connectée."""
        self.anne = creer_enseignant()
        self.client.force_login(self.anne)
        self.url = reverse("lecons:importer")

    def envoyer(self, nom, octets, client=None):
        """Envoie un fichier au point d'entrée."""
        fichier = SimpleUploadedFile(nom, octets)
        return (client or self.client).post(self.url, {"fichier": fichier})

    def test_import_reussi(self):
        """Le texte du .docx revient en HTML pour l'éditeur."""
        reponse = self.envoyer("cours.docx", creer_docx())
        self.assertEqual(reponse.status_code, 200)
        html = reponse.json()["html"]
        self.assertIn("Les causes", html)
        self.assertIn("<strong>Important</strong>", html)

    def test_rien_n_est_enregistre(self):
        """L'import ne crée aucune leçon : l'enseignant doit enregistrer."""
        from .models import Lecon

        self.envoyer("a.txt", b"Un texte")
        self.assertEqual(Lecon.objects.count(), 0)

    def test_get_refuse(self):
        """Seul POST est accepté."""
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonyme_redirige_vers_la_connexion(self):
        """Sans connexion, rien n'est lu."""
        reponse = self.envoyer("a.txt", b"Un texte", client=Client())
        self.assertEqual(reponse.status_code, 302)

    def test_jeton_csrf_exige(self):
        """Sans jeton CSRF, l'import est refusé."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.anne)
        self.assertEqual(self.envoyer("a.txt", b"Un texte", client).status_code, 403)

    def test_aucun_fichier(self):
        """Envoi sans fichier : message clair, code 400."""
        reponse = self.client.post(self.url, {})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Choisissez un fichier", reponse.json()["erreur"])

    def test_fichiers_refuses(self):
        """Extension, contenu et taille incorrects : code 400 et message sobre."""
        cas = {
            "Format non accepté": ("a.pdf", b"texte"),
            "pas un document Word": ("a.docx", b"du texte"),
            "5 Mo": ("a.txt", b"x" * (TAILLE_MAX + 10)),
            "20 000 caractères": ("a.txt", b"x" * 20_001),
        }
        for attendu, (nom, octets) in cas.items():
            with self.subTest(attendu):
                reponse = self.envoyer(nom, octets)
                self.assertEqual(reponse.status_code, 400)
                self.assertIn(attendu, reponse.json()["erreur"])
                self.assertNotIn("Traceback", reponse.content.decode())

    def test_bouton_et_fenetre_dans_le_formulaire(self):
        """Le formulaire de leçon contient le bouton et la fenêtre d'import."""
        reponse = self.client.get(reverse("lecons:creer"))
        self.assertContains(reponse, "Importer un fichier texte")
        self.assertContains(reponse, 'accept=".txt,.docx"')
        self.assertContains(reponse, self.url)
