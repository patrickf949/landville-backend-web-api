import factory
from factory.django import DjangoModelFactory
from faker import Faker
import pytz

from django.utils.timezone import now

from property.models import (
    Property, PropertyEnquiry, PropertyInspection,
    PropertyReview, BuyerPropertyList)

from .authentication_factory import UserFactory, ClientFactory

fake = Faker()
address = {'City': fake.city(), 'Street': fake.street_name(),
           'State': fake.state()}
coordinates = {'lat': '25354.231', 'lon': '45235.0343'}


class PropertyFactory(DjangoModelFactory):
    """This class creates fake property"""

    class Meta:
        model = Property

    title = fake.word()
    address = address
    coordinates = coordinates
    owner = factory.SubFactory(UserFactory)
    listing_type = 'S'
    property_type = 'H'
    description = fake.sentences()
    list_date = now()
    price = 2452345234.43
    lot_size = 2345.435
    image_main = fake.url()
    image_others = [fake.url(), fake.url()]
    last_viewed = now()
    status = 'AV'
    is_published = False


class PropertyEnquiryFactory(DjangoModelFactory):
    """This class creates fake property enquiry"""

    class Meta:
        model = PropertyEnquiry
    enquiry_id = fake.name()
    requester = factory.SubFactory(UserFactory)
    target_property = factory.SubFactory(PropertyFactory)
    visit_date = fake.date_time_between(
        start_date="+3y", end_date="+20y", tzinfo=pytz.UTC)
    message = fake.sentences()


class PropertyReviewFactory(DjangoModelFactory):
    """This class creates fake property reviews"""

    class Meta:
        model = PropertyReview

    reviewer = factory.SubFactory(UserFactory)
    target_property = factory.SubFactory(PropertyFactory)
    comment = fake.sentences()


class PropertyInspectionFactory(DjangoModelFactory):
    """This calss creates fake property inspections"""

    class Meta:
        model = PropertyInspection

    requester = factory.SubFactory(UserFactory)
    target_property = factory.SubFactory(PropertyFactory)
    inspection_time = now()
    remarks = fake.sentences()


class BuyerPropertyListFactory(DjangoModelFactory):
    """This calss creates fake property inspections"""

    class Meta:
        model = BuyerPropertyList

    buyer = factory.SubFactory(UserFactory)
    listed_property = factory.SubFactory(PropertyFactory)
