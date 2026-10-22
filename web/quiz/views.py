"""Vues des quiz : liste (tâche 28.5), puis génération et détail (tâches 29 à 31)."""

import logging
import re

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import FormView, ListView, TemplateView
from pymongo.errors import PyMongoError

from lecons.models import Lecon

from .client_ia import GenerationIAError, generer_questions
from .export import generer_pdf_eleve, nom_fichier
from .forms import (
    DIFFICULTES,
    TYPES_QUESTION,
    QuizAnnulationForm,
    QuizFiltreForm,
    QuizGenerationForm,
)
from .modification import lire_modification, vues_depuis_quiz
from .repository import QuizRepository
from .validation import QuizInvalideError

LONGUEUR_APERCU = 260
# Durée pendant laquelle une annulation est retenue (secondes) : plus que l'attente
# maximale d'une génération
DUREE_ANNULATION = 600


def _cle_annulation(id_utilisateur, id_generation):
    """Clé de cache d'une génération annulée (propre à l'enseignant)."""
    return f"generation-annulee:{id_utilisateur}:{id_generation}"


@require_POST
def annuler_generation(request):
    """Note qu'une génération est annulée : son quiz ne sera pas enregistré.

    L'enseignant ne peut annuler que ses propres générations : l'identifiant
    est rattaché à son compte dans la clé.
    """
    form = QuizAnnulationForm(request.POST)
    if not form.is_valid():
        return HttpResponse(status=400)
    cache.set(
        _cle_annulation(request.user.pk, form.cleaned_data["id_generation"]),
        True,
        DUREE_ANNULATION,
    )
    return HttpResponse(status=204)


logger = logging.getLogger(__name__)


class QuizListView(ListView):
    """Quiz de l'enseignant connecté (maquette 06).

    Recherche par titre, filtres leçon et statut, pagination par 6. Les quiz
    sont lus par le repository, qui filtre toujours sur le propriétaire.
    """

    template_name = "quiz/quiz_liste.html"
    context_object_name = "quiz_liste"
    paginate_by = 6

    def get_queryset(self):
        """Quiz de l'utilisateur connecté, puis les filtres valides.

        Si MongoDB ne répond pas, la liste est vide et la page l'explique.
        """
        self.mongo_indisponible = False
        self.filtres = QuizFiltreForm(self.request.GET, utilisateur=self.request.user)
        criteres = {}
        if self.filtres.is_valid():
            criteres = {
                "recherche": self.filtres.cleaned_data["q"],
                "id_lecon": self.filtres.cleaned_data["lecon"],
                "statut": self.filtres.cleaned_data["statut"],
            }
        try:
            return QuizRepository().lister(self.request.user.pk, **criteres)
        except PyMongoError:
            logger.exception("MongoDB indisponible : liste des quiz")
            self.mongo_indisponible = True
            return []

    def get_context_data(self, **kwargs):
        """Ajoute filtres, titres des leçons, nombre à valider et paramètres d'URL."""
        contexte = super().get_context_data(**kwargs)
        # Un seul accès à PostgreSQL pour les titres des leçons de la page
        identifiants = {quiz["id_lecon"] for quiz in contexte["quiz_liste"]}
        titres = dict(
            Lecon.objects.filter(
                utilisateur=self.request.user, pk__in=identifiants
            ).values_list("pk", "titre")
        )
        for quiz in contexte["quiz_liste"]:
            quiz["lecon_titre"] = titres.get(quiz["id_lecon"], "—")
        parametres = self.request.GET.copy()
        parametres.pop("page", None)
        contexte["filtres"] = self.filtres
        contexte["parametres"] = parametres.urlencode()
        contexte["filtre_actif"] = any(
            self.request.GET.get(nom) for nom in ("q", "lecon", "statut")
        )
        contexte["nb_a_valider"] = sum(
            1 for quiz in self.object_list if quiz["statut"] == "brouillon"
        )
        contexte["mongo_indisponible"] = self.mongo_indisponible
        return contexte


def _apercu(texte):
    """Début de la leçon en texte brut (sans les marques Markdown)."""
    brut = re.sub(r"[#*_`>\-]+", " ", texte or "")
    brut = re.sub(r"\s+", " ", brut).strip()
    if len(brut) > LONGUEUR_APERCU:
        return brut[:LONGUEUR_APERCU].rstrip() + "…"
    return brut


