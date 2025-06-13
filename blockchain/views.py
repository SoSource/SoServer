
from .models import Blockchain, Block, Node
from accounts.models import User, UserPubKey
from legis.models import Government
from posts.models import Region
from blockchain.models import process_data_packet, process_received_data, NodeChain_genesisId, DataPacket, EventLog, logEvent, Validator, process_received_blocks,assess_received_header, Sonet
from utils.models import *
from utils.locked import hash_obj_id, process_posts_for_validating, convert_to_dict, get_signing_data, verify_obj_to_data
import datetime
# import hashlib
# import uuid
import json
# from uuid import uuid4
import django_rq
# from rq import Queue
# import requests
# import ast
# from urllib.parse import urlparse
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt

if testing():
    run_as_worker = False
else:
    run_as_worker = True


@csrf_exempt
def get_broadcast_list_view(request, iden=None):
    prnt('get_broadcast_list_view')
    try:
        A = 'start'
        obj = 'objx'
        obj_json = 'jsonx'
        try:
            # from blockchain.models import get_self_node
            if not get_self_node().activated_dt:
                return JsonResponse({'message' : 'deactivated_node'})
            if request.method == 'POST' and assess_received_header(request.headers) or request.user.is_superuser:
                prnt()
                # try:                                
                A = '1'
                if request.method == 'POST':
                    raw_data = request.body.decode('utf-8')
                    received_data = json.loads(raw_data)
                    obj_json = json.loads(received_data.get('obj'))
                    dt = received_data.get('dt', None)
                    obj = get_dynamic_model(obj_json['object_type'], id=obj_json['id'])
                elif iden:
                    A = '2'
                    obj = get_dynamic_model(iden, id=iden)
                    dt = None
                A = '3'
                if verify_obj_to_data(obj, obj_json):
                    A = '4'
                    from utils.locked import get_node_assignment, get_broadcast_list
                    starting_nodes, validator_nodes = get_node_assignment(obj, dt=dt)
                    broadcast_list = get_broadcast_list(obj, dt=dt)
                    A = '5'
                    return JsonResponse({'message' : 'Success', 'obj' : get_signing_data(obj), 'starting_node' : starting_nodes[0], 'starting_nodes':starting_nodes, 'broadcast_list' : broadcast_list, 'validator_list' : validator_nodes})
                else:
                    return JsonResponse({'message' : 'Not valid', 'obj' : json.dumps(obj_json), 'err':str(A)})
                # else:
                #     prnt('finished get_broadcast_list_view path 4')
                #     return JsonResponse({'message' : 'Failed header assessment'})
            else:
                return JsonResponse({'message' : 'Not post'})
        except Exception as e:
            prnt('fail522334546',str(e))
            try:
                x = request.POST.get('obj')
            except Exception as x:
                x = str(x)
            return JsonResponse({'message': 'failed1', 'err': str(e) + 'A:' + A + '__' + str(obj_json) + '--' + x})
    except Exception as e:
        prnt('fail5836546',str(e))
        return JsonResponse({'message': 'failed2', 'err': str(e) + 'A:' + A + '__' + str(obj_json)})

@csrf_exempt
def get_current_node_list_view(request):
    try:
        # from blockchain.models import get_self_node
        if not get_self_node().activated_dt:
            return JsonResponse({'message' : 'deactivated_node'})
        chain = Blockchain.objects.filter(genesisType='Nodes', genesisId=NodeChain_genesisId).first()
        dt = round_time(dt=now_utc(), dir='down', amount='10mins')
        node_block = Block.objects.filter(blockchainId=chain.id, DateTime__lte=dt, validated=True).order_by('-index').first()
        prntDebug('node_block',node_block)
        node_data = node_block.data
        prntDebug('node_data',node_data)
        data = {}
        target_nodes = []
        for node in node_data['All']:
            prntDebug(node)
            target_nodes.append(node)
        prntDebug('target_nodes',target_nodes)
        data['All'] = list(Node.objects.exclude(activated_dt=None).filter(id__in=target_nodes, suspended_dt=None).exclude(ip_address='').values_list('ip_address', flat=True))
        for chain, tasks in node_data.items():
            if chain != 'All':
                target_nodes = []
                for task, node_list in tasks.items():
                    for i in node_list:
                        target_nodes.append(i)
                data[chain] = list(Node.objects.exclude(activated_dt=None).filter(id__in=target_nodes, suspended_dt=None).exclude(ip_address='').values_list('ip_address', flat=True))
        # for chain, nodes in node_data['regionChains'].items():
        #     target_nodes = []
        #     for i in nodes:
        #         target_nodes.append(i)
        #     data[chain] = list(Node.objects.filter(id__in=target_nodes, self_declare_active=True, deactivated_time=None).exclude(ip_address='').values_list('ip_address', flat=True))
        return JsonResponse({'message' : 'Success', 'data' : json.dumps(data)})
    except Exception as e:
        return JsonResponse({'message' : 'Fail', 'error' : str(e)})
    

@csrf_exempt # redundant but used by node software
def get_node_request_view(request, node_id):
    prnt('---get_node_request view')
    try:
        
        if node_id == 'self':
            # operatorData = get_operatorData()
            # from utils.models import get_operator_obj
            nodeId = get_operator_obj('local_nodeId')
            node_obj = get_or_create_model('Node', id=nodeId)
            response = JsonResponse({'message' : 'Success', 'nodeData' : get_signing_data(node_obj), 'fullNodeData' : json.dumps(convert_to_dict(node_obj))})
            return response
        elif assess_received_header(request.headers):
            try:
                sonet = get_signing_data(Sonet.objects.first())
            except:
                sonet = None
            node_obj = Node.objects.filter(id=node_id).first()
            if node_obj:
                return JsonResponse({'message' : 'Success', 'nodeData' : get_signing_data(node_obj), 'fullNodeData' : json.dumps(convert_to_dict(node_obj)), 'sonet' : sonet})
            else:
                node_id = node_id
                node_obj = Node(id=node_id)
                prnt('return 2')
                return JsonResponse({'message' : 'Node not found', 'nodeData' : get_signing_data(node_obj), 'fullNodeData' : json.dumps(convert_to_dict(node_obj)), 'sonet' : sonet})
    except Exception as e:
        return JsonResponse({'message' : 'Fail', 'error' : str(e)})

