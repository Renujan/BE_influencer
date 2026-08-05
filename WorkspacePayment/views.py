from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from campegin.models import Campaign
from .models import WorkspacePaymentNegotiation, WorkspaceInstallment
from .serializers import WorkspacePaymentNegotiationSerializer, WorkspaceInstallmentSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def propose_final_price(request):
    campaign_id = request.data.get('campaign_id')
    final_price = request.data.get('final_price')

    if not campaign_id or final_price is None:
        return Response({'error': 'campaign_id and final_price are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response({'error': 'Campaign not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        price_val = float(str(final_price).replace(',', '').replace('$', '').replace('Rs', '').strip())
    except ValueError:
        return Response({'error': 'Invalid final_price format.'}, status=status.HTTP_400_BAD_REQUEST)

    negotiation = WorkspacePaymentNegotiation.objects.filter(campaign=campaign).first()
    if not negotiation:
        negotiation = WorkspacePaymentNegotiation(
            campaign=campaign,
            final_price=price_val,
            status='pending_creator_approval'
        )
    else:
        negotiation.final_price = price_val
        negotiation.status = 'pending_creator_approval'
        negotiation.revision_reason = None

    if request.user and request.user.is_authenticated:
        negotiation.proposed_by = request.user

    negotiation.save()

    serializer = WorkspacePaymentNegotiationSerializer(negotiation)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def creator_action(request):
    campaign_id = request.data.get('campaign_id')
    action = request.data.get('action') # 'accept' or 'revise'
    revision_reason = request.data.get('revision_reason', '')

    if not campaign_id or action not in ['accept', 'revise']:
        return Response({'error': 'campaign_id and valid action (accept or revise) are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        negotiation = WorkspacePaymentNegotiation.objects.get(campaign_id=campaign_id)
    except WorkspacePaymentNegotiation.DoesNotExist:
        return Response({'error': 'No payment negotiation found for this campaign.'}, status=status.HTTP_404_NOT_FOUND)

    if action == 'accept':
        negotiation.status = 'creator_accepted'
        negotiation.revision_reason = None
    elif action == 'revise':
        if not revision_reason or not str(revision_reason).strip():
            return Response({'error': 'A reason is required when requesting a revision.'}, status=status.HTTP_400_BAD_REQUEST)
        negotiation.status = 'revision_requested'
        negotiation.revision_reason = str(revision_reason).strip()

    if request.user and request.user.is_authenticated:
        negotiation.action_by = request.user

    negotiation.save()

    serializer = WorkspacePaymentNegotiationSerializer(negotiation)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_negotiation(request, campaign_id):
    try:
        negotiation = WorkspacePaymentNegotiation.objects.get(campaign_id=campaign_id)
        serializer = WorkspacePaymentNegotiationSerializer(negotiation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except WorkspacePaymentNegotiation.DoesNotExist:
        return Response({}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_all_negotiations(request):
    negotiations = WorkspacePaymentNegotiation.objects.all().order_by('-updated_at')
    serializer = WorkspacePaymentNegotiationSerializer(negotiations, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_approve_negotiation(request):
    campaign_id = request.data.get('campaign_id')
    negotiation_id = request.data.get('negotiation_id')

    negotiation = None
    if negotiation_id:
        negotiation = WorkspacePaymentNegotiation.objects.filter(id=negotiation_id).first()
    elif campaign_id:
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign_id=campaign_id).first()

    if not negotiation:
        return Response({'error': 'Payment negotiation entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    negotiation.status = 'admin_approved'
    if request.user and request.user.is_authenticated:
        negotiation.action_by = request.user
    negotiation.save()

    serializer = WorkspacePaymentNegotiationSerializer(negotiation)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_installments(request):
    campaign_id = request.data.get('campaign_id')
    installments_data = request.data.get('installments', [])

    if not campaign_id or not installments_data:
        return Response({'error': 'campaign_id and installments array are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response({'error': 'Campaign not found.'}, status=status.HTTP_404_NOT_FOUND)

    negotiation = WorkspacePaymentNegotiation.objects.filter(campaign=campaign).first()

    WorkspaceInstallment.objects.filter(campaign=campaign).delete()

    created_objs = []
    for idx, item in enumerate(installments_data, start=1):
        title = item.get('title') or f"Installment {idx}"
        amount_val = float(str(item.get('amount', 0)).replace(',', '').replace('$', '').replace('Rs', '').strip())
        is_paid_val = bool(item.get('is_paid', False))
        paid_date_val = item.get('paid_date') or None

        if is_paid_val and not paid_date_val:
            from django.utils import timezone
            paid_date_val = timezone.now().date()

        obj = WorkspaceInstallment.objects.create(
            campaign=campaign,
            negotiation=negotiation,
            title=title,
            amount=amount_val,
            status='released' if is_paid_val else 'in_escrow',
            is_paid=is_paid_val,
            paid_date=paid_date_val if is_paid_val else None,
        )
        created_objs.append(obj)

    serializer = WorkspaceInstallmentSerializer(created_objs, many=True)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_installment(request):
    installment_id = request.data.get('installment_id')
    title = request.data.get('title')
    amount = request.data.get('amount')
    paid_date = request.data.get('paid_date')
    is_paid = request.data.get('is_paid')

    if not installment_id:
        return Response({'error': 'installment_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        installment = WorkspaceInstallment.objects.get(id=installment_id)
    except WorkspaceInstallment.DoesNotExist:
        return Response({'error': 'Installment not found.'}, status=status.HTTP_404_NOT_FOUND)

    if title is not None:
        installment.title = str(title).strip()
    if amount is not None:
        try:
            installment.amount = float(str(amount).replace(',', '').replace('$', '').replace('Rs', '').strip())
        except ValueError:
            pass
    if is_paid is not None:
        installment.is_paid = bool(is_paid)
        if installment.is_paid:
            installment.status = 'released'
            if paid_date:
                installment.paid_date = paid_date
            elif not installment.paid_date:
                from django.utils import timezone
                installment.paid_date = timezone.now().date()
        else:
            installment.status = 'in_escrow'
            if paid_date is not None:
                installment.paid_date = paid_date or None
    elif paid_date is not None:
        installment.paid_date = paid_date or None

    installment.save()

    serializer = WorkspaceInstallmentSerializer(installment)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def upload_installment_receipt(request):
    installment_id = request.data.get('installment_id')
    receipt_url = request.data.get('receipt_url')
    file_obj = request.FILES.get('receipt_image')

    if not installment_id:
        return Response({'error': 'installment_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        installment = WorkspaceInstallment.objects.get(id=installment_id)
    except WorkspaceInstallment.DoesNotExist:
        return Response({'error': 'Installment not found.'}, status=status.HTTP_404_NOT_FOUND)

    if file_obj:
        installment.receipt_image = file_obj
    if receipt_url:
        installment.receipt_url = receipt_url

    installment.status = 'payment_submitted'
    installment.save()

    serializer = WorkspaceInstallmentSerializer(installment)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_installment(request):
    installment_id = request.data.get('installment_id')
    action = request.data.get('action')

    if not installment_id or action not in ['release', 'reject']:
        return Response({'error': 'installment_id and valid action (release or reject) are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        installment = WorkspaceInstallment.objects.get(id=installment_id)
    except WorkspaceInstallment.DoesNotExist:
        return Response({'error': 'Installment not found.'}, status=status.HTTP_404_NOT_FOUND)

    if action == 'release':
        installment.status = 'released'
        installment.is_paid = True
        if not installment.paid_date:
            from django.utils import timezone
            installment.paid_date = timezone.now().date()
    elif action == 'reject':
        installment.status = 'in_escrow'
        installment.is_paid = False
        installment.paid_date = None

    installment.save()

    serializer = WorkspaceInstallmentSerializer(installment)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_installments(request, campaign_id):
    installments = WorkspaceInstallment.objects.filter(campaign_id=campaign_id).order_by('id')
    serializer = WorkspaceInstallmentSerializer(installments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

