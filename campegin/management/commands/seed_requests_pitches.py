from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from campegin.models import Campaign, Pitch

class Command(BaseCommand):
    help = 'Seed the database with sample incoming requests and sent pitches for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')
        
        # Get or create dummy users
        brand, _ = User.objects.get_or_create(username='TestBrand', email='brand@test.com')
        if not brand.password:
            brand.set_password('password')
            brand.save()
            
        creator, _ = User.objects.get_or_create(username='TestCreator', email='creator@test.com')
        if not creator.password:
            creator.set_password('password')
            creator.save()

        # Seed Incoming Requests (Campaigns with status="Pending")
        c1, _ = Campaign.objects.get_or_create(
            name='Summer Campaign Request',
            brand=brand,
            creator=creator,
            status='Pending',
            defaults={
                'budget': 1500.00,
                'start_date': 'July 01',
                'brief': 'Looking for lifestyle summer content.',
                'category': 'Fashion',
                'delivery_language': 'English'
            }
        )
        self.stdout.write(f'Incoming request created: {c1.name}')
        
        c2, _ = Campaign.objects.get_or_create(
            name='Tech Gadget Review',
            brand=brand,
            creator=creator,
            status='Pending',
            defaults={
                'budget': 2500.00,
                'start_date': 'July 15',
                'brief': 'Review our latest smart watch.',
                'category': 'Technology',
                'delivery_language': 'English'
            }
        )
        self.stdout.write(f'Incoming request created: {c2.name}')

        # Seed Sent Pitches (Pitch model)
        p1, _ = Pitch.objects.get_or_create(
            campaign_name='Athletic Wear Drop',
            creator=creator,
            brand=brand,
            defaults={
                'budget': 3200.00,
                'sent_date': 'May 20',
                'tags': ["Fitness", "Sports"],
                'status': 'pending',
                'description': "I'd love to showcase your athletic collection through a 30-day fitness challenge series.",
                'deliverables': ["4× TikTok videos", "2× Instagram Reels"],
            }
        )
        self.stdout.write(f'Sent pitch created: {p1.campaign_name}')

        p2, _ = Pitch.objects.get_or_create(
            campaign_name='Skincare Launch',
            creator=creator,
            brand=brand,
            defaults={
                'budget': 2500.00,
                'sent_date': 'May 17',
                'tags': ["Beauty", "Wellness"],
                'status': 'counter_offer',
                'description': "Authentic skincare routine featuring your hero serums for AM/PM routines.",
                'deliverables': ["3× TikTok videos", "1× Instagram carousel"],
                'counter_offer': 2200.00
            }
        )
        self.stdout.write(f'Sent pitch created: {p2.campaign_name}')

        p3, _ = Pitch.objects.get_or_create(
            campaign_name='Product Review Series',
            creator=creator,
            brand=brand,
            defaults={
                'budget': 4800.00,
                'sent_date': 'May 14',
                'tags': ["Tech", "Lifestyle"],
                'status': 'accepted',
                'description': "Detailed product reviews with authentic usage demos for your latest gadgets.",
                'deliverables': ["2× YouTube videos", "3× Instagram posts"],
            }
        )
        self.stdout.write(f'Sent pitch created: {p3.campaign_name}')

        self.stdout.write(self.style.SUCCESS('Successfully seeded data'))