@csrf_exempt
def declare_node_state_view(request):
    prnt('--declare_node_state_view', now_utc())
    objData_json = 'objData_jsonxx'
    objData = 'objDataxx'
    is_valid = 'is_validxx'
    user = 'userxx'
    x = 'x1'
    prnt(x)

    try:
        if request.method == 'POST':
            x = 'xx1'
            if assess_received_header(request.headers):
                x = 'xx2'
                try:
                    received_json = json.loads(request.body.decode('utf-8'))
                    # sender_dict = json.loads(received_json['sender'])
                    # from blockchain.models import get_user
                    # sig = received_json['signature']
                    # del received_json['signature']
                    # for upk in get_user(user_id=sender_dict['User_obj']).get_keys():
                    #     prnt('declare data validity:',upk.verify(received_json, sig))
                except Exception as e:
                    prnt('node_veri-f99865',str(e))
                try:
                    source = received_json.get('source')
                    prnt('received -source',source)
                except Exception as e:
                    prnt('e496',str(e))
                objData = received_json.get('objData')
                objData_json = json.loads(objData)
                x = 'x2'
                # prnt(x)
                broadcast_to_network = received_json.get('broadcast_to_network',True)
                x = x + objData_json['id']
                prnt(x)
                try:
                    is_self = received_json.get('is_self')
                except Exception as e:
                    prnt('fail38524',str(e))
                    is_self = False
                
                # from blockchain.models import get_self_node
                self_node = get_self_node()
                if is_self:
                    node_obj = get_or_create_model('Node', id=objData_json['id'])
                    x = 'x2a'
                    prnt(x)
                    x = 'x3'
                    prnt(x)
                    if node_obj.id == self_node.id:
                        x = 'x4'
                        prnt(x)
                        node_obj, is_valid = sync_and_share_object(node_obj, objData_json)
                        if is_valid:
                            nodeChain = Blockchain.objects.filter(genesisId='Nodes').first()
                            if nodeChain:
                                nodeChain.add_item_to_queue(node_obj)
                            x = 'x6'
                            prnt(x)
                            return JsonResponse({'message' : 'Success', 'obj' : get_signing_data(node_obj)})
                if self_node.activated_dt:
                    if str(broadcast_to_network).lower() == 'true':
                        x = 'x7'
                        node_obj = get_or_create_model('Node', id=objData_json['id'])
                        x = 'x2ab'
                        prnt(x)
                        queue = django_rq.get_queue('main')
                        queue.enqueue(node_obj.broadcast_state, node_data=objData_json, job_timeout=200, result_ttl=3600)

                    node_obj = get_or_create_model('Node', id=objData_json['id'])
                    x = 'x2ac'
                    prnt(x)
                    node_obj, is_valid = sync_and_share_object(node_obj, objData_json)
                    if is_valid:
                        nodeChain = Blockchain.objects.filter(genesisId='Nodes').first()
                        if nodeChain:
                            nodeChain.add_item_to_queue(node_obj)
                        # return JsonResponse({'message' : 'Success', 'obj' : get_signing_data(node_obj)})
                        return JsonResponse({'message' : 'Success'})
                    return JsonResponse({'message' : 'A problem occured', 'obj':objData,  'err': f'-- is_valid: {is_valid} -- user: {user} -- x: {x}'})
                else:
                    return JsonResponse({'message' : 'self_not_active'})
        return JsonResponse({'message' : 'A problem occured', 'err': f'-- is_valid: {is_valid} -- user: {user} -- x: {x}'})
    except Exception as e:
        prnt('fail583725',x,'/',str(e))
        return JsonResponse({'message' : f'A problem occured', 'err': f'{str(e)} -- objData: {objData} -- objData_json: {objData_json}  -- is_valid: {is_valid} -- user: {user} -- x: {x}'})
    
@csrf_exempt
def receive_disavow(request):
    # if enough nodes disavow self_node:
    # operatorData = get_operatorData()
    # operatorData['disavowed'] = True
    # write_operatorData(operatorData)
    pass

@csrf_exempt
def check_if_exists_view(request):
    prnt('--check_if_exists_view')
    from posts.utils import get_client_ip
    sender_ip = get_client_ip(request) 
    prnt('sender_ip',sender_ip)
    if str(sender_ip) == '127.0.0.1' and request.method == 'POST':

        raw_data = request.body.decode('utf-8')
        received_data = json.loads(raw_data)

        obj_type = received_data.get('type')
        fields = received_data.get('fields', [])
        id_only = received_data.get('id_only', True)
        withold_fields = received_data.get('withold_fields', True)
        if obj_type == 'Blockchain':
            genesisId = received_data.get('genesisId')
            obj = get_dynamic_model(obj_type, genesisId=genesisId)
        elif obj_type == 'Block':
            blockchainId = received_data.get('blockchainId')
            index = received_data.get('index')
            obj = get_dynamic_model(obj_type, blockchainId=blockchainId, index=index)
            block = Block.objects.filter(blockchainId=blockchainId, validated=True).order_by('-index').first()
            if block:
                latest_block_index = block.index
            else:
                latest_block_index = 0
            if not obj:
                return JsonResponse({'message' : 'Not Found', 'latest_index' : latest_block_index})
            if fields: # might error if not text field
                return JsonResponse({'message' : 'Success', 'obj_id' : obj.id, 'latest_index' : latest_block_index, 'requested_fields':{f:getattr(obj, f) for f in fields if has_field(obj, f)}})
            elif withold_fields and id_only:
                return JsonResponse({'message' : 'Success', 'obj_id' : obj.id, 'latest_index' : latest_block_index})
            else:
                return JsonResponse({'message' : 'Success', 'obj' : json.dumps(convert_to_dict(obj, withold_fields=withold_fields)), 'latest_index' : latest_block_index})
        else:
            obj_id = received_data.get('obj_id')
            if not obj_type or obj_type == 'unknown':
                obj_type = obj_id
            obj = get_dynamic_model(obj_type, id=obj_id)

        if obj:
            if fields: # might error if not text field
                return JsonResponse({'message' : 'Success', 'obj_id' : obj.id, 'requested_fields':{f:getattr(obj, f) for f in fields if has_field(obj, f)}})
            elif withold_fields and id_only:
                return JsonResponse({'message' : 'Success', 'obj_id' : obj.id})
            else:
                return JsonResponse({'message' : 'Success', 'obj' : json.dumps(convert_to_dict(obj, withold_fields=withold_fields))})
        else:
            prntDebug('obj not found')
            return JsonResponse({'message' : 'Not Found'})

@csrf_exempt
def broadcast_dataPackets_view(request):
    prnt('broadcast_dataPackets_view')
    # when self_node declares self inactive
    if request.method == 'POST':
        try:
            if assess_received_header(request.headers):
                from blockchain.models import DataPacket

                raw_data = request.body.decode('utf-8')
                received_data = json.loads(raw_data)
                prnt('received_data',received_data) # not receiveing data from node
                if received_data.get('cmd') == 'Broadcast':
                    requested_cmds = json.loads(received_data.get('request'))
                    if string_to_dt(requested_cmds['dt']) >= now_utc() - datetime.timedelta(hours=2):
                        self_node = get_self_node()
                        if self_node.User_obj.verify_sig(requested_cmds, requested_cmds['signature']):
                            dataPackets = DataPacket.objects.filter(Node_obj=self_node, func='share')
                            prnt('dataPackets to broadcast',dataPackets)
                            success = None
                            for dp in dataPackets:
                                if len(dp.data.keys()) > 0 or dp.chainId == NodeChain_genesisId:
                                    result = dp.broadcast() # this will need to be a worker, node should check is_data_processing
                                    if success == None or success == True:
                                        success = result
                            return JsonResponse({'message' : 'Success', 'result':success})
                    return JsonResponse({'message' : 'Invalid'})
        except Exception as e:
            prnt('fail506789134',str(e))
            return JsonResponse({'message' : 'Fail', 'err':str(e)})

def chainTest_view(request):
    prnt('chainTest_view')
    # from posts.models import to_megabytes
    # n = Node(self_declare_active=True, ip_address='10.0.0.39:3005', User_obj=request.user)
    # n.save()
    node = Node.objects.all()[0]
    i = convert_to_dict(node)
    obj = get_dynamic_model(i['object_type'], **i)
    prnt(obj)
    # node.last_updated = now_utc()
    # # node.save()
    # prnt(node)
    # broadcast_peers, broadcast_list, validator_list = get_node_assignment(node)
    # prnt(broadcast_list)
    prnt(to_megabytes(node))
    prnt(to_megabytes(convert_to_dict(node)))
    prnt(to_megabytes(get_signing_data(node)))


