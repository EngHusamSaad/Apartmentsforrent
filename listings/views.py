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

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Apartment


from .models import Building, Apartment, Tenant, Lease, ContractTemplate
from .forms import BuildingForm, ApartmentForm, TenantForm, LeaseForm, LeaseExpireForm
from .utils import render_contract


from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.conf import settings
import pdfkit

from django.db.models.deletion import ProtectedError





@login_required
@require_POST
def toggle_apartment_status(request, pk):
    apt = get_object_or_404(Apartment, pk=pk)

    if apt.status == Apartment.Status.MAINTENANCE:
        return JsonResponse({"ok": False, "error": "لا يمكن تبديل حالة الصيانة من هنا."}, status=400)

    active_qs = Lease.objects.filter(apartment=apt, status=Lease.Status.ACTIVE)
    has_active = active_qs.exists()

    # VACANT -> RENTED (مسموح فقط إذا في عقد نشط)
    if apt.status == Apartment.Status.VACANT:
        if not has_active:
            return JsonResponse(
                {"ok": False, "error": "لا يوجد عقد نشط لهذه الشقة. أنشئ عقداً أولاً ثم اجعلها مؤجرة."},
                status=400
            )
        apt.status = Apartment.Status.RENTED
        apt.save(update_fields=["status"])

    # RENTED -> VACANT (مسموح فقط إذا ما في عقد نشط)
    elif apt.status == Apartment.Status.RENTED:
        if has_active:
            return JsonResponse(
                {"ok": False, "error": "يوجد عقد نشط لهذه الشقة. أنهِ العقد أولاً قبل تحويلها لشاغرة."},
                status=400
            )
        apt.status = Apartment.Status.VACANT
        apt.save(update_fields=["status"])

    return JsonResponse({"ok": True, "status": apt.status, "display": apt.get_status_display()})


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
    status = request.GET.get("status")  # VACANT / RENTED / None

    apartments = Apartment.objects.select_related("building").all()

    if status in ("VACANT", "RENTED"):
        apartments = apartments.filter(status=status)

    apartments = apartments.order_by("building__name", "apartment_no")

    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/apartment_list_partial.html" if is_htmx else "listings/apartment_list.html"

    return render(request, template, {
        "apartments": apartments,
        "current_status": status,  # عشان نعمل active للزر
    })



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
        tenant = form.save(commit=False)

        # (create) عادة ما في حذف، لكن لو حابب نخليها "آمنة" لو checkbox مفعلة:
        if form.cleaned_data.get("remove_photo"):
            if tenant.photo:
                tenant.photo.delete(save=False)
            tenant.photo = None

        if form.cleaned_data.get("remove_id_image"):
            if tenant.id_image:
                tenant.id_image.delete(save=False)
            tenant.id_image = None

        tenant.save()

        tenants = Tenant.objects.all().order_by("full_name")
        resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})

        if is_htmx:
            resp["HX-Trigger"] = "closeModal"
            return resp

        return redirect("tenant_list")

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

    old_photo = tenant.photo
    old_id_image = tenant.id_image

    form = TenantForm(request.POST or None, request.FILES or None, instance=tenant)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)

        # ✅ حذف الصورة الشخصية
        if form.cleaned_data.get("remove_photo"):
            if old_photo:
                old_photo.delete(save=False)
            obj.photo = None

        # ✅ حذف صورة الهوية
        if form.cleaned_data.get("remove_id_image"):
            if old_id_image:
                old_id_image.delete(save=False)
            obj.id_image = None

        obj.save()

        # ✅ لو رفع ملف جديد، امسح القديم (تنظيف التخزين)
        if old_photo and obj.photo and old_photo.name != obj.photo.name:
            old_photo.delete(save=False)

        if old_id_image and obj.id_image and old_id_image.name != obj.id_image.name:
            old_id_image.delete(save=False)

        tenants = Tenant.objects.all().order_by("full_name")
        resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})

        if is_htmx:
            resp["HX-Trigger"] = "closeModal"
            return resp

        return redirect("tenant_list")

    if is_htmx:
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "تعديل مستأجر",
            "post_url": reverse("tenant_edit", args=[tenant.id]),
            "tenant": tenant,  # للعرض المصغر (thumbnails)
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "تعديل مستأجر"})

