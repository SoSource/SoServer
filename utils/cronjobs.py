# from unittest.result import failfast
from django.db import models
from django.db.models import Q, Avg
from collections import Counter

import django_rq
from rq import Queue
from worker import conn

# from accounts.models import *
# from accounts.models import Notification as UserNotification
# from posts.models import *
# from posts.utils import summarize_topic
# from scrapers.canada.federal import *
# import scrapers.canada.prov.ontario as ontario
from blockchain.models import tasker, DataPacket


from firebase_admin.messaging import Notification as fireNotification
from firebase_admin.messaging import Message as fireMessage
# from fcm_django.models import FCMDevice
import datetime
from datetime import date
from django.utils import timezone
import requests
import feedparser
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pytz
import time
import re
import random
import json
import os
# from openai import OpenAI
# from collections import OrderedDict
# from operator import itemgetter
import operator
from unidecode import unidecode

from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

from blockchain.models import script_created_modifiable_models
from utils.models import prnt, get_model, now_utc

# # 20gb demand
# twenty_pod_id = '9kzmbd8wyowzue'
# twenty_url = "https://9kzmbd8wyowzue-5000.proxy.runpod.net/v1"

# #48gb spot
# fourtyeight_pod_id = 'mkwhgqn52r2yhf'
# fourtyeight_url = "https://mkwhgqn52r2yhf-5000.proxy.runpod.net/v1"

runTimes = {
    'daily_summarizer' : 500,
    'send_notifications' : 200,
    'check_elections': 200,
    'updateTop': 200,
}

functions = [
    #  {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : ['x'], 'cmds' : ['updateTop']},
     {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [8], 'cmds' : ['daily_summarizer', 'check_elections']},
     {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [12], 'cmds' : ['check_elections']},
     {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [18], 'cmds' : ['send_notifications','check_elections']},
     {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [24], 'cmds' : ['check_elections']},

]

def remove_old_modded_items():
    for m in script_created_modifiable_models:
        model = get_model(m)
        objs = model.objects.exclude(proposed_modification=None).filter(last_updated__lte=now_utc() - datetime.timedelta(days=5))
        if objs:
            for obj in objs:
                super(get_model(obj.object_type), obj).delete()

def task_runner():
    prnt('-------task_runner')
    queue = django_rq.get_queue('main')
    queue.enqueue(tasker, now_utc(), job_timeout=300)

