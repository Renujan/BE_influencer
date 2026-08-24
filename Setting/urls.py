from django.urls import path
from .views import CreatorSettingsView, BusinessSettingsView, ChangePasswordView, UploadAvatarView, UploadBankBookView, UploadCoverImageView

urlpatterns = [
    path("creator/", CreatorSettingsView.as_view(), name="creator_settings"),
    path("business/", BusinessSettingsView.as_view(), name="business_settings"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("upload-avatar/", UploadAvatarView.as_view(), name="upload_avatar"),
    path("upload-cover-image/", UploadCoverImageView.as_view(), name="upload_cover_image"),
    path("upload-bank-book/", UploadBankBookView.as_view(), name="upload_bank_book"),
]
