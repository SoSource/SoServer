from django.db import models
from django.contrib.postgres.indexes import GinIndex

from utils.models import *
from utils.locked import sort_for_sign, hash_obj_id, super_id, validate_obj, generate_id, sign_obj, get_relevant_nodes_from_block, get_node_assignment, get_broadcast_list, check_block_contents, get_commit_data, check_commit_data, get_signing_data, sign_for_sending, convert_to_dict, check_validation_consensus, verify_data

import datetime
import pytz
from dateutil.parser import parse
# from dateutil import tz
import hashlib
import json
import time
import random
import math

import requests
import re
import django_rq
import operator
from itertools import chain

import platform
# from collections import OrderedDict
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q
import os


current_version = 0.9
golden_ratio = (1 + math.sqrt(5)) / 2
number_of_peers = 2 # used for downstream_broadcast
fails_to_strike = 10 # x failures == 1 strike
recent_failure_range = 3 # how many days between strikes for node if x failures
too_many_strike_count = 10 # deactivate node after x strikes
striking_days = 30 # too_many_strike count within this number of days before being deactivated
max_commit_window = 11 # number of days for an obj to be committed to a block
max_validation_window = 7 # number of days for an obj to be validated
# block_time_delay = 60 
number_of_scrapers = 2

def get_required_validator_count(dt=None, obj=None, func=None, node_ids=None, include_initializers=False):
    if obj and obj.object_type == 'Block':
        return obj.get_required_validator_count(node_ids=node_ids)
    if obj and obj.object_type == 'User':
        return 500
    elif node_ids == None:
        if obj and has_field(obj, 'blockchainId'):
            # if has_field(obj, 'added'):
            #     dt = obj.added
            # elif has_field(obj, 'created'):
            #     dt = obj.created
            if has_field(obj, 'created'):
                dt = obj.created
            if obj.blockchainId:
                chain = Blockchain.objects.filter(id=obj.blockchainId).first()
            else:
                chain = Blockchain.objects.filter(genesisId=NodeChain_genesisId).first()
            if chain:
                node_ids = get_relevant_nodes_from_block(dt=dt, genesisId=chain.genesisId, node_ids_only=True)
        if node_ids == None:
            if obj:
                # if has_field(obj, 'added'):
                #     dt = obj.added
                # elif has_field(obj, 'created'):
                #     dt = obj.created
                if has_field(obj, 'created'):
                    dt = obj.created
            if not dt:
                dt = now_utc()
            node_ids = get_relevant_nodes_from_block(dt=dt, node_ids_only=True)
    # from accounts.models import Sonet
    if func:
        # for scraping functions
        if include_initializers:
            return 2, 1 # 2 scrapers, 1 validator
        return 1 
    else:
        if dt > Sonet.objects.first().created: # adjust here, covers userTransaction objs, not sure if anything else.
            vals = 10
            creator_options = 4
        else:
            vals = 10
            creator_options = 4
        
        # I don't know what this balognia is below - likely important
        if include_initializers: # handles userTransaction blocks, allows for multiple creators if first one is unavailable
            if (creator_options + vals) > len(node_ids):
                vals = int(vals/2)
                run = True
                while run and (creator_options + vals) > len(node_ids):
                    creator_options = int(creator_options/2)
                    vals = int(vals/2)
                    if vals <= 1 and creator_options <= 1:
                        run = False
                        vals = 1
                        creator_options = 1
            return creator_options, vals
        else:
            if len(node_ids) <= 1:
                return 1
            elif vals > len(node_ids):
                return len(node_ids) - 1 # minus creator 
            else:
                return vals
        
def block_time_delay(chain=None): # minimum time (mins) before next block on chain
    users = 0.5 # 30 seconds between transactions
    nodes = 10
    other = 60
    if not chain:
        return other
    if isinstance(chain, str):
        if chain == 'Nodes' or chain == 'Node':
            return nodes
        # elif chain == 'Users' or chain == 'User':
        #     return users
        else:
            return other
    else:
        if has_field(chain, 'blockchainType') and chain.blockchainType == NodeChain_genesisId or has_field(chain, 'genesisType') and chain.genesisType == NodeChain_genesisId:
            return nodes
        # elif chain.genesisType == 'Users' or chain.genesisType == 'User':
        #     return users
        else:
            return other

NodeChain_genesisId = 'Nodes'
UserChains = 'User'
EarthChain_genesisId = 'regSoIkpb6hxMSAEOQI'

default_apps = ['accounts', 'blockchain', 'posts', 'transactions']
mandatoryChains = [NodeChain_genesisId, UserChains, 'Sonet', 'Wallet', EarthChain_genesisId]
specialChains = ['New']
selectableChains = ['Region']
universalChains = mandatoryChains + selectableChains + ['All']
user_created_modifiable_models = ['UserFollow','UserSavePost','DataPacket','Node','NodeReview']
script_created_modifiable_models = ['Region','District','Party']
unshared_models = ['Post','UserAction','UserNotification','Wallet','Blockchain','EventLog','Keyphrase','KeyphraseTrend']

model_prefixes = {'Sonet':'oh','Plugin':'plg','DataPacket':'dat','Node':'nod','NodeReview':'nrev','Block':'blk','Validator':'val','Blockchain':'chn','EventLog':'elog',}

def default_coin_info():
    return {'name': 'Token', 'plural': 'Tokens', 'pronunciation': 'toe-ken'}

class Sonet(models.Model):
    object_type = "Sonet"
    blockchainType = 'Sonet'
    is_modifiable = True
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default='0', primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.PROTECT)
    Title = models.CharField(max_length=200, default="x")
    Subtitle = models.CharField(max_length=200, default=None, blank=True, null=True)
    LogoLink = models.CharField(max_length=200, default="img/default_logo.png")
    coin_info = models.JSONField(default=default_coin_info, blank=True, null=True)
    # coin_name = models.CharField(max_length=200, default="Token")
    # coin_name_plural = models.CharField(max_length=200, default="Tokens")
    # CoinLogoLink = models.CharField(max_length=200, default=None, blank=True, null=True)
    # Description = models.TextField(default=None, blank=True, null=True)
    Info = models.JSONField(default=None, blank=True, null=True)
    anonymous_users = models.BooleanField(default=True)
    private_content = models.BooleanField(default=False)
    approved_nodes_only = models.BooleanField(default=False)
    requirements = models.JSONField(default=None, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self):
        return 'Sonet:%s' %(self.Title)
    
    class Meta:
        ordering = ['created']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Sonet', 'is_modifiable': True, 'blockchainType': 'Sonet', 'modelVersion': 1, 'id': '0', 'created': None, 'last_updated': None, 'Block_obj': None, 'Title': 'x', 'Subtitle': None, 'LogoLink': 'img/default_logo.png', 'coin_info': {'name': 'Token', 'plural': 'Tokens', 'pronunciation': 'toe-ken'}, 'Info': None, 'anonymous_users': True, 'private_content': False, 'approved_nodes_only': False, 'requirements': None, 'publicKey': '', 'signature': '', 'validation_error': False}

    def delete(self):
        exists = Sonet.objects.exclude(id=self.id).first()
        if exists:
            super(Sonet, self).delete()
        else:
            pass

    def initialize(self):
        self.modelVersion = self.latestModel
        if self.id == '0':
            self.id = hash_obj_id(self)
        return self
    
    def boot(self):
        from accounts.models import User
        # from blockchain.models import Blockchain, NodeChain_genesisId
        sonetChain = Blockchain.objects.filter(genesisId=self.id).first()
        if not sonetChain:
            sonetChain = Blockchain(genesisId=self.id, genesisType='Sonet', genesisName='Sonet', created=self.created)
            sonetChain.save()
        sonetChain.add_item_to_queue(self)
        for u in User.objects.all():
            sonetChain.add_item_to_queue(u)
        nodeChain = Blockchain.objects.filter(genesisType='Nodes').first()
        if not nodeChain:
            nodeChain = Blockchain(genesisId=NodeChain_genesisId, genesisType='Nodes', genesisName='Nodes', created=self.created)
            nodeChain.save()

    def save(self, *args, **kwargs):
        # prntDebug('saving sonet...')
        from accounts.models import User, UserPubKey
        exists = Sonet.objects.exclude(id=self.id).first()
        if not exists:
            u = User.objects.filter(id=super_id(net=self)).first()
            if u:
                upks = UserPubKey.objects.filter(User_obj=u) # self.last_updated should be less than upk.end_life_dt
                for upk in upks:
                    if self.publicKey == upk.publicKey:
                        is_valid = verify_data(get_signing_data(self), upk.publicKey, self.signature)
                        # is_valid = upk.verify(get_signing_data(self), self.signature)
                        prnt('is_valid sonetsave',is_valid)
                        if is_valid:
                            super(Sonet, self).save(*args, **kwargs)
                            self.boot()
                            # from utils.models import share_with_network
                            share_with_network(self)
                            break
            else:
                prnt('no super user') 
                pass

class Plugin(models.Model):
    object_type = "Plugin"
    blockchainType = 'Sonet'
    is_modifiable = True
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)

    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    # blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.PROTECT)
    publicKey = models.CharField(max_length=200, default="", blank=True)
    signature = models.CharField(max_length=200, default="", blank=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.SET_NULL)
    Title = models.CharField(max_length=200, default="x")
    Subtitle = models.CharField(max_length=200, default=None, blank=True, null=True)
    Description = models.TextField(default=None, blank=True, null=True)
    data = models.JSONField(default=None, blank=True, null=True)
    app_name = models.CharField(max_length=200, default="x")
    app_dir = models.CharField(max_length=200, default='../', blank=True, null=True)
    plugin_prefix = models.CharField(max_length=200, default=None, blank=True, null=True)
    model_prefixes = models.JSONField(default=None, blank=True, null=True)


    def __str__(self):
        return 'Plugin:%s' %(self.Title)
    
    class Meta:
        ordering = ['created']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Plugin', 'is_modifiable': True, 'blockchainType': 'Sonet', 'modelVersion': 1, 'id': '0', 'created': None, 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'User_obj': None, 'Title': 'x', 'Subtitle': None, 'Description': None, 'data': None, 'app_name': 'x', 'app_dir': '../', 'plugin_prefix': None, 'model_prefixes': None}

    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['id','created','User_obj','Title','model_prefixes','app_name','app_dir','assign_plugin_prefix'] # should create a new block if any of these are changed
        
    def assign_plugin_prefix(self, check_data=None, addition=0):
        if check_data:
            if 'plugin_prefix' not in check_data:
                return False
            if self.Block_obj and self.Block_obj.validated:
                plugin_prefix = self.Block_obj[self.id]['plugin_prefix']
                if self.plugin_prefix != plugin_prefix:
                    self.plugin_prefix = plugin_prefix
                    self.save()
                return True
            if 'app_name' in check_data['app_name'] and check_data['app_name'] in default_apps:
                if self.created < Sonet.objects.first().created + datetime.timedelta(minutes=10): 
                    if check_data['plugin_prefix'] == '0':
                        return True
                return False

            check_num = check_data['plugin_prefix']
            latest_plugin = Plugin.objects.exclude(Block_obj=None, id=self.id).filter(plugin_prefix=check_num).first()
            if latest_plugin:
                return False
            return True # only checks that plugin_prefix not already used
        if self.app_name in default_apps:
            if self.created < Sonet.objects.first().created + datetime.timedelta(minutes=10): 
                return {'plugin_prefix':'0'}
        if self.Block_obj and self.Block_obj.validated:
            plugin_prefix = self.Block_obj[self.id]['plugin_prefix']
            if self.plugin_prefix != plugin_prefix:
                self.plugin_prefix = plugin_prefix
                self.save()
            return {'plugin_prefix':self.plugin_prefix}
        latest_plugin = Plugin.objects.exclude(Block_obj=None).order_by('-plugin_prefix').first()
        if latest_plugin:
            return {'plugin_prefix':str(int(latest_plugin.plugin_prefix) + addition)}
        else:
            return {'plugin_prefix':'1'}

    def initialize(self):
        self.modelVersion = self.latestModel
        if self.id == '0':
            self.id = hash_obj_id(self)
            self.created = now_utc()

            if not self.model_prefixes:
                import importlib
                from django.conf import settings
                app_dict = {}
                for app in settings.INSTALLED_APPS:
                    try:
                        # prnt('app_config.name',app)
                        if app == self.app_name:
                            models_module = importlib.import_module(f"{app}.models")
                            if hasattr(models_module, "model_prefixes"):
                                prefixes = getattr(models_module, "model_prefixes")
                                if isinstance(prefixes, dict):
                                    for key, value in prefixes.items():
                                        app_dict[key] = value
                            break
                    except ModuleNotFoundError:
                        continue
                    except Exception:
                            continue
                self.model_prefixes = app_dict
                
        # user must set User_obj, Title, app_name, app_dir, model_prefixes
        # optionally set Subtitle, Description, data
        return self

        
    def delete(self):
        # if not is_locked(self):
            # delete
        ...

    def save(self, *args, **kwargs):
        # prntDebug('saving plugin...')
        # if self.publicKey belongs to self.User_obj:
            # if any field in commit_data has changed, add to commit queue
                # unchangeable fields = app_name, plugin_prefix, model_prefixes can be added, not changed or removed
                # save
                # share with network
            # elif self.Block_obj and check_commit_data(self) and self.Block_obj.validated:
                # save
            # elif not self.Block_obj:
                # add to commit queue
                # save
        super(Sonet, self).save(*args, **kwargs)
    
    def boot(self):
        blockchain, self, secondChain = find_or_create_chain_from_object(self)
        self.save()
        blockchain.add_item_to_queue(self)


