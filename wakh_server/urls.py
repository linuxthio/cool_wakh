from django.contrib import admin
from django.urls import path

# Cette app Django est montée sous /admin par Starlette (voir asgi.py),
# qui ajuste SCRIPT_NAME/PATH_INFO en conséquence : les patterns ici sont
# donc relatifs à /admin, sans répéter le préfixe.
urlpatterns = [
    path("", admin.site.urls),
]
