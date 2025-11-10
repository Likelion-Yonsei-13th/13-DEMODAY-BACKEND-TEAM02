from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    공통: 객체에 user_id 또는 founder_id가 있으면 그 사용자를 소유자로 간주.
    - SAFE_METHODS(GET/HEAD/OPTIONS): 모두 허용
    - 수정/삭제: 로그인 + 본인 소유(또는 staff)만 허용
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user.is_authenticated:
            return False
        if getattr(user, "is_staff", False):
            return True

        owner_id = None
        if hasattr(obj, "user_id"):
            owner_id = obj.user_id
        elif hasattr(obj, "founder_id"):
            owner_id = obj.founder_id

        # 커스텀 User는 PK가 uuid 이므로 request.user.pk 사용
        return owner_id == getattr(user, "pk", None)


class CanCreateRequest(BasePermission):
    """
    요청서(Request) 생성은 USER만 허용.
    SAFE_METHODS는 모두 허용 (목록/단건 조회는 공개)
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        # account.User.Role.USER
        return getattr(request.user, "role", None) == "USER"


class CanCreateRoot(BasePermission):
    """
    루트(Root) 생성은 LOCAL만 허용.
    SAFE_METHODS는 모두 허용 (목록/단건 조회는 공개)
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        # account.User.Role.LOCAL
        return getattr(request.user, "role", None) == "LOCAL"
