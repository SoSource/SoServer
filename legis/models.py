from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from utils.models import prntDebug, prnt, compensate_save, get_model_and_update, superDelete, now_utc, is_locked, initial_save
# from accounts.models import 
from posts.models import create_keyphrases, find_post, Update, BaseModel, ModifiableModel, Post, new_post
# from django.forms.models import model_to_dict

import uuid
import base64
import re
import random
import json
import pytz
import datetime
import time
from dateutil import tz
from django.utils import timezone
import decimal
import operator
from nltk.corpus import stopwords
import hashlib
import ast
from itertools import islice
from collections import defaultdict

model_prefixes = {'Government':'gv','Agenda':'agn','Bill':'bil','BillText':'btxt',
                'Meeting':'mtg','Statement':'sta','Committee':'com',
                'Motion':'mot','Vote':'vot','Election':'elc',
                'Party':'prt','Person':'per','District':'dis'}

from posts.models import BaseModel
class LegisModel(BaseModel):
    Chamber = models.CharField(max_length=20, default=None, blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    Government_obj = models.ForeignKey('legis.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    
    class Meta:
        abstract = True


class Government(BaseModel):
    object_type = 'Government'
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    LogoLinks = models.JSONField(blank=True, null=True)
    GovernmentNumber = models.IntegerField(blank=True, null=True)
    SessionNumber = models.IntegerField(blank=True, null=True)
    # StartDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=False, null=True)
    gov_level = models.CharField(max_length=100, default="", blank=True, null=True) # Federal, Provincial, State, Greater Municipal, Municipal, County, City
    gov_type = models.CharField(max_length=100, default="", blank=True, null=True) # Parliament, Congress or Government
    
    # update fields
    # EndDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    
    def __str__(self):
        return 'GOVERNMENT:(%s-%s)' %(self.GovernmentNumber, self.SessionNumber)
    
    class Meta:
        ordering = ['-GovernmentNumber','-SessionNumber']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Government', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'Region_obj': None, 'Country_obj': None, 'DateTime': None, 'LogoLinks': None, 'GovernmentNumber': None, 'SessionNumber': None, 'gov_level': '', 'gov_type': ''}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['GovernmentNumber','SessionNumber','gov_level','Country_obj','Region_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['Region_obj','GovernmentNumber','SessionNumber','gov_level','DateTime']

    def migrate_data(self):
        if self.SessionNumber:
            previousGov = Government.objects.filter(Region_obj=self.Region_obj, gov_level=self.gov_level, GovernmentNumber__lte=self.GovernmentNumber, SessionNumber__lte=self.SessionNumber).exclude(id=self.id).first()
        else:
            previousGov = Government.objects.filter(Region_obj=self.Region_obj, gov_level=self.gov_level, GovernmentNumber__lte=self.GovernmentNumber).exclude(id=self.id).first()
        if previousGov:
            self.LogoLinks = previousGov.LogoLinks
            self.gov_type = previousGov.gov_type
            if not self.DateTime:
                from blockchain.models import round_time
                self.DateTime = round_time(dt=now_utc(), dir='down', amount='day')
        else:
            currentGov = Government.objects.filter(Region_obj=self.Region_obj, gov_level=self.gov_level).exclude(id=self.id).first()
            if currentGov:
                self.LogoLinks = currentGov.LogoLinks
                self.gov_type = currentGov.gov_type    

        return self


    def end_previous(self, func): # not currently working
        print('end_previous')
        # dt = datetime.date.today()
        dt_now = now_utc()
        today = dt_now - datetime.timedelta(hours=dt_now.hour, minutes=dt_now.minute, seconds=dt_now.second, microseconds=dt_now.microsecond)
        print('today',today)
        from utils.locked import convert_to_dict
        print('d:',convert_to_dict(self))
        previousCongress = Government.objects.filter(Region_obj=self.Region_obj, gov_level=self.gov_level, GovernmentNumber__lte=self.GovernmentNumber, SessionNumber__lte=self.SessionNumber).exclude(id=self.id).first()
        print('previousCongress',previousCongress)
        if previousCongress:
            obj, update, is_new = get_model_and_update(self.object_type, obj=previousCongress)
            if 'EndDate' not in update.data:
                update.data['EndDate'] = today - datetime.timedelta(days=1)
                # update.data = updateData
                update.func = func
                update, u_is_new = update.save_if_new()
                if update and u_is_new:
                    return update
            # else:
            #     return 
        # except:
        #     # return []
        #     pass
        return None

    def get_gov_num(self):
        return f'{self.GovernmentNumber}-{self.SessionNumber}'

    def version_v1_fields(self):
        fields = ['blockchainId', 'locked_to_chain', 'modelVersion', 'id', 'created', 'publicKey', 'signature', 'Chamber', 'Region', 'GovernmentNumber', 'SessionNumber', 'StartDate', 'EndDate', 'gov_level']
        return fields
    
    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            dt_now = now_utc()
            self.DateTime = dt_now - datetime.timedelta(hours=dt_now.hour, minutes=dt_now.minute, seconds=dt_now.second, microseconds=dt_now.microsecond)
            self = initial_save(self)
        elif not is_locked(self):
            compensate_save(self, Government, *args, **kwargs)
            # super(Government, self).save(*args, **kwargs)
    

    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        p = new_post(self)
        p.save()
        return p




class Agenda(LegisModel):
    object_type = "Agenda"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    bill_dict = models.JSONField(default=None, blank=True, null=True)
    data = models.JSONField(default=None, blank=True, null=True)

    # ---updates
    # EndDateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    # Bill_objs = models.ManyToManyField('posts.Bill', blank=True, related_name='agenda_bills')
    # current_status = models.CharField(max_length=250, default="", blank=True, null=True)
    # NextDateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    # PreviousDateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    # VideoCode = models.IntegerField(default=0, blank=True, null=True)
    # VideoURL = models.URLField(null=True, blank=True)

    def __str__(self):
        return 'AGENDA:%s-%s' %(self.DateTime, self.Chamber)

    class Meta:
        ordering = ['-DateTime']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Agenda', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'bill_dict': None, 'data': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','DateTime','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash']

    def get_absolute_url(self):
        est = pytz.timezone('US/Eastern')
        return "/agenda-item/%s/%s" %(self.Chamber, self.DateTime.astimezone(est).strftime("%Y-%m-%d/%H:%M"))
        # return "/agenda-item/%s-%s-%s/%s:%s" %(self.date_time.astimezone(est).year, self.date_time.astimezone(est).month, self.date_time.astimezone(est).day, self.date_time.astimezone(est).hour, self.date_time.astimezone(est).minute)

    @property
    def is_today(self):
        def convert_to_localtime(utctime):
            fmt = '%Y-%m-%d'
            utc = utctime.replace(tzinfo=pytz.UTC)
            localtz = utc.astimezone(timezone.get_current_timezone())
            return localtz.strftime(fmt)
        return str(datetime.date.today()) == convert_to_localtime(self.DateTime)
        
    def is_last(self):
        a = Agenda.objects.first()
        if self == a:
            return True
        else:
            return False


    # def get_item(self, bill):
    #     print('get_item')
    #     a = AgendaItem.objects.filter(Agenda_obj=self, Bill_obj=bill)
    #     h = Debate.objects.filter(Agenda_obj=self)
    #     for key, value in h.list_all_terms:
    #         if key == a.text:
    #             break
    #     return key

    # def version_v1_fields(self):
    #     fields = ['blockchainId', 'locked_to_chain', 'modelVersion', 'id', 'created', 'publicKey', 'signature', 'Chamber', 'Region', 'DateTime', 'EndDateTime', 'Organization', 'Government', 'gov_level', 'VideoURL', 'VideoCode', 'current_status', 'NextDateTime', 'PreviousDateTime']
    #     return fields
    
    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self, share=share)
        elif not is_locked(self):
            compensate_save(self, Agenda, *args, **kwargs)
            # super(Agenda, self).save(*args, **kwargs)


    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        p = new_post(self)
        p.save(share=share)
        return p

class BillText(BaseModel):
    object_type = "BillText"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    pointerId = models.CharField(max_length=50, default="", blank=True)
    data = models.JSONField(default=dict, blank=True, null=True)
    keyword_array = ArrayField(models.CharField(max_length=50, blank=True, null=True, default=[]), size=20, null=True, blank=True)

    def __str__(self):
        return f'BillText:{self.id}-{self.pointerId}'

    class Meta:
        ordering = ['-created', "pointerId"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'BillText', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'Region_obj': None, 'pointerId': '', 'data': {}, 'keyword_array': []}
            # return {'object_type': 'BillText', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'Region_obj': None, 'pointerId': '', 'data': {}, 'keyword_array':[]}
        # elif int(version) >= 1:
        #     return {'object_type': 'BillText', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'Region_obj': None, 'pointerId': '', 'data': {}}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','pointerId','data']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','pointerId']

    def save(self, share=False, region=None, *args, **kwargs):
        if self.id == '0':
            if region and not self.Region_obj:
                self.Region_obj = region
            elif self.pointerId and not self.Region_obj:
                pointer = Bill.objects.filter(id=self.pointerId).first()
                if pointer and pointer.Region_obj:
                    self.Region_obj = pointer.Region_obj
            self = initial_save(self)
        elif not is_locked(self):
            # from blockchain.models import logError, convert_to_dict
            # logError('try to save billtext', code='76423', func='save', extra={'self':str(convert_to_dict(self))[:200]})
            compensate_save(self, BillText, *args, **kwargs)

    def delete(self):
        if not is_locked(self):
            superDelete(self)