def clear_chrome():
    import subprocess, signal
    import os
    try:
        p = subprocess.Popen(['pgrep', '-l' , 'chrome'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():        
            line = bytes.decode(line)
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)
    except Exception as e:
        prnt('clear chrome fail 2123', str(e))
    try:
        subprocess.call(["pkill", "-f", "Google Chrome for Testing"])
    except Exception as e:
        prnt('clear chrome fail 3462', str(e))
    try:
        subprocess.call(["pkill", "-f", "chrome_crashpad_handler"])
    except Exception as e:
        prnt('clear chrome fail 863', str(e))
    try:
        subprocess.call(["pkill", "-f", "chrome"])
    except Exception as e:
        prnt('clear chrome fail 2845', str(e))
    try:
        subprocess.call(["pkill", "-f", "chromedriver"])
    except Exception as e:
        prnt('clear chrome fail 4567', str(e))


def clear_jold_obs():
    import django_rq
    from rq.registry import FailedJobRegistry

    failed_registry = FailedJobRegistry('main', connection=django_rq.get_connection())
    n = 0
    for job_id in reversed(failed_registry.get_job_ids()):
        n += 1
        if n > 500:
            try:
                failed_registry.remove(job_id, delete_job=True)
            except:
                # failed jobs expire in the queue. There's a
                # chance this will raise NoSuchJobError
                pass

def daily_summarizer(today):
    prnt('run daily')
    # sozed = User.objects.get(username='Sozed')
    # sozed.alert('%s-%s' %(datetime.datetime.now(), 'minute run', 'body'))
    if not today:
        # today = date.today() - datetime.timedelta(days=16)
        today = date.today()
    thisMorning = datetime.datetime.combine(today, datetime.datetime.min.time())
    yesterdayMorning = today - datetime.timedelta(days=1)
    prnt(thisMorning)
    prnt(yesterdayMorning)
    try:
        houseHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization='House')[0]
    except:
        houseHansard = None
    try:
        senateHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization='Senate')[0]
    except:
        senateHansard = None
    prnt('hnsards:')
    prnt(houseHansard)
    prnt(senateHansard)

    def run(item, houseHansard, senateHansard):
        prnt('------run', today)
        houseTopics = [('None', 0)]
        senateTopics = [('None', 0)]
        provTopics = [('None', 0)]
        user = None
        province= None
        line2 = ''
        line3 = ''
        line4 = ''
        line5 = ''
        line6 = ''
        text1 = ''
        text2 = ''
        text3 = ''
        text4 = ''
        text5 = ''
        text6 = ''
        if houseHansard:
            houseTopics = houseHansard.list_all_terms()
        if senateHansard:
            senateTopics = senateHansard.list_all_terms()
        if not item:
            prnt('not item')
            if houseHansard and senateHansard:
                line1 = 'The House and Senate were in session'
            elif houseHansard:
                line1 = 'The House was in session'
            elif senateHansard:
                line1 = 'The Senate was in session'
            # prnt(line1)
            latestBills = Bill.objects.filter(LatestBillEventDateTime__gte=yesterdayMorning, LatestBillEventDateTime__lte=thisMorning).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true'))
            # if latestBills.count() > 1:
            line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s, %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode, latestBills[0].ShortTitle) 
            # elif latestBills.count() > 0:
            #     line2 = "<a href='/bill?date=%ss'>%s Bills</a> were discussed including <a href='%s'>Bill %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode) 
            # prnt(line2)
            latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate'))
            passedMotions = 0
            for m in latestMotions:
                if m.yeas > m.nays:
                    passedMotions += 1
            if latestMotions.count() > 1:
                line3 = "<a href='/motions?date=%s'>%s Motions</a> were held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
                text3 = "%s Motions were held, %s Passed" %(latestMotions.count(), passedMotions)
            
            elif latestMotions.count() == 1:
                line3 = "<a href='/motions?date=%s'>%s Motion</a> was held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
                text3 = "%s Motion was held, %s Passed" %(latestMotions.count(), passedMotions)
            
            topTopics = {}
            if houseHansard:
                for key, value in houseTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(houseHansard.get_absolute_url(), key)]
            if senateHansard:
                for key, value in senateTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(senateHansard.get_absolute_url(), key)]

            topTopics = sorted(topTopics.items(), key=operator.itemgetter(1),reverse=True)
            # prnt(topTopics)
            if len(topTopics) > 0:
                q = list(topTopics)
                line6 = "<a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a> and <a href='/topic/%s?date=%s'>(%s) %s</a>" %(q[0][0], yesterdayMorning, q[0][1][0], q[0][0], q[1][0], yesterdayMorning, q[1][1][0], q[1][0],  q[2][0], yesterdayMorning, q[2][1][0], q[2][0], q[3][0], yesterdayMorning, q[3][1][0], q[3][0])
            # prnt(line6)
        elif item.object_type == 'province':
            # prnt('item province')
            province = item
            try:
                provHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization=province.name +'-Assembly')[0]
                provTopics = provHansard.list_all_terms()
            except:
                provHansard = None
            if houseHansard and senateHansard and provHansard:
                line1 = 'The House, Senate and Assembly were in session'
            elif houseHansard and provHansard:
                line1 = 'The House and Assembly were in session'
            elif provHansard and senateHansard:
                line1 = 'The Senate and Assembly were in session'
            elif houseHansard and senateHansard:
                line1 = 'The House and Senate were in session'
            elif provHansard:
                line1 = 'The Assembly was in session'
            elif houseHansard:
                line1 = 'The House was in session'
            elif senateHansard:
                line1 = 'The Senate was in session'

            latestBills = Bill.objects.filter(LatestBillEventDateTime__gte=yesterdayMorning, LatestBillEventDateTime__lte=thisMorning).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true')|Q(province=province))
            # if latestBills.count() > 1:
            #     line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s</a> and <a href='%s'>Bill %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode, latestBills[1].get_absolute_url(), latestBills[1].NumberCode) 
            # elif latestBills.count() > 0:
            line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s, %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode, latestBills[0].ShortTitle) 
            
            latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate')|Q(OriginatingChamberName=province.name +'-Assembly'))
            passedMotions = 0
            for m in latestMotions:
                if m.yeas > m.nays:
                    passedMotions += 1
            if latestMotions.count() > 1:
                line3 = "<a href='/motions?date=%s'>%s Motions</a> were held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
                text3 = "%s Motions were held, %s Passed" %(latestMotions.count(), passedMotions)
            
            elif latestMotions.count() == 1:
                line3 = "<a href='/motions?date=%s'>%s Motion</a> was held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
                text3 = "%s Motion was held, %s Passed" %(latestMotions.count(), passedMotions)
            
            
            topTopics = {}
            if houseHansard:
                # prnt(houseTopics)
                for key, value in houseTopics:
                    if key not in skipwords:
                        # prnt('--%s--' %(key))
                        topTopics[key] = [value, "%s/?topic=%s" %(houseHansard.get_absolute_url(), key)]
            if senateHansard:
                for key, value in senateTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(senateHansard.get_absolute_url(), key)]
            if provHansard:
                for key, value in provTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(provHansard.get_absolute_url(), key)]
            topTopics = sorted(topTopics.items(), key=operator.itemgetter(1),reverse=True)
            if len(topTopics) > 0:
                q = list(topTopics)
                line6 = "<a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a> and <a href='/topic/%s?date=%s'>(%s) %s</a>" %(q[0][0], yesterdayMorning, q[0][1][0], q[0][0], q[1][0], yesterdayMorning, q[1][1][0], q[1][0],  q[2][0], yesterdayMorning, q[2][1][0], q[2][0], q[3][0], yesterdayMorning, q[3][1][0], q[3][0])

        elif item.object_type == 'user':
            # prnt('item user')
            user = item
            try:
                province = user.province
            except:
                pass
            try:
                provHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization=province.name +'-Assembly')[0]
                provTopics = provHansard.list_all_terms()
            except:
                provHansard = None
            if houseHansard and senateHansard and provHansard:
                line1 = 'The House, Senate and Assembly were in session'
            elif houseHansard and provHansard:
                line1 = 'The House and Assembly were in session'
            elif provHansard and senateHansard:
                line1 = 'The Senate and Assembly were in session'
            elif houseHansard and senateHansard:
                line1 = 'The House and Senate were in session'
            elif provHansard:
                line1 = 'The Assembly was in session'
            elif houseHansard:
                line1 = 'The House was in session'
            elif senateHansard:
                line1 = 'The Senate was in session'
            
            latestBills = Bill.objects.filter(LatestBillEventDateTime__gte=yesterdayMorning, LatestBillEventDateTime__lte=thisMorning).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true')|Q(province=province))
            matchedBills = []
            # prnt('start')
            for b in latestBills:
                if b in user.follow_bill.all():
                    matchedBills.append(b)
            # prnt(matchedBills)
            if len(matchedBills) == 0:
                for b in latestBills[:2]:
                    matchedBills.append(b)
            # prnt(matchedBills)
            if len(matchedBills) > 1:
                line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s, %s</a>" %(yesterdayMorning, latestBills.count(), matchedBills[0].get_absolute_url(), matchedBills[0].NumberCode, matchedBills[0].ShortTitle) 
                text2 = "%s Bills were discussed including Bill %s, %s" %(latestBills.count(), matchedBills[0].NumberCode, matchedBills[1].ShortTitle) 
            elif len(matchedBills) > 0:
                line2 = "<a href='%s'>Bill %s, %s</a> was discussed" %(matchedBills[0].get_absolute_url(), matchedBills[0].NumberCode, matchedBills[0].ShortTitle) 
                text2 = "Bill %s was discussed, %s" %(matchedBills[0].NumberCode, matchedBills[0].ShortTitle) 
            
            if provHansard:
                latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate')|Q(OriginatingChamberName=province.name +'-Assembly'))
            else:
                latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate'))
            passedMotions = 0
            for m in latestMotions:
                if m.yeas > m.nays:
                    passedMotions += 1
            if latestMotions.count() > 1:
                line3 = "<a href='/motions?date=%s'>%s Motions</a> were held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
                text3 = "%s Motions were held, %s Passed" %(latestMotions.count(), passedMotions)
            
            elif latestMotions.count() == 1:
                line3 = "<a href='/motions?date=%s'>%s Motion</a> was held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
                text3 = "%s Motion was held, %s Passed" %(latestMotions.count(), passedMotions)
            

            topTopics = {}
            if houseHansard:
                for key, value in houseTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(houseHansard.get_absolute_url(), key)]
            if senateHansard:
                for key, value in senateTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(senateHansard.get_absolute_url(), key)]
            if provHansard:
                for key, value in provTopics:
                    if key not in skipwords:
                        topTopics[key] = [value, "%s/?topic=%s" %(provHansard.get_absolute_url(), key)]
            original_topTopics = topTopics
            topTopics = sorted(topTopics.items(), key=operator.itemgetter(1),reverse=True)
            
            matchedKeys = {}
            # prnt(user.get_follow_topics())
            keys = []
            if len(user.get_follow_topics()) > 0:
                n = 0
                for key in user.get_follow_topics():
                    # prnt(key)
                    if key in topTopics:
                        matchedKeys[key] = topTopics[key][0][0]
                        n += 1
                        if n == 3:
                            break
                if n < 3 and user.keywords:
                    firstKeys = user.keywords
                    counter = Counter(firstKeys)
                    userKeys = counter.most_common(300)
                    # prnt(userKeys)
                    # for topic in topTopics:
                    #     # prnt(topic[0])
                    #     if topic[0] in user.keywords and topic[0] not in skipwords:
                    #         # prnt(topic[0], topic[1][0])
                    #         matchedKeys[topic[0]] = topic[1][0]
                    #         n += 1
                    #         if n == 3:
                    #             break
                    topicList = []
                    for t in topTopics:
                        if t[0] not in topicList:
                            topicList.append(t[0])
                    for key in userKeys:
                        # prnt(key[0])
                        if key[0] in topicList:
                            matchedKeys[key[0]] = original_topTopics[key[0]][0]
                            n += 1
                            if n == 3:
                                break
                # prnt(matchedKeys)
                keys = list(matchedKeys)
                # prnt(keys)
                for key in keys[:3]:
                    line4 = line4 + "<a href='/topic/%s?date=%s'>(%s) %s</a>, " %(key, yesterdayMorning, matchedKeys[key], key)
                    text4 = text4 + "(%s) %s, " %(matchedKeys[key], key)

                x = line4.rfind(',')
                if len(matchedKeys) > 1:
                    w = ' were'
                else:
                    w = ' was'
                if line4:
                    line4 = line4[:x] + '%s discussed' %(w)
                    if len(matchedKeys) > 1:
                        x = line4.rfind(',')
                        line4 = line4[:x] + ' and ' + line4[x+1:]

                    x = text4.rfind(',')
                    text4 = text4[:x] + '%s discussed' %(w)
                    if len(matchedKeys) > 1:
                        x = text4.rfind(',')
                        text4 = text4[:x] + ' and ' + text4[x+1:]

                # if len(keys) == 3:
                #     line4 = "<a href='/topic/%s'>(%s) %s</a>, <a href='/topic/%s'>(%s) %s</a> and <a href='/topic/%s'>(%s) %s</a> were discussed" %(keys[0][0], keys[0][1], keys[0][0], keys[1][0], keys[1][1], keys[1][0], keys[2][0], keys[2][1], keys[2][0])
                # elif len(keys) == 2:
                #     line4 = "<a href='/topic/%s'>(%s) %s</a> and <a href='/topic/%s'>(%s) %s</a> were discussed" %(keys[0][0], keys[0][1], keys[0][0], keys[1][0], keys[1][1], keys[1][0])
                # elif len(keys) == 1:
                #     line4 = "<a href='/topic/%s'>(%s) %s</a> was discussed" %(keys[0][0], keys[0][1], keys[0][0])
            # prnt('----', topTopics)
            if len(topTopics) > 0:
                q = []
                n = 0
                for t in topTopics:
                    # prnt(t)
                    if t[0] not in keys and t[0] not in skipwords:
                        # prnt('append')
                        q.append(t)
                        n += 1
                        if n == 4:
                            break
                # prnt(q)z]
                # q = list(topTopics)
                line6 = "<a href='/topic/%s?date=%s'>(%s) %s,</a> <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>" %(q[0][0], yesterdayMorning, q[0][1][0], q[0][0], q[1][0], yesterdayMorning, q[1][1][0], q[1][0],  q[2][0], yesterdayMorning, q[2][1][0], q[2][0], q[3][0], yesterdayMorning, q[3][1][0], q[3][0])
                text6 = "(%s) %s, (%s) %s, (%s) %s, (%s) %s" %(q[0][1][0], q[0][0], q[1][1][0],  q[1][0], q[2][1][0], q[2][0], q[3][1][0], q[3][0])

            # prnt(user.follow_person.all())
            if user.follow_person.all().count() > 0:
                if provHansard:
                    hansards = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Q(Organization='Senate')|Q(Organization='House')|Q(Organization=province.name +'-Assembly'))
                else:
                    hansards = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Q(Organization='Senate')|Q(Organization='House'))
                personMatches = {}
                for person in user.follow_person.all():
                    # prnt(person)
                    try:
                        # prnt(hansards)
                        hansardItem = HansardItem.objects.filter(hansard__in=hansards, person=person)[0]
                        # prnt(hansardItems)
                        personMatches[person] = '%s?speaker=%s&date=%s' %(hansardItem.hansard.get_absolute_url(), person.id, yesterdayMorning)
                    except Exception as e: 
                        prnt(str(e))
                people = list(personMatches)
                # prnt(personMatches)
                if len(people) > 1:
                    for person in people[:4]:
                        personLink = personMatches[person]
                        line5 = line5 + "<a href='/%s'>%s</a>, " %(personLink, str(person.get_name()))
                        text5 = text5 + "%s, " %(str(person.get_name())) 
                    x = line5.rfind(',')
                    line5 = line5[:x] + ' spoke in Parliament'
                    x = line5.rfind(',')
                    line5 = line5[:x] + ' and ' + line5[x+1:]

                    x = text5.rfind(',')
                    text5 = text5[:x] + ' spoke in Parliament'
                    x = text5.rfind(',')
                    text5 = text5[:x] + ' and ' + text5[x+1:]

                    # line5 = "<a href='%s'>%s</a> and <a href='%s'>%s</a> spoke in Parliament" %(people[0][1], people[0][0].get_name(), people[1][1], people[1][0].get_name())
                    # text5 = "%s and %s spoke in Parliament" %(people[0][0].get_name(), people[1][0].get_name())
                elif len(people) == 1:
                    # prnt('2,', people)
                    person = people[0]
                    personLink = personMatches[people[0]]
                    # prnt(person)
                    try:
                        terms = {}
                        hansardItems = HansardItem.objects.filter(hansard__in=hansards, person=person)
                        for hansardItem in hansardItems:
                            # prnt(hansardItem)
                            for t in hansardItem.Terms:
                                # prnt(t)
                                if t not in skipwords:
                                    if t not in terms:
                                        terms[t] = 1
                                    else:
                                        terms[t] += 1
                        # prnt(terms)
                        H_terms = sorted(terms.items(), key=operator.itemgetter(1),reverse=True)
                        
                        # prnt('222')
                        # prnt(H_terms)
                        # prnt(person.id)
                        # prnt(H_terms[0])
                        termLink = "%s?topic=%s&speaker=%s&date=%s" %(hansardItems[0].hansard.get_absolute_url(), H_terms[0][0], person.id, yesterdayMorning)
                        # prnt(termLink)
                        if len(H_terms) > 1:
                            total = len(H_terms) - 1
                            line5 = "<a href='%s'>%s</a> spoke on <a href='%s'>%s</a> and %s other topics" %(personLink, person.get_name(), termLink, H_terms[0][0], total)
                            text5 = "%s spoke on %s and %s other topics" %(person.get_name(), H_terms[0][0], total)
                        else:
                            line5 = "<a href='%s'>%s</a> spoke on <a href='%s'>%s</a>" %(personLink, person.get_name(), termLink, H_terms[0][0])
                            text5 = "%s spoke on %s" %(person.get_name(), H_terms[0][0])
                        # prnt('---------------------',line5)
                    except Exception as e:
                        prnt(str(e))

        code = '<li>' + line1 + '</li>' + '\n<br>' 
        if line2:
            code = code + '<li>' + line2 + '</li>' + '\n' 
        if line3:
            code = code + '<li>' + line3 + '</li>' + '\n'
        if user:
            if line4:
                code = code + '<li>' + line4 + '</li>' + '\n'
            if line5:
                code = code + '<li>' + line5 + '</li>' + '\n'
        code = code + '<br>' + '<li>Top Topics:</li>' + '\n' + '<li>' + line6 + '</li>'

        text = line1 + '\n\n' 
        if text2:
            text = text + text2 + '\n' 
        if text3:
            text = text + text3 + '\n'
        if user:
            if text4:
                text = text + text4 + '\n' 
            if text5:
                text = text + text5 + '\n'
        text = text + '\n' + 'Top Topics:' + '\n' + text6 
        return code, text


    thisMorning = datetime.datetime.combine(today, datetime.datetime.min.time())
    yesterday = thisMorning - datetime.timedelta(days=1)
    try:
        code, text = run(None, houseHansard, senateHansard)
        try:
            daily = Daily.objects.filter(date_time=thisMorning - datetime.timedelta(days=1), organization='Federal')[0]
        except:
            daily = Daily(date_time=thisMorning - datetime.timedelta(days=1), organization='Federal')
        daily.content = code
        daily.create_post()
        try:
            n = Notification.objects.filter(title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())[0]
        except:
            n = Notification(title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())
        # n.save()
        # n.created = yesterday    
            n.save()
    except Exception as e:
        prnt('FFAAAIILLL1111111', str(e))

    for p in Province.objects.filter(is_supported=True):
        try:
            code, text = run(p, houseHansard, senateHansard)
            try:
                daily = Daily.objects.filter(date_time=thisMorning - datetime.timedelta(days=1), organization=p.name)[0]
            except:
                daily = Daily(date_time=thisMorning - datetime.timedelta(days=1), organization=p.name)
            daily.content = code
            daily.create_post()
            try:
                n = Notification.objects.filter(province=p, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())[0]
            except:
                n = Notification(province=p, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())
            # n.save()
            # n.created = yesterday    
                n.save()
        except Exception as e:
            prnt('FFAAAIILLL1122222222', str(e))

    for u in User.objects.all():
        try:
            code, text = run(u, houseHansard, senateHansard)
            try:
                alert = False
                daily = Daily.objects.filter(date_time=thisMorning - datetime.timedelta(days=1), user=u)[0]
            except:
                alert = True
                daily = Daily(date_time=thisMorning - datetime.timedelta(days=1), user=u)
            daily.content = code
            daily.create_post()
            # try:
            #     n = Notification.objects.filter(user=u, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())[0]
            # except:
            #     n = Notification(user=u, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())
            # # n.save()
            # # n.created = yesterday    
            #     n.save()
            if alert:
                u.alert('Yesterday in Parliament', daily.get_absolute_url(), text)
        
        except Exception as e:
            prnt('FFAAAIILL3333333331', str(e))
    # prnt('1------')
    # prnt(code)
    # prnt('2------')
    # prnt(text)

