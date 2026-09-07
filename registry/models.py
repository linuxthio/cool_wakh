from django.db import models


class PhoneRegistry(models.Model):
    """
    Compte Wakh : un numéro de téléphone, un code PIN à 4 chiffres
    (haché), et un jeton d'authentification en cours de validité. Créer
    un compte (POST /auth/register) puis se connecter (POST /auth/login)
    est obligatoire pour utiliser le service — voir signaling/auth.py et
    signaling/auth_router.py.

    Ne contient JAMAIS de contenu de message. Le nom affiché reste stocké
    localement sur l'appareil de l'utilisateur (DataStore côté Android) ;
    on ne le duplique pas ici pour limiter les données personnelles
    conservées côté serveur.
    """

    phone_number = models.CharField(max_length=32, unique=True, db_index=True)

    # Géré uniquement via signaling/auth_router.py (hashers Django
    # standard, comme pour un mot de passe classique) — jamais affiché ni
    # modifiable depuis l'admin. Un code PIN à 4 chiffres reste haché de
    # la même façon qu'un mot de passe : le hachage ne dépend pas du
    # format ni de la longueur de la valeur d'origine.
    pin_hash = models.CharField(max_length=255, blank=True)
    auth_token = models.CharField(max_length=64, blank=True, db_index=True)

    is_online = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(auto_now=True)
    first_registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compte"
        verbose_name_plural = "Comptes"
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        state = "en ligne" if self.is_online else "hors ligne"
        return f"{self.phone_number} ({state})"
