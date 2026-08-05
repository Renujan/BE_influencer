from django.urls import path
from . import views

urlpatterns = [
    path('propose-final-price/', views.propose_final_price, name='propose-final-price'),
    path('creator-action/', views.creator_action, name='creator-action'),
    path('negotiation/<int:campaign_id>/', views.get_negotiation, name='get-negotiation'),
    path('all-negotiations/', views.list_all_negotiations, name='list-all-negotiations'),
    path('admin-approve/', views.admin_approve_negotiation, name='admin-approve-negotiation'),
    path('create-installments/', views.create_installments, name='create-installments'),
    path('update-installment/', views.update_installment, name='update-installment'),
    path('upload-installment-receipt/', views.upload_installment_receipt, name='upload-installment-receipt'),
    path('verify-installment/', views.verify_installment, name='verify-installment'),
    path('installments/<int:campaign_id>/', views.get_installments, name='get-installments'),
]
