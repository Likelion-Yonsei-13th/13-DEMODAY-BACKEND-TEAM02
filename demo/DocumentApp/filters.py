import django_filters as df
from .models import Request

class RequestFilter(df.FilterSet):
    date_from = df.DateFilter(field_name="date", lookup_expr="gte")
    date_to   = df.DateFilter(field_name="date", lookup_expr="lte")
    min_people = df.NumberFilter(field_name="number_of_people", lookup_expr="gte")
    max_people = df.NumberFilter(field_name="number_of_people", lookup_expr="lte")
    travel_type = df.CharFilter(field_name="travel_type", lookup_expr="icontains")
    experience  = df.CharFilter(field_name="experience", lookup_expr="icontains")

    class Meta:
        model = Request
        fields = ["place", "guidance", "is_public_profile", "date_from", "date_to",
                  "min_people", "max_people", "travel_type", "experience"]