class DataPacket(models.Model):
    object_type = 'DataPacket'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    queued_dt = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    Node_obj = models.ForeignKey('blockchain.Node', blank=True, null=True, on_delete=models.CASCADE)
    data = models.JSONField(default=dict, blank=True, null=True)
    chainId = models.CharField(max_length=50, default="", blank=True, null=True)
    chainName = models.CharField(max_length=50, default="", blank=True, null=True)
    func = models.CharField(max_length=90, default=None, blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    notes = models.JSONField(default=dict, blank=True, null=True)
    

    def __str__(self):
        return f'DATAPACKET:{self.id} chain:{self.chainId}'
    
    class Meta:
        ordering = ["-created"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            # return {'object_type': 'DataPacket', 'modelVersion': 1, 'id': '0', 'created': None, 'Node_obj': None, 'data': {}, 'chainId': '', 'chainName': '', 'func': None, 'Region_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'notes': {}}
            return {'object_type': 'DataPacket', 'modelVersion': 1, 'id': '0', 'created': None, 'queued_dt':None, 'Node_obj': None, 'data': {}, 'chainId': '', 'chainName': '', 'func': None, 'Region_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'notes': {}}
            # return {'object_type': 'DataPacket', 'modelVersion': 1, 'id': '0', 'created': None, 'queued_dt':None, 'Node_obj': None, 'data': {}, 'chainId': '', 'chainName': '', 'func': None, 'Region_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'notes':{}}
        
    def completed(self, fail=None, note=None, completed='process'):
        if fail:
            self.func = self.func.replace('process','failed').replace('scrape','failed')
            self.func = self.func + f"-f:{fail.replace('process','prcs').replace(' ','_')}"
        elif completed == 'process':
            self.func = self.func.replace('process','completed').replace(' ','_')
        elif completed == 'scrape':
            self.func = self.func.replace('scrape','completed').replace(' ','_')

        else:
            self.func = self.func.replace('process','completed').replace('scrape','completed').replace(' ','_')
        if note:
            self.func = self.func + f"-n:{note.replace(' ','_')}"
        prntDebug('dp completed, func',self.func)
        self.save()

    def broadcast(self, iden=None, broadcast_list=None):
        prnt('\n--broadcast datapacket', self, len(self.data.keys()))
        if not self.data and self.chainId != NodeChain_genesisId:
            if self.queued_dt:
                self.queued_dt = None
                self.save()
            return None
        # if exists_in_worker('broadcast', self.id, queue_name='low', currently_running_only=True, job_count=2):
        #     return False
        else:
            operatorData = get_operatorData()
            self_node = get_self_node(operatorData=operatorData)
            if self.chainId == NodeChain_genesisId:
                try:
                    # include most recent instance of self_node accessing each other node
                    accessed = NodeReview.objects.filter(CreatorNode_obj=self_node, last_updated__gte=now_utc() - datetime.timedelta(minutes=9.8))
                    for a in accessed:
                        self.data[a.id] = sigData_to_hash(a)
                except:
                    pass
                try:
                    # include most recent instances of FCMDevice

                    # not currently being signed, this will prevent sync on receiver node
                    # from fcm_django.models import FCMDevice
                    from accounts.models import CustomFCM
                    fcm_devices = CustomFCM.objects.filter(date_created__gte=now_utc() - datetime.timedelta(minutes=9.8))
                    for a in fcm_devices:
                        self.data[a.id] = sigData_to_hash(a)
                except:
                    pass
                if len(self.data.keys()) == 0:
                    return None
                self.queued_dt = None
                self.save()

            logEvent(f'broadcast pack id: {self.id}. data_len: {len(self.data)}. chainId: {self.chainId}.')
            if not broadcast_list:
                from utils.locked import get_broadcast_list
                broadcast_list = get_broadcast_list(self, dt=now_utc())
            prnt('dataPack broadcast_list',broadcast_list)
            if not broadcast_list:
                if self.data:
                    logEvent('removing datapacket content - no broadcast_list', code='3463', extra=self.data)
                self.data = {}
                self.queued_dt = None
                self.notes[dt_to_string(now_utc())]['fail3'] = 'no broadcast_list'
                self.save()
                return True
            elif not self.data:
                if self.queued_dt:
                    self.queued_dt = None
                    self.save()
                return None
            else:
                now = dt_to_string(now_utc())
                self = sign_obj(self)
                from itertools import islice
                data, not_found, not_valid = get_data(dict(islice(self.data.items(), 500)), include_related=False)
                if data:
                    total_mbs = 0
                    to_send_items = []
                    for d in data:
                        mbs = to_megabytes(d)
                        if (total_mbs + mbs) < 45:
                            total_mbs += mbs
                            to_send_items.append(d)
                        else:
                            break
                    packet_id = hash_obj_id('DataPacket', specific_data=str(to_send_items))
                    self.notes[now] = {packet_id:{}}
                    if not_found or not_valid:
                        if not_found:
                            self.notes[now][packet_id]['not_found'] = not_found
                            for i in not_found:
                                if i in self.data:
                                    del self.data[i]
                        if not_valid:
                            self.notes[now][packet_id]['not_valid'] = [i['id'] for i in not_valid]
                            for i in not_valid:
                                if i['id'] in self.data:
                                    del self.data[i['id']]
                    self.save()
                    compressed_data = to_send_items
                    # compressed_data = compress_data(to_send_items)
                    node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, validated=True).order_by('-index', 'created').first() 
                    sending_data = {'type' : 'DataPacket', 'packet_id':packet_id, 'node_block_id': node_block.id if node_block else None, 'node_block_hash': node_block.hash if node_block else None, 'senderId' : self_node.id, 'sending_idens':[i['id'] for i in to_send_items], 'broadcast_list' : json.dumps({key:value for key, value in broadcast_list.items()}), 'content' : compressed_data}
                    # prnt('sending_data',sending_data)

                    sending_data = sign_for_sending(sending_data)
                    try:
                        successes = downstream_broadcast(broadcast_list, 'blockchain/receive_data_packet', sending_data, self_node=self_node, operatorData=operatorData, stream=True, skip_self=True, exclude=[self_node.id])
                        if successes >= len(broadcast_list[0]) or successes >= Node.objects.exclude(activated_dt=None).filter(supportedChains_array__contains=[self.chainId], suspended_dt=None).count():
                            self.notes[now][packet_id]['sent'] = []
                            for i in to_send_items:
                                if 'id' in i and i['id'] in self.data:
                                    del self.data[i['id']]
                                    self.notes[now][packet_id]['sent'].append(i['id'])
                            if self.data:
                                # if not exists_in_worker('broadcast', self.id, queue_name='low', job_count=2):
                                run_at = now_utc() + datetime.timedelta(minutes=random.randint(1, 7))
                                self.queued_dt = run_at
                                django_rq.get_scheduler('low').enqueue_at(run_at, self.broadcast, timeout=120)
                            else:
                                self.queued_dt = None
                            self.save()
                            return True
                        else:
                            logEvent(f'too few successes: {successes}', func='dp_broadcast', code='824')
                            self.notes[now]['fail1'] = {'too few success':{'req':len(broadcast_list[0]),'achieved':successes}}
                            run_at = now_utc() + datetime.timedelta(minutes=random.randint(10, 25))
                            self.queued_dt = run_at
                            self.save()
                            django_rq.get_scheduler('low').enqueue_at(run_at, self.broadcast, timeout=120)
                    except Exception as e:
                        prnt('dp braod err 3824',str(e))
                        logError(str(e), func='dp_broadcast', code='3824')
                        self.notes[now]['fail2'] = str(e)
                        run_at = now_utc() + datetime.timedelta(minutes=random.randint(1, 7))
                        self.queued_dt = run_at
                        self.save()
                        django_rq.get_scheduler('low').enqueue_at(run_at, self.broadcast, timeout=120)
                else:
                    if self.data:
                        logEvent('removing datapacket content 2', code='6453', extra=self.data)
                    self.data = {}
                    self.queued_dt = None
                    self.save()
                return False
            
    def add_item_to_share(self, obj):
        prnt('--datapackey add_item_to_share',str(obj)[:100],'...')
        exclude = ['cha','wal']
        all = ['nod','reg', 'usr', 'upk','uver','udat']
        if not obj:
            return False


        def add_worker_job(dp):
            if not testing():
                operatorData = get_operatorData()
                if not 'syncingDB' in operatorData or operatorData['syncingDB'] != True:
                    if not self.queued_dt:
                    # if not exists_in_worker('broadcast', dp.id, queue_name='low'):
                        run_at = now_utc() + datetime.timedelta(minutes=random.randint(1, 11))
                        self.queued_dt = run_at
                        # self.save()
                        prnt('add dp_broadcast to scheduler',run_at)
                        django_rq.get_scheduler('low').enqueue_at(run_at, dp.broadcast, iden=dp.id, timeout=120)
                        return True
            return False

        def send_to_all(obj):
            prnt('send_to_all',str(obj)[:150])
            allPacket = DataPacket.objects.filter(chainId='All').first()
            save_all = False
            if isinstance(obj, list):
                for i in obj:
                    if isinstance(i, models.Model):
                        if i.id not in allPacket.data:
                            allPacket.data[i.id] = sigData_to_hash(i)
                            save_all = True
                    elif isinstance(i, dict):
                        if 'id' in i and i['id'] not in allPacket.data:
                            allPacket.data[i['id']] = sigData_to_hash(i)
                            save_all = True
                        else:
                            for key, value in i.items():
                                if key not in allPacket.data:
                                    allPacket.data[key] = value
                                    save_all = True
                    elif isinstance(i, str) and is_id(i):
                        if i not in allPacket.data:
                            allPacket.data[i] = sigData_to_hash(get_dynamic_model(i, id=i))
                            save_all = True
            else:
                if isinstance(obj, models.Model):
                    if obj.id not in allPacket.data:
                        allPacket.data[obj.id] = sigData_to_hash(obj)
                        save_all = True
                elif isinstance(obj, dict):
                    if 'id' in obj and obj['id'] not in allPacket.data:
                        allPacket.data[obj['id']] = sigData_to_hash(obj)
                        save_all = True
                    else:
                        for key, value in obj.items():
                            if key not in allPacket.data:
                                allPacket.data[key] = value
                                save_all = True
                elif isinstance(obj, str) and is_id(i):
                    if obj not in allPacket.data:
                        allPacket.data[obj] = sigData_to_hash(get_dynamic_model(i, id=i))
                        save_all = True
            if save_all:
                allPacket.save()
                add_worker_job(allPacket)

        if not self.data:
            self.data = {}
        to_all = []
        save_self = False
        obj_ids = []
        if isinstance(obj, models.Model):
            if not obj.id.startswith(tuple(exclude)):
                if obj.id.startswith(tuple(all)) and self.chainId != 'All':
                    send_to_all(obj)
                elif obj.id.startswith(get_model_prefix('Validator')):
                    if any(d.startswith(tuple(all)) for d in obj.data):
                        send_to_all(obj)
                # dataPacket = DataPacket.objects.filter(data__has_key=obj.id).first()
                # if dataPacket:
                #     return False
                # else:
                if obj.id not in self.data:
                    self.data[obj.id] = sigData_to_hash(obj)
                    prnt('save_self1')
                    prnt('content:',self.data)
                    add_worker_job(self)
                    self.save()
                    return True
        elif isinstance(obj, dict):
            prnt('obj',obj)
            if 'id' in obj:
                prnt('is dict', obj)
                if not obj['id'].startswith(tuple(exclude)):
                    if obj['id'].startswith(tuple(all)) and self.chainId != 'All':
                        to_all.append(obj)
                    elif obj['id'].startswith(get_model_prefix('Validator')):
                        if 'data' not in obj:
                            obj = Validator.objects.filter(id=obj['id']).first()
                            if obj and any(d.startswith(tuple(all)) for d in obj.data):
                                send_to_all(obj)
                        elif any(d.startswith(tuple(all)) for d in obj['data']):
                            send_to_all(obj)
                    if obj['id'] not in self.data:
                        self.data[obj['id']] = sigData_to_hash(obj)
                        prnt('save_self2')
                        prnt('content:',self.data)
                        add_worker_job(self)
                        self.save()
                        return True
            else:
                prnt('not dict')
                item_dict = obj
                for key, value in item_dict.items():
                    if not key.startswith(tuple(exclude)):
                        obj_ids.append(key)
                    if key.startswith(get_model_prefix('Validator')):
                        if isinstance(value, models.Model):
                            if any(d.startswith(tuple(all)) for d in value.data):
                                send_to_all(value)
                prnt('stage2')
                val_ids = [i for i in obj_ids if i.startswith(get_model_prefix('Validator')) and i not in to_all]
                if val_ids:
                    for v in Validator.objects.filter(id__in=val_ids):
                        if any(d.startswith(tuple(all)) for d in v.data):
                            to_all.append(v)
                # dataPackets = DataPacket.objects.filter(data__contains=obj_ids)
                # for dp in dataPackets:
                #     for i in dp.data:
                #         if i in obj_ids:
                #             obj_ids.remove(i)
                prnt('stage3', to_all)
                if obj_ids:
                    for i in obj_ids:
                        if i not in self.data:
                            self.data[i] = item_dict[i] # value may be hash of obj
                            save_self = True
                        if i.startswith(tuple(all)) and self.chainId != 'All' and {i:item_dict[i]} not in to_all:
                            to_all.append({i:item_dict[i]})
                    if save_self:
                        prnt('save_self3')
                        prnt('content:',self.data)
                        add_worker_job(self)
                        self.save()
                    if to_all:
                        send_to_all(to_all)
                    return True
        elif isinstance(obj, list):
            prnt('is list')
            # from posts.models import is_id
            item_dict = {}
            for o in obj:
                if isinstance(o, models.Model):
                    if not o.id.startswith(tuple(exclude)):
                        if o.id not in self.data:
                            obj_ids.append(o.id)
                            item_dict[o.id] = o
                        if o.object_type == 'Validator':
                            if any(d.startswith(tuple(all)) for d in o.data):
                                to_all.append(o)
                elif is_id(o):
                    if o not in self.data:
                        if not o.startswith(tuple(exclude)):
                            obj_ids.append(o)
            obj_ids = [item for item in obj_ids if not item.startswith(tuple(exclude))]
            val_ids = [i for i in obj_ids if i.startswith(get_model_prefix('Validator')) and i not in to_all]
            if val_ids:
                for v in Validator.objects.filter(id__in=val_ids):
                    if any(d.startswith(tuple(all)) for d in v.data):
                        to_all.append(v)
            # dataPackets = DataPacket.objects.filter(data__contains=obj_ids).exclude(chainId=self.chainId)
            # for dp in dataPackets:
            #     for i in dp.data:
            #         if i in obj_ids:
            #             obj_ids.remove(i)
            if obj_ids:
                prnt('obj_idens_len',len(obj_ids), 'item_dict_len',len(item_dict))
                if len(item_dict) < len(obj_ids):
                    for model_name, iden_list in seperate_by_type(obj_ids).items():
                        prnt('model_name',model_name,'iden_list',iden_list)
                        items = get_dynamic_model(model_name, list=True, id__in=iden_list)
                        for i in items:
                            if i.id.startswith(tuple(all)) and self.chainId != 'All' and i.id not in to_all:
                                to_all.append(i)
                            if i.id not in self.data:
                                self.data[i.id] = sigData_to_hash(i)
                                save_self = True
                else:
                    for i in obj_ids:
                        if i.startswith(tuple(all)) and self.chainId != 'All' and i not in to_all:
                            to_all.append(i)
                        if i not in self.data:
                            self.data[i] = sigData_to_hash(item_dict[i])
                            save_self = True
                prnt('save_self4',save_self)
                prnt('content:',str(self.data)[:1000])
                if save_self:
                    add_worker_job(self)
                    self.save()
                if to_all:
                    send_to_all(to_all)
                return True
        return False
    
    def updateShare(self, obj):
        if 'shareData' not in self.data:
            self.data['shareData'] = []
        if obj.id not in self.data['shareData']:
            self.data['shareData'].append(obj.id)
            self.save()

    def save(self, share=False, *args, **kwargs):
        # prntDebug('dp save...')
        if self.chainId and not self.chainName:
            if self.chainId == 'All':
                self.chainName = 'All'
            else:
                chain = Blockchain.objects.filter(id=self.chainId).first()
                self.chainName = chain.genesisName
        if self.func:
            self.func = self.func[:90]
        if not self.created:
            self.created = now_utc()
        if self.id == '0':
            self = initial_save(self)
        else:
            # prntDebug('dp save final')
            super(DataPacket, self).save(*args, **kwargs)



class Node(models.Model):
    object_type = 'Node'
    blockchainType = 'Nodes'
    secondChainType = 'Sonet'
    is_modifiable = True
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.SET_NULL)
    node_name = models.CharField(max_length=50, default="", blank=True, null=True)
    ip_address = models.CharField(max_length=50, default="", blank=True, null=True)
    # ipv6_address = models.CharField(max_length=50, default="")
    # onion_address = models.CharField(max_length=50, default="")
    # self_declare_active = models.BooleanField(default=None, blank=True, null=True)
    # deactivated = models.BooleanField(default=None, blank=True, null=True) # deactivated if too many strikes or not responsive
    activated_dt = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    suspended_dt = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    supportedChains_array = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=250, null=True, blank=True)
    fcm_capable = models.BooleanField(default=None, blank=True, null=True)
    ai_capable = models.BooleanField(default=None, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    # disavowed = models.BooleanField(default=None, blank=True, null=True)
    expelled = models.BooleanField(default=None, blank=True, null=True)



    def __str__(self):
        return f'NODE: {self.node_name}-{self.id}'

    class Meta:
        ordering = ["-last_updated"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Node', 'is_modifiable': True, 'blockchainType': 'Nodes', 'secondChainType': 'Sonet', 'modelVersion': 1, 'id': '0', 'created': None, 'last_updated': None, 'User_obj': None, 'node_name': '', 'ip_address': '', 'activated_dt': None, 'suspended_dt': None, 'supportedChains_array': None, 'fcm_capable': None, 'ai_capable': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'expelled': None}
            # return {'object_type': 'Node', 'blockchainType': 'Nodes', 'modelVersion': 1, 'id': '0', 'created': None, 'last_updated': None, 'User_obj': None, 'node_name': '', 'ip_address': '', 'self_declare_active': None, 'suspended_dt': None, 'supportedChains_array': None, 'fcm_capable': None, 'ai_capable': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'disavowed': None}
        
    def return_address(self):
        return self.ip_address
        
    def assess_activity(self, self_node=None):
        prnt('--assess_activity')
        # if fail_count greater than fails_to_strike and nodes who determined the failures greater than fails_to_strike
        last_accessed = self.get_last_accessed()
        if last_accessed and last_accessed.accessed < now_utc() - datetime.timedelta(minutes=30):
            total_failures, recent_failures = self.get_failures()
            prnt('total_failures',total_failures,'recent_failures',recent_failures)
            if last_accessed.accessed > recent_failures[0].created:
                prnt('true1')
                return True
            elif recent_failures.count() > fails_to_strike:
                failure_identifiers = []
                for r in recent_failures:
                    if r.CreatorNode_obj.id in failure_identifiers:
                        failure_identifiers[r.CreatorNode_obj.id] += 1
                    else:
                        failure_identifiers[r.CreatorNode_obj.id] = 1
                if len(failure_identifiers) > fails_to_strike:
                    prnt('step2')
                    if not self_node:
                        self_node = get_self_node()
                    strike = NodeReview.objects.filter(TargetNode_obj=self, CreatorNode_obj=self_node, strike_id=self_node.id, created__lte=now_utc() - datetime.timedelta(days=recent_failure_range)).first()
                    if not strike:
                        strike = NodeReview(TargetNode_obj=self, CreatorNode_obj=self_node, strike_id=self_node.id)
                        strike.save()
                        # strike.signature = get_user().sign_transaction(base64.b64decode(private_key), get_expanded_data(strike))
                        # strike.save()
                        # self.get_node(self.creator_node_id)
                        self.too_many_strikes()
                    prnt('false1')
                    return False
        prnt('true2')
        return True

    def is_active(self): # not used
        def func():
            total, recent = self.get_failures()
            if last_accessed > recent[0].created:
                return True
            else:
                nodes_failed_to_access = []
                for r in recent:
                    if r.CreatorNode_obj.id not in nodes_failed_to_access:
                        nodes_failed_to_access.append(r.CreatorNode_obj.id)
                if len(nodes_failed_to_access) > 10 or len(nodes_failed_to_access) > (len(get_node_list())/2):
                    deactivate(node=self)
                    return False
                else:
                    return True
        if self.suspended_dt:
            return False
        else:
            try:
                deactivated = NodeReview.objects.exclude(suspended_dt=None).order_by('-created').first()
            except:
                deactivated = None
            last_accessed = self.get_last_accessed().accessed
            if deactivated:
                if last_accessed > deactivated.suspended_dt:
                    return True
                else:
                    return func()
            else:
                return func()

    def get_last_accessed(self):
        prnt('--get_last_accessed')
        return NodeReview.objects.exclude(accessed=None).filter(TargetNode_obj=self).order_by('-created').first()

    def get_failures(self):
        prnt('get_failures')
        all_failures = NodeReview.objects.filter(TargetNode_obj=self).exclude(last_fail=None).order_by('-created')
        # failures in past recent_failure_range days
        recent_failures = NodeReview.objects.filter(TargetNode_obj=self, last_fail__gte=now_utc() - datetime.timedelta(days=recent_failure_range)).order_by('-created')
        return all_failures, recent_failures
    
    def get_strikes(self):
        return NodeReview.objects.exclude(strikes=None).filter(TargetNode_obj=self).order_by('-created')
        
    def too_many_strikes(self, period=None):
        prnt('too_many_strikes?')
        if period == 'any':
            strike_objects = NodeReview.objects.exclude(strikes=None).filter(TargetNode_obj=self).order_by('-created')
        else:
            strike_objects = NodeReview.objects.exclude(strikes=None).filter(TargetNode_obj=self).filter(created__gte=now_utc() - datetime.timedelta(days=striking_days)).order_by('-created')
        node_strikers = {}
        for s in strike_objects:
            if s.CreatorNode_obj.id not in node_strikers:
                try:
                    node_strikers[s.CreatorNode_obj.id] += 1
                except:
                    node_strikers[s.CreatorNode_obj.id] = 1
        prnt('node_strikers',node_strikers)
        strikes = 0
        if len(node_strikers) >= too_many_strike_count:
            for key, value in node_strikers:
                if int(value) >= too_many_strike_count:
                    strikes += 1
        prnt('strikes',strikes)
        # if strikes >= too_many_strike_count or strikes >= len(get_node_list()):
        #     # report strike to network?
        #     self.deactivated = True
        #     self.save()
        #     prnt('True')
        #     return True
        # else:
        #     prnt('False')
        #     return False
        return False
        
    def add_failure(self, note='None', self_node=None):
        prnt('add_failure')
        if not self_node:
            self_node = get_self_node()
        if self_node != self: # add - limit number of failures within certain timespan
            failure = NodeReview.objects.filter(CreatorNode_obj=self_node, TargetNode_obj=self).first()
            if not failure:
                failure = NodeReview(TargetNode_obj=self, CreatorNode_obj=self_node)
            if not failure.failures:
                failure.failures = {}
            if len(failure.failures) >= 250:
                sorted_keys = sorted(failure.failures.keys(), key=lambda k: string_to_dt(k))
                failure.failures.pop(sorted_keys[0])
            failure.failures[dt_to_string(now_utc())] = note
            failure.last_fail = now_utc()
            failure.save()
            # failure = sign_obj(failure)
            prnt('failure added I hope')
            self.assess_activity(self_node=self_node)  
            prnt('done add_failure')

    def accessed(self, response_time=None, self_node=None):
        prntDev('accessed',self)
        if not self_node:
            self_node = get_self_node()
        if self_node and self_node != self:
            update = NodeReview.objects.filter(TargetNode_obj=self, CreatorNode_obj=self_node).first()
            if not update:
                update = NodeReview(TargetNode_obj=self, CreatorNode_obj=self_node)
            update.accessed = now_utc()
            if response_time:
                if len(update.response_times) >= 250:
                    sorted_keys = sorted(update.response_times.keys(), key=lambda k: string_to_dt(k))
                    update.response_times.pop(sorted_keys[0])
                update.response_times[dt_to_string(now_utc())] = float(response_time)
                avg = 0
                for value in update.response_times.values():
                    avg += float(value)
                update.avg_response_time = avg/len(update.response_times)
            update.last_updated = now_utc()
            update.save()

    
    def deactivate(self):
        self.suspended_dt = now_utc()
        self.save()
    
    def reactivate(self):
        # self_node = get_self_node()
        # update = NodeReview.objects.filter(TargetNode_obj=self, CreatorNode_obj=self_node).first()
        # if not update:
        #     update = NodeReview(TargetNode_obj=self, CreatorNode_obj=self_node)
        self.suspended_dt = None
        # update.save()
        # update = sign_obj(update)
        # self.deactivated = False
        self.save()

    def broadcast_state(self, node_data=None):
        if node_data:
            # from utils.models import sync_and_share_object
            self, is_valid = sync_and_share_object(self, node_data)
        else:
            is_valid = True
        if is_valid:
            prnt('broadcast_state from self',self)
            from utils.locked import get_broadcast_list
            broadcast_list = get_broadcast_list(self)
            # downstream_broadcast(broadcast_list, 'node_update', {'type' : 'node_update'})
            data = {'source':'server','objData' : get_signing_data(self, include_sig=True)}
            prnt('declare state nodeData222222',data)
            prnt('broadcast_list',broadcast_list)
            # starting_node = get_node_assignment(node_obj, creator_only=True)
            downstream_broadcast(broadcast_list, 'blockchain/declare_node_state', data, skip_self=True)
            prnt('finished rboadcast_state2222')


            if self.activated_dt and not self.suspended_dt:
                if self.id == get_self_node().id:
                    # update database
                    pass

    def initialize(self):
        self.modelVersion = self.latestModel
        self.id = hash_obj_id(self)
        return self
    
    def save(self, share=False, *args, **kwargs):
        if testing():
            super(Node, self).save()
        else:
            from accounts.models import UserPubKey
            for upk in UserPubKey.objects.filter(User_obj=self.User_obj):
                is_valid = verify_data(get_signing_data(self), upk, self.signature)
                # is_valid = upk.verify(get_signing_data(self), self.signature)
                if is_valid:
                    super(Node, self).save(*args, **kwargs)
                    break
    
    def delete(self):
        pass

class NodeReview(models.Model):
    object_type = 'NodeReview'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    TargetNode_obj = models.ForeignKey('blockchain.Node', related_name='target_node_obj', blank=True, null=True, db_index=True, on_delete=models.SET_NULL)
    CreatorNode_obj = models.ForeignKey('blockchain.Node', related_name='creator_node_obj', blank=True, null=True, on_delete=models.SET_NULL)
    special_attrs = models.JSONField(default=None, blank=True, null=True)
    accessed = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    response_times = models.JSONField(default=dict, blank=True, null=True)
    avg_response_time = models.DecimalField(max_digits=7, decimal_places=4, default=None, blank=True, null=True)
    last_fail = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    failures = models.JSONField(default=None, blank=True, null=True)
    # suspended_dt = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    strikes = models.JSONField(default=None, blank=True, null=True) #blockId if referencing strike for block
    
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self):
        return 'NODEREVIEW: %s'%(self.id)
    
    class Meta:
        ordering = ["-created"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'NodeReview', 'modelVersion': 1, 'id': '0', 'created': None, 'last_updated': None, 'TargetNode_obj': None, 'CreatorNode_obj': None, 'special_attrs': None, 'accessed': None, 'response_times': {}, 'avg_response_time': None, 'last_fail': None, 'failures': None, 'strikes': None, 'publicKey': '', 'signature': '', 'validation_error': False}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','TargetNode_obj','CreatorNode_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['id','TargetNode_obj','CreatorNode_obj']

    def update_data(self, share=False):
        self.modelVersion = self.latestModel
        self.save(share=share)

    def save(self, share=False, *args, **kwargs):
        prntDev('save NodeReveiw')
        if self.id == '0':
            if not self.created:
                self.created = now_utc()
            self = initial_save(self)
        # else:
        super(NodeReview, self).save(*args, **kwargs)
        # prntDebug('node reveiw saved')

    def delete(self):
        pass
    
class Block(models.Model):
    object_type = 'Block'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    blockchainType = models.CharField(max_length=50, default="")
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    blockchainId = models.CharField(max_length=50, default="", blank=True, null=True)
    Blockchain_obj = models.ForeignKey('blockchain.Blockchain', blank=True, null=True, on_delete=models.CASCADE)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    CreatorNode_obj = models.ForeignKey('blockchain.Node', blank=True, null=True, on_delete=models.PROTECT)
    Transaction_obj = models.ForeignKey('transactions.UserTransaction', blank=True, null=True, on_delete=models.CASCADE)
    index = models.IntegerField(default=1) 
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True) # created time round down to last 60 mins, unless NodeChain then round up to next 10 mins
    hash = models.CharField(max_length=100, default="", blank=True, null=True)
    previous_hash = models.CharField(max_length=100, default="", blank=True, null=True)
    data = models.JSONField(default=dict, blank=True, null=True)
    validators = models.JSONField(default=dict, blank=True, null=True)
    number_of_peers = models.IntegerField(default=None, blank=True, null=True) # only used for node chain
    nodeBlockId = models.CharField(max_length=50, default="", blank=True, null=True)
    # NodeBlock_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.SET_NULL)
    validated = models.BooleanField(default=None, blank=True, null=True)
    notes = models.JSONField(default=dict, blank=True, null=True)


    def __str__(self):
        return f'BLOCK:{self.index} {self.blockchainType}-{self.id}'
    
    class Meta:
        ordering = ['-index','-DateTime','created','validators','hash','Transaction_obj']
        indexes = [
            GinIndex(fields=['data'], name='Block_data_has_key_index'),
        ]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Block', 'blockchainType': '', 'modelVersion': 1, 'id': '0', 'created': None, 'blockchainId': '', 'Blockchain_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'CreatorNode_obj': None, 'Transaction_obj': None, 'index': 1, 'DateTime': None, 'hash': '', 'previous_hash': '', 'data': {}, 'validators': {}, 'number_of_peers': None, 'nodeBlockId':'', 'validated': None, 'notes': {}}
        # elif int(version) >= 1:
        #     return {'object_type': 'Block', 'blockchainType': '', 'modelVersion': 1, 'id': '0', 'created': None, 'blockchainId': '', 'Blockchain_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'CreatorNode_obj': None, 'Transaction_obj': None, 'index': 1, 'DateTime': None, 'hash': '', 'previous_hash': '', 'data': {}, 'validators': {}, 'number_of_peers': None, 'validated': None, 'notes': {}}
        
    def get_previous_block(self, is_validated=False, return_chain=True):
        if is_validated:
            block = Block.objects.filter(blockchainId=self.blockchainId, validated=True, created__lt=self.created).order_by('-index','created').first()
        else:
            block = Block.objects.filter(blockchainId=self.blockchainId, created__lt=self.created).exclude(validated=False).order_by('-index','created').first()
        if block:
            return block
        elif return_chain:
            return self.Blockchain_obj
        else:
            return None
        
    def get_previous_hash(self):
        previous_block = self.get_previous_block()
        if previous_block.object_type == 'Block':
            return previous_block.hash
        elif not previous_block or previous_block.object_type == 'Blockchain':
            return '0000000'
    
    def is_latest(self, is_validated=True):
        if is_validated:
            next_block = Block.objects.filter(blockchainId=self.blockchainId, index__gt=self.index, validated=True).first()
        else:
            next_block = Block.objects.filter(blockchainId=self.blockchainId, index__gt=self.index).first()
        return True if not next_block else False

    def get_assigned_nodes(self, node_block_data={}):
        if not node_block_data:
            node_block_data = get_relevant_nodes_from_block(obj=self, genesisId=self.Blockchain_obj.genesisId)
        if self.Transaction_obj:
            if not self.Transaction_obj.SenderWallet_obj:
                if 'BlockReward' in self.Transaction_obj.regarding and self.Transaction_obj.regarding['BlockReward'] == self.id:
                    transaction_type = 'reward'

                    creator_nodes, validator_nodes = get_node_assignment(self, full_validator_list=True, node_block_data=node_block_data)
                    broadcast_list = get_broadcast_list(self, relevant_nodes=node_block_data, peer_count=self.number_of_peers)
                    return creator_nodes, validator_nodes, broadcast_list
                else:
                    self.is_not_valid()
                    # prntDebug('p5')
                    return [], [], {}
            elif self.Transaction_obj.ReceiverWallet_obj == self.Blockchain_obj:
                transaction_type = 'receiver'
                creator_nodes, validator_nodes = get_node_assignment(self.Transaction_obj, full_validator_list=True, node_block_data=node_block_data)
                broadcast_list = get_broadcast_list(self.Transaction_obj, relevant_nodes=node_block_data, peer_count=self.number_of_peers)
                return creator_nodes, validator_nodes, broadcast_list
                # creator_nodes, validator_nodes = get_node_assignment(self.Transaction_obj, full_validator_list=True, get_stragglers=False, node_block_data=node_block_data, strings_only=True)
            elif self.Transaction_obj.SenderWallet_obj == self.Blockchain_obj:
                transaction_type = 'sender'
                creator_nodes, validator_nodes = get_node_assignment(self.Transaction_obj, sender_transaction=True, full_validator_list=True, node_block_data=node_block_data)
                broadcast_list = get_broadcast_list(self.Transaction_obj, relevant_nodes=node_block_data, peer_count=self.number_of_peers)
                return creator_nodes, validator_nodes, broadcast_list
                # creator_nodes, validator_nodes = get_node_assignment(self.Transaction_obj, full_validator_list=True, sender_transaction=True, get_stragglers=False, node_block_data=node_block_data, strings_only=True)
                
        # if block.Transaction_obj:
            # if transaction_type == 'reward':
            #     creator_nodes, broadcast_list, validator_list = get_node_assignment(self, full_validator_list=True, get_stragglers=False, node_block_data=node_block_data, strings_only=True)
            # elif transaction_type == 'sender':
            #     creator_nodes, broadcast_list, validator_list = get_node_assignment(self.Transaction_obj, full_validator_list=True, sender_transaction=True, get_stragglers=False, node_block_data=node_block_data, strings_only=True)
            # elif transaction_type == 'receiver':
            #     creator_nodes, broadcast_list, validator_list = get_node_assignment(self.Transaction_obj, full_validator_list=True, get_stragglers=False, node_block_data=node_block_data, strings_only=True)
        else:
            creator_nodes, validator_nodes = get_node_assignment(self, full_validator_list=True, node_block_data=node_block_data)
            broadcast_list = get_broadcast_list(self, relevant_nodes=node_block_data, peer_count=self.number_of_peers)
            return creator_nodes, validator_nodes, broadcast_list
            # creator_nodes, validator_nodes = get_node_assignment(self, full_validator_list=True, get_stragglers=False, node_block_data=node_block_data, strings_only=True)
        
    def get_required_validator_count(self, node_ids=None, return_node_data=False, strings_only=True):
        if not node_ids or return_node_data:
            relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=self.DateTime, obj=self, genesisId=self.Blockchain_obj.genesisId, blockchain=self.Blockchain_obj, strings_only=strings_only, include_peers=True)
            node_ids = [iden for iden, addr in relevant_nodes.items()]
        if self.blockchainType == NodeChain_genesisId and self.index == 1:
            prev = self.get_previous_block()
            if not prev or prev.object_type == 'Blockchain':
                if return_node_data:
                    return 1, relevant_nodes
                return 1
        if self.modelVersion >= 1:
            num = 10
        if len(node_ids) <= 1:
            if return_node_data:
                return 1, relevant_nodes
            return 1
        elif num > len(node_ids):
            if return_node_data:
                return len(node_ids) - 1, relevant_nodes
            return len(node_ids) - 1 # minus creator
        else:
            if return_node_data:
                return num, relevant_nodes
            return num

    def get_required_consensus(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return (1/3)*2
        
    def get_required_delay(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return block_time_delay(self)

    def verify_validation(self):
        prnt('verify_validation')
        # if not self.validated:
        #     prnt('opt1')
        #     return False
        # obj_idens = []
        # data = self.data
        # for chunk in chunk_dict(data, 300):
        #     storedModels, not_found, not_valid, delLogs = get_data(chunk, return_model=True, include_related=False, include_deletions=True)
        #     if not_found or not_valid:
        #         prnt('not_found',not_found,'not_valid',not_valid)
        #         return False
        #     for x in storedModels:
        #         prnt('xx',x)
        #         if x.id in self.data:
        #             if self.data[x.id] == check_commit_data(x, self.data[x.id], return_err=True):
        #                 obj_idens.append(x.id)
        #             else:
        #                 prnt('opt4', x.id)
        #                 return False
        #     storedModels.clear()
        # if len(self.data) == len(obj_idens):
        #     prnt('opt2')
        #     return True
        found_idens, missing_idens = check_block_contents(self, retrieve_missing=True, log_missing=False, downstream_worker=False, return_missing=True)
        if any(i for i in self.data if i not in found_idens):

        # if mismatch:
            fail_reason = 113
            prnt('not valid 1')
            validated = False
            fail_reason = []
            for iden, commit in self.data.items():
                if iden != 'meta' and iden not in found_idens:
                    validated = False
                    fail_reason.append(iden)
        prnt('opt3')
        return False

    def get_validators(self):
        returnData, not_found, not_valid = get_data(self.validators, include_related=True, verify_data=False) 
        # prntDebug('get block validators return:',returnData)
        return returnData

    def get_full_data(self, include_validators=True):
        # should also check against hash saved in block
        from utils.locked import verify_obj_to_data
        self_dict = convert_to_dict(self)
        data = self.data
        if self.blockchainType == 'Nodes':
            returnData = []
            id_list = []
            for chain, addresslist in data.items():
                for item in addresslist:
                    if item not in id_list:
                        id_list.append(item)
            nodes = Node.objects.filter(id__in=id_list)
            for obj in nodes:
                is_valid = verify_obj_to_data(obj, obj)
                if is_valid:
                    returnData.append(convert_to_dict(obj))
            nodeUpdates = NodeReview.objects.filter(TargetNode_obj__id__in=id_list)
            for obj in nodeUpdates:
                is_valid = verify_obj_to_data(obj, obj)
                if is_valid:
                    returnData.append(convert_to_dict(obj))

        else:
            returnData = []
            for chunk in chunk_dict(data, 300):
                storedModels, not_found, not_valid, delLogs = get_data(chunk, return_model=False, include_related=True, include_deletions=True, verify_data=False)
                for x in storedModels:
                    returnData.append(x)
                for x in delLogs:
                    returnData.append(x)
                storedModels.clear()
        returnData.append(self_dict)
        if include_validators:
            returnData2, not_found2, not_valid2 = get_data(self.validators, include_related=False, verify_data=False) 
            returnData = returnData2 + returnData
        return returnData


    def broadcast(self, broadcast_list=None, validations=None, validator_list=None, validators_only=False, target_node_id=None, skip_self=True):
        prnt('--broadcast_block', self.id)
        log = logBroadcast(return_log=True)
        if self.id not in log.data:
            log.data[self.id] = {'first_broadcast':dt_to_string(now_utc())}
        #     if 'count' not in log.data[block.id]:
        #         log.data[block.id]['count'] = [dt_to_string(now_utc())]
        #     else:
        #         log.data[block.id]['count'].append(dt_to_string(now_utc()))
        # else:
        #     log.data[block.id] = {'dt':dt_to_string(now_utc())}
        proceed = True
        if validators_only:
            if 'validators' in log.data[self.id]:
                dt = log.data[self.id]['validators']['dt']
                if now_utc() - string_to_dt(dt) < datetime.timedelta(minutes=20):
                    proceed = False
        else:
            if 'all' in log.data[self.id]:
                dt = log.data[self.id]['all']['dt']
                if now_utc() - string_to_dt(dt) < datetime.timedelta(minutes=20):
                    proceed = False
        if proceed:

            from utils.locked import get_broadcast_list
            if not broadcast_list:
                broadcast_list = get_broadcast_list(self)
            self_node = get_self_node()
            if validators_only:
                if not validator_list:
                    from utils.locked import get_node_assignment
                    creator_nodes, validator_list = get_node_assignment(self)
                lst = {self_node.id:[broadcast_list[v] for v in validator_list]}
            else:
                lst = broadcast_list
            if not validations:
                from utils.locked import verify_obj_to_data
                validations = [convert_to_dict(v) for v in Validator.objects.filter(data__has_key=self.id) if verify_obj_to_data(v, v)]
            elif isinstance(validations[0], models.Model):
                validations = [convert_to_dict(v) for v in validations]
            logEvent(f'broadcast_block: block.id: {self.id}, validators_only:{validators_only}, validations: {validations}', log_type='Tasks', code='632')
            node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=self.DateTime, validated=True).order_by('-index', 'created').first()
            sending_data = {'type' : 'Blocks', 'packet_id':hash_obj_id('DataPacket'), 'senderId':self_node.id, 'node_block_id': node_block.id if node_block else None, 'node_block_hash': node_block.hash if node_block else None, 'broadcast_list': lst, 'blockchainId' : self.blockchainId, 'genesisId':self.Blockchain_obj.genesisId, 'block_list' : json.dumps([{'block_dict' : convert_to_dict(self), 'block_transaction':self.get_transaction_data(), 'block_data' : [], 'validations' : validations}]), 'end_of_chain' : True}
            if node_block and node_block.index != node_block.Blockchain_obj.chain_length:
                sending_data['node_block_not_latest'] = True
            sending_data = sign_for_sending(sending_data)
            successes = downstream_broadcast(lst, 'blockchain/receive_blocks', sending_data, target_node_id=target_node_id, stream=True, skip_self=skip_self)
            if self_node.id in lst and successes >= len(lst[self_node.id]) or successes >= Node.objects.exclude(activated_dt=None).filter(supportedChains_array__contains=[self.blockchainId], suspended_dt=None).count():
                for v in validations:
                    if v['CreatorNode_obj'] == self_node.id:
                        toBroadcast(v['id'], remove_item=True)
                        break
            if successes:
                if validators_only:
                    if 'validators' not in log.data[self.id]:
                        log.data[self.id]['validators'] = {}
                    log.data[self.id]['validators']['dt'] = dt_to_string(now_utc())
                    log.data[self.id]['validators']['broadcast_list'] = lst
                else:
                    if 'all' not in log.data[self.id]:
                        log.data[self.id]['all'] = {}
                    log.data[self.id]['all']['dt'] = dt_to_string(now_utc())
                    log.data[self.id]['all']['broadcast_list'] = lst
                log.save()



    def is_not_valid(self, mark_strike=True, note='', check_posts=False, super_delete_content=False):
        prnt('--is_not_valid',self)
        # if block.creator_node = self_node and block failed by validators, log failed items. if items repeatedly fail block creation, stop commit attmpts for those items
        self_node = get_self_node()
        now = now_utc()
        if mark_strike:
            # do not strike self
            strike = NodeReview.objects.filter(TargetNode_obj=self.CreatorNode_obj, CreatorNode_obj=self_node).first()
            if not strike:
                strike = NodeReview(TargetNode_obj=self.CreatorNode_obj, CreatorNode_obj=self_node)
            if not strike.strikes:
                strike.strikes = {}
            
            if self.id not in strike.strikes:
                strike.strikes[self.id] = dt_to_string(now)
                strike.save()
                self.CreatorNode_obj.too_many_strikes()

        # storedModels, not_found, not_valid = get_data(self.data, return_model=True, verify_data=False, include_related=False)
        start_time = time.time()
        for chunk in chunk_dict(self.data, 500):
            storedModels, not_found, not_valid = get_data(chunk, return_model=True, verify_data=False, include_related=False)
            
            obj_ids = []
            add_to_chain = []
            for x in storedModels:
                # prnt('x',x)
                if super_delete_content:
                    # from utils.models import superDelete
                    superDelete(x, force_delete=True)
                else:
                    if has_field(x, 'Block_obj') and x.Block_obj == self:
                        x.Block_obj = None
                        # from utils.models import get_model
                        super(get_model(x.object_type), x).save()
                    if x.object_type != 'UserTransaction':
                        add_to_chain.append(x)
                        if len(add_to_chain) >= 200:
                            self.Blockchain_obj.add_item_to_queue(add_to_chain, force_add=True)
                            add_to_chain = []
                            
                    obj_ids.append(x.id)
            if add_to_chain:
                self.Blockchain_obj.add_item_to_queue(add_to_chain, force_add=True)
            # for x in not_found:
            #     prnt('y',x)
            # for x in not_valid:
            #     prnt('z',x)

            if obj_ids:
                if check_posts:
                    from posts.models import Post, Update
                    from accounts.models import Notification
                    for chunk in chunk_list(obj_ids, 500):
                        for p in Post.objects.filter(pointerId__in=chunk, blockId=self.id):
                            p.blockId = None
                            p.validated = p.verify_is_valid(check_update=False, use_assigned_val=True)
                            p.save()
                        updates = Update.objects.filter(id__in=chunk, validated=True)
                        for u in updates:
                            u.validated = u.verify_is_valid(use_assigned_val=True)
                            u.save()
                        notifications = Notification.objects.filter(id__in=chunk, validated=True)
                        for n in notifications:
                            n.validated = u.verify_is_valid(use_assigned_val=True)
                            u.save()
                else:
                    from posts.models import Post
                    for chunk in chunk_list(obj_ids, 500):
                        Post.all_objects.filter(pointerId__in=chunk, blockId=self.id).update(blockId=None)
            # print('tt',time.time() - start_time)
            # if (time.time() - start_time) > 60:
            #     elapsed_time = time.time() - start_time
            #     tdt = str(datetime.datetime.fromtimestamp(elapsed_time).isoformat())
            #     prnt('breaking off chunking', tdt) 
            #     try:
            #         prnt('elapsed_time',elapsed_time)
            #     except Exception as e:
            #         prnt('fail3743',str(e))

            #     return

        self.validated = False
        if not self.validators:
            self.validators = {}
        if note:
            self.notes['fail_position'] = note
        if 'fail_dt' not in self.notes:
            self.notes['fail_dt'] = dt_to_string(now)
        # self.save()
        self.nodeBlockId = ''
        super(Block, self).save()
        if self.Transaction_obj:
            self.Transaction_obj.is_not_valid(omit=self, note='reward_fail') 
        following_blocks = Block.objects.filter(Blockchain_obj=self.Blockchain_obj, previous_hash=self.hash).exclude(validated=False)
        prnt('folowing_blocks',following_blocks)
        if following_blocks:
            for b in following_blocks:
                b.is_not_valid(note='followed_previous_fail', super_delete_content=super_delete_content)
        if self.Blockchain_obj.genesisId == NodeChain_genesisId:
            dependent_blocks = Block.objects.filter(nodeBlockId=self.id).exclude(validated=False)
            prnt('dependent_blocks',dependent_blocks)
            if dependent_blocks:
                for b in dependent_blocks:
                    b.is_not_valid(note='dependent_block_fail', super_delete_content=super_delete_content)
        self.Blockchain_obj.chain_length = Block.objects.filter(Blockchain_obj=self.Blockchain_obj, validated=True).order_by('-index').count()
        last_block = Block.objects.filter(Blockchain_obj=self.Blockchain_obj, validated=True).order_by('-created').first()
        if last_block:
            last_dt = last_block.created
        else:
            last_dt = self.Blockchain_obj.created
        self.Blockchain_obj.last_block_datetime = last_dt
        self.Blockchain_obj.save()
        logEvent(f'Block is_not_valid: note:{note}, index:{self.index} - chain:{str(self.Blockchain_obj.genesisName)}, id:{self.id}')
        if self.Blockchain_obj.queuedData:
            if self.Blockchain_obj.genesisId == NodeChain_genesisId or self.Blockchain_obj.genesisId != NodeChain_genesisId and now.minute >= 50:
                if self.Blockchain_obj.last_block_datetime < now - datetime.timedelta(minutes=block_time_delay(self.Blockchain_obj)):
                    self.Blockchain_obj.new_block_candidate(self_node=self_node)

        # if previously validated Node block becomes invalid, all data past that block_dt must be rechecked

        prnt('done not valid')
        
    def is_valid_operations(self, attempts=1, downstream_worker=True):
        prnt('-is_valid_operations',self)
        def operations():
            if self.validated:
                return True
            nonlocal attempts
            nonlocal downstream_worker
            prnt('-perform operations',self)
            proceed = False
            
            self_node = get_self_node()
            if self.blockchainType == NodeChain_genesisId:
                proceed = True
            elif self_node.id in self.validators and json.loads(self.validators[self_node.id])['is_valid']: # self_node created validator, doesnt need to process contents again
                proceed = True

            if not proceed:
                obj_idens, problem_idens = check_block_contents(self, retrieve_missing=True, return_missing=True, downstream_worker=downstream_worker)
                proceed = True

                for model_name, iden_list in seperate_by_type(obj_idens, include_only={'has_field':['Block_obj']}).items():
                    dynamic_bulk_update(model_name, update_data={'Block_obj':self}, id__in=iden_list)
                from posts.models import Post, update_post
                node_block_data = {}
                iden_list = obj_idens.copy()
                now = now_utc()
                update_map = {}

                update_prefix = get_app_name(model_name='Update', return_prefix=True)
                if any(i.startswith(update_prefix) for i in obj_idens):
                    update_idens = [i for i in obj_idens if get_pointer_type(i) == 'Update']
                    for chunk in chunk_dict(update_idens, 300):
                        storedModels, not_found, not_valid = get_data(chunk, return_model=True, verify_data=False, include_related=False, include_deletions=False)
                        update_map.update({u.pointerId: u for u in storedModels})
                
                for chunk in chunk_list(iden_list, 500):
                    bulk_update = []
                    fields = []
                    for p in Post.all_objects.filter(pointerId__in=chunk).exclude(validated=True):
                        ran_val = False
                        try:
                            pointer = p.get_pointer()
                            if has_field(pointer, 'created'):
                                created_dt = dt_to_string(pointer.created)
                                if created_dt not in node_block_data:
                                    relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=pointer.created, genesisId=NodeChain_genesisId, include_peers=True)
                                    node_block_data[created_dt] = {'node_ids':[n for n in relevant_nodes],'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}
                                validated = validate_obj(obj=p, node_block_data=node_block_data[created_dt], save_obj=False, verify_validator=False, update_pointer=False)
                                # validated = p.validate(update_pointer=False, save_self=False, verify_validator=False, node_block_data=node_block_data[created_dt])
                                ran_val = True
                        except Exception as e:
                            prnt('get node_data valid_operations fail 5324', str(e))
                        if not ran_val:
                            validated = validate_obj(obj=p, save_obj=False, verify_validator=False, update_pointer=False)
                            # validated = p.validate(update_pointer=False, save_self=False, verify_validator=False)
                        if validated:
                            p.validated = True
                            p.updated_on_node = now
                            p.blockId = self.id
                            p, updated_fields = update_post(p=p, save_p=False, update=update_map.get(p.pointerId))
                            bulk_update.append(p)
                            if updated_fields:
                                fields += [f for f in updated_fields if f not in fields]
                            iden_list.remove(p.pointerId)
                    prnt(f'val posts block_validate bulk_update: {str(bulk_update)[:100]}')
                    if bulk_update:
                        dynamic_bulk_update(model=Post, items_field_update=['validated', 'updated_on_node', 'blockId'] + fields, items=bulk_update)
                for chunk in chunk_list(iden_list, 500):
                    Post.all_objects.filter(pointerId__in=chunk, blockId=None).update(blockId=self.id)
                        
                # for model_name, iden_list in seperate_by_type(obj_idens, include_only={'has_field':['Block_obj']}).items():
                #     dynamic_bulk_update(model_name, update_data={'Block_obj':self}, id__in=iden_list)
                for i in obj_idens:
                    if i in self.Blockchain_obj.queuedData:
                        del self.Blockchain_obj.queuedData[i]
                

                plugin_prefix = get_app_name(model_name='Plugin', return_prefix=True)
                if any(i.startswith(plugin_prefix) for i in obj_idens):
                    plugin_idens = [i for i in obj_idens if get_pointer_type(i) == 'Plugin']
                    for chunk in chunk_dict(plugin_idens, 100):
                        plugins = Plugin.objects.filter(id__in=chunk)
                        for plug in plugins:
                            plug.plugin_prefix = self.data[plug.id]['plugin_prefix']
                        dynamic_bulk_update(model=Plugin, items_field_update=['plugin_prefix'], items=plugins)
                    if plugin_idens and self.is_latest():
                        get_app_info(rerun=True)

            if not proceed:
                return False
            self.validated = True
            if self.Blockchain_obj.genesisId != NodeChain_genesisId:
                self.nodeBlockId = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=self.DateTime, validated=True).order_by('-index', 'created').first().id
            if self.is_latest():
                if self.blockchainType == NodeChain_genesisId:
                    self.adjust_settings()
                super(Block, self).save()
                if self.Transaction_obj:
                    self.Transaction_obj.mark_valid()
                self.Blockchain_obj.chain_length = self.index
                self.Blockchain_obj.last_block_datetime = self.created
                self.Blockchain_obj.save()
            else:
                super(Block, self).save()
                if self.Transaction_obj:
                    self.Transaction_obj.mark_valid()
            dynamic_bulk_update('Validator', update_data={'Block_obj':self}, id__in=[v for v in self.validators])

            logEvent(f'Block validated: {self.index} - chain:{str(self.Blockchain_obj.genesisName)}, id:{self.id}')
            return True
        def assess_for_transactions():
            prnt('-assess_for_transactions')
            if self.Transaction_obj:
                prnt('do assess')
                # both senderBlock and receiverBlock should be validated together
                if self.Transaction_obj.ReceiverBlock_obj and self == self.Transaction_obj.ReceiverBlock_obj:
                    if not self.Transaction_obj.SenderBlock_obj or self.Transaction_obj.SenderBlock_obj.validated == None:
                        if self.Transaction_obj.SenderBlock_obj:
                            is_valid, consensus_found, validations = check_validation_consensus(self.Transaction_obj.SenderBlock_obj, do_mark_valid=False)
                            if is_valid and consensus_found:
                                result = operations()
                                if result:
                                    self.Transaction_obj.SenderBlock_obj.mark_valid()
                                return result
                        # send self to SenderBlock_obj validator nodes
                        log = EventLog.objects.filter(type='Broadcast History', data__has_key=self.id).first()
                        if not log:
                            log = logBroadcast(return_log=True)
                            log.data[self.id] = {'dt':dt_to_string(now_utc()),'to':'SenderBlock_obj.validators'}
                            log.save()
                            from utils.locked import get_node_assignment, get_broadcast_list
                            creator_nodes, validator_nodes = get_node_assignment(self.Transaction_obj, sender_transaction=True)
                            broadcast_list = get_broadcast_list(self.Transaction_obj)
                            self.broadcast(broadcast_list=broadcast_list, validator_list=validator_nodes, validators_only=True, validations=[convert_to_dict(v) for v in Validator.objects.filter(id__in=list(self.validators.keys()))])
                        return None
                    elif self.Transaction_obj.SenderBlock_obj.validated == False:
                        self.is_not_valid(mark_strike=False, note='sender_fail')
                        return False
                    elif self.Transaction_obj.SenderBlock_obj.validated:
                        return operations() # validate self, then broadcast to all - maybe needs broadcast_block() here
                    else:
                        return None # wait for SenderBlock_obj validation
                elif self.Transaction_obj.SenderBlock_obj and self == self.Transaction_obj.SenderBlock_obj:
                    if not self.Transaction_obj.ReceiverBlock_obj or self.Transaction_obj.ReceiverBlock_obj.validated == None:
                        if self.Transaction_obj.ReceiverBlock_obj:
                            is_valid, consensus_found, validations = check_validation_consensus(self.Transaction_obj.ReceiverBlock_obj, do_mark_valid=False)
                            if is_valid and consensus_found:
                                result = operations()
                                if result:
                                    self.Transaction_obj.ReceiverBlock_obj.mark_valid()
                                return result
                        # send self to receiverBlock validator nodes
                        
                        from utils.locked import get_node_assignment, get_broadcast_list
                        creator_nodes, validator_nodes = get_node_assignment(self.Transaction_obj, sender_transaction=True)
                        if get_self_node().id in creator_nodes:
                            if 'BlockReward' in self.Transaction_obj.regarding:
                                if self.Transaction_obj.regarding['BlockReward'] == self.id:
                                    self.Transaction_obj.send_for_block_creation()
                            else:
                                self.Transaction_obj.send_for_block_creation(downstream_worker=False)
                        else:
                            log = EventLog.objects.filter(type='Broadcast History', data__has_key=self.id).first()
                            if not log:
                                log = logBroadcast()
                                log.data[self.id] = {'dt':dt_to_string(now_utc()),'to':'ReceiverBlock_obj.validators'}
                                log.save()
                                broadcast_list = get_broadcast_list(self.Transaction_obj)
                                self.broadcast(broadcast_list=broadcast_list, validator_list=validator_nodes, validators_only=True, validations=[convert_to_dict(v) for v in Validator.objects.filter(id__in=list(self.validators.keys()))])
                        return None
                    elif self.Transaction_obj.ReceiverBlock_obj.validated == False:
                        self.is_not_valid(mark_strike=False, note='receiver_fail')
                        return False
                    elif self.Transaction_obj.ReceiverBlock_obj.validated:
                        return operations() # validate self, then broadcast to all - maybe needs broadcast_block() here
                    else:
                        return None # wait for receiverBlock validation
                else:
                    return False
            else:
                return operations()
        return assess_for_transactions()

    def adjust_settings(self):
        prnt('r-adjust_settings')
        # from utils.models import write_operatorData
        nodes = Node.objects.filter(id__in=self.data['All'])
        nodes_dict = {n.id: n for n in nodes}
        self.notes['addresses'] = {iden:nodes_dict[iden].return_address() for iden in self.data['All'] if iden in nodes_dict}
        prev_block = self.get_previous_block(is_validated=True)
        if prev_block and prev_block.object_type == 'Block':
            if 'addresses' in prev_block.notes:
                del prev_block.notes['addresses']
                super(Block, prev_block).save()
        operatorData = get_operatorData()
        operatorData['ip_master_list'] = self.notes['addresses']
        operatorData['node_list'] = self.data
        write_operatorData(operatorData)

        prnt('a_settings 2')
        import os
        # import shutil
        from os.path import expanduser
        homepath = expanduser("~")
        folder_path = os.path.expanduser(homepath + "/Sonet/.data/special")
        file_path = os.path.join(folder_path, "trusted_sources.py")
        if os.path.exists(file_path):
            prnt(f"The file '{file_path}' already exists!")
        else:
            with open(file_path, "w") as f:
                f.write("")
            print(f"{file_path} has been created.")

            
        prnt('done create dir')
        prnt('a_settings_3')
        addresses = [n.return_address() for n in nodes]

        formatted_addresses = []
        for ip in addresses:
            formatted_addresses.append(f'https://sovote.center')
            formatted_addresses.append(f'http://sovote.center')
            formatted_addresses.append(f'https://sovote.center:56455')
            formatted_addresses.append(f'http://sovote.center:56455')
        for ip in addresses:
            formatted_addresses.append(f'https://{ip}')
            # formatted_addresses.append(f'https://www.{ip}')
            formatted_addresses.append(f'http://{ip}')
            # formatted_addresses.append(f'http://www.{ip}')
        # text = [
        #     f'''ADDRESSES = "{formatted_addresses}"\n''',
        #     f"MY_LIST = {repr(my_list)}\n"
        # ]
        # prnt('text',text)
        f = open(homepath + "/Sonet/.data/special/trusted_sources.py", "r+")
        f.close()
        open(homepath + "/Sonet/.data/special/trusted_sources.py", "w").close()
        f = open(homepath + "/Sonet/.data/special/trusted_sources.py", "r+")
        # f.writelines(text)
        f.write(f"ADDRESSES = {repr(formatted_addresses)}\n")
        f.close


        # trusted_sources.py

        # ADDRESSES = [
        #     'https://184.xx.xx.xxx:12345',
        #     'http://184.xx.xx.xxx:12345',
        #     'https://104.xx.xx.xxx:98765',
        #     'http://104.xx.xx.xxx:98765'
        # ]

        # def generate_cors_config(file_path="/etc/nginx/cors.conf"):
        with open(homepath + "/Sonet/.data/special/cors.conf", "w") as f:
            # f.write("add_header 'Access-Control-Allow-Origin' '' always'';")
            f.write("set $allowed_origin '';")
            for address in addresses:
                f.write(f"\nif ($http_origin = '{address}') {{")
                f.write(f"\n    set $allowed_origin '{address}';")
                f.write("\n}")
            f.write("\nadd_header 'Access-Control-Allow-Origin' $allowed_origin;")
            f.write("\nadd_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';")
            f.write("\nadd_header 'Access-Control-Allow-Headers' 'Origin, Content-Type, Accept, Authorization';")
            f.write("\nadd_header 'Access-Control-Allow-Credentials' 'true';")

        # generate_cors_config()



        prnt('done adjust settings')
        # import time
        # time.sleep(30)
        return None


    def mark_valid(self, downstream_worker=True, worker_name='main', attempts=1):
        prnt('-mark_block_valid',self)
        if not self.validated:
            if downstream_worker and not testing():
                queue = django_rq.get_queue(worker_name)
                queue.enqueue(self.is_valid_operations, attempts=attempts, downstream_worker=downstream_worker, job_timeout=500, result_ttl=3600)
                return None
            else:
                return self.is_valid_operations(attempts=attempts, downstream_worker=downstream_worker)

    def get_transaction_data(self):
        if self.Transaction_obj:
            return convert_to_dict(self.Transaction_obj)
        return None

