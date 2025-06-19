from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.fields import ArrayField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from django.forms.models import model_to_dict
# from utils.models import prnt, prntDev, prntDebug, prntn, now_utc, is_timezone_aware, testing, has_field, has_method, find_or_create_chain_from_object, get_pointer_type, initial_save, is_locked, save_mutable_fields, get_model, get_dynamic_model, superDelete
from utils.models import *
from utils.locked import sign_obj, hash_obj_id

import random
# import json
import pytz
import datetime
# import time
# from zoneinfo import ZoneInfo
import decimal
from nltk.corpus import stopwords
# import hashlib
# from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)



model_prefixes = {'Post':'pst','Update':'upd','Spren':'spr','GenericModel':'gen','Keyphrase':'key','KeyphraseTrend':'kytr','Region':'reg'}

class BaseModel(models.Model):
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    func = models.CharField(max_length=50, default="", blank=True)
    creatorNodeId = models.CharField(max_length=50, default="", blank=True)
    validatorNodeId = models.CharField(max_length=50, default="", blank=True)
    Validator_obj = models.ForeignKey('blockchain.Validator', blank=True, null=True, on_delete=models.PROTECT)
    blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.PROTECT)
    publicKey = models.CharField(max_length=200, default="", blank=True)
    signature = models.CharField(max_length=200, default="", blank=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    
    class Meta:
        abstract = True



class ValidObjsQuerySet(models.QuerySet):
    def default_filter(self):
        return self.filter(proposed_modification=None)

class ValidObjsManager(models.Manager):
    def get_queryset(self):
        return ValidObjsQuerySet(self.model, using=self._db).default_filter()

    def all(self, *args, **kwargs):
        return self.get_queryset()

    def include_invalid(self):
        return super().get_queryset()
    
class ModifiableModel(BaseModel):
    is_modifiable = True
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    proposed_modification = models.CharField(max_length=200, default=None, blank=True, null=True)
    
    objects = models.Manager()
    valid_objects = ValidObjsManager()

    class Meta:
        abstract = True

    def propose_modification(self):
        prnt('propose_modification')
        # requires Name field, Name must not change
        if self.id != '0' and not self.proposed_modification:
            mod = get_dynamic_model(self.object_type, proposed_modification=self.id)
            if not mod:
                from utils.models import create_dynamic_model
                mod = create_dynamic_model(self.object_type)
            from blockchain.models import convert_to_dict
            from utils.models import super_sync
            mod = super_sync(mod, convert_to_dict(self), if_empty_fields=['created'], skip_fields=['Validator_obj','signature','publicKey'])
            if not mod.proposed_modification:
                mod.proposed_modification = self.id
                mod.id = hash_obj_id(mod)
            mod.update_data()
            return mod
        else:
            return self





def get_latest_update(pointerId):
    return Update.objects.filter(pointerId=pointerId).order_by('-created').first()


def create_keyphrases(obj, create_person_trend=False):
    prnt('create keyphrase')
    from utils.models import skipwords
    phrases = []
    terms = []
    if has_field(obj, 'Terms_array'):
        if obj.Terms_array:
            for t in obj.Terms_array:
                if t not in skipwords:
                    terms.append(t)
    if has_field(obj, 'Person_obj') and create_person_trend:
        if obj.Person_obj and obj.Person_obj.Update_obj:
            if has_field(obj, 'keyword_array'):
                if not obj.keyword_array:
                    obj.keyword_array = [] 
                if 'FullName' in obj.Person_obj.Update_obj.data and obj.Person_obj.Update_obj.data['FullName'] not in obj.keyword_array:
                    obj.keyword_array.append(obj.Person_obj.Update_obj.data['FullName'])
            if obj.Person_obj.Update_obj.data['FullName'] not in skipwords:
                terms.append(obj.Person_obj.Update_obj.data['FullName'])
    if has_field(obj, 'keyword_array'):
        if obj.keyword_array:
            for t in obj.keyword_array:
                if t not in skipwords:
                    terms.append(t)
    # prnt('1')
    if has_field(obj, 'DateTime') and obj.DateTime:
        dt = obj.DateTime
    elif has_field(obj, 'Started') and obj.Started:
        dt = obj.Started
    elif has_field(obj, 'created') and obj.created:
        dt = obj.created
    else:
        dt = now_utc()

    for t in terms:
        if t:
            keyphrase = Keyphrase.objects.filter(key=t[:300]).first()
            if not keyphrase:
                keyphrase = Keyphrase(key=t[:300])
                keyphrase.created = dt

            phraseData = {'obj_id':obj.id, 'Region':obj.Region_obj.id, 'Country':obj.Country_obj.id, 'Chamber':obj.Chamber, 'DateTime':dt_to_string(dt)}
            if phraseData not in keyphrase.pointer_array:
                if not keyphrase.first_occured or keyphrase.first_occured > dt:
                    keyphrase.first_occured = dt
                if keyphrase.pointer_array and len(keyphrase.pointer_array) >= 10000:
                    keyphrase.pointer_array.pop(0)
                keyphrase.pointer_array.append(phraseData)

                keyphrase.last_updated = now_utc()
                if keyphrase.last_occured and keyphrase.last_occured > dt:
                    pass
                else:
                    keyphrase.last_occured = dt
                keyphrase.save()
                keyphrase.set_trend()

def get_keywords(obj, text, numOfKeys=7):
    prnt('get keyowrds')
    from utils.models import skipwords
    # logEvent('get keyowrds', code='4674')
    # stop_words = set(stopwords.words('english'))
    # stop_words_french = set(stopwords.words('french'))

    # get_keywords fail,No module named '_bz2'

    if len(text.strip().split(' ')) > 20:
        import re
        text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = text.lower().strip()
        prntDebug('s1')
        start_time = datetime.datetime.now()
        if obj.object_type == 'Statement':
            statement = text
            text = ''
            if obj.OrderOfBusiness:
                text = text + obj.OrderOfBusiness + '\n'
            if obj.SubjectOfBusiness:
                text = text + obj.SubjectOfBusiness + '\n'
            text = text + statement
        try:
            import yake

            # skip_words = {"example", "discussion", "important"}  # Replace with your list

            # print('1')
            spacy_stopwords = set()
            try:
                import spacy

                nlp = spacy.load("en_core_web_sm")
                spacy_stopwords = nlp.Defaults.stop_words
            except Exception as e:
                prnt('e:',str(e))

            # print('2')
            try:
                try:
                    from nltk.corpus import stopwords
                    import nltk
                    nltk_stopwords = set(stopwords.words("english"))
                    # custom_stopwords = {"example", "discussion", "important"}
                except:
                    from nltk.corpus import stopwords
                    import nltk
                    nltk.download("stopwords") # only needs to run the first time
                    nltk_stopwords = set(stopwords.words("english"))
            except Exception as e:
                prnt('fail keyowrkds nltk',str(e))
                nltk_stopwords = set()

            stop_w = set(skipwords)

            final_stopwords = nltk_stopwords | stop_w | spacy_stopwords
            # prnt('final_stopwords isinst list',isinstance(final_stopwords, list))
            # prnt('final_stopwords isinst set',isinstance(final_stopwords, set))
            # prnt('final_stopwords isinst dict',isinstance(final_stopwords, dict))



            
            def extract_keywords(text, n=3, top_n=6):
                kw_extractor = yake.KeywordExtractor(n=n, top=top_n, stopwords=final_stopwords)
                keywords = [kw[0] for kw in kw_extractor.extract_keywords(text)]
                return keywords

            spares = {}
            obj.keyword_array = []
            # prntDebug('s4')
            x = extract_keywords(text, n=5, top_n=2)
            # prntDebug('s4.1')
            n = 0
            terms = ''
            for i in x:
                if i not in stop_w and i not in obj.keyword_array and n < numOfKeys and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
                    n += 1
                    terms = terms + i + ' '
            # prntDebug('s5')
            # prntDebug('obj.keyword_array 00',obj.keyword_array)
            # prntDebug('s4')
            x = extract_keywords(text, n=4, top_n=2)
            # prntDebug('s4.1')
            # n = 0
            # terms = ''
            for i in x:
                if i not in obj.keyword_array and i not in stop_w and i not in obj.keyword_array and n < numOfKeys and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
                    n += 1
                    terms = terms + i + ' '
            # prntDebug('s5')
            # prntDebug('obj.keyword_array 0',obj.keyword_array)
            x = extract_keywords(text, n=2, top_n=3)
            # prntDebug('s6')
            # n = 0
            # terms = ''
            for i in x:
                if i not in stop_w and i not in obj.keyword_array and n < numOfKeys and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
                    n += 1
                    terms = terms + i + ' '
            # prntDebug('s7')
            # prntDebug('obj.keyword_array 1',obj.keyword_array)
            x = extract_keywords(text, n=1, top_n=7)
            # prntDebug('s8')
            # n = 0
            for i in x:
                if i not in stop_w and not i.isnumeric():
                    if i in str(terms):
                        if i in spares:
                            spares[i] += 1
                        else:
                            spares[i] = 1
                    elif n < numOfKeys:
                        obj.keyword_array.append(i)
                        stop_w.add(i)
                        n += 1
            if spares:
                prnt('spares',spares)
            #     for term, count in spares.items():
            #         matches = 0
            #         for i in obj.keyword_array:
            #             if term in i:
            #                 matches += 1
            #         if count > matches or matches > 2:
            #             for i in obj.keyword_array:
            #                 if term in i:
            #                     obj.keyword_array.remove(i)
            #             obj.keyword_array.append(term)


            # # obj.keyword_array = []
            # # for i in reduced_keywords:
            # #     # prnt('i',i)
            # #     if i not in stop_w and i not in obj.keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
            # #         # prnt('y',i)
            # #         obj.keyword_array.append(i)


            # prntDebug('s9')
            # prntDebug('obj.keyword_array 2',obj.keyword_array)
        
        except Exception as e:
            prnt('get_keywords fail', str(e))
            from blockchain.models import logEvent
            logEvent(e, code='59385', func='get_keywords', extra={'obj':obj.id}, log_type='Errors')
            # time.sleep(10)
        finish_time = datetime.datetime.now() - start_time
        prnt('keywords time:',finish_time)
    # logEvent('done get keyowrds', code='765343')
    return obj


def get_point_value(post):
    if post.total_yeas > 1000:
        score = 0.042 # ~1hr per 1000 upvotes
    elif post.total_yeas > 500:
        score = 0.417 # ~1hr per 100 upvotes
    elif post.total_yeas > 75:
        score = 1.04 # ~1hr per 40 upvotes
    elif post.total_yeas > 10:
        score = 4.166 # ~1hr per 10 upvotes
    else:
        score = 41.66 # ~1hr added to rank per upvote for first 10 votes
    return score

def scoreMe(post, save_item=True):
    if post.randomizer == 0:
        post.randomizer = random.randint(1,333) #used in algorithim to reduce number of hansardItems and mix up content by up to 8hrs -- not used anymore
    baseline = baseline_time()
    try:
        t = post.DateTime - baseline
    except Exception as e:
        # prnt(str(e))
        t = post.DateTime - baseline.replace(tzinfo=pytz.UTC)
    secs = t.seconds * (1000 / 86400) # converts 24hrs in seconds to 1000, so there isnt' a big jump in rank numbers at the end of the day
    r = ((t.days * 1000) + secs)  #1000 - 1 day == 1000 on rank scale, 1 minute = 0.694 rank score
    post = post.tally_votes()
    score = get_point_value(post)
    post.rank = decimal.Decimal(r) + decimal.Decimal((post.total_yeas*score))
    post.verifiedRank = decimal.Decimal(r) + decimal.Decimal((post.total_verified_yeas*score))
    if save_item:
        post.save(share=False)



subRegions = ['ProvState', 'Country', 'Region', 'Continent', 'Province', 'State', 'County', 'City', 'Ward']


def new_post(obj):
    # prnt('new_post()')
    p = Post.all_objects.filter(pointerId=obj.id).first()
    if not p or not p.get_pointer(set_pointer=False):
        if not p:
            p = Post(pointerId=obj.id)

        if has_field(obj, 'DateTime') and obj.DateTime:
            p.DateTime = obj.DateTime
        elif has_field(obj, 'Started') and obj.Started:
            p.DateTime = obj.Started
        elif has_field(obj, 'created') and obj.created:
            p.DateTime = obj.created

        # if has_field(obj, 'added') and obj.added:
        #     p.added = obj.added
        # elif has_field(obj, 'created_dt') and obj.created_dt:
        #     p.added = obj.created_dt
        if has_field(obj, 'created') and obj.created:
            p.created = obj.created

        p.pointerId = obj.id
        p.pointerType = obj.object_type
        pointer, p = p.set_pointer(do_save=False, return_self=True)
        p.keyword_array = []

        if has_field(obj, 'Country_obj'):
            p.Country_obj = obj.Country_obj
        if has_field(obj, 'Government_obj') and obj.Government_obj:
            p.Government_obj = obj.Government_obj
            p.filters['gov_level'] = obj.Government_obj.gov_level
        elif has_field(obj, 'object_type') and obj.object_type == 'Government':
            p.Government_obj = obj
            p.filters['gov_level'] = obj.gov_level
        if has_field(obj, 'Chamber'):
            p.filters['Chamber'] = obj.Chamber
        if has_field(obj, 'Region_obj'):
            p.Region_obj = obj.Region_obj
        if not has_field(obj, 'blockchainId'):
            p.blockId = 'N/A'
        return p
    return p

def find_post(obj):
    p = Post.all_objects.filter(pointerId=obj.id).first()
    if not p:
        try:
            p = Archive.objects.filter(pointerId=obj.id).first()
        except:
            p = None
    return p

def update_post(obj=None, p=None, save_p=True, update=None):
    updated_fields = []
    if obj and has_method(obj, 'boot') or p and p.pointerId:
        if obj and not p:
            p = Post.all_objects.filter(pointerId=obj.id).first()
        elif p and not obj:
            obj = get_dynamic_model(p.pointerType, id=p.pointerId)
        if not p or not p.get_pointer(set_pointer=False):
            obj.boot()
        else:
            dt = None
            if has_field(obj, 'DateTime'):  
                dt = obj.DateTime
            elif has_field(obj, 'created'):
                dt = obj.created
            if dt and p.DateTime != dt:
                p.DateTime = dt
                updated_fields.append('DateTime')
            elif has_field(obj, 'created') and obj.created:
                if not p.DateTime or p.DateTime < obj.created:
                    p.DateTime = obj.created
                    updated_fields.append('DateTime')
            if has_field(obj, 'created'):
                if not p.created or p.created < obj.created:
                    p.created = obj.created
                    updated_fields.append('created')
            if update and update != p.Update_obj:
                if not p.Update_obj or update.created > p.Update_obj.created:
                    returned_post = update.sync_with_post(post=p, pointer=obj, do_save=False)
                    if returned_post and isinstance(returned_post, models.Model) and returned_post.object_type == 'Post':
                        p = returned_post
                        updated_fields.append('Update_obj')
                        updated_fields.append('filters')
                        updated_fields.append('keyword_array')
                        if 'DateTime' not in updated_fields:
                            updated_fields.append('DateTime')

            if p.Update_obj:
                if not p.DateTime or not dt or p.Update_obj.DateTime and p.Update_obj.DateTime > dt:
                    p.DateTime = p.Update_obj.DateTime
                    if 'DateTime' not in updated_fields:
                        updated_fields.append('DateTime')

            if has_field(obj, 'keyword_array') and obj.keyword_array:
                for i in obj.keyword_array[:20]:
                    if i not in p.keyword_array:
                        p.keyword_array.append(i)
                        if 'keyword_array' not in updated_fields:
                            updated_fields.append('keyword_array')
            if has_field(obj, 'Country_obj') and p.Country_obj != obj.Country_obj:
                p.Country_obj = obj.Country_obj
                updated_fields.append('Country_obj')
            if has_field(obj, 'Government_obj') and obj.Government_obj:
                if p.Government_obj != obj.Government_obj:
                    p.Government_obj = obj.Government_obj
                    updated_fields.append('Government_obj')
                if has_field(obj, 'gov_level') and p.gov_level != obj.gov_level:
                    p.gov_level = obj.Government_obj.gov_level
                    updated_fields.append('gov_level')
            elif has_field(obj, 'object_type') and obj.object_type == 'Government' and has_field(obj, 'gov_level') and p.gov_level != obj.gov_level:
                p.gov_level = obj.gov_level
                updated_fields.append('gov_level')
            if has_field(obj, 'Chamber') and p.Chamber != obj.Chamber:
                p.Chamber = obj.Chamber
                updated_fields.append('Chamber')
            if has_field(obj, 'Region_obj') and p.Region_obj != obj.Region_obj:
                p.Region_obj = obj.Region_obj
                updated_fields.append('Region_obj')
            if not has_field(obj, 'blockchainId') and p.blockId != 'N/A':
                p.blockId = 'N/A'
                updated_fields.append('blockId')
            if save_p:
                p.save()
    return p, updated_fields

    

# def default_region_menu():
#     return {'Bill': {'name':'Bill','plural':'Bills'}, 'Meeting': {'name':'Debate','plural':'Debates'}, 'Motion': {'name':'RollCall','plural':'RollCalls'}, 'Person': {'name':'Representative','plural':'Officials'}}

class Region(ModifiableModel):
    object_type = "Region"
    blockchainType = 'Region'
    secondChainType = 'Sonet'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    ParentRegion_obj = models.ForeignKey('posts.Region', blank=True, null=True, on_delete=models.SET_NULL)
    nameType = models.CharField(max_length=20, default="State", blank=True) # Continent, Country, Province, State, County, City, Ward
    modelType = models.CharField(max_length=20, default="provState", null=True, blank=True) # provState/country/city
    Name = models.CharField(max_length=100, default="", blank=True)
    AbbrName = models.CharField(max_length=10, default=None, blank=True, null=True)
    FullName = models.CharField(max_length=100, default=None, blank=True, null=True)
    LogoLinks = models.JSONField(default=None, blank=True, null=True)
    # LogoLink = models.CharField(max_length=100, default="img/default_region.jpg", null=True, blank=True)
    timezone = models.CharField(max_length=20, default="US/Eastern", null=True, blank=True)
    data = models.JSONField(default=None, blank=True, null=True)
    menuItem_array = ArrayField(models.CharField(max_length=50, default='', blank=True, null=True), size=7, null=True, blank=True)
    Chamber_array = ArrayField(models.CharField(max_length=30, default='', blank=True, null=True), size=10, null=True, blank=True)
    Office_array = ArrayField(models.CharField(max_length=30, default='', blank=True, null=True), size=25, null=True, blank=True)
    Wiki = models.URLField(default=None, null=True, blank=True)
    is_supported = models.BooleanField(default=False)

    def __str__(self):
        return 'REGION:%s/%s' %(self.Name, self.nameType)
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Region', 'is_modifiable': True, 'blockchainType': 'Region', 'secondChainType': 'Sonet', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'last_updated': None, 'proposed_modification': None, 'modelVersion': 1, 'ParentRegion_obj': None, 'nameType': 'State', 'modelType': 'provState', 'Name': '', 'AbbrName': None, 'FullName': None, 'LogoLinks': None, 'timezone': 'US/Eastern', 'data': None, 'menuItem_array': None, 'Chamber_array': None, 'Office_array': None, 'Wiki': None, 'is_supported': False}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','Name','ParentRegion_obj','modelType']
        # elif int(version) >= 1:
        #     return ['object_type','Name','ParentRegion_obj']

    class Meta:
        ordering = ['-proposed_modification', "created"]

    def lowerName(self):
        return self.Name.lower()

    def add_office(self, office_name):
        # prnt('add_office',office_name)
        if not self.Office_array:
            self.Office_array = []
        if office_name not in self.Office_array:
            self.Office_array.append(office_name)
            self.update_data()
            return True
        else:
            return False
        
    def add_chamber(self, chamber_name):
        if not self.Chamber_array:
            self.Chamber_array = []
        if chamber_name not in self.Chamber_array:
            self.Chamber_array.append(chamber_name)
            self.update_data()
            return True
        else:
            return False

    def update_data(self, share=False):
        self.signature = ''
        self.modelVersion = self.latestModel
        self.last_updated = now_utc()
        self.save()

    def initialize(self):
        self.created = now_utc()
        return self

    def save(self, share=False, *args, **kwargs):
        # prnt('saving region', model_to_dict(self))
        if self.id == '0':
            self = initial_save(self, share=share)
        else:
            save_mutable_fields(self, *args, **kwargs)

    def boot(self):
        chain, self, secondChain = find_or_create_chain_from_object(self)
        self.save()
        chain.add_item_to_queue(self)
        secondChain.add_item_to_queue(self)

    def delete(self):
        pass


