from property.models import Property, PropertyEnquiry
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList
from property.models import Property
from rest_framework.utils.serializer_helpers import ReturnDict
import json

from rest_framework.renderers import JSONRenderer


class PropertyJSONRenderer(JSONRenderer):
    """Properly render the responses for property views.
    Note that errors are not handled by the renderer but instead
    handled by default DRF exception handlers."""
    charset = 'utf-8'

    def single_property_format(self, data):
        """When returning property, fields choices should be returned
        as human readable values.
        For example, instead or returning `listing_type` as `R`,
        we should return `Rent`"""

        # We should only format responses. Because reqeusts don't have
        # the `id` we skip all requests
        if data.get('id'):
            instance = Property.objects.get(pk=data.get('id'))
            data['property_type'] = instance.get_property_type_display(
            ).title()
            data['listing_type'] = instance.get_listing_type_display(
            ).title()
            data['status'] = instance.get_status_display().title()
            if instance.rent_period:
                data['rent_period'] = instance.get_rent_period_display(
                ).title()
            if instance.noise_level:
                data['noise_level'] = instance.get_noise_level_display(
                ).title()
            if instance.distance_to_main_road:
                data['distance_to_main_road'] = \
                    instance.get_distance_to_main_road_display().title()
            if instance.distance_to_city:
                data['distance_to_city'] = \
                    instance.get_distance_to_city_display().title()

    def render(self, data, media_type=None, renderer_context=None):
        if isinstance(data, dict):

            errors = data.get('errors')

            if errors:
                return super().render(data)

            if type(data) == ReturnDict or type(data) == dict:
                # if the response has a `data` key, we pass the actual
                # payload to be rendered as the values in the `property`.
                try:
                    payload = data.get('data')['property']
                    if payload:
                        self.single_property_format(payload)

                    return json.dumps(data)
                except TypeError:
                    return json.dumps(data)

            results = data.get('results')

            # when getting multiple items, the actual payload is contained
            # in the `results` key because they will be paginated
            if isinstance(results, list):
                for item in results:
                    self.single_property_format(item)
                return json.dumps({
                    'data': {'properties': data}
                })

        return json.dumps({
            'data': {'property': data}
        })


class PropertyEnquiryJSONRenderer(JSONRenderer):
    """
    renderer for property enquiry for properly handling responses and 
    data that is returned
    """
    charset = "utf-8"

    def render(self, data, media_type=None, renderer_context=None):

        if isinstance(data, dict):
            errors = data.get('errors', None)

            if errors:
                return super().render(data)

            if 'ErrorDetail' in str(data):
                return json.dumps({
                    'errors': data}
                )

        return json.dumps({"data": {"enquiry": data}})
