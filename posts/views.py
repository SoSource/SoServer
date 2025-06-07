
from django.shortcuts import render, redirect
from django.template.defaulttags import register
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from accounts.forms import *
from .forms import DateForm, SearchForm
from .utils import *
from .models import Region, Post, Update, GenericModel
from legis.models import Government,Agenda,BillText,Bill,Meeting,Statement,Motion,Vote,Election,Party,Person,District
from accounts.models import Notification
# from blockchain.models import get_signing_data, convert_to_dict

# from django.urls import resolve
from django.db.models import Q, Value, F, Avg
from django.db.models import Count
from collections import Counter
from operator import itemgetter as _itemgetter
from django_user_agents.utils import get_user_agent
from django.forms.models import model_to_dict

# import auth_token
from uuid import uuid4
import datetime
from django.utils import timezone
from datetime import date
from bs4 import BeautifulSoup
import re
from django.http import JsonResponse
import unicodedata
from unidecode import unidecode
import string
# Create your views here.

@register.filter
def get_item(dictionary, key):
    # prnt('get_item')
    # prnt(dictionary, key)
    try:
        return dictionary.get(key)
    except Exception as e:
        prnt(str(e))
        return None

@register.filter
def get_list_item(lst, pos):
    # prnt('get_item')
    # prnt(dictionary, key)
    try:
        return lst[pos]
    except Exception as e:
        prnt(str(e))
        return None
    
@register.filter
def get_updated_field(item, args):
    # prnt()
    # prnt('get_updated_field', item, args)

    # if args.startswith('"') or args.startswith("'"):
    #     prnt('has quoets')
    # else:
    #     args = '"' + args + '"'
    #     prnt(args)
    #     prnt('added quotes')
    fields = args.split(",")
    # prnt('subfield', fields)
    if item and item.object_type == 'Update':
        update = item
        if 'extra'in fields:
            fields.remove('extra')
            data = update.extra
        else:
            data = update.data
        # prnt(data)
        if data and fields[0] in data:
            result = data[fields[0]]
        else:
            result = ''
            try:
                # try:
                # result = ''
                # obj_field = str(fields[0]) + '_obj'
                # prnt('obj_field', fields[0])
                obj = getattr(update, fields[0])
                # prnt('obj', obj)
                if obj != None:
                    # fail
                    if len(fields) > 1:
                        # prnt('yes', fields[1])
                        subresult = getattr(result, fields[1])
                        # prnt('subresult', subresult)
                        return subresult
                    result = obj
                else:
                    fail
            except Exception as e:
                # prnt(str(e))
                try:
                    # prnt(str(e))
                    obj_field = str(update.pointerType) + '_obj'
                    # prnt('obj_field', obj_field)
                    obj = getattr(update, 'Pointer_obj')
                    # prnt('obj', obj)
                    result = getattr(obj, fields[0])
                    # prnt('result',result)



                    if len(fields) > 1:
                        # prnt('yes', fields[1])
                        subresult = getattr(result, fields[1])
                        # prnt('subresult', subresult)
                        return subresult
                    elif result:
                        return result
                    else:
                        return None
                except Exception as e:
                    # prnt(str(e))
                    pass
        return result
    elif item:
        try:
            obj = getattr(item, fields[0])
            if len(fields) > 1:
                # prnt('yes', fields[1])
                subresult = getattr(obj, fields[1])
                # prnt('subresult', subresult)
                return subresult
            else:
                return obj
        except:
            return None
    else:
        return None

@register.filter
def get_person_field(obj, field):
    try:
        if obj and obj.object_type == 'Person':
            return obj.Update_obj.data[field]
    except Exception as e:
        prnt('fail59947',str(e))
        pass
    return None

@register.filter
def parse_extra_data(key, dictionary):
    try:
        modelType = get_pointer_type(key)
        if modelType == 'Region':
            for r in subRegions:
                for x in dictionary[r]:
                    if x.id == key:
                        return x
        else:
            for x in dictionary[modelType]:
                if x.id == key:
                    return x
    except Exception as e:
        # prnt('fail593757',str(e))
        pass
    return None

@register.filter
def get_update(obj):
    return Update.objects.filter(pointerId=obj.id).first()

@register.filter
def modelNameByRegion(region, model_name):
    if region.data:
        if model_name in region.data and 'name' in region.data[model_name] and region.data[model_name]['name']:
            return region.data[model_name]['name']
    return model_name

@register.filter
def dt_object(dt):
    try:
        return string_to_dt(dt)
    except Exception as e:
        # prnt(str(e))
        return dt

@register.filter
def timezonify(dt, obj):
    # prnt('timezonify',dt,obj)
    if isinstance(obj, models.Model):
        if has_field(obj, 'Region_obj'):
            to_zone = pytz.timezone(obj.Region_obj.timezone)
            local_dt = dt.astimezone(to_zone)
            # prnt('local_dt',local_dt)
            return local_dt
    # prnt('skip')
    return dt
    
@register.filter
def is_obj(text):
    if text.endswith('Id') or text.endswith('_obj'):
        return True
    if 'So' in text and len(text) > 33:
        return True
    return False

@register.filter
def replace_spaces(text):
    try:
        return text.replace(' ','_')
    except Exception as e:
        # prnt(str(e))
        return text
    
@register.filter
def jsonify(obj):
    try:
        return json.loads(obj)
    except Exception as e:
        prnt(str(e))
        return None

@register.filter
def to_int(num):
    try:
        return int(num)
    except:
        return num

@register.filter
def is_int(obj):
    if isinstance(obj, bool):
        return False
    if isinstance(obj, int):
        return True
    return False
    
@register.filter
def list_all_terms(update):
    # prnt('list all terms', update)
    # return {'a':'b'}
    try:
        d = update.data
        terms = d['Terms']
        prnt('t',terms)
        # prnt(json.loads(terms).items())
        return terms
    except Exception as e:
        prnt(str(e))
        return None

@register.filter
def list_75_terms(update):
    # prnt('list 75')
    try:
        d = update.data
        terms = d['Terms']
        l = []
        for item in terms[:75]:
            for key, value in item.items():
                if key not in skipwords:
                    l.append((key, value))
        return l
    except Exception as e:
        # prnt(str(e))
        return None

@register.filter
def get_terms_overflow(update, num):
    # prnt('get overflow')
    try:
        d = update.data
        terms = d['Terms']
        total = len(terms)
        # prnt(total)
        if total > num:
            remaining = total - num
        else:
            remaining = None
        # prnt(remaining)
        return remaining
    except:
        return None

@register.filter # not used
def list_all_people(update):
    prnt('list all people')
    # from accounts.models import Person
    try:
        d = update.data
        people_json = json.loads(d['People_json'])
        # prnt('people_json',people_json)
        # for key, value in people_json.items():
        #     prnt(key, value)
        # l = list(d.items())
        speakers = {}
        keys = []
        for key, value in people_json.items():
            keys.append(key)
        people = Person.objects.filter(id__in=keys)
        for p, value in [[p, value] for p in people for key, value in people_json.items() if p.id == key]:
            speakers[p] = value
        # for key, value in l:
        #     a = Person.objects.filter(id=key)[0]
        #     speakers[a] = value
        H_people = sorted(speakers.items(), key=operator.itemgetter(1),reverse=True)
        # prnt('people', H_people)
        return H_people
    except Exception as e:
        prnt(str(e))
        return None

@register.filter
def get_count(lst, num):
    num = int(num)
    more = None
    x = []
    for i in lst[:num]:
        x.append(i)

    if len(lst) > num:
        more = len(lst) - num
    return [x, more]

@register.filter
def get_ordinal(num):
    # prnt('get ordinal', num)
    if not num:
        return '1st'
    if isinstance(num, str):
        num = int(num)
    n = num
    while n > 100:
        n -= 100
    if n >= 10 and n <= 20:
        return str(num) + 'th'
    elif n % 10 == 1:
        return str(num) + 'st'
    elif n % 10 == 2:
        return str(num) + 'nd'
    elif n % 10 == 3:
        return str(num) + 'rd'
    else:
        return str(num) + 'th'

@register.filter
def get_role_short(position):
    if position == 'President':
        return 'P'
    elif position == 'Representative':
        return 'R'
    elif position == 'Senator':
        return 'S'
    elif position == 'Prime Minister':
        return 'PM'
    elif position == 'Member of Parliament':
        return 'MP'
    elif position == 'MPP':
        return 'MPP'
    elif position == 'Mayor':
        return 'M'
    elif position == 'Councillor':
        return 'C'

@register.filter
def order_terms(terms, termList):
    order = []
    if terms:
        lowerTerms = [term.lower() for term in terms]
        if termList and terms:
            for t in termList:
                if t.lower() in lowerTerms:
                    # prnt(t)
                    order.append(t)
        if terms:
            for t in terms:
                if t not in order:
                    order.append(t)
    return order

@register.filter
def html_json(text):
    return None
    try:
        return text.replace('"', "'").replace('\n', '').strip()
    except:
        return None
    text = ''.join(text.splitlines())
    return text.replace('"', "'").replace('\n', '').strip()
    text = unidecode(text)
    return text.replace('"', "'").replace(';','').replace('\n', '').strip()

@register.filter
def remove_tags(text):
    try:
        TAG_RE = re.compile(r'<[^>]+>')
        text = TAG_RE.sub('', text).replace('"', "'").replace('\n', '').strip()
        text = ''.join(text.splitlines())
        text = unidecode(text)
        return text
    except:
        return None

@register.filter
def short_gov(gov_type):
    try:
        if gov_type == 'Parliament':
            return 'Parl.'
        elif gov_type == 'Congress':
            return 'Congr.'
        else:
            return 'Gov.'
    except:
        return gov_type

@register.filter
def get_toc(obj):
    if obj:
        try:
            toc = None
            if obj.object_type == 'BillText':
                if 'TextNav' in obj.data:
                    toc = obj.data['TextNav']
            elif obj.object_type == 'Update':
                if 'TextNav' in obj.extra:
                    toc = obj.extra['TextNav']
            if toc and isinstance(toc, list):
                return toc
        except Exception as e:
            prnt(str(e))
            pass
    return None
    
@register.filter
def convert_prntable(text):
    # text = unidecode(text)
    # prntable = set(string.prntable)
    # return ''.join(filter(lambda x: x in prntable, text))
    # return text.encode('ascii',errors='ignore')
    return text

@register.filter
def get_bill_term(hansard, bill):
    d = ''
    try:
        for key, value in hansard.list_all_terms():
            try:
                k = Keyphrase.objects.annotate(string=Value(key)).filter(string__icontains=F('text')).filter(bill=bill, hansardItem__hansard=hansard)[0]
                num = value + 1
                term = key
                return "<li><span>(" + str(num) + ")</span>&nbsp; <a href='" + hansard.get_absolute_url() + "/?topic=" + term + "' title='" + term + "'>" + term + " </a></li>"
            except Exception as e:
                # prnt(str(e))
                pass
    except:
        pass
    return d

@register.filter
def match_terms(update, keywords):
    if 'Terms' in update.data and keywords:
        terms = update.data['Terms']
        count = 0
        n = 0
        order = {}
        for t in terms:
            for key, value in t.items():
                if n <= 5 and key in keywords:
                    n += 1
                    if key not in order:
                        order[key] = value
            if n > 5:
                break
        count = n
        extras = 0
        for t in terms:
            if count < 75:
                count += 1
                for key, value in t.items():
                    if key not in order:
                        order[key] = value
            else:
                extras += 1
        return [order, extras]
    else:
        return []


def render_view(request, context, country=None, feed=False):
    # prnt('renderview')
    style = request.GET.get('style', 'index')
    if style == 'feed' or feed:
        return render(request, "utils/feed.html", get_paginator_url(request, context))
    else:
        # if not request.user.is_authenticated:
        #     try:
        #         appToken = request.COOKIES['appToken'] # for app users
        #         # user = User.objects.filter(appToken=appToken)[0]
        #     except Exception as e:
        #         # prnt(str(e))
        #         appToken = None
        #     # try:
        #     #     userToken = request.COOKIES['userToken'] # for anon users
        #     #     # prnt('userToken', userToken)
        #     #     # user = User.objects.filter(userToken=userToken)[0]
        #     # except Exception as e:
        #     #     # prnt(str(e))
        #     #     # userToken = None
        #     #     userToken = uuid4()

        #         # user_agent = get_user_agent(request)
        #         # if not user_agent.is_bot:
        #         #     from random_username.generate import generate_username
        #         #     rand_username = generate_username(1)[0]
        #         #     user = User(username=rand_username, userToken=userToken, appToken=appToken, anon=True)
        #         #     user.slugger()
        #         #     user.save()
        # else:
        #     appToken = request.user.appToken
        #     if not appToken:
        #         request.user.appToken = uuid4()
        #         request.user.save()
        #     # userToken = request.user.userToken
        #     # if not userToken:
        #     #     request.user.userToken = uuid4()
        #     #     request.user.save()
        try:
            fcmDeviceId = request.GET.get('fcmDeviceId', '')
            if not fcmDeviceId:
                fcmDeviceId = request.COOKIES['fcmDeviceId']
            # prnt('dviceId', fcmDeviceId)
            if fcmDeviceId:
                # from fcm_django.models import FCMDevice
                fcm_device = CustomFCM.objects.filter(registration_id=fcmDeviceId).first()
                if not fcm_device:
                    fcm_device = CustomFCM()
                    fcm_device.registration_id = fcmDeviceId
                fcm_device.user = request.user
                fcm_device.active = True
                fcm_device.save()
                # prnt('saved device')
        except Exception as e:
            # prnt(str(e))
            pass
        
        ctx = get_cookies(request,context,country=country)
        ctx = {}
        prnt('ctx')
        response = render(request, "home.html", ctx)
        prnt('render 1')
        width = request.GET.get('width', '')
        if width:
            response.set_cookie(key='deviceWidth', value=width, expires=datetime.datetime.today()+datetime.timedelta(days=3650))
        if fcmDeviceId:
            response.set_cookie(key='fcmDeviceId', value=fcmDeviceId, expires=datetime.datetime.today()+datetime.timedelta(days=3650))
        # if appToken:
        #     response.set_cookie(key='appToken', value=appToken, expires=datetime.datetime.today()+datetime.timedelta(days=3650))
        prnt('passed render')
        # if userToken:
        #     response.set_cookie(key='userToken', value=userToken, expires=datetime.datetime.today()+datetime.timedelta(days=3650))
        prnt('rendering')
        return response

def test_view(request):
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'recent')

    import numpy as np
    # import pandas as pd
    from os import path
    from PIL import Image
    from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
    import matplotlib.pyplot as plt
    # Start with one review:
    bill = Bill.objects.exclude(first_reading_html=None)[4]
    prnt(bill.NumberCode)
    prnt(bill.ShortTitleEn)
    cleantext = BeautifulSoup(bill.first_reading_html, "lxml").text

    p = Person.objects.filter(first_name='Pierre', last_name='Poilievre')[1]
    prnt(p)
    hansards = HansardItem.objects.filter(person=p)
    prnt(hansards.count())
    cleantext = ''
    for h in hansards:
        cleantext = cleantext + ' ' + h.Content
    cleantext = BeautifulSoup(cleantext, "lxml").text
    
    # Create stopword list:
    stopwords = set(STOPWORDS)
    stopwords.update(["C", "Canada", "House", 'Commons', 'Parliament', 'Government', 'Speaker', 'Canadian', 'Canadians', 'Mr','Madam', 'Paragraph', 'Act', 'subsection', 'section'])
    # Create and generate a word cloud image:
    wordcloud = WordCloud(stopwords=stopwords, background_color="white").generate(cleantext)

    # Display the generated image:
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    # wordcloud = plt.show()

    import base64
    import io
    image = io.BytesIO()
    import urllib.parse
    plt.savefig(image, format="png")
    image.seek(0)
    string = base64.b64encode(image.read())
    image_64 = "data:image/png;base64," +   urllib.parse.quote_plus(string)


    context = {
        # 'title': title,
        # 'nav_bar': list(options.items()),
        # 'view': view,
        'wordcloud': image_64,
        'cards': 'test',
        'sort': sort,
        # 'feed_list':setlist,
        # 'useractions': useractions,
        "form": AgendaForm(request.POST),
    }
    return render_view(request, context)

def testor_script(num):
        prnt('testor script', num)
        time.sleep(30)
        prnt('done',num)

