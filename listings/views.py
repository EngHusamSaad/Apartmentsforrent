from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta
from django.db import transaction


from .models import Building, Apartment, Tenant, Lease, ContractTemplate
from .forms import BuildingForm, ApartmentForm, TenantForm, LeaseForm
from .utils import render_contract


def dashboard(request):
    today = timezone.now().date()

    # --- عقود قاربت على الانتهاء (30 يوم) ---
    soon_days = 30
    soon_until = today + timedelta(days=soon_days)

    expiring_qs = (
        Lease.objects
        .select_related("apartment", "tenant", "apartment__building")
        .filter(status="ACTIVE", end_date__isnull=False, end_date__gte=today, end_date__lte=soon_until)
        .order_by("end_date")
    )

    # --- حساب نافذة "قبل أسبوع من بداية الشهر القادم" ---
    # أول يوم في الشهر الحالي
    month_start = today.replace(day=1)

    # أول يوم في الشهر القادم (بدون مكتبات خارجية)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)

    rent_notice_start = next_month_start - timedelta(days=30)   # قبل أسبوع
    rent_notice_end = next_month_start - timedelta(days=1)     # قبل يوم من بداية الشهر

    show_rent_notice = rent_notice_start <= today <= rent_notice_end

    # العقود التي ستظل فعّالة مع بداية الشهر القادم
    rent_due_qs = (
        Lease.objects
        .select_related("apartment", "tenant", "apartment__building")
        .filter(status="ACTIVE", start_date__lte=next_month_start)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=next_month_start))
        .order_by("apartment__building__name", "apartment__apartment_no")
    )

    # رتّبهم (اختياري)
    rent_due_qs = rent_due_qs.order_by("apartment__building__name", "apartment__apartment_no")

    rent_due_total = rent_due_qs.aggregate(total=Sum("rent_amount"))["total"] or 0

    stats = {
        "buildings": Building.objects.count(),
        "apartments": Apartment.objects.count(),
        "vacant": Apartment.objects.filter(status="VACANT").count(),
        "rented": Apartment.objects.filter(status="RENTED").count(),
        "tenants": Tenant.objects.count(),
        "active_leases": Lease.objects.filter(status="ACTIVE").count(),
        "expiring_soon": expiring_qs.count(),
    }

    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/dashboard_partial.html" if is_htmx else "listings/dashboard.html"

    return render(request, template, {
        "stats": stats,

        # تنبيه العقود المنتهية قريبًا
        "expiring_leases": expiring_qs[:10],
        "soon_days": soon_days,
        "today": today,
        "danger_until": today + timedelta(days=7),
        "warning_until": today + timedelta(days=14),

        # ✅ تنبيه استحقاق الأجرة
        "show_rent_notice": show_rent_notice,
        "next_month_start": next_month_start,
        "rent_due_total": rent_due_total,
        "rent_due_leases": rent_due_qs[:10],  # أول 10 في اللوحة
    })


# ==============================
# ---------- Buildings ----------
# ==============================
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
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "إضافة عمارة",
            "post_url": reverse("building_create"),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "إضافة عمارة"})


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
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "تعديل عمارة",
            "post_url": reverse("building_edit", args=[obj.id]),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "تعديل عمارة"})


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
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {
            "object": obj,
            "title": "حذف عمارة",
        })

    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "حذف عمارة"})


# ===============================
# ---------- Apartments ----------
# ===============================
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
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "إضافة شقة",
            "post_url": reverse("apartment_create"),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "إضافة شقة"})


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
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "تعديل شقة",
            "post_url": reverse("apartment_edit", args=[obj.id]),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "تعديل شقة"})


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
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {
            "object": obj,
            "title": "حذف شقة",
        })

    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "حذف شقة"})


# ============================
# ---------- Tenants ----------
# ============================
def tenant_list(request):
    tenants = Tenant.objects.all().order_by("full_name")
    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/tenant_list_partial.html" if is_htmx else "listings/tenant_list.html"
    return render(request, template, {"tenants": tenants})


def tenant_create(request):
    is_htmx = request.headers.get("HX-Request")
    form = TenantForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        tenants = Tenant.objects.all().order_by("full_name")
        resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})
        if is_htmx:
            resp["HX-Trigger"] = "closeModal"
        return resp if is_htmx else redirect("tenant_list")

    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "إضافة مستأجر",
            "post_url": reverse("tenant_create"),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "إضافة مستأجر"})


