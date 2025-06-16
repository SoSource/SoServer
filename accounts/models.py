from django.db import models
# from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import AbstractUser
# from django.utils.text import slugify
from django.db.models import Q
# from django.db.models import Q, Value, F, Avg

# from django.contrib.postgres.fields import ArrayField
from posts.models import get_point_value, Post
from blockchain.models import Blockchain,  EarthChain_genesisId
from transactions.models import Wallet, UserTransaction
# from utils.models import prnt, prntDev, prntDebug, prntn, prntDevn, prntDebugn, debugging, testing, has_field, has_method, is_locked, now_utc, get_pointer_type, initial_save
from utils.models import *
from utils.locked import hash_obj_id, super_id, verify_obj_to_data, get_signing_data, verify_data
import re
import time
import datetime
import wikipedia
import random
import requests
from bs4 import BeautifulSoup
import json
import base64
import decimal
import pytz
import hashlib
import uuid
import django_rq

from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

model_prefixes = {'User':'usr','UserData':'udat',
    'UserPubKey':'upk','UserVerification':'uver','SuperSign':'sup','Notification':'not','UserNotification':'unot',
    'UserAction':'act','UserVote':'uvot','UserSavePost':'usvp','UserFollow':'ufol','CustomFCM':'fcm'}


class BaseAccountModel(models.Model):
    id = models.CharField(max_length=50, default="0", primary_key=True)
    blockchainId = models.CharField(max_length=50, default="", blank=True, null=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)

    class Meta:
        abstract = True

