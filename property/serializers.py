import json

from rest_framework import serializers

from property.models import (
    Amenity,
    BuyerPropertyList,
    NearbyFeature,
    Property,
    PropertyEnquiry,
    MAX_PROPERTY_IMAGE_COUNT,
)

from property.validators import (
    validate_address, validate_coordinates, validate_image_list,
    validate_visit_date)


class AmenitySerializer(serializers.ModelSerializer):
    """Serializer for the predefined amenity catalogue."""

    group_display = serializers.CharField(
        source='get_group_display', read_only=True)

    class Meta:
        model = Amenity
        fields = ('id', 'name', 'group', 'group_display', 'icon')


class NearbyFeatureSerializer(serializers.ModelSerializer):
    """Serializer for the predefined nearby-feature catalogue."""

    class Meta:
        model = NearbyFeature
        fields = ('id', 'name', 'icon')


class PropertySerializer(serializers.ModelSerializer):
    """This class handles serializing and
       deserializing of Property objects"""

    price = serializers.FloatField()
    lot_size = serializers.FloatField()
    image_others = serializers.ListField(
        required=False, validators=[validate_image_list])
    address = serializers.JSONField(validators=[validate_address])
    coordinates = serializers.JSONField(validators=[validate_coordinates])
    owner = serializers.SerializerMethodField()
    amenities = serializers.PrimaryKeyRelatedField(
        many=True, required=False,
        queryset=Amenity.active_objects.all_objects().filter(is_active=True))
    nearby = serializers.PrimaryKeyRelatedField(
        many=True, required=False,
        queryset=NearbyFeature.active_objects.all_objects().filter(
            is_active=True))

    class Meta:
        model = Property
        exclude = ('is_deleted',)
        read_only_fields = ('view_count', 'slug', 'is_deleted',
                            'is_published', 'status', 'closed_at',
                            'list_date', 'owner')

    def get_owner(self, obj):
        """Expose safe, public details about the listing owner."""
        return {
            'id': obj.owner.pk,
            'email': obj.owner.email,
            'first_name': obj.owner.first_name,
            'last_name': obj.owner.last_name,
        }

    def to_representation(self, instance):
        """Render amenities and nearby features as objects, not ids."""
        rep = super().to_representation(instance)
        rep['amenities'] = AmenitySerializer(
            instance.amenities.all(), many=True).data
        rep['nearby'] = NearbyFeatureSerializer(
            instance.nearby.all(), many=True).data
        return rep

    def validate_image_others(self, image_others):
        """Enforce the photo cap: 1 main image + MAX_PROPERTY_IMAGE_COUNT."""
        if image_others and len(image_others) > MAX_PROPERTY_IMAGE_COUNT:
            raise serializers.ValidationError(
                f'You can upload a maximum of {MAX_PROPERTY_IMAGE_COUNT + 1} '
                f'photos: 1 main photo and {MAX_PROPERTY_IMAGE_COUNT} others.')
        return image_others

    def validate(self, data):
        """Cross-field validation for listing and property types."""
        listing_type = data.get(
            'listing_type',
            self.instance.listing_type if self.instance else 'S')
        rent_period = data.get(
            'rent_period',
            self.instance.rent_period if self.instance else None)
        property_type = data.get(
            'property_type',
            self.instance.property_type if self.instance else 'H')

        if listing_type == 'R' and not rent_period:
            raise serializers.ValidationError({
                'rent_period':
                'Please provide a rent period (Monthly or Yearly) '
                'for rental listings.'})
        if listing_type == 'S':
            data['rent_period'] = None
        if property_type == 'L':
            # land has no rooms
            data['bedrooms'] = None
            data['bathrooms'] = None
            data['garages'] = None
        return data

    def update(self, instance, validated_data):
        """
        Define how images and videos are updated and deleted. All other fields
        are updated the default way.
        All new images are appended to the list of images in the database.
        """
        # Ensure that read-only fields cannot be updated by the user
        for key, value in validated_data.copy().items():
            if key in self.Meta.read_only_fields:
                validated_data.pop(key)

        # Update the list of images in the database if any image is passed.

        if instance.image_others:
            images_in_DB = instance.image_others.copy()
        else:
            images_in_DB = []

        updated_image_list = validated_data.pop('image_others', None)

        if updated_image_list:
            for image in updated_image_list:
                images_in_DB.append(image)

        # Update the main image if it is passed. We won't delete
        # the older image. It is instead added to the `image_others`
        updated_main_image = validated_data.pop('image_main', None)
        if updated_main_image:
            current_main_image = instance.image_main
            instance.image_main = updated_main_image[0]
            images_in_DB.append(current_main_image)

        if len(images_in_DB) > MAX_PROPERTY_IMAGE_COUNT:
            raise serializers.ValidationError({
                'image_others':
                f'This listing can only have {MAX_PROPERTY_IMAGE_COUNT + 1} '
                f'photos in total. Please delete an existing photo first.'})
        instance.image_others = images_in_DB

        # update video
        updated_video = validated_data.pop('video', None)

        if updated_video:
            # The old video is replaced
            instance.video = updated_video[0]

        # we need to ensure that coordinates and addresses are decoded
        # before they can be saved
        coordinates = validated_data.pop('coordinates', None)
        if isinstance(coordinates, str):
            validated_data['coordinates'] = json.loads(coordinates)

        address = validated_data.pop('address', None)
        if isinstance(address, str):
            validated_data['address'] = json.loads(address)

        instance.save()
        return super().update(instance, validated_data)


class PropertyStatusSerializer(serializers.ModelSerializer):
    """Allow an owner to mark their listing Available, Rented or Sold."""

    class Meta:
        model = Property
        fields = ('status',)

    def validate_status(self, value):
        listing_type = self.instance.listing_type if self.instance else 'S'
        if value == 'RE' and listing_type != 'R':
            raise serializers.ValidationError(
                'Only rental listings can be marked as rented.')
        if value == 'SO' and listing_type != 'S':
            raise serializers.ValidationError(
                'Only sale listings can be marked as sold.')
        return value


class BuyerPropertyListSerializer(serializers.ModelSerializer):
    """
    Class handling serialization and deserialization
    of BuyerPropertyList objects.
    """

    property_of_interest = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = BuyerPropertyList
        exclude = ('created_at', 'updated_at', 'is_deleted', 'id')


class PropertyEnquirySerializer(serializers.ModelSerializer):
    """ serializer class for property Enquiry """
    visit_date = serializers.DateTimeField(validators=[validate_visit_date])

    class Meta:
        model = PropertyEnquiry
        fields = ['enquiry_id', 'visit_date', 'message']

    def update(self, instance, validated_data):
        """ update an existing enquiry """

        instance.message = validated_data.get('message', instance.message)
        instance.visit_date = validated_data.get(
            'visit_date', instance.visit_date)

        instance.save()
        return instance