class Bill(LegisModel):
    object_type = "Bill"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Person_obj = models.ForeignKey('legis.Person', blank=True, null=True, on_delete=models.SET_NULL) #sponsor
    GovIden = models.IntegerField(default=0, blank=True, null=True)
    LegisLink = models.URLField(null=True, blank=True) #official link to text of bill
    Started = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    Party_obj = models.ForeignKey('legis.Party', blank=True, null=True, on_delete=models.SET_NULL)
    District_obj = models.ForeignKey('legis.District', related_name='%(class)s_district_obj', blank=True, null=True, on_delete=models.SET_NULL)
    BillText_obj = models.ForeignKey('legis.BillText', related_name='%(class)s_billtext_obj', blank=True, null=True, on_delete=models.SET_NULL)
    
    NumberCode = models.CharField(max_length=20, default="", blank=True, null=True)
    amendedNumberCode = models.CharField(max_length=20, default="", blank=True, null=True) #removes dash for search
    NumberPrefix = models.CharField(max_length=20, default="", blank=True, null=True)
    Number = models.IntegerField(blank=True, null=True)
    
    Subjects = models.CharField(max_length=1000, default="", blank=True, null=True)
    Title = models.CharField(max_length=1000, default="", blank=True, null=True)
    ShortTitle = models.CharField(max_length=1000, default="", blank=True, null=True)
    BillDocumentTypeName = models.CharField(max_length=56, default="", blank=True, null=True) # bill / resolution / ...
    IsGovernmentBill = models.CharField(max_length=10, default="", blank=True, null=True)
    SponsorPersonName = models.CharField(max_length=100, default="", blank=True, null=True)
    SponsorCode = models.CharField(max_length=100, default="", blank=True, null=True)
    keyword_array = ArrayField(models.CharField(max_length=50, blank=True, null=True, default=[]), size=20, null=True, blank=True)
    

    def __str__(self):
        if self.Government_obj:
            return 'BILL:(%s-%s) %s' %(self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.NumberCode)
        else:
            return 'BILL:(%s-%s) %s' %('unknownGov', 'unknownGov', self.NumberCode)

    class Meta:
        ordering = ['-created', "-NumberCode"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Bill', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'Person_obj': None, 'GovIden': 0, 'LegisLink': None, 'Started': None, 'Party_obj': None, 'District_obj': None, 'BillText_obj': None, 'NumberCode': '', 'amendedNumberCode': '', 'NumberPrefix': '', 'Number': None, 'Subjects': '', 'Title': '', 'ShortTitle': '', 'BillDocumentTypeName': '', 'IsGovernmentBill': '', 'SponsorPersonName': '', 'SponsorCode': '', 'keyword_array': None}
            # return {'object_type': 'Bill', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 2, 'Person_obj': None, 'GovIden': 0, 'LegisLink': None, 'Started': None, 'Party_obj': None, 'District_obj': None, 'BillText_obj': None, 'NumberCode': '', 'amendedNumberCode': '', 'NumberPrefix': '', 'Number': None, 'Subjects': '', 'Title': '', 'ShortTitle': '', 'BillDocumentTypeName': '', 'IsGovernmentBill': '', 'SponsorPersonName': '', 'SponsorCode': '', 'keyword_array': None}
        # elif int(version) >= 1:
        #     return {'object_type': 'Bill', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'Person_obj': None, 'GovIden': 0, 'LegisLink': None, 'Started': None, 'Party_obj': None, 'District_obj': None, 'NumberCode': '', 'amendedNumberCode': '', 'NumberPrefix': '', 'Number': None, 'Subjects': '', 'Title': '', 'ShortTitle': '', 'BillDocumentTypeName': '', 'IsGovernmentBill': '', 'SponsorPersonName': '', 'SponsorCode': '', 'keyword_array': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','NumberCode','Government_obj','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','NumberCode','Title','DateTime','Region_obj']

    def get_absolute_url(self):
        if self.Government_obj and self.Government_obj.GovernmentNumber:
            return "/bill/%s/%s/%s/%s/%s" %(self.Country_obj.Name, self.Chamber, self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.NumberCode)
        else:
            return "/bill/%s/%s/%s/%s/%s" %(self.Country_obj.Name, self.Chamber, '00', '00', self.NumberCode)
    
    def get_update_url(self):
        return "/utils/update_bill/%s" %(self.id)

    def get_fields(self):
        return ['%s: %s' %(field.name, field.value_to_string(self)) for field in Bill._meta.fields[:61]]
    
    def choose_nav(self, nav):
        # print(nav)
        try:
            d = json.loads(nav)
            return list(d.items())
        except Exception as e:
            print(str(e))
            return None

    def get_nav(self):
        # if self.royal_assent_nav:
        #     result = self.choose_nav(self.royal_assent_nav)
        # elif self.third_reading_nav:
        #     result = self.choose_nav(self.third_reading_nav)
        # elif self.second_reading_nav:
        #     result = self.choose_nav(self.second_reading_nav)
        # elif self.first_reading_nav:
        #     result = self.choose_nav(self.first_reading_nav)
        # # print(result)
        if self.bill_text_nav:
            d = json.loads(self.bill_text_nav)
            result = list(d.items())
        else:
            result = None
        return result

    def remove_tags(text):
        TAG_RE = re.compile(r'<[^>]+>')
        return TAG_RE.sub('', text)

    def get_latest_version(self):
        # v = BillVersion.objects.filter(Bill_obj=self, current=True)[0]
        return Post.objects.filter(BillVersion_obj__Bill_obj=self, BillVersion_obj__current=True).first()

    def get_bill_keywords(self):
        def strip_tags(text):
            TAG_RE = re.compile(r'<[^>]+>')
            return TAG_RE.sub('', text)
        if self.BillText_obj and self.BillText_obj.data and 'TextHTML' in self.BillText_obj.data:
            text = self.BillText_obj.data['TextHtml']
            if 'TextNav' in self.BillText_obj.data:
                text = text.replace(self.BillText_obj.data['TextNav'], '')
            text = strip_tags(text)
            from posts.models import get_keywords
            self = get_keywords(self, text)
        return self

    def update_keywords(self):
        self.keyword_array = []
        if self.Person_obj and self.Person_obj not in self.keyword_array:
            self.keyword_array.append(self.Person_obj.get_field('FullName'))
        elif not self.Person_obj:
            self.keyword_array.append(self.SponsorPersonName)
        if self.ShortTitle:
            title = f'{self.Chamber} {self.BillDocumentTypeName} {self.amendedNumberCode} ({self.Government_obj.GovernmentNumber}-{self.Government_obj.SessionNumber}): {self.ShortTitle}'
            if title not in self.keyword_array:
                self.keyword_array.append(title)
        # elif self.ShortTitle and self.ShortTitle not in self.keyword_array:
        #     if len(self.ShortTitle) > 980:
        #         title = self.ShortTitle[:977] + '...'
        #     else:
        #         title = self.ShortTitle
        #     title = '*%s Bill %s (%s-%s): %s' %(self.Chamber.replace('-Assembly', ''), self.amendedNumberCode, self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, title[:300])
        #     self.keyword_array.append(title)
        self = self.get_bill_keywords()
        return self

    def save(self, share=False, *args, **kwargs):
        # print('save bill')
        # print(model_to_dict(self))
        if len(self.Title) > 1000:
            print('shorten title')
            self.Title = self.Title[:997] + '...'
        if self.id == '0':

            if not self.ShortTitle:
                if len(self.Title) > 50:
                    self.ShortTitle = self.Title[:50] + '...'
                else:
                    self.ShortTitle = self.Title
            self.amendedNumberCode = self.NumberCode.replace('-', '').replace('.', '').replace(' ', '')
            self = self.update_keywords()
            self = initial_save(self)
        elif not is_locked(self):
            # print('not locked')
            # super(Bill, self).save(*args, **kwargs)
            compensate_save(self, Bill, *args, **kwargs)
            # try:
            #     super(Bill, self).save(*args, **kwargs)
            # except Exception as e:
            #     prntDebug('--------------------------failebill6785',str(e))
            #     if 'is not present in table "legis_bill"' in str(e):
            #         prntDebug('failebill step2')
            #         u = Person(id=self.Person_obj.id)
            #         u.save()
            #         super(Bill, self).save(*args, **kwargs)
            #         prntDebug('failebill step3')
        # print('donesve')
        # time.sleep(4)


    def delete(self):
        if not is_locked(self):
            for text in BillText.objects.filter(pointerId=self.id):
                text.delete()
            superDelete(self)

    def boot(self, share=False):
        # print('boot')
        p = new_post(self)
        if not p.keyword_array:
            p.keyword_array = []
            for k in self.keyword_array:
                if k.lower() not in p.keyword_array:
                    p.keyword_array.append(k.lower())
        p.save(share=share)
        return p

    def new_update(self, update=None):
        # from blockchain.models import logEvent
        if update and 'billText_obj' in update.data:
            # logEvent(f'update bill text: {self.id}-{update.id}-{update.data["billText_obj"]}')
            if not self.BillText_obj or update.data['billText_obj'] != self.BillText_obj.id:
                billText = BillText.objects.filter(id=update.data['billText_obj']).first()
                if billText:
                    from utils.models import dynamic_bulk_update
                    self.BillText_obj = billText
                    self.updated_on_node = now_utc()
                    self = self.update_keywords()
                    dynamic_bulk_update(model=Bill, items_field_update=['BillText_obj', 'keyword_array', 'updated_on_node'], items=[self])
                    

    def upon_validation(self):
        create_keyphrases(self, create_person_trend=True)

    def update_post_time(self):
        # print('running update time')
        p = find_post(self)
        # if p.date_time != self.LatestBillEventDateTime:
        #     users = User.objects.filter(follow_bill=self)
        #     for u in users:
        #         if self.ShortTitle:
        #             title = 'Bill %s, %s' %(self.NumberCode, self.ShortTitle)
        #         else:
        #             title = 'Bill %s, %s' %(self.NumberCode, self.LongTitleEn)
        #         u.alert(title, str(self.get_absolute_url()), None)
        p.DateTime = self.DateTime
        # p.Chamber = self.Chamber
        p.set_score()
        # p.save(share=share)
        if not self.keyword_array:
            self.update_keywords(p)
        # p.save()
        versions = Post.objects.filter(BillVersion_obj__Bill_obj=self, BillVersion_obj__empty=False)
        for v in versions:
            v.BillVersion_obj.boot()

    def hasSummarySpren(self):
        try:
            return Spren.objects.filter(Bill_obj=self, type='summary')[0]
        except:
            return None
    def hasSteelForSpren(self):
        try:
            return Spren.objects.filter(Bill_obj=self, type='steelfor')[0]
        except:
            return None
    def hasSteelAgainstSpren(self):
        try:
            return Spren.objects.filter(Bill_obj=self, type='steelagainst')[0]
        except:
            return None

    def getSpren(self, force):
        print('start getSpren')
        from posts.utils import get_chatgpt_model, get_token_count
        def strip_tags(text):
            TAG_RE = re.compile(r'<[^>]+>')
            return TAG_RE.sub('', text)
        try:
            text = self.bill_text_html.replace(self.bill_text_nav, '')
            text = strip_tags(text)
            model, text = get_chatgpt_model(text)
            num_tokens = get_token_count(text, "cl100k_base")
            print('tokens:', num_tokens)
            print(model)
            import os
            from openai import OpenAI   
            import time
            api_key = ""
            print('summary')
            try:
                spren = Spren.objects.filter(bill=self, type='summary')[0]
                new = False
            except:
                spren = Spren(bill=self, type='summary')
                new = True
            if new or force:
                client = OpenAI(api_key=api_key)
                completion = client.chat.completions.create(
                model = model,
                temperature=0.1,
                max_tokens=500,
                # stream=True,
                messages=[
                    {"role": "system", "content": "You are a non-conversational computer assistant."},
                    {"role": "user", "content": "summarize this to an 18 year old: " + text}
                
                    # {"role": "user", "content": "provide a steelman argument in favor of this: " + text}
                    # {"role": "user", "content": "provide a steelman argument opposing this and use right wing anti-government talking points: " + text}
                ]
                )
                print(completion.choices[0].message.content)
                print(len(completion.choices[0].message.content))
                spren.content = completion.choices[0].message.content[:3000]
                spren.save()
                time.sleep(2)


            print('steelfor')
            try:
                spren = Spren.objects.filter(bill=self, type='steelfor')[0]
                new = False
            except:
                spren = Spren(bill=self, type='steelfor')
                new = True
            if new or force:
                client = OpenAI(api_key=api_key)
                completion = client.chat.completions.create(
                model = model,
                temperature=0.1,
                max_tokens=500,
                # stream=True,
                messages=[
                    {"role": "system", "content": "You are a non-conversational computer assistant."},
                    # {"role": "user", "content": "summarize this to an 18 year old: " + text}
                
                    {"role": "user", "content": "provide a steelman argument in favor of this: " + text}
                    # {"role": "user", "content": "provide a steelman argument opposing this and use right wing anti-government talking points: " + text}
                ]
                )
                print(completion.choices[0].message.content)
                print(len(completion.choices[0].message.content))
                spren.content = completion.choices[0].message.content[:3000]
                spren.save()
                time.sleep(2)
            print('steel against')
            try:
                spren = Spren.objects.filter(bill=self, type='steelagainst')[0]
                new = False
            except:
                spren = Spren(bill=self, type='steelagainst')
                new = True
            if new or force:
                client = OpenAI(api_key=api_key)
                completion = client.chat.completions.create(
                model = model,
                temperature=0.1,
                max_tokens=500,
                # stream=True,
                messages=[
                    {"role": "system", "content": "You are a non-conversational computer assistant."},
                    # {"role": "user", "content": "summarize this to an 18 year old: " + text}
                
                    # {"role": "user", "content": "provide a steelman argument in favor of this: " + text}
                    {"role": "user", "content": "provide a steelman argument opposing this and use right wing anti-government talking points: " + text}
                ]
                )
                print(completion.choices[0].message.content)
                print(len(completion.choices[0].message.content))
                spren.content = completion.choices[0].message.content[:3000]
                spren.save()
            print('saved')
            # u = User.objects.filter(username='Sozed')[0]
            # title = 'Bill %s Spren available' %(self.NumberCode)
            # u.alert(title, str(self.get_absolute_url()), None)
        except Exception as e:
            print(str(e))

class Meeting(LegisModel):
    object_type = "Meeting"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    # Committee_obj = models.ForeignKey('legis.Committee', blank=True, null=True, on_delete=models.SET_NULL)
    meeting_type = models.CharField(max_length=100, default="", blank=True, null=True) # Debate, Committee
    GovPage = models.CharField(max_length=150, default="", blank=True, null=True)
    Title = models.CharField(max_length=150, default="", blank=True, null=True)
    PublicationId = models.CharField(max_length=100, default="", blank=True, null=True)
    hide_time = models.CharField(max_length=100, blank=True, null=True)


    def __str__(self):
        return 'MEETING:(%s) %s' %(self.id, self.Title)
    
    class Meta:
        ordering = ['-DateTime', 'Title']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Meeting', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'meeting_type': '', 'GovPage': '', 'Title': '', 'PublicationId': '', 'hide_time': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','meeting_type','GovPage','PublicationId','Government_obj','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','Title','DateTime','Region_obj']

    def get_absolute_url(self):
        if self.Title:
            return "/%s/%s-meeting/%s/%s/%s" %(self.Government_obj.Region_obj.Name, self.Chamber, self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.Title.replace(' ','_'))
        else:
            return "/%s/%s-meeting/%s/%s/%s" %(self.Government_obj.Region_obj.Name, self.Chamber, self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.id)

    def apply_terms(self, meeting=None, meetingU=None, meeting_is_new=False):
        # print('apply_terms')
        # grouped_by_value = defaultdict(list)
        # for key, value in meeting_terms.items():
        #     grouped_by_value[value].append(key)

        # for keys in grouped_by_value.values():
        #     random.shuffle(keys)

        # sorted_dict = {}
        # for value in sorted(grouped_by_value.keys(), reverse=True):
        #     for key in grouped_by_value[value]:
        #         sorted_dict[key] = value
        # sorted_dict['TESTING'] = True
        if not meeting:
            meeting = self
        if not meetingU:
            meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', obj=self)
        if not meetingU.data:
            meetingU.data = {}
        statements = Statement.objects.filter(Meeting_obj=self)
        meetingU.data['statement_count'] = statements.count()


        H_people = {}
        meeting_terms = {}
        for s in statements:
            p_item = None
            if s.Person_obj:
                p_item = json.dumps({'Name':s.Person_obj.get_field('FullName'), 'obj_id':s.Person_obj.id})
            else:
                p_item = json.dumps({'Name':s.PersonName, 'obj_id':s.PersonName})
            # print('pitem',p_item)
            if p_item:
                try:
                    if not p_item in H_people:
                        H_people[p_item] = 1
                    else:
                        H_people[p_item] += 1
                except Exception as e:
                    # print(str(e))
                    pass
            if s.Terms_array:
                for t in s.Terms_array:
                    if t in meeting_terms:
                        meeting_terms[t] += 1
                    else:
                        meeting_terms[t] = 1
            if s.keyword_array:
                for t in s.keyword_array:
                    if t in meeting_terms:
                        meeting_terms[t] += 1
                    else:
                        meeting_terms[t] = 1
            if s.SubjectOfBusiness:
                if s.SubjectOfBusiness in meeting_terms:
                    meeting_terms[s.SubjectOfBusiness] += 1
                else:
                    meeting_terms[s.SubjectOfBusiness] = 1


        # print('H_people',H_people,'\n')
        # print('meeting_terms',meeting_terms,'\n')

        def sort(item_list):
            grouped_by_value = defaultdict(list)
            for key, value in item_list.items():
                grouped_by_value[value].append(key)

            # for keys in grouped_by_value.values():
            #     random.shuffle(keys)

            sorted_dict = {}
            for value in sorted(grouped_by_value.keys(), reverse=True):
                for key in grouped_by_value[value]:
                    sorted_dict[key] = value
            return sorted_dict

        result  = sort(H_people)
        # print('result',result)
        meetingU.data['People'] = [{key: value} for key, value in list(result.items())]

        meeting_result = sort(meeting_terms)
        # print('Termsresult',result)
        meetingU.data['Terms'] = [{key: value} for key, value in list(meeting_result.items())[:150]]


        # p = Post.objects.filter(pointerId=self.id).first()
        # if p:
        #     p.keyword_array = [key.lower() for key, value in list(meeting_result.items())[:20]]
        #     p.save(share=False)
        return meeting, meetingU, meeting_is_new

    def version_v1_fields(self):
        fields = [
            "object_type",
            "blockchainType",
            "blockchainId",
            "locked_to_chain",
            "modelVersion",
            "id",
            "created",
            "automated",
            "publicKey",
            "signature",
            "Chamber",
            "Region",
            "Government",
            "Agenda",
            "PubIden",
            "GovPage",
            "Title",
            "PublicationDateTime",
            "GovernmentNumber",
            "SessionNumber",
            "PublicationId",
            "Organization",
            "PdfURL",
            "IsTelevised",
            "IsAudioOnly",
            "TypeId",
            "HtmlURL",
            "MeetingIsForSenateOrganization",
            "VideoURL",
            "has_transcript",
            "Subjects",
            "Terms",
            "TermsText",
            "People",
            "PeopleText",
            "completed_model",
        ]
        return fields

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self, share=share)
        elif not is_locked(self):
            compensate_save(self, Meeting, *args, **kwargs)
            # super(Meeting, self).save(*args, **kwargs)


    def delete(self):
        if not is_locked(self):
            for s in Statement.objects.filter(Meeting_obj=self):
                s.delete()
            superDelete(self)

    def new_update(self, update):
        data = update.data
        if 'Terms' in data:
            terms = data['Terms']
            # print('terms',terms)
            p = Post.objects.filter(pointerId=self.id).first()
            if p:
                p.keyword_array = [list(d.keys())[0].lower() for d in update.data['Terms'][:20]]
                p.save()

    def boot(self, share=False):
        # isLatest = True #turn off when building database
        # self.set_Chamber()
        p = new_post(self)
        if not p.keyword_array:
            update = Update.objects.filter(pointerId=self.id).first()
            if update and 'Terms' in update.data:
                data = update.data['Terms']
                # print('data',data)
                p.keyword_array = [key.lower() for z in data for key, value in z.items()]
        p.DateTime = self.DateTime
        p.save()
        return p

    # def list_ten_terms(self):
    #     try:
    #         d = json.loads(self.Terms_json)
    #         return list(d.items())[:10]
    #     except:
    #         return None
    # def list_matching_terms(self, user_keywords):
    #     print('match terms')
    #     try:
    #         from collections import Counter
    #         counter = Counter(user_keywords)
    #         CommonKeys = counter.most_common(500)
    #         print('keylen', len(CommonKeys))
    #         d = json.loads(self.TermsText)
    #         l = []
    #         # print(list(d.items())[:5])
    #         # print()
    #         for key, value in list(d.items())[:75]:
    #             if key not in skipwords:
    #                 # print(key)
    #                 # pass
    #                 # print({key:value})
    #                 l.append((key, value))
    #         return l
    #     except Exception as e:
    #         print(str(e))
    #         return None
    # def list_75_terms(self):
    #     try:
    #         d = json.loads(self.Terms_json)
    #         l = []
    #         # print(list(d.items())[:5])
    #         # print()
    #         for key, value in list(d.items())[:75]:
    #             if key not in skipwords:
    #                 # print(key)
    #                 # pass
    #                 # print({key:value})
    #                 l.append((key, value))
    #         return l
    #     except:
    #         return None
    # def get_terms_overflow(self):
    #     try:
    #         d = json.loads(self.Terms_json)
    #         total = len(d.items())
    #         if total > 75:
    #             remaining = total - 75
    #         else:
    #             remaining = None
    #         return remaining
    #     except:
    #         return None
    # def list_all_terms(self):
    #     # print('list all terms')
    #     try:
    #         d = json.loads(self.Terms_json)
    #         return list(d.items())
    #     except:
    #         return None
    
    def list_people(self):
        # print('list peiple')
        # from accounts.models import Person
        try:
            d = json.loads(self.People_json)
            l = list(d.items())[:10]
            speakers = {}
            keys = []
            for key, value in l:
                keys.append(key)
            people = Person.objects.filter(id__in=keys)
            for p, value in [[p, value] for p in people for key, value in l if p.id == key]:
                speakers[p] = value
            # for key, value in l:
            #     a = Person.objects.filter(id=key)[0]
            #     speakers[a] = value
            return list(speakers.items())
        except Exception as e:
            print(str(e))
            return None

    # def list_all_people(self):
    #     # print('list all people')
    #     from accounts.models import Person
    #     try:
    #         d = json.loads(self.People_json)
    #         l = list(d.items())
    #         speakers = {}
    #         keys = []
    #         for key, value in l:
    #             keys.append(key)
    #         people = Person.objects.filter(id__in=keys)
    #         for p, value in [[p, value] for p in people for key, value in l if p.id == key]:
    #             speakers[p] = value
    #         # for key, value in l:
    #         #     a = Person.objects.filter(id=key)[0]
    #         #     speakers[a] = value
    #         return list(speakers.items())
    #     except Exception as e:
    #         print(str(e))
    #         return None
        
    # from django import template
    # register = template.Library()
    # @register.simple_tag
    # def get_bill_term(self, bill):
    #     d = []
    #     for key, value in self.list_all_terms():
    #         try:
    #             k = Keyphrase.objects.filter(bill=bill, text=key, hansardItem__hansard=self)[0]
    #             print(key)
    #             d.key = value
    #             return key, value
    #         except:
    #             pass
    #     return d