class User(AbstractUser):
    object_type = "User"
    blockchainType = 'User'
    secondChainType = 'Sonet'
    is_modifiable = True
    id = models.CharField(max_length=50, default="0", primary_key=True)
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    nodeCreatorId = models.CharField(max_length=50, default="0", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True) # publicKey will go by stored upk data, except when creating new user
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    display_name = models.CharField(max_length=50, default="", blank=True, null=True)
    must_rename = models.BooleanField(default=None, blank=True, null=True) # if network conflict occurs because display_name already taken on different node
    first_name = models.CharField(max_length=50, default=None, blank=True, null=True)
    last_name = models.CharField(max_length=50, default=None, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    timezone = models.CharField(max_length=20, default="US/Eastern", null=True, blank=True)

    UserData_obj = models.ForeignKey('accounts.UserData', blank=True, null=True, on_delete=models.CASCADE)
    # region_set_date = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    # localities = models.TextField(default='[]', blank=True, null=True)
    # interests = models.TextField(default='[]', blank=True, null=True)
    # follow_topics = models.TextField(default='[]', blank=True, null=True)
    
    receiveNotifications = models.BooleanField(default=True)
    isVerified = models.BooleanField(default=False)
    iden_length = 11
    # is_admin = models.BooleanField(default=False)
    # show_data = models.BooleanField(default=False)
    
    def __str__(self):
        return 'USER:%s' %(self.display_name)
    
    class Meta:
        ordering = ['created']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'User', 'is_modifiable': True, 'blockchainType': 'User', 'secondChainType': 'Sonet', 'password': '', 'last_login': None, 'is_superuser': False, 'username': '', 'is_staff': False, 'is_active': True, 'date_joined': None, 'id': '0', 'modelVersion': 1, 'created': None, 'last_updated': None, 'nodeCreatorId': '0', 'signature': '', 'publicKey': '', 'validation_error': False, 'display_name': '', 'must_rename': None, 'first_name': None, 'last_name': None, 'email': None, 'timezone': 'US/Eastern', 'UserData_obj': None, 'receiveNotifications': True, 'isVerified': False, 'groups': [], 'user_permissions': [], 'iden_length':11}

    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['created']

    def get_absolute_url(self):
        #return reverse("sub", kwargs={"subject": self.name})
        return "/so/%s" % (self.display_name)
    
    def get_userLink_html(self):
        if self.is_superuser:
            return f'''<span style='font-size:85%; color:#0b559a' title='SuperUser'>So</span><span style='color:gray'>/</span><a href='{self.get_absolute_url()}'>{ self.display_name }</a>'''
        elif self.isVerified:
            return f'''<span style='font-size:85%; color:#b78e12' title='Verified User'>V</span><span style='color:gray'>/</span><a href='{self.get_absolute_url()}'>{ self.display_name }</a>'''
        else:
            return f'''<span style='font-size:90%; color:gray' title='anonymous'>a</span><a href='{self.get_absolute_url()}'>{ self.display_name }</a>'''

    def get_follow_topics(self):
        if self.UserData_obj and self.UserData_obj.follow_topics:
            return json.loads(self.UserData_obj.follow_topics)
        return []

    def get_interests(self):
        if self.UserData_obj and self.UserData_obj.interests:
            return json.loads(self.UserData_obj.interests)
        return []
    
    def verify_sig(self, data, signature_hex, simple_verify=False):
        prntDebug('--user verify sig:',self,simple_verify)
        # prnt(data)
        if isinstance(data, dict):
            # prnt('isdict')
            if 'created' in data and data['created']:
                dt = string_to_dt(data['created'])
            elif 'last_updated' in data:
                dt = string_to_dt(data['last_updated'])
            else:
                dt = None

            # if upk.end_life_dt and obj.Block_obj.created > upk.end_life_dt:
                # return False
        else:
            # prnt('else')
            if has_field(data, 'created') and data.created:
                dt = data.created
            elif has_field(data, 'last_updated'):
                dt = data.last_updated
            else:
                dt = None
        if simple_verify:
            if isinstance(data, dict):
                from utils.locked import sort_for_sign
                sorted_dict = sort_for_sign(data)
                sigData = json.dumps(sorted_dict, separators=(',', ':'))
            else:
                sigData = str(data)
        else:
            sigData = get_signing_data(data)
        # prntDebug('sigData',str(sigData)[:1500])
        pubKeys = UserPubKey.objects.filter(User_obj=self)
        for p in pubKeys:
            prntDebug('pkey',p.publicKey)
            if not p.end_life_dt:
                # prnt('1')
                is_valid = verify_data(sigData, p, signature_hex)
                # is_valid = p.verify(sigData, signature_hex)
            elif dt and dt < p.end_life_dt:
                # prnt('2')
                is_valid = verify_data(sigData, p, signature_hex)
                # is_valid = p.verify(sigData, signature_hex)
            else:
                # prntDebug('3- upkf')
                is_valid = False
            if is_valid:
                # prnt('3.5-')
                return True
        # prnt('4-')
        # prnt(sigData)
        return False
    
    def assess_super_status(self, dt=None):
        prnt('assess_super_status', self, dt)
        if super_id(self.id):
            prnt('is super')
            if not self.is_superuser:
                self.is_superuser = True
                self.is_staff = True
                prnt('add super')
                self.save()
            return True
        else:
            prnt('else')
            if dt:
                if not isinstance(dt, datetime.datetime):
                    dt = string_to_dt(dt)
                ss = SuperSign.objects.filter(pointerId=self.id, last_updated__lte=dt).first()
            else:
                ss = SuperSign.objects.filter(pointerId=self.id).first()
            if ss:
                if verify_obj_to_data(ss, ss, requireSuper=True):
                    prnt('is super')
                    if not self.is_superuser:
                        self.is_superuser = True
                        self.is_staff = True
                        prnt('add super')
                        self.save()
                    return True
            prnt('not super')
            if self.is_superuser:
                self.is_superuser = False
                self.is_staff = False
                self.save()
            prnt('endsuper')
            return False

    def assess_verification(self):
        pass

    def alert(self, title, link, body, obj=None, share=False):
        # prnt('alert')
        if title == 'Yesterday in Government':
            x = link.find('?date=') + len('?date=')
            date = link[x:]
            workingTitle = date + ' in Government'
            # prnt(workingTitle)
        else:
            if body:
                if len(body) > 11:
                    b = body[:11] + '...'
                else:
                    b = body
                workingTitle = title + ' - ' + b
            else:
                workingTitle = title
        n = Notification.objects.filter(title=workingTitle, link=link, User_obj=self).first()
        if not n:
            # pass
            n = Notification(title=workingTitle, link=link, User_obj=self)
            if obj:
                # n.pointerType = obj.object_type
                n.pointerId = obj.id
            # else:
            #     n = Notification(title=title, link=link, user=self)
            n.save(share=share)
            try:
                from firebase_admin.messaging import Notification as fireNotification
                from firebase_admin.messaging import Message as fireMessage
                from fcm_django.models import FCMDevice
                if link:
                    link = link.replace('file://', '')
                    if link[0] == '/':
                        link = 'https://sovote.center' + link
                else:
                    link = 'https://sovote.center'
                fcm_devices = FCMDevice.objects.filter(user=self, active=True)
                for device in fcm_devices:
                    try:
                        
                        prnt(device)
                        device.send_message(fireMessage(notification=fireNotification(title=title, body=body), data={"click_action" : "FLUTTER_NOTIFICATION_CLICK","link" : link}))
                        prnt('away')
                    except Exception as e:
                        prnt(str(e))
            except:
                pass
        # prnt(n)
    
    def get_keys(self, dt=None, data=None):
        if dt:
            if not isinstance(dt, datetime.datetime):
                dt = string_to_dt(dt)
            return UserPubKey.objects.filter(User_obj=self).filter(Q(end_life_dt__lte=dt)|Q(end_life_dt=None))
        elif data:
            if 'last_updated' in data:
                dt = data['last_updated']
            elif 'created' in data:
                dt = data['created']
            # elif 'created' in data:
            #     dt = data['created']
            # elif 'added' in data:
            #     dt = data['added']
            else:
                return None
            dt = string_to_dt(dt)
            return UserPubKey.objects.filter(User_obj=self).filter(Q(end_life_dt__lte=dt)|Q(end_life_dt=None))
        else:
            return UserPubKey.objects.filter(User_obj=self, end_life_dt=None)
    
    def get_wallet(self):
        return Wallet.objects.filter(User_obj=self).first()

    def get_chain(self):
        return Blockchain.objects.filter(genesisId=self.id).first()
    
    def create_walletChain(self):
        prnt('--create wallet')
        wallet = Wallet.objects.filter(User_obj=self).first()
        if not wallet:
            blockchain, self, secondChain = find_or_create_chain_from_object(self)
            blockchain.add_item_to_queue(self)
            wallet = Wallet(User_obj=self, name='Main')
            wallet.save()
            blockchain.add_item_to_queue(wallet)
            datapacket = get_latest_dataPacket()
            if datapacket:
                datapacket.add_item_to_share([self, wallet])
        return wallet

    def initialize(self): # in preperation for new object
        prnt('initialize user')
        self.modelVersion = self.latestModel
        if self.id == '0':
            from utils.locked import hash_obj_id
            self.id = hash_obj_id(self)
        if not self.username:
            self.username = self.id
        if not self.created:
            self.created = now_utc()
        try:
            if not self.nodeCreatorId:
                self.nodeCreatorId = get_self_node().id
        except:
            pass
        return self
    
    def boot(self): # after new object saved
        if not self.get_wallet():
            prntDebug('--booting user')
            try:
                self.create_walletChain()
            except Exception as e:
                prnt('boot error 3875623')
                from blockchain.models import logError
                logError(e, code='4847234', func='user-boot', extra={'err':str(e)})
            for key in self.get_keys():
                key.boot()

    def save(self, share=False, is_new=False, *args, **kwargs):
        prnt('--save user(), is_new', is_new, self.id)
        if is_new:
            prnt('is_new',self.created)
            if not isinstance(self.created, datetime.datetime):
                created = string_to_dt(self.created)
            else:
                created = self.created
            prnt('n1')
            if created >= now_utc()-datetime.timedelta(seconds=11):
                prnt('next')
                from blockchain.models import Node
                self_node = get_self_node()
                prnt('self_node',self_node)
                prnt('Node.objects.first()',Node.objects.first())
                if not self_node and self.assess_super_status() and not Node.objects.first() or testing():
                    pass
                else:
                    self.nodeCreatorId = self_node.id
                prnt('saving1...', self)
                super(User, self).save(*args, **kwargs)
                self.boot()
        elif super_id(self.id) or verify_obj_to_data(self, self):
            # self.modelVersion = self.latestModel
            prnt('saving2...', self)
            super(User, self).save(*args, **kwargs)
        prnt('done user save\n')

    def delete(self):
        # deletes only if username previously registered to different user or user created less than 20 seconds ago
        if not isinstance(self.created, datetime.datetime):
            created = string_to_dt(self.created)
        else:
            created = self.created
        if created >= now_utc()-datetime.timedelta(seconds=20): 
            wallet = self.get_wallet()
            if wallet:
                walletChain = wallet.get_chain()
                if walletChain:
                    super(Blockchain, walletChain).delete()
                super(Wallet, wallet).delete()
            super(User, self).delete()
        # else:
        #     u = User.objects.filter(display_name=self.display_name).exclude(id=self.id).first()
        #     if u and u.created < created:   
        #         super(User, self).delete()

