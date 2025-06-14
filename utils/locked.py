
# from utils.models import prnt
import uuid
import hashlib
import datetime
import json


# DO NOT CHANGE THIS FILE
# WILL BREAK ALL VALIDATIONS



skip_sign_fields = [
        'signature','validated','is_active','proposed_modification',
        'password','keyword_array','hash','fcm_capable','ai_capable',
        'coins','last_login','date_joined','Block_obj','nodeCreatorId',
        'suspended_dt','expelled','isVerified','validators','nodeBlockId',
        'blockchainId','groups','user_permissions','updated_on_node',
        'Validator_obj','new','date_created','must_rename','Update_obj',
        'is_superuser','is_staff','display_hour','latestModel','enacted',
        'SenderBlock_obj','ReceiverBlock_obj','validation_error', 'notes',
        'blockchainType','secondChainType','is_modifiable','BillText_obj',
        'queued_dt','plugin_prefix','is_modifiable'
        ]


def process_posts_for_validating(received_json):
    from utils.models import process_received_dp, decompress_data,prnt, now_utc
    prnt('----process_posts_for_validating now_utc:',now_utc(),str(received_json)[:300])
    from django.db import models
    result = process_received_dp(received_json, 'process_posts_for_validating')
    if result and 'dp' in result:
        log = result['dp']
        received_json = log.data
    elif result and 'data' in result:
        received_json = result['data']
        log = None
    else:
        received_json = {}
        log = None
    # prnt('----result333445',result)
    if log and isinstance(log, models.Model):
        if 'process' not in log.func:
            return 'previously completed'
    if not received_json:
        return 'no content'
        
    content = decompress_data(received_json['content'])
    # prnt('content:',content)
    # for i in content:
    #     prnt('c:',i)

    no_post = []
    created = 0
    matches = 0
    mismatches = []
    skipped_items = []
    validated_idens = []
    invalid_idens = []
    waiting_for_self_scrape = []
    total = 'x'
    region_name = 'unknown'
    func = 'unknown'
    q = 00
    if received_json and received_json['type'] == 'for_validation':
        from posts.models import Update, Post
        from legis.models import Government
        from blockchain.models import logError, logEvent, Validator, Blockchain,script_created_modifiable_models,get_scrape_duty,max_validation_window
        from utils.models import get_model_prefix, get_self_node, get_node, find_or_create_chain_from_object, get_latest_dataPacket, data_sort_priority, testing, check_missing_data, prntDebugn, prntDebug, is_locked, has_field, has_method, convert_to_datetime, sigData_to_hash,get_or_create_model,super_sync,get_model,exists_in_worker,create_dynamic_model,skipped_items,dynamic_bulk_update,seperate_by_type,get_model_prefix,debugging,string_to_dt
        validator = None
        invalid_validator = None
        add_val_to_obj = []
        self_node = get_self_node()
        sender_node = get_node(id=received_json['senderId'])
        func = received_json['func']
        job_dt = None
        if 'job_id' in received_json:
            job_id = received_json['job_id']
        else:
            job_id = None
        if 'job_dt' in received_json:
            job_dt = string_to_dt(received_json['job_dt'])
            prnt('job_dt1',dt_to_string(job_dt))
        blockchain = None
        dataPacket = None
        gov = Government.objects.filter(id=received_json['gov_id']).first()
        if gov:
            chainId = 'All'
            blockchain, obj, receiverChain = find_or_create_chain_from_object(gov)
            if blockchain:
                chainId = blockchain.id
                dataPacket = get_latest_dataPacket(blockchain.id)
            region_name = gov.Region_obj.Name
            region_id = gov.Region_obj.id
            gov_level = gov.gov_level
            region = gov.Region_obj
        else:
            # from posts.models import check_missing_data
            check_result = check_missing_data(received_json['gov_id'], retrieve_missing=True, log_missing=True, downstream_worker=False)
            if check_result and 'found_idens' in check_result and received_json['gov_id'] in check_result['found_idens']:
                gov = Government.objects.filter(id=received_json['gov_id']).first()
                if gov:
                    chainId = 'All'
                    blockchain, obj, receiverChain = find_or_create_chain_from_object(gov)
                    if blockchain:
                        chainId = blockchain.id
                        dataPacket = get_latest_dataPacket(blockchain.id)
                    region_name = gov.Region_obj.Name
                    region_id = gov.Region_obj.id
                    gov_level = gov.gov_level
                    region = gov.Region_obj
            if not gov:
                region = json.loads(received_json['region_dict'])
                region_name = region['Name']
                region_id = region['id']
                gov_level = received_json['gov_level']
        bypass = False

        if not job_dt:
            created_string = content[0]['created']
            job_dt = dt_to_string(created_string)
            prnt('job_dt2',dt_to_string(job_dt))
            prnt('job_dt2a',content[0]['id'])
        sorted_content = sorted(content, key=data_sort_priority)
        total = len(sorted_content)
        validated_idens = []
        matched_idens = []
        model_types = []
        exceptions = ['Update'] # these do not need to be stated in scraper approved_models

        # check that Update.pointerType is included in approved_models
        # perhaps created time should match job_dt?

        for i in sorted_content:
            if i['func'] != func or i['validatorNodeId'] != self_node.id or i['creatorNodeId'] != sender_node.id or i['id'] != hash_obj_id(i):
                prnt('-request to valid discrepancy')
                err = '-'
                if i['func'] != func:
                    err = err + f'func {func}, ifunc:{i["func"]}, '
                if i['validatorNodeId'] != self_node.id:
                    prnt("i['validatorNodeId']",i['validatorNodeId'],'self_node.id',self_node.id)
                    err = err + f'validatorNodeId {i["validatorNodeId"]}, self_node:{self_node.id}, '
                if i['creatorNodeId'] != sender_node.id:
                    prnt("i['creatorNodeId']",i['creatorNodeId'],'sender_node.id',sender_node.id)
                    err = err + f'creatorNodeId {i["creatorNodeId"]}, sender_node.id:{sender_node.id}, '
                if i['id'] != hash_obj_id(i):
                    prnt('hash_obj_id(i)',hash_obj_id(i),"i['id']",i['id'])
                    err = err + f'hash_obj_id(i) {hash_obj_id(i)}, id:{i["id"]}, '
                    from posts.models import get_dynamic_model
                    obj = get_dynamic_model(i['object_type'], id=i['id'])
                    prnt('obj',obj)
                    if obj:
                        iden = hash_obj_id(i)
                        prnt('iden',iden)
                        err = err + f'obj iden: {iden} '
                logError(f'ValidatePosts fail', code='8723354', func='processes_posts_for_validating', extra={'item':str(i)[:500], 'err':err})
                return
            elif i['object_type'] not in exceptions and i['object_type'] not in model_types:
                # prntDebug('--accepted',i)
                model_types.append(i['object_type'])
        if bypass and testing():
            scraper_list = [{'function_name':func, 'region_id':region_id, 'scraping_order':[sender_node], 'validator':self_node}]
            approved_funcs = [func]
        else:
            scraper_list, approved_models = get_scrape_duty(gov=gov, receivedDt=job_dt, region=region, gov_level=gov_level, func=func)
            approved_funcs = []
            for key, value in approved_models.items():
                result = all(item in value for item in model_types)
                # prnt('result',result,'key111',key,'value',value)
                if result:
                    approved_funcs.append(key)
        prntDebugn('scraper_list',scraper_list)
        q = {'func':func,'approved_funcs':approved_funcs,'model_types':model_types}
        if func in approved_funcs:
            q = 10
            try:
                processed_data = {'obj_ids':[],'hashes':{}}
                for i in scraper_list:
                    q = 1
                    if i['function_name'] == func and region_id == i['region_id']:
                        q = 2
                        if sender_node.id in i['scraping_order'] and self_node.id == i['validator']:
                            q = 21
                            # if self_node.id not in i['scraping_order'] or len(i['scraping_order']) == 1:
                            # q = 3
                            logEvent(f'ValidatePosts: {region_name} {func} len:{len(sorted_content)}', log_type='Tasks', func=func)
                            # from accounts.models import verify_obj_to_data
                            # from posts.models import get_dynamic_model, super_sync, get_or_create_model, create_dynamic_model
                            for z in sorted_content:
                                try:
                                    prntDebug('zitem',z['id'])
                                except:
                                    prntDebug('zitem',str(z)[:100])
                                try:
                                    q = 3
                                    if any(n == z['creatorNodeId'] for n in i['scraping_order']) and z['validatorNodeId'] == self_node.id and z['id'] != '0':
                                        q = 31
                                        if self_node.id != z['creatorNodeId'] or len(i['scraping_order']) == 1:
                                            q = 4
                                            if not blockchain:
                                                blockchain, obj, secondChain = find_or_create_chain_from_object(obj)
                                                dataPacket = get_latest_dataPacket(blockchain)
                                            if not validator:
                                                if job_id:
                                                    validator = Validator.objects.filter(jobId=job_id, CreatorNode_obj=self_node, func=func, is_valid=True).order_by('-created').first()
                                                else:
                                                    validator = Validator.objects.filter(CreatorNode_obj=self_node, func=func, is_valid=True).order_by('-created').first()
                                                if not validator:
                                                    validator = Validator(blockchainType=blockchain.genesisType, jobId=job_id, blockchainId=blockchain.id, CreatorNode_obj=self_node, created=job_dt, validatorType='scraper', func=func, is_valid=True)
                                                    validator.save()
                                                prnt('scrape val created',validator.id, dt_to_string(now_utc()))
                                                if validator and is_locked(validator):
                                                    q = 41
                                                    break

                                            if verify_obj_to_data(None, z, user=sender_node.User_obj):
                                                q = 5
                                                obj = get_dynamic_model(z['object_type'], id=z['id'])
                                                # obj, is_new = get_or_create_model(z['object_type'], return_is_new=True, id=z['id'])
                                                if obj and has_field(obj, 'Validator_obj') and not obj.Validator_obj or obj and has_field(obj, 'Validator_obj') and not obj.Validator_obj.is_valid:
                                                    q = 6
                                                    prnt('q6')
                                                    # obj = create_dynamic_model(z['object_type'], id=z['id'])
                                                    if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.id in obj.Validator_obj.data and obj.Validator_obj.data[obj.id] == sigData_to_hash(obj):
                                                        skipped_items.append(obj.id)
                                                    else:
                                                        proceed = True
                                                        if has_method(obj, 'required_for_validation'):
                                                            for c in obj.required_for_validation():
                                                                if c not in z or not z[c]:
                                                                    proceed = False
                                                                    q = 61
                                                                    break
                                                        if proceed and convert_to_datetime(z['created']) < now_utc() - datetime.timedelta(days=max_validation_window):
                                                            proceed = False
                                                            q = 62
                                                        prntDebug('proceed',proceed)
                                                        if proceed:
                                                            q = 7
                                                            mismatch = False
                                                            fields = obj._meta.fields
                                                            bypass_fields = ['last_updated','creatorNodeId','created','publicKey','func'] + skip_sign_fields
                                                            for f in fields:
                                                                attr = None
                                                                z_field = None
                                                                try:
                                                                    attr = getattr(obj, f.name)
                                                                    if isinstance(attr, models.Model):
                                                                        attr = attr.id
                                                                except Exception as e:
                                                                    pass
                                                                try:
                                                                    z_field = z[f.name]
                                                                    z_field = dt_to_string(z_field)
                                                                except Exception as e:
                                                                    # prnt(str(e))
                                                                    pass
                                                                if f.name not in bypass_fields and attr and z_field and sort_for_sign(attr) != sort_for_sign(z_field):
                                                                    prnt('mismatch break!','field:',f.name,'-getattr',attr,'-received:',z_field)
                                                                    # logError('mismatch break', code='9457264', func='processes_posts_for_validating', extra={'z':z['id'],'field':f.name,'getattr':attr,'received':z_field})
                                                                    mismatch = True
                                                                    break
                                                            if mismatch:
                                                                q = 8
                                                                def compare_texts(text1, text2, context=10):
                                                                    # print('compare_texts')
                                                                    min_length = min(len(text1), len(text2))
                                                                    result = ''
                                                                    count = 0
                                                                    for i in range(min_length):
                                                                        if text1[i] != text2[i]:
                                                                            if count < 20:
                                                                                start = max(0, i - context)
                                                                                end = min(len(text1), len(text2), i + context + 1)
                                                                                snippet1 = text1[start:end]
                                                                                snippet2 = text2[start:end]
                                                                                
                                                                                result += f"pos:{i}:Text1:...{snippet1}...Text2: ...{snippet2}..."
                                                                            count += 1
                                                                            # print(f"Text 1: ...{snippet1}...")
                                                                            # print(f"Text 2: ...{snippet2}...\n")
                                                                    result = f'count:{count}: {result}'
                                                                    if len(text1) != len(text2):
                                                                        # prnt("Texts have different lengths.")
                                                                        longer_text, shorter_text = (text1, text2) if len(text1) > len(text2) else (text2, text1)
                                                                        result += f"Extra characters in longer text: {longer_text[len(shorter_text):]}"
                                                                    return result
                                                                prnt('---items do not match', obj)
                                                                mismatches.append(z['id'])
                                                                # if obj.updated_on_node:
                                                                #     u_time = obj.updated_on_node.isoformat()
                                                                # else:
                                                                #     u_time = 'none'
                                                                err_data = {'id':z['id'],'now':dt_to_string(now_utc()),'mismatch_field':f.name, 'z-valid':verify_obj_to_data(None, z, user=sender_node.User_obj), 'obj-valid':verify_obj_to_data(None, obj, user=sender_node.User_obj),'field_comparison': compare_texts(str(attr),str(z_field))}
                                                                # err_data = {'id':z['id'],'now':dt_to_string(now_utc()),'obj_updated_on_node':u_time,'f.name':f.name,'z':z[f.name], 'z-valid':verify_obj_to_data(None, z, user=sender_node.User_obj), 'obj-valid':verify_obj_to_data(None, obj, user=sender_node.User_obj),'obj_attr':str(attr)[:500],'received_attr':str(z_field)[:500]}
                                                                # if 'created' in z:
                                                                #     err_data['z_created'] = z['created']
                                                                #     err_data['obj_created'] = obj.created.isoformat()
                                                                # elif 'created' in z:
                                                                #     err_data['z_created'] = z['created']
                                                                #     err_data['obj_created'] = obj.created.isoformat()
                                                                # else:
                                                                #     err_data['z_added'] = z['added']
                                                                #     err_data['obj_added'] = obj.added.isoformat()
                                                                if not invalid_validator:
                                                                    invalid_validator = Validator.objects.filter(jobId=job_id, CreatorNode_obj=self_node, func=f'inval_{func}', is_valid=False).first()
                                                                    if not invalid_validator:
                                                                        invalid_validator = Validator(blockchainType=blockchain.genesisType, jobId=job_id, blockchainId=blockchain.id, CreatorNode_obj=self_node, created=job_dt, validatorType='scraper', func=f'inval_{func}', is_valid=False)
                                                                        invalid_validator.save()
                                                                    prnt('scrape invalid_validator created',invalid_validator.id, dt_to_string(now_utc()))
                                                                invalid_validator.data[obj.id] = sigData_to_hash(obj)




                                                                logError('mismatch break', code='64523', func='processes_posts_for_validating', extra=str(err_data)[:1000])
                                                            else:
                                                                q = 9
                                                                prnt('---items match', obj)
                                                                matches += 1
                                                                if has_field(obj, 'proposed_modification') and obj.proposed_modification:
                                                                    prnt('proposed_modification')
                                                                    modded_obj = obj
                                                                    obj = get_or_create_model(modded_obj.object_type, id=modded_obj.proposed_modification)
                                                                    if not obj.Name or obj.Name == modded_obj.Name:
                                                                        obj = super_sync(obj, convert_to_dict(modded_obj), skip_fields=['latestModel','id'])
                                                                        obj.proposed_modification = None
                                                                        obj.Validator_obj = None
                                                                        obj.save()
                                                                        obj = sign_obj(obj)
                                                                        modded_chain = Blockchain.objects.filter(genesisId=modded_obj.id).first()
                                                                        if modded_chain:
                                                                            super(get_model(modded_chain.object_type), modded_chain).delete()
                                                                        super(get_model(modded_obj.object_type), modded_obj).delete()
                                                                # if not blockchain:
                                                                #     blockchain, obj, secondChain = find_or_create_chain_from_object(obj)
                                                                #     dataPacket = get_latest_dataPacket(blockchain)
                                                                # if not validator:
                                                                #     validator = Validator(blockchainType=blockchain.genesisType, blockchainId=blockchain.id, CreatorNode_obj=self_node, added=job_dt, validatorType='scraper', func=func, is_valid=True)
                                                                #     validator.save()
                                                                #     prnt('scrape val created',validator.id)
                                                                q = 91
                                                                if not is_locked(obj):
                                                                    if has_field(obj, 'creatorNodeId') and obj.creatorNodeId == self_node.id:
                                                                        obj = super_sync(obj, z, do_save=True)
                                                                    obj_hash = sigData_to_hash(obj)
                                                                    validator.data[obj.id] = obj_hash
                                                                    matched_idens.append(obj.id)
                                                
                                                elif obj and has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj.is_valid:
                                                    q = 81
                                                    matches += 1
                                                    if dataPacket:
                                                        dataPacket.add_item_to_share([obj, obj.Validator_obj])
                                                elif self_node.id in i['scraping_order']:
                                                    q = 96
                                                    prnt('q96', obj)
                                                    waiting_for_self_scrape.append(z['id'])
                                                    if len(waiting_for_self_scrape) >= len(sorted_content):
                                                        prnt('awating items from self',waiting_for_self_scrape)
                                                        if job_dt > now_utc() - datetime.timedelta(minutes=60):
                                                            if not exists_in_worker('process_posts_for_validating', log.id, queue_name='low', job_count=2):
                                                                import random
                                                                import django_rq
                                                                run_at = now_utc() + datetime.timedelta(minutes=random.randint(4, 12))
                                                                django_rq.get_scheduler('low').enqueue_at(run_at, process_posts_for_validating, log.id, timeout=600)
                                                            prnt('self still scraping - rerun later')
                                                            return f'self still scraping - rerun later'
                                                        elif log:
                                                            log.completed(f'err:{q}-no_self_scrape')
                                                        break
                                                elif not obj:
                                                    q = 10
                                                    obj = create_dynamic_model(z['object_type'], id=z['id'])
                                                    prnt('creating item',obj)
                                                    obj = super_sync(obj, z, do_save=True)
                                                    if has_method(obj, 'boot'):
                                                        obj.boot()
                                                    created += 1
                                                else:
                                                    q = 82
                                                    try:
                                                        prntDebug('xitem',z['id'])
                                                        skipped_items.append(z['id'])
                                                    except:
                                                        prntDebug('xitem',str(z)[:100])
                                                        skipped_items.append(str(z)[:50])
                                                    
                                            else:
                                                q = 83
                                                invalid_idens.append(z['id'])
                                                if not invalid_validator:
                                                    invalid_validator = Validator(blockchainType=blockchain.genesisType, blockchainId=blockchain.id, CreatorNode_obj=self_node, created=job_dt, validatorType='scraper', func=func, is_valid=False)
                                                    invalid_validator.save()
                                                    prnt('scrape invalid_validator created',invalid_validator.id)
                                                    invalid_validator.data[obj.id] = sigData_to_hash(obj)
                                            #     q = 99
                                            #     prntDebug('break1 - failed verify')
                                            #     if log:
                                            #         log.completed('failed verify')
                                            #     break
                                        else:
                                            q = 98
                                            prntDebug('break2 - self created obj')
                                            if log:
                                                log.completed(note='self created objs')
                                            if validator:
                                                validator.delete()
                                            break
                                    else:
                                        q = 97
                                        prntDebug('break3 - created by wrong node or self not assigned validator')
                                        if log:
                                            log.completed('incorrect assigned scraper or validator')
                                        if validator:
                                            validator.delete()
                                        break
                                except Exception as e:
                                    prntDebug('fail48274',str(e))
                                    if 'id' in z:
                                        iden = z['id']
                                    else:
                                        iden = str(z)[:100]
                                    logError(f'ValidatePost fail {str(e)}', code='836563', func='processes_posts_for_validating', extra={'q':q,'iden':iden})
                                prnt('Q:',q)
                sorted_content.clear()
                now = now_utc()
                if invalid_validator and invalid_validator.data:
                    q = 84
                    prnt('invalid_validator:',invalid_validator)
                    invalid_validator = sign_obj(invalid_validator)
                    if verify_obj_to_data(invalid_validator, invalid_validator):
                        q = 85
                        # if blockchain:
                        #     blockchain.add_item_to_queue(invalid_validator)
                        if dataPacket:
                            dataPacket.add_item_to_share(invalid_validator)

                if validator and validator.data:
                    q = 11
                    
                    prnt('validator:',validator)
                    validator = sign_obj(validator)
                    if verify_obj_to_data(validator, validator):
                        q = 12
                        if blockchain:
                            blockchain.add_item_to_queue(validator)

                        relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=job_dt, genesisId=NodeChain_genesisId, include_peers=True)
                        node_block_data = {'node_ids':[n for n in relevant_nodes],'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}


                        prntDebug(f'val posts step1')
                        logEvent(f'ValidatePosts matched_idens: {len(matched_idens)} items', func=func)
                        pointerIdens = [i for i in matched_idens if not i.startswith(get_model_prefix('Update')) and not i.startswith(get_model_prefix('Notification')) and not i.startswith(get_model_prefix('BillText'))]
                        no_post = pointerIdens
                        from posts.models import update_post
                        while pointerIdens:
                            q = 121
                            bulk_update = []
                            fields = []
                            posts = Post.all_objects.filter(pointerId__in=pointerIdens[:500]).exclude(validated=True)
                            for p in posts:
                                if validate_obj(obj=p, pointer=None, validator=validator, node_block_data=node_block_data, save_obj=False, verify_validator=False, update_pointer=False):
                                # validated = p.validate(validator=validator, update_pointer=False, save_self=False, verify_validator=False, node_block_data=node_block_data)
                                # if validated:
                                    p.validated = True
                                    p.updated_on_node = now
                                    p, updated_fields = update_post(p=p, save_p=False)
                                    validated_idens.append(p.pointerId)
                                    bulk_update.append(p)
                                    if updated_fields:
                                        fields += [f for f in updated_fields if f not in fields]
                                no_post.remove(p.pointerId)
                            posts = None
                            q = 122
                            prnt(f'val posts bulk_update: {str(bulk_update)[:100]}')
                            if bulk_update:
                                dynamic_bulk_update(model=Post, items_field_update=['validated', 'updated_on_node'] + fields, items=bulk_update)
                            if len(pointerIdens) >= 500:
                                pointerIdens = pointerIdens[500:]
                            else:
                                pointerIdens = []
                            q = 123
                        q = 124



                        prntDebug(f'val posts step2')
                        verifiedIdens = [i for i in matched_idens if not i.startswith(get_model_prefix('Update')) and not i.startswith(get_model_prefix('Notification'))]
                        logEvent(f'ValidatePosts validated_idens: {len(verifiedIdens)} items, x:{str(verifiedIdens)[:500]}', func=func)
                        if verifiedIdens:
                            q = 13
                            for model_name, id_list in seperate_by_type(verifiedIdens).items():
                                q = 131
                                objIdens = id_list
                                while objIdens:
                                    q = 132
                                    dynamic_bulk_update(model_name, update_data={'Validator_obj': validator}, id__in=objIdens[:500])
                                    q = 133
                                    if blockchain:
                                        q = 136
                                        blockchain.add_item_to_queue(objIdens[:500])
                                    if len(objIdens) >= 500:
                                        q = 134
                                        objIdens = objIdens[500:]
                                    else:
                                        q = 135
                                        objIdens = []
                                    

                        prntDebug(f'val posts step3')
                        q = 140
                        updateIdens = [u for u in matched_idens if u.startswith(get_model_prefix('Update'))]
                        if updateIdens:
                            q = 14
                            bulk_update = []
                            updates = Update.objects.filter(id__in=updateIdens).exclude(validated=True)
                            for u in updates:
                                if not is_locked(u):
                                    if validate_obj(obj=u, pointer=None, validator=validator, node_block_data=node_block_data, save_obj=False, verify_validator=False, update_pointer=False):
                                    # validated = u.validate(validator=validator, save_self=False, verify_validator=False, node_block_data=node_block_data)
                                    # if validated:
                                        u.validated = True
                                        u.updated_on_node = now
                                        u.Validator_obj = validator
                                        validated_idens.append(u.id)
                                        bulk_update.append(u)
                            updates = None
                            q = 141
                            if bulk_update:
                                items = dynamic_bulk_update(model=Update, items_field_update=['validated', 'Validator_obj','updated_on_node'], items=bulk_update, return_items=True)
                                if blockchain:
                                    blockchain.add_item_to_queue(items)
                        q = 142
                            

                        prntDebug(f'val posts step4')
                        from accounts.models import Notification
                        notiIdens = [u for u in matched_idens if u.startswith(get_model_prefix('Notification'))]
                        if notiIdens:
                            q = 15
                            bulk_update = []
                            notifications = Notification.objects.filter(id__in=notiIdens).exclude(validated=True)
                            for n in notifications:
                                if not is_locked(n):
                                    if validate_obj(obj=n, pointer=None, validator=validator, node_block_data=node_block_data, save_obj=False, update_pointer=False, verify_validator=False, add_to_queue=False):
                                    # validated = n.validate(validator=validator, add_to_queue=False, save_self=False, verify_validator=False, node_block_data=node_block_data)
                                    # if validated:
                                        n.validated = True
                                        n.updated_on_node = now
                                        n.Validator_obj = validator
                                        validated_idens.append(n.id)
                                        bulk_update.append(n)
                            notifications = None
                            if bulk_update:
                                items = dynamic_bulk_update(model=Notification, items_field_update=['validated', 'Validator_obj','updated_on_node'], items=bulk_update, return_items=True)
                                if blockchain:
                                    blockchain.add_item_to_queue(items)


                        prntDebug(f'val posts step5')
                        chains = {}
                        q = 16
                        for m in script_created_modifiable_models:
                            mIdens = [u for u in matched_idens if u.startswith(get_model_prefix(m))]
                            if mIdens:
                                objs = get_dynamic_model(m, list=True, id__in=mIdens)
                                for o in objs:
                                    chain, o, secondChain = find_or_create_chain_from_object(o)
                                    if chain:
                                        if chain not in chains:
                                            chains[chain] = []
                                        chains[chain].append(o)
                                objs = None
                        if chains:
                            for chain in chains:
                                if chain != blockchain:
                                    chain.add_item_to_queue(chains[chain])
                        if dataPacket:
                            dataPacket.add_item_to_share(validated_idens + [validator.id])

                        prntDebug(f'val posts step6')
            except Exception as e:
                prnt('fail3920567',str(e))
                logError(f'ValidatePosts fail {str(e)}', code='83745', func='processes_posts_for_validating', extra={'q':q,"log":log.id if log else'none'})
                if log:
                    log.completed(f'err:{q}:{str(e)}')
                result = f'ValidatePosts result: err:{q}:{str(e)}'
                if log:
                    log.notes[dt_to_string(now_utc())] = {'result':result}
                    log.save()
                return result
            prnt('func',func,'matches',matches,'mismatches',len(mismatches),'created',created,'missing:',total - matches - len(mismatches) - len(skipped_items) - created - len(invalid_idens),'invalid_idens',len(invalid_idens),'waiting_for_self_scrape',waiting_for_self_scrape,'q',str(q))
    if log:
        prnt('has log',log)
        logEvent(f'ValidatePosts result: {region_name} {func} q:{q}, log:{log.id}, total:{total}, validated_idens:{len(validated_idens)}, matches:{matches},mismatches:{mismatches},created:{created},no_post:{len(no_post)}, skipped_items:{skipped_items}, invalid_idens:{invalid_idens}, waiting_for_self_scrape:{len(waiting_for_self_scrape)}, missing:{total - matches - len(mismatches) - len(skipped_items) - created}', log_type='Tasks')
        if total > (matches + created + len(skipped_items) + len(no_post) + len(invalid_idens)) and debugging():
            # missing:{total - matches - len(mismatches) - len(skipped_items) - created},
            pass
        else:
            log.completed()
    else:
        prnt('does not have log')
    prnt('done validating posts')
    result = f'ValidatePosts result: {region_name} {func} q:{q}, total:{total}, validated_idens:{len(validated_idens)}, matches:{matches},mismatches:{mismatches},created:{created},no_post:{len(no_post)}, skipped_items:{skipped_items}, invalid_idens:{invalid_idens}, waiting_for_self_scrape:{waiting_for_self_scrape}, missing:{total - matches - len(mismatches) - len(skipped_items) - created - len(invalid_idens)}, log:{str(convert_to_dict(log))[:200]}'
    if log:
        log.notes[dt_to_string(now_utc())] = {'result':result}
        log.save()
    return result

def check_validation_consensus(block, do_mark_valid=True, broadcast_if_unknown=False, downstream_worker=True, handle_discrepancies=True, backcheck=False, get_missing_blocks=True):
    from utils.models import to_datetime, prntDebug, create_job, sigData_to_hash, get_self_node, now_utc,prnt
    prnt('--check_validation_consensus now_utc:', now_utc(),do_mark_valid,block)
    from blockchain.models import NodeChain_genesisId, Block, Validator, logEvent, resolve_block_differences, retrieve_missing_blocks, send_missing_blocks, request_items
    # return is_valid, consensus_found, validators
    is_new_validation = False
    is_valid = None

    b_dt = to_datetime(block.DateTime)
    b_ct = to_datetime(block.created)
    # if isinstance(block.DateTime, datetime.datetime):
    #     b_dt = block.DateTime
    # else:
    #     b_dt = dt_to_string(block.DateTime)
    # if isinstance(block.created, datetime.datetime):
    #     b_ct = block.created
    # else:
    #     b_ct = dt_to_string(block.created)
    if not block.signature:
        block.is_not_valid(note='no_sig', mark_strike=False)
        prntDebug('p000 block no sig')
        return False, True, []
    if block.Blockchain_obj.genesisType != 'Nodes' and block.Blockchain_obj.genesisType != 'Wallet':
        if b_ct.minute < 50 or b_dt.minute != 50:
            block.is_not_valid(note='wrong_datetime_data')
            prntDebug('p00 created_at_wrong_time')
            return False, True, []
    
    if backcheck and block.index > 1:
        prev_block = Block.objects.filter(blockchainId=block.blockchainId, index=block.index-1, validated=True).first()
    elif backcheck:
        prev_block = None
    else:
        prev_block = block.get_previous_block(is_validated=True, return_chain=False)
    prntDebug('prev_block',prev_block)

    if prev_block and prev_block.hash != block.previous_hash or sigData_to_hash(block) != block.hash:
        prnt(f'prev_block.hash:{prev_block.hash if prev_block else "0"}, block.previous_hash:{block.previous_hash}, sigData_to_hash(block):{sigData_to_hash(block)}, block.hash:{block.hash}')
        carry_on = False
        logEvent(f'prev_block.hash:{prev_block.hash if prev_block else "0"}, block.previous_hash:{block.previous_hash}, sigData_to_hash(block):{sigData_to_hash(block)}, block.hash:{block.hash}, handle_discrepancies:{handle_discrepancies}, prev_block.index:{prev_block.index if prev_block else "x"}, block.index:{block.index}')
        if handle_discrepancies and prev_block:
            if int(prev_block.index) == int(block.index):
                winning_block, validations = resolve_block_differences(block)
                if block.hash != winning_block.hash:
                    create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=block.Blockchain_obj, starting_index=winning_block.index, send_to=block.CreatorNode_obj.id)
                    
                if winning_block and not winning_block.validated:
                    block.is_not_valid(note='did_not_pass_discrepenacies1')
                    block = winning_block
                    if block.get_previous_hash() == block.previous_hash and sigData_to_hash(block) == block.hash:
                        prev_block = block.get_previous_block(is_validated=True)
                        carry_on = True
                # elif winning_block and block.hash != winning_block.hash and winning_block.validated:

                
            elif int(prev_block.index) < int(block.index) - 1:
                if get_missing_blocks:
                    create_job(retrieve_missing_blocks, job_timeout=150, worker='main', blockchain=block.Blockchain_obj, target_node=block.CreatorNode_obj.id, starting_point=prev_block.index + 1)
            elif int(prev_block.index) > int(block.index):



                # problem if blocks are not valid, should check previous blocks?
                create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=block.Blockchain_obj, starting_index=block.index, send_to=block.CreatorNode_obj.id)
            elif int(prev_block.index) + 1 == int(block.index):
                if get_missing_blocks:
                    create_job(retrieve_missing_blocks, job_timeout=150, worker='main', blockchain=block.Blockchain_obj, target_node=block.CreatorNode_obj.id, starting_point=prev_block.index)

        if not carry_on:
            block.is_not_valid(note='did_not_pass_discrepenacies2')
            prntDebug('p0 did_not_pass_discrepenacies')
            return False, True, []
    if prev_block and prev_block.object_type != 'Blockchain' and prev_block.index != block.index - 1:
        block.is_not_valid(note='wrong_index')
        prntDebug('p1 wrong_index')
        return False, True, []
    if handle_discrepancies:
        competing_index = Block.objects.filter(Blockchain_obj=block.Blockchain_obj, index=block.index, validated=True)
        if competing_index:
            winning_block, validations = resolve_block_differences(block, competing_blocks=competing_index)
            if winning_block:
                if winning_block.validated:
                    return True, True, validations
                else:
                    return False, False, validations
        
    if block.Transaction_obj:
        if not block.Transaction_obj.SenderWallet_obj:
            carry_on = False
            if 'BlockReward' in block.Transaction_obj.regarding:
                if block.Transaction_obj.regarding['BlockReward'] == block.id:
                    carry_on = True
                elif block.Transaction_obj.regarding['BlockReward'] == block.Transaction_obj.SenderBlock_obj.id and block.Transaction_obj.ReceiverBlock_obj.id == block.id:
                    carry_on = True
            if not carry_on:
                block.is_not_valid(note='transaction_err1')
                prntDebug('p2 transaction_err1')
                return False, True, []
            
    prntDebug('next stage')
    required_validators, node_block_data = block.get_required_validator_count(return_node_data=True)
    required_consensus = block.get_required_consensus()
    block_time_delay = block.get_required_delay()
    self_node = get_self_node()
    prntDebug('required_validators',required_validators)
    prntDebug('required_consensus',required_consensus)
    prntDebug('block_time_delay',block_time_delay)

    creator_nodes, validator_list, broadcast_list = block.get_assigned_nodes(node_block_data=node_block_data)
        
    prntDebug(f"-creator_nodes:{creator_nodes}, -broadcast_list:{broadcast_list}, -validator_list:{validator_list}")
    prntDebug('validator_list[:required_validators]',validator_list[:required_validators],'self_node.id',self_node.id)
    prnt(f'now_utc:{now_utc()} ---(b_ct + datetime.timedelta(minutes=(block_time_delay*(3/4))+1)): {(b_ct + datetime.timedelta(minutes=(block_time_delay*(3/4))+1))}')
    if block.CreatorNode_obj.id not in creator_nodes:
        block.is_not_valid(note='wrong_creator')
        prntDebug(f'p3 wrong_creator, block.CreatorNode_obj.id:{block.CreatorNode_obj.id}, creator_nodes:{creator_nodes}')
        return False, True, []
    if self_node.id in validator_list[:required_validators]:
        prnt(f'self assigned as validator, {(b_ct + datetime.timedelta(minutes=(block_time_delay*(3/4))+1))}')
        validator = Validator.objects.filter(validatorType='Block', blockchainType=block.blockchainType, data__has_key=block.id, CreatorNode_obj=self_node, created__lt=b_ct + datetime.timedelta(minutes=(block_time_delay*(3/4)))).first()
        if not validator and now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay/2)+1)):
            is_valid, validator, is_new_validation = validate_block(block, creator_nodes=creator_nodes)
            if is_new_validation:
                validator_list = validator_list + [block.CreatorNode_obj.id]
                block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=[convert_to_dict(validator)], validators_only=True, target_node_id=None)
        else:
            prnt('validation window passed')
    prnt('-proceed to check consensus')
    validations = list(Validator.objects.filter(validatorType='Block', blockchainId=block.blockchainId, data__has_key=block.id, CreatorNode_obj__id__in=validator_list[:required_validators], created__lt=b_ct + datetime.timedelta(minutes=(block_time_delay/2))))
    is_valid_vals = [v for v in validations if v.is_valid]
    prnt('is_valid_vals',len(is_valid_vals))
    total = len(validations)
    if len(is_valid_vals):
        percent = len(is_valid_vals) / total * 100
    else:
        percent = 0
    prnt('percent1',percent, 'total',total)
    if total < required_validators:
        # if isinstance(block.created, datetime.datetime):
        #     b_dt = block.created
        # else:
        #     b_dt = dt_to_string(block.created)
        if now_utc() >= (b_ct + datetime.timedelta(minutes=9)) and now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay))):
            # rebraodcast blcok to all missing validators
            prnt(f're broadcasting block {block.id}, total vals:{total}, required_validators:{required_validators}')
            broadcast_block_to = [n for n in validator_list[:required_validators] if n not in [v.CreatorNode_obj.id for v in validations]]
            block.broadcast(broadcast_list=broadcast_list, validator_list=broadcast_block_to, validations=validations, validators_only=True, target_node_id=None)

        prnt('b_ct + datetime.timedelta(minutes=(block_time_delay/2))',b_ct + datetime.timedelta(minutes=(block_time_delay/2)))
        prnt('(b_ct + datetime.timedelta(minutes=9))',(b_ct + datetime.timedelta(minutes=9)))
        if (b_ct + datetime.timedelta(minutes=(block_time_delay/2))) < now_utc() and (b_ct + datetime.timedelta(minutes=9)) < now_utc():
            broadcast_if_unknown = True
            prnt(f'time elapsed for more verifications, total:{total}, required_validators:{required_validators}')
            if now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay))):
                # request validators from validator_list if not present
                request_from_node = [n for n in validator_list[:required_validators] if n not in [v.CreatorNode_obj.id for v in validations]]
                for n in request_from_node:
                    received_validationIds = request_items(requested_items=[block.id], nodes=[n], request_validators=True, return_updated_ids=True)
                    prntDebug('received_validations2344',received_validationIds)
                    if received_validationIds:
                        received_validations = Validator.objects.filter(id__in=received_validationIds)
                        is_valid_vals += [v for v in received_validations if v.is_valid and v not in is_valid_vals and v.created < b_ct + datetime.timedelta(minutes=(block_time_delay/2))]
                        validations += [v for v in received_validations if v not in validations and v.created < b_ct + datetime.timedelta(minutes=(block_time_delay/2))]
            total = len(validations)
            if total >= required_validators:
                if is_valid_vals:
                    percent = len(is_valid_vals) / total * 100
                else:
                    percent = 0

            else:
                prnt('else23456')
                is_new_validation = False
                new_validator_list = validator_list[required_validators:(required_validators*2)].copy()
                new_validations = Validator.objects.filter(validatorType='Block', blockchainId=block.blockchainId, data__has_key=block.id, CreatorNode_obj__in=new_validator_list, created__gte=b_ct + datetime.timedelta(minutes=(block_time_delay/2))).exclude(CreatorNode_obj__id__in=[v.CreatorNode_obj.id for v in validations]).order_by('created')
                prnt('new_validations',new_validations)
                if self_node.id in new_validator_list and not any(v for v in new_validations if v.CreatorNode_obj.id == self_node.id) and now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay))):
                    is_valid, validator, is_new_validation = validate_block(block, creator_nodes=creator_nodes)
                if is_new_validation:
                    validator_list = validator_list + creator_nodes + new_validator_list
                    block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=[convert_to_dict(validator)], validators_only=True, target_node_id=None)
                else:
                    prnt('else23456-a')
                    is_valid_vals += [v for v in new_validations if v.is_valid and v not in is_valid_vals and verify_obj_to_data(v, v)]
                    validations += [v for v in new_validations if v not in validations and verify_obj_to_data(v, v)]
                    prnt('validations',validations)
                    total = len(validations)
                    if is_valid_vals:
                        percent = len(is_valid_vals) / total * 100
                    else:
                        percent = 0

    prnt(f'total:{total}, required_validators:{required_validators}, (b_ct + datetime.timedelta(minutes=(block_time_delay))):{(b_ct + datetime.timedelta(minutes=(block_time_delay)-1.5))}')
    if total < required_validators and now_utc() > (b_ct + datetime.timedelta(minutes=(block_time_delay)-1.5)):
        block.is_not_valid(note='timed_out')
        prntDebug('p6 timed_out')
        return False, True, []
    prntDebug('check consensus stage3')
    save_block = False
    for v in validations:
        if v.id not in block.validators:
            block.validators[v.id] = get_commit_data(v)
            save_block = True
    if save_block:
        block.save()
        # if block.Reward_obj and v.id not in block.Reward_obj.ReceiverBlock_obj.validators:
        #     block.Reward_obj.ReceiverBlock_obj.validators[v.id] = get_commit_data(v)
        #     block.Reward_obj.ReceiverBlock_obj.save()
    prnt(f'percent2:{percent} total:{total} required_validators:{required_validators} required_consensus:{required_consensus}')
    if total >= required_validators and percent >= required_consensus:
        prntDebug('stage3 opt1')
        save_block = False
        for validator in validations:
            if validator.id not in block.validators:
                block.validators[validator.id] = get_commit_data(validator)
                save_block = True
        if save_block:
            block.save()
        if do_mark_valid and not block.validated:
            block.mark_valid(downstream_worker=downstream_worker)
            # queue = django_rq.get_queue('low')
            # queue.enqueue(broadcast_block, block, lst=broadcast_list, job_timeout=200)
        if not block.validated and now_utc() < (b_ct + datetime.timedelta(hours=24)):
            block.broadcast(broadcast_list=broadcast_list, validations=validations, validators_only=False, target_node_id=None)
        return True, True, validations
    elif total >= required_validators and percent < 50:
        prntDebug('stage3 opt2')
        if block.validated != False:
            prnt("now_utc() < (b_ct + datetime.timedelta(hours=24))", now_utc(), (b_ct + datetime.timedelta(hours=24)))
            block.is_not_valid(note='failed_by_validators')
            if now_utc() < (b_ct + datetime.timedelta(hours=24)):
                if any(v for v in validations if v.created > b_ct + datetime.timedelta(minutes=(block_time_delay/2))):
                    prnt('xa1')
                    block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=validations, validators_only=False, target_node_id=None)
                else:
                    prnt('xa2')
                    validator_list += creator_nodes
                    block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=[v for v in validations if v.CreatorNode_obj == self_node], validators_only=True, target_node_id=None)
        return False, True, validations
    elif total >= required_validators and percent < required_consensus and percent > 50:
        broadcast_if_unknown = True
        prntDebug('stage3 opt3')
        prnt('requires extra validators')
        new_validator_list = validator_list[required_validators:(required_validators*2)].copy()
        if self_node.id in new_validator_list and not any(v for v in validations if v.CreatorNode_obj.id == self_node.id) and now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay))):
            is_valid, validator, is_new_validation = validate_block(block, creator_nodes=creator_nodes)
            if is_new_validation:
                validator_list = validator_list + creator_nodes + new_validator_list
                block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=[convert_to_dict(validator)], validators_only=True, target_node_id=None)
                return is_valid, False, validations
        
        new_validations = Validator.objects.filter(validatorType='Block', blockchainId=block.blockchainId, data__has_key=block.id, CreatorNode_obj__in=new_validator_list, created__gte=b_dt + datetime.timedelta(minutes=(block_time_delay/2))).exclude(CreatorNode_obj__id__in=[v.CreatorNode_obj.id for v in validations]).order_by('created')
        is_valid_vals += [v for v in new_validations if v.is_valid and v not in is_valid_vals and verify_obj_to_data(v, v)]
        validations += [v for v in new_validations if v not in validations and verify_obj_to_data(v, v)]
        total = len(validations)
        if is_valid_vals:
            percent = len(is_valid_vals) / total * 100
        else:
            percent = 0

        if percent >= required_consensus:
            prntDebug('stage3 opt3-a')
            save_block = False
            for validator in validations:
                if validator.id not in block.validators:
                    block.validators[validator.id] = get_commit_data(validator)
                    save_block = True
            if save_block:
                block.save()
            if do_mark_valid and not block.validated:
                block.mark_valid(downstream_worker=downstream_worker)
            if not block.validated and now_utc() < (b_ct + datetime.timedelta(hours=24)):
                block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=validations, validators_only=False, target_node_id=None)
                # queue = django_rq.get_queue('low')
                # queue.enqueue(broadcast_block, block, lst=broadcast_list, job_timeout=200)
            return True, True, validations
        elif percent < 50:
            prntDebug('stage3 opt3-b')
            if block.validated != False:
                block.is_not_valid(note='failed_by_validators_s2')
                if now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay))):
                # if now_utc() < (b_ct + datetime.timedelta(hours=24)):
                    if any(v for v in validations if v.created > b_ct + datetime.timedelta(minutes=(block_time_delay/2))):
                        block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=validations, validators_only=False, target_node_id=None)
                    else:
                        validator_list += creator_nodes
                        block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=[v for v in validations if v.CreatorNode_obj == self_node], validators_only=True, target_node_id=None)
            return False, True, validations
    if broadcast_if_unknown and now_utc() < (b_ct + datetime.timedelta(minutes=(block_time_delay))):
        # broadcast to all nodes
        block.broadcast(broadcast_list=broadcast_list, validations=validations, validators_only=False, target_node_id=None)
    elif is_new_validation:
        validator_list += creator_nodes
        block.broadcast(broadcast_list=broadcast_list, validator_list=validator_list, validations=[v for v in validations if v.CreatorNode_obj == self_node], validators_only=True, target_node_id=None)
    return is_valid, False, validations

