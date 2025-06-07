
from django.template.defaulttags import register
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import redirect

# import django_rq

from legis.models import Government, Agenda, Bill, Meeting
from .models import Post,Update,Region,GenericModel
from accounts.models import User, Notification, UserPubKey,UserNotification,UserAction
from .forms import AgendaForm
from blockchain.models import get_signing_data
from utils.models import *

# from django_user_agents.utils import get_user_agent

from django.db.models import Q, Value
from collections import Counter
from uuid import uuid4
#for wordcloud
# import numpy as np
# import pandas as pd
# from os import path
# from PIL import Image
# from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
# import matplotlib.pyplot as plt
# import base64
# import io
# import urllib.parse
import tiktoken
# from openai import OpenAI
from unidecode import unidecode

# from django.contrib.auth import (
#     authenticate,
#     get_user_model,
#     login,
#     logout,

#     )

def getTrendingTop(Chamber, country):
    posts = TopPost.objects.filter(Chamber=Chamber, country=country.Name)
    return posts

def get_trending_keys(dt, include_list, orgs):
    trends = Post.objects.filter(Chamber__in=orgs).filter(Q(DateTime__lte=datetime.datetime.now() + datetime.timedelta(hours=1))|Q(DateTime__gte=datetime.datetime.now() + datetime.timedelta(days=dt.days))).filter(pointerType__in=include_list).order_by('-rank', '-DateTime')[:200]
    # trends = KeyphraseTrend.objects.filter(Chamber__in=orgs).order_by('-trend_score')[:200]
    keys = []
    # prnt('trends', trends)
    for p in trends:
        # keys.append(p.text)
        # prnt(p.pointerType)
        # prnt(p.__dict__)
        if p.keyword_array:
            keys = keys + p.keyword_array 
        # elif p.Meeting_obj.Terms_array:
        #     for t in p.Meeting_obj.list_ten_terms():
        #         if t[0] not in skipwords:
        #             keys.append(t[0])
    return keys

def algorithim(user, include_list, chamber_list, country, provState_name, view, page):
    prnt('algo', chamber_list)
    orgs = chamber_list
    # if Chamber == 'House':
    #     orgs = ['House', 'House of Commons', 'Congress']
    # elif Chamber == 'Senate':
    #     orgs = ['Senate']
    # elif Chamber == 'All':
    #     orgs = ['Senate', 'House', 'House of Commons', 'Congress', '%s-Assembly'%(provState_name)]
    # elif Chamber == 'Assembly':
    #     orgs = ['%s-Assembly'%(provState_name)]
    # prnt('Chamber,orgs', Chamber, orgs)
    if 'Bill' in include_list:
        # prnt('is bill')
        # dateQuery = Bill.objects.filter(OriginatingChamberName__in=orgs).filter(LatestCompletedBillStageDateTime__gte=datetime.datetime.now()-datetime.timedelta(days=100)).order_by('-LatestCompletedBillStageDateTime')
        try:
            dateQuery = Bill.objects.filter(Chamber__in=orgs).order_by('-last_updated')[:10]
            # dateQuery = Bill.objects.filter(Chamber__in=orgs).order_by('-LatestCompletedBillStageDateTime')[10]
            # prnt('dateQuery1', dateQuery[0].last_updated)
            dateQuery = list(dateQuery)[::-1][0]
            date = dateQuery.last_updated
        except Exception as e:
            # prnt(str(e))
            # try:
            #     date = dateQuery.last().LatestCompletedBillStageDateTime
            # except:
            date = now_utc()
        dt = now_utc() - date
    elif 'Meeting' in include_list or 'Statement' in include_list:
        try:
            # prnt('meeting date')
            dateQuery = Meeting.objects.filter(meeting_type='Debate', Chamber__in=orgs).filter(DateTime__gte=now_utc()-datetime.timedelta(days=100)).order_by('-DateTime')[:10]
            # prnt('dateQuery', dateQuery)
            dateQuery = list(dateQuery)[::-1][0]
            date = dateQuery[12].DateTime
        except Exception as e:
            # prnt(str(e))
            # try:
            #     date = dateQuery.last().DateTime
            # except:
            date = now_utc()
        dt = now_utc() - date
    # if request and not request.user.is_authenticated:
    #     try:
    #         userToken = request.COOKIES['userToken']
    #         # prnt(userToken)
    #         user = User.objects.filter(userToken=userToken)[0]
    #     except:
    #         user = None
    # elif request:
    #     user = request.user
    # else:
    #     user = None
    # prnt('dt', dt)
    if view == 'Recommended' and user and json.loads(user.interest_array):
        keys = json.loads(user.interest_array)
        # prnt(keys)
    else:
        if view == 'Recommended' and user and not json.loads(user.interest_array):
            pass
        else:
            view = 'Trending'
        keys = get_trending_keys(dt, include_list, orgs)
    # randomNum = 255
    def get_posts(dayRange, firstKeys, secondKeys, reorder):
        randomNum = random.randint(1, 333) # picks 1/333th (333 = 8hrs by rank) of hansardItems randomly
        # prnt('randInt', randomNum)
        plusRange = randomNum + 8 # sets range for randomNum used in query below
        minusRange = randomNum - 8
        counter = Counter(firstKeys)
        firstCommonKeys = counter.most_common(500)
        if secondKeys == firstKeys:
            firstCommonKeys = firstCommonKeys[:500]
            secondCommonKeys = firstCommonKeys
        else:
            counter = Counter(secondKeys)
            secondCommonKeys = counter.most_common(500)
        
        posts = Post.objects.filter(Country_obj=country, Chamber__in=orgs).filter(DateTime__gte=datetime.datetime.now()-datetime.timedelta(days=dayRange)).filter(pointerType__in=include_list).filter(Q(pointerType='Bill')&Q(keyword_array__overlap=firstKeys)|Q(pointerType='Meeting')&Q(keyword_array__overlap=secondKeys)).order_by('-rank', '-DateTime')[:1000]
        # .exclude(Q(Statement_obj__word_count__lt=20)|Q(pointerType='Statement')&Q(randomizer__lt=minusRange)|Q(pointerType='Statement')&Q(randomizer__gt=plusRange)).filter(Q(pointerType='Bill')&Q(keyword_array__overlap=firstKeys)|Q(pointerType='Statement')&Q(keyword_array__overlap=secondKeys)|Q(Statement_obj__Terms_array__overlap=firstKeys))
        # posts = Post.objects.filter(organization__in=orgs).filter(DateTime__gte=datetime.datetime.now()-datetime.timedelta(days=dt.days)).filter(post_type__in=include_list).filter(Q(post_type__in=include_list)&Q(keywords__overlap=keys)|Q(hansard_key__Terms__overlap=keys)).order_by('-rank', '-DateTime')[:1000]
        prnt('posts', posts)
        if reorder:
            querylist = {}
            for p in posts:
                keywords = []
                if p.keyword_array:
                    keywords = p.keyword_array
                # elif p.Debate_obj.Terms_array:
                #     for k in p.Debate_obj.list_ten_terms():
                #         keywords.append(k[0])
                # q = [s for s in commonKeys if any(xs in s for xs in keywords)]
                if p.pointerType == 'Meeting':
                    y = [{c:k} for c in secondCommonKeys for k in keywords if c[0] == k]
                else:
                    y = [{c:k} for c in firstCommonKeys for k in keywords if c[0] == k]
                for i in y:
                    # prnt(p, i)
                    for key, value in i:
                        if key not in skipwords:
                            if p in querylist:
                                querylist[p] += value
                            else:
                                querylist[p] = value                    
            return querylist
        else:
            return posts
    if len(keys) > 4:
        querylist = get_posts(dt.days, keys, keys, True)
        querylist = sorted(querylist.items(), key=operator.itemgetter(1),reverse=True)
    else:
        querylist = []
    # prnt(querylist)
    posts = []
    for p in querylist:
        posts.append(p[0])
        # if p[0].hansard_key:
            # prnt('hansard')
            # for t in p[0].hansard_key.Terms:
            #     if t in request.user.keywords:
            #         prnt(t)
            # prnt(p[0].hansard_key.Terms)
            # prnt()
    prnt(len(posts))
    if len(posts) <= 20:
        # prnt('less tahn algoritym')
        # prnt(keys)
        trendKeys = get_trending_keys(dt, include_list, orgs)
        # prnt('trendKeys', trendKeys)
        querylist = get_posts(dt.days, trendKeys, keys, True)
        # prnt('querylist', querylist)
        querylist = sorted(querylist.items(), key=operator.itemgetter(1),reverse=True)
        for p in querylist:
            if p[0] not in posts:
                posts.append(p[0])
    # prnt(len(posts))
    # prnt('---', 20 * (int(page)))
    if len(posts) <= 20 * (int(page)):
        # prnt('less than 22 algotrithim')
        trendKeys = get_trending_keys(dt, include_list, orgs)
        querylist = get_posts(90, trendKeys, keys, False)
        # randomNum = random.randint(1, 333)
        # extra_posts = Post.objects.filter(organization__in=orgs).filter(DateTime__gte=datetime.datetime.now()-datetime.timedelta(days=90)).filter(post_type__in=include_list).exclude(Q(hansardItem__wordCount__lt=10)|Q(post_type='hansardItem')&Q(randomizer__lt=randomNum)|Q(post_type='hansardItem')&Q(randomizer__gt=randomNum)).filter(Q(post_type__in=include_list)&Q(keywords__overlap=keys)|Q(post_type='hansardItem')&Q(keywords__overlap=keys)|Q(hansard_key__Terms__overlap=keys)).order_by('-rank', '-DateTime')[:1000]
        # extra_posts = Post.objects.filter(organization__in=orgs).filter(DateTime__gte=datetime.datetime.now()-datetime.timedelta(days=90)).filter(post_type__in=include_list).exclude(Q(post_type='hansardItem')&Q(randomizer__lte=randomNum)).filter(Q(post_type__in=include_list)|Q(hansard_key__Terms__overlap=keys)).order_by('-rank', '-DateTime')
        for p in querylist:
            if p not in posts:
                posts.append(p)
        # prnt(len(posts))
    if len(posts) <= 20 * (int(page)):
        # prnt('less than 33 algotrithim')
        trendKeys = get_trending_keys(dt, include_list, orgs)
        querylist = get_posts(200, trendKeys, keys, False)
        for p in querylist:
            if p not in posts:
                posts.append(p)
        # prnt(len(posts))
    return posts, view


