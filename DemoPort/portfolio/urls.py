from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("skills/", views.skills, name="skills"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/<str:slug>/", views.project_detail, name="project_detail"),
    path("contact/", views.contact, name="contact"),
]
