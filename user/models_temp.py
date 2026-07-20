from user.models import *
from wagtail.admin.panels import InlinePanel
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey
from django.db import models
from wagtail.models import Orderable

class District(Orderable):
    province = ParentalKey("user.Province", on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=100)
    
Province.__bases__ = (Orderable, ClusterableModel)
Province.panels.append(InlinePanel("districts"))
