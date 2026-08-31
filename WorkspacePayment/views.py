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
    role = (request.data.get('role') or request.data.get('proposed_by_role') or '').lower().strip()

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

    min_b = float(getattr(campaign, 'min_budget', None) or getattr(campaign, 'min_price', None) or 10000)
    max_b = float(getattr(campaign, 'max_budget', None) or getattr(campaign, 'max_price', None) or 50000)
    c_min = float(getattr(campaign, 'creator_min_price', None) or getattr(campaign, 'min_price', None) or 20000)
    c_max = float(getattr(campaign, 'creator_max_price', None) or getattr(campaign, 'max_price', None) or 49000)

    overall_min = min(min_b, c_min)
    overall_max = max(max_b, c_max)

    if price_val < overall_min or price_val > overall_max:
        return Response({
            'error': f'Proposed final price ({price_val:,.0f}) must be within the overall allowed range ({overall_min:,.0f} - {overall_max:,.0f}).'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if (request.user and request.user.is_authenticated) else None
    is_creator_role = (role == 'creator') or (user and (user == getattr(campaign, 'creator', None) or hasattr(user, 'creator_profile')))

    target_status = 'pending_business_approval' if is_creator_role else 'pending_creator_approval'

    negotiation = WorkspacePaymentNegotiation.objects.filter(campaign=campaign).order_by('-id').first()
    if not negotiation:
        negotiation = WorkspacePaymentNegotiation(
            campaign=campaign,
            final_price=price_val,
            status=target_status
        )
    else:
        negotiation.final_price = price_val
        negotiation.status = target_status
        negotiation.revision_reason = None

    if user:
        negotiation.proposed_by = user

    negotiation.save()

    serializer = WorkspacePaymentNegotiationSerializer(negotiation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def business_action(request):
    campaign_id = request.data.get('campaign_id')
    action = request.data.get('action') # 'accept' or 'revise'
    revision_reason = request.data.get('revision_reason', '')

    if not campaign_id or action not in ['accept', 'revise']:
        return Response({'error': 'campaign_id and valid action (accept or revise) are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign_id=campaign_id).order_by('-id').first()
        if not negotiation:
            from campegin.models import Campaign
            campaign = Campaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return Response({'error': 'No payment negotiation found for this campaign.'}, status=status.HTTP_404_NOT_FOUND)
            negotiation = WorkspacePaymentNegotiation.objects.create(
                campaign=campaign,
                final_price=campaign.budget or campaign.counter_price or None,
                status='creator_accepted' if action == 'accept' else 'pending_creator_approval'
            )

        if action == 'accept':
            negotiation.status = 'creator_accepted'
            negotiation.revision_reason = None
            campaign = negotiation.campaign
            if campaign and negotiation.final_price is not None:
                campaign.budget = negotiation.final_price
                campaign.counter_price = negotiation.final_price
                campaign.save()
        elif action == 'revise':
            requested_price = request.data.get('requested_price') or request.data.get('price') or request.data.get('final_price')
            if requested_price is not None:
                try:
                    p_val = float(str(requested_price).replace(',', '').replace('$', '').replace('Rs', '').strip())
                    if p_val > 0:
                        camp = getattr(negotiation, 'campaign', None)
                        if camp:
                            min_b = float(getattr(camp, 'min_budget', None) or getattr(camp, 'min_price', None) or 10000)
                            max_b = float(getattr(camp, 'max_budget', None) or getattr(camp, 'max_price', None) or 50000)
                            c_min = float(getattr(camp, 'creator_min_price', None) or getattr(camp, 'min_price', None) or 20000)
                            c_max = float(getattr(camp, 'creator_max_price', None) or getattr(camp, 'max_price', None) or 49000)
                            overall_min = min(min_b, c_min)
                            overall_max = max(max_b, c_max)

                            if p_val < overall_min or p_val > overall_max:
                                return Response({
                                    'error': f'Proposed price ({p_val:,.0f}) must be within the overall allowed range ({overall_min:,.0f} - {overall_max:,.0f}).'
                                }, status=status.HTTP_400_BAD_REQUEST)

                        negotiation.final_price = p_val
                except ValueError:
                    pass
                except Exception:
                    pass
            negotiation.status = 'pending_creator_approval'
            if revision_reason:
                negotiation.revision_reason = str(revision_reason).strip()

        if request.user and request.user.is_authenticated:
            negotiation.action_by = request.user

        negotiation.save()

        serializer = WorkspacePaymentNegotiationSerializer(negotiation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def creator_action(request):
    campaign_id = request.data.get('campaign_id')
    action = request.data.get('action') # 'accept' or 'revise'
    revision_reason = request.data.get('revision_reason', '')

    if not campaign_id or action not in ['accept', 'revise']:
        return Response({'error': 'campaign_id and valid action (accept or revise) are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign_id=campaign_id).order_by('-id').first()
        if not negotiation:
            from campegin.models import Campaign
            campaign = Campaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return Response({'error': 'No payment negotiation found for this campaign.'}, status=status.HTTP_404_NOT_FOUND)
            negotiation = WorkspacePaymentNegotiation.objects.create(
                campaign=campaign,
                final_price=campaign.budget or campaign.counter_price or None,
                status='revision_requested' if action == 'revise' else 'creator_accepted'
            )

        if action == 'accept':
            negotiation.status = 'creator_accepted'
            negotiation.revision_reason = None
            # Sync campaign budget and counter_price with accepted final_price
            campaign = negotiation.campaign
            if campaign and negotiation.final_price is not None:
                campaign.budget = negotiation.final_price
                campaign.counter_price = negotiation.final_price
                campaign.save()
        elif action == 'revise':
            if not revision_reason or not str(revision_reason).strip():
                return Response({'error': 'A reason is required when requesting a revision.'}, status=status.HTTP_400_BAD_REQUEST)
            negotiation.status = 'revision_requested'
            
            reason_str = str(revision_reason).strip()
            requested_price = request.data.get('requested_price') or request.data.get('price')
            
            if requested_price is None and "Requested Price:" in reason_str:
                try:
                    import re
                    match = re.search(r'Requested Price:\s*[\$Rs]*([\d,]+(?:\.\d+)?)', reason_str)
                    if match:
                        requested_price = match.group(1)
                except Exception:
                    pass

            if requested_price is not None:
                try:
                    p_val = float(str(requested_price).replace(',', '').replace('$', '').replace('Rs', '').strip())
                    if p_val > 0:
                        camp = getattr(negotiation, 'campaign', None)
                        if camp:
                            min_b = float(getattr(camp, 'min_budget', None) or getattr(camp, 'min_price', None) or 10000)
                            max_b = float(getattr(camp, 'max_budget', None) or getattr(camp, 'max_price', None) or 50000)
                            c_min = float(getattr(camp, 'creator_min_price', None) or getattr(camp, 'min_price', None) or 20000)
                            c_max = float(getattr(camp, 'creator_max_price', None) or getattr(camp, 'max_price', None) or 49000)
                            overall_min = min(min_b, c_min)
                            overall_max = max(max_b, c_max)

                            if p_val < overall_min or p_val > overall_max:
                                return Response({
                                    'error': f'Requested price ({p_val:,.0f}) must be within the overall allowed range ({overall_min:,.0f} - {overall_max:,.0f}).'
                                }, status=status.HTTP_400_BAD_REQUEST)

                        if not reason_str.startswith('Requested Price:'):
                            reason_str = f"Requested Price: ${p_val:,.2f} — Reason: {reason_str}"
                        negotiation.final_price = p_val
                except ValueError:
                    pass
                except Exception:
                    pass
                    
            negotiation.revision_reason = reason_str

        if request.user and request.user.is_authenticated:
            negotiation.action_by = request.user

        negotiation.save()

        serializer = WorkspacePaymentNegotiationSerializer(negotiation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_negotiation(request, campaign_id):
    try:
        from campegin.models import Campaign
        campaign = Campaign.objects.filter(id=campaign_id).first()
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign_id=campaign_id).order_by('-id').first()
        
        created_via = str(campaign.created_via or '').lower().strip() if campaign else ''

        if created_via == 'pitch':
            from campegin.models import Pitch
            pitch = Pitch.objects.filter(campaign_name=campaign.name, brand=campaign.brand, creator=campaign.creator).order_by("-id").first() or Pitch.objects.filter(campaign_name=campaign.name, brand=campaign.brand).order_by("-id").first() or Pitch.objects.filter(brand=campaign.brand, creator=campaign.creator).order_by("-id").first()
            pitch_price = None
            if pitch:
                if pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0:
                    pitch_price = pitch.counter_history[-1].get("price")
                elif pitch.counter_offer:
                    pitch_price = pitch.counter_offer
                elif pitch.budget:
                    pitch_price = pitch.budget
            
            camp_price = None
            if campaign.counter_history and isinstance(campaign.counter_history, list) and len(campaign.counter_history) > 0:
                camp_price = campaign.counter_history[-1].get("price")
            elif campaign.counter_price:
                camp_price = campaign.counter_price
            elif campaign.budget:
                camp_price = campaign.budget

            last_price = pitch_price or camp_price or campaign.budget

            if not negotiation:
                negotiation = WorkspacePaymentNegotiation.objects.create(
                    campaign=campaign,
                    final_price=last_price,
                    status='creator_accepted'
                )
            else:
                if last_price and negotiation.status not in ['revision_requested', 'pending_creator_approval', 'pending_business_approval'] and negotiation.final_price != float(last_price):
                    negotiation.final_price = float(last_price)
                    negotiation.status = 'creator_accepted'
                    negotiation.save(update_fields=['final_price', 'status'])
        elif not negotiation and campaign:
            negotiation = WorkspacePaymentNegotiation.objects.create(
                campaign=campaign,
                final_price=None,
                status='pending_proposal'
            )
        elif negotiation and campaign and created_via != 'pitch':
            # For direct request campaigns, if status was auto-set to creator_accepted without manual proposal, reset it to pending_proposal
            if negotiation.status == 'creator_accepted' and not negotiation.proposed_by and not negotiation.action_by:
                negotiation.final_price = None
                negotiation.status = 'pending_proposal'
                negotiation.save()

        if not negotiation:
            return Response({'error': 'No payment negotiation found for this campaign.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkspacePaymentNegotiationSerializer(negotiation, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_all_negotiations(request):
    negotiations = WorkspacePaymentNegotiation.objects.all().order_by('-updated_at')
    serializer = WorkspacePaymentNegotiationSerializer(negotiations, many=True, context={'request': request})
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
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign_id=campaign_id).order_by('-id').first()

    if not negotiation:
        return Response({'error': 'Payment negotiation entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    negotiation.status = 'admin_approved'
    if request.user and request.user.is_authenticated:
        negotiation.action_by = request.user
    negotiation.save()

    serializer = WorkspacePaymentNegotiationSerializer(negotiation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_platform_charge(request):
    campaign_id = request.data.get('campaign_id')
    negotiation_id = request.data.get('negotiation_id')
    platform_charge = request.data.get('platform_charge')
    business_platform_charge = request.data.get('business_platform_charge')
    creator_platform_charge = request.data.get('creator_platform_charge')

    negotiation = None
    if negotiation_id:
        negotiation = WorkspacePaymentNegotiation.objects.filter(id=negotiation_id).first()
    elif campaign_id:
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign_id=campaign_id).order_by('-id').first()

    if not negotiation:
        return Response({'error': 'Payment negotiation entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        biz_val = business_platform_charge if business_platform_charge is not None else platform_charge
        if biz_val is not None and str(biz_val).strip() != '':
            charge_val = float(str(biz_val).replace('%', '').strip())
            if charge_val < 2.5 or charge_val > 10.0:
                return Response({'error': 'Business platform charge must be between 2.5% and 10.0%.'}, status=status.HTTP_400_BAD_REQUEST)
            negotiation.platform_charge = charge_val

        if creator_platform_charge is not None and str(creator_platform_charge).strip() != '':
            creator_val = float(str(creator_platform_charge).replace('%', '').strip())
            if creator_val < 1.5 or creator_val > 10.0:
                return Response({'error': 'Creator platform charge must be between 1.5% and 10.0%.'}, status=status.HTTP_400_BAD_REQUEST)
            negotiation.creator_platform_charge = creator_val

        if request.data.get('business_fee_is_paid') is not None:
            negotiation.business_fee_is_paid = str(request.data.get('business_fee_is_paid')).lower() in ['true', '1']
        if request.data.get('business_fee_paid_date') is not None:
            negotiation.business_fee_paid_date = request.data.get('business_fee_paid_date') or None
        if request.FILES.get('business_fee_receipt_image'):
            negotiation.business_fee_receipt_image = request.FILES.get('business_fee_receipt_image')
            if not negotiation.business_fee_paid_date:
                from django.utils import timezone
                negotiation.business_fee_paid_date = timezone.now().date()
        if str(request.data.get('reset_business_fee')).lower() in ['true', '1']:
            negotiation.business_fee_is_paid = False
            negotiation.business_fee_paid_date = None
            negotiation.business_fee_receipt_image = None

        if request.data.get('creator_fee_is_paid') is not None:
            negotiation.creator_fee_is_paid = str(request.data.get('creator_fee_is_paid')).lower() in ['true', '1']
        if request.data.get('creator_fee_paid_date') is not None:
            negotiation.creator_fee_paid_date = request.data.get('creator_fee_paid_date') or None
        if request.FILES.get('creator_fee_receipt_image'):
            negotiation.creator_fee_receipt_image = request.FILES.get('creator_fee_receipt_image')
        if str(request.data.get('reset_creator_fee')).lower() in ['true', '1']:
            negotiation.creator_fee_is_paid = False
            negotiation.creator_fee_paid_date = None
            negotiation.creator_fee_receipt_image = None

        negotiation.save()
    except ValueError:
        return Response({'error': 'Invalid format.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = WorkspacePaymentNegotiationSerializer(negotiation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_installments(request):
    campaign_id = request.data.get('campaign_id')
    installments_data = request.data.get('installments', [])
    installment_type = request.data.get('installment_type', 'creator')

    if not campaign_id or not installments_data:
        return Response({'error': 'campaign_id and installments array are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response({'error': 'Campaign not found.'}, status=status.HTTP_404_NOT_FOUND)

    negotiation = WorkspacePaymentNegotiation.objects.filter(campaign=campaign).first()

    WorkspaceInstallment.objects.filter(campaign=campaign, installment_type=installment_type).delete()

    created_objs = []
    for idx, item in enumerate(installments_data, start=1):
        title = item.get('title') or f"Installment {idx}"
        description = item.get('description') or None
        amount_val = float(str(item.get('amount', 0)).replace(',', '').replace('$', '').replace('Rs', '').strip())
        is_paid_val = bool(item.get('is_paid', False))
        paid_date_val = item.get('paid_date') or None

        if is_paid_val and not paid_date_val:
            from django.utils import timezone
            paid_date_val = timezone.now().date()

        obj = WorkspaceInstallment.objects.create(
            campaign=campaign,
            negotiation=negotiation,
            installment_type=installment_type,
            title=title,
            description=description,
            amount=amount_val,
            status='released' if is_paid_val else (item.get('status') or 'pending'),
            is_paid=is_paid_val,
            paid_date=paid_date_val if is_paid_val else None,
        )
        created_objs.append(obj)

    serializer = WorkspaceInstallmentSerializer(created_objs, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


def sync_platform_fee_from_installment(installment):
    if not installment:
        return
    negotiation = installment.negotiation
    if not negotiation and installment.campaign:
        negotiation = WorkspacePaymentNegotiation.objects.filter(campaign=installment.campaign).first()
    if not negotiation:
        return

    first_inst = WorkspaceInstallment.objects.filter(campaign=installment.campaign, installment_type=installment.installment_type).order_by('id').first()
    if first_inst and first_inst.id == installment.id:
        if installment.installment_type == 'business':
            negotiation.business_fee_is_paid = installment.is_paid
            negotiation.business_fee_paid_date = installment.paid_date
            if installment.receipt_image:
                negotiation.business_fee_receipt_image = installment.receipt_image
            negotiation.save()
        elif installment.installment_type == 'creator':
            negotiation.creator_fee_is_paid = installment.is_paid
            negotiation.creator_fee_paid_date = installment.paid_date
            if installment.receipt_image:
                negotiation.creator_fee_receipt_image = installment.receipt_image
            negotiation.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def update_installment(request):
    installment_id = request.data.get('installment_id')
    title = request.data.get('title')
    description = request.data.get('description')
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
    if description is not None:
        installment.description = str(description).strip() if str(description).strip() else None
    if amount is not None:
        try:
            installment.amount = float(str(amount).replace(',', '').replace('$', '').replace('Rs', '').strip())
        except ValueError:
            pass
    if is_paid is not None:
        installment.is_paid = bool(is_paid)
        if installment.is_paid:
            if installment.status != 'released':
                installment.status = 'approved' if installment.installment_type == 'business' else 'released'
            if paid_date:
                installment.paid_date = paid_date
            elif not installment.paid_date:
                from django.utils import timezone
                installment.paid_date = timezone.now().date()
        else:
            has_receipt = bool(installment.receipt_image or installment.receipt_url)
            installment.status = 'in_escrow' if has_receipt else 'pending'
            if paid_date is not None:
                installment.paid_date = paid_date or None
    elif paid_date is not None:
        installment.paid_date = paid_date or None

    installment.save()
    sync_platform_fee_from_installment(installment)

    serializer = WorkspaceInstallmentSerializer(installment, context={'request': request})
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

    installment.status = 'in_escrow'
    installment.save()
    sync_platform_fee_from_installment(installment)

    serializer = WorkspaceInstallmentSerializer(installment, context={'request': request})
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
        installment.status = 'pending'
        installment.is_paid = False
        installment.paid_date = None

    installment.save()
    sync_platform_fee_from_installment(installment)

    serializer = WorkspaceInstallmentSerializer(installment, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_installments(request, campaign_id):
    installments = WorkspaceInstallment.objects.filter(campaign_id=campaign_id).order_by('id')
    serializer = WorkspaceInstallmentSerializer(installments, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)