def validate_block(block, creator_nodes=None, node_block_data={}, create_validator=True):
    from utils.models import to_datetime, get_self_node, prntDebugn, get_model_prefix, sigData_to_hash, sort_dict,now_utc,prnt,dt_to_string
    prnt('---validate_block now_utc:', now_utc(),block)
    from blockchain.models import Validator, logEvent, NodeChain_genesisId, toBroadcast
    self_node = get_self_node()
    validator = Validator.objects.filter(validatorType='Block', blockchainId=block.blockchainId, data__has_key=block.id, CreatorNode_obj=self_node.id).first()
    if validator:
        is_new_validation = False
        fail_reason = 0
    else:

        logEvent(f'Validate Block: {block.Blockchain_obj.genesisName}', log_type='Tasks')
        prnt('else')
        transaction_type = None
        fail_reason = 1
        hard_pass = False
        proceed_to_valid = False
        validated = False
        prev_block = block.get_previous_block(is_validated=True)
        if prev_block and prev_block.object_type != 'Blockchain' and prev_block.validated and prev_block.index != block.index - 1:
            hard_pass = True
            fail_reason = 75
        elif not block.data and not block.Transaction_obj: # not sure if all transaction blocks will contain data
            hard_pass = True
            fail_reason = 751
        elif not prev_block or prev_block.object_type == 'Blockchain' or prev_block.validated:
            pass
        elif prev_block.validated == False:
            hard_pass = True
            fail_reason = 76
        elif prev_block.validated == None:
            return None, None, None # wait for result of prev_block
        # if not hard_pass and block.data:
        #     if any(key.startswith(get_model_prefix('UserTransaction')) for key in block.data):
        #         hard_pass = True # userTransactions must be block.Transaction_obj only
        #         fail_reason = 12
        if not hard_pass and block.Transaction_obj:
            if to_datetime(block.Transaction_obj.created) != to_datetime(block.created):
                prntDebugn(f'---------***********: block:{convert_to_dict(block)} --------Transaction_obj:{convert_to_dict(block.Transaction_obj)}')
                logEvent(f'---------***********: block:{convert_to_dict(block)} --------Transaction_obj:{convert_to_dict(block.Transaction_obj)}')
                hard_pass = True
                fail_reason = 72
            elif not block.Transaction_obj.SenderWallet_obj:
                if 'BlockReward' in block.Transaction_obj.regarding and block.Transaction_obj.regarding['BlockReward'] == block.id and block.Transaction_obj.token_value == calculate_reward(block.created):
                    transaction_type = 'reward'
                else:
                    fail_reason = 73
                    hard_pass = True
            elif block.Transaction_obj.ReceiverWallet_obj == block.Blockchain_obj:
                transaction_type = 'receiver'
            elif block.Transaction_obj.SenderWallet_obj == block.Blockchain_obj:
                transaction_type = 'sender'
            else:
                fail_reason = 74
                hard_pass = True
        if not hard_pass and block.get_previous_hash() == block.previous_hash:
            fail_reason = 2
            target_hash = sigData_to_hash(block)
            received_hash = block.hash
            prnt('received_hash',received_hash,'target_hash',target_hash)
            if received_hash == target_hash:
                fail_reason = 3
                if not creator_nodes:
                    if block.Transaction_obj:
                        if transaction_type == 'sender':
                            creator_nodes, validator_nodes = get_node_assignment(block.Transaction_obj, sender_transaction=True, node_block_data=node_block_data)
                        elif transaction_type == 'receiver':
                            creator_nodes, validator_nodes = get_node_assignment(block.Transaction_obj, node_block_data=node_block_data)
                        else:
                            creator_nodes, validator_nodes = get_node_assignment(block, node_block_data=node_block_data)
                    else:
                        creator_nodes, validator_nodes = get_node_assignment(block, node_block_data=node_block_data)
                prnt('creator_nodes',creator_nodes,'block.CreatorNode_obj',block.CreatorNode_obj)
                if block.CreatorNode_obj.id in creator_nodes:
                    fail_reason = 4
                    if verify_obj_to_data(block, block):
                        fail_reason = 701
                        if not block.Transaction_obj:
                            proceed_to_valid = True
                        elif verify_obj_to_data(block.Transaction_obj, block.Transaction_obj):
                            fail_reason = 702
                            proceed_to_valid = True
                prnt('proceed to attempt validation:',proceed_to_valid)
                if not proceed_to_valid:
                    if block.Transaction_obj:
                        prnt('rewardData',convert_to_dict(block.Transaction_obj))
                
                if proceed_to_valid:
                    fail_reason = 100
                    if block.blockchainType == NodeChain_genesisId:
                        fail_reason = 101
                        
                        if block.Blockchain_obj.verify_new_node_block_data(block):
                            fail_reason = 102
                            prnt('valid = true22 Nodes')
                            validated = True
                            fail_reason = 'None'
                    # elif block.blockchainType == 'Wallet':
                    #     if verify_obj_to_data(block.Transaction_obj, block.Transaction_obj): # already done above
                    #         # confirm tokens are available to spend?
                    #         validated = True
                    else:

                        found_idens, missing_idens = check_block_contents(block, retrieve_missing=True, log_missing=False, downstream_worker=False, return_missing=True)
                        if not found_idens:
                            fail_reason = 103
                            prnt('not valid 1a')
                            validated = False

                        elif any(i for i in block.data if i not in found_idens):

                        # if mismatch:
                            fail_reason = 113
                            prnt('not valid 1b')
                            validated = False
                            fail_reason = []
                            for iden, commit in block.data.items():
                                if iden != 'meta' and iden not in found_idens:
                                    validated = False
                                    fail_reason.append(iden)
                            if fail_reason:
                                logEvent(str({'block.id':block.id,'fail_reason':fail_reason,'found_idens':len(found_idens),'missing_idens':len(missing_idens)}))
                            prnt(f'invalid contents = {str(fail_reason)[:250]}')
                        else:
                            validated = True
        
        prnt('setp3')
        validator = Validator(CreatorNode_obj=self_node, jobId=block.id, blockchainType=block.blockchainType, blockchainId=block.Blockchain_obj.id, validatorType='Block', func='tasker')
        validator.data[block.id] = get_commit_data(block)
        if block.Transaction_obj:
            validator.data[block.Transaction_obj.id] = get_commit_data(block.Transaction_obj)
            # validator.data[reward.ReceiverBlock_obj.id] = get_commit_data(reward.ReceiverBlock_obj)
        if not validated:
            validator.data['fail_reason'] = fail_reason
        validator.data = sort_dict(validator.data)
        is_new_validation = True
        validator.is_valid = validated
        if create_validator:
            validator.save()
            validator = sign_obj(validator)
            prnt('created validator',validator, dt_to_string(now_utc()))
            block.validators[validator.id] = get_commit_data(validator)
            block.save()
            toBroadcast(validator.id, extra={'re':block.id})
        # if reward:
        #     reward.ReceiverBlock_obj.validators[validator.id] = get_commit_data(validator)
        #     reward.ReceiverBlock_obj.save()
        prnt('done validating block')
        logEvent(f'ValidationBlockResult: {validated}, achieved position:{fail_reason}, - {block.Blockchain_obj.genesisName}', log_type='Tasks')
    prnt('validator:',validator,"is_new_validation",is_new_validation,'validator.is_valid',validator.is_valid,'fail_reason',str(fail_reason)[:300])
    return validator.is_valid, validator, is_new_validation

