import json
import re
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import BusinessService, BusinessServiceRequest

def get_user_from_request(request):
    """
    Helper function to authenticate a user based on Authorization header or GET/POST token parameters.
    """
    # 1. Check HTTP Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Token "):
        token_key = auth_header.split(" ")[1]
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None

    # 2. Check query params or POST body parameter fallback
    token_key = request.GET.get("token") or request.POST.get("token")
    if not token_key and request.content_type == "application/json":
        try:
            body = json.loads(request.body)
            token_key = body.get("token")
        except:
            pass

    if token_key:
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None
            
    # 3. Request session user fallback
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
        
    return None

@csrf_exempt
def api_list_business_services(request):
    """
    GET view to return all active Business Services filtered by the user's role:
    - business/brand: shows 'business' and 'both' services.
    - creator/influencer: shows 'creator' and 'both' services.
    Accepts query param ?role=business or ?role=creator (or ?role=influencer) as fallback/override.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

    try:
        # Determine target role based on authentication or query parameter
        role = request.GET.get("role")
        
        # Authenticate user if possible
        user = get_user_from_request(request)
        if user and not role:
            # Check user profile role
            try:
                role = user.profile.role
            except AttributeError:
                pass

        # Build query for active services
        queryset = BusinessService.objects.filter(is_active=True)

        if role:
            role = role.lower()
            if role in ("business", "brand"):
                queryset = queryset.filter(target_audience__in=["business", "both"])
            elif role in ("creator", "influencer"):
                queryset = queryset.filter(target_audience__in=["creator", "both"])
            elif role == "both":
                pass
            else:
                pass

        # Serialize results
        services_list = []
        for s in queryset.order_by("id"):
            bullet_points = [bp.strip() for bp in s.bullet_points.split("\n") if bp.strip()] if s.bullet_points else []
            services_list.append({
                "id": s.id,
                "service_id": s.service_id,
                "title": s.title,
                "provider": s.provider,
                "rate": s.rate,
                "speed": s.speed,
                "category": s.category.name if s.category else "Production",
                "description": s.description,
                "bulletPoints": bullet_points,
                "target_audience": s.target_audience,
                "target_audience_display": s.get_target_audience_display(),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            })

        return JsonResponse({"services": services_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def download_business_service_pdf(request, pk):
    """Generate and download a PDF for a specific business service."""
    try:
        service = get_object_or_404(BusinessService, pk=pk)

        # Build PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
        styles = getSampleStyleSheet()
        story = []

        # Styles
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#6D28D9"), # Purple matching theme
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            name='SectionStyle',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=14,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            name='BodyStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4B5563")
        )
        bold_body_style = ParagraphStyle(
            name='BoldBodyStyle',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        # Title
        story.append(Paragraph("ampli - Business Service Sheet", title_style))
        story.append(Paragraph(f"Official service catalog entry for <b>{service.title}</b>.", body_style))
        story.append(Spacer(1, 15))

        # Metadata table
        data = [
            [Paragraph("Service ID:", bold_body_style), Paragraph(service.service_id or "N/A", body_style)],
            [Paragraph("Title:", bold_body_style), Paragraph(service.title, body_style)],
            [Paragraph("Provider:", bold_body_style), Paragraph(service.provider, body_style)],
            [Paragraph("Category:", bold_body_style), Paragraph(service.category.name if service.category else "N/A", body_style)],
            [Paragraph("Rate Tier:", bold_body_style), Paragraph(service.rate, body_style)],
            [Paragraph("Timeline / Speed:", bold_body_style), Paragraph(service.speed, body_style)],
            [Paragraph("Target Audience:", bold_body_style), Paragraph(service.get_target_audience_display(), body_style)],
            [Paragraph("Status:", bold_body_style), Paragraph("Active" if service.is_active else "Inactive", body_style)],
        ]
        table = Table(data, colWidths=[130, 374])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F9FAFB")),
        ]))
        story.append(table)
        story.append(Spacer(1, 15))

        # Description
        story.append(Paragraph("Service Description", section_style))
        story.append(Paragraph(service.description.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 15))

        # Bullet points
        story.append(Paragraph("Service Highlights", section_style))
        bullet_points = [bp.strip() for bp in service.bullet_points.split("\n") if bp.strip()] if service.bullet_points else []
        if bullet_points:
            for bp in bullet_points:
                story.append(Paragraph(f"• {bp}", body_style))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("No highlights specified.", body_style))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        
        # Clean title for filename
        clean_title = re.sub(r'[^\w\s-]', '', service.title)
        clean_title = re.sub(r'[-\s]+', '_', clean_title).strip('_').lower()
        filename = f"{clean_title or 'service'}_{service.service_id or service.pk}.pdf"
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

@csrf_exempt
def api_business_service_inquiries(request):
    """
    POST: Create a new business service inquiry.
    GET: List all inquiries created by the authenticated user.
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Authentication required"}, status=401)

    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST

            service_id = data.get("service_id")
            message = data.get("message")
            budget = data.get("budget", "Flexible")
            timeline = data.get("timeline", "Standard")

            if not service_id or not message:
                return JsonResponse({"error": "service_id and message are required"}, status=400)

            # Retrieve business service
            try:
                if isinstance(service_id, int) or (isinstance(service_id, str) and service_id.isdigit()):
                    service = BusinessService.objects.get(id=int(service_id))
                else:
                    service = BusinessService.objects.get(service_id=service_id)
            except BusinessService.DoesNotExist:
                return JsonResponse({"error": "Business service not found"}, status=404)

            # Create inquiry
            inquiry = BusinessServiceRequest.objects.create(
                service=service,
                user=user,
                message=message,
                budget=budget,
                timeline=timeline,
                status="pending"
            )

            # Create notification for admin
            try:
                from notifications.models import Notification
                Notification.objects.create(
                    title="New Service Inquiry",
                    message=f"User '{user.username}' submitted an inquiry for service '{service.title}' (Provider: {service.provider}).",
                    category="campaign",
                    icon="fas fa-paper-plane"
                )
            except Exception as e:
                print(f"Failed to create admin notification: {e}")

            return JsonResponse({
                "message": "Inquiry submitted successfully",
                "inquiry": {
                    "id": inquiry.id,
                    "service_id": service.id,
                    "service_title": service.title,
                    "provider_name": service.provider,
                    "budget": inquiry.budget,
                    "message": inquiry.message,
                    "timeline": inquiry.timeline,
                    "status": inquiry.status,
                    "status_display": inquiry.get_status_display(),
                    "created_at": inquiry.created_at.isoformat()
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "GET":
        try:
            inquiries = BusinessServiceRequest.objects.filter(user=user).select_related("service")
            inquiries_list = []
            for inq in inquiries:
                inquiries_list.append({
                    "id": inq.id,
                    "service_id": inq.service.id,
                    "service_title": inq.service.title,
                    "provider_name": inq.service.provider,
                    "budget": inq.budget,
                    "message": inq.message,
                    "timeline": inq.timeline,
                    "status": inq.status,
                    "status_display": inq.get_status_display(),
                    "created_at": inq.created_at.isoformat()
                })
            return JsonResponse({"inquiries": inquiries_list}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@user_passes_test(lambda u: u.is_staff)
def admin_connect_request_view(request, request_id):
    """Admin action to verify and connect a business service request."""
    inquiry = get_object_or_404(BusinessServiceRequest, pk=request_id)
    inquiry.status = "connected"
    inquiry.save()
    messages.success(request, f"Service Request #{inquiry.id} has been verified and connected successfully!")
    
    # Try to redirect to inspect page of BusinessServiceRequest
    try:
        from django.urls import reverse
        inspect_url = reverse("businessservicerequest_views_inspect", args=[request_id])
        return redirect(inspect_url)
    except Exception:
        try:
            from django.urls import reverse
            inspect_url = reverse("businessservicerequest:inspect", args=[request_id])
            return redirect(inspect_url)
        except Exception:
            return redirect(f"/admin/snippets/business_service/businessservicerequest/inspect/{request_id}/")


@user_passes_test(lambda u: u.is_staff)
def admin_decline_request_view(request, request_id):
    """Admin action to decline a business service request."""
    inquiry = get_object_or_404(BusinessServiceRequest, pk=request_id)
    inquiry.status = "declined"
    inquiry.save()
    messages.warning(request, f"Service Request #{inquiry.id} has been declined.")
    
    # Try to redirect to inspect page of BusinessServiceRequest
    try:
        from django.urls import reverse
        inspect_url = reverse("businessservicerequest_views_inspect", args=[request_id])
        return redirect(inspect_url)
    except Exception:
        try:
            from django.urls import reverse
            inspect_url = reverse("businessservicerequest:inspect", args=[request_id])
            return redirect(inspect_url)
        except Exception:
            return redirect(f"/admin/snippets/business_service/businessservicerequest/inspect/{request_id}/")