def tenant_edit(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    is_htmx = request.headers.get("HX-Request")
    form = TenantForm(request.POST or None, request.FILES or None, instance=tenant)

    if request.method == "POST" and form.is_valid():
        # إذا كنت تستخدم remove_id_image بالفورم (حسب شغلك السابق)
        if hasattr(form, "cleaned_data") and form.cleaned_data.get("remove_id_image"):
            if tenant.id_image:
                tenant.id_image.delete(save=False)
                tenant.id_image = None

        form.save()
        tenants = Tenant.objects.all().order_by("full_name")
        resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})
        if is_htmx:
            resp["HX-Trigger"] = "closeModal"
        return resp if is_htmx else redirect("tenant_list")

    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "تعديل مستأجر",
            "post_url": reverse("tenant_edit", args=[tenant.id]),
            "tenant": tenant,  # إذا بتعرض thumbnail للصورة
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "تعديل مستأجر"})


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
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {
            "object": obj,
            "title": "حذف مستأجر",
        })

    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "حذف مستأجر"})


# ===========================
# ---------- Leases ----------
# ===========================
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
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "إضافة عقد إيجار",
            "post_url": reverse("lease_create"),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "إضافة عقد إيجار"})


def lease_edit(request, pk):
    lease = get_object_or_404(Lease.objects.select_related("apartment"), pk=pk)
    form = LeaseForm(request.POST or None, instance=lease)
    is_htmx = request.headers.get("HX-Request")

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            updated = form.save()
            apt = updated.apartment

            # ✅ ضبط حالة الشقة حسب حالة العقد
            if updated.status == "ACTIVE":
                apt.status = "RENTED"
            else:
                # ENDED: رجّعها VACANT إذا ما في عقد نشط آخر
                still_active = Lease.objects.filter(apartment=apt, status="ACTIVE").exclude(pk=updated.pk).exists()
                apt.status = "RENTED" if still_active else "VACANT"

            apt.save(update_fields=["status"])

        if is_htmx:
            leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
            resp = render(request, "listings/partials/lease_list_partial.html", {"leases": leases})
            resp["HX-Trigger"] = "closeModal"
            return resp
        return redirect("lease_list")

    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {"form": form, "title": "تعديل عقد اجار"})
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "تعديل عقد اجار"})


def lease_delete(request, pk):
    lease = get_object_or_404(Lease.objects.select_related("apartment"), pk=pk)
    is_htmx = request.headers.get("HX-Request")

    if request.method == "POST":
        apt = lease.apartment

        with transaction.atomic():
            lease.delete()

            # ✅ إذا ما ظل في عقد نشط لنفس الشقة -> رجعها VACANT
            still_active = Lease.objects.filter(apartment=apt, status="ACTIVE").exists()
            if not still_active:
                apt.status = "VACANT"
                apt.save(update_fields=["status"])

        if is_htmx:
            leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all().order_by("-start_date")
            resp = render(request, "listings/partials/lease_list_partial.html", {"leases": leases})
            resp["HX-Trigger"] = "closeModal"
            return resp

        return redirect("lease_list")

    if is_htmx:
        return render(request, "listings/partials/confirm_delete_modal_partial.html", {"object": lease, "title": "حذف عقد اجار"})
    return render(request, "listings/confirm_delete.html", {"object": lease, "title": "حذف عقد اجار"})


# =====================================
# ---------- Lease Contract Preview ----
# =====================================
def lease_contract_preview(request, lease_id):
    lease = get_object_or_404(
        Lease.objects.select_related("apartment", "tenant", "apartment__building"),
        pk=lease_id
    )
    apt = lease.apartment
    bld = apt.building
    tenant = lease.tenant

    # إذا عندك tenant.address بالموديل، استخدمه، وإلا خليها خطوط
    tenant_address = getattr(tenant, "address", "") or "________________"

    data = {
        "tenant_name": tenant.full_name,
        "tenant_id": tenant.id_number,
        "tenant_phone": tenant.phone,
        "tenant_address": tenant_address,

        "landlord_name": "عنان سعد علي سعد",
        "landlord_id": "852420470",
        "landlord_address": "جنين - حي البساتين",
        "city": "جنين",

        "apartment_no": apt.apartment_no,
        "floor_no": apt.floor,
        "property_address": bld.address,

        "rent_amount": lease.rent_amount,
        "start_date": lease.start_date,
        "end_date": lease.end_date or "",
        "contract_date": timezone.now().date(),
    }

    template_obj = ContractTemplate.objects.filter(is_active=True).first()

    if not template_obj:
        return render(request, "listings/contract_preview.html", {
            "filled_body": "لا يوجد قالب عقد نشط.",
            "title": "عقد إيجار"
        })

    dynamic_keys = {
        "landlord_name", "landlord_id", "landlord_address", "city",
        "tenant_name", "tenant_id", "tenant_phone", "tenant_address",
        "apartment_no", "floor_no", "property_address",
        "rent_amount", "start_date", "end_date", "contract_date",
    }

    filled_body = render_contract(template_obj.body, data, dynamic_keys)

    return render(request, "listings/contract_preview.html", {
        "filled_body": filled_body,
        "title": template_obj.title
    })