def send_notifications(value):
    prnt('running send notifications')
    parl = Parliament.objects.filter(organization='Federal')[0]
    if value == None:
        users = User.objects.filter(receiveNotifications=True).order_by('-last_login')
    else:
        users = User.objects.filter(username=value).order_by('-last_login')
    # prnt(users)
    for u in users:
        # prnt(u)
        exclude_list = []
        notifs = UserNotification.objects.filter(user=u)[:100]
        for n in notifs:
            exclude_list.append(n.link)
        if u.province:
            prov = Parliament.objects.filter(organization=u.province.name)[0]
        else:
            prov = None
        # try:
        try:
            # find something of interest
            counter = Counter(u.keywords)
            commonKeys = counter.most_common()
            # prnt(commonKeys)
            bills = Bill.objects.exclude(absolute_url__in=exclude_list).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true')|Q(province=u.province)).filter(keywords__overlap=u.keywords).exclude(bill_text_html=None).filter(LatestBillEventDateTime__gte=datetime.datetime.now()-datetime.timedelta(days=30)).order_by('?')
            querylist = {}
            for b in bills:
                q = [s for s in commonKeys if any(xs in s for xs in b.keywords)]
                for w in q:
                    if w[0] not in skipwords:
                        if b in querylist:
                            querylist[b] += w[1]
                        else:
                            querylist[b] = w[1]

            querylist = sorted(querylist.items(), key=operator.itemgetter(1),reverse=True)
            bill = querylist[0]
        except:
        # if bills.count() == 0:
            if prov:
                bill = Bill.objects.filter(Q(parliament=parl)|Q(parliament=prov)).exclude(absolute_url__in=exclude_list).exclude(bill_text_html=None).order_by('?')[0]
            else:
                bill = Bill.objects.filter(parliament=parl).exclude(absolute_url__in=exclude_list).exclude(bill_text_html=None).order_by('?')[0]
        title = "%s Bill %s" %(bill.OriginatingChamberName.replace('-',' '), bill.NumberCode)
        # title = 'Bill %s' %(bill.NumberCode)
        if bill.ShortTitle:
            body = str(bill.ShortTitle)
        else:
            body = str(bill.LongTitleEn)
        # prnt('u.alert')
        u.alert(title=title, link=bill.get_absolute_url(), body=body)
            # fcm_device.send_message(Message(notification=Notification(title=title), data={"click_action" : "FLUTTER_NOTIFICATION_CLICK","link" : b.get_absolute_url()}))
            # prnt('break')
            # break
        # except Exception as e:
        #     prnt(str(e))

