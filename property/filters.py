from django_filters import FilterSet
from django_filters import rest_framework as filters
from property.models import Amenity, NearbyFeature, Property


class PropertyFilter(FilterSet):
    """
    Create a filter class that inherits from FilterSet. This class will help
    us search for properties using specified fields.
    """
    city = filters.CharFilter('address__City', lookup_expr='icontains')
    street = filters.CharFilter('address__Street', lookup_expr='icontains')
    state = filters.CharFilter('address__State', lookup_expr='icontains')
    title = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    listing_type = filters.CharFilter(lookup_expr='iexact')
    property_type = filters.CharFilter(lookup_expr='iexact')
    rent_period = filters.CharFilter(lookup_expr='iexact')
    status = filters.CharFilter(lookup_expr='iexact')
    price = filters.RangeFilter()
    bedrooms = filters.NumberFilter(lookup_expr='gte')
    bathrooms = filters.NumberFilter(lookup_expr='gte')
    lot_size = filters.RangeFilter()
    distance_to_main_road = filters.CharFilter(lookup_expr='iexact')
    distance_to_city = filters.CharFilter(lookup_expr='iexact')
    noise_level = filters.CharFilter(lookup_expr='iexact')
    # conjoined=True gives AND semantics: the property must have ALL
    # the requested amenities / nearby features.
    amenities = filters.ModelMultipleChoiceFilter(
        queryset=Amenity.objects.filter(is_active=True),
        conjoined=True)
    nearby = filters.ModelMultipleChoiceFilter(
        queryset=NearbyFeature.objects.filter(is_active=True),
        conjoined=True)

    class Meta:
        model = Property
        fields = (
            'title',
            'description',
            'city',
            'street',
            'state',
            'listing_type',
            'property_type',
            'rent_period',
            'status',
            'garages',
            'bedrooms',
            'bathrooms',
            'lot_size',
            'price',
            'amenities',
            'nearby',
            'distance_to_main_road',
            'distance_to_city',
            'noise_level',
        )