# redo superuser_id using stronger hash, restore sovote to legis, makemigrations, then run get_model_fields, then go ahead and start new network, 

    def save(self, share=False, *args, **kwargs):
        prnt('saving block...',self.id, self.blockchainId)
        from utils.locked import verify_obj_to_data
        if self.id == '0':
            self = initial_save(self)
        elif not is_locked(self) and not self.signature or not is_locked(self) and verify_obj_to_data(self, self):
            super(Block, self).save(*args, **kwargs)
            prnt('block saved')
        return self
    
    def delete(self, superDel=False):
        if not is_locked(self) or superDel:
            prnt('deleting block',self)
            transaction = self.Transaction_obj
            try:
                if transaction:
                    transaction.delete(superDel=superDel, skipReceiver_Block=True)
            except Exception as e:
                prnt('f4276',str(e))
            super(Block, self).delete()
    

class Validator(models.Model):
    object_type = 'Validator'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    blockchainType = models.CharField(max_length=50, default=None, blank=True, null=True)
    validatorType = models.CharField(max_length=50, default="", blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    jobId = models.CharField(max_length=50, default=None, blank=True, null=True)
    blockchainId = models.CharField(max_length=50, default=None, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    CreatorNode_obj = models.ForeignKey('blockchain.Node', blank=True, null=True, on_delete=models.PROTECT)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.PROTECT)
    data = models.JSONField(default=dict, blank=True, null=True)
    func = models.CharField(max_length=50, default=None, blank=True, null=True)
    is_valid = models.BooleanField(default=False)

    def __str__(self):
        return f'VAL:{self.validatorType}-{self.id}'
    
    class Meta:
        ordering = ['-created']
        indexes = [
            GinIndex(fields=['data'], name='Validator_data_has_key_index'),
        ]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Validator', 'blockchainType': None, 'modelVersion': 1, 'id': '0', 'validatorType': '', 'created': None, 'jobId': None, 'blockchainId': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'CreatorNode_obj': None, 'Block_obj': None, 'data': {}, 'func': None, 'is_valid': False}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','CreatorNode_obj','func','created','validatorType','jobId']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','is_valid','signature','CreatorNode_obj','created','blockchainId']

    def save(self, share=False, *args, **kwargs):
        from utils.locked import verify_obj_to_data
        if self.id == '0':
            if self.jobId and not isinstance(self.jobId, str):
                self.jobId = str(self.jobId)
            if not self.created:
                self.created = now_utc()
            prnt('new val iden data:',hash_obj_id(self, return_data=True))
            self.id = hash_obj_id(self)
            super(Validator, self).save(*args, **kwargs)
        elif not is_locked(self) and verify_obj_to_data(self, self):
            super(Validator, self).save(*args, **kwargs)

    def delete(self, superDel=False):
        if superDel:
            super(Validator, self).delete()
        else:
            pass

class Blockchain(models.Model):
    object_type = 'Blockchain'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    chain_length = models.IntegerField(default=0) 
    queuedData = models.JSONField(default=dict, blank=True, null=True)
    data_added_datetime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True) # when new data was added since last block created
    genesisType = models.CharField(max_length=50, default="0", blank=True, null=True)
    genesisId = models.CharField(max_length=50, default="0", blank=True, null=True, unique=True, db_index=True) # equal to region.id or user.id etc depending on genesisType
    genesisName = models.CharField(max_length=50, default=None, blank=True, null=True)
    last_block_datetime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    def __str__(self):
        return 'chain:%s_%s'%(self.genesisType,self.genesisName)

    class Meta:
        ordering = ['-chain_length','genesisType','genesisName','created']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Blockchain', 'modelVersion': 1, 'id': '0', 'created': None, 'chain_length': 0, 'queuedData': {}, 'data_added_datetime': None, 'genesisType': '0', 'genesisId': '0', 'genesisName': None, 'last_block_datetime': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type', 'genesisType','genesisId']
    
    def save(self, share=False, *args, **kwargs):
        self.modelVersion = self.latestModel
        if self.id == '0':
            if not self.created:
                self.created = now_utc()
            self.id = hash_obj_id(self)
            self.last_block_datetime = self.created
            # operatorData = get_operatorData()
            # if operatorData and 'chainData' in operatorData and 'supported' in operatorData['chainData'] and 'New' in operatorData['chainData']['supported']:
            #     operatorData['chainData']['supported'] += self.genesisId # does register to the network the node is supporting this chain, currently requires node software action, node obj must be signed and updated
            #     write_operatorData(operatorData)
        if self.queuedData:
            temp_data = self.queuedData
            if 'meta' in temp_data:
                del temp_data['meta']
            if temp_data:
                self.queuedData['meta'] = {'item_count' : len(temp_data)}
        super(Blockchain, self).save(*args, **kwargs)
    
    def delete(self):
        # deletes only if created less than 20 seconds ago
        if not isinstance(self.created, datetime.datetime):
            created = string_to_dt(self.created)
        else:
            created = self.created
        if created >= now_utc()-datetime.timedelta(seconds=20): 
            super(Blockchain, self).delete()
        else:
            pass

    def get_genesis_pointer(self):
        # prntDebug('-get_genesis_pointer')
        if self.genesisId == NodeChain_genesisId:
            return Node.objects.all().order_by('created').first()
        obj = get_dynamic_model(self.genesisType, id=self.genesisId)
        return obj

    def create_dummy_block(self, now=now_utc()):
        # now = now_utc()
        if self.genesisType == 'Nodes':
            dt = round_time(dt=now, dir='up', amount='10mins') # node block is 10mins ahead of time to ensure the node list is already created when called upon
        else:
            dt = round_time(dt=now, dir='down', amount='10mins')
        dummy_block = Block(id=hash_obj_id('Block', specific_data={'object_type':'Block','blockchainId':self.id,'DateTime':dt_to_string(dt)}), Blockchain_obj=self, blockchainId=self.id, blockchainType=self.genesisType, created=now, DateTime=dt)
        prnt('dummy_block:',dummy_block, dt)
        return dummy_block

    def new_block_candidate(self, self_node=None, dt=now_utc(), add_to_queue=True, updated_nodes=None):
        prnt('-new_block_candidate')
        # if node is repeadtedly failing to validate blocks while other nodes are successfully validating the same block, node should be removed from duties
        if self.queuedData != {} or self.genesisType == 'Nodes':
            last_block = self.get_last_block()
            if not last_block or last_block.object_type == 'Blockchain' or last_block.validated:
                dummy_block = self.create_dummy_block(now=dt) # dummy block needed to assign creator
                if self.genesisType == 'Nodes':
                    dummy_block.data = self.get_new_node_block_data(dt=dt)
                    dummy_block.number_of_peers = number_of_peers
                if not Block.objects.filter(id=dummy_block.id).first():
                    from utils.locked import get_node_assignment
                    creator_nodes, validator_nodes = get_node_assignment(dummy_block)
                    if not self_node:
                        self_node = get_self_node()
                    prnt('creator_nodes',creator_nodes, 'self_node.id',self_node)
                    if creator_nodes[0] == self_node.id:
                        logEvent(f'new_block_candidate {self.genesisName} creator_nodes:{creator_nodes}, self_node.id:{self_node}', log_type='Tasks')
                        prnt('do commit')
                        if add_to_queue and not testing():
                            queue = django_rq.get_queue('main')
                            queue.enqueue(self.commit_to_chain, dummy_block=dummy_block, dt=dt, updated_nodes=updated_nodes, validator_nodes=validator_nodes, job_timeout=600, result_ttl=3600)
                        else:
                            self.commit_to_chain(dummy_block=dummy_block, dt=dt, updated_nodes=updated_nodes, validator_nodes=validator_nodes)
                        return True
                    else:
                        dummy_block.delete()
        return False
        
    def verify_new_node_block_data(self, block):
        creation_dt = block.created
        nodes = Node.objects.filter(last_updated__lte=creation_dt)
        for node in nodes:
            if node.id in block.data['All']: # active nodes shuold be > 80% match?
                # check node activation dt
                ...
            # check supported_regions is correct

        return True


    def get_new_node_block_data(self, dt=None):
        prnt('-get_new_node_block_data')

        # currently validators need to have the exact same node data as creator
        # this would be a problem in the event of frequent and numerous node changes
        # would be difficult to get new block validated

        data = {}
        nodes = Node.objects.exclude(activated_dt=None).filter(suspended_dt=None).order_by('-created')
        data['All'] = [node.id for node in nodes] # includes 'User' and 'Nodes' chains

        special_chains = specialChains
        if 'New' in specialChains:
            special_chains = specialChains.remove('New') # mandatorychains covered by 'All'
        if special_chains:
            for i in special_chains: 
                nodes = Node.objects.filter(supportedChains_array__contains=i).exclude(activated_dt=None).filter(suspended_dt=None).order_by('-created')
                data[i] = [node.id for node in nodes]

        # get all suppoerted regions
        from posts.models import Region
        supported_regions = Region.objects.filter(is_supported=True)
        for region in supported_regions:
            nodes = Node.objects.filter(supportedChains_array__icontains=region.id).exclude(activated_dt=None).filter(suspended_dt=None).order_by('-created')
            if nodes.count() < 6:
                server_nodes = nodes
                script_nodes = nodes
            else:
                # make so these adjust regularily but is repeatable according to time of creation
                server_nodes = nodes[:3]
                script_nodes = nodes[3:]
            data[region.id] = {'servers':[node.id for node in server_nodes],'scripts':[node.id for node in script_nodes]}
        prnt('resultdata:',data)
        return data

    def commit_to_chain(self, dummy_block=None, dt=None, updated_nodes=None, validator_nodes=[], testing=False):
        prnt('--commit_to_chain', self.genesisType)
        
        if self.genesisType == 'Nodes':
            # check if any nodes have been updated
            # prhaps if limited number of nodes, create new block every 10 minutes if changes. if many nodes only create block at minute 10 and minute 40? 
            # updated_nodes = Node.objects.filter(last_updated__gte=self.last_block_datetime).count()

            if not updated_nodes:
                if self.data_added_datetime and self.last_block_datetime:
                    if self.data_added_datetime > self.last_block_datetime:
                        last_dt = self.data_added_datetime
                    else:
                        last_dt = self.last_block_datetime
                elif self.data_added_datetime:
                    last_dt = self.data_added_datetime
                elif self.last_block_datetime:
                    last_dt = self.last_block_datetime
                else:
                    last_dt = self.created
                updated_nodes = Node.objects.filter(Q(last_updated__gte=last_dt-datetime.timedelta(minutes=1))|Q(suspended_dt__gte=last_dt-datetime.timedelta(minutes=1))).count() # not currently recognizing nodes restored from deactivation
                prnt('updated_nodes',updated_nodes)
            # updated_nodes = Node.objects.filter(Q(last_updated__gte=self.last_block_datetime-datetime.timedelta(minutes=1))|Q(suspended_dt__gte=self.last_block_datetime-datetime.timedelta(minutes=1))).count()
            if updated_nodes:
                prnt('updated nodes')
                # self.data = {}
                
                if not dummy_block:
                    dummy_block = self.create_dummy_block(now=dt)
                    dummy_block.data = self.get_new_node_block_data(dt=dt)
                    dummy_block.number_of_peers = number_of_peers
                prev_block = self.get_last_block()
                if prev_block.object_type == 'Block' and sort_for_sign(prev_block.data) == sort_for_sign(dummy_block.data):
                    prnt('node data repeat, clearing...')
                    self.queuedData = {}
                    self.data_added_datetime = now_utc()
                    self.save()
                    prnt('saved blockchain nodes')
                    return None
                if 'All' not in dummy_block.data or not dummy_block.data['All']:
                    prnt('no nodes in operation')
                    self.queuedData = {}
                    self.data_added_datetime = now_utc()
                    self.save()
                    prnt('saved blockchain nodes')
                    return None


                new_block, reward = self.create_block(dummy_block=dummy_block)

                # broadcast to all broadcast_list
                from utils.locked import get_node_assignment, get_broadcast_list
                if not validator_nodes:
                    creator_nodes, validator_nodes = get_node_assignment(new_block)
                broadcast_list = get_broadcast_list(new_block)
                new_block.broadcast(broadcast_list=broadcast_list, validator_list=validator_nodes, validators_only=True, target_node_id=None, skip_self=False)

                return new_block
            
        elif self.queuedData:
            if not dummy_block:
                dummy_block = self.create_dummy_block(dt=dt)

            if self.chain_length == 0:
                if self.genesisId not in self.queuedData:
                    genesis_obj = get_dynamic_model(self.genesisType, id=self.genesisId)
                    self.add_item_to_queue(genesis_obj)
                    if self.genesisType == 'User':
                        from accounts.models import UserPubKey
                        upk = UserPubKey.objects.filter(User_obj__id=self.genesisId)
                        for i in upk:
                            self.add_item_to_queue(i)
                    self.refresh_from_db() 
                    
            starting_data_len = len(self.queuedData)
            pending = None
            if 'pending' in self.queuedData:
                pending = self.queuedData['pending']
                del self.queuedData['pending']
            post_ids = []
            for key, value in self.queuedData.items():
                if is_id(key):
                    post_ids.append(key)
            for b in Block.objects.filter(Blockchain_obj=self, data__has_any_keys=post_ids).exclude(validated=False):
                self.queuedData = {k: v for k, v in self.queuedData.items() if k not in b.data.keys()}
            if not self.queuedData or len(self.queuedData) == 1 and 'meta' in self.queuedData:
                if 'meta' in self.queuedData:
                    self.queuedData['meta'] = 0
                if pending:
                    self.queuedData['pending'] = pending
                self.save()
                return None
            else:
                to_commit_data = {}
                added_dt = None
                filtered_dict = {k: v for k, v in self.queuedData.items() if is_id(k)} # skip 'meta' by adding '+00:00'
                data = dict(sorted(filtered_dict.items(), key=lambda item: item[1])) # sort by dt added to queue, oldest first
                start_time = time.time()
                delled, removed = 0, 0
                dt_issue = []
                extra_data = 0
                for chunk in chunk_dict(data, 500):
                    storedModels, not_found, not_valid = get_data(chunk, include_related=False, return_model=True, special_request={'exclude':{'Validator_obj':None}})
                    prntDebug(f'commit_to_chain -- storedModels:{len(storedModels)}, not_found:{len(not_found)}, not_valid:{len(not_valid)}')
                    if not_valid or not_found:
                        logEvent(f'commit_to_chain missing items', code='345456', extra={'dummy_block':dummy_block.id,'not_found':not_found, 'not_valid':[i.id for i in not_valid]})
                    for i in not_valid:
                        prntDebug('not valid',i.id)
                        if i.id in self.queuedData:
                            del self.queuedData[i.id]
                            prntDebug(f'removed from queue:{i.id}')
                            removed += 1
                        i.delete()
                        delled += 1
                    for i in not_found:
                        prntDebug('not found',i)
                        if i in self.queuedData:
                            del self.queuedData[i]
                            prntDebug(f'removed from queue:{i}')
                            removed += 1
                    # for i in storedModels:
                        # if not added_dt and has_field(i, 'created') or has_field(i, 'created') and i.created and i.created < added_dt:
                        #     if not has_field(i, 'Validator_obj') or i.Validator_obj and i.Validator_obj.is_valid and i.id in i.Validator_obj.data and i.Validator_obj.data[i.id] == sigData_to_hash(i):
                        #         added_dt = i.created
                    # n = 0
                    # while not added_dt and n < len(storedModels):
                    #     added_dt = storedModels[n].added
                    #     n += 1
                    cq_list = []
                    added_dt = None
                    for i in storedModels:
                        cq = f'cq:{i.id}'
                        if i.id in self.queuedData:
                            cq = cq + '-A'
                            i_dt = get_timeData(i)
                            if i_dt:
                                cq = cq + 'a'
                                if not has_field(i, 'Validator_obj') or i.Validator_obj and i.Validator_obj.is_valid and i.id in i.Validator_obj.data and i.Validator_obj.data[i.id] == sigData_to_hash(i):
                                    cq = cq + 'B'
                                    if i_dt >= dummy_block.DateTime - datetime.timedelta(days=max_commit_window) and i_dt < dummy_block.DateTime:
                                        cq = cq + 'b'
                                        if not added_dt or i_dt < added_dt:
                                            added_dt = i_dt
                                            cq = cq + 'C'
                                            prntn('new added_dt',dt_to_string(added_dt), i.id)
                                        if i_dt <= added_dt + datetime.timedelta(hours=24):
                                            cq = cq + 'c'
                                            if not has_field(i, 'is_valid') or i.is_valid == True:
                                                cq = cq + 'D'
                                                if i.object_type == 'Plugin':
                                                    if not i.app_name in default_apps:
                                                        to_commit_data[i.id] = {'dt':i_dt, 'commit':get_commit_data(i, extra_data)}
                                                        extra_data += 1
                                                    else:
                                                        to_commit_data[i.id] = {'dt':i_dt, 'commit':get_commit_data(i, 0)}
                                                to_commit_data[i.id] = {'dt':i_dt, 'commit':get_commit_data(i)}
                                    elif i_dt < dummy_block.DateTime - datetime.timedelta(days=max_commit_window):
                                        cq = cq + 'F'
                                        del self.queuedData[i.id]
                                else:
                                    cq = cq + 'f'
                                    dt_issue.append(i.id)
                            else:
                                cq = cq + 'G'
                                dt_issue.append(i.id)
                            cq = cq + f'-i_dt:{dt_to_string(i_dt) if i_dt else None}-added_dt:{dt_to_string(added_dt) if added_dt else None}'
                        prnt(cq)
                        cq_list.append(cq)
                    # prntn('to_commit_data',to_commit_data)
                    storedModels.clear()
                    if dt_issue:
                        prnt('dt_issue!',dt_issue)
                    if delled or removed or dt_issue:
                        logEvent(f'commit_to_chain delled:{delled}, removed:{removed}, cq_list_len:{len(cq_list)}, dt_issue:{dt_issue}, to_commit_data_len:{len(to_commit_data)}, added_dt:{added_dt}')
                        # logEvent(f'commit_to_chain delled:{delled}, removed:{removed}, cq_list:{cq_list}')
                    if (time.time() - start_time) > 60:
                        prnt('breaking off chunking') 
                        break
                # prnt('added_dt',dt_to_string(added_dt))
                for iden, value in to_commit_data.items():
                    dt = value['dt']
                    if dt <= added_dt + datetime.timedelta(hours=24):
                        # prnt('adding',iden, dt)
                        dummy_block.data[iden] = value['commit']
                        if iden in self.queuedData and not testing:
                            del self.queuedData[iden]
                
                to_commit_data.clear()
                for iden in dt_issue:
                    if iden in self.queuedData:
                        self.queuedData.pop(iden)
                        self.queuedData[iden] = dt_to_string(now_utc())


                elapsed_time = time.time() - start_time
                dummy_block.notes['build_time'] = f"{int(elapsed_time // 60):02}:{int(elapsed_time % 60):02}"
                if added_dt:
                    dummy_block.notes['content_dt'] = dt_to_string(added_dt)
                else:
                    dummy_block.notes['created_dt'] = dt_to_string(now_utc())
                if pending:
                    self.queuedData['pending'] = pending
                self.save()
                if not dummy_block.data:
                    logEvent(f'No Block Data: {self.genesisName} - starting_data_len:{starting_data_len}', log_type='Tasks')
                    dummy_block.notes['no data'] = True
                    dummy_block.notes['dt_issue'] = dt_issue
                    dummy_block.validated = False
                    dummy_block.save()
                    # try:
                    #     dummy_block.delete()
                    # except:
                    #     pass
                    return None
                dummy_block.data = sort_dict(dummy_block.data)
                dummy_block.notes['data_length'] = len(dummy_block.data)
                prnt('-has queue')
                new_block, reward = self.create_block(dummy_block=dummy_block)
                prnt('new_block',new_block, 'reward',reward)
                if new_block and not testing:
                    # broadcast to all broadcast_list
                    from utils.locked import get_node_assignment, get_broadcast_list
                    if not validator_nodes:
                        creator_nodes, validator_nodes = get_node_assignment(new_block)
                    broadcast_list = get_broadcast_list(new_block)
                    new_block.notes['creator_nodes'] = creator_nodes
                    new_block.notes['validator_nodes'] = validator_nodes
                    new_block.save()
                    prnt('broadcast_list',broadcast_list,'validator_nodes',validator_nodes)
                    new_block.broadcast(broadcast_list=broadcast_list, validator_list=validator_nodes, validators_only=True, target_node_id=None, skip_self=False)
                return new_block
        return 'did_not_pass'

    def create_block(self, dummy_block=None, block_dict=None, transaction=None, is_reward=False, storedModels=None):
        prnt('--create_block')
        logEvent(f'Block Creation: {self.genesisName}', log_type='Tasks')
        err = 'start'
        operatorData = get_operatorData()
        chain_length = Block.objects.filter(Blockchain_obj=self).exclude(validated=False).order_by('-index').first()
        if chain_length:
            chain_length = chain_length.index
        else:
            chain_length = 0
        if block_dict:
            from utils.locked import verify_obj_to_data
            from utils.models import get_or_create_model, sync_model
            transaction_obj = None
            valid_transaction = False
            ReceiverBlock_obj = None
            SenderBlock_obj = None
            new_block = None
            if 'block_dict' in block_dict:
                block_transaction = block_dict['block_transaction']
                # prnt('block_transaction',block_transaction)
                block_dict = block_dict['block_dict']
                # prnt('block_dict',block_dict)
                if block_transaction:
                    transaction_obj, transaction_is_new = get_or_create_model(block_transaction['object_type'], return_is_new=True, id=block_transaction['id'])
                    if transaction_is_new:
                        if 'ReceiverBlock_obj' in block_transaction and block_transaction['ReceiverBlock_obj']:
                            if dummy_block and dummy_block.id == block_transaction['ReceiverBlock_obj']:
                                super(Block, dummy_block).save()
                            else:
                                ReceiverBlock_obj, block_is_new = get_or_create_model('Block', return_is_new=True, id=block_transaction['ReceiverBlock_obj'])
                                if block_is_new:
                                    super(Block, ReceiverBlock_obj).save()
                        if 'SenderBlock_obj' in block_transaction and block_transaction['SenderBlock_obj']:
                            if dummy_block and dummy_block.id == block_transaction['ReceiverBlock_obj']:
                                super(Block, SenderBlock_obj).save()
                            else:
                                SenderBlock_obj, block_is_new = get_or_create_model('Block', return_is_new=True, id=block_transaction['SenderBlock_obj'])
                                if block_is_new:
                                    super(Block, SenderBlock_obj).save()
                        transaction_obj, valid_transaction, updatedDB = sync_model(transaction_obj, block_transaction)
            
            if dummy_block:
                new_block = dummy_block
            elif ReceiverBlock_obj and ReceiverBlock_obj.id == block_dict['id']:
                new_block = ReceiverBlock_obj
            elif SenderBlock_obj and SenderBlock_obj.id == block_dict['id']:
                new_block = SenderBlock_obj
            else:
                new_block = Block.objects.filter(id=block_dict['id']).exclude(validated=True).first()
                if not new_block:
                    new_block = Block()
            prnt('new_block2345',new_block)
            for field, value in block_dict.items():
                if str(value) != 'None':
                    if '_obj' in field:
                        obj = get_dynamic_model(value, id=value)
                        setattr(new_block, field, obj)
                    else:
                        setattr(new_block, field, value)
            # new_block.reward = calculate_reward(new_block.created)
            new_block.validated = None
            new_block.save()
            # new_block.update(hash=sigData_to_hash(new_block))
            if not verify_obj_to_data(new_block, new_block):
                # new_block.delete()
                prnt('BLOCK failed verify', block_dict['id'])
                return None
            return new_block
        elif transaction:
            self_node = get_self_node()
            if not dummy_block:
                new_block = self.create_dummy_block()
            else:
                new_block = dummy_block

            new_block.created = now_utc()
            new_block.DateTime = transaction.created
            new_block.index = chain_length + 1
            new_block.CreatorNode_obj = self_node
            new_block.previous_hash = new_block.get_previous_hash()
            # if 'meta' in self.queuedData:
            #     del self.queuedData['meta']
            # if self.data:
            #     obj_list = []
            #     # added_dt = None
            #     transfer_data = {}
            #     storedModels, not_found, not_valid = get_data(self.data, return_model=True, include_related=False)
            #     # for i in storedModels:
            #     #     if not added_dt or i.added < added_dt:
            #     #         added_dt = i.added
            #     for i in storedModels:
            #         # if i.added == added_dt:
            #         if check_commit_data(i, self.data[i.id]):
            #             transfer_data[i.id] = self.data[i.id]
            #             obj_list.append(i.id)
            #     already_committed = Block.objects.filter(Blockchain_obj=self, data__has_any_keys=obj_list).exclude(validated=False)
            #     for block in already_committed:
            #         # remove items contained in previous valid blocks
            #         transfer_data = {k: v for k, v in transfer_data.items() if k not in block.data.keys()}
            #     if not transfer_data:
            #         return None
            #     self.data = {k: v for k, v in self.data.items() if k not in transfer_data.keys()}
            # if 'pending' not in self.queuedData:
            #     self.queuedData['pending'] = {}
            if self.genesisId == transaction.ReceiverWallet_obj.id:
                new_block.data['value'] = {'before':transaction.ReceiverWallet_obj.value,'value':transaction.token_value}
            elif transaction.SenderWallet_obj and self.genesisId == transaction.SenderWallet_obj.id:
                new_block.data['value'] = {'before':transaction.SenderWallet_obj.value,'value':f'-{transaction.token_value}'}
            else:
                # new_block.delete()
                return None

            

            new_block.data[transaction.id] = get_commit_data(transaction)
            new_block.Transaction_obj = transaction
            # if is_reward and 'BlockReward' in transaction.regarding and not transaction.SenderWallet_obj:
            #     new_block.data['meta'] = {'is_reward':True}
            new_block.publicKey = operatorData['pubKey']
            new_block = new_block.save()
            new_block.hash = sigData_to_hash(new_block)
            new_block = sign_obj(new_block)
            prnt('transaction block created')

            if 'pending' not in self.queuedData:
                self.queuedData['pending'] = {}
            if self.genesisId == transaction.ReceiverWallet_obj.id:
                self.queuedData['pending'][transaction.id] = {'block':new_block.id,'index':new_block.index,'created':dt_to_string(transaction.created),'before':transaction.ReceiverWallet_obj.value,'value':transaction.token_value}
            elif transaction.SenderWallet_obj and self.genesisId == transaction.SenderWallet_obj.id:
                self.queuedData['pending'][transaction.id] = {'block':new_block.id,'index':new_block.index,'created':dt_to_string(transaction.created),'before':transaction.SenderWallet_obj.value,'value':f'-{transaction.token_value}'}
            self.save()

            return new_block

        elif dummy_block:
            err = '0'
            self_node = get_self_node()
            new_block = Block.objects.filter(id=dummy_block.id).exclude(validated=True).first()
            if not new_block:
                new_block = dummy_block
            new_block.created = now_utc()
            new_block.index = chain_length + 1
            new_block.CreatorNode_obj = self_node

            reward = None
            if self.genesisType == 'Region':
                from transactions.models import UserTransaction
                reward = UserTransaction(ReceiverWallet_obj=self_node.User_obj.get_wallet(), regarding={'BlockReward':'coming'}, created=new_block.created)
                reward.save()
                new_block.Transaction_obj = reward
            new_block.previous_hash = new_block.get_previous_hash()
            if 'meta' in self.queuedData:
                del self.queuedData['meta']
            if self.genesisType == NodeChain_genesisId:
                err = 'nodestart'
                self.queuedData = {}
            else:
                err = 'A'
                if not new_block.data:
                    prnt('-no transfre data')
                    logEvent(f'No Block Data: {self.genesisName} - err:{err}', log_type='Tasks')
                    return None, None
                
                self.queuedData = {k: v for k, v in self.queuedData.items() if k not in new_block.data.keys()}
            new_block.publicKey = operatorData['pubKey']
            new_block = new_block.save() # save before creating hash
            new_block.hash = sigData_to_hash(new_block)
            if new_block.Transaction_obj:
                from utils.locked import calculate_reward
                reward.token_value = calculate_reward(new_block.created)
                reward.regarding = {'BlockReward':new_block.id}
                reward.SenderBlock_obj = new_block
                reward = sign_obj(reward)
                new_block.data[reward.id] = get_commit_data(reward)
            new_block = sign_obj(new_block)
            prnt('verify_obj_to_data(new_block, new_block)',verify_obj_to_data(new_block, new_block))
            prnt('-block created')
            if not self.queuedData:
                self.data_added_datetime = None
            self.save()
            prnt('-done create_block', new_block, reward)
            logEvent(f'done create_block: {new_block.index}, {self.genesisName} items:{len(new_block.data)} - prog:{err}', log_type='Tasks')
            return new_block, reward
    
    def get_last_block(self, is_validated=False, do_not_return_self=False):
        # prntDebug('--get_last_block')
        if is_validated:
            block = Block.objects.filter(Blockchain_obj=self, validated=True).order_by('-index').first()
        else:
            block = Block.objects.filter(Blockchain_obj=self).exclude(validated=False).order_by('-index').first()
        if block:
            return block
        else:
            return None if do_not_return_self else self 


    def add_item_to_queue(self, post, force_add=False):
        prntDebug('--add_item_to_blockchain',self)
        # logEvent(f'additem to queue', code='375', func='add_item_to_queue', region=None, extra={'chainId':self.id,'post':str(post)[:500]})
        # previous commits are checked at creation time
        try:
            if post:
                err = '0'
                if not self.queuedData:
                    err = err + '1'
                    self.queuedData = {}
                def add_data(p):
                    # prntDebug('add_data')
                    if has_field(p, 'is_valid') and not p.is_valid:
                        return
                    to_commit = None
                    if p.object_type == 'Region' and has_field(p, 'ParentRegion_obj'):
                        # prntDebug('11')
                        if p.ParentRegion_obj and self.genesisId != p.ParentRegion_obj.id:
                            parentChain = Blockchain.objects.filter(genesisId=p.ParentRegion_obj.id).first()
                        elif not p.ParentRegion_obj:
                            parentChain = Blockchain.objects.filter(genesisType='Sonet').first()
                        else:
                            parentChain = None
                        # prntDebug('parentChain',parentChain)
                        if parentChain:
                            # if p.id == parentChain.genesisId:
                            #     to_commit = {'genesis':p.id}
                            # else:
                            to_commit = dt_to_string(now_utc())
                                # to_commit = get_commit_data(p)
                            parentChain.queuedData[p.id] = to_commit
                            if not parentChain.data_added_datetime:
                                parentChain.data_added_datetime = now_utc()
                            parentChain.save()
                    # if p.object_type == 'Region':
                    #     if self.genesisId != EarthChain_genesisId:
                    #         earthChain = Blockchain.objects.filter(genesisId=EarthChain_genesisId).first()
                    #         # earthChain.add_item_to_queue(p)
                    #         if p.id == earthChain.genesisId:
                    #             to_commit = {'genesis':p.id}
                    #         elif not to_commit:
                    #             to_commit = dt_to_string(now_utc())
                    #             # to_commit = get_commit_data(p)
                    #         earthChain.queuedData[p.id] = to_commit
                    #         earthChain.save()
                    if has_field(p, 'secondChainType'):
                        prnt('add to second chain')
                        firstChain, p, secondChain = find_or_create_chain_from_object(p)
                        if secondChain and secondChain != self:
                            prnt('-secondChain add_to',secondChain)
                            secondChain.add_item_to_queue(p)
                    if p.id not in self.queuedData:
                        # if p.id == self.genesisId: # all genesis objects are modifiable
                        #     to_commit = {'genesis':p.id}
                        # else:
                        to_commit = dt_to_string(now_utc())
                            # to_commit = get_commit_data(p)
                        self.queuedData[p.id] = to_commit
                        # prnt('added to chain queue',p)

                if not force_add and has_field(post, 'Block_obj') and post.Block_obj and post.Block_obj.Blockchain_obj == self and not has_field(post, 'is_modifiable'):
                    prntDebug('pass1', post.Block_obj.Blockchain_obj)
                    return False
                if isinstance(post, models.Model) and post.object_type == 'Node':
                    err = err + '2'
                    if post.activated_dt:
                        self.queuedData[post.id] = {'is_active':dt_to_string(post.activated_dt)}
                    else:
                        self.queuedData[post.id] = {'is_active':dt_to_string(post.last_updated)}
                    if not self.data_added_datetime:
                        self.data_added_datetime = now_utc()
                    self.save()
                    return True
                elif isinstance(post, list):
                    err = err + '3'
                    added = False
                    if not isinstance(post[0], models.Model):
                        err = err + '4'
                        post, not_found, not_valid = get_data(post, return_model=True)
                        err = err + '5'
                    for p in post:
                        if has_field(p, 'blockchainType') or has_field(p, 'blockchainId'):
                            added = True
                            add_data(p)
                    err = err + '6'
                    if added:
                        err = err + '7'
                        if not self.data_added_datetime:
                            self.data_added_datetime = now_utc()
                        self.save()
                    return added
                elif isinstance(post, dict):
                    err = err + '8'
                    added = False
                    post, not_found, not_valid = get_data(post, return_model=True)
                    err = err + '9'
                    for p in post:
                        if has_field(p, 'blockchainType') or has_field(p, 'blockchainId'):
                            added = True
                            add_data(p)
                        else:
                            prnt('skip',p)
                    err = err + '10'
                    if added:
                        if not self.data_added_datetime:
                            self.data_added_datetime = now_utc()
                        self.save()
                    return added
                elif has_field(post, 'blockchainType') or has_field(post, 'blockchainId'):
                    err = err + '11a'
                    add_data(post)
                    if not self.data_added_datetime:
                        self.data_added_datetime = now_utc()
                    self.save()
                    return True
        except Exception as e:
            logError(f'additem to queue {str(e)}', code='53254', func='add_item_to_queue', region=None, extra={'err':err,'chainId':self.id,'post':str(post)[:500]})
        return False