def splash_view(request):
    logger.debug('SPLASH')
    style = request.GET.get('style', 'index')
    prnt('HI!2')
    # u = User.objects.all()
    # for i in u:
    #     prnt('u',convert_to_dict(i))
    # s = Sonet.objects.first()
    # prnt('s',convert_to_dict(s))
    # models = [
    #     'User',
    #     'Sonet',
    # 'Region',
    # # 'Role',
    # 'Update',
    # 'District',
    # 'Person',
    # 'Party',
    # 'Government',
    # 'Vote',
    # 'Motion',
    # 'Committee',
    # 'Statement',
    # 'Meeting',
    # 'Bill',
    # # 'BillVersion',
    # 'Agenda',
    # # 'AgendaItem',
    # # 'AgendaTime',
    # 'GenericModel',
    # 'Post',
    # 'Keyphrase',
    # 'KeyphraseTrend',
    # 'Election',
    # 'Notification',
    # 'UserNotification',
    # 'Blockchain',
    # 'Validator',
    # 'Wallet',
    # 'UserTransaction',
    # 'Node'
    # ]
    # for model in models:
    #     prnt()
    #     prnt('get model:', model)
    #     objs = get_dynamic_model(model, list=True)
    #     for obj in objs:
    #         prnt(obj)
    #         super(get_model(obj.object_type), obj).delete()

    # u = request.user
    # u.is_superuser = True
    # u.is_staff = True
    # u.is_admin = True
    # # u.id = super_id
    # u.save()
    # from accounts.models import User
    # u = request.user
    # u.is_superuser = True
    # u.is_staff = True
    # u.is_admin = True
    # super(User, u).save()
    
    # country = Region.objects.filter(Name='USA').first()
    # member_code = 'A000370'
    # p = Person.objects.filter(GovIden__iexact=member_code, Country_obj=country).first()
    # prnt(p)
    # person, personU, person_is_new = get_model_and_update('Person', obj=p)
    # prnt(person)
    # from blockchain.models import connect_to_node, get_self_node
    # data = [{'testing':123}]
    # json_data = {'type':'for_validation', 'function':'test', 'gov_id':'govid', 'content': json.dumps(data)}
    # # downstream_broadcast(broadcast_list, 'blockchain/receive_posts_for_validating', json_data)
    # connect_to_node(get_self_node(), 'blockchain/receive_posts_for_validating', json_data)
    # data = {'type': 'Blocks', 'broadcast_list': {'nodSo7e7fc6cb070640fa9d1656f1a20d29e3': ['179.61.197.189:54312']}, 'blockchainId': 'chaSoe89e21a42b442188f9d4815d6b503a4a', 'genesisId': 'Nodes', 'block_list': '[{"block_dict": {"object_type": "Block", "latestModel": 1, "modelVersion": 1, "blockchainType": "Nodes", "id": "bloSo51298bad3dd6457c83c40ef005f3493a", "created_dt": "2024-11-17T01:36:26.949144+00:00", "blockchainId": "chaSoe89e21a42b442188f9d4815d6b503a4a", "Blockchain_obj": "chaSoe89e21a42b442188f9d4815d6b503a4a", "publicKey": "0473aabdbd6dbbf2f8fb60fd3ce0bc7035d558e1c4e980c29b7c86e8bdda99ca7dd4275edc8ece06c301cc6788d137ea66f3969a46d84d636eefdaf4d2fb8bfd3a", "signature": "3046022100db2b0c7b2677b1eaffc76546a23a435671273e71ecc900b8e54c04d1285ad6ca022100f1787a7e28387d530c764fdd200cc0a727ec255f22238f9366b313391d514b79", "CreatorNode_obj": "nodSo7e7fc6cb070640fa9d1656f1a20d29e3", "Transaction_obj": null, "index": 1, "DateTime": "2024-11-17T01:40:00+00:00", "hash": "ff50be739ca0d34c670457bffe479239bc33f5b9b75587b44c17ae383042f9df", "previous_hash": "0000000", "data": {"All": ["nodSo7e7fc6cb070640fa9d1656f1a20d29e3"], "regSob66532ffce3928d214c8c7fe791dbbee": {"scripts": ["nodSo7e7fc6cb070640fa9d1656f1a20d29e3"], "servers": ["nodSo7e7fc6cb070640fa9d1656f1a20d29e3"]}}, "validators": {}, "number_of_peers": 2}, "block_transaction": null, "block_data": [], "validations": null}]', 'end_of_chain': True, 'senderId': 'nodSo7e7fc6cb070640fa9d1656f1a20d29e3', 'dt': '2024-11-17T01:36:27.046906+00:00', 'dtsig': '304402203dc474c6d574a222ee2ad0e626e66a949acf6a211a20922a3ca148c4df3d51eb02207862f3c77d48a32b9afdc5d41cd65cb4ccff467e57dd940d3be938b51b167156'}

    # from blockchain.models import Blockchain, Block
    # from accounts.models import Wallet, UserPubKey

    # # sonet = Sonet.objects.first()
    # # prnt('sonet',sonet)
    # # if sonet:
    # #     x = convert_to_dict(sonet)
    # #     prnt('\nx',x)
    
    # chains = Blockchain.objects.exclude(genesisType='Region')
    # prnt('chains',chains)
    # users = User.objects.all()
    # prnt('users',users)
    # for u in User.objects.all():
    #     prnt(u, verify_obj_to_data(u,u))
    # wallets = Wallet.objects.all()
    # prnt('wallets',wallets)
    # upks = UserPubKey.objects.all()
    # prnt('upks',upks)
    # get_model_fields()

    # model = get_model('User')

    # if has_method(model, 'get_version_fields'):
    #     fields = model().get_version_fields()
    # else:
    #     fields = []
    # prnt('fields',fields)

    
    context = {
        'title': 'Welcome',
        'cards': 'splash',
        'supported_regions': Region.valid_objects.filter(is_supported=True).order_by('Name'),
    }
    return render_view(request, context)

def home_view(request, region):
    prnt()
    prnt()
    prnt('------------homeview')
    # prnt(request.user)
    prnt(region)
    
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    


    style = request.GET.get('style', 'index')

    sort = request.GET.get('sort', 'recent')
    if sort == 'trending':
        sort_link = '?sort=recent'
        sort_type = '-date_time'
    else:
        sort_link = '?sort=trending'
        sort_type = '-date_time'
    if user:
        view = request.GET.get('view', 'Recommended')
    else:
        view = request.GET.get('view', 'Trending')
    page = request.GET.get('page', 1)
    getDate = request.GET.get('date', None)
    # province, region = get_region(request)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # Chamber = get_Chamber(request)
    if user:
        # options = {'Chamber: %s' %(Chamber): 'Chamber', 'Page: %s' %(page): '?view=%s&page=' %(view), 'Recommended': '?view=Recommended', 'Trending': '?view=Trending'}
        nav_options = [nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'),
                    nav_item('button', f'Page: {page}', 'subNavWidget', 'pageForm'), 
                    nav_item('link', 'Recommended', f'?view=Recommended', None), 
                    nav_item('link', 'Trending', f'?view=Trending', None)]
    else:
        # options = {'Chamber: %s' %(Chamber): 'Chamber', 'Page: %s' %(page): '?view=%s&page=' %(view), 'Trending': '?view=Trending'}
        nav_options = [nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'),
                    nav_item('button', f'Page: {page}','subNavWidget', 'pageForm'),
                    nav_item('link', 'Trending', f'?view=Trending', None)
                    ]
    # if request.user.is_authenticated and request.user.is_god:
    #     options['testNotify'] = '?test-notify=True'
    cards = 'home_view'
    title = 'The Government of %s' %(country.Name)
    # title = '%s' %(country.Name)
    if style == 'index' and page == 1:
        context = {
            'title': title,
            'nav_bar': nav_options,
            'view': view,
            # 'provState': provState,
            'cards': cards,
            'sort': sort,
            'style':style
        }
        return render_view(request, context, country=country)
    else:
        prnt('feed')
        # return render_view(request, {}, country=country)
        prnt('1 Chamber', current_chamber)
        # posts = Post.objects.filter(Country_obj=country, Meeting_obj__meeting_type__iexact='Debate').filter(Meeting_obj__Chamber__in=chambers).select_related('Meeting_obj').order_by('-Meeting_obj__DateTime')
        # setlist = paginate(posts, page, request)

    # hansardItems = None
        # if view == 'Recommended':
        #     posts = Post.objects.filter(post_type='bill').filter(Q(bill__NumberCode='C-18')|Q(bill__NumberCode='C-11')|Q(bill__NumberCode='C-22')).select_related('bill', 'bill__person').order_by('-rank','-date_time', '-id')
        if view == 'Recommended':
            include_list = ['Bill', 'Meeting']
            
            posts, view = algorithim(user, include_list, current_chamber, country, provState.Name, view, page)

        else:   
            include_list = ['Bill','Meeting']
            # view = 'Trending'
            # trends = Post.objects.filter(organization__in=orgs).filter(Q(date_time__lte=datetime.datetime.now() + datetime.timedelta(hours=1))|Q(date_time__gte=datetime.datetime.now() + datetime.timedelta(days=30))).filter(post_type__in=include_list).order_by('-rank', sort_type)[:200]
            # keys = []
            # for p in trends:
            #     if p.keywords:
            #         keys = keys + p.keywords   
            # posts = Post.objects.filter(organization__in=orgs).filter(Q(date_time__lte=datetime.datetime.now() + datetime.timedelta(hours=1))|Q(date_time__gte=datetime.datetime.now() + datetime.timedelta(days=30))).filter(post_type__in=include_list).filter(keywords__overlap=keys).annotate(matches=Count('keywords')+F('rank')).order_by('-matches','-date_time')
                
            # posts, view = algorithim(request, include_list, Chamber, region, view, page)
            cards = 'top_cards'
            # prnt(Chamber, provState.Name)
            posts = getTrendingTop(current_chamber, country)
            if posts.count() == 0:
                posts, view = algorithim(user, include_list, current_chamber, country, provState.Name, view, page)
                cards = 'home_view'
        setlist = paginate(posts, page, request)
        prnt('view',view)
        # for i in setlist:
        #     prnt(i.pointerType)
        #     prnt(i.keyword_array)
        #     try:
        #         prnt('b',i.Bill_obj.Chamber)
        #     except:
        #         pass
        prnt('--------')
        # for i in setlist:
        #     prnt(i.Update_obj.keyword_array)
        if view == 'Recommended' and user and user.UserData_obj:
            # counter = Counter(request.user.keywords)
            # userKeys = counter.most_common()[0]
            userKeys = [k for k, value in Counter(user.UserData_obj.get_interests()).most_common()]
        else:
            if current_chamber == 'House':
                orgs = ['House', 'House of Commons', 'Congress']
            elif current_chamber == 'Senate':
                orgs = ['Senate']
            elif current_chamber == 'All':
                orgs = ['Senate', 'House', 'House of Commons', 'Congress', '%s-Assembly'%(provState.Name)]
            elif current_chamber == 'Assembly':
                orgs = ['%s-Assembly'%(provState.Name)]
            try:
                dateQuery = Statement.objects.filter(meeting_type='Debate', Chamber__in=orgs).order_by('-DateTime')[12].DateTime
                dt = datetime.datetime.now().replace(tzinfo=pytz.UTC) - dateQuery
            except:
                dt = datetime.datetime.now().replace(tzinfo=pytz.UTC) - datetime.datetime.now().replace(tzinfo=pytz.UTC)
            userKeys = get_trending_keys(dt, include_list, orgs)
            # prnt('!!!!!!!!!!!!!', userKeys)

        # useractions = get_useractions(user, setlist)  
        # my_rep = getMyRepVotes(user, setlist) 
        daily = None
        if page == 1:
            # daily = getDaily(request, province, getDate)
            pass
        try:
            isApp = request.COOKIES['fcmDeviceId']
        except:
            isApp = None
        # cards = 'home_view'
        # prnt('cards',cards)
        prnt('fin')
        context = {
            'title': title,
            'nav_bar': nav_options,
            'isApp': isApp,
            'view': view,
            # 'provState': provState_name,
            'cards': cards,
            'dailyCard': daily,
            'sort': sort,
            'feed_list':setlist,
            'style':style,
            # 'user_keywords': userKeys,
            # 'posts': setlist,
            'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            'myRepVotes': getMyRepVotes(user, setlist),
        }
        return render_view(request, context)

def following_view(request):
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'recent')
    view = request.GET.get('view', 'Current')
    page = request.GET.get('page', 1)
    # u = request.user
    user_data, user = get_user_data(request)
    u = user
    country, provState, county, city = get_regions(request, None, user)
    if not user:
        return redirect('/')
    # country, provState, county, city = get_regions(request, region, user_data, user)
    
    # Chamber = get_Chamber(request)
    # options = {'Current': '?view=Current', 'Upcoming': '?view=Upcoming', 'Following':'%s?view=Following' %(request.user.get_absolute_url())}
    nav_options = [nav_item('link', 'Current', '?view=Current', None), 
                   nav_item('link', 'Upcoming','?view=Upcoming', None),
                   nav_item('link', 'Following','%s?view=Following' %(user.get_absolute_url()), None)]
    cards = 'home_list'
    title = 'Following'
    if style == 'index':
        context = {
            'title': title,
            'nav_bar': nav_options,
            'view': view,
            'cards': cards,
            'sort': sort,
            # 'country': country,    
        }
        return render_view(request, context)
    else:
        getList = []
        topicList = []
        for p in u.follow_Person.objs.all():
            getList.append(p.id)
        for p in u.follow_Bill_objs.all():
            getList.append('%s?current=True' %(p.NumberCode))
        for p in u.follow_Committee_objs.all():
            getList.append(p.code)
        for p in u.get_follow_topics():
            getList.append(p)
            topicList.append(p)
        # prnt(getList)
        posts = Post.objects.filter(Country_obj=country).filter(keyword_array__overlap=getList).filter(date_time__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), '%Y-%m-%d')).select_related('Meeting', 'Statement','Bill').order_by('-date_time')
        setlist = paginate(posts, page, request)
        # useractions = get_useractions(request, setlist) 
        try:
            isApp = request.COOKIES['fcmDeviceId']
        except:
            isApp = None 
        context = {
            'isApp': isApp,
            'view': view,
            'cards': cards,
            'sort': sort,
            'feed_list':setlist,
            'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            'topicList': topicList,
        }   
        return render_view(request, context, country=country)

def topic_view(request, region, keyword):
    prnt(keyword)
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'Newest')
    view = request.GET.get('view', 'Current')
    keyword = request.GET.get('keyword', keyword)
    # keyword = keyword.lower()
    page = request.GET.get('page', 1)
    getDate = request.GET.get('date', None)
    # keyword = request.GET.get('keyword', '')
    # Chamber = get_Chamber(request)
    # province, region = get_region(request)
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, None, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    follow = request.GET.get('follow', '')
    ordering = get_sort_order(sort)
    if follow and keyword:
        # if request.user.is_authenticated:
        #     user = request.user
        # else:
        #     userToken = request.COOKIES['userToken']
        #     user = User.objects.filter(userToken=userToken)[0]
        prnt('follow')
        fList = user.get_follow_topics()
        if keyword in fList:
            fList.remove(keyword)
            user = set_keywords(user, 'remove', keyword)
            response = 'Unfollow "%s"' %(keyword)
        elif keyword not in fList:
            fList.append(keyword)
            user = set_keywords(user, 'add', keyword)
            response = 'Following "%s"' %(keyword)
        user.set_follow_topics(fList)
        user.save()
        prnt('done')
        return render(request, "utils/dummy.html", {"result": response})
    if user and keyword in user.follow_topics:
        f = 'following'
    else:
        f = 'follow'
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    # options = {'Chamber: %s' %(Chamber): 'Chamber', 'follow':'%s?follow=%s' %(request.path, f), 'Sort: %s'%(sort):sort }
    
    # cards = 'home_list'
    title = 'Topic: %s' %(keyword)
    if style == 'index' and page == 1:
        # nav_options = [nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'),
        #         nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
        #         nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
        nav_options = [nav_item('button', f'Chamber:{current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'), 
                   nav_item('button', 'follow', f'react', f'"follow2", "{request.path}?keyword={keyword}&follow={f}"'), 
                   nav_item('link', f'Sort: {sort}', f'?keyword={keyword}&sort={sort}', None)]
        context = {
            'isApp': isApp,
            'title': title,
            'nav_bar': nav_options,
            'view': view,
            'keyword': keyword,
            'cards': 'home_list',
            'sort': sort,
            'gov_levels': gov_levels,
            'style':style,
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)


            # fix all_chambers in get getTrending


        }
        return render_view(request, context, country=country)
        # try:
        #     # if request.user.is_authenticated:
        #     #     user = request.user
        #     # elif not user:
        #     #     userToken = request.COOKIES['userToken']
        #     #     user = User.objects.filter(userToken=userToken)[0]
        #     user = set_keywords(request.user, 'add', keyword)
        #     user.save()
        # except:
        #     pass
        # context = {
        #     'title': title,
        #     'nav_bar': nav_options,
        #     'view': view,
        #     'region': region,
        #     'cards': 'home_list',
        #     'keyword': keyword,
        #     'sort': sort,
        #     'sortOptions': ['Oldest','Newest','Loudest','Random'],
        # }
        # return render_view(request, context, country=country)
    else:
        prnt('isfeed')
        getList = [keyword]
        topicList = [keyword]
        if getDate:
            firstDate = datetime.datetime.strptime(getDate, '%Y-%m-%d')
            secondDate = firstDate + datetime.timedelta(days=1)
        else: 
            secondDate = datetime.datetime.now() + datetime.timedelta(hours=1)
            firstDate = secondDate - datetime.timedelta(days=1000)
        # Chamber, Chambers = get_Chambers(request, country, provState, municipality)
        
        prnt('list',getList)
        posts = Post.objects.filter(Country_obj=country, Chamber__in=chambers).filter(keyword_array__overlap=getList).order_by(ordering,'-DateTime')
        prnt('posts',posts)
        # posts = Post.objects.filter(Country_obj=country, Chamber__iexact__in=chambers).filter(keyword_array__overlap=getList).filter(DateTime=firstDate, DateTime__lt=secondDate).order_by(ordering,'-date_time')
        # if Chamber == 'All':
        # else: 
        #     posts = Post.objects.filter(Country_obj=country, Chamber__iexact=Chamber).filter(keyword_array__overlap=getList).filter(date_time__gte=firstDate, date_time__lt=secondDate).select_related('Meeting', 'Statement','Bill').order_by(ordering,'-date_time')
        
        
        
        
        try:
            setlist = paginate(posts, page, request)
        except:
            setlist = []
        # useractions = get_useractions(request, setlist)  
        
        # cards = 'home_list'
        # context = {
        #     'isApp': isApp,
        #     'view': view,
        #     'cards': 'home_list',
        #     'keyword': keyword,
        #     'sort': sort,
        #     'sortOptions': ['Oldest','Newest','Loudest','Random'],
        #     'feed_list':setlist,
        #     'useractions': get_useractions(user, setlist),
        # # '   updates': get_updates(setlist),
        #     'topicList': topicList,
        # }
        # # return render_view(request, context, country=country)
        setlist = paginate(posts, page, request)
        # useractions = get_useractions(request, setlist)
        context = {
            'isApp': isApp,
            # 'title': title,
            # 'subtitle': subtitle,
            # 'nav_bar': nav_options,
            'view': view,
            # 'region': region,
            # 'dateForm': form,
            'cards': 'home_list',
            'sort': sort,
            'feed_list':setlist,      
            'style':style, 
            'topicList': topicList,
            'keyword': keyword,
            'useractions': get_useractions(user, setlist),
            'isMobile': request.user_agent.is_mobile,
            # 'updates': get_updates(setlist),
        }
        return render_view(request, context, country=country)