class Statement(LegisModel):
    object_type = "Statement"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Meeting_obj = models.ForeignKey('legis.Meeting', blank=True, null=True, related_name='debate_key', on_delete=models.CASCADE)
    Person_obj = models.ForeignKey('legis.Person', blank=True, null=True, on_delete=models.SET_NULL)
    PersonName = models.CharField(max_length=250, default="", blank=True, null=True)
    Party_obj = models.ForeignKey('legis.Party', blank=True, null=True, on_delete=models.SET_NULL)
    District_obj = models.ForeignKey('legis.District', related_name='%(class)s_district_obj', blank=True, null=True, on_delete=models.SET_NULL)
    keyword_array = ArrayField(models.CharField(max_length=50, blank=True, null=True, default='{default}'), size=15, null=True, blank=True)
    # Bill_objs = models.ManyToManyField('posts.Bill', blank=True, related_name='debateItem_bills')
    # bill_array = ArrayField(models.ForeignKey('posts.Bill', blank=True, null=True, on_delete=models.SET_NULL), size=10, null=True, blank=True)
    bill_dict = models.JSONField(blank=True, null=True)
    ItemId = models.CharField(max_length=100, default="", blank=True, null=True)
    EventId = models.CharField(max_length=100, default="", blank=True, null=True)
    # VideoURL = models.URLField(null=True, blank=True)
    source_link = models.CharField(max_length=350, default="", blank=True, null=True)
    OrderOfBusiness = models.CharField(max_length=255, default="", blank=True, null=True)
    SubjectOfBusiness = models.CharField(max_length=450, default="", blank=True, null=True)
    # EventType = models.CharField(max_length=52, default="", blank=True, null=True)
    # Type = models.CharField(max_length=53, default="", blank=True, null=True)
    Language = models.CharField(max_length=54, default="English", blank=True, null=True)

    Content = models.TextField(default='', blank=True, null=True)
    order = models.PositiveIntegerField(blank=True, null=True) # order of statements made during meeting
    word_count = models.PositiveIntegerField(blank=True, null=True)
    Terms_array = ArrayField(models.CharField(max_length=300, blank=True, null=True, default=[]), size=20, null=True, blank=True)
    
    
    # MeetingTitle = models.CharField(max_length=1000, default="", blank=True, null=True)
    
    # question = models.ForeignKey(Question, blank=True, null=True, on_delete=models.SET_NULL)
    # questions = ArrayField(models.ForeignKey(Question, blank=True, null=True, on_delete=models.SET_NULL), size=10, null=True, blank=True)
    # questions = models.ManyToManyField(Question, blank=True, related_name='hansard_questions')

    def __str__(self):
        return 'STATEMENT:%s(%s-%s)' %(self.PersonName, self.id, self.DateTime)

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Statement', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'Meeting_obj': None, 'Person_obj': None, 'PersonName': '', 'Party_obj': None, 'District_obj': None, 'keyword_array': None, 'bill_dict': None, 'ItemId': '', 'EventId': '', 'source_link': '', 'OrderOfBusiness': '', 'SubjectOfBusiness': '', 'Language': 'English', 'Content': '', 'order': None, 'word_count': None, 'Terms_array': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','Meeting_obj','Person_obj','PersonName','Content','order','Government_obj','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','Meeting_obj','PersonName']

    def get_absolute_url(self):
        # if self.Debate_obj:
        return '%s?id=%s' %(self.Meeting_obj.get_absolute_url(), self.order)
        # elif self.CommitteeMeeting_obj:
        #     return '%s?id=%s' %(self.CommitteeMeeting_obj.get_absolute_url(), self.id)

    def remove_tags(self):
        return re.sub('<[^<]+?>', '', self.Content)

    class Meta:
        ordering = ['-order', '-DateTime', 'created']

    def add_term(self, term, bill, share=False):
        if not self.Terms_array:
            self.Terms_array = []
        if term and term not in self.Terms_array:
            self.Terms_array.append(term)
        if bill and bill.NumberCode not in self.Terms_array:
            self.Terms_array.append(bill.NumberCode)
        if bill:
            if not self.bill_dict:
                self.bill_dict = {}
            self.bill_dict[bill.NumberCode] = {'obj_id':bill.id, 'localLink':bill.get_absolute_url()}
            # if x not in self.bill_array:
            #     self.bill_array.append(x)
        return self

    
    def get_item_keywords(self, share=False):
        def strip_tags(text):
            TAG_RE = re.compile(r'<[^>]+>')
            return TAG_RE.sub('', text)
        text = strip_tags(self.Content)
        from posts.models import get_keywords
        self = get_keywords(self, text)
        return self

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            # from blockchain.models import logEvent
            # logEvent('intital save statement', code='34532', extra={'source_link':self.source_link, 'PersonName':self.PersonName})
            if not self.PersonName and self.Person_obj:
                self.PersonName = self.Person_obj.get_name()
            if not self.DateTime:
                try:
                    self.DateTime = self.Meeting_obj.DateTime
                except:
                    pass
            if not self.Chamber:
                if self.Meeting_obj:
                    self.Chamber = self.Meeting_obj.Chamber
            if not self.Country_obj:
                self.Country_obj = self.Government_obj.Country_obj
            if not self.word_count:
                self.word_count = len(self.Content.strip().split(' '))
            self = self.get_item_keywords()
            self = initial_save(self)
        elif not is_locked(self):
            compensate_save(self, Statement, *args, **kwargs)
            # super(Statement, self).save(*args, **kwargs)
        # prnt('done save statement')
        # from blockchain.models import logEvent
        # logEvent('done save statement', code='5435', extra={'id':self.id})
        
    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, create_person_trend=False, share=False):
        # print('--statement create post')
        p = new_post(self) 
        if not p.keyword_array:
            from utils.models import skipwords
            p.keyword_array = []
            if create_person_trend and p.Person_obj: # not used
                if 'FullName' in p.Person_obj.Update_obj.data and p.Person_obj.Update_obj.data['FullName'].lower() not in p.keyword_array:
                    p.keyword_array.append(p.Person_obj.Update_obj.data['FullName'].lower())
            if self.Terms_array:
                for t in self.Terms_array:
                    if t not in p.keyword_array and t not in skipwords:
                        p.keyword_array.append(t.lower())
            if self.keyword_array:
                for t in self.keyword_array:
                    if t not in p.keyword_array and t not in skipwords:
                        p.keyword_array.append(t.lower())
        p.DateTime = self.DateTime
        p.save()
        return p
    
    def upon_validation(self):
        # from blockchain.models import logEvent
        # logEvent('upon_validation', code='2369', func='upon_validation', extra={'id':self.id})
        create_keyphrases(self, create_person_trend=False)
        personPost = Post.objects.filter(Person_obj=self.Person_obj).first()
        if personPost:
            personPost.DateTime = self.DateTime
            personPost.save()

