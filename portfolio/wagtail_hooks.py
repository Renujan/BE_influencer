from wagtail import hooks
from django.utils.safestring import mark_safe


@hooks.register("insert_global_admin_css")
def portfolio_admin_css():
    return mark_safe(
        """
        <style>
            /* Hide any legacy Add Portfolio Item button/link in Wagtail admin */
            a[href*="/portfolioitem/add/"],
            a[href*="/portfolio/portfolioitem/add/"],
            a[href*="/snippets/portfolio/portfolioitem/add/"],
            a[href*="/snippets/Portfolio/portfolioitem/add/"],
            .header-title .action-button[href*="portfolioitem"],
            .action-button[href*="portfolioitem/add"],
            a.button[href*="portfolioitem/add"] {
                display: none !important;
            }
        </style>
        """
    )