def check_elections():
    elections = Election.objects.filter(end_date__lt=datetime.datetime.today(), ongoing=True)
    for q in elections:
        q.ongoing = False
        q.save()


def tester_queue():
    start_time = datetime.datetime.now()
    prnt(start_time)
    prnt('\n')

    tester()
    # ontario.get_all_hansards('latest')
    # get_senate_hansards('latest')
    # start_date = '%s-%s-%s' %(2023, 2, 9)
    # day = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    # start_day = datetime.datetime.strftime(day, '%Y-%m-%d')
    # end_date = '%s-%s-%s' %(2023, 2, 22)
    # day = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    # end_day = datetime.datetime.strftime(day, '%Y-%m-%d')

    # queue = django_rq.get_queue('default')
    # queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)

    # queue = django_rq.get_queue('default')
    # queue.enqueue(tester, job_timeout=7200)

    # queue = django_rq.get_queue('default')
    # queue.enqueue(get_all_agendas, job_timeout=7200)
    
    # queue = django_rq.get_queue('default')
    # queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
    
    # jt = Person.objects.filter(first_name='Justin', last_name='Trudeau')[0]
    # keywords = Keyphrase.objects.filter(text=jt.first_last())
    # for k in keywords:
    #     prnt(k)
    # # get_all_MPs('alltime')
    # # get_senators()
    # # set_party_colours()
    # # get_all_bills('latest')
    # get_all_bills('alltime')
    # get_all_agendas() #includes house committees and house hansards
    # get_committee_work('latest')
    # get_latest_house_motions()
    # # # get_all_house_motions()
    # get_senate_motions('latest')

    # # get_all_senate_committees()
    # get_latest_senate_committees('past')
    # get_senate_committee_work('latest')
    # get_senate_hansards('latest')
    # get_senate_agenda('latest')
    # # get_all_past_mps()
    prnt('\n')
    prnt('done')
    end_time = datetime.datetime.now()
    prnt(end_time - start_time)