class UserData(models.Model):
    object_type = "UserData"
    is_modifiable = True
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)

    userId = models.CharField(max_length=50, default="", blank=True, null=True)

    region_set_date = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    localities = models.TextField(default='[]', blank=True, null=True)
    interests = models.TextField(default='[]', blank=True, null=True)
    follow_topics = models.TextField(default='[]', blank=True, null=True)
    
    # keyword_array = models.TextField(default='[]', blank=True, null=True)

    def __str__(self):
        return 'UserData:%s' %(self.userId)
        
    class Meta:
        ordering = ['id']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserData', 'is_modifiable': True, 'modelVersion': 1, 'id': '0', 'created': None, 'last_updated': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'userId': '', 'region_set_date': None, 'localities': '[]', 'interests': '[]', 'follow_topics': '[]'}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','userId']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['id']
            
    def save(self, *args, **kwargs):
        if self.id == '0':
            self.modelVersion = self.latestModel
            self.id = hash_obj_id(self)
        super(UserData, self).save(*args, **kwargs)




def add_or_verify_pubkey(user, registeredPublicKey, newPublicKey, signature):
    # prnt('verify registeredpubkey', registeredPublicKey)
    # prnt('verify newpubkey', newPublicKey)
    upks = UserPubKey.objects.filter(User_obj=user)
    if upks.count() > 0:
        for u in upks:
            if u.publicKey == newPublicKey:
                return u
        for u in upks:
            # prnt('enxt')
            if registeredPublicKey and u.publicKey == registeredPublicKey:
                isValid = verify_data('new public key', u, signature)
                # isValid = u.verify(signature, 'new public key')
                if isValid and newPublicKey:
                    upk = UserPubKey(User_obj=user, publicKey=newPublicKey)
                    upk.save()
                    return upk
        return None
    elif newPublicKey:
        # prnt('else')
        upk = UserPubKey(User_obj=user, publicKey=newPublicKey)
        upk.save()
        return upk
    else:
        return None