class Committee(LegisModel):
    object_type = "Committee"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Chair_obj = models.ForeignKey('legis.Person', related_name='committee_chair', blank=True, null=True, on_delete=models.SET_NULL)
    # Member_objs = models.ManyToManyField('posts.Role', blank=True)
    # member_array = ArrayField(models.ForeignKey('posts.Role', blank=True, null=True, on_delete=models.SET_NULL), size=20, null=True, blank=True)
    members = models.JSONField(blank=True, null=True)
    Code = models.CharField(max_length=50, default="", blank=True, null=True)
    Title = models.CharField(max_length=251, default="", blank=True, null=True)
    # GovernmentNumber = models.IntegerField(default=0, blank=True, null=True)
    # SessionNumber = models.IntegerField(default=0, blank=True, null=True)
    GovURL = models.CharField(max_length=500, default="", blank=True, null=True)
    
    # Organization = models.CharField(max_length=1000, default="", blank=True, null=True)
    
    def __str__(self):
        if self.Government_obj.GovernmentNumber:
            return 'COMMITTEE:(%s-%s) %s' %(self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.Title)
        else:
            return 'COMMITTEE:(unknownGov) %s' %(self.Title)
    
    class Meta:
        ordering = ['-created', 'Code']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Committee', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'Chair_obj': None, 'members': None, 'Code': '', 'Title': '', 'GovURL': ''}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','Title','Government_obj','DateTime','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','Title','Government_obj','DateTime']

    def get_absolute_url(self):
        if self.Chamber == 'Senate':
            pref = 'senate-committee'
        elif self.Chamber == 'House of Commons' or self.Chamber == 'House':
            pref = 'house-committee'
        else:   
            pref = 'committee'
        if self.Government_obj:
            govNum = self.Government_obj.GovernmentNumber
            govSess = self.Government_obj.SessionNumber
        else:
            govNum = '00'
            govSess = '00'
        return f"/{pref}/{govNum}/{govSess}/{self.Code}"

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self, share=share)
        elif not is_locked(self):
            compensate_save(self, Committee, *args, **kwargs)
            # super(Committee, self).save(*args, **kwargs)


    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        
        p = new_post(self)
        # p.Chamber = self.Chamber
        # p.gov_level = self.Government.gov_level
        # if self.Organization == 'Senate':
        #     p.organization = 'Senate'
        # else:
        #     p.organization = 'House'
        p.save(share=share)
        return p

class Motion(LegisModel):
    object_type = "Motion"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Bill_obj = models.ForeignKey(Bill, blank=True, null=True, on_delete=models.SET_NULL)
    billCode = models.CharField(max_length=30, default="", blank=True, null=True)
    Person_obj = models.ForeignKey('legis.Person', blank=True, null=True, on_delete=models.SET_NULL)
    # Party_objs = models.ManyToManyField('posts.Party', blank=True, related_name='motion_party')

    # party_array = ArrayField(models.ForeignKey('posts.Party', blank=True, null=True, on_delete=models.SET_NULL), size=20, null=True, blank=True)
    # party_array = ArrayField(models.JSONField(blank=True, null=True), size=20, null=True, blank=True, default=list)
    result_data = models.JSONField(blank=True, null=True)

    GovUrl = models.URLField(null=True, blank=True)
    VoteNumber = models.IntegerField(blank=True, null=True) #DecisionDivisionNumber
    Subject = models.CharField(max_length=500, default="", blank=True, null=True)
    MotionText = models.TextField(blank=True, null=True)
    DecisionType = models.CharField(max_length=500, default="", blank=True, null=True)
    Yeas = models.IntegerField(default=0, blank=True, null=True)
    Nays = models.IntegerField(default=0, blank=True, null=True)
    Present = models.IntegerField(blank=True, null=True)
    Absent = models.IntegerField(blank=True, null=True)
    TotalVotes = models.IntegerField(default=0, blank=True, null=True)
    Result = models.CharField(max_length=200, default="", blank=True, null=True)
    # Requirement = models.CharField(max_length=200, default="", blank=True, null=True)
    is_official = models.BooleanField(default=None, blank=True, null=True)
    
    def __str__(self):
        if self.Government_obj:
            return 'MOTION:(%s-%s) %s/%s' %(self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.VoteNumber, self.Result)
        else:
            return 'MOTION:(%s-%s) %s/%s' %('unknownGov', 'unknownGov', self.VoteNumber, self.Result)

    def get_absolute_url(self):
        if self.Government_obj:
            return "/%s/%s-motion/%s/%s/%s" %(self.Country_obj.Name.lower(), self.Chamber.lower(), self.Government_obj.GovernmentNumber, self.Government_obj.SessionNumber, self.VoteNumber)
        else:
            return "/%s/%s-motion/%s/%s/%s" %(self.Country_obj.Name.lower(), self.Chamber.lower(), 'unknownGov', 'unknownGov', self.VoteNumber)
        # else:
        #     return "/motion/%s/%s/%s" %(self.ParliamentNumber, self.SessionNumber, self.vote_number)

    class Meta:
        ordering = ["-DateTime", '-VoteNumber', '-created']

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Motion', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'Bill_obj': None, 'billCode': '', 'Person_obj': None, 'result_data': None, 'GovUrl': None, 'VoteNumber': None, 'Subject': '', 'MotionText': None, 'DecisionType': '', 'Yeas': 0, 'Nays': 0, 'Present': None, 'Absent': None, 'TotalVotes': 0, 'Result': '', 'is_official': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','VoteNumber','Person_obj','Government_obj','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','DateTime','VoteNumber','Result','Subject','MotionText','billCode']

    def required_for_validation(self):
        return ['Result','TotalVotes']

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            if self.VoteNumber and isinstance(self.VoteNumber, str):
                self.VoteNumber = int(self.VoteNumber)
            self = initial_save(self, share=share)
        elif not is_locked(self):
            compensate_save(self, Motion, *args, **kwargs)
            # super(Motion, self).save(*args, **kwargs)

    def return_votes(self):
        try:
            return self.result_data['Votes']
        except:
            return []
        
    def return_parties(self):
        try:
            return self.result_data['Parties']
        except:
            return []
    
    def delete(self):
        if not is_locked(self):
            for v in Vote.objects.filter(Motion_obj=self):
                v.delete()
            superDelete(self)

    def boot(self, share=False):
        p = new_post(self)
        # p.Chamber = self.Chamber
        # p.gov_level = self.Government.gov_level
            # if self.OriginatingChamberName == 'Senate':
            #     p.organization = 'Senate'
            # else:
            #     p.organization = 'House'
        # p.organization = self.OriginatingChamberName
        if not p.keyword_array:
            p.keyword_array = []
            p.keyword_array.append(self.Subject.lower())
        # try:
        #     keyphrase = Keyphrase.objects.filter(pointerType=self.object_type, pointerId=self.id, Region_obj=self.Region_obj, Chamber=self.Chamber, text=self.Subject)[0]
            
        # except:
        #     keyphrase = Keyphrase(Region_obj=self.Region_obj, Country_obj=self.Country_obj, Chamber=self.Chamber, text=self.Subject) 
        #     keyphrase.save(share=share)
        p.save(share=share)
        return p