def tester():
    prnt('test success')
    start_time = datetime.datetime.now()
    
    
    # versions = ['First Reading','Second Reading','Third Reading','Royal Assent']
    # for version in versions:
    #     try:
    #         v = BillVersion.objects.filter(bill=bill, version=version)[0]
    #     except:
    #         v = BillVersion(bill=bill, version=version, code=bill.NumberCode, province=prov)
    #         if version == 'First Reading':
    #             v.current = True
    #             v.empty = False
    #         v.save()
    #         v.create_post()
    
    # versions = ['House First Reading', 'House Second Reading','House Third Reading', 'Senate First Reading', 'Senate Second Reading', 'Senate Third Reading', 'Royal Assent']
    # for version in versions:
    #     try:
    #         v = BillVersion.objects.filter(bill=bill, version=version)[0]
    #     except:
    #         v = BillVersion(bill=bill, version=version, code=bill.NumberCode)
    #         if origin == 'Senate':
    #             if version == 'Senate First Reading':
    #                 v.empty = False
    #                 v.current = True
    #             else:
    #                 v.empty = True
    #         else:
    #             if version == 'House First Reading':
    #                 v.empty = False
    #                 v.current = True
    #             else:
    #                 v.empty = True
    #         v.save()
    #         v.create_post()
    try:
        c = Country.objects.filter(name='USA')[0]
        prnt(c)
    except:
        c = Country(name='USA')
        
        prnt(c, 'created')
    c.menu_items = []
    c.menu_items.append('Bills')
    c.menu_items.append('Debates')
    c.menu_items.append('Rolls')
    # c.menu_items.append('Committees')
    c.menu_items.append('Officials')
    c.menu_items.append('Elections')
    c.save()


    # updateTop()
    
    # start_date = '%s-%s-%s' %(2023, 12, 1)
    # prnt(start_date)
    # day = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    # hansards = Hansard.objects.filter(Publication_date_time__gte=day)
    # def run(b):
    #     if b.summarySpren:
    #         try:
    #             spren = Spren.objects.filter(bill=b, type='summary')[0]
    #         except:
    #             spren = Spren(bill=b, type='summary')
    #         spren.content = b.summarySpren
    #         spren.save()
    #     if b.steelmanSprenFor:
    #         try:
    #             spren = Spren.objects.filter(bill=b, type='steelfor')[0]
    #         except:
    #             spren = Spren(bill=b, type='steelfor')
    #         spren.content = b.steelmanSprenFor
    #         spren.save()
    #     if b.steelmanSprenAgainst:
    #         try:
    #             spren = Spren.objects.filter(bill=b, type='steelagainst')[0]
    #         except:
    #             spren = Spren(bill=b, type='steelagainst')
    #         spren.content = b.steelmanSprenAgainst
    #         spren.save()
    #     # b.getSpren(False)

    # parl1 = Parliament.objects.filter(country='Canada', organization='Ontario')[0]
    # parl2 = Parliament.objects.filter(country='Canada', organization='Federal')[0]
    # bills1 = Bill.objects.filter(parliament=parl1)
    # prnt(bills1.count())
    # time.sleep(3)
    # for b in bills1:
    #     run(b)
    # bills2 = Bill.objects.filter(parliament=parl2)
    # prnt(bills2.count())
    # time.sleep(3)
    # for b in bills2:
    #     run(b)

    
    # hansard = Hansard.objects.exclude(Organization='Senate').exclude(Organization='House').order_by('-Publication_date_time')[0]
    # hansard = Hansard.objects.filter(Organization='Senate').order_by('-Publication_date_time')[2]
    # hansard = Hansard.objects.filter(Organization='House').order_by('-Publication_date_time')[2]
    # x = 0
    # for hansard in hansards:
    #     n = 0
    #     t = 0
    #     for topic in hansard.Terms:
    #         t += 1
    #         search = ['%s'%(topic)]
    #         posts = Post.objects.filter(hansardItem__hansard=hansard).filter(Q(hansardItem__Terms__overlap=search)|Q(hansardItem__keywords__overlap=search)).select_related('hansardItem__person', 'hansardItem').order_by('date_time')
    #         num_tokens, text = makeText(posts)
    #         if posts.count() >= 5 and num_tokens >= 600 or num_tokens > 1200:
    #             prnt(topic, num_tokens, posts.count())
    #             # summarize_topic(hansard, topic)
    #             try:
    #                 spren = Spren.objects.filter(hansard=hansard, topic=topic)[0]
    #             except:
    #                 spren = Spren(hansard=hansard, topic=topic)
    #                 spren.type = 'summary'
    #                 spren.content = 'TBD'
    #                 spren.date_time = hansard.Publication_date_time
    #                 spren.create_post()
    #             n += 1
    #             x += 1
    #     prnt('end', n, t)

    # prnt('fini', x)
    # prnt('---------------------senate hansards')
    # debate = 'https://sencanada.ca/en/in-the-chamber/debates/'
    # r = requests.get(debate)
    # soup = BeautifulSoup(r.content, 'html.parser')
    # links = soup.find_all('a')
    # n = 0
    # for a in links:
    #     if '\content' in a['href'] and '\debates' in a['href'] and n <= 43:
    #         n += 1
    #         link = 'https://sencanada.ca' + a['href'].replace('\\','/')
    #         add_senate_hansard(link, True)
    # reactions = Reaction.objects.exclude(person=None).filter(user=None)
    # for r in reactions:
    #     # prnt(r)
    #     r.delete()
    # bs = Bill.objects.all().order_by('-LatestBillEventDateTime')
    # bs = Bill.objects.filter(NumberCode='C-18', ParliamentNumber='44')
    # for b in bs:
    #     prnt(b)
    #     p = Post.objects.filter(bill=b)
    #     for i in p:
    #         i.total_nays = 0
    #         i.total_yeas = 0
    #         i.total_votes = 0
    #         i.save()
    # prnt('done step 1')
    # time.sleep(5)
    # for b in bs:
    #     prnt()
    #     prnt(b)
    #     b.NumberCode = b.NumberCode.strip()
    #     b.save()
    #     vs = BillVersion.objects.filter(bill=b)
    #     for v in vs:
    #         if v.empty:
    #             v.delete()
    #         else:
    #             try:
    #                 p = Post.objects.filter(billVersion=v)[0]
    #             except:
    #                 v.create_post()
        # prnt('next')
        # try:
        #     def func(motion):
        #         votes = Vote.objects.filter(motion=motion)
        #         # prnt(votes.count())
        #         x = 0
        #         z = 0
        #         f = 0
        #         n = 0
        #         for v in votes:
        #             # prnt(v)
        #             x += 1
        #         # try:
        #             if v.person:
        #                 z += 1
        #                 # prnt(v.person)
        #                 post = Post.objects.filter(bill=motion.bill)[0]
        #                 try:
        #                     reaction = Reaction.objects.filter(post=post, person=v.person)[0]
        #                     reaction.calculate_vote(v.VoteValueName, True)
        #                     f += 1
        #                 except:
        #                     reaction = Reaction(post=post, person=v.person)
        #                     reaction.save()
        #                     reaction.calculate_vote(v.VoteValueName, False)
        #                     n += 1
        #         prnt(str(z)+'/'+str(x)+'||'+str(f)+'/'+str(n))
        #         post = Post.objects.filter(bill=motion.bill)[0]
        #         prnt(post.total_yeas, post.total_nays, post.total_votes)
        #     motion = Motion.objects.filter(bill=b).order_by('date_time')
        #     for m in motion:
        #         prnt(m)
        #         func(m)
        #     # if motion.OriginatingChamberName == 'House':
        #     #     motion = Motion.objects.filter(bill=b, OriginatingChamberName='Senate')[0]
        #     #     prnt(motion)
        #     #     func(motion)
        #     # elif motion.OriginatingChamberName == 'Senate':
        #     #     motion = Motion.objects.filter(bill=b, OriginatingChamberName='House')[0]
        #     #     prnt(motion)
        #     #     func(motion)

        # except Exception as e:
        #     prnt(str(e))

    
    
    prnt('done', datetime.datetime.now() - start_time)

