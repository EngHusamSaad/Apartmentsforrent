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
    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/dashboard_partial.html" if is_htmx else "listings/dashboard.html"
    return render(request, template, {"stats": stats})


# ---------- Buildings ----------
def building_list(request):
    buildings = Building.objects.all().order_by("name")
    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/building_list_partial.html" if is_htmx else "listings/building_list.html"
    return render(request, template, {"buildings": buildings})


def building_create(request):
    form = BuildingForm(request.POST or None)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            buildings = Building.objects.all().order_by("name")
            resp = render(request, "listings/partials/building_list_partial.html", {"buildings": buildings})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("building_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Add Building"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Add Building"})


def building_edit(request, pk):
    obj = get_object_or_404(Building, pk=pk)
    form = BuildingForm(request.POST or None, instance=obj)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            buildings = Building.objects.all().order_by("name")
            resp = render(request, "listings/partials/building_list_partial.html", {"buildings": buildings})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("building_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Edit Building"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Edit Building"})


def building_delete(request, pk):
    obj = get_object_or_404(Building, pk=pk)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST":
        obj.delete()
        if is_htmx:
            buildings = Building.objects.all().order_by("name")
            resp = render(request, "listings/partials/building_list_partial.html", {"buildings": buildings})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("building_list")
    if is_htmx:
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {"object": obj, "title": "Delete Building"})
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Building"})


# ---------- Apartments ----------
def apartment_list(request):
    apartments = Apartment.objects.select_related("building").all().order_by("building__name", "apartment_no")
    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/apartment_list_partial.html" if is_htmx else "listings/apartment_list.html"
    return render(request, template, {"apartments": apartments})


def apartment_create(request):
    form = ApartmentForm(request.POST or None)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            apartments = Apartment.objects.select_related("building").all().order_by("building__name", "apartment_no")
            resp = render(request, "listings/partials/apartment_list_partial.html", {"apartments": apartments})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("apartment_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Add Apartment"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Add Apartment"})


def apartment_edit(request, pk):
    obj = get_object_or_404(Apartment, pk=pk)
    form = ApartmentForm(request.POST or None, instance=obj)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            apartments = Apartment.objects.select_related("building").all().order_by("building__name", "apartment_no")
            resp = render(request, "listings/partials/apartment_list_partial.html", {"apartments": apartments})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("apartment_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Edit Apartment"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Edit Apartment"})


def apartment_delete(request, pk):
    obj = get_object_or_404(Apartment, pk=pk)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST":
        obj.delete()
        if is_htmx:
            apartments = Apartment.objects.select_related("building").all().order_by("building__name", "apartment_no")
            resp = render(request, "listings/partials/apartment_list_partial.html", {"apartments": apartments})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("apartment_list")
    if is_htmx:
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {"object": obj, "title": "Delete Apartment"})
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Apartment"})


# ---------- Tenants ----------
def tenant_list(request):
    tenants = Tenant.objects.all().order_by("full_name")
    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/tenant_list_partial.html" if is_htmx else "listings/tenant_list.html"
    return render(request, template, {"tenants": tenants})


def tenant_create(request):
    form = TenantForm(request.POST or None)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            tenants = Tenant.objects.all().order_by("full_name")
            resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("tenant_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Add Tenant"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Add Tenant"})


def tenant_edit(request, pk):
    obj = get_object_or_404(Tenant, pk=pk)
    form = TenantForm(request.POST or None, instance=obj)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            tenants = Tenant.objects.all().order_by("full_name")
            resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("tenant_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Edit Tenant"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Edit Tenant"})


def tenant_delete(request, pk):
    obj = get_object_or_404(Tenant, pk=pk)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST":
        obj.delete()
        if is_htmx:
            tenants = Tenant.objects.all().order_by("full_name")
            resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("tenant_list")
    if is_htmx:
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {"object": obj, "title": "Delete Tenant"})
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Tenant"})


# ---------- Leases ----------
def lease_list(request):
    leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/lease_list_partial.html" if is_htmx else "listings/lease_list.html"
    return render(request, template, {"leases": leases})


def lease_create(request):
    form = LeaseForm(request.POST or None)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        lease = form.save()
        lease.apartment.status = "RENTED"
        lease.apartment.save(update_fields=["status"])
        if is_htmx:
            leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
            resp = render(request, "listings/partials/lease_list_partial.html", {"leases": leases})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("lease_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Add Lease"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Add Lease"})


def lease_edit(request, pk):
    obj = get_object_or_404(Lease, pk=pk)
    form = LeaseForm(request.POST or None, instance=obj)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx:
            leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
            resp = render(request, "listings/partials/lease_list_partial.html", {"leases": leases})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("lease_list")
    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "Edit Lease"})
        if request.method == "POST":
            resp["HX-Retarget"] = "#appModalBody"
        return resp
    return render(request, "listings/form.html", {"form": form, "title": "Edit Lease"})


def lease_delete(request, pk):
    obj = get_object_or_404(Lease, pk=pk)
    is_htmx = request.headers.get("HX-Request")
    if request.method == "POST":
        obj.delete()
        if is_htmx:
            leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
            resp = render(request, "listings/partials/lease_list_partial.html", {"leases": leases})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("lease_list")
    if is_htmx:
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {"object": obj, "title": "Delete Lease"})
    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "Delete Lease"})
