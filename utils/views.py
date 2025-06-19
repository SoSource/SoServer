
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.template.defaulttags import register
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt

import django_rq
import datetime
from accounts.models import Notification, UserAction, User
from posts.forms import AgendaForm
from posts.models import Region, Post
from posts.utils import get_user_sending_data, get_client_ip
from blockchain.models import Node, assess_received_header, Sonet
from utils.locked import hash_obj_id, convert_to_dict, get_signing_data
# from scrapers.canada.federal import *
# from scrapers.canada.ontario import provincial as ontario_functions
from utils.models import *
# from utils.models import prnt, prntDebug, timezonify, list_all_scrapers, testing, debugging, prntDebugn, prntn, baseline_time, get_pointer_type, now_utc, has_method, get_or_create_model, create_dynamic_model, get_dynamic_model, set_model_attr, super_share
from firebase_admin.messaging import Notification as fireNotification
from firebase_admin.messaging import Message as fireMessage
import time
import json
import random
from uuid import uuid4
from django.core import serializers

@csrf_exempt
def is_sonet_view(request):
    prnt('is_sonet_view')
    sonet = Sonet.objects.first()
    if sonet:
        x = convert_to_dict(sonet)
    else:
        x = {}
    return JsonResponse({'message' : 'is_sonet', 'sonet' : json.dumps(x)})

@csrf_exempt
def get_sonet_view(request):
    if assess_received_header(request.headers):
        sonet = Sonet.objects.first()
        if sonet:
            return JsonResponse({'message' : 'Success', 'signing_obj' : get_signing_data(sonet), 'model_obj':json.dumps(convert_to_dict(sonet))})
        return JsonResponse({'message' : 'None'})

@csrf_exempt
def set_object_data_view(request):
    prnt('---set_obj_data_view')
    objData_json = 'objData_jsonxx'
    objData = 'objDataxx'
    good = 'unknown'
    x = 'x1'
    try:
        if request.method == 'POST':
            # from utils.models import share_with_network, sync_model, has_field
            raw_data = request.body.decode('utf-8')
            received_data = json.loads(raw_data)

            # userData = json.loads(received_data.get('userData'))
            objData = received_data.get('objData')
            x = 'x2'
            objData_json = json.loads(objData)
            prnt('objData_json',objData_json)
            try:
                extra_objData = received_data.get('extra_objData')
                extra_objData_json = json.loads(extra_objData)
            except:
                pass
            x = objData_json['id']
            prnt('x',x)
            if get_pointer_type(x) == 'Node':
                node = Node.objects.filter(id=x).first()
                if not node:
                    node = Node(id=objData_json['id'], User_obj_id=objData_json['User_obj'])
                    # obj, valid_obj, updatedDB = sync_model(node, objData_json, do_save=False)
                prnt('node',node)
                prnt(objData_json['publicKey'])
                for key in node.User_obj.get_keys(dt=objData_json['last_updated']):
                    prnt(key)
                    if key.publicKey == objData_json['publicKey']:
                        obj, valid_obj, updatedDB = sync_model(node, objData_json)
                        if valid_obj:
                            share_with_network(obj, share_node=True)
                            return JsonResponse({'message' : 'Success', 'obj' : get_signing_data(obj)})
            elif assess_received_header(request.headers):
                prntDebug('set super object..',x)
                prnt('set super object..',x)
                # from utils.models import get_superuser_keys
                superKeys = get_superuser_keys(data=objData_json)
                prntDebug('superKeys',superKeys)
                prnt('superKeys',superKeys)
                if objData_json['publicKey'] in superKeys:
                    prntDebug('is super')
                    prnt('is super')
                    # prntDebug('objData_json',objData_json)
                    # prnt('---1')
                    # prnt(get_signing_data(objData_json))
                    # prnt()
                    # prnt(convert_to_dict(objData_json))
                    # prnt('----2')
                    obj = get_or_create_model(objData_json['object_type'], id=objData_json['id'])
                    if has_field(obj, 'created') and not obj.created:
                        obj.created = now_utc()
                    x = obj
                    obj, valid_obj, updatedDB = sync_model(obj, objData_json)
                    prntDebug('synced:',updatedDB,'valid_obj',valid_obj)
                    prnt('synced:',updatedDB,'valid_obj',valid_obj)
                    if valid_obj:
                        if has_method(obj, 'boot'):
                            obj.boot()
                        objs, good = super_share(obj, func='set_object', val_type='set_object', job_id=random.randint(1, 100))
                        prntDebug('obj-good',good)
                        prnt('obj-good',good)
                        if good:
                            return JsonResponse({'message' : 'Success', 'obj' : get_signing_data(objs[0])})
                    
            return JsonResponse({'message' : 'A problem occured', 'obj':objData,  'err': f' -- is_good: {good} -- x: {x}'})
    except Exception as e:
        prntDebug('fail38585', str(e))
        prnt('fail38585', str(e))
        prntDebug('objData_json',objData_json)
        prntDebug('objData',objData)
        return JsonResponse({'message' : f'A problem occured', 'err': f'{str(e)} -- objData: {objData} -- objData_json: {objData_json} -- good: {good} -- x: {x}'})
    
@csrf_exempt
def get_object_data_view(request, obj_type='Region'):
    prnt('--get_object_data_view')
    err = 0
    try:
        if request.method == 'POST':
            err = 1

            raw_data = request.body.decode('utf-8')
            received_data = json.loads(raw_data)

            obj_type = received_data.get('obj_type')
            obj_id = received_data.get('obj_id')
            err = 2
            if obj_id == '0':
                obj = create_dynamic_model(obj_type)
                if has_method(obj,'initialize'):
                    obj.initialize()
                else:
                    obj.id = hash_obj_id(obj) # creating id for some models before data is assigned may result in discrepancy if id not rehashed after data assignment
            else:
                if assess_received_header(request.headers):
                    err = 3
                    obj = get_dynamic_model(obj_type, id=obj_id)
                    if obj and obj.modelVersion != obj.latestModel:
                        from utils.locked import skip_sign_fields
                        latest_fields = obj.get_version_fields(version=obj.latestModel)
                        latest_singing_fields = {key:value for key, value in latest_fields.items() if key not in skip_sign_fields}
                        return JsonResponse({'message' : 'Success', 'signing_obj' : get_signing_data(obj), 'model_obj':json.dumps(convert_to_dict(obj)), 'latest_fields':json.dumps(latest_fields), 'latest_singing_fields':json.dumps(latest_singing_fields)})
            return JsonResponse({'message' : 'Success', 'signing_obj' : get_signing_data(obj), 'model_obj':json.dumps(convert_to_dict(obj))})
        else:
            
            if obj_type == 'Earth':
                err = 4
                prnt('else')
                earthModel = Region(created=now_utc(), func='super', nameType='Planet', Name='Earth', modelType='planet', LogoLinks={"flag":"img/earth_pic.jpg"})
                earthModel.id = hash_obj_id(earthModel)
                return JsonResponse({'message' : 'Success', 'signing_obj' : get_signing_data(earthModel), 'model_obj':json.dumps(convert_to_dict(earthModel))})
            else:
                obj = create_dynamic_model(obj_type)
                if has_method(obj, 'initialize'):
                    obj.initialize()
                return JsonResponse({'message' : 'Success', 'signing_obj' : get_signing_data(obj), 'model_obj':json.dumps(convert_to_dict(obj))})

    except Exception as e:    
        prnt('fail56930532',str(e))
        return JsonResponse({'message' : 'failed', 'err':f'fail1: {str(e)} -- err:{err}'})

@csrf_exempt
def get_object_id_view(request):
    prnt('get_object_id_view')
    try:
        if request.method == 'POST':
            if assess_received_header(request.headers): # some redundant verifying beneath this 

                raw_data = request.body.decode('utf-8')
                received_data = json.loads(raw_data)

                objData = received_data.get('objData')
                # objData = request.POST.get('objData')
                objData_json = json.loads(objData)
                prntDebug('objData_json',objData_json)
                obj_type = objData_json['object_type']
                nodeData = received_data.get('nodeData')
                nodeData_json = json.loads(nodeData)
                operator = Node.objects.filter(id=nodeData_json['id']).first().User_obj
                # if operator.verify_sig(objData_json, objData_json['signature']):
                obj = create_dynamic_model(obj_type, id=objData_json['id'])
                obj, updatedDB = set_model_attr(obj, objData_json, operator)
                prntDebug('202-3',hash_obj_id(obj))
                prntDebug('202-4',hash_obj_id(obj, return_data=True))
                obj.id = hash_obj_id(obj)
                prntDebug('returnning--obj.id',convert_to_dict(obj))
                return JsonResponse({'message' : 'Success', 'obj' : get_signing_data(obj), 'obj_id':obj.id})
    except Exception as e:
        prnt('fail12340986',str(e))     
        return JsonResponse({'message' : 'A problem occured', 'err':str(e)})
    
@csrf_exempt
def can_you_see_me_view(request):
    prnt('can you see me')
    try:
        sender_ip = get_client_ip(request)  
        prnt('from:',sender_ip)
        requested_address = 'unknown'
        if request.method == 'POST':

            raw_data = request.body.decode('utf-8')
            received_data = json.loads(raw_data)

            requested_address = received_data.get('requested_address','')
            prnt('requested_address',requested_address)
            # if sender_ip in requested_address:
            import requests
            if requested_address:
                r = requests.get(f'http://{requested_address}/utils/is_sonet', timeout=5)
                check_address = requested_address
            else:
                r = requests.get(f'http://{sender_ip}/utils/is_sonet', timeout=5)
                check_address = sender_ip
            prnt(r.status_code)
            if r.status_code == 200:
                received_json = r.json()
                if received_json['message'] == 'is_sonet':
                    # node = Node.objects.filter(ip_address=requested_address).first()
                    # if node:
                    #     node = json.dumps(convert_to_dict(node))
                    return JsonResponse({'message' : 'Success', 'requested_address' : requested_address, 'actual_address':sender_ip, 'check_address':check_address})
                # else:
                #     return JsonResponse({'message' : 'not sonet', 'requested_address' : requested_address, 'actual_address':sender_ip})
            return JsonResponse({'message' : 'error', 'requested_address' : requested_address, 'actual_address':sender_ip})
    except Exception as e:
        return JsonResponse({'message' : f'A problem occured','err':str(e), 'requested_address' : requested_address, 'actual_address':sender_ip})
    
@csrf_exempt
def myip_view(request):
    prnt('myip_view')
    sender_ip = get_client_ip(request)
    prnt('sender_ip',sender_ip)
    return render(request, "utils/dummy.html", {"result": sender_ip})
    

def calendar_widget_view(request):
    prnt('cal widget')
    if request.method == 'POST':
        data = request.POST['date']
        # prnt(data)
        # a = data.find('date=')+len('date=')
        date = datetime.datetime.strptime(data, '%Y-%m-%d')
        # prnt(date)
        agenda = Agenda.objects.filter(date_time__gte=date).order_by('date_time')[0]
        agendaItems = AgendaItem.objects.filter(agendaTime__agenda=agenda).select_related('agendaTime').order_by('position')
        form = AgendaForm()   
        try:
            theme = request.COOKIES['theme']
        except:
            theme = 'day'
        context = {
            "theme": theme,
            "agenda":agenda,
            "agendaItems":agendaItems,
            'agendaForm': form,
        }
        return render(request, "utils/agenda_widget.html", context)

def mobile_share_view(request, iden):
    prnt('mobile share')
    post = Post.objects.filter(id=iden).first()
    link = post.get_absolute_url()
    if link[0] == '/':
        link = 'https://SoVote.org' + link
    shareTitle = post.get_title() + ' ' + link
    prnt(shareTitle)
    try:    
        fcmDeviceId = request.COOKIES['fcmDeviceId']
        prnt(fcmDeviceId)
        device = FCMDevice.objects.filter(user=request.user, registration_id=fcmDeviceId).first()
        device.send_message(fireMessage(data={"share" : "True", "shareTitle":shareTitle}))
    except Exception as e:
        prnt(str(e))
    return render(request, "utils/dummy.html", {"result": 'Success'})

def default_modal_view(request, iden):
    return render(request, f"modals/{iden}.html")

def share_modal_view(request, iden):
    post = Post.objects.filter(id=iden).first()
    context = {
        'title': 'Share Post',
        'post': post,
    }
    return render(request, "modals/share_modal.html", context)

@register.filter
def to_percent(num1, num2):
    try:
        percent = (num1 + num2) / num1
    except:
        percent = '-'
    return percent

def post_insight_view(request, iden):
    post = Post.objects.filter(id=iden).first()
    context = {
        'title': 'Insight',
        'post': post,
    }
    return render(request, "modals/post_insight.html", context)

def post_more_options_view(request, iden):
    prnt(iden)
    post = Post.objects.filter(id=iden).first()
    useraction = UserAction.objects.filter(User_obj=request.user, Post_obj=post).first()
    context = {
        'title': 'More Options',
        'post': post,
        'useraction':useraction,
    }
    return render(request, "modals/post_more_options.html", context)

def generic_modal_data_view(request, func, iden):
    prnt(iden)
    post = Post.objects.filter(id=iden).first()
    if func == 'modelData':
        title = 'Model Data'
        update = None
        pointer = post.get_pointer()
        obj = convert_to_dict(pointer, withold_fields=False)
        if has_field(pointer, 'created'):
            obj['created'] = pointer.created
        # elif has_field(pointer, 'created'):
        #     obj['created'] = pointer.created
        obj['updated_on_node'] = pointer.updated_on_node
        post_dict = convert_to_dict(post, withold_fields=False)
        post_dict['updated_on_node'] = post.updated_on_node
        if post.Update_obj:
            update = convert_to_dict(post.Update_obj, withold_fields=False)
            update['created'] = post.Update_obj.created
            update['updated_on_node'] = post.Update_obj.updated_on_node
            # update['validated'] = post.Update_obj.validated
    context = {
        'title': title,
        'obj': obj,
        'post': post_dict,
        'update': update
    }
    return render(request, "modals/generic_modal.html", context)

def verify_post_view(request, iden):

    post = Post.all_objects.filter(id=iden).first()
    context = {
        'title': 'Verify Me',
        'post': post,
    }
    return render(request, "utils/verify_post.html", context)

def deep_link_android_asset_view(request):
    return render(request, "json/deep_link_android_asset.html", content_type="application/json")

def deep_link_iphone_asset_view(request):
    return render(request, "json/deep_link_iphone_asset.html", content_type="application/json")

def continue_reading_view(request, iden):
    # prnt(iden)
    topic = request.GET.get('topic', '')
    # prnt(topic)
    if 'statement-' in iden:
        from legis.models import Statement
        Id = iden.replace('statement-', '')
        hansard = Statement.objects.get(id=Id)
        context = {'h':hansard, 'topicList':topic}
    # elif 'commi-' in iden:
    #     Id = iden.replace('c-', '')
    #     committee = CommitteeItem.objects.get(id=Id)
    #     context = {'c':committee, 'topicList':topic}
    return render(request, "utils/read_more.html", context)

def show_all_view(request, iden, item):
    if iden[0] == 'h':
        Id = iden[2:]
        # prnt(Id)
        hansard = Hansard.objects.get(id=Id)
        if item == 'terms':
            setlist = hansard.list_all_terms()
        else:
            setlist = hansard.list_all_people()
        context = {'hansard':hansard,'setlist':setlist, 'item':item}
    if iden[0] == 'c':
        Id = iden[2:]
        # prnt(Id)
        committee = Committee.objects.get(id=Id)
        if item == 'terms':
            setlist = committee.list_all_terms()
        else:
            setlist = committee.list_all_people()
        context = {'committee':committee,'setlist':setlist, 'item':item}
    return render(request, "utils/show_all.html", context)





# processes = EventLog.objects.filter(type__icontains='process', created__lte=now_utc() - datetime.timedelta(minutes=10))
# prnt('processes',processes)
# if processes:
    
#     for log in processes:
#         prnt('log',log)
#         skip = False
#         if log.created < now_utc() - datetime.timedelta(hours=3):
#             log.delete()
#         elif not log.data:
#             log.delete()
#         else:
#             prnt('log has Data')
#             func = log.type
#             prnt('func',func)
#             skip = False
#             queue = django_rq.get_queue('low')
#             if not exists_in_worker(func, log.id, queue):
#                 prnt('Continuing Run:', func)
#                 # result['restore failed process'].append(f'{region} {func}')
#                 logEvent(f'restoring process: {func} log:{log.id}, len:{len(log.data)}')
#                 # queue.enqueue(cmd, special='super', job_timeout=scraperScripts.runTimes[f]*5)    
#                 queue.enqueue(globals()[func], log.id, job_timeout=300)


#----utils

def broadcast_datapackets_view(request):
    if request.user.is_superuser:
        from blockchain.models import DataPacket, NodeChain_genesisId
        self_node = get_self_node()
        dataPackets = DataPacket.objects.filter(Node_obj=self_node, func='share').exclude(data={})
        for dp in dataPackets:
            if len(dp.data.keys()) > 0 or dp.chainId == NodeChain_genesisId:
                queue = django_rq.get_queue('low')
                queue.enqueue(dp.broadcast, job_timeout=120, result_ttl=3600)
    
def run_super_function_view(request, region, func, worker, super):
    prnt('run_super_function_view', region, func, worker,super)
    if request.user.assess_super_status():
        start_time = timezonify('est', datetime.datetime.now())
        end_time = None
        # if test == 'False':
        #     run_test = False
        # else:
        #     run_test = True

        all_files = list_all_scrapers()
        result = 'result to come'
        for file in all_files:
            try:
                a = file.find('/scrapers/')+len('/scrapers/')
                x = file[a:]
                words = x.split('/')
                txt = x.replace('/', '.').replace('.py','')
                if txt == region:
                    import importlib
                    scraperScripts = importlib.import_module('scrapers.'+txt) 
                    approved_models = scraperScripts.approved_models
                    for f, models in approved_models.items():
                        if f == func:
                            prnt('RUNNING:', func, super, worker)
                            start_time = timezonify('est', datetime.datetime.now())
                            prnt(start_time)
                            prnt()
                            cmd = getattr(scraperScripts, f)
                            from utils.cronjobs import clear_chrome
                            if super == 'Test' and worker == 'False':
                                result = cmd(special='testing')
                                # prnt('returned:',result)
                                clear_chrome()
                            elif super == 'Test' and worker == 'True':
                                queue = django_rq.get_queue('low')
                                queue.enqueue(cmd, special='testing', job_timeout=scraperScripts.runTimes[f]*7)
                                queue = django_rq.get_queue('low')
                                queue.enqueue(clear_chrome, job_timeout=15)

                            elif super == 'Super' and worker == 'False':
                                prnt('run here')
                                result = cmd(special='super')
                                clear_chrome()
                            elif super == 'Super' and worker == 'True':
                                queue = django_rq.get_queue('low')
                                queue.enqueue(cmd, special='super', job_timeout=scraperScripts.runTimes[f]*7)
                    
                                queue = django_rq.get_queue('low')
                                queue.enqueue(clear_chrome, job_timeout=15)

                            elif super == 'False' and worker == 'False':
                                result = cmd()
                                clear_chrome()
                            elif super == 'False' and worker == 'True':
                                queue = django_rq.get_queue('low')
                                queue.enqueue(cmd, job_timeout=scraperScripts.runTimes[f]*7)
                    
                                queue = django_rq.get_queue('low')
                                queue.enqueue(clear_chrome, job_timeout=15)

                            prnt()
                            prnt('completed run')
                            end_time = timezonify('est', datetime.datetime.now())
                            prnt(end_time - start_time)
                            break
                    break
            except Exception as e:
                prnt('BIG Fail 48264', str(e))
                end_time = timezonify('est', datetime.datetime.now())
                return render(request, "utils/dummy.html", {"result": str(e) + ' - ' + str(end_time - start_time)})
        if not end_time:
            end_time = timezonify('est', datetime.datetime.now())
        return render(request, "utils/dummy.html", {"result": str(result) + ' - ' + str(end_time - start_time)})
    
def scrapers_view(request, region, test):
    if request.user.assess_super_status():
        all_files = list_all_scrapers()
        prnt(all_files)
        def get_models():
            from utils.models import get_app_name
            m = []
            # for key, value in get_app_name(return_model_list=True).items():
            #     if value['app_name'] == 'sovote' or value['app_name'] == 'posts':
            #         m.append(key)
            return reversed(m)
        scripts = {}
        for file in all_files:
            try:
                a = file.find('/scrapers/')+len('/scrapers/')
                x = file[a:]
                words = x.split('/')
                scraper_region = words[-2]
                if scraper_region == region:
                    txt = x.replace('/', '.').replace('.py','')
                    scripts[txt] = []
                    import importlib
                    scraperScripts = importlib.import_module(txt) 
                    approved_models = scraperScripts.approved_models
                    for f, models in approved_models.items():
                        scripts[txt].append({txt:f})
            except Exception as e:
                prnt(str(e))
                pass
        # prnt(scripts)
        return render(request, "utils/run_scrapers.html", {'scripts':scripts, 'region':region, 'test':test, 'models':get_models()})

def super_view(request):
    # u = request.user
    # prnt(u)
    # prnt(u.is_superuser)
    if request.user.assess_super_status(): # should have reduced options if superuser is not node operator
        from blockchain.models import get_self_node
        self_node = get_self_node()
        if self_node:
            self_node_name = self_node.node_name
        else:
            self_node_name = 'node unknown'
        all_files = list_all_scrapers()
        # prnt(all_files)
        regions = []
        for file in all_files:
            try:
                a = file.find('/scrapers/')+len('/scrapers/')
                x = file[a:]
                words = x.split('/')
                region = words[-2]
                regions.append(region)
            except Exception as e:
                prnt(str(e))
                pass
        return render(request, "utils/super.html", {'utc':now_utc().strftime("%Y-%m-%d %H:%M:%S"), 'regions':regions, 'scripts':True, 'self_node_name':self_node_name})

def node_logs_view(request, logtype):
    if request.user.is_superuser:
        from blockchain.models import EventLog
        node = get_self_node()
        logs = EventLog.objects.filter(type__iexact=logtype, Node_obj=node).order_by('-created')
        return render(request, "utils/super.html", {'is_logs':True, 'logs':logs})
    
def show_log_view(request, iden):
    if iden.lower() in ['logbook', 'errors', 'tasks', 'requesteditems']:
        # prnt('show_log_view',iden)
        sorted_data = {}
        from blockchain.models import EventLog
        log = EventLog.objects.filter(type__iexact=iden).first()
        # prnt('log',log)
        if log:
            count = request.GET.get('count', 200)
            sorted_data = dict(sorted(log.data.items(), key=lambda item: item[1]))
            # sorted_data = dict(sorted(log.data.items(), key=lambda item: datetime.datetime.fromisoformat(item[0])))
            from itertools import islice
            sorted_data = "\n".join(f"{string_to_dt(key).strftime('%Y-%m-%d %H:%M')}: {value}" for key, value in islice(sorted_data.items(), count) )
        return JsonResponse({'message' : sorted_data})
    if request.user.is_superuser:
        # prnt('show_log_view',iden)
        from blockchain.models import EventLog
        log = EventLog.objects.filter(id=iden).first()
        if log:
            sorted_data = dict(
                sorted(
                    log.data.items(),
                    key=lambda item: string_to_dt(item[0]),
                    reverse=True
                )
            )
            return render(request, "utils/super.html", {'show_log':True, 'log':log, 'log_data':sorted_data})
    


def test_tasker_view(request):
    if request.user.is_superuser:
        from blockchain.models import tasker
        start_date = '%s-%s-%s-%s:00' %(2024, 11, 12, 10)
        start_date = '%s-%s-%s-%s:00' %(2024, 11, 23, 7)
        day = datetime.datetime.strptime(start_date, '%Y-%m-%d-%H:%M').astimezone(pytz.utc)  
        # tasker(now_utc(), test=False)
        tasker(now_utc(), test=True)
        # queue = django_rq.get_queue('default')
        # # queue.enqueue(tasker, day, True, job_timeout=300)
        # queue.enqueue(tasker, now_utc(), True, job_timeout=300)
        return JsonResponse({'message' : 'complete'})

def tidy_up_view(request):
    from blockchain.models import Tidy
    # queue = django_rq.get_queue('low')
    # queue.enqueue(tidy, job_timeout=600)
    queue = django_rq.get_queue('low')
    queue.enqueue(Tidy()._add_all_jobs, job_timeout=60)
    return JsonResponse({'message' : 'running'})


def initial_setup_view(request):
    if request.user.is_superuser:
        if testing() or debugging():
            # sonet = Sonet.objects.first()
            # if not sonet:
            #     sonet = Sonet(Title='SoTest', created=now_utc(), last_updated=now_utc())
            #     sonet.id = hash_obj_id(sonet)
            #     super(Sonet, sonet).save()
            earth = Region.valid_objects.filter(nameType='Planet', Name='Earth', modelType='planet').first()
            if not earth:
                earth = Region(created=now_utc(), func='super', nameType='Planet', Name='Earth', modelType='planet', LogoLinks={"flag":"/static/img/earth_pic.jpg"})
                # earth.id = hash_obj_id(earth)
                earth.save()
            na = Region.valid_objects.filter(Name='North America', nameType='Continent', modelType='continent', ParentRegion_obj=earth).first()
            if not na:
                na = Region(created=now_utc(), func='super', Name='North America', nameType='Continent', modelType='continent', ParentRegion_obj=earth)
                # na.id = hash_obj_id(na)
                na.save()
            usa = Region.valid_objects.filter(Name='USA', modelType='country', nameType='Country', ParentRegion_obj=na).first()
            if not usa:
                usa = Region(is_supported=True, created=now_utc(), func='super', Name='USA', modelType='country', nameType='Country', ParentRegion_obj=na, menuItem_array=['Bills', 'Debates', 'RollCalls', 'Officials'], Chamber_array=['Executive', 'House', 'Senate'], LogoLinks={"flag":"img/usa/american_flag.jpg"})
                # usa.id = hash_obj_id(usa)
                usa.save()
            can = Region.valid_objects.filter(Name='Canada', modelType='country', nameType='Country', ParentRegion_obj=na).first()
            if not can:
                can = Region(is_supported=True, created=now_utc(), func='super', Name='Canada', modelType='country', nameType='Country', menuItem_array=['Bills', 'Debates', 'Motions', 'Officials'], Chamber_array=['House', 'Senate'], ParentRegion_obj=na, LogoLinks={"flag":"img/canada/canadian_flag.jpg"})
                # can.id = hash_obj_id(can)
                can.save()
            node = Node.objects.filter(User_obj=request.user).first()
            if not node:
                node = Node(created=now_utc(), User_obj=request.user, activated_dt=now_utc(), ip_address='127.0.0.1:3005', last_updated=now_utc())
                node.id = hash_obj_id(node)
                super(Node, node).save()
            for u in User.objects.all():
                u.boot()

            return JsonResponse({'message' : 'initial setup complete'})

def validate_test_data_view(request):
    if request.user.is_superuser:
        if testing() or debugging():
            models = ['Region',
            'Update',
            'District',
            'Person',
            'Party',
            'Government',
            'Vote',
            'Motion',
            'Committee',
            'Statement',
            'Meeting',
            'Bill',
            # 'BillVersion',
            'Agenda',
            # 'AgendaItem',
            # 'AgendaTime',
            'GenericModel',
            'Post',
            'Keyphrase',
            'KeyphraseTrend',
            'Election'
            ]
            for model in models:
                prnt('\nget model:', model)
                objs = get_dynamic_model(model, list=True)
                for obj in objs:
                    prnt('\n',obj)
                    try:
                        if has_field(obj, 'boot'):
                            post = obj.boot()
                            # prnt('post',post)
                            if post:
                                post.validated = True
                                post.save()
                            if has_method(obj, 'upon_validation'):
                                obj.upon_validation()
                        elif obj.object_type == 'Update':
                            obj.sync_with_post()
                        elif obj.object_type == 'Post':
                            # prnt('ispost')
                            obj.validated = True
                            obj.save()
                            # prnt('dpost')
                    except Exception as e:
                        prnt('\n',str(e))
                        time.sleep(2)

            return JsonResponse({'message' : 'complete'})
        return JsonResponse({'message' : 'is production'})

def resume_process_view(request, iden):
    if request.user.assess_super_status():
        try:
            from blockchain.models import EventLog
            log = EventLog.objects.filter(id=iden).first()
            if 'process' in log.type:
                func = log.type
                import importlib
                functions = importlib.import_module('blockchain.models')
                cmd = getattr(functions, func)
                cmd(log.id)
            else:
                # from utils.cronjobs import finishScript
                # from utils.models import list_all_scrapers
                all_files = list_all_scrapers()

                region = log.data['region_name'].lower()
                prnt('region',region)
                func = log.data['func']
                prnt('func',func)
                special = log.data['special']
                prnt('special',special)
                for file in all_files:
                    # if not skip:
                    # try:
                    a = file.find('/scrapers/')+len('/scrapers/')
                    x = file[a:]
                    words = x.split('/')
                    txt = x.replace('/', '.').replace('.py','')
                    # prnt('txt',txt)
                    if region in txt:
                        prnt('yes1')
                        import importlib
                        scraperScripts = importlib.import_module('scrapers.'+txt) 
                        approved_models = scraperScripts.approved_models
                        for f, models in approved_models.items():
                            # if not skip:
                                # prnt(f,models)
                            if f == func:
                                finishScript(log, func=func, special=special)
                                    # if not exists_in_worker('finishScript', log, queue):
                                    #     prnt('Continuing Run:', func)
                                    #     result['restore failed scrapers'].append(f'{region} {func}')
                                    #     logEvent(f'finishScript: {region} {func} len:{len(log.data["shareData"])}')
                                    #     # queue.enqueue(cmd, special='super', job_timeout=scraperScripts.runTimes[f]*5)    
                                    #     queue.enqueue(finishScript, log, func=func, job_timeout=scraperScripts.runTimes[f])


            return JsonResponse({'message' : 'it is done'})
        except Exception as e:
            prnt('fail395',str(e))
            return JsonResponse({'message' : 'fail', 'error':str(e)})

def resume_processes_view(request):
    if request.user.assess_super_status():
        from blockchain.models import EventLog
        processes = EventLog.objects.filter(Q(type__icontains='process')|Q(type__icontains='scrape assignment'))
        data = {b:{'id':b.id,'type':b.type,'dt':b.created} for b in processes}
        # from blockchain.models import get_self_node
        self_node = get_self_node()
        return render(request, "utils/super.html", {'show_processes':True, 'data':data, 'self_node_name': self_node.node_name if self_node else 'node unknown'})

def invalidate_test_blocks_view(request):
    if request.user.assess_super_status():
        if testing() or debugging():
            prnt('---invalidate_test_blocks_view')
            from blockchain.models import Block
            noneBlocks = Block.objects.filter(validated=None).distinct('Blockchain_obj_id').order_by('Blockchain_obj_id','-index', '-created')[:50]
            failBlocks = Block.objects.filter(validated=False).distinct('Blockchain_obj_id').order_by('Blockchain_obj_id','-index', '-created')[:50]
            passBlocks = Block.objects.filter(validated=True).distinct('Blockchain_obj_id').order_by('Blockchain_obj_id','-index', '-created')[:50]
            prnt('passBlocks',passBlocks)
            noneBlockData = {b.Blockchain_obj:{'id':b.id,'index':b.index,'created':b.created} for b in noneBlocks}
            failBlockData = {b.Blockchain_obj:{'id':b.id,'index':b.index,'created':b.created} for b in failBlocks}
            passBlockData = {b.Blockchain_obj:{'id':b.id,'index':b.index,'created':b.created} for b in passBlocks}
            prnt('passBlockData',passBlockData)
            # from blockchain.models import get_self_node
            self_node = get_self_node()
            return render(request, "utils/super.html", {'show_blocks':True, 'noneBlockData':noneBlockData, 'failBlockData':failBlockData, 'passBlockData':passBlockData, 'self_node_name': self_node.node_name if self_node else 'node unknown'})

def make_not_valid_view(request, iden):
    prntDebug('---make_not_valid_view')
    if request.user.assess_super_status():
        prnt('pass1')
        if testing() or debugging():
            prntDebug('pass2')
            from blockchain.models import Block
            block = Block.objects.filter(id=iden).first()
            if block:
                prntDebug('pass3')
                if testing():
                    prntDebug('pass4')
                    block.is_not_valid()
                else:
                    prntDebug('pass5')
                    queue = django_rq.get_queue('low')
                    queue.enqueue(block.is_not_valid, job_timeout=500)
                prntDebug('pass6')
                return JsonResponse({'message' : 'it is done'})
            return JsonResponse({'message' : 'block not found'})
        
def make_valid_unknown_view(request, iden):
    prntDebug('---make_valid_unknown_view')
    if request.user.assess_super_status():
        prnt('pass1')
        if testing() or debugging():
            prntDebug('pass2')
            from blockchain.models import Block
            block = Block.objects.filter(id=iden).first()
            if block:
                block.validated = None
                super(Block, block).save()
                prntDebug('pass3')
                return JsonResponse({'message' : 'it is done'})
            return JsonResponse({'message' : 'block not found'})
        
@csrf_exempt
def remove_false_blocks_view(request):
    prnt('---remove_false_blocks_view')
    if request.method == 'POST':
        prnt('proceed')
        # received_data = request.POST.dict()
        if assess_received_header(request.headers, return_is_self=True):
            # from blockchain.models import Block
            raw_data = request.body.decode('utf-8')
            received_data = json.loads(raw_data)
            
            try:
                userData = json.loads(received_data.get('userData'))
                # prntDebug('userData',userData)
                # prnt('reqesed dict',isinstance(userData, dict))
                # prnt('reqesed str',isinstance(userData, str))
            except Exception as e:
                prnt('fail593363',str(e))
            # prnt('------------')


            # upkData = json.loads(request.POST.get('upkData'))
            # prnt('upkData',upkData)
            nodeData = json.loads(received_data.get('nodeData'))
            # prntDebug('nodeData',nodeData)
            # prnt('reqesed dict',isinstance(nodeData, dict))
            # prnt('reqesed str',isinstance(nodeData, str))
            # prnt('---')
            try:
                requested_data = json.loads(received_data.get('request'))
                prntDebug('requested_data',requested_data)
                # prnt('reqesed dict',isinstance(requested_data, dict))
                # prnt('reqesed str',isinstance(requested_data, str))
            except Exception as e:
                prnt('fail5933234',str(e))
            # prnt('------------')
            if 'signature' in requested_data:
                sig = requested_data['signature']
                del requested_data['signature']
                from blockchain.models import Blockchain, Block
                self_node = get_self_node()
                if self_node and self_node.User_obj.verify_sig(requested_data, sig, simple_verify=True):

                    chainId = requested_data['chainId']
                    if chainId:
                        chain = Blockchain.objects.filter(id=chainId).first()
                        for b in Block.objects.filter(Blockchain_obj=chain, validated=False):
                            b.delete()

                    return JsonResponse({'message' : 'Success'})
        return JsonResponse({'message' : 'Failure'})
        
def create_test_blocks_view(request):
    if request.user.assess_super_status():
        if testing() or debugging():
            from blockchain.models import NodeChain_genesisId, Block, Blockchain
            nodechain = Blockchain.objects.filter(genesisId=NodeChain_genesisId).first()
            if not nodechain:
                nodechain = Blockchain(genesisId=NodeChain_genesisId, genesisType='Nodes', genesisName='Nodes', created=baseline_time(), last_block_datetime=now_utc()-datetime.timedelta(days=2))
            nodechain.last_block_datetime=now_utc()-datetime.timedelta(days=2)
            nodechain.save()
            for node in Node.objects.all():
                nodechain.add_item_to_queue(node)
            chains = Blockchain.objects.all().order_by('genesisType','genesisName')
            chainData = {str(c).replace('chain:',''):{'length':c.chain_length,'id':c.id,'queue':len(c.queuedData)} for c in chains}
            unValBlocks = Block.objects.filter(validated=None)
            blockData = {b.Blockchain_obj:{'id':b.id} for b in unValBlocks}
            # from blockchain.models import get_self_node
            self_node = get_self_node()
            return render(request, "utils/super.html", {'show_chains':True, 'chainData':chainData, 'blockData':blockData, 'self_node_name': self_node.node_name if self_node else 'node unknown'})

def create_test_block_view(request, name):
    if request.user.assess_super_status():
        if testing() or debugging():
            from blockchain.models import Blockchain
            chain = Blockchain.objects.filter(id=name).first()
            prnt(chain)
            if testing():
                result = chain.new_block_candidate(add_to_queue=False)
            else:
                result = 'running'
                queue = django_rq.get_queue('low')
                queue.enqueue(chain.new_block_candidate, job_timeout=500)
            return render(request, "utils/dummy.html", {"result": str(result)})

def check_validation_consensus_view(request, iden):
    if request.user.assess_super_status():
        is_valid = 'unknown'
        from blockchain.models import Block
        from utils.locked import check_validation_consensus
        block = Block.objects.filter(id=iden).first()
        if block: 
            if testing():
                is_valid, consensus_found, validations = check_validation_consensus(block, broadcast_if_unknown=False)
            else:
                queue = django_rq.get_queue('low')
                queue.enqueue(check_validation_consensus, block, broadcast_if_unknown=False, job_timeout=500)
            
        return render(request, "utils/dummy.html", {"result": str(is_valid)})
    
def get_assignment_view(request, iden):
    if request.user.assess_super_status():
        prnt('idne',iden)
        if str(iden) == '0':
            return render(request, "utils/dummy.html", {"result": str(0)})
        obj = get_dynamic_model(get_pointer_type(iden), id=iden)
        prnt('obj',obj)
        if obj:
            def convert(field):
                if not isinstance(field, str):
                    field = str(field)
                if 'false' in field.lower():
                    return False
                elif 'true' in field.lower():
                    return True
                elif 'none' in field.lower():
                    return None
                return field
            # creator_only = convert(request.GET.get('creator_only', False))
            dt = convert(request.GET.get('dt', None))
            func = convert(request.GET.get('func', None))
            chainId = convert(request.GET.get('chainId', None))
            # scrapers_only = convert(request.GET.get('scrapers_only', False))
            sender_transaction = convert(request.GET.get('sender_transaction', False))
            full_validator_list = convert(request.GET.get('full_validator_list', False))
            # strings_only = convert(request.GET.get('strings_only', True))
            # if isinstance(creator_only, bool):
            #     prnt('isbool')
            prnt('dt',dt,'func',func,'chainId',chainId,'scrapers_only','scrapers_only','sender_transaction',sender_transaction,'full_validator_list',full_validator_list,'strings_only','strings_only')
            from utils.locked import get_node_assignment
            
            return render(request, "utils/dummy.html", {"result": str(get_node_assignment(obj, dt=dt, func=func, chainId=chainId, sender_transaction=sender_transaction, full_validator_list=full_validator_list))})
        return render(request, "utils/dummy.html", {"result": str(obj)})
    
def get_model_fields_view(request):
    get_model_fields()

    prnt()
    prnt()
    prnt()
    prnt()
    if request.user and request.user.assess_super_status():
        # from utils.models import get_model_fields
        get_model_fields()
        return render(request, "utils/dummy.html", {"result": 'done'})


def supersign_view(request, iden):
    if request.user.assess_super_status():
        try:
            # from .models import get_operatorData, get_self_node
            from accounts.models import SuperSign
            from accounts.forms import SuperSignForm
            operatorData = get_operatorData()
            if operatorData['userData']['id'] == request.user.id:
                if request.method == 'POST':
                    form = SuperSignForm(request.POST)
                    if form.is_valid(): 
                        # prnt(form)
                        form.Super_User_obj = request.user
                        form.save()
                        from utils.locked import sign_obj, share_with_network
                        form = sign_obj(form)
                        # from utils.models import 
                        share_with_network(form)
                        return JsonResponse({'message': 'Form submitted successfully'})
                    else:
                        return JsonResponse({'errors': form.errors}, status=400)
                else:
                    obj = None
                    if iden:
                        obj = get_dynamic_model(iden, id=iden)
                    prnt('iden:',iden)
                    if obj:
                        ss = SuperSign.objects.filter(pointerId=obj.id).first()
                        if ss:
                            superForm = SuperSignForm(instance=ss)
                        else:
                            superForm = SuperSignForm(pointerId=obj.id)
                    else:
                        superForm = SuperSignForm()
                    # from blockchain.models import 
                    try:
                        operator = get_self_node().User_obj.display_name
                    except:
                        operator = 'None'
                    context = {
                    'nodeOperator': operator,
                    'superForm': superForm,
                }
                return render(request, "forms/superform.html", context)
        except Exception as e:
            return JsonResponse({'message' : 'invalid', 'err':str(e)})

def remove_target_test_data_confirm_view(request, region, model):
    if request.user.assess_super_status():
        if testing() or debugging():
            try:
                if region.lower() == 'all':
                    if '_' in model:
                        if model == 'Block_unvalidated':
                            from blockchain.models import Block
                            objs = Block.objects.exclude(validated=True)
                    return render(request, "utils/super.html", {'confirm':True, 'region':region, 'model':model, 'count':len(objs)})
                else:
                    country_obj = Region.valid_objects.filter(Name__iexact=region, modelType='country').first()
                    if '_' in model:
                        if model == 'Block_unvalidated':
                            from blockchain.models import Block
                            objs = Block.objects.filter(Blockchain_obj__genesisId=country_obj.id).exclude(validated=True)
                    else:
                        objs = get_dynamic_model(model, list=True, Region_obj=country_obj)
                    return render(request, "utils/super.html", {'confirm':True, 'region':region, 'model':model, 'count':len(objs)})
            except Exception as e:
                return JsonResponse({'message' : f'error:{str(e)}'})
    
def remove_target_test_data_view(request, region, model):
    if request.user.assess_super_status():
        if testing() or debugging():
            prnt('get model:', model, region)
            try:
                if region.lower() == 'all':
                    if '_' in model:
                        if model == 'Block_unvalidated':
                            from blockchain.models import Block, Validator
                            objs = Block.objects.exclude(validated=True)
                            for obj in objs:
                                prnt(obj)
                                for v in Validator.objects.filter(data__has_key=obj.id):
                                    prnt('v',v)
                                    v.delete(superDel=True)
                                obj.delete(superDel=True)
                    # return render(request, "utils/super.html", {'confirm':True, 'region':region, 'model':model, 'count':len(objs)})
                else:
                    country_obj = Region.valid_objects.filter(Name__iexact=region, modelType='country').first()
                    if '_' in model:
                        if model == 'Block_unvalidated':
                            from blockchain.models import Block, Validator
                            objs = Block.objects.filter(Blockchain_obj__genesisId=country_obj.id).exclude(validated=True)
                            for obj in objs:
                                prnt(obj)
                                for v in Validator.objects.filter(data__has_key=obj.id):
                                    prnt('v',v)
                                    v.delete()
                                obj.delete()
                    else:
                        objs = get_dynamic_model(model, list=True, Region_obj=country_obj)
                    # return render(request, "utils/super.html", {'confirm':True, 'region':region, 'model':model, 'count':len(objs)})
                        for obj in objs:
                            prnt(obj)
                            obj.delete()
                return JsonResponse({'message' : 'complete'})
            except Exception as e:
                return JsonResponse({'message' : f'error:{str(e)}'})

def clear_test_data_view(request):
    if request.user.assess_super_status():
        if testing() or debugging():
            models = [
            'Region',
            # 'Role',
            'Update',
            'District',
            'Person',
            'Party',
            'Government',
            'Vote',
            'Motion',
            'Committee',
            'Statement',
            'Meeting',
            'Bill',
            'BillText',
            'Agenda',
            # 'AgendaItem',
            # 'AgendaTime',
            'GenericModel',
            'Post',
            'Keyphrase',
            'KeyphraseTrend',
            'Election',
            'Notification',
            'UserNotification',
            # 'Blockchain',
            # 'Validator',
            # 'Wallet',
            # 'UserTransaction',
            'Node'
            ]
            for model in models:
                prnt()
                prnt('get model:', model)
                objs = get_dynamic_model(model, list=True)
                for obj in objs:
                    prnt(obj)
                    # from utils.models import get_model
                    super(get_model(obj.object_type), obj).delete()

            return JsonResponse({'message' : 'complete'})
        return JsonResponse({'message' : 'is production'})


def clear_all_app_cache_view(request):
    if request.user.is_superuser:
        prnt('run notify')
        from firebase_admin.messaging import Notification as fireNotification
        from firebase_admin.messaging import Message as fireMessage
        from fcm_django.models import FCMDevice
        from legis.models import Bill
        bill = Bill.objects.all().order_by('-LatestBillEventDateTime')[0]
        link = bill.get_absolute_url().replace('file://', '')
        # if link[0] == '/':
        #     link = 'https://sovote.ca' + link
        FCMDevice.objects.send_message(fireMessage(data={"clearCache":"True"}))
        # from accounts.models import User
        # for u in User.objects.all():
        #     # prnt(u)
        #     fcm_devices = FCMDevice.objects.filter(user=u)

        #     for device in fcm_devices:
        #         try:
        #             # prnt(device)
        #             device.send_message(fireMessage(notification=fireNotification(title='test1', body='body1'), data={"click_action" : "FLUTTER_NOTIFICATION_CLICK","link" : link}))
        #             # prnt('away')
        #         except Exception as e:
        #             prnt(str(e))
        return render(request, "utils/dummy.html", {"result": 'Success'})

def tester_queue(obj=None):
    prnt('---tester_queue')
    # import multiprocessing
    # multiprocessing.set_start_method("forkserver", force=True)


    from blockchain.models import Blockchain, Block,DataPacket,Tidy,EventLog
    # from utils.locked import Wallet, UserPubKey,verify_obj_to_data, hash_obj_id
    from legis.models import Government, Vote, Bill, Statement, Motion
    # from posts.models import get_data, si
    # from utils.models import chunk_dict, open_browser, close_browser
    from scrapers.usa.federal import add_bill
    import uuid
    # operatorData = get_operatorData()
    self_node = get_self_node()

    url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr2317.xml'
    add_bill(url=url, log=[], update_dt=now_utc(), driver=None, driver_service=None, special=None, country=None, ref_func=None)


    # chain = Blockchain.objects.filter(id='chaSo2c3f4f61e713ba2facff6b9484e70b0c').first()

    # from datetime import datetime, timezone
    # time_string = "01:50:04, May 22, 2025"
    # dt = datetime.strptime(time_string, "%H:%M:%S, %B %d, %Y")
    # dt = dt.replace(tzinfo=timezone.utc)

    # dummy_block = chain.create_dummy_block(now=dt) # dummy block needed to assign creator
    # # if self.genesisType == 'Nodes':
    # #     dummy_block.data = self.get_new_node_block_data(dt=dt)
    # #     dummy_block.number_of_peers = number_of_peers
    # # if not Block.objects.filter(id=dummy_block.id).first():
    # creator_nodes = get_node_assignment(dummy_block, creator_only=True, strings_only=True)
    # prnt('creator_nodes',creator_nodes)
    # prnt('chains222',chains)
    # for c in chains:
    # block_assigned = c.new_block_candidate(self_node=self_node, dt=dt)
    # prntDebug('block_assigned123',block_assigned)


    # vid = 'votSo67bbc989f33059bde7b17d12a3ae2dba'
    # v = Vote.objects.filter(id=vid).first()
    # prnt('v',v)
    # cdata = get_commit_data(v)
    # prnt('cdata',cdata)
    # check = check_commit_data(v,cdata)
    # prnt('check',check)

    # 01:50:04 main: blockchain.models.tasker(datetime.datetime(2025, 5, 22, 1, 50, 4, 860327, tzinfo=<UTC>)) (f0880c3b-2f3b-4dd5-8d22-0a61aaa9b13e)
    # ~:--tasker,09:50:04 PM,est
    # ~:dt_utc,2025-05-22 01:50:04.860327+00:00
    # ~:nodeChain,chain:Nodes_Nodes
    # ~:delay,10
    # ~:nodeChain2,chain:Nodes_Nodes
    # ~:updated_nodes,2
    # ~:-new_block_candidate
    # ~:dummy_block:,BLOCK:1 Nodes-bloSo28c22c8dc2281eda870260ae51cb9ab4
    # ~:-get_new_node_block_data
    # ~:resultdata:,{'All': ['nodSo741d333ed251b5b272ed4b86767b6206', 'nodSo44361466c4c21a74831b27204e3d5897'], 'regSof2648c6e31207b99b56d1512d262d525': {'servers': ['nodSo741d333ed251b5b272ed4b86767b6206', 'nodSo44361466c4c21a74831b27204e3d5897'], 'scripts': ['nodSo741d333ed251b5b272ed4b86767b6206', 'nodSo44361466c4c21a74831b27204e3d5897']}}
    # ~:
    # ------get_node_assignment obj:,BLOCK:1 Nodes-bloSo28c22c8dc2281eda870260ae51cb9ab4,func,None,strings:,True,chainId,None,creator_only,True,scrapers_only,False,node_block_data,{},sender_transaction,False
    # ~:--get nodes from node block list - strings_only:,True,genesisId,Nodes,blockchain,None,chains,None,obj,BLOCK:1 Nodes-bloSo28c22c8dc2281eda870260ae51cb9ab4,dt,2025-05-22 00:20:00+00:00,exclude_list,[]
    # ~:node_ids,['nodSo741d333ed251b5b272ed4b86767b6206', 'nodSo44361466c4c21a74831b27204e3d5897'],peers_count,2,relevant_nodes,{'nodSo741d333ed251b5b272ed4b86767b6206': '104.254.90.114:54312', 'nodSo44361466c4c21a74831b27204e3d5897': '173.249.217.51:18141'}
    # ~:--starting_position11,0,dt::,None,date_int:,195,len(node_ids),2,available_creators,1
    # ~:creator_nodes,['nodSo44361466c4c21a74831b27204e3d5897'],self_node.id,NODE: Courtney-nodSo741d333ed251b5b272ed4b86767b6206
    # ~:deleting block,BLOCK:1 Nodes-bloSo28c22c8dc2281eda870260ae51cb9ab4
    # ~:block_assigned,False
    # ~:mandaroryChain,User,mChains,<QuerySet []>
    # ~:mandaroryChain,Sonet,mChains,<QuerySet []>
    # ~:mandaroryChain,Wallet,mChains,<QuerySet []>
    # ~:mandaroryChain,regSo039946b3da35ef6ed083a088eb015600,mChains,<QuerySet []>
    # ~:chains222,<QuerySet [<Blockchain: chain:Region_USA>]>
    # ~:-new_block_candidate
    # ~:dummy_block:,BLOCK:1 Region-bloSo775afd02c9292c7e84a835e9bf62b6ef
    # ~:
    # ------get_node_assignment obj:,BLOCK:1 Region-bloSo775afd02c9292c7e84a835e9bf62b6ef,func,None,strings:,True,chainId,None,creator_only,True,scrapers_only,False,node_block_data,{},sender_transaction,False
    # ~:--get nodes from node block list - strings_only:,True,genesisId,regSof2648c6e31207b99b56d1512d262d525,blockchain,None,chains,None,obj,BLOCK:1 Region-bloSo775afd02c9292c7e84a835e9bf62b6ef,dt,2025-05-22 00:10:00+00:00,exclude_list,[]
    # ~:node_ids,['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'],peers_count,2,relevant_nodes,{'nodSo44361466c4c21a74831b27204e3d5897': '173.249.217.51:18141', 'nodSo741d333ed251b5b272ed4b86767b6206': '104.254.90.114:54312'}
    # ~:--starting_position11,1,dt::,None,date_int:,195,len(node_ids),2,available_creators,1
    # ~:creator_nodes,['nodSo44361466c4c21a74831b27204e3d5897'],self_node.id,NODE: Courtney-nodSo741d333ed251b5b272ed4b86767b6206
    # ~:deleting block,BLOCK:1 Region-bloSo775afd02c9292c7e84a835e9bf62b6ef
    # ~:#block_assigned123,False

    # buu
    # 01:50:03 main: blockchain.models.tasker(datetime.datetime(2025, 5, 22, 1, 50, 3, 68115, tzinfo=<UTC>)) (fa6eb7fc-1f0a-47bf-92c8-5a6f8918d7c9)
    # ~:--tasker,09:50:03 PM,est
    # ~:dt_utc,2025-05-22 01:50:03.068115+00:00
    # ~:log,DATAPACKET:datSocb1acd23bca0628d355d42a0af5c6108 chain:

    # ~:#exists_in_worker,process_posts_for_validating,datSocb1acd23bca0628d355d42a0af5c6108,<DjangoRQ low>,False
    # ~:#job_id,fa6eb7fc-1f0a-47bf-92c8-5a6f8918d7c9
    # ~:#job,<Job fa6eb7fc-1f0a-47bf-92c8-5a6f8918d7c9: blockchain.models.tasker(datetime.datetime(2025, 5, 22, 1, 50, 3, 68115, tzinfo=<UTC>))>
    # ~:#job.func_name,blockchain.models.tasker
    # ~:#running2
    # ~:exists in worker fail3633,'Redis' object has no attribute 'job_class'
    # ~:#cont6
    # ~:#cont7
    # ~:#cont8 false
    # ~:Continuing Run:,process_posts_for_validating
    # ~:log,DATAPACKET:datSo7a17bb3f3280377f85bc197d9242622d chain:

    # ~:#exists_in_worker,process_posts_for_validating,datSo7a17bb3f3280377f85bc197d9242622d,<DjangoRQ low>,False
    # ~:#job_id,fa6eb7fc-1f0a-47bf-92c8-5a6f8918d7c9
    # ~:#job,<Job fa6eb7fc-1f0a-47bf-92c8-5a6f8918d7c9: blockchain.models.tasker(datetime.datetime(2025, 5, 22, 1, 50, 3, 68115, tzinfo=<UTC>))>
    # ~:#job.func_name,blockchain.models.tasker
    # ~:#running2
    # ~:exists in worker fail3633,'Redis' object has no attribute 'job_class'
    # ~:#cont6
    # ~:#cont7
    # ~:#cont8 false
    # ~:Continuing Run:,process_posts_for_validating
    # ~:nodeChain,chain:Nodes_Nodes
    # ~:delay,10
    # ~:nodeChain2,chain:Nodes_Nodes
    # ~:updated_nodes,1
    # ~:-new_block_candidate
    # ~:dummy_block:,BLOCK:1 Nodes-bloSofb13695e05af6e6d8e13bd38459775dc
    # ~:-get_new_node_block_data
    # ~:resultdata:,{'All': ['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'], 'regSof2648c6e31207b99b56d1512d262d525': {'servers': ['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'], 'scripts': ['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206']}}
    # ~:
    # ------get_node_assignment obj:,BLOCK:1 Nodes-bloSofb13695e05af6e6d8e13bd38459775dc,func,None,strings:,True,chainId,None,creator_only,True,scrapers_only,False,node_block_data,{},sender_transaction,False
    # ~:--get nodes from node block list - strings_only:,True,genesisId,Nodes,blockchain,None,chains,None,obj,BLOCK:1 Nodes-bloSofb13695e05af6e6d8e13bd38459775dc,dt,2025-05-22 02:00:00+00:00,exclude_list,[]
    # ~:node_ids,['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'],peers_count,2,relevant_nodes,{'nodSo44361466c4c21a74831b27204e3d5897': '173.249.217.51:18141', 'nodSo741d333ed251b5b272ed4b86767b6206': '104.254.90.114:54312'}
    # ~:--starting_position11,0,dt::,None,date_int:,197,len(node_ids),2,available_creators,1
    # ~:creator_nodes,['nodSo741d333ed251b5b272ed4b86767b6206'],self_node.id,NODE: MajinBuu-nodSo44361466c4c21a74831b27204e3d5897
    # ~:deleting block,BLOCK:1 Nodes-bloSofb13695e05af6e6d8e13bd38459775dc
    # ~:block_assigned,False
    # ~:mandaroryChain,User,mChains,<QuerySet []>
    # ~:mandaroryChain,Sonet,mChains,<QuerySet []>
    # ~:mandaroryChain,Wallet,mChains,<QuerySet []>
    # ~:mandaroryChain,regSo039946b3da35ef6ed083a088eb015600,mChains,<QuerySet []>
    # ~:chains222,<QuerySet [<Blockchain: chain:Region_USA>]>
    # ~:-new_block_candidate
    # ~:dummy_block:,BLOCK:1 Region-bloSo44cba9eb7edc7e31ca467efede1b284e
    # ~:
    # ------get_node_assignment obj:,BLOCK:1 Region-bloSo44cba9eb7edc7e31ca467efede1b284e,func,None,strings:,True,chainId,None,creator_only,True,scrapers_only,False,node_block_data,{},sender_transaction,False
    # ~:--get nodes from node block list - strings_only:,True,genesisId,regSof2648c6e31207b99b56d1512d262d525,blockchain,None,chains,None,obj,BLOCK:1 Region-bloSo44cba9eb7edc7e31ca467efede1b284e,dt,2025-05-22 01:50:00+00:00,exclude_list,[]
    # ~:node_ids,['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'],peers_count,2,relevant_nodes,{'nodSo44361466c4c21a74831b27204e3d5897': '173.249.217.51:18141', 'nodSo741d333ed251b5b272ed4b86767b6206': '104.254.90.114:54312'}
    # ~:--starting_position11,0,dt::,None,date_int:,197,len(node_ids),2,available_creators,1
    # ~:creator_nodes,['nodSo741d333ed251b5b272ed4b86767b6206'],self_node.id,NODE: MajinBuu-nodSo44361466c4c21a74831b27204e3d5897
    # ~:deleting block,BLOCK:1 Region-bloSo44cba9eb7edc7e31ca467efede1b284e
    # ~:#block_assigned123,False



    block_results = {}
    # chain = Blockchain.objects.filter(genesisId='regSof2648c6e31207b99b56d1512d262d525').first()
    # prnt('chains222',chains)
    # for c in chains:
    def run_block(dt):
        dummy_block = chain.create_dummy_block(now=dt) # dummy block needed to assign creator
        # if self.genesisType == 'Nodes':
        #     dummy_block.data = self.get_new_node_block_data()
        #     dummy_block.number_of_peers = number_of_peers
        # if not Block.objects.filter(id=dummy_block.id).first():
        creator_nodes = str(get_node_assignment(dummy_block, creator_only=True, strings_only=True))
        if creator_nodes in block_results:
            block_results[creator_nodes] += 1
        else:
            block_results[creator_nodes] = 1
        # if not self_node:
        #     self_node = get_self_node()
        # prnt('creator_nodes',creator_nodes, 'self_node.id',self_node)
        # if creator_nodes[0] == self_node.id:
        #     logEvent(f'new_block_candidate {self.genesisName} creator_nodes:{creator_nodes}, self_node.id:{self_node}', log_type='Tasks')
        #     prnt('do commit')
        #     if add_to_queue and not testing():
        #         queue = django_rq.get_queue('main')
        #         queue.enqueue(self.commit_to_chain, dummy_block=dummy_block, job_timeout=600, result_ttl=3600)
        #     else:
        #         self.commit_to_chain(dummy_block=dummy_block)
        #     return True
        # else:
        dummy_block.delete()

    def custom_scrape_duty(receivedDt, func=None):
        import pytz

        importScript = f'scrapers.usa.federal'

        import importlib
        scraperScripts = importlib.import_module(importScript) 

        to_zone = pytz.timezone('est')
        local_dt = receivedDt.astimezone(to_zone)
        today = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        dayOfWeek = today.weekday()
        prnt('receivedDt converted to region',local_dt)
        runTimes = scraperScripts.runTimes
        function_set = scraperScripts.functions
        approved_models = scraperScripts.approved_models
        function_list = []
        
        for function_dt, functions in dict(sorted(function_set.items(), key=lambda x: datetime.datetime.strptime(x[0], "%Y-%m-%d"), reverse=True)).items():
            if datetime.datetime.strptime(function_dt, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc) <= receivedDt:
                for function in functions:
                    # runtime_window = [local_dt.hour, local_dt.hour+1] # scrapers allotted two hour window, utc - to region_time conversion may cause offset by 1 hour - this may happen if running only on even hours
                    runtime_window = [local_dt.hour]
                    # prntDebug('runtime_window',runtime_window)
                    # prntDebug("function['hour']",function['hour'])
                    if 'x' in function['hour'] or any(i in function['hour'] for i in runtime_window):
                        if 'x' in function['dayOfWeek'] or dayOfWeek in function['dayOfWeek']:
                            if 'x' in function['date'] or today in function['date']:
                                for f in function['cmds']:
                                    if not func or func == f:
                                        function_list.append({'region_id':'usa','function_name':f, 'function':getattr(scraperScripts, f), 'timeout':runTimes[f]})
                break

        # prnt('function_list',function_list)
        # from blockchain.models import get_scraping_order
        node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2'}, 'node_ids':['nSo1000','nSo2000']}
        master_list = []
        for f in function_list:
            # scrapers, validator = get_scraping_order(chainId='1234567890', func_name=f['function_name'], dt=receivedDt)
            scrapers, validator = get_node_assignment(None, dt=receivedDt, func=f['function_name'], chainId='1234567890', scrapers_only=True, node_block_data=node_block_data, strings_only=True)
            f['scraping_order'] = scrapers
            f['validator'] = validator
            master_list.append(f)
        # prnt('master_list',master_list)
        return master_list, approved_models


    # number_of_peers = node_dict['number_of_peers']
    # relevant_nodes = node_dict['relevant_nodes']
    # node_ids = node_dict['node_ids']


    # get_node_assignment(None, dt=dt, func=func_name, chainId=chainId, scrapers_only=True, node_block_data=node_block_data, strings_only=strings_only)

    results = {}

    # gov = Government.objects.all().first()
    def run_me(receivedDt):
        scraper_list, approved_models = custom_scrape_duty(receivedDt)
        # prntn('!!!',receivedDt, 'scraper_list',scraper_list)
        for s in scraper_list:
            # prntDebug('s',s)
            r = str({'scrape':s['scraping_order'], 'val':s['validator']})
            if r in results:
                results[r] += 1
            else:
                results[r] = 1
        # 'scraping_order': ['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'], 'validator': 'nodSo741d333ed251b5b272ed4b86767b6206'}

        prnt('-----------------------')
        prnt()

    from datetime import datetime, timedelta

    # Start time (you can customize this)
    current_time = now_utc()

    # Number of hours to iterate (change as needed)
    hours_to_iterate = 1000

    # # Loop through each hour
    for i in range(hours_to_iterate):
        # print(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        current_time += timedelta(hours=1)
        run_me(current_time)
        # run_block(current_time)



    prnt()
    prnt()
    prnt()
    prnt('results')
    for key, value in results.items():
        prnt(value, key)
    
    prnt()
    prnt()
    prnt()
    prnt('block_results')
    for key, value in block_results.items():
        prnt(value, key)
    # try:
    #     from nltk.corpus import stopwords
    #     import nltk
    #     # print('3')
    #     nltk.download("stopwords") # only needs to run the first time
    #     nltk_stopwords = set(stopwords.words("english"))
    #     # custom_stopwords = {"example", "discussion", "important"}
    # except Exception as e:
    #     prnt('fail keyowrkds nltk',str(e))
    #     nltk_stopwords = set()



    # driver, driver_service = open_browser(url='https://www.google.com', headless=True, chrome_testing=False)
    # prnt(driver.title)
    # close_browser(driver, driver_service)
    # r = Region.objects.filter(id='regSof2648c6e31207b99b56d1512d262d525').first()
    # prnt('r',r)
    # from datetime import datetime, timezone

    # dt_str = "2025-05-14 19:38:43 UTC".replace(" UTC", "")
    # dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    # prnt('dt_obj',dt_obj)

    # r.created = dt_obj
    # obj = sign_obj(r)

    # # if not blockchain:
    # chainId = 'All'
    # if has_field(obj, 'blockchainType'):
    #     blockchain, obj, receiverChain = find_or_create_chain_from_object(obj)
    #     if blockchain:
    #         chainId = blockchain.id

    # # if not dataPacket:
    # prnt('get datapacket')
    # dataPacket = get_latest_dataPacket(chainId)
    # prnt('dataPacket',dataPacket)
    # dataPacket.add_item_to_share(obj)


    # for dp in DataPacket.objects.filter(id='datSo8b70e3d83e24468d996252718828b04f'):
    #     prnt('dphererere',dp.id)
    #     dp.broadcast()
    #     prnt('process_received_data',process_received_data(dp, override_completed=True))
    # result = {}
    # blocks = Block.objects.filter(validated=True, id='bloSo1ec6dfcdd366522e60754c01bd81bfb5').order_by('blockchainId','index')
    # for block in blocks:
    #     prnt('block',block, block.index)
    #     dynamic_bulk_update('Validator', update_data={'Block_obj':block}, id__in=[v for v in block.validators])

    #     obj_idens, problem_idens = block.check_contents(retrieve_missing=False, log_missing=False, downstream_worker=False, return_missing=True, input_data=[])
    #     # is_valid, validator, is_new_validation = validate_block(block, create_validator=False)
    #     # is_valid, consensus_found, validators = check_validation_consensus(block, do_mark_valid=False, broadcast_if_unknown=False, downstream_worker=False, handle_discrepancies=False, backcheck=False, get_missing_blocks=False)
    #     # result[block] = {'index':block.index,'is_valid':is_valid,'consensus_found':consensus_found}
    #     prntn('index',block.index,'obj_idens',len(obj_idens),'problem_idens',problem_idens)
    #     result[block] = {'index':block.index,'obj_idens':len(obj_idens),'problem_idens':problem_idens}
    #     prntn()


    # prnt()
    # total = 0
    # valid = 0
    # invalid = {}
    # for key, value in result.items():
    #     prnt(key)
    #     prnt(value)
    #     prnt()
    #     total += 1
    #     if value['problem_idens']:
    #         invalid[key] = value
    #         # invalid[value['index']] = value['problem_idens']
    #         # invalid.append(value['index'])
    #     else:
    #         valid += 1
    # prntn()
    # prnt('invalids1',invalid)
    # prntn('invalids2')
    # passed = []
    # failed = []
    # not_found = []
    # skipped = []
    # for block, value in invalid.items():
    #     prnt(block)
    #     prnt(value)
    #     for iden in value['problem_idens']:
    #         if not is_id(iden):
    #             prnt('skipped')
    #             skipped.append(iden)
    #         elif iden in block.data:
    #             x = get_dynamic_model(get_model(iden), id=iden)
    #             prnt('obj',x)
    #             if not x:
    #                 not_found.append(iden)
    #             elif check_commit_data(x, block.data[x.id]):
    #                 prnt('passed')
    #                 passed.append(iden)
    #             else:
    #                 prnt('failed')
    #                 failed.append(iden)
    #     prnt()
    # prnt('skipped',skipped)
    # prnt('not_found',not_found)
    # prnt('passed',passed)
    # prnt('failed',failed)
    # prnt('valid',valid)
    # prnt('total',total)
    # b = Block.objects.filter(blockchainType=NodeChain_genesisId, validated=True).order_by('-index').first()
    # prnt('b',b)
    # if b:
    #     b.adjust_settings()
    # chain = Blockchain.objects.filter(id='chaSo2c3f4f61e713ba2facff6b9484e70b0c').first()
    # r = chain.commit_to_chain(testing=True)
    # prnt('result',r)

    def run_me2(block):
        prntn('block',block)
        problem_idens = []
        obj_idens = []
        requested_idens = []
        requested_validators = []
        data = block.data
        for chunk in chunk_dict(data, 300):
            prnt('chunk')
            storedModels, not_found, not_valid, delLogs = get_data(chunk, return_model=True, include_related=False, include_deletions=True)
            prnt('storedModels',len(storedModels),'not_found',len(not_found),'not_valid',len(not_valid),'delLogs',delLogs)
            for x in storedModels:
                if not has_field(x, 'Validator_obj') or x.Validator_obj and x.Validator_obj.is_valid and x.id in x.Validator_obj.data and x.Validator_obj.data[x.id] == sigData_to_hash(x):
                    if x.id in block.data:
                        if check_commit_data(x, block.data[x.id]):
                            obj_idens.append(x.id)
                        else:
                            requested_idens.append(x.id)
                else:
                    requested_validators.append(x.id)

            storedModels.clear()
            if not_valid:
                problem_idens = requested_idens + [i.id for i in not_valid]
            if not_found:
                problem_idens = requested_idens + not_found
            not_found.clear()
            not_valid.clear()

            

        # problem_idens = []
        for key in block.data:
            if key not in obj_idens and key not in problem_idens:
                problem_idens.append(key)
        prnt('problem_idens',problem_idens)
        if problem_idens:
            self_node = get_self_node()
            now = now_utc()
            start_of_month = round_time(dt=now, dir='down', amount='month')
            from posts.models import Region
            reg = Region.objects.filter(id=block.Blockchain_obj.genesisId).first()

            log = EventLog.objects.filter(type='missing_items', Node_obj=self_node, Region_obj=reg, created__gte=start_of_month).first()
            if not log:
                log = EventLog(type='missing_items', Node_obj=self_node, Region_obj=reg, created=start_of_month)
            for iden in problem_idens:
                if iden not in log.data:
                    log.data[iden] = {'block':block.id}
            log.save()

    # x = ['bilSo023d34e17a9db778b55c1af395c68d14']
    # block = Block.objects.filter(id='bloSo501c14b159d6db80b8394a401e82939b').first()
    # idens, missing = block.check_contents(retrieve_missing=False, log_missing=False, downstream_worker=False, return_missing=True, input_data=x)
    # prntn('ridens',idens)
    # prnt('missing',missing)
    # posts = Post.objects.filter(pointerType='Person', validated=True)
    # prnt('plen',len(posts))
    # updates = Update.objects.filter(pointerId__in=[p.pointerId for p in posts], validated=True)
    # prnt('ulen',len(updates))
    # u_map = {u.pointerId: u for u in updates}
    # for p in posts:
    #     prnt('p',p)
    #     u = u_map.get(p.pointerId)
    #     if u:
    #         p.Update_obj = None
    #         update_post(p=p, save_p=True, update=u)
        # p.Update_obj = u_map.get(p.pointerId)
        # p.save()



    # fails = {}
    # chain = Blockchain.objects.filter(id='chaSo2c3f4f61e713ba2facff6b9484e70b0c').first()
    # blocks = Block.objects.filter(Blockchain_obj=chain, index__gte=1, index__lte=12, validated=True).order_by('index')
    # for block in blocks:
    #     prnt('-----')
    #     good_idens, bad_idens = block.check_contents(retrieve_missing=False, log_missing=False, downstream_worker=False, return_missing=True)
    #     prntn(f'block>{block},index:{block.index}')
    #     prnt(f'good>{good_idens}')
    #     prnt(f'bad_idens>{bad_idens}')
    #     if bad_idens:
    #         fails[block.index] = bad_idens
    #         block.is_not_valid(mark_strike=False, note='super-undone', check_posts=True, super_delete_content=False)
    #         break

    # prnt()
    # prntn('fails:')
    # for f in fails:
    #     prnt(f,f'len:{len(fails[f])}',fails[f])

    # prnt()
    # mid = 'motSo18da664af542ebb69ec8d1cefed6aa53'
    # m = Motion.objects.filter(id=mid).first()
    # m_valid = verify_obj_to_data(m, m)
    # prnt('m_valid',m_valid)
    # post = Post.objects.filter(pointerId=mid).first()
    # p_valid = post.verify_is_valid(check_update=False)
    # prnt('p_valid',p_valid)
    # # c_valid = check_commit_data(m, m.Validator_obj.data[m.id])
    # s = sigData_to_hash(m)
    # v_d = m.Validator_obj.data[m.id]
    # prnt('s',s)
    # prnt('v_d',v_d)

    # vals = Validator.objects.filter(data__has_key=mid)
    # prnt('vals',vals)


#     ver = '131.0.6778.85'

#     cmds = [
#         # # linux
#         # ["mkdir", homepath + "/chrome-for-testing"],
#         ['wget', '-O', '/tmp/chrome.deb', 'https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_131.0.6778.85-1_amd64.deb'],
#         ['sudo', '-S', 'apt', 'install', '-y', '/tmp/chrome.deb'],
#         ['rm', '/tmp/chrome.deb'],
#         # ['wget', '-O', '/tmp/chromedriver_mac64.zip', 'https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chromedriver-linux64.zip'],

#         # ["sudo", "-S", "apt", "install", "zip"],
#         # ["unzip", "/tmp/chromedriver_mac64.zip"],
#         # ["sudo", "-S", "mv", "/tmp/chromedriver_mac64/chromedriver", "/usr/bin/"],
#         # ["sudo", "-S", "chown", "root:root", "/usr/bin/chromedriver"],
#         # ["sudo", "-S", "chmod", "+x", "/usr/bin/chromedriver"],
#     ]
#         # driver_link = f'https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/mac-arm64/chromedriver-mac-arm64.zip'

#     # r = requests.get('https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE')
#     # if r.status_code == 200:
#     #     stable_ver = r.content.decode('utf-8')
# VERSION="114.0.5735.90"
# curl -LO "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/131.0.6778.85/mac-arm64/chrome-mac.zip"


# curl -s https://omahaproxy.appspot.com/all.json | jq

# https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json

# unzip chrome-mac.zip
# open chrome-mac/Chromium.app

# unzip chrome-mac.zip

# mv chrome-mac/Chromium.app /Applications/Chrome114.app


# curl -O https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg


#     import subprocess
#     for cmd in cmds:
#         prnt(cmd)
#         result = subprocess.run(cmd, capture_output=True)
#         if result.returncode == 0:
#             content = f"chrome downloaded successfully:\n{result.stdout}"
#             prnt(content)
#             # Clock.schedule_once(lambda dt, line=content: update_output(line, output))
#         else:
#             content = f"Error downloading chrome:\n{result.stderr}"
#             prnt(content)
#             # Clock.schedule_once(lambda dt, line=content: update_output(line, output))
#             raise content
        
#         # Clock.schedule_once(lambda dt, line=driver_link: update_output(line, output))
#         # Clock.schedule_once(lambda dt, line='Downloading chromedriver...': update_output(line, output))
#         # result = subprocess.run(['wget', '-O', '/tmp/chromedriver_mac64.zip', driver_link], capture_output=True)
#         # if result.returncode == 0:
#         #     content = f"chromedriver downloaded successfully:\n{result.stdout}"
#         #     Clock.schedule_once(lambda dt, line=content: update_output(line, output))
#         # else:
#         #     content = f"Error downloading chromedriver:\n{result.stderr}"
#         #     Clock.schedule_once(lambda dt, line=content: update_output(line, output))
#             raise content
        
        # sudo rm -rf "/Users/sozed/Library/Application Support/Google/Chrome for Testing/Crashpad/pending"
        # sudo mkdir -p "/Users/sozed/Library/Application Support/Google/Chrome for Testing/Crashpad/pending"

        # defaults write com.google.Chrome BreakpadEnable -bool false
        # result = subprocess.run(['defaults', 'write', 'com.google.Chrome', 'BreakpadEnable', '-bool', 'false'], capture_output=True)
        # if result.returncode == 0:
        #     content = f"crash report adjusted successfully:\n{result.stdout}"
        #     Clock.schedule_once(lambda dt, line=content: update_output(line, output))
        # else:
        #     content = f"Error adjusting chrash report:\n{result.stderr}"
        #     Clock.schedule_once(lambda dt, line=content: update_output(line, output))
        #     raise content


    # gov = Government.objects.all().first()
    # prnt('giv',gov)
    # x = 'datSof1d034f264a74909a29ed2b55fbe00e6'
    # items, completed = super_share(log=x, gov=gov, val_type='get_house_persons')
    # prnt('completed',completed)

    # for block in Block.objects.filter(validated=True).order_by('DateTime'):
    #     run_me(block)


    # mid = 'motSo01f1fb7dddf1c3514f9e0f6af0642d96'

    # x = Motion.objects.filter(id=mid).first()
    # prnt('x',x)
    # if x:
    #     prnt('v1',verify_obj_to_data(x, x))
    #     prnt('v2',verify_obj_to_data(x, convert_to_dict(x)))
    #     block = x.Block_obj
    #     prnt('block',block)
    #     if not has_field(x, 'Validator_obj') or x.Validator_obj:
    #         prnt('2')
    #         if x.Validator_obj.is_valid:
    #             prnt('3')
    #             if x.id in x.Validator_obj.data:
    #                 prnt('4')
    #                 if x.Validator_obj.data[x.id] == sigData_to_hash(x):
    #                     prnt('5')
    #                     if x.id in block.data:
    #                         prnt('6')
    #                         if check_commit_data(x, block.data[x.id]):
    #                             prnt('7')

    # Tidy().unvalidator_run()
    # blocks = Block.objects.filter(blockchainId='chaSof309568d9883de18101f0a078f8ac13c', validated=True).order_by('-DateTime')
    # for b in blocks:
    #     b.is_not_valid(super_delete_content=True)

    # blocks = Block.objects.filter(blockchainId='chaSof309568d9883de18101f0a078f8ac13c').order_by('-DateTime')
    # for b in blocks:
    #     super(Block, b).delete()
    # prnt('block',block)
    # validate_block(block, creator_nodes=None, node_block_data={})


    # checked_items = {}
    # requested_idens = []
    # requested_validators = []
    # mismatch = False
    # not_valid = []
    # not_found = []

    # data = block.data
    # for chunk in chunk_dict(data, 500):
    #     prntn('chunk...')
    #     if mismatch:
    #         break
    #     else:
    #         storedModels, not_found, not_valid = get_data(chunk, return_model=True, include_related=False)
    #         prntn(f'storedModels:{len(storedModels)}')
    #         prnt('not_valid',len(not_valid))
    #         prnt('not_found',not_found)
    #         if not_found or not_valid:
    #             fail_reason = 111
    #             prnt('x1')

    #             if not_valid:
    #                 requested_idens = [i.id for i in not_valid]
    #             if not_found:
    #                 requested_idens = requested_idens + not_found
    #             fail_reason = 112
    #         prnt('next1')
    #         if block.blockchainType != NodeChain_genesisId:
    #             for i in storedModels:
    #                 if not has_field(i, 'Validator_obj') or i.Validator_obj and i.Validator_obj.is_valid and i.Validator_obj.data[i.id] == sigData_to_hash(i):
    #                     if i.id in block.data:
    #                         if check_commit_data(i, block.data[i.id]):
    #                             checked_items[i.id] = True
    #                         else:
    #                             mismatch = True
    #                             fail_reason = 131
    #                             prnt('commit data mismatch111', i.id)
    #                             # logEvent(f'mismatch111: {i.id}, achieved position:{fail_reason}, - {block.Blockchain_obj.genesisName}', log_type='Errors', code='4982764')
    #                             break
    #                 else:
    #                     requested_validators += i.id

    # # prnt('next12 requested_idens:',requested_idens)

    # prnt('next1233 mismatch:',mismatch, requested_idens)
    # if not mismatch and requested_idens:
    #     prnt('proceed to fetch')
    #     # updated_objs = request_items(requested_idens, return_updated_objs=True, downstream_worker=False)
    #     # prntDebug('returned updated_objs',updated_objs)
    #     # if updated_objs:
    #     #     storedModels, not_found, not_valid = get_data(requested_idens, return_model=True, include_related=False)
    #     #     for i in storedModels:
    #     #         prntDebug('ia1',i)
    #     #         if i.id in block.data:
    #     #             if check_commit_data(i, block.data[i.id]):
    #     #                 checked_items[i.id] = True
    #     #             else:
    #     #                 mismatch = True
    #     #                 fail_reason = 133
    #     #                 logEvent(f'commit data mismatch4444: {i.id}, achieved position:{fail_reason}, - {block.Blockchain_obj.genesisName}', log_type='Errors', code='384573')
    #     #                 prnt('commit data mismatch4444', i.id)
    #     #                 break

    

    # usa = Region.objects.filter(Name='USA').first()


    # models = [
    #     'Region',
    #     # 'Role',
    #     'Update',
    #     'District',
    #     'Person',
    #     'Party',
    #     'Government',
    #     'Vote',
    #     'Motion',
    #     'Committee',
    #     'Statement',
    #     'Meeting',
    #     'Bill',
    #     'BillText',
    #     'Agenda',
    #     # 'AgendaItem',
    #     # 'AgendaTime',
    #     'GenericModel',
    #     'Post',
    #     'Keyphrase',
    #     'KeyphraseTrend',
    #     'Election',
    #     'Notification',
    #     'UserNotification',
    #     # 'Blockchain',
    #     # 'Validator',
    #     # 'Wallet',
    #     # 'UserTransaction',
    #     'Node'
    #     ]
    # for model in models:
    #     prnt()
    #     prnt('get model:', model)
    #     objs = get_dynamic_model(model, list=True, Block_obj=None, Region_obj=usa)
    #     if objs:
    #         total = len(objs)
    #         prnt('len objs', total)
    #         n = 1
    #         for obj in objs:
    #             prnt(f'{n}/{total}')
    #             n += 1
    #             superDelete(obj, force_delete=True)


    # prnt('stage2')
    # chain = Blockchain.objects.filter(genesisId=usa.id).first()
    # # block = Block.objects.filter(Blockchain_obj=chain).order_by('-index')
    # # for block in blocks:
    
    
    # for block in Block.objects.filter(Blockchain_obj=chain).order_by('-index'):
    #     block.is_not_valid(super_delete_content=True)
    #     block.delete(superDel=True)


    # rd = ['btxtSo02619a84072dc471c5489a492a4c1687', 'btxtSo0baa3fbf25bd1ead268765163ee66216', 'btxtSo1281234a00f63b7800bcdb57b1ce02df', 'btxtSo196ef8de0456536649de5c608367b9bb', 'btxtSo245c0e564758bab360dcd20460646b75', 'btxtSo2a5a2856a91cb093e7e882c11071a12c', 'btxtSo2ab62c7e1a91e42d782b13078b391943', 'btxtSo2bc453880b2e1d7b16a909e2e400fd5f', 'btxtSo2ed8fe170bb46f2be00c2bc61137c97d', 'btxtSo3f8185dc075390a2a36130076a26b90e', 'btxtSo40636e86dbc92c7e32c52690926f010d', 'btxtSo42005d7c6e88fbfd28c9210a70dd2beb', 'btxtSo4883bc3d4cd06a91c855c5b76e10ade2', 'btxtSo4ea43544d8bafa76ef63c4a2bbad4f63', 'btxtSo5ced8f82495494c601701665a2625df8', 'btxtSo7ab9feba7430cd6a25ff6c034786fa0e', 'btxtSo7bc3866667548d33ab76b58210f4eed3', 'btxtSo8518c6beaa8226b69338426c4a6ded6b', 'btxtSo8ec1802865f71e215e7510dd034c6244', 'btxtSoa8f146f3c3a369d098e13948a32bea71', 'btxtSoa96fd2626a19091d63abc05f0b2a78b5', 'btxtSoaab3f3409e4650925538a1506d9891c0', 'btxtSoaddd688d78291a019c952bb326cba6de', 'btxtSoaef092a888587839a1c3e61dac359255', 'btxtSoaffdf009013800286955ce04dece1a38', 'btxtSob27f36517a4a2d3fbd44de4faaaf2a99', 'btxtSob3e7618afcf477727d52358d85b68af9', 'btxtSob52879e9146c67633aaf0472741ec702', 'btxtSob69be5722d3e791f2f66bab241a2098e', 'btxtSob95341fa926102019894027911300c2b', 'btxtSobfe03ee31405a5d098706b4bcc3fc867', 'btxtSoc360fcdcbb3038bc3d24226446e39041', 'btxtSod2fa1db052e207ca429174e149da951b', 'btxtSod651e3d6dc70ce054c7fbfe30843dda4', 'btxtSoda746408235eb4ac216ecaff18032aa1', 'btxtSodb1963406150d3ad28f42c855a29ca24', 'btxtSoe60b2ee5b0656683798ab46220346d78']
    # request_items(requested_items=rd, nodes=None, request_validators=False, return_updated_count=False, return_updated_objs=False, return_updated_ids=False, downstream_worker=False)



    # block = Block.objects.filter(blockchainId='chaSo50a583f28bb6aeb229c06ba93befb382').exclude(validated=True).first()
    # prnt('block',block)
    # if block:
    #     block.is_not_valid()


    text = '''Aurora Greenway, a widow since her daughter Emma was a young girl, keeps several suitors at arm's length in River Oaks, Houston, focusing instead on her close, but controlling, relationship with Emma. Anxious to escape her mother, Emma marries callow young college professor Flap Horton over her mother's objections.

    Despite their frequent spats and difficulty getting along with each other, Emma and Aurora have very close ties and keep in touch by telephone. Soon after the wedding, Emma gets pregnant with their first child. He is a few years old when she is again expecting another.

    The small family moves to Iowa in order for Flap to pursue a career as an English professor. When they run into financial difficulties, Emma calls Aurora for help. Admitting she is pregnant with a third, her mother suggests she go to Colorado for an abortion.

    When Flap gets home, as he was away overnight, Emma demands to be told if he is having an affair. He insists it is paranoia, brought on by the pregnancy hormones. While at the grocery store, Emma does not have enough money to pay for all of her groceries and meets Sam Burns, who helps pay for them.

    Meanwhile the lonely Aurora, after her doctor discloses her real age at her birthday celebration, overcomes her repression and begins a whirlwind romance with her next-door neighbor, retired astronaut Garrett Breedlove, who is promiscuous and coarse. Simultaneously Emma and Sam strike up a friendship and quickly an affair as Sam's wife refuses to have sex with him, and she suspects Flap of infidelity.

    Over the course of the next few years, the marriage begins to fray. Emma catches Flap flirting with one of his students on campus, so drives back to Houston immediately. There, Garrett develops cold feet about his relationship with Aurora after seeing her with her daughter and grandkids and breaks it off.

    While Emma is gone, Flap accepts a promotion in Nebraska; she and the children return to Iowa, then they move to Nebraska. While on the campus, Emma sees the same young woman who she had seen Flap with in Iowa. Confronting her, she finds out he moved them to Nebraska so he could work with his girlfriend Janice.

    When Emma is diagnosed with cancer, before she knows how advanced it is, her lifelong friend Patsy convinces her to explore NYC. She is there a short time when Patsy's friends there first find it strange she has never worked then it gets more uncomfortable when they hear about the cancer. Not enjoying herself, she returns home early.

    When they discover it is terminal cancer, Aurora and Flap stay by Emma's side through her treatment and hospitalization. Garrett flies to Nebraska to be with Aurora and her family. The dying Emma shows her love for her mother by entrusting her children to Aurora's care.

    The newly formed family, Aurora and the kids with Garrett, live together in Houston.'''
    text2 = '''Terms of Endearment is a 1983 American family tragicomedy[3] film directed, written, and produced by James L. Brooks, adapted from Larry McMurtry's 1975 novel of the same name. It stars Debra Winger, Shirley MacLaine, Jack Nicholson, Danny DeVito, Jeff Daniels, and John Lithgow. The film covers 30 years of the relationship between Aurora Greenway (MacLaine) and her daughter Emma Greenway-Horton (Winger).

    Terms of Endearment was theatrically released in limited theatres on November 23, 1983, and to a wider release on December 9 by Paramount Pictures. The film received critical acclaim and was a major commercial success, grossing $165 million at the box office, becoming the second-highest-grossing film of 1983 (after Return of the Jedi). At the 56th Academy Awards, the film received a leading 11 nominations, and won a leading five awards: Best Picture, Best Director, Best Actress (MacLaine), Best Adapted Screenplay, and Best Supporting Actor (Nicholson). A sequel, The Evening Star, was released in 1996.'''

    text3 = '''James L. Brooks wrote the supporting role of Garrett Breedlove for Burt Reynolds, who turned down the role because of a verbal commitment he had made to appear in Stroker Ace. "There are no awards in Hollywood for being an idiot", Reynolds later said of the decision.[4] Harrison Ford and Paul Newman also turned down the role.[5][6]

    The exterior shots of Aurora Greenway's home were filmed at 3060 Locke Lane, Houston, Texas. The exterior shots of locations intended to be in Des Moines, Iowa and Kearney, Nebraska were instead filmed in Lincoln, Nebraska. Many scenes were filmed on, or near, the campus of the University of Nebraska-Lincoln.[7] While filming in Lincoln, the state capital, Winger met then-governor of Nebraska Bob Kerrey; the two wound up dating for two years.[8]

    Shirley MacLaine and Debra Winger reportedly did not get along with each other during production.[9][10][11][12] MacLaine confirmed in an interview that "it was a very tough shoot ... Chaotic...(Jim) likes working with tension on the set."[13]

    On working with Jack Nicholson, MacLaine said, "Working with Jack Nicholson was crazy",[14] but that his spontaneity may have contributed to her performance.[15] She also said,

    We're like old smoothies working together. You know the old smoothies they used to show whenever you went to the Ice Follies. They would have this elderly man and woman – who at that time were 40 – and they had a little bit too much weight around the waist and were moving a little slower. But they danced so elegantly and so in synch with each other that the audience just laid back and sort of sighed. That's the way it is working with Jack. We both know what the other is going to do. And we don't socialize, or anything. It's an amazing chemistry – a wonderful, wonderful feeling.[12]

    MacLaine also confirmed in an interview with USA Today that Nicholson improvised when he put his hand down her dress in the beach scene.[16]'''

    text4 = '''Steele's Greenville expedition took place from April 2 to 25, 1863, during the Vicksburg campaign of the American Civil War. Union forces commanded by Major General Frederick Steele occupied Greenville, Mississippi, and operated in the surrounding area, to divert Confederate attention from a more important movement made in Louisiana by Major General John A. McClernand's corps. Minor skirmishing between the two sides occurred, particularly in the early stages of the expedition. Over 1,000 slaves were freed during the operation, and large quantities of supplies and animals were destroyed or removed from the area. Along with other operations, including Grierson's Raid, Steele's Greenville expedition distracted Confederate attention from McClernand's movement. Some historians have suggested that the Greenville expedition represented the Union war policy's shifting more towards expanding the war to Confederate social and economic structures and the Confederate homefront.

    Background
    Main article: Vicksburg campaign
    During early 1863, when the American Civil War was ongoing, Union Army forces commanded by Major General Ulysses S. Grant were undertaking the Vicksburg campaign against the Confederate-held city of Vicksburg, Mississippi.[1] After having repeatedly failed to maneuver out of the surrounding swamps and onto high ground near Vicksburg, Grant decided between three options: an amphibious crossing of the Mississippi River and attack of the Confederate riverfront defenses; pulling back to Memphis, Tennessee, and then making an overland drive south to Vicksburg; and moving south of Vicksburg and then crossing the Mississippi River to operate against the city. The first option risked heavy casualties and the second could be misconstrued as a retreat by the civilian population and political authorities, so Grant chose the third option.[2] In late March, Grant ordered the XIII Corps, commanded by Major General John A. McClernand, to move down the Louisiana side of the Mississippi River and then prepare to cross the river at a point south of Vicksburg.[1]

    As part of an attempt to distract the Confederate forces at Vicksburg, who were commanded by Lieutenant General John C. Pemberton, from McClernand's movement, Grant sent the division of Major General Frederick Steele to Greenville, Mississippi, roughly 70 miles (110 km) upriver from Vicksburg.[3] Steele's instructions were to land in the Mississippi Delta, advance to Greenville, and then operate in the Deer Creek area.[4] Major General William T. Sherman, the commander of XV Corps and Steele's superior officer,[5] hoped that Steele might reach to where Deer Creek met Rolling Fork, which was the furthest Union penetration in the Steele's Bayou expedition.[6] Once there, the Union soldiers were to burn any baled cotton marked with "CSA" (for Confederate States of America), clear out any Confederate forces in the area, and burn abandoned plantations.[4] Steele was also instructed to warn civilians in the region that retaliation would be made for attacks on Union transports on the Mississippi.[7] About 5,600 soldiers of Steele's division were part of the expedition.[8] Lieutenant Colonel[9] Samuel W. Ferguson commanded the Confederate forces in the area.[10]'''

    text5 = '''Steele's troops left the Young's Point, Louisiana,[a] area late on April 2, heading upriver via steamboats. The soldiers in the ranks did not know their destination.[12] The next morning, the boats reached Smith's Landing,[13] which was 20 miles (32 km) south of Greenville. Flooding rendered the terrain impassable in this area except on the levees,[14] and the Union soldiers learned that a large stash of cotton known to be in the area had already been burned. On either the next day[13] or April 5, the expedition reached Washington's Landing. While much of Steele's force remained in the Washington's Landing area, detachments patrolled inward, learning that the path to Deer Creek was flooded.[4] After the soldiers returned to the transports, movement was made to Greenville that evening, and the Union troops disembarked the next morning at a point about 1 mile (1.6 km) north of Greenville. Two regiments and the Union Navy tinclad steamer USS Prairie Bird were left at the landing point to guard it.[15]

    Steele's pioneer force rebuilt a bridge near the plantation of Confederate officer Samuel G. French, and continued inland.[9][b] The Union commander learned of the presence of Ferguson's Confederates on April 6. The Union officers pushed their troops hard, hoping to overtake and capture the Confederate force. Ferguson had known of the Union presence since not long after the landing, and he sent a messenger to Major General Carter L. Stevenson at Vicksburg, asking for instructions. Stevenson detached the brigade of Brigadier General Stephen Dill Lee to the area, with orders to secure Rolling Fork and then move up the Bogue Phalia stream and strike Steele's rear. Ferguson, in turn, withdrew his troops to the Thomas plantation, which was about 20 miles (32 km) north of Rolling Fork.[16] More reinforcements were positioned at Snyder's Bluff and along the Sunflower River, and some cottonclad gunboats were shifted southwards in response to the threat. Ferguson also sent a task force to a bend on the Mississippi River with instructions to cut a levee near Black Bayou, with the intent of flooding the terrain in the area, particularly where a road in Steele's rear crossed a swamp.[17] Between the commands of Ferguson and Lee, the Confederates had about 4,300 soldiers.[18]

    Ferguson prepared a delaying action. When, on the afternoon of April 7, Steele's column approached the Thomas plantation, Ferguson had Bledsoe's Missouri Battery and Sengstak's Alabama Battery open fire on them;[19] Ferguson's force was deployed in front of a canebrake.[17] Union forces had operated in this area before, during an expedition in February commanded by Brigadier General Stephen G. Burbridge, which had been intended to drive out Confederate troops that were harassing Union shipping.[20] Steele, in turn, deployed artillery and prepared to make an attack, but Ferguson withdrew,[21] 6 miles (9.7 km) south to the Willis plantation.[22] During the pursuit, Union troops stumbled across the body of a lynched African-American who, believing Ferguson's troops were Union forces, had requested a gun with which to kill his master and expressed intent to rape white women.[23] Steele halted the pursuit on the morning on April 8, and his troops confiscated and destroyed goods found on the plantations in the area.[24] A scouting force sent by Steele detected the presence of Lee's force,[25] and the Union general ordered a withdrawal, not wanting to fight both Confederate forces too far from Greenville. During the march back, the Union troops destroyed supplies and took horses, mules, and livestock from the surrounding area.[23] The Confederates pursued, and the Union troops skirmished with them on April 8, continuing on to the French plantation on the 9th.[26] Also on April 9, Pemberton learned from Stevenson that Union troops had landed at Greenville and that Lee had been sent to counter them; Pemberton ordered the transfer of 1,500 soldiers from Fort Pemberton to Rolling Fork to reinforce Lee and Ferguson.[27] The bridge the Union troops had built there collapsed on April 10 while a herd of cattle crossed it, leading to a delay that allowed Confederate troops to catch up to the Union column.[28] Union artillery fire held the Confederate troops at bay; after the Union forces crossed the bridge it was destroyed.[29] During the course of the expedition, Steele's troops had moved 43 miles (69 km) down Deer Creek.[28]

    During the movements, many slaves flocked to the Union lines and followed the troops to gain their freedom.[30] Steele did not want this,[25] and encouraged them to remain on plantations; when the campaign began, he had been ordered to discourage slaves from fleeing to Union lines.[30] Unsure of what to do with the large number of followers, Steele sent a message to Sherman; when Sherman did not respond, Steele contacted Grant.[23] Grant advised Steele to encourage slaves to come to Union lines, and suggested that he should form regiments of United States Colored Troops out of male former slaves who volunteered for military services, much as Brigadier General Lorenzo Thomas had begun doing. About 500 African-Americans volunteered for the service, placed in new regiments to be led by white officers.[31]

    April 13 saw Union troops make another sweep of the Greenville area. Ferguson had withdrawn his troops, but left behind large quantities of supplies and cattle, which the Union soldiers found and brought back to camp.[32] Shortly thereafter, Lee's command withdrew from the area.[33] On April 20, Steele sent the 3rd and 31st Missouri Infantry Regiments to the Williams Bayou area; they returned on April 22 with quantities of mules, corn, and livestock.[34] The Union troops were ordered to avoid disturbing local families who were peaceful and remained at home, but these orders were ignored. Many of the plantations in the area were burned,[35] and hard feelings against the Union forces grew among the local populace.[36] During the expedition Union forces took more than 1,000 animals, besides destroying 500,000 US bushels (18,000,000 L) of corn.[37] Journalist Franc Wilkie accompanied the expedition and estimated the damages as at least $3 million (equivalent to $60,313,000 in 2024).[38] The naval historian Myron J. Smith and the historians William L. Shea and Terrence J. Winschel say that around 1,000 slaves were freed;[37][39] the historian Timothy B. Smith cites estimates that up to 2,000 or 3,000 slaves followed Steele's column back to Greenville.[40] On April 22, Grant instructed Steele to return from the Greenville area, but a shortage of transports prevented the Union soldiers from setting off until late on April 24. The next morning, Steele's forces returned to Young's Point.[34]'''

    text6 = '''In the words of James H. Wilson, Steele's Greenville expedition made the Union army an implement of "agricultural disorganization and distress as well as of emancipation".[31] Both Sherman and Steele believed that Union troops had gone too far in behavior that affected civilians, rather than just Confederate military targets.[35] Shea and Winschel see the expedition as demonstrating a shift in the Union's war policy.[37] In an earlier communication, Henry Halleck (who had been appointed General-in-Chief of the Union Army in July 1862) had written to Grant that he believed that there would be "no peace but that which is forced by the sword". Grant accepted the policy of carrying the war to the social and economic structures of the Confederacy. In the future, in the words of Shea and Winschel, the Union army brought "the war home to [Confederate] civilians by enforcing emancipation and seizing or destroying all items of possible military value".[41] Besides ravaging an area important to the Confederate forces at Vicksburg of supplies, the Greenville expedition also drew Confederate attention away from McClernand's more important operations in Louisiana,[42] although other operations such as Grierson's Raid also played a role.[43]

    In late April, Union forces crossed the Mississippi River south of Vicksburg and then moved inland.[44] The Union troops defeated a Confederate force in the Battle of Port Gibson on May 1, and on May 12 won another victory in the Battle of Raymond. After the action at Raymond, Grant decided to strike a Confederate force forming at Jackson, Mississippi, and then turn west towards Vicksburg.[45] Grant's troops won a small battle at Jackson on May 14, and then defeated Pemberton's army in the climactic Battle of Champion Hill on May 16.[46] After another Confederate defeat at the Battle of Big Black River Bridge on May 17, the Siege of Vicksburg began on May 18. When the city surrendered on July 4, it was a major defeat for the Confederacy.[47]'''


    # country = Region.objects.filter(Name='USA').first()
    # statement = Statement(id='xx'+str(uuid.uuid4().hex), Content=text, PersonName='personName', DateTime=now_utc(),  Government_obj=Government.objects.first(), Country_obj=country, Region_obj=country)
    # time.sleep(3)
    
    # # statement.save()

    prnt('stage 3')
    # # # # mytry(text)
    # from posts.models import get_keywords
    # prntDebugn('round 1')
    # statement = get_keywords(statement, text)
    # prntDebugn('round 2')
    # statement = get_keywords(statement, text2)
    # prntDebugn('round 3')
    # statement = get_keywords(statement, text5)
    # prntn('done xxx')
    # # prnt(statement)


    # import yake

    # # Define your skip words
    # skip_words = {"example", "discussion", "important"}  # Replace with your list

    # print('1')
    # spacy_stopwords = set()
    # try:
    #     import spacy

    #     nlp = spacy.load("en_core_web_sm")
    #     spacy_stopwords = nlp.Defaults.stop_words
    # except Exception as e:
    #     prnt('e:',str(e))

    # # Merge stop words
    # # final_stopwords = spacy_stopwords | custom_stopwords
    # print('2')

    # from nltk.corpus import stopwords
    # import nltk
    # print('3')
    # # Download stop words if not already installed
    # nltk.download("stopwords")

    # # Get English stop words
    # nltk_stopwords = set(stopwords.words("english"))

    # # Your additional skip words
    # custom_stopwords = {"example", "discussion", "important"}

    # # Merge both lists
    # final_stopwords = nltk_stopwords | custom_stopwords | spacy_stopwords
    # print('go')
    # # def extract_keywords(text, top_n=6):
    # #     kw_extractor = yake.KeywordExtractor(n=3, top=top_n, stopwords=final_stopwords)
    # #     keywords = [kw[0] for kw in kw_extractor.extract_keywords(text)]
    # #     return keywords

    # text = "This is an important discussion about AI and machine learning."
    # # print('yake1:',extract_keywords(text))
    # # print('yake2:',extract_keywords(text2))
    # # print('yake3:',extract_keywords(text3))

    # # print()

    # # from sklearn.feature_extraction.text import TfidfVectorizer

    # # # Define your skip words
    # # skip_words = {"example", "discussion", "important"}  # Replace with your list

    # # def extract_keywords(texts, top_n=20):
    # #     vectorizer = TfidfVectorizer(ngram_range=(1,3), stop_words=list(skip_words) + ["english"], min_df=2)
    # #     X = vectorizer.fit_transform(texts)
    # #     feature_array = vectorizer.get_feature_names_out()
        
    # #     # Sort words by highest TF-IDF score
    # #     scores = X.toarray().sum(axis=0)
    # #     sorted_indices = scores.argsort()[::-1]
    # #     keywords = [feature_array[i] for i in sorted_indices[:top_n]]
        
    # #     return keywords

    # # texts = [text, text2, text3]
    # # print('otherone:',extract_keywords(texts))


    # # print()
    # # from keybert import KeyBERT
    # # # import os
    # # # os.environ["TOKENIZERS_PARALLELISM"] = "false"
    # # # prntDebug('s3')
    # # kw_model = KeyBERT()
    # # # prntDebug('s4')
    # # stop_w = []
    # # # from posts.models import skipwords
    # # # for i in skipwords:
    # # #     stop_w.append(i)
    # # spares = {}
    # # keyword_array = []
    # # # prntDebug('s5')
    # # xen = kw_model.extract_keywords(text, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
    # # print('keybert:',xen)
    # # xen = kw_model.extract_keywords(text2, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
    # # print('keybert2:',xen)
    # # xen = kw_model.extract_keywords(text3, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
    # # print('keybert3:',xen)








    # import yake
    # from collections import defaultdict
    # import time

    # # Initialize YAKE extractor
    # def initialize_yake(custom_stopwords=set()):
    #     return yake.KeywordExtractor(n=3, stopwords=custom_stopwords)

    # # Extract keywords from a given text
    # def extract_keywords(text, kw_extractor, top_n=6):
    #     keywords = [kw[0] for kw in kw_extractor.extract_keywords(text)]
    #     return keywords

    # # Function to track and update keywords over time with recency bias
    # def update_keywords_over_time(text, keyword_history, kw_extractor, recency_factor=0.5, top_n=6):
    #     keywords = extract_keywords(text, kw_extractor, top_n)
    #     prnt('keywords',keywords)
    #     # Update keyword history with recency factor
    #     current_time = time.time()  # Get current timestamp
        
    #     for keyword in keywords:
    #         # print('k',keyword)
    #         if keyword in keyword_history:
    #             # Apply recency factor to the keyword score
    #             keyword_history[keyword][0] += 1  # Increment count
    #             keyword_history[keyword][1] = current_time  # Update timestamp
    #         else:
    #             # Initialize keyword history entry
    #             keyword_history[keyword] = [1, current_time]  # [count, timestamp]
        
    #     # Sort by frequency and recency bias (latest texts get more weight)
    #     sorted_keywords = sorted(keyword_history.items(), key=lambda x: (x[1][0], -x[1][1] * recency_factor), reverse=True)
        
    #     # Return the top N keywords based on frequency and recency
    #     return [keyword for keyword, _ in sorted_keywords[:top_n]]

    # # Example usage
    # custom_stopwords = {"example", "discussion", "important", "to", "the", "her"}  # Custom stop words
    # kw_extractor = initialize_yake(final_stopwords)

    # # Simulating incoming texts over time
    # keyword_history = {}
    # texts = [
    #     "This is an important discussion about AI and machine learning.",
    #     "Her insights into artificial intelligence were impressive.",
    #     "AI has the potential to revolutionize many industries."
    # ]

    # # for t in texts:
    # #     print(update_keywords_over_time(t, keyword_history, kw_extractor))

    # print()
    # print(update_keywords_over_time(text, keyword_history, kw_extractor))
    # print(update_keywords_over_time(text2, keyword_history, kw_extractor))
    # print(update_keywords_over_time(text3, keyword_history, kw_extractor))
    # print(update_keywords_over_time(text4, keyword_history, kw_extractor))
    # print(update_keywords_over_time(text5, keyword_history, kw_extractor))
    # print(update_keywords_over_time(text6, keyword_history, kw_extractor))






    # text = '''

    # The SPEAKER pro tempore laid before the House the following 
    # communication from the Speaker:

    #                                             Washington, DC,

    #                                                 March 10, 2025.
    #     I hereby appoint the Honorable Mariannette Miller-Meeks to 
    #     act as Speaker pro tempore on this day.
    #                                                     Mike Johnson,
    #     Speaker of the House of Representatives.

                            


    # '''

# keep at this
# also, somehow a block was created and is unabe to make invalid because the data is 14000 long at the job times out, wtf? how was it created?
    start_time = time.time()
    # if (time.time() - start_time) < 60:
    #     prnt('is yes')
    # else:
    #     prnt('is no')
    # try:
    #     prnt((time.time() - start_time))
    # except Exception as e:
        # prnt('fail123445', str(e))
    # from joblib import parallel_backend
    # parallel_backend("threading")
    # def mytry(text):
    # try:
    #     prnt('1')
    #     # with parallel_backend("threading"):
    #     # import multiprocessing

    #     # multiprocessing.set_start_method("spawn", force=True)
    #     prnt('10')
    #     from keybert import KeyBERT
    #     import os
    #     # os.environ["TRANSFORMERS_OFFLINE"] = "1"
    #     os.environ["TOKENIZERS_PARALLELISM"] = "false"
    #     # os.environ["TRANSFORMERS_PARALLELISM"] = "false"
    #     prnt('1a')
    #     kw_model = KeyBERT(model="all-MiniLM-L6-v2")
    #     prnt('1b')
    #     stop_w = []
    #     # for i in skipwords:
    #     #     stop_w.append(i)
    #     spares = {}
    #     keyword_array = []
    #     prnt('2')
    #     x = kw_model.extract_keywords(text, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
    #     n = 0
    #     prnt('3')
    #     terms = ''
    #     for i, r in x:
    #         if i not in stop_w and i not in keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
    #             keyword_array.append(i)
    #             n += 1
    #             terms = terms + i + ' '
    #     prnt('4')
    #     prnt('keyword array 1', keyword_array)
    #     x = kw_model.extract_keywords(text, top_n=7, keyphrase_ngram_range=(1, 1), stop_words=stop_w)
    #     n = 0
    #     prnt('5')
    #     for i, r in x:
    #         if i not in stop_w and not i.isnumeric():
    #             if i in str(terms):
    #                 if i in spares:
    #                     spares[i] += 1
    #                 else:
    #                     spares[i] = 1
    #             elif n < 7:
    #                 keyword_array.append(i)
    #                 stop_w.append(i)
    #                 n += 1
    #     prnt('6')
    #     if spares:
    #         prnt('7')
    #         for term, count in spares.items():
    #             matches = 0
    #             for i in keyword_array:
    #                 if term in i:
    #                     matches += 1
    #             if count > matches or matches > 2:
    #                 for i in keyword_array:
    #                     if term in i:
    #                         keyword_array.remove(i)
    #                 keyword_array.append(term)
    
    #     prnt('8')
    #     prnt('keyword array 2', keyword_array)
    # except Exception as e:
    #     prnt('get_keywords fail', str(e))
    #     # from blockchain.models import logEvent
    #     # logEvent(e, code='592467385', func='get_keywords', log_type='Errors')
    #     # time.sleep(10)

    # mytry(text)
    prnt('stage 2')
    # # country = Region.objects.filter(Name='USA').first()
    # statement = Statement(id='xx'+str(uuid.uuid4().hex), Content=text, PersonName='personName', DateTime=now_utc(),  Government_obj=Government.objects.first(), Country_obj=country, Region_obj=country)
    # time.sleep(3)
    
    # # # statement.save()

    # prnt('stage 3')
    # # # # mytry(text)
    # from utils.models import get_keywords
    # statement = get_keywords(statement, text)
    prnt('done xxx')
    # prnt(statement)
        
    # blocks = Block.objects.filter(validated=True).order_by('DateTime')
    # for b in blocks:
    #     prnt('\nb',b)
    #     b.is_not_valid()

    # queue = django_rq.get_queue('low')
    # queue.enqueue(process_data_packet, 'datSob868383b146d96e03ae0af600fa7fcee', job_timeout=240, result_ttl=3600)
    # super_share('datSo3ae5ee17b82c4f0daf8a2aca101cf952', Government.objects.first())

    # block = Block.objects.filter(id='bloSoa845d14f028ae0d0774bae4873e4b6ae').first()
    # # prntn('block',block)
    # # prnt(check_validation_consensus(block))
    # url = 'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22119%22%2C%22chamber%22%3A%22Senate%22%7D'
    # try:
    #     driver = open_browser(url)
    #     prnt('loaded')
    #     element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
    #     WebDriverWait(driver, 10).until(element_present)
    #     prnt('ready1')

    #     soup1 = BeautifulSoup(driver.page_source, 'html.parser')
    # except Exception as e:
    #     prnt(str(e))

    # driver.quit()

    # blocks = Block.objects.filter(blockchainType='Nodes').order_by('index', 'created')
    # for b in blocks:
    #     prnt()
    #     prnt('block1234:',b)
    #     if not b.validated:
    #         is_valid, consensus_found, validators = check_validation_consensus(b, do_mark_valid=True, broadcast_if_unknown=False, downstream_worker=False, handle_discrepancies=False, backcheck=False, get_missing_blocks=False)
    #         prntDebugn('******check_consensus:',is_valid, consensus_found)

    prnt('done')
    # http://173.249.217.51:18141/utils/scrapers/usa/True
    # import requests
    # response = requests.get('http://173.249.217.51:18141/utils/myip', timeout=5)
    # prnt('response',response)


    # success, r = connect_to_node('173.249.217.51:18141', 'utils/myip', operatorData=operatorData, timeout=(5,10), get=True, stream=False, node_is_string=True)
    # prnt('success',success)
    # prnt('r',r)

    # success, r = connect_to_node('173.249.217.51:18141', 'utils/myip', data={'hello':'this is a test'}, operatorData=operatorData, timeout=(5,10), get=False, stream=True, node_is_string=True)
    # prnt('success1',success)
    # prnt('r1',r)


    # success, r = connect_to_node('173.249.217.51:18141', 'utils/myip', data={'hello':'this is a test'}, operatorData=operatorData, timeout=(5,10), get=False, stream=True, node_is_string=True)
    # prnt('success2',success)
    # prnt('r2',r)

    # from scrapers.usa.federal import get_senate_debates
    # get_senate_debates(special='super', dt=now_utc(), target={'link':'https://www.govinfo.gov/app/details/CREC-2025-02-04/context'}, driver=None)

    # districts = list(Region.objects.filter(Validator_obj=None))
    # super_share(log=districts, func='set_object')

    # Tidy().uncommitted_posts_run(hours=1)
    # validated_posts = 0
    # nonvalidated_posts = 0
    # posts = Post.all_objects.filter(validated=False).order_by('added')
    # for p in posts:
    #     if p.validate():
    #         validated_posts += 1
    #     else:
    #         nonvalidated_posts += 1

    # validated_updates = 0
    # nonvalidated_updates = 0
    # updates = Update.objects.filter(validated=False).order_by('added')
    # for u in updates:
    #     if u.validate():
    #         validated_updates += 1
    #     else:
    #         nonvalidated_updates += 1
    # prnt(f'posts:{len(posts)}-validated_posts:{validated_posts}-nonvalidated_posts:{nonvalidated_posts}')
    # prnt(f'updates:{len(updates)}-validated_updates:{validated_updates}-nonvalidated_updates:{nonvalidated_updates}')
    # num = 500
    # offset = 0
    # exclude_idens = []
    # # run = True
    # while True:
    #     update_me = []
    #     # prnt('offset',offset)
    #     posts = Post.objects.exclude(id__in=exclude_idens).filter(filters__exact={}).iterator(chunk_size=500)
    #     if not posts:
    #         break
    #     prnt('posts len', posts)
    #     for p in posts:
    #         if p.id not in exclude_idens:
    #             exclude_idens.append(p.id)
    #         if p.Chamber:
    #             p.filters['Chamber'] = p.Chamber
    #         if p.gov_level:
    #             p.filters['gov_level'] = p.gov_level
    #         if p.Update_obj:
    #             if 'Position' in p.Update_obj.data:
    #                 p.filters['Position'] = p.Update_obj.data['Position']
    #             if 'LastName' in p.Update_obj.data:
    #                 p.filters['LastName'] = p.Update_obj.data['LastName']
    #             if 'has_text' in p.Update_obj.data:
    #                 p.filters['has_text'] = p.Update_obj.data['has_text']
    #         if p.pointerType == 'Bill' and p.Bill_obj:
    #             if p.Bill_obj.NumberCode:
    #                 p.filters['NumberCode'] = p.Bill_obj.NumberCode
    #             if p.Bill_obj.amendedNumberCode:
    #                 p.filters['amendedNumberCode'] = p.Bill_obj.amendedNumberCode
    #             if p.Bill_obj.Title:
    #                 p.filters['Title'] = p.Bill_obj.Title
    #             if p.Bill_obj.ShortTitle:
    #                 p.filters['ShortTitle'] = p.Bill_obj.ShortTitle
    #             if p.Bill_obj.BillDocumentTypeName:
    #                 p.filters['BillType'] = p.Bill_obj.BillDocumentTypeName
    #         update_me.append(p)
    #         posts = None
    #     dynamic_bulk_update(model=Post, items_field_update=['filter'], items=update_me)
    #     # offset += num




def tester_queue_view(request):
    if request:
    # if request.user.is_superuser:
        prnt('---tester_queue_view')
        # # tester_queue()
        # import django_rq
        # queue = django_rq.get_queue('low')
        # queue.enqueue(tester_queue, job_timeout=1200)

        from blockchain.models import Blockchain, Block,NodeReview,NodeChain_genesisId
        # from accounts.models import UserTransaction, UserPubKey,verify_obj_to_data, hash_obj_id
        from legis.models import Government, Statement, Bill, Motion, Person, BillText
        from transactions.models import UserTransaction
        import uuid
        # from utils.models import get_model_prefix, get_operatorData,get_self_node
        from scrapers.usa.federal import get_bills
        operatorData = get_operatorData()
        self_node = get_self_node()

        start_time = now_utc()
        prnt('HELLLOO!!')


        all = ['nod','reg', 'usr', 'upk','uver','udat']
        for i in ['regSoIkpb6hxMSAEOQI','regSoYZ4VJcKXEO42Cq','regSo4by0PRcGDSYkSY']:
            prnt(i)
            i.boot()
            # if i.startswith(tuple(all)):
            #     prnt('yes')
            # else:
            #     prnt('no')

        # import importlib
        # from django.conf import settings



        # def get_all_model_prefixes():
        #     model_prefixes_list = []

        #     for app in settings.INSTALLED_APPS:
        #         try:
        #             prnt('app_config.name',app)
        #             if app in ['accounts', 'blockchain', 'transactions', 'posts']:
        #                 # Try to import the models module
        #                 models_module = importlib.import_module(f"{app}.models")
        #                 if hasattr(models_module, "model_prefixes"):
        #                     prefixes = getattr(models_module, "model_prefixes")
        #                     if isinstance(prefixes, dict):
        #                         model_prefixes_list.append(prefixes)
        #         except ModuleNotFoundError:
        #             continue  # No models.py, skip this app
        #         except Exception:
        #             continue  # Handle broken models.py or import issues

        #         # Check for the 'model_prefixes' attribute

        #     return model_prefixes_list
        # prnt('loading apps')
        # prefixes = get_all_model_prefixes()
        # prnt()
        # for d in prefixes:
        #     prnt(d)

        # from django.apps import apps
        # import importlib

        # for app_config in apps.get_app_configs():
        #     try:
        #         prnt('app_config.name',app_config.name)
        #         # importScript = f'scrapers.{country_name}.{provState_name}.{name}'
        #         # Try to import the module where `myDict` is expected (e.g., in app/my_dict.py)
        #         module = importlib.import_module(f"{app_config.name}.model.py")
        #         # Try to get the `myDict` variable from that module
        #         prnt('module',module)
        #         if hasattr(module, "model_prefixes"):
        #             prnt('x1',getattr(module, "model_prefixes"))
        #         else:
        #             prnt('x2')
        #             # all_my_dicts[app_config.name] = getattr(module, "myDict")
        #     except ModuleNotFoundError:
        #         prnt('x3')
        #         # Skip if the app doesn't have my_dict.py
        #         continue
        #     except Exception as e:
        #         prnt(f"Error loading myDict from {app_config.name}: {e}")

        prnt('done loading apps')

        # from scrapers.usa.federal import add_bill
        # import uuid
        # # operatorData = get_operatorData()
        # self_node = get_self_node()

        # url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr2317.xml'
        # add_bill(url=url, log=[], update_dt=now_utc(), driver=None, driver_service=None, special=None, country=None, ref_func=None)




        # import datetime
        # time_string = "01:50:04, May 22, 2025"
        # dt = datetime.datetime.strptime(time_string, "%H:%M:%S, %B %d, %Y")
        # dt = dt.replace(tzinfo=datetime.timezone.utc)

        def custom_scrape_duty(receivedDt, func=None, opt=1):
            import pytz

            importScript = f'scrapers.usa.federal'

            import importlib
            scraperScripts = importlib.import_module(importScript) 

            to_zone = pytz.timezone('est')
            local_dt = receivedDt.astimezone(to_zone)
            today = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            dayOfWeek = today.weekday()
            prnt('receivedDt converted to region',local_dt)
            runTimes = scraperScripts.runTimes
            function_set = scraperScripts.functions
            approved_models = scraperScripts.approved_models
            function_list = []
            
            for function_dt, functions in dict(sorted(function_set.items(), key=lambda x: datetime.datetime.strptime(x[0], "%Y-%m-%d"), reverse=True)).items():
                if datetime.datetime.strptime(function_dt, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc) <= receivedDt:
                    for function in functions:
                        # runtime_window = [local_dt.hour, local_dt.hour+1] # scrapers allotted two hour window, utc - to region_time conversion may cause offset by 1 hour - this may happen if running only on even hours
                        runtime_window = [local_dt.hour]
                        # prntDebug('runtime_window',runtime_window)
                        # prntDebug("function['hour']",function['hour'])
                        if 'x' in function['hour'] or any(i in function['hour'] for i in runtime_window):
                            if 'x' in function['dayOfWeek'] or dayOfWeek in function['dayOfWeek']:
                                if 'x' in function['date'] or today in function['date']:
                                    for f in function['cmds']:
                                        if not func or func == f:
                                            function_list.append({'region_id':'usa','function_name':f, 'function':getattr(scraperScripts, f), 'timeout':runTimes[f]})
                    break

            # prnt('function_list',function_list)
            # from blockchain.models import get_scraping_order
            if opt == 1:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2'}, 'node_ids':['nSo1000','nSo2000']}
            elif opt == 2:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000']}
            elif opt == 3:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000']}
            elif opt == 4:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5','nSo6000':'127.0.0.6'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000','nSo6000']}
            elif opt == 5:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5','nSo6000':'127.0.0.6','nSo7000':'127.0.0.7'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000','nSo6000','nSo7000']}
            master_list = []
            for f in function_list:
                # scrapers, validator = get_scraping_order(chainId='1234567890', func_name=f['function_name'], dt=receivedDt)
                scrapers, validator = get_node_assignment(None, dt=receivedDt, func=f['function_name'], chainId=get_model_prefix('Blockchain')+'1234567890', scrapers_only=True, node_block_data=node_block_data, strings_only=True)
                f['scraping_order'] = scrapers
                f['validator'] = validator
                master_list.append(f)
            # prnt('master_list',master_list)
            return master_list, approved_models


        # number_of_peers = node_dict['number_of_peers']
        # relevant_nodes = node_dict['relevant_nodes']
        # node_ids = node_dict['node_ids']


        # get_node_assignment(None, dt=dt, func=func_name, chainId=chainId, scrapers_only=True, node_block_data=node_block_data, strings_only=strings_only)


        # gov = Government.objects.all().first()
        def run_me(receivedDt, opt=1, results={}):
            scraper_list, approved_models = custom_scrape_duty(receivedDt, opt=opt)
            prntn('!!!',receivedDt, 'scraper_list',scraper_list)
            
            for s in scraper_list:
                # prntDebug('s',s)
                r = json.dumps({'scrape':s['scraping_order'], 'val':s['validator']})
                prnt('r',r)
                if r in results:
                    prnt('p1')
                    results[r] += 1
                else:
                    prnt('p2')
                    results[r] = 1
            return results
            # 'scraping_order': ['nodSo44361466c4c21a74831b27204e3d5897', 'nodSo741d333ed251b5b272ed4b86767b6206'], 'validator': 'nodSo741d333ed251b5b272ed4b86767b6206'}

            prnt('-----------------------')
            prnt()


        import hashlib
        import datetime
        import random

        def get_deterministic_node_order2(func_name, dt, node_ids):
            if isinstance(dt, datetime.datetime):
                dt_str = dt.isoformat()
            elif isinstance(dt, str):
                dt_str = dt
            else:
                raise ValueError("dt must be a datetime or ISO string")

            seed_input = f"{func_name}_{dt_str}"
            seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
            seed_int = int(seed_hash, 16)

            rng = random.Random(seed_int)
            shuffled_nodes = node_ids.copy()
            rng.shuffle(shuffled_nodes)

            return shuffled_nodes
        
        def get_broadcast_map2(func_name, dt, node_ids):
            # Get the deterministic node order first
            ordered_nodes = get_deterministic_node_order(func_name, dt, node_ids)

            broadcast_map = {}

            for i, node in enumerate(ordered_nodes):
                # Assign next 2 nodes (if available)
                recipients = ordered_nodes[i+1:i+3]
                broadcast_map[node] = recipients

            return broadcast_map
        


        def run2(dt, func='test', opt=1):
            if opt == 1:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2'}, 'node_ids':['nSo1000','nSo2000']}
            elif opt == 2:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000']}
            elif opt == 3:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000']}
            elif opt == 4:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5','nSo6000':'127.0.0.6'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000','nSo6000']}
            elif opt == 5:
                node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5','nSo6000':'127.0.0.6','nSo7000':'127.0.0.7'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000','nSo6000','nSo7000']}
            
            import copy
            node_dict = copy.deepcopy(node_block_data)

            number_of_peers = node_dict['number_of_peers']
            relevant_nodes = node_dict['relevant_nodes']
            node_ids = node_dict['node_ids']
            import hashlib
            import datetime
            import random
            if isinstance(dt, datetime.datetime):
                dt_str = dt.isoformat()
            elif isinstance(dt, str):
                dt_str = dt
            else:
                raise ValueError("dt must be a datetime or ISO string")
            seed_input = f"{func}_{dt_str}"
            seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
            seed_int = int(seed_hash, 16)

            rng = random.Random(seed_int)
            shuffled_nodes = node_ids.copy()
            rng.shuffle(shuffled_nodes)

            prnt('seed_input',seed_input,'seed_hash',seed_hash,'seed_int',seed_int)
            prnt('node_ids',node_ids)
            prnt('shuffled_nodes',shuffled_nodes)
        # from datetime import datetime, timedelta

        # Start time (you can customize this)
        # current_time = now_utc()
        # current_time = round_time(dt=current_time, dir='down', amount='hour')

        # Number of hours to iterate (change as needed)
        hours_to_iterate = 1000

        # # Loop through each hour
        results1 = {}
        results2 = {}
        results3 = {}
        # for i in range(hours_to_iterate):
        #     current_time += datetime.timedelta(hours=1)
        #     # results1 = run_me(current_time, opt=1, results=results1)
        #     # results2 = run_me(current_time, opt=2, results=results2)
        #     # results3 = run_me(current_time, opt=5, results=results3)
        #     run2(current_time, opt=2)




        import hashlib
        import datetime
        import random

        # def get_deterministic_broadcast_order3(func_name, dt, node_ids, seed_node, important_nodes):
        #     if isinstance(dt, datetime.datetime):
        #         dt_str = dt.isoformat()
        #     elif isinstance(dt, str):
        #         dt_str = dt
        #     else:
        #         raise ValueError("dt must be a datetime or ISO string")

        #     seed_input = f"{func_name}_{dt_str}"
        #     seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
        #     seed_int = int(seed_hash, 16)
        #     rng = random.Random(seed_int)

        #     excluded = set([seed_node] + important_nodes)
        #     remaining_nodes = [nid for nid in node_ids if nid not in excluded]

        #     rng.shuffle(important_nodes)
        #     rng.shuffle(remaining_nodes)

        #     return [seed_node] + important_nodes + remaining_nodes

        # def get_broadcast_map3(func_name, dt, nodes, seed_node, important_nodes, loop=False):
        #     node_ids = list(nodes.keys())
        #     ordered_ids = get_deterministic_broadcast_order(func_name, dt, node_ids, seed_node, important_nodes)
        #     total = len(ordered_ids)
        #     broadcast_map = {}

        #     for i, node_id in enumerate(ordered_ids):
        #         recipients = []
        #         for j in range(1, 3):  # up to 2 recipients
        #             if loop:
        #                 recipient = ordered_ids[(i + j) % total]
        #             else:
        #                 if i + j < total:
        #                     recipient = ordered_ids[i + j]
        #                 else:
        #                     break
        #             recipients.append(nodes[recipient])
        #         broadcast_map[node_id] = recipients

        #     return broadcast_map


        def get_deterministic_broadcast_order(func_name, dt, node_ids, seed_node, important_nodes):
            if isinstance(dt, datetime.datetime):
                dt_str = dt.isoformat()
            elif isinstance(dt, str):
                dt_str = dt
            else:
                raise ValueError("dt must be a datetime or ISO string")

            seed_input = f"{func_name}_{dt_str}"
            seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
            seed_int = int(seed_hash, 16)
            rng = random.Random(seed_int)

            excluded = set([seed_node] + important_nodes)
            remaining_nodes = [nid for nid in node_ids if nid not in excluded]

            rng.shuffle(important_nodes)
            rng.shuffle(remaining_nodes)

            return [seed_node] + important_nodes + remaining_nodes

        def get_broadcast_map(func_name, dt, nodes, seed_node, important_nodes, loop=False):
            node_ids = list(nodes.keys())
            ordered_ids = get_deterministic_broadcast_order(func_name, dt, node_ids, seed_node, important_nodes)
            broadcast_map = {}
            total = len(ordered_ids)
            recipients_set = set()
            prnt('ordered_ids',ordered_ids)


            if loop:
                for i, node_id in enumerate(ordered_ids):
                    recipients = []
                    for j in range(1, 3):  # up to 2 recipients
                        if loop:
                            recipient = ordered_ids[(i + j) % total]
                        else:
                            if i + j < total:
                                recipient = ordered_ids[i + j]
                            else:
                                break
                        recipients.append(nodes[recipient])
                    broadcast_map[node_id] = recipients
            else:
                for i, node_id in enumerate(ordered_ids):
                    # prnt('i',i,'node_id',node_id)
                    recipients = []
                    count = 0
                    j = i + 1
                    while count < 2 and j < len(ordered_ids):
                        # prnt('j',j)
                        candidate = ordered_ids[j]
                        if candidate not in recipients_set:
                            recipients.append(nodes[candidate])
                            recipients_set.add(candidate)
                            # prnt('recipients',recipients)
                            count += 1
                        j += 1

                    broadcast_map[node_id] = recipients

            prntDebug('broadcast_map',broadcast_map)
            # prnt('ordered_ids',ordered_ids)
            prnt('recipients_set',recipients_set)
            prnt('loop',loop)
            # If loop is enabled, connect remaining unassigned nodes (if any)
            if loop:
                early_candidates = [
                    nid for nid in ordered_ids
                    if nid != seed_node and nid not in recipients_set
                ]
                prnt('early_candidates',early_candidates)
                for sender_id in ordered_ids:
                    if len(broadcast_map[sender_id]) < 2:
                        while early_candidates:
                            candidate = early_candidates.pop(0)
                            if candidate not in recipients_set and candidate != sender_id:
                                broadcast_map[sender_id].append(nodes[candidate])
                                recipients_set.add(candidate)
                                break

            return broadcast_map



        # import hashlib, random, datetime

        # def str_to_hash(text):
        #     return hashlib.sha256(str(text).encode('utf-8')).hexdigest()

        # def get_deterministic_broadcast_order(func_name, dt, node_ids, seed_node, important_nodes):
        #     if isinstance(dt, datetime.datetime):
        #         dt_str = dt.isoformat()
        #     else:
        #         dt_str = str(dt)

        #     seed_input = f"{func_name}_{dt_str}"
        #     seed_hash = str_to_hash(seed_input)
        #     seed_int = int(seed_hash, 16)
        #     rng = random.Random(seed_int)

        #     excluded = set([seed_node] + important_nodes)
        #     remaining_nodes = [nid for nid in node_ids if nid not in excluded]

        #     rng.shuffle(important_nodes)
        #     rng.shuffle(remaining_nodes)

        #     return [seed_node] + important_nodes + remaining_nodes

        # def get_broadcast_map(func_name, dt, nodes, seed_node, important_nodes, loop=False):
        #     node_ids = list(nodes.keys())
        #     ordered_ids = get_deterministic_broadcast_order(func_name, dt, node_ids, seed_node, important_nodes)
        #     broadcast_map = {}
        #     assigned_as_recipient = set()

        #     # Initial assignment (each node gets 0–2 unique children who haven't received yet)
        #     for i, sender in enumerate(ordered_ids):
        #         recipients = []
        #         j = i + 1
        #         while len(recipients) < 2 and j < len(ordered_ids):
        #             candidate = ordered_ids[j]
        #             if candidate not in assigned_as_recipient:
        #                 recipients.append(nodes[candidate])
        #                 assigned_as_recipient.add(candidate)
        #             j += 1
        #         broadcast_map[sender] = recipients

        #     # Loop-back: allow end nodes to send to early nodes
        #     if loop:
        #         loop_candidates = [nid for nid in ordered_ids if nid != seed_node]

        #         for sender in ordered_ids:
        #             while len(broadcast_map[sender]) < 2 and loop_candidates:
        #                 for target in loop_candidates:
        #                     if nodes[target] not in broadcast_map[sender] and target != sender:
        #                         broadcast_map[sender].append(nodes[target])
        #                         break
        #                 else:
        #                     break  # No valid loop target left

        #     return broadcast_map

        nodes = {
            "id1": "addr1",
            "id2": "addr2",
            "id3": "addr3",
            "id4": "addr4",
            "id5": "addr5",
            "id6": "addr6",
            "id7": "addr7",
            "id8": "addr8",
            "id9": "addr9",
            "id10": "addr10",
            "id11": "addr11",
        }

        seed_node = "id3"
        # important_nodes = ["id2", "id5", "id9"]
        important_nodes = []
        dt = "2025-05-22T00:00:00"

        # broadcast_map = get_broadcast_map("my_func2", dt, nodes, seed_node, important_nodes, loop=False)

        # for nid, recipients in broadcast_map.items():
        #     print(f"{nid} → {recipients}")



        # node_ids = ["A", "B", "C", "D", "E"]
        # dt = "2025-05-22T00:00:00"
        # opt = 1

        # if opt == 1:
        #     node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2'}, 'node_ids':['nSo1000','nSo2000']}
        # elif opt == 2:
        #     node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000']}
        # elif opt == 3:
        #     node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000']}
        # elif opt == 4:
        #     node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5','nSo6000':'127.0.0.6'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000','nSo6000']}
        # elif opt == 5:
        #     node_block_data = {'number_of_peers':2, 'relevant_nodes':{'nSo1000':'127.0.0.1','nSo2000':'127.0.0.2','nSo3000':'127.0.0.3','nSo4000':'127.0.0.4','nSo5000':'127.0.0.5','nSo6000':'127.0.0.6','nSo7000':'127.0.0.7'}, 'node_ids':['nSo1000','nSo2000','nSo3000','nSo4000','nSo5000','nSo6000','nSo7000']}
        


        # nodes = {
        #     "id1": "addr1",
        #     "id2": "addr2",
        #     "id3": "addr3",
        #     "id4": "addr4",
        #     "id5": "addr5"
        # }

        # dt = "2025-05-22T00:00:00"
        # result = get_broadcast_map("my_func", dt, nodes)

        # for node_id, addresses in result.items():
        #     print(f"{node_id}: {addresses}")

            
        # broadcast_map = get_broadcast_map("my_func", dt, node_ids)
        # for node, recipients in broadcast_map.items():
        #     print(f"{node} -> {recipients}")

        # prnt()
        # prnt()
        # prnt()
        # prnt('results')
        # final = {}
        # for key, value in results3.items():
        #     prnt(value, key)
        #     key = json.loads(key)
        #     if key['val'] in final:
        #         final[key['val']] += value
        #     else:
        #         final[key['val']] = value


        
        # prnt()
        # prnt()
        # prnt()
        # prnt('opt5')
        # for key, value in final.items():
        #     prnt(value, key)

        #old
        # ~:opt1
        # ~:714,nSo2000
        # ~:144,nSo1000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.637976
        # ~:opt1
        # ~:714,nSo2000
        # ~:144,nSo1000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.265459
        # ~:opt1
        # ~:714,nSo2000
        # ~:144,nSo1000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.325749

        # ~:opt5
        # ~:126,nSo5000
        # ~:125,nSo1000
        # ~:114,nSo7000
        # ~:125,nSo4000
        # ~:125,nSo2000
        # ~:118,nSo6000
        # ~:125,nSo3000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.608379
        # ~:opt5
        # ~:126,nSo5000
        # ~:125,nSo1000
        # ~:114,nSo7000
        # ~:125,nSo4000
        # ~:125,nSo2000
        # ~:118,nSo6000
        # ~:125,nSo3000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.392768
        # ~:opt5
        # ~:126,nSo5000
        # ~:125,nSo1000
        # ~:114,nSo7000
        # ~:125,nSo4000
        # ~:125,nSo2000
        # ~:118,nSo6000
        # ~:125,nSo3000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.274738
        # new
        # ~:opt1
        # ~:408,nSo2000
        # ~:450,nSo1000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.455748
        # ~:opt1
        # ~:408,nSo2000
        # ~:450,nSo1000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.151735
        # ~:opt1
        # ~:408,nSo2000
        # ~:450,nSo1000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.150241

        # ~:opt5
        # ~:115,nSo5000
        # ~:152,nSo1000
        # ~:113,nSo4000
        # ~:128,nSo6000
        # ~:110,nSo2000
        # ~:118,nSo3000
        # ~:122,nSo7000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.373211

        # ~:opt5
        # ~:115,nSo5000
        # ~:152,nSo1000
        # ~:113,nSo4000
        # ~:128,nSo6000
        # ~:110,nSo2000
        # ~:118,nSo3000
        # ~:122,nSo7000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.161385


        # ~:opt3
        # ~:157,nSo5000
        # ~:206,nSo1000
        # ~:174,nSo4000
        # ~:170,nSo3000
        # ~:151,nSo2000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.623757
        # ~:opt3
        # ~:157,nSo5000
        # ~:206,nSo1000
        # ~:174,nSo4000
        # ~:170,nSo3000
        # ~:151,nSo2000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.184956
        # ~:opt3
        # ~:157,nSo5000
        # ~:206,nSo1000
        # ~:174,nSo4000
        # ~:170,nSo3000
        # ~:151,nSo2000
        # ~:gpu_available,False
        # ~:done
        # 0:00:00.143970

        # ~:
        # ~:
        # ~:opt2
        # ~:201,nSo4000
        # ~:250,nSo1000
        # ~:200,nSo2000
        # ~:207,nSo3000
        # ~:gpu_available,False
        # ~:done
        # 0:00:02.064554

        # ~:
        # ~:opt2
        # ~:201,nSo4000
        # ~:250,nSo1000
        # ~:200,nSo2000
        # ~:207,nSo3000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.536672

        # ~:opt2
        # ~:201,nSo4000
        # ~:250,nSo1000
        # ~:200,nSo2000
        # ~:207,nSo3000
        # ~:gpu_available,False
        # ~:done
        # 0:00:01.553458
        
        # mbuu = NodeReview.objects.filter(id='nrevSo065b655705965b08f6656f0d94e10443').first()
        # prnt('mbuu',mbuu)
        # super(NodeReview, mbuu).delete()
        # prnt('deleted')
        # def test_view(request):
        # from django.http import JsonResponse
        # return JsonResponse({ "ok": True }, headers={})

        # objs = Government.objects.filter(id='govSo689ecfa95f8f72d4a7670bd5a867f724')
        # vals = Validator.objects.filter(is_valid=True, data__has_any_keys=['govSo689ecfa95f8f72d4a7670bd5a867f724']).order_by('-created')
        # # val_count += len(vals)
        # prnt('vals',vals)
        # if vals:
        #     val_map = {obj: val for val in vals for obj in val.data.keys()}
        #     prnt('val_map',val_map)
        #     for obj in objs:
        #         prnt('obj',obj)
        #         prnt('sigData_to_hash(obj)',sigData_to_hash(obj))
        #         # prnt('sigData_to_hash(obj)',sigData_to_hash(obj))
        #         val_found = False
        #         val = val_map.get(obj.id)
        #         prnt('val',val)
        #         if val and obj.id in val.data:
        #             prnt('1')
        #             prnt('val.data[obj.id]',val.data[obj.id])
        #             if val.data[obj.id] == sigData_to_hash(obj):
        #                 prnt('2')


        # # v = Validator.objects.filter(id='valSo744eb8444b1ebdd96eaf083ae75c65b2').first()
        # # prnt('v',v)
        # # if v:
        # #     prnt('x',hash_obj_id(v))
        # #     prnt('x2',hash_obj_id(v, return_data=True))
        # # # from django.db.models import Q
        # # reg = Person.objects.filter(id='perSo6312da0fa6271fddff2babe2d90a05ab').first()
        # reg = Government.objects.filter(id='govSo689ecfa95f8f72d4a7670bd5a867f724').first()
        # prnt('reg',reg)
        # if reg:
        #     prnt('x1',verify_obj_to_data(reg, reg))
        #     prnt('x2',verify_obj_to_data(reg, convert_to_dict(reg)))
        #     i = reg
        #     if i.Validator_obj:
        #         prnt('12')
        #         if i.Validator_obj.is_valid:
        #             prnt('13')
        #             if i.id in i.Validator_obj.data:
        #                 prnt('14')
        #                 prnt('x3',i.Validator_obj.data[i.id])
        #                 prnt('x4', sigData_to_hash(i))
        #                 if i.Validator_obj.data[i.id] == sigData_to_hash(i):
        #                     prnt('15')
        #     # super(Validator, reg.Validator_obj).delete()
        #     # super(Region, reg).delete()

        
        # nodes = Nodes.objects.all()
        # # if nodes:
        # #     nodeChain = Blockchain.objects.filter(genesisId=NodeChain_genesisId).first()
        # #     nodeChain.add_item_to_queue(list(nodes))

        # chain, obj, schain = find_or_create_chain_from_object(nodes[0])
        # chain.add_item_to_queue(list(nodes))

        # super_share('datSo5345685272d9e7fe08e1cf7de94fe2c5', Government.objects.all().first(), func='get_senate_persons')


        # objs = Government.objects.all()
        # prntn('objs2',objs)
        # ids = [obj.id for obj in objs] + [obj.id for obj in objs]
        # prnt('ids',ids)
        # # query = Q()
        # # for key in [obj.id for obj in objs]:
        # #     query |= Q(data__has_key=key)
        # # vals = Validator.objects.filter(is_valid=True).filter(query).order_by('-created')
        # # prnt('vals',vals)
        # vals = Validator.objects.filter(is_valid=True, data__has_any_keys=[i.id for i in objs]).order_by('-created')
        # prnt('vals',vals)
        # if not vals:
        #     vals = Validator.objects.filter(data__has_key=objs[0].id).order_by('-created')
        #     prnt('vals2',vals)

        # # val_count += len(vals)
        # if vals:
        #     val_map = {obj: val for val in vals for obj in val.data.keys()}
        #     prnt('val_map',val_map)
        #     for obj in objs:
        #         prnt('obj',obj)
        #         prnt('objed',obj.id)
        #         prnt('sigData_to_hash(obj)',sigData_to_hash(obj))
        #         val_found = False
        #         val = val_map.get(obj.id)
        #         prnt('val',val)
        #         if val and obj.id in val.data:
        #             prnt('found')
        #         #     if val.data[obj.id] == sigData_to_hash(obj):
        #         #         validated += 1
        #         #         val_found = True
        #         #         obj.Validator_obj = val
        #         #         # super(get_model(obj.object_type), obj).save()
        #         # if not val_found and getattr(obj, time_field) < dt - datetime.timedelta(hours=36):
        #         #     if obj.object_type == obj.blockchainType:
        #         #         del_chains.append(obj.id)
        #         #     if obj.id not in exclude_idens:
        #         #         exclude_idens.add(obj.id)
        #         #     obj.delete()
        #         #     delled += 1
        #         # else:
        #         #     skipped += 1
        #         #     if obj.id not in exclude_idens:
        #         #         exclude_idens.add(obj.id)
                        


        # # Build a Q object that checks if the JSONField contains any of the keys
        # query = Q()
        # for key in ids:
        #     # query |= Q(data__has_key={key: None})  # None is a placeholder, you just need the key existence
        #     query |= Q(data__has_key=key)

        # # Apply the filter
        # # results = MyModel.objects.filter(query)
        # prnt('query',query)


        # vals = Validator.objects.filter(is_valid=True).filter(query).order_by('-created')
        # prnt('vals',vals)
        # vals2 = Validator.objects.filter(query).order_by('-created')
        # prnt('vals2',vals2)


        # val_map = {obj.id: val for val in vals for obj in val.data.keys()}
        # prnt('val_map',val_map)
        # for obj in objs:
        #     prnt('obj',obj)
        #     val_found = False
        #     val = val_map.get(obj.id)
        #     prnt('val',val)
        
        # from django.db.models import Q
        # # from myapp.models import MyModel

        # objs = list(Government.objects.filter(Validator_obj=None).filter(**{f'added__lte': dt - datetime.timedelta(hours=2)}).iterator(chunk_size=500))
        # prntn('objs1',objs)

        # filter_string = f"added__lte={dt - datetime.timedelta(hours=2)})"

        # prnt('filter_string',filter_string)
        # filter_string = f"added__lte={dt - datetime.timedelta(hours=2)})"
        # filter_string = {'added__gte': datetime.strptime(dt - datetime.timedelta(hours=2), '%Y-%m-%d %H:%M:%S')}
        # prnt('filter_string2',filter_string)
        # filter_query = eval(filter_string)

        # # Apply the filter to the model
        # # result = MyModel.objects.filter(filter_query)

        # objs = Government.objects.filter(Validator_obj=None).filter(filter_query)
        # prntn('objs0',objs)


        # objs = Government.objects.filter(Validator_obj=None).filter(added__lte=dt - datetime.timedelta(hours=2))
        # prntn('objs2',objs)

        # objs = Government.objects.filter(Validator_obj=None).filter(**{f'added__lte': dt - datetime.timedelta(hours=2)}).iterator(chunk_size=500)
        # prntn('objs3',objs)
        # for o in objs:
        #     prnt('o',o)


        # objs = Government.objects.filter(Validator_obj=None).filter(**{f'added__lte': dt - datetime.timedelta(hours=2)})
        # prntn('objs4',objs)
        # x = 'regSo1bccf7b0cda6c50d49893785bf7ddf25'
        # r = Region.objects.filter(id=x).first()

        # dataPacket = get_latest_dataPacket(r.blockchainId)
        # dataPacket.add_item_to_share(r)

        # x = 'valSoba3ac6d565e749b44b301ae3cb5965c1'
        # val = Validator.objects.filter(id=x).first()
        # prnt('val',val)

        # validator_node = get_scraping_order(dt=val.added, chainId=val.blockchainId, func_name=val.func, validator_only=True, strings_only=False)
        # prnt('validator_node',validator_node)

        # g = 'genSof9af8ea375bf8afabb399ee32899b9ff'
        # b = 'bilSo0afe736dcd7b0f80c49d87b027b5ae40'
        # u = 'updSo595dd18bbcf80ac31cfb3769e398b6bd'
        # n = 'notSo321e0fefc93e3ded8f94bc3ab6fd3585'
        # t = 'btxtSoeeb4100afe274bfae91e0636f900049a'

        # x = [g,b,u,n,t]
        # for i in x:
        #     obj = get_dynamic_model(i,id=i)
        #     prntn('obj',i,obj)
        #     if obj:
        #         q = verify_obj_to_data(None, obj, user=self_node.User_obj)
        #         prnt('valid1:',q)
        #         q = verify_obj_to_data(obj, obj)
        #         prnt('valid2:',q)
        #         q = verify_obj_to_data(obj, convert_to_dict(obj))
        #         prnt('valid3:',q)

        # validator = Validator.objects.filter(id='valSo11b093a2db37c62895f574244ae791c5').first()
        # prnt('',validator)
        # validator_node_id = get_scraping_order(dt=validator.added, chainId=validator.blockchainId, func_name=validator.func, validator_only=True)
        # prnt('validator_node_id2',validator_node_id)



        # node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=validator.added, genesisId=NodeChain_genesisId)
        # node_block_data = {'node_ids':node_ids,'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}
        # validator_node_id = get_scraping_order(dt=validator.added, chainId=validator.blockchainId, func_name=validator.func, validator_only=True, node_block_data=node_block_data)
        # prnt('validator_node_id3',validator_node_id)

        # scraper_list, approved_models = get_scrape_duty(Government.objects.all().first(), validator.added)
        # prnt('scraper_list',scraper_list)

        # s = Statement.objects.filter(keyword_array__icontains='Nomination rollcall')
        # for i in s:
        #     prnt('i',i)




        # def add_worker_job(dp):
        #     # operatorData = get_operatorData()
        #     # if not 'syncingDB' in operatorData or operatorData['syncingDB'] != True:
        #         # if not exists_in_worker('broadcast', dp.id, queue_name='low'):
        #     run_at = now_utc() + datetime.timedelta(minutes=1)
        #     django_rq.get_scheduler('low').enqueue_at(run_at, dp.broadcast, timeout=120)


        # allPacket = DataPacket.objects.filter(chainId='All').first()
        # for r in Region.objects.all():
        #     allPacket.data[r.id] = sigData_to_hash(r)
        # allPacket.save()
        # add_worker_job(allPacket)


        


        # text = '''Aurora Greenway, a widow since her daughter Emma was a young girl, keeps several suitors at arm's length in River Oaks, Houston, focusing instead on her close, but controlling, relationship with Emma. Anxious to escape her mother, Emma marries callow young college professor Flap Horton over her mother's objections.

        # Despite their frequent spats and difficulty getting along with each other, Emma and Aurora have very close ties and keep in touch by telephone. Soon after the wedding, Emma gets pregnant with their first child. He is a few years old when she is again expecting another.

        # The small family moves to Iowa in order for Flap to pursue a career as an English professor. When they run into financial difficulties, Emma calls Aurora for help. Admitting she is pregnant with a third, her mother suggests she go to Colorado for an abortion.

        # When Flap gets home, as he was away overnight, Emma demands to be told if he is having an affair. He insists it is paranoia, brought on by the pregnancy hormones. While at the grocery store, Emma does not have enough money to pay for all of her groceries and meets Sam Burns, who helps pay for them.

        # Meanwhile the lonely Aurora, after her doctor discloses her real age at her birthday celebration, overcomes her repression and begins a whirlwind romance with her next-door neighbor, retired astronaut Garrett Breedlove, who is promiscuous and coarse. Simultaneously Emma and Sam strike up a friendship and quickly an affair as Sam's wife refuses to have sex with him, and she suspects Flap of infidelity.

        # Over the course of the next few years, the marriage begins to fray. Emma catches Flap flirting with one of his students on campus, so drives back to Houston immediately. There, Garrett develops cold feet about his relationship with Aurora after seeing her with her daughter and grandkids and breaks it off.

        # While Emma is gone, Flap accepts a promotion in Nebraska; she and the children return to Iowa, then they move to Nebraska. While on the campus, Emma sees the same young woman who she had seen Flap with in Iowa. Confronting her, she finds out he moved them to Nebraska so he could work with his girlfriend Janice.

        # When Emma is diagnosed with cancer, before she knows how advanced it is, her lifelong friend Patsy convinces her to explore NYC. She is there a short time when Patsy's friends there first find it strange she has never worked then it gets more uncomfortable when they hear about the cancer. Not enjoying herself, she returns home early.

        # When they discover it is terminal cancer, Aurora and Flap stay by Emma's side through her treatment and hospitalization. Garrett flies to Nebraska to be with Aurora and her family. The dying Emma shows her love for her mother by entrusting her children to Aurora's care.

        # The newly formed family, Aurora and the kids with Garrett, live together in Houston.'''
        # text2 = '''Terms of Endearment is a 1983 American family tragicomedy[3] film directed, written, and produced by James L. Brooks, adapted from Larry McMurtry's 1975 novel of the same name. It stars Debra Winger, Shirley MacLaine, Jack Nicholson, Danny DeVito, Jeff Daniels, and John Lithgow. The film covers 30 years of the relationship between Aurora Greenway (MacLaine) and her daughter Emma Greenway-Horton (Winger).

        # Terms of Endearment was theatrically released in limited theatres on November 23, 1983, and to a wider release on December 9 by Paramount Pictures. The film received critical acclaim and was a major commercial success, grossing $165 million at the box office, becoming the second-highest-grossing film of 1983 (after Return of the Jedi). At the 56th Academy Awards, the film received a leading 11 nominations, and won a leading five awards: Best Picture, Best Director, Best Actress (MacLaine), Best Adapted Screenplay, and Best Supporting Actor (Nicholson). A sequel, The Evening Star, was released in 1996.'''

        # text3 = '''James L. Brooks wrote the supporting role of Garrett Breedlove for Burt Reynolds, who turned down the role because of a verbal commitment he had made to appear in Stroker Ace. "There are no awards in Hollywood for being an idiot", Reynolds later said of the decision.[4] Harrison Ford and Paul Newman also turned down the role.[5][6]

        # The exterior shots of Aurora Greenway's home were filmed at 3060 Locke Lane, Houston, Texas. The exterior shots of locations intended to be in Des Moines, Iowa and Kearney, Nebraska were instead filmed in Lincoln, Nebraska. Many scenes were filmed on, or near, the campus of the University of Nebraska-Lincoln.[7] While filming in Lincoln, the state capital, Winger met then-governor of Nebraska Bob Kerrey; the two wound up dating for two years.[8]

        # Shirley MacLaine and Debra Winger reportedly did not get along with each other during production.[9][10][11][12] MacLaine confirmed in an interview that "it was a very tough shoot ... Chaotic...(Jim) likes working with tension on the set."[13]

        # On working with Jack Nicholson, MacLaine said, "Working with Jack Nicholson was crazy",[14] but that his spontaneity may have contributed to her performance.[15] She also said,

        # We're like old smoothies working together. You know the old smoothies they used to show whenever you went to the Ice Follies. They would have this elderly man and woman – who at that time were 40 – and they had a little bit too much weight around the waist and were moving a little slower. But they danced so elegantly and so in synch with each other that the audience just laid back and sort of sighed. That's the way it is working with Jack. We both know what the other is going to do. And we don't socialize, or anything. It's an amazing chemistry – a wonderful, wonderful feeling.[12]

        # MacLaine also confirmed in an interview with USA Today that Nicholson improvised when he put his hand down her dress in the beach scene.[16]'''

        # text4 = '''Steele's Greenville expedition took place from April 2 to 25, 1863, during the Vicksburg campaign of the American Civil War. Union forces commanded by Major General Frederick Steele occupied Greenville, Mississippi, and operated in the surrounding area, to divert Confederate attention from a more important movement made in Louisiana by Major General John A. McClernand's corps. Minor skirmishing between the two sides occurred, particularly in the early stages of the expedition. Over 1,000 slaves were freed during the operation, and large quantities of supplies and animals were destroyed or removed from the area. Along with other operations, including Grierson's Raid, Steele's Greenville expedition distracted Confederate attention from McClernand's movement. Some historians have suggested that the Greenville expedition represented the Union war policy's shifting more towards expanding the war to Confederate social and economic structures and the Confederate homefront.

        # Background
        # Main article: Vicksburg campaign
        # During early 1863, when the American Civil War was ongoing, Union Army forces commanded by Major General Ulysses S. Grant were undertaking the Vicksburg campaign against the Confederate-held city of Vicksburg, Mississippi.[1] After having repeatedly failed to maneuver out of the surrounding swamps and onto high ground near Vicksburg, Grant decided between three options: an amphibious crossing of the Mississippi River and attack of the Confederate riverfront defenses; pulling back to Memphis, Tennessee, and then making an overland drive south to Vicksburg; and moving south of Vicksburg and then crossing the Mississippi River to operate against the city. The first option risked heavy casualties and the second could be misconstrued as a retreat by the civilian population and political authorities, so Grant chose the third option.[2] In late March, Grant ordered the XIII Corps, commanded by Major General John A. McClernand, to move down the Louisiana side of the Mississippi River and then prepare to cross the river at a point south of Vicksburg.[1]

        # As part of an attempt to distract the Confederate forces at Vicksburg, who were commanded by Lieutenant General John C. Pemberton, from McClernand's movement, Grant sent the division of Major General Frederick Steele to Greenville, Mississippi, roughly 70 miles (110 km) upriver from Vicksburg.[3] Steele's instructions were to land in the Mississippi Delta, advance to Greenville, and then operate in the Deer Creek area.[4] Major General William T. Sherman, the commander of XV Corps and Steele's superior officer,[5] hoped that Steele might reach to where Deer Creek met Rolling Fork, which was the furthest Union penetration in the Steele's Bayou expedition.[6] Once there, the Union soldiers were to burn any baled cotton marked with "CSA" (for Confederate States of America), clear out any Confederate forces in the area, and burn abandoned plantations.[4] Steele was also instructed to warn civilians in the region that retaliation would be made for attacks on Union transports on the Mississippi.[7] About 5,600 soldiers of Steele's division were part of the expedition.[8] Lieutenant Colonel[9] Samuel W. Ferguson commanded the Confederate forces in the area.[10]'''

        # text5 = '''Steele's troops left the Young's Point, Louisiana,[a] area late on April 2, heading upriver via steamboats. The soldiers in the ranks did not know their destination.[12] The next morning, the boats reached Smith's Landing,[13] which was 20 miles (32 km) south of Greenville. Flooding rendered the terrain impassable in this area except on the levees,[14] and the Union soldiers learned that a large stash of cotton known to be in the area had already been burned. On either the next day[13] or April 5, the expedition reached Washington's Landing. While much of Steele's force remained in the Washington's Landing area, detachments patrolled inward, learning that the path to Deer Creek was flooded.[4] After the soldiers returned to the transports, movement was made to Greenville that evening, and the Union troops disembarked the next morning at a point about 1 mile (1.6 km) north of Greenville. Two regiments and the Union Navy tinclad steamer USS Prairie Bird were left at the landing point to guard it.[15]

        # Steele's pioneer force rebuilt a bridge near the plantation of Confederate officer Samuel G. French, and continued inland.[9][b] The Union commander learned of the presence of Ferguson's Confederates on April 6. The Union officers pushed their troops hard, hoping to overtake and capture the Confederate force. Ferguson had known of the Union presence since not long after the landing, and he sent a messenger to Major General Carter L. Stevenson at Vicksburg, asking for instructions. Stevenson detached the brigade of Brigadier General Stephen Dill Lee to the area, with orders to secure Rolling Fork and then move up the Bogue Phalia stream and strike Steele's rear. Ferguson, in turn, withdrew his troops to the Thomas plantation, which was about 20 miles (32 km) north of Rolling Fork.[16] More reinforcements were positioned at Snyder's Bluff and along the Sunflower River, and some cottonclad gunboats were shifted southwards in response to the threat. Ferguson also sent a task force to a bend on the Mississippi River with instructions to cut a levee near Black Bayou, with the intent of flooding the terrain in the area, particularly where a road in Steele's rear crossed a swamp.[17] Between the commands of Ferguson and Lee, the Confederates had about 4,300 soldiers.[18]

        # Ferguson prepared a delaying action. When, on the afternoon of April 7, Steele's column approached the Thomas plantation, Ferguson had Bledsoe's Missouri Battery and Sengstak's Alabama Battery open fire on them;[19] Ferguson's force was deployed in front of a canebrake.[17] Union forces had operated in this area before, during an expedition in February commanded by Brigadier General Stephen G. Burbridge, which had been intended to drive out Confederate troops that were harassing Union shipping.[20] Steele, in turn, deployed artillery and prepared to make an attack, but Ferguson withdrew,[21] 6 miles (9.7 km) south to the Willis plantation.[22] During the pursuit, Union troops stumbled across the body of a lynched African-American who, believing Ferguson's troops were Union forces, had requested a gun with which to kill his master and expressed intent to rape white women.[23] Steele halted the pursuit on the morning on April 8, and his troops confiscated and destroyed goods found on the plantations in the area.[24] A scouting force sent by Steele detected the presence of Lee's force,[25] and the Union general ordered a withdrawal, not wanting to fight both Confederate forces too far from Greenville. During the march back, the Union troops destroyed supplies and took horses, mules, and livestock from the surrounding area.[23] The Confederates pursued, and the Union troops skirmished with them on April 8, continuing on to the French plantation on the 9th.[26] Also on April 9, Pemberton learned from Stevenson that Union troops had landed at Greenville and that Lee had been sent to counter them; Pemberton ordered the transfer of 1,500 soldiers from Fort Pemberton to Rolling Fork to reinforce Lee and Ferguson.[27] The bridge the Union troops had built there collapsed on April 10 while a herd of cattle crossed it, leading to a delay that allowed Confederate troops to catch up to the Union column.[28] Union artillery fire held the Confederate troops at bay; after the Union forces crossed the bridge it was destroyed.[29] During the course of the expedition, Steele's troops had moved 43 miles (69 km) down Deer Creek.[28]

        # During the movements, many slaves flocked to the Union lines and followed the troops to gain their freedom.[30] Steele did not want this,[25] and encouraged them to remain on plantations; when the campaign began, he had been ordered to discourage slaves from fleeing to Union lines.[30] Unsure of what to do with the large number of followers, Steele sent a message to Sherman; when Sherman did not respond, Steele contacted Grant.[23] Grant advised Steele to encourage slaves to come to Union lines, and suggested that he should form regiments of United States Colored Troops out of male former slaves who volunteered for military services, much as Brigadier General Lorenzo Thomas had begun doing. About 500 African-Americans volunteered for the service, placed in new regiments to be led by white officers.[31]

        # April 13 saw Union troops make another sweep of the Greenville area. Ferguson had withdrawn his troops, but left behind large quantities of supplies and cattle, which the Union soldiers found and brought back to camp.[32] Shortly thereafter, Lee's command withdrew from the area.[33] On April 20, Steele sent the 3rd and 31st Missouri Infantry Regiments to the Williams Bayou area; they returned on April 22 with quantities of mules, corn, and livestock.[34] The Union troops were ordered to avoid disturbing local families who were peaceful and remained at home, but these orders were ignored. Many of the plantations in the area were burned,[35] and hard feelings against the Union forces grew among the local populace.[36] During the expedition Union forces took more than 1,000 animals, besides destroying 500,000 US bushels (18,000,000 L) of corn.[37] Journalist Franc Wilkie accompanied the expedition and estimated the damages as at least $3 million (equivalent to $60,313,000 in 2024).[38] The naval historian Myron J. Smith and the historians William L. Shea and Terrence J. Winschel say that around 1,000 slaves were freed;[37][39] the historian Timothy B. Smith cites estimates that up to 2,000 or 3,000 slaves followed Steele's column back to Greenville.[40] On April 22, Grant instructed Steele to return from the Greenville area, but a shortage of transports prevented the Union soldiers from setting off until late on April 24. The next morning, Steele's forces returned to Young's Point.[34]'''

        # text6 = '''In the words of James H. Wilson, Steele's Greenville expedition made the Union army an implement of "agricultural disorganization and distress as well as of emancipation".[31] Both Sherman and Steele believed that Union troops had gone too far in behavior that affected civilians, rather than just Confederate military targets.[35] Shea and Winschel see the expedition as demonstrating a shift in the Union's war policy.[37] In an earlier communication, Henry Halleck (who had been appointed General-in-Chief of the Union Army in July 1862) had written to Grant that he believed that there would be "no peace but that which is forced by the sword". Grant accepted the policy of carrying the war to the social and economic structures of the Confederacy. In the future, in the words of Shea and Winschel, the Union army brought "the war home to [Confederate] civilians by enforcing emancipation and seizing or destroying all items of possible military value".[41] Besides ravaging an area important to the Confederate forces at Vicksburg of supplies, the Greenville expedition also drew Confederate attention away from McClernand's more important operations in Louisiana,[42] although other operations such as Grierson's Raid also played a role.[43]

        # In late April, Union forces crossed the Mississippi River south of Vicksburg and then moved inland.[44] The Union troops defeated a Confederate force in the Battle of Port Gibson on May 1, and on May 12 won another victory in the Battle of Raymond. After the action at Raymond, Grant decided to strike a Confederate force forming at Jackson, Mississippi, and then turn west towards Vicksburg.[45] Grant's troops won a small battle at Jackson on May 14, and then defeated Pemberton's army in the climactic Battle of Champion Hill on May 16.[46] After another Confederate defeat at the Battle of Big Black River Bridge on May 17, the Siege of Vicksburg began on May 18. When the city surrendered on July 4, it was a major defeat for the Confederacy.[47]'''


        # country = Region.objects.filter(Name='USA').first()
        # statement = Statement(id='xx'+str(uuid.uuid4().hex), Content=text, PersonName='personName', DateTime=now_utc(),  Government_obj=Government.objects.first(), Country_obj=country, Region_obj=country)
        # # time.sleep(3)
        
        # # # statement.save()

        # prnt('stage 3')
        # # # # mytry(text)
        # from posts.models import get_keywords
        # prntDebugn('round 1')
        # statement = get_keywords(statement, text)
        # prnt(statement.keyword_array)
        # prntDebugn('round 2')
        # statement = get_keywords(statement, text2)
        # prnt(statement.keyword_array)
        # prntDebugn('round 3')
        # statement = get_keywords(statement, text5)
        # prnt(statement.keyword_array)
        # prntn('done xxx')
        # # prnt(statement)





        # u = Update.objects.filter(pointerId='mtgSo84fe5936db27d6c12d6f18000a164a79').first()
        # prnt('Update',u)
        # if u:
        #     u.validate()

        # x = 'govSo24ed1a3463d0a7cfacedf4ee22327584'
        # gov = Government.objects.all().first()
        # prnt('gov',gov)
        # prnt('11',gov.Validator_obj.data[gov.id])
        # prnt('sigData_to_hash(gov)',sigData_to_hash(gov))
        # if gov.Validator_obj.data[gov.id] == sigData_to_hash(gov):
        #     prnt('yes')
        # else:
        #     prnt('no')
        
        # if not has_field(gov, 'Validator_obj') or gov.Validator_obj and gov.Validator_obj.is_valid and gov.Validator_obj.data[gov.id] == sigData_to_hash(gov):



    #     	valSo84e29a0fdaa0d1b84889611a3dede0b1	March 20, 2025, 4:33 a.m.	Region	scraper	super	True	March 20, 2025, 4:40 a.m.
	# valSobc95d663e0219a01200d61ea39a3a8a2	March 20, 2025, 4:26 a.m.	Region	scraper	super	True	March 20, 2025, 4:33 a.m.
	# valSob1fc52d4eadff29f47c8d4d9048be8a2	March 18, 2025, 4:40 a.m.	Region	scraper	super	True	March 18, 2025, 4:50 a.m.
	# valSo977a9f7c01e60406f900e8c50dffbde2	March 18, 2025, 4:29 a.m.	Region	scraper	super	True	March 18, 2025, 4:34 a.m.
	# valSob8babf69130963b24698034f9282d13d	March 18, 2025, 3:48 a.m.	Region	scraper	super	True	March 18, 2025, 3:50 a.m.
	# valSo092ff24a773d3a1bb7e9c01ed07005d7	March 16, 2025, 1:17 a.m.	Region	scraper	super	True	March 16, 2025, 1:20 a.m.
	# valSo7492653f5cf35b57fa14b2a7705687cf

        # r = 'regSo65fa1c10ad23b4b7f103870a5ffe76c3'
        # region = Region.objects.filter(id=r).first()
        # prnt('region',region)
        # if region:
        #     prnt('111',verify_obj_to_data(region, region))
        #     prntn('222',verify_obj_to_data(region, convert_to_dict(region)))

        # r = 'regSoaac8133e05c1ef6f47be77b34b0f1f0a'
        # region = Region.objects.filter(id=r).first()
        # prnt('region2',region)
        # if region:
        #     prnt('111223',verify_obj_to_data(region, region))
        #     prntn('222223',verify_obj_to_data(region, convert_to_dict(region)))

        # target_data = sort_for_sign(convert_to_dict(bt))
        # iden1 = hash_obj_id(bt)
        # iden2 = hash_obj_id(convert_to_dict(bt))
        # iden3 = hash_obj_id(target_data)
        # prnt('id',bt.id)
        # prnt('iden1',iden1)
        # prnt('iden2',iden2)
        # prnt('iden3',iden3)
        # prntDebug('33-1',len(str(hash_obj_id(bt, return_data=True))))
        # prntDebug('33-2',len(str(hash_obj_id(convert_to_dict(bt), return_data=True))))
        # prntDebug('33-3',len(str(hash_obj_id(target_data, return_data=True))))

        # x1 = hash_obj_id(convert_to_dict(bt), return_data=True)
        # x2 = hash_obj_id(target_data, return_data=True)
        # if x1 == x2:
        #     prnt('match1')
        # else:
        #     for key in x1:
        #         prnt('key',key)
        #         if x1[key] == x2[key]:
        #             prnt('match2')
        #         else:
        #             prnt('npo natch')

        # prnt('stagwe2')
        # prnt('1',isinstance(x1['data'], dict))
        # prnt('12',isinstance(x1['data'], str))
        # prnt('2',isinstance(x1['data'], dict))
        # prnt('22',isinstance(x1['data'], str))

        # def find_first_difference(dict1, dict2, context=50):
        #     str1 = str(dict1)
        #     str2 = str(dict2)

        #     min_len = min(len(str1), len(str2))

        #     for i in range(min_len):
        #         if str1[i] != str2[i]:
        #             start = max(0, i - context)
        #             end = min(len(str1), i + context)
        #             context_str1 = str1[start:end]
        #             context_str2 = str2[start:end]
        #             return f"Difference at index {i}:\nDict1: ...{context_str1}...\nDict2: ...{context_str2}..."
            
        #     if len(str1) != len(str2):
        #         return f"Difference in length: Dict1 is {len(str1)} chars, Dict2 is {len(str2)} chars."

        #     return "No differences found."

        # # Example usage
        # # dict1 = {"key1": "value1", "key2": "value2", "html_key": "<html><body><p>Hello</p></body></html>"}
        # # dict2 = {"key1": "value1", "key2": "value2_modified", "html_key": "<html><body><p>Hello World</p></body></html>"}

        # prnt(find_first_difference(x1['data'], x2['data']))


        # get_signing_data(obj, extra_data=None, include_sig=False)

        # block = Block.objects.filter(id='bloSo987defd4c641c6e687c0949ae5c57223').first()
        # prnt('b',block)
        # if block:
        #     prnt('b index',block.index)
        #     prev_block = block.get_previous_block(is_validated=True)
        #     prnt('prev_block',prev_block)
        #     prnt('prev_block hash',prev_block.hash)
        #     prnt('prev_block index',prev_block.index)
        #     prnt('block.get_previous_hash()',block.get_previous_hash())
        #     prnt('block.previous_hash',block.previous_hash)



        # x = ["btxtSo2115ef7fc9c586d2ea994528dc8f1eac", "btxtSo43d062da4e83306234133023af9f71d7", "btxtSo4b98516b994c41abcc5afc32dbe4d91b", "btxtSo64288b0c5253c3adfa3efd115373cd21", "btxtSo85bea97ff8332a6102c94c57d66ed7de", "btxtSoded8bff7a31c8dcb6f6ad27f9094a99b", "valSo00af872c9232e4ec0b646307fc662843", "valSo014de035bcc30162e5ee664763596618", "valSo03f3584c85d16461e718cd4a4f3f3f25", ]

        # storedModels, not_found, not_valid = get_data(x, include_related=False, return_model=True, special_request={'exclude':{'Validator_obj':None}})
        # prntDebug(f'commit_to_chain -- storedModels:{len(storedModels)}, not_found:{len(not_found)}, not_valid:{len(not_valid)}')
        # for i in storedModels:
        #     prnt('stored',i)
        # for i in not_valid:
        #     prnt('not_valid',i)
        # prnt('not_found',not_found)
                    


        text = '''Aurora Greenway, a widow since her daughter Emma was a young girl, keeps several suitors at arm's length in River Oaks, Houston, focusing instead on her close, but controlling, relationship with Emma. Anxious to escape her mother, Emma marries callow young college professor Flap Horton over her mother's objections.

        Despite their frequent spats and difficulty getting along with each other, Emma and Aurora have very close ties and keep in touch by telephone. Soon after the wedding, Emma gets pregnant with their first child. He is a few years old when she is again expecting another.

        The small family moves to Iowa in order for Flap to pursue a career as an English professor. When they run into financial difficulties, Emma calls Aurora for help. Admitting she is pregnant with a third, her mother suggests she go to Colorado for an abortion.

        When Flap gets home, as he was away overnight, Emma demands to be told if he is having an affair. He insists it is paranoia, brought on by the pregnancy hormones. While at the grocery store, Emma does not have enough money to pay for all of her groceries and meets Sam Burns, who helps pay for them.

        Meanwhile the lonely Aurora, after her doctor discloses her real age at her birthday celebration, overcomes her repression and begins a whirlwind romance with her next-door neighbor, retired astronaut Garrett Breedlove, who is promiscuous and coarse. Simultaneously Emma and Sam strike up a friendship and quickly an affair as Sam's wife refuses to have sex with him, and she suspects Flap of infidelity.

        Over the course of the next few years, the marriage begins to fray. Emma catches Flap flirting with one of his students on campus, so drives back to Houston immediately. There, Garrett develops cold feet about his relationship with Aurora after seeing her with her daughter and grandkids and breaks it off.

        While Emma is gone, Flap accepts a promotion in Nebraska; she and the children return to Iowa, then they move to Nebraska. While on the campus, Emma sees the same young woman who she had seen Flap with in Iowa. Confronting her, she finds out he moved them to Nebraska so he could work with his girlfriend Janice.

        When Emma is diagnosed with cancer, before she knows how advanced it is, her lifelong friend Patsy convinces her to explore NYC. She is there a short time when Patsy's friends there first find it strange she has never worked then it gets more uncomfortable when they hear about the cancer. Not enjoying herself, she returns home early.

        When they discover it is terminal cancer, Aurora and Flap stay by Emma's side through her treatment and hospitalization. Garrett flies to Nebraska to be with Aurora and her family. The dying Emma shows her love for her mother by entrusting her children to Aurora's care.

        The newly formed family, Aurora and the kids with Garrett, live together in Houston.'''
        text2 = '''Terms of Endearment is a 1983 American family tragicomedy[3] film directed, written, and produced by James L. Brooks, adapted from Larry McMurtry's 1975 novel of the same name. It stars Debra Winger, Shirley MacLaine, Jack Nicholson, Danny DeVito, Jeff Daniels, and John Lithgow. The film covers 30 years of the relationship between Aurora Greenway (MacLaine) and her daughter Emma Greenway-Horton (Winger).

        Terms of Endearment was theatrically released in limited theatres on November 23, 1983, and to a wider release on December 9 by Paramount Pictures. The film received critical acclaim and was a major commercial success, grossing $165 million at the box office, becoming the second-highest-grossing film of 1983 (after Return of the Jedi). At the 56th Academy Awards, the film received a leading 11 nominations, and won a leading five awards: Best Picture, Best Director, Best Actress (MacLaine), Best Adapted Screenplay, and Best Supporting Actor (Nicholson). A sequel, The Evening Star, was released in 1996.'''

        text3 = '''James L. Brooks wrote the supporting role of Garrett Breedlove for Burt Reynolds, who turned down the role because of a verbal commitment he had made to appear in Stroker Ace. "There are no awards in Hollywood for being an idiot", Reynolds later said of the decision.[4] Harrison Ford and Paul Newman also turned down the role.[5][6]

        The exterior shots of Aurora Greenway's home were filmed at 3060 Locke Lane, Houston, Texas. The exterior shots of locations intended to be in Des Moines, Iowa and Kearney, Nebraska were instead filmed in Lincoln, Nebraska. Many scenes were filmed on, or near, the campus of the University of Nebraska-Lincoln.[7] While filming in Lincoln, the state capital, Winger met then-governor of Nebraska Bob Kerrey; the two wound up dating for two years.[8]

        Shirley MacLaine and Debra Winger reportedly did not get along with each other during production.[9][10][11][12] MacLaine confirmed in an interview that "it was a very tough shoot ... Chaotic...(Jim) likes working with tension on the set."[13]

        On working with Jack Nicholson, MacLaine said, "Working with Jack Nicholson was crazy",[14] but that his spontaneity may have contributed to her performance.[15] She also said,

        We're like old smoothies working together. You know the old smoothies they used to show whenever you went to the Ice Follies. They would have this elderly man and woman – who at that time were 40 – and they had a little bit too much weight around the waist and were moving a little slower. But they danced so elegantly and so in synch with each other that the audience just laid back and sort of sighed. That's the way it is working with Jack. We both know what the other is going to do. And we don't socialize, or anything. It's an amazing chemistry – a wonderful, wonderful feeling.[12]

        MacLaine also confirmed in an interview with USA Today that Nicholson improvised when he put his hand down her dress in the beach scene.[16]'''

        text4 = '''Steele's Greenville expedition took place from April 2 to 25, 1863, during the Vicksburg campaign of the American Civil War. Union forces commanded by Major General Frederick Steele occupied Greenville, Mississippi, and operated in the surrounding area, to divert Confederate attention from a more important movement made in Louisiana by Major General John A. McClernand's corps. Minor skirmishing between the two sides occurred, particularly in the early stages of the expedition. Over 1,000 slaves were freed during the operation, and large quantities of supplies and animals were destroyed or removed from the area. Along with other operations, including Grierson's Raid, Steele's Greenville expedition distracted Confederate attention from McClernand's movement. Some historians have suggested that the Greenville expedition represented the Union war policy's shifting more towards expanding the war to Confederate social and economic structures and the Confederate homefront.

        Background
        Main article: Vicksburg campaign
        During early 1863, when the American Civil War was ongoing, Union Army forces commanded by Major General Ulysses S. Grant were undertaking the Vicksburg campaign against the Confederate-held city of Vicksburg, Mississippi.[1] After having repeatedly failed to maneuver out of the surrounding swamps and onto high ground near Vicksburg, Grant decided between three options: an amphibious crossing of the Mississippi River and attack of the Confederate riverfront defenses; pulling back to Memphis, Tennessee, and then making an overland drive south to Vicksburg; and moving south of Vicksburg and then crossing the Mississippi River to operate against the city. The first option risked heavy casualties and the second could be misconstrued as a retreat by the civilian population and political authorities, so Grant chose the third option.[2] In late March, Grant ordered the XIII Corps, commanded by Major General John A. McClernand, to move down the Louisiana side of the Mississippi River and then prepare to cross the river at a point south of Vicksburg.[1]

        As part of an attempt to distract the Confederate forces at Vicksburg, who were commanded by Lieutenant General John C. Pemberton, from McClernand's movement, Grant sent the division of Major General Frederick Steele to Greenville, Mississippi, roughly 70 miles (110 km) upriver from Vicksburg.[3] Steele's instructions were to land in the Mississippi Delta, advance to Greenville, and then operate in the Deer Creek area.[4] Major General William T. Sherman, the commander of XV Corps and Steele's superior officer,[5] hoped that Steele might reach to where Deer Creek met Rolling Fork, which was the furthest Union penetration in the Steele's Bayou expedition.[6] Once there, the Union soldiers were to burn any baled cotton marked with "CSA" (for Confederate States of America), clear out any Confederate forces in the area, and burn abandoned plantations.[4] Steele was also instructed to warn civilians in the region that retaliation would be made for attacks on Union transports on the Mississippi.[7] About 5,600 soldiers of Steele's division were part of the expedition.[8] Lieutenant Colonel[9] Samuel W. Ferguson commanded the Confederate forces in the area.[10]'''

        text5 = '''Steele's troops left the Young's Point, Louisiana,[a] area late on April 2, heading upriver via steamboats. The soldiers in the ranks did not know their destination.[12] The next morning, the boats reached Smith's Landing,[13] which was 20 miles (32 km) south of Greenville. Flooding rendered the terrain impassable in this area except on the levees,[14] and the Union soldiers learned that a large stash of cotton known to be in the area had already been burned. On either the next day[13] or April 5, the expedition reached Washington's Landing. While much of Steele's force remained in the Washington's Landing area, detachments patrolled inward, learning that the path to Deer Creek was flooded.[4] After the soldiers returned to the transports, movement was made to Greenville that evening, and the Union troops disembarked the next morning at a point about 1 mile (1.6 km) north of Greenville. Two regiments and the Union Navy tinclad steamer USS Prairie Bird were left at the landing point to guard it.[15]

        Steele's pioneer force rebuilt a bridge near the plantation of Confederate officer Samuel G. French, and continued inland.[9][b] The Union commander learned of the presence of Ferguson's Confederates on April 6. The Union officers pushed their troops hard, hoping to overtake and capture the Confederate force. Ferguson had known of the Union presence since not long after the landing, and he sent a messenger to Major General Carter L. Stevenson at Vicksburg, asking for instructions. Stevenson detached the brigade of Brigadier General Stephen Dill Lee to the area, with orders to secure Rolling Fork and then move up the Bogue Phalia stream and strike Steele's rear. Ferguson, in turn, withdrew his troops to the Thomas plantation, which was about 20 miles (32 km) north of Rolling Fork.[16] More reinforcements were positioned at Snyder's Bluff and along the Sunflower River, and some cottonclad gunboats were shifted southwards in response to the threat. Ferguson also sent a task force to a bend on the Mississippi River with instructions to cut a levee near Black Bayou, with the intent of flooding the terrain in the area, particularly where a road in Steele's rear crossed a swamp.[17] Between the commands of Ferguson and Lee, the Confederates had about 4,300 soldiers.[18]

        Ferguson prepared a delaying action. When, on the afternoon of April 7, Steele's column approached the Thomas plantation, Ferguson had Bledsoe's Missouri Battery and Sengstak's Alabama Battery open fire on them;[19] Ferguson's force was deployed in front of a canebrake.[17] Union forces had operated in this area before, during an expedition in February commanded by Brigadier General Stephen G. Burbridge, which had been intended to drive out Confederate troops that were harassing Union shipping.[20] Steele, in turn, deployed artillery and prepared to make an attack, but Ferguson withdrew,[21] 6 miles (9.7 km) south to the Willis plantation.[22] During the pursuit, Union troops stumbled across the body of a lynched African-American who, believing Ferguson's troops were Union forces, had requested a gun with which to kill his master and expressed intent to rape white women.[23] Steele halted the pursuit on the morning on April 8, and his troops confiscated and destroyed goods found on the plantations in the area.[24] A scouting force sent by Steele detected the presence of Lee's force,[25] and the Union general ordered a withdrawal, not wanting to fight both Confederate forces too far from Greenville. During the march back, the Union troops destroyed supplies and took horses, mules, and livestock from the surrounding area.[23] The Confederates pursued, and the Union troops skirmished with them on April 8, continuing on to the French plantation on the 9th.[26] Also on April 9, Pemberton learned from Stevenson that Union troops had landed at Greenville and that Lee had been sent to counter them; Pemberton ordered the transfer of 1,500 soldiers from Fort Pemberton to Rolling Fork to reinforce Lee and Ferguson.[27] The bridge the Union troops had built there collapsed on April 10 while a herd of cattle crossed it, leading to a delay that allowed Confederate troops to catch up to the Union column.[28] Union artillery fire held the Confederate troops at bay; after the Union forces crossed the bridge it was destroyed.[29] During the course of the expedition, Steele's troops had moved 43 miles (69 km) down Deer Creek.[28]

        During the movements, many slaves flocked to the Union lines and followed the troops to gain their freedom.[30] Steele did not want this,[25] and encouraged them to remain on plantations; when the campaign began, he had been ordered to discourage slaves from fleeing to Union lines.[30] Unsure of what to do with the large number of followers, Steele sent a message to Sherman; when Sherman did not respond, Steele contacted Grant.[23] Grant advised Steele to encourage slaves to come to Union lines, and suggested that he should form regiments of United States Colored Troops out of male former slaves who volunteered for military services, much as Brigadier General Lorenzo Thomas had begun doing. About 500 African-Americans volunteered for the service, placed in new regiments to be led by white officers.[31]

        April 13 saw Union troops make another sweep of the Greenville area. Ferguson had withdrawn his troops, but left behind large quantities of supplies and cattle, which the Union soldiers found and brought back to camp.[32] Shortly thereafter, Lee's command withdrew from the area.[33] On April 20, Steele sent the 3rd and 31st Missouri Infantry Regiments to the Williams Bayou area; they returned on April 22 with quantities of mules, corn, and livestock.[34] The Union troops were ordered to avoid disturbing local families who were peaceful and remained at home, but these orders were ignored. Many of the plantations in the area were burned,[35] and hard feelings against the Union forces grew among the local populace.[36] During the expedition Union forces took more than 1,000 animals, besides destroying 500,000 US bushels (18,000,000 L) of corn.[37] Journalist Franc Wilkie accompanied the expedition and estimated the damages as at least $3 million (equivalent to $60,313,000 in 2024).[38] The naval historian Myron J. Smith and the historians William L. Shea and Terrence J. Winschel say that around 1,000 slaves were freed;[37][39] the historian Timothy B. Smith cites estimates that up to 2,000 or 3,000 slaves followed Steele's column back to Greenville.[40] On April 22, Grant instructed Steele to return from the Greenville area, but a shortage of transports prevented the Union soldiers from setting off until late on April 24. The next morning, Steele's forces returned to Young's Point.[34]'''

        text6 = '''In the words of James H. Wilson, Steele's Greenville expedition made the Union army an implement of "agricultural disorganization and distress as well as of emancipation".[31] Both Sherman and Steele believed that Union troops had gone too far in behavior that affected civilians, rather than just Confederate military targets.[35] Shea and Winschel see the expedition as demonstrating a shift in the Union's war policy.[37] In an earlier communication, Henry Halleck (who had been appointed General-in-Chief of the Union Army in July 1862) had written to Grant that he believed that there would be "no peace but that which is forced by the sword". Grant accepted the policy of carrying the war to the social and economic structures of the Confederacy. In the future, in the words of Shea and Winschel, the Union army brought "the war home to [Confederate] civilians by enforcing emancipation and seizing or destroying all items of possible military value".[41] Besides ravaging an area important to the Confederate forces at Vicksburg of supplies, the Greenville expedition also drew Confederate attention away from McClernand's more important operations in Louisiana,[42] although other operations such as Grierson's Raid also played a role.[43]

        In late April, Union forces crossed the Mississippi River south of Vicksburg and then moved inland.[44] The Union troops defeated a Confederate force in the Battle of Port Gibson on May 1, and on May 12 won another victory in the Battle of Raymond. After the action at Raymond, Grant decided to strike a Confederate force forming at Jackson, Mississippi, and then turn west towards Vicksburg.[45] Grant's troops won a small battle at Jackson on May 14, and then defeated Pemberton's army in the climactic Battle of Champion Hill on May 16.[46] After another Confederate defeat at the Battle of Big Black River Bridge on May 17, the Siege of Vicksburg began on May 18. When the city surrendered on July 4, it was a major defeat for the Confederacy.[47]'''


        # country = Region.objects.filter(Name='USA').first()
        # statement = Statement(id='xx'+str(uuid.uuid4().hex), Content=text, PersonName='personName', DateTime=now_utc(),  Government_obj=Government.objects.first(), Country_obj=country, Region_obj=country)
        # # time.sleep(3)
        
        # # # statement.save()

        # prnt('stage 3')
        # # # # mytry(text)
        # from posts.models import get_keywords
        # prntDebugn('round 1')
        # statement = get_keywords(statement, text)
        # prntDebugn('round 2')
        # statement = get_keywords(statement, text2)
        # prntDebugn('round 3')
        # statement = get_keywords(statement, text5)
        # prntn('done xxx')
        # # prnt(statement)

        # bill = '''                    AMERICAN RELIEF ACT, 2025

        #     [[Page 138 STAT. 1722]]

        #     Public Law 118-158
        #     118th Congress

        #                                     An Act


            
        #     Making further continuing appropriations for the fiscal year ending 
        #         September 30, 2025, and for other purposes. <<NOTE: Dec. 21, 
        #                             2024 -  [H.R. 10545]>> 

        #         Be it enacted by the Senate and House of Representatives of the 
        #     United States of America in Congress assembled, <<NOTE: American Relief 
        #     Act, 2025.>> 
        #     SECTION 1. SHORT TITLE.

        #         This Act may be cited as the ``American Relief Act, 2025''.
        #     SEC. 2. TABLE OF CONTENTS.

        #         The table of contents of this Act is as follows:

        #     Sec. 1. Short title.
        #     Sec. 2. Table of contents.
        #     Sec. 3. References.

        #             DIVISION A--FURTHER CONTINUING APPROPRIATIONS ACT, 2025

        #         DIVISION B--DISASTER RELIEF SUPPLEMENTAL APPROPRIATIONS ACT, 2025

        #                             DIVISION C--HEALTH

        #     Sec. 3001. Short title; table of contents.

        #                         TITLE I--PUBLIC HEALTH EXTENDERS

        #     Sec. 3101. Extension for community health centers, National Health 
        #             Service Corps, and teaching health centers that operate GME 
        #             programs.
        #     Sec. 3102. Extension of special diabetes programs.
        #     Sec. 3103. National health security extensions.

        #                             TITLE II--MEDICARE

        #     Sec. 3201. Extension of increased inpatient hospital payment adjustment 
        #             for certain low-volume hospitals.
        #     Sec. 3202. Extension of the Medicare-dependent hospital (MDH) program.
        #     Sec. 3203. Extension of add-on payments for ambulance services.
        #     Sec. 3204. Extension of funding for quality measure endorsement, input, 
        #             and selection.
        #     Sec. 3205. Extension of funding outreach and assistance for low-income 
        #             programs.
        #     Sec. 3206. Extension of the work geographic index floor.
        #     Sec. 3207. Extension of certain telehealth flexibilities.
        #     Sec. 3208. Extending acute hospital care at home waiver authorities.
        #     Sec. 3209. Extension of temporary inclusion of authorized oral antiviral 
        #             drugs as covered part D drugs.
        #     Sec. 3210. Medicare improvement fund.

        #                             TITLE III--HUMAN SERVICES

        #     Sec. 3301. Sexual risk avoidance education extension.
        #     Sec. 3302. Personal responsibility education extension.
        #     Sec. 3303. Extension of funding for family-to-family health information 
        #             centers.

        #                             TITLE IV--MEDICAID

        #     Sec. 3401. Eliminating certain disproportionate share hospital payment 
        #             cuts.

        #                 DIVISION D--EXTENSION OF AGRICULTURAL PROGRAMS

        #     Sec. 4101. Extension of agricultural programs.

        #     [[Page 138 STAT. 1723]]

        #                             DIVISION E--OTHER MATTERS

        #     Sec. 5101. Commodity futures trading commission whistleblower program.
        #     Sec. 5102. Protection of certain facilities and assets from unmanned 
        #             aircraft.
        #     Sec. 5103. Additional special assessment.
        #     Sec. 5104. National cybersecurity protection system authorization.
        #     Sec. 5105. Extension of temporary order for fentanyl-related substances.

        #     SEC. 3. <<NOTE: 1 USC 1 note.>> REFERENCES.

        #         Except as expressly provided otherwise, any reference to ``this 
        #     Act'' contained in any division of this Act shall be treated as 
        #     referring only to the provisions of that division.

        #     DIVISION A <<NOTE: Further Continuing Appropriations Act, 2025.>> --
        #     FURTHER CONTINUING APPROPRIATIONS ACT, 2025

        #         Sec. 101.  The Continuing Appropriations Act, 2025 (division A of 
        #     Public Law 118-83) is amended--
        #                 (1) by striking the date specified in section 
        #             106(3) <<NOTE: Ante, p. 1526.>> and inserting ``March 14, 
        #             2025'';
        #                 (2) in section 126 <<NOTE: Ante, p. 1529.>> to read as 
        #             follows:

        #         ``Sec. 126.  Notwithstanding section 101, amounts are provided for 
        #     `District of Columbia--Federal Payment for Emergency Planning and 
        #     Security Costs in the District of Columbia' at a rate for operations of 
        #     $90,000,000, of which not less than $50,000,000 shall be for costs 
        #     associated with the Presidential Inauguration to be held in January 
        #     2025: Provided, That such amounts may be apportioned up to the rate for 
        #     operations necessary to maintain emergency planning and security 
        #     activities.''; and
        #                 (3) by adding after section 152 the following new sections:

        #         ``Sec. 153.  Amounts made available by section 101 for `Department 
        #     of Commerce--National Oceanic and Atmospheric Administration--
        #     Procurement, Acquisition and Construction' may be apportioned up to the 
        #     rate for operations necessary to maintain the acquisition schedule for 
        #     Geostationary Earth Orbit in an amount not to exceed $625,000,000.
        #         ``Sec. 154.  Amounts made available by section 101 for `Department 
        #     of Justice--Justice Operations, Management and Accountability--Justice 
        #     Information Sharing Technology' may be apportioned up to the rate for 
        #     operations necessary to carry out proactive vulnerability detection and 
        #     penetration testing activities.
        #         ``Sec. 155.  In addition to amounts otherwise provided by section 
        #     101, there is appropriated to the Department of Justice for `Federal 
        #     Bureau of Investigation--Salaries and Expenses', $16,668,000, for an 
        #     additional amount for fiscal year 2025, to remain available until 
        #     September 30, 2026, to conduct risk reduction and modification of 
        #     National Security Systems: Provided, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.
        #         ``Sec. 156. (a) Amounts made available by section 101 to the 
        #     Department of Defense for `Procurement--Shipbuilding and Conversion, 
        #     Navy', may be apportioned up to the rate for operations necessary for 
        #     `Columbia Class Submarine (AP)' in an amount not to exceed 
        #     $5,996,130,000.
        #         ``(b) Amounts made available by section 101 to the Department of 
        #     Defense for `Procurement--Shipbuilding and Conversion, Navy' may be 
        #     apportioned up to the rate for operations necessary for `Columbia Class 
        #     Submarine' in an amount not to exceed $2,922,300,000.

        #     [[Page 138 STAT. 1724]]

        #         ``Sec. 157. (a) In addition to amounts otherwise provided by section 
        #     101, there is appropriated to the Department of Defense for 
        #     `Procurement--Shipbuilding and Conversion, Navy', $5,691,000,000, for an 
        #     additional amount for fiscal year 2025, to remain available until 
        #     September 30, 2029, for the Virginia Class Submarine program and for 
        #     workforce wage and non-executive salary improvements for other nuclear-
        #     powered vessel programs: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.
        #         ``(b) Amounts appropriated by subsection (a) may be used to 
        #     incrementally fund contract obligations for the improvement of workforce 
        #     wages and non-executive level salaries on new or existing contracts 
        #     pertaining to the Virginia Class Submarine program or to other nuclear-
        #     powered vessel programs.
        #         ``Sec. 158.  In addition to amounts otherwise provided by section 
        #     101, there is appropriated to the Department of Defense for `Operation 
        #     and Maintenance--Defense-Wide', $913,440,000, for an additional amount 
        #     for fiscal year 2025, to remain available until September 30, 2026, to 
        #     conduct risk reduction and modification of National Security Systems: 
        #     Provided, That the amount provided by this section may be transferred to 
        #     accounts under the headings `Operation and Maintenance', `Procurement', 
        #     and `Research, Development, Test and Evaluation': Provided further, That 
        #     funds transferred pursuant to the preceding proviso shall be merged with 
        #     and available for the same purpose and for the same time period as the 
        #     appropriations to which the funds are transferred: Provided further, 
        #     That any transfer authority provided herein is in addition to any other 
        #     transfer authority provided by law: Provided further, That such amount 
        #     is designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.
        #         ``Sec. 159. (a) Amounts made available by section 101 for 
        #     `Department of Energy--Atomic Energy Defense Activities--Environmental 
        #     and Other Defense Activities--Other Defense Activities' may be 
        #     apportioned up to the rate for operations necessary to sustain 
        #     specialized security activities.
        #         ``(b) <<NOTE: Notification. Deadline.>> The Director of the Office 
        #     of Management and Budget and the Secretary of Energy shall notify the 
        #     Committees on Appropriations of the House of Representatives and the 
        #     Senate not later than 3 days after each use of the authority provided in 
        #     subsection (a).

        #         ``Sec. 160.  In addition to amounts otherwise provided by section 
        #     101, there is appropriated to the Department of Energy for `Atomic 
        #     Energy Defense Activities--Environmental and Other Defense Activities--
        #     Other Defense Activities', $1,750,000, for an additional amount for 
        #     fiscal year 2025, to remain available until September 30, 2026, to 
        #     conduct risk reduction and modification of National Security Systems: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.
        #         ``Sec. 161.  <<NOTE: Applicability.>>  During the period covered by 
        #     this Act, section 10609(a) of the Northwestern New Mexico Rural Water 
        #     Projects Act (subtitle B of title X of Public Law 111-11) shall be 
        #     applied

        #     [[Page 138 STAT. 1725]]

        #     by substituting `$1,640,000,000' for `$870,000,000' and `2025' for 
        #     `2024'.

        #         ``Sec. 162.  In addition to amounts otherwise provided by section 
        #     101, there is appropriated to the Department of the Treasury for 
        #     `Departmental Offices--Office of Terrorism and Financial Intelligence--
        #     Salaries and Expenses', $908,000, for an additional amount for fiscal 
        #     year 2025, to remain available until September 30, 2026, to conduct risk 
        #     reduction and modification of National Security Systems: Provided, That 
        #     such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.
        #         ``Sec. 163.  <<NOTE: Applicability.>>  Section 302 of title III of 
        #     Public Law 108-494 shall be applied by substituting the date specified 
        #     in section 106(3) of this Act for `December 31, 2024' each place it 
        #     appears.

        #         ``Sec. 164. <<NOTE: Applicability.>>  (a) Notwithstanding section 
        #     101, section 747 of title VII of division B of Public Law 118-47 shall 
        #     be applied through the date specified in section 106(3) of this Act by--
        #                 ``(1) substituting `2024' for `2023' each place it appears;
        #                 ``(2) substituting `2025' for `2024' each place it appears;
        #                 ``(3) substituting `2026' for `2025'; and
        #                 ``(4) substituting `section 747 of division B of Public Law 
        #             118-47, as in effect on September 30, 2024' for `section 747 of 
        #             division E of Public Law 117-328' each place it appears.

        #         ``(b) <<NOTE: Effective date.>> Subsection (a) shall not take effect 
        #     until the first day of the first applicable pay period beginning on or 
        #     after January 1, 2025.

        #         ``Sec. 165. <<NOTE: Apportionment.>>   Amounts made available by 
        #     section 101 for `Department of Education--Student Aid Administration' 
        #     may be apportioned up to the rate for operations necessary to ensure the 
        #     continuation of student loan servicing activities and student aid 
        #     application and eligibility determination processes.

        #         ``Sec. 166.  During the period covered by this Act, section 123 of 
        #     division A of Public Law 118-42 and the provisions carrying the same 
        #     restriction in prior Acts making appropriations to the Department of 
        #     Defense for military construction shall not apply to unobligated 
        #     balances from prior year appropriations made available under the heading 
        #     `Department of Defense--Military Construction, Army' and such balances 
        #     may be obligated for an access road project at Arlington National 
        #     Cemetery.
        #         ``Sec. 167. (a) Notwithstanding section 101, the second proviso 
        #     under the heading `Department of Veterans Affairs--Veterans Health 
        #     Administration--Medical Services' shall not apply during the period 
        #     covered by this Act.
        #         ``(b) Notwithstanding section 101, the second proviso under the 
        #     heading `Department of Veterans Affairs--Veterans Health 
        #     Administration--Medical Community Care' shall not apply during the 
        #     period covered by this Act.
        #         ``(c) Notwithstanding section 101, the second proviso under the 
        #     heading `Department of Veterans Affairs--Veterans Health 
        #     Administration--Medical Support and Compliance' shall not apply during 
        #     the period covered by this Act.
        #         ``Sec. 168. <<NOTE: Applicability.>>  Notwithstanding section 101, 
        #     the fifth and sixth provisos under the heading `Millennium Challenge 
        #     Corporation' in division F of Public Law 118-47 shall be applied by 
        #     substituting `December 31, 2025' for `December 31, 2024' each place it 
        #     appears.

        #     [[Page 138 STAT. 1726]]

        #         ``Sec. <<NOTE: Apportionment.>> 169.  Amounts made available by 
        #     section 101 for `Department of Transportation--Federal Aviation 
        #     Administration--Operations' may be apportioned up to the rate for 
        #     operations necessary to fund mandatory pay increases and other 
        #     inflationary adjustments, to maintain and improve air traffic services, 
        #     to hire and train air traffic controllers, and to continue aviation 
        #     safety oversight, while avoiding service reductions.''.

        #         This division may be cited as the ``Further Continuing 
        #     Appropriations Act, 2025''.

        #     DIVISION B-- <<NOTE: Disaster Relief Supplemental Appropriations Act, 
        #     2025.>> DISASTER RELIEF SUPPLEMENTAL APPROPRIATIONS ACT, 2025

        #         The following sums are appropriated, out of any money in the 
        #     Treasury not otherwise appropriated, for the fiscal year ending 
        #     September 30, 2025, and for other purposes, namely:

        #                                     TITLE I

        #                             DEPARTMENT OF AGRICULTURE

        #                             AGRICULTURAL PROGRAMS

        #                     Processing, Research, and Marketing

        #                             office of the secretary

        #         For an additional amount for ``Office of the Secretary'', 
        #     $30,780,000,000, to remain available until expended, for necessary 
        #     expenses related to losses of revenue, quality or production of crops 
        #     (including milk, on-farm stored commodities, crops prevented from 
        #     planting, and harvested adulterated wine grapes), trees, bushes, and 
        #     vines, as a consequence of droughts, wildfires, hurricanes, floods, 
        #     derechos, excessive heat, tornadoes, winter storms, freeze, including a 
        #     polar vortex, smoke exposure, and excessive moisture occurring in 
        #     calendar years 2023 and 2024 under such terms and conditions as 
        #     determined by the Secretary of Agriculture (referred to in this title as 
        #     ``Secretary''): Provided, <<NOTE: Determination. Time period.>> That of 
        #     the amounts provided in this paragraph under this heading in this Act, 
        #     the Secretary shall use up to $2,000,000,000 to provide assistance to 
        #     producers of livestock, as determined by the Secretary, for losses 
        #     incurred during calendar years 2023 and 2024 due to drought, wildfires, 
        #     or floods: Provided further, <<NOTE: Determination.>> That the Secretary 
        #     may provide assistance for such losses in the form of block grants to 
        #     eligible States and territories and such assistance may include 
        #     compensation to producers, as determined by the Secretary, for timber 
        #     (including payments to non-Federal forest landowners), citrus, pecan, 
        #     and poultry (including infrastructure) losses, and for agricultural 
        #     producers who have suffered losses due to the failure of Mexico to 
        #     deliver water to the United States in accordance with the 1944 Water 
        #     Treaty: Provided further, That of the amounts provided under this 
        #     heading in this Act, the Secretary shall offer individualized technical 
        #     assistance to interested non-insured producers to help them apply for 
        #     assistance made available under this heading: Provided further, That of 
        #     the amounts made available

        #     [[Page 138 STAT. 1727]]

        #     under this paragraph under this heading in this Act, the Secretary may 
        #     use up to $30,000,000, for reimbursement for administrative and 
        #     operating expenses available for crop insurance contracts for 2022 and 
        #     2023 reinsurance years in a manner consistent with Section 771 of the 
        #     Consolidated Appropriations Act, 2023 (Public Law 117-328): Provided 
        #     further, That of the amounts made available under this paragraph under 
        #     this heading in this Act, and without regard to 44 U.S.C. 3501 et. seq., 
        #     the Secretary shall use $3,000,000 to carry out regular testing for the 
        #     purposes of verifying and validating the methodology and protocols of 
        #     the inspection of molasses at any United States ports of entry, 
        #     including whether the molasses meets each statutory requirement without 
        #     the use of additives or blending, relevant definitional explanatory 
        #     notes, and each property typical of molasses in the United States as 
        #     directed in Senate Report 118-193: Provided 
        #     further, <<NOTE: Determination.>> That at the election of a processor 
        #     eligible for a loan under section 156 of the Federal Agriculture 
        #     Improvement and Reform Act of 1996 (7 U.S.C. 7272) or a cooperative 
        #     processor of dairy, the Secretary shall make payments for losses in 2023 
        #     and 2024 to such processors (to be paid to producers, as determined by 
        #     such processors) in lieu of payments to producers and under the same 
        #     terms and conditions as payments made to processors pursuant to title I 
        #     of the Additional Supplemental Appropriations for Disaster Relief Act, 
        #     2019 (Public Law 116-20) under the heading ``Department of Agriculture--
        #     Agricultural Programs--Processing, Research and Marketing--Office of the 
        #     Secretary'', as last amended by section 791(c) of title VII of division 
        #     B of the Further Consolidated Appropriations Act, 2020 (Public Law 116-
        #     94): Provided further, That notwithstanding section 760.1503(j) of title 
        #     7, Code of Federal Regulations, in the event that a processor described 
        #     in the preceding proviso does not elect to receive payments under such 
        #     clause, the Secretary shall make direct payments to producers under this 
        #     heading in this Act: Provided further, <<NOTE: Determinations.>> That 
        #     the total amount of payments received under this paragraph under this 
        #     heading in this Act for producers who did not obtain a policy or plan of 
        #     insurance for an insurable commodity for the applicable crop year under 
        #     the Federal Crop Insurance Act (7 U.S.C. 1501 et seq.) for the crop 
        #     incurring the losses or did not file the required paperwork and pay the 
        #     service fee by the applicable State filing deadline for a noninsurable 
        #     commodity for the applicable crop year under Noninsured Crop Disaster 
        #     Assistance Program for the crop incurring the losses shall not exceed 70 
        #     percent of the loss as determined by the Secretary, except the Secretary 
        #     shall provide payments not to exceed 90 percent of the producer's 
        #     revenue losses as determined by the Secretary if the Secretary 
        #     determines a de minimis amount of a producer's revenue loss is 
        #     attributable to crops for which the producer did not insure or obtain 
        #     Noninsured Crop Disaster Assistance Program coverage: Provided 
        #     further, <<NOTE: Applicability.>> That the amount provided in this 
        #     paragraph under this heading in this Act shall be subject to the terms 
        #     and conditions set forth in the first, second, sixth, seventh, eighth, 
        #     ninth, tenth, and 12th provisos under this heading in title I of the 
        #     Disaster Relief Supplemental Appropriations Act, 2022 (division B of 
        #     Public Law 117-43), except that such ninth proviso under such heading 
        #     shall be applied by substituting ``2023 and 2024'' for ``2020 and 2021'' 
        #     and the Secretary shall apply a separate payment limit for economic 
        #     assistance payments: Provided 
        #     further, <<NOTE: Applicability. Reports.>> That not later than 120 days 
        #     after the enactment

        #     [[Page 138 STAT. 1728]]

        #     of this Act, and for each fiscal quarter thereafter until the amounts 
        #     provided under this heading in this Act are expended, the Secretary 
        #     shall report to the Committees on Appropriations of the House of 
        #     Representatives and the Senate on the implementation of any programs 
        #     provided for under this heading in this Act specifying the type, amount, 
        #     and method of such assistance by State and territory: Provided further, 
        #     That of the amounts provided in this paragraph, $10,000,000,000 shall be 
        #     made available for the Secretary to make economic assistance available 
        #     pursuant to section 2102 of this title in this Act: Provided further, 
        #     That such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #         For an additional amount for ``Office of the Secretary'', 
        #     $220,000,000, to remain available until expended, for the Secretary to 
        #     provide assistance in the form of block grants to eligible States to 
        #     provide compensation to producers for necessary expenses related to 
        #     crop, timber, and livestock losses, including on-farm infrastructure, as 
        #     a consequence of any weather event in 2023 or 2024 that a State, in its 
        #     sole discretion, determines warrants such relief: Provided, That 
        #     eligible States are those States with a net farm income for 2023 of less 
        #     than $250,000,000, as recorded in the data in the Economic Research 
        #     Service publication ``Farm Income and Wealth Statistics'' as of December 
        #     3, 2024, and fewer than eight thousand farms and an average farm size of 
        #     fewer than one thousand acres per farm, as recorded in the National 
        #     Agricultural Statistics Service publication ``Farms and Land in Farms 
        #     2023 Summary (February, 2024)'': Provided further, That the Secretary 
        #     shall work with eligible States on any necessary terms and conditions of 
        #     the block grants, fully taking in account the needs of each State: 
        #     Provided further, That any such terms and conditions may not impose 
        #     additional costs on producers: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1729]]

        #                         Office of Inspector General

        #         For an additional amount for ``Office of Inspector General'', 
        #     $7,500,000, to remain available until expended, for audits, 
        #     investigations, and other oversight of projects and activities carried 
        #     out with funds made available to the Department of Agriculture in this 
        #     Act: Provided, That such amount is designated by the Congress as being 
        #     for an emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         Agricultural Research Service

        #                             buildings and facilities

        #         For an additional amount for ``Buildings and Facilities'', 
        #     $42,500,000, to remain available until expended: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                     FARM PRODUCTION AND CONSERVATION PROGRAMS

        #                             Farm Service Agency

        #                     emergency forest restoration program

        #         For an additional amount for ``Emergency Forest Restoration 
        #     Program'', $356,535,000, to remain available until expended: Provided, 
        #     That such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                         emergency conservation program

        #         For an additional amount for ``Emergency Conservation Program'', 
        #     $828,000,000, to remain available until expended: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                     Natural Resources Conservation Service

        #                     emergency watershed protection program

        #         For an additional amount for ``Emergency Watershed Protection 
        #     Program'' for necessary expenses for the Emergency Watershed Protection 
        #     Program, $920,000,000, to remain available until expended: Provided, 
        #     That such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1730]]

        #                         RURAL DEVELOPMENT PROGRAMS

        #                 Rural Development Disaster Assistance Fund

        #         For an additional amount for the ``Rural Development Disaster 
        #     Assistance Fund'' as authorized under section 6945 of title 7, United 
        #     States Code, as amended by this Act, $362,500,000, to remain available 
        #     until expended: Provided, <<NOTE: Applicability.>> That section 6945(b) 
        #     of title 7, United States Code, shall apply to amounts provided under 
        #     this heading in this Act: Provided further, That amounts provided under 
        #     this heading in this Act may not be transferred pursuant to section 2257 
        #     of title 7, United States Code:  Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                             DOMESTIC FOOD PROGRAMS

        #                         Food and Nutrition Service

        #                         commodity assistance program

        #         For an additional amount for ``Commodity Assistance Program'' for 
        #     the emergency food assistance program as authorized by section 27(a) of 
        #     the Food and Nutrition Act of 2008 (7 U.S.C. 2036(a)) and section 
        #     204(a)(1) of the Emergency Food Assistance Act of 1983 (7 U.S.C. 
        #     7508(a)(1)), $25,000,000, to remain available until September 30, 2026: 
        #     Provided, That such funds shall be for infrastructure needs related to 
        #     the consequences of a major disaster declaration pursuant to the Robert 
        #     T. Stafford Disaster Relief and Emergency Assistance Act (42 U.S.C. 5121 
        #     et seq.) in calendar years 2023 and 2024: Provided further, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                         GENERAL PROVISIONS--THIS TITLE

        #         Sec. 2101.  Section 10101 of the Disaster Relief and Recovery 
        #     Supplemental Appropriations Act, 2008 (division B of Public Law 110-329; 
        #     7 U.S.C. 6945) is amended--
        #                 (1) in subsection (b)--
        #                         (A) in the first sentence--
        #                             (i) by striking ``for authorized activities'' 
        #                         and inserting ``, in the form of loans, grants, 
        #                         loan guarantees, or cooperative agreements, for 
        #                         any authorized activity'';
        #                             (ii) by striking ``or'' between ``President'' 
        #                         and ``the Secretary of Agriculture'' and inserting 
        #                         a comma; and
        #                             (iii) by inserting after ``the Secretary of 
        #                         Agriculture'' the following: ``, or the Governor 
        #                         of a State or Territory'';
        #                         (B) in the second sentence, inserting after ``to 
        #                     carry out the activity'', the following: ``, but shall 
        #                     not be limited to the original form of assistance, if 
        #                     any''; and
        #                         (C) by inserting after the first sentence, as so 
        #                     amended, the following: ``The cost of such direct and 
        #                     guaranteed loans, including the cost of modifying loans, 
        #                     shall be as

        #     [[Page 138 STAT. 1731]]

        #                     defined in section 502 of the Congressional Budget Act 
        #                     of 1974.''; and
        #                 (2) in subsection (c), to read as follows--

        #         ``(c) Waiver of Activity or Project Limitations.--For any activity 
        #     or project for which amounts in the Rural Development Disaster 
        #     Assistance Fund will be obligated under subsection (b)--
        #                 ``(1) the Secretary of Agriculture may waive any limits on 
        #             population, income, age, and duplication with respect to 
        #             replacement of damaged or destroyed utilities, or cost-sharing 
        #             otherwise applicable, except that, if the amounts proposed to be 
        #             obligated in connection with the disaster would exceed the 
        #             amount specified in subsection (h), the notification required by 
        #             that subsection shall include information and justification with 
        #             regard to any waivers to be granted under this subsection;
        #                 ``(2) the Secretary of Agriculture may use alternative 
        #             sources of income data provided by local, regional, State, or 
        #             Federal government sources to determine program eligibility; and
        #                 ``(3) with respect to grants authorized by 7 U.S.C. 
        #             1926(a)(19), the Secretary of Agriculture shall not require the 
        #             applicant to demonstrate that it is unable to finance the 
        #             proposed project from its own resources, or through commercial 
        #             credit at reasonable rates and terms, or other funding sources 
        #             without grant assistance.''.
        #                 (3) Amounts provided by this section are designated by the 
        #             Congress as being for an emergency requirement pursuant to 
        #             section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #             Deficit Control Act of 1985.

        #         Sec. 2102. <<NOTE: Time 
        #     periods. Determinations. Deadline. Payment.>> (a)(1) With respect to the 
        #     2024 crop year, if the Secretary determines that the expected gross 
        #     return per acre for an eligible commodity determined under paragraph (2) 
        #     is less than the expected cost of production per acre for that eligible 
        #     commodity determined under paragraph (3), the Secretary shall, not later 
        #     than 90 days after the date of enactment of this Act, make a 1-time 
        #     economic assistance payment to each producer of that eligible commodity 
        #     during that crop year.
        #                 (2) The expected gross return per acre for an eligible 
        #             commodity referred to in paragraph (1) shall be equal to--
        #                         (A) in the case of wheat, corn, grain sorghum, 
        #                     barley, oats, cotton, rice, and soybeans, the product 
        #                     obtained by multiplying--
        #                             (i) the projected average farm price for the 
        #                         applicable eligible commodity for the 2024-2025 
        #                         marketing year contained in the most recent World 
        #                         Agricultural Supply and Demand Estimates published 
        #                         before the date of enactment of this Act by the 
        #                         World Agricultural Outlook Board; and
        #                             (ii) the national average harvested yield per 
        #                         acre for the applicable eligible commodity for the 
        #                         most recent 10 crop years, as determined by the 
        #                         Secretary; and
        #                         (B) in the case of each eligible commodity not 
        #                     specified in subparagraph (A), a comparable estimate of 
        #                     gross returns, as determined by the Secretary.
        #                 (3) The expected cost of production per acre for an eligible 
        #             commodity referred to in paragraph (1) shall be equal to--

        #     [[Page 138 STAT. 1732]]

        #                         (A) in the case of wheat, corn, grain sorghum, 
        #                     barley, oats, cotton, rice, and soybeans, the total 
        #                     costs listed for the 2024 crop year with respect to the 
        #                     applicable eligible commodity contained in the most 
        #                     recent data product entitled ``national average cost-of-
        #                     production forecasts for major U.S. field crops'' 
        #                     published by the Economic Research Service; and
        #                         (B) in the case of each eligible commodity not 
        #                     specified in subparagraph (A), a comparable total 
        #                     estimated cost-of-production, as determined by the 
        #                     Secretary.
        #                 (4)(A) The amount of an economic assistance payment to a 
        #             producer for an eligible commodity under paragraph (1) shall be 
        #             equal to 26 percent of the product obtained by multiplying--
        #                             (i) the economic loss for that eligible 
        #                         commodity determined under subparagraph (B); and
        #                             (ii) the eligible acres of that eligible 
        #                         commodity on the farm determined under 
        #                         subparagraph (C).
        #                         (B) For purposes of subparagraph (A)(i), the 
        #                     economic loss for an eligible commodity shall be equal 
        #                     to the difference between--
        #                             (i) the expected cost of production per acre 
        #                         for that eligible commodity, as determined under 
        #                         paragraph (3); and
        #                             (ii) the expected gross return per acre for 
        #                         that eligible commodity, as determined under 
        #                         paragraph (2).
        #                         (C) For purposes of subparagraph (A)(ii), the 
        #                     eligible acres of an eligible commodity on a farm shall 
        #                     be equal to the sum obtained by adding--
        #                             (i) the acreage planted on the farm to that 
        #                         eligible commodity for harvest, grazing, haying, 
        #                         silage, or other similar purposes for the 2024 
        #                         crop year; and
        #                             (ii) an amount equal to 50 percent of the 
        #                         acreage on the farm that was prevented from being 
        #                         planted during the 2024 crop year to that eligible 
        #                         commodity because of drought, flood, or other 
        #                         natural disaster, or other condition beyond the 
        #                         control of the producers on the farm, as 
        #                         determined by the Secretary.
        #                         (D) For purposes of subparagraph (C)(i), the 
        #                     Secretary shall consider acreage planted to include any 
        #                     land devoted to planted acres for accepted skip-row 
        #                     planting patterns, as determined by the Secretary.
        #                         (E) If the Secretary determines there is 
        #                     insufficient data to determine the comparable estimate 
        #                     of gross returns with respect to an eligible commodity 
        #                     under paragraph (2)(B) or a comparable total estimated 
        #                     cost-of-production with respect to an eligible commodity 
        #                     under paragraph (3)(B), the Secretary shall use data 
        #                     related to a similarly situated commodity for purposes 
        #                     of determining the payment amount under this paragraph.
        #                 (5) In no case shall the amount of an economic assistance 
        #             payment to a producer for an eligible commodity under paragraph 
        #             (1) be equal to less than the product obtained by multiplying--
        #                         (A) 8 percent of the reference price for the 
        #                     eligible commodity described in section 1111(19) of the 
        #                     Agricultural Act of 2014 (7 U.S.C. 9011(19));

        #     [[Page 138 STAT. 1733]]

        #                         (B) the national average payment yield for the 
        #                     eligible commodity described in section 1111(15) of that 
        #                     Act (7 U.S.C. 9011(15)); and
        #                         (C) the number of eligible acres for the eligible 
        #                     commodity described in paragraph (4)(C).

        #         (b)(1) <<NOTE: Applicability.>> Except as provided in paragraph (2), 
        #     sections 1001, 1001A, 1001B, and 1001C of the Food Security Act of 1985 
        #     (7 U.S.C. 1308, 1308-1, 1308-2, 1308-3) shall apply with respect to 
        #     assistance provided under this section.
        #                 (2) The total amount of payments received, directly or 
        #             indirectly, by a person or legal entity (except a joint venture 
        #             or general partnership) under this section may not exceed--
        #                         (A) $125,000, if less than 75 percent of the average 
        #                     gross income of the person or legal entity for the 2020, 
        #                     2021, and 2022 tax years is derived from farming, 
        #                     ranching, or silviculture activities; and
        #                         (B) $250,000, if not less than 75 percent of the 
        #                     average gross income of the person or legal entity for 
        #                     the 2020, 2021, and 2022 tax years is derived from 
        #                     farming, ranching, or silviculture activities.
        #                 (3) The payment limitations under paragraph (2) shall be 
        #             separate from annual payment limitations under any other 
        #             program.

        #         (c) <<NOTE: Definitions.>>  In this section:
        #                 (1) The terms ``extra-long staple cotton'' and ``producer'' 
        #             have the meanings given those terms in section 1111 of the 
        #             Agricultural Act of 2014 (7 U.S.C. 9011).
        #                 (2) The term ``cotton'' means extra-long staple cotton and 
        #             upland cotton.
        #                 (3)(A) The term ``eligible commodity'' means a loan 
        #             commodity (as defined in section 1201(a) of the Agricultural Act 
        #             of 2014 (7 U.S.C. 9031(a)).
        #                         (B) The term ``eligible commodity'' does not include 
        #                     graded wool, nongraded wool, mohair, or honey.
        #                 (4) The terms ``legal entity'' and ``person'' have the 
        #             meanings given those terms in section 1001(a) of the Food 
        #             Security Act of 1985 (7 U.S.C. 1308(a)).
        #                 (5) The term ``rice'' means long grain rice and medium grain 
        #             rice.
        #                 (6) The term ``Secretary'' means the Secretary of 
        #             Agriculture.

        #         (d) Amounts provided by this section are designated by the Congress 
        #     as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #     [[Page 138 STAT. 1734]]

        #                                     TITLE II

        #                             DEPARTMENT OF COMMERCE

        #                     Economic Development Administration

        #                     economic development assistance programs

        #                         (including transfers of funds)

        #         For an additional amount for ``Economic Development Assistance 
        #     Programs'', $1,510,000,000, to remain available until expended, pursuant 
        #     to sections 209 and 703 of the Public Works and Economic Development Act 
        #     (42 U.S.C. 3149 and 3233), for economic adjustment assistance related to 
        #     flood mitigation, disaster relief, long-term recovery, and restoration 
        #     of infrastructure in areas that received a major disaster designation as 
        #     a result of hurricanes, wildfires, severe storms and flooding, 
        #     tornadoes, and other natural disasters occurring in calendar years 2023 
        #     and 2024 under the Robert T. Stafford Disaster Relief and Emergency 
        #     Assistance Act (42 U.S.C. 5121 et seq.): Provided, That within the 
        #     amount appropriated under this heading in this Act, up to 3 percent of 
        #     funds may be transferred to ``Salaries and Expenses'' for administration 
        #     and oversight activities: Provided further, That within the amount 
        #     appropriated under this heading in this Act, $10,000,000 shall be 
        #     transferred to the Delta Regional Authority (7 U.S.C. 2009aa et seq.): 
        #     Provided further, <<NOTE: Notification. Deadline.>> That the Delta 
        #     Regional Authority shall notify the Committees on Appropriations of the 
        #     House of Representatives and the Senate 15 days prior to the obligation 
        #     of the amounts made available under the preceding proviso: Provided 
        #     further, <<NOTE: Compensation.>> That the Secretary of Commerce is 
        #     authorized to appoint and fix the compensation of such temporary 
        #     personnel as may be necessary to implement the requirements under this 
        #     heading in this Act, without regard to the provisions of title 5, United 
        #     States Code, governing appointments in the competitive service: Provided 
        #     further, That within the amount appropriated under this heading in this 
        #     Act, $7,000,000 shall be transferred to ``Departmental Management--
        #     Office of Inspector General'' for carrying out investigations and audits 
        #     related to the funding provided under this heading in this Act: Provided 
        #     further, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                 National Oceanic and Atmospheric Administration

        #                     operations, research, and facilities

        #         For an additional amount for ``Operations, Research, and 
        #     Facilities'' for necessary expenses related to the consequences of 
        #     hurricanes, typhoons, flooding, wildfires, and other disasters in 
        #     calendar years 2023 and 2024, $244,000,000, to remain available until 
        #     September 30, 2026, as follows:
        #                 (1) $144,000,000 for repair and replacement of observing 
        #             assets, real property, and equipment; for marine debris 
        #             assessment and removal; and for mapping, charting, and geodesy 
        #             services; and

        #     [[Page 138 STAT. 1735]]

        #                 (2) $100,000,000 for necessary expenses related to the 
        #             consequences of tornadoes, hurricanes, typhoons, flooding, and 
        #             wildfires in calendar year 2024;

        #     Provided, <<NOTE: Spending plan. Deadline.>> That the National Oceanic 
        #     and Atmospheric Administration shall submit a spending plan to the 
        #     Committees on Appropriations of the House of Representatives and the 
        #     Senate not later than 45 days after the date of enactment of this Act: 
        #     Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                     procurement, acquisition and construction

        #         For an additional amount for ``Procurement, Acquisition and 
        #     Construction'' for necessary expenses related to the consequences of 
        #     hurricanes, typhoons, wildfires, volcanoes, and other disasters in 
        #     calendar years 2022, 2023 and 2024, $499,000,000, to remain available 
        #     until expended, as follows:
        #                 (1) $100,000,000 for repair and replacement of observing 
        #             assets, real property, and equipment; and
        #                 (2) $399,000,000 for the acquisition of hurricane hunter 
        #             aircraft and related expenses as authorized under section 11708 
        #             of division K of Public Law 117-263:

        #     Provided, <<NOTE: Spending plan. Deadline.>> That the National Oceanic 
        #     and Atmospheric Administration shall submit a spending plan to the 
        #     Committees on Appropriations of the House of Representatives and the 
        #     Senate not later than 45 days after the date of enactment of this Act: 
        #     Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         fisheries disaster assistance

        #         For an additional amount for ``Fisheries Disaster Assistance'' for 
        #     necessary expenses associated with fishery resource disaster relief as 
        #     authorized by law, $300,000,000, to remain available until expended: 
        #     Provided, <<NOTE: Evaluation.>> That notwithstanding section 
        #     312(a)(3)(A) of the Magnuson-Stevens Fishery Conservation and Management 
        #     Act (18 U.S.C. 1861a(a)(3)(A)), any request for a fishery resource 
        #     disaster determination in Tribal salmon and urchin fisheries received by 
        #     the Secretary prior to September 30, 2025, may be evaluated by the 
        #     Secretary: Provided further, That a portion of the amounts provided 
        #     under this heading in this Act shall be used to provide additional 
        #     assistance up to the historical percentage for positively determined 
        #     disasters announced in calendar year 2024 that were partially funded: 
        #     Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1736]]

        #                             DEPARTMENT OF JUSTICE

        #                         United States Marshals Service

        #                             salaries and expenses

        #         For an additional amount for ``Salaries and Expenses'', $12,000,000, 
        #     to remain available until September 30, 2027, for necessary expenses 
        #     related to the protection of the residences of the Supreme Court 
        #     Justices: Provided, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                             Federal Prison System

        #                             buildings and facilities

        #         For an additional amount for ``Buildings and Facilities'', 
        #     $64,795,500, to remain available until expended, for necessary expenses 
        #     related to the consequences of major disasters: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                                     SCIENCE

        #                 National Aeronautics and Space Administration

        #             construction and environmental compliance and restoration

        #                         (including transfer of funds)

        #         For an additional amount for ``Construction and Environmental 
        #     Compliance and Restoration'' for repair and replacement of National 
        #     Aeronautics and Space Administration facilities damaged by hurricanes, 
        #     tropical storms, typhoons, and tornadoes in calendar years 2023 and 
        #     2024, $740,200,000, to remain available until expended: Provided, That 
        #     up to 20 percent of such amount may be transferred to ``Space 
        #     Operations'' for necessary expenses related to communications facilities 
        #     and equipment, required remediation, and alternative operations caused 
        #     by Typhoon Mawar: Provided further, That except as provided in the 
        #     preceding proviso, the amounts appropriated under this heading in this 
        #     Act shall not be available for transfer under any transfer authority 
        #     provided for the National Aeronautics and Space Administration in an 
        #     appropriation Act for fiscal year 2025: Provided 
        #     further, <<NOTE: Spending plan. Deadline.>> That the National 
        #     Aeronautics and Space Administration shall submit a spending plan to the 
        #     Committees on Appropriations of the House of Representatives and the 
        #     Senate not later than 45 days after the date of enactment of this Act: 
        #     Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1737]]

        #                                     TITLE III

        #                             DEPARTMENT OF DEFENSE

        #                             OPERATION AND MAINTENANCE

        #                         Operation and Maintenance, Army

        #         For an additional amount for ``Operation and Maintenance, Army'', 
        #     $451,894,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of severe storms, 
        #     straight-line winds, tornadoes, microbursts, and hurricanes in calendar 
        #     years 2023 and 2024: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                         Operation and Maintenance, Navy

        #         For an additional amount for ``Operation and Maintenance, Navy'', 
        #     $1,454,153,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of Hurricanes Ian, 
        #     Nicole, Idalia, Helene, and Milton, Typhoon Mawar, and severe storms in 
        #     calendar year 2023: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                     Operation and Maintenance, Marine Corps

        #         For an additional amount for ``Operation and Maintenance, Marine 
        #     Corps'', $8,900,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of Hurricanes Helene and 
        #     Milton: Provided, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                     Operation and Maintenance, Air Force

        #         For an additional amount for ``Operation and Maintenance, Air 
        #     Force'', $912,778,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of Hurricanes Helene and 
        #     Milton and Typhoon Mawar: Provided, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #     [[Page 138 STAT. 1738]]

        #                     Operation and Maintenance, Space Force

        #         For an additional amount for ``Operation and Maintenance, Space 
        #     Force'', $90,230,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of Hurricanes Helene and 
        #     Milton and Typhoon Mawar: Provided, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                     Operation and Maintenance, Defense-Wide

        #         For an additional amount for ``Operation and Maintenance, Defense-
        #     Wide'', $1,208,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of Hurricanes Helene and 
        #     Milton: Provided, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                     Operation and Maintenance, Army Reserve

        #         For an additional amount for ``Operation and Maintenance, Army 
        #     Reserve'', $19,594,000, to remain available until September 30, 2025, 
        #     for necessary expenses related to the consequences of Hurricanes Helene 
        #     and Milton and microbursts in calendar year 2024: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                 Operation and Maintenance, Air Force Reserve

        #         For an additional amount for ``Operation and Maintenance, Air Force 
        #     Reserve'', $1,319,000, to remain available until September 30, 2025, for 
        #     necessary expenses related to the consequences of Hurricanes Helene and 
        #     Milton and Typhoon Mawar: Provided, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                 Operation and Maintenance, Army National Guard

        #         For an additional amount for ``Operation and Maintenance, Army 
        #     National Guard'', $26,065,000, to remain available until September 30, 
        #     2025, for necessary expenses related to the consequences of Hurricanes 
        #     Helene and Milton, Typhoon Mawar, and severe storms in calendar years 
        #     2023 and 2024: Provided, That such amount is designated by the Congress 
        #     as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                 Operation and Maintenance, Air National Guard

        #         For an additional amount for ``Operation and Maintenance, Air 
        #     National Guard'', $2,209,000, to remain available until September 30, 
        #     2025, for necessary expenses related to the consequences of Hurricane 
        #     Helene and Typhoon Mawar: Provided, That such amount is designated by 
        #     the Congress as being for an emergency

        #     [[Page 138 STAT. 1739]]

        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                                 PROCUREMENT

        #                         Procurement of Ammunition, Army

        #         For an additional amount for ``Procurement of Ammunition, Army'', 
        #     $125,100,000, to remain available until September 30, 2027, for 
        #     necessary expenses related to the consequences of Hurricane Helene: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         Other Procurement, Air Force

        #         For an additional amount for ``Other Procurement, Air Force'', 
        #     $129,722,000, to remain available until September 30, 2027, for 
        #     necessary expenses related to the consequences of Typhoon Mawar: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                             Procurement, Space Force

        #         For an additional amount for ``Procurement, Space Force'', 
        #     $37,994,000, to remain available until September 30, 2027, for necessary 
        #     expenses related to the consequences of Typhoon Mawar: Provided, That 
        #     such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                 RESEARCH, DEVELOPMENT, TEST AND EVALUATION

        #                 Research, Development, Test and Evaluation, Army

        #         For an additional amount for ``Research, Development, Test and 
        #     Evaluation, Army'', $41,400,000, to remain available until September 30, 
        #     2026, for necessary expenses related to the consequences of severe 
        #     storms and wave overwash: Provided, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #             Research, Development, Test and Evaluation, Air Force

        #         For an additional amount for ``Research, Development, Test and 
        #     Evaluation, Air Force'', $69,278,000, to remain available until 
        #     September 30, 2026, for necessary expenses related to the consequences 
        #     of Typhoon Mawar: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #     [[Page 138 STAT. 1740]]

        #                     OTHER DEPARTMENT OF DEFENSE PROGRAMS

        #                             Defense Health Program

        #         For an additional amount for ``Defense Health Program'', 
        #     $17,362,000, to remain available until September 30, 2025, for necessary 
        #     expenses related to the consequences of Hurricanes Helene and Milton: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                                     TITLE IV

        #                             CORPS OF ENGINEERS--CIVIL

        #                             DEPARTMENT OF THE ARMY

        #                             Corps of Engineers--Civil

        #                                 investigations

        #         For an additional amount for ``Investigations'', $20,000,000, to 
        #     remain available until expended, for necessary expenses related to the 
        #     completion, or initiation and completion, of flood and storm damage 
        #     reduction, including shore protection, studies that are currently 
        #     authorized, to reduce risks from future floods and hurricanes, at full 
        #     Federal expense: Provided, That amounts made available under this 
        #     heading in this Act shall be for high-priority studies of projects in 
        #     States and insular areas with a major disaster, including for glacial 
        #     lake outbursts, in calendar year 2022, 2023, or 2024: Provided 
        #     further, <<NOTE: Deadlines. Work plan. List. Costs. Schedule.>> That not 
        #     later than 60 days after the date of enactment of this Act and not less 
        #     than three business days prior to public release, the Chief of Engineers 
        #     shall submit directly to the Committees on Appropriations of the House 
        #     of Representatives and the Senate a detailed work plan for the funds 
        #     provided under this heading in this Act, including a list of study 
        #     locations, new studies selected to be initiated, the total cost for each 
        #     study selected for funding, the remaining cost for each ongoing study 
        #     selected for funding, and a schedule by fiscal year of the proposed use 
        #     of such funds: Provided further, That the Secretary of the Army shall 
        #     not deviate from the work plan, once the plan has been submitted to such 
        #     Committees: Provided further, That funds included in a submitted work 
        #     plan shall be deemed allocated to specific projects and subject to the 
        #     reprogramming requirements specified in section 101(6) of the Energy and 
        #     Water Development and Related Agencies Appropriations Act, 2024: 
        #     Provided further, That beginning <<NOTE: Time period. Reports.>> not 
        #     later than 60 days after the date of enactment of this Act and until all 
        #     amounts provided under this heading in this Act have been expended, the 
        #     Assistant Secretary of the Army for Civil Works shall provide a 
        #     quarterly report directly to such Committees detailing the allocation, 
        #     obligation, and expenditure of the funds provided under this heading in 
        #     this Act: Provided further, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #     [[Page 138 STAT. 1741]]

        #                                 construction

        #         For an additional amount for ``Construction'', $700,000,000, to 
        #     remain available until expended, for necessary expenses to address 
        #     emergency situations at Corps of Engineers projects, construct Corps of 
        #     Engineers projects, and rehabilitate and repair damages caused by 
        #     natural disasters to Corps of Engineers projects: Provided, That of the 
        #     amount provided under this heading in this Act, $100,000,000 shall be 
        #     used for continuing authorities projects to reduce the risk of flooding 
        #     and storm damage, notwithstanding project number or program cost 
        #     limitations: Provided further, That of the amount provided under this 
        #     heading in this Act, $300,000,000 shall be to complete, or initiate and 
        #     complete, without regard to new start or new investment decision 
        #     considerations, a useful increment of work for water-related 
        #     environmental infrastructure assistance in States and insular areas that 
        #     were impacted by disasters occurring in or prior to calendar year 2024: 
        #     Provided further, That of the amount provided under this heading in this 
        #     Act, $300,000,000 shall be for projects that have previously received 
        #     funds under this heading in chapter 4 of title X of the Disaster Relief 
        #     Appropriations Act, 2013 (division A of Public Law 113-2), title IV of 
        #     division B of the Bipartisan Budget Act of 2018 (Public Law 115-123), or 
        #     title IV of the Disaster Relief Supplemental Appropriations Act, 2022 
        #     (division B of Public Law 117-43), and for which non-Federal interests 
        #     have entered into binding agreements with the Secretary as of the date 
        #     of enactment of this Act: Provided further, That each project receiving 
        #     funds pursuant to the preceding proviso shall be subject to the terms 
        #     and conditions of such chapter 4 of title X of the Disaster Relief 
        #     Appropriations Act, 2013 (division A of Public Law 113-2), title IV of 
        #     division B of the Bipartisan Budget Act of 2018 (Public Law 115-123), or 
        #     title IV of the Disaster Relief Supplemental Appropriations Act, 2022 
        #     (division B of Public Law 117-43), and as specifically modified by 
        #     section 111 of the Energy and Water Development and Related Agencies 
        #     Appropriations Act, 2024 (division D of Public Law 118-42), as 
        #     applicable: Provided further, That of the amount provided under this 
        #     heading in this Act, such sums as are necessary to cover the Federal 
        #     share of eligible construction costs for coastal harbors and channels, 
        #     and for inland harbors eligible to be derived from the Harbor 
        #     Maintenance Trust Fund under section 101 or section 104 of the Water 
        #     Resources and Development Act of 2020 shall be derived from the general 
        #     fund of the Treasury: Provided further, That for projects receiving 
        #     funding under this heading in this Act, the limitation concerning total 
        #     project costs in section 902 of the Water Resources Development Act of 
        #     1986 (Public Law 99-662) shall not apply to funds provided under this 
        #     heading in this Act: Provided further, That for <<NOTE: Time 
        #     period.>> any projects using funding provided under this heading in this 
        #     Act, the non-Federal cash contribution for projects shall be financed in 
        #     accordance with the provisions of section 103(k) of Public Law 99-662 
        #     over a period of 30 years from the date of completion of the project, 
        #     separable element, or useful increment: Provided further, 
        #     That <<NOTE: Contracts.>>  any projects initiated using funds provided 
        #     under this heading in this Act shall be initiated only after non-Federal 
        #     interests have entered into binding agreements with the Secretary 
        #     requiring, where applicable, the non-Federal interests to pay 100 
        #     percent of the operation, maintenance, repair, replacement, and 
        #     rehabilitation costs of the project and to hold and save

        #     [[Page 138 STAT. 1742]]

        #     the United States free from damages due to the construction or operation 
        #     and maintenance of the project, except for damages due to the fault or 
        #     negligence of the United States or its contractors: Provided 
        #     further, <<NOTE: Deadlines. Work plan. Project costs. Schedule. List.>>  
        #     That not later than 60 days after the date of enactment of this Act and 
        #     not less than three business days prior to public release, the Chief of 
        #     Engineers shall submit directly to the Committees on Appropriations of 
        #     the House of Representatives and the Senate a detailed work plan for the 
        #     funds provided under this heading in this Act, including a list of 
        #     project locations, the total cost for all projects, and a schedule by 
        #     fiscal year of proposed use of such funds: Provided further, That the 
        #     Secretary shall not deviate from the work plan, once the plan has been 
        #     submitted to such Committees: Provided further, That funds included in a 
        #     submitted work plan shall be deemed allocated to specific projects and 
        #     subject to the reprogramming requirements specified in section 101(7) of 
        #     the Energy and Water Development and Related Agencies Appropriations 
        #     Act, 2024: Provided further, <<NOTE: Time period. Reports.>>  That 
        #     beginning not later than 60 days after the date of enactment of this Act 
        #     and until all amounts provided under this heading in this Act have been 
        #     expended, the Assistant Secretary of the Army for Civil Works shall 
        #     provide a quarterly report directly to such Committees detailing the 
        #     allocation, obligation, and expenditure of the funds provided under this 
        #     heading in this Act: Provided further, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                         mississippi river and tributaries

        #         For an additional amount for ``Mississippi River and Tributaries'', 
        #     $50,000,000, to remain available until expended, for necessary expenses 
        #     to address emergency situations at Corps of Engineers projects, and to 
        #     construct, and rehabilitate and repair damages to Corps of Engineers 
        #     projects, caused by natural disasters: Provided, <<NOTE: Time 
        #     period. Reports.>> That beginning not later than 60 days after the date 
        #     of enactment of this Act and until all amounts provided under this 
        #     heading in this Act have been expended, the Assistant Secretary of the 
        #     Army for Civil Works shall provide a quarterly report directly to the 
        #     Committees on Appropriations of the House of Representatives and the 
        #     Senate detailing the allocation, obligation, and expenditure of the 
        #     funds provided under this heading in this Act: Provided further, That 
        #     such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                     flood control and coastal emergencies

        #         For an additional amount for ``Flood Control and Coastal 
        #     Emergencies'', as authorized by section 5 of the Act of August 18, 1941 
        #     (33 U.S.C. 701n), $745,000,000, to remain available until expended, for 
        #     necessary expenses to prepare for flood, hurricane, and other natural 
        #     disasters and support emergency operations, repairs, and other 
        #     activities in response to such disasters, as authorized by law: 
        #     Provided, That funding provided under this heading in this Act utilized 
        #     to repair authorized shore protection projects shall restore such 
        #     projects to their full project profile at full Federal expense: Provided 
        #     further, <<NOTE: Time period. Reports.>> That beginning not later than 
        #     60 days

        #     [[Page 138 STAT. 1743]]

        #     after the date of enactment of this Act and until all amounts provided 
        #     under this heading in this Act have been expended, the Chief of 
        #     Engineers shall provide a quarterly report directly to the Committees on 
        #     Appropriations of the House of Representatives and the Senate detailing 
        #     the allocation, obligation, and expenditure of the funds provided under 
        #     this heading in this Act: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                         DEPARTMENT OF THE INTERIOR

        #                             Bureau of Reclamation

        #                         water and related resources

        #         For an additional amount for ``Water and Related Resources'', 
        #     $74,464,000, to remain available until expended, of which $27,930,000 
        #     shall be for necessary expenses related to the consequences of natural 
        #     disasters that occurring in or prior to calendar year 2024: Provided, 
        #     That $46,534,000 shall be available for deposit into the Aging 
        #     Infrastructure Account established by section 9603(d)(1) of the Omnibus 
        #     Public Land Management Act of 2009 (43 U.S.C. 510b(d)(1)), and shall be 
        #     made available for reserved or transferred works that have suffered a 
        #     critical failure, in accordance with section 40901(2)(A) of division D 
        #     of Public Law 117-58: Provided further, That such amount is designated 
        #     by the Congress as being for an emergency requirement pursuant to 
        #     section 251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit 
        #     Control Act of 1985.

        #                             DEPARTMENT OF ENERGY

        #                                 ENERGY PROGRAMS

        #                         Strategic Petroleum Reserve

        #         For an additional amount for ``Strategic Petroleum Reserve'', 
        #     $60,000,000, to remain available until expended, for necessary expenses 
        #     related to damages caused by natural disasters: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                         ATOMIC ENERGY DEFENSE ACTIVITIES

        #                     NATIONAL NUCLEAR SECURITY ADMINISTRATION

        #                             Weapons Activities

        #         For an additional amount for ``Weapons Activities'', $1,884,000, to 
        #     remain available until expended, for necessary expenses related to 
        #     damages caused by Hurricanes Helene and Milton: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1744]]

        #                 ENVIRONMENTAL AND OTHER DEFENSE ACTIVITIES

        #                         Defense Environmental Cleanup

        #         For an additional amount for ``Defense Environmental Cleanup'', 
        #     $2,415,000, to remain available until expended, for necessary expenses 
        #     related to damages caused by Hurricanes Helene and Milton: Provided, 
        #     That such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                                     TITLE V

        #                                 THE JUDICIARY

        #                     Supreme Court of the United States

        #                             salaries and expenses

        #         For an additional amount for ``Salaries and Expenses'', $13,597,000, 
        #     to remain available until expended, for protection of the residences of 
        #     the Supreme Court Justices: Provided, That such amount is designated by 
        #     the Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                             INDEPENDENT AGENCIES

        #                         Small Business Administration

        #                         disaster loans program account

        #                         (including transfer of funds)

        #         For an additional amount for ``Disaster Loans Program Account'' for 
        #     the cost of direct loans authorized by section 7(b) of the Small 
        #     Business Act, $2,249,000,000, to remain available until expended, of 
        #     which $50,000,000 shall be transferred to ``Small Business 
        #     Administration--Office of Inspector General'' for audits and reviews of 
        #     disaster loans and the disaster loans programs, and of which 
        #     $613,000,000 may be transferred to ``Small Business Administration--
        #     Salaries and Expenses'' for administrative expenses to carry out the 
        #     disaster loan program authorized by section 7(b) of the Small Business 
        #     Act: Provided, That such amount is designated by the Congress as being 
        #     for an emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1745]]

        #                                     TITLE VI

        #                         DEPARTMENT OF HOMELAND SECURITY

        #                     SECURITY, ENFORCEMENT, AND INVESTIGATIONS

        #                                 Coast Guard

        #                             operations and support

        #         For an additional amount for ``Operations and Support'', 
        #     $102,500,000, to remain available until September 30, 2027, for 
        #     necessary expenses related to the consequences of the Francis Scott Key 
        #     Bridge collapse and other disasters, including for minor repairs, 
        #     maintenance, and environmental remediation costs: 
        #     Provided, <<NOTE: Expenditure plan. Time period. Updates.>>  That the 
        #     Commandant of the Coast Guard shall provide to the Committees on 
        #     Appropriations of the House of Representatives and the Senate an 
        #     expenditure plan and quarterly updates for the expenditure of such 
        #     funds: Provided further, That such amount is designated by the Congress 
        #     as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                 procurement, construction, and improvements

        #         For an additional amount for ``Procurement, Construction, and 
        #     Improvements'', $210,200,000, to remain available until September 30, 
        #     2029, for necessary expenses related to the consequences of disasters: 
        #     Provided, <<NOTE: Expenditure plan. Time period. Updates.>>  That the 
        #     Commandant of the Coast Guard shall provide to the Committees on 
        #     Appropriations of the House of Representatives and the Senate an 
        #     expenditure plan and quarterly updates for the expenditure of such 
        #     funds: Provided further, That such amount is designated by the Congress 
        #     as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                 PROTECTION, PREPAREDNESS, RESPONSE, AND RECOVERY

        #                     Federal Emergency Management Agency

        #                             disaster relief fund

        #                         (including transfer of funds)

        #         For an additional amount for ``Disaster Relief Fund'', 
        #     $29,000,000,000, to remain available until expended, of which 
        #     $28,000,000,000 shall be for major disasters declared pursuant to the 
        #     Robert T. Stafford Disaster Relief and Emergency Assistance Act (42 
        #     U.S.C. 5121 et seq.): Provided, That $4,000,000 shall be transferred to 
        #     ``Office of Inspector General--Operations and Support'' for audits and 
        #     investigations funded under ``Federal Emergency Management Agency--
        #     Disaster Relief Fund'':  Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1746]]

        #                 hermit's peak/calf canyon fire assistance account

        #                         (including transfer of funds)

        #         For an additional amount for ``Hermit's Peak/Calf Canyon Fire 
        #     Assistance Account'', $1,500,000,000, to remain available until 
        #     expended: Provided, That $1,000,000 shall be transferred to ``Office of 
        #     Inspector General--Operations and Support'' for oversight of activities 
        #     authorized by the Hermit's Peak/Calf Canyon Fire Assistance Act: 
        #     Provided further, <<NOTE: Reports.>>  That the amounts provided under 
        #     this heading in this Act shall be subject to the reporting requirement 
        #     in the third proviso of section 136 of the Continuing Appropriations 
        #     Act, 2023 (division A of Public Law 117-180): Provided further, That 
        #     amounts provided under this heading in this Act shall be subject to the 
        #     same authorities and conditions as if such amounts were provided by 
        #     title III of the Department of Homeland Security Appropriations Act, 
        #     2024 (division C of Public Law 118-47): Provided further, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                 RESEARCH, DEVELOPMENT, TRAINING, AND SERVICES

        #                     Federal Law Enforcement Training Centers

        #                 procurement, construction, and improvements

        #         For an additional amount for ``Procurement, Construction, and 
        #     Improvements'', $14,020,000, to remain available until September 30, 
        #     2029, for necessary expenses relating to the consequences of disasters: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                                     TITLE VII

        #                         DEPARTMENT OF THE INTERIOR

        #                             Bureau of Land Management

        #                         management of lands and resources

        #         For an additional amount for ``Management of Lands and Resources'', 
        #     $58,115,000, to remain available until expended, for necessary expenses 
        #     related to the consequences of natural disasters occurring in and prior 
        #     to calendar year 2024: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                     United States Fish And Wildlife Service

        #                                 construction

        #         For an additional amount for ``Construction'', $500,000,000, to 
        #     remain available until expended, for necessary expenses related

        #     [[Page 138 STAT. 1747]]

        #     to the consequences of natural disasters occurring in and prior to 
        #     calendar year 2024: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                             National Park Service

        #                         historic preservation fund

        #         For an additional amount for ``Historic Preservation Fund'', 
        #     $50,000,000, to remain available until expended, for necessary expenses 
        #     related to the consequences of natural disasters occurring in and prior 
        #     to calendar year 2024, including costs to States, Tribes, and 
        #     territories necessary to complete compliance activities required by 
        #     section 306108 of title 54, United States Code, and costs needed to 
        #     administer the program: Provided, That funds appropriated under this 
        #     heading in this Act shall be used for historic and cultural resource 
        #     preservation work that meets the Secretary of the Interior's Standards 
        #     and Guidelines as published in the Federal Register (Vol. 48, No. 190, 
        #     September 29, 1983), to include Reconstruction of National Register 
        #     listed or eligible sites: Provided further, That grants using funds 
        #     appropriated under this heading in this Act shall only be available for 
        #     areas that have received a major disaster declaration pursuant to the 
        #     Robert T. Stafford Disaster Relief and Emergency Assistance Act (42 
        #     U.S.C. 5121 et seq.): Provided further, That such grants shall not be 
        #     subject to a non-Federal matching requirement: Provided further, That 
        #     such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                                 construction

        #         For an additional amount for ``Construction'', $2,262,871,000, to 
        #     remain available until expended, for necessary expenses related to the 
        #     consequences of disasters, including hurricanes, tropical storms, 
        #     tornadoes, and other severe storms, wildfire, fire, and flooding 
        #     occurring in and prior to calendar year 2024: Provided, That such amount 
        #     is designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                         United States Geological Survey

        #                     surveys, investigations, and research

        #         For an additional amount for ``Surveys, Investigations, and 
        #     Research'', $2,743,000, to remain available until expended, for 
        #     necessary expenses related to the consequences of natural disasters 
        #     occurring in and prior to calendar year 2024: Provided, That such amount 
        #     is designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1748]]

        #                                 Indian Affairs

        #                             Bureau of Indian Affairs

        #                         operation of indian programs

        #         For an additional amount for ``Operation of Indian Programs'', 
        #     $17,765,000, to remain available until expended, for necessary expenses 
        #     related to the consequences of natural disasters occurring in and prior 
        #     to calendar year 2024: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                         Bureau of Indian Education

        #                             education construction

        #         For an additional amount for ``Education Construction'', 
        #     $153,000,000, to remain available until expended, for necessary expenses 
        #     related to the consequences of natural disasters occurring in and prior 
        #     to calendar year 2024: Provided, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                         Office of Inspector General

        #                             salaries and expenses

        #         For an additional amount for ``Salaries and Expenses'', $8,000,000, 
        #     to remain available until expended, for oversight of the Department of 
        #     the Interior activities funded by this Act: Provided, That such amount 
        #     is designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                         ENVIRONMENTAL PROTECTION AGENCY

        #             Leaking Underground Storage Tank Trust Fund Program

        #         For an additional amount for ``Leaking Underground Storage Tank 
        #     Trust Fund Program'', $17,000,000, to remain available until expended, 
        #     for necessary expenses related to the consequences of Hurricanes Helene 
        #     and Hilary: Provided, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                     State and Tribal Assistance Grants

        #         For an additional amount for ``State and Tribal Assistance Grants'', 
        #     $3,000,000,000 to remain available until expended, of which 
        #     $1,230,000,000 shall be for capitalization grants for the Clean Water 
        #     State Revolving Funds under title VI of the Federal Water Pollution 
        #     Control Act, and of which $1,770,000,000 shall be for capitalization 
        #     grants under section 1452 of the Safe Drinking Water Act: Provided, That 
        #     notwithstanding section 604(a) of the Federal

        #     [[Page 138 STAT. 1749]]

        #     Water Pollution Control Act and section 1452(a)(1)(D) of the Safe 
        #     Drinking Water Act, funds appropriated under this paragraph in this Act 
        #     shall be provided to States or territories in EPA Regions 3, 4, and 9 in 
        #     amounts determined by the Administrator of the Environmental Protection 
        #     Agency for wastewater treatment works and drinking water facilities 
        #     impacted by Hurricanes Helene and Milton and Hawaii wildfires: Provided 
        #     further, That notwithstanding the requirements of section 603(i) of the 
        #     Federal Water Pollution Control Act and section 1452(d) of the Safe 
        #     Drinking Water Act, for the funds appropriated under this paragraph in 
        #     this Act, each State shall use not less than 30 percent of the amount of 
        #     its capitalization grants to provide additional subsidization to 
        #     eligible recipients in the form of forgiveness of principal, negative 
        #     interest loans or grants, or any combination of these: Provided further, 
        #     That the funds appropriated under this paragraph in this Act shall be 
        #     used for eligible projects whose purpose is to reduce flood or fire 
        #     damage risk and vulnerability or to enhance resiliency to rapid 
        #     hydrologic change or natural disaster at treatment works, as defined by 
        #     section 212 of the Federal Water Pollution Control Act, or any eligible 
        #     facilities under section 1452 of the Safe Drinking Water Act, and for 
        #     other eligible tasks at such treatment works or facilities necessary to 
        #     further such purposes: Provided further, That the funds provided under 
        #     this paragraph in this Act shall not be subject to the matching or cost 
        #     share requirements of section 1452(e) of the Safe Drinking Water Act: 
        #     Provided further, That funds provided under this paragraph in this Act 
        #     shall not be subject to the matching or cost share requirements of 
        #     sections 602(b)(2), 602(b)(3), or 202 of the Federal Water Pollution 
        #     Control Act: Provided further, That the Administrator of the 
        #     Environmental Protection Agency may retain up to $5,000,000 of the funds 
        #     appropriated under this paragraph in this Act for management and 
        #     oversight: Provided further, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.
        #         For an additional amount for ``State and Tribal Assistance Grants'', 
        #     $85,000,000, to remain available until expended, for capitalization 
        #     grants for the Clean Water State Revolving Funds under title VI of the 
        #     Federal Water Pollution Control Act: Provided, 
        #     That <<NOTE: Determination.>>  notwithstanding section 604(a) of the 
        #     Federal Water Pollution Control Act, funds appropriated under this 
        #     paragraph in this Act shall be provided to States or territories in EPA 
        #     Regions 3 and 4 impacted by Hurricanes Helene and Milton in amounts 
        #     determined by the Administrator of the Environmental Protection Agency 
        #     to improve the resilience of decentralized wastewater treatment systems 
        #     to flooding, to assess the potential to connect homes served by 
        #     decentralized wastewater treatment systems to centralized wastewater 
        #     systems, and to fund such connections: Provided further, That 
        #     notwithstanding the requirements of section 603(i) of the Federal Water 
        #     Pollution Control Act, for the funds appropriated under this paragraph 
        #     in this Act, each State shall use 100 percent of the amount of its 
        #     capitalization grants to provide additional subsidization to eligible 
        #     recipients in the form of forgiveness of principal, grants, negative 
        #     interest loans, other loan forgiveness, and through buying, refinancing, 
        #     or restructuring debt or any combination thereof: Provided further, That 
        #     funds appropriated under this paragraph in this Act shall not be subject 
        #     to the matching

        #     [[Page 138 STAT. 1750]]

        #     or cost share requirements of sections 602(b)(2), 602(b)(3), or 202 of 
        #     the Federal Water Pollution Control Act: Provided further, That the 
        #     Administrator of the Environmental Protection Agency may retain up to 
        #     $3,000,000 of the funds appropriated under this paragraph in this Act 
        #     for management and oversight: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #         For an additional amount for ``State and Tribal Assistance Grants'', 
        #     $60,000,000, to remain available until expended, for necessary expenses 
        #     to address water emergencies under section 1442(b) of the Safe Drinking 
        #     Water Act (42 U.S.C. 300j-1(b)) or section 504(a) of the Federal Water 
        #     Pollution Control Act (33 U.S.C. 1364) in States or territories in EPA 
        #     Regions 3 and 4 impacted by Hurricanes Helene and Milton: Provided, That 
        #     notwithstanding section 1442(b) of the Safe Drinking Water Act, funds 
        #     appropriated under this paragraph in this Act may be used to provide 
        #     technical assistance and grants regardless of whether the emergency 
        #     situation presents a substantial danger to public health: Provided 
        #     further, That notwithstanding section 1442(b) of the Safe Drinking Water 
        #     Act, funds appropriated under this paragraph in this Act may be used to 
        #     provide grants regardless of whether such grants will be used to support 
        #     actions that would not otherwise be taken without emergency assistance: 
        #     Provided further, <<NOTE: Determination.>> That funds appropriated under 
        #     this paragraph in this Act may be used to provide technical assistance 
        #     and grants under section 1442(b) of the Safe Drinking Water Act to any 
        #     appropriate recipient, as determined by the Administrator of the 
        #     Environmental Protection Agency, to assist in responding to and 
        #     alleviating an emergency situation affecting a privately owned water 
        #     system: Provided further, That funds appropriated under this paragraph 
        #     in this Act may be used to take actions authorized under section 504(a) 
        #     of the Federal Water Pollution Control Act that the Administrator of the 
        #     Environmental Protection Agency deems necessary to protect the health or 
        #     welfare of persons affected by a water emergency, including other 
        #     necessary actions and for providing technical assistance and grants to 
        #     address such water emergency: Provided further, That the Administrator 
        #     of the Environmental Protection Agency may retain up to $1,000,000 of 
        #     the funds appropriated under this paragraph in this Act for management 
        #     and oversight: Provided further, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #         For an additional amount for ``State and Tribal Assistance Grants'', 
        #     $10,000,000, to remain available until expended, for grants and other 
        #     activities authorized by subsections (a) through (c) of section 103 of 
        #     the Clean Air Act (42 U.S.C. 7403) or section 105 of such Act (42 U.S.C. 
        #     7405) for necessary expenses related to the consequences of Hurricanes 
        #     Milton and Helene, including repair or replacement of damaged air 
        #     monitoring equipment: Provided, That funds appropriated under this 
        #     paragraph in this Act may be awarded noncompetitively: Provided further, 
        #     That such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.
        #         For an additional amount for ``State and Tribal Assistance Grants'', 
        #     $95,000,000, to remain available until expended, for the

        #     [[Page 138 STAT. 1751]]

        #     hazardous waste financial assistance grants program and other solid 
        #     waste management activities for necessary expenses related to the 
        #     consequences of Hurricanes Helene and Milton: Provided, That none of the 
        #     funds appropriated under this paragraph in this Act shall be subject to 
        #     section 3011(b) of the Solid Waste Disposal Act: Provided further, That 
        #     the Administrator of the Environmental Protection Agency may retain up 
        #     to $500,000 of the funds appropriated under this paragraph in this Act 
        #     for management and oversight: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                             DEPARTMENT OF AGRICULTURE

        #                                 Forest Service

        #                             forest service operations

        #         For an additional amount for ``Forest Service Operations'', 
        #     $68,100,000, to remain available until expended, for necessary expenses 
        #     related to the consequences of calendar year 2022, 2023, and 2024 
        #     wildfires, hurricanes, and other natural disasters: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                         forest and rangeland research

        #         For an additional amount for ``Forest and Rangeland Research'', 
        #     $26,000,000, to remain available until expended, for necessary expenses 
        #     related to the consequences of calendar year 2022, 2023, and 2024 
        #     wildfires, hurricanes, and other natural disasters: Provided, That such 
        #     amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                     state, private, and tribal forestry

        #         For an additional amount for ``State, Private, and Tribal 
        #     Forestry'', $208,000,000, to remain available until expended, for 
        #     necessary expenses related to the consequences of calendar year 2022, 
        #     2023, and 2024 wildfires, hurricanes, and other natural disasters: 
        #     Provided, That of the amounts made available under this heading in this 
        #     Act, $14,000,000 shall be to provide Forest Health Protection assistance 
        #     to States for an emerging eastern spruce budworm outbreak approaching 
        #     the northeastern U.S. border: Provided further, That with respect to the 
        #     preceding proviso, an award of financial assistance from the Forest 
        #     Service will not be subject to a non-Federal cost-share requirement: 
        #     Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                             national forest system

        #         For an additional amount for ``National Forest System'', 
        #     $2,523,000,000, to remain available until expended: Provided, That

        #     [[Page 138 STAT. 1752]]

        #     of the amounts made available under this heading in this Act, 
        #     $2,448,000,000 shall be for necessary expenses related to the 
        #     consequences of calendar year 2022, 2023, and 2024 wildfires, 
        #     hurricanes, and other natural disasters: Provided further, That of the 
        #     amounts made available under this heading in this Act, $75,000,000 shall 
        #     be for the construction or maintenance of shaded fuel breaks in the 
        #     Pacific Regions: Provided further, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                     capital improvement and maintenance

        #         For an additional amount for ``Capital Improvement and 
        #     Maintenance'', $3,525,000,000, to remain available until expended, for 
        #     necessary expenses related to the consequences of calendar year 2022, 
        #     2023, and 2024 wildfires, hurricanes, and other natural disasters: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         GENERAL PROVISIONS--THIS TITLE

        #         Sec. 2701. <<NOTE: 43 USC 1457 note.>>   Notwithstanding section 
        #     3304 of title 5, United States Code, and without regard to the 
        #     provisions of sections 3309 through 3318 of such title 5, the Secretary 
        #     of the Interior and the Secretary of Agriculture, acting through the 
        #     Chief of the Forest Service, may recruit and directly appoint highly 
        #     qualified individuals into the competitive service to address critical 
        #     hiring needs for the planning and execution of the projects and 
        #     activities funded in this title: Provided, That such authority shall not 
        #     apply to positions in the Excepted Service or the Senior Executive 
        #     Service: Provided further, <<NOTE: Compliance.>>  That any action 
        #     authorized herein shall be consistent with the merit principles of 
        #     section 2301 of such title 5, and the Department of the Interior and the 
        #     Department of Agriculture shall comply with the public notice 
        #     requirements of section 3327 of such title 5: Provided 
        #     further, <<NOTE: Termination date.>> That the authority under this 
        #     section shall terminate on September 30, 2029: Provided further, That 
        #     amounts provided by this section are designated by the Congress as being 
        #     for an emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #         Sec. 2702. <<NOTE: Deadlines. Operating plan.>>  Not later than 45 
        #     days after the date of enactment of this Act, the agencies receiving 
        #     funds appropriated by this title shall provide a detailed operating plan 
        #     of anticipated uses of funds made available in this title by State and 
        #     Territory, and by program, project, and activity, to the Committees on 
        #     Appropriations of the House of Representatives and the Senate: Provided, 
        #     That no such funds shall be obligated before the operating plans are 
        #     provided to such Committees: Provided further, <<NOTE: Updates.>>  That 
        #     such plans shall be updated, including obligations and expenditures to 
        #     date, and submitted to such Committees on Appropriations every 60 days 
        #     until all such funds are expended.

        #     [[Page 138 STAT. 1753]]

        #                                 TITLE VIII

        #                     DEPARTMENT OF HEALTH AND HUMAN SERVICES

        #                     Administration for Children and Families

        #         payments to states for the child care and development block grant

        #         For an additional amount for ``Payments to States for the Child Care 
        #     and Development Block Grant'', $250,000,000, to remain available through 
        #     September 30, 2026, for necessary expenses directly related to the 
        #     consequences of major disasters and emergencies declared pursuant to the 
        #     Robert T. Stafford Disaster Relief and Emergency Assistance Act (42 
        #     U.S.C. 5121 et seq.) occurring in 2023 and 2024 (referred to under this 
        #     heading in this Act as ``covered disaster or emergency''), including 
        #     activities authorized under section 319(a) of the Public Health Service 
        #     Act: Provided, That <<NOTE: Allocation. Assessment.>> the Secretary of 
        #     Health and Human Services shall allocate such funds to States, 
        #     territories, and Tribes based on assessed need notwithstanding sections 
        #     658J and 658O of the Child Care and Development Block Grant Act of 1990: 
        #     Provided further, That not to exceed 2 percent of funds appropriated in 
        #     this paragraph may be reserved, to remain available until expended, for 
        #     Federal administration costs: Provided further, That such funds may be 
        #     used for alteration, renovation, construction, equipment, and other 
        #     capital improvement costs, including for child care facilities without 
        #     regard to section 658F(b) of such Act, and for other expenditures 
        #     related to child care, as necessary to meet the needs of areas affected 
        #     by a covered disaster or emergency: Provided further, That funds made 
        #     available in this paragraph may be used without regard to section 658G 
        #     of such Act and with amounts allocated for such purposes excluded from 
        #     the calculation of percentages under subsection 658E(c)(3) of such Act: 
        #     Provided further, <<NOTE: Time periods.>> That notwithstanding section 
        #     658J(c) of such Act, funds allotted to a State may be obligated by the 
        #     State in that fiscal year or the succeeding three fiscal years: Provided 
        #     further, That Federal interest provisions will not apply to the 
        #     renovation or construction of privately-owned family child care homes, 
        #     and the Secretary of Health and Human Services shall develop parameters 
        #     on the use of funds for family child care homes: Provided 
        #     further, <<NOTE: Time period.>>  That the Secretary shall not retain 
        #     Federal interest after a period of 10 years (from the date on which the 
        #     funds are made available to purchase or improve the property) in any 
        #     facility renovated or constructed with funds made available in this 
        #     paragraph: Provided further, That funds made available in this paragraph 
        #     shall not be available for costs that are reimbursed by the Federal 
        #     Emergency Management Agency, under a contract for insurance, or by self-
        #     insurance: Provided further, That <<NOTE: Reimbursement.>>  funds 
        #     appropriated in this paragraph may be made available to restore amounts, 
        #     either directly or through reimbursement, for obligations incurred for 
        #     such purposes, prior to the date of enactment of this Act: Provided 
        #     further, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #         For an additional amount for ``Payments to States for the Child Care 
        #     and Development Block Grant'', $250,000,000, to remain

        #     [[Page 138 STAT. 1754]]

        #     available until September 30, 2025: Provided, That amounts made 
        #     available in this paragraph shall be available without regard to 
        #     requirements in sections 658E(c)(3)(E) or 658G of the Child Care and 
        #     Development Block Grant Act: Provided further, <<NOTE: Time 
        #     periods.>> That payments made to States, territories, Indian Tribes, and 
        #     Tribal organizations from amounts made available in this paragraph shall 
        #     be obligated in this fiscal year or the succeeding two fiscal years: 
        #     Provided further, That amounts made available in this paragraph shall be 
        #     used to supplement and not supplant other Federal, State, and local 
        #     public funds expended to provide child care services for eligible 
        #     individuals: Provided further, That such amount is designated by the 
        #     Congress as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                         GENERAL PROVISION--THIS TITLE

        #         Sec. 2801. <<NOTE: Deadline. Operating plans.>>   Not later than 45 
        #     days after the date of enactment of this Act, the agencies receiving 
        #     funds appropriated by this title in this Act shall provide a detailed 
        #     operating plan of anticipated uses of funds made available in this title 
        #     in this Act by State and territory, and by program, project, and 
        #     activity, to the Committees on Appropriations of the House of 
        #     Representatives and the Senate: Provided, That no such funds shall be 
        #     obligated before the operating plans are provided to such Committees: 
        #     Provided further, <<NOTE: Updates. Time period.>> That such plans shall 
        #     be updated, including obligations to date and anticipated use of funds 
        #     made available in this title in this Act, and submitted to such 
        #     Committees quarterly until all such funds expire.

        #                                     TITLE IX

        #                             LEGISLATIVE BRANCH

        #                         GOVERNMENT ACCOUNTABILITY OFFICE

        #                             salaries and expenses

        #         For an additional amount for ``Salaries and Expenses'', $10,000,000, 
        #     to remain available until expended, for audits and investigations 
        #     related to Hurricanes Helene and Milton, and other disasters declared 
        #     pursuant to the Robert T. Stafford Disaster Relief and Emergency 
        #     Assistance Act (42 U.S.C. 5121 et seq.) in calendar years 2023 and 2024: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                                     TITLE X

        #                             DEPARTMENT OF DEFENSE

        #                 Military Construction, Navy and Marine Corps

        #         For an additional amount for ``Military Construction, Navy and 
        #     Marine Corps'', $1,127,281,000, to remain available until September 30, 
        #     2029, for necessary expenses related to the consequences of Typhoon 
        #     Mawar: Provided, <<NOTE: Deadline. Submission. Expenditure plan.>> That 
        #     not later than 60 days after

        #     [[Page 138 STAT. 1755]]

        #     enactment of this Act, the Secretary of the Navy, or their designee, 
        #     shall submit to the Committees on Appropriations of the House of 
        #     Representatives and the Senate form 1391 for each specific project and 
        #     an expenditure plan for funds provided under this heading in this Act: 
        #     Provided further, That such funds may be obligated or expended for 
        #     design and military construction projects not otherwise authorized by 
        #     law: Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         Military Construction, Air Force

        #         For an additional amount for ``Military Construction, Air Force'', 
        #     $487,300,000, to remain available until September 30, 2029, for 
        #     necessary expenses related to the consequences of Typhoon Mawar: 
        #     Provided, That <<NOTE: Deadline. Submission. Expenditure plan.>>  not 
        #     later than 60 days after enactment of this Act, the Secretary of the Air 
        #     Force, or their designee, shall submit to the Committees on 
        #     Appropriations of the House of Representatives and the Senate form 1391 
        #     for each specific project and an expenditure plan for funds provided 
        #     under this heading in this Act: Provided further, That such funds may be 
        #     obligated or expended for design and military construction projects not 
        #     otherwise authorized by law: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                 Military Construction, Army National Guard

        #         For an additional amount for ``Military Construction, Army National 
        #     Guard'', $21,000,000, to remain available until September 30, 2029, for 
        #     necessary expenses related to the consequences of Typhoon Mawar and 
        #     severe storms in calendar year 2023: Provided, 
        #     That <<NOTE: Deadline. Submission. Expenditure plan.>>  not later than 
        #     60 days after enactment of this Act, the Director of the Army National 
        #     Guard, or their designee, shall submit to the Committees on 
        #     Appropriations of the House of Representatives and the Senate form 1391 
        #     for each specific project and an expenditure plan for funds provided 
        #     under this heading in this Act: Provided further, That such funds may be 
        #     obligated or expended for design and military construction projects not 
        #     otherwise authorized by law: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #             Family Housing Construction, Navy and Marine Corps

        #         For an additional amount for ``Family Housing Construction, Navy and 
        #     Marine Corps'', $27,399,000, to remain available until September 30, 
        #     2029, for necessary expenses related to the consequences of Typhoon 
        #     Mawar: Provided, <<NOTE: Deadline. Expenditure plan.>> That not later 
        #     than 60 days after enactment of this Act, the Secretary of the Navy, or 
        #     their designee, shall submit to the Committees on Appropriations of the 
        #     House of Representatives and the Senate an expenditure plan for funds 
        #     provided under this heading in this Act: Provided further, That such 
        #     amount is designated by the Congress as being

        #     [[Page 138 STAT. 1756]]

        #     for an emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #         Family Housing Operation and Maintenance, Navy and Marine Corps

        #         For an additional amount for ``Family Housing Operation and 
        #     Maintenance, Navy and Marine Corps'', $102,168,000, to remain available 
        #     until September 30, 2026, for necessary expenses related to the 
        #     consequences of Typhoon Mawar: Provided, <<NOTE: Deadline. Expenditure 
        #     plan.>>  That not later than 60 days after enactment of this Act, the 
        #     Secretary of the Navy, or their designee, shall submit to the Committees 
        #     on Appropriations of the House of Representatives and the Senate an 
        #     expenditure plan for funds provided under this heading in this Act: 
        #     Provided further, That such amount is designated by the Congress as 
        #     being for an emergency requirement pursuant to section 251(b)(2)(A)(i) 
        #     of the Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         DEPARTMENT OF VETERANS AFFAIRS

        #                         Veterans Health Administration

        #                                 medical services

        #         For an additional amount for ``Medical Services'', $19,258,000, to 
        #     remain available until September 30, 2027, for necessary expenses 
        #     related to the consequences of Hurricanes Milton and Helene: Provided, 
        #     That such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #                         medical support and compliance

        #         For an additional amount for ``Medical Support and Compliance'', 
        #     $330,000, to remain available until September 30, 2027, for necessary 
        #     expenses related to the consequences of Hurricanes Milton and Helene: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                             medical facilities

        #         For an additional amount for ``Medical Facilities'', $41,660,000, to 
        #     remain available until September 30, 2029, for necessary expenses 
        #     related to the consequences of Hurricanes Milton and Helene and other 
        #     Federally declared disasters occurring in 2023 and 2024: Provided, That 
        #     such amount is designated by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985.

        #     [[Page 138 STAT. 1757]]

        #                         National Cemetery Administration

        #         For an additional amount for ``National Cemetery Administration'' 
        #     for necessary expenses related to the consequences of Hurricanes Milton 
        #     and Helene, $693,000, to remain available until September 30, 2029: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         Departmental Administration

        #                         construction, major projects

        #         For an additional amount for ``Construction, Major Projects'', 
        #     $4,000,000, to remain available until September 30, 2029, for necessary 
        #     expenses related to the consequences of Hurricanes Milton and Helene: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                         construction, minor projects

        #         For an additional amount for ``Construction, Minor Projects'', 
        #     $2,020,000, to remain available until September 30, 2029, for necessary 
        #     expenses related to the consequences of Hurricanes Milton and Helene: 
        #     Provided, That such amount is designated by the Congress as being for an 
        #     emergency requirement pursuant to section 251(b)(2)(A)(i) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985.

        #                                     TITLE XI

        #                     DEPARTMENT OF STATE AND RELATED AGENCY

        #                             DEPARTMENT OF STATE

        #                             International Commissions

        #     international boundary and water commission, united states and mexico

        #                                 construction

        #         For an additional amount for ``Construction'', $250,000,000, to 
        #     remain available until expended: Provided, <<NOTE: Notification.>> That 
        #     funds provided under this heading in this Act shall be subject to prior 
        #     consultation with, and the regular notification procedures of, the 
        #     Committees on Appropriations of the House of Representatives and the 
        #     Senate: Provided further, That such amount is designated by the Congress 
        #     as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #     [[Page 138 STAT. 1758]]

        #                                     TITLE XII

        #                         DEPARTMENT OF TRANSPORTATION

        #                         Federal Highway Administration

        #     emergency relief program <<NOTE: Maryland.>> 

        #         For an additional amount for the ``Emergency Relief Program'' as 
        #     authorized under section 125 of title 23, United States Code, 
        #     $8,086,020,000, to remain available until expended: Provided, That 
        #     notwithstanding subsection (e) of section 120 of title 23, United States 
        #     Code, for any obligations made on or after March 26, 2024, for fiscal 
        #     year 2024, this fiscal year, and hereafter, the Federal share for 
        #     Emergency Relief funds made available under section 125 of such title to 
        #     respond to damage caused by the cargo ship Dali to the Francis Scott Key 
        #     Bridge located in Baltimore City and Baltimore and Anne Arundel 
        #     Counties, Maryland, including reconstruction of that bridge and its 
        #     approaches, shall be 100 percent: Provided further, That consistent with 
        #     section 668.105(e) of title 23, Code of Federal Regulations (or a 
        #     successor regulation), any insurance proceeds, judgments, settlements, 
        #     penalties, fines, or other compensation for damages, including interest, 
        #     from whatever source derived, recovered by a State, a political 
        #     subdivision of a State, or a toll authority for repair, including 
        #     reconstruction, of the Francis Scott Key Bridge located in Baltimore 
        #     City and Baltimore and Anne Arundel Counties, Maryland, in response to, 
        #     or as a result of, the damage caused by the cargo ship Dali to that 
        #     bridge and its approaches, shall be used upon receipt to reduce 
        #     liability on the repair, including reconstruction, of such bridge and 
        #     its approaches from the emergency fund authorized under section 125 of 
        #     title 23, United States Code: Provided further, That any funds recovered 
        #     and used to reduce liability pursuant to the preceding proviso shall not 
        #     exceed the total amount of liability on the repair, including 
        #     reconstruction, of the Francis Scott Key Bridge located in Baltimore 
        #     City and Baltimore and Anne Arundel Counties, Maryland, and its 
        #     approaches, from the emergency fund authorized under section 125 of 
        #     title 23, United States Code: Provided further, That such amount is 
        #     designated by the Congress as being for an emergency requirement 
        #     pursuant to section 251(b)(2)(A)(i) of the Balanced Budget and Emergency 
        #     Deficit Control Act of 1985.

        #                 DEPARTMENT OF HOUSING AND URBAN DEVELOPMENT

        #                     Community Planning and Development

        #                         community development fund

        #                         (including transfers of funds)

        #         For an additional amount for ``Community Development Fund'', 
        #     $12,039,000,000, to remain available until expended, for the same 
        #     purposes and under the same terms and conditions as funds appropriated 
        #     under such heading in title VIII of the Disaster Relief Supplemental 
        #     Appropriations Act, 2022 (Public Law 117-43), except that such amounts 
        #     shall be for major disasters that occurred in 2023 or 2024 and the 
        #     fourth, tenth, 15th, 16th, 20th, and 21st

        #     [[Page 138 STAT. 1759]]

        #     provisos under such heading in such Act shall not apply: Provided, 
        #     That <<NOTE: Allocations. Federal Register, publication. Deadline.>>  
        #     the Secretary of Housing and Urban Development shall allocate all funds 
        #     provided under this heading in this Act for the total estimate for unmet 
        #     needs including additional mitigation for qualifying disasters and 
        #     publish such allocations in the Federal Register no later than January 
        #     15, 2025: Provided further, That the amount obligated for each 
        #     qualifying disaster area shall be no less than the amounts specified in 
        #     such Federal Register publication, unless such allocation is rejected by 
        #     the grantee: Provided further, That <<NOTE: Plan. Criteria.>> a grantee 
        #     shall submit a plan to the Secretary for approval detailing the proposed 
        #     use of all funds, including criteria for eligibility and how the use of 
        #     these funds will address long-term recovery and restoration of 
        #     infrastructure and housing, economic revitalization, and mitigation in 
        #     the most impacted and distressed areas: Provided 
        #     further, <<NOTE: Effective date.>>  That unobligated balances remaining 
        #     as of the date of enactment of this Act included under Treasury 
        #     Appropriation Fund Symbol 86 X 0162 from Public Laws 108-324, 109-148, 
        #     109-234, 110-252, 110-329, 111-212, 112-55, and 113-2 shall also be 
        #     available for the purposes authorized under this heading in this Act 
        #     (except that the amount for each set-aside provided herein shall not be 
        #     exceeded), notwithstanding the purposes for which such amounts were 
        #     appropriated: Provided further, That of the amounts made available under 
        #     this heading in this Act, $45,000,000 shall be transferred to 
        #     ``Department of Housing and Urban Development--Management and 
        #     Administration--Program Offices'' for salaries and expenses of the 
        #     Office of Community Planning and Development for necessary costs, 
        #     including information technology costs, of administering and overseeing 
        #     the obligation and expenditure of amounts made available for activities 
        #     authorized under title I of the Housing and Community Development Act of 
        #     1974 (42 U.S.C. 5301 et seq.) related to disaster relief, long-term 
        #     recovery, restoration of infrastructure and housing, economic 
        #     revitalization, and mitigation in the most impacted and distressed areas 
        #     resulting from a major disaster in this, prior, or future Acts (``this, 
        #     prior, or future disaster Acts''): Provided further, That of the amounts 
        #     made available under this heading in this Act, $1,850,000 shall be 
        #     transferred to ``Department of Housing and Urban Development--
        #     Information Technology Fund'' for the disaster recovery data portal: 
        #     Provided further, That of the amounts made available under this heading 
        #     in this Act, $7,000,000 shall be transferred to ``Department of Housing 
        #     and Urban Development--Office of Inspector General'' for necessary costs 
        #     of overseeing and auditing amounts made available in this, prior, or 
        #     future disaster Acts: Provided further, That of the amounts made 
        #     available under this heading in this Act, $25,000,000 shall be made 
        #     available for capacity building and technical assistance, including 
        #     assistance on contracting and procurement processes, to support 
        #     recipients of allocations from this, prior, or future disaster Acts: 
        #     Provided further, That amounts made available under this heading in this 
        #     Act may be used by a grantee to assist utilities as part of a disaster-
        #     related eligible activity under section 105(a) of the Housing and 
        #     Community Development Act of 1974 (42 U.S.C. 5305(a)): Provided 
        #     further, <<NOTE: 42 USC 4370mm-4 note.>>  That recipients of funds made 
        #     available in this, prior, or future disaster Acts that use such funds to 
        #     supplement other Federal assistance may adopt, without review or public 
        #     comment, any environmental review, approval, or permit performed

        #     [[Page 138 STAT. 1760]]

        #     by a Federal agency, and such adoption shall satisfy the 
        #     responsibilities of the recipient with respect to such environmental 
        #     review, approval or permit, so long as the actions covered by the 
        #     existing environmental review, approval, or permit and the actions 
        #     proposed for these supplemental funds are substantially the same: 
        #     Provided further, That <<NOTE: Request. Certification.>> the Secretary 
        #     or a State may, upon receipt of a request for release of funds and 
        #     certification, immediately approve the release of funds for any activity 
        #     or project if the recipient has adopted an environmental review, 
        #     approval or permit under the previous proviso or if the activity or 
        #     project is categorically excluded from review under the National 
        #     Environmental Policy Act of 1969 (42 U.S.C. 4321 et seq.), 
        #     notwithstanding section 104(g)(2) of the Housing and Community 
        #     Development Act of 1974 (42 U.S.C. 5304(g)(2)): Provided further, That 
        #     such amount and amounts repurposed under this heading that were 
        #     previously designated by the Congress as an emergency requirement 
        #     pursuant to a concurrent resolution on the budget or the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985 are designated by the Congress 
        #     as being for an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985.

        #                                 TITLE XIII

        #                             GENERAL PROVISIONS

        #         Sec. 21301.  Each amount appropriated or made available by this Act 
        #     is in addition to amounts otherwise appropriated for the fiscal year 
        #     involved.
        #         Sec. 21302.  No part of any appropriation contained in this Act 
        #     shall remain available for obligation beyond the current fiscal year 
        #     unless expressly so provided herein.
        #         Sec. 21303.  Unless otherwise provided for by this Act, the 
        #     additional amounts appropriated by this Act to appropriations accounts 
        #     shall be available under the authorities and conditions applicable to 
        #     such appropriations accounts for fiscal year 2025.
        #         Sec. 21304. <<NOTE: President. Designations.>>   Each amount 
        #     designated in divisions A or B by the Congress as being for an emergency 
        #     requirement pursuant to section 251(b)(2)(A)(i) of the Balanced Budget 
        #     and Emergency Deficit Control Act of 1985 shall be available (or 
        #     repurposed, rescinded, or transferred, if applicable) only if the 
        #     President subsequently so designates all such amounts and transmits such 
        #     designations to the Congress.

        #         Sec. 21305.  Any amount appropriated by divisions A or B, designated 
        #     by the Congress as an emergency requirement pursuant to section 
        #     251(b)(2)(A)(i) of the Balanced Budget and Emergency Deficit Control Act 
        #     of 1985, and subsequently so designated by the President, and 
        #     transferred pursuant to transfer authorities provided by this division 
        #     shall retain such designation.
        #         Sec. 21306.  Budgetary Effects.--
        #                 (1) Statutory paygo scorecards.--The budgetary effects of 
        #             division C and each succeeding division shall not be entered on 
        #             either PAYGO scorecard maintained pursuant to section 4(d) of 
        #             the Statutory Pay-As-You-Go Act of 2010.
        #                 (2) Senate paygo scorecards.--The budgetary effects of 
        #             division C and each succeeding division shall not be entered

        #     [[Page 138 STAT. 1761]]

        #             on any PAYGO scorecard maintained for purposes of section 4106 
        #             of H. Con. Res. 71 (115th Congress).
        #                 (3) Classification of budgetary effects.--Notwithstanding 
        #             Rule 3 of the Budget Scorekeeping Guidelines set forth in the 
        #             joint explanatory statement of the committee of conference 
        #             accompanying Conference Report 105-217 and section 250(c)(8) of 
        #             the Balanced Budget and Emergency Deficit Control Act of 1985, 
        #             the budgetary effects of division C and each succeeding division 
        #             shall not be estimated--
        #                         (A) for purposes of section 251 of such Act;
        #                         (B) for purposes of an allocation to the Committee 
        #                     on Appropriations pursuant to section 302(a) of the 
        #                     Congressional Budget Act of 1974; and
        #                         (C) for purposes of paragraph (4)(C) of section 3 of 
        #                     the Statutory Pay-As-You-Go Act of 2010 as being 
        #                     included in an appropriation Act.
        #                 (4) <<NOTE: Effective date. Determination.>> Balances on the 
        #             paygo scorecards.--Effective on the date of the adjournment of 
        #             the second session of the 118th Congress, and for the purposes 
        #             of the annual report issued pursuant to section 5 of the 
        #             Statutory Pay-As-You-Go Act of 2010 (2 U.S.C. 934) after such 
        #             adjournment and for determining whether a sequestration order is 
        #             necessary under such section, the balances on the PAYGO 
        #             scorecards established pursuant to paragraphs (4) and (5) of 
        #             section 4(d) of such Act shall be zero.

        #         This division may be cited as the ``Disaster Relief Supplemental 
        #     Appropriations Act, 2025''.

        #         DIVISION C-- <<NOTE: Health Extensions and Other Matters Act, 
        #     2025.>> HEALTH
        #     SEC. 3001. SHORT TITLE; TABLE OF CONTENTS.

        #         (a) <<NOTE: 42 USC 201 note.>>  Short Title.--This division may be 
        #     cited as the ``Health Extensions and Other Matters Act, 2025''.

        #         (b) Table of Contents.--The table of contents for this division is 
        #     as follows:

        #     Sec. 3001. Short title; table of contents.

        #                         TITLE I--PUBLIC HEALTH EXTENDERS

        #     Sec. 3101. Extension for community health centers, National Health 
        #             Service Corps, and teaching health centers that operate GME 
        #             programs.
        #     Sec. 3102. Extension of special diabetes programs.
        #     Sec. 3103. National health security extensions.

        #                             TITLE II--MEDICARE

        #     Sec. 3201. Extension of increased inpatient hospital payment adjustment 
        #             for certain low-volume hospitals.
        #     Sec. 3202. Extension of the Medicare-dependent hospital (MDH) program.
        #     Sec. 3203. Extension of add-on payments for ambulance services.
        #     Sec. 3204. Extension of funding for quality measure endorsement, input, 
        #             and selection.
        #     Sec. 3205. Extension of funding outreach and assistance for low-income 
        #             programs.
        #     Sec. 3206. Extension of the work geographic index floor.
        #     Sec. 3207. Extension of certain telehealth flexibilities.
        #     Sec. 3208. Extending acute hospital care at home waiver authorities.
        #     Sec. 3209. Extension of temporary inclusion of authorized oral antiviral 
        #             drugs as covered part D drugs.
        #     Sec. 3210. Medicare improvement fund.

        #                             TITLE III--HUMAN SERVICES

        #     Sec. 3301. Sexual risk avoidance education extension.

        #     [[Page 138 STAT. 1762]]

        #     Sec. 3302. Personal responsibility education extension.
        #     Sec. 3303. Extension of funding for family-to-family health information 
        #             centers.

        #                             TITLE IV--MEDICAID

        #     Sec. 3401. Eliminating certain disproportionate share hospital payment 
        #             cuts.

        #                         TITLE I--PUBLIC HEALTH EXTENDERS

        #     SEC. 3101. <<NOTE: Time periods.>>  EXTENSION FOR COMMUNITY HEALTH 
        #                             CENTERS, NATIONAL HEALTH SERVICE CORPS, 
        #                             AND TEACHING HEALTH CENTERS THAT OPERATE 
        #                             GME PROGRAMS.

        #         (a) Extension for Community Health Centers.--Section 10503(b)(1) of 
        #     the Patient Protection and Affordable Care Act (42 U.S.C. 254b-2(b)(1)) 
        #     is amended--
        #                 (1) in subparagraph (E), by striking ``and'' at the end;
        #                 (2) in subparagraph (F), by striking ``, $4,000,000,000 for 
        #             each of fiscal years 2019 through 2023'' and all that follows 
        #             through ``and ending on December 31, 2024; and'' and inserting a 
        #             semicolon; and
        #                 (3) by adding at the end the following:
        #                         ``(G) $4,000,000,000 for each of fiscal years 2019 
        #                     through 2023;
        #                         ``(H) $526,027,397 for the period beginning on 
        #                     October 1, 2023, and ending on November 17, 2023, 
        #                     $690,410,959 for the period beginning on November 18, 
        #                     2023, and ending on January 19, 2024, $536,986,301 for 
        #                     the period beginning on January 20, 2024, and ending on 
        #                     March 8, 2024, and $3,592,328,767 for the period 
        #                     beginning on October 1, 2023, and ending on December 31, 
        #                     2024; and
        #                         ``(I) $1,050,410,959 for the period beginning on 
        #                     January 1, 2025, and ending on March 31, 2025.''.

        #         (b) Extension for the National Health Service Corps.--Section 
        #     10503(b)(2) of the Patient Protection and Affordable Care Act (42 U.S.C. 
        #     254b-2(b)(2)) is amended--
        #                 (1) in subparagraph (H), by striking ``and'' at the end;
        #                 (2) in subparagraph (I), by striking the period at the end 
        #             and inserting ``; and''; and
        #                 (3) by adding at the end the following:
        #                         ``(J) $85,068,493 for the period beginning on 
        #                     January 1, 2025, and ending on March 31, 2025.''.

        #         (c) Teaching Health Centers That Operate Graduate Medical Education 
        #     Programs.--Section 340H(g)(1) of the Public Health Service Act (42 
        #     U.S.C. 256h(g)(1)) is amended--
        #                 (1) by striking ``not to exceed $230,000,000'' and all that 
        #             follows through ``and ending on December 31, 2024,''; and
        #                 (2) by striking the period at the end and inserting the 
        #             following: ``, not to exceed--
        #                         ``(A) $230,000,000, for the period of fiscal years 
        #                     2011 through 2015;
        #                         ``(B) $60,000,000 for each of fiscal years 2016 and 
        #                     2017;
        #                         ``(C) $126,500,000 for each of fiscal years 2018 
        #                     through 2023;
        #                         ``(D) $16,635,616 for the period beginning on 
        #                     October 1, 2023, and ending on November 17, 2023, 
        #                     $21,834,247 for the period beginning on November 18, 
        #                     2023, and ending on January 19, 2024, $16,982,192 for 
        #                     the period beginning on January 20, 2024, and ending on 
        #                     March 8, 2024, and

        #     [[Page 138 STAT. 1763]]

        #                     $164,136,986 for the period beginning on October 1, 
        #                     2023, and ending on December 31, 2024; and
        #                         ``(E) $43,150,685 for the period beginning on 
        #                     January 1, 2025, and ending on March 31, 2025.''.

        #         (d) Application of Provisions.--Amounts appropriated pursuant to the 
        #     amendments made by this section shall be subject to the requirements 
        #     contained in Public Law 117-328 for funds for programs authorized under 
        #     sections 330 through 340 of the Public Health Service Act (42 U.S.C. 
        #     254b et seq.).
        #         (e) Conforming Amendments.--Section 3014(h) of title 18, United 
        #     States Code, is amended--
        #                 (1) in paragraph (1), by striking ``under subparagraphs (E) 
        #             and (F) of section 10503(b)(1) of the Patient Protection and 
        #             Affordable Care Act (42 U.S.C. 254b-2(b)(1))'' and inserting 
        #             ``under section 10503(b)(1) of the Patient Protection and 
        #             Affordable Care Act (42 U.S.C. 254b-2(b)(1)) for fiscal year 
        #             2015 and each subsequent fiscal year (or period thereof)''; and
        #                 (2) in paragraph (4), by striking ``and section 101(d) of 
        #             the Consolidated Appropriations Act, 2024'' and inserting 
        #             ``section 101(d) of division G of the Consolidated 
        #             Appropriations Act, 2024, and section 3101(d) of the Health 
        #             Extensions and Other Matters Act, 2025''.
        #     SEC. 3102. <<NOTE: Time period.>> EXTENSION OF SPECIAL DIABETES 
        #                             PROGRAMS.

        #         (a) Extension of Special Diabetes Programs for Type I Diabetes.--
        #     Section 330B(b)(2) of the Public Health Service Act (42 U.S.C. 254c-
        #     2(b)(2)) is amended--
        #                 (1) in subparagraph (D), by striking ``and'' at the end;
        #                 (2) in subparagraph (E), by striking the period at the end 
        #             and inserting ``; and''; and
        #                 (3) by adding at the end the following:
        #                         ``(F) $39,261,745 for the period beginning on 
        #                     January 1, 2025, and ending on March 31, 2025, to remain 
        #                     available until expended.''.

        #         (b) Extending Funding for Special Diabetes Programs for Indians.--
        #     Section 330C(c)(2) of the Public Health Service Act (42 U.S.C. 254c-
        #     3(c)(2)) is amended--
        #                 (1) in subparagraph (D), by striking ``and'' at the end;
        #                 (2) in subparagraph (E), by striking the period at the end 
        #             and inserting ``; and''; and
        #                 (3) by adding at the end the following:
        #                         ``(F) $39,261,745 for the period beginning on 
        #                     January 1, 2025, and ending on March 31, 2025, to remain 
        #                     available until expended.''.
        #     SEC. 3103. NATIONAL HEALTH SECURITY EXTENSIONS.

        #         (a) Section 319(e)(8) of the Public Health Service Act (42 U.S.C. 
        #     247d(e)(8)) is amended by striking ``December 31, 2024'' and inserting 
        #     ``March 31, 2025''.
        #         (b) Section 319L(e)(1)(D) of the Public Health Service Act (42 
        #     U.S.C. 247d-7e(e)(1)(D)) is amended by striking ``December 31, 2024'' 
        #     and inserting ``March 31, 2025''.
        #         (c) Section 319L-1(b) of the Public Health Service Act (42 U.S.C. 
        #     247d-7f(b)) is amended by striking ``December 31, 2024'' and inserting 
        #     ``March 31, 2025''.
        #         (d)(1) Section 2811A(g) of the Public Health Service Act (42 U.S.C. 
        #     300hh-10b(g)) is amended by striking ``December 31, 2024'' and inserting 
        #     ``March 31, 2025''.

        #     [[Page 138 STAT. 1764]]

        #         (2) Section 2811B(g)(1) of the Public Health Service Act (42 U.S.C. 
        #     300hh-10c(g)(1)) is amended by striking ``December 31, 2024'' and 
        #     inserting ``March 31, 2025''.
        #         (3) Section 2811C(g)(1) of the Public Health Service Act (42 U.S.C. 
        #     300hh-10d(g)(1)) is amended by striking ``December 31, 2024'' and 
        #     inserting ``March 31, 2025''.
        #         (e) Section 2812(c)(4)(B) of the Public Health Service Act (42 
        #     U.S.C. 300hh-11(c)(4)(B)) is amended by striking ``December 31, 2024'' 
        #     and inserting ``March 31, 2025''.

        #                             TITLE II--MEDICARE

        #     SEC. 3201. EXTENSION OF INCREASED INPATIENT HOSPITAL PAYMENT 
        #                             ADJUSTMENT FOR CERTAIN LOW-VOLUME 
        #                             HOSPITALS.

        #         (a) In General.----Section 1886(d)(12) of the Social Security Act 
        #     (42 U.S.C. 1395ww(d)(12)) is amended--
        #                 (1) in subparagraph (B), in the matter preceding clause (i), 
        #             by striking ``January 1, 2025'' and inserting ``April 1, 2025'';
        #                 (2) in subparagraph (C)(i)--
        #                         (A) in the matter preceding subclause (I), by 
        #                     striking ``December 31, 2024'' and inserting ``March 31, 
        #                     2025'';
        #                         (B) in subclause (III), by striking ``December 31, 
        #                     2024'' and inserting ``March 31, 2025''; and
        #                         (C) in subclause (IV), by striking ``January 1, 
        #                     2025'' and inserting ``April 1, 2025''; and
        #                 (3) in subparagraph (D)--
        #                         (A) in the matter preceding clause (i), by striking 
        #                     ``December 31, 2024'' and inserting ``March 31, 2025''; 
        #                     and
        #                         (B) in clause (ii), by striking ``December 31, 
        #                     2024'' and inserting ``March 31, 2025''.

        #         (b) <<NOTE: 42 USC 1395ww note.>> Implementation.--Notwithstanding 
        #     any other provision of law, the Secretary of Health and Human Services 
        #     may implement the amendments made by this section by program instruction 
        #     or otherwise.
        #     SEC. 3202. EXTENSION OF THE MEDICARE-DEPENDENT HOSPITAL (MDH) 
        #                             PROGRAM.

        #         (a) In General.----Section 1886(d)(5)(G) of the Social Security Act 
        #     (42 U.S.C. 1395ww(d)(5)(G)) is amended--
        #                 (1) in clause (i), by striking ``January 1, 2025'' and 
        #             inserting ``April 1, 2025''; and
        #                 (2) in clause (ii)(II), by striking ``January 1, 2025'' and 
        #             inserting ``April 1, 2025''.

        #         (b) Conforming Amendments.--
        #                 (1) In general.--Section 1886(b)(3)(D) of the Social 
        #             Security Act (42 U.S.C. 1395ww(b)(3)(D)) is amended--
        #                         (A) in the matter preceding clause (i), by striking 
        #                     ``January 1, 2025'' and inserting ``April 1, 2025''; and
        #                         (B) in clause (iv), by striking ``December 31, 
        #                     2024'' and inserting ``March 31, 2025''.
        #                 (2) Permitting hospitals to decline reclassification.--
        #             Section 13501(e)(2) of the Omnibus Budget Reconciliation Act of 
        #             1993 (42 U.S.C. 1395ww note) is amended by striking ``December 
        #             31, 2024'' and inserting ``March 31, 2025''.

        #     [[Page 138 STAT. 1765]]

        #     SEC. 3203. EXTENSION OF ADD-ON PAYMENTS FOR AMBULANCE SERVICES.

        #         Section 1834(l) of the Social Security Act (42 U.S.C. 1395m(l)) is 
        #     amended--
        #                 (1) in paragraph (12)(A), by striking ``January 1, 2025'' 
        #             and inserting ``April 1, 2025''; and
        #                 (2) in paragraph (13), by striking ``January 1, 2025'' each 
        #             place it appears and inserting ``April 1, 2025'' in each such 
        #             place.
        #     SEC. 3204. EXTENSION OF FUNDING FOR QUALITY MEASURE ENDORSEMENT, 
        #                             INPUT, AND SELECTION.

        #         Section 1890(d)(2) of the Social Security Act (42 U.S.C. 
        #     1395aaa(d)(2)) is amended--
        #                 (1) in the first sentence--
        #                         (A) by striking ``$9,000,000'' and inserting 
        #                     ``$11,030,000''; and
        #                         (B) by striking ``December 31, 2024'' and inserting 
        #                     ``March 31, 2025''; and
        #                 (2) in the third sentence, by striking ``December 31, 2024'' 
        #             and inserting ``March 31, 2025''.
        #     SEC. 3205. EXTENSION OF FUNDING OUTREACH AND ASSISTANCE FOR LOW-
        #                             INCOME PROGRAMS.

        #         (a) State Health Insurance Assistance Programs.--Subsection 
        #     (a)(1)(B)(xiv) of section 119 of the Medicare Improvements for Patients 
        #     and Providers Act of 2008 (42 U.S.C. 1395b-3 note) is amended by 
        #     striking ``December 31, 2024, $18,750,000'' and inserting ``March 31, 
        #     2025, $22,500,000''.
        #         (b) Area Agencies on Aging.--Subsection (b)(1)(B)(xiv) of such 
        #     section 119 is amended by striking ``December 31, 2024, $18,750,000'' 
        #     and inserting ``March 31, 2025, $22,500,000''.
        #         (c) Aging and Disability Resource Centers.--Subsection 
        #     (c)(1)(B)(xiv) of such section 119 is amended by striking ``December 31, 
        #     2024, $6,250,000'' and inserting ``March 31, 2025, $8,500,000''.
        #         (d) Coordination of Efforts to Inform Older Americans About Benefits 
        #     Available Under Federal and State Programs.--Subsection (d)(2)(xiv) of 
        #     such section 119 is amended by striking ``December 31, 2024, 
        #     $18,750,000'' and inserting ``March 31, 2025, $22,500,000''.
        #     SEC. 3206. EXTENSION OF THE WORK GEOGRAPHIC INDEX FLOOR.

        #         Section 1848(e)(1)(E) of the Social Security Act (42 U.S.C. 1395w-
        #     4(e)(1)(E)) is amended by striking ``January 1, 2025'' and inserting 
        #     ``April 1, 2025''.
        #     SEC. 3207. EXTENSION OF CERTAIN TELEHEALTH FLEXIBILITIES.

        #         (a) Removing Geographic Requirements and Expanding Originating Sites 
        #     for Telehealth Services.--Section 1834(m) of the Social Security Act (42 
        #     U.S.C. 1395m(m)) is amended--
        #                 (1) in paragraph (2)(B)(iii), by striking ``ending December 
        #             31, 2024'' and inserting ``ending March 31, 2025''; and
        #                 (2) in paragraph (4)(C)(iii), by striking ``ending on 
        #             December 31, 2024'' and inserting ``ending on March 31, 2025''.

        #         (b) Expanding Practitioners Eligible to Furnish Telehealth 
        #     Services.--Section 1834(m)(4)(E) of the Social Security Act (42 U.S.C. 
        #     1395m(m)(4)(E)) is amended by striking ``ending on December 31, 2024'' 
        #     and inserting ``ending on March 31, 2025''.

        #     [[Page 138 STAT. 1766]]

        #         (c) Extending Telehealth Services for Federally Qualified Health 
        #     Centers and Rural Health Clinics.--Section 1834(m)(8)(A) of the Social 
        #     Security Act (42 U.S.C. 1395m(m)(8)(A)) is amended by striking ``ending 
        #     on December 31, 2024'' and inserting ``ending on March 31, 2025''.
        #         (d) Delaying the In-person Requirements Under Medicare for Mental 
        #     Health Services Furnished Through Telehealth and Telecommunications 
        #     Technology.--
        #                 (1) Delay in requirements for mental health services 
        #             furnished through telehealth.--Section 1834(m)(7)(B)(i) of the 
        #             Social Security Act (42 U.S.C. 1395m(m)(7)(B)(i)) is amended, in 
        #             the matter preceding subclause (I), by striking ``on or after'' 
        #             and all that follows through ``described in section 
        #             1135(g)(1)(B))'' and inserting ``on or after April 1, 2025''.
        #                 (2) Mental health visits furnished by rural health 
        #             clinics.--Section 1834(y)(2) of the Social Security Act (42 
        #             U.S.C. 1395m(y)(2)) is amended by striking ``January 1, 2025'' 
        #             and all that follows through the period at the end and inserting 
        #             ``April 1, 2025.''.
        #                 (3) Mental health visits furnished by federally qualified 
        #             health centers.--Section 1834(o)(4)(B) of the Social Security 
        #             Act (42 U.S.C. 1395m(o)(4)(B)) is amended by striking ``January 
        #             1, 2025'' and all that follows through the period at the end and 
        #             inserting ``April 1, 2025.''.

        #         (e) Allowing for the Furnishing of Audio-only Telehealth Services.--
        #     Section 1834(m)(9) of the Social Security Act (42 U.S.C. 1395m(m)(9)) is 
        #     amended by striking ``ending on December 31, 2024'' and inserting 
        #     ``ending on March 31, 2025''.
        #         (f) Extending Use of Telehealth to Conduct Face-to-face Encounter 
        #     Prior to Recertification of Eligibility for Hospice Care.--Section 
        #     1814(a)(7)(D)(i)(II) of the Social Security Act (42 U.S.C. 
        #     1395f(a)(7)(D)(i)(II)) is amended by striking ``ending on December 31, 
        #     2024'' and inserting ``ending on March 31, 2025''.
        #         (g) <<NOTE: 42 USC 1395m note.>> Program Instruction Authority.--The 
        #     Secretary of Health and Human Services may implement the amendments made 
        #     by this section through program instruction or otherwise.
        #     SEC. 3208. EXTENDING ACUTE HOSPITAL CARE AT HOME WAIVER 
        #                             AUTHORITIES.

        #         Section 1866G(a)(1) of the Social Security Act (42 U.S.C. 1395cc-
        #     7(a)(1)) is amended by striking ``December 31, 2024'' and inserting 
        #     ``March 31, 2025''.
        #     SEC. 3209. EXTENSION OF TEMPORARY INCLUSION OF AUTHORIZED ORAL 
        #                             ANTIVIRAL DRUGS AS COVERED PART D DRUGS.

        #         Section 1860D-2(e)(1)(C) of the Social Security Act (42 U.S.C. 
        #     1395w-102(e)(1)(C)) is amended by striking ``December 31, 2024'' and 
        #     inserting ``March 31, 2025''.
        #     SEC. 3210. MEDICARE IMPROVEMENT FUND.

        #         Section 1898(b)(1) of the Social Security Act (42 U.S.C. 
        #     1395iii(b)(1)) is amended by striking ``$3,197,000,000'' and inserting 
        #     ``$1,251,000,000''.

        #     [[Page 138 STAT. 1767]]

        #                             TITLE III--HUMAN SERVICES

        #     SEC. 3301. SEXUAL RISK AVOIDANCE EDUCATION EXTENSION.

        #         Section 510 of the Social Security Act (42 U.S.C. 710) is amended--
        #                 (1) in subsection (a)(1), by striking ``December 31, 2024'' 
        #             and inserting ``March 31, 2025''; and
        #                 (2) in subsection (f)(1), by striking ``December 31, 2024'' 
        #             and inserting ``March 31, 2025''.
        #     SEC. 3302. PERSONAL RESPONSIBILITY EDUCATION EXTENSION.

        #         Section 513 of the Social Security Act (42 U.S.C. 713) is amended--
        #                 (1) in subsection (a)(1)--
        #                         (A) in subparagraph (A), in the matter preceding 
        #                     clause (i), by striking ``December 31, 2024'' and 
        #                     inserting ``March 31, 2025''; and
        #                         (B) in subparagraph (B)(i), by striking ``December 
        #                     31, 2024'' and inserting ``March 31, 2025''; and
        #                 (2) in subsection (f), by striking ``December 31, 2024'' and 
        #             inserting ``March 31, 2025''.
        #     SEC. 3303. EXTENSION OF FUNDING FOR FAMILY-TO-FAMILY HEALTH 
        #                             INFORMATION CENTERS.

        #         Section 501(c)(1)(A)(viii) of the Social Security Act (42 U.S.C. 
        #     701(c)(1)(A)(viii)) is amended--
        #                 (1) by striking ``$1,500,000'' and inserting ``$3,000,000''; 
        #             and
        #                 (2) by striking ``January 1, 2025'' and inserting ``April 1, 
        #             2025''.

        #                             TITLE IV--MEDICAID

        #     SEC. 3401. ELIMINATING CERTAIN DISPROPORTIONATE SHARE HOSPITAL 
        #                             PAYMENT CUTS.

        #         Section 1923(f)(7)(A) of the Social Security Act (42 U.S.C. 1396r- 
        #     4(f)(7)(A)) is amended--
        #                 (1) in clause (i), by striking ``January 1'' and inserting 
        #             ``April 1''; and
        #                 (2) in clause (ii), by striking ``January 1'' and inserting 
        #             ``April 1''.

        #                 DIVISION D--EXTENSION OF AGRICULTURAL PROGRAMS

        #     SEC. 4101. EXTENSION OF AGRICULTURAL PROGRAMS.

        #         (a) <<NOTE: 7 USC 9001 note.>> Extension.--
        #                 (1) In general.--Except as otherwise provided in this 
        #             section and the amendments made by this section, notwithstanding 
        #             any other provision of law, the authorities (including any 
        #             limitations on such authorities) provided by each provision of 
        #             the Agriculture Improvement Act of 2018 (Public Law 115-334; 132 
        #             Stat. 4490) and each provision of law amended by that Act (and 
        #             for mandatory programs at such funding levels) as in effect 
        #             (including pursuant to section 102 of division B of

        #     [[Page 138 STAT. 1768]]

        #             the Further Continuing Appropriations and Other Extensions Act, 
        #             2024 (Public Law 118-22)) on September 30, 2024, shall continue 
        #             and be carried out until the date specified in paragraph (2).
        #                 (2) Date specified.--With respect to an authority described 
        #             in paragraph (1), the date specified in this paragraph is the 
        #             later of--
        #                         (A) September 30, 2025;
        #                         (B) the date specified with respect to such 
        #                     authority in the Agriculture Improvement Act of 2018 
        #                     (Public Law 115-334; 132 Stat. 4490) or a provision of 
        #                     law amended by that Act (Public Law 115-334; 132 Stat. 
        #                     4490); or
        #                         (C) the date in effect with respect to such 
        #                     authority pursuant to section 102 of division B of the 
        #                     Further Continuing Appropriations and Other Extensions 
        #                     Act, 2024 (Public Law 118-22)).

        #         (b) Discretionary Programs.--Programs carried out using the 
        #     authorities described in subsection (a)(1) that are funded by 
        #     discretionary appropriations (as defined in section 250(c) of the 
        #     Balanced Budget and Emergency Deficit Control Act of 1985 (2 U.S.C. 
        #     900(c))) shall be subject to the availability of appropriations.
        #         (c) <<NOTE: Applicability.>> Commodity Programs.--
        #                 (1) In general.--The provisions of law applicable to a 
        #             covered commodity (as defined in section 1111 of the 
        #             Agricultural Act of 2014 (7 U.S.C. 9011)), a loan commodity (as 
        #             defined in section 1201 of that Act (7 U.S.C. 9031)), sugarcane, 
        #             or sugar beets for the 2024 crop year pursuant to title I of 
        #             that Act (7 U.S.C. 9011 et seq.), each amendment made by 
        #             subtitle C of title I of the Agriculture Improvement Act of 2018 
        #             (Public Law 115-334; 132 Stat. 4511), and section 102 of 
        #             division B of the Further Continuing Appropriations and Other 
        #             Extensions Act, 2024 (Public Law 118-22) shall be applicable to 
        #             the 2025 crop year for that covered commodity, loan commodity, 
        #             sugarcane, or sugar beets.
        #                 (2) Extra long staple cotton.--Section 1208(a) of the 
        #             Agricultural Act of 2014 (7 U.S.C. 9038 (a)) is amended by 
        #             striking ``2024'' and inserting ``2026''.
        #                 (3) Extension of payment amount.--Section 1116(d) of the 
        #             Agricultural Act of 2014 (7 U.S.C. 9016(d)) is amended, in the 
        #             matter preceding paragraph (1), by striking ``2024'' and 
        #             inserting ``2025''.
        #                 (4) Dairy.--
        #                         (A) Dairy margin coverage.--
        #                             (i) Duration.--Section 1409 of the 
        #                         Agricultural Act of 2014 (7 U.S.C. 9059) is 
        #                         amended by striking ``December 31, 2024'' and 
        #                         inserting ``December 31, 2025''.
        #                             (ii) <<NOTE: Applicability. 7 USC 9057 
        #                         note.>> Availability of premium discount.--With 
        #                         respect to coverage for calendar year 2025, 
        #                         section 1407(g) of the Agricultural Act of 2014 (7 
        #                         U.S.C. 9057(g)) shall only apply to a 
        #                         participating dairy operation with respect to 
        #                         which the premium was reduced in accordance with 
        #                         that section (as applied to such participating 
        #                         dairy operation pursuant to section 
        #                         102(c)(2)(B)(ii) of division B of the Further 
        #                         Continuing Appropriations and Other Extensions 
        #                         Act, 2024 (Public Law 118-22)) for calendar year 
        #                         2024.

        #     [[Page 138 STAT. 1769]]

        #                         (B) Dairy forward pricing program.--Section 
        #                     1502(e)(2) of the Food, Conservation, and Energy Act of 
        #                     2008 (7 U.S.C. 8772(e)(2)) is amended by striking 
        #                     ``2027'' and inserting ``2028''.
        #                 (5) <<NOTE: 7 USC 9092 note.>>  Suspension of permanent 
        #             price support authorities.--The provisions of law specified in--
        #                         (A) subsections (a) and (b) of section 1602 of the 
        #                     Agricultural Act of 2014 (7 U.S.C. 9092)--
        #                             (i) shall not be applicable to the 2025 crops 
        #                         of covered commodities (as defined in section 1111 
        #                         of that Act (7 U.S.C. 9011)), cotton, and sugar; 
        #                         and
        #                             (ii) shall not be applicable to milk through 
        #                         December 31, 2025; and
        #                         (B) section 1602(c) of that Act (7 U.S.C. 9092(c)) 
        #                     shall not be applicable to the crops of wheat planted 
        #                     for harvest in calendar year 2025.

        #         (d) Other Programs.--
        #                 (1) Trade.--Section 302(h)(2) of the Bill Emerson 
        #             Humanitarian Trust Act (7 U.S.C. 1736f-1(h)(2)) is amended by 
        #             striking ``September 30, 2024'' and inserting ``September 30, 
        #             2025''.
        #                 (2) Grazinglands research laboratory.--Section 7502 of the 
        #             Food, Conservation, and Energy Act of 2008 (Public Law 110-246; 
        #             122 Stat. 2019; 132 Stat. 4817) is amended to read as follows:
        #     ``SEC. 7502. <<NOTE: Oklahoma. Time period.>> GRAZINGLANDS 
        #                             RESEARCH LABORATORY.

        #         ``Except as otherwise specifically authorized by law and 
        #     notwithstanding any other provision of law, the Federal land and 
        #     facilities at El Reno, Oklahoma, administered by the Secretary (as of 
        #     the date of enactment of this Act) as the Grazinglands Research 
        #     Laboratory, shall not at any time, in whole or in part, be declared to 
        #     be excess or surplus Federal property under chapter 5 of subtitle I of 
        #     title 40, United States Code, or otherwise be conveyed or transferred in 
        #     whole or in part, for the period beginning on the date of the enactment 
        #     of this Act and ending on September 30, 2025.''.
        #                 (3) Energy.--Section 9010(b) of the Farm Security and Rural 
        #             Investment Act of 2002 (7 U.S.C. 8110(b)) is amended in 
        #             paragraphs (1)(A) and (2)(A) by striking ``2024'' each place it 
        #             appears and inserting ``2025''.

        #         (e) <<NOTE: 7 USC 9001 note.>> Exceptions.--
        #                 (1) Commodities.--Subsection (a) does not apply with respect 
        #             to mandatory funding under the following provisions of law:
        #                         (A) Section 1614(c)(4) of the Agricultural Act of 
        #                     2014 (7 U.S.C. 9097(c)(4)).
        #                         (B) Section 12314(h) of the Agricultural Act of 2014 
        #                     (7 U.S.C. 2101 note; Public Law 113-79).
        #                         (C) Section 12315(f) of the Agricultural Act of 2014 
        #                     (7 U.S.C. 7101 note; Public Law 113-79).
        #                         (D) Section 12316(a) of the Agricultural Act of 2014 
        #                     (7 U.S.C. 7101 note; Public Law 113-79).
        #                 (2) Conservation.--
        #                         (A) Mandatory funding.--Subsection (a) does not 
        #                     apply with respect to mandatory funding under the 
        #                     following provisions of law for fiscal years 2024 and 
        #                     2025:

        #     [[Page 138 STAT. 1770]]

        #                             (i) Section 1240O(b)(3) of the Food Security 
        #                         Act of 1985 (16 U.S.C. 3839bb-2(b)(3)).
        #                             (ii) Section 1240R(f)(1) of the Food Security 
        #                         Act of 1985 (16 U.S.C. 3839bb-5(f)(1)).
        #                             (iii) Subparagraphs (A) and (B) of section 
        #                         1241(a)(1) of the Food Security Act of 1985 (16 
        #                         U.S.C. 3841(a)(1)).
        #                             (iv) Section 2408(g)(1) of the Agriculture 
        #                         Improvement Act of 2018 (7 U.S.C. 8351 note).
        #                         (B) Limitations.--Subsection (a) does not apply with 
        #                     respect to limitations under the following provisions of 
        #                     law:
        #                             (i) Section 1240G of the Food Security Act of 
        #                         1985 (16 U.S.C. 3839aa-7).
        #                             (ii) Section 1240L(f) of the Food Security Act 
        #                         of 1985 (16 U.S.C. 3839aa-24(f)).
        #                 (3) Nutrition.--Subsection (a) does not apply with respect 
        #             to the mandatory funding in section 203D(d)(5) of the Emergency 
        #             Food Assistance Act of 1983 (7 U.S.C. 7507(d)(5)).
        #                 (4) Rural development.--Subsection (a) does not apply with 
        #             respect to the mandatory funding in section 313B(e)(2) of the 
        #             Rural Electrification Act of 1936 (7 U.S.C. 940c-2(e)(2)).
        #                 (5) Research.--Subsection (a) does not apply with respect to 
        #             mandatory funding under the following provisions of law:
        #                         (A) Section 1446(b)(1) of the National Agricultural 
        #                     Research, Extension, and Teaching Policy Act of 1977 (7 
        #                     U.S.C. 3222a(b)(1)).
        #                         (B) Section 1672E(d)(1) of the Food, Agriculture, 
        #                     Conservation, and Trade Act of 1990 (7 U.S.C. 
        #                     5925g(d)(1)).
        #                         (C) Section 7601(g)(1)(A) of the Agricultural Act of 
        #                     2014 (7 U.S.C. 5939(g)(1)(A)).
        #                 (6) Energy.--Subsection (a) does not apply with respect to 
        #             mandatory funding under the following provisions of law:
        #                         (A) Section 9002(k)(1) of the Farm Security and 
        #                     Rural Investment Act of 2002 (7 U.S.C. 8102(k)(1)).
        #                         (B) Section 9003(g)(1)(A) of the Farm Security and 
        #                     Rural Investment Act of 2002 (7 U.S.C. 8103(g)(1)(A)).
        #                         (C) Section 9005(g)(1) of the Farm Security and 
        #                     Rural Investment Act of 2002 (7 U.S.C. 8105(g)(1)).
        #                 (7) Horticulture.--Subsection (a) does not apply with 
        #             respect to mandatory funding under the following provisions of 
        #             law:
        #                         (A) Section 7407(d)(1) of the Farm Security and 
        #                     Rural Investment Act of 2002 (7 U.S.C. 5925c(d)(1)).
        #                         (B) Section 2123(c)(4) of the Organic Foods 
        #                     Production Act of 1990 (7 U.S.C. 6522(c)(4)).
        #                         (C) Section 10606(d)(1)(C) of the Farm Security and 
        #                     Rural Investment Act of 2002 (7 U.S.C. 6523(d)(1)(C)).
        #                         (D) Section 10109(c)(1) of the Agriculture 
        #                     Improvement Act of 2018 (Public Law 115-334).
        #                 (8) Miscellaneous.--Subsection (a) does not apply with 
        #             respect to mandatory funding under the following provisions of 
        #             law:
        #                         (A) Section 209(c) of the Agricultural Marketing Act 
        #                     of 1946 (7 U.S.C. 1627a(c)).
        #                         (B) Section 12605(d) of the Agriculture Improvement 
        #                     Act of 2018 (7 U.S.C. 7632 note).

        #     [[Page 138 STAT. 1771]]

        #         (f) Reports.--
        #                 (1) <<NOTE: Continuation.>>  In general.--Subject to 
        #             paragraph (2), any requirement under a provision of law 
        #             described in paragraph (1) of subsection (a) to submit a report 
        #             on a recurring basis, and the final report under which was 
        #             required to be submitted during fiscal year 2024, shall 
        #             continue, and the requirement shall be carried out, on the same 
        #             recurring basis, until the later of the dates specified in 
        #             paragraph (2) of that subsection.
        #                 (2) <<NOTE: Applicability.>>  Appropriations required.--If 
        #             discretionary appropriations (as defined in section 250(c) of 
        #             the Balanced Budget and Emergency Deficit Control Act of 1985 (2 
        #             U.S.C. 900(c))) are required to carry out a reporting 
        #             requirement described in paragraph (1), the application of that 
        #             paragraph to that reporting requirement shall be subject to the 
        #             availability of appropriations.

        #         (g) <<NOTE: Applicability.>>  Effective Date.--This section and the 
        #     amendments made by this section shall be applied and administered as if 
        #     this section and those amendments had been enacted on September 30, 
        #     2024.

        #                             DIVISION E--OTHER MATTERS

        #     SEC. 5101. COMMODITY FUTURES TRADING COMMISSION WHISTLEBLOWER 
        #                             PROGRAM.

        #         (a) In General.--Section 1(b) of Public Law 117-25 (135 Stat. 297; 
        #     136 Stat. 2133; 136 Stat. 5984) <<NOTE: 136 Stat. 2309.>>  is amended, 
        #     in paragraphs (3) and (4), by striking ``October 1, 2024'' each place it 
        #     appears and inserting ``March 14, 2025''.

        #         (b) Effective Date.--The amendments made by subsection (a) shall 
        #     take effect as if enacted on September 30, 2024.
        #     SEC. 5102. PROTECTION OF CERTAIN FACILITIES AND ASSETS FROM 
        #                             UNMANNED AIRCRAFT.

        #         Section 210G(i) of the Homeland Security Act of 2002 (6 U.S.C. 
        #     124n(i)) is amended by striking ``December 20, 2024'' and inserting 
        #     ``March 14, 2025''.
        #     SEC. 5103. ADDITIONAL SPECIAL ASSESSMENT.

        #         Section 3014 of title 18, United States Code, is amended by striking 
        #     ``December 23, 2024'' and inserting ``March 14, 2025''.
        #     SEC. 5104. NATIONAL CYBERSECURITY PROTECTION SYSTEM AUTHORIZATION.

        #         Section 227(a) of the Federal Cybersecurity Enhancement Act of 2015 
        #     (6 U.S.C. 1525(a)) is amended by striking ``December 20, 2024'' and 
        #     inserting ``March 14, 2025''.
        #     SEC. 5105. EXTENSION OF TEMPORARY ORDER FOR FENTANYL-RELATED 
        #                             SUBSTANCES. <<NOTE:   Effective date.>> 
        #     Effective 
        #     date.

        #         Effective as if included in the enactment of the Temporary 
        #     Reauthorization and Study of the Emergency Scheduling of Fentanyl 
        #     Analogues Act (Public Law 116-114), section 2 of such'''


        # statement = get_keywords(statement, bill)
        # prntn('done xxx',len(bill))

        # text = '''

        #     The SPEAKER pro tempore laid before the House the following 
        #     communication from the Speaker:

        #                                                 Washington, DC,

        #                                                     March 10, 2025.
        #         I hereby appoint the Honorable Mariannette Miller-Meeks to 
        #         act as Speaker pro tempore on this day.
        #                                                         Mike Johnson,
        #         Speaker of the House of Representatives.

                                    


        #     '''

        # # keep at this
        # # also, somehow a block was created and is unabe to make invalid because the data is 14000 long at the job times out, wtf? how was it created?
        # start_time = time.time()
        # # if (time.time() - start_time) < 60:
        # #     prnt('is yes')
        # # else:
        # #     prnt('is no')
        # # try:
        # #     prnt((time.time() - start_time))
        # # except Exception as e:
        #     # prnt('fail123445', str(e))
        # # from joblib import parallel_backend
        # # parallel_backend("threading")
        # # def mytry(text):
        # try:
        #     prnt('1')
        #     # with parallel_backend("threading"):
        #     import multiprocessing

        #     multiprocessing.set_start_method("spawn", force=True)
        #     prnt('10')
        #     from keybert import KeyBERT
        #     import os
        #     # os.environ["TRANSFORMERS_OFFLINE"] = "1"
        #     os.environ["TOKENIZERS_PARALLELISM"] = "false"
        #     os.environ["TRANSFORMERS_PARALLELISM"] = "false"
        #     prnt('1a')
        #     kw_model = KeyBERT(model="all-MiniLM-L6-v2")
        #     prnt('1b')
        #     stop_w = []
        #     # for i in skipwords:
        #     #     stop_w.append(i)
        #     spares = {}
        #     keyword_array = []
        #     prnt('2')
        #     x = kw_model.extract_keywords(text, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
        #     n = 0
        #     prnt('3')
        #     terms = ''
        #     for i, r in x:
        #         if i not in stop_w and i not in keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
        #             keyword_array.append(i)
        #             n += 1
        #             terms = terms + i + ' '
        #     prnt('4')
        #     prnt('keyword array 1A', keyword_array)
        #     x = kw_model.extract_keywords(text, top_n=7, keyphrase_ngram_range=(1, 1), stop_words=stop_w)
        #     n = 0
        #     prnt('5')
        #     for i, r in x:
        #         if i not in stop_w and not i.isnumeric():
        #             if i in str(terms):
        #                 if i in spares:
        #                     spares[i] += 1
        #                 else:
        #                     spares[i] = 1
        #             elif n < 7:
        #                 keyword_array.append(i)
        #                 stop_w.append(i)
        #                 n += 1
        #     prnt('6')
        #     if spares:
        #         prnt('7')
        #         for term, count in spares.items():
        #             matches = 0
        #             for i in keyword_array:
        #                 if term in i:
        #                     matches += 1
        #             if count > matches or matches > 2:
        #                 for i in keyword_array:
        #                     if term in i:
        #                         keyword_array.remove(i)
        #                 keyword_array.append(term)
        
        #     prnt('8')
        #     prnt('keyword array 2B', keyword_array)
        # except Exception as e:
        #     prnt('get_keywords failB', str(e))


        # django_rq.get_queue('main').enqueue_at()
        # django_rq.get_scheduler('main').enqueue_at()
        # # run_at = now_utc() + datetime.timedelta(minutes=1)
        # # queue.enqueue_at(run_at, print, 'jobA Here!', job_timeout=120, result_ttl=3600)

        # from django_rq import get_scheduler
        # scheduler = get_scheduler('low')  # Try 'high' or 'low' if needed
        # job = scheduler.enqueue_at(now_utc() + datetime.timedelta(seconds=60), print, "job low Checking In")

        # from django_rq import get_scheduler
        # scheduler = get_scheduler('main')  # Try 'high' or 'low' if needed
        # job = scheduler.enqueue_at(now_utc() + datetime.timedelta(seconds=60), print, "job main Checking In")

        # from django_rq import get_scheduler
        # scheduler = get_scheduler('high')  # Try 'high' or 'low' if needed
        # job = scheduler.enqueue_at(now_utc() + datetime.timedelta(seconds=60), print, "job high Checking In")


        # mid = 'motSo0e082469cbcca58b8794ca610a959685'
        # p = Post.all_objects.filter(pointerId=mid).first()
        # prnt('p',p)
        # if p:
        #     p.validate()
        # b = 'genSo0e75e7be02f515bc2441892ae38bf481'
        # obj = get_dynamic_model(b, id=b)

        # prntn(convert_to_dict(obj))
        # gm = 'genSo5fe0a1afee51edf13cc2003dc07a7d82'
        # node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=dt, validated=True).order_by('-index', 'created').first()

        # node_block.adjust_settings()

        try:
            import torch
            gpu_available = torch.cuda.is_available()
        except Exception as e:
            prnt('torch chcek fail',str(e))
            gpu_available = False
        prnt('gpu_available',gpu_available)
        # if not gpu_available:
        #     import subprocess
        #     from os.path import expanduser
        #     homepath = expanduser("~")
        #     prnt('installing...')
        #     'pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu'
        #     subprocess.run([homepath + f"/Sonet/.data/env/bin/pip", 'install', 'torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu'])
        prnt('done')
        # import time

# sudo -u www-data /Users/sozed/Sonet/.data/env/bin/python -c "from keybert import KeyBERT; kw_model = KeyBERT(); print('KeyBERT loaded')"
        
#         text = '''

#         The SPEAKER pro tempore laid before the House the following 
#         communication from the Speaker:

#                                                     Washington, DC,

#                                                         March 10, 2025.
#             I hereby appoint the Honorable Mariannette Miller-Meeks to 
#             act as Speaker pro tempore on this day.
#                                                             Mike Johnson,
#             Speaker of the House of Representatives.

                                


#         '''

#         try:
#             prnt('1')
#             # import multiprocessing

#             # multiprocessing.set_start_method("fork", force=True)
#             prnt('10')
#             from keybert import KeyBERT
#             import os
#             os.environ["TOKENIZERS_PARALLELISM"] = "false"
#             prnt('1a')
#             kw_model = KeyBERT(model='all-MiniLM-L6-v2')
#             prnt('1b')
#             stop_w = []
#             for i in skipwords:
#                 stop_w.append(i)
#             spares = {}
#             keyword_array = []
#             prnt('2')
#             x = kw_model.extract_keywords(text, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
#             n = 0
#             prnt('3')
#             terms = ''
#             for i, r in x:
#                 if i not in stop_w and i not in keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
#                     keyword_array.append(i)
#                     n += 1
#                     terms = terms + i + ' '
#             prnt('4')
#             x = kw_model.extract_keywords(text, top_n=7, keyphrase_ngram_range=(1, 1), stop_words=stop_w)
#             n = 0
#             prnt('5')
#             for i, r in x:
#                 if i not in stop_w and not i.isnumeric():
#                     if i in str(terms):
#                         if i in spares:
#                             spares[i] += 1
#                         else:
#                             spares[i] = 1
#                     elif n < 7:
#                         keyword_array.append(i)
#                         stop_w.append(i)
#                         n += 1
#             prnt('6')
#             if spares:
#                 prnt('7')
#                 for term, count in spares.items():
#                     matches = 0
#                     for i in keyword_array:
#                         if term in i:
#                             matches += 1
#                     if count > matches or matches > 2:
#                         for i in keyword_array:
#                             if term in i:
#                                 keyword_array.remove(i)
#                         keyword_array.append(term)
        
#             prnt('8')
#         except Exception as e:
#             prnt('get_keywords fail', str(e))
#             from blockchain.models import logEvent
#             logEvent(e, code='592467385', func='get_keywords', log_type='Errors')
#             # time.sleep(10)
        
# https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr977.xml</a>
# <br/><a href=https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr948.xml>https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr948.xml</a>
# <br/><a href=https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr1017.xml>https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr1017.xml</a>
# <br/><a href=https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr1110.xml>https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr1110.xml</a><br/><a href=https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hres/BILLSTATUS-119hres185.xml>https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hres/BILLSTATUS-119hres185.xml</a><br/><a
# 'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr948.xml>https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr948.xml'



        # x = ['https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr948.xml']

        # r = get_bills(special='Super', dt=now_utc(), target_dt=None, target_links=['https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr1110.xml'])
        # prnt('result',r)

        # b = 'genSo5fe0a1afee51edf13cc2003dc07a7d82'

        # obj = get_dynamic_model(b, id=b)

        # prntn(convert_to_dict(obj))
        # prnt('self_node,self_node')
        # obj.func = 'super'
        # try:
        #     obj.creatorNodeId = self_node.id
        #     obj.validatorNodeId = self_node.id
        # except:
        #     pass
        # obj = sign_obj(obj, operatorData=operatorData)
        # prntn(convert_to_dict(obj))





# ~:GEN SAVE,{'object_type': 'GenericModel', 'blockchainType': 'Region', 'id': '0',                                              'created': None, 'added': None,                                             'func': 'add_bill', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'publicKey': '', 'signature': '', 'Chamber': 'House',                                         'Region_obj': 'regSob66532ffce3928d214c8c7fe791dbbee', 'Country_obj': 'regSob66532ffce3928d214c8c7fe791dbbee', 'Government_obj': 'govSo13e7fed7eb13e4daac5b72ad654f62ed', 'DateTime': '2025-02-05T00:00:00-05:00', 'modelVersion': 2, 'pointerId': 'bilSoec6617187da743aeeace1edead4a065d', 'distinction': 'x', 'Data': {'Code': 'H.R.1017', 'Text': ''}, 'type': 'BillAction'}

# ~:---initial save,GenericModel:(BillAction)-id:0-pointer:bilSoec6617187da743aeeace1edead4a065d
# ~:newId:,genSo5fe0a1afee51edf13cc2003dc07a7d82,GenericModel
# ~:#-find_or_create_chain_from_object,GenericModel:(BillAction)-id:genSo5fe0a1afee51edf13cc2003dc07a7d82-pointer:bilSoec6617187da743aeeace1edead4a065d
# ~:try create post,GenericModel:(BillAction)-id:genSo5fe0a1afee51edf13cc2003dc07a7d82-pointer:bilSoec6617187da743aeeace1edead4a065d
# ~:*--save_mutable_fields,POST-genSo5fe0a/2025-03-15 02:00:00+00:00-pstSo651ec
# ~:*-saving...,POST-genSo5fe0a/2025-03-15 02:00:00+00:00-pstSo651ec
# ~:done initial save,GenericModel:(BillAction)-id:genSo5fe0a1afee51edf13cc2003dc07a7d82-pointer:bilSoec6617187da743aeeace1edead4a065d



# ~:          {'object_type': 'GenericModel', 'blockchainType': 'Region', 'id': 'genSo5fe0a1afee51edf13cc2003dc07a7d82', 'created': '2025-03-15T02:40:46.923863+00:00', 'added': '2025-03-15T02:00:00+00:00', 'func': 'add_bill', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': 'chaSo50a583f28bb6aeb229c06ba93befb382', 'publicKey': '', 'signature': '', 'Chamber': 'House', 'Region_obj': 'regSob66532ffce3928d214c8c7fe791dbbee', 'Country_obj': 'regSob66532ffce3928d214c8c7fe791dbbee', 'Government_obj': 'govSo13e7fed7eb13e4daac5b72ad654f62ed', 'DateTime': '2025-02-05T05:00:00+00:00', 'modelVersion': 2, 'pointerId': 'bilSoec6617187da743aeeace1edead4a065d', 'distinction': 'x', 'Data': {'Code': 'H.R.1017', 'Text': ''}, 'type': 'BillAction'}
# ~:self_node,self_node
# ~:#sign_obj
# ~:failSign4958,GenericModel:(BillAction)-id:genSo5fe0a1afee51edf13cc2003dc07a7d82-pointer:bilSoec6617187da743aeeace1edead4a065d



        # b = 'bilSoe9b364a946a25f529c2d179baee72303'
        # obj = get_dynamic_model(b, id=b)
        # prntn('obj',obj)
        # if obj:
        #     iden = hash_obj_id(obj)
        #     prnt('idenhashed', iden, 'id',obj.id)
        #     v1 = verify_obj_to_data(obj, obj)
        #     prnt('v1',v1)
        #     v1 = verify_obj_to_data(obj, convert_to_dict(obj))
        #     prnt('v2',v1)
        # b = 'genSodb9aa185d28d8df0e21decf00d5b35a6'
        # obj = get_dynamic_model(b, id=b)
        # prntn('obj2',obj)
        # if obj:
        #     iden = hash_obj_id(obj)
        #     prnt('idenhashed2', iden, 'id',obj.id)
        #     v1 = verify_obj_to_data(obj, obj)
        #     prnt('v12',v1)
        #     v1 = verify_obj_to_data(obj, convert_to_dict(obj))
        #     prnt('v22',v1)

        # valid_blocks = []
        # invalid_blocks = []
        # b = Block.objects.filter(id='bloSo0920a132de9e62b33066ad66da87a0a8').first()
        # prnt(convert_to_dict(b))
        # b = UserTransaction.objects.filter(id='utraSo09246abaf5c2458eb60748b307bf3dfd').first()
        # prntn(convert_to_dict(b))


    # if receivedDt.minute < 10 and receivedDt.hour == round_time(dt=receivedDt, amount='hour').hour:
        # if 'chainData' in operatorData and 'supported' in operatorData['chainData']:
        # govPosts = Post.objects.filter(pointerType='Government', Region_obj__is_supported=True, Region_obj__id__in=self_node.supportedChains_array).exclude(Update_obj__data__has_key='EndDate').distinct('Region_obj__id').order_by('Region_obj__id','-DateTime')
        # prnt('govPosts',govPosts)
        # for post in govPosts:
        #     gov = post.Government_obj
        #     scraper_list, approved_models = get_scrape_duty(gov, dt)
        #     prnt('scraper_list',scraper_list)
        #     for i in scraper_list:
        #         if self_node.id in i['scraping_order']:
        #             prnt('FOUND!',i)



        # required_validators, node_block_data = block.get_required_validator_count(return_node_data=True, strings_only=True)
        # required_consensus = block.get_required_consensus()
        # block_time_delay = block.get_required_delay()
        # # self_node = get_self_node()
        # prntDebug('required_validators',required_validators)
        # prntDebug('required_consensus',required_consensus)
        # prntDebug('block_time_delay',block_time_delay)
        # prntDebug('node_block_data',node_block_data)

        # prnt()
        # prnt('TASK1')
        # creator_nodes, broadcast_list, validator_list = block.get_assigned_nodes(node_block_data=node_block_data)
        # # prntDebugn('creator_nodes, broadcast_list, validator_list', creator_nodes, broadcast_list, validator_list)
        # prntDebugn(f'*******creator_nodes0000:{creator_nodes}, broadcast_list000:{broadcast_list}, validator_lis000:{validator_list}')


        # prnt()
        # prnt('TASK2')
        # prntDebug('node_block_data',node_block_data)
        # creator_nodes = get_node_assignment(block, creator_only=True, node_block_data=node_block_data, strings_only=True)
        # prntDebugn('*******creator_nodes22',creator_nodes)



        # prnt()
        # prnt('TASK3')
        # creator_nodes, broadcast_list, validator_list = block.get_assigned_nodes()
        # prntDebugn(f'*****creator_nodes5555:{creator_nodes}, broadcast_list555:{broadcast_list}, validator_list555:{validator_list}')


        # prnt()
        # prnt('TASK4')
        # creator_nodes = get_node_assignment(block, creator_only=True, strings_only=True)
        # prntDebugn('******creator_nodes333',creator_nodes)


        # prnt()
        # prnt('TASK5')
        # is_valid, consensus_found, validators = check_validation_consensus(block, do_mark_valid=False, broadcast_if_unknown=False, downstream_worker=False, handle_discrepancies=False, backcheck=False, get_missing_blocks=False)

        # prntDebugn('******check_consensus:',is_valid, consensus_found)

        # creator_nodes = get_node_assignment(dummy_block, creator_only=True, strings_only=True)
        # queue = django_rq.get_queue('low')
        # queue.enqueue(process_data_packet, 'datSob868383b146d96e03ae0af600fa7fcee', job_timeout=240, result_ttl=3600)
        
        # v = Validator.objects.filter(id='valSoae5277978d9d4bc032776e6d4546251d').first()
        # prnt('v',v)
        # if v:
        #     prntn('h_i_d11',v.id,hash_obj_id(v))
        #     prntn('h_i_d22',v.id,hash_obj_id(convert_to_dict(v)))
        # chain = Blockchain.objects.filter(id='chaSoe89e21a42b442188f9d4815d6b503a4a').first()
        # prnt('chain',chain)
        #     if verify_obj_to_data(b, b):
        #         valid_blocks.append(b)
        #     else:
        #         invalid_blocks.append(b)
        # prnt('valid_blocks:',len(valid_blocks))
        # for b in valid_blocks:
        #     prnt(f'{b.id} - {b.DateTime} - {b.index} - {b.Blockchain_obj}')
        # prnt()
        # prnt('invalid_blocks:',len(invalid_blocks))
        # for b in invalid_blocks:
        #     prnt(f'{b.id} - {b.DateTime} - {b.index} - {b.Blockchain_obj}')


        # e = 'elogSo3117464a017d440e81daecfb6ac39874'
        # gov = Government.objects.all().first()
        # super_share(e, gov)

        # validator = Validator.objects.filter(id='valSo7492653f5cf35b57fa14b2a7705687cf').first()
        # prnt('result:',validator.CreatorNode_obj.User_obj.assess_super_status(dt=validator.created))


        # chain = Blockchain.objects.filter(genesisId='00So67080ba97418450da701979b944580c3').first()
        # prnt('chain',chain)
        
        # from utils.models import open_browser
                
        # driver = open_browser('https://www.google.com')

        # # element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="by-state"]/div/div/div[2]'))
        # # WebDriverWait(driver, 10).until(element_present)
        # time.sleep(1)
        # soup = BeautifulSoup(driver.page_source, 'html.parser')
        # print(soup)
        # driver.quit()

        # x = 'elogSo473068116392479ca344d216e939b191'
        # gov = Government.objects.all().first()
        # # items, completed = super_share(x, gov)
        # queue = django_rq.get_queue('low')
        # queue.enqueue(super_share, x, gov, job_timeout=310)
        # # prnt('thats all',completed)
        # users = User.objects.all()
        # prnt('users',users)
        # # for u in users:
        # #     prnt('u',u)
        # chain.add_item_to_queue(users)
        # 'bloSo3cf38daa2a934e14bff2e3b5bf186943'

        # i = 'usrSoff4130e4525d460da12bc1f45938f776'
        # u = User.objects.filter(id=i).first()
        # c = 'chaSo1b952890ea1a72cc64de973ab306e1e4'
        # chain = Blockchain.objects.filter(id=c).first()
        # chain.add_item_to_queue(u)
        
        # lo_val = ['bloSofcd938c9c4f74602ba93fd216eed8192',
        # 'bloSofe55d2744cd2436b915d78695bb24f47',]


        # court_val = ['bloSobec13bed875b4d328008780b0cdc3d66',
        # 'bloSo0df747de1c0a404d99f520276328c954',
        # 'bloSof613ba2ab3804959a82f0165db9a56fb',
        # 'bloSo7782d9f258bd4c559ae60923f05e0783',
        # # 'bloSo3cf38daa2a934e14bff2e3b5bf186943',]
        did = 'datSoab5426f5e68066072aa0ae1edfb833ac'
        # process_data_packet(did)
        # if self_node.node_name == 'Courtney':
        # #     blocks = Block.objects.filter(id__in=court_val).order_by('index')
        #     block = Block.objects.filter(id='bloSo9c010b51ac0802b177039ee530261cb9').first()
        #     broadcast_block(block)
        # elif self_node.node_name == 'Lois':
        #     x = 'datSof9824f194cdd918ee4a04f4721f226e0'
        #     queue = django_rq.get_queue('low')
        #     queue.enqueue(process_received_blocks, x, job_timeout=500)

        #     blocks = Block.objects.filter(id__in=lo_val).order_by('index')
        #     bl = Block.objects.filter(id='bloSo69bb4259641c7003d49ce01136e36983').first()
        #     if bl:
        #         bl.validated = None
        #         super(Block, bl).save()

        # for b in blocks:
        #     prnt('b',b)
        #     b.is_valid_operations()

        # b1 = Block.objects.filter(id='bloSo3cf38daa2a934e14bff2e3b5bf186943').first()
        # prnt('b1',b1)
        # if b1:
        #     b1.is_not_valid()
        # # on

        # 'bloSofcd938c9c4f74602ba93fd216eed8192'
        # b1 = Block.objects.filter(id='bloSofcd938c9c4f74602ba93fd216eed8192').first()
        # prnt('b2',b1)
        # if b1:
        #     b1.is_valid_operations()
        # ''
        # off

        # log = EventLog.objects.filter(id='elogSo6f8caf9faec4db21c563f3783233967b').first()
        # prnt('log',log)
        # process_received_blocks(log, get_missing_blocks=True, return_result=False, force_check=False)
        # # keyPair = get_operator_obj('keyPair', operatorData=operatorData)
        # # prnt('keyPair',keyPair)
        # check_validation_consensus(block, do_mark_valid=True, broadcast_if_unknown=False, downstream_worker=True, handle_discrepancies=True, backcheck=False)
        
        # prnt('passBlocks',passBlocks)
        # passBlocks.is_valid_operations()

        # success, r = connect_to_node('184.75.208.2:56455', 'utils/myip', data={'hello':'this is a test'}, operatorData=operatorData, timeout=(5,10), get=False, stream=True, node_is_string=True)
        # prnt('success',success)
        # prnt('r',r)

        # start_date = '%s-%s-%s-%s-%s' %(2025, 1, 25, 14, 30)

        # posts = Post.objects.filter(DateTime=datetime.datetime.strptime(start_date, '%Y-%m-%d-%H-%M'))
        # for p in posts:
        #     prnt(p)
        #     try:
        #         p.DateTime = p.get_pointer().DateTime
        #         p.save()
        #     except Exception as e:
        #         prnt(p.id, str(e))

        # 'updSo20bcf85b98227e8285ca4e7fbf01aec1'
        # person = Person.objects.filter(id='perSo4f60f3dcd46cf410b9e29de54151b755').first()
        # prnt('person',person)
        # i = person
        # if i.Validator_obj and i.Validator_obj.is_valid:
        #     prnt('1')
        #     if i.id in i.Validator_obj.data:
        #         prnt('2')
        #         if i.Validator_obj.data[i.id] == sigData_to_hash(i):
        #             prnt('3')
        #         else:
        #             prnt('i.Validator_obj.data[i.id]',i.Validator_obj.data[i.id])
        #             prnt('sigData_to_hash(i)',sigData_to_hash(i))
        # prnt()



        # storedModels, not_found, not_valid = get_data(['perSo4f60f3dcd46cf410b9e29de54151b755','updSo20bcf85b98227e8285ca4e7fbf01aec1'], include_related=False, return_model=True, special_request={'exclude':{'Validator_obj':None}})
        # prntDebug(f'commit_to_chain -- storedModels:{len(storedModels)}, not_found:{len(not_found)}, not_valid:{len(not_valid)}')
        # for i in not_valid:
        #     prntDebug('not valid',i.id)
        #     # if i.id in self.queuedData:
        #     #     del self.queuedData[i.id]
        #     #     prntDebug(f'removed from queue:{i.id}')
        #     #     removed += 1
        #     # i.delete()
        #     # delled += 1
        # for i in not_found:
        #     prntDebug('not found',i)
        #     # if i in self.queuedData:
        #     #     del self.queuedData[i]
        #     #     prntDebug(f'removed from queue:{i}')
        #     #     removed += 1
        # for i in storedModels:
        #     prnt(1)
        #     # if not added_dt and has_field(i, 'added') or has_field(i, 'added') and i.added < added_dt:
        #     #     if not has_field(i, 'Validator_obj') or i.Validator_obj and i.Validator_obj.is_valid and i.id in i.Validator_obj.data and i.Validator_obj.data[i.id] == sigData_to_hash(i):
        #     #         added_dt = i.added
        # # cq_list = []
        # # for i in storedModels:
        # #     cq = f'cq:{i.id}'
        # #     if i.id in self.queuedData:
        # #         cq = cq + '-A'
        # #         if not has_field(i, 'Validator_obj') or i.Validator_obj and i.Validator_obj.is_valid and i.id in i.Validator_obj.data and i.Validator_obj.data[i.id] == sigData_to_hash(i):
        # #             cq = cq + 'B'
        # #             if not added_dt or get_timeData(i) <= added_dt + datetime.timedelta(hours=2):
        # #                 cq = cq + 'C'
        # #                 dummy_block.data[i.id] = get_commit_data(i)
        # #                 if i.id in self.queuedData:
        # #                     cq = cq + 'D'
        # #                     del self.queuedData[i.id]
        # #                     # prntDebug(f'removed from queue2:{i}')



                            
        # item = Region.objects.filter(Name='North America').first()
        # prnt('item',item)
        # prnt(get_signing_data(ea))
        # prnt()
        # prnt(convert_to_dict(ea))

        # chain, item, secondChain = find_or_create_chain_from_object(item)
        # prntDebug('chain',chain)
        # if chain and has_field(item, 'blockchainId'):
        #     item.blockchainId = chain.id
        #     item.save()
        #     prntDebug('saved()')

        # item = Region.objects.filter(Name='USA').first()
        # prnt('item2',item)
        # # prnt(get_signing_data(ea))
        # # prnt()
        # # prnt(convert_to_dict(ea))

        # chain, item, secondChain = find_or_create_chain_from_object(item)
        # prntDebug('chain2',chain)
        # if chain and has_field(item, 'blockchainId'):
        #     item.blockchainId = chain.id
        #     item.save()
        #     prntDebug('saved2()')
        # dt = now_utc()
        # for model_name, model_data in get_app_name(return_model_list=True).items():
        #     if model_name not in ['Post', 'Update', 'Notification']:
        #         model = get_model(model_name)
        #         if has_field(model, 'Validator_obj'):
        #             prnt('model_name',model_name)
        #             time_field = get_timeData(model, sort='created', first_string=True)
        #             objs = model.objects.filter(Validator_obj=None).filter(**{f'{time_field}__lte': dt - datetime.timedelta(hours=12)}).count()
        #             prnt('objs len:',objs)

                # maybe once randomly per week?
        # from utils.models import run_database_maintenance
        # # for model_name, model_info in get_app_name(return_model_list=True).items():
        #     # model_class = get_model(model_name)
        # run_database_maintenance()
        #     queue = django_rq.get_queue('default')
        #     queue.enqueue(reindex_model, model_class)
        # dt=now_utc()
        # model = GenericModel
        # time_field = get_timeData(model, sort='created', first_string=True)
        # prnt('time_field',time_field)
        # objs = list(model.objects.filter(Validator_obj=None).filter(**{f'{time_field}__lte': dt - datetime.timedelta(hours=12)}).iterator(chunk_size=500))
        # exclude_idens = set()
        # delled = 0
        # unvalled_obj_count = 0
        # skipped = 0
        # validated = 0
        # runs = 0
        # val_count = 0
        # while objs and runs < 20:
        #     prnt('run',runs)
        #     runs += 1
        #     for i in objs:
        #         unvalled_obj_count += 1
        #     prnt('unvalled_obj_count',unvalled_obj_count)
        #     ids = [obj.id for obj in objs]
        #     vals = Validator.objects.filter(is_valid=True, data__has_any_key=ids).order_by('-created')

        #     # vals = Validator.objects.filter(is_valid=True, data__has_any_key=[i.id for i in objs]).order_by('-created')
        #     prnt('vals',vals)
        #     val_count += len(vals)
        #     if vals:
        #         val_map = {obj.id: val for val in vals for obj in val.data.keys()}
        #         for obj in objs:
        #             val_found = False
        #             val = val_map.get(obj.id)
        #             if val and obj.id in val.data:
        #                 if val.data[obj.id] == sigData_to_hash(obj):
        #                     validated += 1
        #                     val_found = True
        #                     obj.Validator_obj = val
        #                     super(get_model(obj.object_type), obj).save()
        #                     prnt('saved',obj.id)
        #             if not val_found and getattr(obj, time_field) < dt - datetime.timedelta(hours=36):
        #                 # if obj.object_type == obj.blockchainType:
        #                 #     del_chains.append(obj.id)
        #                 obj.delete()
        #                 delled += 1
        #             else:
        #                 skipped += 1
        #                 if obj.id not in exclude_idens:
        #                     exclude_idens.add(obj.id)
        #     else:
        #         for obj in objs:
        #             if getattr(obj, time_field) < dt - datetime.timedelta(hours=36):
        #                 # if obj.object_type == obj.blockchainType:
        #                 #     del_chains.append(obj.id)
        #                 obj.delete()
        #                 delled += 1
        #             else:
        #                 skipped += 1
        #                 if obj.id not in exclude_idens:
        #                     exclude_idens.add(obj.id)
        #     prnt(f'skipped:{skipped} delled:{delled} validated:{validated}')
        #     objs = list(model.objects.filter(Validator_obj=None).exclude(id__in=exclude_idens).filter(**{f'{time_field}__lte': dt - datetime.timedelta(hours=12)}).iterator(chunk_size=500))
        
        
                            

        end_time = now_utc()
        print(end_time - start_time)
        return render(request, "utils/dummy.html", {"result": 'Success'})

def daily_summarizer_view(request):
    if request.user.is_superuser:
        daily_summarizer(None)
        # queue = django_rq.get_queue('default')
        # queue.enqueue(send_notifications, job_timeout=500)
        return render(request, "utils/dummy.html", {"result": 'Success'})

def run_notifications_view(request):
    if request.user.is_superuser:
        send_notifications('Sozed')
        # queue = django_rq.get_queue('default')
        # queue.enqueue(send_notifications, job_timeout=500)
        return render(request, "utils/dummy.html", {"result": 'Success'})

def add_test_notification_view(request):
    if request.user.is_superuser:
        # prnt('test notification')

        sozed = User.objects.get(username='d704bb87a7444b0ab304fd1566ee7aba')
        sozed.alert('%s-%s' %(datetime.datetime.now(), 'test notify'), None, 'test body')

        # request.user.alert('new test notification', '/', 'test body')
        return render(request, "utils/dummy.html", {"result": 'Success'})

def remove_notification_view(request, iden):
    n = Notification.objects.filter(id=iden, user=request.user)[0]
    n.new = False
    n.save()
    return render(request, "utils/dummy.html", {"result": 'Success'})

def view(request):
    def stream_generator():
        t_start = datetime.datetime.now()
        stream = ollama.chat(
            model='llama3',
            messages=[{'role': 'user', 'content': prompt}],
            stream=True,
        )
        totes = ''
        for chunk in stream:
            x = chunk['message']['content']
            totes = totes + x
            yield x
        t_end = datetime.datetime.now() - t_start
    response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response


def html_playground_view(request):
    # if request.user.is_superuser:
    # return render(request, "utils/playground.html")

    # import hashlib

    # def deterministic_sort(items, seed):
    #     return sorted(items, key=lambda item: hashlib.sha256((seed + item).encode('utf-8')).hexdigest())

    # node_ids = ['node1','node2','node3','node4','node5','node6']

    # node_ids = ['node1', 'node2', 'node3', 'node4', 'node5', 'node6', 'node7', 'node8', 'node9', 'node10', 'node11', 'node12', 'node13', 'node14', 'node15', 'node16', 'node17', 'node18', 'node19', 'node20', 'node21', 'node22', 'node23', 'node24', 'node25', 'node26', 'node27', 'node28', 'node29', 'node30', 'node31', 'node32', 'node33', 'node34', 'node35', 'node36', 'node37', 'node38', 'node39', 'node40', 'node41', 'node42', 'node43', 'node44', 'node45', 'node46', 'node47', 'node48', 'node49']
    # # shuffled_nodes = deterministic_sort(node_ids, "myseed")
    # # prntn('shuffled_nodes', shuffled_nodes)

    # import hashlib
    # prnt('now',now_utc())
    # prnt('now',now_utc().isoformat())


    # # from datetime import datetime, timezone

    # def dt_to_string(dt_input):
    #     if isinstance(dt_input, str):
    #         # Parse ISO string to datetime object
    #         dt = datetime.datetime.fromisoformat(dt_input)
    #     elif isinstance(dt_input, datetime.datetime):
    #         dt = dt_input
    #     else:
    #         raise TypeError("Input must be a datetime object or an ISO 8601 string")

    #     # Normalize to UTC
    #     if dt.tzinfo is None:
    #         dt = dt.replace(tzinfo=datetime.timezone.utc)
    #     else:
    #         dt = dt.astimezone(datetime.timezone.utc)

    #     # Return JS-style ISO string (milliseconds precision, 'Z' suffix)
    #     return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # prnt(dt_to_string("2025-05-26T20:41:30.905919+00:00"))
    # prnt(dt_to_string(now_utc()))
    # prnt(dt_to_string(now_utc().isoformat()))
    # prnt()

    # # from datetime import datetime, timezone

    # dt_str = '2025-05-26T20:55:03.272Z'

    # def string_to_dt(dt_str):
    #     if isinstance(dt_str, datetime.datetime):
    #         return dt_str
    #     if isinstance(dt_str, str):
    #         if 'Z' in dt_str:
    #             dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    #             print(dt)
    #             return dt
    #         return datetime.datetime.fromisoformat(dt_str)
    #     return None

    # prnt('datetimeify', string_to_dt(dt_str))
    # prnt('datetimeify2', string_to_dt(now_utc()))
    # prnt('datetimeify3', string_to_dt(now_utc().isoformat()))

    # def browser_shuffle(text_input, dt, node_ids): # works in javascript so can be run by user but is much slower
    #     if isinstance(dt, datetime.datetime):
    #         dt_str = dt.isoformat()
    #     elif isinstance(dt, str):
    #         dt_str = dt
    #     else:
    #         raise ValueError("dt must be a datetime or ISO string")
    #     seed_input = f"{text_input}_{dt_str}"
    #     prnt('seed_input', seed_input)
    #     # f"{text_input}_{dt_str}_{item}"
    #     prnt('seed_inputEE', seed_input + node_ids[0])
    #     return sorted(node_ids, key=lambda item: hashlib.sha256((seed_input + item).encode('utf-8')).hexdigest())
    # prnt('browser_shuffle',browser_shuffle("myseed", '2025-05-26T20:55:03.272Z', node_ids))

    # 2025-05-23T14:00:00+00:00

    # # node_ids = ['node1','node2','node3','node4','node5','node6','node7','node8','node']
    # # shuffled_nodes = deterministic_sort(node_ids, "myseed2")
    # # prntn('shuffled_nodes2', shuffled_nodes)
    # # shuffled_nodes = deterministic_sort(node_ids, "myseed3")
    # # prntn('shuffled_nodes3', shuffled_nodes)
    # # shuffled_nodes = deterministic_sort(node_ids, "myseed4")
    # # prntn('shuffled_nodes4', shuffled_nodes)
    # # n = 0
    # # idens = []
    # # for i in range(1,51):
    # #     prnt(i)
    # #     idens.append(f'node{i}')
    # # prntn(f'idens = {idens}')


    # def shuffle_nodes(node_ids, seed_input):
    #     # if isinstance(dt, datetime.datetime):
    #     #     dt_str = dt.isoformat()
    #     # elif isinstance(dt, str):
    #     #     dt_str = dt
    #     # else:
    #     #     raise ValueError("dt must be a datetime or ISO string")
        
    #     # node_ids = ['node1','node2','node3','node4','node5','node6']
    #     # seed_input = f"myseed"
    #     # seed_input = f"{text_input}_{dt_str}"
    #     seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
    #     seed_int = int(seed_hash, 16)
    #     rng = random.Random(seed_int)
    #     node_ids.sort()
    #     shuffled_nodes = node_ids.copy()
    #     rng.shuffle(shuffled_nodes)
    #     # prnt('shuffled_nodes',shuffled_nodes)
    #     return shuffled_nodes

    # # for i in range(1, 51):

    #     # prntn('deterministic_sort', deterministic_sort(node_ids, "myseed2"))

    # import hashlib

    # def deterministic_sort_3(items, seed):
    #     def get_hash(item):
    #         return hashlib.sha256((seed + item).encode('utf-8')).hexdigest()

    #     hashes = [(item, get_hash(item)) for item in items]
    #     hashes.sort(key=lambda x: x[1])
    #     return [item for item, _ in hashes]
    
    # import hashlib

    # def deterministic_sort_3(items, seed):
    #     def get_hash(item):
    #         return hashlib.md5((seed + item).encode('utf-8')).hexdigest()
    #     return [item for item, _ in sorted(
    #         [(item, get_hash(item)) for item in items],
    #         key=lambda x: x[1]
    #     )]


    # def deterministic_sort_2(items, seed):
    #     return sorted(items, key=lambda item: hashlib.md5((seed + item).encode('utf-8')).hexdigest())
    # # from datetime import datetime, timedelta

    # # Start time (you can customize this)
    # current_time = now_utc()
    # start_time1 = now_utc()
    # # current_time = round_time(dt=current_time, dir='down', amount='hour')

    # # Number of hours to iterate (change as needed)
    # hours_to_iterate = 10
    # import datetime


    # node_ids = []
    # for i in range(1,1001):
    #     # prnt(i)
    #     node_ids.append(f'node{i}')
    # # prntn(f'node_ids = {node_ids}')
    # # # Loop through each hour
    # results1 = {}
    # results2 = {}
    # results3 = {}
    # # for i in range(11):
    # #     current_time += datetime.timedelta(hours=1)
    # #     # results1 = run_me(current_time, opt=1, results=results1)
    # #     # results2 = run_me(current_time, opt=2, results=results2)
    # #     # results3 = run_me(current_time, opt=5, results=results3)
    # #     # run2(current_time, opt=2)
    # #     dt_str = current_time.isoformat()
    # #     text_input = f'func_{i}'
    # seed_input = f'func_me'
    # #     seed_input = f"{text_input}_{dt_str}"
    # #     prntn('seed_input',seed_input)
    # # start_time = now_utc()
    # # t1 = deterministic_sort(node_ids, seed_input)
    # # start_time2 = now_utc()
    # # t2 = deterministic_sort_2(node_ids, seed_input)
    # # start_time3 = now_utc()
    # # t3 = deterministic_sort(node_ids, seed_input)
    # # start_time4 = now_utc()
    # # #     if t1 == t2 == t3:
    # # if t1 == t2:
    # #     prnt('all match!')
    # # #     else:
    # # #         if t1 == t2:
    # # #             prnt('t1-t2 match')
    # # #         if t1 == t3:
    # # #             prnt('t1-t3 match')
    # # #         if t3 == t2:
    # # #             prnt('t3-t2 match')
    # # else:
    # #     prnt('no match...')
    # # prnt(f't1A = {start_time2 - start_time}')
    # # prnt(f't2B = {start_time3 - start_time2}')
    # # prnt(f't3C = {start_time4 - start_time3}')
    # #     # prnt('--')
    # #     # # prnt('new_mthod', deterministic_sort(node_ids, seed_input))
    # # mid_time = now_utc()
    # # # prnt('time:', mid_time - start_time)
    # # t4 = shuffle_nodes(node_ids, seed_input)
    # # end_time = now_utc()
    # # prnt(f't4D = {end_time - mid_time}')
    #     # # prnt(':', end_time - mid_time)
    #     # # if t1 == t3:
    #     # #     prnt('match3!')
    #     # # else:
    #     # #     prnt('no match3...')

    # # import hashlib, random

    # # node_ids = ['node1','node2','node3','node4','node5','node6']
    # # seed_input = "myseed"
    # # seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
    # # seed_int = int(seed_hash, 16)
    # # rng = random.Random(seed_int)
    # # node_ids.sort()
    # # shuffled_nodes = node_ids.copy()
    # # rng.shuffle(shuffled_nodes)
    # # print('shuffled_nodes', shuffled_nodes)

    # # prnt()
    # node_ids = []
    # for i in range(1,50000):
    #     # prnt(i)
    #     node_ids.append(f'node{i}')
    # # node_ids = ['node1','node2','node3','node4','node5','node6']
    # # prntn(f'node_ids_final = {node_ids}')
    # # t3 = shuffle_nodes(node_ids, 'myseed')
    # # prntn('final = ',t3)

    # # from typing import List

    # # # FNV-1a 32-bit
    # # def fnv1a_32(s: str) -> int:
    # #     h = 0x811c9dc5
    # #     for c in s:
    # #         h ^= ord(c)
    # #         h = (h * 0x01000193) % (1 << 32)
    # #     return h

    # # # SplitMix64 for seeding
    # # class SplitMix64:
    # #     def __init__(self, seed: int):
    # #         self.state = seed & 0xFFFFFFFFFFFFFFFF

    # #     def next(self):
    # #         self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    # #         z = self.state
    # #         z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & 0xFFFFFFFFFFFFFFFF
    # #         z = (z ^ (z >> 27)) * 0x94D049BB133111EB & 0xFFFFFFFFFFFFFFFF
    # #         return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF

    # # # Shuffle using seeded PRNG
    # # def deterministic_shuffle(lst: List[str], seed: str) -> List[str]:
    # #     seed_int = fnv1a_32(seed)
    # #     rng = SplitMix64(seed_int)
    # #     lst = sorted(lst)
    # #     result = lst.copy()
    # #     for i in range(len(result) - 1, 0, -1):
    # #         j = rng.next() % (i + 1)
    # #         result[i], result[j] = result[j], result[i]
    # #     return result

    # # Test
    # # node_ids = ['node1', 'node2', 'node3', 'node4', 'node5', 'node6']
    # # prntn(deterministic_shuffle(node_ids, "myseed"))

    # prnt('-_-')

    # # def fnv1a_32(s):
    # #     h = 0x811c9dc5
    # #     for c in s.encode('utf-8'):
    # #         h ^= c
    # #         h *= 0x01000193
    # #         h &= 0xffffffff
    # #     return h

    # # def seeded_shuffle(items, seed):
    # #     return sorted(items, key=lambda x: fnv1a_32(x + seed))
    
    # # def fnv1a_32(s):
    # #     h = 0x811c9dc5
    # #     for b in s.encode('utf-8'):
    # #         h ^= b
    # #         h = (h * 0x01000193) & 0xffffffff  # force 32-bit
    # #     return h

    # # def seeded_shuffle(items, seed):
    # #     return sorted(items, key=lambda x: fnv1a_32(x + seed))


    # # # Example
    # # # items = ['obj1', 'obj2', 'obj3']
    # # seed = "my_seed"
    # # # print(seeded_shuffle(node_ids, seed))


    # def deterministic_sort(items, seed):
    #     return sorted(items, key=lambda item: hashlib.sha256((seed + item).encode('utf-8')).hexdigest())


    # seed_input = f'func_me'
    # #     seed_input = f"{text_input}_{dt_str}"
    # # #     prntn('seed_input',seed_input)
    # start_time = now_utc()
    # t1 = deterministic_sort(node_ids, seed_input)
    # start_time2 = now_utc()
    # t2 = shuffle_nodes(node_ids, seed_input)
    # start_time3 = now_utc()
    # t3 = deterministic_sort(node_ids, seed_input)
    # start_time4 = now_utc()
    # # start_time5 = now_utc()
    # t4 = shuffle_nodes(node_ids, seed_input)
    # start_time6 = now_utc()
    # # if t1 == t2 == t3:
    # # # if t1 == t2:
    # #     prnt('all match!')
    # # else:
    # # if t1 == t3:
    # #     prnt('t1-t2 match')
    # if t1 == t3:
    #     prnt('t1-t3 match')
    # if t2 == t4:
    #     prnt('t2-t4 match')
    # # else:
    # #     prnt('no match...')
    # prnt(f't1 = {start_time2 - start_time}')
    # prnt(f't2 = {start_time3 - start_time2}')
    # prnt(f't3 = {start_time4 - start_time3}')
    # prnt(f't4 = {start_time6 - start_time4}')

    # prnt()
    # prnt((start_time4 - start_time3)*1000)
    # prnt((start_time6 - start_time4)*1000)

    # prntn(f'node_ids_final = {len(node_ids)}')

    # def deterministic_sort_2(items, seed):
    #     return sorted(items, key=lambda item: hashlib.md5((seed + item).encode('utf-8')).hexdigest())
    
    # node_ids = ['node1', 'node2', 'node3', 'node4', 'node5', 'node6', 'node7', 'node8', 'node9', 'node10', 'node11', 'node12', 'node13', 'node14', 'node15', 'node16', 'node17', 'node18', 'node19', 'node20', 'node21', 'node22', 'node23', 'node24', 'node25', 'node26', 'node27', 'node28', 'node29', 'node30', 'node31', 'node32', 'node33', 'node34', 'node35', 'node36', 'node37', 'node38', 'node39', 'node40', 'node41', 'node42', 'node43', 'node44', 'node45', 'node46', 'node47', 'node48', 'node49']
    # t1 = deterministic_sort(node_ids, 'myseed')
    # prntn(t1)
    # t1 = shuffle_nodes(node_ids, 'myseed')
    # prntn(t1)
# shuffle_nodes
# ~:shuffled_nodes,['node34', 'node46', 'node48', 'node37', 'node9', 'node4', 'node6', 'node33', 'node30', 'node3', 'node13', 'node8', 'node15', 'node42', 'node49', 'node29', 'node20', 'node1', 'node23', 'node44', 'node39', 'node38', 'node31', 'node45', 'node2', 'node10', 'node11', 'node18', 'node27', 'node19', 'node7', 'node24', 'node32', 'node28', 'node16', 'node21', 'node14', 'node40', 'node17', 'node36', 'node47', 'node26', 'node5', 'node35', 'node12', 'node22', 'node41', 'node43', 'node25']

# ~:shuffled_nodes2,['node28', 'node47', 'node26', 'node35', 'node32', 'node17', 'node41', 'node21', 'node7', 'node40', 'node20', 'node2', 'node45', 'node33', 'node36', 'node14', 'node39', 'node13', 'node1', 'node43', 'node23', 'node6', 'node3', 'node38', 'node34', 'node49', 'node31', 'node25', 'node24', 'node44', 'node30', 'node19', 'node5', 'node8', 'node42', 'node22', 'node9', 'node12', 'node48', 'node11', 'node4', 'node16', 'node10', 'node15', 'node27', 'node46', 'node29', 'node18', 'node37']

# ~:shuffled_nodes3,['node12', 'node19', 'node36', 'node39', 'node17', 'node27', 'node4', 'node42', 'node38', 'node5', 'node26', 'node46', 'node43', 'node32', 'node37', 'node31', 'node25', 'node34', 'node2', 'node20', 'node9', 'node10', 'node48', 'node21', 'node49', 'node23', 'node7', 'node13', 'node24', 'node47', 'node35', 'node29', 'node3', 'node45', 'node22', 'node14', 'node16', 'node30', 'node8', 'node41', 'node1', 'node6', 'node15', 'node40', 'node18', 'node11', 'node33', 'node28', 'node44']

# ~:shuffled_nodes4,['node11', 'node2', 'node19', 'node5', 'node39', 'node35', 'node32', 'node38', 'node8', 'node41', 'node13', 'node18', 'node42', 'node37', 'node26', 'node45', 'node17', 'node23', 'node47', 'node30', 'node40', 'node14', 'node46', 'node6', 'node48', 'node25', 'node49', 'node28', 'node1', 'node34', 'node20', 'node4', 'node24', 'node3', 'node31', 'node43', 'node22', 'node21', 'node7', 'node16', 'node15', 'node29', 'node27', 'node10', 'node44', 'node12', 'node9', 'node33', 'node36']




# shuffled_nodes (49) ['node34', 'node46', 'node48', 'node37', 'node9', 'node4', 'node6', 'node33', 'node30', 'node3', 'node13', 'node8', 'node15', 'node42', 'node49', 'node29', 'node20', 'node1', 'node23', 'node44', 'node39', 'node38', 'node31', 'node45', 'node2', 'node10', 'node11', 'node18', 'node27', 'node19', 'node7', 'node24', 'node32', 'node28', 'node16', 'node21', 'node14', 'node40', 'node17', 'node36', 'node47', 'node26', 'node5', 'node35', 'node12', 'node22', 'node41', 'node43', 'node25']
# html_playground1:89 shuffled_nodes2 (49) ['node28', 'node47', 'node26', 'node35', 'node32', 'node17', 'node41', 'node21', 'node7', 'node40', 'node20', 'node2', 'node45', 'node33', 'node36', 'node14', 'node39', 'node13', 'node1', 'node43', 'node23', 'node6', 'node3', 'node38', 'node34', 'node49', 'node31', 'node25', 'node24', 'node44', 'node30', 'node19', 'node5', 'node8', 'node42', 'node22', 'node9', 'node12', 'node48', 'node11', 'node4', 'node16', 'node10', 'node15', 'node27', 'node46', 'node29', 'node18', 'node37']
# html_playground1:91 shuffled_nodes3 (49) ['node12', 'node19', 'node36', 'node39', 'node17', 'node27', 'node4', 'node42', 'node38', 'node5', 'node26', 'node46', 'node43', 'node32', 'node37', 'node31', 'node25', 'node34', 'node2', 'node20', 'node9', 'node10', 'node48', 'node21', 'node49', 'node23', 'node7', 'node13', 'node24', 'node47', 'node35', 'node29', 'node3', 'node45', 'node22', 'node14', 'node16', 'node30', 'node8', 'node41', 'node1', 'node6', 'node15', 'node40', 'node18', 'node11', 'node33', 'node28', 'node44']
# html_playground1:93 shuffled_nodes4 (49) ['node11', 'node2', 'node19', 'node5', 'node39', 'node35', 'node32', 'node38', 'node8', 'node41', 'node13', 'node18', 'node42', 'node37', 'node26', 'node45', 'node17', 'node23', 'node47', 'node30', 'node40', 'node14', 'node46', 'node6', 'node48', 'node25', 'node49', 'node28', 'node1', 'node34', 'node20', 'node4', 'node24', 'node3', 'node31', 'node43', 'node22', 'node21', 'node7', 'node16', 'node15', 'node29', 'node27', 'node10', 'node44', 'node12', 'node9', 'node33', 'node36']

    # import hashlib
    # def shuffle_nodes(node_ids=None, text_input=None, dt=None):
    #     # if isinstance(dt, datetime.datetime):
    #     #     dt_str = dt.isoformat()
    #     # elif isinstance(dt, str):
    #     #     dt_str = dt
    #     # else:
    #     #     raise ValueError("dt must be a datetime or ISO string")
        
    #     node_ids = ['node1','node2','node3','node4','node5','node6']
    #     seed_input = f"myseed"
    #     # seed_input = f"{text_input}_{dt_str}"
    #     seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
    #     seed_int = int(seed_hash, 16)
    #     rng = random.Random(seed_int)
    #     node_ids.sort()
    #     shuffled_nodes = node_ids.copy()
    #     rng.shuffle(shuffled_nodes)
    #     prnt('shuffled_nodes',shuffled_nodes)
    #     return shuffled_nodes
    # shuffle_nodes()


    # Derived Seed (Hex): 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # html_playground1:38 Private Key: 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # html_playground1:39 Public Key: 04571ccc4ddd01e08777a8b725623cc2b4c4079b20889266ed7326cc906d14c28f71434a40962548110ced9baeace1cf777d0b1b75eac71de348bca212e48a6eb0
    # html_playground1:52 Signature: 304402204ade0d0f94bece6a04b7f60dbb90d6f09f00260c7edef6a55a6ead024ebb9a6d022027e0d578cebab5616e90ab3c6964738740a1398d98049c546e72ce9ddf89c494


    # Derived seed: 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # Private Key (hex): 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # Public Key (hex): 04571ccc4ddd01e08777a8b725623cc2b4c4079b20889266ed7326cc906d14c28f71434a40962548110ced9baeace1cf777d0b1b75eac71de348bca212e48a6eb0


    # new:
    # ~:salt,b'P\xe3Q\xea+\x06\xe6li\xc1x\x99\xedt\x0f\xe0:\xdf\xd9\x9c+\xf3\x88=\xd6\xa3\x9f\xaa\x98\x80\x1c\x07'
    # 1 0:00:00.000311
    # ~:Derived seed:,5f36f79cc6769e9bebf11510418b7fcde70da51021b03d2dae8a15f271f0cfc3
    # ~:Private Key (hex):,5f36f79cc6769e9bebf11510418b7fcde70da51021b03d2dae8a15f271f0cfc3
    # ~:Public Key (hex):,044f67a25fc08414cbd2a71645c3c7d70a9e00c82ab71688023d94dbd043d5ff6fb8769fba9b61f179b1ac6ca3bda7c65472071f4c2de2b5e2c11a4d0b3381fea3

    # js:
    # saltHex: 50e351ea2b06e66c69c17899ed740fe03adfd99c2bf3883dd6a39faa98801c07
    # html_playground1:96 Derived Seed (Hex): 5f36f79cc6769e9bebf11510418b7fcde70da51021b03d2dae8a15f271f0cfc3
    # html_playground1:104 Private Key: 5f36f79cc6769e9bebf11510418b7fcde70da51021b03d2dae8a15f271f0cfc3
    # html_playground1:105 Public Key: 044f67a25fc08414cbd2a71645c3c7d70a9e00c82ab71688023d94dbd043d5ff6fb8769fba9b61f179b1ac6ca3bda7c65472071f4c2de2b5e2c11a4d0b3381fea3
    # html_playground1:117 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:122 Signature: 30450221009d7049780ac97db582f637eb49a7759e85b0c4399d20f1475897cebc840f8ea902207a2277f276e51b174f0d900022513557cd3ecb230de3c623f1cb2ad6ce866824





    # ~:salt,b'\x81RHZ\x03\x9b\xbd[\xb1l\xb7\xf0\xb2\xc4\xb1\xad\x98[o$\xf4Ud\xf8)\x88\x11\xd8\x9d\xc9\xa3\x14'
    # 1 0:00:00.000156
    # ~:Derived seed:,057009ef08353a15d83170e43f0e55af63c90d0b8ae21f55cab14cdc0f0cb2dd
    # ~:Private Key (hex):,057009ef08353a15d83170e43f0e55af63c90d0b8ae21f55cab14cdc0f0cb2dd
    # ~:Public Key (hex):,04d58736334973f9323a8f297e168ab56cbbc520ac6f5ebea4e338f392efa1f68513daefceec4d674e5991911f53dd870770d69d96fca3e4214a2fa8ccec1ffdc3


    # saltHex: 8152485a039bbd5bb16cb7f0b2c4b1ad985b6f24f45564f8298811d89dc9a314
    # html_playground1:96 Derived Seed (Hex): 057009ef08353a15d83170e43f0e55af63c90d0b8ae21f55cab14cdc0f0cb2dd
    # html_playground1:104 Private Key: 057009ef08353a15d83170e43f0e55af63c90d0b8ae21f55cab14cdc0f0cb2dd
    # html_playground1:105 Public Key: 04d58736334973f9323a8f297e168ab56cbbc520ac6f5ebea4e338f392efa1f68513daefceec4d674e5991911f53dd870770d69d96fca3e4214a2fa8ccec1ffdc3
    # html_playground1:117 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:122 Signature: 304402205e75661b91819a0900921e706f285d0a4e3b93c59840a63829fbacc9f7db0ca002202e180dd0d526bc151ae66a875b6444f5be7c004863fc3f6cd06fc6f9609dcf8f




    # Mnemonic: void diagram address drill tackle refuse tornado extend category crazy disorder bottom
    # html_playground1:74 Full Seed (512-bit hex): afd77f25f154ea28efc5fe0b71cb1537d3b34fe45791cca929c67cbe376cf2d93befce1c6b36d4718d64920790348618d2ac018c33c7e4e5bbe97f6860f0afd4
    # html_playground1:80 Derived 32-byte seed for key (hex): a3ee91054ff255562f3f4b4eba4da650de6386e69d7db318318b6c843d292bb3
    # html_playground1:92 saltHex: cb09c4179abe02831e0a342f9857d5a5457760e6ec419a59256e9f2c59925f6f
    # html_playground1:116 Derived Seed (Hex): ab28576def6d336cff20017e8c289dd3ac7925ecddac56f9680c15e0b2419e18
    # html_playground1:124 Private Key: ab28576def6d336cff20017e8c289dd3ac7925ecddac56f9680c15e0b2419e18
    # html_playground1:125 Public Key: 0460496efb1fe8f49d09ab8a7ff8f334bb2285dac46f7f9a9b1e9e3965ba81d3a3d57080622aa969bda1506fdf949c58a1253c7b37b11251a71e5508a379d6288c
    # html_playground1:137 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:142 Signature: 3045022100da191cf53774fff8089af1bdd92eaa7378ce37a56b6bf2b26270a8efd446d3db022029e0d59afa6030d9543de69cd68764c0cd39ddf924b54cc6559d0292da318f19
    
    # ~:salt,b'\xcb\t\xc4\x17\x9a\xbe\x02\x83\x1e\n4/\x98W\xd5\xa5Ew`\xe6\xecA\x9aY%n\x9f,Y\x92_o'
    # 1 0:00:00.000065
    # ~:Derived seed:,ab28576def6d336cff20017e8c289dd3ac7925ecddac56f9680c15e0b2419e18
    # ~:Private Key (hex):,ab28576def6d336cff20017e8c289dd3ac7925ecddac56f9680c15e0b2419e18
    # ~:Public Key (hex):,0460496efb1fe8f49d09ab8a7ff8f334bb2285dac46f7f9a9b1e9e3965ba81d3a3d57080622aa969bda1506fdf949c58a1253c7b37b11251a71e5508a379d6288c




    # Mnemonic (24 words): weekend pluck sustain lend result oval first electric match current income file diamond tube electric reward follow hood various arrow convince noble minimum mutual
    # html_playground1:80 saltHex: 27cfa620ae9b0316b2da606c49e57a21e4314e4eaa62dd776395543e584d6e51
    # html_playground1:104 Derived Seed (Hex): bcba188bf70f7543d17293b310c047248587268a00625248bfc6c660ab5c345c
    # html_playground1:112 Private Key: bcba188bf70f7543d17293b310c047248587268a00625248bfc6c660ab5c345c
    # html_playground1:113 Public Key: 041855413eda81edda2823889047907caa6b35fb0e811d856d4862991a1ea8aed5336356e6c6dc3de962c780a9f513e3c9ac7924dd5fae6a48d9c9f0a7f7d68477
    # html_playground1:125 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:130 Signature: 304402206fb84f1335554a37def88408e1e220f91da62a6fb496bca91e1732f4833baaca02204ac44375c342cb3066cc7a655023d25e81c685b308ac045c45b73518ed76b873
    # html_playground1:173 hashed12 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:178 Signature2: 304402206fb84f1335554a37def88408e1e220f91da62a6fb496bca91e1732f4833baaca02204ac44375c342cb3066cc7a655023d25e81c685b308ac045c45b73518ed76b873


    # Mnemonic (24 words): parent icon certain river guide casual toast wrong arrow link stuff exhaust unveil shiver elite govern taste isolate social ill bag include lounge cook
    # html_playground1:80 saltHex: b6c9f735d9b0ffb7315b152f01892a8f87012193c50a440634a3f10dc6af86cb
    # html_playground1:104 Derived Seed (Hex): 025a3c13ff91eb423a411a9e7e490fa5210d2ae62d4ad7d7ee8f13a77a18b877
    # html_playground1:112 Private Key: 025a3c13ff91eb423a411a9e7e490fa5210d2ae62d4ad7d7ee8f13a77a18b877
    # html_playground1:113 Public Key: 044ec1a7fee1d6670b9b13418a15177ba5aa8d16f27bd674e7dde0910b373bc29d9cafe718c20fb04f5cc26aa469f757900fcf81f6ac8415af1eb2a63378583a8e
    # html_playground1:125 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:130 Signature: 304402207bcd7843ae08293a4f14570b62959a30b3f70d0e45f7b1974ff79071e097a5400220400e633b924de4c12b3d472343f090d7ee66e263bafea3743a73d24f6d052a53
    # html_playground1:171 loaded_privateKey bcba188bf70f7543d17293b310c047248587268a00625248bfc6c660ab5c345c
    # html_playground1:174 hashed12 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:179 Signature2: 304402206fb84f1335554a37def88408e1e220f91da62a6fb496bca91e1732f4833baaca02204ac44375c342cb3066cc7a655023d25e81c685b308ac045c45b73518ed76b873



    # key found
    # html_playground1:110 Mnemonic (24 words): exact price basket arena gentle carry exact random priority ball later amused switch mix bind spot enhance surround fiber enact hero erupt alert year
    # html_playground1:120 saltHex: a30dfd4d7ca19a451121d02b47e886709825e11245c32fdf04327ae89f8ab727
    # html_playground1:144 Derived Seed (Hex): 4b3454646fba5f461f6f3de5b5160a4cd458d10ac26d433b882ec6b69636957c
    # html_playground1:152 Private Key: 4b3454646fba5f461f6f3de5b5160a4cd458d10ac26d433b882ec6b69636957c
    # html_playground1:153 Public Key: 042432fb2496d4218e62027539345a4066ec540d852413a7be3d030e4ee21c95a586320fe64c3bbb8ec31df5b5a8a0f539643a03607a55d3ab8f54aae1cb2fe9e6
    # html_playground1:169 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:174 Signature: 304402205ca7599b31f518aaac8964768d53a9357dd30fe93978a6af884fc8d1c3780cdb022077ac5c07c9b213ac860821140c4ae2c7c13ff0764c0557c01e38ee73b672e43f
    # html_playground1:180 loaded_privateKey 4b3454646fba5f461f6f3de5b5160a4cd458d10ac26d433b882ec6b69636957c
    # html_playground1:183 hashed12 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    # html_playground1:188 Signature2: 304402205ca7599b31f518aaac8964768d53a9357dd30fe93978a6af884fc8d1c3780cdb022077ac5c07c9b213ac860821140c4ae2c7c13ff0764c0557c01e38ee73b672e43f


# Private Key: 5da043dd08c99f4ad4fbf7934068dddf5130c85c7f3c6f716a2eee0afcc379d0
# html_playground1:467 Public Key: 04bbd30cbc89d588b063bf2d63e34b73fb794d1843641ab2db5bd2bfac03ed06ca9c8ba4c250546c0efa6a33b9af0380017accb40cc102ac73917ee780faac93ca
# html_playground1:483 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
# html_playground1:488 Signature: 3045022100d524f50cda89222e14795e942bec11a537ab1b2bd5b874d0d24a156e47bf0d4402202f8adc5e46c1a746dddffed9daad9cd8590eb3e1ecc617992504fe4893dbfd18
# html_playground1:494 loaded_privateKey 5da043dd08c99f4ad4fbf7934068dddf5130c85c7f3c6f716a2eee0afcc379d0
# html_playground1:497 hashed12 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
# html_playground1:502 Signature2: 3045022100d524f50cda89222e14795e942bec11a537ab1b2bd5b874d0d24a156e47bf0d4402202f8adc5e46c1a746dddffed9daad9cd8590eb3e1ecc617992504fe4893dbfd18

# ~:salt,b'G\xa5v\xfb,\x0c\xd3\x15\x81\x1b\xea\xa9$\xae\x1b=0\x86\xa7\\a\xda\x01\xcd&\xa1W\xfe#h\x81`'
# 1 0:00:00.000415
# ~:Derived seed:,5da043dd08c99f4ad4fbf7934068dddf5130c85c7f3c6f716a2eee0afcc379d0
# ~:Private Key (hex):,5da043dd08c99f4ad4fbf7934068dddf5130c85c7f3c6f716a2eee0afcc379d0
# ~:Public Key (hex):,04bbd30cbc89d588b063bf2d63e34b73fb794d1843641ab2db5bd2bfac03ed06ca9c8ba4c250546c0efa6a33b9af0380017accb40cc102ac73917ee780faac93ca

    import hashlib
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives import hashes

    from mnemonic import Mnemonic
    passphrase = Mnemonic("english").generate(strength=256)
    prnt('passphrase',passphrase)

    # === Inputs
    #   const user_id = 'fj8D3h75Hnbe8u';
    #   const user_pass = 'jtVE5u8bT&s#';
    user_id = 'fj8D3h75Hnbe8u'
    # user_pass = 'jtVE5u8bT&s#'
    user_pass = 'void diagram address drill tackle refuse tornado extend category crazy disorder bottom'
    user_pass = 'cement when oil perfect infant version obscure fly lend air cross recall'
    # salt = hashlib.sha256(f"NeedsSomeSalt:{user_id}".encode()).digest()
    salt = hashlib.sha256(f"{user_pass}:{user_id}".encode()).digest()
    prnt('salt',salt)
    # salt = user_id.encode()
    password = user_pass.encode()

    # # === Step 1: Derive 32-byte seed using scrypt
    start_time = now_utc()
    kdf = Scrypt(salt=salt, length=32, n=262144, r=8, p=1, backend=default_backend())
    end_time = now_utc()
    print('1',end_time - start_time)

    seed = kdf.derive(password)
    prnt("Derived seed:", seed.hex())

    # start_time = now_utc()

    # kdf = Scrypt(
    #     salt=salt,
    #     length=32,
    #     n=262144,  # logN = 18
    #     # n=65536,  # logN = 16
    #     r=8,
    #     p=1,
    #     backend=default_backend()
    # )
    # end_time = now_utc()
    # print('2',end_time - start_time)
    # start_time = now_utc()
    # kdf = Scrypt(salt=salt, length=32, n=16384, r=8, p=1, backend=default_backend())
    # end_time = now_utc()
    # print('3',end_time - start_time)
        

    # # === Step 2: Create secp256k1 private key from seed
    # # Ensure it's within curve range
    # private_int = int.from_bytes(seed, 'big') % ec.SECP256K1().key_size
    # private_int = private_int or 1  # avoid zero
    # private_key = ec.derive_private_key(private_int, ec.SECP256K1(), default_backend())

    # # === Step 3: Export public key (uncompressed, 65 bytes)
    # public_key = private_key.public_key()
    # public_key_bytes = public_key.public_bytes(
    #     encoding=serialization.Encoding.X962,
    #     format=serialization.PublicFormat.UncompressedPoint
    # )
    # print("Public Key (hex):", public_key_bytes.hex())
    # print("private_key Key (hex):", private_key.hex())

    from cryptography.hazmat.primitives.asymmetric.ec import SECP256K1
    from binascii import hexlify
    # === Step 2: Use seed directly as private key (just like elliptic in JS)
    priv_int = int.from_bytes(seed, 'big')
    # Clamp to curve order (if needed)
    curve = SECP256K1()
    # order = curve.order
    order = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
    priv_int = priv_int % order
    if priv_int == 0:
        priv_int = 1  # avoid zero

    private_key = ec.derive_private_key(priv_int, curve, default_backend())

    # === Step 3: Get private key bytes (same as seed, if unmodified)
    priv_key_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    prnt("Private Key (hex):", priv_key_bytes.hex())

    # === Step 4: Get uncompressed public key (X9.62, 65 bytes, starts with 0x04)
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    prnt("Public Key (hex):", public_key_bytes.hex())
    from cryptography.exceptions import InvalidSignature


    # Derived Seed (Hex): 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # sig_hex = '5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f'
    # html_playground1:77 Public Key: 04571ccc4ddd01e08777a8b725623cc2b4c4079b20889266ed7326cc906d14c28f71434a40962548110ced9baeace1cf777d0b1b75eac71de348bca212e48a6eb0
    # html_playground1:87 hashed1 9e1b04359ce9f650852b7f468eb9cbaa8198d8678a7ddce5caaeb123b76439ff
    # sig_hex = '304402201466142b6a60a0e1fb95f7152b90bc40705ac6c35725276b2c201ea3ec25ea0d02201c97e5d56654211bcd0ebdb6527132e4e2c2851cb2d8cdff5f8cdbdde5b84860'




    # Derived Seed (Hex): 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # html_playground1:105 Private Key: 5e3c13ced3a16fbc22379dd65c477dc9d23d4a60fb144bc17067494e2815256f
    # html_playground1:106 Public Key: 04571ccc4ddd01e08777a8b725623cc2b4c4079b20889266ed7326cc906d14c28f71434a40962548110ced9baeace1cf777d0b1b75eac71de348bca212e48a6eb0
    # html_playground1:116 hashed1 b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    sig_hex = '3045022100d524f50cda89222e14795e942bec11a537ab1b2bd5b874d0d24a156e47bf0d4402202f8adc5e46c1a746dddffed9daad9cd8590eb3e1ecc617992504fe4893dbfd18'

    # javascript:
    # const msg = "hello world";
    # const hashed_data1 = CryptoJS.SHA256(msg).toString(CryptoJS.enc.Hex);
    # console.log('hashed1',hashed_data1)
    # const curve = new elliptic.ec('secp256k1');
    # let keys = curve.keyFromPrivate(privKeyHex);
    # const signature = keys.sign(hashed_data1, { canonical: true });
    # const sig = signature.toDER('hex');
    # console.log("Signature:", sig);
        
    # python:
    try:
        msg = "hello world"
        signature_bytes = bytes.fromhex(sig_hex)
        public_key_bytes = bytes.fromhex(public_key_bytes.hex())
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)
        try:
            public_key.verify(signature_bytes, (msg).encode('utf-8'), ec.ECDSA(hashes.SHA256()))
            prntDebug(f" - Signature is valid IT WORKED!!!.")
        except InvalidSignature:
            prnt("Invalid signature.")
        except Exception as e:
            prntDebug('failed to verify data:',str(e))
    except Exception as e:
        prnt('err2',str(e))

    from cryptography.exceptions import InvalidSignature
    try:
        pub_bytes = bytes.fromhex(public_key_bytes.hex())
        sig_bytes = bytes.fromhex(sig_hex)

        # Load public key
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)

        # Verify
        try:
            public_key.verify(sig_bytes, msg, ec.ECDSA(hashes.SHA256()))
            print("✅ Signature is valid!")
        except InvalidSignature:
            print("❌ Signature is INVALID!")
    except Exception as e:
        prnt('err3',str(e))
            
    prntn('next task:')
    

    def create_keys(user_id, user_pass, path=1):
        prnt('\ncreate_keys',path)
        import hashlib
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ec import SECP256K1

        if path == 1:
            salt = hashlib.sha256(f"{user_pass}:{user_id}".encode()).digest()
        else:
            text_bytes = f"{user_pass}:{user_id}".encode()
            salt = hashlib.shake_256(text_bytes).digest(128)

        prnt('salt',salt)
        password = user_pass.encode()

        kdf = Scrypt(salt=salt, length=32, n=262144, r=8, p=1, backend=default_backend())

        seed = kdf.derive(password)
        prnt("Derived seed:", seed.hex())

        priv_int = int.from_bytes(seed, 'big')
        curve = SECP256K1()
        order = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
        priv_int = priv_int % order
        if priv_int == 0:
            priv_int = 1

        private_key = ec.derive_private_key(priv_int, curve, default_backend())
        priv_key_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
        prnt("Private Key (hex):", priv_key_bytes.hex())

        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        prnt("Public Key (hex):", public_key_bytes.hex())
        return priv_key_bytes.hex(), public_key_bytes.hex()

    def simpleSign(private_key, data):
        # prntDebugn('simpleSign',data)
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        private_key_bytes = bytes.fromhex(private_key)
        private_key = ec.derive_private_key(int.from_bytes(private_key_bytes, byteorder='big'), ec.SECP256K1())
        signature = private_key.sign((data+'5uHPEF0DPaI4egus4sa6AX').encode('utf-8'), ec.ECDSA(hashes.SHA256()))
        signature_hex = signature.hex()
        prnt('signature_hex',signature_hex)
        return signature_hex

    def verify_data(data, public_key, signature):
        prnt('verifying...',data)
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        from cryptography.exceptions import InvalidSignature
        try:
            pub_bytes = bytes.fromhex(public_key)
            sig_bytes = bytes.fromhex(signature)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
            try:
                public_key.verify(sig_bytes, (data+'5uHPEF0DPaI4egus4sa6AX').encode('utf-8'), ec.ECDSA(hashes.SHA256()))
                prnt("Signature is valid!")
                return True
            except InvalidSignature:
                prnt("Signature is INVALID!")
        except Exception as e:
            prnt('err3',str(e))
        return False

    # user_pass = Mnemonic("english").generate(strength=256)
    # user_id = '1234567890'

    privKey, pubKey = create_keys(user_id, user_pass, path=2)
    data = 'some data'
    sigHex = simpleSign(privKey, data)
    verified = verify_data(data, pubKey, sigHex)
    prnt('verified',verified)
    prntn('rendering')
    return render(request, "utils/testing.html")

    # import hashlib
    # from cryptography.hazmat.primitives.asymmetric import ec
    # from cryptography.hazmat.primitives import hashes, serialization
    # from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    # from cryptography.exceptions import InvalidSignature

    # # Inputs
    # user_id = "fj8D3h75Hnbe8u"
    # user_pass = "jtVE5u8bT&s#"
    # data = "hello world"

    # # Derive seed
    # kdf = Scrypt(
    #     salt=user_id.encode(),
    #     length=32,
    #     n=16384,
    #     r=8,
    #     p=1,
    # )
    # seed = kdf.derive(user_pass.encode())
    # priv_int = int.from_bytes(seed, byteorder='big')

    # # Create key
    # private_key = ec.derive_private_key(priv_int, ec.SECP256K1())
    # public_key = private_key.public_key()

    # # Sign
    # signature = private_key.sign(data.encode(), ec.ECDSA(hashes.SHA256()))
    # print("Signature:", signature.hex())

    # # Verify
    # public_key.verify(signature, data.encode(), ec.ECDSA(hashes.SHA256()))
    # print("Verified!")




# javascript:

# function sha256Hex(str) {
#     return CryptoJS.SHA256(str).toString(CryptoJS.enc.Hex);
# }

# function hexToBytes(hex) {
#     return Uint8Array.from(hex.match(/.{1,2}/g).map(b => parseInt(b, 16)));
# }

# function deriveKey(user_id, user_pass) {
#     const saltHex = sha256Hex("myAppSaltPrefix:" + user_id);
#     const saltBytes = hexToBytes(saltHex);


# # function deriveKey(user_id, user_pass) {
#     return new Promise((resolve, reject) => {
#         scrypt(user_pass, user_id, {
#         N: 262144,
#         r: 8,
#         p: 1,
#         dkLen: 32,
#         encoding: 'hex'
#         }, function (derivedKeyHex) {
#         resolve(derivedKeyHex);
#         });
#     });
# }

# const user_id = 'fj8D3h75Hnbe8u';
# const user_pass = 'jtVE5u8bT&s#';

# const seedHex = await deriveKey(user_id, user_pass);
# console.log("Derived Seed (Hex):", seedHex);

# const ec = new elliptic.ec('secp256k1');
# const keyPair = ec.keyFromPrivate(seedHex);


# python:
# user_id = 'fj8D3h75Hnbe8u'
# user_pass = 'jtVE5u8bT&s#'


# salt = hashlib.sha256(f"myAppSaltPrefix:{user_id}".encode()).digest()
# password = user_pass.encode()


# salt = user_id.encode()
# password = user_pass.encode()
# kdf = Scrypt(salt=salt, length=32, n=16384, r=8, p=1, backend=default_backend())
# seed = kdf.derive(password)
# prnt("Derived seed:", seed.hex())
# kdf = Scrypt(
#     salt=salt,
#     length=32,
#     n=262144,
#     r=8,
#     p=1,
#     backend=default_backend()
# )


# from django.views.decorators.csrf import csrf_exempt

# @csrf_exempt
# def stream_view(request):
#     prnt('streamview')
#     from django.http import StreamingHttpResponse

#     def stream_generator():
#         for i in range(10):
#             yield f"data: Chunk {i}\n\n"
#             time.sleep(1)  # Simulate delay for streaming

#     response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
#     response['Cache-Control'] = 'no-cache'
#     return response








# def set_party_colours_view(request):
#     if request.user.is_superuser:
#         set_party_colours()
#         return render(request, "utils/dummy.html", {"result": 'Success'})



# def committee_reprocess(request, organization, parliament, session, iden):
#     prnt('committee reprocess')
#     # organization = None
#     if organization == 'senate':
#         c = CommitteeMeeting.objects.exclude(committee__Organization='House').filter(ParliamentNumber=parliament, SessionNumber=session, id=iden).select_related('committee', 'committee__chair__person')[0]
#         if 'Subcommittee' in c.committee.Title:
#             title = 'Senate Committee'
#         else:
#             title = 'Senate Committee'
#     else:
#         c = CommitteeMeeting.objects.exclude(committee__Organization='Senate').filter(ParliamentNumber=parliament, SessionNumber=session, id=iden).select_related('committee', 'committee__chair__person')[0]
#         title = 'House Committee'
#     get_senate_committee_transcript(c)
#     return render(request, "utils/dummy.html", {'result':'success'})
    
# def hansard_reprocess(request, organization, parliament, session, iden):
#     prnt('hansard reprocess')
#     # organization = None
#     if organization == 'senate':
#         h = Hansard.objects.filter(Organization='Senate', ParliamentNumber=parliament, SessionNumber=session, id=iden)[0]
#         title = 'Senate Hansard %s' %(str(h.Title))
#     else:
#         h = Hansard.objects.filter(Organization='House of Commons', ParliamentNumber=parliament, SessionNumber=session, pub_iden=iden)[0]
#         title = 'House %s' %(str(h.Title))
#     add_senate_hansard(h.gov_page, True)
#     return render(request, "utils/dummy.html", {'result':'success'})







# #----ontario
# def get_current_mpps_view(request):
#     if request.user.is_superuser:
#         ontario_functions.get_current_MPPs()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_ontario_bills_view(request):
#     if request.user.is_superuser:
#         ontario_functions.get_current_bills()
#         # queue = django_rq.get_queue('default')
#         # queue.enqueue(ontario_functions.get_current_bills, job_timeout=1000)
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_ontario_agenda_view(request):
#     if request.user.is_superuser:
#         ontario_functions.get_weekly_agenda()
#         return render(request, "utils/dummy.html", {"result": 'Success'})
        
# def get_ontario_motions_view(request):
#     if request.user.is_superuser:
#         ontario_functions.get_all_hansards_and_motions('latest')
#         return render(request, "utils/dummy.html", {"result": 'Success'})
  
# def get_ontario_hansard_view(request):
#     if request.user.is_superuser:
#         ontario_functions.get_hansard(None)
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_ontario_latest_hansards_view(request):
#     if request.user.is_superuser:
#         ontario_functions.get_all_hansards_and_motions('recent')
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_ontario_elections_view(request):
#     if request.user.is_superuser:
#         ontario_functions.check_elections()
#         return render(request, "utils/dummy.html", {"result": 'Success'})


# #----federal
# def update_agenda_view(request):
#     if request.user.is_superuser:
#         # daily_update()
#         queue = django_rq.get_queue('default')
#         queue.enqueue(daily_update, job_timeout=500)
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def all_agendas_view(request):
#     if request.user.is_superuser:
#         get_all_agendas()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_latest_agenda_view(request):
#     if request.user.is_superuser:
#         get_house_agendas(url='https://www.ourcommons.ca/en/parliamentary-business/')
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_todays_xml_agenda_view(request):
#     if request.user.is_superuser:
#         get_todays_xml_agenda()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_all_mps_view(request):
#     if request.user.is_superuser:
#         get_house_persons()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_all_senators_view(request):
#     if request.user.is_superuser:
#         get_senate_persons()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_latest_bills_view(request):
#     if request.user.is_superuser:
#         get_house_bills()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_all_bills_view(request, param):
#     if request.user.is_superuser:
#         get_all_bills(param)
#         # queue = django_rq.get_queue('default')
#         # queue.enqueue(get_all_bills, param, job_timeout=7200)
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def update_bill_view(request, iden):
#     b = Bill.objects.filter(id=iden)[0]    
#     xml = 'https://www.parl.ca/LegisInfo/en/bill/%s-%s/%s/xml' %(b.ParliamentNumber, b.SessionNumber, b.NumberCode)
#     prnt(xml)
#     r2 = requests.get(xml)
#     root2 = ET.fromstring(r2.content)
#     bills2 = root2.findall('Bill')
#     for bill in bills2:
#         get_bill(bill)    
#     return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_latest_house_motions_view(request):
#     if request.user.is_superuser:
#         get_house_motions()
#         return render(request, "utils/dummy.html", {"result": 'Success'})
 
# def get_all_house_motions_view(request):
#     if request.user.is_superuser:
#         get_all_house_motions()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_federal_house_expenses_view(request):
#     if request.user.is_superuser:
#         get_house_expenses()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_session_senate_motions_view(request):
#     if request.user.is_superuser:
#         get_senate_motions()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_federal_candidates_view(request):
#     if request.user.is_superuser:
#         get_federal_candidates(1)
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_latest_house_hansard_view(request):
#     if request.user.is_superuser:
#         # get_house_hansard_or_committee('hansard', 'latest')
#         get_house_debates()
#         return render(request, "utils/dummy.html", {"result": 'Success'})
    
# def get_session_house_hansards_view(request):
#     if request.user.is_superuser:
#         get_session_house_hansards()
#         return render(request, "utils/dummy.html", {"result": 'Success'})
    
# def get_all_house_hansards_view(request):
#     if request.user.is_superuser:
#         get_all_house_hansards()
#         return render(request, "utils/dummy.html", {"result": 'Success'})
    
# def get_latest_house_committees_view(request):
#     if request.user.is_superuser:
#         get_house_hansard_or_committee('committee', 'period')
#         # get_latest_house_committee_hansard_and_list()
#         return render(request, "utils/dummy.html", {"result": 'Success'})
        
# def get_latest_house_committees_work_view(request):
#     if request.user.is_superuser:
#         get_committee_work('latest')
#         return render(request, "utils/dummy.html", {"result": 'Success'})
        
# def get_latest_house_committee_list_view(request):
#     if request.user.is_superuser:
#         get_house_committee_list('latest')
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_latest_senate_committees_view(request, item):
#     if request.user.is_superuser:
#         get_latest_senate_committees(item)
#         return render(request, "utils/dummy.html", {"result": 'Success'})
    
# def get_all_senate_committees_view(request):
#     if request.user.is_superuser:
#         get_all_senate_committees()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

# def get_all_senate_hansards_view(request):
#     if request.user.is_superuser:
#         get_senate_debates()
#         return render(request, "utils/dummy.html", {"result": 'Success'})