# def update_database3():
#     # sozed = User.objects.get(username='Sozed')
#     # sozed.alert('%s-%s' %(datetime.datetime.now(), 'update_database'), None, 'body')


#     today = date.today()
#     # datetime.combine(today, datetime.min.time()) # midnight this morning
#     dt = datetime.datetime.now()
#     houseHansards = Hansard.objects.filter(Publication_date_time__gte=datetime.datetime.now() - datetime.timedelta(days=2), Publication_date_time__lte=datetime.datetime.combine(today, datetime.datetime.min.time()), Organization='House', has_transcript=False).count()
#     if houseHansards:
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_house_motions, job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
        
#     senateHansards = Hansard.objects.filter(Publication_date_time__gte=datetime.datetime.now() - datetime.timedelta(days=2), Publication_date_time__lte=datetime.datetime.combine(today, datetime.datetime.min.time()), Organization='Senate', has_transcript=False).count()
#     if senateHansards:
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_motions, 'latest', job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_hansards, 'latest', job_timeout=200)
#     if dt.hour == 9:
#         # morning
#         queue = django_rq.get_queue('default')
#         queue.enqueue(daily_summarizer, None, job_timeout=500)
#     if dt.hour == 18:
#         # evening
#         prov = Province.objects.filter(name='Ontario')[0]
#         elections = Election.objects.filter(level='Provincial', province=prov, ongoing=True)
#         if elections.count() > 0:
#             queue = django_rq.get_queue('default')
#             queue.enqueue(ontario.check_candidates, job_timeout=500)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(send_notifications, None, job_timeout=200)
#     if datetime.datetime.today().weekday() == 5 and dt.hour == 1:
#         # saturday 1am / weekly
#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.check_elections, job_timeout=500)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_current_MPPs, job_timeout=1000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_all_MPs, 'current', job_timeout=2000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senators, job_timeout=2000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_all_bills, 'session', job_timeout=7200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=7200)

