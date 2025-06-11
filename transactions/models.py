from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.utils.text import slugify
from django.db.models import Q
# from django.db.models import Q, Value, F, Avg

# from django.contrib.postgres.fields import ArrayField
# from posts.models import Post
from blockchain.models import Blockchain, Block
# from utils.models import *
from utils.models import prnt, prntDev, prntDebug, prntn, prntDevn, prntDebugn, debugging, testing, is_locked, now_utc, initial_save, string_to_dt
from utils.locked import hash_obj_id, dt_to_string
import re
# import time
# import datetime
# import wikipedia
# import random
# import requests
# from bs4 import BeautifulSoup
# import json
# import base64
# import decimal
# import pytz
# import hashlib
# import uuid
import django_rq

model_prefixes = {'UserTransaction':'utra','Wallet':'wal'}

class Wallet(models.Model):
    is_modifiable = True
    object_type = "Wallet"
    blockchainType = 'Wallet'
    secondChainType = 'User'
    blockchainId = models.CharField(max_length=50, default="", blank=True, null=True)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, default="", blank=True, null=True)
    value = models.TextField(default="0")
    
    def __str__(self):
        return f'WALLET:{self.User_obj}-{self.name}'
        
    class Meta:
        ordering = ['-created', 'id']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Wallet', 'is_modifiable': True, 'blockchainType': 'Wallet', 'secondChainType': 'User', 'blockchainId': '', 'id': '0', 'modelVersion': 1, 'created': None, 'last_updated': None, 'User_obj': None, 'name': '', 'value': '0'}
            # return {'object_type': 'Wallet', 'is_modifiable': True, 'blockchainType': 'Wallet', 'secondChainType': 'User', 'blockchainId': '', 'id': '0', 'modelVersion': 1, 'created': None, 'last_updated': None, 'User_obj': None, 'value': '0'}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','User_obj','name']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['User_obj']

    def get_chain(self):
        return Blockchain.objects.filter(id=self.blockchainId).first()
    

    def tally_tokens(self):
        prnt('--tally_tokens wallet')

        latest_block = Block.objects.filter(Blockchain_obj=self.get_chain(), validated=True).order_by('-index').first()
        if latest_block:
            latest_dt = string_to_dt(latest_block.notes['wallet_total']['dt'])
            latest_value = float(latest_block.notes['wallet_total']['value'])
            latest_transactions = UserTransaction.objects.filter(Q(ReceiverWallet_obj=self)|Q(SenderWallet_obj=self), validated=True, enacted=True, enact_dt__gt=latest_dt).order_by('enact_dt')
            for transaction in latest_transactions:
                if transaction.ReceiverWallet_obj == self:
                    latest_value += float(transaction.token_value)
                elif transaction.SenderWallet_obj == self:
                    latest_value -= float(transaction.token_value)
            if self.value != str(latest_value):
                self.value = str(latest_value)
                self.save()
            return str(latest_value)
        else:
                
            target_value = 0
            utrIdens = []
            
            # if history:
            #     utrs = UserTransaction.objects.filter(Q(ReceiverWallet_obj=self)|Q(SenderWallet_obj=self), validated=True, enact_dt__lte=now_utc()).order_by('-enact_dt')[:history]
            # else:
            utrs = UserTransaction.objects.filter(Q(ReceiverWallet_obj=self)|Q(SenderWallet_obj=self), validated=True, enact_dt__lte=now_utc()).order_by('-enact_dt')
            for utr in utrs:
                if utr.ReceiverWallet_obj == self and utr.ReceiverBlock_obj and utr.ReceiverBlock_obj.validated:
                    target_value = float(target_value) + float(utr.token_value)
                elif utr.SenderWallet_obj == self and utr.SenderBlock_obj and utr.SenderBlock_obj.validated:
                    target_value = float(target_value) - float(utr.token_value)
            
            # from blockchain.models import Block
            # blocks = Block.objects.filter(Blockchain_obj=self, validated=True).order_by('index')
            # for block in blocks:
            #     idens = [key for key in block.data if key.startswith(get_model_prefix('UserTransaction'))]
            #     utrIdens.append(idens[0])
            # if utrIdens:
            #     utrs = get_dynamic_model('UserTransaction', list=True, id__in=utrIdens)
            #     for utr in utrs:
            #         if not utr.enacted or utr.enact_dt and utr.enact_dt > now_utc():
            #             pass
            #         else:
            #             if utr.ReceiverBlock_obj and utr.ReceiverBlock_obj.Blockchain_obj == self:
            #                 target_value = float(target_value) + float(utr.token_value)
            #             elif utr.SenderBlock_obj and utr.SenderBlock_obj.Blockchain_obj == self:
            #                 target_value = float(target_value) - float(utr.token_value)
            self.value = str(target_value)
            self.save()
            return self.value
            

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self)
            prntDebug('save wallet 1')
            # self.get_chain().add_item_to_queue(self)
            self.last_updated = now_utc()
        super(Wallet, self).save(*args, **kwargs)

    def delete(self):
        pass
        # if not is_locked(self):
        #     super(Wallet, self).delete()

