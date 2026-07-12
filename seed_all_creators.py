import os
import django
import datetime
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BE_influencer.settings')
django.setup()

from django.contrib.auth.models import User
from campegin.models import Campaign, PaymentInstallment
from user.models import CreatorProfile

# Get a random brand (or the first user who is a business)
# For simplicity, we just assign the first user as the brand, or any user.
brand_user = User.objects.first()

creators = CreatorProfile.objects.all()
now = datetime.datetime.now()

for cp in creators:
    user = cp.user
    
    # Create a dummy campaign for this creator
    campaign, created = Campaign.objects.get_or_create(
        name="Demo Earnings Campaign",
        creator=user,
        defaults={
            'brand': brand_user,
            'budget': Decimal('2000.00'),
            'status': 'Live',
            'progress': 100,
        }
    )
    
    # Add a paid payment for June
    PaymentInstallment.objects.get_or_create(
        campaign=campaign,
        milestone_name="Initial Deliverable",
        amount=Decimal('850.00'),
        status="Released",
        payment_date="2026-06-15"
    )

    # Add a paid payment for July
    PaymentInstallment.objects.get_or_create(
        campaign=campaign,
        milestone_name="Final Deliverable",
        amount=Decimal('1150.00'),
        status="Released",
        payment_date="2026-07-20"
    )
    
print(f"Seeded earnings data for {creators.count()} creators.")
