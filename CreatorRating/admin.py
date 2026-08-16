from django.contrib import admin
from .models import CreatorRating, BusinessRating

@admin.register(CreatorRating)
class CreatorRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "creator", "brand", "rating", "campaign", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("creator__username", "brand__username", "campaign__name", "review")

@admin.register(BusinessRating)
class BusinessRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "creator", "rating", "campaign", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("brand__username", "creator__username", "campaign__name", "review")