class Vote(LegisModel):
    object_type = "Vote"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Motion_obj = models.ForeignKey(Motion, blank=True, null=True, on_delete=models.CASCADE)
    Person_obj = models.ForeignKey('legis.Person', blank=True, null=True, on_delete=models.SET_NULL)
    Party_obj = models.ForeignKey('legis.Party', blank=True, null=True, on_delete=models.SET_NULL)
    District_obj = models.ForeignKey('legis.District', related_name='%(class)s_district_obj', blank=True, null=True, on_delete=models.SET_NULL)
    ConstituencyName = models.CharField(max_length=150, default="", blank=True, null=True)
    VoteValue = models.CharField(max_length=20, default="", blank=True, null=True)
    # PersonOfficialFirstName = models.CharField(max_length=100, default="", blank=True, null=True)
    # PersonOfficialLastName = models.CharField(max_length=100, default="", blank=True, null=True)
    PersonFullName = models.CharField(max_length=100, default="", blank=True, null=True)
    ConstituencyProvStateName = models.CharField(max_length=100, default="", blank=True, null=True)
    CaucusName = models.CharField(max_length=50, default="", blank=True, null=True)
    IsVoteYea = models.CharField(max_length=10, default="", blank=True, null=True)
    IsVoteNay = models.CharField(max_length=10, default="", blank=True, null=True)
    IsVotePresent = models.CharField(max_length=10, default="", blank=True, null=True)
    IsVoteAbsent = models.CharField(max_length=10, default="", blank=True, null=True)
    # DecisionResultName = models.CharField(max_length=50, default="", blank=True, null=True)
    PersonId = models.CharField(max_length=20, default="", blank=True, null=True)

    def __str__(self):
        # if self.Person_obj:
        #     return 'VOTE:person-%s: %s' %(self.Person_obj.id, self.VoteValue)
        # else:
        return 'VOTE:voter-%s-%s-%s' %(self.VoteValue, self.PersonFullName, self.id)

    class Meta:
        ordering = ['PersonFullName', 'ConstituencyName', "-created"]
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Vote', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'Motion_obj': None, 'Person_obj': None, 'Party_obj': None, 'District_obj': None, 'ConstituencyName': '', 'VoteValue': '', 'PersonFullName': '', 'ConstituencyProvStateName': '', 'CaucusName': '', 'IsVoteYea': '', 'IsVoteNay': '', 'IsVotePresent': '', 'IsVoteAbsent': '', 'PersonId': ''}
            # return {'object_type': 'Vote', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 2, 'Motion_obj': None, 'Person_obj': None, 'Party_obj': None, 'District_obj': None, 'ConstituencyName': '', 'VoteValue': '', 'PersonFullName': '', 'ConstituencyProvStateName': '', 'CaucusName': '', 'IsVoteYea': '', 'IsVoteNay': '', 'IsVotePresent': '', 'IsVoteAbsent': '', 'PersonId': ''}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','Motion_obj','Person_obj','PersonFullName']
        # elif int(version) >= 1:
        #     return ['object_type','Motion_obj','Person_obj','PersonFullName','Government_obj','DateTime','Chamber','Region_obj','Country_obj']

    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','PersonFullName','Motion_obj','VoteValue']

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self)
        elif not is_locked(self):
            compensate_save(self, Vote, *args, **kwargs)
            # super(Vote, self).save(*args, **kwargs)


    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        p = new_post(self)
        # try:
        #     print(self.Person_obj)
        #     print(self.Person_obj.Party_obj)
        #     personU = Update.objects.filter(Person_obj=self.Person_obj)[0]
        #     print(personU.Party_obj)
        #     self.Motion_obj.Party_objs.add(personU.Party_obj)
        #     self.Motion_obj.save()
        # except Exception as e:
        #     print(str(e))
        #     pass
        p.save(share=share)
        return p


class Election(LegisModel):
    object_type = "Election"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    # start_date = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    # end_date = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    type = models.CharField(max_length=25, default="", blank=True, null=True)
    gov_level = models.CharField(max_length=20, default=None, blank=True, null=True)
    # riding = models.ForeignKey('accounts.Riding', blank=True, null=True, on_delete=models.SET_NULL)
    District_obj = models.ForeignKey('legis.District', blank=True, null=True, on_delete=models.SET_NULL)
    # total_votes = models.IntegerField(blank=True, null=True)
    # total_valid_votes = models.IntegerField(blank=True, null=True)
    # rejected_votes = models.IntegerField(blank=True, null=True)
    # # Parliament = models.IntegerField(default=0, blank=True, null=True)
    # # government = models.ForeignKey('posts.Government', blank=True, null=True, on_delete=models.SET_NULL)
    # ongoing = models.BooleanField(default=None, blank=True, null=True)

    def __str__(self):
        return 'ELECTION:%s %s' %(self.Chamber, self.type)

    class Meta:
        ordering = ["-DateTime"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Election', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'type': '', 'gov_level': None, 'District_obj': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','DateTime','gov_level','type','District_obj','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','DateTime','Region_obj']

    def get_absolute_url(self):
        # if self.Riding:
        #     return '/election/%s/%s/%s' %(self.Chamber, self.Riding.Name, self.id)
        # if self.District_obj:
        #     return '/election/%s/%s/%s' %(self.Chamber, self.District_obj.Name, self.id)
        # else:
        return '/election/%s/%s/%s' %(self.Chamber, self.Government_obj.Country.Name, self.id)

    # def send_alerts(self):
    #     from accounts.models import User
    #     name = self.District.Name
    #     User.objects.filter(username='Sozed')[0].alert('%s in %s on %s' %(self.type, name, self.end_date), self.get_absolute_url(), "See who's running")
    #     users = User.objects.filter(district=self.district)
    #     for u in users:
    #         u.alert('%s in %s on %s' %(self.type, name, self.end_date), self.get_absolute_url(), "See who's running")

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self = initial_save(self, share=share)
        elif not is_locked(self):
            compensate_save(self, Election, *args, **kwargs)
            # super(Election, self).save(*args, **kwargs)


    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        p = new_post(self)
        # p.set_score()
        p.save(share=share)
        return p

class Party(ModifiableModel):
    object_type = "Party"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    ProvState_obj = models.ForeignKey('posts.Region', related_name='%(class)s_provstate_obj', blank=True, null=True, on_delete=models.CASCADE)
    # Government_obj = models.ForeignKey('posts.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    # DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    Name = models.CharField(max_length=100, default="", blank=True, null=True)
    AltName = models.CharField(max_length=100, default=None, blank=True, null=True)
    ShortName = models.CharField(max_length=100, default=None, blank=True, null=True)
    gov_level = models.CharField(max_length=20, default=None, blank=True, null=True)
    Leader = models.CharField(max_length=30, default=None, blank=True, null=True)
    Color = models.CharField(max_length=30, default="#808080")
    InfoLink = models.URLField(null=True, blank=True)
    LogoLink = models.URLField(null=True, blank=True)
    StartDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    EndDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    # Websites = models.CharField(max_length=1000, default='[]', blank=True, null=True)
    Website_array = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=10, null=True, blank=True)
    Wiki = models.URLField(null=True, blank=True)

    def __str__(self):
        return 'PARTY:%s-%s' %(self.Name, self.gov_level)

    class Meta:
        ordering = ['-proposed_modification', "Name"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Party', 'is_modifiable': True, 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'last_updated': None, 'proposed_modification': None, 'modelVersion': 1, 'Chamber': '', 'Region_obj': None, 'Country_obj': None, 'ProvState_obj': None, 'Name': '', 'AltName': None, 'ShortName': None, 'gov_level': None, 'Leader': None, 'Color': '#808080', 'InfoLink': None, 'LogoLink': None, 'StartDate': None, 'EndDate': None, 'Website_array': None, 'Wiki': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['Name','gov_level','Country_obj','Chamber']
    
    # def commit_data(self, version=None):
    # if not version:
    #     version = self.modelVersion
    # if version <= 1:
        #     return ['id']

    def update_data(self, share=False):
        self.signature = ''
        self.modelVersion = self.latestModel
        self.last_updated = now_utc()
        self.save(share=share)

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            if self.Color == "#808080":
                self.Color = self.set_color()
            self = initial_save(self)
        else:
            compensate_save(self, Party, *args, **kwargs)
            # super(Party, self).save(*args, **kwargs)

    def set_color(self):
        colorList = {
            'country' : {
                'Canada' : {
                    'Liberal' : '#ED2E38',
                    'Conservative' : '#002395',
                    'NDP' : '#FF5800',
                    'Bloc Québécois' : '#0088CE',
                    'Green Party' : '#427730',
                    'Progressive Senate Group' : '#ED2E38',
                    'Canadian Senators Group' : '#386B67',
                    'Independent Senators Group' : '#845B87',
                    'Conservative Party of Canada' : '#002395',
                },
                'USA' : {
                    'Republican' : '#D61F26',
                    'Democratic' : '#0044C8',
                    'Libertarian' : '#FED000',
                    'Green' : '#427730',
                }
            },
            'Republican' : '#D61F26',
            'Democratic' : '#0044C8',
            'Libertarian' : '#FED000',
            'Green' : '#427730',
        }
        try:
            return colorList[self.Region_obj.modelType][self.Region_obj.Name][self.Name]
        except:
            try:
                return colorList[self.Region_obj.modelType][self.Name]
            except:
                try:
                    return colorList[self.Name]
                except:
                    return self.Color

    def boot(self, share=False):
        # from posts.models import Post, Keyphrase
        p = new_post(self)
        if not p.keyword_array:
            p.keyword_array = []
            p.keyword_array.append(self.Name.lower())
        # if self.level == 'Federal':
        #     organization = 'House'
        # else:
        #     organization = self.province_name
        # try:
        #     keyphrase = Keyphrase.objects.filter(pointerType=self.object_type, pointerId=self.id, text=self.Name)[0]
        # except:
        #     keyphrase = Keyphrase(pointerType=self.object_type, pointerId=self.id, Chamber=self.Chamber, text=self.Name) 
        #     keyphrase.save(share=share)
        if self.AltName and self.AltName.lower() not in p.keyword_array:
            p.keyword_array.append(self.AltName.lower()) 
            # try:
            #     keyphrase = Keyphrase.objects.filter(pointerType=self.object_type, pointerId=self.id, text=self.AltName)[0]
            # except:
            #     keyphrase = Keyphrase(pointerType=self.object_type, pointerId=self.id, Chamber=self.Chamber, text=self.AltName) 
            #     keyphrase.save(share=share)
        p.save(share=share)
        return p

    def delete(self):
        pass
    #     # if not is_locked(self):
    #     superDelete(self)

    def fillout(self):
        #for federal only
        print('fillout - party: %s' %(self.Name))
        try:
            if not self.Leader:
                print('opening browser')
                chrome_options = Options()
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument("--headless")
                driver = webdriver.Chrome(options=chrome_options)
                caps = DesiredCapabilities().CHROME
                caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
                # caps["pageLoadStrategy"] = "eager"   # Do not wait for full page load
                driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
                # url= 'https://lop.parl.ca/sites/ParlInfo/default/en_CA/Parties/Profile?partyId=15161'
                print(self.InfoLink)
                driver.get(self.InfoLink)
                element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="gridPartyLeaders"]/div/div[5]'))
                WebDriverWait(driver, 15).until(element_present)
                # time.sleep(1)
                try:
                    div = driver.find_element(By.ID, 'PartyPic')
                    try:
                        img = div.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                        if 'LogoNA' not in img:
                            self.LogoLink = img
                    except:
                        self.LogoLink = None
                    try:
                        div = driver.find_element(By.ID, 'PartyInfo')
                        h = div.find_element(By.CSS_SELECTOR, 'h2').text
                        a = h.find('(')
                        b = h[a:].find(' - ')
                        date = h[a:a+b]
                        date_time = datetime.datetime.strptime(date, '(%Y-%m-%d')
                        self.start_date = date_time
                    except:
                        pass
                    info = div.find_elements(By.CSS_SELECTOR, 'p')
                    # for i in info:
                    #     if 'Last Official Leader' in i.text:
                    #         print(i.text)
                    #         try:
                    #             l = i.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    #             role = Role.objects.filter(GovPage=l)[0]
                    #             p = role.Person_obj
                    #             self.Leader = '%s, %s' %(p.LastName, p.FirstName)
                    #             try:
                    #                 r = Role.objects.get(Person_obj=p, Position='Party Leader')
                    #             except:
                    #                 r = Role(Person_obj=p, Current=True, Position='Party Leader')
                    #             r.Current = True
                    #             r.save()
                    #         except Exception as e:
                    #             print(str(e))
                    #             self.Leader = i.text.replace('Last Official Leader: ', '')
                    website = div.find_element(By.CSS_SELECTOR, 'tr').find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    self.Websites_array = website
                except Exception as e:
                    print(str(e))
                driver.close()
                # wikipedia
            if not self.Wikipedia:
                name = '%s Canada' %(self.Name)
                title = wikipedia.search(name)[0].replace(' ', '_')
                self.Wikipedia = 'https://en.wikipedia.org/wiki/' + title
                if not self.LogoLink:
                    r = requests.get('https://en.wikipedia.org/wiki/' + title)
                    soup = BeautifulSoup(r.content, 'html.parser')
                    td = soup.find('td', {'class':'logo'})
                    img = td.find('img')['src']
                    self.LogoLink = img
                    # print(name)
                    # driver.get("https://en.wikipedia.org/wiki/Main_Page")
                    # element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="searchInput"]'))
                    # WebDriverWait(driver, 15).until(element_present)
                    # # time.sleep(1)
                    # searchbox = driver.find_element(By.XPATH, '//*[@id="searchInput"]')
                    # searchbox.send_keys(name)
                    # time.sleep(1)
                    # search_enter = driver.find_element(By.XPATH, '//*[@id="searchform"]/div/button')
                    # # searchbox.send_keys(Keys.RETURN)
                    # search_enter.click()
                    # # time.sleep(1)
                    # element_present = EC.presence_of_element_located((By.CLASS_NAME, 'mw-search-results-container'))
                    # WebDriverWait(driver, 10).until(element_present)
                    # # time.sleep(1)
                    # div = driver.find_element(By.CLASS_NAME, 'mw-search-results-container')
                    # li = div.find_element(By.CSS_SELECTOR, 'li')
                    # d = li.find_element(By.CLASS_NAME, 'mw-search-result-heading')
                    # a = d.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    # self.wikipedia = a
                    # if not self.img_link: 
                    #     driver.get(a)
                    #     td = driver.find_element(By.CLASS_NAME, 'infobox-image')
                    #     img = td.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    #     self.img_link = img
            self.save()
        except Exception as e:
            print(str(e))
            self.save()

