from django.db import models


class Building(models.Model):
    name = models.CharField("اسم العمارة", max_length=150)
    address = models.CharField("العنوان", max_length=255, blank=True)
    notes = models.TextField("ملاحظات", blank=True)

    class Meta:
        verbose_name = "عمارة"
        verbose_name_plural = "العمارات"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Apartment(models.Model):
    class Status(models.TextChoices):
        VACANT = "VACANT", "شاغرة"
        RENTED = "RENTED", "مؤجرة"
        MAINTENANCE = "MAINT", "صيانة"

    building = models.ForeignKey(
        Building,
        verbose_name="العمارة",
        on_delete=models.CASCADE,
        related_name="apartments"
    )

    apartment_no = models.CharField("رقم الشقة", max_length=50)
    floor = models.CharField("الطابق", max_length=50, blank=True)

    rooms = models.PositiveSmallIntegerField("عدد الغرف", default=0)
    area_m2 = models.DecimalField("المساحة (م²)", max_digits=8, decimal_places=2, default=0)

    rent_amount = models.DecimalField("قيمة الإيجار", max_digits=12, decimal_places=2, default=0)
    status = models.CharField("الحالة", max_length=10, choices=Status.choices, default=Status.VACANT)

    notes = models.TextField("ملاحظات", blank=True)

    class Meta:
        verbose_name = "شقة"
        verbose_name_plural = "الشقق"
        unique_together = ("building", "apartment_no")
        ordering = ["building", "apartment_no"]

    def __str__(self):
        return f"{self.building.name} - شقة {self.apartment_no}"


class Tenant(models.Model):
    full_name = models.CharField("اسم المستأجر", max_length=150)
    phone = models.CharField("رقم الهاتف", max_length=50, blank=True)
    id_number = models.CharField("رقم الهوية", max_length=50, blank=True)

    address = models.CharField("العنوان", max_length=255, blank=True)

    photo = models.ImageField(
        "الصورة الشخصية",
        upload_to="tenant_photos/",
        blank=True,
        null=True
    )

    id_image = models.ImageField("صورة الهوية", upload_to="tenant_ids/", blank=True, null=True)
    notes = models.TextField("ملاحظات", blank=True)

    class Meta:
        verbose_name = "مستأجر"
        verbose_name_plural = "المستأجرون"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Lease(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "نشط"
        EXPIRED = "EXPIRED", "منتهي"
        ENDED = "ENDED", "منتهي"

    apartment = models.ForeignKey(
        Apartment,
        verbose_name="الشقة",
        on_delete=models.PROTECT,
        related_name="leases"
    )

    tenant = models.ForeignKey(
        Tenant,
        verbose_name="المستأجر",
        on_delete=models.PROTECT,
        related_name="leases"
    )

    start_date = models.DateField("تاريخ البداية")
    end_date = models.DateField("تاريخ النهاية", null=True, blank=True)

    rent_amount = models.DecimalField("قيمة الإيجار المتفق عليها", max_digits=12, decimal_places=2)
    security_deposit = models.DecimalField("مبلغ التأمين", max_digits=12, decimal_places=2, default=0)

    status = models.CharField("حالة العقد", max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        verbose_name = "عقد"
        verbose_name_plural = "العقود"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["apartment"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_lease_per_apartment",
            )
        ]
    def __str__(self):
        return f"{self.apartment} - {self.tenant}"


class ContractTemplate(models.Model):
    title = models.CharField("العنوان", max_length=200)
    body = models.TextField("نص العقد")
    is_active = models.BooleanField("نشط", default=True)

    class Meta:
        verbose_name = "قالب عقد"
        verbose_name_plural = "قوالب العقود"
        ordering = ["-is_active", "title"]

    def __str__(self):
        return self.title