@csrf_exempt
def is_data_processing_view(request, iden):
    prnt('---is_data_processing_view',iden) # only used by nodesoftware for syncDB, normal data process runs on low
    if assess_received_header(request.headers):
        # from blockchain.models import exists_in_worker
        dp = DataPacket.objects.filter(id=iden).first()
        if dp:

            if 'completed' in dp.func:
                return JsonResponse({'message' : 'Success', 'result':'completed', 'iden': dp.id})
            elif 'fail' in dp.func:
                return JsonResponse({'message' : 'Success', 'result':'failed', 'iden': dp.id})
            else:
                queue = django_rq.get_queue('main')
                if not exists_in_worker('process_received_data', dp.id, queue):
                    queue.enqueue(process_received_data, dp.id, downstream_worker=False, skip_log_check=True, job_timeout=1200, result_ttl=3600)
                    return JsonResponse({'message' : 'Success', 'result':'running', 'iden': dp.id, 'added_to_queue':True})
                else:
                    return JsonResponse({'message' : 'Success', 'result':'running', 'iden': dp.id, 'added_to_queue':False})

                
        else:
            return JsonResponse({'message' : 'not found', 'result':'not running'})
    return JsonResponse({'message' : 'fail', 'result':'error'})

@csrf_exempt
def check_latest_data_view(request, model_type):
    prnt('---check_latest_data_view',model_type)
    if assess_received_header(request.headers, return_is_self=True):
        latest_obj_count = 'x'
        if 'Blocks' in model_type:
            if model_type == 'User_Blocks':
                latest_obj = Block.objects.filter(Blockchain_obj__genesisType='User', validated=True).order_by('-DateTime').first()
            elif model_type == 'Wallet_Blocks':
                latest_obj = Block.objects.filter(Blockchain_obj__genesisType='Wallet', validated=True).order_by('-DateTime').first()
            else:
                a = model_type.find('-')
                genesisId = model_type[:a]
                latest_obj = Block.objects.filter(Blockchain_obj__genesisId=genesisId, validated=True).order_by('-DateTime').first()
            # latest_obj_count = Block.objects.filter(Blockchain_obj__genesisId=genesisId, validated=True).count()
        elif model_type == 'Users-Keys':
            latest_user = User.objects.order_by('-last_updated').first()
            latest_key = UserPubKey.objects.order_by('-last_updated').first()
            if latest_user and latest_key and latest_user.last_updated < latest_key.last_updated:
                latest_obj = latest_user
                # latest_obj_count = User.objects.all().count()
            else:
                latest_obj = latest_key
                # latest_obj_count = UserPubKey.objects.all().count()
        else:
            model = get_model(model_type)
            latest_obj = model.objects.order_by(*get_timeData(model(), sort='updated', querying=True)).first()
            # latest_obj_count = model.objects.all().count()
        if latest_obj:
            return JsonResponse({'message' : 'Success', 'model_type':model_type, 'update_dt' : dt_to_string(get_timeData(latest_obj, sort='updated')), 'obj_count':latest_obj_count})
        else:
            prnt('no latest_obj')
            return JsonResponse({'message' : 'Not Found'})

@csrf_exempt
def receive_data_view(request):
    prnt('---receive_data_view')
    try:
        if request.method == 'POST':
            if assess_received_header(request.headers):

                raw_data = request.body.decode('utf-8')
                received_data = json.loads(raw_data)
                # prnt('received_data',received_data)
                try:
                    is_self = received_data.get('is_self')
                except Exception as e:
                    prnt('fail38524',str(e))
                    is_self = False
                if 'packet_id' in received_data:
                    packet_id = received_data['packet_id']
                else:
                    packet_id = hash_obj_id('DataPacket', specific_data=received_data)
                if 'senderId' in received_data:
                    sender_id = received_data['senderId']
                else:
                    # from blockchain.models import get_self_node
                    sender = get_self_node()
                    if sender:
                        sender_id = sender.id
                    elif not Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, validated=True).count():
                        sender_id = None
                obj_type = received_data['type']
                data = received_data.get('content')
                func = 'process_received_data'
                time.sleep(3)
                if is_self and assess_received_header(request.headers, return_is_self=True) or is_self and Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, validated=True).count() == 0:
                    prnt('bbbbb')

                    run_as_worker = True
                    if run_as_worker:
                        prnt('packet_id',packet_id)
                        # iden = hash_obj_id('DataPacket', specific_data=received_data)
                        dp = DataPacket.objects.filter(id=packet_id).first()
                        if not dp:
                            if sender_id:
                                dp = DataPacket(id=packet_id, Node_obj_id=sender_id, func=func, data=received_data)
                            else:
                                dp = DataPacket(id=packet_id, func=func, data=received_data)
                            dp.created = now_utc()
                            dp.save()
                        elif 'received_data' not in dp.func:
                            dp.func = dp.func + '_' + func
                            dp.save()
                        if 'process' in dp.func:
                            queue = django_rq.get_queue('main')
                            queue.enqueue(process_received_data, dp.id, downstream_worker=False, skip_log_check=True, get_missing_blocks=False, override_completed=True, job_timeout=1200, result_ttl=3600)
                        return JsonResponse({'message' : 'Success', 'iden': dp.id})
                    # else:
                    #     result = process_received_data(received_data, run_as_worker=False)
                    #     prnt('result of process recieved data', result)
                    #     return JsonResponse({'message' : 'Success', 'result' : str(result)})
                else:
                    prnt('CCCCC')

                    # iden = hash_obj_id('DataPacket', specific_data=received_data)
                    dp = DataPacket.objects.filter(id=packet_id).first()
                    if not dp:
                        dp = DataPacket(id=packet_id, func=func, data=received_data)
                        dp.created = now_utc()
                        dp.save()
                    elif 'received_data' not in dp.func:
                        dp.func = dp.func + '_' + func
                        dp.save()
                    queue = django_rq.get_queue('low')
                    queue.enqueue(process_received_data, dp.id, job_timeout=600, result_ttl=3600)
                    return JsonResponse({'message' : 'Success', 'iden': dp.id})

        prnt('eeeeeee')
    except Exception as e:
        return JsonResponse({'message' : 'Fail', 'error' : str(e)})
    return JsonResponse({'message' : 'Fail', 'error' : 'None'})

max_obj_send_count = 200