class Person(BaseModel):
    object_type = "Person"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    GovIden = models.CharField(max_length=50, blank=True, null=True)
    GovProfilePage = models.CharField(max_length=500, blank=True, null=True)
    Update_obj = models.ForeignKey('posts.Update', related_name='%(class)s_update_obj', blank=True, null=True, on_delete=models.SET_NULL)
    # Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    # PersonData_obj = models.ForeignKey('posts.PersonData', related_name='%(class)s_data_obj', blank=True, null=True, on_delete=models.CASCADE)
    
    
    # Government_obj = models.ForeignKey('legis.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    # DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)



    def __str__(self):
        if self.Country_obj and self.Country_obj.Name:
            return 'PERSON:%s %s' %(self.GovIden, self.Country_obj.Name)
        else:
            return 'PERSON:%s NoCountry' %(self.GovIden)

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Person', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'GovIden': None, 'GovProfilePage': None, 'Update_obj': None, 'Region_obj': None, 'Country_obj': None}
            # return {'object_type': 'Person', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'GovIden': None, 'GovProfilePage': None, 'Update_obj': None, 'Region_obj': None, 'Country_obj': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','GovIden','Region_obj']
        # elif int(version) >= 1:
        #     return ['object_type','GovIden','Country_obj']

    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','Region_obj','GovIden']

    def get_name(self, update_obj=None):
        if not update_obj:
            update_obj = Update.objects.filter(pointerId=self.id).first()
        if update_obj:
            if update_obj['Honorific']:
                return '%s %s %s' %(update_obj['Honorific'], update_obj['FirstName'], update_obj['LastName'])
            else:
                return '%s %s' %(update_obj['FirstName'], update_obj['LastName'])
        elif self.GovIden:
            return str(self.GovIden)
        else:
            return str(self.GovProfilePage)

    def get_field(self, field, update_obj=None):
        update_obj = self.Update_obj
        if update_obj:
            if field in update_obj.data:
                return update_obj.data[field]
        return None

    class Meta:
        ordering = ["GovIden", 'Country_obj', 'id']

    def update_role(self, update_obj, role=None, current=False, data=None):
        # print('update_role', update_obj, role)
        found = False
        if not update_obj.extra:
            update_obj.extra = {}
        if 'roles' not in update_obj.extra:
            # print('e1')
            update_obj.extra['roles'] = []
        if data:
            # print('d')
            role = data['role']
            # print('role',role)
            for r in update_obj.extra['roles']:
                # print("r['role']",r['role'])
                if r['role'] == role:
                    r.update(data)
                    # print('rrr',r)
                    # r[role] = data
                    found = True
                    # print('f1')
                    break
            if not found:
                # print('f2')
                update_obj.extra['roles'].append(data)
        else:
            # print('e')
            for r in update_obj.extra['roles']:
                # print('e0')
                if r['role'] == role:
                # if role in r:
                    r['current'] = current
                    found = True
                    # print('e1')
                    break
            if not found:
                # print('e2')
                update_obj.extra['roles'].append({'role':role, 'current':current})
        # print('done role update')



    def get_absolute_url(self):
        #return reverse("sub", kwargs={"subject": self.name})
        # if not update_obj:
        #     update_obj = Update.objects.filter(pointerId=self.id).first()
        if self.Update_obj:
            if self.GovIden:
                return "/profile/%s/%s_%s/%s" % (self.Region_obj.Name, self.Update_obj.data['FirstName'].replace(' ', '_'), self.Update_obj.data['LastName'].replace(' ', '_'), self.GovIden)
            else:
                return "/profile/%s/%s_%s/%s" % (self.Region_obj.Name, self.Update_obj.data['FirstName'].replace(' ', '_'), self.Update_obj.data['LastName'].replace(' ', '_'), self.id)
        else:
            if self.GovIden:
                return f"/profile/{self.GovIden}"
            else:
                return f"/profile/{self.id}"
            
    def new_update(self, update):
        self.Update_obj = update
        self.save()

    def upon_validation(self):
        create_keyphrases(self, create_person_trend=True)
        if not self.Update_obj:
            u = Update.objects.filter(pointerId=self.id, validated=True).order_by('-DateTime').first()
            if u:
                self.Update_obj = u
                self.save()
        # update = Update.objects.filter(pointerId=self.id).first()
        # if update:
        #     personPost = Post.objects.filter(Person_obj=self.Person_obj).first()
        #     if personPost:
        #         # personPost.DateTime = self.DateTime
        #         personPost.keyword_array.append(self.FullName.lower()) 
        #         personPost.save()

    def save(self, share=False, *args, **kwargs):
        prntDebug('------------saving person....')
        if self.id == '0':
            # if not self.FullName:
            #     self.FullName = self.first_last()
            if self.Country_obj and not self.Region_obj:
                self.Region_obj = self.Country_obj
            # filter_args = {field: getattr(self, field) for field in self.get_hash_to_id() if field != 'salt'}
            # self.salt = Person.objects.filter(**filter_args).exclude(id='0').count()
            self = initial_save(self)
        else:
            compensate_save(self, Person, *args, **kwargs)


    def boot(self, share=False):
        p = new_post(self)
        if not p.keyword_array:
            p.keyword_array = []
        p.save()
        prnt('created person post:',p)
        return p
    
    def delete(self):
        superDelete(self)
        

class District(ModifiableModel):
    object_type = "District"
    blockchainType = 'Region'
    Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    # Government_obj = models.ForeignKey('posts.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    # DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)

    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    
    # Government_obj = models.ForeignKey('posts.Government', blank=True, null=True, on_delete=models.RESTRICT)
    # modelType = models.CharField(max_length=100, default="") #federal, provState, municipal
    Office_array = ArrayField(models.CharField(max_length=30, default='', blank=True, null=True), size=25, null=True, blank=True)
    nameType = models.CharField(max_length=100, default="", blank=True, null=True) # Riding, District, Ward
    Name = models.CharField(max_length=100, default="", blank=True, null=True)
    AltName = models.CharField(max_length=100, default="", blank=True, null=True)
    gov_level = models.CharField(max_length=100, default="", blank=True, null=True) # Federal, Provincial, State, Greater Municipal, Municipal
    # province_name = models.CharField(max_length=100, default="")
    # Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    ProvState_obj = models.ForeignKey('posts.Region', related_name='%(class)s_provstate_obj', blank=True, null=True, on_delete=models.CASCADE)
    # Region_obj = models.ForeignKey(Region, related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.RESTRICT)
    Population = models.IntegerField(blank=True, null=True)
    StartDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    MapLink = models.URLField(null=True, blank=True)
    InfoLink = models.URLField(null=True, blank=True)
    Info = models.TextField(blank=True, null=True)
    # opennorthId = models.IntegerField(default=0, blank=True, null=True)
    Wiki = models.URLField(null=True, blank=True)


    def __str__(self):
        if self.ProvState_obj:
            return 'DISTRICT:%s-%s/%s' %(self.Name, self.ProvState_obj.Name, self.Region_obj.Name)
        elif self.Region_obj:
            return 'DISTRICT:%s-%s' %(self.Name, self.Region_obj.Name)
        else:
            return 'DISTRICT:%s' %(self.Name)

    class Meta:
        ordering = ['-proposed_modification', "Name"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'District', 'is_modifiable': True, 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'last_updated': None, 'proposed_modification': None, 'Chamber': '', 'Region_obj': None, 'Country_obj': None, 'modelVersion': 1, 'Office_array': None, 'nameType': '', 'Name': '', 'AltName': '', 'gov_level': '', 'ProvState_obj': None, 'Population': None, 'StartDate': None, 'MapLink': None, 'InfoLink': None, 'Info': None, 'Wiki': None}
        
    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['Name','gov_level','Country_obj','ProvState_obj']
    
    def add_office(self, office_name):
        if not self.Office_array:
            self.Office_array = []
        if office_name not in self.Office_array:
            if office_name:
                self.Office_array.append(office_name)
            self.update_data()
            return True
        else:
            return False
    
    def update_data(self, share=False):
        self.signature = ''
        self.modelVersion = self.latestModel
        self.last_updated = now_utc()
        self.save(share=share)

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            if not self.Region_obj:
                self.Region_obj = self.Country_obj
            self = initial_save(self, share=share)
        else:
            compensate_save(self, District, *args, **kwargs)
            # super(District, self).save(*args, **kwargs)

    def boot(self, share=False):
        p = new_post(self)
        p.save()
        return p

    def delete(self):
        # pass
        if not is_locked(self):
            superDelete(self)

    def fillout(self):
        print('fillout - Riding: %s' %(self.Name))
        try:
            if not self.map_link:
                chrome_options = Options()
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument("--headless")
                driver = webdriver.Chrome(options=chrome_options)
                caps = DesiredCapabilities().CHROME
                caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
                # caps["pageLoadStrategy"] = "eager"   # Do not wait for full page load
                driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
                print(self.parlinfo_link)
                driver.get(self.parlinfo_link)
                element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="RidingPic"]'))
                WebDriverWait(driver, 10).until(element_present)
                div = driver.find_element(By.ID, 'RidingPic')
                img = div.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                self.map_link = img
                div = driver.find_element(By.ID, 'RidingInfo')
                h = div.find_element(By.CSS_SELECTOR, 'h2').text
                a = h.find('(')
                b = h[a:].find(' - ')
                date = h[a:a+b]
                try:
                    date_time = datetime.datetime.strptime(date, '(%Y-%m-%d')
                    self.StartDate = date_time
                except:
                    try:
                        date_time = datetime.datetime.strptime(date, '(%Y-%m')
                        self.StartDate = date_time
                    except:
                        pass
                text = driver.find_element(By.ID, 'RidingNotes').text
                self.info = text
                driver.close()
                # wikipedia
            if not self.wikipedia:
                name = '%s %s federal electoral district' %(self.Name, self.Region_obj.Name)
                title = wikipedia.search(name)[0].replace(' ', '_')
                self.wikipedia = 'https://en.wikipedia.org/wiki/' + title
                # if not self.img_link:
                #     r = requests.get('https://en.wikipedia.org/wiki/' + title)
                #     soup = BeautifulSoup(r.content, 'html.parser')
                #     td = soup.find('td', {'class':'logo'})
                #     img = td.find('img')['src']
                #     self.img_link = img

                    # name = '%s Canada' %(self.name)
                    # print(name)
                    # driver.get("https://en.wikipedia.org/wiki/Main_Page")
                    # element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="searchInput"]'))
                    # WebDriverWait(driver, 15).until(element_present)
                    # # time.sleep(1)
                    # searchbox = driver.find_element(By.XPATH, '//*[@id="searchInput"]')
                    # searchbox.send_keys(name)
                    # time.sleep(1)
                    # search_enter = driver.find_element(By.XPATH, '//*[@id="searchform"]/div/button')
                    # # searchbox.send_keys(Keys.RETURN)
                    # search_enter.click()
                    # # time.sleep(1)
                    # element_present = EC.presence_of_element_located((By.CLASS_NAME, 'mw-search-results-container'))
                    # WebDriverWait(driver, 10).until(element_present)
                    # # time.sleep(1)
                    # div = driver.find_element(By.CLASS_NAME, 'mw-search-results-container')
                    # li = div.find_element(By.CSS_SELECTOR, 'li')
                    # d = li.find_element(By.CLASS_NAME, 'mw-search-result-heading')
                    # a = d.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    # self.wikipedia = a
                    # if not self.map_link: 
                    #     driver.get(a)
                    #     td = driver.find_element(By.CLASS_NAME, 'infobox-image')
                    #     img = td.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    #     self.map_link = img
            self.save()
        except Exception as e:
            print(str(e))
            self.save()

