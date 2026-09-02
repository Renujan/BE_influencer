from django.db import migrations, models

def seed_initial_privacy_policies(apps, schema_editor):
    PrivacyPolicy = apps.get_model("privacy_policy", "PrivacyPolicy")

    initial_policies = [
        {
            "policy_id": "PRIV001-PU",
            "title": "Public Data Collection & Visitor Privacy",
            "content": "We collect minimal diagnostic telemetry and cookie preferences to deliver seamless navigation. Personal visitor data is never sold to third-party data brokers.",
            "target_audience": "public"
        },
        {
            "policy_id": "PRIV002-PU",
            "title": "Cookie Preferences & Tracking Safeguards",
            "content": "Visitors maintain complete control over analytical and functional cookie configurations. Essential security cookies are utilized solely to prevent malicious automated access.",
            "target_audience": "public"
        },
        {
            "policy_id": "PRIV003-CR",
            "title": "Creator Profile Data & Analytics Privacy",
            "content": "Social media metrics, engagement stats, and portfolio assets connected to Ampli are encrypted and displayed strictly to registered brands for collaboration verification.",
            "target_audience": "creator"
        },
        {
            "policy_id": "PRIV004-CR",
            "title": "Payout & Banking Information Encryption",
            "content": "Bank account details, tax forms, and payout histories are encrypted at rest with AES-256 and processed through PCI-DSS Level 1 compliant financial gateways.",
            "target_audience": "creator"
        },
        {
            "policy_id": "PRIV005-BU",
            "title": "Brand Campaign Confidentiality & Data Protection",
            "content": "Unreleased campaign briefs, target deliverables, and proprietary marketing assets remain strictly confidential between the brand and contracted creators.",
            "target_audience": "business"
        },
        {
            "policy_id": "PRIV006-BU",
            "title": "Commercial Escrow Transaction Records",
            "content": "Transaction ledgers, invoice details, and billing identities are securely archived for audit compliance and are accessible only by authorized financial administrators.",
            "target_audience": "business"
        },
        {
            "policy_id": "PRIV007-CS",
            "title": "Creator Support Ticket Privacy & Audit Logs",
            "content": "Communications, attachments, and audio notes submitted during support inquiries are preserved confidentially to resolve disputes and improve platform quality.",
            "target_audience": "creator_support"
        },
        {
            "policy_id": "PRIV008-BS",
            "title": "Business Support Mediation & Data Handling",
            "content": "Dispute tickets and arbitration submissions filed by business accounts are handled by certified compliance officers under strict confidentiality protocols.",
            "target_audience": "business_support"
        }
    ]

    for p in initial_policies:
        PrivacyPolicy.objects.create(
            policy_id=p["policy_id"],
            title=p["title"],
            content=p["content"],
            target_audience=p["target_audience"],
            is_active=True
        )

def reverse_policies(apps, schema_editor):
    PrivacyPolicy = apps.get_model("privacy_policy", "PrivacyPolicy")
    PrivacyPolicy.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("privacy_policy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PrivacyPolicy",
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
                    "policy_id",
                    models.CharField(
                        blank=True,
                        help_text="Unique privacy policy identifier (automatically generated).",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                (
                    "target_audience",
                    models.CharField(
                        choices=[
                            ("public", "Public (Landing Page)"),
                            ("business", "Business"),
                            ("creator", "Creator"),
                            ("both", "Both"),
                            ("business_support", "Business Support"),
                            ("creator_support", "Creator Support"),
                        ],
                        default="public",
                        help_text="Determine whether this privacy policy shows for public, businesses, creators, both, or support.",
                        max_length=50,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Only active privacy policies will be shown in the dashboards and public site.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Privacy Policy",
                "verbose_name_plural": "Privacy Policies",
            },
        ),
        migrations.DeleteModel(
            name="PrivacyPolicyGuide",
        ),
        migrations.RunPython(seed_initial_privacy_policies, reverse_policies),
    ]