@csrf_exempt
def request_data_view(request):
    prnt('--request_data_view')
    e = 'e'
    err = 'x'
    try:
        # from blockchain.models import get_self_node
        if not get_self_node().activated_dt:
            return JsonResponse({'message' : 'deactivated_node'})
        if request.method == 'POST':
            if assess_received_header(request.headers, if_self_active=True):
                proceed = False
                raw_data = request.body.decode('utf-8')
                received_data = json.loads(raw_data)

                try:
                    userData = json.loads(received_data.get('userData'))
                except Exception as e:
                    prnt('fail5933',str(e))
                nodeData = json.loads(received_data.get('nodeData'))
                try:
                    requested_data = json.loads(received_data.get('request'))
                    logEvent('request_data_view', code='4824', extra={'requested_data':requested_data})
                    prntDebug('requested_data_len',sum(items if isinstance(items, int) else len(items) for items in requested_data.values()),'requested_data',str(requested_data)[:1000])
                except Exception as e:
                    prnt('fail59331',str(e))
                if 'hashed' in requested_data:
                    hashed = requested_data['hashed']
                else:
                    hashed = None
                prnt('hashed',hashed)


                obj_type = requested_data['type']
                prnt(f'obj_type:{obj_type}-- hello Im here!! hashed:{hashed}')
                err = 'validating request'
                if string_to_dt(request.headers.get('dt')) >= now_utc() - datetime.timedelta(minutes=20):
                    if 'requested_update_dt' in requested_data and requested_data['requested_update_dt']:
                        requested_update_dt = string_to_dt(requested_data['requested_update_dt'])
                    else:
                        requested_update_dt = None
                    # pubKey = requested_data['publicKey']
                    sig = requested_data['signature']
                    del requested_data['signature']
                    node = Node.objects.filter(id=nodeData['id']).first()
                    user = User.objects.filter(id=userData['id']).first()
                    from utils.locked import sort_for_sign, verify_data
                    if node and user:
                        # prntDebug('2b sig',sig)
                        # prntn('requested_data',requested_data)
                        err = 'node found'
                        if hashed and user.verify_sig(hashed, sig, simple_verify=True) or user.verify_sig(sort_for_sign(requested_data), sig, simple_verify=True):
                            proceed = True
                            err = 'request valid'
                    elif user:
                        # prntDebug('creating node')
                        err = 'creating node'
                        if user.verify_sig(sort_for_sign(requested_data), sig, simple_verify=True):
                            if user.verify_sig(get_signing_data(nodeData), nodeData['signature']):
                                node = get_or_create_model(nodeData['object_type'], id=nodeData['id'])
                                node, valid_obj, updatedDB = sync_model(node, nodeData)
                                if valid_obj:
                                    proceed = True
                                    err = 'node created'
                    else:
                        err = 'attempting to create objs'
                        # validator_upk = UserPubKey()
                        if verify_data(get_signing_data(userData), userData['publicKey'], userData['signature']):
                        # if validator_upk.verify(get_signing_data(userData), userData['signature'], userData['publicKey']):
                            # if validator_upk.verify(get_signing_data(upkData), upkData['signature'], userData['publicKey']):
                            # if validator_upk.verify(get_signing_data(nodeData), nodeData['signature'], userData['publicKey']):
                            if verify_data(get_signing_data(nodeData), userData['publicKey'], nodeData['signature']):
                                err = 'creation data valid'
                                user = User()
                                for key, value in userData.items():
                                    if value != 'None':
                                        setattr(user, key, value)
                                user.save(share=False, is_new=True)
                                # upk = UserPubKey()
                                # for key, value in upkData.items():
                                #     if value != 'None':
                                #         if str(key) == 'User_obj':
                                #             setattr(upk, 'User_obj_id', value)
                                #         else:
                                #             setattr(upk, key, value)
                                # upk.save(share=False, is_new=True)
                                # err = 'user/upk created'
                                # upk, valid_obj, updatedDB = sync_model(upk, upkData)
                                # if valid_obj:
                                #     err = 'upk good'
                                user, valid_obj, updatedDB = sync_model(user, userData)
                                if valid_obj:
                                    err = 'user good'
                                    node = get_or_create_model(nodeData['object_type'], id=nodeData['id'])
                                    node, valid_obj, updatedDB = sync_model(node, nodeData)
                                    if valid_obj:
                                        err = 'node good'
                                        proceed = True
                if not proceed:
                    prnt('not proceeding')
                else:
                    # from blockchain.models import sigData_to_hash
                    from itertools import islice
                    err = 'proceeding'
                    data_to_send = []
                    found_items = []
                    not_found = []
                    validators = []
                    max_send = False
                    index = 0
                    total_mbs = 0
                    to_send_items = []
                    sending_idens = []
                    compressed_data = []
                    # checked_idens = []
                    
                    if obj_type == 'Blockchain':
                        genesisId = requested_data['genesisId']
                        try:
                            from utils.models import is_id
                            if is_id(genesisId):
                                chain = Blockchain.objects.filter(genesisId=genesisId).first()
                            else:
                                chain = Blockchain.objects.filter(genesisName=genesisId).first()
                            if not chain:
                                return JsonResponse({'message' : 'Not Found', 'type':obj_type, 'genesisId' : genesisId})
                            else:
                                gen = chain.get_genesis_pointer()
                                return JsonResponse({'message' : 'Success', 'type':obj_type, 'content' : json.dumps([convert_to_dict(gen)]), 'blockchain_obj' : json.dumps(convert_to_dict(chain))})
                        except Exception as e:
                            return JsonResponse({'message' : 'Not Found', 'type':obj_type, 'genesisId' : genesisId, 'error' : str(e)})
                    elif obj_type == 'Block':

                        if 'blockchainId' in requested_data:
                            blockchainId = requested_data['blockchainId']
                        else:
                            blockchainId = None
                        if 'iden' in requested_data:
                            iden = requested_data['iden']
                        else:
                            iden = None
                        if 'include_content' in requested_data:
                            include_content = requested_data['include_content']
                        else:
                            include_content = False
                        if 'include_content' in requested_data:
                            include_validators = requested_data['include_validators']
                        else:
                            include_validators = True
                        if 'items' in requested_data:
                            items = requested_data['items']
                        else:
                            items = 1
                        if 'hash_history' in requested_data:
                            hash_history = requested_data['hash_history']
                        else:
                            hash_history = []
                        if 'index' in requested_data:
                            index = requested_data['index']
                        else:
                            index = 1
                        if 'force_check' in requested_data:
                            force_check = requested_data['force_check']
                        else:
                            force_check = False
                        prntDebug('blockchainId',blockchainId,'include_validators',include_validators)
                        if blockchainId:
                            chain = Blockchain.objects.filter(id=blockchainId).first()
                            if not chain:
                                return JsonResponse({'message' : 'Not Found', 'type':obj_type, 'blockchainId' : blockchainId})
                        try:
                            if hash_history:
                                block = Block.objects.filter(Blockchain_obj=chain, validated=True, hash__in=hash_history).defer("data").order_by('-index').first()
                                if block:
                                    index = block.index
                                blocks = Block.objects.filter(Blockchain_obj=chain, validated=True, index__gte=index).defer("data").order_by('index')
                            elif iden:
                                if isinstance(iden, list):
                                    blocks = Block.objects.filter(id__in=iden)  
                                else:
                                    blocks = [Block.objects.filter(id=iden).first()]
                            elif isinstance(index, int):
                                blocks = Block.objects.filter(Blockchain_obj=chain, validated=True, index__gte=index).defer("data").order_by('index')
                            else:
                                block = []
                                block = Block.objects.filter(Blockchain_obj=chain, validated=True, hash=index).defer("data").order_by('-index').first()
                                if block:
                                    blocks = Block.objects.filter(Blockchain_obj=chain, validated=True, index__gte=block.index).defer("data").order_by('index')[:items]
                            
                            if not blocks:
                                return JsonResponse({'message' : 'Not Found', 'type':obj_type, 'blockchainId' : blockchainId, 'index' : index})
                            elif items == 1:
                                index += 1
                                block_content = []
                                block = blocks[0]
                                prnt('block in question',block)
                                transaction_obj = None
                                transaction_data = block.get_transaction_data()
                                if transaction_data:
                                    transaction_obj = json.dumps(transaction_data)
                                if block and str(include_content) == 'True':
                                    prnt('block and include_content')
                                    block_content = block.get_full_data()
                                    if transaction_obj:
                                        block_content.insert(0, transaction_data)
                                    block_content.insert(0, convert_to_dict(block))
                                elif block and str(include_validators) == 'True':
                                    prnt('block and include_validators')
                                    block_content = block.get_validators()
                                    if transaction_obj:
                                        block_content.insert(0, transaction_data)
                                    block_content.insert(0, convert_to_dict(block))
                                if str(include_content).lower() == 'true':
                                    block_content = compress_data(block_content)
                                else:
                                    block_content = json.dumps(block_content)
                                return JsonResponse({'message' : 'Success', 'type':obj_type, 'block_obj' : json.dumps(convert_to_dict(block)), 'transaction_obj':transaction_obj, 'index' : index, 'content' : block_content, 'force_check':force_check, 'end_of_chain':True if block.index == block.Blockchain_obj.chain_length else False})
                            elif items:
                                prntDebug('else items',items)
                                if any(b for b in blocks if b.index >= index):
                                    prntDebug('has any')
                                    blocks = [b for b in blocks if b.index >= index]
                                prntDebug('blocks',blocks)
                                block_list = []
                                block_idens = []
                                # index = 0
                                for block in blocks[:items]:
                                    if block.index > index:
                                        index = block.index
                                    data = {
                                        'block_dict' : convert_to_dict(block),
                                        'block_transaction' : block.get_transaction_data(),
                                        'validations' : block.get_validators(),
                                        'block_data' : []
                                    }
                                    block_list.append(data)
                                    block_idens.append(block.id)
                                    prntDebug('b add', block.index)
                                    # if str(include_content).lower() == 'true':
                                    #     data['block_data'] = block.get_full_data(include_validators=False)
                                block_list = json.dumps(block_list)
                                prntDebug('sending block_list',str(block_list)[:1000])
                                if len(blocks) > 1 or str(include_content).lower() == 'true':
                                    block_list = compress_data(block_list)
                                return JsonResponse({'message' : 'Success', 'type' : 'Blocks', 'blockchainId' : block.blockchainId, 'genesisId':block.Blockchain_obj.genesisId, 'block_idens':block_idens, 'block_list' : block_list, 'index' : index, 'end_of_chain' : True if any(b for b in blocks if b.index == block.Blockchain_obj.chain_length) else False, 'force_check':force_check})
                        except Exception as e:
                            return JsonResponse({'message' : 'Not Found', 'type':obj_type, 'blockchainId' : blockchainId, 'index' : index, 'error' : str(e)})
                    elif obj_type == 'multi':
                        requested_items = requested_data['items']
                        if 'exclude' in requested_data:
                            exclude = requested_data['exclude']
                        else:
                            exclude = []
                        if 'obj_count' in requested_data:
                            obj_count = requested_data['obj_count']
                        else:
                            obj_count = 'x'
                        if 'index' in requested_data:
                            index = int(requested_data['index'])
                        from posts.models import Update
                        for objType, idList in islice(requested_items.items(), index, index+max_obj_send_count):
                            if requested_update_dt:
                                model = get_model(obj_type)
                                timeField = get_timeData(model(), sort='updated', first_string=True)
                                filter_kwargs = {"id__in": idList, f"{timeField}__gte": requested_update_dt}
                                models = get_dynamic_model(objType, list=True, order_by='created', exclude={"id__in": exclude}, **filter_kwargs)
                            else:
                                models = get_dynamic_model(objType, list=True, exclude={"id__in": exclude}, id__in=idList)
                            if models:
                                for obj in models:
                                    if verify_obj_to_data(obj, obj):
                                        if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj):
                                            if obj.Validator_obj not in data_to_send and obj.Validator_obj.id not in exclude:
                                                data_to_send.append(obj.Validator_obj)
                                                found_items.append(obj.Validator_obj.id)
                                            # if not validator, add to missing_items
                                        if obj.object_type == 'Person':
                                            update = Update.objects.filter(pointerId=obj.id, validated=True).order_by('-DateTime').first()
                                            if update and update not in data_to_send and update not in exclude:
                                                data_to_send.append(update)
                                                found_items.append(update.id)
                                                if update.Validator_obj and update.Validator_obj not in data_to_send and update.Validator_obj.id not in exclude:
                                                    data_to_send.append(update.Validator_obj)
                                                    found_items.append(update.Validator_obj.id)
                                                # if not validator, add to missing_items
                                        data_to_send.append(obj)
                                        found_items.append(obj.id)
                                        if len(data_to_send) >= max_obj_send_count:
                                            max_send = True
                                            break
                            if objType == 'User': # include upk
                                if requested_update_dt:
                                    model = get_model(obj_type)
                                    timeField = get_timeData(model(), sort='updated', first_string=True)
                                    filter_kwargs = {"User_obj__id__in": idList, f"{timeField}__gte": requested_update_dt}
                                    models = get_dynamic_model('UserPubKey', list=True, order_by='created', exclude={"id__in": exclude}, **filter_kwargs)
                                else:
                                    models = get_dynamic_model('UserPubKey', list=True, exclude={"id__in": exclude}, User_obj__id__in=idList)
                                if models:
                                    for obj in models:
                                        if verify_obj_to_data(obj, obj):
                                            if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj):
                                                if obj.Validator_obj not in data_to_send and obj.Validator_obj.id not in exclude:
                                                    data_to_send.append(obj.Validator_obj)
                                                    found_items.append(obj.Validator_obj.id)
                                            # if not validator, add to missing_items
                                            data_to_send.append(obj)
                                            found_items.append(obj.id)
                                            if len(data_to_send) >= max_obj_send_count:
                                                max_send = True
                                            #     break
                            if len(data_to_send) >= max_obj_send_count:
                                break

                        
                        for objType, idList in islice(requested_items.items(), index, index+max_obj_send_count):
                            for i in idList:
                                if i not in found_items:
                                    not_found.append(i)
                        if not_found:
                            delLogs = EventLog.objects.filter(type='Deletion_Log', data__has_any_key=not_found)
                            not_found_list = not_found
                            for log in delLogs:
                                add_to_send = False
                                for i in not_found_list:
                                    if i in log:
                                        not_found.remove(i)
                                        add_to_send = True
                                if add_to_send:
                                    data_to_send.append(log)
                        # prntDebug('data_to_send',str(data_to_send)[:500])
                        prntDebug('not_found_len',not_found,'found_items_len',len(found_items),'found_items',found_items)
                        total_mbs = 0
                        to_send_items = []
                        sending_idens = []
                        for d in data_to_send:
                            if d.id not in exclude:
                                mbs = to_megabytes(d)
                                if (total_mbs + mbs) < 45:
                                    total_mbs += mbs
                                    to_send_items.append(convert_to_dict(d))
                                    sending_idens.append(d.id)
                                else:
                                    max_send = True
                                    break
                        if to_send_items:
                            if max_send:
                                index = len(to_send_items)
                            # validator_idens = [v.id for v in validators]
                            # validators = [convert_to_dict(v) for v in validators]
                            compressed_data = compress_data(to_send_items)
                            logEvent('returning_request_data', code='7193', extra={'returned_data':sending_idens})
                            return JsonResponse({'message' : 'Success', 'type':obj_type, 'content' : compressed_data, 'not_found' : not_found, 'returning_idens':sending_idens, 'index':index})
                        else:
                            return JsonResponse({'message' : 'Not Found', 'type':obj_type})
                    elif obj_type == 'Users-Keys':
                        if 'exclude' in requested_data:
                            exclude = requested_data['exclude']
                        else:
                            exclude = []
                        items = requested_data['items']
                        index = 'NA'
                        for model_type in ['User','UserPubKey']:
                            if items == 'All':
                                index = requested_data['index']
                                if requested_update_dt:
                                    models = get_dynamic_model(model_type, list=[int(index), int(index) + max_obj_send_count], order_by='created', exclude={"id__in": exclude}, last_updated__gte=requested_update_dt)
                                else:
                                    models = get_dynamic_model(model_type, list=[int(index), int(index) + max_obj_send_count], order_by='created', exclude={"id__in": exclude})
                            else:
                                if requested_update_dt:
                                    models = get_dynamic_model(model_type, list=True, order_by='created', exclude={"id__in": exclude}, last_updated__gte=requested_update_dt, id__in=items)
                                else:
                                    models = get_dynamic_model(model_type, list=True, order_by='created', exclude={"id__in": exclude}, id__in=items)
                            if models:
                                for obj in models:
                                    if verify_obj_to_data(obj, obj):
                                        if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj):
                                            if obj.Validator_obj not in data_to_send and obj.Validator_obj.id not in exclude:
                                                data_to_send.append(obj.Validator_obj)
                                                found_items.append(obj.Validator_obj.id)
                                        data_to_send.append(obj)
                                        found_items.append(obj.id)
                        if items != 'All':
                            for i in items:
                                if i not in found_items:
                                    not_found.append(i)
                            if not_found:
                                delLogs = EventLog.objects.filter(type='Deletion_Log', data__has_any_key=not_found)
                                not_found_list = not_found
                                for log in delLogs:
                                    add_to_send = False
                                    for i in not_found_list:
                                        if i in log:
                                            not_found.remove(i)
                                            add_to_send = True
                                    if add_to_send:
                                        data_to_send.append(log)
                        if data_to_send:
                            if len(data_to_send) >= max_obj_send_count:
                                index = int(index) + max_obj_send_count
                            else:
                                index == 'NA'

                            # data_to_send = [obj for obj in vals if verify_obj_to_data(obj, obj)]
                            # if data_to_send:
                            for d in data_to_send:
                                if d.id not in exclude:
                                    mbs = to_megabytes(d)
                                    if (total_mbs + mbs) < 45:
                                        total_mbs += mbs
                                        to_send_items.append(convert_to_dict(d))
                                        sending_idens.append(d.id)
                                    else:
                                        max_send = True
                                        break
                            compressed_data = compress_data(to_send_items)

                            # validators = [convert_to_dict(v) for v in validators]
                            # mbs = 0
                            # try:
                            #     for i in data_to_send:
                            #         mbs += to_megabytes(i)
                            # except Exception as e:
                            #     prnt('fail497511',str(e))
                            # try:
                            #     for i in validators:
                            #         mbs += to_megabytes(i)
                            # except Exception as e:
                            #     prnt('fail43456511',str(e))
                            # if validators or data_to_send:
                            #     compressed_data = compress_data(validators + data_to_send)
                            # else:
                            #     compressed_data = []
                            return JsonResponse({'message' : 'Success', 'type':obj_type, 'content' : compressed_data, 'not_found' : not_found, 'returning_idens':sending_idens, 'index' : index})
                        else:
                            return JsonResponse({'message' : 'Not Found', 'type':obj_type, 'index' : index})
                    elif 'Blocks' in obj_type:
                        a = obj_type.find('_')
                        genesisType = obj_type[:a]

                        if 'index' in requested_data:
                            index = requested_data['index']
                        else:
                            index = 0

                        if requested_update_dt:
                            blocks = Block.objects.filter(Blockchain_obj__genesisType=genesisType, validated=True, DateTime__gte=requested_update_dt).order_by('DateTime').values('id', 'DateTime')[int(index): int(index) + max_obj_send_count]
                            requested_update_dt = dt_to_string(requested_update_dt)
                            index = int(index) + max_obj_send_count
                        else:
                            blocks = Block.objects.filter(Blockchain_obj__genesisType=genesisType, validated=True).order_by('DateTime').values('id', 'DateTime')[int(index): int(index) + max_obj_send_count]
                            index = int(index) + max_obj_send_count
                        if blocks:
                            result = [{dt_to_string(obj['DateTime']): obj['id']} for obj in blocks]
                            prnt('resut blocks',result)
                            if len(blocks) < max_obj_send_count:
                                index = 'end'
                            return JsonResponse({'message' : 'Success', 'type':obj_type, 'block_ids' : json.dumps(result), 'index' : index, 'requested_update_dt' : requested_update_dt})
                        elif int(index) >= max_obj_send_count:
                            return JsonResponse({'message' : 'Success', 'type':obj_type, 'block_ids' : json.dumps([]), 'index' : 'end', 'requested_update_dt' : requested_update_dt})
                        else:
                            prnt('no models found')
                            return JsonResponse({'message' : 'None Found', 'type':obj_type})
                    else:
                        prnt('elsea')
                        items = requested_data['items']
                        if 'exclude' in requested_data:
                            exclude = requested_data['exclude']
                        else:
                            exclude = []
                        if 'obj_count' in requested_data:
                            obj_count = requested_data['obj_count']
                        else:
                            obj_count = 'x'
                        index = 'NA'
                        if items == 'All':
                            if obj_type == 'test':
                                prnt('is test')
                                from legis.models import Person
                                from posts.models import Update,Post
                                from itertools import chain
                                posts = Post.objects.filter(pointerType='Person').exclude(Chamber=None)[:5]
                                objs = Person.objects.filter(id__in=[p.pointerId for p in posts])
                                prnt('objs',objs)
                                upds = Update.objects.filter(pointerId__in=[i.id for i in objs]) 
                                prnt('upds',upds)
                                models = list(chain(objs, upds))
                                prnt('models',models)
                            else:
                                index = requested_data['index']
                                if requested_update_dt:
                                    model = get_model(obj_type)
                                    timeField = get_timeData(model(), sort='updated', first_string=True)
                                    filter_kwargs = {f"{timeField}__gte": requested_update_dt}
                                    models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], order_by='created', **filter_kwargs)
                                else:
                                    models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count])
                                # not_found = list(set(not_found + idList))
                                index = int(index) + max_obj_send_count
                        elif obj_type == 'Region' and items == 'networkSupported':
                            index = requested_data['index']
                            if requested_update_dt:
                                models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], order_by='created', last_updated__gte=requested_update_dt, is_supported=True)
                            else:
                                models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], is_supported=True)
                            index = int(index) + max_obj_send_count
                        elif obj_type == 'Validators_only':
                            vals = []
                            # from posts.models import get_model_prefix, seperate_by_type
                            # from blockchain.models import check_commit_data
                            # from utils.models import get_model_prefix, seperate_by_type
                            from utils.locked import check_commit_data
                            for objType, idList in items.items():

                                val_idens = [i for i in idList if i.startswith(get_model_prefix('Validator'))]
                                validated_idens = [i for i in idList if not i.startswith(get_model_prefix('Validator'))] # get validators for these items
                                if val_idens:
                                    objs = Validator.objects.filter(id__in=val_idens).exclude(id__in=exclude)
                                    for obj in objs:
                                        vals.append(obj)
                                if validated_idens:
                                    for model_name, iden_list in seperate_by_type(validated_idens).items():
                                        objs = get_dynamic_model(model_name, list=True, exclude={"id__in": exclude}, id__in=iden_list)
                                        for obj in objs:
                                            if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in vals and obj.Validator_obj.is_valid and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj):
                                                vals.append(obj.Validator_obj)
                                            elif has_field(obj, 'validators'):
                                                validators = Validator.objects.filter(id__in=[v_id for v_id in obj.validators])
                                                for v in validators:
                                                    if check_commit_data(v, obj.validators[v.id]):
                                                        vals.append(v)
                            data_to_send = [obj for obj in vals if verify_obj_to_data(obj, obj)]
                            if data_to_send:
                                for d in data_to_send:
                                    if d.id not in exclude:
                                        mbs = to_megabytes(d)
                                        if (total_mbs + mbs) < 45:
                                            total_mbs += mbs
                                            to_send_items.append(convert_to_dict(d))
                                            sending_idens.append(d.id)
                                        else:
                                            max_send = True
                                            break
                                compressed_data = compress_data(to_send_items)
                            return JsonResponse({'message' : 'Success', 'type':'Validator', 'content' : compressed_data, 'returning_idens':sending_idens, 'index' : index})

                        else:
                            if 'index' in requested_data:
                                index = int(requested_data['index'])
                            else:
                                index = 0
                            if obj_type == 'User': # include upk
                                if requested_update_dt:
                                    model = get_model(obj_type)
                                    timeField = get_timeData(model(), sort='updated', first_string=True)
                                    filter_kwargs = {"id__in": idList, f"{timeField}__gt": requested_update_dt}
                                    models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], order_by='created', exclude={"id__in": exclude}, **filter_kwargs)
                                else:
                                    models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], exclude={"id__in": exclude}, id__in=idList)
                                if models:
                                    for obj in models:
                                        if verify_obj_to_data(obj, obj):
                                            if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj):
                                                if obj.Validator_obj not in data_to_send and obj.Validator_obj.id not in exclude:
                                                    data_to_send.append(obj.Validator_obj)
                                                    found_items.append(obj.Validator_obj.id)
                                            # if not validator, add to missing_items
                                            if obj.object_type == 'Person':
                                                update = Update.objects.filter(pointerId=obj.id, validated=True).order_by('-DateTime').first()
                                                if update and update not in data_to_send and update not in exclude:
                                                    data_to_send.append(update)
                                                    found_items.append(update.id)
                                                    if update.Validator_obj and update.Validator_obj not in data_to_send and update.Validator_obj.id not in exclude:
                                                        data_to_send.append(update.Validator_obj)
                                                        found_items.append(update.Validator_obj.id)
                                                    # if not validator, add to missing_items
                                            data_to_send.append(obj)
                                            found_items.append(obj.id)
                                if requested_update_dt:
                                    model = get_model(obj_type)
                                    timeField = get_timeData(model(), sort='updated', first_string=True)
                                    filter_kwargs = {"User_obj__id__in": found_items, f"{timeField}__gt": requested_update_dt}
                                    models = get_dynamic_model('UserPubKey', list=True, order_by='created', exclude={"id__in": exclude}, **filter_kwargs)
                                else:
                                    models = get_dynamic_model('UserPubKey', list=True, exclude={"id__in": exclude}, User_obj__id__in=found_items)
                                if models:
                                    for obj in models:
                                        if verify_obj_to_data(obj, obj):
                                            if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj):
                                                if obj.Validator_obj not in data_to_send and obj.Validator_obj.id not in exclude:
                                                    data_to_send.append(obj.Validator_obj)
                                                    found_items.append(obj.Validator_obj.id)
                                                # if not validator, add to missing_items
                                            data_to_send.append(obj)
                                            found_items.append(obj.id)

                            else:
                                if requested_update_dt:
                                    model = get_model(obj_type)
                                    timeField = get_timeData(model(), sort='updated', first_string=True)
                                    filter_kwargs = {f"{timeField}__gte": requested_update_dt, "id__in":items}
                                    models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], order_by='created', exclude={"id__in": exclude}, **filter_kwargs)
                                else:
                                    models = get_dynamic_model(obj_type, list=[int(index), int(index) + max_obj_send_count], exclude={"id__in": exclude}, id__in=items)
                                if models:
                                    for obj in models:
                                        if verify_obj_to_data(obj, obj):
                                            if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj):
                                                if obj.Validator_obj not in data_to_send and obj.Validator_obj.id not in exclude:
                                                    data_to_send.append(obj.Validator_obj)
                                                    found_items.append(obj.Validator_obj.id)
                                                # if not validator, add to missing_items
                                            data_to_send.append(obj)
                                            found_items.append(obj.id)
                        if models or data_to_send:
                            prnt('has models', len(models), 'data_to_send',len(data_to_send))
                            total_mbs = 0
                            to_send_items = []
                            sending_idens = []
                            if data_to_send:
                                for d in data_to_send:
                                    if d.id not in exclude:
                                        mbs = to_megabytes(d)
                                        if (total_mbs + mbs) < 45:
                                            total_mbs += mbs
                                            to_send_items.append(convert_to_dict(d))
                                            sending_idens.append(d.id)
                                        else:
                                            max_send = True
                                            break
                            else:
                                for d in models:
                                    if d.id not in exclude:
                                        if has_field(d, 'Validator_obj') and d.Validator_obj:
                                            if d.Validator_obj not in exclude and d.Validator_obj not in to_send_items:
                                                total_mbs += to_megabytes(d)
                                                to_send_items.append(convert_to_dict(d.Validator_obj))
                                        mbs = to_megabytes(d)
                                        if (total_mbs + mbs) < 45:
                                            total_mbs += mbs
                                            to_send_items.append(convert_to_dict(d))
                                            sending_idens.append(d.id)
                                        else:
                                            max_send = True
                                            break
                            if max_send:
                                index = len(to_send_items)
                            # data_to_send = [convert_to_dict(obj) for obj in to_send_items if verify_obj_to_data(obj, obj)]
                            # validators = [convert_to_dict(obj.Validator_obj) for obj in to_send_items if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj not in validators and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj) and verify_obj_to_data(obj.Validator_obj, obj.Validator_obj)]
                            # data_size = get_object_size_in_mb(json.dumps(validators + data_to_send))
                            # if len(models) < max_obj_send_count:
                            #     index = 'end'
                            if to_send_items:
                                compressed_data = compress_data(to_send_items)
                            else:
                                compressed_data = []
                            prnt('returning...', total_mbs)
                            return JsonResponse({'message' : 'Success', 'type':obj_type, 'content' : compressed_data, 'returning_idens':sending_idens, 'index' : index})
                        else:
                            if index >= max_obj_send_count:
                                return JsonResponse({'message' : 'Success', 'type':obj_type, 'index':'end'})
                            else:
                                prnt('no models found')
                                return JsonResponse({'message' : 'None Found', 'type':obj_type})
            else:
                return JsonResponse({'message' : 'Fail', 'err' : 'header assessment'})
    except Exception as ex:
        e = str(ex)
        prnt('fail8472998',str(e))
        pass
    try:
        if not e:
            e = 'wtf?'
    except Exception as e:
        e = 'wtf@!'
        prnt('e',e)
    try:
        return JsonResponse({'message' : 'Fail', 'err' : str(e) + ' -- ' + err})
    except Exception as e:
        return JsonResponse({'message' : 'Fail', 'err2' : str(e) + ' -- ' + err})


