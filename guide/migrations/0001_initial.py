from django.db import migrations, models

def seed_initial_guides(apps, schema_editor):
    Guide = apps.get_model("guide", "Guide")

    initial_guides = [
        {
            "guide_id": "GUID001-CR",
            "title": "Creator Handbook & Profile Optimization",
            "category": "handbook",
            "content": "Tips and strategies for optimizing your creator bio, connecting social channels, showcasing portfolio media, and maximizing discovery by top brands.",
            "target_audience": "creator"
        },
        {
            "guide_id": "GUID002-CR",
            "title": "Creator Protection & Earnings Guarantee",
            "category": "protection",
            "content": "How Ampli protects your work with upfront escrow funding, dispute arbitration, and secure milestone payout guarantees.",
            "target_audience": "creator"
        },
        {
            "guide_id": "GUID003-CR",
            "title": "Payment & Payout Lifecycle Guide",
            "category": "payment",
            "content": "A comprehensive breakdown of escrow deposits, milestone submissions, client approvals, fee calculations (5%), and bank payout settlement times.",
            "target_audience": "creator"
        },
        {
            "guide_id": "GUID004-CR",
            "title": "Brand Request Evaluation & Negotiation Guide",
            "category": "brand_request",
            "content": "How to evaluate incoming brand offers, review briefing requirements, submit counter-proposals, and accept campaign contracts.",
            "target_audience": "creator"
        },
        {
            "guide_id": "GUID005-BU",
            "title": "Brand Campaign Briefing & Influencer Hiring Guide",
            "category": "general",
            "content": "Best practices for drafting clear campaign briefs, establishing deliverable milestones, screening creator portfolios, and funding escrow.",
            "target_audience": "business"
        },
        {
            "guide_id": "GUID006-CS",
            "title": "Creator Support Ticket & Escalation Guide",
            "category": "deliverable",
            "content": "Step-by-step instructions on submitting support tickets, requesting revision arbitration, and resolving communication disputes.",
            "target_audience": "creator_support"
        }
    ]

    for g in initial_guides:
        Guide.objects.create(
            guide_id=g["guide_id"],
            title=g["title"],
            category=g["category"],
            content=g["content"],
            target_audience=g["target_audience"],
            is_active=True
        )

def reverse_guides(apps, schema_editor):
    Guide = apps.get_model("guide", "Guide")
    Guide.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Guide",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "guide_id",
                    models.CharField(
                        blank=True,
                        help_text="Unique guide identifier (automatically generated).",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("handbook", "Handbook"),
                            ("protection", "Protection"),
                            ("payment", "Payment Guide"),
                            ("brand_request", "Brand Request Guide"),
                            ("deliverable", "Deliverables"),
                            ("general", "General Platform"),
                        ],
                        default="general",
                        help_text="Category topic for this guide.",
                        max_length=50,
                    ),
                ),
                ("content", models.TextField()),
                (
                    "target_audience",
                    models.CharField(
                        choices=[
                            ("creator", "Creator"),
                            ("business", "Business"),
                            ("both", "Both"),
                            ("public", "Public"),
                            ("creator_support", "Creator Support"),
                            ("business_support", "Business Support"),
                        ],
                        default="creator",
                        help_text="Target audience who can access and view this guide.",
                        max_length=50,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Only active guides will be shown in platform dashboards.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Guide",
                "verbose_name_plural": "Guides",
            },
        ),
        migrations.RunPython(seed_initial_guides, reverse_guides),
    ]