class Keyphrase(models.Model):
    object_type = "Keyphrase"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    # added = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    key = models.CharField(max_length=1000, default="", blank=True, null=True)
    pointer_array = ArrayField(models.JSONField(default=dict, blank=True, null=True), size=10000, null=True, blank=True, default=list)
    last_occured = models.DateTimeField(auto_now=False, auto_now_add=False, blank=False, null=True)
    first_occured = models.DateTimeField(auto_now=False, auto_now_add=False, blank=False, null=True)
    # numberOfOccurences = models.IntegerField(default=0, blank=True, null=True)

    class Meta:
        ordering = ['-last_occured']
    
    def __str__(self):
        return 'KEYPHRASE:(%s)' %(self.key)
    
    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Keyphrase', 'modelVersion': 1, 'id': '0', 'last_updated': None, 'key': '', 'pointer_array': [], 'last_occured': None, 'first_occured': None}
            # return {'object_type': 'Keyphrase', 'modelVersion': 1, 'id': '0', 'last_updated': None, 'key': '', 'pointer_array': [], 'last_occured': None, 'first_occured': None}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','key']
    
    def set_score(self, trend):
        # prnt('set_score')
        utc_tz = pytz.utc
        trend.total_occurences += 1
        start_date = '%s-%s-%s' %(trend.last_updated.year, trend.last_updated.month, trend.last_updated.day)
        day = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        day = utc_tz.localize(day)
        dayRange = datetime.datetime.strftime(day - datetime.timedelta(days=7), '%Y-%m-%d')
        sevenDays = datetime.datetime.strptime(dayRange, '%Y-%m-%d')
        sevenDays = utc_tz.localize(sevenDays)
        occurences = 0
        for i in self.pointer_array:
            if i['Chamber'] == trend.Chamber and i['Country'] == trend.Country_obj.id and string_to_dt(i['DateTime']) >= sevenDays and string_to_dt(i['DateTime']) <= self.last_occured:
                occurences += 1
        trend.recent_occurences = occurences
        settime = datetime.datetime(2022, 10, 23, 1, 0).replace(tzinfo=pytz.UTC)
        t = trend.last_updated - settime
        secs = t.seconds * (12 / 86400) # converts 24hrs in seconds to 12
        r = ((t.days * 12) + secs) # 24 hour bump == 12 recent_occurences over 7 days
        trend.trend_score = r + trend.recent_occurences
        trend.save()

    def set_trend(self, pos=-1):
        # prnt('set_trend')
        if self.key and not self.key.startswith('*') and self.key not in skipwords and len(self.key) >= 4:
            trend = KeyphraseTrend.objects.filter(Chamber=self.pointer_array[pos]['Chamber'], Country_obj__id=self.pointer_array[pos]['Country'], Region_obj__id=self.pointer_array[pos]['Region'], key__iexact=self.key[:300]).first()
            if trend:
                if self.pointer_array[pos] in trend.pointer_array:
                    return 
            else:
                trend = KeyphraseTrend(Chamber=self.pointer_array[pos]['Chamber'], Country_obj_id=self.pointer_array[pos]['Country'], Region_obj_id=self.pointer_array[pos]['Region'], key=self.key[:300])
            trend.last_updated = now_utc()
            if trend.pointer_array and len(trend.pointer_array) >= 10000:
                trend.pointer_array.pop(0)
            trend.pointer_array.append(self.pointer_array[pos])
            trend.save()
            self.set_score(trend)
        # prnt('done set trend')
        return

    def save(self, share=False, *args, **kwargs):
        # prnt('start save', self.locked_to_chain)
        if self.id == '0':
            self.modelVersion = self.latestModel
            self.id = hash_obj_id(self)
        super(Keyphrase, self).save(*args, **kwargs)
    
    def delete(self):
        for k in KeyphraseTrend.objects.filter(key=self.key):
            k.delete()
        super(Keyphrase, self).delete()