@csrf_exempt
def receive_posts_for_validating_view(request):
    # take special note of receiving keyphrase or notification

    prnt('---receive_posts_for_validating_view')
    try:
        if request.method == 'POST':

            if assess_received_header(request.headers):
                raw_data = request.body.decode('utf-8')
                received_data = json.loads(raw_data)
                packet_id = received_data['packet_id']
                prnt('packet_id',packet_id)
                sender_id = received_data['senderId']
                if 'func' in received_data:
                    func = f'process_posts_for_validating:{received_data["func"]}'
                else:
                    func = f'process_posts_for_validating'
                # iden = hash_obj_id('DataPacket', specific_data=received_data)
                dp = DataPacket.objects.filter(id=packet_id).first()
                if not dp:
                    dp = DataPacket(id=packet_id, Node_obj_id=sender_id, func=func, data=received_data)
                    
                    dp.created = now_utc()
                    dp.save()
                elif 'posts_for_validating' not in dp.func:
                    dp.func = dp.func + '_' + func
                    dp.save()
                    
                if testing():
                    process_posts_for_validating(dp.id)
                else:
                    queue = django_rq.get_queue('low')
                    queue.enqueue(process_posts_for_validating, dp.id, job_timeout=600, result_ttl=3600)
                return JsonResponse({'message' : 'Success'})
            else:
                return JsonResponse({'message' : 'fail', 'error': 'invalid'})
        return JsonResponse({'message' : 'not post method'})
    except Exception as e:
        prnt('fail920589',str(e))
        return JsonResponse({'message' : 'fail', 'error':str(e)})


