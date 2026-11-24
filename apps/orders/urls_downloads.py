from django.urls import path

from . import downloads

app_name = "downloads"
urlpatterns = [
    path("request/<int:license_id>/<int:version_id>/", downloads.request_download, name="request"),
    path("<str:token>/", downloads.serve, name="serve"),
]