def calculate_reward(dt):
    from utils.models import prnt, now_utc, string_to_dt
    prnt('calculate_reward',dt)
    from blockchain.models import Sonet, golden_ratio
    import math
    # 100 coins reduced by the golden ration every 4th anniversary of sonet creation
    if not dt:
        dt = now_utc()
    if not isinstance(dt, datetime.datetime):
        dt = string_to_dt(dt)
    # from accounts.models import Sonet
    sonet = Sonet.objects.first()
    years_since = (dt.year - sonet.created.year)
    num = math.floor(years_since / 4)
    reward = 100
    reward = reward / (golden_ratio ** num)
    prnt('reward',reward)
    return str(reward)

def validate_obj(obj=None, pointer=None, validator=None, save_obj=True, update_pointer=True, verify_validator=True, add_to_queue=True, node_block_data={}):
    from utils.models import prnt, now_utc
    prnt('---validate _obj now_utc:', now_utc(),obj,pointer)
    # pointer = None
    target = None
    proceed = False
    validator_node_id = None
    err = 0
    from posts.models import update_post, Post, Update
    if pointer and not obj and save_obj:
        obj = Post.objects.filter(pointerId=pointer.id).first()
    if obj and not obj.validated and obj.id != '0' or pointer and update_pointer and not pointer.Validator_obj:
        from utils.models import prntDebug, sigData_to_hash, convert_to_datetime, find_or_create_chain_from_object, has_field, has_method, get_model
        from blockchain.models import Validator, max_validation_window, logEvent
        # from accounts.models import verify_obj_to_data
        # logError('validate post', code='5784', func='posts_validate', extra={'self_dict':convert_to_dict(self)})
        if obj and obj.object_type == 'Post':
            if not pointer:
                pointer, obj = obj.get_pointer(return_self=True, do_save=False)
            # if pointer and validator:
            #     proceed = True
            # elif pointer.Validator_obj:
            #     validator = pointer.Validator_obj
            #     proceed = True
            if pointer:
                target = pointer
        elif obj:
            target = obj
        elif pointer:
            target = pointer
        if target:
            prnt('target',target.id)
        if target and not proceed:
            # else:
            if validator:
                if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                    validator_node_id = validator.CreatorNode_obj.id
                    proceed = True
                else:
                    creator_nodes, validator_nodes = get_node_assignment(dt=convert_to_datetime(target.created), chainId=target.blockchainId, node_block_data=node_block_data)
                    # validator_node_id = get_scraping_order(dt=convert_to_datetime(target.created), chainId=, func_name=target.func, validator_only=True, node_block_data=node_block_data)
                    if target.validatorNodeId in validator_nodes:
                        validator_node_id = target.validatorNodeId
                        proceed = True
            else:
                validators = Validator.objects.filter(data__contains={target.id: sigData_to_hash(target)}, is_valid=True).order_by('-created')
                for validator in validators:
                    if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                        validator_node_id = validator.CreatorNode_obj.id
                        proceed = True
                        break
                    else:
                        creator_nodes, validator_nodes = get_node_assignment(dt=convert_to_datetime(target.created), chainId=target.blockchainId, func_name=target.func, node_block_data=node_block_data)
                        # validator_node_id = get_scraping_order(dt=convert_to_datetime(target.created), chainId=target.blockchainId, func_name=target.func, validator_only=True, node_block_data=node_block_data)
                        if target.validatorNodeId in validator_nodes:
                            validator_node_id = target.validatorNodeId
                            proceed = True
                            break   
        err = 1
        prnt('validator in use:',validator)
        if proceed and target and validator and validator.is_valid and validator.signature and target.signature:
            if has_field(target, 'created'):
                if convert_to_datetime(validator.created) > convert_to_datetime(target.created) + datetime.timedelta(days=max_validation_window) or convert_to_datetime(validator.created) < convert_to_datetime(target.created):
                    err = '1a'
                    prnt('validator created outside of window')
                    if obj and has_field(obj, 'notes'):
                        obj.notes[(now_utc())] = f'validator created outside of window:{err}.'
                        obj.save()
                    prnt('failed to validaed post',err,target)
                    return False
            err = 2
            if not verify_validator or verify_obj_to_data(validator, validator):
                err = '2a'
                if target.id in validator.data:
                    err = 3
                    hash = validator.data[target.id]
                    if hash == sigData_to_hash(target):
                        # err = 4
                        # if not isinstance(validator.created_dt, datetime.datetime):
                        #     v_created = dt_to_string(validator.created_dt)
                        # else:
                        #     v_created = validator.created_dt
                        # if v_created >= pointer.added and v_created <= (pointer.added + datetime.timedelta(hours=12)):
                        err = 5
                        if not validator_node_id:
                            if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                                validator_node_id = validator.CreatorNode_obj.id
                                err = '444a' + validator_node_id
                            else:
                                creator_nodes, validator_nodes = get_node_assignment(dt=convert_to_datetime(target.created), chainId=target.blockchainId, func_name=target.func, node_block_data=node_block_data)
                                # validator_node_id = get_scraping_order(dt=convert_to_datetime(target.created), chainId=target.blockchainId, func_name=target.func, validator_only=True, node_block_data=node_block_data)
                                err = '444b' + str(validator_nodes)
                        if target.validatorNodeId in validator_nodes:
                            err = 6
                            if obj and obj.object_type == 'Post':
                                err = 7
                                if save_obj:
                                    obj, updated_fields = update_post(obj=target, p=obj, save_p=False)
                                    obj.validated = True
                                    obj.save()
                                    # super(Update, self).save()
                                if update_pointer and target.Validator_obj != validator and not target.Block_obj:
                                    target.Validator_obj = validator
                                    super(get_model(target.object_type), target).save()
                                    if has_field(target, 'blockchainId'):
                                        blockchain, item, secondChain = find_or_create_chain_from_object(target)
                                        blockchain.add_item_to_queue(target)
                            elif obj and obj.object_type == 'Update':
                                err = 8
                                if save_obj:
                                    if obj.Validator_obj != validator and not obj.Block_obj:
                                        obj.Validator_obj = validator
                                    obj.validated = True
                                    super(Update, obj).save()
                                    blockchain, item, secondChain = find_or_create_chain_from_object(obj.Pointer_obj)
                                    if blockchain:
                                        blockchain.add_item_to_queue(obj)
                                    else:
                                        # from blockchain.models import logEvent, convert_to_dict
                                        logEvent('no blockchain', code='9763', func='update.validate()', extra={'self.id':obj.id,'dict':str(convert_to_dict(obj.Pointer_obj))[:500]})
                                synced = obj.sync_with_post()
                            elif obj and obj.object_type == 'Notification':
                                err = 9
                                prnt('validated notification')
                                from accounts.models import UserNotification, User, Notification
                                if save_obj:
                                    if obj.Validator_obj != validator and not obj.Block_obj:
                                        obj.Validator_obj = validator
                                    obj.validated = True
                                    super(Notification, obj).save()
                                try:
                                    err = 10
                                    notify = next(iter(obj.targetUsers))
                                    prnt('notify',notify)
                                    target_users = obj.targetUsers[notify]
                                    prnt('target_users',target_users)
                                    if notify == 'all':
                                        for u in User.objects.all():
                                            prnt(u)
                                            n = UserNotification.objects.filter(User_obj=u, Notification_obj=obj).first()
                                            if not n:
                                                n = UserNotification(User_obj=u, Notification_obj=obj)
                                                n.save()
                                    elif notify == 'all_in_country':
                                        pass
                                        # for u in User.objects.filter(Country_obj__id=target):
                                        #     n = UserNotification.objects.filter(User_obj=u, Notification_obj=self).first()
                                        #     if not n:
                                        #         n = UserNotification(User_obj=u, Notification_obj=self)
                                        #         n.save()
                                    elif notify == 'all_in_provState':
                                        pass
                                    elif notify == 'follow_bill':
                                        pass
                                    elif notify == 'follow_person':
                                        pass
                                    if add_to_queue:
                                        blockchain, item, secondChain = find_or_create_chain_from_object(obj.Region_obj)
                                        # blockchain = Blockchain.objects.filter(id=self.blockchainId).first()
                                        blockchain.add_item_to_queue(obj)
                                        # blockchain.add_item_to_queue(validator)
                                    # return True
                                except Exception as e:
                                    prnt('fail40636',str(e))
                                    err = e
                            else:
                                err = 11
                                if update_pointer and target.Validator_obj != validator and not target.Block_obj:
                                    err = 12
                                    target.Validator_obj = validator
                                    super(get_model(target.object_type), target).save()
                                    if has_field(target, 'blockchainId'):
                                        blockchain, item, secondChain = find_or_create_chain_from_object(target)
                                        blockchain.add_item_to_queue(target)

                            if has_method(target, 'upon_validation'):
                                target.upon_validation()
                            prntDebug(f'post validated - id:{obj.id if obj else "0"}, pointerId:{target.id}, err:{err}, save_self:{save_obj}, node_block_data:{node_block_data}')
                            # logEvent('post validated', code='64356', func='posts_validate', extra={'id':self.id,'pointerId':self.pointerId,'save_self':save_self,'node_block_data':node_block_data})
                            return True
                        else:
                            prnt('valId incorrect',target)
                        # else:
                        #     print('creatd_dt not appropriate. v_created:',v_created,'pointer.added:',pointer.added)
                    else:
                        prnt('hash no match',target)
                        if obj and has_field(obj, 'notes'):
                            obj.notes[dt_to_string(now_utc())] = f'hash no match err:{err}. {target}'
                else:
                    prnt('point.id not in validator')
                    if obj and has_field(obj, 'notes'):
                        obj.notes[dt_to_string(now_utc())] = f'point.id not in validator err:{err}. {validator.id}'
            else:
                prnt('val not verified')
                if obj and has_field(obj, 'notes'):
                    obj.notes[dt_to_string(now_utc())] = f'val not verified err:{err}. {validator.id}'
        else:
            prnt('validator not valid')
            if obj and has_field(obj, 'notes'):
                obj.notes[dt_to_string(now_utc())] = f'no val or val not valid err:{err}.'
        prnt('failed to validaed post',err,target)
        if obj:
            obj.save()

    #     if pointer and validator:
    #         logEvent('failed to validate post', code='8642', func='posts_validate', extra={'err':str(err),'p.id':pointer.id,'val_id':validator.id,'pointer':pointer,'pointer_dict':convert_to_dict(pointer),'self_dict':convert_to_dict(self)})
    #     else:
    #         logEvent('failed to validate post', code='86426', func='posts_validate', extra={'err':str(err),'pointer':pointer,'validator':validator,'self_dict':convert_to_dict(self)})
    # else:
    #     logEvent('post already validated', code='743', func='posts_validate', extra={'self_dict':convert_to_dict(self)})
    if obj and obj.validated or pointer and pointer.Validator_obj:
        prnt('already validated')
        return True
    prnt('rturn False', err)
    return False

