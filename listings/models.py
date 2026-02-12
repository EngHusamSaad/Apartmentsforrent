from django.db import models

class Building(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Apartment(models.Model):
    class Status(models.TextChoices):
        VACANT = "VACANT", "Vacant"
        RENTED = "RENTED", "Rented"
        MAINTENANCE = "MAINT", "Maintenance"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="apartments")
    apartment_no = models.CharField(max_length=50)
    floor = models.CharField(max_length=50, blank=True)

    rooms = models.PositiveSmallIntegerField(default=0)
    area_m2 = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    rent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.VACANT)

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("building", "apartment_no")

    def __str__(self):
        return f"{self.building.name} - {self.apartment_no}"


class Tenant(models.Model):
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=50, blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class Lease(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, related_name="leases")
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="leases")

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)  # المتفق عليه في العقد
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.apartment} / {self.tenant}"