def get_paginator_url(request, c):
    prnt('get_paginator_url')
    paginatorURL = ''
    # try:
    #     paginatorURL = paginatorURL + str(c['feed_list'].next_page_number())
    # except Exception as e:
    #     pass
    try:
        paginatorURL = paginatorURL + '&sort=%s' %(c['sort'])
    except Exception as e:
        pass
    try:
        paginatorURL = paginatorURL + '&view=%s' %(c['view'])
    except:
        pass
    try:
        paginatorURL = paginatorURL + '&time=%s' %(c['time'])
    except:
        pass
    try:
        paginatorURL = paginatorURL + '&topic=%s' %(c['topic'])
    except:
        pass
    try:
        paginatorURL = paginatorURL + '&id=%s' %(c['id'])
    except:
        pass
    try:
        paginatorURL = paginatorURL + '&speaker_id=%s' %(c['speaker_id'])
    except Exception as e:
        pass     
    return {**{'paginatorURL': paginatorURL}, **c}

def get_cookies(request, c, country=None):
    prnt('get_cookies')
    try:
        theme = request.COOKIES['theme']
    except:
        theme = 'day'
    # prnt('Theme:', theme)
    if not country:
        url = request.get_full_path()
        x = url[1:].find('/')
        possibleCountry = url[1:1+x].lower()
        # prnt('pc', possibleCountry)
        country = Region.valid_objects.filter(Name__iexact=possibleCountry, modelType='country').first()
        if not country:
            # prnt(str(e))
            # if request.user.is_authenticated and request.user.Country_obj:
            #     country = request.user.Country_obj
            # else:
            if 'country' in request.session:
                country_name = request.session['country']
            else:
                country_name = None
            if country_name:
                country = Region.valid_objects.filter(Name__iexact=country_name, modelType='country').first()
                if not country:
                    country, provState, county, city = get_regions(request, None, None)
                    # country, provState, provState_name, municipality, municipality_name = get_regions(request, None, None)
            else:
                country, provState, county, city = get_regions(request, None, None)
                # country, provState, provState_name, municipality, municipality_name = get_regions(request, None, None)

            # country = Region.objects.filter(Name__iexact='USA', modelType='country')[0]
                
    # prnt('cookies:',country)
    notifications = get_notifications(request.user, country)
    # prnt('notifications',notifications)
    # include server data json detailing version number and latest modelVersions
    # user device will store a blank copy of user models

    width = request.GET.get('width', '')
    if not width:
        try:
            width = request.COOKIES['deviceWidth']
        except:
            width = None
    # prnt(width)
    # try:
    #     if float(width) < 810:
    #         mobile = request.user_agent.is_mobile
    #         width = int(width)
    #     else:
    #         mobile = False  
    # except Exception as e:
    #     # prnt(str(e))
    #     mobile = request.user_agent.is_mobile
    mobile = get_isMobile(request)
    # prnt('mobile',mobile)
    # prnt(request.headers.get('X-Requested-With'))
    xRequest = False
    if request.headers.get('X-Requested-With') and 'sonetapp' in request.headers.get('X-Requested-With'):
        if width and float(width) < 810:
            xRequest = True
    # prnt('---')
    # prnt(xRequest)
    # xRequest = request.headers.get('X-Requested-With')
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    # prnt('----------------')
    # prnt(ua)
    # prnt(xRequest)
    if 'iphone' in str(ua):
        iphone = 'true'
    elif 'ipad' in str(ua):
        mobile = False
        iphone = None
    else:
        iphone = None
    # return server copy of userData for user to locally verify
    if request.user.is_authenticated:
        userData = get_user_sending_data(request.user)
    else:
        userData = None
    # prnt('utils.py UserData', userData)
    nodeData = {}
    from blockchain.models import Block, Sonet
    latest_node_block = Block.objects.filter(blockchainType='Nodes', validated=True).order_by('-index').first()
    if latest_node_block:
        nodeData['blockId'] = latest_node_block.id
        nodeData['blockDatetime'] = dt_to_string(latest_node_block.DateTime)
        nodeData['id_data'] = latest_node_block.data
        nodeData['addresses'] = latest_node_block.notes['addresses']
    else:
        from blockchain.models import Node, NodeChain_genesisId,Blockchain
        nodes = Node.objects.exclude(activated_dt=None).filter(suspended_dt=None)
        if nodes:
            nodeChain = Blockchain.objects.filter(genesisId=NodeChain_genesisId).first()
            if nodeChain:
                nodeChain.add_item_to_queue(list(nodes))
        nodeData['blockId'] = 'none'
        nodeData['blockDatetime'] = dt_to_string(now_utc())
        nodeData['id_data'] = {'All':['nodSo40693jf95jd94']}
        nodeData['addresses'] = {'nodSo40693jf95jd94': '127.0.0.1:3005'}
    prnt('returning nodeData',json.dumps(nodeData))


    sonet = Sonet.objects.first()
    if not sonet:
        sonet = {'Title' : 'Nonet', 'LogoLink' : "img/default_logo.png"}
        # sonet = {}
        nodeData['sonetInitializedDatetime'] = dt_to_string(now_utc())
    else:
        nodeData['sonetInitializedDatetime'] = dt_to_string(sonet.created)

    # prnt('sonet', sonet)
    context = {
        "sonet": sonet,
        "userData": userData,
        "nodeData": json.dumps(nodeData),
        "country": country,
        "theme": theme,
        "notifications": notifications,
        # "updatedAgenda":updatedAgenda,
        # "agendaItems":agendaItems,
        # 'agendaForm': form,
        # 'trending': trending,
        'isMobile': mobile,
        'xRequest': xRequest,
        'iphone': iphone,
        }
    if not userData:
        from utils.locked import generate_id
        context['anonId'] = 'tusrSo' + generate_id(len=10)
    prnt('done cookies',context)
    return {**context, **get_paginator_url(request, c)}

def get_user_data(request):
    prnt('get user')
    try:
        userData = request.POST.get('userData')
        userData = json.loads(userData)
    except:
        userData = None
    try:
        if request.user.is_authenticated:
            return userData, request.user
        else:
            user_id = request.GET.get('userId', '')
            # prnt(request.COOKIES['userData'])
            try:
                prnt('1', user_id)
                user = User.objects.filter(id=user_id).first()
            except Exception as e:
                prnt('err77543',str(e))
                user = None
            prnt(user)
            return userData, user
    except Exception as e:
        prnt('err76325',str(e))
        return userData, None

def get_user_sending_data(user):
    # prnt()
    # prnt('get_user_sending_data')
    x = get_signing_data(user, include_sig=True)
    # prnt('x',x)
    # prnt('get_user_sending_data22')
    # sig = ',"signature":"%s"' %(user.signature)
    # pk = ',"publicKey":"%s"' %(user.publicKey)
    # x = x[:-1] + sig + pk + '}'
    # prnt(x)
    u = User()
    user_json = json.loads(x)
    user_json['must_rename'] = user.must_rename
    user_json['latestModel'] = u.latestModel
    user_json['signature'] = user.signature
    if u.latestModel != user.modelVersion:
        user_json['updated_model'] = json.dumps(get_signing_data(u))
    from utils.locked import sort_for_sign
    user_json = sort_for_sign(user_json)
    userData = json.dumps(user_json, separators=(',', ':'))
    prnt('returning userData;',userData)
    return userData