def search_view(request, keyword):
    style = request.GET.get('style', 'index')
    # sort = request.GET.get('sort', 'recent')
    view = request.GET.get('view', '')
    sort = request.GET.get('sort', 'Newest')
    keyword = request.GET.get('keyword', keyword)
    keyword = keyword.lower()
    page = request.GET.get('page', 1)
    search = request.POST.get('post_type', '')
    autoComplete = request.GET.get('search')
    follow = request.GET.get('follow', '')
    cards = 'home_list'
    ordering = get_sort_order(sort)
    title = 'Search: %s' %(search)    
    # province, region = get_region(request)
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, None, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # options = {'Chamber: %s' %(Chamber): 'Chamber'}
    # nav_options = [nav_item('button', f'Chamber:{Chamber}', 'subNavWidget("chamberForm")')]
    searchform = SearchForm(initial={'post_type': search})
    subtitle = ''
    if follow and follow != 'following' and follow != 'follow':
        # if request.user.is_authenticated:
        #     user = request.user
        # else:
        #     try:
        #         userToken = request.COOKIES['userToken']
        #         user = User.objects.filter(userToken=userToken)[0]
        #     except:
        #         pass
        if user:
            fList = user.get_follow_topics()
            topic = follow
            if topic in fList:
                fList.remove(topic)
                response = 'Unfollow "%s"' %(topic)
                user = set_keywords(user, 'remove', topic)
            elif topic not in fList:
                fList.append(topic)
                response = 'Following "%s"' %(topic)
                user = set_keywords(user, 'add', topic)
            user.set_follow_topics(fList)
            user.save()
        else:
            response = 'Please login'
        return render(request, "utils/dummy.html", {"result": response})
    if keyword:
        title = 'Search: %s' %(keyword)
        # options['follow'] = '%s' %(keyword)
        nav_options.append(nav_item('button', 'follow', f'react("follow2", "{keyword}")'))
        posts = Post.objects.filter(keyword_array__icontains=keyword).exclude(date_time=None).order_by(ordering,'-date_time')
        if posts.count() == 0:
            posts = Archive.objects.filter(keyword_array__icontains=keyword).exclude(date_time=None).order_by(ordering,'-date_time')
        if posts.count() == 1:
            response = redirect(posts[0].get_absolute_url())
            return response
    elif autoComplete:
        keyphrases = Keyphrase.objects.filter(Chamber__iexact__in=Chambers).filter(key__icontains=autoComplete)[:500]
        # if Chamber == 'All':
        # else:
        #     keyphrases = Keyphrase.objects.filter(Chamber__iexact=Chamber).filter(text__icontains=autoComplete)[:500]

        # if Chamber == 'All':
        #     if 
        #     keyphrases = Keyphrase.objects.filter(text__icontains=autoComplete)[:500]
        #     # prnt(keyphrases)
        # elif Chamber == 'House':
        #     keyphrases = Keyphrase.objects.filter(Chamber__iexact=Chamber).filter(text__icontains=autoComplete)[:500]
        # elif Chamber == 'Senate':
        #     keyphrases = Keyphrase.objects.filter(organization='Senate').filter(text__icontains=autoComplete)[:500]
        # elif Chamber == 'Assembly':
        #     # org = get_province_name
        #     keyphrases = Keyphrase.objects.filter(organization='%s-Assembly'%(region)).filter(text__icontains=autoComplete)[:500]
        data = []
        for k in keyphrases:
            if k.key not in data:
                data.append(k.key)
        return JsonResponse({'status':200, 'data':data})
    else:
        posts = {}
    try:
        setlist = paginate(posts, page, request)
    except:
        setlist = []
    # useractions = get_useractions(request, setlist) 
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None 
    # my_rep = getMyRepVotes(request, setlist) 
    # options = {'Chamber: %s' %(Chamber): 'Chamber', 'Page: %s' %(page): '?page=1', 'Sort: %s'%(sort): sort, 'Search': 'search', 'Date': 'date'}
    nav_options = [nav_item('button', f'Chamber:{Chamber}', 'subNavWidget', 'chamberForm'), 
                   nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'),
            # nav_item('link', 'Page: %s' %(page), '?view=%s&page=' %(view)), 
            nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm'), 
            # nav_item('link', 'Current', '?view=Current'), 
            # nav_item('link', 'Upcoming', '?view=Upcoming'),
            nav_item('button', 'Search', 'subNavWidget', 'searchForm'), 
            nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
    context = {
        'isApp': isApp,
        'title': title,
        'subtitle': subtitle,
        'nav_bar': nav_options,
        'sort': sort,
        'sortOptions': ['OLdest','Newest','Loudest','Random'],
        'keyword': keyword,
        'view': view,
        # 'region': region,
        'searchForm': searchform,
        'cards': cards,
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        'myRepVotes': getMyRepVotes(user, setlist),
        'topicList': [keyword],
        # 'myRepVotes': my_rep,
        # 'country': Country.objects.all()[0],
    }
    return render_view(request, context, country=country)

def region_view(request):

    # 'http://127.0.0.1:3005/region/?roles=248a5155ed65dca9314691b8fc2268e2_c92a453e9ac93a2c7d21acb4805b0a96_69594b4d93480d5dfaf3f27b96d2dc79_27fb9a930b4783e5e23d351dcbf2a62e_c8a7b81c2e498c8758ff370fd292b734_285a72dacd7a33b5e3a67d900de0e149_2aaac504f2a2d03b4178ea2acc527951_ecb11ecceeedb1bc8388d2cba5a3622e_388584696567db337808dfbd90190f7b_282610a7da9438aa60b2da63c548583a_438f39af65b86b541394a341cdbc5a56_3e1be8b27e43ac131b7dbc63694c1e50_f1c0bd179caa381407803b236353bbb3_505d69b9375103ac4bcdbe00e3bb05e8_'

    # style = request.GET.get('style', 'index')
    # sort = request.GET.get('sort', 'recent')
    # if sort == 'trending':
    #     sort_link = '?sort=recent'
    #     sort_type = '-date_time'
    # else:
    #     sort_link = '?sort=trending'
    #     sort_type = '-date_time'
    # view = request.GET.get('view', 'current')
    # if request.user.is_authenticated:
    #     if not request.user.postal_code: 
    #         response = redirect('/set-region')
    #         # prnt(response)
    #         return response
    title = 'My Representatives'
    role_idens = request.GET.get('roles', '')
    user_data, user = get_user_data(request)
    prnt(user)
    nav_options = [nav_item('button', 'Set Region', "modalPopPointer", '"Select Region", "/accounts/get_country_modal"'), nav_item('button', 'Save to Account', "save_regions_to_account", user.id)]
    prnt('role_idens',role_idens)
    def process_me(posts, data):
        for p in posts:
            if p.Role_obj.gov_level == 'Federal':
                level = 'Country'
            else:
                level = p.Role_obj.gov_level
            if p.Role_obj.Country_obj:
                data['country'] = p.Role_obj.Country_obj
            if p.Role_obj.ProvState_obj:
                data['provState'] = p.Role_obj.ProvState_obj
            if p.Role_obj.Region_obj:
                data[level]['region'] = p.Role_obj.Region_obj

            if p.Role_obj.District_obj and p.Role_obj.District_obj.Name in data[level]['districts']:
                data[level]['districts'][p.Role_obj.District_obj.Name]['roles'].append(p)
            elif p.Role_obj.District_obj:
                data[level]['districts'][p.Role_obj.District_obj.Name] = {'district':p.Role_obj.District_obj, 'roles':[p]}
            else:
                data[level]['roles'].append(p)
        for key, value in data.items():
            try:
                data[key]['roles'] = [p for p in data[key]['roles'] if p.Role_obj.Chamber == 'Executive'] + [p for p in data[key]['roles'] if p.Role_obj.Chamber == 'House'] + [p for p in data[key]['roles'] if p.Role_obj.Chamber == 'Senate'] + [p for p in data[key]['roles'] if p.Role_obj.Chamber == None]
            except:
                pass
            try:
                for k, v in data[key]['districts'].items():
                    data[key]['districts']['roles'] = [p for p in data[key]['districts']['roles'] if p.Role_obj.Chamber == 'Executive'] + [p for p in data[key]['districts']['roles'] if p.Role_obj.Chamber == 'House'] + [p for p in data[key]['districts']['roles'] if p.Role_obj.Chamber == 'Senate'] + [p for p in data[key]['districts']['roles'] if p.Role_obj.Chamber == None]
            except:
                pass
        return data
    
    data = {
        'country': None,
        'provState': None,
        'Country':{'region':None, 'districts':{}, 'roles':[]},
        'State':{'region':None, 'districts':{}, 'roles':[]},
        'County':{'region':None, 'districts':{}, 'roles':[]},
        'City':{'region':None, 'districts':{}, 'roles':[]},
            }
    if role_idens:
        id_list = []
        id_list = role_idens.split('_')
        posts = Post.objects.filter(pointerType='Role', Role_obj__id__in=id_list)
        data = process_me(posts, data)
        
    elif user and user.localities:
        localities = json.loads(user.localities)
        regions = Region.valid_objects.filter(id__in=localities)
        districts = District.objects.filter(id__in=localities)
        # for r in regions:
        #     prnt(r)
        # for d in districts:
        #     prnt(d)
        offices = [office for office in [d.Office_array for d in districts]] + [office for office in [r.Office_array for r in regions]]
        posts = Post.objects.filter(pointerType='Role').filter(Role_obj__Position__in=offices, Update_obj__data__contains={'Current': True}).filter(Q(Role_obj__ProvState_obj__id__in=localities)|Q(Role_obj__District_obj__id__in=localities)|Q(Role_obj__Region_obj__id__in=localities)|Q(Role_obj__Country_obj__id__in=localities))
        # for p in posts:
        #     prnt(p)
        data = process_me(posts, data)
    else:
        data = None

    # prnt('\ndata:',data)
    # options = [{'type':'button', 'text':'Set Region', 'target':'/set-region'}]
    # cards = 'region_form'
    # try:
    #     MP = Role.objects.filter(position='Member of Parliament', riding=request.user.riding, current=True)[0]
    # except:
    #     MP = None
    # reps = {}
    # if user_data:
    # if user:
    #     reps = get_reps(user)
    # else:
    #     reps = {}
    # prnt(reps)
    # form = RegionForm(initial={'address': request.user.address})
    context = {
        # 'has_reps': True,
        # 'user': user,
        'title': title,
        'nav_bar': nav_options,
        # 'view': view,
        'cards': 'region_form',
        'data':data,
        # 'roles':roles,
        # 'districts':districts,
        # 'regions':regions,
        # 'provStates':provStates,
        # 'updates': get_updates(setlist),
        # 'sort': sort,
        # 'country': Country.objects.all()[0],
        # 'form': form,
        # 'feed_list':setlist,
        # 'useractions': useractions,
        # 'MP': MP,
    }
    # context = {**reps, **context}
    return render_view(request, context)

def citizenry_view(request, region):
    style = request.GET.get('style', 'index')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    context = {
        'title': 'Citizenry',
        'cards': 'citizenry',
    }
    return render_view(request, context, country=country)

def citizen_debates_view(request, region):
    style = request.GET.get('style', 'index')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    context = {
        'title': 'Citizen Debates',
        'cards': 'citizenry',
    }
    return render_view(request, context, country=country)

def citizen_bills_view(request, region):
    style = request.GET.get('style', 'index')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    context = {
        'title': 'Citizen Bills',
        'cards': 'citizenry',
    }
    return render_view(request, context, country=country)

def polls_view(request, region):
    style = request.GET.get('style', 'index')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    context = {
        'title': 'Polls',
        'cards': 'citizenry',
    }
    return render_view(request, context, country=country)

def petitions_view(request, region):
    style = request.GET.get('style', 'index')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    context = {
        'title': 'Petitions',
        'cards': 'citizenry',
    }
    return render_view(request, context, country=country)

def someta_view(request):
    style = request.GET.get('style', 'index')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, None, user)
    context = {
        'title': 'SoMeta',
        'cards': 'citizenry',
    }
    return render_view(request, context, country=country)

def legislature_view(request, region):
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'recent')
    if sort == 'trending':
        sort_link = '?sort=recent'
        sort_type = '-DateTime'
    else:
        sort_link = '?sort=trending'
        sort_type = '-DateTime'
    view = request.GET.get('view', 'Current')
    page = request.GET.get('page', 1)
    getDate = request.GET.get('date', None)
    date = request.POST.get('date')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # options = {'Chamber: %s' %(Chamber): 'Chamber', 'Page: %s' %(page): '?view=%s&page=' %(view), 'Current': '?view=Current', 'Recommended': '?view=Recommended', 'Trending': '?view=Trending'}
    nav_options = [
        nav_item('button', f'Chamber:{current_chamber}', 'subNavWidget', 'chamberForm'), 
        nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
        nav_item('link', 'Current', '?view=Current', None), 
        nav_item('link', 'Recommended', '?view=Recommended', None), 
        nav_item('link', 'Trending', '?view=Trending', None)]
    form = AgendaForm()
    title = f'{country.Name} Legislature'
    subtitle = ''
    cards = 'home_list'

    if style == 'index' and page == 1:
        context = {
            'title': title,
            'nav_bar': nav_options,
            'view': view,
            'region': region,
            'cards': cards,
            'sort': sort,
            # 'country': country,
        }
        return render_view(request, context, country=country)
    else:
        # exclude_list = ['person', 'party', 'district', 'riding', 'agendaTime', 'hansardItem', 'committeeItem', 'committee', 'agenda', 'vote', 'bill']
        if view == 'Upcoming':
            include_list = ['Bill','Meeting', 'Motion']
            posts = Post.objects.filter(Country_obj=country, DateTime__gte=datetime.datetime.now() - datetime.timedelta(hours=1)).filter(pointerType__in=include_list).exclude(BillVersion__Current=False).order_by('date_time', 'id')
        elif view == 'Current':
            prnt('currret')
            include_list = ['Bill','Meeting', 'Motion']
            if getDate:
                firstDate = datetime.datetime.strptime(getDate, '%Y-%m-%d')
                secondDate = firstDate + datetime.timedelta(days=1)
            else: 
                secondDate = datetime.datetime.now() + datetime.timedelta(hours=1)
                firstDate = secondDate - datetime.timedelta(days=1000)
            
            posts = Post.objects.filter(Country_obj=country, Chamber__in=chambers).filter(DateTime__gte=firstDate, DateTime__lt=secondDate).filter(pointerType__in=include_list).exclude(BillVersion_obj__Current=False).order_by(sort_type, 'id')
            prnt('posts',len(posts))
            # if Chamber == 'All':
            #     # orgs = ['House', 'House of Commons', 'Congress']
            # else:
            #     posts = Post.objects.filter(Country_obj=country, Chamber=Chamber).filter(date_time__gte=firstDate, date_time__lt=secondDate).filter(pointerType__in=include_list).exclude(BillVersion__Current=False).order_by(sort_type, 'id')
            
            # elif Chamber == 'Senate':
            #     posts = Post.objects.filter(Chamber='Senate').filter(date_time__gte=firstDate, date_time__lt=secondDate).filter(pointerType__in=include_list).exclude(BillVersion__Current=False).order_by(sort_type, 'id')
            # elif Chamber == 'All':
            #     orgs = ['Senate', 'House', 'House of Commons', 'Congress', '%s-Assembly'%(provState_name)]
            #     posts = Post.objects.filter(Chamber__in=orgs).filter(date_time__gte=firstDate, date_time__lt=secondDate).filter(pointerType__in=include_list).exclude(BillVersion__Current=False).order_by(sort_type, 'id')
            # elif Chamber == 'Assembly':
            #     posts = Post.objects.filter(Chamber='%s-Assembly'%(provState_name)).filter(date_time__gte=firstDate, date_time__lt=secondDate).filter(pointerType__in=include_list).exclude(BillVersion__Current=False).order_by(sort_type, 'id')        
        elif view == 'Recommended':
            include_list = ['Bill','Meeting']
            posts, view = algorithim(request, include_list, current_chamber, provState, view, page)
        elif view == 'Trending':
            include_list = ['Bill','Meeting']
            # posts, view = algorithim(request, include_list, Chamber, region, view, page)
            posts = getTrendingTop(current_chamber, provState)
            cards = 'top_cards'

        # elif Chamber == 'All':
        #     title = 'Canadian Legislature'
        #     if request.method == 'POST':
        #         date = datetime.datetime.strptime(date, '%Y-%m-%d')
        #         subtitle = date
        #         view = None
        #         posts = Post.objects.exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Q(post_type='agendaTime')|Q(bill__OriginatingChamberName='House of Commons')|Q(hansard_key__Organization='House')|Q(motion__OriginatingChamberName='House')|Q(committeeMeeting__Organization='House')).order_by('date_time')
        #     elif view == 'Upcoming':
        #         posts = Post.objects.exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=datetime.datetime.now()).order_by('date_time')
        #     else:
        #         posts = Post.objects.exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__lte=datetime.datetime.now() + datetime.timedelta(hours=1)).order_by(sort_type)
        # elif Chamber == 'House':
        #     title = 'The House of Commons'
        #     if request.method == 'POST':
        #         date = datetime.datetime.strptime(date, '%Y-%m-%d')
        #         subtitle = date
        #         view = None
        #         posts = Post.objects.filter(organization__icontains='House').exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Q(post_type='agendaTime')|Q(bill__OriginatingChamberName='House of Commons')|Q(hansard_key__Organization='House')|Q(motion__OriginatingChamberName='House')|Q(committeeMeeting__Organization='House')).order_by('date_time')
        #     elif view == 'Upcoming':
        #         posts = Post.objects.filter(organization__icontains='House').exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=datetime.datetime.now()).order_by('date_time')
        #     else:
        #         posts = Post.objects.filter(organization='House').exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__lte=datetime.datetime.now() + datetime.timedelta(hours=1)).order_by(sort_type)
        # elif Chamber == 'Senate':
        #     title = 'Canadian Senate'
        #     if request.method == 'POST':
        #         date = datetime.datetime.strptime(date, '%Y-%m-%d')
        #         subtitle = date
        #         view = None
        #         posts = Post.objects.filter(organization='Senate').exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Q(post_type='agendaTime')|Q(bill__OriginatingChamberName='House of Commons')|Q(hansard_key__Organization='House')|Q(motion__OriginatingChamberName='House')|Q(committeeMeeting__Organization='House')).order_by('date_time')
        #     elif view == 'upcoming':
        #         posts = Post.objects.filter(organization='Senate').exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d-%H:%M')).order_by('date_time')
        #     else:
        #         posts = Post.objects.filter(organization='Senate').exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(hours=1), '%Y-%m-%d-%H:%M')).order_by(sort_type)
        # elif Chamber == 'Assembly':
        #     title = '%s Assembly' %(province.name)
        #     if request.method == 'POST':
        #         date = datetime.datetime.strptime(date, '%Y-%m-%d')
        #         subtitle = date
        #         view = None
        #         posts = Post.objects.filter(organization='%s-Assembly'%(region)).exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Q(post_type='agendaTime')|Q(bill__OriginatingChamberName='House of Commons')|Q(hansard_key__Organization='House')|Q(motion__OriginatingChamberName='House')|Q(committeeMeeting__Organization='House')).order_by('date_time')
        #     elif view == 'upcoming':
        #         posts = Post.objects.filter(organization='%s-Assembly'%(region)).exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d-%H:%M')).order_by('date_time')
        #     else:
        #         posts = Post.objects.filter(organization='%s-Assembly'%(region)).exclude(post_type__in=exclude_list).exclude(billVersion__current=False).filter(date_time__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(hours=1), '%Y-%m-%d-%H:%M')).order_by(sort_type)    
        
        if view != 'Trending' and user:
            userKeys = [k for k, value in Counter(json.loads(user.localities)).most_common()]
        else:
            # if Chamber == 'House':
            #     orgs = ['House', 'House of Commons', 'Congress']
            # elif Chamber == 'Senate':
            #     orgs = ['Senate']
            # elif Chamber == 'All':
            #     orgs = ['Senate', 'House', 'House of Commons', 'Congress', '%s-Assembly'%(provState_name)]
            # elif Chamber == 'Assembly':
            #     orgs = ['%s-Assembly'%(provState_name)]
            # dateQuery = Debate.objects.filter(Chamber__in=orgs).order_by('-PublicationDateTime')[12].PublicationDateTime
            # dt = datetime.datetime.now().replace(tzinfo=pytz.UTC) - dateQuery
            try:
                if current_chamber == 'All':
                    dateQuery = Meeting.objects.filter(meeting_type='Debate', Country_obj=country, Chamber__in=chambers).order_by('-DateTime')[12].DateTime
                else:
                    dateQuery = Meeting.objects.filter(meeting_type='Debate', Country_obj=country, Chamber=current_chamber).order_by('-DateTime')[12].DateTime
                dt = datetime.datetime.now().replace(tzinfo=pytz.UTC) - dateQuery
            except:
                dt = datetime.datetime.now().replace(tzinfo=pytz.UTC) - datetime.datetime.now().replace(tzinfo=pytz.UTC)
            userKeys = get_trending_keys(dt, include_list, chambers)
        setlist = paginate(posts, page, request)
        # my_rep = getMyRepVotes(request, setlist)   
        # useractions = get_useractions(user, setlist)
        daily = None
        if page == 1:
            pass
            # if getDate:
            #     daily = getDaily(request, provState, getDate)
            # else:
            #     daily = getDaily(request, provState, None)
        try:
            isApp = request.COOKIES['fcmDeviceId']
        except:
            isApp = None
        context = {
            'isApp': isApp,
            'title': title,
            'subtitle': subtitle,
            'nav_bar': nav_options,
            'view': view,
            'region': region,
            'dateForm': form,
            'user_keywords': userKeys,
            'dailyCard': daily,
            'cards': cards,
            'sort': sort,
            'filter': current_chamber,
            'feed_list':setlist,
            'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            'myRepVotes': getMyRepVotes(user, setlist),
            # 'country': country,
            # 'xRequestr': request.headers.get('X-Requested-With')
        }
        return render_view(request, context, country=country)
        