def get_broadcast_list(seed, dt=None, region_id=None, relevant_nodes={}, seed_nodes=[], important_nodes=[], excluded_nodes=[], peer_count=None, loop=False):
    # some inputs not utilized here
    from django.db import models
    from utils.models import is_id, get_dynamic_model, round_time, now_utc, dt_to_string,prnt
    prnt('get_broadcast_list',seed)

    def get_deterministic_broadcast_order(func_name, dt, node_ids, seed_nodes, important_nodes, excluded_nodes=[]):
        import random
        if isinstance(dt, datetime.datetime):
            dt_str = dt_to_string(dt)
        elif isinstance(dt, str):
            dt_str = dt
        else:
            raise ValueError("dt must be a datetime or ISO string")

        seed_input = f"{func_name}_{dt_str}"
        seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
        seed_int = int(seed_hash, 16)
        rng = random.Random(seed_int)

        excluded = set(seed_nodes + important_nodes + excluded_nodes)
        remaining_nodes = [nid for nid in node_ids if nid not in excluded]

        rng.shuffle(important_nodes)
        rng.shuffle(remaining_nodes)

        return seed_nodes + important_nodes + remaining_nodes

    def get_broadcast_map(func_name, dt, nodes, seed_nodes, important_nodes, peer_count=2, excluded_nodes=[], loop=False):
        # prnt('get_broadcast_map',nodes,'important_nodes',important_nodes)
        node_ids = list(nodes.keys())
        ordered_ids = get_deterministic_broadcast_order(func_name, dt, node_ids, seed_nodes, important_nodes, excluded_nodes=excluded_nodes)
        broadcast_map = {}
        total = len(ordered_ids)
        recipients_set = set()
        # prnt('ordered_ids',ordered_ids)


        if loop:
            for i, node_id in enumerate(ordered_ids):
                recipients = []
                count = 0
                j = 1
                # for j in range(1, peer_count+1): 
                while count < peer_count and j < total:
                    if loop:
                        recipient = ordered_ids[(i + j) % total]
                    else:
                        if i + j < total:
                            recipient = ordered_ids[i + j]
                        else:
                            break
                    if nodes[recipient] not in excluded_nodes:
                        recipients.append(nodes[recipient])
                        count += 1
                    j += 1
                broadcast_map[node_id] = recipients
        else:
            for i, node_id in enumerate(ordered_ids):
                # prnt('i',i,'node_id',node_id)
                recipients = []
                count = 0
                j = i + 1
                while count < peer_count and j < total:
                    # prnt('j',j)
                    candidate = ordered_ids[j]
                    if candidate not in recipients_set and candidate not in excluded_nodes:
                        recipients.append(nodes[candidate])
                        recipients_set.add(candidate)
                        # prnt('recipients',recipients)
                        count += 1
                    j += 1

                broadcast_map[node_id] = recipients

        # prntDebug('broadcast_map',broadcast_map)
        # prnt('ordered_ids',ordered_ids)
        # prnt('recipients_set',recipients_set)
        # prnt('loop',loop)
        # If loop is enabled, connect remaining unassigned nodes (if any)
        # if loop:
        #     early_candidates = [
        #         nid for nid in ordered_ids
        #         if nid not in seed_nodes and nid not in recipients_set
        #     ]
        #     prnt('early_candidates',early_candidates)
        #     for sender_id in ordered_ids:
        #         if len(broadcast_map[sender_id]) < peer_count:
        #             while early_candidates:
        #                 candidate = early_candidates.pop(0)
        #                 if candidate not in recipients_set and candidate != sender_id:
        #                     broadcast_map[sender_id].append(nodes[candidate])
        #                     recipients_set.add(candidate)
        #                     break

        return broadcast_map

    if is_id(seed):
        seed = get_dynamic_model(seed, id=seed)
        relevant_nodes, peer_count = get_relevant_nodes_from_block(obj=seed, include_peers=True)
    elif isinstance(seed, models.Model):
        if seed and seed.object_type == 'Block' or seed and seed.object_type == 'UserTransaction':

            if seed.object_type == 'Block' and not seed.Transaction_obj or seed.object_type == 'Block' and 'BlockReward' in seed.Transaction_obj.regarding and seed.Transaction_obj.regarding['BlockReward'] == seed.id:
                relevant_nodes, peer_count = get_relevant_nodes_from_block(dt=seed.DateTime, obj=seed, genesisId=seed.Blockchain_obj.genesisId, include_peers=True)
                seed_nodes, important_nodes = get_node_assignment(chainId=region_id, obj=seed, dt=dt)
            else:
                if seed.object_type == 'Block' and seed.Transaction_obj:
                    seed = seed.Transaction_obj
                dt = round_time(dt=seed.created, dir='down', amount='evenhour')
                relevant_nodes, peer_count = get_relevant_nodes_from_block(dt=dt, obj=seed, include_peers=True)
                seed_nodes, important_nodes = get_node_assignment(chainId=region_id, obj=seed, dt=dt)

        elif seed.object_type == 'DataPacket':
            prnt('ssed is datapacket', seed.Node_obj)
            dt = round_time(dt=seed.created, dir='down', amount='10mins')
            excluded_nodes.append(seed.Node_obj.id)
        elif seed.object_type == 'Validator':
            dt = round_time(dt=seed.created, dir='down', amount='10mins')
        elif seed.object_type == 'Node':
            dt = round_time(dt=seed.last_updated, dir='down', amount='10mins')
        elif seed.object_type == 'User':
            dt = round_time(dt=seed.last_updated, dir='down', amount='10mins')
        relevant_nodes, peer_count = get_relevant_nodes_from_block(obj=seed, include_peers=True)
        seed_text = seed.id
    elif isinstance(seed, str) and region_id and dt:
        seed_nodes, important_nodes = get_node_assignment(chainId=region_id, func=seed, dt=dt)
        relevant_nodes, peer_count = get_relevant_nodes_from_block(obj=seed, include_peers=True)
        seed_text = seed
    else:
        raise ValueError("get_broadcast_list received wrong input")

    if not dt:
        # from posts.models import 
        dt = now_utc()
    broadcast_map = {}
    for nid, recipients in get_broadcast_map(seed_text, dt, relevant_nodes, seed_nodes, important_nodes, peer_count=peer_count, excluded_nodes=excluded_nodes, loop=loop).items():
        print(f"{nid} → {recipients}")
        broadcast_map[nid] = recipients
    return broadcast_map