# class Recap(LegisModel):
#     object_type = "Recap"
#     blockchainType = 'Region'
#     # blockchainId = models.CharField(max_length=50, default="0")
#     # locked_to_chain = models.BooleanField(default=False)
#     latestModel = 1
#     modelVersion = models.IntegerField(default=latestModel)
#     # id = models.CharField(max_length=50, default="0", primary_key=True)
#     # created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
#     # automated = True
#     # publicKey = models.CharField(max_length=200, default="0")
#     # signature = models.CharField(max_length=200, default="0")
#     # Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
#     # Region_obj = models.ForeignKey('accounts.Region', related_name='daily_region_obj', blank=True, null=True, on_delete=models.RESTRICT)
#     # Country_obj = models.ForeignKey('accounts.Region', related_name='daily_country_obj', blank=True, null=True, on_delete=models.CASCADE)
#     # # Region_obj = models.ForeignKey('accounts.Region', related_name='daily_region_obj', blank=True, null=True, on_delete=models.CASCADE)
#     # last_updated = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
#     # Government_obj = models.ForeignKey(Government, blank=True, null=True, on_delete=models.SET_NULL)
#     User_obj = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.CASCADE)
#     # date_time = models.DateTimeField(auto_now=False, auto_now_add=False, blank=False, null=True)
    
#     # organization = models.CharField(max_length=250, default="", blank=True, null=True)
    
#     content = models.JSONField(default=dict, blank=True, null=True)
    
#     def __str__(self):
#         return 'Recap:%s, %s' %(self.Chamber, self.DateTime)

#     class Meta:
#         ordering = ["-DateTime"]

#     def get_version_fields(self, version=None):
#         if not version:
#             version = self.modelVersion
#         if version <= 1:
#             return ['id', 'created', 'added', 'updated_on_node', 'func', 'creatorNodeId', 'validatorNodeId', 'Validator_obj', 'blockchainId', 'Block_obj', 'publicKey', 'signature', 'validation_error', 'Chamber', 'Region_obj', 'Country_obj', 'Government_obj', 'DateTime', 'modelVersion', 'User_obj', 'content']
        
#     def get_hash_to_id(self, version=None):
#         if not version:
#             version = self.modelVersion
#         if version <= 1:
#             return ['object_type','User_obj','content','DateTime','Government_obj','Region_obj','Country_obj']
    
#     # def commit_data(self, version=None):
#     # if not version:
#     #     version = self.modelVersion
#     # if version <= 1:
#         #     return ['hash']

#     def get_absolute_url(self):
#         return '/legislature?date=%s-%s-%s' %(self.DateTime.year, self.DateTime.month, self.DateTime.day)

#     def save(self, share=False, *args, **kwargs):
#         if self.id == '0':
#             self = initial_save(self, share=share)
#         elif not is_locked(self):
#             super(Recap, self).save(*args, **kwargs)


#     def delete(self):
#         if not is_locked(self):
#             superDelete(self)

#     def boot(self, share=False):
#         # self.save()
#         # try:
#         #     p = Post.objects.filter(daily=self)[0]
#         # except:
#         #     try:
#         #         p = Archive.objects.filter(daily=self)[0]
#         #     except:
#         #         p = Post()
#         #         p.daily = self
#         #         p.date_time = self.date_time
#         #         p.post_type = 'daily'
#         p = new_post(self)
#         # p.Chamber = self.Chamber
#         # p.gov_level = self.Government.gov_level
#                 # text = self.content
#                 # stop_words = set(stopwords.words('english'))
#                 # stop_words_french = set(stopwords.words('french'))
#                 # kw_model = KeyBERT()
#                 # p.keywords = []
#                 # x = kw_model.extract_keywords(text, top_n=10, keyphrase_ngram_range=(1, 1), stop_words=None)
#                 # n = 0
#                 # for i, r in x:
#                 #     if i not in skipwords and i not in stop_words and i not in stop_words_french and i not in p.keywords and n <= 10:
#                 #         p.keywords.append(i)
#                 #         n += 1
#                 # x = kw_model.extract_keywords(text, top_n=10, keyphrase_ngram_range=(2, 2), stop_words=None)
#                 # n = 0
#                 # for i, r in x:
#                 #     if i not in skipwords and i not in p.keywords and n <= 5:
#                 #         p.keywords.append(i)
#                 #         n += 1
#         p.save(share=share)
#         # print('done create dailyPost')
#         return p


# class PersonData(ModifiableBaseModel):
#     object_type = "PersonData"

#     Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
#     Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
#     Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
#     # Government_obj = models.ForeignKey('posts.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
#     # DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
#     salt = models.IntegerField(default=0)
#     latestModel = 1
    # modelVersion = models.IntegerField(default=latestModel)
#     Honorific = models.CharField(max_length=100, blank=True, null=True, default="")
#     FirstName = models.CharField(max_length=100, blank=True, null=True, default="")
#     LastName = models.CharField(max_length=100, blank=True, null=True, default="")
#     FullName = models.CharField(max_length=200, default="")
#     Position = models.CharField(max_length=200, default="")
#     ProvState_obj = models.ForeignKey('posts.Region', blank=True, related_name='%(class)s_provstate_obj', null=True, on_delete=models.SET_NULL)
#     Party_obj = models.ForeignKey('legis.Party', blank=True, null=True, on_delete=models.SET_NULL)
#     District_obj = models.ForeignKey('legis.District', blank=True, null=True, on_delete=models.SET_NULL)
#     gov_level = models.CharField(max_length=100, default="", blank=True, null=True) # Federal, Provincial, State, Greater Municipal, Municipal
#     PhotoLink = models.CharField(max_length=400, blank=True, null=True)
#     Websites = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=10, null=True, blank=True, default=list)
#     Gender = models.CharField(max_length=15, blank=True, null=True)
#     Emails = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=10, null=True, blank=True, default=list)
#     Telephones = ArrayField(models.CharField(max_length=20, default='', blank=True, null=True), size=10, null=True, blank=True, default=list)
#     Socials = ArrayField(models.JSONField(default=dict, blank=True, null=True), size=10, null=True, blank=True, default=list)
#     Wiki = models.CharField(max_length=200, blank=True, null=True)
#     Bio = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return 'PERSONDATA:%s %s' %(self.FirstName, self.LastName)

    # def get_version_fields(self, version=None):
    # if not version:
    #     version = self.modelVersion
    #     if version <= 1:
    #         return 
        
# #     def get_hash_to_id(self, version=None):
# if not version:
#     version = self.modelVersion
# #       versioname','LastName','Country_obj','salt']

# #     def first_last(self):
# #         return '%s %s' %(self.FirstName, self.LastName)

# #     def last_first(self):
# #         return '%s %s' %(self.LastName, self.FirstName)
    

# #     def save(self, share=False, *args, **kwargs):
# #         if self.id == '0':
# #             if not self.FullName:
# #                 self.FullName = self.first_last()
# #             if self.Country_obj and not self.Region_obj:
# #                 self.Region_obj = self.Country_obj
# #             filter_args = {field: getattr(self, field) for field in self.get_hash_to_id() if field != 'salt'}
# #             self.salt = Person.objects.filter(**filter_args).exclude(id='0').count()
# #             self = initial_save(self, share=share)
# #         else:
# #             super(Person, self).save(*args, **kwargs)


# # class Role(LegisModel):
# #     object_type = "Role"
# #     blockchainType = 'Region'
# #     latestModel = 1
#     # modelVersion = models.IntegerField(default=latestModel)
# #     Person_obj = models.ForeignKey('legis.Person', blank=True, null=True, on_delete=models.CASCADE)
# #     District_obj = models.ForeignKey('legis.District', related_name='%(class)s_district_obj', blank=True, null=True, on_delete=models.SET_NULL)
# #     ProvState_obj = models.ForeignKey('posts.Region', blank=True, related_name='%(class)s_provstate_obj', null=True, on_delete=models.SET_NULL)
# #     Party_obj = models.ForeignKey(Party, blank=True, null=True, on_delete=models.SET_NULL)
# #     Committee_obj = models.ForeignKey('legis.Committee', related_name='%(class)s_committee_obj',  blank=True, null=True, on_delete=models.CASCADE)
# #     Election_obj = models.ForeignKey('legis.Election', blank=True, null=True, on_delete=models.SET_NULL)
# #     StartDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
# #     # EndDate = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
# #     PhotoLink = models.CharField(max_length=400, blank=True, null=True)
# #     Title = models.CharField(max_length=200, default="", blank=True, null=True) #exmaple chair or member
# #     # GovernmentNumber = models.CharField(max_length=10, default="", blank=True, null=True)
# #     gov_level = models.CharField(max_length=100, default="", blank=True, null=True) # Federal, Provincial, State, Greater Municipal, Municipal
# #     salt = models.IntegerField(default=0)
# #     # person_name = models.CharField(max_length=101, default="", blank=True, null=True)
# #     # party_name = models.CharField(max_length=102, default="", blank=True, null=True)
# #     # riding_name = models.CharField(max_length=103, default="", blank=True, null=True)
# #     # district_name = models.CharField(max_length=152, default="", blank=True, null=True)
# #     # municipality_name = models.CharField(max_length=104, default="", blank=True, null=True)
# #     member_detail = models.CharField(max_length=105, default="", blank=True, null=True)
# #     Position = models.CharField(max_length=200, default="", blank=True, null=True) #example MP or committee member
# #     # constituency_name = models.CharField(max_length=106, default="", blank=True, null=True)
# #     # province_name = models.CharField(max_length=50, default="", blank=True, null=True)
# #     # attendanceCount = models.IntegerField(default=None, blank=True, null=True)
# #     # attendancePercent = models.IntegerField(default=None, blank=True, null=True)
# #     # quarterlyExpenseReport = models.FloatField(default=None, blank=True, null=True)
# #     # Result = models.CharField(max_length=40, default="", blank=True, null=True)
# #     # Group = models.CharField(max_length=300, default="", blank=True, null=True)
# #     order = models.IntegerField(default=0) # for ourcommons/roles and senator list page scrape
# #     # vote_count = models.IntegerField(default=0)
# #     # vote_percent = models.IntegerField(default=0)
# #     # occupation = ArrayField(models.CharField(max_length=20, blank=True, null=True, default='{default}'), size=6, null=True, blank=True)
# #     # Current = models.BooleanField(default=False)
# #     # identifier = models.CharField(max_length=300, default='', blank=True, null=True)
# #     Affiliation = models.CharField(max_length=100, default="", blank=True, null=True)
# #     Occupation = models.CharField(max_length=100, default="", blank=True, null=True)
# #     GovPage = models.CharField(max_length=250, default="", blank=True, null=True)
# #     # Websites = models.CharField(max_length=1000, default='[]', blank=True, null=True)
# #     Websites = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=10, null=True, blank=True)
# #     # Emails = models.CharField(max_length=1000, default='[]', blank=True, null=True)
# #     Emails = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=10, null=True, blank=True)
# #     Fax = models.CharField(max_length=26, blank=True, null=True)
# #     # Telephones = models.CharField(max_length=1000, default='[]', blank=True, null=True)
# #     Telephones = ArrayField(models.CharField(max_length=20, default='', blank=True, null=True), size=10, null=True, blank=True)
# #     # Addresses = models.CharField(max_length=1000, default='[]', blank=True, null=True)
# #     Addresses = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=10, null=True, blank=True)
# #     OfficeName = models.CharField(max_length=250, default="", blank=True, null=True)
# #     # Socials = models.CharField(max_length=1000, default='[]', blank=True, null=True)
# #     Socials = ArrayField(models.JSONField(default=dict, blank=True, null=True), size=10, null=True, blank=True)