# many votes not validated
# many bill actions contain no text


class EventLog(models.Model):
    object_type = 'EventLog'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    type = models.CharField(max_length=90, default=None, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True, null=True)
    Node_obj = models.ForeignKey('blockchain.Node', blank=True, null=True, on_delete=models.CASCADE)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    publicKey = models.CharField(max_length=200, default="", blank=True)
    signature = models.CharField(max_length=200, default="", blank=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    
    def __str__(self):
        if self.Node_obj:
            return 'EventLog: %s/%s - %s'%(self.created, self.type, self.Node_obj.node_name)
        else:
            return 'EventLog: %s/%s - %s'%(self.created, self.type, self.Node_obj)
    
    class Meta:
        ordering = ["-created"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'EventLog', 'modelVersion': 1, 'id': '0', 'created': None, 'type': None, 'data': {}, 'Node_obj': None, 'Region_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False}
            # return {'object_type': 'EventLog', 'modelVersion': 1, 'id': '0', 'created': None, 'type': None, 'data': {}, 'Node_obj': None}
        
    def updateShare(self, obj): #not used
        if 'shareData' not in self.data:
            self.data['shareData'] = []
        if obj.id not in self.data['shareData']:
            self.data['shareData'].append(obj.id)
            self.save()
    
    def completed(self, fail=None):
        if fail:
            self.type = self.type.replace('process','failed').replace('scrape','failed')
            self.type = self.type + f"-{fail.replace('process','prcs')}"
        else:
            self.type = self.type.replace('process','completed').replace('scrape','completed')
        self.save()

    def save(self, *args, **kwargs):
        if self.id == '0':
            self.id = hash_obj_id(self)
        if not self.created:
            self.created = now_utc()
        if not self.Node_obj:
            self.Node_obj = get_self_node()
        self.type = self.type[:90]
        # prnt('self dict',model_to_dict(self))
        super(EventLog, self).save(*args, **kwargs)

class Tidy:

    def invalid_posts_run(self):
        prnt('invalid_posts_run')
        dt=now_utc()
        from posts.models import Post
        # num = 250
        invalid_posts = Post.all_objects.exclude(validated=True).filter(updated_on_node__lte=dt - datetime.timedelta(minutes=120)).order_by('updated_on_node').iterator(chunk_size=500)
        model_types = []
        delled = 0
        valled = 0
        skipped = 0
        runs = 0
        while invalid_posts and runs < 20:
            prnt('run',runs, invalid_posts)
            runs += 1
            for p in invalid_posts:
                # prnt('p',p)
                try:
                    if p.verify_is_valid(check_update=False):
                        p.validate()
                        valled += 1
                    else:
                        try:
                            obj = p.get_pointer()
                            if has_field(obj, 'created') and obj.created < dt - datetime.timedelta(days=3) or not obj.signature and has_field(obj, 'created') and obj.created < dt - datetime.timedelta(hours=8):
                                deleted = obj.delete()
                                delled += 1
                                m_type = get_pointer_type(p.pointerId)
                                if m_type not in model_types:
                                    model_types.append(m_type)
                            else:
                                skipped += 1
                        except Exception as e:
                            prnt('fail7534',p,str(e))
                            p.delete()
                            delled += 1
                            m_type = get_pointer_type(p.pointerId)
                            if m_type not in model_types:
                                model_types.append(m_type)
                except Exception as e:
                    print('invalid post run fail',str(e))
            prntDebug(f'run {runs} result, delled: {delled}, model_types:{model_types}, validated:{valled}, skipped:{skipped}')
            invalid_posts = Post.all_objects.exclude(validated=True).filter(updated_on_node__lte=dt - datetime.timedelta(minutes=120)).order_by('updated_on_node').iterator(chunk_size=500)
        r = f'removing posts, delled: {delled}, model_types:{model_types}, validated:{valled}, skipped:{skipped}'
        if delled or valled:
            logEvent(r, log_type='Tasks')
        prnt(r)
        return r

    def invalid_updates_run(self):
        dt=now_utc()
        from posts.models import Update
        # num = 250
        invalid_updates = Update.objects.exclude(validated=True).filter(updated_on_node__lte=dt - datetime.timedelta(minutes=120)).order_by('updated_on_node').iterator(chunk_size=500)
        model_types = []
        delled = 0
        valled = 0
        runs = 0
        while invalid_updates and runs < 20:
            runs += 1
            for u in invalid_updates:
                if u.verify_is_valid():
                    u.validate()
                    valled += 1
                elif u.created < dt - datetime.timedelta(days=3) or not u.signature and u.created < dt - datetime.timedelta(hours=8):
                    delled += 1
                    m_type = get_pointer_type(u.pointerId)
                    if m_type not in model_types:
                        model_types.append(m_type)
                    u.delete()
            invalid_updates = Update.objects.exclude(validated=True).filter(updated_on_node__lte=dt - datetime.timedelta(minutes=120)).order_by('updated_on_node').iterator(chunk_size=500)
        r = f'removing updates, delled: {delled}, model_types:{model_types}, validated:{valled}'
        if delled or valled:
            logEvent(r, log_type='Tasks')
        return r

    def unvalidator_run(self):
        prnt('unvalidator_run')
        dt=now_utc()
        # from utils.models import get_app_name, get_model
        del_chains = []
        for model_name, model_data in get_app_name(return_model_list=True).items():
            if model_name not in ['Post', 'Update', 'Notification']:
                prnt(model_name)
                model = get_model(model_name)
                if has_field(model, 'Validator_obj'):
                    time_field = get_timeData(model, sort='created', first_string=True)
                    objs = list(model.objects.filter(Validator_obj=None).filter(**{f'{time_field}__lte': dt - datetime.timedelta(hours=4)}).iterator(chunk_size=200))
                    exclude_idens = set()
                    delled = 0
                    item_tracker = []
                    skipped = 0
                    validated = 0
                    runs = 0
                    val_count = 0
                    while objs and runs < 20:
                        runs += 1
                        unvalled_obj_count = 0
                        for i in objs:
                            unvalled_obj_count += 1
                        item_tracker.append(unvalled_obj_count)
                        # query = Q()
                        # for key in [obj.id for obj in objs]:
                        #     query |= Q(data__has_key=key)
                        # vals = Validator.objects.filter(is_valid=True).filter(query).order_by('-created')
                        # prnt('vals',vals)
                        vals = Validator.objects.filter(is_valid=True, data__has_any_keys=[i.id for i in objs]).order_by('-created')
                        val_count += len(vals)
                        if vals:
                            val_map = {obj: val for val in vals for obj in val.data.keys()}
                            for obj in objs:
                                # creator_nodes, validator_nodes = get_scraping_order(dt=obj.created, chainId=obj.blockchainId, func_name=obj.func)
                                creator_nodes, validator_nodes = get_node_assignment(dt=obj.created, chainId=obj.blockchainId, func_name=obj.func)
                                val_found = False
                                val = val_map.get(obj.id)
                                if val and val.CreatorNode_obj.id in validator_nodes and obj.id in val.data:
                                    if validate_obj(obj=None, pointer=obj, validator=val, node_block_data={}):
                                    # if val.data[obj.id] == sigData_to_hash(obj):
                                        validated += 1
                                        val_found = True
                                        # obj.Validator_obj = val
                                        # super(get_model(obj.object_type), obj).save()
                                        # blockchain, obj, secondChain = find_or_create_chain_from_object(obj)
                                        # if blockchain:
                                        #     blockchain.add_item_to_queue(obj)
                                if not val_found and getattr(obj, time_field) < dt - datetime.timedelta(hours=36) or not obj.signature and has_field(obj, 'created') and obj.created < dt - datetime.timedelta(hours=8):
                                    if obj.object_type == obj.blockchainType:
                                        del_chains.append(obj.id)
                                    if obj.id not in exclude_idens:
                                        exclude_idens.add(obj.id)
                                    obj.delete()
                                    delled += 1
                                else:
                                    skipped += 1
                                    if obj.id not in exclude_idens:
                                        exclude_idens.add(obj.id)
                        else:
                            for obj in objs:
                                if getattr(obj, time_field) < dt - datetime.timedelta(hours=36) or not obj.signature and has_field(obj, 'created') and obj.created < dt - datetime.timedelta(hours=8):
                                    if obj.object_type == obj.blockchainType:
                                        del_chains.append(obj.id)
                                    if obj.id not in exclude_idens:
                                        exclude_idens.add(obj.id)
                                    obj.delete()
                                    delled += 1
                                else:
                                    skipped += 1
                                    if obj.id not in exclude_idens:
                                        exclude_idens.add(obj.id)
                        objs = list(model.objects.filter(Validator_obj=None).exclude(id__in=exclude_idens).filter(**{f'{time_field}__lte': dt - datetime.timedelta(hours=4)}).iterator(chunk_size=200))
                    r = f'unvalidator_run {model_name}, item_tracker:{item_tracker} validated:{validated} delled:{delled} skipped:{skipped} val_count:{val_count} runs:{runs}'
                    if validated or delled or skipped:
                        logEvent(r, log_type='Tasks')
                    prnt(r)

        if del_chains:
            prnt('del_chains',del_chains)
            logEvent(f'removing chains:{del_chains}', log_type='Tasks')
            chains = Blockchain.objects.filter(genesisId__in=del_chains)
            if chains:
                for c in chains:
                    if not c.get_genesis_pointer():
                        prnt('chain deletion 432',c)
                        super(Blockchain, c).delete()
        
    
    def invalid_notifications_run(self):
        from accounts.models import Notification
        dt=now_utc()
        invalid_notifications = Notification.objects.exclude(validated=True).filter(updated_on_node__lte=dt - datetime.timedelta(minutes=120))
        if invalid_notifications:
            model_types = []
            delled = 0
            valled = 0
            for n in invalid_notifications:
                if n.verify_is_valid():
                    n.validate()
                    valled += 1
                elif n.created < dt - datetime.timedelta(days=3) or not n.signature and has_field(n, 'created') and n.created < dt - datetime.timedelta(hours=8):
                    delled += 1
                    m_type = get_pointer_type(n.pointerId)
                    if m_type not in model_types:
                        model_types.append(m_type)
                    n.delete()
            r = f'removing notifications, count: {delled}, model_types:{model_types}, validated:{valled}'
            if delled or valled:
                logEvent(r, log_type='Tasks')
            return r

    def uncommitted_posts_run(self, hours=8):
        prnt('uncommitted_posts_run', hours)
        dt=now_utc()
        # from utils.models import get_model
        def run_me(model_name):
            model = get_model(model_name)
            if model_name == 'Post':
                uncommitted_posts = list(model.objects.filter(blockId=None, created__lte=dt - datetime.timedelta(hours=hours)).iterator(chunk_size=500))
            elif model_name == 'Update':
                uncommitted_posts = list(model.objects.filter(Block_obj=None, validated=True, created__lte=dt - datetime.timedelta(hours=hours)).iterator(chunk_size=500))
            else:
                uncommitted_posts = list(model.objects.filter(Block_obj=None, created__lte=dt - datetime.timedelta(hours=hours)).iterator(chunk_size=500))
            runs = 0
            exclude_idens = set()
            while uncommitted_posts and runs < 20:
                runs += 1
            # if uncommitted_posts:
                prnt('has uncommitted_posts')
                logEvent(f'uncommitted_posts, model_name:{model_name} run:{runs}', log_type='Tasks')
                obj_idens = []
                has_block = {}
                add_to_queue = {}
                run_posts = []
                for p in uncommitted_posts:
                    exclude_idens.add(p.id)
                    run_posts.append(p)
                    if p.object_type == 'Post':
                        obj_idens.append(p.pointerId)
                    else:
                        obj_idens.append(p.id)
                    # if p.Update_obj:
                    #     obj_idens.append(p.Update_obj.id)
                prntDebug('obj_idens',obj_idens)
                if obj_idens:
                    in_queue = Blockchain.objects.filter(queuedData__has_any_keys=obj_idens)
                else:
                    in_queue = None
                if in_queue:
                    for c in in_queue:
                        for key in c.queuedData:
                            if key in obj_idens:
                                obj_idens.remove(key)
                                prntDebug('rmv1', key)
                            if not obj_idens:
                                break
                if obj_idens:
                    existing_blocks = Block.objects.filter(data__has_any_keys=obj_idens).exclude(validated=False)
                    for b in existing_blocks:
                        for key in obj_idens:
                            if key in b.data:
                                obj_idens.remove(key)
                                has_block[key] = b
                                prntDebug('rmv2', key)
                            if not obj_idens:
                                break
                if has_block:
                    prnt('has has_block')
                else:
                    prnt('no beat')
                for p in run_posts:
                    prnt(p)
                    if p.object_type == 'Post':
                        obj_iden = p.pointerId
                    else:
                        obj_iden = p.id
                    if obj_iden in has_block:
                        # or has_field(p, 'Update_obj') and p.Update_obj and p.Update_obj.id in has_block:
                        prnt('opt1')
                        # if p.pointerId in has_block:
                        if has_field(p, 'blockId'):
                            p.blockId = has_block[obj_iden].id
                            p.save()
                            pointer = p.get_pointer()
                            if has_field(pointer,'Block_obj') and not pointer.Block_obj:
                                if has_block[p.pointerId][p.pointerId] == get_commit_data(pointer):
                                    pointer.Block_obj = has_block[p.pointerId]
                                    super(get_model(pointer.object_type), pointer).save()
                        elif has_field(p, 'Block_obj') and not p.Block_obj:
                            if has_block[p.id][p.id] == get_commit_data(p):
                                p.Block_obj = has_block[p.id]
                                super(get_model(p.object_type), p).save()

                        # if p.Update_obj and has_field(p.Update_obj,'Block_obj') and not p.Update_obj.Block_obj:
                        #     p.Update_obj.Block_obj = has_block[p.Update_obj.id]
                        #     super(get_model(pointer.object_type), pointer).save()
                
                    elif obj_iden in obj_idens:
                        prnt('opt2')
                        if p.object_type == 'Post':
                            pointer = p.get_pointer()
                        else:
                            pointer = p
                        # if has_field(pointer, 'Block_obj') and pointer.Block_obj:
                        #     pointer.Block_obj = None
                        #     super(get_model(pointer.object_type), pointer).save()

                        find_chain = True
                        if has_field(pointer, 'created'):
                            if pointer.created < dt - datetime.timedelta(days=max_commit_window):
                                # if post is valid, invalidate
                                if p.validated:
                                    p.validated = False
                                    p.save()
                                find_chain = False
                                ...
                            elif pointer.created < dt - datetime.timedelta(days=2):
                                dataPacket = get_latest_dataPacket(pointer)
                                dataPacket.add_item_to_share(pointer)
                        if find_chain:
                            blockchain, obj, secondChain = find_or_create_chain_from_object(pointer)
                            prntDebug('blockchain',blockchain)
                            if blockchain:
                                if blockchain not in add_to_queue:
                                    add_to_queue[blockchain] = []
                                add_to_queue[blockchain].append(pointer)
                            elif has_field(p, 'blockId') and has_field(pointer, 'proposed_modification') and not pointer.proposed_modification:
                                p.blockId = 'N/A'
                                p.save()
                    # elif p.Update_obj and p.Update_obj.id in obj_idens:
                    #     # prnt('opt3')
                    #     blockchain, obj, secondChain = find_or_create_chain_from_object(p.Update_obj)
                    #     if blockchain:
                    #         if blockchain not in add_to_queue:
                    #             add_to_queue[blockchain] = []
                    #         add_to_queue[blockchain].append(p.Update_obj)

                if add_to_queue:
                    prnt('has add_to_queue')
                    for chain, idens in add_to_queue.items():
                        chain.add_item_to_queue(idens)

                if model_name == 'Post':
                    uncommitted_posts = list(model.objects.exclude(id__in=exclude_idens).filter(blockId=None, created__lte=dt - datetime.timedelta(hours=hours)).iterator(chunk_size=500))
                elif model_name == 'Update':
                    uncommitted_posts = list(model.objects.exclude(id__in=exclude_idens).filter(Block_obj=None, validated=True, created__lte=dt - datetime.timedelta(hours=hours)).iterator(chunk_size=500))
                else:
                    uncommitted_posts = list(model.objects.exclude(id__in=exclude_idens).filter(Block_obj=None, created__lte=dt - datetime.timedelta(hours=hours)).iterator(chunk_size=500))

        run_me('Post')
        run_me('Update')

    def get_missing_items(self, dt=now_utc()):
        self_node = get_self_node()
        
        start_of_month = round_time(dt=dt, dir='down', amount='month')
        logs = EventLog.objects.filter(type='missing_items', Node_obj=self_node, created__gte=start_of_month).exclude(data={})
        for log in logs:
            save_log = False
            result = request_items(requested_items=[key for key in log.data], nodes=None, return_updated_ids=True, return_missing=True, downstream_worker=False) # should get nodes by region if applicable
            prnt(f'received missing idens for {log.id}:', str(result)[:100])
            if result and isinstance(result, dict):
                if 'found' in result and isinstance(result['found'], list):
                    for i in result['found']:
                        prnt('i',i)
                        if i in log.data:
                            del log.data[i]
                            save_log = True
                if 'not found' in result and isinstance(result['not found'], list):
                    if result['not found']:
                        for i in result['not found']:
                            if i in log.data:
                                del log.data[i]
                                save_log = True

            if save_log:
                log.save()

    def prune_validator_objs(self, dt=now_utc()):
        # blocks are removed when invalid, validators for those should be removed after a time
        pass

    def rotate_logs(self):
        prnt('rotate_logs')
        import os
        import shutil

        LOG_DIR = os.path.expanduser("~/Sonet/.data/logs")
        # LOG_FILE = "gunicorn.log"
        MAX_LOGS = 10
        MAX_SIZE_MB = 5  # rotate if gunicorn.log exceeds this size

        rotate_me = ["gunicorn.log", "gunicorn_err.log", "nginx.log", "nginx_err.log", "rqscheduler.log", "supervisor.log", "supervisord.log", "supervisor.err"]
        for LOG_FILE in rotate_me:
            prnt('LOG_FILE',LOG_FILE)
            log_path = os.path.join(LOG_DIR, LOG_FILE)
            
            # Only rotate if the log file exists and is too large
            if not os.path.exists(log_path):
                prnt("Log file does not exist.")
                return
            
            if os.path.getsize(log_path) < MAX_SIZE_MB * 1024 * 1024:
                prnt("Log file is not large enough to rotate.")
                return

            # Delete the oldest log if it exists
            oldest = os.path.join(LOG_DIR, f"{LOG_FILE}.{MAX_LOGS}")
            if os.path.exists(oldest):
                os.remove(oldest)

            # Shift all logs down by one
            for i in range(MAX_LOGS - 1, 0, -1):
                src = os.path.join(LOG_DIR, f"{LOG_FILE}.{i}")
                dst = os.path.join(LOG_DIR, f"{LOG_FILE}.{i+1}")
                if os.path.exists(src):
                    os.rename(src, dst)

            # Rename current log to .1
            rotated = os.path.join(LOG_DIR, f"{LOG_FILE}.1")
            shutil.move(log_path, rotated)

            # Create a new empty log file (optional: match owner/permissions)
            open(log_path, "a").close()

            prnt(f"Rotated {log_path} to {rotated}")


    # check harddrive still has space
    # clean up logs (EventLogs and ~/Sonet/.data/logs)
    # remove old datapackets
    

    def _add_all_jobs(self, dt=now_utc(), *args, **kwargs):
        logEvent(f'tidying', log_type='Tasks')
        prnt('tidying')

        for block in Block.objects.filter(validated=False, created__lt=dt - datetime.timedelta(days=3)):
            block.delete()
        
        for block in Block.objects.filter(validated__isnull=True, DateTime__lt=dt - datetime.timedelta(days=1)):
            block.is_not_valid(mark_strike=False, note='day_old')

        # maybe once randomly per week?
        # from utils.models import run_database_maintenance
        #     queue = django_rq.get_queue('main')
        #     queue.enqueue(run_database_maintenance)

        import inspect
        if dt.hour == 9:
            # from utils.cronjobs import clear_jold_obs
            try:
                queue = django_rq.get_queue('low')
                queue.enqueue(clear_jold_obs, job_timeout=20)
            except Exception as e:
                prnt('fail58394', str(e))
            methods = [method for name, method in inspect.getmembers(self, predicate=inspect.ismethod) if not name.startswith('_')]
        else:
            skip_jobs = ['uncommitted_posts_run']
            methods = [method for name, method in inspect.getmembers(self, predicate=inspect.ismethod) if not name.startswith('_') and not name in skip_jobs]

        random.shuffle(methods)
        # prnt('tidying methods',methods)
        queue = django_rq.get_queue('low')
        for method in methods:
            # create_job(method, job_timeout=300, worker=queue)
            queue.enqueue(method, job_timeout=600, result_ttl=3600)



# run update.sync_to_post on lois
# cors not yet wokring from court to lois 
# cors did work from lois to court

# # Add to the top of your views.py
# from django.core.cache import cache
# from django.http import HttpResponse
# import time
# potentially store keys or ids instead of using get_operatorData() so often
# def rate_limit(request, limit=60, period=60):
#     """Limit requests to 'limit' per 'period' seconds per IP"""
#     client_ip = get_client_ip(request)
#     cache_key = f"rate_limit:{client_ip}"
    
#     # Get current request count
#     request_history = cache.get(cache_key, [])
#     now = time.time()
    
#     # Filter out old requests
#     request_history = [t for t in request_history if now - t < period]
    
#     # Check if limit exceeded
#     if len(request_history) >= limit:
#         return False
        
#     # Add current request time and update cache
#     request_history.append(now)
#     cache.set(cache_key, request_history, period)
#     return True

# # Then in your view:
# @csrf_exempt
# def receive_data_view(request):
#     if not rate_limit(request, limit=100, period=60):
#         return JsonResponse({'message': 'Rate limit exceeded'}, status=429)

def logEvent(details, code=None, region=None, func=None, extra=None, log_type='LogBook', dt='week'):
    # from utils.models import timezonify
    now = now_utc()
    if dt and dt == 'week':
        start_time = round_time(dt=now, dir='down', amount='week')
    elif dt and isinstance(dt, datetime.datetime):
        start_time = dt
    else:
        start_time = now
    log = EventLog.objects.filter(type=log_type, created__gte=start_time).first()
    if not log:
        log = EventLog(type=log_type, created=start_time)
    event = {'~':str(details)}
    if func:
        event['func'] = func
    if code:
        event['code'] = code
    if region:
        if isinstance(region, models.Model):
            region = region.Name
        elif not isinstance(region, str):
            region = str(region)
        event['reg'] = region
    if extra:
        if not isinstance(extra, str):
            extra = str(extra)
        event['extra'] = extra
    log.data[dt_to_string(now)] = event
    # log.data[timezonify('est', now).isoformat()] = event
    log.save()

def logTask(task, code=None, region=None, extra=None):
    # prnt('logError', err, code, func, region, extra)
    now = now_utc()
    start_of_week = round_time(dt=now, dir='down', amount='week')
    log = EventLog.objects.filter(type='Tasks', created__gte=start_of_week).first()
    if not log:
        log = EventLog(type='Tasks', created=start_of_week)
    event = {'task':str(task)}
    if code:
        event['code'] = code
    if region:
        if isinstance(region, models.Model):
            region = region.Name
        elif not isinstance(region, str):
            region = str(region)
        event['reg'] = region
    if extra:
        if not isinstance(extra, str):
            extra = str(extra)
        event['extra'] = extra
    log.data[dt_to_string(now)] = event
    # log.data[timezonify('est', now).isoformat()] = event
    log.save()

def logError(err, code=None, func=None, region=None, extra=None):
    # prnt('logError', err, code, func, region, extra)
    now = now_utc()
    start_of_week = round_time(dt=now, dir='down', amount='week')
    log = EventLog.objects.filter(type='Errors', created__gte=start_of_week).first()
    if not log:
        log = EventLog(type='Errors', created=start_of_week)
    event = {'err':str(err)}
    if func:
        event['func'] = func
    if code:
        event['code'] = code
    if region:
        if isinstance(region, models.Model):
            region = region.Name
        elif not isinstance(region, str):
            region = str(region)
        event['reg'] = region
    if extra:
        if not isinstance(extra, str):
            extra = str(extra)
        event['extra'] = extra
    log.data[dt_to_string(now)] = event
    # log.data[timezonify('est', now).isoformat()] = event
    log.save()

def logRequest(items, return_log=False, dt='week'):
    logEvent(f'request_items:{items}')
    now = now_utc()
    start_of_week = round_time(dt=now, dir='down', amount=dt)
    log = EventLog.objects.filter(type='RequestedItems', created__gte=start_of_week).first()
    if not log:
        log = EventLog(type='RequestedItems', created=start_of_week)
    log.data[dt_to_string(now)] = items
    log.save()
    if return_log:
        return log

def logMissing(iden, reg=None, context={}):
    self_node = get_self_node()
    now = now_utc()
    start_of_month = round_time(dt=now, dir='down', amount='month')
    if reg and is_id(reg):
        from posts.models import Region
        reg = Region.objects.filter(id=reg).first()
    elif reg and not isinstance(reg, models.Model) or reg and reg.object_type != 'Region':
        reg = None

    log = EventLog.objects.filter(type='missing_items', Node_obj=self_node, Region_obj=reg, created__gte=start_of_month).first()
    if not log:
        log = EventLog(type='missing_items', Node_obj=self_node, Region_obj=reg, created=start_of_month)

    if isinstance(iden, list):
        for i in iden:
            if i not in log.data:
                log.data[i] = context
    elif isinstance(iden, str):
        if iden not in log.data:
            log.data[iden] = context

    log.save()

def logBroadcast(return_log=True):
    now = now_utc()
    start_of_week = round_time(dt=now, dir='down', amount='week')
    log = EventLog.objects.filter(type='Broadcast History', created__gte=start_of_week).first()
    if not log:
        log = EventLog(type='Broadcast History', created=start_of_week)
    return log
    
def toBroadcast(obj, remove_item=False, extra={}):
    if not is_id(obj):
        if isinstance(obj, models.Model):
            obj = obj.id
    now = now_utc()
    if remove_item:
        log = EventLog.objects.filter(type='toBroadcast', data__icontains=obj).first()
        if log:
            del log.data[obj]
            if not log.data:
                log.delete()
            else:
                log.save()
    else:
        start_of_week = round_time(dt=now, dir='down', amount='week')
        log = EventLog.objects.filter(type='toBroadcast', created__gte=start_of_week).first()
        if not log:
            log = EventLog(type='toBroadcast', created=start_of_week)
        if obj not in log.data:
            extra['dt'] = dt_to_string(now)
            log.data[obj] = extra
        log.save()


# mark block valid needs to invalidate problem idens ?? maybe not

# validater needs block_obj and is_locked function, check for locked in validation jobs
# add block to validater.block_obj when block marked valid, both vals in data and in block.validators
# block_obj field should be protected
# check max_winddow on all validations and block.commts is being used

# move some functions to utils.locked like validate_block, maybe check_contents and check _consensus

# move transaction models to new transactions app
# in prcs_rcvd_data if incoming obj has blocck_obj, check data against block

# def data_sort_priority(entry, version=None):
#     type_order = {'type1': 0, 'type2': 1}
#     if isinstance(entry, dict):
#         type_priority = type_order.get(entry.get('object_type', ''), float('inf'))
#         datetime_keys = ['created', 'last_updated']
#         datetime_priority = next(
#             (entry[key] for key in datetime_keys if key in entry and entry[key] is not None),
#             float('inf')  # Fallback for missing datetime values
#         )
#     elif is_id(entry):
#         type_priority = type_order.get(get_pointer_type(entry), float('inf'))
#         datetime_priority = 'inf'
#     elif isinstance(entry, list):
#         from posts.models import get_app_name
#         result = sorted(entry, key=lambda x: type_order.get(get_app_name(model_name=x, am_i_model=True), float('inf')))
#         datetime_priority = 'inf'
#         return result
#     return (type_priority, datetime_priority)




def request_items(requested_items=None, nodes=None, request_validators=False, return_updated_count=False, return_updated_objs=False, return_updated_ids=False, return_missing=False, downstream_worker=True):
    prntDebug('--request_items now_utc:',now_utc(), len(requested_items), str(requested_items)[:500], 'nodes',nodes)
    # prnt("A00")
    logRequest(requested_items, return_log=False, dt='week')
    # prnt("A")
    operatorData = get_operatorData()
    # prnt("B")
    # if 'syncingDB' in operatorData and operatorData['syncingDB'] != False:
    #     prnt("C")
    #     try:
    #         sync_dt = string_to_dt(operatorData['syncingDB'])
    #         prnt("sync_dt",sync_dt_to_string(dt))
    #         prnt("now_utc()",dt_to_string(now_utc()))
    #         if sync_dt < now_utc() - datetime.timedelta(hours=2):
    #             prnt('yes2')
    #         else:
    #             prnt('no2')
    #     except Exception as e:
    #         prnt('fail345',str(e))
    #         sync_dt = None
    #         prnt("sync_dt",sync_dt)
    #     prnt("D")
    #     if not sync_dt or sync_dt < now_utc() - datetime.timedelta(hours=2):
    #         prnt("E")
    #         operatorData['syncingDB'] = False
    #         write_operatorData(operatorData)
    #     else:
    #         prnt("F")
    #         return
    # prnt("G")
    if not nodes:
        prnt("H")
        # get appropriate nodes for requesed_items
        nodes = Node.objects.exclude(activated_dt=None).filter(suspended_dt=None)
    elif isinstance(nodes, list) and isinstance(nodes[0], str):
        prnt("I")
        nodes = Node.objects.filter(id__in=nodes, suspended_dt=None).exclude(activated_dt=None)
    elif isinstance(nodes, str) and is_id(nodes):
        prnt("J")
        nodes = Node.objects.filter(id=nodes, suspended_dt=None).exclude(activated_dt=None)
    prnt('0')
    from django.db.models.query import QuerySet
    if isinstance(nodes, QuerySet):
        nodes = list(nodes)

    def fetch_data(data, nodes, output=None, target_node=None, starting_index=0):
        prnt('\nfetch_data',now_utc(),'nodes',nodes,'target_node:',target_node, 'data',str(data)[:500])
        if target_node: 
            nodes.remove(target_node)
            nodes.insert(0, target_node)
        nonlocal return_updated_count
        nonlocal return_updated_objs
        nonlocal return_updated_ids
        nonlocal self_node
        returned_update = False
        for node in nodes:
            prnt('fetch node',node)
            if node != self_node and node != self_node.id:
                try:
                    success, response = connect_to_node(node, 'blockchain/request_data', data=data, operatorData=operatorData, timeout=(7,25), stream=True, log_reponse_time=False)
                    if success and response.status_code == 200:
                        received_json = response.json()
                        # prnt('received_json',received_json)
                        if received_json['message'].lower() == 'success':
                            if 'returning_idens' in received_json:
                                returned_idens = received_json['returning_idens']
                            else:
                                returned_idens = None
                            if 'not_found' in received_json:
                                not_found_idens = received_json['not_found']
                            else:
                                not_found_idens = []
                            if received_json['type'] == 'Blockchain':
                                blockchain_dict = json.loads(received_json['blockchain_obj'])
                                update_response = process_received_data(received_json['content'], return_updated_count=return_updated_count, return_updated_objs=return_updated_objs, return_updated_ids=return_updated_ids, downstream_worker=downstream_worker, force_sync=True)
                                logEvent('request_items result', code='61459', extra={'update_response_len':len(update_response),'update_response':str(update_response)[:1000]})
                            elif received_json['type'] == 'Block':
                                block_dict = json.loads(received_json['block_obj'])
                                content = [block_dict]
                                if 'transaction_obj' in received_json and received_json['transaction_obj']:
                                    content.append(json.loads(received_json['transaction_obj']))
                                index = block_dict['index']
                                update_response = process_received_data(received_json['content'], return_updated_count=return_updated_count, return_updated_objs=return_updated_objs, return_updated_ids=return_updated_ids, downstream_worker=downstream_worker, force_sync=True)
                                logEvent('request_items result', code='49292', extra={'update_response_len':len(update_response),'update_response':str(update_response)[:1000]})
                            else:
                                try:
                                    index = int(received_json['index'])
                                except:
                                    index = 'NA'
                                update_response = process_received_data(received_json['content'], return_updated_count=return_updated_count, return_updated_objs=return_updated_objs, return_updated_ids=return_updated_ids, downstream_worker=downstream_worker, force_sync=True)
                                if index != 'NA' and index != starting_index:
                                    time.sleep(2)
                                    json_data = json.loads(data['request'])
                                    if returned_idens:
                                        obj_types = {}
                                        for obj_type in json_data['items']:
                                            again_idens = [i for i in json_data['items'][obj_type] if i not in returned_idens]
                                            if not_found_idens:
                                                not_found_idens = [i for i in not_found_idens if i not in returned_idens]
                                            if again_idens:
                                                obj_types[obj_type] = again_idens
                                        json_data['items'] = obj_types
                                        json_data['exclude'] = returned_idens
                                    else:
                                        json_data['index'] = index
                                    logEvent('request_items result', code='0863', extra={'returned_idens':returned_idens,'index':index,'update_response_len':len(update_response),'update_response':str(update_response)[:1000]})
                                    json_data['dt'] = dt_to_string(now_utc())
                                    signedRequest = json.dumps(sign_for_sending(json_data))
                                    data['request'] = signedRequest
                                    returned_update = fetch_data(data, nodes, output=output, target_node=node, starting_index=index)
                                else:
                                    logEvent('request_items result', code='98284', extra={'returned_idens':returned_idens,'update_response_len':len(update_response),'update_response':str(update_response)[:1000]})
                            prnt('ending festch and process')
                            if isinstance(update_response, int) and isinstance(returned_update, int):
                                r = update_response + returned_update
                            elif isinstance(update_response, list) and isinstance(returned_update, list):
                                r = update_response + returned_update
                            else:
                                r = update_response or returned_update
                            if return_missing:
                                return {'found': r, 'not_found':not_found_idens}
                            else:
                                return r
                        else:
                            prnt('fetch data success = False')
                            logError('fetch data not successful 1', code='853')
                            prnt('received_json 853',received_json)
                    else:
                        prnt('fetch data not successful')
                        logError('fetch data not successful 2', code='5424')
                        prnt('received_json 5424',received_json)
                except Exception as e:
                    prnt('fetch data err',str(e))
                    logError('fetch data not successful 3', code='9745', extra={'err':str(e)})
    
    self_node = get_self_node(operatorData=operatorData)
    prnt('sef_nod',self_node)
    if isinstance(requested_items, list):
        # prnt('1')
        requested_items = data_sort_priority(requested_items)
    else:
        # prnt('2')
        requested_items = sorted(requested_items, key=data_sort_priority)
    prnt('3, ',requested_items)
    userData = json.dumps(sign_obj(operatorData['userData']))
    upkData = json.dumps(sign_obj(operatorData['upkData']))
    selfNode = json.dumps(sign_obj(convert_to_dict(self_node)))
    prnt('4')
    from blockchain.views import max_obj_send_count
    if len(requested_items) <= max_obj_send_count:
        obj_types = {}
        for i in requested_items:
            objType = get_pointer_type(i)
            if objType in obj_types:
                obj_types[objType].append(i)
            else:
                obj_types[objType] = [i]
        if request_validators:
            request_type = 'Validators_only'
        else:
            request_type = 'multi'
        signedRequest = json.dumps(sign_for_sending({'type':request_type,'items' : obj_types, 'index' : 0,'dt':dt_to_string(now_utc())}))
        data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
        result = fetch_data(data, nodes)
        return result
    else:
        prnt('request items path 1')
        obj_types = {}
        for i in requested_items:
            objType = get_pointer_type(i)
            if objType in obj_types:
                obj_types[objType].append(i)
            else:
                obj_types[objType] = [i]
        if return_updated_count:
            result = 0
        elif return_updated_objs or return_updated_ids:
            result = []
        else:
            result = False
        for obj_type, iden_list in obj_types.items():
            if request_validators:
                request_type = 'Validators_only'
            else:
                request_type = obj_type
            if len(iden_list) <= max_obj_send_count:
                prnt('request items path 12')
                signedRequest = json.dumps(sign_for_sending({'type':request_type,'items' : iden_list, 'index' : 0,'dt':dt_to_string(now_utc())}))
                data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
                resp = fetch_data(data, nodes)
                if resp:
                    if isinstance(resp, int) or isinstance(resp, list):
                        if not result:
                            result = resp
                        else:
                            result = result + resp
                    else:
                        result = True
                time.sleep(1)
            else:
                prnt('request items path 13')
                def process_in_chunks(request_type, items, chunk_size):
                    result = False
                    for i in range(0, len(items), chunk_size):
                        chunk = items[i:i + chunk_size]
                        signedRequest = json.dumps(sign_for_sending({'type':request_type,'items' : chunk, 'index' : 0,'dt':dt_to_string(now_utc())}))
                        data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
                        resp = fetch_data(data, nodes)
                        if resp:
                            if isinstance(resp, int) or isinstance(resp, list):
                                if not result:
                                    result = resp
                                else:
                                    result = result + resp
                            else:
                                result = True
                        time.sleep(1)
                    return result

                resp = process_in_chunks(request_type, iden_list, max_obj_send_count)
                if resp:
                    if isinstance(resp, int) or isinstance(resp, list):
                        if not result:
                            result = resp
                        else:
                            result = result + resp
                    else:
                        result = True
        return result



def get_relevant_nodes_from_block_old(dt=None, genesisId=None, chains=None, blockchain=None, ai_capable=False, firebase_capable=False, exclude_list=[], obj=None, node_block=None, strings_only=False, sublist='scripts'):
    prnt('--get nodes from node block list - strings_only:',strings_only,'genesisId',genesisId,'blockchain',blockchain,'chains',chains,'obj',obj,'dt',dt,'exclude_list',exclude_list)
    if not dt and obj:
        dt = get_timeData(obj, sort='updated')
    elif not dt:
        dt = now_utc()
    
    if obj and has_field(obj, 'object_type') and obj.object_type == 'Block' and obj.blockchainType == 'Nodes':
        # NodeChain block assignments use the node block in question (datetime is 10mins ahead of creation time, allowing for propagation of block before it begins use)
        # eveything else uses block assigned to its datetime
        # node blocks must be done by currently active nodes, ie. if a node deactivates, it can't be assigned to validate the next node block
        node_block = obj
        # prnt('received node_block')
    else:
        if not node_block and not testing():
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
        if genesisId and genesisId in mandatoryChains or get_pointer_type(genesisId) in mandatoryChains or get_chain_type(genesisId) in mandatoryChains:
            prnt('op1')
            prnt("node_block.data['All']",node_block.data['All'])
            node_ids = [n for n in node_block.data['All'] if n not in exclude_list]
            prnt('node_idsA',node_ids)
            if strings_only and 'addresses' in node_block.notes:
                prnt('path1')
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                prnt('path12')
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                prnt('path13')
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
            prnt('relevant_nodesA',relevant_nodes)

        elif genesisId or blockchain:
            prnt('is gen or bchain')
            if not blockchain and get_pointer_type(genesisId) == 'Blockchain':
                # prnt('11')
                blockchain = Blockchain.objects.filter(id=genesisId).first()
            elif is_id(blockchain):
                # prnt('1122')
                blockchain = Blockchain.objects.filter(id=blockchain).first()
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
            # else:
            #     node_ids = []
            
            if strings_only and 'addresses' in node_block.notes:
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
        elif chains:
            prnt('is chains')
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
            prnt('node_ids',node_ids)
            if strings_only and 'addresses' in node_block.notes:
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
            prnt('done is chains')
        else:
            prnt('else')
            node_ids = [n for n in node_block.data['All'] if n not in exclude_list]
            if strings_only and 'addresses' in node_block.notes:
                relevant_nodes = {iden:node_block.notes['addresses'][iden] for iden in node_ids}
            elif strings_only:
                relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
            else:
                relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
        if node_block.number_of_peers > len(node_ids):
            peers_count = len(node_ids)
        else:
            peers_count = node_block.number_of_peers
        prnt('1 node_ids',node_ids, 'peers_count',peers_count, 'relevant_nodes',relevant_nodes)
        return node_ids, peers_count, dict(sorted(relevant_nodes.items()))
    else:
        all_nodes = Node.objects.all().order_by('created')[:1]
        node_ids = [n.id for n in all_nodes if n.id not in exclude_list]
        if strings_only:
            relevant_nodes = {n.id:n.return_address() for n in Node.objects.filter(id__in=node_ids)}
        else:
            relevant_nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
        
        if number_of_peers > len(node_ids):
            peers_count = len(node_ids)
        else:
            peers_count = number_of_peers
        prnt('2 node_ids',node_ids, 'number_of_peers',number_of_peers, 'relevant_nodes',relevant_nodes)
        return node_ids, number_of_peers, dict(sorted(relevant_nodes.items()))

def get_node_assignment_old(obj, creator_only=False, dt=None, func=None, chainId=None, scrapers_only=False, sender_transaction=False, full_validator_list=False, strings_only=False, get_stragglers=True, node_block_data={}):
    prnt('\n------get_node_assignment obj:', obj, 'func',func, 'strings:', strings_only,'chainId',chainId,'creator_only',creator_only,'scrapers_only',scrapers_only,'node_block_data',node_block_data,'sender_transaction',sender_transaction)

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

            number_of_peers = node_dict['number_of_peers']
            relevant_nodes = node_dict['relevant_nodes']
            node_ids = node_dict['node_ids']
            valid_node_ids_received = True
        except Exception as e:
            prnt('fail4782674',str(e))
            pass

    if obj and obj.object_type == 'Block' or obj and obj.object_type == 'UserTransaction':
        if obj.Transaction_obj:
            prnt('obj.Transaction_obj',obj.Transaction_obj)
            prnt('obj.Transaction_obj.regarding',obj.Transaction_obj.regarding)
            if 'BlockReward' in obj.Transaction_obj.regarding:
                prnt('yes1')
            if obj.Transaction_obj.regarding['BlockReward'] == obj.id:
                prnt('yes2')

        if obj.object_type == 'Block' and not obj.Transaction_obj or obj.object_type == 'Block' and 'BlockReward' in obj.Transaction_obj.regarding and obj.Transaction_obj.regarding['BlockReward'] == obj.id:
            chain_list = [obj.Blockchain_obj.genesisId]
            # prnt('valid_node_ids_received',valid_node_ids_received)
            if not valid_node_ids_received:
                node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=obj.DateTime, obj=obj, genesisId=obj.Blockchain_obj.genesisId, strings_only=strings_only)
            
            date_int = date_to_int(obj.DateTime)
            starting_position = hash_to_int(obj.id, len(node_ids))

            # available_creators = 10 # user transaction validators
            if full_validator_list:
                required_validators = len(node_ids)
            else:
                required_validators = get_required_validator_count(obj=obj, node_ids=node_ids) # user connects to nodes in order of this

            
            if isinstance(dt, datetime.datetime):
                dt_str = dt_to_string(dt)
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
            prnt('shuffled_nodes',shuffled_nodes)
            creator_nodes = shuffled_nodes[:available_creators]
            validator_list = shuffled_nodes[-required_validators]
            return creator_nodes, broadcast_list, validator_list


        else:
            # prnt('else12334')
            is_transaction = True
            if obj.object_type == 'Block' and obj.Transaction_obj:
                obj = obj.Transaction_obj
            dt = round_time(dt=obj.created, dir='down', amount='evenhour')
            if not valid_node_ids_received:
                node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, strings_only=strings_only)
            date_int = date_to_int(dt)
            if sender_transaction: # reverse receiver/sender
                creator_position = hash_to_int(obj.Sender_obj.id, len(node_ids))
                starting_position = hash_to_int(obj.Sender_obj.id, len(node_ids))
            else:
                creator_position = hash_to_int(obj.Receiver_obj.id, len(node_ids))
                starting_position = hash_to_int(obj.Receiver_obj.id, len(node_ids))
            available_creators, required_validators = get_required_validator_count(obj=obj, node_ids=node_ids, include_initializers=True)

    elif obj and obj.object_type == 'DataPacket':
        chain_list = [obj.chainId]


        if not dt:
            dt = round_time(dt=obj.created, dir='down', amount='10mins')
        if not valid_node_ids_received:
            node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, blockchain=obj.chainId, strings_only=strings_only)
        if obj.Node_obj:
            if strings_only:
                creator_nodes.append(obj.Node_obj.id)
            else:
                creator_nodes.append(obj.Node_obj)
        date_int = date_to_int(dt)
        starting_position = hash_to_int(obj.id, len(node_ids))
        
    elif obj and obj.object_type == 'Validator':
        chain = Blockchain.objects.filter(id=obj.blockchainId).first()
        chain_list = [chain.genesisId]
        dt = round_time(dt=obj.created, dir='down', amount='10mins')
        if not valid_node_ids_received:
            node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, genesisId=chain.genesisId, strings_only=strings_only)
        date_int = date_to_int(dt)
        starting_position = hash_to_int(obj.id, len(node_ids))
        
    elif obj and obj.object_type == 'Node':
        chain_list = obj.supportedChains_array
        if not dt:
            dt = round_time(dt=obj.last_updated, dir='down', amount='10mins')
        if not valid_node_ids_received:
            node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, strings_only=strings_only)
        date_int = date_to_int(dt)
        starting_position = hash_to_int(obj.id, len(node_ids))
    
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
        if not valid_node_ids_received: # careful, this is different from other assignments
            node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, blockchain=chainId, strings_only=strings_only, sublist='servers')
        date_int = date_to_int(dt)
        starting_position = hash_to_int(obj.id, len(node_ids))
        available_creators = 0
        if full_validator_list:
            required_validators = len(node_ids)
        else:
            required_validators = get_required_validator_count(obj=obj, node_ids=node_ids)
        
    elif obj:
        dt = round_time(dt=obj.created, dir='down', amount='10mins')
        if not valid_node_ids_received:
            node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, obj=obj, strings_only=strings_only)
        date_int = date_to_int(dt)
        starting_position = hash_to_int(obj.id, len(node_ids))
        required_validators = get_required_validator_count(obj=obj, node_ids=node_ids)
    
    elif func:
        # prnt('is func',func,'chainId',chainId)
        if not chainId.startswith(get_model_prefix('Blockchain')):
            chainId = Blockchain.objects.filter(genesisId=chainId).first().id
        if not valid_node_ids_received:
            # prnt('get node b lock')
            node_ids, number_of_peers, relevant_nodes = get_relevant_nodes_from_block(dt=dt, blockchain=chainId, strings_only=strings_only)
        # else:
        #     prnt('has node data: relevant_nodes',relevant_nodes,'node_ids',node_ids)

        # if not dt:
        #     dt = round_time(dt=obj.created, dir='down', amount='10mins')


        if isinstance(dt, datetime.datetime):
            dt_str = dt_to_string(dt)
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
        prnt('shuffled_nodes',shuffled_nodes)


        # sha256_hash = str_to_hash(func)
        # name_position = hash_to_int(sha256_hash, len(node_ids))
        # date_int = date_to_int(dt)
        # id_position = hash_to_int(chainId, len(node_ids))
        # prnt('name_position',name_position,'id_position',id_position,'sha256_hash',sha256_hash)
        # starting_position = name_position + id_position
        required_scrapers, required_validators = get_required_validator_count(dt=dt, func=func, node_ids=node_ids, include_initializers=True)
        # prntDebug('required_scrapers',required_scrapers,'required_validators',required_validators)
        return shuffled_nodes[:required_scrapers], shuffled_nodes[-required_validators] # validator_node should maybe be [validator_node] for consistency

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
    
    prnt('--starting_position11',starting_position,'dt::',dt,'date_int:',date_int,'len(node_ids)',len(node_ids),'available_creators',available_creators)
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



    if len(node_ids) == 0:
        prnt('node_lengths:==000')
        return [], {}, []
    elif len(node_ids) == 1:
        prnt('node_lengths:==1')
        if creator_only:
            if strings_only:
                return [node_ids[0]]
            else:
                return [relevant_nodes[node_ids[0]]]
        elif scrapers_only:
            if func:
                return [node_ids[0]], node_ids[0] # [scrapers], validator
            else:
                return [], None
        else:
            if strings_only:
                return [node_ids[0]], {node_ids[0] : [relevant_nodes[node_ids[0]]]}, [node_ids[0]] 
            else:
                return [node_ids[0]], {node_ids[0] : [relevant_nodes[node_ids[0]]]}, [node_ids[0]] # [creators], {broadcast_list}, [validators.id]

    def get_peer_nodes(broadcaster, position, node_ids, checked_node_list):
        # prntDebug('get_peer_nodes',broadcaster, position, node_ids, checked_node_list)
        nonlocal broadcast_list
        nonlocal relevant_nodes
        # prntDebug('get_peer_nodes 22',broadcast_list, relevant_nodes)
        if broadcaster not in broadcast_list:
            if broadcaster in node_ids:
                node_ids.remove(broadcaster)
            # prntDebug('get peers step 1')
            broadcaster_hashed_int = hash_to_int(broadcaster, len(node_ids))
            def run(position, node_ids):
                # prntDebug('run',position, node_ids)
                position += (broadcaster_hashed_int + date_int)
                if position >= len(node_ids):
                    position = position % len(node_ids)
                new_node_id = node_ids[position]
                # prntDebug('run step 2')
                node_ids.remove(new_node_id)
                return new_node_id, position, node_ids
            peers = []
            while len(peers) < number_of_peers and len(node_ids) > 0:
                new_node_id, position, node_ids = run(position, node_ids)
                if new_node_id != broadcaster:
                    # prntDebug('follow run')
                    peers.append(relevant_nodes[new_node_id])
                    checked_node_list.append(new_node_id)
            # prntDebug('get peers stpe 2')
            broadcast_list[broadcaster] = peers
            if broadcaster not in checked_node_list:
                checked_node_list.append(broadcaster)
        # prntDebug('end get peer nodes',broadcast_list, checked_node_list, node_ids)
        return broadcast_list, checked_node_list, node_ids
    
    def process(broadcaster, position, node_ids, checked_node_list, broadcast_list, v):
        # prntDebug('process',broadcaster, position, node_ids, checked_node_list, broadcast_list, v)
        nonlocal creator_nodes
        nonlocal validator_list
        nonlocal scraper_list
        
        broadcast_list, checked_node_list, node_ids = get_peer_nodes(broadcaster, position, node_ids, checked_node_list)
        # prnt('1234')
        if len(validator_list) < required_validators and broadcaster not in creator_nodes and broadcaster not in validator_list:
            validator_list.append(broadcaster)
        # prnt('56789',scraper_list)
        if func and len(scraper_list) < required_scrapers and broadcaster != validator_node and broadcaster not in scraper_list:
            # prnt('02342',broadcaster)
            scraper_list.append(broadcaster)
        return broadcast_list, checked_node_list, node_ids, v

    # prntDebug('assign step2')
    starting_node_list_len = len(node_ids)
    starting_position += date_int
    starting_position = int(starting_position)
    def reduce_pos(pos):
        pos = pos % len(node_ids)
        return pos
    
    if is_transaction:
        x = reduce_pos(creator_position)
    else:
        x = reduce_pos(starting_position)
    prnt('x1',x)
    if available_creators:
        if not creator_nodes:
            prntDebug('get creator_nodes')
            y = x
            for i in range(available_creators):
                prntDebug('i',i)
                if strings_only:
                    if node_ids[x] not in creator_nodes:
                        creator_nodes.append(node_ids[x])
                else:
                    if relevant_nodes[node_ids[x]] not in creator_nodes:
                        creator_nodes.append(relevant_nodes[node_ids[x]])
                x += y
                prntDebug('y',y)
                x = reduce_pos(x)
                prntDebug('x',x)
        prntDebug('creator_nodes',creator_nodes, 'scraper_list',scraper_list)
        for c in creator_nodes:
            prntDebug('rem c',c)
            if strings_only:
                node_ids.remove(c)
            else:
                node_ids.remove(c.id)
        checked_node_list = creator_nodes.copy()
        if func and creator_nodes:
            validator_node = creator_nodes[0]
            checked_node_list = [validator_node]
        if creator_only:
            # prntDebug('returning creator only 123e4',creator_nodes)
            return creator_nodes
        if not strings_only:
            checked_node_list = [n.id for n in checked_node_list]
        x = 0
        run = True
        target_node = checked_node_list[x]
    else: # for creating user list, likely not needed by node, is needed by user, user creates with javascript
        
        run = True
        if strings_only:
            target_node = node_ids[x]
        else:
            target_node = relevant_nodes[node_ids[x]]
    prntDebug('assign step3')
    # run for nodes registered to node_block at time of dt
    while x < len(node_ids) and run:
        try:
            prntDebug(f'while x:{x}, v:{v}, target_node:{target_node}, starting_position:{starting_position}, node_ids:{node_ids}, checked_node_list:{checked_node_list}, broadcast_list:{broadcast_list}, ')
            broadcast_list, checked_node_list, node_ids, v = process(target_node, starting_position, node_ids, checked_node_list, broadcast_list, v)
            if func and scrapers_only:
                if len(scraper_list) >= required_scrapers or len(node_ids) == 0:
                    run = False
            if target_node not in broadcast_list:
                run = False
            x += 1
            target_node = checked_node_list[x]
        except Exception as e:
            prntDebug(f'fail459373 {e}')
            run = False
    prntDebug('required_validators',required_validators,'validator_list',validator_list)

    if len(validator_list) < required_validators and starting_node_list_len >= required_validators:
        for n in relevant_nodes:
            prnt('n',n)
            if n not in validator_list:
                if strings_only and n not in creator_nodes:
                    validator_list.append(n)
                elif not strings_only:
                    for c in creator_nodes:
                        if n != c.id:
                            validator_list.append(n)
                if len(validator_list) >= required_validators:
                    break

    if func and scrapers_only:
        if len(scraper_list) < required_scrapers:
            for n in relevant_nodes:
                if n not in scraper_list:
                    scraper_list.append(n)
                    if len(scraper_list) >= required_scrapers:
                        break
        if strings_only:
            scraper_list = [n if isinstance(n, str) else n.id for n in scraper_list]
        prntDebug('func and scrfapers only', scraper_list, validator_node)
        return scraper_list, validator_node # validator_node should maybe be [validator_node] for consistency
    
    # add creators to end of broadcast_list
    added_creators = []
    for node_id in reversed(checked_node_list):
        for creator in creator_nodes:
            if creator not in added_creators:
                if strings_only:
                    if node_id != creator:
                        if node_id not in broadcast_list:
                            broadcast_list[node_id] = []
                        broadcast_list[node_id].append(relevant_nodes[creator])
                        added_creators.append(creator)
                        break
                else:
                    if isinstance(creator, models.Model):
                        if node_id != creator.id:
                            if node_id not in broadcast_list:
                                broadcast_list[node_id] = []
                            broadcast_list[node_id].append(creator.return_address())
                            added_creators.append(creator)
                            break
                    elif is_id(creator):
                        if node_id != creator:
                            if node_id not in broadcast_list:
                                broadcast_list[node_id] = []
                            broadcast_list[node_id].append(relevant_nodes[creator].return_address())
                            added_creators.append(creator)
                            break
        if len(added_creators) == len(creator_nodes):
            break

    # prnt('assign step 4')
    # prnt('relevant_nodes',relevant_nodes)
    if not valid_node_ids_received and get_stragglers:
        prntDebug('assign step4')
        if strings_only:
            exclude_list = checked_node_list
        else:
            exclude_list = [n.id for n in checked_node_list]
        latest_node_ids, number_of_peers, latest_relevant_nodes = get_relevant_nodes_from_block(chains=chain_list, obj=obj, exclude_list=exclude_list, strings_only=strings_only)
        prnt('latest_node_ids',latest_node_ids)
        prnt('latest_relevant_nodes',latest_relevant_nodes)
        # look closely at the following, it may need work

        # run for remaining nodes not in initial snapshot
        node_list = latest_node_ids
        for node in checked_node_list:
            if node in latest_node_ids:
                latest_node_ids.remove(node)
        cross_reference_list = [node for node in checked_node_list if node in latest_node_ids]
        prntDebug('assign step5')
        run = True
        n = 0
        while len(cross_reference_list) < len(latest_node_ids) and run and n < len(node_ids):
            try:
                n += 1
                target_node = checked_node_list[x]
                prntDebug(f'n:{n}, cross_reference_list:{cross_reference_list}, target_node:{target_node}, starting_position:{starting_position}, node_ids:{node_ids}, checked_node_list:{checked_node_list}, broadcast_list:{broadcast_list}, ')
                broadcast_list, checked_node_list, node_ids = get_peer_nodes(target_node, starting_position, node_ids, checked_node_list)
                # broadcast_list, checked_node_list, node_list, v = process(target_node, starting_position, node_list, checked_node_list, v)
                # break if target_node has no broadcast_peers
                if target_node in broadcast_list:
                    peers = broadcast_list[target_node]
                    for peer in peers:
                        if peer not in cross_reference_list:
                            cross_reference_list.append(peer)
                x += 1
            except Exception as e:
                prntDebug(f'fail485 {e}')
                run = False

        
    prntDebug(f'----finish_get_node_assignment\n --creator_nodes:{creator_nodes},\n --broadcast_list:{broadcast_list},\n --validator_list:{validator_list}\n')

    return creator_nodes, broadcast_list, validator_list
    
