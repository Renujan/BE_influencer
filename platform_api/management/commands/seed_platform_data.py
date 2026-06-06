from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from platform_api.models import (
    Niche, UserProfile, CreatorSocialAccount, Campaign, CampaignTask,
    CampaignMilestone, Deliverable, PaymentInstallment, WorkspaceFile,
    WorkspaceMessage, AdminComplianceTicket
)
from rest_framework.authtoken.models import Token

class Command(BaseCommand):
    help = "Seeds the database with default mockup data for influencers, brands, and campaigns"

    def handle(self, *args, **options):
        self.stdout.write("Seeding platform database...")

        # 1. Niches
        niche_names = ["Fashion", "Beauty", "Travel", "Food", "Tech", "Fitness", "Gaming", "Lifestyle", "Music", "Finance"]
        niches = {}
        for name in niche_names:
            niche, _ = Niche.objects.get_or_create(name=name)
            niches[name] = niche
        self.stdout.write("Niches created.")

        # 2. Creators
        creators_data = [
            {
                "username": "maya",
                "first_name": "Maya",
                "last_name": "Chen",
                "email": "maya@example.com",
                "location": "Tokyo, JP",
                "bio": "Curating beautiful moments and honest reviews. Worked with 40+ premium brands across travel and lifestyle.",
                "wallet_balance": 8420.50,
                "next_payout_date": "May 15",
                "niches": ["Lifestyle", "Travel", "Fashion"],
                "socials": [
                    {"platform": "instagram", "username": "@mayachen", "followers": "1.2M", "er": 8.20, "is_connected": True},
                    {"platform": "youtube", "username": "Maya Chen", "followers": "320K", "er": 6.10, "is_connected": True},
                    {"platform": "tiktok", "username": "@mayachen", "followers": "—", "er": 0.00, "is_connected": False},
                ]
            },
            {
                "username": "james",
                "first_name": "James",
                "last_name": "Okafor",
                "email": "james@example.com",
                "location": "Lagos, NG",
                "bio": "Exploring tech solutions, coding, gadgets, and reviews.",
                "wallet_balance": 1500.00,
                "niches": ["Tech", "Gaming"],
                "socials": [
                    {"platform": "instagram", "username": "@james_ok", "followers": "880K", "er": 7.40, "is_connected": True},
                    {"platform": "youtube", "username": "James Tech", "followers": "440K", "er": 6.80, "is_connected": True},
                ]
            },
            {
                "username": "priya",
                "first_name": "Priya",
                "last_name": "Nair",
                "email": "priya@example.com",
                "location": "Mumbai, IN",
                "bio": "Beauty tips, skincare routines, and cosmetics audits.",
                "wallet_balance": 0.00,
                "niches": ["Beauty", "Lifestyle"],
                "socials": [
                    {"platform": "instagram", "username": "@priya_nair", "followers": "640K", "er": 6.90, "is_connected": True},
                ]
            },
            {
                "username": "lia",
                "first_name": "Lia",
                "last_name": "Park",
                "email": "lia@example.com",
                "location": "Seoul, KR",
                "bio": "Solo wanderlust and travel tips in South Korea and Asia.",
                "wallet_balance": 6500.00,
                "niches": ["Travel", "Food"],
                "socials": [
                    {"platform": "instagram", "username": "@lia_travels", "followers": "420K", "er": 6.10, "is_connected": True},
                ]
            },
            {
                "username": "marco",
                "first_name": "Marco",
                "last_name": "Vinci",
                "email": "marco@example.com",
                "location": "Milan, IT",
                "bio": "High street fashion and classic Italian design blogs.",
                "wallet_balance": 0.00,
                "niches": ["Fashion"],
                "socials": [
                    {"platform": "instagram", "username": "@marco_vinci", "followers": "1.8M", "er": 5.80, "is_connected": True},
                ]
            }
        ]

        users = {}
        for c in creators_data:
            user, created = User.objects.get_or_create(username=c["username"], email=c["email"])
            if created or not user.password:
                user.set_password("password123")
                user.first_name = c["first_name"]
                user.last_name = c["last_name"]
                user.save()
            
            # Auth Token
            Token.objects.get_or_create(user=user)

            # Profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = "influencer"
            profile.location = c["location"]
            profile.bio = c["bio"]
            profile.wallet_balance = c["wallet_balance"]
            profile.next_payout_date = c.get("next_payout_date", "")
            profile.save()

            # Niches
            profile.niches.clear()
            for n_name in c["niches"]:
                profile.niches.add(niches[n_name])

            # Socials
            CreatorSocialAccount.objects.filter(user=user).delete()
            for s in c["socials"]:
                CreatorSocialAccount.objects.create(
                    user=user,
                    platform=s["platform"],
                    username=s["username"],
                    followers_count=s["followers"],
                    engagement_rate=s["er"],
                    is_connected=s["is_connected"]
                )
            users[c["username"]] = user

        self.stdout.write("Creators created.")

        # 3. Brands/Businesses
        brands_data = [
            {
                "username": "alex",
                "first_name": "Alex",
                "last_name": "BrandManager",
                "email": "alex@acme.com",
                "company_name": "Acme Inc.",
                "business_type": "DTC Brand",
                "website": "https://acme.com"
            },
            {
                "username": "vertex",
                "first_name": "Vertex",
                "last_name": "Admin",
                "email": "info@vertex.com",
                "company_name": "Vertex",
                "business_type": "Enterprise",
                "website": "https://vertex.com"
            },
            {
                "username": "forma",
                "first_name": "Forma",
                "last_name": "Admin",
                "email": "info@forma.com",
                "company_name": "Forma",
                "business_type": "Agency",
                "website": "https://forma.com"
            },
            {
                "username": "lumen",
                "first_name": "Lumen",
                "last_name": "Admin",
                "email": "info@lumen.com",
                "company_name": "Lumen",
                "business_type": "DTC Brand",
                "website": "https://lumenbeauty.com"
            },
            {
                "username": "aurora",
                "first_name": "Aurora",
                "last_name": "Admin",
                "email": "info@aurora.com",
                "company_name": "Aurora",
                "business_type": "DTC Brand",
                "website": "https://aurorafit.com"
            }
        ]

        for b in brands_data:
            user, created = User.objects.get_or_create(username=b["username"], email=b["email"])
            if created or not user.password:
                user.set_password("password123")
                user.first_name = b["first_name"]
                user.last_name = b["last_name"]
                user.save()
            
            # Auth Token
            Token.objects.get_or_create(user=user)

            # Profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = "business"
            profile.company_name = b["company_name"]
            profile.business_type = b["business_type"]
            profile.website = b["website"]
            profile.save()
            
            users[b["username"]] = user

        self.stdout.write("Brands created.")

        # Clear existing campaigns to avoid duplicates
        Campaign.objects.all().delete()

        # 4. Campaign 1: "Summer Drop 2026"
        c1 = Campaign.objects.create(
            name="Summer Drop 2026",
            brand=users["alex"],
            creator=users["maya"],
            status="Live",
            budget=4200.00,
            start_date="May 12",
            progress=62,
            brief="3-post Instagram series + 1 reel showcasing the new spring collection. Brand voice: warm, modern, confident."
        )
        
        # Tasks for c1
        CampaignTask.objects.create(campaign=c1, title="Brief approval", is_done=True)
        CampaignTask.objects.create(campaign=c1, title="Content moodboard", is_done=True)
        CampaignTask.objects.create(campaign=c1, title="Draft #1 review", is_done=False, due_date="May 14")
        CampaignTask.objects.create(campaign=c1, title="Final delivery", is_done=False, due_date="May 18")

        # Milestones for c1
        CampaignMilestone.objects.create(campaign=c1, title="Kickoff", is_done=True)
        CampaignMilestone.objects.create(campaign=c1, title="Drafts approved", is_done=True)
        CampaignMilestone.objects.create(campaign=c1, title="Content live", is_done=False)
        CampaignMilestone.objects.create(campaign=c1, title="Final payout", is_done=False)

        # Deliverables for c1
        Deliverable.objects.create(
            campaign=c1, name="Reel #1", type="reel", status="Revision Requested", deadline="May 14",
            brief="Showcase the new Summer Collection in a 15-second high-energy Reel. Focus on seamless outfit transitions and vibrant summer styling."
        )
        Deliverable.objects.create(
            campaign=c1, name="Reel #2", type="reel", status="Approved", deadline="May 16",
            brief="Unboxing experience and first-impression review of the signature beach bag. Keep the tone organic and focus on details.",
            link="https://instagram.com/reel/C7a9k2N1sP", screenshot_name="analytics_reel2.png"
        )
        Deliverable.objects.create(
            campaign=c1, name="Post #1", type="post", status="Published", deadline="May 18",
            brief="Carousel feed post detailing 3 unique ways to style the brand's graphic tee. Include a discount code in the caption.",
            link="https://instagram.com/p/C6b8m3K4vQ", screenshot_name="analytics_post1.png"
        )
        Deliverable.objects.create(
            campaign=c1, name="Post #3", type="post", status="Revision Requested", deadline="May 20",
            brief="City lifestyle photo highlighting the brand's activewear set in a natural urban park setting."
        )

        # Payments for c1
        PaymentInstallment.objects.create(campaign=c1, milestone_name="Kickoff payment", amount=1000.00, status="Released", payment_date="May 02")
        PaymentInstallment.objects.create(campaign=c1, milestone_name="Drafts approved", amount=1500.00, status="Released", payment_date="May 10")
        PaymentInstallment.objects.create(campaign=c1, milestone_name="Final delivery", amount=1700.00, status="In Escrow")

        # Files for c1
        WorkspaceFile.objects.create(campaign=c1, name="Brief.pdf", size="2.4 MB", sender=users["alex"], date="May 10, 2026", time="10:32 AM")
        WorkspaceFile.objects.create(campaign=c1, name="Moodboard.zip", size="14.8 MB", sender=users["maya"], date="May 11, 2026", time="02:15 PM")
        WorkspaceFile.objects.create(campaign=c1, name="Logo-pack.zip", size="8.2 MB", sender=users["alex"], date="May 11, 2026", time="04:40 PM")
        WorkspaceFile.objects.create(campaign=c1, name="Draft-v1.mp4", size="45.1 MB", sender=users["maya"], date="May 12, 2026", time="09:12 AM")
        WorkspaceFile.objects.create(campaign=c1, name="Contract.pdf", size="1.1 MB", sender=users["alex"], date="May 12, 2026", time="11:05 AM")
        WorkspaceFile.objects.create(campaign=c1, name="Invoice.pdf", size="640 KB", sender=users["maya"], date="May 13, 2026", time="03:20 PM")

        # Messages for c1
        WorkspaceMessage.objects.create(campaign=c1, sender=users["alex"], text="Hey Maya! Just shared the moodboard — let me know your thoughts ✨", time="10:24")
        WorkspaceMessage.objects.create(campaign=c1, sender=users["maya"], text="Love the direction! Thinking we add a sunset shoot day 2.", time="10:31")
        WorkspaceMessage.objects.create(campaign=c1, sender=users["alex"], text="Perfect. Sending the brief PDF now.", file_attachment="Summer-Drop-Brief.pdf", time="10:32")
        WorkspaceMessage.objects.create(campaign=c1, sender=users["maya"], text="Got it. I'll send drafts by Friday 🙌", time="10:35")

        # Tickets for c1
        AdminComplianceTicket.objects.create(
            campaign=c1, category="Contract Check", message="Requesting admin to verify milestone #2 escrow setup.", date="May 19",
            status="Resolved", reply="Escrow verified. Funds of $1,500 are safely secured in compliance with platform guidelines."
        )
        AdminComplianceTicket.objects.create(
            campaign=c1, category="Safety Compliance", message="Automatic audit of real-time chat messages.", date="May 20",
            status="Approved", reply="Audited chat contents contain no violation. Protection active."
        )

        # 5. Campaign 2: "Festival Series" (Completed)
        c2 = Campaign.objects.create(
            name="Festival Series",
            brand=users["forma"],
            creator=users["maya"],
            status="Completed",
            budget=6500.00,
            start_date="Apr 28",
            progress=100,
            brief="Social coverage of summer music festival."
        )
        PaymentInstallment.objects.create(campaign=c2, milestone_name="Milestone release", amount=6500.00, status="Released", payment_date="May 08")

        # 6. Campaign 3: "Sneaker Launch" (Live)
        c3 = Campaign.objects.create(
            name="Sneaker Launch",
            brand=users["vertex"],
            creator=users["james"],
            status="Live",
            budget=8900.00,
            start_date="May 09",
            progress=30,
            brief="Review and unboxing of new runner sneakers."
        )

        # 7. Campaign 4: "Skincare Edit" (Pending Request)
        c4 = Campaign.objects.create(
            name="Skincare Edit",
            brand=users["lumen"],
            creator=users["priya"],
            status="Pending",
            budget=2400.00,
            start_date="May 05",
            progress=0,
            brief="Skincare review with hero routine pack."
        )

        # 8. Campaign 5: "Holiday Teaser" (Live)
        c5 = Campaign.objects.create(
            name="Holiday Teaser",
            brand=users["alex"],
            creator=users["marco"],
            status="Live",
            budget=3800.00,
            start_date="Apr 21",
            progress=15,
            brief="Teaser campaign for the holiday winter drop."
        )

        self.stdout.write("Campaigns and safety workflows seeded.")
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully."))