class UserPubKey(models.Model):
    object_type = "UserPubKey"
    blockchainType = 'User'
    # is_modifiable = True
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    end_life_dt = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.SET_NULL)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    keyType = models.CharField(max_length=50, default="password") # password or biometrics
    
    def __str__(self):
        return 'USERPUBLICKEY:%s' %(self.id)
        
    class Meta:
        ordering = ['-created', 'id']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserPubKey', 'blockchainType': 'User', 'modelVersion': 1, 'id': '0', 'created': None, 'end_life_dt': None, 'last_updated': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'blockchainId': '', 'Block_obj': None, 'User_obj': None, 'keyType': 'password'}

    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['created','publicKey','signature','User_obj']

    # def get_hash_to_id(self):
    #     return ['object_type','User_obj','publicKey']
    
    def verify(self, data, signature_hex, publicKey=None):
        try:
            iden = 'x'
            f = 'upk unknown'

            # if isinstance(data, dict):

            #     # for key, value in data.items():
            #     #     if isinstance(value, dict) or str(value).startswith('{'):
            #     #         data[key] = sort_dict(value)
            #     data = dict(sorted(data.items(), key=lambda item: item[0].lower()))
            
            if not isinstance(data, dict):
                # prnt('verfiy obj is dict')
                # from blockchain.models import sort_for_sign
                # data = sort_for_sign(data)
                try:
                    d = json.loads(data)
                except:
                    d = data
                # if 'object_type' in d:
                #     f = 'upk verify data dict ' + d['object_type']
                #     iden = d['id']
                # f = 'upk data is dict - ' + str(data)[:25]
            elif not isinstance(data, str):
                data = str(data)
                f = 'upk verify data stringified: ' + data
            else:
                f = 'upk verify data else - ' + str(data)[:25]
        except Exception as e:
            f = '-upk verify data: ' + str(e)
        if not publicKey:
            publicKey = self.publicKey
        prntn('publicKey',publicKey,'---signature_hex',signature_hex)
        prnt('f',f)
        from utils.locked import verify_data
        return verify_data(data, publicKey, signature_hex)
        # data = data + ' '
        # # prnt(f)
                
        # # prntn('verifying data:')
        # # prnt('upk verify signature_hex',signature_hex)
        # # prnt('upk verify publicKey',publicKey)
        # # publicKey = '04ff82508610cedbdf4b27b57b95c58ee8558c7c62d21f1e6af8533a21008c685ed41d210d4b61311ec730ad067b67d48f3162db4d3a9b98974099e0e77ffc40cd'
        # if not publicKey:
        #     publicKey = self.publicKey
        # # prnt('upk verify publicKey2',publicKey)
        # signature_bytes = bytes.fromhex(signature_hex)
        # # prnt('signature_bytes',signature_bytes)
        # public_key_bytes = bytes.fromhex(publicKey)
        # public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)
        # # data = 'X' + str(data)
        # try:
        #     public_key.verify(signature_bytes, (data).encode('utf-8'), ec.ECDSA(hashes.SHA256()))
        #     # prntDebug(f"{f} - Signature is valid IT WORKED!!!. {data}")
        #     return True
        # # except InvalidSignature:
        # #     prnt("Invalid signature.")
        # except Exception as e:
        #     # prnt(f'{f} ----FAILVERIFY!!!! {str(e)}, {iden}')
        #     prntDebug('failed to verify data:',str(data)[:1000])
        #     return False

    def initialize(self):
        self.modelVersion = self.latestModel
        if not self.created:
            self.created = now_utc()
        self.id = hash_obj_id(self)
        return self
    
    def boot(self):
        prntDebug('boot upk')
        chain = self.User_obj.get_chain()
        self.blockchainId = chain.id
        super(UserPubKey, self).save()
        if not self.Block_obj:
            chain.add_item_to_queue(self)
            # from blockchain.models import get_latest_dataPacket
            datapacket = get_latest_dataPacket()
            if datapacket:
                datapacket.add_item_to_share(self)

    def save(self, share=False, is_new=False):
        from utils.locked import convert_to_dict
        prntDebug('save upk', convert_to_dict(self))
        if is_new:
            prnt('is new')
            upk = UserPubKey.objects.filter(publicKey=self.publicKey).first()
            prnt('upk',upk)
            if not upk:
                prnt('self.User_obj',self.User_obj)
                prntDebug('user dict', convert_to_dict(self.User_obj))
                if not isinstance(self.User_obj.created, datetime.datetime):
                    user_created = string_to_dt(self.User_obj.created)
                else:
                    user_created = self.User_obj.created
                if user_created >= now_utc()-datetime.timedelta(seconds=7):
                    self.boot()
                else:
                    prntn('!!!!!user_created',user_created)
                    prntn('!!!!!now_utc(',now_utc())

        elif verify_obj_to_data(self, self):
            super(UserPubKey, self).save()

    def delete(self, signature=None):
        if not isinstance(self.created, datetime.datetime):
            created = string_to_dt(self.created)
        else:
            created = self.created
        # if signature and self.verify('delete', signature):
        #     super(UserPubKey, self).delete()
        # else:
        if created <= now_utc()-datetime.timedelta(seconds=20):
            # delete from dataPacket and blockchain queue as well
            super(UserPubKey, self).delete()

class UserVerification(BaseAccountModel):
    object_type = "UserVerification"
    blockchainType = 'User'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    creatorNodeId = models.CharField(max_length=50, default="", blank=True)
    validatorNodeId = models.CharField(max_length=50, default="", blank=True)
    Validator_obj = models.ForeignKey('blockchain.Validator', blank=True, null=True, on_delete=models.SET_NULL)
    # pointerId = models.CharField(max_length=50, default="", blank=True, null=True)
    # pointerType = 'User'
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    isVerified = models.BooleanField(default=False)
    # signature = models.CharField(max_length=200, default="0")
    # publicKey = models.CharField(max_length=200, default="0")
    

    def __str__(self):
        return 'UserVerification:%s' %(self.id)
        
    class Meta:
        ordering = ['-created', 'id']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserVerification', 'blockchainType': 'User', 'id': '0', 'blockchainId': '', 'created': None, 'last_updated': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'User_obj': None, 'isVerified': False}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','User_obj','created']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','isVerified','signature','User_obj']

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self, share=share)
            # broadcast changes immediatly
        elif not is_locked(self):
            # if not self.signature:
            #     sign_obj(self)
            super(UserVerification, self).save(*args, **kwargs)

    def delete(self):
        if not is_locked(self):
            super(UserVerification, self).delete()