# you were inputting the dt into the seed for the browser sorting pattern. needs doing on server and browser
# userTransactions shuold use browser_shuffle? unless is block reward? users should be able to verify any transaction, even if block reward?

def get_relevant_nodes_from_block(dt=None, genesisId=None, chains=None, blockchain=None, ai_capable=False, firebase_capable=False, exclude_list=[], obj=None, node_block=None, strings_only=True, sublist='scripts', include_peers=False, node_ids_only=False):
    from utils.models import has_field, now_utc, get_timeData, testing, round_time, prnt
    prnt('--get nodes from node block list - strings_only:',strings_only,'genesisId',genesisId,'blockchain',blockchain,'chains',chains,'obj',obj,'dt',dt,'exclude_list',exclude_list)
    if not dt and obj:
        # from .models import 
        dt = get_timeData(obj, sort='updated')
    elif not dt:
        # from posts.models import 
        dt = now_utc()
    if obj and has_field(obj, 'object_type') and obj.object_type == 'Block' and obj.blockchainType == 'Nodes':
        # NodeChain block assignments use the node block in question (datetime is 10mins ahead of creation time, allowing for propagation of block before it begins use)
        # eveything else uses block assigned to its datetime
        # node blocks must be done by currently active nodes, ie. if a node deactivates, it can't be assigned to validate the next node block
        node_block = obj
        # prnt('received node_block')
    else:
        # from .models import 
        if not node_block and not testing():
            from blockchain.models import NodeChain_genesisId, Block, Blockchain, Sonet
            dt = round_time(dt=dt, dir='down', amount='10mins')
            node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=dt, validated=True).order_by('-index', 'created').first()
            if not node_block:
                chain = Blockchain.objects.filter(genesisId=NodeChain_genesisId).first()
                if not chain:
                    # from accounts.models import Sonet
                    sonet = Sonet.objects.first()
                    if sonet:
                        chain = Blockchain(genesisId=NodeChain_genesisId, genesisType='Nodes', genesisName='Nodes', created=sonet.created)
                        chain.save()

    if node_block:
        prnt('relevant_nodes_block_id',node_block)
        from blockchain.models import mandatoryChains, Node, Blockchain
        from utils.models import get_pointer_type, get_chain_type, is_id
        if genesisId and genesisId in mandatoryChains or get_pointer_type(genesisId) in mandatoryChains or get_chain_type(genesisId) in mandatoryChains:
            # prnt('op1')
            # prnt("node_block.data['All']",node_block.data['All'])
            node_ids = [n for n in node_block.data['All'] if n not in exclude_list]
            # prnt('node_idsA',node_ids)
            # prnt('node_idsB sort',sorted(node_ids))
            if node_ids_only:
                return sorted(node_ids)
            if strings_only and 'addresses' in node_block.notes:
                # prnt('path1')
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                # prnt('path12')
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                # prnt('path13')
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
            # prnt('relevant_nodesA',relevant_nodes)

        elif genesisId or blockchain:
            # prnt('is gen or bchain')
            if not blockchain and get_pointer_type(genesisId) == 'Blockchain':
                # prnt('11')
                blockchain = Blockchain.objects.filter(id=genesisId).first()
            elif is_id(blockchain):
                # prnt('1122')
                blockchain = Blockchain.objects.filter(id=blockchain).first()
            from django.db import models
            if isinstance(blockchain, str) and blockchain == 'All' or isinstance(blockchain, models.Model) and blockchain.genesisType in mandatoryChains:
                # prnt('1133')
                genesisId = 'All'
            elif isinstance(blockchain, models.Model):
                # prnt('1144')
                genesisId = blockchain.genesisId
            # prnt('genesisId',genesisId,'sublist',sublist)
            if genesisId in node_block.data and sublist in node_block.data[genesisId]: # scripts or servers
                node_ids = [n for n in node_block.data[genesisId][sublist] if n not in exclude_list]
            else:
                node_ids = [n for n in node_block.data['All'] if n not in exclude_list]
            if node_ids_only:
                return sorted(node_ids)
            # else:
            #     node_ids = []
            
            if strings_only and 'addresses' in node_block.notes:
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
        elif chains:
            # prnt('is chains')
            node_ids = []
            for c in chains:
                if c in mandatoryChains:
                    c = 'All'
                if c in node_block.data:
                    # prnt('---c',c, node_block.data[c])
                    if c == 'All':
                        for node_iden in node_block.data[c]:
                            if node_iden not in node_ids and node_iden not in exclude_list:
                                node_ids.append(node_iden)
                    else:
                        for i in node_block.data[c]:  # specify which duties; {'scripts':['nodSo..'],'servers':['nodSo..']}
                            if node_block.data[c][i]:
                                # prnt('-----i',node_block.data[c][i])
                                for node_iden in node_block.data[c][i]:
                                    prnt('-----node_iden',node_iden)
                                    if node_iden not in node_ids and node_iden not in exclude_list:
                                        node_ids.append(node_iden)
            # prnt('node_ids',node_ids)
            if node_ids_only:
                return sorted(node_ids)
            if strings_only and 'addresses' in node_block.notes:
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
            # prnt('done is chains')
        else:
            # prnt('else')
            node_ids = [n for n in node_block.data['All'] if n not in exclude_list]
            if node_ids_only:
                return sorted(node_ids)
            if strings_only and 'addresses' in node_block.notes:
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}

        prnt('1 node_ids',node_ids, 'relevant_nodes',relevant_nodes)
        if include_peers:
            if node_block.number_of_peers > len(node_ids):
                peers_count = len(node_ids)
            else:
                peers_count = node_block.number_of_peers
            prnt('peers_count',peers_count)
            return dict(sorted(relevant_nodes.items())), peers_count
        else:
            return dict(sorted(relevant_nodes.items()))
    else:
        from django.db import models
        from blockchain.models import Node, number_of_peers, NodeChain_genesisId
        if obj and isinstance(obj, models.Model) and obj.object_type == 'Block' and obj.Blockchain_obj.genesisId == NodeChain_genesisId:
            all_nodes = Node.objects.all().order_by('created')[:1]
            node_ids = [n.id for n in all_nodes if n.id not in exclude_list]
            if node_ids_only:
                return sorted(node_ids)
            if strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
            if include_peers:
                if number_of_peers > len(node_ids):
                    peers_count = len(node_ids)
                else:
                    peers_count = number_of_peers
                return dict(sorted(relevant_nodes.items())), peers_count
            else:
                return dict(sorted(relevant_nodes.items()))
    if node_ids_only:
        return []
    if include_peers:
        return {}, 0
    return {}