#     if dt.day == 1 and dt.hour == 1:
#         # monthly
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_house_expenses, job_timeout=600)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(clear_jold_obs, job_timeout=200)
#     daily = [9, 12, 18, 23]
#     if dt.hour in daily:
#         prnt('start daily update')
#         # sozed = User.objects.get(username='Sozed')
#         # sozed.alert('%s-%s' %(datetime.datetime.now(), 'daily'), None, 'body')
#         sluggers = User.objects.filter(slug=None)
#         for s in sluggers:
#             s.slugger()
#             s.save()
#         elections = Election.objects.filter(end_date__lt=datetime.datetime.today(), ongoing=True)
#         for q in elections:
#             q.ongoing = False
#             q.save()

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_agenda, 'latest', job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=1000)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_current_bills, job_timeout=1000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_todays_xml_agenda, job_timeout=1000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_bills, job_timeout=1000)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_house_motions, job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_house_committee_hansard_and_list, job_timeout=500)
       
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_committee_work, 'latest', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_motions, 'latest', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_committee_work, 'latest', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_senate_committees, 'past', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_senate_committees, 'upcoming', job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(updateTop, job_timeout=200)
    
#     # from utils.models import run_runpod
#     queue = django_rq.get_queue('default')
#     queue.enqueue(clear_chrome, job_timeout=200)
#     queue = django_rq.get_queue('default')
#     queue.enqueue(clear_jold_obs, job_timeout=200)
    

# def update_database2():
#     # sozed = User.objects.get(username='Sozed')
#     # sozed.alert('%s-%s' %(datetime.datetime.now(), 'update_database'), None, 'body')


#     today = date.today()
#     # datetime.combine(today, datetime.min.time()) # midnight this morning
#     dt = datetime.datetime.now()
#     houseHansards = Hansard.objects.filter(Publication_date_time__gte=datetime.datetime.now() - datetime.timedelta(days=2), Publication_date_time__lte=datetime.datetime.combine(today, datetime.datetime.min.time()), Organization='House', has_transcript=False).count()
#     if houseHansards:
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_house_motions, job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
        
#     senateHansards = Hansard.objects.filter(Publication_date_time__gte=datetime.datetime.now() - datetime.timedelta(days=2), Publication_date_time__lte=datetime.datetime.combine(today, datetime.datetime.min.time()), Organization='Senate', has_transcript=False).count()
#     if senateHansards:
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_motions, 'latest', job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_hansards, 'latest', job_timeout=200)
#     if dt.hour == 9:
#         # morning
#         queue = django_rq.get_queue('default')
#         queue.enqueue(daily_summarizer, None, job_timeout=500)
#     if dt.hour == 18:
#         # evening
#         prov = Province.objects.filter(name='Ontario')[0]
#         elections = Election.objects.filter(level='Provincial', province=prov, ongoing=True)
#         if elections.count() > 0:
#             queue = django_rq.get_queue('default')
#             queue.enqueue(ontario.check_candidates, job_timeout=500)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(send_notifications, None, job_timeout=200)
#     if datetime.datetime.today().weekday() == 5 and dt.hour == 1:
#         # saturday 1am / weekly
#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.check_elections, job_timeout=500)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_current_MPPs, job_timeout=1000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_all_MPs, 'current', job_timeout=2000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senators, job_timeout=2000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_all_bills, 'session', job_timeout=7200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=7200)

#     if dt.day == 1 and dt.hour == 1:
#         # monthly
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_house_expenses, job_timeout=600)
#     daily = [9, 12, 18, 23]
#     if dt.hour in daily:
#         prnt('start daily update')
#         # sozed = User.objects.get(username='Sozed')
#         # sozed.alert('%s-%s' %(datetime.datetime.now(), 'daily'), None, 'body')
#         sluggers = User.objects.filter(slug=None)
#         for s in sluggers:
#             s.slugger()
#             s.save()
#         elections = Election.objects.filter(end_date__lt=datetime.datetime.today(), ongoing=True)
#         for q in elections:
#             q.ongoing = False
#             q.save()

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_agenda, 'latest', job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=1000)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.get_current_bills, job_timeout=1000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_todays_xml_agenda, job_timeout=1000)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_bills, job_timeout=1000)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_house_motions, job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_house_committee_hansard_and_list, job_timeout=500)
       
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_committee_work, 'latest', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_motions, 'latest', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_senate_committee_work, 'latest', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_senate_committees, 'past', job_timeout=200)
        
#         queue = django_rq.get_queue('default')
#         queue.enqueue(get_latest_senate_committees, 'upcoming', job_timeout=200)

#         queue = django_rq.get_queue('default')
#         queue.enqueue(updateTop, job_timeout=200)
    
#     from utils.models import run_runpod
#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(run_runpod, job_timeout=3600)

# def updateTop():
#     from posts.utils import algorithim
#     tops1 = TopPost.objects.all()
#     if tops1 and tops1[0].cycle == 1:
#         cycle = 2
#     else:
#         cycle = 1
#     include_list = ['bill','hansard']
#     chambers = ['House', 'Senate','All']
#     def run(posts, chamber, region):
#         for post in posts:
#             try:
#                 top = TopPost.objects.filter(cycle=cycle, post=post, chamber=chamber, region=region)[0]
#             except:
#                 top = TopPost(cycle=cycle, post=post, chamber=chamber, region=region)
#                 top.save()
#     for p in Province.objects.filter(is_supported=True):
#         posts, view = algorithim(None, include_list, 'All', p.name, 'Trending', 10)
#         run(posts, 'All', p.name)
#         posts, view = algorithim(None, include_list, 'Assembly', p.name, 'Trending', 10)
#         run(posts, 'Assembly', p.name)
    
#     for c in chambers:
#         posts, view = algorithim(None, include_list, c, None, 'Trending', 10)
#         run(posts, c, None)
    
#     for t in tops1:
#         t.delete()