class SuperSign(BaseAccountModel):
    object_type = "SuperSign"
    blockchainType = 'User'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.SET_NULL)
    pointerId = models.CharField(max_length=50, default="", blank=True, null=True)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    data = models.JSONField(default=dict, blank=True, null=True)
    
    def __str__(self):
        return 'SuperSign:%s' %(self.id)
        
    class Meta:
        ordering = ['-created', 'id']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'SuperSign', 'blockchainType': 'User', 'id': '0', 'created': None, 'last_updated': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'blockchainId': '', 'Block_obj': None, 'pointerId': '', 'User_obj': None, 'data': {}}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','User_obj','pointerId','data'] # fields not editable after initial save

    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','User_obj','pointerId','signature','created']

    def save(self, share=False, *args, **kwargs):
        if self.id == '0' and self.User_obj.assess_super_status():
            self = initial_save(self, share=share)
        elif self.User_obj.assess_super_status() and verify_obj_to_data(self, self):
            super(SuperSign, self).save(*args, **kwargs)

    def delete(self):
        if not is_locked(self):
            super(SuperSign, self).delete()

class UserNotification(models.Model):
    object_type = "UserNotification"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    # func = models.CharField(max_length=50, default="")
    # creatorNodeId = models.CharField(max_length=50, default="")
    # validatorNodeId = models.CharField(max_length=50, default="")
    Notification_obj = models.ForeignKey('accounts.Notification', blank=True, null=True, on_delete=models.CASCADE)
    # blockchainId = models.CharField(max_length=50, default="")
    # locked_to_chain = models.BooleanField(default=False)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
   
    # Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
    # Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    # Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    # # Government_obj = models.ForeignKey('posts.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, db_index=True, on_delete=models.CASCADE)
    # title = models.CharField(max_length=400, blank=True, null=True, default="")
    # link = models.CharField(max_length=500, blank=True, null=True, default="")
    # Region_obj = models.ForeignKey('posts.Region', blank=True, null=True, on_delete=models.SET_NULL)
    new = models.BooleanField(default=True)
    iden_length = 20
    # pointerId = models.CharField(max_length=50, default="")
    # pointerType = models.CharField(max_length=50, default="")
    # validated = models.BooleanField(default=False)

    def __str__(self):
        return 'UserNotification-%s' %(self.id)  
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserNotification', 'modelVersion': 1, 'id': '0', 'created': None, 'last_updated': None, 'Notification_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'DateTime': None, 'User_obj': None, 'new': True, 'iden_length':20}
            # return {'object_type': 'UserNotification', 'modelVersion': 1, 'id': '0', 'created': None, 'added': None, 'last_updated': None, 'Notification_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'DateTime': None, 'User_obj': None, 'new': True}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','User_obj','Notification_obj']
    

    def update_data(self, share=False):
        self.modelVersion = self.latestModel
        self.save(share=share)

    def save(self, share=False, *args, **kwargs):
        prnt('save usernotification')
        if self.id == '0':
            self.modelVersion = self.latestModel
            self.id = hash_obj_id(self)
            self.created = self.Notification_obj.created
            self.DateTime = self.Notification_obj.DateTime
            # assess if self_node is fcm_capable and selected to send fcm notification, then User_obj.alert() which needs modification
        # 'new' should be signed by User_obj - look into this - if not signed, new = True
        super(UserNotification, self).save(*args, **kwargs)



# Notification, SavePost, Follow should be shared regionally, as in, they need a chainId to be assigned to a datapacket
# but should not be saved to a Block --- look into this