def get_node_assignment(obj=None, dt=None, func=None, chainId=None, sender_transaction=False, full_validator_list=False, strings_only=False, node_block_data={}):
    import random
    from blockchain.models import get_required_validator_count
    from utils.models import round_time, dt_to_string, prnt
    prnt('\n------get_node_assignment obj:', obj, 'func',func, 'strings:', strings_only,'chainId',chainId,'node_block_data',node_block_data,'sender_transaction',sender_transaction)

    # use receieved object.id to get starting position
    # sort nodes by pattern based on datetime
    # for each node create a list of peers to broadcast to
    # each node should only receive broadcast once
    # each node should be able to discern entire broadcast list repeatably
    # not all nodes will need to broadcast
    # also assign roles for tasks

    # this has become messy, sorry. its important that it return the exact same results across time - here and in javascript
    # may return different combinations of the following depending on datetime and task:
    # creators, validators, scrapers, broadcast_list


    def shuffle_nodes(text_input, dt, node_ids):
        if isinstance(dt, datetime.datetime):
            dt_str = dt_to_string(dt)
        elif isinstance(dt, str):
            dt_str = dt
        else:
            raise ValueError("dt must be a datetime or ISO string", dt)
        # prnt('node_ids133',node_ids)
        
        # node_ids = ['node1','node2','node3','node4','node5','node6']
        # seed_input = f"myseed"
        seed_input = f"{text_input}_{dt_str}"
        seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
        seed_int = int(seed_hash, 16)
        rng = random.Random(seed_int)
        # node_ids.sort()
        # shuffled_nodes = node_ids.copy()
        shuffled_nodes = sorted(node_ids.copy())
        rng.shuffle(shuffled_nodes)
        # prnt('shuffled_nodes',shuffled_nodes)
        return shuffled_nodes

    def browser_shuffle(text_input, dt, node_ids): # works in javascript so can be run by user but is much slower
        if isinstance(dt, datetime.datetime):
            dt_str = dt_to_string(dt)
        elif isinstance(dt, str):
            dt_str = dt
        else:
            raise ValueError("dt must be a datetime or ISO string", dt)
        # seed_input = f"{text_input}_{dt_str}"
        return sorted(node_ids, key=lambda item: hashlib.sha256((f"{text_input}_{dt_str}_{item}").encode('utf-8')).hexdigest())

    is_transaction = False
    chain_list = None
    required_validators = 0
    required_scrapers = 0
    broadcast_list = {}
    validator_list = []
    scraper_list = []
    available_creators = 1
    creator_nodes = []
    node_ids = None
    number_of_peers = None
    relevant_nodes = None
    valid_node_ids_received = False
    v = 0
    if node_block_data:
        try:

            import copy
            node_dict = copy.deepcopy(node_block_data)

            # number_of_peers = node_dict['number_of_peers']
            # relevant_nodes = node_dict['relevant_nodes']
            node_ids = node_dict['node_ids']
            valid_node_ids_received = True
        except Exception as e:
            prnt('fail4782674',str(e))
            try:
                node_ids = [n for n in node_block_data]
                valid_node_ids_received = True
            except Exception as e:
                prnt('fail454923784',str(e))

    if obj and obj.object_type == 'Block' or obj and obj.object_type == 'UserTransaction':
        # if obj.object_type == 'Block' and obj.Transaction_obj:
        #     prnt('obj.Transaction_obj',obj.Transaction_obj)
        #     prnt('obj.Transaction_obj.regarding',obj.Transaction_obj.regarding)
        #     if 'BlockReward' in obj.Transaction_obj.regarding:
        #         prnt('yes1')
        #     if obj.Transaction_obj.regarding['BlockReward'] == obj.id:
        #         prnt('yes2')

        if obj.object_type == 'Block' and not obj.Transaction_obj or obj.object_type == 'Block' and 'BlockReward' in obj.Transaction_obj.regarding and obj.Transaction_obj.regarding['BlockReward'] == obj.id:
            
            if not valid_node_ids_received:
                node_ids = get_relevant_nodes_from_block(dt=obj.DateTime, obj=obj, genesisId=obj.Blockchain_obj.genesisId, strings_only=strings_only, node_ids_only=True)
            # prnt('node_ids11',node_ids)

            # if sender_transaction: # retrieves ReceiverBlock assignment
            #     shuffle_seed = obj.Transaction_obj.ReceiverWallet_obj.id
            # else:
            #     if obj.Transaction_obj:
            #         shuffle_seed = obj.Transaction_obj.id
            #     else:
            shuffle_seed = obj.id
            if not dt:
                dt = obj.DateTime
            shuffled_nodes = shuffle_nodes(shuffle_seed, dt, node_ids)
            if full_validator_list:
                required_validators = len(node_ids)
            else:
                required_validators = get_required_validator_count(obj=obj, node_ids=node_ids)
            
            creator_nodes = shuffled_nodes[:available_creators]
            validator_nodes = list(reversed(shuffled_nodes[-required_validators:]))
            return creator_nodes, validator_nodes


        else:
            # prnt('else12334')
            if obj.object_type == 'Block' and obj.Transaction_obj:
                obj = obj.Transaction_obj
            if obj.object_type == 'UserTransaction' and 'BlockReward' in obj.regarding and obj.regarding['BlockReward']:
                if not valid_node_ids_received:
                    node_ids = get_relevant_nodes_from_block(dt=obj.SenderBlock_obj.DateTime, obj=obj.SenderBlock_obj, genesisId=obj.SenderBlock_obj.Blockchain_obj.genesisId, strings_only=strings_only, node_ids_only=True)
                # prnt('node_ids112',node_ids)
                if sender_transaction: # retrieves ReceiverBlock assignment list
                    shuffle_seed = obj.id
                else:
                    shuffle_seed = obj.SenderBlock_obj.id # senderBlock_obj is block getting reward
                if not dt:
                    dt = obj.SenderBlock_obj.DateTime
                shuffled_nodes = shuffle_nodes(shuffle_seed, dt, node_ids)
                if full_validator_list:
                    required_validators = len(node_ids)
                else:
                    required_validators = get_required_validator_count(obj=obj.SenderBlock_obj, node_ids=node_ids)
            else: # user to user transaction
                dt = round_time(dt=obj.created, dir='down', amount='evenhour')
                if sender_transaction: # reverse receiver/sender
                    shuffle_seed = obj.SenderWallet_obj.id
                else:
                    shuffle_seed = obj.ReceiverWallet_obj.id
                if not valid_node_ids_received:
                    node_ids = get_relevant_nodes_from_block(dt=dt, obj=obj, strings_only=strings_only, node_ids_only=True)
                shuffled_nodes = browser_shuffle(shuffle_seed, dt, node_ids)

                available_creators, required_validators = get_required_validator_count(obj=obj, node_ids=node_ids, include_initializers=True)

            creator_nodes = shuffled_nodes[:available_creators]
            validator_nodes = list(reversed(shuffled_nodes[-required_validators:]))
            return creator_nodes, validator_nodes


    elif obj and obj.object_type == 'DataPacket':
        chain_list = [obj.chainId]

        if not dt:
            dt = round_time(dt=obj.created, dir='down', amount='10mins')
        # if not valid_node_ids_received:
        #     node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, blockchain=obj.chainId, strings_only=strings_only)
        if obj.Node_obj:
            if strings_only:
                creator_nodes.append(obj.Node_obj.id)
            else:
                creator_nodes.append(obj.Node_obj)
        # date_int = date_to_int(dt)
        # starting_position = hash_to_int(obj.id, len(node_ids))


        if not valid_node_ids_received:
            node_ids = get_relevant_nodes_from_block(dt=dt, blockchain=obj.chainId, strings_only=strings_only, node_ids_only=True)
        shuffled_nodes = shuffle_nodes(obj.id, dt, node_ids)
        return shuffled_nodes, []

        # creator_nodes = shuffled_nodes[:available_creators]
        # validator_nodes = shuffled_nodes[-required_validators]
        # return creator_nodes, validator_nodes
        
    elif obj and obj.object_type == 'Validator':
        chain = Blockchain.objects.filter(id=obj.blockchainId).first()
        chain_list = [chain.genesisId]
        dt = round_time(dt=obj.created, dir='down', amount='10mins')
        # if not valid_node_ids_received:
        #     node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, genesisId=chain.genesisId, strings_only=strings_only)
        # date_int = date_to_int(dt)
        # starting_position = hash_to_int(obj.id, len(node_ids))

        shuffled_nodes = shuffle_nodes(obj.id, dt, node_ids)
        return shuffled_nodes, []

        
    elif obj and obj.object_type == 'Node':
        chain_list = obj.supportedChains_array
        if not dt:
            dt = round_time(dt=obj.last_updated, dir='down', amount='10mins')
        # if not valid_node_ids_received:
        #     node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, strings_only=strings_only)
        # date_int = date_to_int(dt)
        # starting_position = hash_to_int(obj.id, len(node_ids))


        if not valid_node_ids_received:
            node_ids = get_relevant_nodes_from_block(dt=dt, strings_only=strings_only, node_ids_only=True)
        shuffled_nodes = shuffle_nodes(obj.id, dt, node_ids)
        return shuffled_nodes, []
    
    elif obj and obj.object_type == 'User':
        # return a simple ordered list of nodes for user to connect to
        # user will connect to node in order of validator list.
        # build list according to chainId, servers not scripts
        # user transactions are validated by first x number of nodes on list at time of creation. transaction must have a region_obj if user is using region list, which currently is
        # transaction blocks are created for sender and receiver. sender block is created/validated by list of nodes assigned to sender of transaction, receiver will have his own list \
        # how to get list of nodes to validate receiver block? someone needs to have receiver region so nodes know where to send the validated transaction. \
        # other option is transactions are worldwide, no region assignment needed. use a seperate (world) list for transactions than normal list that connects user to server
        # correct validator nodes are needed because nodes are assigned to a user for a period of time rather than all nodes doing all transactions at all times
        # would be nice to be region specific so smaller regions are able to use lesser hardware and fewer nodes? could create issues for those regions if nodes not responding, transactions would fail
        if not dt:
            dt = round_time(dt=obj.last_updated, dir='down', amount='10mins')
        # if not valid_node_ids_received: # careful, this is different from other assignments
        #     node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, blockchain=chainId, strings_only=strings_only, sublist='servers')
        # date_int = date_to_int(dt)
        # starting_position = hash_to_int(obj.id, len(node_ids))
        available_creators = 0
        if full_validator_list:
            required_validators = len(node_ids)
        else:
            required_validators = get_required_validator_count(obj=obj, node_ids=node_ids)
        

        if not valid_node_ids_received:
            node_ids = get_relevant_nodes_from_block(dt=dt, blockchain=chainId, strings_only=strings_only, node_ids_only=True, sublist='servers')
        # shuffled_nodes = shuffle_nodes(obj.id, dt)
        shuffled_nodes = browser_shuffle(obj.id, dt, node_ids)
        return shuffled_nodes, []
        
    elif obj:
        dt = round_time(dt=obj.created, dir='down', amount='10mins')
        # if not valid_node_ids_received:
        #     node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, obj=obj, strings_only=strings_only)
        # date_int = date_to_int(dt)
        # starting_position = hash_to_int(obj.id, len(node_ids))
        required_validators = get_required_validator_count(obj=obj, node_ids=node_ids)


        if not valid_node_ids_received:
            node_ids = get_relevant_nodes_from_block(dt=dt, obj=obj, strings_only=strings_only, node_ids_only=True)
        shuffled_nodes = shuffle_nodes(obj.id, dt, node_ids)
        return shuffled_nodes, []
    
    elif func:
        # prnt('is func',func,'chainId',chainId)
        from django.db import models
        if isinstance(chainId, models.Model):
            chainId = chainId.id
        from posts.models import get_model_prefix
        if not chainId.startswith(get_model_prefix('Blockchain')):
            from blockchain.models import Blockchain
            chainId = Blockchain.objects.filter(genesisId=chainId).first().id
        if not valid_node_ids_received:
            node_ids = get_relevant_nodes_from_block(dt=dt, blockchain=chainId, strings_only=strings_only, node_ids_only=True)
        shuffled_nodes = shuffle_nodes(func, dt, node_ids)

        required_scrapers, required_validators = get_required_validator_count(dt=dt, func=func, node_ids=node_ids, include_initializers=True)
        return shuffled_nodes[:required_scrapers], list(reversed(shuffled_nodes[-required_validators:])) # validator_node should maybe be [validator_node] for consistency

    # prnt('--starting_position11',starting_position,'dt::',dt,'date_int:',date_int,'len(node_ids)',len(node_ids),'available_creators',available_creators)
    # prntDebug('relevant_nodes',relevant_nodes)


    # import hashlib
    # import datetime
    # import random

    # def get_deterministic_node_order(func_name, dt, node_ids):
    #     if isinstance(dt, datetime.datetime):
    #         dt_str = dt_to_string(dt)
    #     elif isinstance(dt, str):
    #         dt_str = dt
    #     else:
    #         raise ValueError("dt must be a datetime or ISO string")

    #     seed_input = f"{func_name}_{dt_str}"
    #     seed_hash = hashlib.sha256(seed_input.encode('utf-8')).hexdigest()
    #     seed_int = int(seed_hash, 16)

    #     rng = random.Random(seed_int)
    #     shuffled_nodes = node_ids.copy()
    #     rng.shuffle(shuffled_nodes)

    #     return shuffled_nodes



    # if len(node_ids) == 0:
    #     prnt('node_lengths:==000')
    #     return [], {}, []
    # elif len(node_ids) == 1:
    #     prnt('node_lengths:==1')
    #     if creator_only:
    #         if strings_only:
    #             return [node_ids[0]]
    #         else:
    #             return [relevant_nodes[node_ids[0]]]
    #     elif scrapers_only:
    #         if func:
    #             return [node_ids[0]], node_ids[0] # [scrapers], validator
    #         else:
    #             return [], None
    #     else:
    #         if strings_only:
    #             return [node_ids[0]], {node_ids[0] : [relevant_nodes[node_ids[0]]]}, [node_ids[0]] 
    #         else:
    #             return [node_ids[0]], {node_ids[0] : [relevant_nodes[node_ids[0]]]}, [node_ids[0]] # [creators], {broadcast_list}, [validators.id]

    # def get_peer_nodes(broadcaster, position, node_ids, checked_node_list):
    #     # prntDebug('get_peer_nodes',broadcaster, position, node_ids, checked_node_list)
    #     nonlocal broadcast_list
    #     nonlocal relevant_nodes
    #     # prntDebug('get_peer_nodes 22',broadcast_list, relevant_nodes)
    #     if broadcaster not in broadcast_list:
    #         if broadcaster in node_ids:
    #             node_ids.remove(broadcaster)
    #         # prntDebug('get peers step 1')
    #         broadcaster_hashed_int = hash_to_int(broadcaster, len(node_ids))
    #         def run(position, node_ids):
    #             # prntDebug('run',position, node_ids)
    #             position += (broadcaster_hashed_int + date_int)
    #             if position >= len(node_ids):
    #                 position = position % len(node_ids)
    #             new_node_id = node_ids[position]
    #             # prntDebug('run step 2')
    #             node_ids.remove(new_node_id)
    #             return new_node_id, position, node_ids
    #         peers = []
    #         while len(peers) < number_of_peers and len(node_ids) > 0:
    #             new_node_id, position, node_ids = run(position, node_ids)
    #             if new_node_id != broadcaster:
    #                 # prntDebug('follow run')
    #                 peers.append(relevant_nodes[new_node_id])
    #                 checked_node_list.append(new_node_id)
    #         # prntDebug('get peers stpe 2')
    #         broadcast_list[broadcaster] = peers
    #         if broadcaster not in checked_node_list:
    #             checked_node_list.append(broadcaster)
    #     # prntDebug('end get peer nodes',broadcast_list, checked_node_list, node_ids)
    #     return broadcast_list, checked_node_list, node_ids
    
    # def process(broadcaster, position, node_ids, checked_node_list, broadcast_list, v):
    #     # prntDebug('process',broadcaster, position, node_ids, checked_node_list, broadcast_list, v)
    #     nonlocal creator_nodes
    #     nonlocal validator_list
    #     nonlocal scraper_list
        
    #     broadcast_list, checked_node_list, node_ids = get_peer_nodes(broadcaster, position, node_ids, checked_node_list)
    #     # prnt('1234')
    #     if len(validator_list) < required_validators and broadcaster not in creator_nodes and broadcaster not in validator_list:
    #         validator_list.append(broadcaster)
    #     # prnt('56789',scraper_list)
    #     if func and len(scraper_list) < required_scrapers and broadcaster != validator_node and broadcaster not in scraper_list:
    #         # prnt('02342',broadcaster)
    #         scraper_list.append(broadcaster)
    #     return broadcast_list, checked_node_list, node_ids, v

    # # prntDebug('assign step2')
    # starting_node_list_len = len(node_ids)
    # starting_position += date_int
    # starting_position = int(starting_position)
    # def reduce_pos(pos):
    #     pos = pos % len(node_ids)
    #     return pos
    
    # if is_transaction:
    #     x = reduce_pos(creator_position)
    # else:
    #     x = reduce_pos(starting_position)
    # prnt('x1',x)
    # if available_creators:
    #     if not creator_nodes:
    #         prntDebug('get creator_nodes')
    #         y = x
    #         for i in range(available_creators):
    #             prntDebug('i',i)
    #             if strings_only:
    #                 if node_ids[x] not in creator_nodes:
    #                     creator_nodes.append(node_ids[x])
    #             else:
    #                 if relevant_nodes[node_ids[x]] not in creator_nodes:
    #                     creator_nodes.append(relevant_nodes[node_ids[x]])
    #             x += y
    #             prntDebug('y',y)
    #             x = reduce_pos(x)
    #             prntDebug('x',x)
    #     prntDebug('creator_nodes',creator_nodes, 'scraper_list',scraper_list)
    #     for c in creator_nodes:
    #         prntDebug('rem c',c)
    #         if strings_only:
    #             node_ids.remove(c)
    #         else:
    #             node_ids.remove(c.id)
    #     checked_node_list = creator_nodes.copy()
    #     if func and creator_nodes:
    #         validator_node = creator_nodes[0]
    #         checked_node_list = [validator_node]
    #     if creator_only:
    #         # prntDebug('returning creator only 123e4',creator_nodes)
    #         return creator_nodes
    #     if not strings_only:
    #         checked_node_list = [n.id for n in checked_node_list]
    #     x = 0
    #     run = True
    #     target_node = checked_node_list[x]
    # else: # for creating user list, likely not needed by node, is needed by user, user creates with javascript
        
    #     run = True
    #     if strings_only:
    #         target_node = node_ids[x]
    #     else:
    #         target_node = relevant_nodes[node_ids[x]]
    # prntDebug('assign step3')
    # # run for nodes registered to node_block at time of dt
    # while x < len(node_ids) and run:
    #     try:
    #         prntDebug(f'while x:{x}, v:{v}, target_node:{target_node}, starting_position:{starting_position}, node_ids:{node_ids}, checked_node_list:{checked_node_list}, broadcast_list:{broadcast_list}, ')
    #         broadcast_list, checked_node_list, node_ids, v = process(target_node, starting_position, node_ids, checked_node_list, broadcast_list, v)
    #         if func and scrapers_only:
    #             if len(scraper_list) >= required_scrapers or len(node_ids) == 0:
    #                 run = False
    #         if target_node not in broadcast_list:
    #             run = False
    #         x += 1
    #         target_node = checked_node_list[x]
    #     except Exception as e:
    #         prntDebug(f'fail459373 {e}')
    #         run = False
    # prntDebug('required_validators',required_validators,'validator_list',validator_list)

    # if len(validator_list) < required_validators and starting_node_list_len >= required_validators:
    #     for n in relevant_nodes:
    #         prnt('n',n)
    #         if n not in validator_list:
    #             if strings_only and n not in creator_nodes:
    #                 validator_list.append(n)
    #             elif not strings_only:
    #                 for c in creator_nodes:
    #                     if n != c.id:
    #                         validator_list.append(n)
    #             if len(validator_list) >= required_validators:
    #                 break

    # if func and scrapers_only:
    #     if len(scraper_list) < required_scrapers:
    #         for n in relevant_nodes:
    #             if n not in scraper_list:
    #                 scraper_list.append(n)
    #                 if len(scraper_list) >= required_scrapers:
    #                     break
    #     if strings_only:
    #         scraper_list = [n if isinstance(n, str) else n.id for n in scraper_list]
    #     prntDebug('func and scrfapers only', scraper_list, validator_node)
    #     return scraper_list, validator_node # validator_node should maybe be [validator_node] for consistency
    
    # # add creators to end of broadcast_list
    # added_creators = []
    # for node_id in reversed(checked_node_list):
    #     for creator in creator_nodes:
    #         if creator not in added_creators:
    #             if strings_only:
    #                 if node_id != creator:
    #                     if node_id not in broadcast_list:
    #                         broadcast_list[node_id] = []
    #                     broadcast_list[node_id].append(relevant_nodes[creator])
    #                     added_creators.append(creator)
    #                     break
    #             else:
    #                 if isinstance(creator, models.Model):
    #                     if node_id != creator.id:
    #                         if node_id not in broadcast_list:
    #                             broadcast_list[node_id] = []
    #                         broadcast_list[node_id].append(creator.return_address())
    #                         added_creators.append(creator)
    #                         break
    #                 elif is_id(creator):
    #                     if node_id != creator:
    #                         if node_id not in broadcast_list:
    #                             broadcast_list[node_id] = []
    #                         broadcast_list[node_id].append(relevant_nodes[creator].return_address())
    #                         added_creators.append(creator)
    #                         break
    #     if len(added_creators) == len(creator_nodes):
    #         break

    # # prnt('assign step 4')
    # # prnt('relevant_nodes',relevant_nodes)
    # if not valid_node_ids_received and get_stragglers:
    #     prntDebug('assign step4')
    #     if strings_only:
    #         exclude_list = checked_node_list
    #     else:
    #         exclude_list = [n.id for n in checked_node_list]
    #     latest_node_ids, number_of_peers, latest_relevant_nodes = get_relevant_nodes_from_block(chains=chain_list, obj=obj, exclude_list=exclude_list, strings_only=strings_only)
    #     prnt('latest_node_ids',latest_node_ids)
    #     prnt('latest_relevant_nodes',latest_relevant_nodes)
    #     # look closely at the following, it may need work

    #     # run for remaining nodes not in initial snapshot
    #     node_list = latest_node_ids
    #     for node in checked_node_list:
    #         if node in latest_node_ids:
    #             latest_node_ids.remove(node)
    #     cross_reference_list = [node for node in checked_node_list if node in latest_node_ids]
    #     prntDebug('assign step5')
    #     run = True
    #     n = 0
    #     while len(cross_reference_list) < len(latest_node_ids) and run and n < len(node_ids):
    #         try:
    #             n += 1
    #             target_node = checked_node_list[x]
    #             prntDebug(f'n:{n}, cross_reference_list:{cross_reference_list}, target_node:{target_node}, starting_position:{starting_position}, node_ids:{node_ids}, checked_node_list:{checked_node_list}, broadcast_list:{broadcast_list}, ')
    #             broadcast_list, checked_node_list, node_ids = get_peer_nodes(target_node, starting_position, node_ids, checked_node_list)
    #             # broadcast_list, checked_node_list, node_list, v = process(target_node, starting_position, node_list, checked_node_list, v)
    #             # break if target_node has no broadcast_peers
    #             if target_node in broadcast_list:
    #                 peers = broadcast_list[target_node]
    #                 for peer in peers:
    #                     if peer not in cross_reference_list:
    #                         cross_reference_list.append(peer)
    #             x += 1
    #         except Exception as e:
    #             prntDebug(f'fail485 {e}')
    #             run = False

        
    # prntDebug(f'----finish_get_node_assignment\n --creator_nodes:{creator_nodes},\n --broadcast_list:{broadcast_list},\n --validator_list:{validator_list}\n')

    # return creator_nodes, broadcast_list, validator_list
    

