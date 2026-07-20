import re

with open("user/models.py", "r") as f:
    content = f.read()

# Replace Country model
old_country = """class Country(ClusterableModel):
    name = models.CharField(max_length=100, unique=True)
    
    panels = [
        FieldPanel("name"),
        InlinePanel("provinces", label="Provinces", heading="Provinces"),
    ]"""

new_country = """class Country(ClusterableModel):
    name = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=50, blank=True, null=True)
    country_code = models.CharField(max_length=10, blank=True, null=True)
    
    panels = [
        FieldPanel("name"),
        FieldPanel("currency"),
        FieldPanel("country_code"),
        InlinePanel("mediums", label="Mediums", heading="Mediums"),
        InlinePanel("provinces", label="Provinces", heading="Provinces"),
        InlinePanel("districts", label="Districts", heading="Districts (Select Province)"),
    ]"""
content = content.replace(old_country, new_country)

# Replace Medium model
old_medium = """@register_snippet
class Medium(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name"""

new_medium_and_district = """class Medium(Orderable):
    country = ParentalKey(Country, on_delete=models.CASCADE, related_name="mediums")
    name = models.CharField(max_length=100)

    panels = [
        FieldPanel("name"),
    ]

    def __str__(self):
        return self.name

class District(Orderable):
    country = ParentalKey(Country, on_delete=models.CASCADE, related_name="districts")
    province = models.ForeignKey("Province", on_delete=models.CASCADE, related_name="districts_list")
    name = models.CharField(max_length=100)
    
    panels = [
        FieldPanel("province"),
        FieldPanel("name"),
    ]

    def __str__(self):
        return self.name"""

content = content.replace(old_medium, new_medium_and_district)

with open("user/models.py", "w") as f:
    f.write(content)