# not used
def senate_view(request):
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'recent')
    if sort == 'trending':
        sort_link = '?sort=recent'
        sort_type = '-date_time'
    else:
        sort_link = '?sort=trending'
        sort_type = '-date_time'
    view = request.GET.get('view', 'current')
    page = request.GET.get('page', 1)
    # view = request.GET.get('view', 'past')
    date = request.POST.get('date')
    form = AgendaForm()
    subtitle = ''
    if request.method == 'POST':
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        subtitle = date
        view = None
        posts = Post.objects.filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Q(bill__OriginatingChamberName='Senate')|Q(hansard_key__Organization='Senate')|Q(motion__OriginatingChamberName='Senate')|Q(committeeMeeting__Organization='Senate')).select_related('bill', 'bill__person', 'hansard_key', 'motion','motion__sponsor','committeeMeeting', 'committeeMeeting__committee__chair').order_by('date_time')
    elif view == 'upcoming':
        posts = Post.objects.filter(Q(bill__OriginatingChamberName='Senate')|Q(hansard_key__Organization='Senate')|Q(motion__OriginatingChamberName='Senate')|Q(committeeMeeting__Organization='Senate')).filter(date_time__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d-%H:%M')).select_related('bill', 'bill__person', 'hansard_key', 'motion','motion__sponsor','committeeMeeting', 'committeeMeeting__committee__chair').order_by('date_time')
    else:
        posts = Post.objects.filter(Q(bill__OriginatingChamberName='Senate')|Q(hansard_key__Organization='Senate')|Q(motion__OriginatingChamberName='Senate')|Q(committeeMeeting__Organization='Senate')).filter(date_time__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(hours=1), '%Y-%m-%d-%H:%M')).select_related('bill', 'bill__person', 'hansard_key', 'motion','motion__sponsor','committeeMeeting', 'committeeMeeting__committee__chair').order_by(sort_type)
    title = 'The Senate'
    setlist = paginate(posts, page, request)
    # useractions = get_useractions(request, setlist)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    options = {'Current': '?view=current', 'Upcoming': '?view=upcoming', 'Page: %s' %(page): '?page=', 'Sort: %s' %(sort): sort_link, 'Date': 'date'}
    cards = 'home_list'
    context = {
        'isApp': isApp,
        'title': title,
        'subtitle': subtitle,
        'nav_bar': list(options.items()),
        'view': view,
        'dateForm': form,
        'cards': cards,
        'sort': sort,
        'feed_list':setlist,
        'useractions': useractions,
        'country': Country.objects.all()[0],
    }
    return render_view(request, context)

def agenda_watch_view(request, region, Chamber, year, month, day, hour, minute):
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', '')
    page = request.GET.get('page', 1)
    view = request.GET.get('view', 'past')
    date = request.POST.get('date')
    form = AgendaForm()
    seconds = '00'
    subtitle = ''
    # user_data, user = get_user_data(request)
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    # Chamber, Chambers = get_Chambers(request, country, provState, municipality)
    # country, provState, county, city = get_regions(region, user_data)
    # posts = Post.objects.filter(hansard_key__Organization='House').select_related('hansard_key').order_by('-hansard_key__Publication_date_time')
    # agenda = Hansard.objects.filter(Organization=organization, Publication_date_time__gte=date, Publication_date_time__lt=date + datetime.timedelta(days=1))[0]
    if request.method == 'POST':
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        subtitle = date
        view = None
        # agenda = Agenda.objects.filter(organization=organization, date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1))[0]
        debate = Debate.objects.filter(Chamber=Chamber, PublicationDateTime__gte=date, PublicationDateTime__lt=date + datetime.timedelta(days=1))[0]
    else:
        subtitle = '%s-%s-%s/%s:%s' %(year, month, day, hour, minute),
        # agenda = Agenda.objects.filter(organization=organization, Publication_date_time__year=year, Publication_date_time__month=month, Publication_date_time__day=day)[0]
        debate = Debate.objects.filter(Chamber=Chamber, PublicationDateTime__year=year, PublicationDateTime__month=month, PublicationDateTime__day=day)[0]
    card = 'watch_video'
    title = '%s Agenda' %(Chamber)
    if Chamber == 'House':
        video_link = 'https://parlvu.parl.gc.ca/Harmony/en/PowerBrowser/PowerBrowserV2/%s%s%s/-1/%s?mediaStartTime=%s%s%s%s%s%s&viewMode=3&globalStreamId=29' %(year,month,day,Debate.Agenda.videoCode,year,month,day,hour,minute,seconds)
    elif Chamber == 'Senate':
        video_link = Debate.Agenda.VideoURL
    posts = Post.objects.filter(Debate_key=debate)
    setlist = paginate(posts, page, request)
    # useractions = get_useractions(user, setlist)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    options = {'Date': 'date'}
    context = {
        'isApp': isApp,
        'title': title, 
        'subtitle': subtitle,
        'nav_bar': list(options.items()),
        'view': view,
        'dateForm': form,
        'cards': card,
        'video_link': video_link,
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        # 'myRepVotes': getMyRepVotes(user, setlist),
    }
    return render_view(request, context, country=country)