class QuizGenerationView(FormView):
    """Génération d'un quiz par l'IA à partir d'une leçon (maquettes 07 et 07b).

    L'appel au microservice IA est synchrone : la page affiche un écran d'attente
    pendant la requête. Le quiz créé est un brouillon, à relire avant validation.
    """

    template_name = "quiz/quiz_generation.html"
    form_class = QuizGenerationForm

    def get_form_kwargs(self):
        """Limite le choix des leçons à celles de l'enseignant connecté."""
        kwargs = super().get_form_kwargs()
        kwargs["utilisateur"] = self.request.user
        return kwargs

    def get_initial(self):
        """Présélectionne la leçon de ?lecon=<id> si elle appartient à l'enseignant."""
        initial = super().get_initial()
        identifiant = self.request.GET.get("lecon", "")
        if identifiant.isdigit():
            lecon = Lecon.objects.filter(
                utilisateur=self.request.user, pk=int(identifiant)
            ).first()
            if lecon:
                initial["lecon"] = lecon.pk
                initial["titre"] = f"Quiz — {lecon.titre}"[:100]
        return initial

    def form_valid(self, form):
        """Appelle l'IA, enregistre le quiz en brouillon puis revient à la liste."""
        donnees = form.cleaned_data
        lecon = donnees["lecon"]
        # Types dans l'ordre de l'interface, pas dans celui de la requête
        types = [code for code, _ in TYPES_QUESTION if code in donnees["types"]]
        try:
            questions = generer_questions(
                self.request.user.pk,
                lecon.contenu,
                donnees["difficulte"],
                types,
                donnees["nombre"],
            )
            if self._annulee(donnees["id_generation"]):
                return self._echec(form, "Génération annulée : aucun quiz enregistré.")
            QuizRepository().creer(
                id_utilisateur=self.request.user.pk,
                id_lecon=lecon.pk,
                titre=donnees["titre"],
                difficulte=donnees["difficulte"],
                questions=questions,
            )
        except GenerationIAError as erreur:
            return self._echec(form, str(erreur))
        except QuizInvalideError:
            logger.exception("Quiz généré refusé par la validation")
            return self._echec(
                form, "Le quiz généré n'est pas utilisable. Relancez la génération."
            )
        except PyMongoError:
            logger.exception("MongoDB indisponible : enregistrement du quiz")
            return self._echec(
                form,
                "Le quiz n'a pas pu être enregistré. Réessayez dans quelques instants.",
            )
        messages.success(
            self.request,
            f"Le quiz « {donnees['titre']} » a été généré en brouillon. "
            "Relisez-le avant de le valider.",
        )
        return redirect("quiz:liste")

    def _annulee(self, id_generation):
        """Vrai si l'enseignant a annulé cette génération pendant l'attente."""
        return bool(
            id_generation
            and cache.get(_cle_annulation(self.request.user.pk, id_generation))
        )

    def _echec(self, form, message):
        """Réaffiche le formulaire avec son contenu et le message d'erreur."""
        return self.render_to_response(
            self.get_context_data(form=form, erreur_ia=message)
        )

    def get_context_data(self, **kwargs):
        """Ajoute les leçons (pour l'aperçu), la sélection et l'état de l'IA."""
        contexte = super().get_context_data(**kwargs)
        form = contexte["form"]
        lecons = [
            {
                "pk": lecon.pk,
                "titre": lecon.titre,
                "matiere": lecon.get_matiere_display(),
                "niveau": lecon.get_niveau_scolaire_display(),
                "nb_car": len(lecon.contenu),
                "apercu": _apercu(lecon.contenu),
            }
            for lecon in form.fields["lecon"].queryset
        ]
        choisie = str(form["lecon"].value() or "")
        contexte["lecons"] = lecons
        contexte["selection"] = next(
            (lecon for lecon in lecons if str(lecon["pk"]) == choisie), None
        )
        contexte["types_choisis"] = [str(t) for t in (form["types"].value() or [])]
        contexte["difficulte_choisie"] = form["difficulte"].value()
        contexte["erreur_ia"] = kwargs.get("erreur_ia", "")
        contexte["ia_locale"] = settings.IA["FOURNISSEUR"] == "ollama"
        return contexte


