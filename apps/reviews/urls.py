from django.urls import path

from . import views

app_name = "reviews"
urlpatterns = [path("<int:license_id>/", views.post_review, name="post")]
