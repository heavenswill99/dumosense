"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""


from django.contrib import admin
from django.urls import include, path

from accounts.views import UserProfileView, ProductEnrollmentListView
from consent.views import ConsentListView,  ConsentWithdrawView, ConsentGrantView


urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentication
    path("api/v1/auth/", include("accounts.urls")),

    # User profile
    path("api/v1/profile/", UserProfileView.as_view(), name="user-profile"),

    # Product enrollments
    path(
        "api/v1/products/",
        ProductEnrollmentListView.as_view(),
        name="user-products",
    ),

    #Consent
    path("api/v1/consents/", ConsentListView.as_view(), name="user-consents"),

    path(
    "api/v1/consents/<str:consent_id>/withdraw/",
    ConsentWithdrawView.as_view(),
    name="withdraw-consent",
    ),

    path(
    "api/v1/consents/<str:consent_id>/grant/",
    ConsentGrantView.as_view(),
    name="grant-consent"   
    ),



    


]