# def run_runpod():
#     prnt('start runpod')
#     # caught in a loop in summarize_topic
#     sprens = Spren.objects.filter(content='TBD')
#     try:
#         prnt(sprens[0])
#         prnt(sprens.count())
#         time.sleep(2)
#         import runpod
#         # from runpod import api_key

#         def run(pod_id, url):
#             prnt('sleep')
#             time.sleep(5)
#             n = 5
#             # fail
#             run = True
#             while run == True:
#                 time.sleep(2)
#                 n += 2
#                 pods = runpod.get_pods()
#                 # prnt(pods)
#                 for pod in pods:
#                     prnt()
#                     prnt(pod)
#                 # fail
#                 try:
#                     n += 5
#                     prnt(n)
#                     time.sleep(5)
#                     prnt('go')
#                     os.environ["TOKENIZERS_PARALLELISM"] = "false"
#                     client = OpenAI(api_key="EMPTY", base_url=url)
#                     completion = client.chat.completions.create(
#                     model="llama-2-13b-chat.Q4_K_M.gguf",
#                     temperature=0,
#                     max_tokens=500,
#                     # stream=True,
#                     messages=[
#                         {"role": "system", "content": "You are a non-conversational computer assistant."},
#                         {"role": "user", "content": 'hello'}
#                     ]
#                     )
#                     prnt('-----')
#                     prnt(completion)
#                     prnt()
#                     prnt(completion.choices[0].message.content)
#                     run = False
#                     ready = True
#                 except Exception as e:
#                     prnt('fail', str(e))
#                     if n > 190:
#                         run = False
#                         ready = False
#                         response = runpod.stop_pod(pod_id)
#                         try:
#                             prnt(response)
#                         except Exception as e:
#                             prnt(str(e))
#                         try:
#                             prnt(response.content)
#                         except Exception as e:
#                             prnt(str(e))

#             prnt(n)
#             return ready
        
#         pod_id = twenty_pod_id
#         url = twenty_url
#         response = runpod.resume_pod(pod_id, 1)
#         try:
#             prnt(response)
#         except Exception as e:
#             prnt(str(e))
#         try:
#             prnt(response.content)
#         except Exception as e:
#             prnt(str(e))
#         prnt()
#         ready = run(pod_id, url)
#         if not ready:
#             pod_id = fourtyeight_pod_id
#             url = fourtyeight_url
#             headers = {'content-type': 'application/json',}
#             params = {'api_key': a_key,}
#             json_data = {"query": "mutation { podBidResume( input: { podId: \"%s\", bidPerGpu: 0.2, gpuCount: 1 } ) { id desiredStatus imageName env machineId machine { podHostId } } }" %(pod_id)}
#             response = requests.post('https://api.runpod.io/graphql', params=params, headers=headers, json=json_data)
#             try:
#                 prnt(response)
#             except Exception as e:
#                 prnt(str(e))
#             try:
#                 prnt(response.content)
#             except Exception as e:
#                 prnt(str(e))
#             prnt()
#             ready = run(pod_id, url)
#         if ready:
#             for spren in sprens:
#                 summarize_topic(spren.hansard, spren.topic, url)
#         response = runpod.stop_pod(pod_id)
#         try:
#             prnt(response)
#         except Exception as e:
#             prnt(str(e))
#         try:
#             prnt(response.content)
#         except Exception as e:
#             prnt(str(e)) 
#     except Exception as e:
#         prnt(str(e))
#         try:
#             response = runpod.stop_pod(pod_id)
#             try:
#                 prnt(response)
#             except Exception as e:
#                 prnt(str(e))
#             try:
#                 prnt(response.content)
#             except Exception as e:
#                 prnt(str(e)) 
#         except Exception as e:
#             prnt(str(e))

#     prnt('done runpod')



# def daily_update():
#     prnt('start daily update')
#     sluggers = User.objects.filter(slug=None)
#     for s in sluggers:
#         s.slugger()
#         s.save()
#     elections = Election.objects.filter(end_date__lt=datetime.datetime.today(), ongoing=True)
#     for q in elections:
#         q.ongoing = False
#         q.save()
    
#     # user = User.objects.filter(username='Sozed')[0]
#     # user.alert('Daily update started at %s' %(datetime.datetime.now()), '/')

#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(ontario.get_weekly_agenda, job_timeout=500)

#     queue = django_rq.get_queue('low')
#     queue.enqueue(ontario.get_current_bills, job_timeout=1000)


#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_todays_xml_agenda, job_timeout=1000)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_latest_bills, job_timeout=1000)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_latest_house_motions, job_timeout=200)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_latest_house_committee_hansard_and_list, job_timeout=500)
    
#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_committee_work, 'latest', job_timeout=200)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_senate_agenda, 'latest', job_timeout=200)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_senate_motions, 'latest', job_timeout=200)
    
#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(get_senate_hansards, 'latest', job_timeout=200)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_senate_committee_work, 'latest', job_timeout=200)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_latest_senate_committees, 'past', job_timeout=200)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_latest_senate_committees, 'upcoming', job_timeout=200)


# def midnight_update():
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)

# def morning_update():
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_senate_hansards, 'latest', job_timeout=200)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=1000)

# def evening_update():
#     prov = Province.objects.filter(name='Ontario')[0]
#     elections = Election.objects.filter(level='Provincial', province=prov, ongoing=True)
#     if elections.count() > 0:
#         queue = django_rq.get_queue('default')
#         queue.enqueue(ontario.check_candidates, job_timeout=500)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_senate_hansards, 'latest', job_timeout=200)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=1000)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(send_notifications, None, job_timeout=200)

# def weekly_update():
#     # u = User.objects.filter(username='Sozed')[0]
#     # title = 'running weekly update'
#     # u.alert(title, None, None)
#     queue = django_rq.get_queue('default')
#     queue.enqueue(ontario.check_elections, job_timeout=500)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_all_bills, 'session', job_timeout=7200)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(ontario.get_all_hansards_and_motions, 'recent', job_timeout=7200)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(ontario.get_current_MPPs, job_timeout=1000)

#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_all_MPs, 'current', job_timeout=2000)

# def monthly_update():
#     # u = User.objects.filter(username='Sozed')[0]
#     # title = 'running monthly update'
#     # u.alert(title, None, None)
    
#     queue = django_rq.get_queue('default')
#     queue.enqueue(get_house_expenses, job_timeout=600)