def tenant_delete(request, pk):
    obj = get_object_or_404(Tenant, pk=pk)
    is_htmx = request.headers.get("HX-Request")

    if request.method == "POST":
        try:
            obj.delete()

            if is_htmx:
                tenants = Tenant.objects.all().order_by("full_name")
                resp = render(request, "listings/partials/tenant_list_partial.html", {"tenants": tenants})
                resp["HX-Trigger"] = "closeModal"
                return resp
            return redirect("tenant_list")

        except ProtectedError:
            # عقود مرتبطة تمنع الحذف
            leases = Lease.objects.select_related("apartment", "apartment__building").filter(tenant=obj).order_by("-start_date")

            if is_htmx:
                resp = render(request, "listings/partials/cannot_delete_tenant_modal_partial.html", {
                    "object": obj,
                    "title": "تعذّر حذف المستأجر",
                    "leases": leases,
                    "message": "لا يمكن حذف المستأجر لأنه مرتبط بعقد/عقود إيجار. احذف العقود أولاً.",
                })
                resp["HX-Retarget"] = "#appModalBody"
                resp["HX-Trigger"] = "openModal"
                return resp

            return render(request, "listings/cannot_delete_tenant.html", {
                "object": obj,
                "title": "تعذّر حذف المستأجر",
                "leases": leases,
                "message": "لا يمكن حذف المستأجر لأنه مرتبط بعقد/عقود إيجار. احذف العقود أولاً.",
            })

    # GET
    if is_htmx:
        resp = render(request, "listings/partials/confirm_delete_modal_partial.html", {
            "object": obj,
            "title": "حذف مستأجر",
        })
        resp["HX-Retarget"] = "#appModalBody"
        resp["HX-Trigger"] = "openModal"
        return resp

    return render(request, "listings/confirm_delete.html", {"object": obj, "title": "حذف مستأجر"})


# ===========================
# ---------- Leases ----------
# ===========================
def lease_list(request):
    # (A) تحويل تلقائي للحالة: ACTIVE -> EXPIRED إذا انتهى العقد (اليوم التالي لانتهاء العقد)
    today = timezone.localdate()
    Lease.objects.filter(
        status=Lease.Status.ACTIVE,
        end_date__isnull=False,
        end_date__lt=today,
    ).update(status=Lease.Status.EXPIRED)

    tenant_id = request.GET.get("tenant", "")
    q = (request.GET.get("q", "") or "").strip()

    leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all()

    if tenant_id:
        leases = leases.filter(tenant_id=tenant_id)

    if q:
        leases = leases.filter(
            Q(tenant__full_name__icontains=q) |
            Q(tenant__id_number__icontains=q) |
            Q(tenant__phone__icontains=q)
        )

    leases = leases.order_by("-start_date")
    tenants = Tenant.objects.all().order_by("full_name")

    is_htmx = request.headers.get("HX-Request")
    template = "listings/partials/lease_list_partial.html" if is_htmx else "listings/lease_list.html"

    return render(request, template, {
        "leases": leases,
        "tenants": tenants,
        "current_tenant": str(tenant_id) if tenant_id else "",
        "q": q,
    })


def lease_toggle_status(request, pk):
    lease = get_object_or_404(
        Lease.objects.select_related("apartment", "tenant", "apartment__building"),
        pk=pk
    )
    is_htmx = request.headers.get("HX-Request")

    tenant_id = request.GET.get("tenant", "") if request.method == "GET" else request.POST.get("tenant", "")
    q = (request.GET.get("q", "") or "").strip() if request.method == "GET" else (request.POST.get("q", "") or "").strip()

    if request.method == "POST":
        if lease.status == Lease.Status.ACTIVE:
            form = LeaseExpireForm(request.POST)
            if form.is_valid():
                end_date = form.cleaned_data["end_date"]
                if lease.start_date and end_date < lease.start_date:
                    form.add_error("end_date", "تاريخ النهاية لا يمكن أن يكون قبل تاريخ البداية.")
                else:
                    lease.status = Lease.Status.EXPIRED
                    lease.end_date = end_date
                    lease.save(update_fields=["status", "end_date"])

                    # تحديث الجدول فقط (#leasesWrapper) + اغلاق المودال
                    leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all()
                    if tenant_id:
                        leases = leases.filter(tenant_id=tenant_id)
                    if q:
                        leases = leases.filter(
                            Q(tenant__full_name__icontains=q) |
                            Q(tenant__id_number__icontains=q) |
                            Q(tenant__phone__icontains=q)
                        )
                    leases = leases.order_by("-start_date")
                    tenants = Tenant.objects.all().order_by("full_name")
                    response = render(request, "listings/partials/lease_list_partial.html", {
                        "leases": leases,
                        "tenants": tenants,
                        "current_tenant": str(tenant_id) if tenant_id else "",
                        "q": q,
                    })
                    response["HX-Trigger"] = "closeModal"
                    return response
        else:
            # EXPIRED -> ACTIVE (مسح end_date)
            lease.status = Lease.Status.ACTIVE
            lease.end_date = None
            lease.save(update_fields=["status", "end_date"])

            leases = Lease.objects.select_related("apartment", "tenant", "apartment__building").all()
            if tenant_id:
                leases = leases.filter(tenant_id=tenant_id)
            if q:
                leases = leases.filter(
                    Q(tenant__full_name__icontains=q) |
                    Q(tenant__id_number__icontains=q) |
                    Q(tenant__phone__icontains=q)
                )
            leases = leases.order_by("-start_date")
            tenants = Tenant.objects.all().order_by("full_name")
            response = render(request, "listings/partials/lease_list_partial.html", {
                "leases": leases,
                "tenants": tenants,
                "current_tenant": str(tenant_id) if tenant_id else "",
                "q": q,
            })
            response["HX-Trigger"] = "closeModal"
            return response

        # لو في أخطاء: ارجع نفس المودال مع الأخطاء
        if is_htmx:
            title = "إنهاء العقد" if lease.status == Lease.Status.ACTIVE else "إرجاع لنشط"
            resp = render(request, "listings/partials/lease_toggle_status_modal_partial.html", {
                "lease": lease,
                "form": form if lease.status == Lease.Status.ACTIVE else None,
                "title": title,
                "tenant": tenant_id,
                "q": q,
                "today": timezone.localdate(),
            })
            resp["HX-Retarget"] = "#appModalBody"
            resp["HX-Reswap"] = "innerHTML"
            return resp

    # GET: اعرض المودال بحسب الحالة
    if lease.status == Lease.Status.ACTIVE:
        form = LeaseExpireForm(initial={"end_date": timezone.localdate()})
        title = "إنهاء العقد"
    else:
        form = None
        title = "إرجاع لنشط"

    if is_htmx:
        resp = render(request, "listings/partials/lease_toggle_status_modal_partial.html", {
            "lease": lease,
            "form": form,
            "title": title,
            "tenant": tenant_id,
            "q": q,
            "today": timezone.localdate(),
        })
        resp["HX-Retarget"] = "#appModalBody"
        return resp

    return redirect("lease_list")



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

            if updated.status == "ACTIVE":
                apt.status = "RENTED"
            else:
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
        resp = render(request, "listings/partials/form_modal_partial.html", {
            "form": form,
            "title": "تعديل عقد إيجار",
            "post_url": reverse("lease_edit", args=[lease.id]),  # ✅ مهم
        })
        resp["HX-Retarget"] = "#appModalBody"
        resp["HX-Trigger"] = "openModal"  # ✅ مهم
        return resp

    return render(request, "listings/form.html", {"form": form, "title": "تعديل عقد إيجار"})



