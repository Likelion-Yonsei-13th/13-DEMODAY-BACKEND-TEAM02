from rest_framework.pagination import CursorPagination

class MessageCursorPagination(CursorPagination):
    page_size = 30
    ordering = "-created_at"
