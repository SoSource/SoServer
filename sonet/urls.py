"""sovote URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
# from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import ListView, TemplateView
from accounts import views as account_views
from utils import views as util_views

from django.urls import path, re_path, include
from django.views.static import serve

urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path('admin/', admin.site.urls),
    path('signup/', account_views.register_view),
    re_path('get_user_data/(?P<username>(.*))', account_views.get_user_data_view),
    path('generate-registration-options/', account_views.register_options_view),
    path('verify-registration/', account_views.register_verify_view),
    path('generate-authentication-options/', account_views.login_options_view),
    path('verify-authentication/', account_views.login_verify_view),
    path('login/', account_views.login_view),
    path('logout/', account_views.logout_view),
    path('sovoteapplogin/', account_views.api_login_view),
    path('sovoteappcreateuser/', account_views.api_create_user_view),
    path('redirect_to_social_auth/', account_views.redirect_to_social_auth_view),
    path('redirect_from_social_auth/', account_views.redirect_from_social_auth_view),
    path('.well-known/assetlinks.json', util_views.deep_link_android_asset_view),
    path('.well-known/apple-app-site-association', util_views.deep_link_iphone_asset_view),

    path('accounts/', include("accounts.urls")),
    path('utils/', include("utils.urls")),
    path('blockchain/', include("blockchain.urls")),
    # path('accounts/', include('allauth.urls')),
    path('', include("posts.urls")),

    re_path(r'^static/(?P<path>.*)$', serve,
            {'document_root': settings.STATIC_ROOT}),
    # url(r'^/', account_views.MP_list),

    # url(r'^utils/', include("utils.urls")),

]

# if settings.DEBUG:
# import debug_toolbar
# print('-----adding toolbar')
# urlpatterns += path('__debug__/', include(debug_toolbar.urls)),
         
