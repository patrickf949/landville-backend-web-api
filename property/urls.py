from django.urls import path
from property.views import (
    AmenityListView, CreateAndListPropertyView, PropertyDetailView,
    BuyerPropertyListView, NearbyFeatureListView, PropertyStatusUpdateView,
    TrendingPropertyView, DeleteCloudinaryResourceView,
    PropertyEnquiryDetailView, ListCreateEnquiryAPIView)


urlpatterns = [
    path('', CreateAndListPropertyView.as_view(),
         name='create_and_list_property'),
    path('amenities/', AmenityListView.as_view(), name='amenity_list'),
    path('nearby-features/', NearbyFeatureListView.as_view(),
         name='nearby_feature_list'),
    path('buyer-list/', BuyerPropertyListView.as_view(),
         name='get_buyer_list'),
    path('buyer-list/<slug:slug>/', BuyerPropertyListView.as_view(),
         name='modify_buyer_list'),
    path('trending/', TrendingPropertyView.as_view(),
         name='trending_property'),
    path('<slug:slug>/resource', DeleteCloudinaryResourceView.as_view(),
         name='delete_cloudinary_resource'),
    path('<slug:slug>/status/', PropertyStatusUpdateView.as_view(),
         name='property_status'),
    path('<slug:slug>/', PropertyDetailView.as_view(), name='single_property'),
    path('enquiries/<property_slug>/create/',
         ListCreateEnquiryAPIView.as_view(), name='post_enquiry'),
    path('enquiries/all/', ListCreateEnquiryAPIView.as_view(),
         name='all-enquiries'),
    path('enquiries/<enquiry_id>/',
         PropertyEnquiryDetailView.as_view(), name='one-enquiry')
]
