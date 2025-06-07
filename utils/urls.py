# from django.conf.urls import include, url
from django.urls import path, re_path, include
from . import views as util_views

from django.views.generic import ListView

urlpatterns = [
    path('calendar_widget', util_views.calendar_widget_view),
    re_path('remove_notification/(?P<iden>[\w-]+)', util_views.remove_notification_view),
    re_path('continue_reading/(?P<iden>[\w-]+)', util_views.continue_reading_view),
    re_path('show_all/(?P<iden>[\w-]+)/(?P<item>[\w-]+)', util_views.show_all_view),
    
    #----utils
    path('is_sonet', util_views.is_sonet_view),
    path('get_sonet', util_views.get_sonet_view),
    path('set_object_data', util_views.set_object_data_view),
    re_path('get_object_data/(?P<obj_type>(.*))', util_views.get_object_data_view),
    path('get_object_data', util_views.get_object_data_view, {'obj_type':'Region'}),
    path('get_object_id', util_views.get_object_id_view),
    path('can_you_see_me', util_views.can_you_see_me_view),
    path('myip', util_views.myip_view),

    re_path('mobile_share/(?P<iden>(.*))', util_views.mobile_share_view),
    re_path('default_modal/(?P<iden>(.*))', util_views.default_modal_view),
    re_path('share_modal/(?P<iden>(.*))', util_views.share_modal_view),
    re_path('post_insight_modal/(?P<iden>(.*))', util_views.post_insight_view),
    re_path('post_more_options_modal/(?P<iden>(.*))', util_views.post_more_options_view),
    re_path('verify_post_modal/(?P<iden>(.*))', util_views.verify_post_view),
    re_path('generic_modal_data/(?P<func>[\w-]+)/(?P<iden>(.*))', util_views.generic_modal_data_view),
    path('super', util_views.super_view),
    path('tester1', util_views.tester_queue_view),
    path('html_playground1', util_views.html_playground_view),
    path('daily_summarizer', util_views.daily_summarizer_view),
    path('test_notify', util_views.clear_all_app_cache_view),
    path('run_notifications', util_views.add_test_notification_view),
    
    re_path('supersign/(?P<iden>(.*))', util_views.supersign_view, name='supersign'),
    re_path('supersign', util_views.supersign_view, {'iden':''}, name='supersign'),
    re_path('broadcast_datapackets', util_views.broadcast_datapackets_view),
    re_path('tidy_up', util_views.tidy_up_view),
    re_path('test_tasker', util_views.test_tasker_view),
    re_path('show_log/(?P<iden>(.*))', util_views.show_log_view),
    re_path('resume_processes', util_views.resume_processes_view),
    re_path('resume_process/(?P<iden>(.*))', util_views.resume_process_view),

    path('remove_false_blocks', util_views.remove_false_blocks_view),
    re_path('create_test_blocks', util_views.create_test_blocks_view),
    re_path('create_test_block/(?P<name>(.*))', util_views.create_test_block_view),
    re_path('check_validation_consensus/(?P<iden>(.*))', util_views.check_validation_consensus_view),
    re_path('make_not_valid/(?P<iden>(.*))', util_views.make_not_valid_view),
    re_path('make_valid_unknown/(?P<iden>(.*))', util_views.make_valid_unknown_view),
    re_path('invalidate_test_blocks', util_views.invalidate_test_blocks_view),
    re_path('get_assignment/(?P<iden>(.*))/', util_views.get_assignment_view),
    path('get_model_fields', util_views.get_model_fields_view),
    re_path('logs/(?P<logtype>(.*))/', util_views.node_logs_view),
    # path('node_logs', util_views.node_logs_view),
    # path('error_logs', util_views.error_logs_view),
    path('initial_setup', util_views.initial_setup_view),
    path('validate_test_data', util_views.validate_test_data_view),
    path('clear_test_data', util_views.clear_test_data_view),
    re_path('scrapers/(?P<region>(.*))/(?P<test>[\w-]+)', util_views.scrapers_view),
    re_path('run_super_function/(?P<region>(.*))/(?P<func>[\w-]+)/(?P<worker>[\w-]+)/(?P<super>[\w-]+)', util_views.run_super_function_view),
    re_path('run_super_function/(?P<region>(.*))/(?P<func>[\w-]+)', util_views.run_super_function_view, {'worker':'True','super':'False'}),
    re_path('remove_target_test_data_confirm/(?P<region>(.*))/(?P<model>[\w-]+)', util_views.remove_target_test_data_confirm_view),
    re_path('remove_target_test_data/(?P<region>(.*))/(?P<model>[\w-]+)', util_views.remove_target_test_data_view),

    path('django-rq/', include('django_rq.urls')),

    # path('stream/', util_views.stream_view, name='stream'),

    
    # url(r'^mps_update/$', util_views.get_all_mps)
    # path('daily_update', util_views.update_agenda_view),
    # path('all_agendas', util_views.all_agendas_view),
    # path('get_latest_agenda', util_views.get_latest_agenda_view),
    # path('set_party_colours', util_views.set_party_colours_view),
    # path('test_notification', util_views.test_notify_view),

    # #----ontario
    # path('mpps_update', util_views.get_current_mpps_view),
    # path('ontario/current_bills', util_views.get_ontario_bills_view),
    # path('ontario/get_weekly_agenda', util_views.get_ontario_agenda_view),
    # path('ontario/get_motions', util_views.get_ontario_motions_view),
    # path('ontario/get_hansard', util_views.get_ontario_hansard_view),
    # path('ontario/get_latest_hansards', util_views.get_ontario_latest_hansards_view),
    # path('ontario/check_elections', util_views.get_ontario_elections_view),

    # #----federal
    # path('mps_update', util_views.get_all_mps_view),
    # path('senators_update', util_views.get_all_senators_view),
    # path('get_federal_candidates', util_views.get_federal_candidates_view),
    # path('get_federal_house_expenses', util_views.get_federal_house_expenses_view),

    # path('get_todays_xml_agenda', util_views.get_todays_xml_agenda_view),
    
    # path('get_latest_house_motions', util_views.get_latest_house_motions_view),
    # path('get_all_house_motions', util_views.get_all_house_motions_view),
    # path('get_session_senate_motions', util_views.get_session_senate_motions_view),

    # # path('get_todays_bills', util_views.get_todays_bills_view),
    # path('get_latest_bills', util_views.get_latest_bills_view),
    # re_path('update_bill/(?P<iden>\d+)', util_views.update_bill_view),
    # re_path('get_all_bills/(?P<param>[\w-]+)', util_views.get_all_bills_view),

    # path('get_latest_house_hansard', util_views.get_latest_house_hansard_view),
    # path('get_session_house_hansards', util_views.get_session_house_hansards_view),
    # path('get_all_house_hansards', util_views.get_all_house_hansards_view),
    # path('get_all_senate_hansards', util_views.get_all_senate_hansards_view),
    
    # path('get_latest_house_committee_list', util_views.get_latest_house_committee_list_view),
    # path('get_latest_house_committees_work', util_views.get_latest_house_committees_work_view),
    # path('get_latest_house_committees', util_views.get_latest_house_committees_view),
    # # path('get_latest_senate_committees', util_views.get_latest_senate_committees_view),
    # re_path('get_latest_senate_committees/(?P<item>[\w-]+)', util_views.get_latest_senate_committees_view),
    # path('get_all_senate_committees', util_views.get_all_senate_committees_view),
    # re_path('reprocess/(?P<organization>[\w-]+)-committee/(?P<parliament>\d+)/(?P<session>\d+)/(?P<iden>[\w-]+)', util_views.committee_reprocess),
    # re_path('reprocess/(?P<organization>[\w-]+)-debate/(?P<parliament>(.*))/(?P<session>(.*))/(?P<iden>\d+)', util_views.hansard_reprocess),



]
