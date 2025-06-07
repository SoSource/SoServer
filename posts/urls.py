from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import ListView, TemplateView
from accounts import views as account_views
from posts import views as posts_views

from django.urls import path, re_path, include
urlpatterns = [
    path('', posts_views.splash_view),
    # path('canada', posts_views.home_view, {'region':'canada'}),
    # path('america', posts_views.home_view, {'region':'america'}),
    re_path('(?P<region>[\w-]+)/home', posts_views.home_view),
    re_path('home', posts_views.home_view, {'region':None}),
    path('following', posts_views.following_view),
    path('privacy_policy', account_views.privacy_policy_view),
    path('sovalues', account_views.values_view),
    path('values', account_views.values_view),
    path('hero', account_views.hero_view),
    path('get-the-app', account_views.get_app_view),
    path('someta', posts_views.someta_view),
    # path('about', account_views.about_view),
    # path('a_story', account_views.story_view),
    path('test', posts_views.test_view),
    
    re_path('profile/(?P<region>[\w-]+)/(?P<name>(.*))/(?P<iden>(.*))', posts_views.representative_view),
    re_path('set-region', account_views.user_set_region_view),
    re_path('user/settings', account_views.user_settings_view),
    re_path('so/(?P<username>(.*))', account_views.user_view),
    re_path('so%7C(?P<username>(.*))', account_views.user_view),
    re_path('u/(?P<username>(.*))', account_views.user_view),
    re_path('u%7C(?P<username>(.*))', account_views.user_view),
    # re_path('user/(?P<username>(.*))/constituency', account_views.user_view),
    re_path('subregions_modal/(?P<region>[\w-]+)/(?P<regionType>[\w-]+)/(?P<baseLink>(.*))', posts_views.subregions_modal_view),
    
    re_path('search/(?P<keyword>(.*))', posts_views.search_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/search/(?P<keyword>(.*))', posts_views.search_view),
    path('region', posts_views.region_view),
    path('citizenry', posts_views.citizenry_view),
    re_path('(?P<region>[\w-]+)/citizenry', posts_views.citizenry_view),
    path('citizen-debates', posts_views.citizen_debates_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/citizen-debates', posts_views.citizen_debates_view),
    path('citizen-bills', posts_views.citizen_bills_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/citizen-bills', posts_views.citizen_bills_view),
    path('polls', posts_views.polls_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/polls', posts_views.polls_view),
    path('petitions', posts_views.petitions_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/petitions', posts_views.petitions_view),
    # path('legislature', posts_views.legislature_view, {'organization':'all'}),
    re_path('(?P<region>[\w-]+)/legislature', posts_views.legislature_view),
    re_path('legislature', posts_views.legislature_view, {'region':'none'}),
    
    # path('legislature/house', posts_views.legislature_view, {'organization':'House'}),
    # path('legislature/senate', posts_views.legislature_view, {'organization':'Senate'}),
    # path('agendas', posts_views.agendas_view, {'organization':'all'}),
    path('agendas', posts_views.agendas_view, {'chamber':'all', 'region':'none'}),
    re_path('(?P<region>[\w-]+)/agendas', posts_views.agendas_view, {'chamber':'all'}),
    re_path('(?P<region>[\w-]+)/(?P<chamber>[\w-]+)-agendas', posts_views.agendas_view),
    re_path('(?P<region>[\w-]+)/agenda-item/(?P<chamber>[\w-]+)/(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)/(?P<hour>\d+):(?P<minute>\d+)', posts_views.agenda_watch_view),
    
    re_path('(?P<region>[\w-]+)/topic/(?P<keyword>(.*))', posts_views.topic_view),

    # path('senator-list', account_views.senator_list),
    # path('mp-list', account_views.MP_list),
    path('officials', posts_views.officials_list, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/officials', posts_views.officials_list),
    # path('officials/mps', account_views.officials_list, {'type':'mps'}),
    # path('officials/senators', account_views.officials_list, {'type':'senators'}),

    re_path('bill/(?P<region>[\w-]+)/(?P<chamber>[a-zA-Z -]+)/(?P<govNumber>\d+)/(?P<session>\d+)/(?P<numcode>(.*))', posts_views.bill_view),
    # re_path('(?P<organization>[\w-]+)-bills/(?P<parliament>\d+)/(?P<session>\d+)', posts_views.bills_view),
    path('bills', posts_views.bills_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/bills', posts_views.bills_view),
    path('house-bills', posts_views.bills_view, {'region':'none'}),
    path('senate-bills', posts_views.bills_view, {'region':'none'}),
    path('debates', posts_views.house_or_senate_hansards_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/debates', posts_views.house_or_senate_hansards_view),
    # path('house-debates', posts_views.house_or_senate_hansards_view, {'type':'house'}),
    # path('senate-debates', posts_views.house_or_senate_hansards_view, {'type':'senate'}),
    path('elections', posts_views.elections_view, {'region':'none'}),
    re_path('(?P<region>[\w-]+)/elections', posts_views.elections_view),
    re_path('election/(?P<chamber>[\w-]+)/(?P<region>(.*))/(?P<iden>\d+)', posts_views.candidates_view),
    
    # re_path('(?P<organization>[\w-]+)-hansards/(?P<parliament>\d+)/(?P<session>\d+)', posts_views.house_or_senate_hansards_view),
    # path('latest-house-hansard', posts_views.latest_house_hansard_view),
    # re_path('house-hansard/(?P<parliament>\d+)/(?P<session>\d+)/(?P<iden>\d+)', posts_views.hansard_view),
    # path('latest-senate-hansard', posts_views.latest_senate_hansard_view),
    # re_path('HouseofCommons-debate/(?P<parliament>(.*))/(?P<session>(.*))/(?P<iden>\d+)', posts_views.hansard_view, {'organization':'house'}),
    re_path('(?P<region>[\w-]+)/(?P<chamber>[\w-]+)-meeting/(?P<govNumber>\d+)/(?P<session>\d+)/(?P<iden>(.*))/', posts_views.debate_view, {'year':None, 'month':None, 'day':None, 'hour':None, 'minute':None}),
    re_path('(?P<region>[\w-]+)/(?P<chamber>[\w-]+)-meeting/(?P<govNumber>\d+)/(?P<session>\d+)/(?P<iden>(.*))/(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)/(?P<hour>\d+):(?P<minute>\d+)', posts_views.debate_view),

    path('committees', posts_views.latest_committees_view, {'chamber':'all', 'region':'none'}),
    re_path('(?P<region>[\w-]+)/committees', posts_views.latest_committees_view, {'chamber':'all'}),
    re_path('(?P<chamber>[\w-]+)-committees', posts_views.latest_committees_view, {'region':'none'}),
    # path('house-committees', posts_views.latest_house_committees_view),
    # path('senate-committees', posts_views.latest_senate_committees_view),
    re_path('(?P<chamber>[\w-]+)-committee/(?P<govNumber>\d+)/(?P<session>\d+)/(?P<iden>[\w-]+)', posts_views.committee_view),
    
    path('motions', posts_views.motions_view, {'region':'none','type':'motion'}),
    re_path('(?P<region>[\w-]+)/motions', posts_views.motions_view, {'type':'motion'}),
    re_path('(?P<region>[\w-]+)/(?P<chamber>[\w-]+)-motion/(?P<govNumber>\d+)/(?P<session>\d+)/(?P<number>(.*))', posts_views.motion_view, {'type':'motion'}),
    path('rollcalls', posts_views.motions_view, {'region':'none','type':'rollcall'}),
    re_path('(?P<region>[\w-]+)/rollcalls', posts_views.motions_view, {'type':'rollcall'}),
    re_path('(?P<region>[\w-]+)/(?P<chamber>[\w-]+)-rollcall/(?P<govNumber>\d+)/(?P<session>\d+)/(?P<number>(.*))', posts_views.motion_view, {'type':'rollcall'}),
    
    
    # path('house-motions', posts_views.house_or_senate_motions_view),
    # re_path('house-motion/(?P<parliament>\d+)/(?P<session>\d+)/(?P<number>\d+)', posts_views.house_motion_view),
    # path('senate-motions', posts_views.house_or_senate_motions_view),
    # re_path('senate-motion/(?P<parliament>\d+)/(?P<session>\d+)/(?P<number>\d+)', posts_views.senate_motion_view),

]