def get_isMobile(request):
    width = request.GET.get('width', '')
    if not width:
        try:
            width = request.COOKIES['deviceWidth']
        except:
            width = None
    # prnt(width)
    try:
        if float(width) < 810:
            mobile = request.user_agent.is_mobile
            width = int(width)
        else:
            mobile = False  
    except Exception as e:
        # prnt(str(e))
        mobile = request.user_agent.is_mobile    
    # prnt('mobile',mobile)
    return mobile

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_regions(request, region, user):
    from django.db.models import Model
    # prnt('ggget region')
    prnt('r', region)
    # returns country, provState, county, city
    try:
        if request.subdomain == 'ca':
            region = 'Canada'
        elif request.subdomain == 'us':
            region = 'USA'
        else:
            region = 'Unknown Region'

        prnt('subdoman:', request.subdomain)
    except:
        pass
    if isinstance(region, Model):
        country_obj = region
    elif isinstance(region, str):
        country_obj = Region.valid_objects.filter(Name__iexact=region, modelType='country').first()
    else:
        country_obj = Region.valid_objects.filter(modelType='country', Name='USA').first()
        if not country_obj:
            country_obj = Region.valid_objects.filter(modelType='country').first()
    prnt('country_obj',country_obj)
    return country_obj, None, None, None
    country_obj = None
    if region and user and user.Country_obj and region.lower() == user.Country_obj.lowerName():
        country_obj = user.Country_obj
        # country_obj = Region.valid_objects.filter(Name=country, modelType='country')[0]
    elif region:
        try:
            country_obj = Region.valid_objects.filter(Name__iexact=region, modelType='country')[0]
        except:
            try:
                country = request.session['country']
                country_obj = Region.valid_objects.filter(Name__iexact=country, modelType='country')[0]
            except Exception as e:
                try:
                    country_obj = Region.valid_objects.filter(modelType='country')[0]
                except:
                    country_obj = Region.valid_objects.all()[0]
    elif user and user.Country_obj:
        country_obj = user.Country_obj
        
    else:
        try:
            country = request.session['country']
        except:
            country = None
        if country:
            try:
                country_obj = Region.valid_objects.filter(Name__iexact=country, modelType='country')[0]
            except:
                country_obj, ProvState, ProvState_name = get_location(request, user)
        else:
            country_obj, ProvState, ProvState_name = get_location(request, user)

    if country_obj:
        request.session.setdefault('country', country_obj.Name)
        request.session['country'] = country_obj.Name


    #     country_obj = None
    # prnt('1')
    # prnt(country_obj)
    # prnt(region)
    if user and country_obj and not region or user and country_obj and region.lower() == country_obj.lowerName():
        if user.ProvState_obj:
            provState_obj = user.ProvState_obj
            provState_name = provState_obj.lowerName()
        else:
            provState_obj = None
            provState_name = 'None'
        if user.Municipality_obj:
            municipality_obj = user.Municipality_obj
            municipality_name = municipality_obj.lowerName()
        else:
            municipality_obj = None
            municipality_name = 'None'
        # prnt('2')
        return country_obj, provState_obj, provState_name, municipality_obj, municipality_name
    else:
        # prnt('3')
        try:
            # prnt('3a')
            # prnt(ProvState)
            if not country_obj:
                country_obj, ProvState, ProvState_name = get_location(request, user)
                # prnt('3b')
                # prnt(ProvState.ParentRegion)
                if not country_obj:
                    country_obj = ProvState.ParentRegion_obj
                # prnt('3bb')
                return country_obj, ProvState, ProvState_name, None, 'None'
            elif ProvState.ParentRegion_obj == country_obj:
                # prnt('3c')
                return country_obj, ProvState, ProvState_name, None, 'None'
            else:
                # prnt('3d')
                return country_obj, None, 'None', None, 'None'
        except:
            # prnt('4')
            return country_obj, None, 'None', None, 'None'
    # if not country_obj or not provState_obj:
    #     try:
    #         from django.contrib.gis.geoip2 import GeoIP2
    #         g = GeoIP2('geoip')
    #         # prnt(g.country('google.com'))
    #         # prnt(g.city('google.com'))
    #         #http
    #         ip = request.META.get('REMOTE_ADDR', None)
    #         if not ip:
    #             #https
    #             ip = request.META.get('HTTP_X_REAL_IP', None)

    #         prnt(ip)
    #         if ip:
    #             data = g.city(ip)
    #             region = data['region']
    #             # prnt(region)
    #             # lat = data['latitude']
    #             # long = data['longitude']
            
    #         p = Province.objects.filter(short_name=region)[0]
    #         # prnt(p)
    #         if p.is_supported:
    #             region = p.name
    #         else:
    #             region = None
    #         # prnt(region)
    #         request.session.setdefault('region', p.name)
    #         request.session['region'] = p.name
    #         return p, region, long, lat
    #     except Exception as e:
    #         # prnt(str(e))
    #         return None, None, None, None

    # return country_obj, provState_obj, municipality_obj

def get_location(request, user):
    prnt('get location')
    Country = None
    def run_region(request):
        prnt('run region111')
        try:
            from django.contrib.gis.geoip2 import GeoIP2
            g = GeoIP2('geoip')
            # prnt(g.country('google.com'))
            # prnt(g.city('google.com'))
            #http
            ip = request.META.get('REMOTE_ADDR', None)
            if not ip:
                #https
                ip = request.META.get('HTTP_X_REAL_IP', None)
            

            prnt(ip)
            if ip:
                data = g.city(ip)
                prnt(data)
                city_city = data['city']
                provState_abbrv = data['region']
                country_name = data['country_name']
                # prnt(region)
                lat = data['latitude']
                long = data['longitude']
            Country = Region.valid_objects.filter(Name=country_name, modelType='country').first()
            try:
                p = Region.valid_objects.filter(AbbrName=provState_abbrv, is_supported=True, modelType='provState').first()
                return Country, p, p.lowerName(), long, lat
            except Exception as e:
                return Country, None, 'None', None, None
        except Exception as e:
            try:
                Country = Region.valid_objects.filter(Name='USA', modelType='country').first()
            except:
                Country = None
            return Country, None, 'None', None, None
    def run():
        Country_obj, ProvState, ProvState_name, long, lat = run_region(request)

        # def locate_user(user):
        #     locations = {}
        #     for p in user.longLat:
        #         try:
        #             if not p in locations:
        #                 locations[p] = 1
        #             else:
        #                 locations[p] += 1
        #         except:
        #             pass
        #     locations = sorted(locations.items(), key=operator.itemgetter(1),reverse=True)
        #     mostOccured = locations[0][0]
        #     mostOccured = json.loads(mostOccured)
        #     mostLongitude = next(iter(mostOccured))
        #     mostLatitude = mostOccured[mostLongitude]
        #     url = 'https://represent.opennorth.ca/boundaries/?contains=%s,%s' %(mostLatitude, mostLongitude)
        #     user.clear_region()
        #     user.get_data(url)

        return Country_obj, ProvState, ProvState_name
    if user:
        # prnt('a')
        if user.ProvState_obj:
            # prnt('c')
            # prnt(user.ProvState)
            ProvState = user.ProvState_obj
            # request.session['provState'] = ProvState.Name
            if ProvState.is_supported:
                # prnt('c1')
                ProvState_name = ProvState.lowerName()
            else:
                # prnt('c2')
                ProvState_name = 'None'
        else:
            # prnt('d')
            Country, ProvState, ProvState_name = run()
    else:
        #  prnt('b')
        Country, ProvState, ProvState_name = run()
    # prnt('e')
    return Country, ProvState, ProvState_name

def nav_item(type, text, target, var, fields=None, key=None, new_tab=None):
    x = {'type':type, 'text':text, 'target':target, 'var':var}
    if fields:
        x['fields'] = fields
    if key:
        x['key'] = key
    if new_tab:
        x['new_tab'] = new_tab
    # prnt(x)
    return x

def get_theme(request):
    try:
        theme = request.COOKIES['theme']
    except:
        theme = 'day'
    return {"theme": theme}

def get_notifications(user, country):
    # return
    if user.is_authenticated:
        n = UserNotification.objects.filter(User_obj=user, new=True).order_by("-DateTime", '-created')[:40]
        if n:
            return n
        else:
            return Notification.objects.filter(validated=True, Region_obj=country).order_by("-DateTime", '-created')[:40]
    else:
        return Notification.objects.filter(validated=True, Region_obj=country).order_by("-DateTime", '-created')[:40]



def get_trending(request, country, provState, county, city, current_chamber, all_chambers):
    from posts.models import KeyphraseTrend
    prnt('get trend')
    region_ids = []
    if country:
        region_ids.append(country.id)
    if provState:
        region_ids.append(provState.id)
    if county:
        region_ids.append(county.id)
    if city:
        region_ids.append(city.id)
    trendList = []
    # assembly = None
    # try:
    #     Chamber = request.session['Chamber']
    # except:
    #     Chamber = 'All'
    # prnt(Chamber)
    # if 'Assembly' in Chamber or Chamber == 'All':
    try:
        # region = request.session['region']
        # prnt(region)
        # p = Region.objects.filter(Name=region)[0]
        # assembly = '%s-Assembly' %(p.name)
        if current_chamber != 'All':
            kt = KeyphraseTrend.objects.filter(Region_obj__id__in=region_ids).exclude(recent_occurences=0).filter(Chamber=current_chamber)[:20]
        else:
            # Chambers = ['House', 'Senate', 'Assembly', 'Municipality']
            kt =  KeyphraseTrend.objects.filter(Region_obj__id__in=region_ids).exclude(recent_occurences=0)[:20]
    except Exception as e:
        prnt('failtrend')
        prnt('err98654',str(e))
        kt = []
            # kt =  KeyphraseTrend.objects.filter(Country_obj=country).filter(Chamber=Chamber)[:20]
    # else:
    #     kt =  KeyphraseTrend.objects.filter(Country_obj=country).filter(Chamber=Chamber)[:20]
    # prnt('kt', kt)
    for t in kt:
        trend = {}
        trend['key'] = t.key
        # trend['id'] = t.id
        trend['get_absolute_url'] = t.get_absolute_url()
        trend['recentOccurences'] = t.recent_occurences
        # if trend not in trendList:
        #     prnt('append', trend)
        #     trendList.append(trend)
        # else:
        #     prnt('found')
        # prnt(trend)
        for i in trendList:
            if i['key'] == t.key:
                trend['recentOccurences'] += i['recentOccurences']
                trendList.remove(i)
                break
        trendList.append(trend)
    # prnt('trendList',trendList)

    agenda_list, agendaForm = get_agenda(request, country, provState, county, city, current_chamber, all_chambers)
    return {'trend_list':trendList, 'agenda_list':agenda_list, 'agendaForm':agendaForm}


