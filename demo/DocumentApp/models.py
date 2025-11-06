# DocumentApp/models.py
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.db import models


class Request(models.Model):  # 제안 요청서
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    place = models.ForeignKey(
        "PlaceApp.TravelPlace", 
        on_delete=models.PROTECT,
        related_name="requests",
    )

    date = models.DateField()                                           # NOT NULL
    number_of_people = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )                                                                   # NOT NULL
    guidance = models.BooleanField(default=True)                        # DEFAULT TRUE
    travel_type = models.CharField(max_length=512, null=True, blank=True)   # NULL 허용
    experience = models.CharField(max_length=255, null=True, blank=True)    # NULL 허용
    is_public_profile = models.BooleanField(default=True)               # NOT NULL DEFAULT TRUE
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "request"
        indexes = [
            models.Index(fields=["place", "date"]),
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"Request#{self.pk} by user={self.user_id} place={self.place_id}"


class Root(models.Model):  # 여행 루트
    id = models.BigAutoField(primary_key=True)
    founder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roots",
    )
    place = models.ForeignKey(
        "PlaceApp.TravelPlace",
        on_delete=models.PROTECT,
        related_name="roots",
    )

    number_of_people = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )                                                                   # NOT NULL
    guidance = models.BooleanField(default=True)                        # DEFAULT TRUE
    travel_type = models.CharField(max_length=512, null=True, blank=True)   # NULL 허용
    experience = models.CharField(max_length=255, null=True, blank=True)    # NULL 허용
    created_at = models.DateTimeField(auto_now_add=True)                # NOT NULL
    modified_at = models.DateTimeField(auto_now=True)                   # NOT NULL

    class Meta:
        db_table = "root"
        indexes = [
            models.Index(fields=["place", "created_at"]),
            models.Index(fields=["founder", "created_at"]),
        ]

    def __str__(self):
        return f"Root#{self.pk} by founder={self.founder_id} place={self.place_id}"


class RequestRootMap(models.Model):  # 요청서-루트 연결(제안)
    id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name="proposals"
    )
    root = models.ForeignKey(
        Root, on_delete=models.CASCADE, related_name="proposals"
    )

    acceptance = models.BooleanField(default=False)                     # NOT NULL DEFAULT FALSE
    is_finished = models.BooleanField(default=False)                    # NOT NULL DEFAULT FALSE
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )                                                                   # NOT NULL
    review = models.CharField(
        max_length=512, validators=[MinLengthValidator(20)]
    )                                                                   # NOT NULL
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "request_root_map"
        indexes = [
            models.Index(fields=["request", "acceptance"]),
            models.Index(fields=["root", "acceptance"]),
        ]

    def __str__(self):
        return f"RequestRootMap#{self.pk} req={self.request_id} root={self.root_id}"