def agendas_view(request, region, Chamber):
    prnt('agenda_view')
    cards = 'agenda_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'time')
    page = request.GET.get('page', 1)
    view = request.GET.get('view', 'past')
    date = request.POST.get('date')
    search = request.POST.get('post_type')
    dateform = AgendaForm()
    searchform = SearchForm()
    subtitle = ''
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city, chamber=Chamber)
    if request.method == 'POST':
        if date:
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            subtitle = date
            view = None
            posts = Post.objects.filter(Country_obj=country, Agenda__Chamber__in=Chambers, date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(pointerType='Agenda').order_by('-date_time')
            # if Chamber == 'All':
            # else:
            #     posts = Post.objects.filter(Country_obj=country, Agenda__Chamber=Chamber, date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).order_by('-date_time')
        elif search:
            subtitle = search
            view = None
            agendaItems = AgendaItem.objects.filter(text__icontains=search)
            search_list = []
            for i in agendaItems:
                search_list.append(i.agendaTime)
            posts = Post.objects.filter(AgendaTime__in=search_list).select_related('AgendaTime').order_by('-date_time')
    else:
        posts = Post.objects.filter(pointerType='Agenda', Agenda__Chamber__in=Chambers).select_related('Agenda').order_by('-date_time')
        # if Chamber == 'All':
        # # elif Chamber == 'Senate':
        # #     posts = Post.objects.filter(pointerType='Agenda', Agenda__Chamber='Senate').select_related('Agenda').order_by('-date_time')
        # else:
        #     posts = Post.objects.filter(pointerType='Agenda', Agenda__Chamber=Chamber).select_related('Agenda').order_by('-date_time')
    if Chamber == 'All':
        title = 'Agendas'
        h = '/House-agendas'
        s = '/Senate-agendas'
    elif Chamber == 'House':
        title = '%s Agendas' %(Chamber)
        h = '/agendas'
        s = '/Senate-agendas'
    elif Chamber == 'Senate':
        title = '%s Agendas' %(Chamber)
        h = '/House-agendas'
        s = '/agendas'
    setlist = paginate(posts, page, request)
    # useractions = get_useractions(user, setlist) 
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None   
    # options = {'House':h, 'Senate':s,'Page: %s' %(page): '?page=', 'Search':'search', 'Date': 'date'}
    nav_options = [
        nav_item('link', 'House', h, None), 
        nav_item('link', 'Senate', s, None), 
        nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
        nav_item('button', 'Search', 'subNavWidget', 'searchForm'), 
        nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
    context = {
        'isApp': isApp,
        'title': title,
        'subtitle': subtitle,
        'nav_bar': nav_options,
        'view': view,
        'filter': Chamber,
        'dateForm': dateform,
        'searchForm': searchform,
        'cards': cards,
        'sort': sort,
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
    }
    return render_view(request, context, country=country)

def bill_view(request, region, chamber, govNumber, session, numcode):
    prnt()
    prnt('bill_view')
    # cards = 'bill_view'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'new')
    view = request.GET.get('view', 'Overview')
    page = request.GET.get('page', 1)
    reading = request.GET.get('reading', '')
    getSpren = request.GET.get('getSpren', '')
    topicList = []
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # govs = get_gov(country, gov_levels, govNumber, session)
    if view == 'LatestText':
        reading = 'LatestText'
    if sort == 'old':
        changeSort = 'new'
        ordering = 'DateTime'
        order2 = 'id'
    else:
        changeSort = 'old'
        ordering = '-DateTime'
        order2 = '-id'
    billPost = Post.objects.filter(Bill_obj__NumberCode=numcode, Bill_obj__Government_obj__GovernmentNumber=govNumber, Bill_obj__Government_obj__SessionNumber=session).first()
    if not billPost:
        billPost = Archive.objects.filter(Bill_obj__NumberCode=numcode, Bill_obj__Government_obj__GovernmentNumber=govNumber, Bill_obj__Government_obj__SessionNumber=session).first()
    # prnt()

    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    if style == 'index':
        nav_options = [nav_item('link', 'Overview', '%s?view=Overview' %(billPost.Bill_obj.get_absolute_url()), None), 
                    nav_item('link', 'Text', '%s?view=Text' %(billPost.Bill_obj.get_absolute_url()), None), 
                    
                    #    nav_item('button', 'Sort: %s' %(sort), 'subNavWidget', 'sortForm'), 
                    nav_item('link', 'Debates', '%s?view=Debates' %(billPost.Bill_obj.get_absolute_url()), None), 
                    nav_item('link', 'Motions', '%s?view=Motions' %(billPost.Bill_obj.get_absolute_url()), None),
                    nav_item('link', 'Updates', '%s?view=Updates' %(billPost.Bill_obj.get_absolute_url()), None),
                    nav_item('link', 'Work', '%s?view=Work' %(billPost.Bill_obj.get_absolute_url()), None)]
        if view != 'Text':
            nav_options.insert(2, nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'))
    
        context = {
            'isApp': isApp,
            'title': f"{billPost.Bill_obj.Chamber} {billPost.Bill_obj.BillDocumentTypeName}",
            'title_link': billPost.Bill_obj.get_absolute_url(),
            'nav_bar': nav_options,
            'cards': 'bill_view',
            'useractions': get_useractions(request, [billPost]),
            'page': page,
            'sort': sort,
            'view': view,
            'post': billPost,
            # 'person_data': fetch_person_data([billPost]),
            'page':page,
            'style':style,
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)
        }
        return render_view(request, context, country=country)
    else:
        updatedVersion = None
        if getSpren and user and user.is_superuser:
            prnt('runme')
            # bill.get_bill_keywords()
            billPost.Bill_obj.getSpren(False)
            # import django_rq
            # from rq import Queue
            # from worker import conn
            # queue = django_rq.get_queue('default')
            # queue.enqueue(bill.sprenBot, job_timeout=500)
        # prnt(bill.summarySpren)
        if view.lower() == 'work':
            posts = Post.objects.filter(pointerType='Meeting', Country_obj=country, Update_obj__data__Terms__icontains=billPost.Bill_obj.NumberCode).order_by(ordering)
        elif view.lower() == 'debates':
            # posts = Post.objects.filter(hansard_key__agenda__bills=bill).order_by(ordering)
            # Assuming 'custom_key' is the dynamic part you want to replace 'xxx' with
            # custom_key = '45Soe1f8e577fb0fa70436cba672d063245f'

            # # Build the filter argument dynamically
            # filter_kwargs = {f"Statement_obj__bill_dict__{billPost.Bill_obj.NumberCode}__obj_id": billPost.Bill_obj.id}

            # # Perform the query using the dynamic filter
            # posts = Post.objects.filter(**filter_kwargs)

            posts = Post.objects.filter(**{f"Statement_obj__bill_dict__{billPost.Bill_obj.NumberCode}__obj_id": billPost.Bill_obj.id}).filter(Country_obj=country).order_by(ordering, order2)
            # prnt(posts.count())
            # keys = Keyphrase.objects.filter(Bill_obj=billPost.Bill_obj)
            topicList = [billPost.Bill_obj.NumberCode]
            # for key in keys:
            #     if not key.text in topicList:
            #         topicList.append(key.text)
            # prnt(topicList)
        elif view.lower() == 'motions':
            posts = Post.objects.filter(pointerType='Motion', Country_obj=country, Motion_obj__Bill_obj=billPost.Bill_obj).order_by(ordering)
        elif view.lower() == 'text':
            # updatedVersion = Update.objects.filter(BillVersion_obj__Bill_obj=bill, BillVersion_obj__Version=currentVersion)[0]
            prnt('updatedVersion', updatedVersion)
            posts = {}
            # reading = 'LatestText'
        elif view.lower() == 'updates':
            posts = Post.objects.filter(pointerType='GenericModel', Country_obj=country, GenericModel_obj__pointerId=billPost.Bill_obj.id).order_by(ordering, order2)
        else:
            posts = Post.objects.filter(Q(Motion_obj__Bill_obj=billPost.Bill_obj)|Q(pointerType='Meeting')&Q(Update_obj__data__Terms__icontains=billPost.Bill_obj.NumberCode)).filter(Country_obj=country).order_by(ordering, order2)
            # prnt('postsoverview', posts)
            # posts = []
            topicList = [billPost.Bill_obj.NumberCode]
        prnt("%s Bill" %(billPost.Bill_obj.Chamber))
        # titl = "%s Bill" %(bill.Chamber)
        prnt('posts:',len(posts))
        # prnt('posts',posts)
        if posts:
            setlist = paginate(posts, page, request)
        else:
            setlist = {}
        # prnt('set',setlist)
        useractions = get_useractions(request, setlist) 
        # my_rep = getMyRepVotes(request, setlist)   
        # prnt(my_rep)         
        # r = Interaction.objects.filter(Post_obj=billPost, User_obj=user).first()
        # if r and not r.viewed:
        #     r.viewed = True
        #     r.save()
            # useractions[r.postId] = r
        # except:
        #     try:
        #         r = Interaction(Post_obj=billPost, User_obj=user, viewed=True)
        #         r.save()
        #         useractions[r.postId] = r
        #     except:
        #         pass
        # latest_reading = bill.get_latest_reading 
        # options = {'Overview': '%s?view=Overview' %(bill.get_absolute_url()),  'LatestText': '%s?view=LatestText' %(bill.get_absolute_url()), 'Page: %s' %(page): '?view=%s&page=' %(view), 'Sort: %s' %(sort): '%s?view=%s&sort=%s' %(bill.get_absolute_url(), view, changeSort), 'Debates': '%s?view=Debates' %(bill.get_absolute_url()), 'Motions': '%s?view=Motions' %(bill.get_absolute_url()), 'Work': '%s?view=Work' %(bill.get_absolute_url())}
        

        # if request.user.is_authenticated and request.user.is_god:
        #     # options['update'] = bill.get_update_url()
        #     options['getSpren'] = '%s?getSpren=True' %(bill.get_absolute_url())
        context = {
            'isMobile': get_isMobile(request),
            'isApp': isApp,
            'cards': 'bill_view',
            'sort': sort,
            'view': view,
            'post': billPost,
            'page':page,
            'style':style,
            'feed_list': setlist,
            'useractions': useractions,
            # 'updates': get_updates(setlist),
            # 'myRepVotes': getMyRepVotes(user, setlist),
            # 'reading': reading,  
            'topicList': topicList,   
            # 'country': Country.objects.all()[0],   
        }
        return render_view(request, context, country=country)
    
def bills_view(request, region):
    prnt('bills_view')
    # cards = 'bills_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'Latest')
    page = request.GET.get('page', 1)
    hasText = request.GET.get('hasText', None)
    getDate = request.GET.get('date', None)
    date = request.GET.get('date', None)
    search = request.GET.get('search', None)
    subtitle = ''
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)

    if sort == 'Latest':
        ordering = '-DateTime'
    elif sort == 'Newest':
        ordering = '-Bill_obj__created'
    else:
        ordering = '-DateTime'
    prnt('or2',ordering)

    if not hasText:
        # if request.user.is_authenticated:
        hasText = request.GET.get('billsHaveText', None)
        if not hasText:
            try:
                hasText = request.session['billsHaveText']
            except Exception as e:
                hasText = 'True'
        # else:
        #     hasText = 'True'
    # if request.user.is_authenticated:
    try:
        request.session.setdefault('billsHaveText', hasText)
        request.session['billsHaveText'] = hasText
    except:
        pass
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    if style == 'index':
        if current_chamber.lower() == 'all':
            title = "Government Bills"
        else:
            title = '%s Bills' %(current_chamber.replace('-', ' '))

        # if request.method == 'POST':
        if date:
            hasText = 'Either'
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            subtitle = 'date %s' %(date)
        elif search:
            hasText = 'Either'
            subtitle = 'search %s' %(search)
        nav_options = [nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'),
                    nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm', fields=['Latest','For You','Trending','Newest'], key='sort'),  
                    nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
                    nav_item('button', 'HasText: %s'%(hasText), 'subNavWidget', 'hasTextForm', fields=['True','False','Either'], key='hasText'),  
                    #    nav_item('link', 'Recommended', '?view=Recommended', None), 
                    #    nav_item('link', 'Trending', '?view=Trending', None),
                        nav_item('button', 'Search', 'subNavWidget', 'searchForm'), 
                        nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
    
        context = {
            'isApp': isApp,
            'title': title,
            'subtitle': subtitle,
            'nav_bar': nav_options,
            'view': sort,
            # 'region': region,
            'dateForm': DateForm(),
            'searchForm': SearchForm(),
            'cards': 'bills_list',
            'sort': sort,
            'page':page,
            'style':style,
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)
        }
        return render_view(request, context, country=country)
    else:
        # if request.method == 'POST':
        if date:
            hasText = 'Either'
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            subtitle = date
            view = None
            posts = Post.objects.filter(pointerType='Bill', DateTime__gte=date, DateTime__lt=date + datetime.timedelta(days=1)).filter(Country_obj=country, Bill_obj__Chamber__in=chambers).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
            # if posts.count() == 0:
            #     posts = Archive.objects.filter(pointerType='Bill', date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1), validated=True).filter(Country_obj=country, Bill_obj__Chamber__in=chambers).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
            if current_chamber.lower() == 'all':
                title = "Government Bills"
            else:
                title = '%s Bills' %(current_chamber.replace('-', ' '))
                # posts = Post.objects.filter(pointerType='Bill', date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Country_obj=country, Bill_obj__Chamber=Chamber).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-date_time', 'id')
                # if posts.count() == 0:
                #     posts = Archive.objects.filter(pointerType='Bill', date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).filter(Country_obj=country, Bill_obj__Chamber=Chamber).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-date_time', 'id')
                    
        elif search:
            hasText = 'Either'
            prnt('search',search)
            subtitle = search
            view = None
            posts = Post.objects.filter(pointerType='Bill').filter(Country_obj=country, Bill_obj__Chamber__in=chambers).filter(Q(Bill_obj__amendedNumberCode__icontains=search)|Q(Bill_obj__NumberCode__icontains=search)|Q(Bill_obj__Title__icontains=search)|Q(Bill_obj__ShortTitle__icontains=search)).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
            # prnt('ps',posts)
            # if posts.count() == 0:
            #     posts = Archive.objects.filter(pointerType='Bill', validated=True).filter(Country_obj=country, Bill_obj__Chamber__in=chambers).filter(Q(Bill_obj__amendedNumberCode__icontains=search)|Q(Bill_obj__NumberCode__icontains=search)|Q(Bill_obj__Title__icontains=search)|Q(Bill_obj__ShortTitle__icontains=search)).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
        else:

            if sort == 'For You':
                include_list = ['bill']
                posts, view = algorithim(user, include_list, all_chambers, country, provState, 'Recommended', page)
            elif sort == 'Trending':
                include_list = ['bill']
                posts, view = algorithim(user, include_list, all_chambers, country, provState, 'Trending', page)
            else:
                if getDate:
                    firstDate = datetime.datetime.strptime(getDate, '%Y-%m-%d')
                    secondDate = firstDate + datetime.timedelta(days=1)
                else: 
                    secondDate = datetime.datetime.now() + datetime.timedelta(hours=1)
                    firstDate = secondDate - datetime.timedelta(days=1000)

                if hasText.lower() == 'true':
                    posts = Post.objects.filter(pointerType='Bill', Region_obj=country, filters__Chamber__in=chambers).filter(filters__contains={'has_text': True}).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                    # posts = Post.objects.filter(pointerType='Bill', Update_obj__data__icontains='"has_text": true').filter(Country_obj=country, Bill_obj__Chamber__in=chambers, validated=True).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                elif hasText.lower() == 'false':
                    posts = Post.objects.filter(pointerType='Bill', Region_obj=country, filters__Chamber__in=chambers).exclude(filters__contains={'has_text': True}).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                    # posts = Post.objects.filter(pointerType='Bill', Update_obj__data__contains={'has_text': F}).filter(Country_obj=country, Bill_obj__Chamber__in=chambers).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                    # posts = Post.objects.filter(pointerType='Bill').exclude(Update_obj__data__icontains='"has_text": true').filter(Country_obj=country, Bill_obj__Chamber__in=chambers, validated=True).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                else:
                    prnt('else')
                    posts = Post.objects.filter(pointerType='Bill').filter(Region_obj=country, filters__Chamber__in=chambers).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                # if posts.count() == 0:
                #     posts = Archive.objects.filter(pointerType='Bill').filter(Country_obj=country, Bill_obj__Chamber__in=chambers, validated=True).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-DateTime')
                if current_chamber.lower() == 'all':
                    title = "Government Bills"
                else:
                    title = '%s Bills' %(current_chamber.replace('-', ' '))
                    # posts = Post.objects.filter(pointerType='Bill').filter(Country_obj=country, Bill_obj__Chamber=Chamber).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-date_time', 'id')
                    # if posts.count() == 0:
                    #     posts = Archive.objects.filter(pointerType='Bill').filter(Country_obj=country, Bill_obj__Chamber=Chamber).select_related('Bill_obj', 'Bill_obj__Person_obj').order_by(ordering, '-date_time', 'id')
                        

                # prnt('len',posts.count())
                # prnt(posts[0].Bill_obj)

        setlist = paginate(posts, page, request)
        context = {
            'isApp': isApp,
            'view': sort,
            'cards': 'bills_list',
            'sort': sort,
            'feed_list':setlist,
            # 'person_data': fetch_person_data(setlist),
            'useractions': get_useractions(user, setlist),
            'page':page,
            'style':style,
            'isMobile': get_isMobile(request)
        }
        return render_view(request, context, country=country)
    
def elections_view(request, region):
    # prnt('elections view')
    title = "Upcoming Elections"
    # cards = 'elections_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', '')
    if request.user.is_authenticated:
        view = request.GET.get('view', 'My Elections')
    else:
        view = request.GET.get('view', 'All Elections')
    page = request.GET.get('page', 1)
    # province, region = get_region(request)
    # # Chamber = get_Chamber(request)
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city, chamber=None)

    # if style == 'index':
    #     page = 1
    if user and view == 'My Elections':
        posts = Post.objects.filter(pointerType='Election').filter(Election_obj__end_date__gte=datetime.datetime.now()-datetime.timedelta(days=30)).exclude(Election_obj__District_obj=None).filter(Q(Election_obj__District_obj=user.Federal_District_obj)|Q(Election_obj__District_obj=user.ProvState_District_obj)|Q(Election_obj__District_obj=user.Greater_Municipal_District_obj)|Q(Election_obj__District_obj=user.Municipal_District_obj)).order_by('DateTime')
        
        # if request.user.Federal_District_obj and request.user.ProvState_District_obj:
        #     posts = Post.objects.filter(post_type='election').filter(election__end_date__gte=datetime.datetime.now()-datetime.timedelta(days=30)).filter(Q(election__riding=request.user.riding)|Q(election__district=request.user.district)).order_by('date_time')
        # elif request.user.riding:
        #     posts = Post.objects.filter(post_type='election').filter(election__end_date__gte=datetime.datetime.now()-datetime.timedelta(days=30)).filter(election__riding=request.user.riding).order_by('date_time')
        # elif request.user.district:
        #     posts = Post.objects.filter(post_type='election').filter(election__end_date__gte=datetime.datetime.now()-datetime.timedelta(days=30)).filter(election__district=request.user.district).order_by('date_time')
        # else:
        #     posts = []
    elif view == 'My Elections':
        posts = []
    else:
        posts = []

        # if province:
        #     posts = Post.objects.filter(post_type='election').filter(election__end_date__gte=datetime.datetime.now()-datetime.timedelta(days=30)).filter(Q(election__level='Federal')|Q(election__province=province)).order_by('date_time')
        # else:
        #     posts = Post.objects.filter(post_type='election').filter(election__end_date__gte=datetime.datetime.now()-datetime.timedelta(days=30)).filter(election__level='Federal').order_by('date_time')
    
    # posts = Post.objects.filter(post_type='election').filter(Q(election__level='Federal')|Q(election__province=province)).order_by('date_time')
    # prnt(posts)
    if user:
        # options = {'My Elections': '?view=My Elections', 'All Elections': '?view=All Elections'}
        nav_options = [nav_item('link', 'My Elections', '?view=My Elections', None),
                       nav_item('link', 'All Elections', '?view=All Elections', None)]
    else:  
        # options = {'All Elections': '?view=All Elections'}
        nav_options = [nav_item('link', 'All Elections', '?view=All Elections', None)]


    setlist = paginate(posts, page, request) 
    # setlist = posts
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    context = {
        'isApp': isApp,
        'title': title,
        'view': view,
        'nav_bar': nav_options,
        'cards': 'elections_list',
        'sort': sort,
        'feed_list':setlist,
        # 'updates': get_updates(setlist),
        # 'country': Country.objects.all()[0],
    }
    return render_view(request, context, country=country)
        
def candidates_view(request, organization, region, iden):
    prnt('candidates view')
    cards = 'candidates_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', '')
    view = request.GET.get('view', '')
    page = request.GET.get('page', 1)
    # province, region = get_region(request)
    # Chamber = get_Chamber(request)
    election = Election.objects.filter(id=iden)[0]
    candidates = Role.objects.filter(election=election).order_by('?')
    if election.riding:
        title = "%s %s %s" %(election.province.name, election.riding.name, election.type)
    elif election.district:
        title = "%s %s %s" %(election.province.name, election.district.name, election.type)
    else:
        title = "%s %s %s" %(election.province.name, election.level, election.type)
    setlist = paginate(candidates, page, request)    
    # agenda, agendaItems = get_agenda()
    context = {
        'title': title,
        'view': view,
        # 'subtitle': '44th Parliament of Canada',
        # "agenda":agenda,
        # "agendaItems":agendaItems,
        'cards': cards,
        'sort': sort,
        'feed_list':setlist,
        'country': Country.objects.all()[0],
    }
    return render_view(request, context)
    
def house_or_senate_hansards_view(request, region):
    prnt('house/senate hansard view')
    
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'time')
    page = request.GET.get('page', 1)
    view = request.GET.get('view', 'Current')
    date = request.POST.get('date')
    form = AgendaForm()
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # prnt(get_trending(request, country, provState, county, city, current_chamber, all_chambers))
    if current_chamber == 'All':
        title = '%s Debates' %('All')
    else:   
        title = '%s Debates' %(current_chamber)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    if style == 'index' and page == 1:
        nav_options = [nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'),
                nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
                nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
        context = {
            'isApp': isApp,
            'title': title,
            'subtitle': '',
            'nav_bar': nav_options,
            'view': view,
            # 'region': region,
            'dateForm': form,
            'cards': 'debates_list',
            'sort': sort,
            'gov_levels': gov_levels,
            'style':style,
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)


            # fix all_chambers in get getTrending


        }
        return render_view(request, context, country=country)
    else:
        subtitle = ''
        if request.method == 'POST':
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            subtitle = date
            view = None
            posts = Post.objects.filter(Country_obj=country, Meeting_obj__meeting_type='Debate', Meeting_obj__DateTime__gte=date, Meeting_obj__DateTime__lt=date + datetime.timedelta(days=1)).filter(Meeting_obj__Chamber__in=Chambers).select_related('Meeting_obj').order_by('-Meeting_obj__DateTime','Meeting_obj__Title')

        else:
            if view == 'Current':
                # posts = Post.objects.filter(Country_obj=country, Meeting_obj__meeting_type__iexact='Debate', DateTime__lte=now_utc() + datetime.timedelta(hours=12)).filter(Meeting_obj__Chamber__in=Chambers).select_related('Meeting_obj').order_by('-Meeting_obj__DateTime')
                posts = Post.objects.filter(Country_obj=country, Meeting_obj__meeting_type__iexact='Debate').filter(Meeting_obj__Chamber__in=chambers).select_related('Meeting_obj').order_by('-Meeting_obj__DateTime','Meeting_obj__Title')
                # prnt('posts', posts)
                # for p in posts:
                #     prnt(p)
                #     prnt(p.DateTime)
            elif view == 'Recommended':
                include_list = ['Statement']
                posts, view = algorithim(user, include_list, current_chamber, country, provState.Name, view, page)
                # posts, view = algorithim(request, include_list, Chamber, region, view, page)
            elif view == 'Trending':
                include_list = ['Meeting']
                posts, view = algorithim(user, include_list, current_chamber, country, provState.Name, view, page)
                # posts, view = algorithim(request, include_list, Chamber, region, view, page)
        
        
        if view != 'Trending' and user and user.UserData_obj:
            userKeys = [k for k, value in Counter(user.UserData_obj.get_interests()).most_common()]
        else:
            try:
                dateQuery = Meeting.objects.filter(Country_obj=country, meeting_type='Debate', Chamber__in=chambers).order_by('-DateTime')[12].DateTime
            except:
                dateQuery = now_utc()
            dt = now_utc().replace(tzinfo=pytz.UTC) - dateQuery
            userKeys = get_trending_keys(dt, ['Meeting'], chambers)
        setlist = paginate(posts, page, request)
        # useractions = get_useractions(request, setlist)
        context = {
            'isApp': isApp,
            'title': title,
            'subtitle': subtitle,
            # 'nav_bar': nav_options,
            'view': view,
            # 'region': region,
            'dateForm': form,
            'cards': 'debates_list',
            'sort': sort,
            'feed_list':setlist,      
            'style':style, 
            'user_keywords': userKeys,
            'useractions': get_useractions(user, setlist),
            'isMobile': request.user_agent.is_mobile,
            # 'updates': get_updates(setlist),
        }
        return render_view(request, context, country=country)