class Notification(models.Model):
    object_type = "Notification"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    func = models.CharField(max_length=50, default="", blank=True, null=True)
    creatorNodeId = models.CharField(max_length=50, default="", blank=True, null=True)
    validatorNodeId = models.CharField(max_length=50, default="", blank=True, null=True)
    Validator_obj = models.ForeignKey('blockchain.Validator', blank=True, null=True, on_delete=models.SET_NULL)
    blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.SET_NULL)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)

    Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    # Government_obj = models.ForeignKey('posts.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    # TargetUser_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    Title = models.CharField(max_length=400, blank=True, null=True, default="")
    Link = models.CharField(max_length=500, blank=True, null=True, default="")
    # Region_obj = models.ForeignKey('posts.Region', blank=True, null=True, on_delete=models.SET_NULL)
    # new = models.BooleanField(default=True)
    targetUsers = models.JSONField(default=dict, blank=True, null=True)
    pointerId = models.CharField(max_length=50, default="", blank=True, null=True)
    # pointerType = models.CharField(max_length=50, default="")
    validated = models.BooleanField(default=False, blank=True, null=True)

 
    def __str__(self):
        return 'Notification-%s' %(self.Title)   
    
    class Meta:
        ordering = ["-created", '-id']
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Notification', 'blockchainType': 'Region', 'modelVersion': 1, 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': '', 'Region_obj': None, 'Country_obj': None, 'DateTime': None, 'Title': '', 'Link': '', 'targetUsers': {}, 'pointerId': '', 'validated': False}
            # return {'object_type': 'Notification', 'blockchainType': 'Region', 'modelVersion': 1, 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': '', 'Region_obj': None, 'Country_obj': None, 'DateTime': None, 'Title': '', 'Link': '', 'targetUsers': {}, 'pointerId': '', 'validated': False}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','Chamber','Region_obj','Country_obj','DateTime','Title']
    
    # def update(self, share=False):
    #     self.modelVersion = 'v1'
    #     self.save(share=share)

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self, share=share)
        elif not is_locked(self):
            super(Notification, self).save(*args, **kwargs)

    def verify_is_valid(self, use_assigned_val=False):
        from blockchain.models import Validator
        from utils.locked import get_node_assignment
        if use_assigned_val:
            v = self.Validator_obj
        else:
            v = Validator.objects.filter(data__has_key=self.id, is_valid=True).order_by('-created').first()
        if v:
            if self.id in v.data and v.data[self.id] == sigData_to_hash(self):
                if verify_obj_to_data(v, v):
                    creator_nodes, validator_nodes = get_node_assignment(None, dt=self.added, func=self.func, chainId=self.blockchainId)
                    # validator_node_id = get_scraping_order(dt=self.added, chainId=self.blockchainId, func_name=self.func, validator_only=True)
                    if self.validatorNodeId in validator_nodes:
                        return True
        return False

    def validate(self, validator=None, add_to_queue=True, save_self=True, verify_validator=True, node_block_data={}):
        prnt('--validate notification', self.id)
        from utils.locked import validate_obj
        return validate_obj(obj=self, pointer=None, validator=validator, save_obj=save_self, update_pointer=False, verify_validator=verify_validator, add_to_queue=add_to_queue, node_block_data=node_block_data)

        err = 0
        if not self.validated:
            err = 1
            proceed = False
            from blockchain.models import Validator, sigData_to_hash, get_scraping_order, max_validation_window, convert_to_datetime
            if validator:
                proceed = True
            else:
                if self.Validator_obj:
                    validator = self.Validator_obj
                    proceed = True
                if not validator:
                    validators = Validator.objects.filter(data__contains={self.id: sigData_to_hash(self)}, is_valid=True).order_by('-created')
                    for validator in validators:
                        if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                            validator_node_id = validator.CreatorNode_obj.id
                            proceed = True
                            break
                        else:
                            validator_node_id = get_scraping_order(dt=convert_to_datetime(self.created), chainId=self.blockchainId, func_name=self.func, validator_only=True, node_block_data=node_block_data)
                            if self.validatorNodeId == validator_node_id:
                                proceed = True
                                break
            # validator shuold be crated within x hours of pointer.added
            if proceed and validator and validator.is_valid and validator.signature and self.signature:
                if convert_to_datetime(validator.created) > convert_to_datetime(self.created) + datetime.timedelta(days=max_validation_window) or convert_to_datetime(validator.created) < convert_to_datetime(self.created):
                    err = 11
                    prnt('validator created outside of window')
                    return False
                err = 2
                if not verify_validator or verify_obj_to_data(validator, validator):
                    err = 21
                    hash = validator.data[self.id]
                    if hash == sigData_to_hash(self):
                        err = 3
                        if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                            validator_node_id = validator.CreatorNode_obj.id
                            err = '333a' + validator_node_id
                        else:
                            validator_node_id = get_scraping_order(dt=convert_to_datetime(self.created), chainId=validator.blockchainId, func_name=validator.func, validator_only=True, node_block_data=node_block_data)
                            err = '333b' + validator_node_id
                        if self.validatorNodeId == validator_node_id:
                            err = 4
                            prnt('proceed to validate')
                            if save_self:
                                if self.Validator_obj != validator:
                                    self.Validator_obj = validator
                                    # self.save()
                                self.validated = True
                                self.save()
                            prnt('validated')
                            try:
                                err = 5
                                notify = next(iter(self.targetUsers))
                                prnt('notify',notify)
                                target = self.targetUsers[notify]
                                prnt('target',target)
                                if notify == 'all':
                                    for u in User.objects.all():
                                        prnt(u)
                                        n = UserNotification.objects.filter(User_obj=u, Notification_obj=self).first()
                                        if not n:
                                            n = UserNotification(User_obj=u, Notification_obj=self)
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
                                    blockchain, item, secondChain = find_or_create_chain_from_object(self.Region_obj)
                                    # blockchain = Blockchain.objects.filter(id=self.blockchainId).first()
                                    blockchain.add_item_to_queue(self)
                                    # blockchain.add_item_to_queue(validator)
                                return True
                            except Exception as e:
                                prnt('fail40636',str(e))
                                err = e
                        else:
                            prnt('valId incorrect')
                    else:
                        prnt('hash no match')
            from blockchain.models import logError, convert_to_dict
            logError('failed to validate notification', code='357021', func='accounts_notification_validate', extra={'err':str(err),'self_dict':convert_to_dict(self)})
        # prnt('failed to validaed post')
                # break
        # except Exception as e:
        #     prnt(str(e))
        return False


    def delete(self, force_delete=False):
        if force_delete or not is_locked(self):
            super(Notification, self).delete()

class UserVote(BaseAccountModel):
    object_type = "UserVote"
    blockchainType = 'Region'
    # secondChainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.SET_NULL)
    postId = models.CharField(max_length=50, default="0")
    pointerId = models.CharField(max_length=50, default="", blank=True, null=True) # obj post points to
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.SET_NULL)
    District_obj = models.ForeignKey('legis.District', default=None, related_name='vote_district', blank=True, null=True, on_delete=models.SET_NULL)
    voteValue = models.CharField(max_length=20, default='', blank=True, null=True)
    iden_length = 20

    def __str__(self):
        return f'UserVote: username:{self.User_obj.display_name}, postId:{self.postId}'

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserVote', 'blockchainType': 'Region', 'id': '0', 'created': None, 'last_updated': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'blockchainId': '', 'Block_obj': None, 'postId': '0', 'pointerId': '', 'User_obj': None, 'District_obj': None, 'voteValue': '', 'iden_length':20}
        
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','voteValue','signature','User_obj','pointerId','created','District_obj']

    def boot(self):
        # creates UserAction
        useraction = UserAction.objects.filter(User_obj=self.User_obj, Post_obj__id=self.postId).first()
        if not useraction:
            post = Post.objects.filter(id=self.postId).first()
            useraction = UserAction(User_obj=self.User_obj, Post_obj=post)
        if not useraction.last_updated or useraction.last_updated < self.created:
            useraction.last_updated = self.created
            useraction.UserVote_obj = self
            useraction.save()

    def initialize(self):
        self.modelVersion = self.latestModel
        self.id = hash_obj_id(self)
        return self
    
    def save(self, share=False, *args, **kwargs):
        # if self.id == '0':
        #     self = initial_save(self, share=share)
        if verify_obj_to_data(self, self):
            if not is_locked(self):
                # from utils.models import find_or_create_chain_from_object
                chain, obj, secondChain = find_or_create_chain_from_object(self)
                if not self.blockchainId:
                    self.blockchainId = chain.id
                chain.add_item_to_queue(self)
                # secondChain.add_item_to_data(self)
                super(UserVote, self).save(*args, **kwargs)
    
    def delete(self):
        if not is_locked(self):
            super(UserVote, self).delete()

