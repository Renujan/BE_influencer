from wagtail import hooks
from wagtail.admin.menu import MenuItem
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from .views import admin_ratecard_list_view, admin_ratecard_detail_view


@hooks.register("register_admin_urls")
def register_ratecard_admin_urls():
    return [
        path("rate-cards/", admin_ratecard_list_view, name="admin_ratecard_list"),
        path("rate-cards/<int:creator_id>/", admin_ratecard_detail_view, name="admin_ratecard_detail"),
    ]


@hooks.register("register_admin_menu_item")
def register_rate_cards_sidebar_menu():
    return MenuItem(
        "Rate Cards",
        reverse("admin_ratecard_list"),
        icon_name="doc-full",
        order=190,
    )


@hooks.register("insert_global_admin_css")
def rate_card_admin_css():
    return mark_safe(
        """
        <style>
            /* Enable horizontal scroll on Wagtail listing tables & snippet tables */
            .w-table-wrapper,
            .listing-wrapper,
            .table-wrapper,
            div:has(> table.listing),
            div:has(> table.w-table) {
                overflow-x: auto !important;
                max-width: 100% !important;
                -webkit-overflow-scrolling: touch !important;
            }
            table.listing, .w-table {
                width: max-content !important;
                min-width: 100% !important;
            }
            table.listing td, table.listing th, .w-table td, .w-table th {
                white-space: nowrap !important;
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
            }

            /* Hide any legacy Add Rate Card button/link in Wagtail admin */
            a[href*="/ratecard/add/"],
            a[href*="/ratecard/new/"],
            a[href*="/snippets/RateCard/ratecard/add/"],
            a[href*="/snippets/ratecard/ratecard/add/"],
            .header-title .action-button[href*="ratecard"],
            .action-button[href*="ratecard/add"],
            a.button[href*="ratecard/add"] {
                display: none !important;
            }
        </style>
        """
    )