def debate_view(request, region, chamber, govNumber, session, iden, year, month, day, hour, minute):
    prnt(' hansard _view')
    govNumber = re.sub("[^0-9]", "", govNumber)
    session = re.sub("[^0-9]", "", session)
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'Earliest')
    page = request.GET.get('page', 1)
    speaker_id = request.GET.get('speaker', '')
    speaker_name = request.GET.get('speakerName', '')
    topic = request.GET.get('topic', '')
    business = request.GET.get('business', '')
    view = request.GET.get('view', '')
    id = request.GET.get('id', '')
    time = request.GET.get('time', '')
    # prnt('t1', time)
    instruction = None
    userData = None
    # ordering = get_sort_order(sort)
    if sort == 'Earliest':
        ordering = 'Statement_obj__order'
    else:
        ordering = '-Statement_obj__order'
    prnt('ordering', ordering)
    # cards = 'debate_view'
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    # chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city, chamber=chamber)
    # govs = get_gov(country, gov_levels, govNumber, session)
    sprenPost = None
    # # preview card
    # iden = 12167831
    # time = '03:00pm'
    video_link = None
    # prnt('region', region)
    # prnt('Chamber', Chamber)
    # prnt('govNumber', govNumber)
    # prnt('session', session)
    prnt('topic', topic)
    # m = Meeting.objects.filter(id=iden)[0]
    if '_' in iden or len(iden) < 33:
        p = Post.objects.filter(Meeting_obj__Title__iexact=iden.replace('_',' ')).first()
    else:
        p = Post.objects.filter(Meeting_obj__id=iden).first()
    m = p.Meeting_obj
    meetingUpdate = p.Update_obj
    title = f'{current_chamber} {m.meeting_type} {str(m.Title)}'
    # prnt(m.__dict__)
    # prnt('meetingUpdate', json.loads(meetingUpdate.data)['Terms'])
    prnt('----------')
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    if style == 'index':
        if topic:
            searchField = topic
        elif business:
            searchField = business.replace('_',' ')
        elif speaker_name:
            searchField = speaker_name.replace('_',' ')
        elif speaker_id:
            if len(speaker_id) > 33:
                person = Person.objects.filter(id=speaker_id).first()
            else:
                person = Person.objects.filter(GovIden=speaker_id).first()
            if person:
                searchField = person.get_field('FullName')
            else:
                searchField = None
        elif time:
            searchField = time
        else:
            searchField = None
        subtitle = str(short_gov(m.Government_obj.gov_type)) + ' ' + str(m.Government_obj.GovernmentNumber) + '/' + str(m.Government_obj.SessionNumber)
        if not time and m.hide_time != 'hour':
            time = request.GET.get('time', m.DateTime.strftime("%I:%M%p"))
            subtitle2 = '%s %s' %(datetime.datetime.strftime(m.DateTime, '%B %-d, %Y'), time)
        else:
            subtitle2 = '%s' %(datetime.datetime.strftime(m.DateTime, '%B %-d, %Y'))
        nav_options = [ 
                nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
                nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm', fields=['Earliest', 'Latest', 'Loudest'], key='sort'),
                nav_item('link', 'Transcript', m.GovPage, None, new_tab=True)]
        if topic:
            if user and topic in user.get_follow_topics():
                f = 'following'
            else:
                f = 'follow'
            # options = {'Page: %s'%(page): '?page=', 'Sort: %s' %(sort):sort, 'follow':'%s?topic=%s&follow=%s' %(h.get_absolute_url(), topic, f), 'Transcript': h.GovPage}
            nav_options = [ 
                nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
                nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm', fields=['Earliest', 'Latest'], key='sort'), 
                nav_item('link', 'follow', '%s?topic=%s&follow=%s' %(m.get_absolute_url(), topic, f), None), 
                nav_item('link', 'Transcript', m.GovPage, None, new_tab=True),]
        context = {
            'isApp': isApp,
            'title': title,
            'subtitle': subtitle,
            'subtitle2': subtitle2,  
            'title_link': m.get_absolute_url(),      
            'nav_bar': nav_options,
            'cards': 'debate_view',
            'view': view,
            'sort': sort,
            'page':page,
            'search_field': searchField,
            # 'country': Country.objects.all()[0],
            # 'sortOptions': ['Oldest','Newest','Loudest','Random'],
            'topic': topic,
            # 'id': id,
            'time': time,
            'speaker_id': speaker_id,
            # 'feed_list':setlist,
            # 'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            'debate': m,
            'debateUpdate': meetingUpdate,
            # 'sprenPost': sprenPost,
            # 'video_link': video_link,
            # 'hasContext': hasContext,
            # 'wordCloud': wordCloud,
            'topicList': [topic],
            # 'userData':userData,
            # 'instruction':instruction,
            'style':style,
            # 'sidebarData': get_trending(request, country, provState, county, city, current_chamber)
        }
        return render_view(request, context, country=country)
    else:

        # ttt = 'C-360, An Act to establish a national strategy to reduce the amount of wasted food in Canada'
        # # Keyphrase.objects.filter(text=trend.text, Country_obj=self.Country_obj, DateTime__gte=sevenDays, DateTime__lte=self.DateTime)
        # kxs = Keyphrase.objects.filter(text=ttt)
        # prnt('kxs', kxs)
        # kk = kxs[0]
        # kk.set_trend()
        # prnt(kk.KeyphraseTrend_obj)
        # prnt('done set trend')
        # if Chamber == 'All':
        #     h = Meeting.objects.filter(Chamber__in=Chambers, Government_obj=gov, pub_iden=iden)[0]
        #     title = '%s %s' %(Chamber, str(h.Title))
        # else:
        #     h = Meeting.objects.filter(Chamber=Chamber, Government_obj=gov, pub_iden=iden)[0]
        #     title = '%s %s' %(Chamber, str(h.Title))
            
        # else:
        #     h = Hansard.objects.filter(ParliamentNumber=parliament, SessionNumber=session, id=iden)[0]
        #     title = '%s %s' %(str(h.Organization.replace('-',' ')), str(h.Title))
        if m.Region_obj.timezone:
            tz = m.Region_obj.timezone
        else:
            tz = 'US/Eastern'
        hasContext = True
        # prnt('topic',topic)
        if topic or speaker_id:
            hasContext = False
            # if speaker_id:
            #     speaker = Person.objects.filter(id=speaker_id).first()
        elif page == 1 and sort.lower() == 'oldest':
            seconds = '00'
            try:
                videoUrl = json.loads(meetingUpdate.data)['VideoUrl']
            except:
                agendaUpdate = Post.objects.filter(Agenda_obj=m.Agenda_obj).first().Update_obj
                if agendaUpdate:
                    videoUrl = json.loads(agendaUpdate.data)['VideoUrl']
                else:
                    videoUrl = None
            if videoUrl:
                if current_chamber == 'House' and country.Name == 'Canada':
                    date = '%s-%s-%s' %(m.DateTime.year, m.DateTime.month, m.DateTime.day)
                    dt = datetime.datetime.strptime(date + '/' + time, '%Y-%m-%d/%I:%M%p')
                    # doesn't work on mac, needs leading zero
                    video_link = 'https://parlvu.parl.gc.ca/Harmony/en/PowerBrowser/PowerBrowserV2/%s%s%s/-1/%s?mediaStartTime=%s%s%s%s%s%s&viewMode=3&globalStreamId=29' %(dt.year,dt.month,dt.day,videoUrl,dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second)
                    # # preview video
                    # video_link = 'https://parlvu.parl.gc.ca/Harmony/en/PowerBrowser/PowerBrowserV2/20221214/-1/38300?mediaStartTime=20221214150123&viewMode=3&globalStreamId=29'
                elif current_chamber == 'Senate' and country.Name == 'Canada':
                    video_link = videoUrl
        follow = request.GET.get('follow', '')
        if follow and topic and request.user.is_authenticated:
            prnt('gogo')
            fList = request.user.get_follow_topics()
            if topic in fList:
                # fList.remove(topic)
                # response = 'Unfollow "%s"' %(topic)
                # user = set_keywords(request.user, 'remove', topic)
                instruction = 'follow_topics remove "%s"' %(topic)
            elif topic not in fList:
                # fList.append(topic)
                # response = 'Following "%s"' %(topic)
                # user = set_keywords(request.user, 'add', topic)
                instruction = 'follow_topics add "%s"' %(topic)
            # user.set_follow_topics(fList)
            # request.user.save()
            # userData = get_user_signing_data(user)
            return render(request, "utils/dummy.html", {"result": 'success', 'userData': get_user_sending_data(user), 'instruction':instruction})
        wordCloud = None
        if topic:
            prnt(topic)
            # if user:
            #     # user = set_keywords(user, 'add', topic)
            #     userData = get_user_sending_data(user)

            #     instruction = 'keyword_array add "%s"' %(topic)
        
            hasContext = False
            search = [f'{topic}']
            prnt('searxh', search)
            if speaker_id:
                if len(speaker_id) > 33:
                    posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Statement_obj__Person_obj__id=speaker_id).filter(Q(Statement_obj__Terms_array__overlap=search)|Q(Statement_obj__keyword_array__overlap=search)).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering,'-DateTime')
                else:
                    posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Statement_obj__Person_obj__GovIden=speaker_id).filter(Q(Statement_obj__Terms_array__overlap=search)|Q(Statement_obj__keyword_array__overlap=search)).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering,'-DateTime')
                # if posts.count() == 0:
                #     posts = Post.objects.filter(hansardItem__person=speaker, hansardItem__keywords__overlap=search, hansardItem__hansard=h).select_related('hansardItem__person', 'hansardItem').order_by(ordering,'-date_time')
            else:
                # s = Statement.objects.all().first()
                # prnt('h', h)
                # posts = Post.objects.filter(Statement_obj__Meeting_obj=h)
                posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Q(Statement_obj__SubjectOfBusiness__icontains=topic)|Q(Statement_obj__Terms_array__overlap=search)|Q(Statement_obj__keyword_array__overlap=search)).order_by(ordering,'-DateTime')
                # prnt('posts1', posts)
                # if posts.count() == 0:
                #     posts = Post.objects.filter(hansardItem__keywords__overlap=search, hansardItem__hansard=h).select_related('hansardItem__person', 'hansardItem').order_by(ordering,'-date_time')
            # from posts.utils import summarize_topic, get_token_count
            # prnt('pstss',posts[0].keyword_array)
            spren = None
            # spren = Spren.objects.filter(Meeting_obj=m, topic=topic).exclude(content='TBD').first()
            if spren:
                sprenPost = spren.get_post()
        elif business:
            hasContext = False
            if '___' in business:
                a = business.find('___')
                business = business[:a]
            x = business.replace('_',' ').replace('...','')
            # x = 'SENATE CONCURRENT RESOLUTION 41--SETTING FORTH THE CONGRESSIONAL BUDGET FOR THE UNITED STATES GOVERNMENT FOR FISCAL YEAR 2025 AND SETTING FORTH '
            # x = 'SENATE CONCURRENT RESOLUTION 41--SETTING FORTH THE CONGRESSIONAL BUDGET '
            # prnt('x',x)
            posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Q(Statement_obj__OrderOfBusiness__icontains=x.strip())|Q(Statement_obj__SubjectOfBusiness__icontains=x.strip())).order_by(ordering,'-DateTime')

        elif speaker_id:
            if len(speaker_id) > 33:
                posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Statement_obj__Person_obj__id=speaker_id).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering,'-DateTime')
            else:
                posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Statement_obj__Person_obj__GovIden=speaker_id).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering,'-DateTime')
        elif speaker_name:
            speaker_name = speaker_name.replace('_',' ')
            posts = Post.objects.filter(Statement_obj__Meeting_obj=m).filter(Statement_obj__PersonName__iexact=speaker_name).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering,'-DateTime')
        
        elif time:
            prnt('time', time)
            if time == None:
                prnt('eys')
            else:
                prnt('no')
            date_time = '%s/%s/%s/%s' %(m.DateTime.year, m.DateTime.month, m.DateTime.day, time)
            prnt(date_time)
            dt = datetime.datetime.strptime(date_time, '%Y/%m/%d/%I:%M%p')
            posts = Post.objects.filter(Statement_obj__Meeting_obj=m, Statement_obj__DateTime__gte=dt).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering,'-DateTime')
        else:
            prnt('eeeee')
            # hasContext = False
            posts = Post.objects.filter(Statement_obj__Meeting_obj=m).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by(ordering, 'Statement_obj__created')
        if id:
            setlist = paginate(posts, 'id=%s' %(id), request)
            # prnt('s',setlist)
            hasContext = setlist[0].Statement_obj.order
            id = int(id)
            video_link = None
        else:
            setlist = paginate(posts, page, request)
            # if not topic and not speaker_id:
            #     if page != 1 or time:
            #         try:
            #             hasContext = setlist[0].Statement_obj.order
            #             id = int(hasContext)
            #         except:
            #             pass
        prnt('len',len(posts))
        # useractions = get_useractions(request, setlist)
        try:
            isApp = request.COOKIES['fcmDeviceId']
        except:
            isApp = None
        context = {
            'isApp': isApp,
            # 'title': title,
            # 'subtitle': subtitle,
            # 'subtitle2': subtitle2,  
            # 'title_link': m.get_absolute_url(),      
            # 'nav_bar': nav_options,
            'cards': 'debate_view',
            'view': view,
            'sort': sort,
            'page': page,
            'style': style,
            # 'country': Country.objects.all()[0],
            # 'sortOptions': ['Oldest','Newest','Loudest','Random'],
            'topic': topic,
            'id': id,
            'time': time,
            'speaker_id': speaker_id,
            'feed_list':setlist,
            'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            'debate': m,
            'debateUpdate': meetingUpdate,
            'sprenPost': sprenPost,
            'video_link': video_link,
            'hasContext': hasContext,
            'wordCloud': wordCloud,
            'topicList': [topic],
            # 'userData':userData,
            # 'instruction':instruction
        }
        return render_view(request, context, country=country)


def motions_view(request, region, type):
    prnt('house/senate motions view')
    # cards = 'motions_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'Time')
    page = request.GET.get('page', 1)
    view = request.GET.get('view', 'past')
    getDate = request.GET.get('date', None)
    date = request.POST.get('date')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    if sort.lower() == 'time':
        sort_option = '-DateTime'
    elif sort.lower() == 'number':
        sort_option = '-Motion_obj__VoteNumber'
    else:
        sort_option = '-DateTime'
    # subtitle = ''
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    if style == 'index':
        if current_chamber.lower() == 'all':
            title = type[0].upper() + type[1:] + 's'
        else:
            title = current_chamber + ' ' + type[0].upper() + type[1:] + 's'
        nav_options = [nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'), 
            nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
            nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm', fields=['Time', 'Number', 'Passed', 'Failed'], key='sort'), 
            # nav_item('button', 'Search', 'subNavWidget("searchForm")'), 
            nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
        context = {
            'isApp': isApp,
            'title': title,
            'nav_bar': nav_options,
            'view': view,
            'dateForm': AgendaForm(),
            'cards': 'motions_list',
            'sort': sort,
            'page':page,
            # 'myRepVotes': getMyRepVotes(user, setlist),
            'style':style,
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)
        }
        return render_view(request, context, country=country)
    else:

        if request.method == 'POST':
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            subtitle = date
            view = None
            posts = Post.objects.filter(pointerType='Motion', Country_obj=country, Chamber__in=chambers).filter(DateTime__gte=date, DateTime__lt=date + datetime.timedelta(days=1)).select_related('Motion_obj').order_by('-DateTime')
            if current_chamber.lower() == 'all':
                title = type[0].upper() + type[1:] + 's'
            else:
                title = current_chamber + ' ' + type[0].upper() + type[1:] + 's'
            # if Chamber == 'Senate':
            #     # posts = Post.objects.filter(motion__OriginatingChamberName='Senate').filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).select_related('motion').order_by('-date_time')
            #     title = 'Senate Motions'
            # elif Chamber == 'House':    
            #     posts = Post.objects.filter(motion__OriginatingChamberName='House').filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).select_related('motion').order_by('-date_time')
            #     title = 'House of Commons Motions'
            # elif Chamber == 'All':
            #     posts = Post.objects.filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1)).select_related('motion').order_by('-date_time')
            #     title = 'House and Senate Motions'
        # elif view == 'upcoming':
        #     posts = Post.objects.filter(committeeMeeting__date_time_start__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')).exclude(committeeMeeting=None).exclude(committeeMeeting__Organization='House').order_by('-committeeMeeting__date_time_start')
        else:
            # prnt('motion else')
            if getDate:
                # prnt('getdate')
                firstDate = datetime.datetime.strptime(getDate, '%Y-%m-%d')
                secondDate = firstDate + datetime.timedelta(days=1)
            else: 
                secondDate = now_utc() + datetime.timedelta(hours=1)
                firstDate = secondDate - datetime.timedelta(days=1000)
            # posts = Post.objects.filter(Country_obj=country, pointerType='Motion')
            # posts = Post.objects.filter(Country_obj=country, pointerType='Motion', Chamber__in=Chambers).filter(DateTime__gte=firstDate, DateTime__lt=secondDate).select_related('Motion_obj').order_by('-DateTime')
            prnt('Chambers', chambers)
            prnt('country', country)
            # posts = Post.objects.filter(Country_obj=country, pointerType='Motion', Chamber__in=chambers).order_by(sort_option, '-DateTime')
            posts = Post.objects.filter(Country_obj=country, pointerType='Motion', filters__Chamber__in=chambers).order_by(sort_option, '-DateTime', 'Motion_obj__VoteNumber')
            # prnt('posts',posts)
            # if Chamber == 'Senate':
            #     posts = Post.objects.filter(motion__OriginatingChamberName='Senate').filter(date_time__gte=firstDate, date_time__lt=secondDate).select_related('motion').order_by('-date_time')
            #     title = 'Senate Motions'
            # elif Chamber == 'House':    
            #     posts = Post.objects.filter(motion__OriginatingChamberName='House').filter(date_time__gte=firstDate, date_time__lt=secondDate).select_related('motion').order_by('-date_time')
            #     title = 'House of Commons Motions'
            # elif Chamber == 'All':
            #     posts = Post.objects.exclude(motion=None).filter(date_time__gte=firstDate, date_time__lt=secondDate).select_related('motion').order_by('-date_time')
            #     title = 'House and Senate Motions'
            # elif 'Assembly' in Chamber:
            #     title = 'Assembly Motions'
            #     posts = Post.objects.filter(motion__OriginatingChamberName=region+'-Assembly').filter(date_time__gte=firstDate, date_time__lt=secondDate).select_related('motion').order_by('-date_time', '-id')
        
        if sort.lower() == 'passed':
            posts = posts.filter(Motion_obj__Yeas__gt=F('Motion_obj__Nays'))
        elif sort.lower() == 'failed':
            posts = posts.filter(Motion_obj__Nays__gt=F('Motion_obj__Yeas'))
        # if party != 'All':
        #     votes = votes.filter(CaucusName__iexact=party)
        # if vote != 'All':
        #     votes = votes.filter(VoteValue__iexact=vote)
        # if sort != 'All':
        #     votes = votes.filter(PersonFullName__istartswith=sort)
        # if subRegion != 'All':
        #     votes = votes.filter(ConstituencyProvStateName__icontains=subRegion)
        # if not subtitle:
        #     latest = posts[0]
        #     subtitle = str(latest.motion.ParliamentNumber) + 'th Parliament, ' + str(latest.hansard_key.SessionNumber) + 'st Session'
        setlist = paginate(posts, page, request)
        # useractions = get_useractions(request, setlist)
        # my_rep = getMyRepVotes(request, setlist)   
        # prnt(my_rep)         
        context = {
            'isApp': isApp,
            # 'title': title,
            # 'subtitle': subtitle,
            # 'nav_bar': nav_options,
            'view': view,
            # 'region': region,
            # 'dateForm': form,
            'cards': 'motions_list',
            'page':page,
            'sort': sort,
            'style':style,
            'feed_list':setlist,
            'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            'myRepVotes': getMyRepVotes(user, setlist),
        }
        return render_view(request, context, country=country)