class UserTransaction(models.Model):
    object_type = "UserTransaction"
    blockchainType = 'Wallet'
    secondChainType = 'Wallet'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    publicKey = models.CharField(max_length=200, default="", blank=True, null=True)
    signature = models.CharField(max_length=200, default="", blank=True, null=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    SenderBlock_obj = models.ForeignKey('blockchain.Block', related_name='receiver_block', blank=True, null=True, on_delete=models.SET_NULL)
    ReceiverBlock_obj = models.ForeignKey('blockchain.Block', related_name='sender_block', blank=True, null=True, on_delete=models.SET_NULL)

    ReceiverWallet_obj = models.ForeignKey('transactions.Wallet', related_name='receiver', blank=True, null=True, on_delete=models.PROTECT)
    SenderWallet_obj = models.ForeignKey('transactions.Wallet', related_name='sender', blank=True, null=True, on_delete=models.PROTECT)

    token_value = models.TextField(default="0")
    regarding = models.JSONField(default=None, blank=True, null=True)
    validated = models.BooleanField(default=None, blank=True, null=True)
    enact_dt = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    enacted = models.BooleanField(default=None, blank=True, null=True)
    iden_length = 20


    def __str__(self):
        return f'UserTransaction:re:{self.regarding},to:{self.ReceiverWallet_obj}-{self.token_value}/tokens.{self.id}'
        # if self.Sender_obj:
        #     return f'UserTransaction:from:{self.Sender_obj.display_name},to:{self.Receiver_obj.display_name}-{self.token_value}/tokens.{self.id}'
        # else:
        #     return f'UserTransaction:re:{self.regarding},to:{self.Receiver_obj.display_name}-{self.token_value}/tokens.{self.id}'
        
    class Meta:
        ordering = ['-created', 'id']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'UserTransaction', 'blockchainType': 'Wallet', 'secondChainType': 'Wallet', 'modelVersion': 1, 'id': '0', 'created': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'SenderBlock_obj': None, 'ReceiverBlock_obj': None, 'ReceiverWallet_obj': None, 'SenderWallet_obj': None, 'token_value': '0', 'regarding': None, 'validated': None, 'enact_dt': None, 'enacted': None, 'iden_length':20}
        
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','token_value','signature','ReceiverWallet_obj','SenderWallet_obj','enact_dt']

    def assess_validation(self):
        prnt('--assess_validation')
        if self.ReceiverBlock_obj:
            # prnt('1')
            prev_block = self.ReceiverBlock_obj.get_previous_block()
            # prnt(prev_block)
            if prev_block and prev_block.object_type == 'Blockchain' or prev_block.validated:
                # prnt('2')
                from utils.locked import verify_obj_to_data
                if verify_obj_to_data(self, self):
                    # prnt('3')
                    if self.SenderBlock_obj:
                        # prnt('4')
                        prev_Sendblock = self.SenderBlock_obj.get_previous_block()
                        if prev_Sendblock and prev_Sendblock.object_type == 'Blockchain' or prev_Sendblock.validated:
                            if self.SenderBlock_obj.validated and self.ReceiverBlock_obj.validated:
                                return True
        
                    elif 'BlockReward' in self.regarding:
                        # prnt('5')
                        # rewardBlock = self.get_reward_block()
                        # prnt('rewardBlock',rewardBlock)
                        if self.ReceiverBlock_obj.validated:
                            prnt('6')
                            return True
        prnt('false')
        return False
    
    def get_reward_block(self):
        if 'BlockReward' in self.regarding:
            from blockchain.models import Block
            rewardBlockId = self.regarding['BlockReward']
            return Block.objects.filter(id=rewardBlockId).first()
        return None

    def calculate(self, value=None, wallet_total=None, dir='receive', return_float=False):
        if not value:
            value = self.token_value
        # if not wallet_total:
        if dir == 'receive' or dir == 'add':
            wallet_total = self.ReceiverWallet_obj.tally_tokens()
        elif self.SenderWallet_obj:
            if dir == 'send' or dir == 'subtract' or dir == 'sub':
                wallet_total = self.SenderWallet_obj.tally_tokens()
        if dir == 'receive':
            result = float(wallet_total) + float(value)
        elif dir == 'send':
            result = float(wallet_total) - float(value)
        if return_float:
            return result
        else:
            return str(result)

    def enact_transaction(self):
        prnt('--enact_transaction')
        if not self.validated:
            return False
        if self.enacted:
            return True
        if self.enact_dt and self.enact_dt > now_utc():
            return False
        if not self.assess_validation():
            return False
        if self.SenderWallet_obj:
            sender_wallet = self.SenderWallet_obj
            sender_wallet.value = self.calculate(value=self.token_value, dir='send')
            # sender_chain = sender_wallet.get_chain()
            # if 'pending' in sender_chain.queuedData:
            #     created_dt_string = dt_to_string(self.created)
            #     if created_dt_string in sender_chain.queuedData['pending'] and sender_chain.queuedData['pending'][created_dt_string]['transactionId'] == self.id:
            #         sender_wallet.value = sender_chain.queuedData['pending'][created_dt_string]['result']
            #         del sender_chain.queuedData['pending'][created_dt_string]
            #         sender_chain.save()
            sender_wallet.last_updated = now_utc()
            sender_wallet.save()
        receiver_wallet = self.ReceiverWallet_obj
        receiver_wallet.value = self.calculate(value=self.token_value, dir='receive')
        receiver_wallet.last_updated = now_utc()
        receiver_wallet.save()
        self.enacted = True
        super(UserTransaction, self).save()
        prnt('receiver_wallet.value',receiver_wallet.value)
        return True
        
    def tally_tokens(self):
        prnt('--tally_tokens trs')
        if self.ReceiverWallet_obj:
            self.ReceiverWallet_obj.tally_tokens()
        if self.SenderWallet_obj:
            self.SenderWallet_obj.tally_tokens()

    def send_for_block_creation(self, downstream_worker=True):
        from utils.locked import get_node_assignment
        from utils.models import get_self_node
        self_node = get_self_node()
        if not self.ReceiverBlock_obj:
            creator_nodeIds, broadcast_list, validator_list = get_node_assignment(self, dt=self.created)
            if self_node.id in creator_nodeIds:
                # if 'BlockReward' in self.regarding and not self.SenderWallet_obj:
                #     receiverChain = self.ReceiverWallet_obj.get_chain()
                #     receiverBlock = receiverChain.create_block(transaction=self, is_reward=True)
                # elif not self.SenderWallet_obj:
                #     return None
                # else:
                receiverChain = self.ReceiverWallet_obj.get_chain()
                receiverBlock = receiverChain.create_block(transaction=self)
                self.ReceiverBlock_obj = receiverBlock
                self.save()
                # broadcast_block(receiverBlock, lst={creator_nodeId:validator_list})
                if downstream_worker:
                    queue = django_rq.get_queue('main')
                    queue.enqueue(receiverBlock.broadcast, lst={self_node.id:validator_list}, target_node_id=self_node.id, job_timeout=150)
                else:
                    receiverBlock.broadcast(lst={self_node.id:validator_list}, target_node_id=self_node.id)

        if self.SenderWallet_obj and not self.SenderBlock_obj:
            sendCreator_nodeIds, broadcast_list, validator_list = get_node_assignment(self, dt=self.created, sender_transaction=True)
            if self_node.id in sendCreator_nodeIds:
                senderChain = self.SenderWallet_obj.get_chain()
                senderBlock = senderChain.create_block(transaction=self)
                self.SenderBlock_obj = senderBlock
                self.save()
                # broadcast_block(senderBlock, lst={sendCreator_nodeId:validator_list})
                if downstream_worker:
                    queue = django_rq.get_queue('main')
                    queue.enqueue(senderBlock.broadcast, lst={self_node.id:validator_list}, target_node_id=self_node.id, job_timeout=150)
                else:
                    senderBlock.broadcast(lst={self_node.id:validator_list}, target_node_id=self_node.id)

    def mark_valid(self):
        prnt('--mark_valid')
        if not self.validated:
            if self.assess_validation():
                from utils.locked import verify_obj_to_data
                if verify_obj_to_data(self, self):
                    self.validated = True
                    super(UserTransaction, self).save()

                if not self.ReceiverBlock_obj.notes:
                    self.ReceiverBlock_obj.notes = {}
                self.ReceiverBlock_obj.notes['wallet_total'] = {'dt':dt_to_string(now_utc()),'value':self.ReceiverWallet_obj.tally_tokens()}
                super(Block, self.ReceiverBlock_obj).save()
                receiverChain = self.ReceiverWallet_obj.get_chain()
                if 'pending' in receiverChain.queuedData and self.id in receiverChain.queuedData['pending']:
                    del receiverChain.queuedData['pending'][self.id]
                    receiverChain.save()

                if self.SenderWallet_obj:
                    if not self.SenderBlock_obj.notes:
                        self.SenderBlock_obj.notes = {}
                    self.SenderBlock_obj.notes['wallet_total'] = {'dt':dt_to_string(now_utc()),'value':self.SenderWallet_obj.tally_tokens()}
                    super(Block, self.SenderBlock_obj).save()
                    senderChain = self.SenderWallet_obj.get_chain()
                    if 'pending' in senderChain.queuedData and self.id in senderChain.queuedData['pending']:
                        del senderChain.queuedData['pending'][self.id]
                    senderChain.save()
                            
        if self.validated and not self.enacted:
            if not self.enact_dt or self.enact_dt < now_utc():
                self.enact_transaction()

    def is_not_valid(self, omit=None, note=None):
        self.validated = False
        super(UserTransaction, self).save()

        receiverChain = self.ReceiverWallet_obj.get_chain()
        if 'pending' in receiverChain.queuedData and self.id in receiverChain.queuedData['pending']:
            del receiverChain.queuedData['pending'][self.id]
            receiverChain.save()
        if self.SenderWallet_obj:
            senderChain = self.SenderWallet_obj.get_chain()
            if 'pending' in senderChain.queuedData and self.id in senderChain.queuedData['pending']:
                del senderChain.queuedData['pending'][self.id]
            senderChain.save()

        if self.ReceiverBlock_obj and self.ReceiverBlock_obj != omit and self.ReceiverBlock_obj.validated != False:
            self.ReceiverBlock_obj.is_not_valid(note=note)
        if self.SenderBlock_obj and self.SenderBlock_obj != omit and self.SenderBlock_obj.validated != False:
            self.SenderBlock_obj.is_not_valid(note=note)
        if self.enacted:
            self.enacted = False
            super(UserTransaction, self).save()
            self.tally_tokens()

    def initialize(self):
        self.modelVersion = self.latestModel
        if not self.created:
            self.created = now_utc()
        if not self.enact_dt:
            self.enact_dt = self.created
        if self.id == '0':
            self.id = hash_obj_id(self)
        return self

    def save(self, share=False, *args, **kwargs):
        prnt('saving transaction', self)
        def contains_invalid_characters(s):
            return bool(re.search(r'[^0-9.]', s))
        if not self.SenderWallet_obj and 'BlockReward' not in self.regarding or contains_invalid_characters(self.token_value):
            prnt('do not save transaction')
            return None
        # create block obj
        from utils.locked import verify_obj_to_data
        if self.id == '0' and 'BlockReward' in self.regarding and self.regarding['BlockReward'] == 'coming' and float(self.token_value) == 0:
            self.initialize()
            super(UserTransaction, self).save(*args, **kwargs)
            prnt('transaction saved1')
        elif verify_obj_to_data(self, self):
            if not is_locked(self):
                super(UserTransaction, self).save(*args, **kwargs)
                prnt('transaction saved2')
    
    def delete(self, superDel=False, skipReceiver_Block=False):
        if not is_locked(self) or superDel:
            if self.SenderBlock_obj:
                self.SenderBlock_obj.delete(superDel=superDel)
            if not skipReceiver_Block: # in event of recursion loop
                try:
                    self.ReceiverBlock_obj.delete(superDel=superDel)
                except:
                    pass
            super(UserTransaction, self).delete()