def get_agenda(request, country, provState, county, city, current_chamber, all_chambers):
    prnt('get agenda')
    start_time = datetime.datetime.now()
    prnt('start', start_time, country)
    agenda_list = []
    if current_chamber == 'All':
        if country:
            agendas = Agenda.objects.filter(Region_obj=country, Chamber__in=all_chambers).exclude(Validator_obj=None).order_by('-Chamber','-DateTime').distinct('Chamber')
            agenda_list = list(agendas)
            # for a in agendas:
            #     agenda_list.append(a)
        if provState:
            a = Agenda.objects.filter(Region_obj=provState, Chamber__in=all_chambers).exclude(Validator_obj=None).order_by('-DateTime').first()
            if a:
                agenda_list.append(a)
        if county:
            a = Agenda.objects.filter(Region_obj=county, Chamber__in=all_chambers).exclude(Validator_obj=None).order_by('-DateTime').first()
            if a:
                agenda_list.append(a)
        if city:
            a = Agenda.objects.filter(Region_obj=city, Chamber__in=all_chambers).exclude(Validator_obj=None).order_by('-DateTime').first()
            if a:
                agenda_list.append(a)
    else:
        agendas = Agenda.objects.filter(Country_obj=country, Chamber=current_chamber).exclude(Validator_obj=None).order_by('-Chamber', '-DateTime').distinct('Chamber')
        agenda_list = list(agendas)
        # for a in agendas:
        #     agenda_list.append(a)
    prnt()
    # updatedAgenda = Update.objects.filter(Country_obj=country, Chamber='House', Agenda_obj__DateTime__lte=datetime.datetime.today())[0]
    # prnt(updatedAgenda.data)
    # agendaItems = AgendaItem.objects.filter(Agenda_obj=agenda).select_related('AgendaTime_obj').order_by('position')
    # prnt(agendaItems)
    # end_time = datetime.datetime.now() - start_time
    # prnt('end', end_time)
    return agenda_list, AgendaForm()

def get_gov(country, gov_levels, govNum=None, session=None):
    prnt('get__gov_levels', gov_levels)
    prnt('country',country)
    try:
        if govNum and session:
            # if Chamber == 'All':
            govs = Government.objects.filter(Country_obj=country, gov_level__in=gov_levels, GovernmentNumber=govNum, SessionNumber=session).distinct('gov_level').order_by('gov_level', '-DateTime')
            # else:
            #     gov = Government.objects.filter(Country_obj=country, gov_level=gov_level, GovernmentNumber=govNum, SessionNumber=session)[0]
            #     govs = [gov]
        else:
            # if Chamber == 'All':
            govs = Government.objects.filter(Country_obj=country, gov_level__in=gov_levels).distinct('gov_level').order_by('gov_level', '-DateTime')
            # else:
            #     gov = Government.objects.filter(Country_obj=country, gov_level__in=gov_levels)[0]
            #     govs = [gov]
    except Exception as e:
        prnt('err249',str(e))
        govs = []
    return govs

def get_chambers(request, country, provState=None, county=None, city=None, chamber=None):
    # prnt('get_chambers:', country, provState, county, city, chamber)
    # if Chamber:
    chambers = country.Chamber_array
    if not chambers:
        chambers = []
    # prnt('chhh',chambers)
    if provState:
        provState_name = provState.Name
    else:
        provState_name = 'none'
    if county:
        county_name = county.Name
    else:
        county_name = 'none'
    if city:
        city_name = city.Name
    else:
        city_name = 'none'
    # chambers = []
    # chambers = ['House','Senate']
    if provState:
        chambers.append(f'{provState_name}-Assembly')
    if county:
        chambers.append(f'{county_name}-Council')
    gov_levels = []
    # chamber = get_chamber
    if not chamber:
        chamber = request.GET.get('chamber', None)
        if not chamber:
            try:
                chamber = request.session['chamber']
            except Exception as e:
                chamber = 'All'
        # prnt('aaa')
        # prnt('cc',chamber)
        # Chambers.append(Chamber)
    # if chamber:
        words = chamber.split(' ')
        # prnt('words', words)
        chamber = ''
        for w in words:
            if chamber:
                chamber = chamber + ' '
            chamber = chamber + w[0].upper() + w[1:]
        # prnt('ch', chamber)
        request.session.setdefault('chamber', chamber)
        request.session['chamber'] = chamber
    if chamber.lower() == 'assembly':
        r = f'{provState_name}-Assembly'
        # chambers.append(r)
        gov_levels.append('Provincial')
        gov_levels.append('State')
    elif chamber.lower() == 'council':
        r = f'{county_name}-Council'
        # chambers.append(r)
        gov_levels.append('Municipal')
    elif chamber.lower() == 'house':
        # r = f'{municipality_name}-Council'
        # chambers.append(chamber)
        gov_levels.append('Federal')
    elif chamber.lower() == 'senate':
        # r = f'{municipality_name}-Council'
        # chambers.append(chamber)
        gov_levels.append('Federal')
    if chamber.lower() == 'all':
        # prnt('all')
        target_chamber = chambers
        gov_levels = ['Federal', 'Provincial', 'State', 'Territory', 'Municipal', 'County', 'City']
        # prnt('x')
    else:
        target_chamber = [chamber]
    return target_chamber, chamber, chambers, gov_levels

def get_Chamber(request):
    Chamber = request.GET.get('Chamber', '')
    # prnt('Chamber,', Chamber)
    if 'Assembly' in Chamber:
        Chamber = 'Assembly'
    if Chamber:
        request.session.setdefault('Chamber', Chamber)
        request.session['Chamber'] = Chamber
    else:
        try:
            Chamber = request.session['Chamber']
        except Exception as e:
            Chamber = 'All'
    return Chamber

def getDaily(request, country, provState, date):
    # must receive region
    try:
        if request.user.is_authenticated:
            try:
                if date:
                    daily = Daily.objects.filter(User_obj=request.user, DateTime=date)[0]
                else:
                    daily = Daily.objects.filter(User_obj=request.user)[0]
            except:
                if provState and provState.is_supported:
                    if date:
                        daily = Daily.objects.filter(Region_obj=provState.Name + '-Assembly', DateTime=date)[0]
                    else:
                        daily = Daily.objects.filter(Region_obj=provState.Name + '-Assembly')[0]
                else:
                    if date:
                        daily = Daily.objects.filter(Country_obj=country, Chamber='Federal', DateTime=date)[0]
                    else:
                        daily = Daily.objects.filter(Country_obj=country, Chamber='Federal')[0]
        else:
            if date:
                daily = Daily.objects.filter(Country_obj=country, Chamber='Federal', DateTime=date)[0]
            else:
                daily = Daily.objects.filter(Country_obj=country, Chamber='Federal')[0]
    except: 
        prnt('daily fail')  
        if date: 
            daily = Daily.objects.filter(Country_obj=country, Chamber='Federal', DateTime=date)[0]
        else:
            daily = Daily.objects.filter(Country_obj=country, Chamber='Federal')[0]
    return daily