def motion_view(request, region, chamber, govNumber, session, number, type):
    prnt('vote motion view')
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'All')
    page = request.GET.get('page', 1)
    party = request.GET.get('party', 'All')
    view = request.GET.get('view', '')
    subRegion = request.GET.get('subRegion', 'All')
    # prnt(party)
    vote = request.GET.get('vote', 'All')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city, chamber=chamber)
    
    # govs = get_gov(country, gov_levels, govNumber, session)
    motion = Motion.objects.filter(Chamber__iexact=current_chamber, Government_obj__GovernmentNumber=govNumber, Government_obj__SessionNumber=session, VoteNumber=number).first()
    motionPost = Post.objects.filter(pointerId=motion.id).first()
    # prnt('motions',motions)
    # motion = motions[0]
    if type == 'rollcall':
        type = 'Roll Call'
    else:
        type = type[0].upper() + type[1:]
    title = '%s %s No. %s' %(motion.Chamber.replace('-', ' '), type, motion.VoteNumber)
    # cards = 'vote_list'

    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    if style == 'index':
        nav_options = [
            # nav_item('button', f'Chamber:{Chamber}', 'subNavWidget("chamberForm")'), 
                nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
                nav_item('button', 'Party: %s' %(party), 'subNavWidget', 'partyForm', fields=[p['Name'] for p in motion.return_parties()], key='party'), 
                nav_item('button', 'Vote: %s' %(vote), 'subNavWidget', 'voteForm', fields=['All'] + [v['Vote'] for v in motion.return_votes()], key='vote'),
                nav_item('button', 'Name: %s'%(sort), 'subNavWidget', 'sortForm', fields=['All'] + list(string.ascii_uppercase), key='sort'),
                nav_item('button', 'Region: %s' %(subRegion), 'modalPopPointer', f'"Regions", "/subregions_modal/{country.Name}/{country.nameType}/{motion.get_absolute_url()}"')
                ]
        context = {


            'isApp': isApp,
            'title': title,
            'title_link': motion.get_absolute_url(),
            'view': view,
            'nav_bar': nav_options,
            'cards': 'vote_list',
            'sort': sort,
            'page':page,
            'motion': motion,
            'motionPost': motionPost,
            # 'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            # 'myRepVotes': getMyRepVotes(user, setlist),
            'myRepVotes': {},
            'style':style,
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)
        }
        return render_view(request, context, country=country)
    else:


        votes = Post.objects.filter(Vote_obj__Motion_obj=motion)
        # votes = Vote.objects.filter(Motion_obj=motion)
        # prnt(votes)
        # selected = set()
        # vote_options = [v.VoteValue for v in votes if v.VoteValue not in selected and not selected.add(v.VoteValue)]
        if party != 'All':
            votes = votes.filter(Vote_obj__CaucusName__iexact=party)
        if vote != 'All':
            votes = votes.filter(Vote_obj__VoteValue__iexact=vote)
        if sort != 'All':
            votes = votes.filter(Vote_obj__PersonFullName__istartswith=sort)
        if subRegion != 'All':
            votes = votes.filter(Vote_obj__ConstituencyProvStateName__icontains=subRegion)
        # prnt(motion.partys)
        setlist = paginate(votes, page, request)
        # setlist = votes
        try:
            isApp = request.COOKIES['fcmDeviceId']
        except:
            isApp = None
        # my_rep = getMyRepVotes(request, motions)      
        # prnt(my_rep)      
        # if setlist.paginator.num_pages < int(page):
        #     page = str(setlist.paginator.num_pages)
        # options = {'Page: %s'%(page): '?sort=%s&party=%s&vote=%s&page=' %(sort, party, vote), 'Party: %s' %(party):'?page=%s&sort=%s&vote=%s&party=' %(page, sort, vote), 'Vote: %s' %(vote): '?page=%s&sort=%s&party=%s&vote=' %(page, sort, party)}
        
        context = {
            'isApp': isApp,
            # 'title': title,
            # 'title_link': motion.get_absolute_url(),
            'view': view,
            # 'nav_bar': nav_options,
            'cards': 'vote_list',
            'sort': sort,
            'page':page,
            'feed_list':setlist,
            'motion': motion,
            # 'useractions': get_useractions(user, setlist),
            # 'updates': get_updates(setlist),
            # 'myRepVotes': getMyRepVotes(user, setlist),
            # 'myRepVotes': {},
            # 'partyOptions': motion.party_array,
            # 'sortOptions': ['All'] + list(string.ascii_uppercase),
            # 'voteOptions': vote_options
            'style':style,
        }
        prnt('next')
        return render_view(request, context, country=country)

# not used
def house_motion_view(request, govNumber, session, number):
    prnt('latest house motion view')
    # h = Hansard.objects.get(Parliament=parliament, Session=session, pub_iden=iden)
    # title = None
    # subtitle = str(motion.ParliamentNumber) + 'th Parliament, ' + str(motion.SessionNumber) + 'st Session'
    # subtitle2 = datetime.datetime.strftime(h.Publication_date_time, '%B %-d, %Y')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, None, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    govs = get_gov(country, gov_levels, govNumber, session)

    motion = Motion.objects.filter(Government_obj__in=govs, Chamber=Chamber, VoteNumber=number)[0]
    title = 'House Motion No. %s' %(motion.VoteNumber)

    cards = 'vote_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'alphabetical')
    view = request.GET.get('view', '')
    page = request.GET.get('page', 1)
    votes = Vote.objects.filter(Motion_obj=motion)
    setlist = paginate(votes, page, request)
    # useractions = get_useractions(user, setlist)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    # agenda, agendaItems = get_agenda()
    # options = {'Page: %s'%(page): page, 'Sort: %s'%(sort): sort, 'Party: All':'previous', 'Vote: All': 'all'}
    nav_options = [
            nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
            nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm'),  
            nav_item('button', 'Party: All', 'subNavWidget', 'partyForm'), 
            nav_item('button', 'Vote: All', 'subNavWidget', 'voteForm' )]
    # options = {'Roles':'%s?view=Roles'%(person.get_absolute_url()), 'Vote History':'%s?view=Vote History'%(person.get_absolute_url())}
    context = {
        'isApp': isApp,
        'title': title,
        'view': view,
        # 'subtitle': subtitle,
        # 'subtitle2': subtitle2,  
        # "agenda":agenda,
        # "agendaItems":agendaItems,      
        'nav_bar': nav_options,
        'cards': cards,
        'sort': sort,
        # 'country': Country.objects.all()[0],
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        'm': motion,
    }
    return render_view(request, context, country=country)
# not used
def senate_motion_view(request, govNumber, session, number):
    prnt('senate motion view')
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, None, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    govs = get_gov(country, gov_levels, govNumber, session)

    # h = Hansard.objects.get(Parliament=parliament, Session=session, pub_iden=iden)
    motion = Motion.objects.filter(Government_obj__in=govs, Chamber__in=Chambers, VoteNumber=number)[0]
    title = 'Senate Motion No. %s' %(motion.VoteNumber)
    # subtitle = str(motion.ParliamentNumber) + 'th Parliament, ' + str(motion.SessionNumber) + 'st Session'
    # subtitle2 = datetime.datetime.strftime(h.Publication_date_time, '%B %-d, %Y')
    cards = 'vote_list'
    style = request.GET.get('style', 'index')
    view = request.GET.get('view', '')
    sort = request.GET.get('sort', 'alphabetical')
    page = request.GET.get('page', 1)
    votes = Vote.objects.filter(motion=motion).order_by('person__last_name')
    setlist = paginate(votes, page, request)
    # useractions = get_useractions(user, setlist)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    # agenda, agendaItems = get_agenda()
    # options = {'Page: %s'%(page): page, 'Sort: %s'%(sort): sort, 'Party: All':'previous', 'Vote: All': 'all'}
    nav_options = [
            nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'),
            nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm'),  
            nav_item('button', 'Party: All', 'subNavWidget', 'partyForm'), 
            nav_item('button', 'Vote: All', 'subNavWidget', 'voteForm' )]
    # options = {'Roles':'%s?view=Roles'%(person.get_absolute_url()), 'Vote History':'%s?view=Vote History'%(person.get_absolute_url())}
    context = {
        'isApp': isApp,
        'title': title,
        'view': view,
        # 'subtitle': subtitle,
        # 'subtitle2': subtitle2, 
        # "agenda":agenda,
        # "agendaItems":agendaItems,       
        'nav_bar': nav_options,
        'cards': cards,
        'sort': sort,
        # 'country': Country.objects.all()[0],
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        'm': motion,
    }
    return render_view(request, context, country=country)

    
def latest_committees_view(request, region, Chamber):
    prnt('latest committees view')
    title = 'Latest Committee Events' 
    # subtitle = str(latest.ParliamentNumber) + 'th Parliament, ' + str(latest.SessionNumber) + 'st Session'
    # subtitle2 = datetime.datetime.strftime(latest.date_time_start, '%B %-d, %Y')
    cards = 'committeeMeeting_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'time')
    page = request.GET.get('page', 1)
    view = request.GET.get('view', 'Current')
    # filter = request.GET.get('filter', 'all')
    date = request.POST.get('date')
    form = AgendaForm()
    subtitle = ''
    # Chamber = get_Chamber(request)
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    govs = get_gov(country, gov_levels)

    # options = {'Chamber: %s' %(Chamber): 'Chamber', 'Current': '?view=Current', 'Upcoming': '?view=Upcoming', 'Date': 'date'}
    nav_options = [
            nav_item('button', f'Chamber:{Chamber}', 'subNavWidget', 'chamberForm'), 
            # nav_item('link', 'Page: %s' %(page), '?view=%s&page=' %(view)), 
            # nav_item('button', 'Sort: %s'%(sort), 'subNavWidget("sortForm")'), 
            nav_item('link', 'Current', '?view=Current', None), 
            nav_item('link', 'Upcoming', '?view=Upcoming', None),
            # nav_item('button', 'Search', 'subNavWidget("searchForm")'), 
            nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
    # parl = Parliament.objects.filter(organization='Federal').first()
    committeeList = Committee.objects.exclude(Chamber__in=Chamber).filter(Government_obj__in=govs).order_by('Title')
    # if Chamber == 'House':
    #     committeeList = Committee.objects.exclude(Chamber__in=Chamber).filter(Government_obj__in=govs).order_by('Title')
    # elif Chamber == 'Senate':
    #     committeeList = Committee.objects.exclude(Organization='House').filter(ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber).order_by('Title')
    # else:
    #     # prnt('else')
    #     committeeList = Committee.objects.filter(ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber).order_by('Title')
    if request.method == 'POST':
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        subtitle = date
        title = 'House Committees'
        view = None
        posts = Post.objects.filter(Meeting_obj__meeting_type='Commitee', Meeting_obj__date_time_start__gte=date, Meeting_obj__date_time_start__lt=date + datetime.timedelta(days=1)).exclude(Meeting_obj=None).order_by('-date_time')
    elif view == 'Upcoming':
        posts = Post.objects.filter(Meeting_obj__meeting_type='Commitee', Meeting_obj__date_time_start__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')).exclude(Meeting_obj=None).order_by('-date_time')
        if Chamber.lower() == 'all':
            title = 'Upcoming Committee Events'
        else:
            title = f'Upcoming {Chamber} Committee Events'

        # posts = Post.objects.filter(committeeMeeting__date_time_start__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')).exclude(committeeMeeting=None).exclude(committeeMeeting__Organization='Senate').order_by('-date_time')
        # if Chamber == 'Senate':
        #     title = 'Upcoming Senate Committee Events' 
        #     # posts = Post.objects.filter(committeeMeeting__date_time_start__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')).exclude(committeeMeeting=None).exclude(committeeMeeting__Organization='House').order_by('date_time')
        # elif Chamber == 'House':
        #     title = 'Upcoming House Committee Events' 
        #     posts = Post.objects.filter(committeeMeeting__date_time_start__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')).exclude(committeeMeeting=None).exclude(committeeMeeting__Organization='Senate').order_by('date_time')
        # else:
        #     title = 'Upcoming Committee Events' 
        #     posts = Post.objects.filter(committeeMeeting__date_time_start__gte=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')).exclude(committeeMeeting=None).order_by('date_time')
    else:
        posts = Post.objects.filter(Meeting_obj__meeting_type='Commitee', Meeting_obj__Chamber__in=Chambers, Meeting_obj__date_time_start__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), '%Y-%m-%d')).exclude(Meeting_obj=None).order_by('-date_time')
        if Chamber.lower() == 'all':
            title = 'Latest Committee Events'
        else:
            title = f'Latest {Chamber} Committee Events'

        # if Chamber == 'Senate':
        #     title = 'Latest Senate Committee Events' 
        #     posts = Post.objects.filter(committeeMeeting__date_time_start__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), '%Y-%m-%d')).exclude(committeeMeeting=None).exclude(committeeMeeting__Organization='House').order_by('-date_time')
        # elif Chamber == 'House':
        #     title = 'Latest House Committee Events' 
        #     posts = Post.objects.filter(committeeMeeting__date_time_start__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), '%Y-%m-%d')).exclude(committeeMeeting=None).exclude(committeeMeeting__Organization='Senate').order_by('-date_time')
        # else:
        #     title = 'Latest Committee Events' 
        #     posts = Post.objects.filter(committeeMeeting__date_time_start__lte=datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), '%Y-%m-%d')).exclude(committeeMeeting=None).order_by('-date_time')
    if not request.method == 'POST':
        setlist = paginate(posts, page, request)
    else:
        setlist = posts
    # useractions = get_useractions(user, setlist)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    context = {
        'isApp': isApp,
        'title': title,
        'subtitle': subtitle,
        'nav_bar': nav_options,
        'view': view,
        'dateForm': form,
        'cards': cards,
        'sort': sort,
        # 'country': Country.objects.all()[0],
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        'committeeList': committeeList,
    }
    return render_view(request, context, country=country)

