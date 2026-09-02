import re
from django.db import migrations, models

def seed_support_terms(apps, schema_editor):
    TermsAndCondition = apps.get_model("terms", "TermsAndCondition")
    
    support_terms = [
        {
            "title": "Business Support & SLA Guidelines",
            "content": "Business accounts are eligible for priority dispute mediation, dedicated ticketing SLA within 2 hours, and compliance auditing on active campaign deliverables.",
            "target_audience": "business_support",
            "suffix": "-BS"
        },
        {
            "title": "Business Escalation & Mediation Terms",
            "content": "In case of milestone delays or deliverable mismatches, business clients can request administrative arbitration. All milestone escrow funds remain secured until resolution.",
            "target_audience": "business_support",
            "suffix": "-BS"
        },
        {
            "title": "Creator Support & Payout Assistance Terms",
            "content": "Creators have access to 24/7 self-service troubleshooting and express email assistance for payout verification, bank transfer reconciliation, and milestone disputes.",
            "target_audience": "creator_support",
            "suffix": "-CS"
        },
        {
            "title": "Creator Deliverable Scope & Revision Protection",
            "content": "Brands may not request revisions exceeding the parameters established in the approved campaign brief. Creators facing out-of-scope demands can request support intervention for additional compensation or brief enforcement.",
            "target_audience": "creator_support",
            "suffix": "-CS"
        }
    ]

    for item in support_terms:
        if not TermsAndCondition.objects.filter(title=item["title"]).exists():
            max_num = 0
            for t in TermsAndCondition.objects.all():
                if t.terms_id:
                    match = re.match(r"^TERM(\d+)", t.terms_id)
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
            next_num = max_num + 1
            terms_id = f"TERM{next_num:03d}{item['suffix']}"
            TermsAndCondition.objects.create(
                terms_id=terms_id,
                title=item["title"],
                content=item["content"],
                target_audience=item["target_audience"],
                is_active=True
            )

def reverse_seed_support_terms(apps, schema_editor):
    TermsAndCondition = apps.get_model("terms", "TermsAndCondition")
    TermsAndCondition.objects.filter(target_audience__in=["business_support", "creator_support"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("terms", "0003_alter_termsandcondition_target_audience"),
    ]

    operations = [
        migrations.AlterField(
            model_name="termsandcondition",
            name="target_audience",
            field=models.CharField(
                choices=[
                    ("business", "Business"),
                    ("creator", "Creator"),
                    ("both", "Both"),
                    ("public", "Public"),
                    ("business_support", "Business Support"),
                    ("creator_support", "Creator Support"),
                ],
                default="both",
                help_text="Determine whether these terms show for businesses, creators, both, public, business support, or creator support.",
                max_length=50,
            ),
        ),
        migrations.RunPython(seed_support_terms, reverse_seed_support_terms),
    ]