def tasker(dt, test=False):

    try:
        est = pytz.timezone('US/Eastern')
        est_time = dt.astimezone(est)
        formatted_time = est_time.strftime("%I:%M:%S %p")
        prnt('--tasker',formatted_time,'est')
    except:
        prnt('--tasker',dt)
    prnt('dt_utc',dt)
    # return
    # runs every 10 minutes

    result = {'dt':dt_to_string(dt),'now_utc':dt_to_string(now_utc())}
    # skip if start time is excessively delayed
    difference = now_utc() - dt
    diff_mins = difference.total_seconds() / 60
    if diff_mins < 30 or test:
        result = result | {'dps':[],'unvalidated_blocks':[],'new_block_candidate':[],'restore failed scrapers':[],'scrape assignment':[]}
        self_node = get_self_node()

        failed_broadcasts = EventLog.objects.filter(type='toBroadcast', created__gte=dt - datetime.timedelta(days=7)).exclude(data={})
        if failed_broadcasts:
            prnt('failed_broadcasts',failed_broadcasts)
            for log in failed_broadcasts:
                # rebroadcast - currently only assigned to block validations
                for iden, data in log.data.items():
                    if 'dt' in data and string_to_dt(data['dt']) < dt - datetime.timedelta(days=7):
                        toBroadcast(iden, remove_item=True)
                    else:
                        if 're' in data:
                            create_job(broadcast_validation, job_timeout=60, worker='low', block=data['re'])
                        # re_obj = None
                        # broadcast_list = None
                        # broadcast_obj = get_dynamic_model(iden, id=iden)
                        # if broadcast_obj:
                        #     if 're' in data:
                        #         re_obj = get_dynamic_model(data['re'], id=data['re'])
                        #         if re_obj.object_type == 'Block':
                        #             creator_nodes, broadcast_list, validator_list = re_obj.get_assigned_nodes()
                        #     if re_obj and not broadcast_list:
                        #         starting_nodes, broadcast_list, validator_list = get_node_assignment(re_obj, strings_only=True, dt=string_to_dt(data['dt']))
                        #     elif broadcast_obj and not broadcast_list:
                        #         starting_nodes, broadcast_list, validator_list = get_node_assignment(broadcast_obj, strings_only=True, dt=string_to_dt(data['dt']))
                        #     if broadcast_obj and re_obj and broadcast_list:
                        #         broadcast_validation(re_obj, broadcast_list=broadcast_list, validations=[broadcast_obj])
                    
        low_queue = django_rq.get_queue('low')
        processes = DataPacket.objects.filter(func__icontains='process', created__lte=now_utc() - datetime.timedelta(minutes=9.8)).exclude(func__icontains='completed').order_by('created')
        if processes:
            
            for log in processes:
                prnt('log',log)
                skip = False
                if log.created < now_utc() - datetime.timedelta(hours=2):
                    log.completed('passed_2_hours')
                elif not log.data:
                    log.delete()
                else:
                    func = log.func
                    if ':' in func:
                        func = func[:func.find(':')]
                    skip = False
                    # queue = django_rq.get_queue('low')
                    if not exists_in_worker(func, log.id, queue=low_queue):
                        prnt('Continuing Run:', func)
                        logEvent(f'restoring process: {func} log:{log.id}, dt:{log.created} len:{len(log.data)}', log_type='Tasks')
                        # queue.enqueue(cmd, special='super', job_timeout=scraperScripts.runTimes[f]*5)    
                        low_queue.enqueue(globals()[func], log.id, job_timeout=300, result_ttl=3600)



        nodePacket = DataPacket.objects.filter(Node_obj=self_node, func='share', chainId=NodeChain_genesisId).first() # broadcast nodeReviews and/or node updates
        if nodePacket:
            # queue = django_rq.get_queue('low')
            # queue.enqueue_at(run_at, nodePacket.broadcast, job_timeout=60, result_ttl=3600)
            low_queue.enqueue(nodePacket.broadcast, job_timeout=30, result_ttl=3600)

        # if dt.minute >= 30 and dt.minute < 50:
        
        dataPackets = DataPacket.objects.filter(Node_obj=self_node, func='share').exclude(chainId=NodeChain_genesisId).exclude(data={})
        for dp in dataPackets:
            if not exists_in_worker('broadcast', dp.id, queue=low_queue):
                # run_at = now_utc() + datetime.timedelta(minutes=random.randint(5, 15))
                
                # queue.enqueue_at(run_at, dp.broadcast, job_timeout=60, result_ttl=3600)
                low_queue.enqueue(dp.broadcast, iden=dp.id, job_timeout=60, result_ttl=3600)
                

        for block in Block.objects.filter(validated__isnull=True).filter(Q(data__meta__isnull=True) | ~Q(data__meta__has_key='is_reward')).exclude(Blockchain_obj=None): # exclude .data['meta']['is_reward']
            result['unvalidated_blocks'].append(block.Blockchain_obj.genesisName)
            # queue = django_rq.get_queue('low')
            low_queue.enqueue(check_validation_consensus, block, job_timeout=300, result_ttl=3600)

        # new node block every 10 mins if new data
        # currently, if a new block (any block) is failing to validate, it will be discarded after its block_delay_time. A new block should immediatly be created, but chainQueue is not registering data here because previous block gets invalidated moments after this check. somehow should check for pending blocks and take appropriate action after 10 mins (or 60 mins)
        nodeChain = Blockchain.objects.filter(genesisId=NodeChain_genesisId, last_block_datetime__lte=dt - datetime.timedelta(minutes=block_time_delay(NodeChain_genesisId)-1)).first()
        prnt('nodeChain',nodeChain)
        prnt('delay',block_time_delay(NodeChain_genesisId))
        if nodeChain:
            prnt('nodeChain2',nodeChain)
            if nodeChain.data_added_datetime and nodeChain.last_block_datetime:
                if nodeChain.data_added_datetime > nodeChain.last_block_datetime:
                    last_dt = nodeChain.data_added_datetime
                else:
                    last_dt = nodeChain.last_block_datetime
            elif nodeChain.data_added_datetime:
                last_dt = nodeChain.data_added_datetime
            elif nodeChain.last_block_datetime:
                last_dt = nodeChain.last_block_datetime
            else:
                last_dt = nodeChain.created
            updated_nodes = Node.objects.filter(Q(last_updated__gte=last_dt-datetime.timedelta(minutes=1))|Q(suspended_dt__gte=last_dt-datetime.timedelta(minutes=1))).count() # not currently recognizing nodes restored from deactivation
            prnt('updated_nodes',updated_nodes)
            if updated_nodes:
                block_assigned = nodeChain.new_block_candidate(self_node=self_node, dt=dt, updated_nodes=updated_nodes)
                prnt('block_assigned',block_assigned)
                if block_assigned:
                    result['new_block_candidate'].append(nodeChain.genesisName)

        # every 60 mins create block if data
        if dt.minute >= 50 or test==True:
            block_assigned = False
            for chain in mandatoryChains:
                if chain != NodeChain_genesisId:
                    mChains = None
                    if is_id(chain):
                        mChains = Blockchain.objects.filter(genesisId=chain, last_block_datetime__lte=dt - datetime.timedelta(minutes=block_time_delay(chain)-10)).exclude(queuedData={})
                    else:
                        mChains = Blockchain.objects.filter(genesisType=chain, last_block_datetime__lte=dt - datetime.timedelta(minutes=block_time_delay(chain)-10)).exclude(queuedData={})
                    prnt('mandaroryChain',chain,'mChains',mChains)
                    if mChains:
                        for mChain in mChains:
                            block_assigned = mChain.new_block_candidate(self_node=self_node, dt=dt)
                            prntDebug('block_assigned1',block_assigned)
                            if block_assigned:
                                result['new_block_candidate'].append(mChain.genesisName)
            try:
                chains = Blockchain.objects.filter(genesisId__in=self_node.supportedChains_array, genesisType__in=selectableChains, last_block_datetime__lte=dt - datetime.timedelta(minutes=block_time_delay()-10)).exclude(queuedData={}).order_by('?')
                prnt('chains222',chains)
                for c in chains:
                    block_assigned = c.new_block_candidate(self_node=self_node, dt=dt)
                    prntDebug('block_assigned123',block_assigned)
                    if block_assigned:
                        result['new_block_candidate'].append(c.genesisName)
            except Exception as e:
                prnt('fail0398612',str(e))

        # scrapers log objs in GenericModel
        # send to validator in instances where scraper crashed before finishing, try to salvage some data
        logs = DataPacket.objects.filter(func__icontains='scrape assignment', updated_on_node__lt=dt - datetime.timedelta(minutes=9))
        if logs:
            prnt('logs',logs)
            for log in logs:
                skip = False
                if not test and log.created < dt - datetime.timedelta(hours=3):
                    log.delete()
                elif not log.data:
                    log.delete()
                else:
                    prnt('log has Data')
                    if 'shareData' not in log.data or not log.data['shareData']:
                        log.delete()
                    else:
                        # from utils.cronjobs import finishScript
                        # from utils.models import list_all_scrapers
                        all_files = list_all_scrapers()
                        region = log.data['region_name'].lower()
                        prnt('region',region)
                        func = log.data['func']
                        prnt('func',func)
                        # queue = django_rq.get_queue('low')
                        
                        for file in all_files:
                            if not skip:
                                a = file.find('/scrapers/')+len('/scrapers/')
                                x = file[a:]
                                words = x.split('/')
                                txt = x.replace('/', '.').replace('.py','')
                                if region in txt:
                                    import importlib
                                    scraperScripts = importlib.import_module('scrapers.'+txt) 
                                    approved_models = scraperScripts.approved_models
                                    for f, models in approved_models.items():
                                        if not skip:
                                            if f == func:
                                                if not exists_in_worker('finishScript', log.id, queue=low_queue):
                                                    prnt('Continuing Run:', func)
                                                    result['restore failed scrapers'].append(f'{region} {func}')
                                                    logEvent(f'Restore scraper: {region} {func} dt:{log.created} len:{len(log.data["shareData"])}', log_type='Tasks')
                                                    low_queue.enqueue(finishScript, log.id, func=func, log_event=False, send_off=True, job_timeout=420, result_ttl=3600)

        if dt.minute < 10 and test==False:
            create_job(run_script_duty, job_timeout=300, worker='main', receivedDt=dt, result=result)

        # there may also utils.cronjobs that may need to be run periodically
    return result