def committee_view(request, organization, govNumber, session, iden):
    prnt('latest committee view')
    # organization = None
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, None, user)

    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    govs = get_gov(country, gov_levels, govNumber, session)
    c = Meeting.objects.filter(id=iden, meeting_type='Committee', Government_obj__in=govs, Chamber__in=chambers).select_related('Committee_obj', 'Committee_obj__Chair_obj')[0]
    if 'Subcommittee' in c.Committee_obj.Title:
        title = 'Senate Committee'
    else:
        title = f'{Chamber} Committee'
    # if organization == 'senate':
    #     c = CommitteeMeeting.objects.exclude(committee__Organization='House').filter(ParliamentNumber=parliament, SessionNumber=session, id=iden).select_related('Committee_obj', 'Committee_obj__Chair_obj')[0]
        
    # else:
    #     c = CommitteeMeeting.objects.exclude(committee__Organization='Senate').filter(ParliamentNumber=parliament, SessionNumber=session, id=iden).select_related('committee', 'committee__chair__person')[0]
    #     title = 'House Committee'
    subtitle = str(get_ordinal(c.Government_obj__GovernmentNumber)) + ' Num. ' + str(get_ordinal(c.Government_obj__SessionNumber)) + ' Sess.'
    subtitle2 = datetime.datetime.strftime(c.date_time_start, '%B %-d, %Y')
    cards = 'committeeMeeting_view'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'time')
    view = request.GET.get('view', '')
    page = request.GET.get('page', 1)
    speaker_id = request.GET.get('speaker', '')
    topic = request.GET.get('topic', '')
    iden = request.GET.get('id', '')
    hasContext = True
    if topic:
        title = topic
        hasContext = False
    elif speaker_id:
        speaker = Person.objects.filter(id=speaker_id)[0]
        title = speaker.get_name()
        hasContext = False
    follow = request.GET.get('follow', '')
    if follow and topic:
        fList = user.get_follow_topics()
        if topic in fList:
            fList.remove(topic)
        elif topic not in fList:
            fList.append(topic)
        user.set_follow_topics(fList)
        user.save()
        # prnt(request.user.get_follow_topics())
        return render(request, "utils/dummy.html", {"result": 'Success'}, country=country)
    # prnt(request.user.get_follow_topics())
    if speaker_id:
        # prnt(speaker)
        # hansards = HansardItem.objects.filter(person=speaker, hansard=h).select_related('person')
        posts = Post.objects.filter(Statement_obj__Person_obj=speaker, Statement_obj__Meeting_obj=c).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by('Statement_obj__DateTime', 'created')
    elif topic:
        # hansards = HansardItem.objects.filter(Terms__icontains=term, hansard=h).select_related('person')
        posts = Post.objects.filter(Statement_obj__Terms_array__icontains=topic, Statement_obj__Meeting_obj=c).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by('Statement_obj__DateTime', 'created')
        # posts = Post.objects.filter(committeeItem__Terms__icontains=topic, committeeItem__committeeMeeting=c).select_related('committeeItem__person', 'committeeItem').order_by('committeeItem__Item_date_time', 'created')
    else:
        # hansards = HansardItem.objects.filter(hansard=h).select_related('person')
        posts = Post.objects.filter(Statement_obj__Meeting_obj=c).select_related('Statement_obj__Person_obj', 'Statement_obj').order_by('Statement_obj__DateTime', 'created')
        # posts = Post.objects.filter(committeeItem__committeeMeeting=c).select_related('committeeItem__person', 'committeeItem').order_by('committeeItem__Item_date_time', 'created')
        # prnt('found posts')
    # prnt(posts[0])
    if iden:
        # prnt('iden:',iden)
        setlist = paginate(posts, 'id=%s' %(iden), request)
        hasContext = setlist[0].Statement_obj.id
        iden = int(iden)
    else:
        setlist = paginate(posts, page, request)
        if page != 1:
            hasContext = setlist[0].Statement_obj.id
    # setlist = paginate(posts, page, request)
    # useractions = get_useractions(user, setlist)
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None
    # options = {'Page: %s'%(page): page, 'Sort: %s'%(sort): sort}
    nav_options = [
            nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'),
            nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm'), ]
    if topic:
        if user and topic in user.get_follow_topics():
            f = 'following'
        else:
            f = 'follow'
        follow_link = '%s?topic=%s&follow=%s' %(c.get_absolute_url(), topic, f)
        nav_options.append(nav_item('button', 'follow', f'react("follow2", "{follow_link}")'))
    # if request.user.is_god:
    #     options['reprocess'] = '/utils/reprocess%s' %(c.get_absolute_url())

 # options = {'Roles':'%s?view=Roles'%(person.get_absolute_url()), 'Vote History':'%s?view=Vote History'%(person.get_absolute_url())}
    context = {
        'isApp': isApp,
        'title': title,
        'title_link': c.get_absolute_url(),
        'subtitle': subtitle,
        'subtitle2': subtitle2,        
        'nav_bar': nav_options,
        'view': view,
        'cards': cards,
        'sort': sort,
        'topic': topic,
        'id': iden,
        'hasContext': hasContext,
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        'committee': c,
        'topicList': [topic],
        # 'country': Country.objects.all()[0],
    }
    return render_view(request, context, country=country)


def officials_list(request, region):
    prnt('rep_list')
    # cards = 'rep_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'All')
    page = request.GET.get('page', 1)
    subRegion = request.GET.get('subRegion', 'All')
    search = request.POST.get('post_type')
    view = request.GET.get('view', 'Current')    
    searchform = SearchForm()
    user_data, user = get_user_data(request)
    country, provState, county, city = get_regions(request, region, user)
    chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    govs = get_gov(country, gov_levels)
    prnt('gov', govs)
    # gov = govs[0]
    filter = ''
    prnt('Chamber', chambers, current_chamber)
    if style == 'index':
        nav_options = [
            nav_item('button', f'Chamber: {current_chamber}', 'subNavWidget', 'chamberForm', fields=['All'] + all_chambers, key='chamber'), 
                nav_item('button', 'Region: %s' %(subRegion), f'modalPopPointer', f'"Regions", "/subregions_modal/{country.Name}/{country.nameType}/officials"'),
                nav_item('button', 'Name: %s'%(sort), 'subNavWidget', 'sortForm', fields=['All'] + list(string.ascii_uppercase), key='sort'),
                nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'), 
                nav_item('button', 'Search', 'subNavWidget', 'searchForm'),
                ]
        context = {
            'title': 'Legislative Officials',
            'title_link': f'/{country.Name}/officials',
            'cards': 'rep_list',
            'sort': sort,
            'view': view,
            'region': region,
            'style':style,
            'page':page,
            # 'filter': filter,
            'searchForm': searchform,
            'nav_bar': nav_options,
            # 'feed_list':setlist,
            # 'includedUpdates': {},
            'sidebarData': get_trending(request, country, provState, county, city, current_chamber, all_chambers)
        }
        return render_view(request, context, country=country)
    else:
        positions = country.Office_array
        prnt('pos',positions)
        prnt('pos',positions)
        if not positions:
            posts = []
        elif subRegion == 'All':
            posts = Post.objects.filter(pointerType='Person', Region_obj=country, filters__Chamber__in=chambers).filter(Q(**{'Update_obj__data__Position__in': positions})).order_by('Update_obj__data__LastName')
            # role_query = Q()
            # for position in positions:
            #     role_query |= Q(**{f"extra__roles__{position}__current": True})

            # # Combine the two queries with AND condition
            # updates = Update.objects.filter(query & role_query)
        else:
        #     # prnt(subRegion)
            subR = Region.valid_objects.filter(ParentRegion_obj=country, Name=subRegion).first()
            posts = Post.objects.filter(pointerType='Person', Region_obj=country, Update_obj__data__ProvState_id=subR.id, Chamber__in=chambers).filter(Q(**{'Update_obj__data__Position__in': positions})).order_by('Update_obj__data__LastName')
        #     posts = Post.objects.filter(Country_obj=country, Role_obj__ProvState_obj=subR, Update_obj__data__contains={'Current': True}, Role_obj__Position__in=positions, Chamber__in=chambers).order_by('Role_obj__Person_obj__LastName')
        #     # data__roles__contains=[{'Senator': {'current': True}}]
        prnt('len',len(posts))
        if sort != 'All':
            posts = posts.filter(Update_obj__data__LastName__startswith=sort)
        setlist = paginate(posts, page, request)
        extra_data = fetch_updated_objs(setlist, ['Party', 'District', 'ProvState'])
        context = {
            # 'title': 'Legislative Officials',
            # 'title_link': f'/{country.Name}/officials',
            'cards': 'rep_list',
            'sort': sort,
            'view': view,
            'region': region,
            'page':page,
            # 'filter': filter,
            # 'searchForm': searchform,
            # 'nav_bar': nav_options,
            'feed_list':setlist,
            'extra_data':extra_data,
            'style':style,
            # 'includedUpdates': {},
        }
        return render_view(request, context, country=country)


def representative_view(request, region, name, iden):
    # start1 = datetime.datetime.now()
    prnt('representative_view')
    # cards = 'representative_view'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'new')
    if sort == 'old':
        ordering = 'DateTime'
        newSort = 'new'
    else:
        ordering = '-DateTime'
        newSort = 'old'
    page = request.GET.get('page', 1)
    view = request.GET.get('view', '')
    topic = request.GET.get('topic', '')
    follow = request.GET.get('follow', '')
    if follow and not request.user.is_authenticated:
        return render(request, "utils/dummy.html", {'result':'Please Login'})
    
    country = Region.valid_objects.filter(Name=region, nameType='Country').first()
    prnt('country',country)
    prnt('iden',iden)
    if is_id(iden):
        personPost = Post.objects.filter(pointerType='Person', Person_obj__id=iden, Country_obj=country).first()
    else:
        personPost = Post.objects.filter(pointerType='Person', Person_obj__GovIden=iden, Country_obj=country).first()
    # personUpdate = Update.objects.filter(Person_obj__id=iden).order_by('-created')[0]
    # person = personUpdate.Person_obj
    title = personPost.Person_obj.Position
    person = personPost.Person_obj
    prnt('person',person)
    user_data, user = get_user_data(request)
    # country = person.Country_obj
    country, provState, county, city = get_regions(request, country, user)
    # chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # govs = get_gov(country, gov_levels)
    if follow and follow != 'following' and follow != 'follow':
        fList = request.user.get_follow_topics()
        topic = follow
        if topic in fList:
            fList.remove(topic)
            response = 'Unfollow "%s"' %(topic)
            user = set_keywords(request.user, 'remove', topic)
        elif topic not in fList:
            fList.append(topic)
            response = 'Following "%s"' %(topic)
            user = set_keywords(request.user, 'add', topic)
        request.user.set_follow_topics(fList)
        request.user.save()
        return render(request, "utils/dummy.html", {"result": response})
    elif follow and follow == 'following' or follow and person in request.user.follow_Person_objs.all():
        request.user.follow_Person_objs.remove(person)
        request.user.save()
        return render(request, "utils/dummy.html", {'result':'Unfollow %s' %(person.FullName)})
    elif follow and follow == 'follow' or follow and person not in request.user.follow_Person_objs.all():
        request.user.follow_Person_objs.add(person)
        request.user.save()
        return render(request, "utils/dummy.html", {'result':'Following %s' %(person.FullName)})
    
    # if person.parliamentary_position:
    #     title = person.parliamentary_position  
    #     # prnt(title)
    #     if person.parliamentary_position == 'Member of Provincial Parliament':
    #         organization = person.province_name
    #         # prnt(organization)
    #         # organization = 'Ontario'
    #     else:
    #         organization = 'Federal'
    # else:
    #     organization = 'Federal'


    # updates = Update.objects.filter(pointerType='Role', Person_obj=person).distinct('Role_obj__created').order_by('-Role_obj__created', '-StartDate', '-EndDate')


    # if organization == 'Federal':
    #     r = Role.objects.filter(person=person, current=True).filter(Q(position='Member of Parliament')|Q(position='Senator'))[0]
    #     prnt(r)
    # else:
    #     r = Role.objects.filter(person=person, position='MPP', current=True)[0]
    prnt('person.Position',person.Position)
    rolePost = Post.objects.filter(pointerType='Role', Role_obj__Person_obj=person, Role_obj__Position=person.Position, Update_obj__data__contains={'Current': True}).first()
    # rolePost = Post.objects.filter(pointerType='Role', Role_obj__Person_obj=person, Role_obj__Position=person.Position, Update_obj__data__contains={'Current': True}).first()
    # role = Role.objects.filter(Person_obj=person, Position=person.Position)
    # r = Update.objects.filter(pointerType='Role', Role_obj__Position=person.Position, data__contains={'Current': True}).order_by('-created').first()
    # if request.user.is_authenticated and person in request.user.follow_Person_objs.all():
    #     follow = 'following'
    # else:
    #     follow = 'follow'
    # prnt(r)

    # u = Update.objects.filter(pointerId=rolePost.Role_obj.id)
    # prnt('u',u)
    follow = 'follow'
    # prnt('rolePost',convert_to_dict(rolePost))
    # prnt('rolePost1',convert_to_dict(rolePost.Role_obj))
    # prnt('rolePost2',convert_to_dict(rolePost.Update_obj))
    # if request.user.is_authenticated:
    #     try:
    #         match = Reaction.objects.filter(user=request.user, person=person).exclude(match=None)[0]
    #     except:
    #         match = Reaction(user=request.user, person=person)
    #     if not match.match or match.updated < datetime.datetime.now().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=7):
    #         match_percentage, total_matches, vote_matches, my_votes, return_votes = get_matches(request, person, organization)
    #         match.match = match_percentage
    #         match.save()
    #     if match.match:
    #         match = str(match.match) + '%'
    #     else:
    #         match = 'None'
    # else:
    #     match = 'Login'
    # terms = Keyphrase.objects.filter(hansardItem__person=person)[:500]
    if style == 'index':
        nav_options = [
                nav_item('link', 'Match: %s' %('match'), '%s?view=Match'%(person.get_absolute_url()), None), 
                nav_item('link', 'Votes', '%s?view=Votes'%(person.get_absolute_url()), None), 
                nav_item('link', 'Debates', '%s?view=Debates'%(person.get_absolute_url()), None), 
                nav_item('link', 'Sponsorships', '%s?view=Sponsorships'%(person.get_absolute_url()), None), 
                nav_item('link', 'Roles', '%s?view=Roles'%(person.get_absolute_url()), None), 
                ]
        if topic:
            # nav_options['follow'] = '%s' %(topic)
            nav_options.append(nav_item('link', 'Sort: %s' %(sort), '%s?topic=%s&sort=%s' %(person.get_absolute_url(), topic, newSort), None)) 
            # ['Sort: %s' %(sort)] = '%s?topic=%s&sort=%s' %(person.get_absolute_url(), topic, newSort)
        elif view == 'Debates':
            # nav_options['follow'] = '?follow=%s' %(follow)
            # nav_options['Sort: %s' %(sort)] = '%s?view=Debates&sort=%s' %(person.get_absolute_url(), newSort)
            nav_options.append(nav_item('link', 'Sort: %s' %(sort), '%s?view=Debates&sort=%s' %(person.get_absolute_url(), newSort), None)) 
        context = {
            'title': title,
            'nav_bar': nav_options,
            # 'updatedPerson': {},
            'view': view,
            'cards': 'representative_view',
            'sort': sort,
            # 'personTerms': termsList,
            'personPost': person,
            'rolePost': rolePost,
            # 'cards': cards,
            # 'sort': sort,
            # 'view': view,
            'page': page,
            'style':style,
            # 'filter': f,
            # 'nav_bar': list(options.items()),
            # 'feed_list':setlist,
            # 'mp': person,
            # 'updatedRole': r,
            # 'reactions': reactions,
            # 'match': match_percentage,
            # 'voteMatches': vote_matches,
            # 'totalMatches': total_matches,
            # 'myVotes': my_votes,
            # 'r' : Role.objects.filter(position="Member of Parliament", person=person)[0],
            # 'wordCloud': wordCloud,
            'topicList': [topic],
        }
        prnt('rendersend')
        return render_view(request, context, country=country)
    else:
        prnt('feed')
        items = Statement.objects.filter(Person_obj=person).order_by('-DateTime')[:200]
        termsDic = {}
        for item in items:
            # item = p.hansardItem
            if item.Terms_array:
                for t in item.Terms_array:
                    if t not in skipwords:
                        if t in termsDic:
                            termsDic[t] += 1
                        else:
                            termsDic[t] = 1
            if item.keyword_array:
                loweredTerms = []
                if item.Terms_array:
                    loweredTerms = [x.lower() for x in item.Terms_array]  
                for t in item.keyword_array:
                    if t not in skipwords and t not in loweredTerms:
                        if t in termsDic:
                            termsDic[t] += 1
                        else:
                            termsDic[t] = 1
        termsList = sorted(termsDic.items(), key=operator.itemgetter(1),reverse=True)
        # context = {
        #     'title': title,
        #     'nav_bar': list(options.items()),
        #     'person': person,
        #     'view': view,
        #     'cards': cards,
        #     'sort': sort,
        #     'personTerms': termsList
        # }
        #     return render_view(request, context)
        # else:
            # categories = []
            # for r in roles:
            #     if r.position not in categories:
                    # categories.append(r.position = [])
                # categories[r.position] += r
            # for c in categories:
            # prnt('organization', organization)
        wordCloud = ''
        my_votes = {}
        vote_matches = 0
        total_matches = 0
        match_percentage = None
        # if view == 'Match' or view == '':
        #     if request.user.is_authenticated:
        #         match_percentage, total_matches, vote_matches, my_votes, return_votes = get_matches(request, person, govs)
        #         posts = return_votes
        #         match = Interaction.objects.filter(User_obj=user, User_obj=person).exclude(match=None).first()
        #         if match:
        #             match.match = match_percentage
        #             match.save()
        #         else:
        #             match = None
        #             prnt('fai11l')
        #             view = 'Votes'
        #     else:
        #         posts = ['Please login and start voting to see how you match']
        #         match_percentage = None
        if view == 'Roles':
            # posts = Update.objects.filter(pointerType='Role', Role_obj__Person_obj=person).distinct('Role_obj__created').order_by('-Role_obj__created', '-Role_obj__StartDate')
            # posts = Role.objects.filter(person=person).select_related('person').order_by('-end_date', '-start_date', 'ordered')
            posts = Post.objects.filter(pointerType='Role', Role_obj__Person_obj=person).order_by('-DateTime')

        elif view == 'Votes':
            posts = Vote.objects.filter(Person_obj=person).order_by('-Motion_obj__DateTime')
            # # posts = Vote.objects.filter(post_type='vote', vote__person=person).order_by('-date_time')
            # # prnt(posts)
            # if page == 1:
            #     match_percentage, total_matches, vote_matches, my_votes, return_votes = get_matches(request, person, govs)
            # try:
            #     match = Interaction.objects.filter(User_obj=user, Person_obj=person).exclude(match=None)[0]
            #     match.match = match_percentage
            #     match.save()
            # except:
            #     match = None
        elif view == 'Debates':
            posts = Post.objects.filter(Q(Statement_obj__Person_obj=person)|Q(Statement_obj__PersonName__icontains=person.FullName)).order_by(ordering)
        elif topic:
            # posts = Post.objects.filter(hansardItem__person=person, hansardItem__Terms__icontains=topic).select_related('hansardItem').order_by(ordering)
            search = ['%s'%(topic)]
            posts = Post.objects.filter(Statement_obj__Terms_array__overlap=search, Statement_obj__Person_obj=person).order_by(ordering)
            if posts.count() == 0:
                posts = Post.objects.filter(Statement_obj__keyword_array__icontains=topic, Statement_obj__Person_obj=person).order_by(ordering)
        elif view == 'Sponsorships':
            posts = Post.objects.filter(Q(Bill_obj__Person_obj=person)|Q(Bill_obj__CoSponsor_objs=person)).order_by(ordering)
            prnt(posts)
        else:
            posts = None
        # elif view == 'All':
        #     hansardItem, Vote, 
        # elif view == 'Word Cloud':
        #     try:
        #         hansards = HansardItem.objects.filter(person=person)
        #         prnt(hansards.count())
        #         cleantext = ''
        #         for h in hansards:
        #             cleantext = cleantext + ' ' + h.Content
        #         cleantext = BeautifulSoup(cleantext, "lxml").text
        #         wordCloud = get_wordCloud(request, cleantext)
        #         posts = []
        #     except:
        #         posts = []

        # options = {'Match: %s' %(match):'%s?view=Match'%(person.get_absolute_url()), 'Votes':'%s?view=Votes'%(person.get_absolute_url()), 
        #            'Debates':'%s?view=Debates'%(person.get_absolute_url()), 'Sponsorships':'%s?view=Sponsorships'%(person.get_absolute_url()), 'Roles':'%s?view=Roles'%(person.get_absolute_url())}
        # if topic:
        #     options['follow'] = '%s' %(topic)
        #     options['Sort: %s' %(sort)] = '%s?topic=%s&sort=%s' %(person.get_absolute_url(), topic, newSort)
        # elif view == 'Debates':
        #     options['follow'] = '?follow=%s' %(follow)
        #     options['Sort: %s' %(sort)] = '%s?view=Debates&sort=%s' %(person.get_absolute_url(), newSort)
        # else:
        #     options['follow'] = '?follow=%s' %(follow)
        # else:
        #     nav_options['follow'] = '?follow=%s' %(follow)
        prnt('pots',posts)
        setlist = paginate(posts, page, request)
        reactions = get_useractions(request, setlist)
        context = {
            'title': title,
            # 'nav_bar': nav_options,
            # 'updatedPerson': {},
            'view': view,
            'cards': 'representative_view',
            'sort': sort,
            'personTerms': termsList,
            # 'person': person,
            # 'personPost': person,
            # 'rolePost': rolePost,
            # 'cards': cards,
            # 'sort': sort,
            # 'view': view,
            'page': page,
            'style':style,
            # 'filter': f,
            # 'nav_bar': list(options.items()),
            'feed_list':setlist,
            # 'mp': person,
            # 'updatedRole': r,
            'reactions': reactions,
            'match': match_percentage,
            'voteMatches': vote_matches,
            'totalMatches': total_matches,
            'myVotes': my_votes,
            # 'r' : Role.objects.filter(position="Member of Parliament", person=person)[0],
            'wordCloud': wordCloud,
            'topicList': [topic],
        }
        return render_view(request, context, country=country)


def senator_list(request):
    prnt('Senator list')
    title = "All Senators"
    cards = 'senator_list'
    style = request.GET.get('style', 'index')
    sort = request.GET.get('sort', 'position')
    page = request.GET.get('page', 1)
    # if style == 'index':
    #     page = 1
    roles = Role.objects.filter(position='Senator', current=True).select_related('person').order_by('ordered')
    setlist = paginate(roles, page, request)
    # options = ['Page: %s'%(page), 'Sort: %s'%(sort), 'Party: all']
    options = {'Page: %s' %(page):'page', 'Sort: %s' %(sort):'sort', 'Party: all': 'party'}
    context = {
        'title': title,
        'cards': cards,
        'sort': sort,
        'nav_bar': list(options.items()),
        'feed_list':setlist,
    }
    return render_view(request, context)


def subregions_modal_view(request, region, regionType, baseLink):
    # prnt(region)
    if baseLink.startswith('/'):
        baseLink = baseLink[1:]
    baseLink = region + '/' + baseLink
    # prnt('baseLink',baseLink)
    pRegion = Region.valid_objects.filter(Name=region, nameType=regionType).first()
    subRegions = Region.valid_objects.filter(ParentRegion_obj=pRegion)
    context = {
        'title': 'Regions',
        'subRegions': subRegions,
        'baseLink' : baseLink,
    }
    return render(request, "modals/regions_modal.html", context)