def get_chain_data_view(request):
    prnt('get_supported_chains_view')
    # returns genesisId of supported region chains, genesisId == region.id
    from blockchain.models import mandatoryChains, specialChains
    earth = Region.valid_objects.filter(Name='Earth').first()
    if earth:
        regions = {'Earth':{'type':earth.nameType,'id':earth.id,'children':[]}}
        def get_children(parent, children_list, support_found=False):
            children = Region.valid_objects.filter(ParentRegion_obj=parent).order_by('Name')
            for child in children:
                has_support = support_found
                # prnt(child.Name, has_support)
                gov = Government.objects.filter(Region_obj=child).first()
                data = {child.Name:{'obj_type':child.object_type,'type':child.nameType,'id':child.id,'children':[]}}
                if gov:
                    govData = {gov.gov_level:{'obj_type':gov.object_type,'type':'Government','id':gov.id,'regionId':gov.Region_obj.id,'children':[]}}
                # else:
                #     govData = None
                    # if govData:
                    data[child.Name]['children'].append(govData)
                if not has_support and child.is_supported:
                    has_support = True
                if not has_support or has_support and child.is_supported:
                    children_list.append(data)
                    new_list = data[child.Name]['children']
                    xlist = get_children(child, new_list, support_found=has_support)
                    new_list = data[child.Name]['children'] = xlist
                elif has_support and child.is_supported:
                    children_list.append(data)
                
            return children_list

        xlist = get_children(earth, regions['Earth']['children'])
        regions['Earth']['children'] = xlist
        # prnt('regions',regions)
        try:
            sonet = get_signing_data(Sonet.objects.first())
        except:
            sonet = None
        return JsonResponse({'mandatoryChains' : json.dumps(mandatoryChains), 'specialChains' : json.dumps(specialChains), 'regionChains' : json.dumps(regions), 'sonet' : sonet})
    
