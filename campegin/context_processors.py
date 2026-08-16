from django.db.models import Sum, Count
from django.contrib.auth.models import User
from django.conf import settings
from user.models import CreatorProfile, BusinessProfile, CreatorSocialAccount
from campegin.models import Campaign, Deliverable, PaymentInstallment
from complaint.models import Complaint
from notifications.models import Notification
import decimal

def dashboard_metrics(request):
    """
    Context processor to inject real-time influencer marketing statistics
    and analytics into the Wagtail admin dashboard templates.
    """
    # 1. Total statistics
    total_campaigns = Campaign.objects.count()
    live_campaigns = Campaign.objects.filter(status="Live").count()
    completed_campaigns = Campaign.objects.filter(status="Completed").count()
    pending_campaigns = Campaign.objects.filter(status="Pending").count()

    total_influencers = CreatorProfile.objects.count()
    total_brands = BusinessProfile.objects.count()

    # 2. Budget and Escrow calculations
    total_budget = Campaign.objects.aggregate(total=Sum('budget'))['total'] or 0.0
    released_payments = PaymentInstallment.objects.filter(status="Released").aggregate(total=Sum('amount'))['total'] or 0.0
    escrow_payments = PaymentInstallment.objects.filter(status="In Escrow").aggregate(total=Sum('amount'))['total'] or 0.0
    funded_payments = PaymentInstallment.objects.filter(status="Funded").aggregate(total=Sum('amount'))['total'] or 0.0
    
    total_escrow_balance = float(escrow_payments) + float(funded_payments)

    # 3. Complaints and support dispute tickets
    total_tickets = Complaint.objects.count()
    pending_tickets = Complaint.objects.filter(status="pending").count()
    resolved_tickets = Complaint.objects.filter(status="resolved").count()
    investigating_tickets = Complaint.objects.filter(status="investigating").count()
    approved_tickets = resolved_tickets

    # 4. Deliverables breakdown
    total_deliverables = Deliverable.objects.count()
    approved_deliverables = Deliverable.objects.filter(status="Approved").count()
    published_deliverables = Deliverable.objects.filter(status="Published").count()
    revision_deliverables = Deliverable.objects.filter(status="Revision Requested").count()

    # 5. Lists for tables
    recent_tickets = Complaint.objects.select_related('user', 'campaign').order_by('-id')[:5]
    top_campaigns = Campaign.objects.select_related('brand', 'creator').order_by('-budget')[:5]
    top_creators = CreatorSocialAccount.objects.select_related('user', 'user__creator_profile').order_by('-is_connected', '-followers_count', '-id')[:5]

    # 6. Notifications tracking — only show unread in the admin bell dropdown
    unread_notifications_count = Notification.objects.filter(is_read=False).count()
    recent_notifications = Notification.objects.filter(is_read=False).order_by('-id')[:10]

    # 7. Weekly statistics mockup for the performance chart
    # Build chart data mapping campaigns by status or budget allocation
    chart_budgets = []
    chart_names = []
    for camp in Campaign.objects.order_by('-budget')[:6]:
        chart_budgets.append(float(camp.budget))
        chart_names.append(camp.name[:15] + '...' if len(camp.name) > 15 else camp.name)

    # 8. User's currency format & symbol determination
    from campegin.models import extract_currency_symbol
    user_currency_symbol = "Rs"
    user_currency_format = "LKR (Rs)"
    if request and hasattr(request, "user") and request.user and request.user.is_authenticated:
        try:
            if hasattr(request.user, "creator_profile") and request.user.creator_profile:
                cp = request.user.creator_profile
                if hasattr(cp, "settings") and cp.settings and cp.settings.currency:
                    user_currency_format = cp.settings.currency
                    user_currency_symbol = extract_currency_symbol(cp.settings.currency) or "Rs"
                elif cp.country and cp.country.currency:
                    user_currency_format = cp.country.currency
                    user_currency_symbol = extract_currency_symbol(cp.country.currency) or "Rs"
        except Exception:
            pass
        try:
            if hasattr(request.user, "business_profile") and request.user.business_profile:
                bp = request.user.business_profile
                if hasattr(bp, "settings") and bp.settings and bp.settings.currency:
                    user_currency_format = bp.settings.currency
                    user_currency_symbol = extract_currency_symbol(bp.settings.currency) or "Rs"
                elif bp.country and bp.country.currency:
                    user_currency_format = bp.country.currency
                    user_currency_symbol = extract_currency_symbol(bp.country.currency) or "Rs"
        except Exception:
            pass

    return {
        'total_campaigns': total_campaigns,
        'live_campaigns': live_campaigns,
        'completed_campaigns': completed_campaigns,
        'pending_campaigns': pending_campaigns,
        'total_influencers': total_influencers,
        'total_brands': total_brands,
        'total_budget': float(total_budget),
        'released_payments': float(released_payments),
        'escrow_payments': float(escrow_payments),
        'total_escrow_balance': total_escrow_balance,
        'total_tickets': total_tickets,
        'pending_tickets': pending_tickets,
        'resolved_tickets': resolved_tickets,
        'approved_tickets': approved_tickets,
        'investigating_tickets': investigating_tickets,
        'total_deliverables': total_deliverables,
        'approved_deliverables': approved_deliverables,
        'published_deliverables': published_deliverables,
        'revision_deliverables': revision_deliverables,
        'recent_tickets': recent_tickets,
        'top_campaigns': top_campaigns,
        'top_creators': top_creators,
        'chart_budgets': chart_budgets,
        'chart_names': chart_names,
        'user_currency_symbol': user_currency_symbol,
        'user_currency_format': user_currency_format,
        'currency_symbol': user_currency_symbol,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
        'FRONTEND_URL': getattr(settings, 'FRONTEND_URL', 'http://localhost:5173'),
    }
