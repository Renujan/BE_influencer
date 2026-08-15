from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from rest_framework import viewsets, permissions

from .models import RateCard
from .serializers import RateCardSerializer
from user.models import CreatorProfile


class RateCardViewSet(viewsets.ModelViewSet):
    queryset = RateCard.objects.all().order_by("-id")
    serializer_class = RateCardSerializer
    permission_classes = [permissions.AllowAny]


# ==========================================
# Wagtail Super Admin Custom Views
# ==========================================

@user_passes_test(lambda u: u.is_staff)
def admin_ratecard_list_view(request):
    """
    Overview list of creators with their Rate Card packages.
    Accessible at: /admin/rate-cards/
    """
    query = request.GET.get("q", "").strip()

    creators_qs = CreatorProfile.objects.select_related("user", "country").prefetch_related("niches", "rates", "user__rate_cards").all()

    if query:
        creators_qs = creators_qs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(location__icontains=query) |
            Q(country__name__icontains=query) |
            Q(niches__name__icontains=query) |
            Q(rates__content_type__icontains=query) |
            Q(rates__platforms__icontains=query) |
            Q(user__rate_cards__type__icontains=query) |
            Q(user__rate_cards__platform__icontains=query)
        ).distinct()

    creators_data = []

    for cp in creators_qs:
        # Fetch rate cards for this creator
        rate_cards = list(RateCard.objects.filter(creator=cp.user).order_by("-id"))
        
        # If no direct RateCard objects, fallback to cp.rates
        if not rate_cards and cp.rates.exists():
            for r in cp.rates.all():
                rate_cards.append(RateCard(
                    creator=cp.user,
                    creator_name=cp.user.get_full_name() or cp.user.username,
                    platform=r.platforms or "General",
                    type=r.content_type or "Deliverable",
                    price=r.price or 0.00,
                    min_price=r.min_price or 0.00,
                    max_price=r.max_price or 0.00,
                    description=r.notes or "",
                    is_active=True
                ))

        pkg_count = len(rate_cards)

        prices = [float(rc.price) for rc in rate_cards if rc.price and float(rc.price) > 0]
        if not prices:
            for rc in rate_cards:
                if rc.min_price and float(rc.min_price) > 0:
                    prices.append(float(rc.min_price))
                if rc.max_price and float(rc.max_price) > 0:
                    prices.append(float(rc.max_price))

        curr_sym = cp.currency_symbol or "$"

        if prices:
            min_p = min(prices)
            max_p = max(prices)
            if min_p == max_p:
                price_range = f"{curr_sym}{min_p:,.2f}"
            else:
                price_range = f"{curr_sym}{min_p:,.0f} – {curr_sym}{max_p:,.0f}"
        else:
            price_range = "Not set"

        # Unique platforms
        platforms = set()
        for rc in rate_cards:
            if rc.platform:
                for p in rc.platform.replace(",", " ").split():
                    if p.strip():
                        platforms.add(p.strip().capitalize())

        niches_list = [n.name for n in cp.niches.all()]
        country_name = cp.country.name if cp.country else (cp.location or "—")
        location_str = cp.location or country_name

        creators_data.append({
            "id": cp.id,
            "user": cp.user,
            "username": cp.user.username,
            "full_name": f"{cp.user.first_name} {cp.user.last_name}".strip() or cp.user.username,
            "avatar_url": cp.avatar_url or "",
            "location": location_str,
            "country_name": country_name,
            "niches": niches_list,
            "packages_count": pkg_count,
            "price_range": price_range,
            "currency_symbol": curr_sym,
            "platforms": list(platforms),
        })

    # Sort creators with rate cards first
    creators_data.sort(key=lambda c: c["packages_count"], reverse=True)

    context = {
        "creators": creators_data,
        "total_creators": len(creators_data),
        "search_query": query,
    }
    return render(request, "RateCard/admin_list.html", context)


@user_passes_test(lambda u: u.is_staff)
def admin_ratecard_detail_view(request, creator_id):
    """
    Individual creator's Rate Card detail view with responsive card grid.
    Accessible at: /admin/rate-cards/<creator_id>/
    """
    creator = (
        CreatorProfile.objects.filter(pk=creator_id).select_related("user", "country").first()
        or CreatorProfile.objects.filter(user_id=creator_id).select_related("user", "country").first()
    )
    if not creator:
        return get_object_or_404(CreatorProfile, pk=creator_id)

    # Fetch RateCards
    rate_cards = list(RateCard.objects.filter(creator=creator.user).order_by("-id"))
    if not rate_cards and creator.rates.exists():
        for r in creator.rates.all():
            rate_cards.append(RateCard(
                creator=creator.user,
                creator_name=creator.user.get_full_name() or creator.user.username,
                platform=r.platforms or "General",
                type=r.content_type or "Deliverable",
                price=r.price or 0.00,
                min_price=r.min_price or 0.00,
                max_price=r.max_price or 0.00,
                description=r.notes or "",
                is_active=True
            ))

    total_packages = len(rate_cards)
    prices = [float(rc.price) for rc in rate_cards if rc.price and float(rc.price) > 0]
    if not prices:
        for rc in rate_cards:
            if rc.min_price and float(rc.min_price) > 0:
                prices.append(float(rc.min_price))
            if rc.max_price and float(rc.max_price) > 0:
                prices.append(float(rc.max_price))

    curr_sym = creator.currency_symbol or "$"

    min_price_str = f"{curr_sym}{min(prices):,.2f}" if prices else f"{curr_sym}0.00"
    max_price_str = f"{curr_sym}{max(prices):,.2f}" if prices else f"{curr_sym}0.00"
    avg_price_str = f"{curr_sym}{round(sum(prices) / len(prices), 2):,.2f}" if prices else f"{curr_sym}0.00"

    for rc in rate_cards:
        min_p = float(rc.min_price) if rc.min_price else 0.0
        max_p = float(rc.max_price) if rc.max_price else 0.0
        std_p = float(rc.price) if rc.price else 0.0
        if min_p and max_p and min_p != max_p:
            rc.formatted_display_price = f"{curr_sym}{min_p:,.0f} – {curr_sym}{max_p:,.0f}"
            rc.has_range = True
        elif min_p:
            rc.formatted_display_price = f"{curr_sym}{min_p:,.2f}"
            rc.has_range = False
        elif std_p:
            rc.formatted_display_price = f"{curr_sym}{std_p:,.2f}"
            rc.has_range = False
        else:
            rc.formatted_display_price = f"{curr_sym}0.00"
            rc.has_range = False

    platforms_set = set()
    for rc in rate_cards:
        if rc.platform:
            for p in rc.platform.replace(",", " ").split():
                if p.strip():
                    platforms_set.add(p.strip().capitalize())

    niches_list = [n.name for n in creator.niches.all()]
    country_name = creator.country.name if creator.country else ""
    location_display = creator.location or country_name or "Location not specified"

    context = {
        "creator": creator,
        "user": creator.user,
        "currency_symbol": curr_sym,
        "location_display": location_display,
        "country_name": country_name,
        "niches": niches_list,
        "rate_cards": rate_cards,
        "stats": {
            "total_packages": total_packages,
            "min_price": min_price_str,
            "max_price": max_price_str,
            "avg_price": avg_price_str,
            "platforms_count": len(platforms_set),
        },
    }
    return render(request, "RateCard/admin_detail.html", context)
