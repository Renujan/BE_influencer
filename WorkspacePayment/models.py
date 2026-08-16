from django.db import models
from django.conf import settings
from campegin.models import Campaign
from django.utils import timezone
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel

class WorkspacePaymentNegotiation(ClusterableModel):
    STATUS_CHOICES = (
        ('pending_creator_approval', 'Pending Creator Approval'),
        ('creator_accepted', 'Creator Accepted'),
        ('revision_requested', 'Revision Requested'),
        ('admin_approved', 'Admin Approved'),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='payment_negotiations')
    final_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    platform_charge = models.DecimalField(max_digits=5, decimal_places=2, default=2.50) # Business Platform Charge %
    creator_platform_charge = models.DecimalField(max_digits=5, decimal_places=2, default=1.50) # Creator Platform Charge %
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending_creator_approval')
    revision_reason = models.TextField(blank=True, null=True)

    business_fee_is_paid = models.BooleanField(default=False)
    business_fee_paid_date = models.DateField(null=True, blank=True)
    business_fee_receipt_image = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    creator_fee_is_paid = models.BooleanField(default=False)
    creator_fee_paid_date = models.DateField(null=True, blank=True)
    creator_fee_receipt_image = models.FileField(upload_to='payment_receipts/', null=True, blank=True)

    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='proposed_payments')
    action_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='actioned_payments')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel('campaign'),
        FieldPanel('final_price'),
        FieldPanel('platform_charge', heading="Business Platform Charge %"),
        FieldPanel('creator_platform_charge', heading="Creator Platform Charge %"),
        FieldPanel('status'),
        FieldPanel('revision_reason'),
        FieldPanel('proposed_by'),
        FieldPanel('action_by'),
        InlinePanel('installments', label="Milestone Installments Breakdown"),
    ]

    @property
    def business_platform_charge(self):
        return self.platform_charge

    @business_platform_charge.setter
    def business_platform_charge(self, value):
        self.platform_charge = value

    @property
    def business_platform_charge_amount(self):
        fp = float(self.final_price or 0)
        pc = float(self.platform_charge if self.platform_charge is not None else 2.5)
        return round(fp * (pc / 100.0), 2)

    @property
    def creator_platform_charge_amount(self):
        fp = float(self.final_price or 0)
        pc = float(self.creator_platform_charge if self.creator_platform_charge is not None else 1.5)
        return round(fp * (pc / 100.0), 2)

    @property
    def platform_charge_amount(self):
        return self.business_platform_charge_amount

    @property
    def business_total_payment(self):
        fp = float(self.final_price or 0)
        return round(fp + self.business_platform_charge_amount, 2)

    @property
    def creator_net_received(self):
        fp = float(self.final_price or 0)
        return round(fp - self.creator_platform_charge_amount, 2)

    @property
    def total_platform_fee(self):
        return round(self.business_platform_charge_amount + self.creator_platform_charge_amount, 2)

    def get_platform_charge_display(self, obj=None):
        target = obj or self
        b_pc = target.platform_charge if target.platform_charge is not None else 2.5
        c_pc = target.creator_platform_charge if target.creator_platform_charge is not None else 1.5
        return f"Biz: {b_pc}% / Creator: {c_pc}%"
    get_platform_charge_display.short_description = "Platform Charges (Biz / Creator)"

    def get_platform_fee_display(self, obj=None):
        target = obj or self
        return f"${target.total_platform_fee:,.2f}"
    get_platform_fee_display.short_description = "Total Platform Fee"

    def get_creator_net_display(self, obj=None):
        target = obj or self
        return f"${target.creator_net_received:,.2f}"
    get_creator_net_display.short_description = "Creator Net Received"

    def __str__(self):
        return f"Campaign {self.campaign_id} - Price: {self.final_price} (Biz: {self.platform_charge}%, Creator: {self.creator_platform_charge}%) ({self.status})"


class WorkspaceInstallment(models.Model):
    INSTALLMENT_TYPE_CHOICES = (
        ('business', 'Business Installment (Inbound)'),
        ('creator', 'Creator Installment (Outbound)'),
    )
    STATUS_CHOICES = (
        ('in_escrow', 'In Escrow'),
        ('payment_submitted', 'Payment Submitted'),
        ('released', 'Released'),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='workspace_installments')
    negotiation = ParentalKey(WorkspacePaymentNegotiation, on_delete=models.CASCADE, related_name='installments', null=True, blank=True)
    installment_type = models.CharField(max_length=20, choices=INSTALLMENT_TYPE_CHOICES, default='creator')
    title = models.CharField(max_length=255, default='Installment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='in_escrow')
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    receipt_image = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    receipt_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel('installment_type'),
        FieldPanel('title'),
        FieldPanel('amount'),
        FieldPanel('paid_date'),
        FieldPanel('is_paid'),
        FieldPanel('status'),
        FieldPanel('receipt_image'),
    ]

    def save(self, *args, **kwargs):
        if self.status == 'released' or self.is_paid:
            self.is_paid = True
            if not self.paid_date:
                self.paid_date = timezone.now().date()
        super().save(*args, **kwargs)

    @property
    def milestone_name(self):
        return self.title

    @milestone_name.setter
    def milestone_name(self, value):
        self.title = value

    @property
    def payment_date(self):
        return self.paid_date

    def __str__(self):
        return f"{self.title} - Campaign {self.campaign_id} (${self.amount}) - {self.status} (Paid: {self.is_paid})"