# from django_rq import get_scheduler, get_queue
# from rq.job import Job

# def check_job_status(job_id, queue_name='main'):
#     # Get scheduler and queue
#     scheduler = get_scheduler(queue_name)
#     queue = get_queue(queue_name)
    
#     # Check if job is scheduled
#     scheduled_jobs = list(scheduler.get_jobs())
#     scheduled_job = next((job for job in scheduled_jobs if job.id == job_id), None)
    
#     if scheduled_job:
#         print(f"Job {job_id} is scheduled.")
#     else:
#         print(f"Job {job_id} is not scheduled.")
    
#     # Check if job is running
#     running_jobs = queue.get_jobs()
#     running_job = next((job for job in running_jobs if job.id == job_id), None)
    
#     if running_job:
#         print(f"Job {job_id} is currently running.")
#     else:
#         print(f"Job {job_id} is not running.")

# # Example usage
# job_id_to_check = 'your_job_id_here'  # Replace with the actual job ID
# check_job_status(job_id_to_check)


def get_scraperScripts(gov=None, region=None, gov_level=''):
    prnt('--get_scraperScripts')
    model_type = None
    if gov:
        region = gov.Region_obj
        region_name = region.Name
        gov_level = gov.gov_level
        model_type = region.modelType
    elif region:
        if isinstance(region, models.Model):
            region_name = region.Name
            model_type = region.modelType
        elif isinstance(region, dict):
            region_name = region['Name']
            model_type = region['modelType']
    if region and model_type and model_type == 'country':
        country_name = region_name.lower()
        importScript = f'scrapers.{country_name}.{gov_level.lower()}'
    elif region and model_type and model_type == 'provState':
        provState_name = region_name.lower()
        if isinstance(region, dict):
            from posts.models import Region
            par_region = Region.objects.filter(id=region['ParentRegion_obj']).first()
            country_name = par_region.Name.lower()
        else:
            country_name = region.ParentRegion_obj.Name.lower()
        importScript = f'scrapers.{country_name}.{provState_name}.{gov_level.lower()}'
    elif region and model_type and model_type == 'city':
        name = region_name.lower()
        if isinstance(region, dict):
            from posts.models import Region
            provState = Region.objects.filter(id=region['ParentRegion_obj']).first()
            provState_name = provState.Name.lower()
            country_name = provState.ParentRegion_obj.Name.lower()
        else:
            provState_name = region.ParentRegion_obj.Name.lower()
            country_name = region.ParentRegion_obj.ParentRegion_obj.Name.lower()
        importScript = f'scrapers.{country_name}.{provState_name}.{name}'
    else:
        logError('err', code='5423', func='get_scraperScripts', extra={'gov':gov,'region':region})
    
    import importlib
    scraperScripts = importlib.import_module(importScript) 
    return scraperScripts

# def get_scraping_order(chainId=1, func_name=None, dt=None, validator_only=False, node_block_data={}, strings_only=True):
#     prnt('get scraping order -validator_only:',validator_only,'-func_name:',func_name)
#     dt = round_time(dt=dt, dir='down', amount='hour')
#     # if validator_only:
#     # required_scrapers, required_validators = get_required_validator_count(dt=dt, func=func, node_ids=node_ids, include_initializers=True)
#     return get_node_assignment(None, dt=dt, func=func_name, chainId=chainId, node_block_data=node_block_data, strings_only=strings_only)
#     # return creator_nodes validator_nodes[-required_validators:]
#     # else:
#     #     return get_node_assignment(None, dt=dt, func=func_name, chainId=chainId, node_block_data=node_block_data, strings_only=strings_only)


def get_scrape_duty(gov=None, receivedDt=None, region=None, gov_level=None, debate_obj=None, func=None):
    # requires either gov or region AND gov_level 
    prnt('--get scrape duty',gov,receivedDt,region)

    if gov:
        region = gov.Region_obj
        region_id = region.id
        to_zone = pytz.timezone(region.timezone)
        scraperScripts = get_scraperScripts(gov)
    elif region and gov_level:
        if isinstance(region, models.Model):
            region_id = region.id
            tz = region.timezone
        elif isinstance(region, dict):
            region_id = region['id']
            tz = region['timezone']
        to_zone = pytz.timezone(tz)
        scraperScripts = get_scraperScripts(region=region, gov_level=gov_level)
    else:
        logEvent('missing gov or region and gov_level', code='86432', func='get_scrape_duty', log_type='Errors')
        return [], {}

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
                                    function_list.append({'region_id':region_id,'function_name':f, 'function':getattr(scraperScripts, f), 'timeout':runTimes[f]})
            break

    # prnt('function_list',function_list)
    master_list = []
    for f in function_list:
        scrapers, validators = get_node_assignment(chainId=region_id, func=f['function_name'], dt=receivedDt)
        # get_scraping_order(chainId=region_id, func_name=f['function_name'], dt=receivedDt)
        f['scraping_order'] = scrapers
        f['validators'] = validators
        master_list.append(f)
    # prnt('master_list',master_list)
    return master_list, approved_models

def run_script_duty(receivedDt=None, result=None):
    # runs every hour
    prnt('\n---run_script_duty',receivedDt)
    from posts.models import Post
    self_node = get_self_node()

    if not receivedDt:
        receivedDt = now_utc()
    if receivedDt.hour in [9, 11, 20]:
        # also check for User objs without valid UPK and vice versa, maybe less often
        queue = django_rq.get_queue('low')
        queue.enqueue(Tidy()._add_all_jobs, job_timeout=60, result_ttl=3600)
                    

    if receivedDt.minute < 10 and receivedDt.hour == round_time(dt=receivedDt, amount='hour').hour:
        # if 'chainData' in operatorData and 'supported' in operatorData['chainData']:
        govPosts = Post.objects.filter(pointerType='Government', Region_obj__is_supported=True, Region_obj__id__in=self_node.supportedChains_array).exclude(Update_obj__data__has_key='EndDate').distinct('Region_obj__id').order_by('Region_obj__id','-DateTime')
        prnt('govPosts',govPosts)
        for post in govPosts:
            gov = post.Government_obj
            scraper_list, approved_models = get_scrape_duty(gov, receivedDt)
            prnt('scraper_list',scraper_list)
            for i in scraper_list:
                if self_node.id in i['scraping_order']:
                    # job_dt = round_time(dt=receivedDt, dir='down', amount='hour')
                    # job_iden = f'{i["function_name"]} - {gov.Region_obj.id} - {receiveddt_to_string(Dt)}'
                    # log = DataPacket(func=f'scrape assignment - {i["function_name"]}')
                    # log.id = hash_obj_id(log, verify=False, specific_data=job_iden, return_data=False, model=None, version=None)
                    # log.created = job_dt
                    # log.Node_obj = self_node
                    # log.data['func'] = i["function_name"]
                    # log.data['scapers'] = i['scraping_order']
                    # log.data['validator'] = i['validator']
                    # log.data['created'] = job_dt_to_string(dt)
                    # log.data['region_name'] = gov.Region_obj.Name
                    # log.data['shareData'] = []
                    # log.Region_obj = gov.Region_obj
                    # log.save()
                    
                    if result:
                        result['scrape assignment'].append(f'{gov.Region_obj.Name} {i["function_name"]}')

                    create_job(i['function'], job_timeout=i['timeout'], worker='low', clear_chrome_job=True, dt=receivedDt)

    if result:
        return result