class KeyphraseTrend(models.Model):
    object_type = "KeyphraseTrend"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    # added = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    Chamber = models.CharField(max_length=20, default=None, blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    pointer_array = ArrayField(models.JSONField(default=dict, blank=True, null=True), size=10000, null=True, blank=True, default=list)
    key = models.CharField(max_length=300, default="", blank=True, null=True)
    total_occurences = models.IntegerField(default=0, blank=True, null=True)
    recent_occurences = models.IntegerField(default=0, blank=True, null=True)
    trend_score = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['-trend_score', 'recent_occurences', 'total_occurences']
    
    def __str__(self):
        return 'KEYPHRASETREND:(%s/%s)' %(self.Chamber, self.key)

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'KeyphraseTrend', 'modelVersion': 1, 'id': '0', 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'last_updated': None, 'pointer_array': [], 'key': '', 'total_occurences': 0, 'recent_occurences': 0, 'trend_score': 0.0}
            # return {'object_type': 'KeyphraseTrend', 'modelVersion': 1, 'id': '0', 'created': None, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'last_updated': None, 'pointer_array': [], 'key': '', 'total_occurences': 0, 'recent_occurences': 0, 'trend_score': 0.0}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','key','Chamber','Region_obj','Country_obj']
    
    def get_absolute_url(self):
        return "%s/topic/%s" %(self.Country_obj.Name, self.key)

    def save(self, share=False, *args, **kwargs):
        if self.id == '0':
            self.modelVersion = self.latestModel
            self.id = hash_obj_id(self)
        super(KeyphraseTrend, self).save(*args, **kwargs)
    
    # def delete(self):
    #     # for k in Keyphrase.objects.filter(KeyphraseTrend_obj=self):
    #     #     k.delete()
    #     superDelete(self)


