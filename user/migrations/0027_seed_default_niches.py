from django.db import migrations

def seed_default_creator_niches(apps, schema_editor):
    Niche = apps.get_model("user", "Niche")
    mock_niches = [
        "Lifestyle", "Beauty", "Fashion", "Fitness", "Food", "Tech",
        "Travel", "Gaming", "Parenting", "Finance", "Health", "Comedy",
        "Education", "Music", "Sports"
    ]
    for name in mock_niches:
        Niche.objects.get_or_create(name=name, defaults={"is_active": True})

def reverse_seed_default_creator_niches(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ("user", "0026_otpverification"),
    ]

    operations = [
        migrations.RunPython(seed_default_creator_niches, reverse_seed_default_creator_niches),
    ]