def check_block_contents(block, retrieve_missing=True, log_missing=True, downstream_worker=True, return_missing=False, input_data=[]):
    from utils.models import chunk_dict, get_timeData, has_field, get_dynamic_model, sigData_to_hash, exists_in_worker, get_data, now_utc, prnt, string_to_dt
    prnt('check_block_contents now_utc:', now_utc( ),block.id, block.index, input_data)
    from blockchain.models import Validator, logEvent, request_items, logMissing, logError, max_commit_window
    # from posts.models import 
    obj_idens = []
    requested_idens = []
    requested_validators = []
    # if input_data:
    #     prnt('input_data',input_data)
    #     data = input_data
    # else:
    #     prnt('no input_data')
    #     data = self.data
    if 'content_dt' in block.notes:
        content_dt = string_to_dt(block.notes['content_dt'])
    elif 'created_dt' in block.notes:
        content_dt = string_to_dt(block.notes['created_dt'])
    else:
        content_dt = block.created
    if not isinstance(block.DateTime, datetime.datetime):
        self_dt = string_to_dt(block.DateTime)
    else:
        self_dt = block.DateTime
    total_found = 0
    for chunk in chunk_dict(block.data, 300):
        storedModels, not_found, not_valid, delLogs = get_data(chunk, return_model=True, include_related=False, include_deletions=True)
        total_found += len(not_found)
        total_found += len(not_valid)
        total_found += len(storedModels)
        for x in storedModels:
            # prnt('x',x)
            if not has_field(x, 'Validator_obj') or x.Validator_obj and x.Validator_obj.is_valid and x.id in x.Validator_obj.data and x.Validator_obj.data[x.id] == sigData_to_hash(x):
                # prnt('a')
                if x.id in block.data:
                    # prnt('ab')
                    i_dt = get_timeData(x)
                    if i_dt and i_dt <= content_dt + datetime.timedelta(hours=24) and i_dt >= self_dt - datetime.timedelta(days=max_commit_window) and i_dt < self_dt:
                        # prnt('ac')
                        if check_commit_data(x, block.data[x.id]): 
                            obj_idens.append(x.id)
                        else:
                            requested_idens.append(x.id)
            elif has_field(x, 'Validator_obj') and not x.Validator_obj:
                if validate_obj(obj=None, pointer=x, node_block_data={}):
                    pass
                else:
                    requested_idens.append(x.id)
                if x.id in block.data:
                    # prnt('az')
                    i_dt = get_timeData(x)
                    if i_dt and i_dt <= content_dt + datetime.timedelta(hours=24) and i_dt >= self_dt - datetime.timedelta(days=max_commit_window) and i_dt < self_dt:
                        # prnt('ax')
                        if check_commit_data(x, block.data[x.id]):
                            obj_idens.append(x.id)
            else:
                requested_validators.append(x.id)

        storedModels.clear()
        if not_valid:
            requested_idens = requested_idens + [i.id for i in not_valid]
        if not_found:
            requested_idens = requested_idens + not_found
        not_found.clear()
        not_valid.clear()
    prnt('total_found',total_found,'requested_idens',requested_idens,'obj_idens',len(obj_idens),'requested_validators',requested_validators)

    if requested_validators:
        vals = Validator.objects.filter(data__has_any_keys=requested_validators, is_valid=True).order_by('-created')
        if vals:
            for i in requested_validators:
                creator_nodes, validator_nodes = get_node_assignment(dt=i.created, chainId=i.blockchainId, func_name=i.func)

                for val in vals:
                    # prnt('val',val)
                    if val.CreatorNode_obj.id in validator_nodes and i in val.data:
                        # prnt('y')
                        obj = get_dynamic_model(i, id=i)
                        # prnt('obj',obj)
                        if obj and validate_obj(obj=None, pointer=obj, validator=val, node_block_data={}):
                            if obj.id in block.data and get_timeData(x) >= self_dt - datetime.timedelta(days=max_commit_window) and get_timeData(x) < self_dt and check_commit_data(obj, block.data[obj.id]):
                                obj_idens.append(obj.id)
                                requested_validators.remove(obj.id)
    prnt('next stage')
    if retrieve_missing:
        fetch_idens = [i for i in block.data if i not in obj_idens]
        if fetch_idens:
            request_nodes = [block.CreatorNode_obj.id]
            for iden, data in block.validators.items():
                # prnt(iden, data)
                request_nodes.append(json.loads(data)['CreatorNode_obj'])
            prnt('is valid path 11 request_nodes',request_nodes)
            logEvent(f'requesting:{fetch_idens}', func='is_valid_operations')
            if downstream_worker:
                import django_rq
                queue = django_rq.get_queue('low')
                if not exists_in_worker('request_items', fetch_idens, queue):
                    # attempts += 1
                    queue.enqueue(request_items, fetch_idens, nodes=request_nodes, job_timeout=600, result_ttl=3600)
                    return None
            else:
                prnt('is valid path 444')
                fetch_again = []
                retreived_objs = request_items(fetch_idens, return_updated_objs=True, nodes=request_nodes)
                for chunk in chunk_dict(fetch_idens, 300):
                    storedModels, not_found, not_valid, delLogs = get_data(chunk, return_model=True, include_related=False, include_deletions=True)
                    for x in storedModels:
                        if not has_field(x, 'Validator_obj') or x.Validator_obj and x.Validator_obj.is_valid and x.id in x.Validator_obj.data and x.Validator_obj.data[x.id] == sigData_to_hash(x):
                            if x.id in block.data:
                                if check_commit_data(x, block.data[x.id]):
                                    obj_idens.append(x.id)
                        elif has_field(x, 'Validator_obj') and not x.Validator_obj:
                            if not validate_obj(obj=None, pointer=x, node_block_data={}):
                                fetch_again.append(x.id)
                            elif x.id in block.data:
                                if check_commit_data(x, block.data[x.id]):
                                    obj_idens.append(x.id)
                    # retreived_objs.clear()
                if fetch_again:
                    retreived_objs = request_items(fetch_again, return_updated_objs=True, nodes=request_nodes)
                    for chunk in chunk_dict(fetch_again, 300):
                        storedModels, not_found, not_valid, delLogs = get_data(chunk, return_model=True, include_related=False, include_deletions=True)
                        for x in storedModels:
                            if not has_field(x, 'Validator_obj') or x.Validator_obj and x.Validator_obj.is_valid and x.id in x.Validator_obj.data and x.Validator_obj.data[x.id] == sigData_to_hash(x):
                                if x.id in block.data:
                                    if check_commit_data(x, block.data[x.id]):
                                        obj_idens.append(x.id)
                            elif has_field(x, 'Validator_obj') and not x.Validator_obj:
                                if not validate_obj(obj=None, pointer=x, node_block_data={}):
                                    pass
                                elif x.id in block.data:
                                    if check_commit_data(x, block.data[x.id]):
                                        obj_idens.append(x.id)

    
    prnt('self.data_len',len(block.data),'obj_idens_len',len(obj_idens),'self.data',str(block.data)[:500],'obj_idens',str(obj_idens)[:500])
    # if len(self.data) != len(obj_idens):
    problem_idens = []
    for key in block.data:
        if key not in obj_idens:
            problem_idens.append(key)
    if problem_idens and log_missing:
        logMissing(problem_idens, reg=block.Blockchain_obj.genesisId, context={'block':block.id})
        logError(f'missing items from valid block {block.id}', code='5832645', func='is_valid_operations', region=None, extra=problem_idens)

        # return False
    if return_missing:
        return obj_idens, problem_idens
    return obj_idens



def dt_to_string(dt_input):
    if isinstance(dt_input, str):
        dt = datetime.datetime.fromisoformat(dt_input)
    elif isinstance(dt_input, datetime.datetime):
        dt = dt_input
    else:
        raise TypeError("Input must be a datetime object or an ISO 8601 string")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    # Return JS-style ISO string (milliseconds precision, 'Z' suffix)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def sign_obj(item, operatorData=None, do_save=True, return_error=False):
    # prntDebug('sign_obj')
    try:
        from blockchain.models import logError
        from accounts.models import  User
        from .models import get_operator_obj, get_operatorData, now_utc, has_field, has_method, testing, get_model, prnt
        from django.db import models
        if has_method(item, 'get_hash_to_id') and item.id != hash_obj_id(item) or isinstance(item, models.Model) and item.id == '0':
            prnt('failSign4958', item)
            logError('item.id != hash_obj_id', code='4958', func='sign_obj', extra={'item.id':item.id, 'correct_id':hash_obj_id(item), 'hash_obj_id_data':hash_obj_id(item, return_data=True), 'dict':str(convert_to_dict(item))[:500]})
            if return_error:
                return item, 'err1'
            return item
        if has_field(item, 'latestModel'):
            item.modelVersion = item.latestModel
        if has_field(item, 'last_updated'):
            item.last_updated = now_utc()
        if not operatorData:
            operatorData = get_operatorData()
        if operatorData:
            if has_field(item, 'func') and item.func and item.func.lower() == 'super':
                if do_save and testing() and User.objects.all().count() <= 2:
                    pass
                else:
                    user = User.objects.filter(id=get_operator_obj('userId', operatorData=operatorData)).first()
                    if not user.assess_super_status():
                        if return_error:
                            return item, 'err2'
                        return item
            keyPair = get_operator_obj('keyPair', operatorData=operatorData)
            if isinstance(item, dict):
                item['publicKey'] = keyPair['pubKey']
            elif has_field(item, 'publicKey'):
                item.publicKey = keyPair['pubKey']
            sig = simpleSign(keyPair['privKey'], get_signing_data(item))
            if isinstance(item, dict):
                item['signature'] = sig
            else:
                item.signature = sig
                if do_save:
                    item.save()
            # prntn('signed:',get_signing_data(item))
        elif do_save and testing() and User.objects.all().count() <= 2:
            prnt('bypass sign')
            super(get_model(item.object_type), item).save()
    except Exception as e:
        prnt('fail472549',str(e),convert_to_dict(item))
        logError(str(e), code='7532', func='sign_obj', extra={'dict':str(convert_to_dict(item))[:500]})
        if return_error:
            return item, str(e)
    if return_error:
        return item, None
    return item



def get_commit_data(target, extra_data=None):
    from .models import get_dynamic_model, get_model, has_method, has_field, sigData_to_hash, dt_to_string, prnt, prntDebug
    prntDebug('-get_commit_data',target)
    if isinstance(target, str):
        obj_id = target
        obj = get_dynamic_model(target, id=target)
        is_model = True
    elif isinstance(target, dict):
        obj_id = target['id']
        obj_data = target
        model = get_model(obj_data['object_type'])
        obj = model()
        is_model = False
    else:
        is_model = True
        obj = target
        obj_id = obj.id
    to_commit = {}
    if has_method(obj, 'commit_data'):
        field_names = [f.name for f in obj._meta.get_fields()]
        for i in obj.commit_data():
            try:
                if i == 'hash':
                    to_commit[i] = sigData_to_hash(obj)
                else:
                    prnt(i)
                    if i in field_names:
                        prnt('p1')
                        if is_model:
                            attr = getattr(obj, i)
                        else:
                            attr = obj_data[i]
                        if isinstance(attr, datetime.datetime):
                            to_commit[i] = dt_to_string(attr)
                        elif i.endswith('_obj') and attr:
                            to_commit[i] = attr.id
                        else:
                            to_commit[i] = attr
                        prnt('p1 attr',attr)
                    elif has_method(obj, i):
                        prnt('p2')
                        if extra_data != None:
                            resp = getattr(obj, i)(extra_data)
                        else:
                            resp = getattr(obj, i)()
                        if resp:
                            for key, value in resp.items():
                                to_commit[key] = value
                        prnt('p2 resp',resp)
            except Exception as e:
                prnt('fail get_commit_data 5092', str(e), obj_id, i)
                to_commit[i] = str(e)
    if has_field(obj, 'proposed_modification') or has_field(obj, 'is_modifiable'):
        to_commit['modifiable'] = True
        if 'created' not in to_commit:
            if is_model:
                crtd = dt_to_string(obj.created)
            else:
                crtd = obj_data['created']
            to_commit['created'] = crtd
    if not to_commit:
        to_commit['hash'] = sigData_to_hash(obj)
    prnt('result:',to_commit)
    return json.dumps(to_commit)

def check_commit_data(target, data, return_err=False, return_obj=False):
    # prnt('-check_commit_data',target,data)
    from utils.models import get_dynamic_model, get_model, has_method, sigData_to_hash, prnt, has_field, string_to_dt
    from blockchain.models import logEvent
    err = 0
    try:
        data = json.loads(data)
    except:
        pass
    err = 1
    if isinstance(target, str):
        obj_id = target
        obj = get_dynamic_model(target, id=target)
        is_model = True
        xxxx = obj
    elif isinstance(target, dict):
        obj_id = target['id']
        obj_data = target
        model = get_model(obj_data['object_type'])
        obj = model()
        is_model = False
        xxxx = obj_data
    else:
        is_model = True
        obj = target
        obj_id = obj.id
        xxxx = obj
    required = None
    success = False
    if is_model:
        if not has_method(obj, 'get_hash_to_id'):
            success = True
        elif hash_obj_id(obj) == obj.id:
            success = True
    else:
        if not has_method(model, 'get_hash_to_id'):
            success = True
        elif hash_obj_id(obj_data, model=obj) == obj_id:
            success = True
    if not success:
        err = 12
        prnt(' check_commit fail1',obj_id)
        prnt(f'xxxx- {str(convert_to_dict(xxxx, withold_fields=False)[:700])}')
        if return_err:
            logEvent(f'check_commit_error1:{obj_id}', log_type='Errors')
    elif 'modifiable' in data and data['modifiable']:
        if is_model:
            target_created = obj.created
        else:
            target_created = string_to_dt(obj_data['created'])
        if string_to_dt(data['created']) == target_created:
            success = True
        else:
            err = 8
            success = False
            prnt(' check_commit fail8',obj_id)
            prnt(f'xxxx- {str(convert_to_dict(xxxx, withold_fields=False)[:700])}')
            if return_err:
                logEvent(f'check_commit_error2:{obj_id}', log_type='Errors')
    elif 'hash' in data:
        if is_model:
            sigHash = sigData_to_hash(obj)
        else:
            sigHash = sigData_to_hash(obj_data)
        if data['hash'] == sigHash:
            success = True
        else:
            err = 13
            success = False
            prnt(' check_commit fail2',obj_id)
            prnt(f'xxxx- {str(convert_to_dict(xxxx, withold_fields=False)[:700])}')
            if return_err:
                logEvent(f'check_commit_error3:{obj_id}', log_type='Errors')

    elif 'genesis' in data and data['genesis'] == obj_id:
        success = True
    if success and has_method(obj, 'commit_data'):
        for i in obj.commit_data():
            if i != 'hash':
                if has_field(obj, i):
                    if is_model:
                        attr = getattr(obj, i)
                        if isinstance(attr, datetime.datetime):
                            attr = dt_to_string(attr)
                        elif i.endswith('_obj') and attr:
                            attr = attr.id
                    else:
                        attr = obj_data[i]
                    if i not in data:
                        success = False
                        err = 5
                        prnt('check_commit fail5','f',obj_id,i,str(i),str(data))
                        prnt(f'xxxx- {str(convert_to_dict(xxxx, withold_fields=False)[:700])}')
                        if return_err:
                            logEvent(f'check_commit_error5: f,{obj_id}, {i},{str(data[i])},{str(attr)}', log_type='Errors')
                    elif str(data[i]) != str(attr):
                        success = False
                        err = 6
                        prnt('check_commit fail6','f',obj_id,i,str(data[i]),str(attr))
                        prnt(f'xxxx- {str(convert_to_dict(xxxx, withold_fields=False)[:700])}')
                        if return_err:
                            logEvent(f'check_commit_error6: f,{obj_id}, {i},{str(data[i])},{str(attr)}', log_type='Errors')
                        # break
                elif has_method(obj, i):
                    resp = getattr(obj, i)(data)
                    if not resp:
                        success = False
                        err = 7
                        prnt('check_commit fail7','f',obj_id,i,str(data[i]))
                        prnt(f'xxxx- {str(convert_to_dict(xxxx, withold_fields=False)[:700])}')
                        if return_err:
                            logEvent(f'check_commit_error7: f,{obj_id}, {i},{str(data[i])}', log_type='Errors')
    # prntDebug('check_commit_data-result:',success)
    if return_obj:
        if is_model:
            return success, obj
        else:
            return success, None
    if return_err:
        return success, err
    return success


def get_signing_data(obj, extra_data=None, include_sig=False):
    # WARNING changes here could break ALL signing and verifying abilities
    
    # prntDev('--get_signing_data')
    from django.db import models
    # from blockchain.models import convert_to_dict
    from utils.models import get_model, has_method, prnt
    data = {}
    if isinstance(obj, models.Model):
        objDict = convert_to_dict(obj)
        for key, value in objDict.items():
            if key not in skip_sign_fields:
                data[key] = objDict[key]
            elif include_sig and key == 'signature' or include_sig and key == 'publicKey':
                data[key] = objDict[key]
        sorted_dict = sort_for_sign(data)
        json_dump = json.dumps(sorted_dict, separators=(',', ':'))
        # prntDebug('json_dump1', json_dump, '\n')
        return json_dump
    else:
        try: # obj may or not be json object
            objDict = json.loads(obj)
        except:
            objDict = obj
        fields = objDict
        if 'object_type' in objDict:
            model = get_model(objDict['object_type'])
            if has_method(model, 'get_version_fields'):
                fields = model().get_version_fields(version=objDict['modelVersion'])
        for key, value in fields.items():
            if key not in skip_sign_fields:
                data[key] = objDict[key]
            elif include_sig and key == 'signature' or include_sig and key == 'publicKey':
                data[key] = objDict[key]

    sorted_dict = sort_for_sign(data)
    json_dump = json.dumps(sorted_dict, separators=(',', ':'))
    # prntDebug('json_dump2', json_dump, '\n')
    return json_dump


def sign_for_sending(sending_data, operatorData=None):
    from utils.models import now_utc, get_operator_obj, prnt
    # from blockchain.models import 
    sending_data['dt'] = dt_to_string(now_utc())
    
    hashed = hashlib.md5(str(sort_for_sign(sending_data)).encode('utf-8')).hexdigest()
    # prntDebug('send jhashed',hashed)
    keyPair = get_operator_obj('keyPair', operatorData=operatorData)
    # from accounts.models import simpleSign
    sig = simpleSign(keyPair['privKey'], hashed)
    sending_data['hashed'] = hashed
    sending_data['signature'] = sig
    sending_data['pubKey'] = keyPair['pubKey']
    return sending_data