class UserSavePost(models.Model):
    is_modifiable = True
    object_type = "UserSavePost"
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    blockchainId = models.CharField(max_length=50, default="", blank=True) # chainId of pointerId
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    postId = models.CharField(max_length=50, default="", blank=True, null=True)
    pointerId = models.CharField(max_length=50, default="", blank=True, null=True)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    saved = models.BooleanField(default=None, blank=True, null=True)

    # def get_hash_to_id(self):
    #     return ['object_type','User_obj','postId','pointerId','created']
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserSavePost', 'is_modifiable': True, 'id': '0', 'created': None, 'modelVersion': 1, 'blockchainId': '', 'publicKey': '', 'signature': '', 'validation_error': False, 'postId': '', 'pointerId': '', 'User_obj': None, 'saved': None}
        
    def boot(self):
        # creates UserAction
        useraction = UserAction.objects.filter(User_obj=self.User_obj, Post_obj__id=self.postId).first()
        if not useraction:
            post = Post.objects.filter(id=self.postId).first()
            useraction = UserAction(User_obj=self.User_obj, Post_obj=post)
        if not useraction.last_updated or useraction.last_updated < self.created:
            useraction.last_updated = self.created
            useraction.UserSavePost_obj = self
            useraction.save()
            previous_objs = UserSavePost.objects.filter(User_obj=self.User_obj, postId=self.postId).exclude(id=self.id)
            for obj in previous_objs:
                obj.delete()

    def initialize(self):
        # set chainId from pointer_obj.chainId
        self.modelVersion = self.latestModel
        self.id = hash_obj_id(self)
        return self
    
    def save(self, share=False, *args, **kwargs):
        if verify_obj_to_data(self, self):
            super(UserSavePost, self).save(*args, **kwargs)
    
    def delete(self):
        useraction = UserAction.objects.filter(User_obj=self.User_obj, SavePost_obj=self).first()
        if useraction:
            useraction.UserSavePost_obj = None
            useraction.save()
        super(UserSavePost, self).delete()

class UserFollow(models.Model):
    is_modifiable = True
    object_type = "UserFollow"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    blockchainId = models.CharField(max_length=50, default="", blank=True) # chainId of pointerId
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    postId = models.CharField(max_length=50, default="", blank=True, null=True)
    pointerId = models.CharField(max_length=50, default="", blank=True, null=True)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    following = models.BooleanField(default=None, blank=True, null=True)

    # def get_hash_to_id(self):
    #     return ['object_type','User_obj','postId','pointerId','created']
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserFollow', 'is_modifiable': True, 'modelVersion': 1, 'id': '0', 'created': None, 'blockchainId': '', 'publicKey': '', 'signature': '', 'validation_error': False, 'postId': '', 'pointerId': '', 'User_obj': None, 'following': None}
        
    def boot(self):
        # creates UserAction
        useraction = UserAction.objects.filter(User_obj=self.User_obj, Post_obj__id=self.postId).first()
        if not useraction:
            post = Post.objects.filter(id=self.postId).first()
            useraction = UserAction(User_obj=self.User_obj, Post_obj=post)
        if not useraction.last_updated or useraction.last_updated < self.created:
            useraction.last_updated = self.created
            useraction.UserFollow_obj = self
            useraction.save()
            previous_objs = UserFollow.objects.filter(User_obj=self.User_obj, postId=self.postId).exclude(id=self.id)
            for obj in previous_objs:
                obj.delete()

    def initialize(self):
        # set chainId from pointer_obj.chainId
        self.modelVersion = self.latestModel
        self.id = hash_obj_id(self)
        return self

    def save(self, share=False, *args, **kwargs):
        if verify_obj_to_data(self, self):
            super(UserFollow, self).save(*args, **kwargs)
    
    def delete(self):
        useraction = UserAction.objects.filter(User_obj=self.User_obj, Follow_obj=self).first()
        if useraction:
            useraction.UserFollow_obj = None
            useraction.save()
        super(UserFollow, self).delete()