def get_reps(user):
    # user = request.user
    # prnt('get reps')
    # userId = request.GET.get('userId', '')
    # countryId = request.GET.get('countryId', '')
    # provStateId = request.GET.get('provStateId', '')
    # regionalMunicipalId = request.GET.get('regionalMunicipalId', '')
    # # prnt('rmid', regionalMunicipalId)
    # municipalId = request.GET.get('municipalId', '')
    # federalDistrictId = request.GET.get('federalDistrictId', '')
    # federalDistrictName = request.GET.get('federalDistrictName', '')
    # provStateDistrictId = request.GET.get('provStateDistrictId', '')
    # regionalMunicipalityDistrictId = request.GET.get('regionalMunicipalityDistrictId', '')
    # wardId = request.GET.get('wardId', '')
    regions = []
    if user.Municipality_obj:
        regions.append(user.Municipality_obj.id)
    districts = []
    if user.Federal_District_obj:
        districts.append(user.Federal_District_obj.id)
    if user.ProvState_District_obj:
        districts.append(user.ProvState_District_obj.id)
    if user.Greater_Municipal_District_obj:
        districts.append(user.Greater_Municipal_District_obj.id)
    if user.Municipal_District_obj:
        districts.append(user.Municipal_District_obj.id)
    context = {}
    # regions = Region.objects.filter(id__in=regions)
    # districts = District.objects.filter(id__in=districts)
    Uroles = Update.objects.filter(pointerType='Role', Role_obj__District_obj__in=districts, data__icontains='"Current": true')
    # roles = Role.objects.filter(Q(District_obj__id__in=districts)&Q(Current=True)|Q(Region_obj__id__in=regions)&Q(Current=True)).select_related('Person_obj')
    elections = Election.objects.filter(end_date__gte=now_utc()-datetime.timedelta(days=30)).filter(District_obj__id__in=districts)
    # for region in regions:
    #     # prnt(region)
    #     context[region.modelType] = region
    # for district in districts:
    #     context[district.modelType] = district
    for r in Uroles:
        context[r.Role_obj.gov_level] = r
        # prnt(r)
        # try:
        #     prnt(r.District.id, wardId)
        # except:
        #     pass
        # prnt()

        # if r.Role_obj.District_obj and r.Role_obj.District_obj == user.Federal_District_obj:
            # context[r.Role_obj.gov_level] = r

        # if r.District_obj and r.District_obj == user.Federal_District_obj:
        #     if r.Position == 'Member of Parliament':
        #         context['MP_role'] = r
        #         # prnt('found')
        # elif r.District_obj and r.District_obj == user.ProvState_District_obj:
        #     if r.Position == 'MPP':
        #         context['MPP_role'] = r
        # elif r.District_obj and r.District_obj == user.Greater_Municipal_District_obj:
        #     if r.Position == 'Regional Councillor':
        #         context['regionalCouncillor_role'] = r
        # elif r.District_obj and r.District_obj == user.Municipal_District_obj:
        #     if r.Position == 'Councillor':
        #         context['Councillor_role'] = r
        # elif r.Region_obj and r.Region_obj == user.Municipality_obj:
        #     if r.Position == 'Mayor':
        #         context['Mayor_role'] = r
    for e in elections:
        # prnt(e)
        if e.District_obj == user.Federal_District_obj:
            context['MP_election'] = e
        elif e.District_obj == user.ProvState_District_obj:
            context['MPP_election'] = e
        elif e.District_obj == user.Greater_Municipal_District_obj:
            context['greater_municipal_election'] = e
        elif e.District_obj == user.Municipal_District_obj:
            context['municipal_election'] = e

    return context

def fetch_updated_objs(setlist, requestList):
    prnt('fetch_updated_objs')
    objs = {}
    data = {}
    try:
        for p in setlist:
            if p.Update_obj:
                for a in requestList:
                    ar = a + '_id'
                    if ar in p.Update_obj.data:
                        if a in objs:
                            objs[a].append(p.Update_obj.data[ar])
                        else:
                            objs[a] = [p.Update_obj.data[ar]]
        # prnt('objs',objs)
        from posts.models import subRegions
        for key, valueList in objs.items():
            # prnt(key, valueList)
            try:
                if key in subRegions:
                    items = get_dynamic_model('Region', list=True, id__in=valueList)
                else:
                    items = get_dynamic_model(key, list=True, id__in=valueList)
                data[key] = [i for i in items]
            except Exception as e:
                pass
    except Exception as e:
        prnt('err50582',str(e))
        pass
    return data

# def fetch_person_data(setlist):
#     person_idens = []
#     for i in setlist:
#         if i.pointerType == 'Bill':
#             if i.Bill_obj and i.Bill_obj.Person_obj:
#                 person_idens.append(i.Bill_obj.Person_obj.id)
#             # if i.Bill_obj and 'cosponsors' in i.Bill_obj.data:
#             #     for c in i.Bill_obj.data['cosponsors']:
#             #         person_idens.append(c['obj_id'])
#         elif i.Person_obj:
#             person_idens.append(i.Person_obj.id)
#     items = get_dynamic_model('Update', list=True, PointerId__in=person_idens)
#     return {i.pointerId:i for i in items}

def get_useractions(user, setlist):
    # prnt('get interactions')
    from accounts.models import UserAction
    if user and setlist:
        id_list = []
        actions = {}
        if user:
            # prnt('i user', user)
            for p in setlist:
                try:
                    id_list.append(p.id)
                except:
                    pass
            action_list = UserAction.objects.filter(User_obj=user, Post_obj__id__in=id_list)
            for r in action_list:
                actions[r.Post_obj.id] = r
            return actions
        else:
            return {}
    else:
        return {}
    #     try:
    #         userToken = request.COOKIES['userToken']
    #         user = User.objects.filter(userToken=userToken)[0]
    #         for p in setlist:
    #             try:
    #                 id_list.append(p.id)
    #             except:
    #                 pass
    #         reaction_list = Reaction.objects.filter(postId__in=id_list, user=user)
    #         for r in reaction_list:
    #             reactions[r.postId] = r
    #         return reactions
    #     except Exception as e:
    #         prnt('reaction fail',str(e))
    #         return {}

def paginate(queryset_list, page, request):
    # pager = request.GET.get('page', 1)
    # if int(page) > 100:
    #     page = 1
    # prnt('paginate',queryset_list)
    if not queryset_list:
        return None
    if 'id=' in str(page):
        # include context for discussions
        # maybe doesn't work on mac
        def clamp(n, minn):
            return max(minn, n)
        iden = page.replace('id=', '')
        # prnt('----',iden)
        queryset = []
        x = 0
        for i in queryset_list:
            if i.pointerType == 'Statement' and i.Statement_obj.order == int(iden):
                z = clamp((x-7), 0)
                for y in queryset_list[z:]:
                    # prnt(y)
                    queryset.append(y)
                break
            # elif i.post_type == 'committeeItem' and i.committeeItem.id == int(iden):
            #     z = clamp((x-7), 0)
            #     for y in queryset_list[z:]:
            #         queryset.append(y)
            #     break
            x += 1
        queryset_list = queryset
    paginator = Paginator(queryset_list, 20)
    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        queryset = paginator.page(1)
    except EmptyPage:
        try:
            queryset = paginator.page(paginator.num_pages)
        except:
            pass
    return queryset

