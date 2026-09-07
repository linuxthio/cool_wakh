from django.contrib import admin

from wakh_server.stats import get_dashboard_stats


class WakhAdminSite(admin.AdminSite):
    site_header = "Wakh — Administration"
    site_title = "Wakh Admin"
    index_title = "Tableau de bord"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["wakh_stats"] = get_dashboard_stats()
        return super().index(request, extra_context)