@csrf_exempt
def test_eventlog_view(request):
    prnt('---eventlog_view')
    if request.method == "POST":
        try:
            senderId = request.headers.get('senderId')
            prnt('senderId',senderId)
            sent_dt = request.headers.get('dt')
            prnt('sent_dt',sent_dt)
            dtsig = request.headers.get('dtsig')
            prnt('dtsig',dtsig)

            body = request.body
            received_data = body.decode('utf-8')
            json_data = json.loads(received_data)
            iden = hash_obj_id('DataPacket', specific_data=received_data)
            dp = DataPacket.objects.filter(id=iden, func='eventlog_view').first()
            prnt('dp',dp)
            if not dp:
                prnt('creating dp')
                dp = DataPacket(id=iden, func='eventlog_view', data=received_data)
                
                dp.created = now_utc()
                dp.save()
                prnt('dp saved')
            prnt('proper received')
            return JsonResponse({"message": "Data stored successfully!", "event_id": dp.id})
        except Exception as e:
            prnt('fail472t645',str(e))
            return JsonResponse({"error": str(e)}, status=400)
    prnt('data not received')
    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)


@csrf_exempt
def receive_blocks_view(request):
    prnt('--receive_blocks')
    if request.method == 'POST':
        try:
            if assess_received_header(request.headers):
                raw_data = request.body.decode('utf-8')
                received_data = json.loads(raw_data)
                prnt('received_data',str(received_data)[:500]) 
                data_type = received_data.get('type')
                prnt('received -data_type',data_type)
                packet_id = received_data['packet_id']
                sender_id = received_data['senderId']
                prnt('packet_id',packet_id)
                prnt('senderId',sender_id)
                # iden = hash_obj_id('DataPacket', specific_data=received_data)
                dp = DataPacket.objects.filter(id=packet_id).first()
                prnt('dp',dp)
                if not dp:
                    prnt('creating dp')
                    dp = DataPacket(id=packet_id, Node_obj_id=sender_id, func='process_received_blocks', created = now_utc(), data=received_data)
                    dp.save()
                    prnt('dp2',dp)

                # log = EventLog.objects.filter(id=iden).first()
                # if not log:
                #     log = EventLog(id=iden, type='process_received_blocks', data=received_data)
                #     log.Node_obj = get_self_node()
                #     log.created = now_utc()
                #     log.save()
                    if run_as_worker:
                        prnt('add worker job')
                        queue = django_rq.get_queue('main')
                        queue.enqueue(process_received_blocks, dp.id, job_timeout=500, result_ttl=3600)
                    else:
                        prnt('run right now')
                        process_received_blocks(dp)
                return JsonResponse({'message' : 'Success'})
        except Exception as e:
            prnt('fail58926395',str(e))
            return JsonResponse({'message' : f'error:{str(e)}'})
    prnt('not post')
    return JsonResponse({'message' : f'None'})

