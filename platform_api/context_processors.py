from django.db.models import Sum, Count
from django.contrib.auth.models import User
from platform_api.models import UserProfile, Campaign, CreatorSocialAccount, Deliverable, PaymentInstallment, AdminComplianceTicket
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

    total_influencers = UserProfile.objects.filter(role="influencer").count()
    total_brands = UserProfile.objects.filter(role="business").count()

    # 2. Budget and Escrow calculations
    total_budget = Campaign.objects.aggregate(total=Sum('budget'))['total'] or 0.0
    released_payments = PaymentInstallment.objects.filter(status="Released").aggregate(total=Sum('amount'))['total'] or 0.0
    escrow_payments = PaymentInstallment.objects.filter(status="In Escrow").aggregate(total=Sum('amount'))['total'] or 0.0
    funded_payments = PaymentInstallment.objects.filter(status="Funded").aggregate(total=Sum('amount'))['total'] or 0.0
    
    total_escrow_balance = float(escrow_payments) + float(funded_payments)

    # 3. Compliance and dispute tickets
    total_tickets = AdminComplianceTicket.objects.count()
    pending_tickets = AdminComplianceTicket.objects.filter(status="Pending Review").count()
    resolved_tickets = AdminComplianceTicket.objects.filter(status="Resolved").count()
    approved_tickets = AdminComplianceTicket.objects.filter(status="Approved").count()

    # 4. Deliverables breakdown
    total_deliverables = Deliverable.objects.count()
    approved_deliverables = Deliverable.objects.filter(status="Approved").count()
    published_deliverables = Deliverable.objects.filter(status="Published").count()
    revision_deliverables = Deliverable.objects.filter(status="Revision Requested").count()

    # 5. Lists for tables
    recent_tickets = AdminComplianceTicket.objects.select_related('campaign').order_by('-id')[:5]
    top_campaigns = Campaign.objects.select_related('brand', 'creator').order_by('-budget')[:5]
    top_creators = CreatorSocialAccount.objects.select_related('user').order_by('-engagement_rate')[:5]

    # 6. Notifications tracking
    unread_notifications_count = Notification.objects.filter(is_read=False).count()
    recent_notifications = Notification.objects.all().order_by('-id')[:10]

    # 7. Weekly statistics mockup for the performance chart
    # Build chart data mapping campaigns by status or budget allocation
    chart_budgets = []
    chart_names = []
    for camp in Campaign.objects.order_by('-budget')[:6]:
        chart_budgets.append(float(camp.budget))
        chart_names.append(camp.name[:15] + '...' if len(camp.name) > 15 else camp.name)

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
        'total_deliverables': total_deliverables,
        'approved_deliverables': approved_deliverables,
        'published_deliverables': published_deliverables,
        'revision_deliverables': revision_deliverables,
        'recent_tickets': recent_tickets,
        'top_campaigns': top_campaigns,
        'top_creators': top_creators,
        'chart_budgets': chart_budgets,
        'chart_names': chart_names,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }
