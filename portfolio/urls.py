from django.urls import path
from .views import portfolio_items_view, portfolio_item_detail_view

app_name = "portfolio"

urlpatterns = [
    path("items/", portfolio_items_view, name="items"),
    path("items/<int:item_id>/", portfolio_item_detail_view, name="item_detail"),
]