def simpleSign(private_key, data):
    # prntDebugn('simpleSign',data)
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    # for key, value in data.items():
    #     if isinstance(value, dict) or str(value).startswith('{'):
    #         data[key] = sort_dict(value)
    # sorted_dict = dict(sorted(data.items(), key=lambda item: item[0].lower()))

    private_key_bytes = bytes.fromhex(private_key)
    private_key = ec.derive_private_key(int.from_bytes(private_key_bytes, byteorder='big'), ec.SECP256K1())
    signature = private_key.sign((data+'5uHPEF0DPaI4egus4sa6AX').encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    signature_hex = signature.hex()
    return signature_hex

# does not appear to be used
def sign_old(data, privKey=None, pubKey=None):
    # prnt('signing...',data)
    # prnt('data',data)
    if not privKey or not pubKey:
        keyPair = get_operator_obj('keyPair')
    # if not pubKey:
        pubKey = keyPair['pubKey']
    # if not privKey:
        privKey = keyPair['privKey']
    # if 'publicKey' in data:
    #     del data['publicKey']
    # prnt('1')
    if 'signature' in data:
        del data['signature']
    data['publicKey'] = pubKey
    if 'last_updated' in data:
        data['last_updated'] = dt_to_string(now_utc())
        # prnt('lastUpdated',data['last_updated'])
    # prnt('data1',data)
    for key, value in data.items():
        if isinstance(value, dict) or str(value).startswith('{'):
            data[key] = sort_dict(value)
    sorted_dict = dict(sorted(data.items(), key=lambda item: item[0].lower()))
    data = json.dumps(sorted_dict, separators=(',', ':'))
    # prnt('data getting signed:',data)
    
    private_key_bytes = bytes.fromhex(privKey)
    # prnt('private_key_bytes1',private_key_bytes)
    private_key = ec.derive_private_key(int.from_bytes(private_key_bytes, byteorder='big'), ec.SECP256K1())
    signature = private_key.sign(str(data+' ').encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    signature_hex = signature.hex()
    # prnt('sig',signature_hex)
    data = json.loads(data)
    # data['publicKey'] = pubKey
    data['signature'] = signature_hex
    # prnt('signed data:', data)
    return data

def verify_obj_to_data(obj, target_data, user=None, return_user=False, requireSuper=False, record_error=True):
    from utils.models import prnt, prntDebug
    # requires data and obj or data and user
    f = '---verify_obj_to_data'
    # prntDebug(f)
    is_valid = False
    x = 0
    try:
        from django.db.models import Model
        if not isinstance(target_data, Model):
            record_error = False
        # prnt('verify_obj_to_data target_data',target_data)
        # prnt('verify_obj_to_data user:',user)
        # verify an object against itself or against proposed syncData
        from blockchain.models import get_user, sigData_to_hash, Validator
        from utils.models import has_method, has_field, get_pointer_type
        from transactions.models import Wallet
        failed = False
        user_id = None
        node_id = None
        wallet_id = None
        x = '1'
        if isinstance(target_data, dict):
            x += '2'
            iden = target_data['id']
            pubKey = target_data['publicKey']
            sig = target_data['signature']
            target_data = sort_for_sign(target_data)
            x += 'a'
            # prntDebug('verify_obj_to_data failed', x)
            if has_method(obj, 'get_hash_to_id') and iden != hash_obj_id(target_data):
                failed = True
                x += 'b'
                # prntDebug('22-1',iden)
                # # prntDebug('22-2',hash_obj_id(obj, return_data=True))
                # prntDebug('22-3',hash_obj_id(target_data))
                # # prntDebug('22-4',hash_obj_id(target_data, return_data=True))
                # # prnt('iden2',iden2)
                # prntDebug('22-5',len(str(hash_obj_id(target_data, return_data=True))))
            if not failed and 'proposed_modification' not in target_data and 'Validator_obj' in target_data and target_data['Validator_obj']:
                x += 'c'
                val = Validator.objects.filter(id=target_data['Validator_obj']).first()
                if not val:
                    failed = True
                    x += 'd'
                if iden not in val.data:
                    failed = True
                    x += 'e'
                if val.data[iden] != sigData_to_hash(target_data):
                    failed = True
                    x += 'f'
            # prntDebug('verify_obj_to_data failed', x)
        else:
            x += '3'
            # prntDebug('verify_obj_to_data failed', x)
            iden = target_data.id
            pubKey = target_data.publicKey
            sig = target_data.signature
            if has_method(obj, 'get_hash_to_id') and iden != hash_obj_id(target_data):
                failed = True
                x += 'a'
            if not failed and not has_field(target_data, 'proposed_modification') and has_field(target_data, 'Validator_obj') and target_data.Validator_obj:
                x += 'b'
                if not target_data.id in target_data.Validator_obj.data:
                    failed = True
                    x += 'c'
                if target_data.Validator_obj.data[target_data.id] != sigData_to_hash(target_data):
                    failed = True
                    x += 'd'

        # if failed:
        # prntDebug('verify_obj_to_data failed', x)
        if obj != None and user == None:
            # prnt('n1')
            x += '4'
            if obj.object_type == 'User':
                user = obj
            else:
                if isinstance(target_data, dict):
                    x += '5'
                    if not failed or return_user:
                        x += 'a'
                        if 'object_type' in target_data and target_data['object_type'] == 'User':
                            user_id = target_data['id']
                            x += 'b'
                        else:
                            x += 'c'
                            if 'User_obj' in target_data:
                                user_id = target_data['User_obj']
                            elif 'Node_obj' in target_data:
                                node_id = target_data['Node_obj']
                            elif 'CreatorNode_obj' in target_data:
                                node_id = target_data['CreatorNode_obj']
                            elif 'Super_User_obj' in target_data:
                                user_id = target_data['Super_User_obj']
                            elif 'SenderWallet_obj' in target_data and target_data['SenderWallet_obj']:
                                wallet_id = target_data['SenderWallet_obj']
                            elif 'ReceiverWallet_obj' in target_data:
                                wallet_id = target_data['ReceiverWallet_obj']
                    
                else:
                    x += '6'
                    # prnt('0001')
                    if not failed or return_user:
                        x += 'a'
                        if not failed:
                            x += 'b'
                    # if iden == hash_obj_id(data):
                        if has_field(obj, 'User_obj'):
                            # prnt('1')
                            user = obj.User_obj
                        elif has_field(obj, 'Node_obj'):
                            user = obj.Node_obj.User_obj
                        elif has_field(obj, 'CreatorNode_obj'):
                            user = obj.CreatorNode_obj.User_obj
                        elif has_field(obj, 'Super_User_obj'):
                            user = obj.Super_User_obj
                        elif has_field(obj, 'SenderWallet_obj') and obj.SenderWallet_obj:
                            user = obj.SenderWallet_obj.User_obj
                        elif has_field(obj, 'ReceiverWallet_obj'):
                            user = obj.ReceiverWallet_obj.User_obj
                        # else:
                        if not failed:
                            x += 'c'
                if not user and not failed or not user and return_user:
                    x += '8'
                    # prntDebug(f'not user1-- user_id:{user_id}, node_id:{node_id}, wallet_id:{wallet_id}')
                    if not failed:
                        x += 'a'
                    if user_id:
                        user = get_user(user_id=user_id)
                        # prnt('user_id',user_id)
                    elif node_id:
                        user = get_user(node_id=node_id)
                    elif wallet_id:
                        user = Wallet.objects.filter(id=wallet_id).first().User_obj
                    elif get_pointer_type(iden) == 'User':
                        user = get_user(user_id=iden)
                    if not user and pubKey:
                        x += 'b' 
                        user = get_user(public_key=pubKey)
        # prntDebug('verify_obj_to_data failed', x)

        def record_result(is_valid):
            if is_valid or record_error:
                if isinstance(obj, Model):
                    if is_valid and obj.validation_error or not is_valid and record_error:
                        if sigData_to_hash(obj) == sigData_to_hash(target_data):
                            if is_valid and obj.validation_error:
                                obj.validation_error = None
                                obj.save()
                            elif record_error and not is_valid and not obj.validation_error:
                                from utils.models import get_model
                                obj.validation_error = True
                                super(get_model(obj.object_type), obj).save()
                    
        if user:
            x += '9'
            # prntDebug(f, 'user-',user)
            if not failed and not requireSuper or not failed and requireSuper and user.id == super_id():
                x += 'a'
                is_valid = user.verify_sig(target_data, sig)
            else:
                prnt('failed validate',failed,'requireSuper',requireSuper,'user.id',user.id,'super_id',super_id(),'x',x)
            # prntDebug('is_valid', is_valid, 'x',x, 'failed',failed)
            
        record_result(is_valid)
    except Exception as e:
        prnt(f'verify_obj_to_data error 3875623-{x}, iden:{iden}',str(e))
    if not is_valid:
        prntDebug(f, f'failed is_valid err:{x} hardFail:{failed}, iden:{iden}')
    if return_user and user:
        return is_valid, user
    if return_user:
        return is_valid, x
    else:
        return is_valid


def convert_to_dict(obj, broadcast=False, withold_fields=True): 
    # prntDebug('--convert_to_dict')
    if not obj:
        return None
    from django.db.models import Model
    from utils.models import get_dynamic_model, has_field, has_method, sort_dict
    # from blockchain.models import 
    if not isinstance(obj, Model):
        return obj
    do_not_share_fields = ['validated','enacted','Block_obj','validation_error','user_permissions','groups']
    if broadcast: # doesnt seem to be used
        new_dict = {'object_type' : obj.object_type}
        if has_field(obj, 'latestModel'):
            new_dict['latestModel'] = obj.latestModel
        fields = obj._meta.fields
        for f in fields:
            if f.name not in do_not_share_fields:
                value = getattr(obj, f.name)
                if value:
                    if isinstance(value, datetime.datetime):
                        new_dict[f.name] = dt_to_string(value)
                    elif isinstance(value, dict):
                        new_dict[f.name] = sort_dict(value)
                    else:
                        new_dict[f.name] = value
    else:
        d1 = {'object_type' : obj.object_type}
        if has_field(obj, 'latestModel'):
            d1['latestModel'] = obj.latestModel
        from django.forms.models import model_to_dict
        d2 = {**d1, **model_to_dict(obj)}
        if has_method(obj, 'get_version_fields'):
            fields = obj.get_version_fields()
        else:
            fields = d2
        data = {}
        for key, value in fields.items():
            if key in d2:
                data[key] = d2[key]
            else:
                data[key] = value
        from decimal import Decimal
        for key, value in data.items():
            if isinstance(value, datetime.datetime):
                data[key] = dt_to_string(value)
            elif isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, dict) or str(value).startswith('{') or '_array' in key:
                data[key] = sort_dict(value)

        if withold_fields:
            for f in do_not_share_fields:
                try:
                    del data[f]
                except Exception as e:
                    pass
    # prnt('--convert_to_dict new_dict',data)
    return data

id_len = 14
def generate_id(data=None, len=id_len):
    from utils.models import prnt
    prnt('generate_id')
    import xxhash
    import base62
    if not len:
        len = 100000
    if data:
        hash_hex = xxhash.xxh128(str(data)).hexdigest()
        hash_int = int(hash_hex, 16)
        encoded = base62.encode(hash_int)
    else:
        uuid_int = int.from_bytes(uuid.uuid4().bytes, byteorder='big')
        encoded = base62.encode(uuid_int)
    encoded = encoded.replace('So','so')
    return str(encoded)[:len]

    
def hash_obj_id(obj, verify=False, specific_data=None, return_data=False, model=None, version=None, len=id_len):
    from utils.models import has_method, has_field, get_model_prefix, get_model,sort_dict,prnt
    prnt('hash_obj_id', obj)
    if not len:
        len = id_len
    if specific_data:
        # prnt('specific_data',specific_data)
        # return get_model_prefix(obj) + 'So' + str(hashlib.md5(str(specific_data).encode('utf-8')).hexdigest())
        return get_model_prefix(obj) + 'So' + generate_id(specific_data, len=len)
    # from blockchain.models import 
    from django.db.models import Model
    data = {}
    err = 0
    try:
        if isinstance(obj, Model):
            err = 1
            if has_field(obj, 'iden_length'):
                # len = obj.iden_length
                len = obj.get_version_fields(version=version)['iden_length']
            if has_method(obj, 'get_hash_to_id'):
                err = 2
                for i in obj.get_hash_to_id(version=version):
                    if '_obj' in i:
                        attr = getattr(obj, i+'_id')
                    else:
                        attr = getattr(obj, i)
                    if isinstance(attr, datetime.datetime):
                        attr = dt_to_string(attr)
                    elif isinstance(attr, dict):
                        attr = sort_dict(attr)
                    data[i] = attr
                err = 3
                if has_field(obj,'proposed_modification'):
                    mod = getattr(obj, 'proposed_modification')
                    if mod:
                        data['proposed_modification'] = mod                    
                # prntn('dat',err, str(data)[:500])
                
                data = sort_for_sign(data)
                if return_data:
                    return data
                return get_model_prefix(obj) + 'So' + generate_id(data, len=len)
            elif verify:
                return None
            else:
                return get_model_prefix(obj) + 'So' + generate_id(len=len)
        elif isinstance(obj, str) and verify == False:
            err = 10
            if not model:
                model = get_model(obj)
            return get_model_prefix(model) + 'So' + generate_id(len=len)
        else:
            err = 100
            try:
                obj = json.loads(obj)
            except:
                pass
            if not model:
                if 'object_type' in obj:
                    model = get_model(obj['object_type'])()
                elif 'id' in obj:
                    model = get_model(obj['id'])()
            if model:
                if not version:
                    version = int(obj['modelVersion'])
                err = 101
                if has_field(model, 'iden_length'):
                    # len = model.iden_length
                    len = model.get_version_fields(version=version)['iden_length']

                if has_method(model, 'get_hash_to_id'):
                    err = 102
                    for i in model.get_hash_to_id(version=version):
                        if i.endswith('_obj'):
                            c = i + '_id'
                            if c in obj:
                                i = c
                        if i in obj:
                            # if isinstance(obj[i], dict):
                            #     data[i] = sort_dict(obj[i])
                            # else:
                            data[i] = obj[i]
                        else:
                            prnt('hash_obj_id error 389573',i)
                    if has_field(model,'proposed_modification'):
                        if 'proposed_modification' in obj:
                            mod = obj['proposed_modification']
                        else:
                            mod = None
                        if mod:
                            data['proposed_modification'] = mod
                    # prntn('dat2',err, str(data)[:500])
                    data = sort_for_sign(data)
                    if return_data:
                        return data
                    return get_model_prefix(model) + 'So' + generate_id(data, len=len)
                elif verify:
                    return None
                else:
                    return get_model_prefix(model) + 'So' + generate_id(len=len)
    except Exception as e:
        prnt(f'hash-id-fail49204-{err}',obj,str(e))
    # prnt('err',err)
    return None

def generate_mnemonic():
    from mnemonic import Mnemonic
    return Mnemonic("english").generate(strength=256)

def create_keys(user_id, user_pass):
    import hashlib
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ec import SECP256K1
    from utils.models import prnt

    salt = hashlib.sha256(f"{user_pass}:{user_id}".encode()).digest()
    prnt('salt',salt)
    # salt = user_id.encode()
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
    

def verify_data(data, public_key, signature):
    from utils.models import prnt
    prnt('verifying...',data, public_key, signature)
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    from django.db import models
    err = 0
    try:
        if isinstance(public_key, models.Model):
            public_key = public_key.publicKey
        err = 1
        pub_bytes = bytes.fromhex(public_key)
        err = 2
        sig_bytes = bytes.fromhex(signature)
        err = 3
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
        err = 4
        try:
            public_key.verify(sig_bytes, (data+'5uHPEF0DPaI4egus4sa6AX').encode('utf-8'), ec.ECDSA(hashes.SHA256()))
            prnt("Signature is valid!")
            return True
        except InvalidSignature:
            prnt("Signature is INVALID!")
    except Exception as e:
        prnt('err3',str(e), 'code:',err)
    return False

def sort_for_sign(data):
    # recursively sort data for signing
    from utils.models import deep_sort_key, process_value, stringify_if_bool, prnt
    if not data:
        return data
    if isinstance(data, dict):
        order_list = [
            'id', 'object_type', 'modelVersion', 'created', 'created_dt', 'added', 'updated_on_node', 'last_updated', 'func',
            'creatorNodeId', 'validatorNodeId', 'Validator_obj', 'blockchainId', 'Block_obj', 'publicKey', 'Name', 'Title', 'display_name'
        ]
        data = {k: process_value(v) for k, v in data.items()}
        sorted_dict = dict(sorted(data.items(), key=lambda item: item[0].lower()))
        starting_dict = {key: sorted_dict.pop(key) for key in order_list if key in sorted_dict}
        return {**starting_dict, **sorted_dict}
    elif isinstance(data, list):
        return sorted(
            (process_value(v) for v in data), 
            key=deep_sort_key
        )
    return stringify_if_bool(data)

_super_id = None

def super_id(iden=None, net=None):
    from utils.models import prntDev, prnt, prntDebug
    prnt('super_id()',iden)
    global _super_id
    if _super_id is None:
        from blockchain.models import Sonet
        sonet = Sonet.objects.first()
        prntDebug('sonet',sonet)
        if not sonet and net:
            sonet = net
        if sonet:
            if isinstance(sonet, dict):
                net_iden = sonet['id']
                net_created_dt = sonet['created']
            else:
                net_iden = sonet.id
                net_created_dt = sonet.created
            if net_iden == 'ohSo4ysURHSGh2i8QYsceeS4yI':
                # _super_id = 'usrSo7vmfyZc7GoAq4ky8skiiif'
                _super_id = 'usrSoXra8XFCgMwu4ucc0GsY0g'
                prntDebug('_super_id1',_super_id)
            elif net_created_dt:
                prntDebug('sonet.created',net_created_dt)
                if net and isinstance(net_created_dt, str):
                    c_dt = net_created_dt
                else:
                    c_dt = dt_to_string(net_created_dt)
                _super_id = 'usrSo' + generate_id(f'ShardHolder-{c_dt}',len=14)
                prntDebug('_super_id2',_super_id)
        else:
            return True
        
    prnt('_super_id',_super_id)
    if iden:
        return True if _super_id == iden else False
    return _super_id
