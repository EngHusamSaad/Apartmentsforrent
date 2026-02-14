from django import forms
from .models import Building, Apartment, Tenant, Lease


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ["name", "address", "notes"]


class ApartmentForm(forms.ModelForm):
    class Meta:
        model = Apartment
        fields = ["building", "apartment_no", "floor", "rooms", "area_m2", "rent_amount", "status", "notes"]



class TenantForm(forms.ModelForm):
    remove_id_image = forms.BooleanField(
        required=False,
        label="حذف صورة الهوية",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta:
        model = Tenant
        fields = ["full_name", "phone", "id_number", "id_image","address", "notes"]
        widgets = {
            # هذا يلغي ClearableFileInput وبالتالي يختفي Currently/Clear/Change
            "id_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }


class LeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ["apartment", "tenant", "start_date", "end_date", "rent_amount", "security_deposit", "status", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ في حالة الإنشاء فقط: اعرض الشقق الشاغرة فقط
        # (إذا بدك تظهر كل الشقق بالتعديل اتركه هيك)
        if not self.instance.pk:
            self.fields["apartment"].queryset = Apartment.objects.filter(status="VACANT")

    def clean(self):
        cleaned = super().clean()
        apartment = cleaned.get("apartment")
        status = cleaned.get("status")

        # ✅ منع أكثر من عقد نشط لنفس الشقة
        if apartment and status == "ACTIVE":
            qs = Lease.objects.filter(apartment=apartment, status="ACTIVE")

            # في حالة تعديل عقد موجود، لا نحسب نفسه
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError("هذه الشقة مؤجرة حاليًا بعقد نشط، ولا يمكن تأجيرها لشخص آخر.")

        return cleaned