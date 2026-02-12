from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("buildings/", views.building_list, name="building_list"),
    path("buildings/add/", views.building_create, name="building_create"),
    path("buildings/<int:pk>/edit/", views.building_edit, name="building_edit"),
    path("buildings/<int:pk>/delete/", views.building_delete, name="building_delete"),

    path("apartments/", views.apartment_list, name="apartment_list"),
    path("apartments/add/", views.apartment_create, name="apartment_create"),
    path("apartments/<int:pk>/edit/", views.apartment_edit, name="apartment_edit"),
    path("apartments/<int:pk>/delete/", views.apartment_delete, name="apartment_delete"),

    path("tenants/", views.tenant_list, name="tenant_list"),
    path("tenants/add/", views.tenant_create, name="tenant_create"),
    path("tenants/<int:pk>/edit/", views.tenant_edit, name="tenant_edit"),
    path("tenants/<int:pk>/delete/", views.tenant_delete, name="tenant_delete"),

    path("leases/", views.lease_list, name="lease_list"),
    path("leases/add/", views.lease_create, name="lease_create"),
    path("leases/<int:pk>/edit/", views.lease_edit, name="lease_edit"),
    path("leases/<int:pk>/delete/", views.lease_delete, name="lease_delete"),
]