# #     # --updates
# #     # Current
# #     # EndDate

# #     def __str__(self):
# #         return 'ROLE:%s-%s/%s: %s' %(self.id, self.Title, self.Position, self.Person_obj.FullName)

# #     class Meta:
# #         ordering = ["order","-StartDate","Position","Title",'created']
    
#     # def get_version_fields(self, version=None):
#     if not version:
#         version = self.modelVersion
#     #     if version <= 1:
#     #         return 
        
# #     def get_hash_to_id(self, version=None):
# if not version:
#     version = self.modelVersion
# #       versionon','Title','gov_level','Person_obj','Country_obj','Chamber','District_obj','ProvState_obj','salt']
    
# #     def boot(self, share=False):
# #         p = new_post(self)
# #         p.save(share=share)
# #         return p

# #     def save(self, share=False, *args, **kwargs):
# #         print('role save1')
# #         if self.id == '0':
# #             # print('1')
# #             filter_args = {field: getattr(self, field) for field in self.get_hash_to_id() if field != 'salt'}
# #             # print('filter_args',filter_args)
# #             self.salt = Role.objects.filter(**filter_args).exclude(id='0').count()
# #             # print('self.salt',self.salt)
# #             self = initial_save(self, share=share)
# #             # super(Role, self).save()
# #         elif not is_locked(self):
# #             print('r save2')
# #             super(Role, self).save(*args, **kwargs)


# #     def delete(self):
# #         if not is_locked(self):
# #             superDelete(self)


# # class AgendaTime(LegisModel):
# #     object_type = "AgendaTime"
# #     blockchainType = 'Region'
# #     # blockchainId = models.CharField(max_length=50, default="0")
# #     # locked_to_chain = models.BooleanField(default=False)
# #     latestModel = 1
#     # modelVersion = models.IntegerField(default=latestModel)
# #     # id = models.CharField(max_length=50, default="0", primary_key=True)
# #     # created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
# #     # automated = True
# #     # publicKey = models.CharField(max_length=200, default="0")
# #     # signature = models.CharField(max_length=200, default="0")
# #     # Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
# #     # Region_obj = models.ForeignKey('accounts.Region', related_name='agendatime_region_obj', blank=True, null=True, on_delete=models.RESTRICT)
# #     # Country_obj = models.ForeignKey('accounts.Region', blank=True, null=True, on_delete=models.CASCADE)
# #     # last_updated = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
# #     # Government_obj = models.ForeignKey(Government, blank=True, null=True, on_delete=models.SET_NULL)
# #     Agenda_obj = models.ForeignKey(Agenda, blank=True, null=True, on_delete=models.CASCADE)
    
# #     # updates
# #     # DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
# #     # Bill_objs = models.ManyToManyField('posts.Bill', blank=True, related_name='agendaTime_bills')
# #     # bill_array = ArrayField(models.ForeignKey('posts.Bill', blank=True, null=True, on_delete=models.SET_NULL), size=20, null=True, blank=True)
# #     bill_array = models.JSONField(default=dict, blank=True, null=True)
    
# #     def __str__(self):
# #         return 'AGENDATIME:%s' %(self.DateTime)

# #     def get_absolute_url(self):
# #         est = pytz.timezone('US/Eastern')
# #         return "/agenda-item/%s" %(self.DateTime.astimezone(est).strftime("%Y-%m-%d/%H:%M"))
# #         # return "/agenda-item/%s-%s-%s/%s:%s" %(self.date_time.astimezone(est).year, self.date_time.astimezone(est).month, self.date_time.astimezone(est).day, self.date_time.astimezone(est).hour, self.date_time.astimezone(est).minute)

# #     class Meta:
# #         ordering = ['-DateTime']

#     # def get_version_fields(self, version=None):
#     if not version:
#         version = self.modelVersion
#     #     if version <= 1:
#     #         return 
        
# #     def get_hash_to_id(self, version=None):
# if not version:
#     version = self.modelVersion
# #       version_type','DateTime','Agenda_obj','Chamber','Region_obj','Country_obj']
    
# #     def version_v1_fields(self):
# #         fields = ['blockchainId', 'locked_to_chain', 'modelVersion', 'id', 'created', 'publicKey', 'signature', 'Chamber', 'Region', 'DateTime', 'EndDateTime', 'Organization', 'Government', 'gov_level', 'VideoURL', 'VideoCode', 'current_status', 'NextDateTime', 'PreviousDateTime']
# #         return fields
    
# #     def save(self, share=False, *args, **kwargs):
# #         if self.id == '0':
# #             self.Government_obj = self.Agenda_obj.Government_obj
# #             self = initial_save(self, share=share)
# #         elif not is_locked(self):
# #             super(AgendaTime, self).save(*args, **kwargs)


# #     def delete(self):
# #         if not is_locked(self):
# #             superDelete(self)

# #     def boot(self, share=False):
# #         p = new_post(self)
# #         # if self.agenda.gov_level == 'Senate':
# #         #     p.organization = 'Senate'
# #         # else:
# #         #     p.organization = 'House'
# #         p.save(share=share)
# #         return p

# # class AgendaItem(LegisModel):
# #     object_type = "AgendaItem"
# #     blockchainType = 'Region'
# #     # blockchainId = models.CharField(max_length=50, default="0")
# #     # locked_to_chain = models.BooleanField(default=False)
# #     latestModel = 1
#     # modelVersion = models.IntegerField(default=latestModel)
# #     # id = models.CharField(max_length=50, default="0", primary_key=True)
# #     # created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
# #     # automated = True
# #     # publicKey = models.CharField(max_length=200, default="0")
# #     # signature = models.CharField(max_length=200, default="0")
# #     # Chamber = models.CharField(max_length=100, default="", blank=True, null=True)
# #     # Region_obj = models.ForeignKey('accounts.Region', related_name='agendaitem_region_obj', blank=True, null=True, on_delete=models.RESTRICT)
# #     # Country_obj = models.ForeignKey('accounts.Region', blank=True, null=True, on_delete=models.CASCADE)
# #     # last_updated = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
# #     # Government_obj = models.ForeignKey(Government, blank=True, null=True, on_delete=models.SET_NULL)
# #     Agenda_obj = models.ForeignKey(Agenda, blank=True, null=True, on_delete=models.CASCADE)
# #     AgendaTime_obj = models.ForeignKey(AgendaTime, blank=True, null=True, on_delete=models.CASCADE)
# #     Bill_obj = models.ForeignKey('posts.Bill', blank=True, null=True, on_delete=models.SET_NULL)
# #     # DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
# #     Text = models.CharField(max_length=250, default="", blank=True, null=True)
    
# #     # organization = models.CharField(max_length=250, default="", blank=True, null=True)
# #     # gov_level = models.CharField(max_length=250, default="", blank=True, null=True)
    
# #     position = models.IntegerField(default=0, blank=True, null=True)
    
# #     has_post = models.BooleanField(default=False)

# #     def __str__(self):
# #         return 'AGENDAITEM:%s-%s' %(self.Text, self.position)

# #     def get_absolute_url(self):
# #         est = pytz.timezone('US/Eastern')
# #         return "/agenda-item/%s/%s" %(self.Chamber, self.DateTime.astimezone(est).strftime("%Y-%m-%d/%H:%M"))
# #         # return "/agenda-item/%s-%s-%s/%s:%s" %(self.date_time.astimezone(est).year, self.date_time.astimezone(est).month, self.date_time.astimezone(est).day, self.date_time.astimezone(est).hour, self.date_time.astimezone(est).minute)

# #     class Meta:
# #         ordering = ['position','DateTime', 'created',] #required ordering for agenda_card

#     # def get_version_fields(self, version=None):
#     if not version:
#         version = self.modelVersion
#     #     if version <= 1:
#     #         return 
        
# #     def get_hash_to_id(self, version=None):
# if not version:
#     version = self.modelVersion
# #       version_type','DateTime','Agenda_obj','AgendaTime_obj','Text','Chamber','Region_obj','Country_obj']
    
# #     def save(self, share=False, *args, **kwargs):
# #         if self.id == '0':
# #             self.Government_obj = self.Agenda_obj.Government_obj
# #             self = initial_save(self, share=share)
# #         elif not is_locked(self):
# #             super(AgendaItem, self).save(*args, **kwargs)
    

# #     def delete(self):
# #         if not is_locked(self):
# #             superDelete(self)

# # class BillVersion(LegisModel):
# #     object_type = "BillVersion"
# #     blockchainType = 'Region'
# #     latestModel = 1
#     # modelVersion = models.IntegerField(default=latestModel)
# #     Bill_obj = models.ForeignKey(Bill, blank=True, null=True, on_delete=models.CASCADE)
# #     NumberCode = models.CharField(max_length=100, default="", blank=True, null=True)
# #     Version = models.CharField(max_length=100, default="", blank=True, null=True)
# #     Summary = models.TextField(blank=True, null=True)
# #     TextHtml = models.TextField(blank=True, null=True)
# #     TextNav = models.TextField(blank=True, null=True)
# #     # Current = models.BooleanField(default=False)
# #     # empty = models.BooleanField(default=True)
    
# #     class Meta:
# #         ordering = ['-DateTime']

# #     def __str__(self):
# #         return 'BILLVERSION:(%s-%s) %s-%s' %(self.Bill_obj.Government_obj.GovernmentNumber, self.Bill_obj.Government_obj.SessionNumber, self.NumberCode, self.Version)

# #     def get_absolute_url(self):
# #         return '%s?reading=LatestReading' %(self.Bill_obj.get_absolute_url())


# #     def get_nav(self):
# #         print('get nav')
# #         if self.TextNav:
# #             d = json.loads(self.TextNav)
# #             result = list(d.items())
# #         else:
# #             result = None
# #         return result
    
# #     def get_bill_keywords(self, p):
# #         #not running after text is received because it takes too long, keywords is title and sponsor only
# #         def strip_tags(text):
# #             TAG_RE = re.compile(r'<[^>]+>')
# #             return TAG_RE.sub('', text)
# #         if self.TextHtml:
# #             text = self.TextHtml.replace(self.TextNav, '')
# #             text = strip_tags(text)
# #             self, p = get_keywords(self, p, text)

# #             self.save()
# #             # p.save()
# #         return self, p

# #     def save(self, share=False):
# #         if self.id == '0':
# #             if not self.DateTime:
# #                 self.DateTime = self.Bill_obj.DateTime
# #             self = initial_save(self, share=share)
# #         elif not is_locked(self):
# #             super(BillVersion, self).save()


# #     def delete(self):
# #         if not is_locked(self):
# #             superDelete(self)

# #     def boot(self, share=False):
# #         p = new_post(self)
# #         # print(p)
# #         if self.DateTime:
# #             p.DateTime = self.DateTime
# #         # else:
# #         #     try:
# #         #         if self.bill.PassedFirstChamberFirstReadingDateTime < self.bill.PassedSecondChamberFirstReadingDateTime:
# #         #             self.bill.Started = self.bill.PassedFirstChamberFirstReadingDateTime
# #         #             self.bill.save()
# #         #             p.DateTime = self.bill.Started
# #         #             # print(self.bill.started)
# #         #         elif self.bill.PassedSecondChamberFirstReadingDateTime < self.bill.PassedFirstChamberFirstReadingDateTime:
# #         #             self.bill.Started = self.bill.PassedSecondChamberFirstReadingDateTime
# #         #             self.bill.save()
# #         #             p.DateTime = self.bill.started
# #         #     except Exception as e:
# #         #         print(str(e))
# #         #         self.Bill_obj.Started = now_utc()
# #         #         self.Bill_obj.save()
# #         #         p.DateTime = self.Bill_obj.Started
# #         #     # print(self.bill.started)
# #         # print('p.keywords', p.keyword_array)
# #         # p.keyword_array = []
# #         # for k in self.keyword_array:
# #         # self, p = self.get_bill_keywords(p):
# #         # if p.keyword_array:
# #         #     p.keyword_array.clear()
# #         # p.keyword_array.append('%s?current=%s' %(self.Bill_obj.NumberCode, str(self.Current)))
# #         p.save(share=share)
# #         return p

