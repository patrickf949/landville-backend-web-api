from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from rest_framework import status, serializers
from rest_framework.test import APITestCase, APIRequestFactory

from authentication.models import User
from property.models import Property, Amenity, NearbyFeature, PropertyEnquiry
from property.renderers import PropertyJSONRenderer, PropertyEnquiryJSONRenderer
from property.serializers import (
    PropertySerializer, PropertyStatusSerializer, MAX_PROPERTY_IMAGE_COUNT
)
from property.views import PropertyStatusUpdateView, DeleteCloudinaryResourceView
from tests.factories.authentication_factory import UserFactory
from tests.factories.property_factory import PropertyFactory


class PropertyCoverageBoostTests(APITestCase):

    def setUp(self):
        self.owner = UserFactory.create(role='CA')
        self.buyer = UserFactory.create(role='BY')
        self.admin = UserFactory.create(role='LA')
        self.property = PropertyFactory.create(
            owner=self.owner,
            is_published=True,
            listing_type='S',
            property_type='H',
            rent_period='M',
            noise_level='Q',
            distance_to_main_road='1',
            distance_to_city='1'
        )

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.token}')

    def test_property_models_str(self):
        amenity = Amenity.objects.create(name='Swimming Pool', group='U')
        self.assertEqual(str(amenity), 'Swimming Pool')

        feature = NearbyFeature.objects.create(name='Central Hospital')
        self.assertEqual(str(feature), 'Central Hospital')

    def test_property_renderers_edge_cases(self):
        renderer = PropertyJSONRenderer()

        # single_property_format without 'id'
        empty_data = {'title': 'Sample'}
        renderer.single_property_format(empty_data)
        self.assertNotIn('property_type', empty_data)

        # single_property_format with populated choices
        prop_data = {'id': self.property.pk}
        renderer.single_property_format(prop_data)
        self.assertEqual(prop_data['rent_period'], 'Monthly')
        self.assertEqual(prop_data['noise_level'], 'Quiet')
        self.assertEqual(prop_data['distance_to_main_road'], 'Less Than 500M')
        self.assertEqual(prop_data['distance_to_city'], 'Less Than 5Km')

        # render non-dict data
        res_list = renderer.render([{'id': self.property.pk}])
        self.assertIn('property', res_list)

        # render errors dictionary (line 50)
        res_err = renderer.render({'errors': {'msg': 'failed'}})
        self.assertIn('failed', res_err.decode() if isinstance(res_err, bytes) else res_err)

        # render with empty property payload
        res_empty_prop = renderer.render({'data': {'property': None}})
        self.assertIn('"property": null', res_empty_prop)

        # render with data=None causing TypeError (lines 72-73)
        res_type_err = renderer.render({'data': None})
        self.assertIn('"data": null', res_type_err)

        # render with dict subclass to cover 63->75 branch
        class CustomDict(dict):
            pass

        cd = CustomDict({'title': 'custom'})
        res_custom = renderer.render(cd)
        self.assertIn('property', res_custom)

        # PropertyEnquiryJSONRenderer with ErrorDetail
        enq_renderer = PropertyEnquiryJSONRenderer()
        mock_err_data = {'field': 'ErrorDetail(string="error")'}
        rendered_err = enq_renderer.render(mock_err_data)
        self.assertIn('errors', rendered_err)

        # PropertyEnquiryJSONRenderer with non-dict data (line 100)
        res_enq_list = enq_renderer.render([1, 2, 3])
        self.assertIn('enquiry', res_enq_list)

    def test_property_serializers_edge_cases(self):
        serializer = PropertySerializer()

        # validate_image_others cap exceeded
        too_many_images = [f'http://image{i}.jpg' for i in range(MAX_PROPERTY_IMAGE_COUNT + 1)]
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate_image_others(too_many_images)
        self.assertIn('maximum', str(cm.exception))

        # validate listing_type='R' without rent_period
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate({'listing_type': 'R', 'rent_period': None})
        self.assertIn('rent_period', cm.exception.detail)

        # validate listing_type='R' with rent_period (branch 107->109)
        val_rent = serializer.validate({'listing_type': 'R', 'rent_period': 'M'})
        self.assertEqual(val_rent['rent_period'], 'M')

        # update method photo cap
        self.property.image_others = [f'http://old{i}.jpg' for i in range(MAX_PROPERTY_IMAGE_COUNT)]
        self.property.save()
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.update(self.property, {
                'image_others': ['http://new1.jpg'],
                'image_main': ['http://newmain.jpg'],
                'coordinates': '{"lat": 1.2, "lng": 3.4}',
                'address': '{"city": "Nairobi"}'
            })
        self.assertIn('photos in total', str(cm.exception.detail['image_others']))

        # PropertyStatusSerializer transitions
        sale_prop = self.property  # listing_type='S'
        status_serializer = PropertyStatusSerializer(instance=sale_prop)
        with self.assertRaises(serializers.ValidationError) as cm:
            status_serializer.validate_status('RE')
        self.assertIn('Only rental listings', str(cm.exception))

        rental_prop = PropertyFactory.create(owner=self.owner, listing_type='R', rent_period='M')
        rental_status_serializer = PropertyStatusSerializer(instance=rental_prop)
        with self.assertRaises(serializers.ValidationError) as cm:
            rental_status_serializer.validate_status('SO')
        self.assertIn('Only sale listings', str(cm.exception))

    def test_property_views_edge_cases(self):
        # 1. Enquire about own property (buyer who owns the listing)
        buyer_owner = UserFactory.create(role='BY')
        self.property.owner = buyer_owner
        self.property.save()
        self.auth(buyer_owner)
        res_own_enquiry = self.client.post(
            reverse('property:post_enquiry', args=[self.property.slug]),
            {'message': 'I am interested in my own property'}
        )
        self.assertEqual(res_own_enquiry.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot enquire about your own property', res_own_enquiry.data['errors'])

        # 2. Unauthenticated GET /properties/ hits anonymous branch line 198
        self.client.credentials()  # clear auth
        res_anon_list = self.client.get(reverse('property:create_and_list_property'))
        self.assertEqual(res_anon_list.status_code, status.HTTP_200_OK)

        # 3. PropertyStatusUpdateView patch and get_queryset
        self.auth(buyer_owner)
        res_status_so = self.client.patch(
            reverse('property:property_status', args=[self.property.slug]),
            {'status': 'SO'}
        )
        self.assertEqual(res_status_so.status_code, status.HTTP_200_OK)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'SO')
        self.assertIsNotNone(self.property.closed_at)

        # Reset to available clears closed_at
        res_status_av = self.client.patch(
            reverse('property:property_status', args=[self.property.slug]),
            {'status': 'AV'}
        )
        self.assertEqual(res_status_av.status_code, status.HTTP_200_OK)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'AV')
        self.assertIsNone(self.property.closed_at)

        # Test get_queryset branches for PropertyStatusUpdateView
        rf = APIRequestFactory()
        view = PropertyStatusUpdateView()
        req_la = rf.get('/')
        req_la.user = self.admin
        view.request = req_la
        self.assertGreaterEqual(view.get_queryset().count(), 1)

        req_anon = rf.get('/')
        req_anon.user = AnonymousUser()
        view.request = req_anon
        self.assertEqual(view.get_queryset().count(), 0)

        # Test DeleteCloudinaryResourceView get_queryset anonymous branch (line 427)
        del_view = DeleteCloudinaryResourceView()
        del_view.request = req_anon
        self.assertGreaterEqual(del_view.get_queryset().count(), 1)
