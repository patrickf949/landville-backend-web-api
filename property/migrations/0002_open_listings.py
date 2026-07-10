# Atterville open-listings migration.
# Property ownership moves from Client companies to individual users,
# listings gain rent/sale + land support, a 5-photo cap, amenities,
# and location-quality attributes.

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


def client_to_owner(apps, schema_editor):
    """Point each property at its client company's admin user."""
    Property = apps.get_model('property', 'Property')
    for prop in Property.objects.select_related('client').all():
        prop.owner = prop.client.client_admin
        prop.save(update_fields=['owner'])


def owner_to_client(apps, schema_editor):
    """Reverse: nothing sensible to restore; leave client rows untouched."""
    pass


def map_types_and_status(apps, schema_editor):
    """B->House, E->Land; is_sold -> status."""
    Property = apps.get_model('property', 'Property')
    Property.objects.filter(property_type='B').update(property_type='H')
    Property.objects.filter(property_type='E').update(property_type='L')
    Property.objects.filter(is_sold=True).update(status='SO')


def unmap_types_and_status(apps, schema_editor):
    Property = apps.get_model('property', 'Property')
    Property.objects.filter(property_type='H').update(property_type='B')
    Property.objects.exclude(property_type='B').update(property_type='E')


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('property', '0001_initial'),
    ]

    operations = [
        # --- new catalogue models -------------------------------------
        migrations.CreateModel(
            name='Amenity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('group', models.CharField(choices=[
                    ('U', 'UTILITIES'), ('S', 'SECURITY'), ('C', 'COMFORT'),
                    ('A', 'ACCESS'), ('L', 'LAND')], max_length=1)),
                ('icon', models.CharField(
                    blank=True, default='',
                    help_text='FontAwesome icon class, e.g. fa-wifi',
                    max_length=50)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'verbose_name_plural': 'amenities',
                     'ordering': ['group', 'name']},
        ),
        migrations.CreateModel(
            name='NearbyFeature',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('icon', models.CharField(
                    blank=True, default='',
                    help_text='FontAwesome icon class, e.g. fa-school',
                    max_length=50)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['name']},
        ),
        # --- new property fields --------------------------------------
        migrations.AddField(
            model_name='property',
            name='owner',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='properties', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='property',
            name='listing_type',
            field=models.CharField(choices=[('R', 'RENT'), ('S', 'SALE')],
                                   default='S', max_length=1),
        ),
        migrations.AddField(
            model_name='property',
            name='rent_period',
            field=models.CharField(
                blank=True, choices=[('M', 'MONTHLY'), ('Y', 'YEARLY')],
                max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='status',
            field=models.CharField(choices=[
                ('AV', 'AVAILABLE'), ('RE', 'RENTED'), ('SO', 'SOLD')],
                default='AV', max_length=2),
        ),
        migrations.AddField(
            model_name='property',
            name='distance_to_main_road',
            field=models.CharField(blank=True, choices=[
                ('1', 'LESS THAN 500M'), ('2', '500M TO 2KM'),
                ('3', '2KM TO 5KM'), ('4', 'MORE THAN 5KM')],
                max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='distance_to_city',
            field=models.CharField(blank=True, choices=[
                ('1', 'LESS THAN 5KM'), ('2', '5KM TO 20KM'),
                ('3', '20KM TO 50KM'), ('4', 'MORE THAN 50KM')],
                max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='noise_level',
            field=models.CharField(blank=True, choices=[
                ('Q', 'QUIET'), ('M', 'MODERATE'), ('B', 'BUSY')],
                max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='amenities',
            field=models.ManyToManyField(
                blank=True, related_name='properties', to='property.amenity'),
        ),
        migrations.AddField(
            model_name='property',
            name='nearby',
            field=models.ManyToManyField(
                blank=True, related_name='properties',
                to='property.nearbyfeature'),
        ),
        # --- data migrations -------------------------------------------
        migrations.RunPython(client_to_owner, owner_to_client),
        migrations.RunPython(map_types_and_status, unmap_types_and_status),
        # --- field alterations ------------------------------------------
        migrations.AlterField(
            model_name='property',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='properties', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='property',
            name='property_type',
            field=models.CharField(choices=[
                ('H', 'HOUSE'), ('A', 'APARTMENT'), ('L', 'LAND'),
                ('C', 'COMMERCIAL'), ('R', 'ROOM/SHARED')],
                default='H', max_length=1),
        ),
        migrations.AlterField(
            model_name='property',
            name='image_others',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.URLField(unique=True), blank=True,
                default=list, size=4),
        ),
        migrations.RenameField(
            model_name='property',
            old_name='sold_at',
            new_name='closed_at',
        ),
        # --- removals ----------------------------------------------------
        migrations.RemoveField(model_name='property', name='client'),
        migrations.RemoveField(model_name='property', name='is_sold'),
        migrations.RemoveField(model_name='property', name='purchase_plan'),
        migrations.RemoveField(model_name='propertyenquiry', name='client'),
    ]