def process_received_data(received_data, block_dict=None, downstream_worker=True, return_updated_count=False, return_updated_objs=False, return_updated_ids=False, check_consensus=True, skip_log_check=False, get_missing_blocks=True, override_completed=False, force_sync=False):
    prnt('---process_received_data now_utc:', now_utc())
    # prntn('received_data',received_data)
    from accounts.models import User, Notification, UserPubKey
    from transactions.models import UserTransaction
    from posts.models import scoreMe, Update, Post
    from utils.locked import verify_data
    # from utils.models import get_or_create_model, get_dynamic_model, get_model_prefix, sync_model
    # specialTypes = ['Node', 'User'] # sync previous data, do not write to chain

    result = process_received_dp(received_data, 'process_received_data', skip_log_check=skip_log_check, override_completed=override_completed)
    # prnt('result111',result)
    logEvent('process_received_data-data:', code='75328', func='process_received_data', extra=str(result)[:2000])
    if result and 'dp' in result:
        log = result['dp']
        received_data = log.data
    elif result and 'data' in result:
        received_data = result['data']
        log = None
    else:
        received_data = []
        log = None

    if not force_sync and log and isinstance(log, models.Model):
        if 'process' not in log.func and not override_completed:
            return []

    updated_objs = []
    updated_count = 0
    databaseUpdated = False
    try:
        # prntDebug('test mne')
        # prnt('123')
        if isinstance(received_data, dict) and 'content' in received_data:
            # prnt('234')
            content = received_data['content']
            if isinstance(content, dict) and 'content' in content: 
                # prnt('345')
                content = content['content']
        else:
            # prnt('456')
            content = received_data
        # prnt('567')
        content = decompress_data(content)
        # prnt('678')
        if isinstance(content, str):
            # prnt('789')
            content = json.loads(content)
        elif isinstance(content, list):
            # prnt('890')
            content = content
        prnt('next3')
        if not content:
            prnt('no data')
            if log:
                log.completed(note='no_data')
            return False
        # prnt('content',content)
        objs = {}
        for i in content:
            try:
                objs[i['object_type']].append(i['id'])
            except:
                objs[i['object_type']] = [i['id']]
        # prnt('objs--', objs)
        prnt('stage2-')
        node_block_data = {'index':{}}
        userVotes = []
        validators = []
        received_invalids = []
        storedModels, not_found, not_valid = get_data(content, return_model=True, include_related=False, result_as_dict=True, verify_data=False)
        prnt('existing_objs-',len(storedModels))

        sorted_data = sorted(content, key=data_sort_priority) # data must be added in order due to dependancies
        prntDebug('\n-----received_data22',len(sorted_data))

        def save_to_db(bulk_update_items):
            prntDev('save_to_db',bulk_update_items)
            nonlocal updated_objs
            nonlocal updated_count
            created_items = []
            bulk_create_objs = [bulk_update_items[key]['obj'] for key in bulk_update_items if bulk_update_items[key]['is_new']]
            if bulk_create_objs:
                created_items = dynamic_bulk_create(current_model_type, items=bulk_create_objs, return_items=True)
                if return_updated_objs:
                    updated_objs = updated_objs + created_items
                elif return_updated_ids:
                    updated_objs = updated_objs + [i.id for i in created_items]
                elif return_updated_count:
                    updated_count += len(created_items)
            bulk_update_objs = [bulk_update_items[key]['obj'] for key in bulk_update_items if not bulk_update_items[key]['is_new'] and bulk_update_items[key]['updatedDB']]
            if bulk_update_objs:
                updated_items = dynamic_bulk_update(current_model_type, items=bulk_update_objs, return_items=True)
                if return_updated_objs:
                    updated_objs = updated_objs + updated_items
                elif return_updated_ids:
                    updated_objs = updated_objs + [i.id for i in updated_items]
                elif return_updated_count:
                    updated_count += len(updated_items)
                updated_items.clear()

            for obj in created_items:
                if bulk_update_items[obj.id]['is_new'] or bulk_update_items[obj.id]['updatedDB']:
                    if has_method(obj, 'boot'):
                        if not has_field(obj, 'proposed_modification') or not obj.proposed_modification:
                            prntDebug('booting obj', obj.id)
                            obj.boot()
            created_items.clear()
            bulk_update_items.clear()

        current_model_type = None
        bulk_update_items = {}
        for i in sorted_data:
            prntDebugn('ixi:',str(i)[:500])
            # prntDebugn('ixi:',str(i)[:200])
            if not current_model_type:
                current_model_type = i['object_type']
            if current_model_type != i['object_type'] or len(bulk_update_items) >= 1000:
                if bulk_update_items:
                    save_to_db(bulk_update_items)
                current_model_type = i['object_type']
                bulk_update_items = {}
            valid_obj = False
            bad_commit = False
            val_err = '-'
            updatedDB = False
            if block_dict: # not doing anything currently
                hash = sigData_to_hash(i)
                receivedHash = [data['hash'] for iden, data in block_dict['data'].items() if iden == i['id'] and 'hash' in data][0]
                if receivedHash == hash:
                    hashMatch = True
                else:
                    hashMatch = False
            try:
                prnt('try')
                userObjects = ['User', 'Node', 'UserTransaction','UserPubKey']
                if i['object_type'] in storedModels and i['id'] in storedModels[i['object_type']]:
                    obj = storedModels[i['object_type']][i['id']]
                    is_new = False
                else:
                    obj, is_new = get_or_create_model(i['object_type'], return_is_new=True, id=i['id'])
                if 'Block_obj' in i and i['Block_obj']:
                    block = Block.objects.filter(id=i['Block_obj']).first()

                    if block and not check_commit_data(i, block.data[i['id']]):
                        bad_commit = True
                if bad_commit:
                    prnt('bad_commit',bad_commit)
                elif i['object_type'] in userObjects:
                    val_err += 'A'
                    if obj.object_type == 'User':
                        prnt('obj is user')
                        val_err += 'B'
                        if is_new or obj.validation_error:
                            val_err += '1'
                            prntDebug('is new')
                            validator_upk = UserPubKey()
                            # if validator_upk.verify(get_signing_data(i), i['signature'], i['publicKey']):
                            if verify_data(get_signing_data(i), i['publicKey'], i['signature']):
                                val_err += '2'
                                valid_obj = True
                                user = User()
                                prnt('create user')
                                for key, value in i.items():
                                    if value != 'None':
                                        setattr(user, key, value)
                                prntDebug('save new user', convert_to_dict(user))
                                user.save()
                                updatedDB = True
                                # new_user_valid = validator_upk.verify(get_signing_data(user), i['signature'], i['publicKey'])
                                new_user_valid = verify_data(get_signing_data(user), i['publicKey'], i['signature'])
                                prnt('new_user_valid',new_user_valid)
                                if new_user_valid:
                                    obj = user


                        else:
                            val_err += 'C'
                            if obj.isVerified == False and i['isVerified'] == 'True' or obj.isVerified == True and i['isVerified'] == 'False':
                                val_err += '1'
                                is_verified = obj.assess_verification()
                                obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)
                                if not is_verified:
                                    obj.isVerified = False
                                    # obj.save()
                            else:
                                val_err += '2'
                                obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)
                        val_err += 'D'
                        # check if username already taken
                        must_rename = False
                        u = User.objects.filter(display_name=i['display_name']).exclude(id=i['id']).first()
                        if u and u.last_updated > string_to_dt(i['last_updated']):
                            u.must_rename = True
                            # u.save() # shuold broadcast?
                            bulk_update_items[u.id] = {'is_new':False,'updatedDB':True,'obj':u}

                        elif u:
                            must_rename = True
                        if must_rename:
                            obj.must_rename = True
                            # obj.save()
                    elif obj.object_type == 'UserTransaction':
                        val_err += 'E'
                        if 'ReceiverBlock_obj' in i and i['ReceiverBlock_obj']:
                            ReceiverBlock_obj, block_is_new = get_or_create_model('Block', return_is_new=True, id=i['ReceiverBlock_obj'])
                            if block_is_new:
                                ReceiverBlock_obj.save()
                        if 'SenderBlock_obj' in i and i['SenderBlock_obj']:
                            SenderBlock_obj, block_is_new = get_or_create_model('Block', return_is_new=True, id=i['SenderBlock_obj'])
                            if block_is_new:
                                SenderBlock_obj.save()
                        val_err += '1'
                        obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)
                    elif obj.object_type == 'Node':
                        val_err += 'F'
                        if obj.expelled or i['expelled'] == 'True':
                            # handle disavowed claims appropriately
                            pass
                        if obj.suspended_dt and i['suspended_dt'] == 'None':
                            val_err += '1'
                            is_active = obj.assess_activity()
                            if is_active:
                                val_err += '2'
                                obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)
                            else:
                                val_err += '3'
                                obj, valid_obj, updatedDB = sync_model(obj, i, skip_fields=['suspended_dt'], do_save=False, force_sync=force_sync)
                                obj.save()
                        else:
                            val_err += '4'
                            obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)
                    elif obj.object_type == 'UserPubKey':
                        val_err += 'G'
                        prnt('obj is upk')
                        if is_new or obj.validation_error:
                            val_err += '1'
                            prntDebug('is new')
                            # validator_upk = UserPubKey()
                            # if validator_upk.verify(get_signing_data(i), i['signature'], i['publicKey']):
                            if verify_data(get_signing_data(i), i['publicKey'], i['signature']):
                                val_err += '2'
                                valid_obj = True
                                upk = UserPubKey()
                                prntDebug('creta upk')
                                for key, value in i.items():
                                    if value != 'None':
                                        if str(key) == 'User_obj':
                                            setattr(upk, 'User_obj_id', value)
                                        else:
                                            setattr(upk, key, value)
                                upk.save()
                                updatedDB = True
                                # upk = get_or_create_model(i['object_type'], id=i['id'])
                                # upk, valid_obj, updatedDB = sync_model(upk, i)
                                # upk.save()
                                new_upk_valid = verify_data(get_signing_data(upk), i['publicKey'], i['signature'])
                                # new_upk_valid = validator_upk.verify(get_signing_data(upk), i['signature'], i['publicKey'])
                                prnt('new_upk_valid',new_upk_valid)
                                if new_upk_valid:
                                    obj = upk
                        else:
                            val_err += '3'
                            obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)

                elif is_locked(obj) and not has_field(obj, 'is_modifiable'):
                    valid_obj = True
                    val_err += 'X'
                else:
                    val_err += 'H'
                    try:
                        if 'created' in i:
                            val_err += '1'
                            if i['created'] not in node_block_data:
                                relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=string_to_dt(i['created']), genesisId=NodeChain_genesisId, include_peers=True)
                                node_block_data[i['created']] = {'node_ids':[n for n in relevant_nodes],'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}
                            node_block_data['index'][i['id']] = i['created']
                            val_err += '2'
                            obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, node_block_data=node_block_data[i['created']], force_sync=force_sync)
                        else:
                            val_err += '3'
                            obj, valid_obj, updatedDB = sync_model(obj, i, do_save=False, force_sync=force_sync)

                        if valid_obj and obj.object_type == 'UserVote':
                            userVotes.append(obj)

                    except Exception as e:
                        prntDebug('---fail5937564, val_err:',val_err,str(e),str(i)[:1000])
                        logError(e, code='482764', func='processed_received_data', extra=str(i)[:1000])
                if valid_obj and obj.object_type == 'Validator':
                    if obj not in validators:
                        if obj.validatorType != 'Block' or is_new:
                            validators.append(obj)
                        elif obj.validatorType == 'Block':
                            val_block = Block.objects.filter(id__in=obj.data).first()
                            if val_block and val_block.validated == None:
                                validators.append(obj) # check_block_consensus()
                if not valid_obj:
                    received_invalids.append({i['id']:val_err,'updatedDB':updatedDB})
                if updatedDB:
                    bulk_update_items[obj.id] = {'is_new':is_new,'updatedDB':updatedDB,'obj':obj}
                if not databaseUpdated and valid_obj and updatedDB:
                    databaseUpdated = True
                prnt('val_err',val_err)
            except Exception as e:
                prntDebug('---fail5937123, val_err:',val_err,str(e),str(i)[:1000])
                logError(e, code='09863', func='processed_received_data', extra={'err':str(e),'i':str(i)[:1000]})
        if received_invalids:
            logError('received_invalids', code='4684', func='processed_received_data', extra={'received_invalids_count':len(received_invalids),'received_invalids':received_invalids[:500]})

        if bulk_update_items:
            save_to_db(bulk_update_items)
        prnt('stage3-',databaseUpdated)
        func = 'process_received_data'
        if validators:
            prnt('validators...')
            now = now_utc()
            chain_list = {}
            validIds = []
            v_list = {}
            prnt('vals step1',validators)
            for v in validators:
                if v.validatorType != 'Block' and v.is_valid:
                    for key, value in v.data.items():
                        validIds.append(key)
                        v_list[key] = v
                    if v.blockchainId not in chain_list:
                        blockchain = Blockchain.objects.filter(id=v.blockchainId).first()
                        if blockchain:
                            chain_list[v.blockchainId] = blockchain
                    if v.blockchainId in chain_list:
                        chain_list[v.blockchainId].add_item_to_queue(v)
                logEvent(f'received validator: {len(v.data)} items, id:{v.id}', func=func)
                
            validated_obj_idens = []
            validated_idens = [i for i in validIds if not i.startswith(get_model_prefix('Update')) and not i.startswith(get_model_prefix('Notification'))]

            logEvent(f'ValidatePosts validated_idens: {len(validated_idens)} items, x:{str(validated_idens)[:500]}', func=func)
            prnt('vals step2',len(validated_idens))
            if validated_idens:
                q = 13
                for model_name, id_list in seperate_by_type(validated_idens).items():
                    q = 131
                    to_queue = {}
                    objIdens = id_list
                    while objIdens:
                        q = 132
                        prnt('objIdens[:1000]',objIdens[:1000])
                        objs = list(get_dynamic_model(model_name, list=True, id__in=objIdens[:1000]))
                        for obj in objs:
                            if obj.id in v_list:
                                if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj.is_valid:
                                    validated_obj_idens.append(obj.id)
                                    objs.remove(obj)
                                else:
                                    if obj.id in node_block_data['index']:
                                        created_dt = node_block_data['index'][obj.id]
                                        target_node_block = node_block_data[created_dt]
                                    elif has_field(obj, 'created'):
                                        relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=convert_to_datetime(obj.created), genesisId=NodeChain_genesisId, include_peers=True)
                                        node_block_data[dt_to_string(obj.created)] = {'node_ids':[n for n in relevant_nodes],'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}
                                        node_block_data['index'][obj.id] = dt_to_string(obj.created)
                                        target_node_block = node_block_data[dt_to_string(obj.created)]
                                    else:
                                        target_node_block = {}
                                    if validate_obj(obj=None, pointer=obj, validator=v_list[obj.id], node_block_data=target_node_block, save_obj=False, update_pointer=False):
                                    # validator_node = get_scraping_order(dt=obj.created, chainId=obj.blockchainId, func_name=obj.func, validator_only=True, strings_only=False)
                                    
                                    # if v_list[obj.id].data[obj.id] == sigData_to_hash(obj) and v_list[obj.id].CreatorNode_obj == validator_node:
                                        obj.Validator_obj = v_list[obj.id]
                                        obj.updated_on_node = now
                                        validated_obj_idens.append(obj.id)
                                        if has_field(obj, 'blockchainId') and obj.blockchainId:
                                            if obj.blockchainId not in to_queue:
                                                to_queue[obj.blockchainId] = []
                                            to_queue[obj.blockchainId].append(obj)
                        dynamic_bulk_update(model_name, items_field_update=['Validator_obj','updated_on_node'], items=validated_obj_idens) 
                        # logEvent(f'ValidatePosts dynamic_bulk_update 0987:', func=func)
                        q = 133
                        objs.clear()
                        if len(objIdens) >= 1000:
                            q = 134
                            objIdens = objIdens[1000:]
                        else:
                            q = 135
                            objIdens = []
                    if to_queue:
                        for chainId, objs in to_queue.items():
                            if chainId not in chain_list:
                                blockchain = Blockchain.objects.filter(id=chainId).first()
                                if blockchain:
                                    chain_list[chainId] = blockchain
                            if chainId in chain_list:
                                chain_list[chainId].add_item_to_queue(objs)
                    to_queue.clear()

            logEvent(f'ValidatePosts matched_idens: {len(validated_obj_idens)} items', func=func)
            pointerIdens = [i for i in validated_obj_idens if not i.startswith(get_model_prefix('Update')) and not i.startswith(get_model_prefix('Notification')) and not i.startswith(get_model_prefix('BillText'))]
            prnt('vals step2.5',len(pointerIdens))
            from posts.models import update_post
            while pointerIdens:
                q = 121
                prnt('pointerIdens[:1000]',pointerIdens[:1000])
                bulk_update = []
                fields = []
                posts = Post.all_objects.filter(pointerId__in=pointerIdens[:1000]).exclude(validated=True)
                logEvent(f'ValidatePosts posts to validate: {posts.count()}', func=func)
                for p in posts:
                    if p.pointerId in node_block_data['index']:
                        created_dt = node_block_data['index'][p.pointerId]
                        target_node_block = node_block_data[created_dt]
                    else:
                        target_node_block = {}
                    if validate_obj(obj=p, pointer=None, validator=v_list[p.pointerId], node_block_data=target_node_block, save_obj=False, update_pointer=False, verify_validator=False):
                    # if validate_obj(obj=None, pointer=obj, validator=val, node_block_data={}):
                    # validated = p.validate(validator=v_list[p.pointerId], update_pointer=False, save_self=False, verify_validator=False, node_block_data=target_node_block)
                    # if validated:
                        p.validated = True
                        p.updated_on_node = now
                        p, updated_fields = update_post(p=p, save_p=False)
                        bulk_update.append(p)
                        if updated_fields:
                            fields += [f for f in updated_fields if f not in fields]
                posts = None
                q = 122
                prnt('bulk_update',bulk_update)
                if bulk_update:
                    dynamic_bulk_update(model=Post, items_field_update=['validated','updated_on_node']+fields, items=bulk_update)
                if len(pointerIdens) >= 1000:
                    pointerIdens = pointerIdens[1000:]
                else:
                    pointerIdens = []
                q = 123
            q = 124
            updateIdens = [u for u in validIds if u.startswith(get_model_prefix('Update'))]
            logEvent(f'ValidatePosts updateIdens: {len(updateIdens)} items, x:{str(updateIdens)[:500]}', func=func)
            prnt('vals step3',len(updateIdens))
            if updateIdens:
                q = 14
                prnt('updateIdens',updateIdens)
                bulk_update = []
                to_queue = {}
                updates = Update.objects.filter(id__in=updateIdens).exclude(validated=True)
                for u in updates:
                    prnt(u)
                    # if not is_locked(u):
                    if u.created in node_block_data:
                        # target_node_block = node_block_data[u.created]
                        created_dt = node_block_data['index'][u.id]
                        target_node_block = node_block_data[created_dt]
                    elif has_field(u, 'created'):
                        relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=convert_to_datetime(u.created), genesisId=NodeChain_genesisId, include_peers=True)
                        node_block_data[dt_to_string(u.created)] = {'node_ids':[n for n in relevant_nodes],'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}
                        node_block_data['index'][u.id] = dt_to_string(u.created)
                        target_node_block = node_block_data[dt_to_string(u.created)]
                    else:
                        target_node_block = {}
                    if validate_obj(obj=u, pointer=None, validator=v_list[u.id], node_block_data=target_node_block, save_obj=False, update_pointer=False):
                    # validator_node = get_scraping_order(dt=u.created, chainId=u.blockchainId, func_name=u.func, validator_only=True, strings_only=False)
                    # if v_list[u.id].CreatorNode_obj == validator_node:
                    #     validated = u.validate(validator=v_list[u.id], save_self=False, verify_validator=False, node_block_data=target_node_block)
                    #     if validated:
                        u.validated = True
                        u.updated_on_node = now
                        u.Validator_obj = v_list[u.id]
                        bulk_update.append(u)
                        if has_field(u, 'blockchainId') and u.blockchainId:
                            if u.blockchainId not in to_queue:
                                to_queue[u.blockchainId] = []
                            to_queue[u.blockchainId].append(u)
                updates = None
                q = 141
                prnt('bulk_update',bulk_update)
                if bulk_update:
                    dynamic_bulk_update(model=Update, items_field_update=['validated', 'Validator_obj','updated_on_node'], items=bulk_update)
                    logEvent(f'ValidateUpdates dynamic_bulk_update 3456: {len(bulk_update)} items', func=func)

                    if to_queue:
                        for chainId, objs in to_queue.items():
                            if chainId not in chain_list:
                                blockchain = Blockchain.objects.filter(id=chainId).first()
                                if blockchain:
                                    chain_list[chainId] = blockchain
                            if chainId in chain_list:
                                chain_list[chainId].add_item_to_queue(objs)
                    to_queue.clear()

            q = 142
            from accounts.models import Notification
            notiIdens = [u for u in validIds if u.startswith(get_model_prefix('Notification'))]
            logEvent(f'ValidatePosts notiIdens: {len(notiIdens)} items, x:{str(notiIdens)[:500]}', func=func)
            prnt('vals step3.5',len(notiIdens))
            if notiIdens:
                q = 15
                prnt('notiIdens',notiIdens)
                bulk_update = []
                to_queue = {}
                notifications = Notification.objects.filter(id__in=notiIdens).exclude(validated=True)
                for n in notifications:
                    # if not is_locked(n):
                    if n.created in node_block_data:
                        # target_node_block = node_block_data[n.created]
                        created_dt = node_block_data['index'][n.id]
                        target_node_block = node_block_data[created_dt]
                    elif has_field(n, 'created'):
                        relevant_nodes, number_of_peers = get_relevant_nodes_from_block(dt=convert_to_datetime(n.created), genesisId=NodeChain_genesisId, include_peers=True)
                        node_block_data[dt_to_string(n.created)] = {'node_ids':[n for n in relevant_nodes],'number_of_peers':number_of_peers,'relevant_nodes':relevant_nodes}
                        node_block_data['index'][n.id] = dt_to_string(n.created)
                        target_node_block = node_block_data[dt_to_string(n.created)]
                    else:
                        target_node_block = {}
                    if validate_obj(obj=u, pointer=None, validator=v_list[n.id], node_block_data=target_node_block, save_obj=False, update_pointer=False):
                    # validator_node = get_scraping_order(dt=n.created, chainId=n.blockchainId, func_name=n.func, validator_only=True, strings_only=False)
                    # if v_list[n.id].CreatorNode_obj == validator_node:
                    #     validated = n.validate(validator=v_list[n.id], add_to_queue=False, save_self=False, verify_validator=False, node_block_data=target_node_block)
                    #     if validated:
                            n.validated = True
                            n.updated_on_node = now
                            n.Validator_obj = v_list[n.id]
                            bulk_update.append(n)
                            if has_field(n, 'blockchainId') and n.blockchainId:
                                if n.blockchainId not in to_queue:
                                    to_queue[n.blockchainId] = []
                                to_queue[n.blockchainId].append(n)
                notifications = None
                prnt('bulk_update',bulk_update)
                if bulk_update:
                    dynamic_bulk_update(model=Notification, items_field_update=['validated', 'Validator_obj','updated_on_node'], items=bulk_update)
                    if to_queue:
                        for chainId, objs in to_queue.items():
                            if chainId not in chain_list:
                                blockchain = Blockchain.objects.filter(id=chainId).first()
                                if blockchain:
                                    chain_list[chainId] = blockchain
                            if chainId in chain_list:
                                chain_list[chainId].add_item_to_queue(objs)
                    to_queue.clear()

            transIdens = [u for u in validIds if u.startswith(get_model_prefix('UserTransaction'))]
            prnt('vals step4',len(transIdens))
            transactions = UserTransaction.objects.filter(id__in=transIdens)
            for t in transactions:
                t.assess_validation()
            transactions = None

            chains = {}
            prnt('vals step6')
            # from blockchain.models import script_created_modifiable_models
            for m in script_created_modifiable_models:
                mIdens = [u for u in validIds if u.startswith(get_model_prefix(m))]
                if mIdens:
                    objs = get_dynamic_model(m, list=True, id__in=mIdens)
                    for o in objs:
                        chain, o, secondChain = find_or_create_chain_from_object(o)
                        if chain:
                            if chain not in chains:
                                chains[chain] = []
                            chains[chain].append(o)
                    objs = None
            prnt('vals step7')
            if chains:
                for chain in chains:
                    chain.add_item_to_queue(chains[chain])
            val_block = None
            for v in validators:
                prntDebug('v2',v)
                if v.validatorType == 'Block' and check_consensus:
                    for key in v.data:
                        if not val_block or key.startswith(get_model_prefix('Block')) and val_block.id != key:
                            val_block = Block.objects.filter(id=key).first()
                        prnt('val_block',val_block)
                        if val_block:
                            if v.id not in val_block.validators:
                                val_block.validators[v.id] = get_commit_data(v)
                                val_block.save()
                            if not val_block.validated and len(val_block.validators) >= val_block.get_required_validator_count():
                                if not downstream_worker or testing():
                                    check_validation_consensus(val_block, downstream_worker=downstream_worker, get_missing_blocks=get_missing_blocks)
                                else:
                                    queue = django_rq.get_queue('low')
                                    if not exists_in_worker('check_validation_consensus', val_block, queue):
                                        queue.enqueue(check_validation_consensus, val_block, broadcast_if_unknown=False, get_missing_blocks=get_missing_blocks, job_timeout=300, result_ttl=3600)
                            elif val_block.validated and not v.Block_obj:
                                if v.id in val_block.data and check_commit_data(v, val_block.data[v.id]) or v.id in val_block.validators and check_commit_data(v, val_block.validators[v.id]):
                                    Validator.objects.filter(id=v.id).update(Block_obj=val_block)

            validators.clear()
            
        if userVotes:
            prnt('userVotes...')
            postIds = []
            for v in userVotes:
                if v.postId not in postIds:
                    postIds.append(v.postId)
            posts = Post.objects.filter(id__in=postIds)
            for p in posts:
                scoreMe(p)
        if log:
            log.completed()
    except Exception as e:
        prnt('fail process data 9374',str(e))
        if log:
            log.completed(str(e))
    prnt('done process received data databaseUpdated',databaseUpdated)
    if return_updated_objs or return_updated_ids:
        return updated_objs
    elif return_updated_count:
        return updated_count
    return databaseUpdated            
            
def process_data_packet(received_json):
    prnt('---process_data_packet')

    result = process_received_dp(received_json, 'process_data_packet')
    if result and 'dp' in result:
        dp = result['dp']
        received_json = dp.data

    elif result and 'data' in result:
        received_json = result['data']
        dp = None
    else:
        received_json = []
        dp = None

    if dp and isinstance(dp, models.Model):
        if 'completed' in dp.func:
            return 'previously completed'

    if 'node_block_id' in received_json:
        prnt('node_block_id1')
        node_block = Block.objects.filter(id=received_json['node_block_id']).first()
        prnt('node_block_id2',node_block)
        if not node_block:
            prnt('node_block_id3')
            create_job(retrieve_missing_blocks, job_timeout=200, worker='low', genesisId=NodeChain_genesisId, target_node=received_json['senderId'], starting_point=received_json['node_block_id'])
        elif not node_block.validated or node_block.hash != received_json['node_block_hash'] and node_block.validated:
            prnt('node_block_id4')
            create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=node_block.Blockchain_obj, starting_index=node_block.index, send_to=received_json['senderId'])
        elif 'node_block_not_latest' in received_json:
            prnt('node_block_id5')
            pass
        elif node_block and node_block.index != node_block.Blockchain_obj.chain_length:
            prnt('node_block_id6')
            sent_dt = string_to_dt(received_json['dt'])
            latest_node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=sent_dt, validated=True).order_by('-index', 'created').first()
            prnt('node_block_id7 latest_node_block',latest_node_block)
            if latest_node_block and latest_node_block != node_block:
                prnt('node_block_id8')
                create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=latest_node_block.Blockchain_obj, starting_index=node_block.index, send_to=received_json['senderId'])
    else:
        prnt('node_block not included')
    try:
        broadcast_list = json.loads(received_json['broadcast_list'])
    except:
        broadcast_list = []
    updated = False
    prnt('next1')
    if 'type' in received_json and received_json['type'] == 'DataPacket':
        # prnt('received_json',received_json)
        # received_json['senderId']
        sender_node = Node.objects.filter(id=received_json['senderId']).first()
        # if 'self_dict' in received_json:
        #     self_dict = json.loads(received_json['self_dict'])
        #     user = Node.objects.filter(id=self_dict['Node_obj']).first().User_obj
        #     prnt('user',user)
        if sender_node == get_self_node():
            if dp:
                dp.completed()
        else:
            if dp:
                updated = process_received_data(dp, return_updated_count=True, skip_log_check=True)
            else:
                updated = process_received_data(received_json, return_updated_count=True, skip_log_check=True)
            if updated:
                downstream_broadcast(broadcast_list, 'blockchain/receive_data_packet', received_json, stream=True, exclude=[sender_node.id])
            # elif dp:
            #     dp.func = 'invalid'
            #     dp.save()
        prnt('done process datapacket, updated:',updated)

def process_received_blocks(received_json, get_missing_blocks=True, return_result=False, force_check=False):
    prntn('--process_received_blocks now_utc:',now_utc())
    # prntn('received_json',received_json)
    prnt()
    
    result = process_received_dp(received_json, 'process_received_blocks', override_completed=False)
    # prnt('result3333',result)
    if result and 'dp' in result:
        log = result['dp']
        received_json = log.data
    elif result and 'data' in result:
        received_json = result['data']
        log = None
    else:
        received_json = []
        log = None
    completed = False
    prntn('received_json5555',str(received_json)[:2000])
    if not received_json or 'genesisId' not in received_json:
        if log:
            log.completed('no_data')
        return completed
    if 'node_block_id' in received_json:
        node_block = Block.objects.filter(id=received_json['node_block_id']).first()
        prnt('node_block??',node_block)
        if not node_block:
            create_job(retrieve_missing_blocks, job_timeout=200, worker='low', genesisId=NodeChain_genesisId, target_node=received_json['senderId'], starting_point=received_json['node_block_id'])
        elif not node_block.validated or node_block.hash != received_json['node_block_hash'] and node_block.validated:
            create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=node_block.Blockchain_obj, starting_index=node_block.index, send_to=received_json['senderId'])
        elif 'node_block_not_latest' in received_json:
            pass
        elif node_block and node_block.index != node_block.Blockchain_obj.chain_length:
            sent_dt = string_to_dt(received_json['dt'])
            latest_node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=sent_dt, validated=True).order_by('-index', 'created').first()
            if latest_node_block and latest_node_block != node_block:
                create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=latest_node_block.Blockchain_obj, starting_index=node_block.index, send_to=received_json['senderId'])
    else:
        prnt('node_block not included')

    # from posts.models import sync_model
    # from utils.models import get_or_create_model, sync_model
    blockchain = find_or_create_chain_from_json(genesisId=received_json['genesisId'])
    logEvent(f'process_received_blocks: {blockchain.genesisName}')
    prntDebug('blockchain',blockchain)
    if 'force_check' in received_json:
        force_check = received_json['force_check']
    blocks = {}
    if 'block_list' in received_json:
        # prnt("received_json['block_list']",received_json['block_list'])
        block_list = decompress_data(received_json['block_list'])
        # prnt('\nblock_list',(block_list))
        try:
            block_list = json.loads(block_list)
        except:
            pass
        for b in block_list:
            blocks[b['block_dict']['index']] = b
    else:
        blocks[received_json['block_dict']['index']] = received_json
    prnt('number of blocks',len(blocks))
    from utils.locked import calculate_reward
    for index, b in sorted(blocks.items(), key=operator.itemgetter(0)):
        completed = False
        new_block = b['block_dict']
        prntDebugn('new_block',new_block['id'])
        block_transaction = b['block_transaction']
        prntDebug('block_transaction',block_transaction)
        block = Block.objects.filter(id=new_block['id']).first()
        if block and block.validated and not force_check:
            prnt('block already validated')
            if b['validations']:
                process_received_data(b['validations'], check_consensus=True)
            pass
        else:
            prnt('block not validated or force check',force_check)
            if 'nodeBlockId' in new_block and new_block['nodeBlockId']:
                node_block = Block.objects.filter(id=new_block['nodeBlockId']).first()
                if not node_block:
                    updated_objs = request_items([new_block['nodeBlockId']], return_updated_objs=True, downstream_worker=False)

            if block and block.hash != new_block['hash']:
                block = blockchain.create_block(block_dict=b, dummy_block=block)
            signature_verified = False
            prev_block = Block.objects.filter(blockchainId=new_block['blockchainId'], hash=new_block['previous_hash'], validated=True).first()
            prnt('prev_block',prev_block)
            if prev_block and prev_block.index+1 == int(new_block['index']) or int(new_block['index']) == 1 and new_block['previous_hash'] == '0000000':
                if block and not block.validation_error:
                    signature_verified = True
                else:
                    signature_verified = get_user(public_key=new_block['publicKey']).verify_sig(get_signing_data(new_block), new_block['signature'])
                prntDebug('signature_verified',signature_verified)
            elif not prev_block:
                prnt(f'prev_block not found11-- blockchain.chain_length:{blockchain.chain_length}, new_block_index:{new_block["index"]}, get_missing_blocks:{get_missing_blocks}')
                last_block = blockchain.get_last_block(is_validated=True, do_not_return_self=True)
                prnt('last_block',last_block, 'index',last_block.index if last_block else 0)
                if not last_block:
                    if get_missing_blocks:
                        create_job(retrieve_missing_blocks, job_timeout=200, worker='low', blockchain=blockchain, target_node=received_json['senderId'], starting_point=blockchain.chain_length)
                elif last_block.index <= int(new_block['index']) - 1:
                    if get_missing_blocks:
                        create_job(retrieve_missing_blocks, job_timeout=200, worker='low', blockchain=blockchain, target_node=received_json['senderId'], starting_point=last_block.index)
                elif last_block.index >= int(new_block['index']):
                    create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=blockchain, starting_index=int(new_block['index']), send_to=received_json['senderId'])
                if log:
                    log.completed('received_blocks_missing_prev_block')
                return False
            elif prev_block and prev_block.index < int(new_block['index']) - 1:
                if get_missing_blocks:
                    create_job(retrieve_missing_blocks, job_timeout=200, worker='low', blockchain=blockchain, target_node=received_json['senderId'], starting_point=prev_block.hash)
                if log:
                    log.completed('received_blocks_retrieve_missing')
                return False
            elif prev_block and prev_block.index >= int(new_block['index']):
                create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=blockchain, starting_index=int(new_block['index']), send_to=received_json['senderId'])
                if log:
                    log.completed('received_blocks_send_missing')
                return False
            elif prev_block and prev_block.index == int(new_block['index']):
                prntDebug('sort out competeing blocks')
                winning_block, validations = resolve_block_differences(block)
                if not winning_block:
                    if log:
                        log.completed('competing_block_p2')
                    return False 
                if winning_block != block:
                    block = winning_block
                    create_job(send_missing_blocks, job_timeout=60, worker='main', blockchain=blockchain, starting_index=int(new_block['index']), send_to=received_json['senderId'])
                else:
                    if block and not block.validation_error:
                        signature_verified = True
                    else:
                        signature_verified = get_user(public_key=new_block['publicKey']).verify_sig(get_signing_data(new_block), new_block['signature'])
                    prntDebug('signature_verified22',signature_verified)
            else:
                prnt('prev_block not found22')    
            
            if signature_verified:
                if b['validations']:
                    process_received_data(b['validations'], check_consensus=False)
                if not block or block.validation_error:
                    block = blockchain.create_block(block_dict=b, dummy_block=block)
                if block: 
                    prntDebug('opt 1')
                    proceed_to_check_consensus = True
                    if not block_transaction:
                        prntDebug('no reward')
                        proceed_to_check_consensus = True
                        transaction = None
                    else:
                        prntDebug('process reward')
                        proceed_to_check_consensus = False
                        if block_transaction['token_value'] == calculate_reward(block_transaction['created']):
                            transaction_signature_verified = get_user(public_key=block_transaction['publicKey']).verify_sig(get_signing_data(block_transaction), block_transaction['signature'])
                            prntDebug('transaction_signature_verified',transaction_signature_verified)
                            if transaction_signature_verified:
                                # reward_signature_verified = get_user(public_key=block_transaction['receiver_block']['publicKey']).verify_sig(get_signing_data(block_transaction['receiver_block']), block_transaction['receiver_block']['signature'])
                                # prnt('reward_signature_verified',reward_signature_verified)
                                # if reward_signature_verified:
                                    # receiverBlock = Block.objects.filter(id=block_transaction['receiver_block']['id']).first()
                                    # if not receiverBlock:
                                    #     receiverBlock = blockchain.create_block(block_dict=block_transaction['receiver_block'])
                                transaction = get_or_create_model('UserTransaction', id=block_transaction['id'])
                                transaction, proceed_to_check_consensus, transaction_updatedDB = sync_model(transaction, block_transaction)


                    prntDebug('proceed_to_check_consensus',proceed_to_check_consensus, block.id)
                    if proceed_to_check_consensus:
                        block_is_valid, consensus_found, validations = check_validation_consensus(block, backcheck=force_check, get_missing_blocks=get_missing_blocks)
                        prntDebug('-a-a-block_is_valid',block_is_valid,'consensus_found',consensus_found)
                        if not block_is_valid and consensus_found and block.id != sorted(blocks.items(), key=operator.itemgetter(0))[-1][1]['block_dict']['id']:
                            prntDebug('send_missing_blocks path 1')
                            send_missing_blocks(blockchain=blockchain, starting_index=block.index-1, send_to=received_json['senderId'])   
                            if log:
                                log.completed('invalid')
                            return False
                        else:
                            prntDebug('process_received_blocks path 2::',sorted(blocks.items(), key=operator.itemgetter(0))[-1][1]['block_dict']['id'])
                            if force_check and block_is_valid and consensus_found and block.id == sorted(blocks.items(), key=operator.itemgetter(0))[-1][1]['block_dict']['id']:
                                next_block = Block.objects.filter(blockchainId=blockchain.id, previous_hash=block.hash, validated=True).first()
                                prntDebug('next_block',next_block)  
                                if next_block:
                                    block_is_valid, consensus_found, validations = check_validation_consensus(next_block, backcheck=True, get_missing_blocks=get_missing_blocks)
                                    prntDebug('-a-a-block_is_valid-222',block_is_valid,'consensus_found',consensus_found)
                            if block_is_valid and consensus_found:
                                completed = True


                        
    if log:
        log.completed()
    return completed


def resolve_block_differences(block, competing_blocks=None):
    prnt('--resolve_block_differences')
    if not competing_blocks:
        competing_blocks = Block.objects.filter(blockchainId=block.blockchainId, index=block.index, validated=True).order_by('DateTime','created')
    if any(cBlock.id != block.id for cBlock in competing_blocks):

        earliest_block = competing_blocks[0]
        validation_set = {}
        is_valid = False
        proceed = False
        block_list = [earliest_block]
        for block in competing_blocks:
            if block.id != earliest_block.id:
                proceed = True
                block_list.append(block)

        if proceed:
            for competing_block in block_list:
                is_valid, consensus_found, validations = check_validation_consensus(competing_block, do_mark_valid=False, handle_discrepancies=False)
                validation_set[competing_block.id] = validations
                if is_valid or not consensus_found:
                    if competing_block != earliest_block:
                        if competing_block.validated and not earliest_block.validated or not earliest_block.validated and not consensus_found:
                            if competing_block.DateTime > earliest_block.DateTime:
                                pass
                            elif competing_block.DateTime < earliest_block.DateTime:
                                earliest_block = competing_block
                            elif competing_block.created > earliest_block.created:
                                pass
                            elif competing_block.created < earliest_block.created:
                                earliest_block = competing_block
            # if is_valid:
            for block in block_list:
                if block != earliest_block:
                    # block.delete(superDel=True)
                    block.is_not_valid(mark_strike=False, note=f'resolved_differences-:{earliest_block.id}')
        if not validation_set:
            is_valid, consensus_found, validations = check_validation_consensus(earliest_block, do_mark_valid=False, handle_discrepancies=False)
            validation_set[earliest_block.id] = validations
            # if is_valid:
        winning_block = earliest_block
        prnt('initial block',block.id,'winning_block',winning_block.id)
        logEvent(f'resolve_block_differences: initial block:{block.id},winning_block:{winning_block.id}')
        return winning_block, validation_set[winning_block.id]
    logEvent(f'error resolving_block_differences: block:{block.id}, competing_blocks:{len(competing_blocks)}', log_type='Errors')
    return None, []