def lease_delete(request, pk):
    lease = get_object_or_404(Lease.objects.select_related("apartment"), pk=pk)
    is_htmx = request.headers.get("HX-Request")

    if request.method == "POST":
        apt = lease.apartment
        with transaction.atomic():
            lease.delete()
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
        resp = render(request, "listings/partials/confirm_delete_modal_partial.html", {
            "object": lease,
            "title": "حذف عقد إيجار",
        })
        resp["HX-Retarget"] = "#appModalBody"
        resp["HX-Trigger"] = "openModal"   # ✅ مهم
        return resp

    return render(request, "listings/confirm_delete.html", {"object": lease, "title": "حذف عقد إيجار"})



# =====================================
# ---------- Lease Contract Helpers ----
# =====================================
def _build_contract_filled_body(lease_id):
    lease = get_object_or_404(
        Lease.objects.select_related("apartment", "tenant", "apartment__building"),
        pk=lease_id
    )
    apt = lease.apartment
    bld = apt.building
    tenant = lease.tenant

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
        return {
            "title": "عقد إيجار",
            "filled_body": "لا يوجد قالب عقد نشط.",
        }

    dynamic_keys = {
        "landlord_name", "landlord_id", "landlord_address", "city",
        "tenant_name", "tenant_id", "tenant_phone", "tenant_address",
        "apartment_no", "floor_no", "property_address",
        "rent_amount", "start_date", "end_date", "contract_date",
    }

    filled_body = render_contract(template_obj.body, data, dynamic_keys)

    return {
        "title": template_obj.title,
        "filled_body": filled_body,
    }


# =====================================
# ---------- Lease Contract Preview ----
# =====================================
def lease_contract_preview(request, lease_id):
    ctx = _build_contract_filled_body(lease_id)

    # ✅ مهم جدًا: مرّر lease_id عشان زر PDF يشتغل
    return render(request, "listings/contract_preview.html", {
        "filled_body": ctx["filled_body"],
        "title": ctx["title"],
        "lease_id": lease_id,
    })


# =====================================
# ---------- Lease Contract PDF --------
# =====================================
def lease_contract_pdf(request, lease_id):
    from weasyprint import HTML  # داخل الفنكشن حتى ما يكسر runserver

    ctx = _build_contract_filled_body(lease_id)

    context = {
        "title": ctx["title"],
        "filled_body": ctx["filled_body"],
        "year": now().year,
    }

    html_string = render_to_string(
        "listings/contract_preview_pdf.html",
        context,
        request=request
    )

    pdf_bytes = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")  # لقراءة static/logo
    ).write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="contract_{lease_id}.pdf"'
    return response

def tenant_quick_view(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)

    leases = (Lease.objects
              .select_related("apartment")
              .filter(tenant=tenant)
              .order_by("-start_date")[:5])

    return render(request, "listings/partials/tenant_quick_view.html", {
        "tenant": tenant,
        "leases": leases,
    })
