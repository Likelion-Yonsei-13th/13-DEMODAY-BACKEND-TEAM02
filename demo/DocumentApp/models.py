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

    title = models.CharField(max_length=100, null=True, blank=True)     # 제안서 제목
    date = models.DateField()                                           # 시작 날짜
    end_date = models.DateField(null=True, blank=True)                  # 종료 날짜 (선택사항)
    number_of_people = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )                                                                   # NOT NULL
    guidance = models.BooleanField(default=True)                        # DEFAULT TRUE

    # 사용자가 선택한 모든 여행 테마 태그 (level1/2/3 포함 가능)
    travel_type = models.ManyToManyField(
        "ThemeTag",
        blank=True,
        related_name="requests",
        help_text="사용자가 선택한 모든 여행 테마 태그 (level1/2/3 포함 가능)",
    )

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

    # 루트에 연결된 여행 테마 태그 (level1/2/3 포함 가능)
    travel_type = models.ManyToManyField(
        "ThemeTag",
        blank=True,
        related_name="roots",
        help_text="루트에 연결된 여행 테마 태그 (level1/2/3 포함 가능)",
    )

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


class ThemeTag(models.Model):
    """
    여행 테마 태그 보관용 테이블
    - id        : BIGINT UNSIGNED AUTO_INCREMENT, PK
    - name      : VARCHAR(100) NOT NULL
    - level     : TINYINT UNSIGNED NOT NULL, CHECK (1~3)
    - parent_id : BIGINT UNSIGNED, FK(ThemeTag.id), level 1 은 NULL
    """

    id = models.BigAutoField(primary_key=True)

    name = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text='태그 이름 (예: "여유로운 여행", "숨겨진 로컬 스팟")',
    )

    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="계층 레벨 (1=대분류, 2=중분류, 3=소분류)",
    )

    # DB 컬럼명은 parent_id 로 생성됨
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        help_text="부모 태그 (level 1은 NULL, level 2/3은 상위 테마 태그)",
    )

    class Meta:
        db_table = "theme_tag"
        verbose_name = "여행 테마 태그"
        verbose_name_plural = "여행 테마 태그들"

    def __str__(self):
        return f"ThemeTag#{self.pk} name={self.name} level={self.level}"