class Spren(models.Model):
    object_type = "Spren"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    blockchainType = models.CharField(max_length=50, default="", blank=True)
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    added = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    func = models.CharField(max_length=50, default="", blank=True)
    creatorNodeId = models.CharField(max_length=50, default="", blank=True)
    validatorNodeId = models.CharField(max_length=50, default="", blank=True)
    Validator_obj = models.ForeignKey('blockchain.Validator', blank=True, null=True, on_delete=models.SET_NULL)
    blockchainId = models.CharField(max_length=50, default="", blank=True)
    Block_obj = models.ForeignKey('blockchain.Block', blank=True, null=True, on_delete=models.SET_NULL)
    publicKey = models.CharField(max_length=200, default="", blank=True)
    signature = models.CharField(max_length=200, default="", blank=True)
    validation_error = models.BooleanField(default=False, blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    
    pointerId = models.CharField(max_length=50, default="", blank=True)
    topic = models.CharField(max_length=500, default="", blank=True, null=True)
    type = models.CharField(max_length=250, default="", blank=True, null=True)
    content = models.CharField(max_length=3000, default="", blank=True, null=True)
    version = models.CharField(max_length=10, default="", blank=True, null=True)
    data = models.JSONField(blank=True, null=True)

    # refrenceType = models.CharField(max_length=50, default="", blank=True)
    # referenceId = models.CharField(max_length=50, default="", blank=True)
    
    
    def __str__(self):
        return 'SPREN:%s, %s' %(self.type, self.DateTime)

    class Meta:
        ordering = ["-DateTime"]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            # return {'object_type': 'Spren', 'blockchainType': '', 'modelVersion': 1, 'id': '0', 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Region_obj': None, 'Country_obj': None, 'DateTime': None, 'pointerId': '', 'topic': '', 'type': '', 'content': '', 'version': '', 'data': None}
            return {'object_type': 'Spren', 'blockchainType': '', 'modelVersion': 1, 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Region_obj': None, 'Country_obj': None, 'DateTime': None, 'pointerId': '', 'topic': '', 'type': '', 'content': '', 'version': '', 'data': None}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','Meeting_obj','Statement_obj','Bill_obj','content','type','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash']

    def get_post(self):
        p = Post.all_objects.filter(Spren_obj=self).first()
        return p

    def save(self, share=False, *args, **kwargs):
        prnt('start save spren')
        if self.id == '0':
            if self.Statement_obj:
                self.blockchainType = self.Statement_obj.blockchainType
                self.Chamber = self.Statement_obj.Chamber
                self.Region_obj = self.Statement_obj.Region_obj
                self.Country_obj = self.Statement_obj.Country_obj
                self.Government_obj = self.Statement_obj.Government_obj
            elif self.Meeting_obj:
                self.blockchainType = self.Meeting_obj.blockchainType
                self.Chamber = self.Meeting_obj.Chamber
                self.Region_obj = self.Meeting_obj.Region_obj
                self.Country_obj = self.Meeting_obj.Country_obj
                self.Government_obj = self.Meeting_obj.Government_obj
            elif self.Bill_obj:
                self.blockchainType = self.Bill_obj.blockchainType
                self.Chamber = self.Bill_obj.Chamber
                self.Region_obj = self.Bill_obj.Region_obj
                self.Country_obj = self.Bill_obj.Country_obj
                self.Government_obj = self.Bill_obj.Government_obj
            # add blockchainType according to pointer
            self = initial_save(self, share=share)
        elif not is_locked(self):
            super(Spren, self).save(*args, **kwargs)


    def delete(self):
        if not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        if not self.DateTime:
            if self.Statement_obj:
                self.DateTime = self.Statement_obj.DateTime
            elif self.Meeting_obj:
                self.DateTime = self.Meeting_obj.DateTime
            elif self.Bill_obj:
                self.DateTime = self.Bill_obj.DateTime
            else:
                self.DateTime = self.created
        self.save()
        p = new_post(self)
        # p.set_score()
        prnt('done create sprenPost')
        p.save()
        prnt('saved spren post')
        return p

class GenericModel(BaseModel):
    object_type = "GenericModel"
    blockchainType = 'Region'
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    pointerId = models.CharField(max_length=50, db_index=True, default=None, null=True, blank=True)
    distinction = models.CharField(max_length=50, default=None, null=True, blank=True) # allows for unique id if DateTime, pointerId and type are repeated
    Data = models.JSONField(default=dict, blank=True, null=True)
    type = models.CharField(max_length=90, default=None, blank=True, null=True)

    Chamber = models.CharField(max_length=20, default=None, blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', blank=True, null=True, on_delete=models.CASCADE)
    Government_obj = models.ForeignKey('legis.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    
    class Meta:
        ordering = ['-DateTime']

    def __str__(self):
        return f'GenericModel:({self.type})-id:{self.id}-pointer:{self.pointerId}'

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'GenericModel', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'pointerId': None, 'distinction': None, 'Data': {}, 'type': None}
            # return {'object_type': 'GenericModel', 'blockchainType': 'Region', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 2, 'pointerId': None, 'distinction': None, 'Data': {}, 'type': None}
        # elif int(version) >= 1:
        #     return {'object_type': 'GenericModel', 'blockchainType': 'Region', 'id': '0', 'created': None, 'added': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'Chamber': None, 'Region_obj': None, 'Country_obj': None, 'Government_obj': None, 'DateTime': None, 'modelVersion': 1, 'pointerId': None, 'Data': {}, 'type': None}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','pointerId','type','DateTime','distinction','Government_obj','Chamber','Region_obj','Country_obj']
        # elif int(version) >= 1:
        #     return ['object_type','pointerId','type','DateTime','Government_obj','Chamber','Region_obj','Country_obj']
    
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','pointerId']

    def updateShare(self, obj):
        if 'shareData' not in self.Data:
            self.Data['shareData'] = []
        self.Data['shareData'].append(obj.id)
        self.save()

    def save(self, share=False, *args, **kwargs):
        # from blockchain.models import convert_to_dict
        # prntDebugn('GEN SAVE', convert_to_dict(self))
        if self.id == '0':
            self.distinction = str(self.distinction)[:50]
            self = initial_save(self)
        elif not is_locked(self):
            self.distinction = str(self.distinction)[:50]
            from utils.models import compensate_save
            compensate_save(self, GenericModel, *args, **kwargs)
            # super(GenericModel, self).save(*args, **kwargs)

    def delete(self, force_delete=False):
        if force_delete or not is_locked(self):
            superDelete(self)

    def boot(self, share=False):
        p = new_post(self)
        if self.DateTime:
            p.DateTime = self.DateTime
        p.save(share=share)
        return p


class UpdateQuerySet(models.QuerySet):
    def with_deferred_text(self):
        return self.defer('extra')

    def include_text(self):
        return self

class UpdateManager(models.Manager):
    def get_queryset(self):
        return UpdateQuerySet(self.model, using=self._db).with_deferred_text()

class Update(BaseModel):
    object_type = "Update"
    latestModel = 1
    modelVersion = models.IntegerField(default=latestModel)
    blockchainType = models.CharField(max_length=50, default="", blank=True)
    validated = models.BooleanField(default=False, null=True, blank=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', blank=True, null=True, on_delete=models.CASCADE)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    pointerId = models.CharField(max_length=50, db_index=True, default="", blank=True)
    pointerKey = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, default=None)
    Pointer_obj = GenericForeignKey('pointerKey', 'pointerId')
    # distinction = models.CharField(max_length=50, default=None, null=True, blank=True) # consider this in get_hash_to_id instead of added, will require being set in scrapers
    data = models.JSONField(default=dict, blank=True, null=True)
    extra = models.JSONField(blank=True, null=True)
    objects = UpdateManager()

    def __str__(self):
        return 'UPDATE:%s-%s' %(get_pointer_type(self.pointerId),self.id)

    class Meta:
        ordering = ["-created","-DateTime","pointerId"]
        indexes = [
            GinIndex(fields=['data'], name='gin_index_jsonb_path_ops', opclasses=['jsonb_path_ops']),
        ]

    def get_version_fields(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return {'object_type': 'Update', 'blockchainType': '', 'id': '0', 'created': None, 'func': '', 'creatorNodeId': '', 'validatorNodeId': '', 'Validator_obj': None, 'blockchainId': '', 'Block_obj': None, 'publicKey': '', 'signature': '', 'validation_error': False, 'modelVersion': 1, 'validated': False, 'Region_obj': None, 'DateTime': None, 'pointerId': '', 'pointerKey': None, 'data': {}, 'extra': None}

    def get_hash_to_id(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['object_type','pointerId','created','Region_obj']
        
    def commit_data(self, version=None):
        if not version:
            version = self.modelVersion
        if int(version) >= 1:
            return ['hash','pointerId','created']

    skipFields = ['id', 'func', 'created', 'added', 'last_updated', 'modelVersion', 'publicKey', 'signature', 'updated_on_node', 'creatorNodeId', 'validatorNodeId', 'Validator_obj', 'Block_obj', 'Pointer_obj', 'validated']

    def create_next_version(self, obj=None):
        from blockchain.models import convert_to_dict, round_time
        prnt('create_next_version', obj)
        if not self.created:
            self.created=round_time(dt=now_utc(), dir='down', amount='hour') # obj can be updated once per hour, once validated is no longer updateable until next hour
        if obj:
            current = Update.objects.filter(pointerId=obj.id, validated=True).first()
            if current and current.created < self.created:
                prnt('current 1',current.id)
                fields = current._meta.fields
                for f in fields:
                    if f.name not in self.skipFields:
                        attr = getattr(current, f.name)
                        setattr(self, f.name, attr)
            elif current:
                prnt('current 2',current.id)
                return current
        else:
            current = Update.objects.filter(pointerId=self.pointerId, validated=True).first()
            if current and current.created < self.created:
                prnt('current 3',current.id)
                fields = current._meta.fields
                for f in fields:
                    if f.name not in self.skipFields:
                        attr = getattr(current, f.name)
                        setattr(self, f.name, attr)
            elif current:
                prnt('current 4',current.id)
                return current
        prnt('no current update')
        return self



    
    def get_pointer(self):
        return self.Pointer_obj
        
    def verify_is_valid(self, use_assigned_val=False):
        from blockchain.models import Validator, sigData_to_hash, get_scraping_order
        from utils.locked import verify_obj_to_data
        if use_assigned_val:
            v = self.Validator_obj
        else:
            v = Validator.objects.filter(data__has_key=self.id, is_valid=True).order_by('-created').first()
        if v:
            if self.id in v.data and v.data[self.id] == sigData_to_hash(self):
                if verify_obj_to_data(v, v):
                    validator_node_id = get_scraping_order(dt=self.added, chainId=self.blockchainId, func_name=self.func, validator_only=True)
                    if self.validatorNodeId == validator_node_id:
                        return True
        return False

    def save_if_new(self, func=None, share=False):
        prnt('save update if new')
        if not self.data:
            return None, False

        if self.id == '0':
            match = Update.objects.filter(pointerId=self.pointerId, DateTime=self.DateTime, data=self.data, extra=self.extra).first()
        else:
            match = Update.objects.exclude(id=self.id).filter(pointerId=self.pointerId, DateTime=self.DateTime, data=self.data, extra=self.extra).first()
            # query_kwargs = {field: getattr(self, field) for field in self.get_hash_to_id() if field != 'object_type'}
            # match = Update.objects.filter(**query_kwargs).first()
        if match:
            return self, False
            # prnt('has match')
            # if not match.Block_obj:
            #     if match.DateTime != self.DateTime or match.data != self.data or match.extra != self.extra:
            #         match.DateTime = self.DateTime
            #         match.data = self.data
            #         match.extra = self.extra
            #         match.validated = False
            #         match.Validator_obj = None
            #         match.signature = ''
            #         match.publicKey = ''
            if not is_locked(match) and save_mutable_fields(match):
                prnt('is saveable')
                return match, True
            else:
                prnt('not new')
                return match, False
        else:
            prnt('true2')
            self.save()
            return self, True

    def validate(self, validator=None, save_self=True, verify_validator=True, node_block_data={}):
        prnt('---validate update', self.id)
        from utils.locked import validate_obj
        return validate_obj(obj=self, pointer=None, validator=validator, save_obj=save_self, update_pointer=False, verify_validator=verify_validator, add_to_queue=False, node_block_data=node_block_data)


        # from blockchain.models import Validator, sigData_to_hash, get_scraping_order, logEvent, convert_to_dict, max_validation_window, convert_to_datetime
        # from accounts.models import verify_obj_to_data
        # proceed = False
        # validator_node_id = None
        # e = 0
        # if not self.validated and self.id != '0':
        #     e = 1
        #     if validator:
        #         proceed = True
        #     else:
        #         e = 2
        #         if self.Validator_obj:
        #             e = 21
        #             validator = self.Validator_obj
        #             proceed = True
        #         else:
        #             e = 22
        #             # validator = Validator.objects.filter(data__has_key=self.id, is_valid=True).order_by('-created').first()
        #             validators = Validator.objects.filter(data__contains={self.id: sigData_to_hash(self)}, is_valid=True).order_by('-created')
        #             for validator in validators:
        #                 if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
        #                     validator_node_id = validator.CreatorNode_obj.id
        #                     proceed = True
        #                     break
        #                 else:
        #                     validator_node_id = get_scraping_order(dt=self.added, chainId=self.blockchainId, func_name=self.func, validator_only=True, node_block_data=node_block_data)
        #                     if self.validatorNodeId == validator_node_id:
        #                         proceed = True
        #                         break
        #     # validator shuold be crated within x hours of pointer.added
        #     if proceed and validator and validator.is_valid and validator.signature and self.signature:
        #         # if has_field(pointer, 'created'):
        #         if convert_to_datetime(validator.created) > convert_to_datetime(self.created) + datetime.timedelta(days=max_validation_window) or convert_to_datetime(validator.created) < convert_to_datetime(self.created):
        #             e = 23
        #             prnt('validator created outside of window')
        #             prnt('failed to validated', e, validator)
        #             return False
        #         # e = 3
        #         if not verify_validator or verify_obj_to_data(validator, validator):
        #             e = 31
        #             if self.id in validator.data:
        #                 e = 4
        #                 hash = validator.data[self.id]
        #                 if hash == sigData_to_hash(self):
        #                     e = 5
        #                     if not validator_node_id:
        #                         if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
        #                             e = 6
        #                             validator_node_id = validator.CreatorNode_obj.id
        #                             e = '333a' + validator_node_id
        #                         else:
        #                             e = 7
        #                             validator_node_id = get_scraping_order(dt=convert_to_datetime(self.created), chainId=self.blockchainId, func_name=self.func, validator_only=True, node_block_data=node_block_data)
        #                             e = '333b' + validator_node_id
        #                     if self.validatorNodeId == validator_node_id:
        #                         e = 8
        #                         if save_self:
        #                             if self.Validator_obj != validator:
        #                                 self.Validator_obj = validator
        #                             self.validated = True
        #                             super(Update, self).save()
        #                             blockchain, item, secondChain = find_or_create_chain_from_object(self.Pointer_obj)
        #                             if blockchain:
        #                                 blockchain.add_item_to_queue(self)
        #                             else:
        #                                 logEvent('no blockchain', code='9763', func='update.validate()', extra={'self.id':self.id,'dict':str(convert_to_dict(self.Pointer_obj))[:500]})
        #                         synced = self.sync_with_post()
        #                         e = 9

        #                         # dataPacket = get_latest_dataPacket(self.blockchainType)
        #                         # prnt('dataPacket',dataPacket)
        #                         # if dataPacket:
        #                         #     dataPacket.add_item_to_data(self)
        #                         #     dataPacket.add_item_to_data(validator)
        #                         #     prnt('shared')
        #                         prntDebug('validated')
        #                         # logEvent('update validated', code='753', func='posts_update_validate', extra={'pointerId':self.pointerId,'synced':synced})
        #                         return True
        #                     else:
        #                         prnt('valId no match')
        #                 else:
        #                     prnt('hash no match')
        #     prnt('failed to validated', e, validator)
        # # logEvent('failed to validate update', code='08751', func='posts_update_validate', extra={'err':str(e),'pointerId':self.pointerId})
        # return False
            
    def sync_with_post(self, post=None, pointer=None, do_save=True):
        prnt('---sync',self)
        if not post:
            post = Post.all_objects.filter(pointerId=self.pointerId).first()
        if not post:
            pointer = self.Pointer_obj
            if not pointer:
                if self.pointerId and not self.pointerKey:
                    pointer = get_dynamic_model(self.pointerId, id=self.pointerId)
                    if pointer:
                        self.pointerKey = ContentType.objects.get_for_model(pointer)
                        self.save()
                if not pointer:
                    from blockchain.models import request_items, logMissing
                    fetch_result = request_items(requested_items=[self.pointerId], nodes=[self.creatorNodeId], return_updated_objs=True, downstream_worker=False)
                    if fetch_result:
                        if isinstance(fetch_result, list):
                            try:
                                pointer = [i for i in fetch_result if i.id == self.pointerId]
                            except Exception as e:
                                prnt('update pointer fail 325', str(e))
                if not pointer:
                    logMissing(self.pointerId, reg=self.Region_obj.id, context={'update':self.id})
            if pointer and has_field(pointer, 'boot'):
                post = pointer.boot()
        if post:
            if post.Update_obj != self:
                if not post.Update_obj or self.created > post.Update_obj.created:
                    prntDebug('syncing...')
                    if post.Update_obj:
                        # add operator option to preserve/remove historical data
                        # post.Update_obj.log_deletion(data={'replaced_by':self.id})
                        pass
                    if 'Chamber' in self.data and self.data['Chamber']:
                        post.filters['Chamber'] = self.data['Chamber']
                    if 'gov_level' in self.data and self.data['gov_level']:
                        post.filters['gov_level'] = self.data['gov_level']
                    if 'has_text' in self.data and self.data['has_text']:
                        post.filters['has_text'] = self.data['has_text']
                    if 'Position' in self.data and self.data['Position']:
                        post.filters['Position'] = self.data['Position']
                    if 'LastName' in self.data and self.data['LastName']:
                        post.filters['LastName'] = self.data['LastName']
                    if 'FullName' in self.data and self.data['FullName'] not in post.keyword_array:
                        post.keyword_array.append(self.data['FullName'])
                    post.Update_obj = self
                    if self.DateTime:
                        if not post.DateTime or self.DateTime > post.DateTime:
                            post.DateTime = self.DateTime
                    if do_save:
                        post.save()
                    if not pointer:
                        pointer = self.Pointer_obj
                    if has_method(pointer, 'new_update'):
                        try:
                            pointer.new_update(self)
                        except Exception as e:
                            prnt('meeting update fail:',str(e))
                    prnt('synced')
                    return True if do_save else post
        return False if do_save else post

    def save(self, share=False, *args, **kwargs):
        # from blockchain.models import convert_to_dict
        prnt('--saveupdate',self.id)
        if self.id == '0':
            if self.pointerId and not self.pointerKey:
                pointer = get_dynamic_model(self.pointerId, id=self.pointerId)
                self.pointerKey = ContentType.objects.get_for_model(pointer)
            elif self.pointerKey:
                pointer = self.Pointer_obj
                self.pointerId = pointer.id
            if has_field(pointer, 'DateTime') and pointer.DateTime:
                self.DateTime = pointer.DateTime
            elif has_field(pointer, 'last_updated') and pointer.last_updated:
                self.DateTime = pointer.last_updated
                
            try:
                self.Region_obj = pointer.Region_obj
            except:
                pass
            self.blockchainType = pointer.blockchainType
            self = initial_save(self)
        elif not is_locked(self) and save_mutable_fields(self, *args, **kwargs):
            # from blockchain.models import get_signing_data
            prnt('done save u')
    
    def log_deletion(self, data={}):
        if self.validated:
            from datetime import timezone
            from blockchain.models import EventLog, Blockchain
            self_node = get_self_node()
            now = now_utc()
            start_of_month = round_time(dt=now, dir='down', amount='month')
            delLog = EventLog.objects.filter(type='Deletion_Log', Node_obj=self_node, Region_obj=self.Region_obj, created__gte=start_of_month).first()
            if not delLog:
                delLog = EventLog(type='Deletion_Log', Node_obj=self_node, Region_obj=self.Region_obj, created__gte=start_of_month)
            if self.id not in delLog.data:
                jsonData = {'dt':now}
                for key in data:
                    jsonData[key] = data[key]
                delLog.data[self.id] = jsonData
                delLog = sign_obj(delLog)
                chain = Blockchain.objects.filter(genesisId=self.Region_obj.id).first()
                datapacket = get_latest_dataPacket(chain.id)
                if datapacket:
                    datapacket.add_item_to_share(delLog)
        self.delete()


class ValidPostQuerySet(models.QuerySet):
    def default_filter(self):
        return self.filter(validated=True)

class ValidPostManager(models.Manager):
    def get_queryset(self):
        return ValidPostQuerySet(self.model, using=self._db).default_filter()

    def all(self, *args, **kwargs):
        return self.get_queryset()

    def include_invalid(self):
        return super().get_queryset()

class Post(models.Model):
    object_type = "Post"
    id = models.CharField(max_length=50, default="0", primary_key=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    updated_on_node = models.DateTimeField(auto_now=True, auto_now_add=False, blank=True, null=True)
    validated = models.BooleanField(default=False, null=True, blank=True) # is validated by validator nodes
    blockId = models.CharField(max_length=50, default=None, blank=True, null=True)
    Chamber = models.CharField(max_length=20, default=None, db_index=True, blank=True, null=True)
    Region_obj = models.ForeignKey('posts.Region', related_name='%(class)s_region_obj', db_index=True, blank=True, null=True, on_delete=models.CASCADE)
    Country_obj = models.ForeignKey('posts.Region', related_name='%(class)s_country_obj', db_index=True, blank=True, null=True, on_delete=models.CASCADE)
    Government_obj = models.ForeignKey('legis.Government', related_name='%(class)s_government_obj', blank=True, null=True, on_delete=models.SET_NULL)
    DateTime = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    gov_level = models.CharField(max_length=250, default="", blank=True, null=True)
    filters = models.JSONField(default=dict, blank=True, null=True)

    pointerId = models.CharField(max_length=50, default="", unique=True)
    pointerType = models.CharField(max_length=50, default="", db_index=True)
    Update_obj = models.ForeignKey('posts.Update', blank=True, null=True, on_delete=models.SET_NULL)
    Spren_obj = models.ForeignKey(Spren, blank=True, null=True, on_delete=models.CASCADE)
    Agenda_obj = models.ForeignKey('legis.Agenda', blank=True, null=True, on_delete=models.CASCADE)
    Bill_obj = models.ForeignKey('legis.Bill', blank=True, null=True, on_delete=models.CASCADE)
    GenericModel_obj = models.ForeignKey(GenericModel, blank=True, null=True, on_delete=models.CASCADE)
    Meeting_obj = models.ForeignKey('legis.Meeting', related_name='%(class)s_meeting_obj', blank=True, null=True, on_delete=models.CASCADE)
    Statement_obj = models.ForeignKey('legis.Statement', blank=True, null=True, on_delete=models.CASCADE)
    Committee_obj = models.ForeignKey('legis.Committee', related_name='%(class)s_committee_obj', blank=True, null=True, on_delete=models.CASCADE)
    Motion_obj = models.ForeignKey('legis.Motion', blank=True, null=True, on_delete=models.CASCADE)
    Vote_obj = models.ForeignKey('legis.Vote', blank=True, null=True, on_delete=models.CASCADE)
    Election_obj = models.ForeignKey('legis.Election', blank=True, null=True, on_delete=models.CASCADE)
    Person_obj = models.ForeignKey('legis.Person', blank=True, null=True, on_delete=models.CASCADE)
    Party_obj = models.ForeignKey('legis.Party', blank=True, null=True, on_delete=models.CASCADE)
    District_obj = models.ForeignKey('legis.District', blank=True, null=True, on_delete=models.CASCADE)

    rank = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    verifiedRank = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    randomizer = models.IntegerField(blank=True, null=True) 
    keyword_array = ArrayField(models.CharField(max_length=200, default='{default}'), size=20, blank=True, null=True)
    total_votes = models.IntegerField(blank=True, null=True) 
    total_yeas = models.IntegerField(blank=True, null=True) 
    total_nays = models.IntegerField(blank=True, null=True) 
    total_verified_votes = models.IntegerField(blank=True, null=True) 
    total_verified_yeas = models.IntegerField(blank=True, null=True) 
    total_verified_nays = models.IntegerField(blank=True, null=True) 
    total_comments = models.IntegerField(blank=True, null=True) 
    total_saves = models.IntegerField(blank=True, null=True) 
    total_shares = models.IntegerField(blank=True, null=True) 

    notes = models.JSONField(default=dict, blank=True, null=True)

    all_objects = models.Manager()
    objects = ValidPostManager()

    def __str__(self):
        return 'POST-%s/%s-%s' %(self.pointerId[:10], self.created, self.id[:10])     
    
    class Meta:
        ordering = ['-created','-DateTime','validated']
        indexes = [
            # GinIndex(fields=['filters']),
            GinIndex(fields=["filters"], name="gin_index_filters", opclasses=["jsonb_ops"]),
            GinIndex(fields=['keyword_array'], name='keyword_array_overlap_index'),
        ]

    def get_hash_to_id(self, version=None):
        if not version:
            version = 1
        if int(version) >= 1:
            return ['object_type','pointerId']
    
    def get_absolute_url(self):
        if self.pointerType == 'Person':
            if not self.Update_obj:
                if self.Person_obj.GovIden:
                    return f"/profile/{self.Person_obj.GovIden}"
                else:
                    return f"/profile/{self.Person_obj.id}"
            if self.Person_obj.GovIden:
                return "/profile/%s/%s_%s/%s" % (self.Region_obj.Name, self.Update_obj.data['FirstName'].replace(' ', '_'), self.Update_obj.data['LastName'].replace(' ', '_'), self.Person_obj.GovIden)
            else:
                return "/profile/%s/%s_%s/%s" % (self.Region_obj.Name, self.Update_obj.data['FirstName'].replace(' ', '_'), self.Update_obj.data['LastName'].replace(' ', '_'), self.Person_obj.id)
        
    def get_title(self):
        if self.Agenda_obj:
            return '%s agenda %s' %(self.Agenda_obj.Chamber, datetime.datetime.strftime(self.Agenda_obj.DateTime, '%d/%m/%Y'))
        elif self.Bill_obj and self.Bill_obj.Title:
            return 'Bill %s %s' %(self.Bill_obj.NumberCode, self.Bill_obj.Title)
        elif self.Bill_obj and self.Bill_obj.ShortTitle:
            return 'Bill %s %s' %(self.Bill_obj.NumberCode, self.Bill_obj.ShortTitle)
        elif self.Meeting_obj:
            return '%s %s %s' %(self.Meeting_obj.Chamber, self.Meeting_obj.meeting_type, self.Meeting_obj.DateTime)
        elif self.Statement_obj:
            if self.Statement_obj.Person_obj:
                return '%s Stated %s' %(self.Statement_obj.Person_obj.FullName, self.Statement_obj.DateTime)
            else:
                return '%s Stated %s' %(self.Statement_obj.PersonName, self.Statement_obj.DateTime)
        # elif self.committee:
        #     return '%s Debated %s' %(self.hansardItem.person_name, self.hansardItem.Item_date_time)
        # elif self.CommitteeMeeting_obj:
        #     return 'Committee %s %s' %(self.CommitteeMeeting_obj.Code, self.CommitteeMeeting_obj.DateTimeStart)
        # elif self.CommitteeItem:
        #     return '%s In Committee %s' %(self.CommitteeItem.Person.FullName, self.CommitteeItem.ItemDateTime)
        elif self.Motion_obj:
            return 'Bill %s Motion %s' %(self.Motion_obj.billCode, self.Motion_obj.DateTime)
        else:
            return '%s' %(self.pointerType)
        # elif self.vote:
        #     return self.vote.get_absolute_url()
        # elif self.person:
        #     return self.person.get_absolute_url()
        # elif self.party:
        #     return self.party.get_absolute_url()
        # elif self.district:
        #     return self.district.get_absolute_url()

    def tally_votes(self):
        from accounts.models import UserAction
        actions = UserAction.objects.filter(pointerId=self.pointerId)
        self.total_votes = actions.count()
        self.total_yeas = len([r for r in actions if r.isYea])
        self.total_nays = len([r for r in actions if r.isNay])
        self.total_verified_votes = len([r for r in actions if r.User_obj.isVerified])
        self.total_verified_yeas = len([r for r in actions if r.isYea and r.User_obj.isVerified])
        self.total_verified_nays = len([r for r in actions if r.isNay and r.User_obj.isVerified])
        # self.save()
        return self

    def validate(self, validator=None, save_self=True, update_pointer=True, verify_validator=True, node_block_data={}):
        prnt('---validate _post', self.id)
        from utils.locked import validate_obj
        return validate_obj(obj=self, pointer=None, validator=validator, save_obj=save_self, update_pointer=update_pointer, verify_validator=verify_validator, add_to_queue=False, node_block_data=node_block_data)

        pointer = None
        proceed = False
        validator_node_id = None
        err = 0
        if not self.validated and self.id != '0':
            from blockchain.models import Validator, sigData_to_hash, get_scraping_order, max_validation_window, convert_to_datetime
            from accounts.models import verify_obj_to_data
            # logError('validate post', code='5784', func='posts_validate', extra={'self_dict':convert_to_dict(self)})
            pointer, self = self.get_pointer(return_self=True, do_save=False)
            if pointer and validator:
                proceed = True
            elif pointer:
                if pointer.Validator_obj:
                    validator = pointer.Validator_obj
                    proceed = True
                else:
                    
                    validators = Validator.objects.filter(data__contains={pointer.id: sigData_to_hash(pointer)}, is_valid=True).order_by('-created')
                    for validator in validators:
                        if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                            validator_node_id = validator.CreatorNode_obj.id
                            proceed = True
                            break
                        else:
                            validator_node_id = get_scraping_order(dt=convert_to_datetime(pointer.created), chainId=pointer.blockchainId, func_name=pointer.func, validator_only=True, node_block_data=node_block_data)
                            if pointer.validatorNodeId == validator_node_id:
                                proceed = True
                                break
            err = 1
            # validator shuold be crated within x hours of pointer.added
            if proceed and pointer and validator and validator.is_valid and validator.signature and pointer.signature:
                if has_field(pointer, 'created'):
                    if convert_to_datetime(validator.created) > convert_to_datetime(pointer.created) + datetime.timedelta(days=max_validation_window) or convert_to_datetime(validator.created) < convert_to_datetime(pointer.created):
                        err = 11
                        prnt('validator created outside of window')
                        self.notes[now_utc().isoformat()] = f'validator created outside of window:{err}.'
                        prnt('failed to validaed post',err,pointer)
                        self.save()
                        return False
                err = 2
                if not verify_validator or verify_obj_to_data(validator, validator):
                    err = 21
                    if pointer.id in validator.data:
                        err = 3
                        hash = validator.data[pointer.id]
                        if hash == sigData_to_hash(pointer):
                            # err = 4
                            # if not isinstance(validator.created_dt, datetime.datetime):
                            #     v_created = string_to_dt(validator.created_dt)
                            # else:
                            #     v_created = validator.created_dt
                            # if v_created >= pointer.added and v_created <= (pointer.added + datetime.timedelta(hours=12)):
                            err = 5
                            if not validator_node_id:
                                if validator.func.lower() == 'super' and validator.CreatorNode_obj.User_obj.assess_super_status(dt=convert_to_datetime(validator.created)):
                                    validator_node_id = validator.CreatorNode_obj.id
                                    err = '444a' + validator_node_id
                                else:
                                    validator_node_id = get_scraping_order(dt=convert_to_datetime(pointer.created), chainId=pointer.blockchainId, func_name=pointer.func, validator_only=True, node_block_data=node_block_data)
                                    err = '444b' + validator_node_id
                            if pointer.validatorNodeId == validator_node_id:
                                err = 6
                                if save_self:
                                    self.validated = True
                                    self, updated_fields = update_post(obj=pointer, p=self, save_p=False)
                                    self.save()
                                if update_pointer and pointer.Validator_obj != validator:
                                    pointer.Validator_obj = validator
                                    pointer.save()
                                    if has_field(pointer, 'blockchainId'):
                                        blockchain, item, secondChain = find_or_create_chain_from_object(self.get_pointer())
                                        blockchain.add_item_to_queue(pointer)
                                if has_method(pointer, 'upon_validation'):
                                    pointer.upon_validation()
                                prntDebug(f'post validated - id:{self.id}, pointerId:{self.pointerId}, save_self:{save_self}, node_block_data:{node_block_data}')
                                # logEvent('post validated', code='64356', func='posts_validate', extra={'id':self.id,'pointerId':self.pointerId,'save_self':save_self,'node_block_data':node_block_data})
                                return True
                            else:
                                prnt('valId incorrect',pointer)
                            # else:
                            #     print('creatd_dt not appropriate. v_created:',v_created,'pointer.added:',pointer.added)
                        else:
                            prnt('hash no match',pointer)
                            self.notes[now_utc().isoformat()] = f'hash no match err:{err}. {pointer}'
                    else:
                        prnt('point.id not in validator')
                        self.notes[now_utc().isoformat()] = f'point.id not in validator err:{err}. {validator.id}'
                else:
                    prnt('val not verified')
                    self.notes[now_utc().isoformat()] = f'val not verified err:{err}. {validator.id}'
            else:
                prnt('validator not valid')
                self.notes[now_utc().isoformat()] = f'no val or val not valid err:{err}.'
            prnt('failed to validaed post',err,pointer)
            self.save()

        #     if pointer and validator:
        #         logEvent('failed to validate post', code='8642', func='posts_validate', extra={'err':str(err),'p.id':pointer.id,'val_id':validator.id,'pointer':pointer,'pointer_dict':convert_to_dict(pointer),'self_dict':convert_to_dict(self)})
        #     else:
        #         logEvent('failed to validate post', code='86426', func='posts_validate', extra={'err':str(err),'pointer':pointer,'validator':validator,'self_dict':convert_to_dict(self)})
        # else:
        #     logEvent('post already validated', code='743', func='posts_validate', extra={'self_dict':convert_to_dict(self)})

        return False

    def verify_is_valid(self, check_update=True, use_assigned_val=False):
        update_valid = None
        pointer_valid = False
        from blockchain.models import Validator, sigData_to_hash
        from utils.locked import verify_obj_to_data, get_node_assignment
        pointer = self.get_pointer()
        if use_assigned_val:
            v = pointer.Validator_obj
        else:
            v = Validator.objects.filter(data__has_key=self.pointerId, is_valid=True).order_by('-created').first()
        if v:
            if self.pointerId in v.data and v.data[self.pointerId] == sigData_to_hash(pointer):
                if verify_obj_to_data(v, v):
                    creator_nodes, validator_nodes = get_node_assignment(dt=pointer.added, func=pointer.func, chainId=pointer.blockchainId)
                    # validator_nodes = get_scraping_order(dt=pointer.added, chainId=pointer.blockchainId, func_name=func_name, validator_only=True)
                    if pointer.validatorNodeId in validator_nodes:
                        pointer_valid = True

        if check_update and self.Update_obj:
            update_valid = False
            if self.Update_obj.verify_is_valid():
                update_valid = True
            # v = Validator.objects.filter(data__has_key=self.Update_obj.id, is_valid=True).first()
            # if v:
            #     if self.Update_obj.id in v.data and v.data[self.Update_obj.id] == sigData_to_hash(self.Update_obj):
            #         if verify_obj_to_data(v, v):
        if check_update:
            return pointer_valid, update_valid
        return pointer_valid

    def get_pointer(self, set_pointer=True, return_self=False, do_save=True):
        pointer = getattr(self, self.pointerType + '_obj')
        if not pointer and set_pointer:
            if return_self:
                pointer, self = self.set_pointer(return_self=return_self, do_save=do_save)
            else:
                pointer = self.set_pointer(return_self=return_self, do_save=do_save)
        if return_self:
            return pointer, self
        return pointer

    def set_pointer(self, do_save=True, return_self=False):
        pointer = get_dynamic_model(self.pointerType, id=self.pointerId)
        pointer_obj = self.pointerType + '_obj'
        setattr(self, pointer_obj, pointer)
        if do_save:
            super(Post, self).save()
        if return_self:
            return pointer, self
        return pointer

    def set_score(self, save_item=True):
        scoreMe(self, save_item=save_item)

    def save(self, share=False, *args, **kwargs):
        # prnt('save post', self.pointerId, self.id)
        pointer = None
        if self.id == '0':
            self.id = hash_obj_id(self)
            pointer, self = self.get_pointer(return_self=True, do_save=False)
            self.created = get_timeData(pointer)
            if has_field(pointer, 'Government_obj'):
                self.Government_obj = pointer.Government_obj
                if pointer.Government_obj:
                    self.filters['gov_level'] = pointer.Government_obj.gov_level
            if has_field(pointer, 'Chamber') and pointer.Chamber:
                self.filters['Chamber'] = pointer.Chamber
            if has_field(pointer, 'Country_obj'):
                self.Country_obj = pointer.Country_obj
            if has_field(pointer, 'Region_obj'):
                self.Region_obj = pointer.Region_obj
            if pointer.object_type == 'Bill':
                if pointer.NumberCode:
                    self.filters['NumberCode'] = pointer.NumberCode
                if pointer.amendedNumberCode:
                    self.filters['amendedNumberCode'] = pointer.amendedNumberCode
                if pointer.Title:
                    self.filters['Title'] = pointer.Title
                if pointer.ShortTitle:
                    self.filters['ShortTitle'] = pointer.ShortTitle
                if pointer.BillDocumentTypeName:
                    self.filters['BillType'] = pointer.BillDocumentTypeName
                
        if not self.DateTime:
            if not pointer:
                pointer, self = self.get_pointer(return_self=True, do_save=False)
            if has_field(pointer, 'DateTime'):
                self.DateTime = pointer.DateTime
            elif has_field(pointer, 'last_updated'):
                self.DateTime = pointer.last_updated
            elif has_field(pointer, 'created'):
                self.DateTime = pointer.created
        if self.rank == 0:
            self.set_score(save_item=False)
        save_mutable_fields(self, *args, **kwargs)
        # prnt('done save post')
        # super(Post, self).save(*args, **kwargs)



# Access to fetch at 'http://104.254.90.114:54312/usa/bills?style=feed' from origin 'http://184.75.208.122:56455' has been blocked by CORS policy: 
# The 'Access-Control-Allow-Origin' header contains multiple values 'http://184.75.208.122:56455, http://184.75.208.122:56455', but only one is allowed. 
# Have the server send the header with a valid value, or, if an opaque response serves your needs, set the request's mode to 'no-cors' to fetch the resource with CORS disabled.

# curl -i -H "Origin: http://184.75.208.122:56455" http://127.0.0.1:54312/usa/bills

# curl -i -H "Origin: http://104.254.90.114:5431" http://127.0.0.1:56455/usa/bills

# class MonitorPageForChange(models.Model):
#     id = models.CharField(max_length=50, default="0", primary_key=True)
#     link = models.URLField(null=True, blank=True)
#     text = models.TextField(blank=True, null=True)
#     new_text = models.TextField(blank=True, null=True)
#     Region = models.ForeignKey('posts.Region', blank=True, null=True, on_delete=models.SET_NULL)

#     def monitor(self):
#         if self.new_text != self.text:
#             from accounts.models import User
#             User.objects.filter(username='Sozed')[0].alert('Page Monitor Alert', self.link, self.province.name)
    
#     def save(self, share=False):
#         if self.id == '0':
#             self = initial_save(self, share=share)
#         # if not self.signature:
#         # sign_obj(self)
#         super(MonitorPageForChange, self).save()