def retrieve_missing_blocks(blockchain=None, genesisId=None, target_node=None, starting_point=0):
    if not blockchain and genesisId:
        blockchain = Blockchain.objects.filter(genesisId=genesisId).first()
    prntDebugn('--retrieve_missing_blocks- chainid:', blockchain)
    logEvent(f'retrieve_missing_blocks, chain: {blockchain.id if blockchain else 0}, starting_point:{starting_point}, target_node: {target_node}')

    relevant_nodes = get_relevant_nodes_from_block(genesisId=blockchain.genesisId)
    if target_node and not target_node in relevant_nodes:
        n = Node.objects.filter(id=target_node).first()
        if n and n.activated_dt:
            relevant_nodes[target_node] = n.return_address()
        else:
            target_node = random.choice([n for n in relevant_nodes])
    elif not target_node:
        target_node = random.choice([n for n in relevant_nodes])

    value = relevant_nodes[target_node]
    relevant_nodes.pop(target_node)
    relevant_nodes = {target_node: value, **relevant_nodes}

    operatorData = get_operatorData()
    self_node = get_self_node(operatorData=operatorData)

    if not starting_point or is_id(starting_point):
        starting_point = blockchain.chain_length
    elif not isinstance(starting_point, int):
        start_block = Block.objects.filter(blockchainId=blockchain.id, hash=starting_point, validated=True).first()
        starting_point = start_block.index

    prev_blocks = Block.objects.filter(blockchainId=blockchain.id, index__lte=starting_point, index__gt=starting_point-20, validated=True).order_by('index')
    hash_history = []
    if prev_blocks:
        hash_history = [b.hash for b in prev_blocks]

    userData = json.dumps(operatorData['userData'])
    selfNode = json.dumps(convert_to_dict(self_node))

    signedRequest = json.dumps(sign_for_sending({'type':'Block', 'blockchainId' : blockchain.id, 'genesisId':blockchain.genesisId, 'include_content' : False, 'force_check':True, 'include_validators':True, 'items': 3, 'hash_history':hash_history, 'index':starting_point}))
    prntn('signedRequest',signedRequest)
    sendingData = {'userData':userData, 'nodeData':selfNode, 'request':signedRequest}

    content = create_post_header(data=sendingData, operatorData=operatorData, self_node=self_node, post='post')
    successes = 0
    for nodeId, ip in relevant_nodes.items():
        if nodeId != self_node.id:
            received_data = None
            success, response = connect_to_node(ip, 'blockchain/request_data', self_node=self_node, content=content, operatorData=operatorData)

            print('connect success',success)
            if success and response.status_code == 200:
                response_json = response.json()
                prntn('response_json666',str(response_json)[:500])    
                if response_json['message'] == 'Success' and 'block_obj' in response_json:
                    block_list = json.dumps([{'block_dict' : response_json['block_obj'], 'block_transaction':response_json['transaction_obj'], 'block_data' : [], 'validations' : response_json['content']}])
                    received_data = {'type' : 'Blocks', 'blockchainId' : blockchain.id, 'genesisId':blockchain.genesisId, 'block_list' : block_list, 'force_check':True, 'end_of_chain' : response_json['end_of_chain']}
                elif response_json['message'] == 'Success' and 'block_list' in response_json:
                    received_data = response_json

                if received_data:
                    received_data['senderId'] = nodeId
                    received_data = sign_for_sending(received_data, operatorData=operatorData)

                    iden = hash_obj_id('DataPacket', specific_data=received_data)
                    dp = DataPacket.objects.filter(id=iden).first()
                    if not dp:
                        dp = DataPacket(id=iden, func='process_received_blocks', created = now_utc(), data=received_data)
                        dp.save()

                    # iden = hash_obj_id('EventLog', specific_data=received_data)
                    # log = EventLog.objects.filter(id=iden).first()
                    # if not log:
                    #     log = EventLog(id=iden, type='process_received_blocks', data=received_data)
                    #     log.Node_obj = self_node
                    #     log.save()

                    if process_received_blocks(dp, get_missing_blocks=False, return_result=True, force_check=True):
                        if response_json['end_of_chain'] == 'False':
                            create_job(retrieve_missing_blocks, job_timeout=200, worker='low', blockchain=blockchain, starting_point=int(received_data['index'])+1)
                            successes += 1
                        else:
                            break
                else:
                    prnt('pass node, retrieve_missing_blocks 23595', response_json)
    return successes

def send_missing_blocks(blockchain=None, genesisId=None, missing_blocks=None, starting_index=1, send_to=''):
    if not blockchain and genesisId:
        blockchain = Blockchain.objects.filter(genesisId=genesisId).first()
    prntn('send_missing_blocks')
    from utils.locked import verify_obj_to_data
    operatorData = get_operatorData()
    self_node = get_self_node(operatorData=operatorData)
    success = False
    if send_to and send_to != self_node.id:

        node_block = None
        json_data = {'type' : 'Block', 'packet_id':hash_obj_id('DataPacket'), 'senderId':self_node.id, 'broadcast_list': [], 'blockchainId' : blockchain.id, 'genesisId':blockchain.genesisId, 'block_list' : [], 'force_check':True}
        sending_blocks = []
        if not missing_blocks:
            if isinstance(starting_index, int):
                missing_blocks = Block.objects.filter(blockchainId=blockchain.id, index__gte=starting_index, validated=True).defer("data").order_by('index')[:10]
            elif is_id(starting_index):
                block = Block.objects.filter(id=starting_index).first()
                if not block:
                    return
                missing_blocks = Block.objects.filter(blockchainId=blockchain.id, index__gte=block.index-5, validated=True).defer("data").order_by('index')[:10]

        for return_block in missing_blocks:
            if verify_obj_to_data(return_block, return_block):
                if return_block.index == starting_index or return_block.id == starting_index:
                    node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, DateTime__lte=return_block.DateTime, validated=True).order_by('-index', 'created').first() 

                validations = Validator.objects.filter(validatorType='Block', blockchainId=return_block.blockchainId, data__has_key=return_block.id)
                validator_list = [convert_to_dict(v) for v in validations if verify_obj_to_data(v, v)]
                # data, not_found, not_valid = get_data(return_block.data, include_related=False)
                sending_blocks.append({'block_dict' : convert_to_dict(return_block), 'block_transaction':return_block.get_transaction_data(), 'block_data' : [], 'validations' : validator_list})
            break
        
        if sending_blocks:

            sending_blocks = json.dumps(sending_blocks)
            prntn('sending_blocks',str(sending_blocks)[:1000])
            if len(sending_blocks) > 1:
                sending_blocks = compress_data(sending_blocks)
            json_data['block_list'] = sending_blocks
            if not node_block:
                node_block = Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, validated=True).order_by('-index', 'created').first() 
            if node_block:
                json_data['node_block_id'] = node_block.id
                json_data['node_block_hash'] = node_block.hash
                if node_block.index != node_block.Blockchain_obj.chain_length:
                    json_data['node_block_not_latest'] = True
            json_data = sign_for_sending(json_data, operatorData=operatorData)
            
            success, response = connect_to_node(get_node(id=send_to), 'blockchain/receive_blocks', json_data, operatorData=operatorData, self_node=self_node)
            logEvent(f'send_missing_blocks to: {send_to}, result:{success}')
    return success




def send_for_validation(log=None, gov=None):
    # from blockchain.models import get_scraperScripts, get_scraping_order, convert_to_dict, connect_to_node, get_self_node, get_operatorData,DataPacket,logError,logEvent,sign_for_sending
    prnt('--send_for_validation() now_utc:',now_utc(), gov, log)
    job_time = None
    job_id = None
    completed = False
    obj_list = []
    func = None
    items = []
    q = 0
    if is_id(log):
        log = DataPacket.objects.filter(id=log).first()
    if not log:
        prnt('no log')
        return False
    if 'process' not in log.func and 'scrape' not in log.func:
        prnt('job completed')
        return None
    if isinstance(log, list):
        q = 1
        items = log
    elif isinstance(log, models.Model):
        if log.object_type == 'DataPacket':
            # from utils.models import get_all_objects
            if 'shareData' in log.data and log.data['shareData']:
                items = get_all_objects(log.data['shareData'])
                prnt('func1:',func)
            elif 'content' in log.data and log.data['content']:
                # from blockchain.models import process_received_dp
                content = process_received_dp(log.data['content'], 'send_for_validation')
                items = get_all_objects(content)
                prnt('func2:',func)

            if not gov and 'gov_id' in log.data:
                from legis.models import Government
                gov = Government.objects.filter(id=log.data['gov_id']).first()
            q = 2
            if 'created' in log.data:
                job_time = string_to_dt(log.data['created'])
            job_id = log.id
            func = log.data['func']

        else:
            q = 3
            items = [log]
    try:
        start_len = len(items)
    except:
        start_len = 'x'
    if not job_time:
        # from blockchain.models import round_time
        job_time = round_time(dt=now_utc(), dir='down', amount='hour')
    logEvent(f'--send_for_validation initial func:{func} log:{log.id if log else"none"} q:{q} items:{len(items)}, start_len:{start_len}', log_type='Tasks', code='9046')
    if items and 'post_processed' in log.notes and log.notes['post_processed']:
        for i in items:
            # if not job_time or has_field(i, 'added') and i.added and i.added < job_time:
            #     job_time = i.added
            if not gov and has_field(i, 'Government_obj') and i.Government_obj:
                gov = i.Government_obj
            if gov:
                break
        if not gov:
            from legis.models import Government
            for i in items:
                if not gov and has_field(i,'Region_obj') and i.Region_obj:
                    gov = Government.objects.filter(Region_obj=i.Region_obj).first()
                    if gov:
                        break
        operatorData = get_operatorData()
        self_node = get_self_node(operatorData=operatorData)
        creator_nodes, validator_nodes = get_node_assignment(dt=job_time, func=func, chainId=gov.Region_obj.id, strings_only=False)
        # validator_node = get_scraping_order(dt=job_time, chainId=gov.Region_obj.id, func_name=func, validator_only=True)
        
        obj_list = [convert_to_dict(obj) for obj in items if obj.signature]
        if log:
            packet_id = log.id
        else:
            packet_id = hash_obj_id('DataPacket', specific_data=str(obj_list))
        # compressed_data = compress_data(obj_list)
        compressed_data = json.dumps(obj_list)

        sending_data = {'type':'for_validation', 'packet_id':packet_id, 'job_id':job_id, 'job_dt':dt_to_string(job_time), 'func':func, 'senderId':self_node.id, 'gov_id':gov.id, 'gov_level':gov.gov_level, 'scrapers':[s for s in scrapers], 'validator':validator_node_id, 'region_dict':json.dumps(convert_to_dict(gov.Region_obj)), 'content': compressed_data}
        
        sending_data = sign_for_sending(sending_data)
        c = completed
        for node in validator_nodes:
            c, response = connect_to_node(node, 'blockchain/receive_posts_for_validating', sending_data, operatorData=operatorData, stream=True)
            completed = completed or c
            logEvent(f'send_for_validation COMPlet func:{func} log:{log.id if log else"none"}, val_node:{str(node)} gov:{gov}', log_type='Tasks', code='5434')
        if log:
            log.refresh_from_db(fields=['func'])
            log.data = sending_data
            log.notes['post_processed'] = True
            log.save()
    elif items:
        prnt('length', len(items))
        for i in items:
            # if not job_time or has_field(i, 'added') and i.added and i.added < job_time:
            #     job_time = i.added
            if not gov and has_field(i, 'Government_obj') and i.Government_obj:
                gov = i.Government_obj
            if gov:
                break
        if not gov:
            from legis.models import Government
            for i in items:
                if not gov and has_field(i,'Region_obj') and i.Region_obj:
                    gov = Government.objects.filter(Region_obj=i.Region_obj).first()
                    if gov:
                        break
            
        logEvent(f'send_for_validation func:{func} log:{log.id if log else"none"} gov:{gov} items:{len(items)}', log_type='Tasks', code='5432')
        if func == 'get_user_region':
            # get_user_region is initiated by user and scraping_order does not apply
            # send as background process, user is waiting for result of scraper
            # downstream_broadcast
            pass
        elif job_time:
            operatorData = get_operatorData()
            scraperScripts = get_scraperScripts(gov)
            approved_models = scraperScripts.approved_models
            
            model_types = []
            approved_funcs = []
            exceptions = ['Update', 'Notification']
            for i in items:
                if not i or not isinstance(i, models.Model):
                    items.remove(i)
                elif i.object_type not in model_types:
                    if i.object_type == 'Update' and get_pointer_type(i.pointerId) not in model_types:
                        model_types.append(get_pointer_type(i.pointerId))
                    elif i.object_type not in exceptions:
                        model_types.append(i.object_type)
            for key, value in approved_models.items():
                result = all(item in value for item in model_types)
                if result:
                    approved_funcs.append(key)
            prnt('func', func)
            prnt('approved funcs', approved_funcs)
            prntDev('itemslen',len(items))
            if func in approved_funcs:
                creator_nodes, validator_nodes = get_node_assignment(dt=job_time, func=func, chainId=gov.Region_obj.id, strings_only=False)
                # scraper_list, approved_models = get_scrape_duty(gov, job_time)
                # scrapers, validator_node_id = get_scraping_order(dt=job_time, chainId=gov.Region_obj.id, func_name=func)
                prnt('validator_nodes',str(validator_nodes))
                if validator_nodes:
                    validator_node = validator_nodes[0]
                    # validator_node_id = validator_node.id
                try:
                    self_node = get_self_node(operatorData=operatorData)
                    prnt('self_node', self_node)
                    processed_data = {'obj_ids':[],'hashes':{}}
                    for i in items:
                        proceed = True
                        if has_method(i, 'required_for_validation'):
                            for c in i.required_for_validation():
                                if not getattr(i, c):
                                    proceed = False
                                    break
                        if proceed:
                            processed_data['obj_ids'].append(i.id)
                            if True == False:
                                ...
                            elif not is_locked(i):
                                # prntDev(i.object_type)
                                i.func = func
                                i.creatorNodeId = self_node.id
                                i.validatorNodeId = validator_node.id
                                if not has_field(i, 'is_modifiable'):
                                    i.created = job_time
                                obj, err = sign_obj(i, operatorData=operatorData, return_error=True)
                                if obj.signature and not err:
                                    obj_list.append(convert_to_dict(obj))
                    if obj_list:
                        if len(creator_nodes) == 1 or validator_node.id != self_node.id:
                            # posts = Post.objects.filter(pointerId__in=processed_data['obj_ids'])
                            # for p in posts:
                            #     p = update_post(p=p)
                            # if log:
                            #     log.save()

                            prntDev('sending for validation...')
                            prntDev('len(data)',len(obj_list))
                            if log:
                                packet_id = log.id
                            else:
                                packet_id = hash_obj_id('DataPacket', specific_data=str(obj_list))

                            # compressed_data = compress_data(obj_list)
                            compressed_data = json.dumps(obj_list)

                            

                            sending_data = {'type':'for_validation', 'packet_id':packet_id, 'job_id':job_id, 'job_dt':dt_to_string(job_time), 'func':func, 'senderId':self_node.id, 'gov_id':gov.id, 'gov_level':gov.gov_level, 'scrapers':[s for s in scrapers], 'validator':validator_node_id, 'region_dict':json.dumps(convert_to_dict(gov.Region_obj)), 'content_length':len(obj_list), 'content': compressed_data}
                            
                            sending_data = sign_for_sending(sending_data)

                            completed, response = connect_to_node(validator_node, 'blockchain/receive_posts_for_validating', sending_data, operatorData=operatorData, stream=True)
                            # completed = completed or c
                            logEvent(f'send_for_validation COMPlet func:{func} log:{log.id if log else"none"}, val_node:{str(validator_node)}, gov:{gov}', log_type='Tasks', code='764')
                            if log:
                                log.refresh_from_db(fields=['func'])
                                log.data = sending_data
                                log.notes['post_processed'] = True
                                log.save()
                        else:
                            completed = True
                            prnt('skipping sending to self')
                        
                except Exception as e:
                    prnt('fail987542', str(e))
                    logError('failed to send for validation', code='98274',func='send_for_validation',extra={'err':str(e),"log":log.id if log else'none'})
    else:
        try:
            ix = log.data['shareData']
        except Exception as e:
            ix = str(e)
        logEvent(f'send_for_validation func:{func} log:{log.id if log else"none"} gov:{gov} items:no-items, shareData:{ix}', log_type='Tasks', code='127')
    prnt('finish up...')
    if log:
        if completed or len(items) == 0 or log.created < now_utc() - datetime.timedelta(hours=24):
    # if log and completed or log and not obj_list:
            try:
                log.completed(completed='scrape')
            except Exception as e:
                prnt('fail086421',str(e))
    return completed



def assess_received_header(header, return_is_self=False, if_self_active=False):
    prnt('--assess_received_header')
    dt = string_to_dt(header.get('dt'))
    now = now_utc()
    try:
        if dt >= now - datetime.timedelta(seconds=30) and dt < now + datetime.timedelta(seconds=2):
            senderId = header.get('senderid')
            # senderId = request.META.get('HTTP_SENDERID')
            prnt('senderId',senderId)
            sender_node = get_node(id=senderId)
            prnt('sender_node',sender_node)
            if sender_node and not sender_node.expelled and sender_node.User_obj.verify_sig(header.get('dt'), header.get('dtsig'), simple_verify=True):
                prnt('-good')
                if if_self_active and not get_self_node().activated_dt:
                    return False
                elif return_is_self:
                    if sender_node == get_self_node():
                        return True
                    else:
                        return False
                sender_node.accessed()
                return True
            else:
                prnt('failed sig')
            if not sender_node and Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, validated=True).count() == 0:
                prnt('pass for initial setup')
                return True
            elif is_debug():
                prntDebug('sender_node',sender_node, 'node_block_count',Block.objects.filter(Blockchain_obj__genesisId=NodeChain_genesisId, validated=True).count())
        else:
            prnt('failed dt',dt, now)
    except Exception as e:
        prnt('fail864',str(e))
    prnt('failed assess header')
    return False

def create_post_header(data={}, operatorData=None, self_node=None, post='post'):
    headers = {}
    if post:
        if not operatorData:
            operatorData = get_operatorData()
        if not self_node:
            self_node = get_self_node(operatorData=operatorData)
        now = dt_to_string(now_utc())
        if isinstance(data, dict):
            data = json.dumps(data)
        from utils.locked import simpleSign
        sig = simpleSign(operatorData['privKey'], str(now))
        if post == 'stream':
            content_length = len(data.encode('utf-8'))
            headers = {'Content-Type': 'application/json','Transfer-Encoding': 'chunked'}
            if device_system == 'mac' and testing():
                headers['Content-Length'] = str(content_length)
            headers['senderId'] = self_node.id
            headers['dt'] = now
            headers['dtsig'] = sig
            # prnt('header to send',headers)
        else:
            headers = {'Content-Type': 'application/json'}
            headers['senderId'] = self_node.id
            headers['dt'] = now
            headers['dtsig'] = sig
    return {'body':data, 'headers':headers}

def connect_to_node(node, url, data=None, self_node=None, content={}, operatorData=None, timeout=(5,10), get=False, stream=False, node_is_string=False, log_reponse_time=True):
    prnt('---connect to node---', node, url, now_utc(),stream)
    response = None
    try:
        start_time = None
        if node_is_string:
            ip = node
            node = None
        elif is_id(node):
            node = Node.objects.filter(id=node).first()
            ip = node.return_address()
        elif isinstance(node, str):
            ip = node
            node = Node.objects.filter(ip_address=ip).first()
        elif isinstance(node, models.Model):
            ip = node.return_address()
        if node_is_string or node and not node.suspended_dt or ip:
            if url.startswith('/'):
                url = url[1:]
            if not operatorData:
                operatorData = get_operatorData()
            if isinstance(node, models.Model):
                if operatorData and 'local_nodeId' in operatorData and operatorData['local_nodeId'] == node.id:
                    ip = f'127.0.0.1:{ip[ip.find(":")+1:]}'
            elif operatorData and 'local_nodeId' in operatorData and operatorData['local_nodeId'] and operatorData['local_nodeId'] in operatorData['myNodes']:
                full_nodeData = operatorData['myNodes'][operatorData['local_nodeId']]
                if full_nodeData and ip == full_nodeData['nodeData']['ip_address']:
                    ip = full_nodeData['settings']['localhost']
            prnt('ip',ip)
            start_time = time.time()
            if get:
                prnt('sending get from server...',ip,now_utc())
                response = requests.get('http://' + ip + '/' + url, timeout=timeout)
            else: 
                def data_iterator(json_data, chunk_size=1024 * 1024):  # 1 MB chunks
                    for i in range(0, len(json_data), chunk_size):
                        yield json_data[i:i + chunk_size].encode('utf-8')
                if not content:
                    post_type = 'get' if get else 'stream' if stream else 'post'
                    content = create_post_header(data=data, operatorData=operatorData, self_node=self_node, post=post_type)
                if stream:
                    response = requests.post('http://' + ip + '/' + url, data=data_iterator(content['body']), headers=content['headers'], timeout=(5,20))
                else:
                    response = requests.post('http://' + ip + '/' + url, data=content['body'], headers=content['headers'], timeout=timeout)
            elapsed_time = time.time() - start_time
            prnt('post connection', f"{int(elapsed_time // 60):02}:{int(elapsed_time % 60):02}") 
            if response.status_code == 200 and 'message' in response.json():
                prnt('success connection')
                if log_reponse_time:
                    node.accessed(response_time=response.elapsed.total_seconds(), self_node=self_node)
                else:
                    node.accessed(self_node=self_node)
                return True, response
            else:
                prnt('-connect fail',str(response.content)[:650])
                if node:
                    node.add_failure(note=url, self_node=self_node)
                return False, response
        else:
            return False, None
    except Exception as e:
        if start_time:
            elapsed_time = time.time() - start_time
            prnt('connect to node fail03786213',str(e), f"{int(elapsed_time // 60):02}:{int(elapsed_time % 60):02}") 
        else:
            prnt('connect to node fail5609781',str(e))
        # node.add_failure()
        return False, response
    

def downstream_broadcast(broadcast_list, url, sendingData, operatorData=None, self_node=None, target_node_id=None, skip_self=False, stream=False, exclude=[]):
    prnt('downstream broadcast now_utc:', now_utc(), url, broadcast_list)
    from django.db.models import Model
    if not isinstance(sendingData, dict):
        sendingData = json.loads(sendingData)
    if not operatorData:
        operatorData = get_operatorData()
    if not self_node:
        self_node = get_self_node(operatorData=operatorData)
    total_successes = 0
    if not target_node_id:
        target_node_id = self_node.id
    prnt('target_node_id',target_node_id)
    attemped_nodes = []
    def func(peer_nodes, content={}):
        prntDebug('func', peer_nodes)
        successes = 0
        if not isinstance(peer_nodes[0], Model):
            if 'So' in str(peer_nodes[0]):
                peer_nodes = Node.objects.filter(id__in=peer_nodes)
            else:
                peer_nodes = Node.objects.filter(ip_address__in=peer_nodes)
        for node in peer_nodes:
            if node.id not in exclude:
                if not node.suspended_dt and node.activated_dt and node not in attemped_nodes:
                    attemped_nodes.append(node)
                    if skip_self and node == self_node:
                        success = True
                    else:
                        success, response = connect_to_node(node, url, self_node=self_node, content=content, operatorData=operatorData, stream=stream)
                    if success:
                        successes += 1
                    elif node.id != target_node_id:
                        try:
                            s = func(broadcast_list[node.id])
                            successes += s
                        except Exception as e:
                            prnt('fali05834',str(e))
                            # prnt(broadcast_list[node.id])
                elif node not in attemped_nodes and node.id in broadcast_list:
                    attemped_nodes.append(node)
                    try:
                        s = func(broadcast_list[node.id])
                        successes += s
                    except Exception as e:
                        prnt('fail592374',str(e))
                elif node == self_node:
                    successes += 1
        return successes
    
    if isinstance(target_node_id, list):
        prntDebug('db1')
        content = create_post_header(data=sendingData, operatorData=operatorData, self_node=self_node, post='stream' if stream else 'post')
        for target_id in target_node_id:
            prntDebug('db1.1',target_id)
            if target_id in broadcast_list:
                prntDebug('db1.2')
                peers = broadcast_list[target_id]
                s = func(peers, content=content)
                total_successes += s

    elif target_node_id in broadcast_list:
        prntDebug('db2')
        content = create_post_header(data=sendingData, operatorData=operatorData, self_node=self_node, post='stream' if stream else 'post')
        peers = broadcast_list[target_node_id]
        s = func(peers, content=content)
        total_successes += s
    return total_successes

def node_ai_capable():
    # when declaring self_node ai_capable, an already established ai_capable node
    # should test the response, should be a simple prompt that it's own ai can verify
    # should also return response in a reasonable time. if good, validate, share validation
    pass



def process_received_validations_old(received_json):
    prnt('--process_received_validation')
    if isinstance(received_json, str) and get_pointer_type(received_json) == 'EventLog':
        log = EventLog.objects.filter(id=received_json).first()
        if not log:
            return None
        received_json = log.data
    elif isinstance(received_json, models.Model) and received_json.object_type == 'EventLog':
        log = received_json
        received_json = log.data
    else:
        log = None
    if log and 'completed' in log.type:
        return None 
    broadcast_list = json.loads(received_json['broadcast_list'])
    prntDebug('broadcast_list',broadcast_list)
    prntDebug('received_json',received_json)
    if 'type' in received_json and received_json['type'] == 'Validations' and 'block_list' in received_json:
        block_list = json.loads(received_json['block_list'])
        process_received_blocks(received_json)
        for b in block_list:
            prntDebug('----b',str(b)[:500])
            databaseUpdated = process_received_data(b['validations'], check_consensus=False)
            prntDebug('-a-a-databaseUpdated:',databaseUpdated)
            if databaseUpdated:
                prntDebug('--rebroadcasting received validation after alleged database update')
                downstream_broadcast(broadcast_list, 'blockchain/receive_validations', received_json)
                # # block_data = json.loads(b['block_dict'])
                block = Block.objects.filter(id=b['block_dict']['id']).first()
                prntDebug('-a-a-block',block)
                if block:
                    # process_received_blocks(b)
                    # block = Block.objects.filter(id=b['block_dict']['id']).first()
                    if not block.validated:
                        check_validation_consensus(block)
    if log:
        log.completed()


# not used ?
def broadcast_validation_old(block=None, broadcast_list=None, validator_list=None, validations=None):
    prnt('---broadcast_validation funct-------',block)
    # broadcast only to validators if received validator_list
    if is_id(block):
        block = get_dynamic_model(block, id=block)
    if not broadcast_list:
        # starting_nodes, broadcast_list, returned_validator_list = get_node_assignment(block, strings_only=True)
        creator_nodes, broadcast_list, validator_list = block.get_assigned_nodes()
    if not validations:
        validations = [convert_to_dict(v) for v in Validator.objects.filter(data__has_key=block.id)]
    else:
        validations = [convert_to_dict(v) for v in validations]

    self_node = get_self_node()
    json_data = {'type' : 'Validations', 'packet_id':hash_obj_id('DataPacket'), 'senderId' : self_node.id, 'broadcast_list': json.dumps(broadcast_list), 'blockchainId' : block.blockchainId, 'genesisId':block.Blockchain_obj.genesisId, 'block_list' : json.dumps([{'block_dict' : convert_to_dict(block), 'block_transaction':block.get_transaction_data(), 'block_data' : [], 'validations' : validations}])}
    successes = downstream_broadcast(broadcast_list, 'blockchain/receive_validations', json_data, target_node_id=validator_list)
    if successes >= len(broadcast_list[self_node.id]) or successes >= Node.objects.exclude(activated_dt=None).filter(supportedChains_array__contains=[block.blockchainId], suspended_dt=None).count():

        for v in validations:
            if v['CreatorNode_obj'] == self_node.id:
                toBroadcast(v['id'], remove_item=True)



# I think not used
def get_latest_node_data_old(sort='-last_updated'):
    json_data = {'nodes' : [], 'deactivated' : [], 'last_accessed' : [], 'recent_failures' : []}
    active_nodes = Node.objects.exclude(activated_dt=None).filter(suspended_dt=None)
    for n in active_nodes:
        json_data['nodes'].append(convert_to_dict(n))
    deactivated_nodes = Node.objects.exclude(suspended_dt=None).order_by('-suspended_dt')
    for n in deactivated_nodes:
        json_data['deactivated'].append(convert_to_dict(n))
    last_accessed = NodeReview.objects.exclude(accessed=None).order_by('-created')
    for n in last_accessed:
        json_data['last_accessed'].append(convert_to_dict(n))
    recent_failures = NodeReview.objects.filter(last_fail__gte=now_utc() - datetime.timedelta(days=recent_failure_range)).order_by('-created')
    for n in recent_failures:
        json_data['recent_failures'].append(convert_to_dict(n))
    return json_data


def return_test_result(log):
    from posts.models import Post
    prnt('\nreturn_test_result')
    isTest = testing()
    # shareData = log.data['shareData']
    # prnt('shareData:',shareData)
    # get_data(log.data['shareData'])
    storedModels, not_found, not_valid = get_data(log.data['shareData'], return_model=True, include_related=False, verify_data=False)
    mb = 0
    if storedModels:
        for i in storedModels:
            if i:
                mb += to_megabytes(i)
                skip = False
                post = None
                if isTest:
                    prnt('\n',i.object_type)
                    try:
                        if i.object_type == 'Update':
                            post = Post.objects.filter(pointerId=i.pointerId).first()
                            if not post:
                                if has_method(i.Pointer_obj, 'create_post'):
                                    post = i.Pointer_obj.create_post()
                                    # post = Post.objects.filter(pointerId=i.pointerId).first()
                                if not post:
                                    skip = True
                            if not skip and post.Update_obj != i:
                                i.sync_with_post(post=post)
                                # if post.Update_obj:
                                #     post.Update_obj.delete()
                                # post.Update_obj = i
                                # post.DateTime = i.DateTime
                                # post.save()
                        else:
                            # prnt('else')
                            if has_method(i, 'create_post'):
                                # prnt('p1')
                                post = Post.all_objects.filter(pointerId=i.id).first()
                                if not post:
                                    post = i.create_post()
                                prnt('post:',post)
                                if post:
                                    # if post:
                                    post.validated = True
                                    post.save()
                                    if has_method(i, 'upon_validation'):
                                        i.upon_validation()
                                # prnt('p2')
                    except Exception as e:
                        prnt('FAIL-return:',str(e))
                        time.sleep(5)
        # log.delete()
    prnt('mb:', mb)
    return f'shareData: {len(storedModels)}, not_found:{len(not_found)}, not_valid:{len(not_valid)}\nMBs: {mb}'


# def process_value(value):
#     if isinstance(value, dict):
#         return sort_for_sign(value)  # Recursively process dictionaries
#     elif isinstance(value, list):
#         # return sorted([process_value(v) for v in value])  # Recursively process lists and sort them
#         return sorted(value, key=lambda v: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v)
#     return stringify_if_bool(value)

# def sort_for_sign(data):
#     if not data:
#         return data
#     if isinstance(data, dict):
#         order_list = [
#             'id', 'object_type', 'modelVersion', 'created', 'created', 'added', 'updated_on_node', 'last_updated', 'func',
#             'creatorNodeId', 'validatorNodeId', 'Validator_obj', 'blockchainId', 'Block_obj', 'publicKey', 'Name', 'Title', 'display_name'
#         ]
#         data = {k: process_value(v) for k, v in data.items()}
#         sorted_dict = dict(sorted(data.items(), key=lambda item: item[0].lower()))
#         starting_dict = {key: sorted_dict.pop(key) for key in order_list if key in sorted_dict}
#         return {**starting_dict, **sorted_dict}
#     else:
#         return data

# # def process_value(value):
# #     if isinstance(value, dict):
# #         return sort_for_sign(value)
# #     elif isinstance(value, list):
# #         return [process_value(v) for v in value]  # Recursively process lists
# #     return stringify_if_bool(value)

# # def sort_for_sign(data):
# #     order_list = [
# #         'id', 'object_type', 'modelVersion', 'created', 'created', 'added', 'updated_on_node', 'last_updated', 'func',
# #         'creatorNodeId', 'validatorNodeId', 'Validator_obj', 'blockchainId', 'Block_obj', 'publicKey', 'Name', 'Title', 'display_name'
# #     ]
# #     data = {k: process_value(v) for k, v in data.items()}
# #     sorted_dict = dict(sorted(data.items(), key=lambda item: item[0].lower()))
# #     starting_dict = {key: sorted_dict.pop(key) for key in order_list if key in sorted_dict}
# #     return {**starting_dict, **sorted_dict}


# # def sort_for_sign(data):
# #     prntDebugn('--sort_for_sign111')
# #     # this is also in node software and default.js, all must match
# #     order_list = ['id','object_type','modelVersion','created','created','added','updated_on_node','last_updated','func',
# #                 'creatorNodeId','validatorNodeId','Validator_obj','blockchainId','Block_obj','publicKey','Name','Title','display_name'
# #                 ]
# #     data = {k:stringify_if_bool(v) for k, v in data.items()}
# #     sorted_dict = dict(sorted(data.items(), key=lambda item: item[0].lower()))
# #     starting_dict = {key: sorted_dict.pop(key) for key in order_list if key in sorted_dict}
# #     return {**starting_dict, **sorted_dict}

# def capitalize(string):
#     if isinstance(string, str):
#         return string[0].upper() + string[1:]
#     return string

# def stringify_if_bool(obj):
#     if isinstance(obj, bool):
#         return capitalize(str(obj))
#     return obj