class QuizDetailView(TemplateView):
    """Détail d'un quiz : questions, bonnes réponses, explications (maquette 08).

    Le quiz est cherché uniquement parmi ceux de l'utilisateur connecté : un
    identifiant d'un autre enseignant, invalide ou inconnu donne la même erreur
    404 (faille IDOR). La leçon source est elle aussi limitée à son propriétaire.
    """

    template_name = "quiz/quiz_detail.html"

    def get_context_data(self, **kwargs):
        """Quiz, leçon d'origine et récapitulatif par type de question."""
        contexte = super().get_context_data(**kwargs)
        try:
            quiz = QuizRepository().obtenir(kwargs["id_quiz"], self.request.user.pk)
        except PyMongoError:
            logger.exception("MongoDB indisponible : détail d'un quiz")
            contexte["mongo_indisponible"] = True
            return contexte
        if quiz is None:
            raise Http404("Quiz introuvable")
        types = [question["type_question"] for question in quiz["questions"]]
        contexte.update(
            quiz=quiz,
            lecon=Lecon.objects.filter(
                utilisateur=self.request.user, pk=quiz["id_lecon"]
            ).first(),
            recap={
                "total": len(types),
                "qcm": types.count("qcm"),
                "vrai_faux": types.count("vrai_faux"),
                "ouverte": types.count("ouverte"),
            },
        )
        return contexte

    def render_to_response(self, context, **kwargs):
        """Répond 503 quand MongoDB ne répond pas (page avec message)."""
        if context.get("mongo_indisponible"):
            kwargs["status"] = 503
        return super().render_to_response(context, **kwargs)


@require_POST
def valider_un_quiz(request, id_quiz):
    """Valide un quiz relu par l'enseignant (vérification humaine, CDC).

    Seule la méthode POST (protégée par le jeton CSRF) change le statut : un
    simple lien ne peut jamais valider un quiz. Le quiz est cherché parmi ceux
    de l'enseignant connecté : sinon, erreur 404 (protection contre l'accès
    direct par l'URL, faille IDOR).
    """
    repository = QuizRepository()
    try:
        quiz = repository.obtenir(id_quiz, request.user.pk)
        if quiz is None:
            raise Http404("Quiz introuvable")
        if quiz["statut"] == "valide" or not repository.valider(
            id_quiz, request.user.pk
        ):
            messages.info(request, "Ce quiz est déjà validé.")
        else:
            messages.success(
                request,
                f"Le quiz « {quiz['titre']} » a été validé. Il est prêt à servir.",
            )
    except PyMongoError:
        logger.exception("MongoDB indisponible : validation d'un quiz")
        messages.error(
            request, "Le quiz n'a pas pu être validé. Réessayez dans quelques instants."
        )
    return redirect("quiz:detail", id_quiz=id_quiz)


@require_GET
def exporter_un_quiz(request, id_quiz):
    """Télécharge le quiz en PDF, version élève (tâche 40).

    Seul un quiz validé par l'enseignant peut être exporté : un quiz généré par
    l'IA et non relu ne doit pas être distribué aux élèves. Le fichier ne
    contient jamais les réponses ; le corrigé reste dans l'espace de
    l'enseignant. Le refus est vérifié ici, pas seulement par le bouton grisé.
    Le quiz est cherché parmi ceux de l'enseignant connecté (404 sinon, IDOR).
    """
    try:
        quiz = QuizRepository().obtenir(id_quiz, request.user.pk)
    except PyMongoError:
        logger.exception("MongoDB indisponible : export d'un quiz")
        messages.error(
            request,
            "Le quiz n'a pas pu être exporté. Réessayez dans quelques instants.",
        )
        return redirect("quiz:detail", id_quiz=id_quiz)
    if quiz is None:
        raise Http404("Quiz introuvable")
    if quiz["statut"] != "valide":
        messages.error(
            request,
            "Validez le quiz avant de l'exporter : seul un quiz relu peut être "
            "distribué aux élèves.",
        )
        return redirect("quiz:detail", id_quiz=id_quiz)
    lecon = Lecon.objects.filter(utilisateur=request.user, pk=quiz["id_lecon"]).first()
    contenu = generer_pdf_eleve(
        quiz,
        matiere=lecon.get_matiere_display() if lecon else "",
        niveau=lecon.get_niveau_scolaire_display() if lecon else "",
    )
    reponse = HttpResponse(contenu, content_type="application/pdf")
    reponse["Content-Disposition"] = f'attachment; filename="{nom_fichier(quiz)}"'
    # Document personnel : ne pas le garder dans un cache (navigateur, proxy)
    reponse["Cache-Control"] = "private, no-store"
    return reponse