def get_token_count(string: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens

def makeText(data):
    def remove_tags(text):
        try:
            TAG_RE = re.compile(r'<[^>]+>')
            text = TAG_RE.sub('', text).replace('"', "'").replace('\n', '').strip()
            text = ''.join(text.splitlines())
            text = unidecode(text)
            return text
        except:
            return None
    def textualize(p, text):
        try:
            party_name = p.Statement_obj.Person_obj.Party_obj.Name
        except:
            party_name = 'NA'
        text = text + '[post_id:ppxpp%sqqxqq]%s:\n%s\n\n' %(p.Statement_obj.id, p.Statement_obj.Person_obj.FullName, p.Statement_obj.Content)
        return text
    text = ""
    # prnt(data)
    if data and isinstance(data[0], int) or data and isinstance(data[0], str):
        # prnt('isstring')
        for i in data:
            try:
                p = Post.objects.filter(Statement_obj__id=i)[0]
                text = textualize(p, text)
            except:
                prnt('iiimmake text', i)
                text = ''
            # prnt(text)
    else:
        for p in data:
            if len(p.Statement_obj.Content) > 100:
                text = textualize(p, text)
    text = remove_tags(text)
    # prnt('text', text)
    num_tokens = get_token_count(text)
    prnt('num_tokens',num_tokens)
    return num_tokens, text



def summarize_topic(item, topic, url):
    def summarize(prompt):
        prnt('start summarize')
        # import os
        # os.environ["TOKENIZERS_PARALLELISM"] = "false"
        sum_start_time = datetime.datetime.now()
        prnt(sum_start_time)
        # # 48gb spot
        # # url = "https://mkwhgqn52r2yhf-5000.proxy.runpod.net/v1"
        # # url = "https://dv51uv5uqrfat4-5000.proxy.runpod.net/v1"
        # # url = "https://69ddb67yyor5p5-5000.proxy.runpod.net/v1"
        # # #20gb on demand:
        # # url = "https://9kzmbd8wyowzue-5000.proxy.runpod.net/v1"
        # # prnt('---------------', datetime.datetime.now() - start_time, topic)
        # client = OpenAI(api_key="EMPTY", base_url=url)
        # completion = client.chat.completions.create(
        # model="llama-2-13b-chat.Q4_K_M.gguf",
        # temperature=0.1,
        # max_tokens=500,
        # # stream=True,
        # messages=[
        #     {"role": "system", "content": "You are a non-conversational computer assistant."},
        #     {"role": "user", "content": prompt}
        # ]
        # )
        #     # {"role": "user", "content": "Summarize the most important point from the following parlimentary debate, do not opine, do not go over 250 characters, provide a quote of the point at the end: %s" %(text[:2000])}
        #     # {"role": "user", "content": "Summarize the main points from the following parlimentary debate, do not opine, do not go over 1000 characters: %s" %(text)}

        # # prnt(completion)

        # # prnt()
        prnt(len(prompt))
        # prnt()
        import ollama


        
        t_start = datetime.datetime.now()
        stream = ollama.chat(
            model='llama3',
            messages=[{'role': 'user', 'content': 'Hello'}],
            stream=True,
        )
        # totes = ''
        for chunk in stream:
            x = chunk['message']['content']
            # totes = totes + x
            prnt(x)
            # yield x
        t_end = datetime.datetime.now() - t_start
        prnt(t_end)



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
            prnt(x)
            # yield x
        t_end = datetime.datetime.now() - t_start
        prnt(t_end)
        prnt()
        prnt(totes)
        # json_data = {'prompt':prompt}
        # def get_response():
        #     response = requests.post(url, json=json_data, timeout=600, stream=True)
        #     if response.status_code == 200:
        #         answer = ''
        #         for chunk in response.iter_content(chunk_size=10):
        #             try:
        #                 if chunk:
        #                     prnt(chunk)
        #                     answer = answer + chunk.decode('utf-8')
        #             except Exception as e:
        #                 prnt(str(e))
            
        #     prnt()
        #     prnt(answer)
        #     return answer
        # try:
        #     answer = get_response()
        # except Exception as e:
        #     prnt(str(e))
        #     prnt('-----', datetime.datetime.now() - sum_start_time)
        #     sum_start_time = datetime.datetime.now()
        #     prnt()
        #     answer = get_response()

        prnt('-----', datetime.datetime.now() - sum_start_time)
        # prnt(completion.choices[0].message.content)
        # for chunk in completion:
        #     try:
        #         prnt(chunk.choices[0].message['content'])
        #     except:
        #         prnt('-')
        # prnt('---')
        return totes
    bill = False
    hansard = False
    text = None
    if item.object_type == 'Meeting':
        search = ['%s'%(topic)]
        posts = Post.objects.filter(Statement_obj__Meeting_obj=item).filter(Q(Statement_obj__Terms_array__overlap=search)|Q(Statement_obj__keyword_array__overlap=search))
        post_count = posts.count()
        prnt(posts.count())
        hansard = True
    try:
        spren = Spren.objects.filter(Meeting_obj=item, topic=topic)[0]
    except:
        spren = Spren(Meeting_obj=item, topic=topic)
        spren.type = 'summary'
        spren.DateTime = item.DateTime
        spren.save()
    for i in SprenItem.objects.filter(Spren_obj=spren):
        i.delete()
    prnt('-------------')
    start_time = datetime.datetime.now()
    
    def get_prompt(data, topic, num):
        if num == 1:
            # return "the following is from a parliamentary debate: %s |END| select the most important post related to the topic '%s', and tell me why it is the most important." %(data, topic)
            return "the following is from a parliamentary debate: %s |END| select the most important post related to the topic '%s', and give me just the post_id, do not say anything besides the post_id" %(data, topic)
            # return "the following is from a parliamentary debate: %s |END| select the most important posts related to the topic '%s', and return the post id" %(data, topic)
        elif num == 2:
            return "Read the following text: %s |END| Very briefly present the most important points from the preceeding text to an audience in bullet form, do not go over 2 bullets, do not say anything besides the bullet points, do not say 'Here are the two bullet points'" %(data)
            # return "Present the most important points from the following to an audience in bullet form: %s" %(data)
            # return "Thoroughly summarize the most important points from the following in bullet form: %s" %(data)
        elif num == 3:
            return "Summarize the following in paragraph form: %s" %(data)
    
    n = 0
    m = 0
    total_tokens = 0
    # summaries = ""
    # sum1 = None
    # sum2 = None
    # sum3 = None
    # sum4 = None
    # sum5 = None
    idenList = []
    def run(posts, n, post_count, rounded, promptPosition):
        # z = 7
        prnt('n',n, 'post_count',post_count,'rounded',rounded)
        num_tokens, text = makeText(posts[n:n+rounded])
        if num_tokens != 3945:
            return 'haha', n, post_count
        if num_tokens < 1000:
            try:
                while num_tokens < 1000 and rounded <= (post_count-n):
                    rounded += 2
                    num_tokens, text = makeText(posts[n:n+rounded])
                    if num_tokens > 3500:
                        while num_tokens > 3500 and rounded > 1:
                            rounded -= 1
                            num_tokens, text = makeText(posts[n:n+rounded])
                            if num_tokens < 1000:
                                num_tokens = 1000
            except:
                pass
            if rounded > 1:
                prompt = get_prompt(text, topic, promptPosition)
                result = summarize(prompt)
            else:
                if isinstance(posts[n+rounded], int) or isinstance(posts[n+rounded], str):
                    result = "ppxpp%sqqxqq" %(posts[n+rounded])
                else:
                    result = "ppxpp%sqqxqq" %(posts[n+rounded].Statement_obj.id)
        elif num_tokens < 3500:
            if rounded > 1:
                prompt = get_prompt(text, topic, promptPosition)
                result = summarize(prompt)
            else:
                if isinstance(posts[n+rounded], int) or isinstance(posts[n+rounded], str):
                    result = "ppxpp%sqqxqq" %(posts[n+rounded])
                else:
                    result = "ppxpp%sqqxqq" %(posts[n+rounded].Statement_obj.id)
        else:
            while num_tokens >= 3500 and rounded > 1:
                if rounded > 3:
                    rounded -= 2
                else:
                    rounded -= 1
                prnt('roundedn, n', rounded, n)
                prnt(len(posts))

                num_tokens, text = makeText(posts[n:n+rounded])
            if num_tokens > 3500:
                prnt()
                prnt('num_tokens > 3500')
                q = 0
                while num_tokens > 4000:
                    q += 10
                    text = text[:-q]
                    num_tokens = get_token_count(text, "cl100k_base")
                    prnt('q', q)
                    prnt('num_toeksn', num_tokens)
            if promptPosition == 2:
                prnt('111')
                prompt = get_prompt(text, topic, promptPosition)
                num_tokens = get_token_count(prompt, "cl100k_base")
                prnt('prompt tokens', num_tokens)
                result = summarize(prompt)
            else:
                prnt('22else')
                prnt('len(posts)',len(posts))
                prnt(f'{posts}[{n}+{rounded}]')
                if isinstance(posts[n+rounded], int) or isinstance(posts[n+rounded], str):
                    result = "ppxpp%sqqxqq" %(posts[n+rounded])
                else:
                    result = "ppxpp%sqqxqq" %(posts[n+rounded].Statement_obj.id)
        n += rounded
        if promptPosition == 1:
            x = result.find('ppxpp')+5
            q = result.find('qqxqq')
            try:
                selectedPost = int(result[x:q])
            except:
                selectedPost = 99999999999
            prnt(result)
            prnt(n, '/', rounded)
            prnt('------result', str(selectedPost))
            return selectedPost, n, post_count
        else:
            return result, n, post_count
    if post_count > 7:
        rounded = 7
        if post_count < 35:
            rounded = round(post_count/7)
            # prnt('rounded',rounded)
        prnt('post count', post_count)
        while n < post_count:
            m += 1
            prnt('cycle:', m) # !!!!!!!!!!!!!!!!!!!!!! caught in a loop, should be circumvented by n += 1 below
            

            try:
                selectedPost, n, post_count = run(posts, n, post_count, rounded, 1)
                idenList.append(selectedPost)
            except Exception as e:
                prnt(str(e))
                n += 1
    else:
        # selectedPost, n, t = run(posts, n, t, 1)
        for i in posts:
            idenList.append(i.Statement_obj.id)

    prnt('total tokens', total_tokens)
    prnt('-----next1', datetime.datetime.now() - start_time)
    total = len(idenList)
    prnt(total)
    if total > 7:
        # nextList = []
        rounded = round(total / 7)
        def run2(idenList, total):
            prnt('---run2')
            returnList = []
            n = 0
            while n < total:
                prnt('n:', n, 'total:', total)
                # prnt(idenList[n:n+7])
                try:
                    selectedPost, n, total = run(idenList, n, total, rounded, 1)
                    returnList.append(selectedPost)
                except Exception as e:
                    prnt(str(e))
            return returnList
        
        returnList = run2(idenList, total)
        if len(returnList) > 7:
            while len(returnList) > 7:
                nextList1 = []
                for x in returnList:
                    nextList1.append(x)
                returnList = run2(nextList1, len(returnList))
        idenList = returnList


    prnt('-----next2', datetime.datetime.now() - start_time)

    summary = ""
    idenList = sorted(idenList)
    prnt(idenList)
    for i in idenList:
        # prnt(i)
        try:
            result, n, post_count = run([i], 0, 1, 7, 2)
            # prnt(result)
            if 'Sure' in result or 'Here' in result:
                if "Sure" in result:
                    k = result.find('Sure')
                elif "Hure" in result:
                    k = result.find('Here')
                try:
                    l = result[k:].find('\n')
                    sure = result[:k+l+1]
                    prnt(sure)
                    result = result.replace(sure,'').replace('\n\n', '\n')
                except:
                    pass
            summary = summary + '\n' + result.strip() + '\n---'
            try:
                statement = Statement.objects.filter(id=i)[0]
                try:
                    sprenItem = SprenItem.objects.filter(Spren_obj=spren, Statement_obj=statement)[0]
                except:
                    sprenItem = SprenItem(Spren_obj=spren, Statement_obj=statement)
                sprenItem.content = result.strip()
                sprenItem.save()
                prnt('sprenItem created')
            except Exception as e:
                prnt(str(e))
        except Exception as e:
            prnt('yikes', str(e))
            time.sleep(2)

    spren.content = ''
    spren.save()
    prnt('----summary----')
    prnt(summary)
    prnt('-----')
    prnt('done summarizer', datetime.datetime.now() - start_time)
    prnt(spren)

def summarize_old(prompt):
    prnt('start summarize')
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    url = "https://mkwhgqn52r2yhf-5000.proxy.runpod.net/v1"
    # prnt('---------------', datetime.datetime.now() - start_time, topic)
    client = OpenAI(api_key="EMPTY", base_url=url)
    completion = client.chat.completions.create(
    model="llama-2-13b-chat.Q4_K_M.gguf",
    temperature=0,
    max_tokens=500,
    # stream=True,
    messages=[
        {"role": "system", "content": "You are a non-conversational computer assistant."},
        {"role": "user", "content": prompt}
    ]
    )
        # {"role": "user", "content": "Summarize the most important point from the following parlimentary debate, do not opine, do not go over 250 characters, provide a quote of the point at the end: %s" %(text[:2000])}
        # {"role": "user", "content": "Summarize the main points from the following parlimentary debate, do not opine, do not go over 1000 characters: %s" %(text)}

    # prnt(completion)
    prnt('-----')
    # prnt(completion.choices[0].message.content)
    # for chunk in completion:
    #     try:
    #         prnt(chunk.choices[0].message['content'])
    #     except:
    #         prnt('-')
    # prnt('---')
    return completion.choices[0].message.content

def summarize_topic_old(item, topic):
    bill = False
    hansard = False
    text = None
    if item.object_type == 'hansard':
        search = ['%s'%(topic)]
        posts = Post.objects.filter(hansardItem__hansard=item).filter(Q(hansardItem__Terms__overlap=search)|Q(hansardItem__keywords__overlap=search)).select_related('hansardItem__person', 'hansardItem').order_by('DateTime')
        t = posts.count()
        prnt(posts.count())
        hansard = True
    elif item.object_type == 'bill':
        bill = True
        def strip_tags(text):
            TAG_RE = re.compile(r'<[^>]+>')
            return TAG_RE.sub('', text)
        # if self.bill_text_html:
        text = item.bill_text_html.replace(item.bill_text_nav, '')
        text = strip_tags(text)
        t = len(text)
    prnt('-------------')
    start_time = datetime.datetime.now()
      
    def makeText(data):
        def remove_tags(text):
            try:
                TAG_RE = re.compile(r'<[^>]+>')
                text = TAG_RE.sub('', text).replace('"', "'").replace('\n', '').strip()
                text = ''.join(text.splitlines())
                text = unidecode(text)
                return text
            except:
                return None
        text = ""
        for p in data:
            if len(p.hansardItem.Content) > 100:
                text = text + '%s(%s):\n%s\n\n' %(p.hansardItem.person_name, p.hansardItem.person.party, p.hansardItem.Content)
        text = remove_tags(text)
        # prnt(len(text))
        num_tokens = get_token_count(text, "cl100k_base")
        prnt(num_tokens)
        return num_tokens, text
    def get_prompt(data, topic, num):
        if num == 1:
            return "the following is from a parliamentary debate: %s |END| Summarize the most important points related to the topic '%s' in paragraph form" %(data, topic)
        elif num == 2:
            return "Present the most important points from the following to an audience in bullet form: %s" %(data)
            # return "Thoroughly summarize the most important points from the following in bullet form: %s" %(data)
        elif num == 3:
            return "Summarize the following in paragraph form: %s" %(data)
    def snipText(text, m, z):
        snip = text[m:z]
        z = snip.rfind('. ')
        num_tokens = get_token_count(text[m:z], "cl100k_base")
        prnt(num_tokens)
        return num_tokens, text[m:z], m ,z
    n = 0
    m = 0
    total_tokens = 0
    summaries = ""
    sum1 = None
    sum2 = None
    sum3 = None
    sum4 = None
    sum5 = None
    while n < t:
        m += 1
        prnt('cycle:', m)
        if hansard:
            z = 7
            num_tokens, text = makeText(posts[n:n+z])
            if num_tokens < 1000:
                try:
                    while num_tokens < 1000 and z <= (t-n):
                        z += 2
                        num_tokens, text = makeText(posts[n:n+z])
                except:
                    pass
                prompt = get_prompt(text, topic, 1)
                result = summarize(prompt)
            elif num_tokens < 3500:
                prompt = get_prompt(text, topic, 1)
                result = summarize(prompt)
            else:
                while num_tokens >= 3500 and z > 1:
                    z -= 2
                    num_tokens, text = makeText(posts[n:n+z])
                prompt = get_prompt(text, topic, 1)
                result = summarize(prompt)
        elif bill:
            z = 3000
            num_tokens, text = snipText(text, m, z)
            if num_tokens < 1200:
                while num_tokens < 1200 and z <= (t-n):
                    z += 500
                    num_tokens, text, m, z = snipText(text, m, z)
                prompt = get_prompt(text, None, 3)
                result = summarize(prompt)
            elif num_tokens < 3500:
                prompt = get_prompt(text, topic, 1)
                result = summarize(prompt)
            else:
                while num_tokens >= 3500 and z > 500:
                    z -= 500
                    num_tokens, text, m, z = snipText(text, m, z)
                prompt = get_prompt(text, None, 3)
                result = summarize(prompt)
            
        # prnt(text)
        # prnt('------result')
        n += z
        # prnt(n,'/',z)
        prnt(result)
        summaries = summaries + ' ' + result
        total_tokens += num_tokens
        sum_tokens = get_token_count(summaries, "cl100k_base")
        if sum_tokens > 2000:
            if not sum1:
                prnt('s1',sum_tokens)
                sum1 = summaries
                summaries = ""
            elif not sum2:
                prnt('s2',sum_tokens)
                sum2 = summaries
                summaries = ""
            elif not sum3:
                prnt('s3',sum_tokens)
                sum3 = summaries
                summaries = ""
            elif not sum4:
                prnt('s4',sum_tokens)
                sum4 = summaries
                summaries = ""
            else:
                prnt('s5',sum_tokens)
                sum5 = summaries
                summaries = ""
    prnt('total tokens', total_tokens)
    prnt('-----next1', datetime.datetime.now() - start_time)
    num_tokens = get_token_count(summaries, "cl100k_base")
    prnt(num_tokens)
    if sum1:
        if num_tokens > 2000:
            prnt('sum0')
            prompt = get_prompt(summaries, topic, 1)
            summaries = summarize(prompt)
            prnt(summaries)
            prnt('---')
        prnt('---sum1')
        if hansard:
            prompt = get_prompt(sum1, topic, 1)
        elif bill:
            prompt = get_prompt(sum1, topic, 3)
        result = summarize(prompt)
        # result = summarize(sum1, 1)
        summaries = result + ' ' + summaries
        prnt(result)
    if sum2:
        prnt('---sum2')
        if hansard:
            prompt = get_prompt(sum2, topic, 1)
        elif bill:
            prompt = get_prompt(sum2, topic, 3)
        result = summarize(prompt)
        summaries = summaries + ' ' + result
        prnt(result)
    if sum3:
        prnt('---sum3')
        if hansard:
            prompt = get_prompt(sum3, topic, 1)
        elif bill:
            prompt = get_prompt(sum3, topic, 3)
        result = summarize(prompt)
        summaries = summaries + ' ' + result
        prnt(result)
    if sum4:
        prnt('---sum4')
        if hansard:
            prompt = get_prompt(sum4, topic, 1)
        elif bill:
            prompt = get_prompt(sum4, topic, 3)
        result = summarize(prompt)
        summaries = summaries + ' ' + result
        prnt(result)
    if sum5:
        prnt('---sum5')
        if hansard:
            prompt = get_prompt(sum5, topic, 1)
        elif bill:
            prompt = get_prompt(sum5, topic, 3)
        result = summarize(prompt)
        summaries = summaries + ' ' + result
        prnt(result)
    # if sum1:
    prnt('sumof sums')

    # prnt('----------- summarries')
    # prnt(summaries)
    prnt('-----next2', datetime.datetime.now() - start_time)
    num_tokens = get_token_count(summaries, "cl100k_base")
    prnt(num_tokens)
    # prnt(summaries)
    prnt('-----------final sum:')
    prompt = get_prompt(summaries, topic, 2)
    summaries = summarize(prompt)
    # summaries = summarize(summaries, 2)
    prnt(summaries)
    if hansard:
        try:
            spren = Spren.objects.filter(hansard=item, topic=topic)[0]
        except:
            spren = Spren(hansard=item, topic=topic, type='summary')
        spren.DateTime = hansard.DateTime
        spren.content = summaries[:2000]
    elif bill:
        try:
            spren = Spren.objects.filter(bill=item)[0]
        except:
            spren = Spren(hansard=hansard, type='summary')
        spren.DateTime = bill.LatestCompletedBillStageDateTime
        spren.content = summaries[:3000]
    # spren.save()
    spren.boot()
    # def sum(summary):
    #     client = OpenAI(api_key="EMPTY", base_url=url5)
    #     completion = client.chat.completions.create(
    #     model="llama-2-13b-chat.Q4_K_M.gguf",
    #     temperature=0,
    #     max_tokens=600,
    #     # stream=True,
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {"role": "user", "content": "the following is an outline of a parliamentary debate. State the most important points. Provide only the points, do not say anything else: %s" %(summaries)}
    #     ]
    #     )
    #         # {"role": "user", "content": "Summarize the most important point from the following parlimentary debate, do not opine, do not go over 250 characters, provide a quote of the point at the end: %s" %(text[:2000])}
    #         # {"role": "user", "content": "Summarize the main points from the following parlimentary debate, do not opine, do not go over 1000 characters: %s" %(text)}
    #     return completion.choices[0].message.content
    # prnt(completion)
    # if num_tokens > 5000 and num_tokens < 10000:
    #     x = len(summaries) / 2
    #     prnt('1')
    #     sum1 = sum(summaries[:x])
    #     prnt('2')
    #     sum2 = sum(summaries[x:])
    #     prnt('3')
    #     sumOfSums = sum(sum1 + sum2)
    # else:
    #     sumOfSums = sum(summaries)
    # prnt(sumOfSums)
    prnt('-----')
    prnt('done summarizer', datetime.datetime.now() - start_time)

def get_sort_order(sort):
    if sort == 'Oldest':
        ordering = 'DateTime'
    elif sort == 'Newest':
        ordering = '-DateTime'
    elif sort == 'Random':
        ordering = '?'
    elif sort == 'Loudest':
        ordering = '-rank'
    return ordering

def get_chatgpt_model(text):
    def get_token_count(string: str, encoding_name: str) -> int:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    def reduce_text(text, n):
        text = text[:-n]
        num_tokens = get_token_count(text, "cl100k_base")
        return num_tokens, text
    num_tokens = get_token_count(text, "cl100k_base")
    if num_tokens <= 3500:
        model = 'gpt-3.5-turbo'
    elif num_tokens <= 6000:
        # n = 0
        while num_tokens > 3500:
            # n += 1
            num_tokens, text = reduce_text(text, 500)
        model = 'gpt-3.5-turbo'
    elif num_tokens <= 15500:
        model = 'gpt-3.5-turbo-16k'
    elif num_tokens > 15500:
        # n = 0
        while num_tokens > 15500 and num_tokens > 4000:
            # n += 1
            while num_tokens > 20000:
                num_tokens, text = reduce_text(text, 5000)
            num_tokens, text = reduce_text(text, 500)
        model = 'gpt-3.5-turbo-16k'
    return model, text

def get_party(list):
    people_list = []
    for p in list:
        people_list.append(p.Person)
    roles = Role.objects.filter(Person_obj__in=people_list).exclude(Party_obj=None).select_related('Party_obj')
    prnt('parties')
    prnt(roles.count())
    return roles

def sprenderize(debate):
    prnt('sprenderizing')
    url = 'http://x.x.x.x:3009/llamarun/'
    update = Update.objects.filter(Meeting_obj=debate)[0]
    data = json.loads(update.data)
    terms_array = json.loads(data['Terms'])
    if terms_array:
        n = 0
        t = 0
        for topic, count in terms_array.items():
            prnt(topic, '--', count)
            t += 1
            search = ['%s'%(topic)]
            prnt(search)
            posts = Post.objects.filter(Statement_obj__Meeting_obj=debate).filter(Q(Statement_obj__Terms_array__overlap=search)|Q(Statement_obj__keyword_array__overlap=search))
            # # num_tokens, text = makeText(posts)
            prnt('posts.count()', posts.count())
            # prnt('num_tokens', num_tokens)
            if count == 6:
                num_tokens, text = makeText(posts)
                if count >= 6 and num_tokens >= 600 or num_tokens > 1200:
                    prnt(topic, num_tokens, count)
                    # summarize_topic(hansard, topic)
                    # try:
                    #     spren = Spren.objects.filter(Meeting_obj=debate, topic=topic)[0]
                    # except:
                    #     spren = Spren(Meeting_obj=debate, topic=topic)
                    #     spren.type = 'summary'
                    #     spren.content = 'TBD'
                    #     spren.DateTime = debate.DateTime
                    #     # spren.create_post()
                    #     spren.save()
                    # n += 1
                    # summarize_topic(debate, topic, url)
                    break
        # from utils.models import run_runpod
        # queue = django_rq.get_queue('default')
        # queue.enqueue(run_runpod, job_timeout=3600)
        # prnt('end', n, t)

    prnt('fini')

# def get_wordCloud(request, text):
#     prnt('start wordcloud')
#     try:
#         theme = request.COOKIES['theme']
#     except:
#         theme = 'day'
#     import matplotlib
#     matplotlib.use('SVG')
#     # # Start with one review:
#     # bill = Bill.objects.exclude(first_reading_html=None)[4]
#     # prnt(bill.NumberCode)
#     # prnt(bill.LongTitleEn)
#     # cleantext = BeautifulSoup(bill.first_reading_html, "lxml").text

#     # p = Person.objects.filter(first_name='Pierre', last_name='Poilievre')[1]
#     # prnt(p)
#     # hansards = HansardItem.objects.filter(person=p)
#     # prnt(hansards.count())
#     # cleantext = ''
#     # for h in hansards:
#     #     cleantext = cleantext + ' ' + h.Content
#     # cleantext = BeautifulSoup(cleantext, "lxml").text
    
#     # Create stopword list:
#     stopwords = set(STOPWORDS)
#     stopwords.update(["C", "Canada", "House", 'Commons', 'Parliament', 'Government', 'Speaker', 'Canadian', 'Canadians', 'Mr','Madam', 'Paragraph', 'Act', 'subsection', 'section'])
#     if theme == 'night':
#         wordcloud = WordCloud(height=500, width=1000, stopwords=stopwords, background_color="#222222").generate(text)
#     else:
#         wordcloud = WordCloud(height=500, width=1000, stopwords=stopwords, background_color='white').generate(text)
#     # prnt('1')
#     plt.imshow(wordcloud)
#     plt.axis("off")
#     prnt('2')
#     # wordcloud = plt.show()
#     image = ''
#     image = io.BytesIO()
#     prnt('2a')
#     plt.savefig(image, format="png")
#     prnt(len(image.read()))
#     image.seek(0)
#     string = base64.b64encode(image.read())
#     # prnt('4')
#     image_64 = "data:image/png;base64," +   urllib.parse.quote_plus(string)
#     # prnt('done:', image_64)
#     prnt('5')
#     return image_64


def getMyRepVotes(user, setlist):
    my_rep = {}
    if setlist and setlist[0].object_type != 'toppost':
        for p in setlist:
            if p.object_type == 'Motion' or p.pointerType == 'Motion':
                # prnt(p)
                try:
                    try:
                        x = p.Motion_obj
                    except:
                        x = p
                    if x.Chamber == 'House':
                        r = Role.objects.filter(District=user.Federal_District_obj, current=True)[0]
                    else:
                        r = Role.objects.filter(District=user.ProvState_District_obj, current=True)[0]
                    v = Vote.objects.filter(Motion_obj=x, Person_obj=r.Person_obj)[0]
                    # prnt(v)
                    my_rep[p.id] = v
                except Exception as e:
                    # prnt(str(e))
                    pass
    return my_rep

def get_matches(user, person, govs):
    # prnt('get matches')
    # prnt(organization)
    # gov = Government.objects.filter(organization=organization)[0]
    # if organization == 'Federal':
    #     provState = None
    # else: 
    #     provState = Region.objects.filter(name=organization)[0]
    # prnt(prov)
    actions = UserAction.objects.filter(User_obj=user, Post_obj__pointerType='Bill').filter(Post_obj__Bill_obj__Government_obj__in=govs).order_by('-Post_obj__DateTime')
    votes = {}
    my_votes = {}
    return_votes = []
    vote_matches = 0
    total_matches = 0
    match_percentage = None
    for r in actions:
        try:
            bill = r.Post_obj.Bill_obj
            if r.isYea:
                votes[bill] = 'Yea'
            elif r.isNay:
                votes[bill] = 'Nay'
            # prnt(r.isYea, r.isNay)
        except:
            pass
    matched = []
    def match_vote(m, person, votes, bill, vote_matches, total_matches, return_votes):
        try:
            v = Vote.objects.filter(Motion_obj=m, Person_obj=person).order_by('-Motion_obj__DateTime')[0]
            total_matches += 1
            return_votes.append(v)
            if v.VoteValueName == votes[bill]:
                vote_matches += 1
                # prnt('match')
            return 'match', vote_matches, total_matches, return_votes
        except Exception as e:
            pass
        return 'nomatch', vote_matches, total_matches, return_votes
    for bill in votes:
        # prnt('------', bill)
        # prnt(billVersion)
        # prnt(votes[billVersion])
        try:
            motions = Motion.objects.filter(Bill_obj=bill).order_by('-DateTime')
            for m in motions:
                my_votes[m.id] = votes[bill]
                result, vote_matches, total_matches, return_votes = match_vote(m, person, votes, bill, vote_matches, total_matches, return_votes)
                if result == 'match':
                    matched.append(m)
                    break
        except Exception as e:
            prnt(str(e))
    # prnt(vote_matches, '/', total_matches)
    try:
        match_percentage = int((vote_matches / total_matches) * 100)
    except Exception as e:
        # prnt(str(e))
        match_percentage = None
    # prnt(match_percentage)
    return match_percentage, total_matches, vote_matches, my_votes, return_votes