class UserAction(models.Model):
    object_type = "UserAction"
    id = models.CharField(max_length=50, default="0", primary_key=True)
    # created = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    # added = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    # automated = models.BooleanField(default=False)
    # publicKey = models.CharField(max_length=200, default="0")
    # signature = models.CharField(max_length=200, default="0")

    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    Post_obj = models.ForeignKey(Post, blank=True, null=True, on_delete=models.CASCADE)
    # Archive_obj = models.ForeignKey(Archive, blank=True, null=True, on_delete=models.SET_NULL)
    # post_id = models.IntegerField(null=True) 
    pointerId = models.CharField(max_length=50, default="", blank=True, null=True) # points to post_obj.pointer, not post
    # pointerType = models.CharField(max_length=50, default="0")

    UserVote_obj = models.ForeignKey('accounts.UserVote', blank=True, null=True, on_delete=models.SET_NULL)
    UserSavePost_obj = models.ForeignKey('accounts.UserSavePost', blank=True, null=True, on_delete=models.SET_NULL)
    UserFollow_obj = models.ForeignKey('accounts.UserFollow', blank=True, null=True, on_delete=models.SET_NULL)



    score = models.IntegerField(default=None, blank=True, null=True)

    # Person_obj = models.ForeignKey('posts.Person', blank=True, null=True, on_delete=models.SET_NULL)
    match = models.IntegerField(default=None, blank=True, null=True)
    
    # saved = models.BooleanField(default=False)
    # saved_time = models.DateTimeField(auto_now_add=False, auto_now=False, null=True)
    # shared = models.BooleanField(default=False)
    # shared_time = models.DateTimeField(auto_now_add=False, auto_now=False, null=True)

    # voted_keywords_added = models.BooleanField(default=False)
    # viewed_keywords_added = models.BooleanField(default=False)
    shared_keywords_added = models.BooleanField(default=None, blank=True, null=True)
    iden_length = 20

    def __str__(self):
        return f'UserAction: user:{self.User_obj.display_name}, pointerId:{self.pointerId}'

    class Meta:
        ordering = ["-last_updated"]
    
    # def get_version_fields(self, version=None): # no model version here!
    #     if not version:
    #         version = self.modelVersion
    #     if int(version) >= 1:
    #         return {'object_type': 'UserAction', 'id': '0', 'last_updated': None, 'Region_obj': None, 'User_obj': None, 'Post_obj': None, 'pointerId': '', 'UserVote_obj': None, 'UserSavePost_obj': None, 'UserFollow_obj': None, 'score': None, 'match': None, 'shared_keywords_added': None}
        
    def get_hash_to_id(self):
        return ['object_type','User_obj','Post_obj']
    
    # def get_or_create_object(self, obj_type, **kwargs):
    #     item = getattr(self, obj_type)
    #     reuse = check_dataPacket(item)
    #     if reuse:
    #         return item
    #     else:
    #         return create_dynamic_model(obj_type, **kwargs)

    def calculate_vote(self, vote, forceVote):
        if self.Post_obj:
            p = self.Post_obj
        # elif self.Archive_obj:
        #     p = self.Archive_obj
        score = get_point_value(p)
        if vote == 'yea' or vote == 'Yea':
            if self.isYea == False or forceVote:
                if self.isYea == True:
                    p.total_yeas -= 1
                self.isYea = True
                if self.isNay == True:
                    p.total_nays -= 1
                self.isNay = False
                points = decimal.Decimal(score)
                p.rank += points
                p.total_yeas += 1
                if not forceVote:
                    p.total_votes += 1
                # self = set_keywords(self, 'add', None)
            elif self.isYea == True:
                self.isYea = False
                points = decimal.Decimal(score)
                p.rank -= points
                p.total_votes -= 1
                p.total_yeas -= 1
                # self = set_keywords(self, 'remove', None)
        elif vote == 'nay' or vote == 'Nay':
            # self.cast_vote = ''
            if self.isNay == False or forceVote:
                if self.isNay == True:
                    p.total_nays -= 1
                self.isNay = True
                if self.isYea == True:
                    self.isYea = False
                    points = decimal.Decimal(score)
                    p.rank -= points
                    p.total_yeas -= 1
                p.total_nays += 1
                if not forceVote:
                    p.total_votes += 1
            elif self.isNay == True:
                self.isNay = False
                p.rank += points
                # self = set_keywords(self, 'add', None)
                p.total_votes -= 1
                p.total_nays -= 1
        p.save()
        self.save()

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            if self.Post_obj:
                post = self.Post_obj
            # elif self.Archive_obj:
            #     post = self.Archive_obj
            self.Region_obj = post.Region_obj
            pointer = post.get_pointer()
            self.pointerId = pointer.id
            # self.pointerType = pointer.object_type
            self.id = hash_obj_id(self)
        super(UserAction, self).save(*args, **kwargs)
    
    # def delete(self):
    #     super(UserAction, self).delete()

# from fcm_django.models import FCMDevice

class CustomFCM(models.Model):
    object_type = "CustomFCM"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)


    # # Define a custom primary key as CharField
    # id = models.CharField(max_length=50, primary_key=True, default="0")

    # Include necessary fields from FCMDevice
    registration_id = models.TextField(unique=True, blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    active = models.BooleanField(default=True, blank=True, null=True)
    User_obj = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, blank=True, null=True)
    # created = models.DateTimeField(auto_now_add=True, blank=True, null=True)  # Custom created field
    # Add your custom fields here
    # object_type = models.CharField(max_length=50, default="CustomFCM")


    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'CustomFCM', 'modelVersion': 1, 'id': '0', 'registration_id': None, 'device_id': None, 'active': True, 'User_obj': None, 'type': None}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','User_obj','device_id','registration_id']
    
    def save(self, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self)
        else:
            super(CustomFCM, self).save(*args, **kwargs)
        # # Custom logic before saving
        # prnt(f"Saving device with token: {self.registration_id}")
        
        # # Call the parent class's save method to ensure normal saving behavior
        # super().save(*args, **kwargs)
        
        # # Custom logic after saving
        # prnt("Device saved successfully.")

