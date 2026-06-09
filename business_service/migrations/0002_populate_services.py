from django.db import migrations

def populate_services(apps, schema_editor):
    BusinessService = apps.get_model("business_service", "BusinessService")
    services = [
        {
            "title": "Elite Video Production",
            "provider": "Vanguard Studios",
            "rate": "From $1,500 / project",
            "speed": "3-5 Days",
            "category": "Production",
            "description": "Get connected with award-winning creative studios to script, film, and produce top-tier social media advertising assets.",
            "bullet_points": "Full 4K Editing & Color Grading\nLicensed background audio library\nIncludes 2 rounds of edits",
            "gradient": "from-purple-500 to-indigo-600",
            "target_audience": "both",
        },
        {
            "title": "Contract Draft & Review",
            "provider": "LexCreative Law LLC",
            "rate": "From $250 / hour",
            "speed": "1-2 Days",
            "category": "Legal",
            "description": "Bulletproof collaboration agreements, NDA templates, and IP assignment clauses drafted specifically for creator partnerships.",
            "bullet_points": "100% legal protection guarantee\nCustomizable multi-tier terms\nDirect attorney review call",
            "gradient": "from-teal-500 to-emerald-600",
            "target_audience": "both",
        },
        {
            "title": "Global PR & Talent Placement",
            "provider": "Apex Outreach Agency",
            "rate": "From $800 / month",
            "speed": "Ongoing",
            "category": "Marketing",
            "description": "Scale your organic brand presence. Secure high-tier PR placements, press releases, and guaranteed editorial spots.",
            "bullet_points": "Guaranteed niche placements\nDedicated media outreach rep\nMonthly coverage reporting",
            "gradient": "from-rose-500 to-orange-600",
            "target_audience": "both",
        },
        {
            "title": "Logo & Media Kit Styling",
            "provider": "PixelPerfect Designs",
            "rate": "From $400 / project",
            "speed": "3 Days",
            "category": "Design",
            "description": "Establish a premier visual identity. Custom branding kits, banners, logos, and media templates designed with sleek typography.",
            "bullet_points": "3 creative design concepts\nSource vector files included\nSleek glassmorphic templates",
            "gradient": "from-blue-500 to-cyan-600",
            "target_audience": "both",
        },
        {
            "title": "Creator Tax & Advisory",
            "provider": "Vantage Finance Group",
            "rate": "From $180 / hour",
            "speed": "2 Days",
            "category": "Finance",
            "description": "Optimize your creator accounting. Set up multi-member LLCs, write-offs guidance, and cross-border payment structures.",
            "bullet_points": "LLC incorporation guidance\nWrite-offs maximization checkup\nVirtual CFO hourly advising",
            "gradient": "from-amber-500 to-yellow-600",
            "target_audience": "both",
        },
    ]
    for idx, s in enumerate(services, start=1):
        suffix = "-BO"
        s["service_id"] = f"BS{idx:03d}{suffix}"
        BusinessService.objects.create(**s)

def unload_services(apps, schema_editor):
    BusinessService = apps.get_model("business_service", "BusinessService")
    BusinessService.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ("business_service", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_services, unload_services),
    ]
