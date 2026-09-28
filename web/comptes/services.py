from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def envoyer_invitation(utilisateur, request):
    """Envoie à un nouvel utilisateur le lien pour choisir son mot de passe.

    Le lien contient l'identifiant encodé et un jeton signé, valable 72 heures
    et utilisable une seule fois.

    Args:
        utilisateur: Compte qui vient d'être créé, sans mot de passe utilisable.
        request: Requête HTTP en cours, pour construire l'adresse complète du lien.
    """
    uid = urlsafe_base64_encode(force_bytes(utilisateur.pk))
    jeton = default_token_generator.make_token(utilisateur)
    lien = request.build_absolute_uri(
        reverse("comptes:definir_mot_de_passe", args=[uid, jeton])
    )
    send_mail(
        subject="EduQuizAI — Activez votre compte",
        message=render_to_string(
            "comptes/emails/invitation.txt", {"utilisateur": utilisateur, "lien": lien}
        ),
        from_email=None,
        recipient_list=[utilisateur.email],
    )
