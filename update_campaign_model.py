import re

with open("campegin/models.py", "r") as f:
    content = f.read()

if "country = models.CharField" not in content:
    content = content.replace(
        '    delivery_language = models.CharField(max_length=100, blank=True, null=True)',
        '    delivery_language = models.CharField(max_length=100, blank=True, null=True)\n    country = models.CharField(max_length=100, blank=True, null=True)\n    medium = models.CharField(max_length=100, blank=True, null=True)'
    )
    content = content.replace(
        "        FieldPanel('delivery_language'),",
        "        FieldPanel('delivery_language'),\n        FieldPanel('country'),\n        FieldPanel('medium'),"
    )
    with open("campegin/models.py", "w") as f:
        f.write(content)

with open("campegin/serializers.py", "r") as f:
    content = f.read()

if '"country", "medium"' not in content:
    content = content.replace(
        '"category", "delivery_language",',
        '"category", "delivery_language", "country", "medium",'
    )
    with open("campegin/serializers.py", "w") as f:
        f.write(content)