@csrf_exempt
def receive_data_packet_view(request):
    prnt('receive_data_packet_view')
    if request.method == 'POST':
        if assess_received_header(request.headers):
            received_data = json.loads(request.body.decode('utf-8'))
            packet_id = received_data['packet_id']
            prnt('packet_id',packet_id)
            sender_id = received_data['senderId']

            # iden = hash_obj_id('DataPacket', specific_data=received_data)
            func = 'process_data_packet'
            dp = DataPacket.objects.filter(id=packet_id).first()
            if not dp:
                try:
                    dp = DataPacket(id=packet_id, Node_obj_id=sender_id, func='process_data_packet', data=received_data)
                    dp.created = now_utc()
                    dp.save()
                except:
                    if not Node.objects.all().count():
                        dp = DataPacket(id=packet_id, func='process_data_packet', data=received_data)
                        dp.created = now_utc()
                        dp.save()

            if 'completed' not in dp.func:
            #     dp.func = dp.func + '_' + func
            #     dp.save()

                queue = django_rq.get_queue('low')
                queue.enqueue(process_data_packet, dp.id, job_timeout=240, result_ttl=3600)
            return JsonResponse({'message' : 'Success'})
    return JsonResponse({'message' : 'not post method'})
        
        
@csrf_exempt # not used
def receive_validations_view(request):
    prnt('receive_validations_view')
    try:
        if request.method == 'POST':
            if assess_received_header(request.headers):
                received_data = json.loads(request.body.decode('utf-8'))
                packet_id = received_data['packet_id']
                sender_id = received_data['senderId']
                data_type = received_data.get('type')
                prnt('received -data_type',data_type)
                # iden = hash_obj_id('EventLog', specific_data=received_data)
                log = EventLog.objects.filter(id=packet_id, data=received_data).first()
                if not log:
                    log = EventLog(id=packet_id, Node_obj_id=sender_id, type='process_received_validations', data=received_data)
                    log.save()

                    if run_as_worker:
                        queue = django_rq.get_queue('low')
                        queue.enqueue(process_received_validations, log.id, job_timeout=310, result_ttl=3600)
                    else:
                        process_received_validations(log.id)

                return JsonResponse({'message' : 'Success'})
    except Exception as e:
        prnt('failgj39284',str(e))
        return JsonResponse({'message' : f'error:{str(e)}'})



# Connecting new nodes, not used I think
# @csrf_exempt
def node_update(request):
    if request.method == 'POST':
        update_node_data(json.loads(request.body)['node_data'])
        return JsonResponse({'message':'Success'})
    else:
        return JsonResponse({'message':'not post method'})

