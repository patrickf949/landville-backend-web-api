from django.contrib import admin

from property.models import (
    Amenity, BuyerPropertyList, NearbyFeature, Property, PropertyEnquiry,
    PropertyInspection, PropertyReview)


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'icon', 'is_active')
    list_filter = ('group', 'is_active')
    search_fields = ('name',)


@admin.register(NearbyFeature)
class NearbyFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


admin.site.register(Property)
admin.site.register(PropertyReview)
admin.site.register(PropertyEnquiry)
admin.site.register(PropertyInspection)
admin.site.register(BuyerPropertyList)
