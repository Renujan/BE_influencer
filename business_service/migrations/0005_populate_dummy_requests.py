from django.db import migrations

def populate_dummy_requests(apps, schema_editor):
    User = apps.get_model("auth", "User")
    BusinessService = apps.get_model("business_service", "BusinessService")
    BusinessServiceRequest = apps.get_model("business_service", "BusinessServiceRequest")

    # Helper function to get model instance or None
    def get_user(username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    def get_service(title):
        try:
            return BusinessService.objects.get(title=title)
        except BusinessService.DoesNotExist:
            return None

    # Define dummy requests
    dummy_data = [
        {
            "username": "maya",
            "service_title": "Elite Video Production",
            "message": "Need a high-quality video production partner for my next brand deal. I will provide the script, but I need full 4K editing and licensed background audio tracks. 2 rounds of review are preferred.",
            "budget": "1500",
            "timeline": "Standard",
            "status": "pending"
        },
        {
            "username": "james",
            "service_title": "Creator Tax & Advisory",
            "message": "Filing taxes for my newly formed multi-member LLC. Need immediate advising on write-offs and international revenue optimization before the deadline next week.",
            "budget": "500",
            "timeline": "Urgent",
            "status": "connected"
        },
        {
            "username": "alex",
            "service_title": "Contract Draft & Review",
            "message": "Drafting standard collaboration agreements and NDA templates for our upcoming summer campaign. Need customized clauses for intellectual property transfer and multi-tier payment structures.",
            "budget": "Flexible",
            "timeline": "Flexible",
            "status": "pending"
        },
        {
            "username": "priya",
            "service_title": "Logo & Media Kit Styling",
            "message": "Need a new brand logo and media kit designed before pitching to key agencies in August. Love the glassmorphic aesthetics and modern clean typography.",
            "budget": "400",
            "timeline": "Standard",
            "status": "declined"
        }
    ]

    for item in dummy_data:
        user = get_user(item["username"])
        service = get_service(item["service_title"])
        if user and service:
            BusinessServiceRequest.objects.create(
                user=user,
                service=service,
                message=item["message"],
                budget=item["budget"],
                timeline=item["timeline"],
                status=item["status"]
            )

def unload_dummy_requests(apps, schema_editor):
    BusinessServiceRequest = apps.get_model("business_service", "BusinessServiceRequest")
    BusinessServiceRequest.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ("business_service", "0004_businessservicerequest"),
        ("auth", "__first__"),
    ]

    operations = [
        migrations.RunPython(populate_dummy_requests, unload_dummy_requests),
    ]
