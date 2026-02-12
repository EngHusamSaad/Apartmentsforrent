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
    class Meta:
        model = Tenant
        fields = ["full_name", "phone", "id_number", "notes"]


class LeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ["apartment", "tenant", "start_date", "end_date", "rent_amount", "security_deposit", "status", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