class QuizModificationView(TemplateView):
    """Modification d'un quiz : titre, difficulté, questions (maquette 09).

    Le quiz est cherché parmi ceux de l'enseignant connecté (404 sinon, faille
    IDOR). Le formulaire n'est pas cru sur parole : chaque question est
    reconstruite à partir du quiz enregistré (voir ``modification.py``).
    Un quiz modifié repasse en brouillon : il doit être relu puis revalidé.
    """

    template_name = "quiz/quiz_modification.html"

    def _charger(self, id_quiz):
        """Quiz de l'enseignant ; None si MongoDB ne répond pas ; 404 si absent."""
        try:
            quiz = QuizRepository().obtenir(id_quiz, self.request.user.pk)
        except PyMongoError:
            logger.exception("MongoDB indisponible : modification d'un quiz")
            return None
        if quiz is None:
            raise Http404("Quiz introuvable")
        return quiz

    def _afficher(self, quiz, **contexte):
        """Affiche le formulaire (503 si MongoDB ne répond pas)."""
        if quiz is None:
            return self.render_to_response({"mongo_indisponible": True}, status=503)
        contexte.setdefault("titre_saisi", quiz["titre"])
        contexte.setdefault("difficulte_saisie", quiz["difficulte"])
        contexte.setdefault("vues", vues_depuis_quiz(quiz))
        contexte.setdefault("erreurs", [])
        return self.render_to_response(
            {"quiz": quiz, "difficultes": DIFFICULTES, **contexte}
        )

    def get(self, request, *args, **kwargs):
        """Formulaire prérempli avec le quiz enregistré."""
        return self._afficher(self._charger(kwargs["id_quiz"]))

    def post(self, request, *args, **kwargs):
        """Contrôle la saisie puis enregistre ; sinon réaffiche avec les erreurs."""
        id_quiz = kwargs["id_quiz"]
        quiz = self._charger(id_quiz)
        if quiz is None:
            return self._afficher(None)
        saisie = lire_modification(request.POST, quiz)
        if not saisie["valide"]:
            return self._afficher(
                quiz,
                titre_saisi=saisie["titre"],
                difficulte_saisie=saisie["difficulte"],
                vues=saisie["vues"],
                erreurs=saisie["erreurs"],
            )
        etait_valide = quiz["statut"] == "valide"
        try:
            QuizRepository().modifier(
                id_quiz,
                request.user.pk,
                titre=saisie["titre"],
                description=quiz.get("description", ""),
                questions=saisie["questions"],
                difficulte=saisie["difficulte"],
            )
        except QuizInvalideError:
            logger.exception("Quiz modifié refusé par la validation")
            return self._afficher(
                quiz,
                titre_saisi=saisie["titre"],
                difficulte_saisie=saisie["difficulte"],
                vues=saisie["vues"],
                erreurs=["Le quiz n'a pas pu être enregistré. Vérifiez votre saisie."],
            )
        except PyMongoError:
            logger.exception("MongoDB indisponible : enregistrement d'un quiz modifié")
            return self._afficher(
                quiz,
                titre_saisi=saisie["titre"],
                difficulte_saisie=saisie["difficulte"],
                vues=saisie["vues"],
                erreurs=[
                    "Le quiz n'a pas pu être enregistré. "
                    "Réessayez dans quelques instants."
                ],
            )
        messages.success(request, f"Le quiz « {saisie['titre']} » a été modifié.")
        if etait_valide:
            messages.info(
                request,
                "Le quiz est repassé en brouillon : relisez-le puis validez-le "
                "de nouveau.",
            )
        return redirect("quiz:detail", id_quiz=id_quiz)


class QuizSuppressionView(QuizDetailView):
    """Suppression d'un quiz, avec confirmation (maquette 10).

    GET affiche la fenêtre de confirmation par-dessus le détail du quiz.
    Seul le POST (protégé par le jeton CSRF) supprime. Le quiz est cherché parmi
    ceux de l'enseignant connecté : 404 sinon (faille IDOR).
    """

    template_name = "quiz/quiz_confirmation_suppression.html"

    def post(self, request, *args, **kwargs):
        """Supprime le quiz puis retourne à la liste."""
        id_quiz = kwargs["id_quiz"]
        repository = QuizRepository()
        try:
            quiz = repository.obtenir(id_quiz, request.user.pk)
            if quiz is None or not repository.supprimer(id_quiz, request.user.pk):
                raise Http404("Quiz introuvable")
        except PyMongoError:
            logger.exception("MongoDB indisponible : suppression d'un quiz")
            messages.error(
                request,
                "Le quiz n'a pas pu être supprimé. Réessayez dans quelques instants.",
            )
            return redirect("quiz:detail", id_quiz=id_quiz)
        messages.success(request, f"Le quiz « {quiz['titre']} » a été supprimé.")
        return redirect("quiz:liste")
