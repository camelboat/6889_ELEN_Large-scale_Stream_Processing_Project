from django.urls import path
from django.conf.urls import url, include
from django.contrib import admin
from . import views

urlpatterns = [
    path('', views.results),
    path('<str:state_name>', views.state_details)
]