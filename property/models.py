from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder

from utils.models import BaseAbstractModel
from utils.managers import CustomQuerySet, PropertyQuery, PropertyEnquiryQuery
from authentication.models import User
from utils.slug_generator import generate_unique_slug
import uuid


# assiging this as a global variable makes it easier to access it
# and use it for validators in other areas. There is now only one place
# to change if you want to alter this attribute.
# 1 main image + 4 others = 5 photos per listing.
MAX_PROPERTY_IMAGE_COUNT = 4


class Amenity(BaseAbstractModel):
    """A predefined, filterable amenity that a property can have."""

    GROUP_CHOICES = (
        ('U', 'UTILITIES'),
        ('S', 'SECURITY'),
        ('C', 'COMFORT'),
        ('A', 'ACCESS'),
        ('L', 'LAND'),
    )

    name = models.CharField(max_length=100, unique=True)
    group = models.CharField(max_length=1, choices=GROUP_CHOICES)
    icon = models.CharField(
        max_length=50, blank=True, default='',
        help_text='FontAwesome icon class, e.g. fa-wifi')
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active_objects = CustomQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'amenities'
        ordering = ['group', 'name']

    def __str__(self):
        return self.name


class NearbyFeature(BaseAbstractModel):
    """A predefined feature close to a property, e.g. a school or market."""

    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(
        max_length=50, blank=True, default='',
        help_text='FontAwesome icon class, e.g. fa-school')
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    active_objects = CustomQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Property(BaseAbstractModel):
    """This class defines the Property model"""

    LISTING_TYPES = (
        ('R', 'RENT'),
        ('S', 'SALE'),
    )

    PROPERTY_TYPES = (
        ('H', 'HOUSE'),
        ('A', 'APARTMENT'),
        ('L', 'LAND'),
        ('C', 'COMMERCIAL'),
        ('R', 'ROOM/SHARED'),
    )

    RENT_PERIODS = (
        ('M', 'MONTHLY'),
        ('Y', 'YEARLY'),
    )

    STATUS_CHOICES = (
        ('AV', 'AVAILABLE'),
        ('RE', 'RENTED'),
        ('SO', 'SOLD'),
    )

    ROAD_DISTANCES = (
        ('1', 'LESS THAN 500M'),
        ('2', '500M TO 2KM'),
        ('3', '2KM TO 5KM'),
        ('4', 'MORE THAN 5KM'),
    )

    CITY_DISTANCES = (
        ('1', 'LESS THAN 5KM'),
        ('2', '5KM TO 20KM'),
        ('3', '20KM TO 50KM'),
        ('4', 'MORE THAN 50KM'),
    )

    NOISE_LEVELS = (
        ('Q', 'QUIET'),
        ('M', 'MODERATE'),
        ('B', 'BUSY'),
    )

    title = models.CharField(max_length=255)
    address = models.JSONField(encoder=DjangoJSONEncoder)
    coordinates = models.JSONField(encoder=DjangoJSONEncoder)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='properties')
    listing_type = models.CharField(
        max_length=1, choices=LISTING_TYPES, default='S')
    property_type = models.CharField(
        max_length=1, choices=PROPERTY_TYPES, default='H')
    rent_period = models.CharField(
        max_length=1, choices=RENT_PERIODS, null=True, blank=True)
    description = models.TextField()
    list_date = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    status = models.CharField(
        max_length=2, choices=STATUS_CHOICES, default='AV')
    closed_at = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=14)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    garages = models.IntegerField(null=True, blank=True)
    lot_size = models.DecimalField(decimal_places=4, max_digits=8)
    image_main = models.URLField()
    image_others = ArrayField(models.URLField(
        unique=True), size=MAX_PROPERTY_IMAGE_COUNT, blank=True, default=list)
    video = models.URLField(unique=True, blank=True, null=True)
    view_count = models.IntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)
    slug = models.SlugField(max_length=250, unique=True)
    amenities = models.ManyToManyField(
        Amenity, blank=True, related_name='properties')
    nearby = models.ManyToManyField(
        NearbyFeature, blank=True, related_name='properties')
    distance_to_main_road = models.CharField(
        max_length=1, choices=ROAD_DISTANCES, null=True, blank=True)
    distance_to_city = models.CharField(
        max_length=1, choices=CITY_DISTANCES, null=True, blank=True)
    noise_level = models.CharField(
        max_length=1, choices=NOISE_LEVELS, null=True, blank=True)

    objects = models.Manager()
    active_objects = PropertyQuery.as_manager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Saves all the changes of the Property model"""
        if not self.slug:
            self.slug = generate_unique_slug(
                self, 'slug')
        super().save(*args, **kwargs)


class PropertyEnquiry(BaseAbstractModel):
    """This class defines the model for enquiries that are made by the user"""

    enquiry_id = models.CharField(
        max_length=100, blank=True, unique=True, default=uuid.uuid4)
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='enquiry_requester')
    target_property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='enquired_property')
    visit_date = models.DateTimeField()
    message = models.TextField(max_length=1000)
    is_resolved = models.BooleanField(default=False)

    objects = models.Manager()
    active_objects = PropertyEnquiryQuery.as_manager()

    def __str__(self):
        return f'Enquiry {self.enquiry_id} by {self.requester}'


class PropertyInspection(BaseAbstractModel):
    """This class defines the model for property inspections"""

    INSPECTION_CHOICES = (
        ('P', 'PHYSICAL INSPECTION'),
        ('V', 'VIDEO INSPECTION'),
    )

    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='requesters')
    target_property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='inspected_property')
    inspection_time = models.DateTimeField()
    remarks = models.TextField()
    inspection_mode = models.CharField(
        max_length=1, choices=INSPECTION_CHOICES, default='P')

    objects = models.Manager()
    active_objects = CustomQuerySet.as_manager()

    def __str__(self):
        return f'Inspection by {self.requester} due on {self.inspection_time}'


class PropertyReview(BaseAbstractModel):
    """This class defines the model for the property reviews"""

    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviewers')
    target_property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='reviewed_property')
    comment = models.TextField()
    is_published = models.BooleanField(default=True)

    objects = models.Manager()
    active_objects = CustomQuerySet.as_manager()

    def __str__(self):
        return f'Review by {self.reviewer} on {self.created_at}'


class BuyerPropertyList(BaseAbstractModel):
    """
    Model for users' saved properties. Contains
    the list of properties a user may be interested
    in.
    """

    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='property_of_interest')
    listed_property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='property')

    objects = models.Manager()
    active_objects = CustomQuerySet.as_manager()

    def __str__(self):
        return 'Saved properties for: ' + str(self.buyer.email)
