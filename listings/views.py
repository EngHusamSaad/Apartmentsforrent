from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from .models import Building, Apartment, Tenant, Lease
from .forms import BuildingForm, ApartmentForm, TenantForm, LeaseForm


def dashboard(request):
    stats = {
        "buildings": Building.objects.count(),
        "apartments": Apartment.objects.count(),
        "vacant": Apartment.objects.filter(status="VACANT").count(),
        "rented": Apartment.objects.filter(status="RENTED").count(),
        "tenants": Tenant.objects.count(),
        "active_leases": Lease.objects.filter(status="ACTIVE").count(),
    }
    return render(request, "listings/dashboard.html", {"stats": stats})


# ---------- Buildings ----------
def building_list(request):
    buildings = Building.objects.all().order_by("name")
    return render(request, "listings/building_list.html", {"buildings": buildings})


def building_create(request):
    form = BuildingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("building_list")
    return render(request, "listings/form.html", {"form": form, "title": "Add Building"})


def building_edit(request, pk):
    obj = get_object_or_404(Building, pk=pk)
    form = BuildingForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("building_list")
    return render(request, "listings/form.html", {"form": form, "title": "Edit Building"})


def building_delete(request, pk):
    obj = get_object_or_404(Building, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("building_list")
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Building"})


# ---------- Apartments ----------
def apartment_list(request):
    apartments = Apartment.objects.select_related("building").all().order_by("building__name", "apartment_no")
    return render(request, "listings/apartment_list.html", {"apartments": apartments})


def apartment_create(request):
    form = ApartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("apartment_list")
    return render(request, "listings/form.html", {"form": form, "title": "Add Apartment"})


def apartment_edit(request, pk):
    obj = get_object_or_404(Apartment, pk=pk)
    form = ApartmentForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("apartment_list")
    return render(request, "listings/form.html", {"form": form, "title": "Edit Apartment"})


def apartment_delete(request, pk):
    obj = get_object_or_404(Apartment, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("apartment_list")
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Apartment"})


# ---------- Tenants ----------
def tenant_list(request):
    tenants = Tenant.objects.all().order_by("full_name")
    return render(request, "listings/tenant_list.html", {"tenants": tenants})


def tenant_create(request):
    form = TenantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("tenant_list")
    return render(request, "listings/form.html", {"form": form, "title": "Add Tenant"})


def tenant_edit(request, pk):
    obj = get_object_or_404(Tenant, pk=pk)
    form = TenantForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("tenant_list")
    return render(request, "listings/form.html", {"form": form, "title": "Edit Tenant"})


def tenant_delete(request, pk):
    obj = get_object_or_404(Tenant, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("tenant_list")
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Tenant"})


# ---------- Leases ----------
def lease_list(request):
    leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
    return render(request, "listings/lease_list.html", {"leases": leases})


def lease_create(request):
    form = LeaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lease = form.save()
        # Optional: update apartment status
        lease.apartment.status = "RENTED"
        lease.apartment.save(update_fields=["status"])
        return redirect("lease_list")
    return render(request, "listings/form.html", {"form": form, "title": "Add Lease"})


def lease_edit(request, pk):
    obj = get_object_or_404(Lease, pk=pk)
    form = LeaseForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("lease_list")
    return render(request, "listings/form.html", {"form": form, "title": "Edit Lease"})


def lease_delete(request, pk):
    obj = get_object_or_404(Lease, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("lease_list")
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Lease"})
