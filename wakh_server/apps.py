from django.contrib.admin.apps import AdminConfig


class WakhAdminConfig(AdminConfig):
    """
    Remplace le site d'admin par défaut par WakhAdminSite, sans avoir à
    toucher aux `@admin.register(...)` existants dans registry/admin.py et
    audioqueue/admin.py : `django.contrib.admin.site` (utilisé partout par
    ces décorateurs) résout automatiquement vers cette classe une fois
    `default_site` défini ici. Mécanisme officiel Django, voir :
    https://docs.djangoproject.com/en/5.0/ref/contrib/admin/#overriding-the-default-admin-site
    """

    default_site = "wakh_server.admin_site.WakhAdminSite"
