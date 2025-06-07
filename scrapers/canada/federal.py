
# from unittest.result import failfast
from django.db import models
from django.db.models import Q, Avg

import django_rq
from rq import Queue
from worker import conn

from accounts.models import *
from legis.models import *
from posts.models import *
from posts.views import get_ordinal
# from posts.utils import sprenderize
from utils.cronjobs import finishScript, create_share_object
from blockchain.models import logEvent, logError, script_test_error
from utils.models import timezonify, remove_accents, open_browser


# from firebase_admin.messaging import Notification as fireNotification
# from firebase_admin.messaging import Message as fireMessage
# from fcm_django.models import FCMDevice
import sys
import gc
import datetime
from dateutil.parser import parse
import requests
import feedparser
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pytz
import time
import re
import random
import json
# from collections import OrderedDict
# from operator import itemgetter
import operator

from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

province_list = {
  "Alberta": "AB",
  "British Columbia": "BC",
  "Manitoba": "MB",
  "New Brunswick": "NB",
  "Newfoundland and Labrador": "NL",
  "Northwest Territories": "NT",
  "Nova Scotia": "NS",
  "Nunavut": "NU",
  "Ontario": "ON",
  "Prince Edward Island": "PE",
  "Quebec": "QC",
  "Saskatchewan": "SK",
  "Yukon": "YT"
}
prov_or_terr = {
  "Alberta": "Province",
  "British Columbia": "Province",
  "Manitoba": "Province",
  "New Brunswick": "Province",
  "Newfoundland and Labrador": "Province",
  "Northwest Territories": "Territory",
  "Nova Scotia": "Province",
  "Nunavut": "Territory",
  "Ontario": "Province",
  "Prince Edward Island": "Province",
  "Quebec": "Province",
  "Saskatchewan": "Province",
  "Yukon": "Territory"
}

runTimes = {
    'initialize_region' : 1000,
    'get_recent_bills' : 1000, 'get_senate_bills' : 1000, 'get_house_bills' : 1000, 'get_all_bills' : 7200, 
    'get_house_agendas' : 200, 'get_house_debates' : 1000, 'get_senate_debates' : 200,
    'get_house_persons' : 2000, 'get_senate_persons' : 2000, 'get_senate_agendas' : 200,
    'get_house_motions' : 200, 'get_senate_motions' : 200, 'get_senate_committees' : 200, 'get_house_expenses' : 600,
    'get_todays_xml_agenda' : 1000, 'get_house_committees' : 1000, 'get_upcoming_senate_committees' : 200,
    }

typical = ['get_house_agendas', 'get_senate_agendas', 'get_todays_xml_agenda',
    # 'get_house_committees', 'get_senate_committees',
    ]

functions = {
    "2025-03-13" : [
    # {'date' : [1], 'dayOfWeek' : ['x'], 'hour' : [2], 'cmds' : ['get_house_expenses']},
    {'date' : ['x'], 'dayOfWeek' : [6,2], 'hour' : [5], 'cmds' : ['get_house_persons', 'get_senate_persons']},
    # mon - sat
    {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [8, 10, 12, 18, 24], 'cmds' : ['get_house_agendas', 'get_senate_agendas', 'get_todays_xml_agenda'] },
    {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [3, 7, 10, 12, 13, 15, 17, 20, 23], 'cmds' : ['get_bills'] },
    {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [2, 6, 18, 22], 'cmds' : ['get_house_debates', 'get_house_motions']},
    {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [4, 8, 20, 24], 'cmds' : ['get_senate_debates', 'get_senate_motions']},
    ],
}

approved_models = {
    'initialize_region' : [],
    'get_house_agendas' : ['Government', 'Agenda', 'AgendaTime', 'AgendaItem'],
    'get_house_persons' : ['Person', 'Party', 'District', 'Region'],
    'get_senate_persons' : ['Person', 'District', 'Party', 'Region'],
    'get_all_bills' : ['Bill', 'BillVersion', 'Role', 'Person', 'Notification'],
    'get_house_bills' : ['Bill', 'BillVersion', 'Role', 'Person', 'Notification'],
    'get_senate_bills' : ['Bill', 'BillVersion', 'Role', 'Person', 'Notification'],
    'get_house_debates' : ['Meeting', 'Statement', 'Agenda', 'Government', 'Person', 'Bill'],
    'get_senate_debates' : ['Meeting', 'Statement', 'Bill'],
    'get_house_motions' : ['Government', 'Motion', 'Vote', 'Interaction', 'Person'],
    'get_senate_motions' : ['Government', 'Motion', 'Vote', 'Interaction'],
    'get_user_region' : ['District', 'Region', 'Role', 'Party', 'Person'],
    }

gov_logo_links = {"House": "img/canada/house.png", "Senate": "img/canada/senate.png"}


get_wiki = not testing()

def initialize_region(special=None, dt=now_utc(), iden=None):
    get_house_agendas(special=special, iden=iden)
    get_house_persons(special=special, iden=iden)
    get_senate_persons(special=special, iden=iden)
        


def find_party(party_short=None, party_name=None):
    # prntDebug('find_party',party_short,party_name)
    party_list = {
        'Liberal':{'short':'L','alt':'Lib'},
        'Conservative':{'short':'C','alt':'Con'},
        'NDP':{'short':'NDP','alt':'New Democratic Party'},
        'Green Party':{'short':'G','alt':'Greens'},
        'Bloc Quebecios':{'short':'BQ','alt':'Bloc'},
        "People's Party":{'short':'PP','alt':'Peoples'},
        "Progressive Senate Group":{'short':'PSG','alt':'Progressive'},
        "Canadian Senators Group":{'short':'CSG','alt':'CSG'},
        "Independent Senators Group":{'short':'ISG','alt':'Independent Group'},
        "Non-affiliated":{'short':'NA','alt':'Independent'},
    }
    if party_name:
        party_name_modded = party_name.replace('The','').replace('Party','').replace('the','').replace('party','').strip()
        for key, value in party_list.items():
            if key.lower() == party_name_modded.lower() or value['alt'] and value['alt'].lower() == party_name_modded.lower():
                return key, value['short'], value['alt']
    if party_short:
        for key, value in party_list.items():
            if value['short'] == party_short:
                return key, value['short'], value['alt']
    if party_short and not party_name:
        party_name = party_short
    return party_name, party_short, None
    

def get_house_persons(special=None, value='current', dt=now_utc(), iden=None):
    prntDebug('start gather mps')
    func = 'get_house_persons'
    country = Region.objects.filter(modelType='country', Name='Canada').first()
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country).first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)

    modded_country = None
    if not country.Office_array or 'Member of Parliament' not in country.Office_array:
        modded_country = country.propose_modification()
        modded_country.add_office('Member of Parliament')
        log.updateShare(modded_country)
    if not country.Chamber_array or 'House' not in country.Chamber_array:
        if not modded_country:
            modded_country = country.propose_modification()
        modded_country.add_chamber('House')
        log.updateShare(modded_country)

    # if country.add_office('Member of Parliament') or country.add_chamber('House'):
    #     country.update_data()
    #     log.updateShare(country)
    #     # log.updateShare(country)
    if not special:
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')

    def get_data(url, log):
        current_mps = []
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        m_list = []
        members = soup.find_all('div', {'class':'ce-mip-mp-tile-container'})
        for member in members:
            a = member.find('a',{'class':'ce-mip-mp-tile'})
            page = 'https://www.ourcommons.ca' + a['href']
            img = a.find(['img'])
            picture = 'https://www.ourcommons.ca' + img['src']
            name = a.find('div', {'class':'ce-mip-mp-name'}).text
            # prntDebug(name)
            party = a.find('div', {'class':'ce-mip-mp-party'}).text
            con = a.find('div', {'class':'ce-mip-mp-constituency'}).text
            prov_name = a.find('div', {'class':'ce-mip-mp-province'}).text
            AbbrName = None
            if prov_name in province_list:
                AbbrName = province_list[prov_name]
            if prov_name in prov_or_terr:
                region_type = prov_or_terr[prov_name]
            else:
                region_type = 'Province'
            prov = Region.objects.filter(Name=prov_name, AbbrName=AbbrName, modelType='provState', ParentRegion_obj=log.Region_obj).first()
            if not prov:
                prov = Region(func=func, Name=prov_name, AbbrName=AbbrName, nameType=region_type, modelType='provState', ParentRegion_obj=log.Region_obj)
                # prov.add_office('Member of Parliament')
                prov.update_data()
                log.updateShare(prov)

            a = page.find('(')+1
            b = page[a:].find(')')
            iden = page[a:a+b]
            m = {}
            m['name'] = name
            # m['party'] = party
            # m['con'] = con
            # m['prov'] = prov
            m['picture'] = picture
            m['link'] = page
            m['iden'] = iden
            m_list.append(m)
        
        url = 'https://www.ourcommons.ca/Members/en/search/XML'
        r = requests.get(url)
        root = ET.fromstring(r.content)
        members = root.findall('MemberOfParliament')
        # q = len(m_list)
        # w = 1
        for member in members:
            first = member.find('PersonOfficialFirstName').text
            last = member.find('PersonOfficialLastName').text
            # prntDebug(first, last)
            elected = member.find('FromDateTime').text
            elecdate = timezonify('est', datetime.datetime.strptime(elected, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.UTC))
            # prntDebug(elecdate)
            for m in m_list:
                if first in m['name'] and last in m['name']:
                    person, personU, person_is_new = get_model_and_update('Person', GovProfilePage=m['link'], Country_obj=log.Region_obj, Region_obj=log.Region_obj)
                    # personData['GovProfilePage'] = m['link']
                    if person_is_new:
                        personU.data['FirstName'] = first
                        personU.data['LastName'] = last
                        personU.data['FullName'] = first + ' ' + last
                        # mp.gov_profile_page = m['link']
                        personU.data['PhotoLink'] = m['picture']
                        person.GovIden = m['iden']
                        # must save person before profile info can be assigned
                        person, personU, person_is_new, log = save_and_return(person, personU, log)
                    time.sleep(2)
                    # if 'http' not in personData['GovProfilePage']:
                    #     url = 'https:%s/roles' %(personData['GovProfilePage'])
                    # else:
                    #     url = '%s/roles' %(personData['GovProfilePage'])
                    # prntDebug(url)
                    log = get_MP(person, personU, person_is_new, log, chamber='House')
                    # for d in mpData:
                    #     shareData.append(d)
                    current_mps.append(person.id)
                    # prntDebug('saved')
                    # role = Role.objects.filter(position='Member of Parliament', person=mp).order_by('-start_date')
                    break
            # break
        prntDebug('done get_data')
        return current_mps, log
    if value == 'alltime':
        parliaments = ['44', '43', '42', '41', '40', '39', '38', '37', '36']
        for p in parliaments:
            url = 'https://www.ourcommons.ca/Members/en/search/xml?parliament=%s&caucusId=all&province=all&gender=all' %(p)
            current_mps, log = get_data(url, log)
    elif value == 'current':
        url = 'https://www.ourcommons.ca/Members/en/search'
        current_mps, log = get_data(url, log)
        prntDebug('len:', len(current_mps))
        if len(current_mps) > 300:
            # prntDebug(current_mps)
            # prntDebug('updating current')
            # prntDebug()
            repUpdates = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, extra__roles__contains=[{'role':'Member of Parliament','current':True, 'gov_level':'Federal'}]).exclude(pointerId__in=current_mps)
            prntDebug('repUpdates',repUpdates)
            for u in repUpdates:
                prntDebug('removing:::',u.pointerId)
                update = u.create_next_version()
                if 'Position' in update.data and update.data['Position'] == 'Member of Parliament':
                    del update.data['Position']
                update.Pointer_obj.update_role(update, role='Member of Parliament', current=False)
                update, u_is_new = update.save_if_new(func=func)
                if u_is_new:
                    log.updateShare(update)
            prnt('done')
                    
    
    prntDebug('done gather mps')
    # send_for_validation(shareData, gov, func)
    return finishScript(log, gov, special)

def get_MP(person, personU, person_is_new, log, chamber='House'):
    prntDebug('start get_MP')
    # prntDebug(mp.FirstName, mp.FirstName)
    if chamber == 'House':
        office = 'Member of Parliament'
    elif chamber == 'Senate':
        office = 'Senator'
    else:
        office = None
    if 'http' not in person.GovProfilePage:
        url = 'https:%s/roles' %(person.GovProfilePage)
    else:
        url = '%s/roles' %(person.GovProfilePage)
    if not person.GovIden:
        a = person.GovProfilePage.find('members/')+len('members/')
        person.GovIden = person.GovProfilePage[a:]
        # mp.save()
    # https://www.ourcommons.ca/Members/en/ziad-aboultaif(89156)#contact
    r = requests.get(url)
    # prntDebug(r.content)
    soup = BeautifulSoup(r.content, 'html.parser')
    h1 = soup.find('h1', {'class':'mt-0'}).text

    if 'Hon' in h1:
        # prntDebug('is honourable')
        personU.data['Honorific'] = 'Hon.'
        # mp.Honorific = 'Hon.'
        # mp.save()
    if not personU.data['PhotoLink']:
        try:
            div = soup.find('div', {'class':'ce-mip-mp-picture-container'})
            img = div.find('img')['src']
            # 'https://www.ourcommons.ca/Content/Parliamentarians/Images/OfficialMPPhotos/38/Schmiw.JPG'
            personU.data['PhotoLink'] = 'https://www.ourcommons.ca' + img
            # mp.save()
        except:
            pass
    try:
        personU.data['Position'] = office
        party_name = soup.find('div', {'class':'ce-mip-mp-party'})
        party_name = party_name.text
        party_name, party_short, alt_name = find_party(party_name=party_name)
        party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=log.Region_obj, Region_obj=log.Region_obj, gov_level='Federal')
        if party_is_new and get_wiki:
            try:
                time.sleep(1)
                search_name = f'Canadian {party_name} federal political party'
                prnt(search_name)
                link = wikipedia.search(search_name)[0].replace(' ', '_')
                party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                prnt('party.Wiki',party.Wiki)
            except Exception as e:
                prnt('party:',str(e))
                pass
        party, partyU, party_is_new, log = save_and_return(party, partyU, log)
        prov_name = soup.find('div', {'class':'ce-mip-mp-province'}).text
        prov = Region.objects.filter(Name=prov_name, nameType='Province', modelType='provState', ParentRegion_obj=log.Region_obj).first()
        constituency_name = soup.find('div', {'class':'ce-mip-mp-constituency'}).text
        district = District.objects.filter(Q(Name=constituency_name)|Q(AltName=constituency_name.replace('—', ''))).filter(Country_obj=log.Region_obj, Region_obj=log.Region_obj, ProvState_obj=prov, gov_level='Federal', nameType='Federal District').first() # the character being removed is not a regular dash
        if district:
            if not district.Office_array or 'Member of Parliament' not in district.Office_array:
                modded_district = district.propose_modification()
                modded_district.add_office('Member of Parliament')
                log.updateShare(modded_district)
        if not district:
            district = District(func=log.data['func'], Name=constituency_name, AltName=constituency_name.replace('—', ''), Country_obj=log.Region_obj, Region_obj=log.Region_obj, ProvState_obj=prov, gov_level='Federal', nameType='Federal District')
            if get_wiki:
                try:
                    time.sleep(1)
                    search_name = f'Canadian federal district of {constituency_name}'
                    prntDebug('search_name',search_name)
                    title = wikipedia.search(search_name)[0].replace(' ', '_')
                    district.Wiki = 'https://en.wikipedia.org/wiki/' + title
                    prntDebug('district.Wiki',district.Wiki)
                    # district.update_data()
                except Exception as e:
                    prntDebug(str(e))
            district.add_office(office)
            log.updateShare(district)
        personU.data['Chamber'] = chamber
        personU.data['District_id'] = district.id
        personU.data['ProvState_id'] = prov.id
        personU.data['Position'] = office
        personU.data['gov_level'] = 'Federal'
        personU.data['Party_id'] = party.id
        person.update_role(personU, data={'role':office,'gov_level':'Federal','current':True})

    except Exception as e:
        prntDebug('fail get mp 345', str(e))
        logError(f'fail get mp', code='49384', func='get_mp', region=None, extra={'url':url})



    # # roles-mp
    # # time data 'Monday, September 20, 2021' does not match format '%B %d, %Y'
    # # time data 'Monday, October 21, 2019' does not match format '%B %d, %Y'
    # # time data 'Monday, October 19, 2015' does not match format '%B %d, %Y'
    # # roles-affiliation
    # create_next_version,PARTY:Liberal-Federal
    # update_role UPDATE:Person-updSoaee8684e42af5b03c011592ccf208da6 None
    # done role update
    # create_next_version,PARTY:Liberal-Federal
    # update_role UPDATE:Person-updSoaee8684e42af5b03c011592ccf208da6 None
    # done role update
    # create_next_version,PARTY:Liberal-Federal
    # update_role UPDATE:Person-updSoaee8684e42af5b03c011592ccf208da6 None
    # done role update
    # # roles-offices
    # # roles-offices
    # # 'Update' object does not support item assignment
    # # roles-committees

    ordered = 0
    group_link = None
    try:
        prntDebug('roles-mp')
        table = soup.find('table', {'id':'roles-mp'})
        tbody = table.find('tbody')
        roles = tbody.find_all('tr', {'role':'row'})
        ordered += 1
        for r in roles:
            try:
                td = r.find_all('td')
                constituency_name = td[0].text
                province_name = td[1].text
                start = td[2].text
                end = td[3].text
                start_date = timezonify('est', datetime.datetime.strptime(start, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                if end:
                    end_date = timezonify('est', datetime.datetime.strptime(end, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                else:
                    end_date = None
                prov = Region.objects.filter(Name=prov_name, nameType='Province', modelType='provState', ParentRegion_obj=log.Region_obj).first()
                district = District.objects.filter(Q(Name=constituency_name)|Q(AltName=constituency_name.replace('—', ''))).filter(Country_obj=log.Region_obj, Region_obj=log.Region_obj, ProvState_obj=prov, gov_level='Federal', nameType='Federal District').first() #that character being removed is important, it is not a regular dash
                if district:
                    if not district.Office_array or 'Member of Parliament' not in district.Office_array:
                        modded_district = district.propose_modification()
                        modded_district.add_office('Member of Parliament')
                        log.updateShare(modded_district)
                if not district:
                    district = District(func=log.data['func'], Name=constituency_name, AltName=constituency_name.replace('—', ''), Country_obj=log.Region_obj, Region_obj=log.Region_obj, ProvState_obj=prov, gov_level='Federal', nameType='Federal District')
                    district.add_office(office)
                    log.updateShare(district)
                rolData = {'role':office,'chamber':chamber,'gov_level':'Federal','District_id':district.id,'ProvState_id':prov.id,'start_date':start_date.isoformat()}
                if end_date == None:
                    rolData['current'] = True
                else:
                    rolData['current'] = False
                    rolData['end_date'] = end_date.isoformat()
                person.update_role(personU, data=rolData)
            except Exception as e:
                prntDebug('mp roll error 4092', str(e))
    except Exception as e:
        prntDebug('mp error 23634', str(e))
    try: 
        prntDebug('roles-affiliation')
        table = soup.find('table', {'id':'roles-affiliation'})
        tbody = table.find('tbody')
        roles = tbody.find_all('tr', {'role':'row'})
        ordered += 1
        for r in roles:
            try:
                td = r.find_all('td')
                one = td[0].text
                party_name = td[1].text
                start = td[2].text
                end = td[3].text
                start_date = timezonify('est', datetime.datetime.strptime(start, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                if end:
                    end_date = timezonify('est', datetime.datetime.strptime(end, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                else:
                    end_date = None
                
                party_name, party_short, alt_name = find_party(party_name=party_name)
                party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=log.Region_obj, Region_obj=log.Region_obj, gov_level='Federal')
                if party_is_new:
                    party, partyU, party_is_new, log = save_and_return(party, partyU, log)
                    
                rolData = {'role':'Caucus Member','gov_level':'Federal','Party_id':party.id,'start_date':start_date.isoformat()}
                if end_date == None:
                    rolData['current'] = True
                else:
                    rolData['current'] = False
                    rolData['end_date'] = end_date.isoformat()
                person.update_role(personU, data=rolData)

            except Exception as e:
                prntDebug('mp role error 643', str(e))
    except Exception as e:
        prntDebug('mp error roles-affiliation 3565', str(e))
    try:
        prntDebug('roles-offices')
        
        table = soup.find('table', {'id':'roles-offices'})
        tbody = table.find('tbody')
        roles = tbody.find_all('tr', {'role':'row'})
        ordered += 1
        # personU.data['GovernmentPosition'] = ''
        for r in roles:
            # prntDebug(r)
            try:
                td = r.find_all('td')
                one = td[0].text
                two = td[1].text
                start = td[2].text
                end = td[3].text
                prnt('start',start)
                prnt('end',end)
                start_date = timezonify('est', datetime.datetime.strptime(start, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                if end:
                    end_date = timezonify('est', datetime.datetime.strptime(end, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                else:
                    end_date = None
                rolData = {'role':'Parliamentary Position','title':two,'parliament_number':one,'gov_level':'Federal','start_date':start_date.isoformat()}
                if end_date == None:
                    rolData['current'] = True
                else:
                    rolData['current'] = False
                    rolData['end_date'] = end_date.isoformat()
                person.update_role(personU, data=rolData)
            except Exception as e:
                prntDebug('mp role error 6424', str(e))
            # prntDebug('mpData111111', mpData)
            
    except Exception as e:
        prntDebug('mp roles-offices error 753', str(e))
    try:
        prntDebug('roles-committees')
        table = soup.find('table', {'id':'roles-committees'})
        tbody = table.find('tbody')
        roles = tbody.find_all('tr', {'role':'row'})
        ordered += 1
        for r in roles:
            try:
                td = r.find_all('td')
                one = td[0].text
                two = td[1].text
                three = td[2].text
                try:
                    group_link = td[2]['src']
                except:
                    pass
                start = td[3].text
                end = td[4].text
                start_date = timezonify('est', datetime.datetime.strptime(start, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                if end:
                    end_date = timezonify('est', datetime.datetime.strptime(end, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                else:
                    end_date = None 
                rolData = {'role':'Committee Member','affiliation':two,'group':three,'parliament_session':one,'gov_level':'Federal','start_date':start_date.isoformat()}
                if group_link:
                    rolData['group_link'] = group_link
                if end_date == None:
                    rolData['current'] = True
                else:
                    rolData['current'] = False
                    rolData['end_date'] = end_date.isoformat()
                person.update_role(personU, data=rolData)
            except Exception as e:
                prntDebug('mp roles error 3421', str(e))
                prntDebug(str(e))
    except Exception as e:
        prntDebug('mp roles-committees error 8626', str(e))
    try:
        prntDebug('roles-iia')
        table = soup.find('table', {'id':'roles-iia'})
        tbody = table.find('tbody')
        roles = tbody.find_all('tr', {'role':'row'})
        ordered += 1
        for r in roles:
            try:
                td = r.find_all('td')
                one = td[0].text
                two = td[1].text
                three = td[2].text
                start = td[3].text
                end = td[4].text
                start_date = timezonify('est', datetime.datetime.strptime(start, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                if end:
                    end_date = timezonify('est', datetime.datetime.strptime(end, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                else:
                    end_date = None
                rolData = {'role':'Parliamentary Association','group':three,'parliament_session':one,'gov_level':'Federal','start_date':start_date.isoformat()}
                if group_link:
                    rolData['group_link'] = group_link
                if end_date == None:
                    rolData['current'] = True
                else:
                    rolData['current'] = False
                    rolData['end_date'] = end_date.isoformat()
                person.update_role(personU, data=rolData)
            except Exception as e:
                prntDebug('mp roles error 9252', str(e))
                prntDebug(str(e))
    except Exception as e:
        prntDebug('mp roles-iia error 9235754', str(e))
    try:
        prntDebug('roles-elections')
        table = soup.find('table', {'id':'roles-elections'})
        tbody = table.find('tbody')
        roles = tbody.find_all('tr', {'role':'row'})
        ordered += 1
        for r in roles:
            try:
                td = r.find_all('td')
                end = td[0].text
                if end:
                    start_date = timezonify('est', datetime.datetime.strptime(end, '%A, %B %d, %Y').replace(tzinfo=pytz.UTC))
                else:
                    start_date = None
                two = td[1].text
                constituency_name = td[2].text
                province_name = td[3].text
                result = td[4].text

                prov = Region.objects.filter(Name=province_name, nameType='Province', modelType='provState', ParentRegion_obj=log.Region_obj).first()
                district = District.objects.filter(Q(Name=constituency_name)|Q(AltName=constituency_name.replace('—', ''))).filter(Country_obj=log.Region_obj, Region_obj=log.Region_obj, ProvState_obj=prov, gov_level='Federal', nameType='Federal District').first() #that character being removed is important, it is not a regular dash
                if district:
                    if not district.Office_array or 'Member of Parliament' not in district.Office_array:
                        modded_district = district.propose_modification()
                        modded_district.add_office('Member of Parliament')
                        log.updateShare(modded_district)
                if not district:
                    district = District(func=log.data['func'], Name=constituency_name, AltName=constituency_name.replace('—', ''), Country_obj=log.Region_obj, Region_obj=log.Region_obj, ProvState_obj=prov, gov_level='Federal', nameType='Federal District')
                    district.add_office(office)
                    log.updateShare(district)
                rolData = {'role':'Election Candidate','result':result,'group':two,'parliament_session':one,'gov_level':'Federal','start_date':start_date.isoformat()}
                if group_link:
                    rolData['group_link'] = group_link
                if end_date == None:
                    rolData['current'] = True
                else:
                    rolData['current'] = False
                    rolData['end_date'] = end_date.isoformat()
                person.update_role(personU, data=rolData)

            except Exception as e:
                prntDebug('mp roles error 13533', str(e))
    except Exception as e:
        prntDebug('mp roles-elections error 923575863564', str(e))
    # prntDebug('mpData', mpData)
    # shareData.append(save_obj_and_update(mp, mpU, mpData, mp_is_new))
    person, personU, person_is_new, log = save_and_return(person, personU, log)

    # prntDebug('-----------')
    # mp.save()
    # prntDebug('')
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()
    prntDebug('done get _MP', url)
    return log

def get_senate_persons(special=None, dt=now_utc(), iden=None):
    func = 'get_senate_persons'
    # gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country).first()
    # func = 'get_house_persons'
    # gov = None
    country = Region.objects.filter(modelType='country', Name='Canada').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    modded_country = None
    if not country.Office_array or 'Senator' not in country.Office_array:
        modded_country = country.propose_modification()
        modded_country.add_office('Senator')
        log.updateShare(modded_country)
    if not country.Chamber_array or 'Senate' not in country.Chamber_array:
        if not modded_country:
            modded_country = country.propose_modification()
        modded_country.add_chamber('Senate')
        log.updateShare(modded_country)

    if not special:
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country).first()
    
    # prntDebug('bill saved')

    # if bill_is_new:
    #     bill, billU, billData, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden, NumberCode=numCode)
    #     billV.Bill_obj = bill
    # prntDebug('save billv')
    # shareData.append(save_obj_and_update(billV, billVU, billVData, billV_is_new))

    # dt_now = now_utc()
    # today = dt_now - datetime.timedelta(hours=dt_now.hour, minutes=dt_now.minute, seconds=dt_now.second, microseconds=dt_now.microsecond)
    # country = Region.objects.filter(modelType='country', Name='Canada')[0]
    # ParliamentNumber = b.find('ParliamentNumber').text
    # SessionNumber = b.find('SessionNumber').text
    # try:
    #     gov = Government.objects.filter(Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)[0]
    # except:
    #     gov = Government(Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    #     gov.save()
    #     gov.end_previous()
    # gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country)[0]
    
    # gov, govU, govData, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    # if gov_is_new:
    #     shareData.append(gov.end_previous())
    #     shareData.append(save_obj_and_update(gov, govU, govData, gov_is_new))


    
    # gov, govU, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', gov_type='Parliament', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    # if gov_is_new:
    #     from blockchain.models import round_time
    #     gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
    #     gov.migrate_data()
    #     gov.LogoLinks = gov_logo_links
    #     # prev = gov.end_previous(func)
    #     # if prev:
    #     #     log.updateShare(prev)
    #     gov, govU, gov_is_new, log = save_and_return(gov, govU, log)
    prnt('gov',gov)


    chamber = 'Senate'
    # current_senators = Update.objects.filter(Role_obj__Position='Senator', data__icontains='"Current": true', Role_obj__gov_level='Federal', Country_obj=country)


    url = 'https://sencanada.ca/en/senators'
    driver = open_browser(url, headless=False)
    # prntDebug("opening browser")
    # chrome_options = Options()
    # chrome_options.add_argument('--no-sandbox')
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    # driver = webdriver.Chrome(options=chrome_options)
    # caps = DesiredCapabilities().CHROME
    # caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    # driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    # driver.get(url)
    # time.sleep(5)
    element_present = EC.presence_of_element_located((By.CLASS_NAME, 'sc-senators-political-card'))
    WebDriverWait(driver, 10).until(element_present)
    s_cards = driver.find_elements(By.CLASS_NAME, 'sc-senators-political-card')
    # senators = Role.objects.filter(position='Senator', current=True)
    # for s in senators:
    #     s.current = False
    #     s.save()
    updated_senators = []
    order_num = 0
    first_batch = []
    for c in s_cards:
        a = c.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
        govPage = a
        # govPage = url + a
        src = c.find_element(By.CSS_SELECTOR, "img").get_attribute('src')
        try:
            title = c.find_element(By.CLASS_NAME, 'sc-senators-political-card-title').text
            # prntDebug(title)
        except Exception as e:
            prntDebug(str(e))
            title = None
        prntDebug(title)
        h = c.find_element(By.CSS_SELECTOR, 'h5').text
        h1 = h.find(', ')
        last_name = h[:h1]
        first_name = h[h1+2:]
        prntDebug(first_name)
        prntDebug(last_name)
        # p = c.find_element(By.CSS_SELECTOR, "p").text
        # p1 = p.find(' - ')
        # p2 = p[p1+3:]
        # prntDebug(p2)
        # try:
        #     p3 = p2.find(' (')
        #     provName = p2[:p3]
        # except:
        #     provName = p2
        prntDebug('')
        party = None
        prov = None
        district = None
        region_name = None
        district_name = None
        party_prov = c.find_element(By.CLASS_NAME, 'sc-senators-political-card-text-province').text
        
        if ' - ' in party_prov:
            # PSG - Prince Edward Island (Epekwitk, Mi'kma'ki)
            # ISG - Quebec - Gulf
            # Non-affiliated - Manitoba

            a = party_prov.find(' - ')
            party_short = party_prov[:a]
            party_name, party_short, alt_name = find_party(party_short=party_short)
            party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=log.Region_obj, Region_obj=log.Region_obj, gov_level='Federal')
            if party_is_new and get_wiki:
                try:
                    time.sleep(1)
                    search_name = f'Canadian {party_name} federal political party'
                    prnt(search_name)
                    link = wikipedia.search(search_name)[0].replace(' ', '_')
                    party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                    prnt('party.Wiki',party.Wiki)
                except Exception as e:
                    prnt('party:',str(e))
                    pass
                
            if ' - ' in party_prov[a+len(' - '):]:
                b = party_prov[a+len(' - '):].find(' - ')
                district_name = party_prov[a+len(' - ')+b+len(' - '):].strip()
                region_name = party_prov[a+len(' - '):a+len(' - ')+b].strip()
            elif ' (' in party_prov[a+len(' - '):]:
                b = party_prov[a+len(' - '):].find('(')
                district_name = party_prov[a+len(' - ')+b+1:].replace(')','').strip()
                region_name = party_prov[a+len(' - '):a+len(' - ')+b].strip()
            else:
                district_name = party_prov[a+len(' - '):].strip()
                region_name = district_name
        prnt('region_name',region_name)
        prnt('district_name',district_name)
        if region_name:
            AbbrName = None
            if region_name in province_list:
                AbbrName = province_list[region_name]
            if region_name in prov_or_terr:
                region_type = prov_or_terr[region_name]
            else:
                region_type = 'Province'
            prov = Region.valid_objects.filter(Name=region_name, AbbrName=AbbrName, modelType='provState', ParentRegion_obj=country).first()
            # if state:
            if not prov:
                prov = Region(func=func, Name=region_name, AbbrName=AbbrName, nameType=region_type, modelType='provState', ParentRegion_obj=country)
                prov.update_data()
                log.updateShare(prov)

            if district_name:
                district = District.objects.filter(Name=district_name, Country_obj=country, Region_obj=country, ProvState_obj=prov, gov_level='Federal', nameType='Federal District').first()
                if district:
                    if not district.Office_array or 'Senator' not in district.Office_array:
                        modded_district = district.propose_modification()
                        modded_district.add_office('Senator')
                        log.updateShare(modded_district)
                else:
                    district = District(func=func, Name=district_name, Country_obj=country, Region_obj=country, ProvState_obj=prov, gov_level='Federal', nameType='Federal District')
                    district.add_office('Senator')
                    log.updateShare(district)

        
        person, personU, person_is_new = get_model_and_update('Person', GovProfilePage=govPage, Country_obj=log.Region_obj, Region_obj=log.Region_obj)
        
        
        personU.data['FirstName'] = first_name
        personU.data['LastName'] = last_name
        personU.data['FullName'] = first_name + ' ' + last_name
        # mp.gov_profile_page = m['link']
        personU.data['PhotoLink'] = src
        personU.data['Chamber'] = chamber
        if district:
            personU.data['District_id'] = district.id
        personU.data['ProvState_id'] = prov.id if prov else prov
        personU.data['Position'] = 'Senator'
        personU.data['gov_level'] = 'Federal'
        personU.data['Party_id'] = party.id if party else party
        person.update_role(personU, data={'role':'Senator','gov_level':'Federal','current':True})

        order_num += 1
        first_batch.append(govPage)
        
        # shareData.append(save_obj_and_update(role, roleU, roleData, role_is_new))
        updated_senators.append({'link':govPage,'order_num':order_num,'data':{'person':person,'personU':personU,'person_is_new':person_is_new}})
        
    # title = None
    prntDebug('-------second list-------')
    s_cards = driver.find_elements(By.CLASS_NAME, 'sc-senators-senator-card')
    for c in s_cards:
        a = c.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
        govPage = a
        src = c.find_element(By.CSS_SELECTOR, "img").get_attribute('src')
        name_text = c.find_element(By.CLASS_NAME, 'sc-senators-senator-card-text-name').text
        h1 = name_text.find(', ')
        last_name = name_text[:h1]
        first_name = name_text[h1+2:]
        prntDebug(first_name)
        prntDebug(last_name)
        p = c.find_element(By.CSS_SELECTOR, "p").text
        p1 = p.find(' - ')
        p2 = p[p1+3:]
        try:
            p3 = p2.find(' (')
            provName = p2[:p3]
        except:
            provName = p2
        prntDebug('')
        
        if govPage not in first_batch:
            party = None
            prov = None
            region_name = None
            district_name = None
            party_prov = c.find_element(By.CLASS_NAME, 'sc-senators-senator-card-text-province').text
            if ' - ' in party_prov:
                # PSG - Prince Edward Island (Epekwitk, Mi'kma'ki)
                # ISG - Quebec - Gulf
                # Non-affiliated - Manitoba

                a = party_prov.find(' - ')
                party_short = party_prov[:a]
                party_name, party_short, alt_name = find_party(party_short=party_short)
                party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=log.Region_obj, Region_obj=log.Region_obj, gov_level='Federal')
                if party_is_new and get_wiki:
                    try:
                        time.sleep(1)
                        search_name = f'Canadian {party_name} federal political party'
                        prnt(search_name)
                        link = wikipedia.search(search_name)[0].replace(' ', '_')
                        party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                        prnt('party.Wiki',party.Wiki)
                    except Exception as e:
                        prnt('party:',str(e))
                        pass
                    
                if ' - ' in party_prov[a+len(' - '):]:
                    b = party_prov[a+len(' - '):].find(' - ')
                    district_name = party_prov[a+len(' - ')+b+len(' - '):].strip()
                    region_name = party_prov[a+len(' - '):a+len(' - ')+b].strip()
                elif ' (' in party_prov[a+len(' - '):]:
                    b = party_prov[a+len(' - '):].find('(')
                    district_name = party_prov[a+len(' - ')+b+1:].replace(')','').strip()
                    region_name = party_prov[a+len(' - '):a+len(' - ')+b].strip()
                else:
                    district_name = party_prov[a+len(' - '):].strip()
                    region_name = district_name

            prnt('region_name',region_name)
            prnt('district_name',district_name)
            if region_name:
                AbbrName = None
                if region_name in province_list:
                    AbbrName = province_list[region_name]
                if region_name in prov_or_terr:
                    region_type = prov_or_terr[region_name]
                else:
                    region_type = 'Province'
                prov = Region.valid_objects.filter(Name=region_name, AbbrName=AbbrName, modelType='provState', ParentRegion_obj=country).first()
                # if state:
                if not prov:
                    prov = Region(func=func, Name=region_name, AbbrName=AbbrName, nameType=region_type, modelType='provState', ParentRegion_obj=country)
                    prov.update_data()
                    log.updateShare(prov)

                if district_name:
                    district = District.objects.filter(Name=district_name, Country_obj=country, Region_obj=country, ProvState_obj=prov, gov_level='Federal', nameType='Federal District').first()
                    if district:
                        if not district.Office_array or 'Senator' not in district.Office_array:
                            modded_district = district.propose_modification()
                            modded_district.add_office('Senator')
                            log.updateShare(modded_district)
                    else:
                        district = District(func=func, Name=district_name, Country_obj=country, Region_obj=country, ProvState_obj=prov, gov_level='Federal', nameType='Federal District')
                        # try:
                        #     dNum = get_ordinal(int(district_name))
                        # except:
                        #     dNum = district_name
                        # if get_wiki:
                        #     try:
                        #         time.sleep(1)
                        #         search_name = dNum + ' congressional district of ' + region_name
                        #         prnt('search_name',search_name)
                        #         title = wikipedia.search(search_name)[0].replace(' ', '_')
                        #         district.Wiki = 'https://en.wikipedia.org/wiki/' + title
                        #         prnt('district.Wiki',district.Wiki)
                        #         # district.update_data()
                        #     except Exception as e:
                        #         prnt(str(e))
                        district.add_office('Senator')
                        log.updateShare(district)

                

            person, personU, person_is_new = get_model_and_update('Person', GovProfilePage=govPage, Country_obj=log.Region_obj, Region_obj=log.Region_obj)
            order_num += 1

            personU.data['FirstName'] = first_name
            personU.data['LastName'] = last_name
            # mp.gov_profile_page = m['link']
            personU.data['PhotoLink'] = src
            personU.data['Chamber'] = chamber
            # personU.data['District_id'] = district.id
            personU.data['ProvState_id'] = prov.id if prov else prov
            personU.data['Position'] = 'Senator'
            personU.data['gov_level'] = 'Federal'
            personU.data['Party_id'] = party.id if party else party
            person.update_role(personU, data={'role':'Senator','gov_level':'Federal','current':True})
            # person, personU, person_is_new, log = save_and_return(person, personU, log)
            updated_senators.append({'link':govPage,'order_num':order_num,'data':{'person':person,'personU':personU,'person_is_new':person_is_new}})

    prntDebug('get details')
    # current_senators = Role.objects.filter(position='Senator', current=True).select_related('person')
    # updated_senators = Update.objects.filter(Role_obj__Position='Senator', data__icontains='"Current": true', Role_obj__gov_level='Federal', Country_obj=country)
    prntDebug('-------current senators-------')
    current_senators = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, extra__roles__contains=[{'role':'Senator','current':True, 'gov_level':'Federal'}])
    for update in current_senators:
        prnt('upd',update)
        if not any(i for i in updated_senators if i['data']['person'].id == update.pointerId):
            prnt('sen not in scraped list')
            prnt('update.Pointer_obj')
        # if update.pointerId not in str(updated_senators):
            if 'Position' in update.data and update.data['Position'] == 'Senator':
                del update.data['Position']
            update.Pointer_obj.update_role(personU, data={'role':'Senator','gov_level':'Federal','current':False})
            update.save_if_new()
            log.updateShare(update)

            # role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=u.Role_obj)
            # roleData['Current'] = False
            # # shareData.append(save_obj_and_update(role, roleU, roleData, role_is_new))
            # role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
    prnt('----updated senators:-----')
    for i in updated_senators:
        # role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=r)
        # person, personU, personData, person_is_new = get_model_and_update('Person', obj=role.Person_obj)
        person = i['data']['person']
        personU = i['data']['personU']
        person_is_new = i['data']['person_is_new']
        # r = u.Role_obj
        # uData = json.loads(u.data)
        prntDebug(i['link'])
        if person_is_new or not person.GovIden:
            # 'sen_pho_official'
            try:
                time.sleep(3)
                driver.get(i['link'])
                prntDebug('retreived')
                element_present = EC.presence_of_element_located((By.CLASS_NAME, 'senatorbiography'))
                WebDriverWait(driver, 20).until(element_present)
                items = driver.find_elements(By.CLASS_NAME, 'sc-senator-bio-senatorheader-content-card-list-item')
                for item in items:
                    # prntDebug(item.text)
                    # if 'Affiliation' in item.text:
                        # personU.data['Affiliation'] = item.text.replace('Affiliation: ', '')
                        # r.person.party_name = r.affiliation
                        # party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=personU.data['Affiliation'], chamber=chamber, Country_obj=country, Region_obj=country, gov_level='Federal')
                        # if party_is_new:
                        #     party, partyU, partyData, party_is_new, shareData = save_and_return(party, partyU, partyData, party_is_new, shareData, func)

                        # party_name, party_short, alt_name = find_party(party_short=party_short)
                        # party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=country, Region_obj=country, gov_level='Federal')
                        # if party_is_new:
                        #     if get_wiki:
                        #         try:
                        #             time.sleep(1)
                        #             search_name = party_name + ' american federal political party'
                        #             prnt(search_name)
                        #             link = wikipedia.search(search_name)[0].replace(' ', '_')
                        #             party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                        #             prnt('party.Wiki',party.Wiki)
                        #         except Exception as e:
                        #             prnt('party:',str(e))
                        #             pass
                        #     party, partyU, party_is_new, log = save_and_return(party, partyU, log)
                        
                        # personU.data['Party_id'] = party.id
                        # if party_is_new:
                        #     shareData.append(save_obj_and_update(party, partyU, partyData, party_is_new))
                        #     party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=roleData['Affiliation'], chamber=chamber, Country_obj=country, Region_obj=country, gov_level='Federal')

                        # personU.Party_obj = party
                        # roleU.Party_obj = party
                        # try:
                        #     party = Party.objects.filter(Name=uData['Affiliation'], gov_level='Federal', chamber=chamber)[0]
                        # except:
                        #     prntDebug('creating party')
                        #     prntDebug(r.affiliation)
                        #     party = Party(name=r.affiliation, level='Senate')
                        #     party.save()
                        #     party.create_post()
                        # r.party = party
                        # r.person.party = party
                    if 'Personal Website' in item.text:
                        # r.person.website = item.text.replace('Personal Website: ', '')
                        personU.data['Website'] = item.text.replace('Personal Website: ', '')
                    elif 'Email' in item.text:
                        # r.person.email = item.text.replace('Email: ', '').replace('Electronic card', '').replace('&nbsp;', '')
                        personU.data['Email'] = item.text.replace('Email: ', '').replace('Electronic card', '').replace('&nbsp;', '')

                        
                        links = item.find_elements(By.CSS_SELECTOR, 'a')
                        for l in links:
                            if 'vcard/senator' in l.get_attribute('href'):
                                # r.person.twitter = l.get_attribute('href')
                                href = l.get_attribute('href')
                                print('---vcard taken', href)
                                a = href.find('/senator/en/')+len('/senator/en/')
                                # b = votes_link[a:].find('/')
                                iden = href[a:]
                                prntDebug('idn',iden)
                                person.GovIden = iden

                        # links = item.find_all('a')
                        # for link in links:
                        #     print('link',link)
                        #     print('linkref',link['href'])
                        #     if link['href'] and 'vcard/senator' in link['href']:
                        #         print('---vcard taken', link['href'])
                        #         a = link['href'].find('/senator/en/')+len('/senator/en/')
                        #         # b = votes_link[a:].find('/')
                        #         iden = link['href'][a:]
                        #         prntDebug('idn',iden)
                        #         person.GovIden = iden
                    elif 'Telephone' in item.text:
                        # r.person.telephone = item.text.replace('Telephone: ', '')
                        personU.data['Telephone'] = item.text.replace('Telephone: ', '')
                    elif 'Follow' in item.text:
                        links = item.find_elements(By.CSS_SELECTOR, 'a')
                        for l in links:
                            if 'twitter' in l.get_attribute('href'):
                                # r.person.twitter = l.get_attribute('href')
                                personU.data['XTwitter'] = l.get_attribute('href')

                prntDebug('')
                prnt('personU.data',personU.data)
                bio = driver.find_element(By.CLASS_NAME, 'senatorbiography').text
                personU.extra['Bio'] = bio
            except Exception as e:
                prntDebug('fail get senator details', str(e))
                time.sleep(5)
            # prntDebug('1111')



#             try:
#   soup = BeautifulSoup(driver.page_source, 'html.parser')
#   # sc-senator-bio-senatorheader-content-card-list

#   bio_cards = soup.find_all('li',{'class':'sc-senator-bio-senatorheader-content-card-list-item'})
#         # div = soup.find('div', {'id':'house-in-session'}).text
#   for item in bio_cards:
#       print('item',item )
#       links = item.find_all('a')
#       for link in links:
#           print('link',link)
#           print('linkref',link['href'])
#           if link['href'] and 'vcard/senator' in link['href']:
#             print('---vcard taken', link['href'])
#             break
# except Exception as e:


            # try:
            #     prntDebug('retrieve2')
            #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            #     element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="pills-votes-tab"]'))
            #     WebDriverWait(driver, 20).until(element_present)
            #     # time.sleep(2)
            #     votes_button = driver.find_element(By.XPATH, '//*[@id="pills-votes-tab"]')
            #     prntDebug('btn',votes_button.text)
            #     votes_button.click()
            #     time.sleep(1)
            #     votes_link = driver.find_element(By.XPATH, '//*[@id="pills-votes"]/div/div[2]/p/a').get_attribute('href')
            #     prntDebug('vlink',votes_link)
            #     a = votes_link.find('/senator/')+len('/senator/')
            #     b = votes_link[a:].find('/')
            #     iden = votes_link[a:a+b]
            #     prntDebug('idn',iden)
            #     person.GovIden = iden
            # except Exception as e:
            #     prntDebug('fail get senator iden', str(e))
            #     time.sleep(10)
            # prntDebug('roleData', roleData)
            # r.person.save()
            # r.save()
            # prntDebug('save obj and update')
        # person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
        # role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
        if person.GovIden:
            person, personU, person_is_new, log = save_and_return(person, personU, log)
        # shareData.append(save_obj_and_update(person, personU, personData, person_is_new))
        # shareData.append(save_obj_and_update(role, roleU, roleData, role_is_new))

        prntDebug('saved')
        time.sleep(2)
    try:
        driver.quit()
    except:
        pass
    return finishScript(log, gov, special)

def get_house_agendas(url='https://www.ourcommons.ca/en/parliamentary-business/', special=None, dt=now_utc(), iden=None):
    func = 'get_house_agendas'
    country = Region.objects.filter(modelType='country', Name='Canada').first()
    # log = create_share_object(func, country, special=special)
    # if not special:
    #     logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')

    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')


    # url = 'https://www.ourcommons.ca/en/parliamentary-business/2022-12-14'
    date_time = None
    dt_now = now_utc()
    today = dt_now - datetime.timedelta(hours=dt_now.hour, minutes=dt_now.minute, seconds=dt_now.second, microseconds=dt_now.microsecond)
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    try:
        session = soup.find('span', {'class':'session-subtitle'})
        prntDebug(session)
        '(44th Parliament, 1st Session)'
        t = session.text.replace('(', '').replace(')','')
        a = t.find(' Parliament, ')
        b = t.find(' Session')
        parl = t[:a].replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
        sess = t[a+len(' Parliament, '):b].replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
        today = soup.find('span', {'class':'session-title'}).text
        # prntDebug(today)
        # 'Sunday, June 25, 2023'
        d = today.rfind(',')
        e = today[d-2:d]
        if e[0] == ' ':
            e = '0' + e[1]
            today = today[:d-1] + e + today[d:]
        dt = datetime.datetime.strptime(today, '%A, %B %d, %Y')
        prntDebug(dt)
        gov, govU, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', gov_type='Parliament', GovernmentNumber=int(parl), SessionNumber=int(sess), Region_obj=country)
        if gov_is_new:
            from blockchain.models import round_time
            gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
            gov.migrate_data()
            gov.LogoLinks = gov_logo_links
            gov, govU, gov_is_new, log = save_and_return(gov, govU, log)
    except Exception as e:
        prntDebug('fail48257',str(e))
        dt = today
        gov = Government.objects.filter(Region_obj=country, Country_obj=country, gov_level='Federal').first()
        if not gov:
            url = 'https://www.parl.ca/LegisInfo/en/overview/xml/recentlyintroduced'
            r = requests.get(url, verify=False)
            root = ET.fromstring(r.content)
            bills = root.findall('Bill')
            for b in bills:
                ShortTitle = b.find('ShortTitle').text
                prntDebug(ShortTitle)
                parl = b.find('ParliamentNumber').text
                sess = b.find('SessionNumber').text
                if parl:
                    break
            gov, govU, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', gov_type='Parliament', GovernmentNumber=int(parl), SessionNumber=int(sess), Region_obj=country)
            if gov_is_new:
                from blockchain.models import round_time
                gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
                gov.migrate_data()
                gov.LogoLinks = gov_logo_links
                gov, govU, gov_is_new, log = save_and_return(gov, govU, log)
        elif not gov.Validator_obj or not gov.Validator_obj.is_valid:
            log.updateShare(gov)

    try:
        section = soup.find('section', {'class':'block-in-the-chamber'})
        watch = section.find('div', {'class':'watch-previous'})
        watch_link = watch.find('a')['href']
    except Exception as e:
        prnt('agenda fail 453',str(e))
        return finishScript(log, gov, special)

    # prntDebug(watch_link)
    try:
        status = soup.find('p', {'class':'chamber-status'})
        prntDebug(status.text.replace('.','').replace('\r','').replace('\n','').strip())
        # 'The House is adjourned until Monday, December 5, 2022 at 11:00 a.m. (EST).'
        # time data 'The House is adjourned until Monday, January 27, 2025' does not match format 'The House is adjourned until %A, %B %d, %Y at %H:%M %p (EDT)'
        if 'a.m.' in status.text or 'p.m.' in status.text:
            if '(EST)' in status.text:
                date_time = datetime.datetime.strptime(status.text.replace('.','').replace('\r','').replace('\n','').strip(), 'The House is adjourned until %A, %B %d, %Y at %H:%M %p (EST)')
            elif '(EDT)' in status.text:
                date_time = datetime.datetime.strptime(status.text.replace('.','').replace('\r','').replace('\n','').strip(), 'The House is adjourned until %A, %B %d, %Y at %H:%M %p (EDT)')
            else:
                date_time = datetime.datetime.strptime(status.text.replace('.','').replace('\r','').replace('\n','').strip(), 'The House is adjourned until %A, %B %d, %Y at %H:%M %p')
        else:
            if '(EST)' in status.text:
                date_time = datetime.datetime.strptime(status.text.replace('.','').replace('\r','').replace('\n','').strip(), 'The House is adjourned until %A, %B %d, %Y (EST)')
            elif '(EDT)' in status.text:
                date_time = datetime.datetime.strptime(status.text.replace('.','').replace('\r','').replace('\n','').strip(), 'The House is adjourned until %A, %B %d, %Y (EDT)')
            else:
                date_time = datetime.datetime.strptime(status.text.replace('.','').replace('\r','').replace('\n','').strip(), 'The House is adjourned until %A, %B %d, %Y')

    except Exception as e:
        prntDebug('fil47265',str(e))
        # date_time = datetime.datetime.strptime(url, 'https://www.ourcommons.ca/en/parliamentary-business/%Y-%m-%d')
    try:
        widget = section.find('div', {'class':'agenda-widget-content-wrapper'})
        if widget:
            date = widget.find('div').text.strip()
            prntDebug(date)
            'Agenda for Monday, November 28, 2022'
            date_time = datetime.datetime.strptime(date, 'Agenda for %A, %B %d, %Y')
    except Exception as e:
        prntDebug('fail48364',str(e))
    if not date_time:
        return finishScript(log, gov, special)
    date_time = timezonify('est', date_time.replace(tzinfo=pytz.UTC))

    def get_video_code():
        r = requests.get('http:' + watch_link, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        iden = str(soup).find('contentEntityId')+len('contentEntityId')
        # prntDebug(str(soup)[iden:iden+20])
        a = str(soup)[iden:].find(' = ')+len(' = ')
        b = str(soup)[iden+a:].find(';')
        special = str(soup)[iden+a:iden+a+b]
        # if isinstance(special, int):
        #     A.videoCode = special
        # try:
        #     A.VideoCode = int(special)
        # except Exception as e:
        #     prntDebug(str(e))
        return int(special)
    prntDebug('1',date_time)
    agenda = Agenda.objects.filter(DateTime__gte=date_time, DateTime__lt=date_time + datetime.timedelta(days=1), Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country).first()
    if agenda:
        agenda, agendaU, agenda_is_new = get_model_and_update('Agenda', obj=agenda)
    else:
        agenda, agendaU, agenda_is_new = get_model_and_update('Agenda', DateTime=date_time, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
        agenda, agendaU, agenda_is_new, log = save_and_return(agenda, agendaU, log)
    prntDebug('2',agenda)
    # if agenda_is_new:
    #     meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', meeting_type='Debate', Government_obj=gov, Country_obj=country, DateTime=date_time, Chamber='House', Region_obj=country)
    #     meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)
    prntDebug('3')
    if not 'VideoURL' in agendaU.data or agendaU.data['VideoURL'] != watch_link:
        agendaU.data['VideoURL'] = get_video_code()
    try:
        if 'adjourned' in status.text:
            # fail48264,time data 'The House is adjourned until Monday, January 27, 2025' does not match format 'The House is adjourned until %A, %B %d, %Y at %I:%M %p (%Z)'
            if 'a.m.' in status.text or 'p.m.' in status.text:
                nextDt = datetime.datetime.strptime(status.text.strip().replace('.', ''), 'The House is adjourned until %A, %B %d, %Y at %I:%M %p (%Z)')
            else:
                nextDt = datetime.datetime.strptime(status.text.strip().replace('.', ''), 'The House is adjourned until %A, %B %d, %Y')
            nextDt = timezonify('est', nextDt.replace(tzinfo=pytz.UTC))
            agendaU.data['NextDateTime'] = nextDt.isoformat()
        agendaU.data['CurrentStatus'] = status.text.strip()
        # prntDebug(A.current_status)
    except Exception as e:
        prntDebug('fail48264',str(e))
        agendaU.data['CurrentStatus'] = 'Adjourned'
        prnt('Adjourned')
    prntDebug('4')
    if widget:
        agenda = widget.find('div', {'class':'agenda-items'})
        divs = agenda.find_all('div', {'class':'row'})
        position = 0
        start_time = None
        agendaTime = None
        if not agenda.data:
            agenda.data = {}
        for div in divs:
            position += 1
            try:
                hour = div.find('span', {'class':'the-time'}).text.strip()
                # prntDebug('\n', hour)
                item_time = datetime.datetime.strptime(date + ' / ' + hour.replace('.',''), 'Agenda for %A, %B %d, %Y / %I:%M %p')
                item_time = timezonify('est', item_time.replace(tzinfo=pytz.UTC))
                prntDebug(item_time)
                if not start_time:
                    start_time = item_time
                    agenda.DateTime = item_time
                agendaTime = item_time.isoformat()
            except Exception as e:
                prntDebug('fail58204873', str(e))
            agenda.data[position] = {'dt':agendaTime}
            try:
                title = div.find('div', {'class':'agenda-item-title'}).text.strip()
                prntDebug(title)
                agenda.data[position]['text'] = title
                if ' ╼ ' in title:
                    a = title.find(' ╼ ')
                    bill = Bill.objects.filter(NumberCode=title[:a], Government_obj=gov, Country_obj=country, Region_obj=country).first()
                    if bill:
                        if not agenda.bill_dict:
                            agenda.bill_dict = {}
                        agenda.bill_dict[bill.NumberCode] = bill.id
            except Exception as e:
                prntDebug('fail49385',str(e))
    agenda, agendaU, agenda_is_new, log = save_and_return(agenda, agendaU, log)
    return finishScript(log, gov, special)

def get_house_bills(special=None, dt=now_utc(), iden=None):
    func = 'get_house_bills'
    shareData, gov = get_recent_bills(special=special, dt=dt, func=func, iden=iden)
    # prntDebug('sharedata:', shareData)
    send_for_validation(shareData, gov, func)

def get_senate_bills(special=None, dt=now_utc(), iden=None):
    func = 'get_senate_bills'
    shareData, gov = get_recent_bills(special=special, dt=dt, func=func, iden=iden)
    send_for_validation(shareData, gov, func)

def get_house_debates(object_type='hansard', value='latest'):
    # meetings = Meeting.objects.filter(meeting_type='Debate', chamber='House', DateTime__gte=now_utc() - datetime.timedelta(days=2), DateTime__lte=datetime.datetime.combine(now_utc().date(), datetime.datetime.min.time()), Region_obj=Region.objects.filter(modelType='country', Name='Canada')[0], has_transcript=False)
    meetings = Post.objects.filter(Meeting_obj__meeting_type='Debate', Meeting_obj__chamber='House', Meeting_obj__DateTime__gte=now_utc() - datetime.timedelta(days=2), Meeting_obj__DateTime__lte=datetime.datetime.combine(now_utc().date(), datetime.datetime.min.time()), Region_obj=Region.objects.filter(modelType='country', Name='Canada')[0]).exclude(Update_obj__data__contains='"has_transcript": true')
    if meetings.count() > 0:
        func = 'get_house_debates'
        shareData, gov = get_house_hansard_or_committee(object_type, value, func)
        prntDebug('get house debates step 2')
        send_for_validation(shareData, gov, func)
        prntDebug('done done')

def get_senate_debates(time='latest'):
    # meetings = Meeting.objects.filter(meeting_type='Debate', chamber='Senate', DateTime__gte=now_utc() - datetime.timedelta(days=2), DateTime__lte=datetime.datetime.combine(now_utc().date(), datetime.datetime.min.time()), Region_obj=Region.objects.filter(modelType='country', Name='Canada')[0], has_transcript=False)
    meetings = Post.objects.filter(Meeting_obj__meeting_type='Debate', Meeting_obj__chamber='Senate', Meeting_obj__DateTime__gte=now_utc() - datetime.timedelta(days=2), Meeting_obj__DateTime__lte=datetime.datetime.combine(now_utc().date(), datetime.datetime.min.time()), Region_obj=Region.objects.filter(modelType='country', Name='Canada')[0]).exclude(Update_obj__data__contains='"has_transcript": true')
    if meetings.count() > 0:
        func = 'get_senate_debates'
        shareData = []
        if time == 'latest':
            prntDebug('---------------------senate hansards')
            debate = 'https://sencanada.ca/en/in-the-chamber/debates/'
            r = requests.get(debate)
            soup = BeautifulSoup(r.content, 'html.parser')
            links = soup.find_all('a')
            for a in reversed(links[:5]):
                if '\content' in a['href'] and '\debates' in a['href']:
                    link = 'https://sencanada.ca' + a['href'].replace('\\','/')
                    data, gov = add_senate_hansard(link, False, func)
                    for d in data:
                        shareData.append(d)
                    break
        elif time == 'alltime':
            sessions = ['44-1', '43-2', '43-1', '42-1', '41-2', '41-1', '40-3', '40-2', '40-1', '39-2','39-1','38-1', '37-3','37-2','37-1','36-2','36-1','35-2']
            for s in sessions:
                debate = 'https://sencanada.ca/en/in-the-chamber/debates/%s' %(s)
                r = requests.get(debate)
                soup = BeautifulSoup(r.content, 'html.parser')
                links = soup.find_all('a')
                for a in reversed(links):
                    if '\content' in a['href'] and '\debates' in a['href']:
                        link = 'https://sencanada.ca' + a['href'].replace('\\','/')
                        prntDebug('')
                        prntDebug(link)
                        data, gov = add_senate_hansard(link, False, func)
                        for d in data:
                            shareData.append(d)
                        time.sleep(2)
        send_for_validation(shareData, gov, func)

def get_todays_xml_agenda():
    prntDebug('---------------------xml agenda')
    func = 'get_todays_xml_agenda'
    shareData = []
    url = 'https://www.parl.ca/LegisInfo/en/overview/xml/onagenda'
    r = requests.get(url, verify=False)
    root = ET.fromstring(r.content)
    bills = root.findall('Bill')
    for b in bills:
        ShortTitle = b.find('ShortTitle').text
        prntDebug(ShortTitle)
        data, gov = get_bill(b, func)
        for d in data:
            shareData.append(d)
    send_for_validation(shareData, gov, func)
        # break

def get_house_motions():
    prntDebug('---------------------house motions')
    country = Region.objects.filter(modelType='country', Name='Canada')[0]
    try:
        meeting = Post.objects.filter(Meeting_obj__meeting_type='Debate', Meeting_obj__chamber='House', Meeting_obj__DateTime__gte=now_utc() - datetime.timedelta(days=2), Meeting_obj__DateTime__lte=datetime.datetime.combine(now_utc().date(), datetime.datetime.min.time()), Region_obj=Region.objects.filter(modelType='country', Name='Canada')[0], Update_obj__data__contains='"has_transcript": true')[0]
        recent_motion = Motion.objects.filter(chamber='House', Country_obj=country, Region_obj=country, DateTime__gte=meeting.Meeting_obj.DateTime)[0]
    except:
        shareData = []
        func = 'get_house_motions'
        # prntDebug('-----get latest house motions')
        vote1 = 'https://www.ourcommons.ca/members/en/votes/xml'
        # prntDebug(vote1)
        r = requests.get(vote1, verify=False)
        root = ET.fromstring(r.content)
        motions = root.findall('Vote')
        # count = 0
        motion_list = []
        for motion in reversed(motions[:10]):
            m, gov, shareData = add_motion(motion, shareData, func)
            motion_list.append(m)
            prntDebug('-----------')
            # break
        
        # parl = Parliament.objects.filter(country='Canada', organization='Federal')[0]
        # total_motions = Motion.objects.filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='House of Commons')).filter(ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber).count()
        # roles = Role.objects.filter(position='Member of Parliament', current=True).order_by('person')
        # mps = {}
        # for r in roles:
        #     # prntDebug(r.person)
        #     mps[r.person] = 0
        # for m in motion_list:
        #     # prntDebug(m)
        #     votes = Vote.objects.filter(motion=m)
        #     for v in votes:
        #         try:
        #             if v.person:
        #                 mps[v.person] += 1
        #         except Exception as e:
        #             # prntDebug(str(e))
        #             pass
        # for r in roles:
        #     # prntDebug(r.person)
        #     try:
        #         r.attendanceCount += mps[r.person]
        #         # prntDebug(r.attendanceCount, total, str((r.attendanceCount/total)*100))
        #         r.attendancePercent = int((r.attendanceCount/total_motions)*100)
        #         r.save()
        #         # prntDebug(r.attendancePercent)
        #     except Exception as e:
        #         prntDebug(str(e))
        send_for_validation(shareData, gov, func)
    
def get_senate_motions(time='latest'):    
    prntDebug('---------------------senate motions')
    country = Region.objects.filter(modelType='country', Name='Canada')[0]
    try:
        meeting = Post.objects.filter(Meeting_obj__meeting_type='Debate', Meeting_obj__chamber='Senate', Meeting_obj__DateTime__gte=now_utc() - datetime.timedelta(days=2), Meeting_obj__DateTime__lte=datetime.datetime.combine(now_utc().date(), datetime.datetime.min.time()), Region_obj=Region.objects.filter(modelType='country', Name='Canada')[0], Update_obj__data__contains='"has_transcript": true')[0]
        recent_motion = Motion.objects.filter(chamber='Senate', Country_obj=country, Region_obj=country, DateTime__gte=meeting.Meeting_obj.DateTime)[0]
    except:
        func = 'get_senate_motions'
        shareData = []
        if time == 'latest':
            url = 'https://sencanada.ca/en/in-the-chamber/votes/'
            r = requests.get(url)
            soup = BeautifulSoup(r.content, 'html.parser')
            section = soup.find('section', {'class':'votes-page'})
            tbody = section.find('tbody')
            trs = tbody.find_all('tr')
            m_num = 0
            for tr in reversed(trs):
                gov, shareData = add_senate_motion(tr, shareData, func)
                break
        elif time == 'alltime':
            sessions = ['43-2', '43-1', '42-1']
            for s in reversed(sessions):
                url = 'https://sencanada.ca/en/in-the-chamber/votes/%s' %(s)
                prntDebug(url)
                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'html.parser')
                section = soup.find('section', {'class':'votes-page'})
                tbody = section.find('tbody')
                trs = tbody.find_all('tr')
                m_num = 0
                for tr in reversed(trs):
                    gov, shareData = add_senate_motion(tr, shareData, func)

                    # prntDebug('----')
            # m_num += 1
            # prntDebug('m_num:', m_num)
            # if m_num >= 6:
            #     break
        send_for_validation(shareData, gov, func)

def get_user_region(u, url):
    func = 'get_user_region'
    shareData = []

    # u = user
    # items = []
    result = {}
    result['greaterMunicipality_name'] = ''
    result['greaterMunicipality_id'] = ''
    result['greaterMunicipalityDistrict_name'] = ''
    result['greaterMunicipalityDistrict_id'] = ''

    country = Region.objects.filter(Name='Canada', modelType='country')[0]
    # u.Country_obj = country
    result['country_name'] = country.Name
    result['country_id'] = country.id
    # should not use verify=False but opennorth is giving ssl error
    r = requests.get(url, verify=False)
    data = json.loads(r.content)
    prntDebug(data)
    # responseData = {}
    try:
        prov = data['province']
        city = data['city']
        # u.city_name = city
        root = data['boundaries_centroid']
    except:
        root = data['objects']
    second_list = []
    try:
        for d in root:
            prntDebug('')
            # prntDebug(d)
            iden = d['external_id']
            name = d['name']
            type = d['boundary_set_name']
            prntDebug(type)
            if d['related']['boundary_set_url'] == '/boundary-sets/federal-electoral-districts/':
                prntDebug('riding,,,')
                try:
                    prntDebug('aa')
                    riding = District.objects.filter(Q(Name=name)&Q(Country_obj=country)&Q(modelType='riding'))[0]
                    # riding, ridingu, ridingData, riding_is_new = get_model_and_update('District', obj=riding)
                except Exception as e:
                    prntDebug(str(e))
                    riding = District(Name=name, Country_obj=country, Region_obj=country, AltName=name.replace('—', ''), gov_level='Federal', modelType='riding', nameType='Riding')
                    prntDebug('bb')
                    riding.save()
                    shareData.append(riding)
                    prntDebug('cc')
                
                    # riding, ridingu, ridingData, riding_is_new = get_model_and_update('District', Name=name, gov_level='Federal', AltName=name.replace('—', ''), modelType='riding', nameType='Riding', Country_obj=country, Region_obj=country)
    
                    # riding, ridingu, ridingData, riding_is_new, shareData = save_and_return(riding, ridingu, ridingData, riding_is_new, shareData, func)
                # if not riding.opennorthId:
                #     riding.opennorthId = iden
                #     riding.save()
                prntDebug(riding)
                # u.Federal_District_obj = riding
                # responseData['Federal_District_obj_id'] = riding.id
                prntDebug('done riding')
                result['federalDistrict_name'] = riding.Name
                result['federalDistrict_id'] = riding.id
                # u.riding_name = name
                # if not riding in items:
                #     items.append(riding)
            elif 'electoral district' in type and '2005' not in d['url'] and 'Federal' not in type:
                # prntDebug(type)
                provState_name = type.replace(' electoral district', '')
                prntDebug(provState_name)
                try:
                    provState = Region.objects.filter(Name=provState_name, ParentRegion_obj=country, nameType='Province', modelType='provState')[0]
                except:
                    provState = Region(Name=provState_name, ParentRegion_obj=country, nameType='Province', modelType='provState')
                    provState.save()
                    shareData.append(provState)

                # provState, provStateU, provStateData, provState_is_new = get_model_and_update('Region', Name=provState_name, ParentRegion_obj=country, nameType='Province', modelType='provState')

            
                # u.ProvState_obj = provState
                # responseData['ProvState_obj_id'] = provState.id
                # u.province_name = province_name
                result['provState_id'] = provState.id
                result['provState_name'] = provState.Name
                if not provState.AbbrName:
                    provState.AbbrName = prov
                    # provStateU['AbbrName'] = prov
                    provState.save()
                # provState, provStateU, provStateData, provState_is_new, shareData = save_and_return(provState, provStateU, provStateData, provState_is_new, shareData, func)
                
                try:
                    district = District.objects.filter(Name=name, Region_obj=provState, gov_level='Provincial', modelType='district', nameType='District')[0]
                except:
                    district = District(Name=name, Country_obj=country, Region_obj=provState, gov_level='Provincial', modelType='district', nameType='District')
                    district.save()
                    shareData.append(district)

                # district, districtU, districtData, district_is_new = get_model_and_update('District', Name=name, Country_obj=country, Region_obj=provState, gov_level='Provincial', modelType='district', nameType='District')

                # district, districtU, districtData, district_is_new, shareData = save_and_return(district, districtU, districtData, district_is_new, shareData, func)
            
                # if not district.opennorthId:
                #     district.province = province
                #     district.province_name = province_name
                #     district.opennorthId = iden
                #     district.save()
                # u.ProvState_District_obj = district
                # responseData['ProvState_District_obj_id'] = district.id
                # u.district_name = name
                result['provStateDistrict_name'] = district.Name
                result['provStateDistrict_id'] = district.id
                # if not district in items:
                #     items.append(district)
            elif 'ward' in type:
                second_list.append(d)
            elif 'School' in type:
                second_list.append(d)
        for m in second_list:
            iden = m['external_id']
            name = m['name']
            type = m['boundary_set_name']
            if 'ward' in type:
                # prntDebug('WARD')
                mun_name = type.replace(' ward', '')
                try:
                    municipality = Region.objects.filter(Name=mun_name, nameType='Municipality', modelType='municipality')[0]
                    # municipality, municipalityU, municipalityData, municipality_is_new = get_model_and_update('Region', obj=municipality)
                except:
                    municipality = Region(Name=mun_name, ParentRegion_obj=provState, nameType='Municipality', modelType='municipality')
                    municipality.save()
                    shareData.append(municipality)

                    # ParentRegion_obj may be changed below
                    # municipality, municipalityU, municipalityData, municipality_is_new = get_model_and_update('Region', Name=mun_name, ParentRegion_obj=provState, nameType='Municipality', modelType='municipality')

                # municipality, municipalityU, municipalityData, municipality_is_new, shareData = save_and_return(municipality, municipalityU, municipalityData, municipality_is_new, shareData, func)
            
                # if not district.o
                # try:
                #     municipality = District.objects.filter(Name=mun_name, Region=city, Type='Municipality')[0]
                # except:
                #     municipality = District(Name=mun_name, Region=city, Type='Municipality')
                #     municipality.save()
                # u.Municipality_obj = municipality
                # responseData['Municipality_obj_id'] = municipality.id
                # u.municipality_name = mun_name
                result['municipality_name'] = municipality.Name
                result['municipality_id'] = municipality.id
                # prntDebug(municipality)
                try:
                    ward = District.objects.filter(Name=name, Country_obj=country, Region_obj=municipality, gov_level='Municipal', modelType='ward', nameType='Ward')[0]
                except:
                    ward = District(Name=name, Country_obj=country, Region_obj=municipality, gov_level='Municipal', modelType='ward', nameType='Ward')
                    ward.save()
                    shareData.append(ward)

                # ward, wardU, wardData, ward_is_new = get_model_and_update('District', Name=name, Country_obj=country, Region_obj=municipality, gov_level='Municipal', modelType='ward', nameType='Ward')

                # ward, wardU, wardData, ward_is_new, shareData = save_and_return(ward, wardU, wardData, ward_is_new, shareData, func)
            
                # if not district.o
                # if not ward in items:
                #     items.append(ward)
                # u.Municipal_District_obj = ward
                # responseData['Municipal_District_obj_id'] = ward.id
                # u.ward_name = name
                result['ward_name'] = ward.Name
                result['ward_id'] = ward.id
            elif 'School' in type:
                # prntDebug('school')
                pass
    except Exception as e:
        prntDebug(str(e))
        pass
            # prntDebug('PASS')
            # prntDebug(type)
            # board_name = type.replace(' boundry', '')
            # prntDebug(board_name)
            # try:
            #     schoolBoard = SchoolBoard.objects.filter(name=board_name)[0]
            # except:
            #     schoolBoard = SchoolBoard(name=board_name, province=province, province_name=province_name)
            #     schoolBoard.save()
            # try:
            #     schoolRegion = SchoolBoardRegion.objects.filter(schoolBoard=schoolBoard, name=name)[0]
            # except:
            #     schoolRegion = SchoolBoardRegion(schoolBoard=schoolBoard, name=name, province=province, province_name=province_name)
            #     schoolRegion.save()
            # # if not schoolRegion in items:
            # #     items.append(schoolRegion)
            # # prntDebug(schoolRegion)
            # schoolRegion.schoolBoard_name = board_name
            # schoolRegion.save()
            # u.schoolBoardRegion = schoolRegion
            # u.schoolBoardRegion_name = name
    # u.save()
    try:
        prntDebug('-------------representatives')
        try:
            root = data['representatives_centroid']
        except:
            root = data['objects']
        region = None
        # if not province:
        #     province = u.ProvState
        for d in root:
            prntDebug('-----------')
            prntDebug('provstate',provState)
            url = d['url']
            last_name = d['last_name']
            first_name = d['first_name']
            name = d['name']
            # prntDebug(name)
            type = d['representative_set_name']
            personal_url = d['personal_url']
            elected_office = d['elected_office']
            gender = d['gender']
            district_name = d['district_name']
            email = ['email']
            for i in d['offices']:
                try:
                    postal = i['postal']
                except:
                    postal = None
                try:
                    fax = i['fax']
                except:
                    fax = None
                try:
                    tel = i['tel']
                except:
                    tel = None
            photo_url = d['photo_url']
            try:
                twitter = d['extra']['twitter']
            except:
                twitter = None
            party_name = d['party_name']
            if 'Assembly' in type:
                try:
                    role = Role.objects.filter(Position=elected_office, District_obj=district, Region_obj=provState, Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name)[0]
                    role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=role)
                except:
                    # try:
                    #     party = Party.objects.filter(Name=party_name, gov_level='Provincial', Region_obj=provState)[0]
                    # except:
                    #     prntDebug('create party')
                    #     party = Party(Name=party_name, gov_level='Provincial', Region_obj=provState)
                    #     party.save()
                    party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=party_name, gov_level='Provincial', Region_obj=provState)
                    party, partyU, partyData, party_is_new, shareData = save_and_return(party, partyU, partyData, party_is_new, shareData, func)
            
                    # try:
                    #     p = Person.objects.filter(Region_obj=provState, FirstName=first_name, LastName=last_name)[0]
                    # except:
                    #     prntDebug('create person')
                    #     p = Person(Region_obj=provState, FirstName=first_name, LastName=last_name, Gender=gender)
                    #     p.save()
                    person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=provState, FirstName=first_name, LastName=last_name)
                    if photo_url and not person.PhotoLink:
                        person.PhotoLink = photo_url
                        personData['PhotoLink'] = photo_url
                        # p.save()
                    person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
                    # r = Role(Position=elected_office, Person_obj=p, District_obj=district, Region_obj=provState, Party_obj=party, Current=True)
            
                    role, roleU, roleData, role_is_new = get_model_and_update('Role', Position=elected_office, Person_obj=p, District_obj=district, Region_obj=provState, Party_obj=party)
            
                roleData['Current'] = True
                role.Telephone = tel
                role.Fax = fax
                role.Address = postal
                role.Email = email
                role.PhotoLink = photo_url
                role.Website = personal_url
                
                roleData['Telephone'] = tel
                roleData['Fax'] = fax
                roleData['Address'] = postal
                roleData['Email'] = email
                roleData['PhotoLink'] = photo_url
                roleData['Website'] = personal_url
                if twitter:
                    role.XTwitter = twitter
                    roleData['XTwitter'] = twitter
                role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
                
                # r.save()
                # u.follow_person.add(r.Person)
            elif 'Commons' in type:
            
                try:
                    role = Role.objects.filter(Position='Member of Parliament', District_obj=riding, Region_obj=country, Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name)[0]
                    role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=role)
                except:
                    party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=party_name, gov_level='Federal', Region_obj=country)
                    party, partyU, partyData, party_is_new, shareData = save_and_return(party, partyU, partyData, party_is_new, shareData, func)
                    person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=country, FirstName=first_name, LastName=last_name)
                    if photo_url and not person.PhotoLink:
                        person.PhotoLink = photo_url
                        personData['PhotoLink'] = photo_url
                    person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
                    role, roleU, roleData, role_is_new = get_model_and_update('Role', Position='Member of Parliament', Person_obj=person, District_obj=riding, Region_obj=country, Party_obj=party)
            
                roleData['Current'] = True
                role.Telephone = tel
                role.Fax = fax
                role.Address = postal
                role.Email = email
                role.PhotoLink = photo_url
                role.Website = personal_url
                
                roleData['Telephone'] = tel
                roleData['Fax'] = fax
                roleData['Address'] = postal
                roleData['Email'] = email
                roleData['PhotoLink'] = photo_url
                roleData['Website'] = personal_url
                if twitter:
                    role.XTwitter = twitter
                    roleData['XTwitter'] = twitter
                role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
                


                # u.follow_person.add(r.Person)
            elif 'City Council' in type:
                if 'Ward' in district_name:
                    # prntDebug("WARD")
                    # try:
                    #     r = Role.objects.filter(Position=elected_office, District_obj=ward, Region_obj=municipality, Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name, Current=True)[0]
                    #     # r.ward_name = ward.name
                    #     # r.save()
                    # except:
                    #     try:
                    #         p = Person.objects.filter(FirstName=first_name, LastName=last_name, Region_obj=municipality)[0]
                    #     except:
                    #         prntDebug('create person')
                    #         p = Person(FirstName=first_name, LastName=last_name, Gender=gender, Region_obj=municipality)
                    #         p.save()
                    #     if photo_url and not p.AvatarLink:
                    #         p.AvatarLink = photo_url
                    #         p.save()
                    #     r = Role(Position=elected_office, Person_obj=p, District_obj=ward, Region_obj=municipality, Current=True)        
                    # # u.follow_person.add(r.person)try:
                    try:
                        role = Role.objects.filter(Position=elected_office, District_obj=ward, Region_obj=municipality, Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name)[0]
                        role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=role)
                    except:
                        # party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=party_name, gov_level='Federal', Region_obj=country)
                        # party, partyU, partyData, party_is_new, shareData = save_and_return(party, partyU, partyData, party_is_new, shareData, func)
                        person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=municipality, FirstName=first_name, LastName=last_name)
                        if photo_url and not person.PhotoLink:
                            person.PhotoLink = photo_url
                            personData['PhotoLink'] = photo_url
                        person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
                        role, roleU, roleData, role_is_new = get_model_and_update('Role', Position=elected_office, Person_obj=person, District_obj=ward, Region_obj=municipality)
                
                else:
                    # prntDebug('NOT WARD')
                    # try:
                    #     r = Role.objects.filter(Position=elected_office, Region_obj=municipality, Person_obj__last_name__icontains=last_name, Person_obj__first_name__icontains=first_name, Current=True)[0]
                    #     # r.municipality_name = municipality.name
                    #     # r.save()
                    # except:
                        # try:
                        #     p = Person.objects.filter(FirstName=first_name, LastName=last_name, Region_obj=municipality)[0]
                        # except:
                        #     prntDebug('create person')
                        #     p = Person(FirstName=first_name, LastName=last_name, Gender=gender, Region_obj=municipality)
                        #     p.save()
                        # if photo_url and not p.AvatarLink:
                        #     p.AvatarLink = photo_url
                        #     p.save()
                        # r = Role(Position=elected_office, Person_obj=p, Region_obj=municipality, Current=True)
                    try:
                        role = Role.objects.filter(Position=elected_office, Region_obj=municipality, Person_obj__last_name__icontains=last_name, Person_obj__first_name__icontains=first_name)[0]
                        role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=role)
                    except:
                        # party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=party_name, gov_level='Federal', Region_obj=country)
                        # party, partyU, partyData, party_is_new, shareData = save_and_return(party, partyU, partyData, party_is_new, shareData, func)
                        person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=municipality, FirstName=first_name, LastName=last_name)
                        if photo_url and not person.PhotoLink:
                            person.PhotoLink = photo_url
                            personData['PhotoLink'] = photo_url
                        person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
                        role, roleU, roleData, role_is_new = get_model_and_update('Role', Position=elected_office, Person_obj=person, Region_obj=municipality)
                
                # u.follow_person.add(r.person)
                roleData['Current'] = True
                role.Telephone = tel
                role.Fax = fax
                role.Address = postal
                role.Email = email
                role.PhotoLink = photo_url
                role.Website = personal_url
                
                roleData['Telephone'] = tel
                roleData['Fax'] = fax
                roleData['Address'] = postal
                roleData['Email'] = email
                roleData['PhotoLink'] = photo_url
                roleData['Website'] = personal_url
                if twitter:
                    role.XTwitter = twitter
                    roleData['XTwitter'] = twitter
                role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
                
            elif 'School Board' in type:
                pass
                # prntDebug('PASS')
                # # if not region:
                # #     try:
                # #         region = Municipality.objects.filter(name=district_name, province=province)[0]
                # #     except:
                # #         region = Municipality(name=district_name, province=province)
                # #         region.save()
                # try:
                #     r = Role.objects.filter(position=elected_office, schoolBoardRegion=schoolRegion, person__last_name__icontains=last_name, person__first_name__icontains=first_name, current=True)[0]
                # except:
                #     try:
                #         p = Person.objects.filter(first_name=first_name, last_name=last_name)[0]
                #     except:
                #         prntDebug('create person')
                #         p = Person(first_name=first_name, last_name=last_name, gender=gender)
                #         p.save()
                #     if photo_url and not p.logo:
                #         p.logo = photo_url
                #         p.save()
                #     r = Role(position=elected_office, person=p, schoolBoardRegion=schoolRegion, current=True)
                # r.telephone = tel
                # r.fax = fax
                # r.address = postal
                # r.email = email
                # r.logo = photo_url
                # r.website = personal_url
                # if twitter:
                #     r.twitter = twitter
                # r.save()
            elif 'Regional Council' in type:
                # pass
                # prntDebug('Regiaonal')
                # prntDebug(name)
                # prntDebug(type)
                # prntDebug(district_name)
                region_name = type.replace(' Regional Council', '')
                try:
                    greater_municipality = Region.objects.filter(Name=region_name, ParentRegion_obj=provState, modelType='regionalMunicipality', nameType='Regional Municipality')[0]
                    # prntDebug('found')
                except:
                    greater_municipality = Region(Name=region_name, ParentRegion_obj=provState, modelType='regionalMunicipality', nameType='Regional Municipality')
                    greater_municipality.save()
                    shareData.append(greater_municipality)

                    municipality.ParentRegion_obj = greater_municipality
                    municipality.save()
                    shareData.append(municipality)


                # greater_municipality, greater_municipalityU, greater_municipalityData, greater_municipality_is_new = get_model_and_update('Region', Name=region_name, ParentRegion_obj=provState, modelType='regionalMunicipality', nameType='Regional Municipality')
                # greater_municipality, greater_municipalityU, greater_municipalityData, greater_municipality_is_new, shareData = save_and_return(greater_municipality, greater_municipalityU, greater_municipalityData, greater_municipality_is_new, shareData, func)
            
                # if greater_municipality_is_new:
                #     municipality
                #     municipalityU
                # municipality, municipalityU, municipalityData, municipality_is_new, shareData = save_and_return(municipality, municipalityU, municipalityData, municipality_is_new, shareData, func)
            

                result['greaterMunicipality_name'] = greater_municipality.Name
                result['greaterMunicipality_id'] = greater_municipality.id
                try:
                    greater_municipality_district = District.objects.filter(Name=district_name, Region_obj=greater_municipality, gov_level='regionalMunicipality', modelType='regionalDistrict', nameType='Regional District')[0]
                except:
                    greater_municipality_district = District(Name=district_name, Country_obj=country, Region_obj=greater_municipality, gov_level='regionalMunicipality', modelType='regionalDistrict', nameType='Regional District')
                    greater_municipality_district.save()
                    shareData.append(greater_municipality_district)

                # u.Greater_Municipality_obj = upper_municipality
                if municipality.Name.lower() == district_name.lower():
                    # u.Greater_Municipal_District_obj = upper_municipality_district
                    result['greaterMunicipalityDistrict_name'] = greater_municipality_district.Name
                    result['greaterMunicipalityDistrict_id'] = greater_municipality_district.id



                try:
                    role = Role.objects.filter(Position=elected_office, District_obj=greater_municipality_district, Region_obj=greater_municipality, Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name)[0]
                    role, roleU, roleData, role_is_new = get_model_and_update('Role', obj=role)
                except:
                    # party, partyU, partyData, party_is_new = get_model_and_update('Party', Name=party_name, gov_level='Federal', Region_obj=country)
                    # party, partyU, partyData, party_is_new, shareData = save_and_return(party, partyU, partyData, party_is_new, shareData, func)
                    
                    try:
                        person = Person.objects.filter(FirstName=first_name, LastName=last_name).filter(Q(Region_obj=greater_municipality)|Q(Region_obj=municipality))[0]
                        person, personU, personData, person_is_new = get_model_and_update('Person', obj=person)

                    except:
                        # prntDebug('create person')
                        # p = Person(FirstName=first_name, LastName=last_name, Gender=gender, Region_obj=upper_municipality)
                        # p.save()
                        person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=greater_municipality, FirstName=first_name, LastName=last_name)
                    if photo_url and not person.PhotoLink:
                        person.PhotoLink = photo_url
                        personData['PhotoLink'] = photo_url
                    person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
                    role, roleU, roleData, role_is_new = get_model_and_update('Role', Position=elected_office, Person_obj=person, Region_obj=municipality)
                
                # u.follow_person.add(r.person)
                roleData['Current'] = True
                role.Telephone = tel
                role.Fax = fax
                role.Address = postal
                role.Email = email
                role.PhotoLink = photo_url
                role.Website = personal_url
                
                roleData['Telephone'] = tel
                roleData['Fax'] = fax
                roleData['Address'] = postal
                roleData['Email'] = email
                roleData['PhotoLink'] = photo_url
                roleData['Website'] = personal_url
                if twitter:
                    role.XTwitter = twitter
                    roleData['XTwitter'] = twitter
                role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
                

                # try:
                #     r = Role.objects.filter(Position=elected_office, District_obj=upper_municipality_district, Region_obj=upper_municipality, Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name, Current=True)[0]
                # except:
                #     try:
                #         p = Person.objects.filter(FirstName=first_name, LastName=last_name).filter(Q(Region_obj=upper_municipality)|Q(Region_obj=municipality))[0]
                #     except:
                #         prntDebug('create person')
                #         p = Person(FirstName=first_name, LastName=last_name, Gender=gender, Region_obj=upper_municipality)
                #         p.save()
                #     if photo_url and not p.AvatarLink:
                #         p.AvatarLink = photo_url
                #         p.save()
                #     r = Role(Position=elected_office, Person_obj=p, District_obj=upper_municipality_district, Region_obj=upper_municipality, Current=True)
                # r.Telephone = tel
                # r.Fax = fax
                # r.Address = postal
                # r.Email = email
                # r.LogoLink = photo_url
                # r.Website = personal_url
                # if twitter:
                #     r.XTwitter = twitter
                # r.save()
                # prntDebug(upper_municipality)
            # else:
            #     prntDebug('ELSE')
    except Exception as e:
        prntDebug(str(e))
        pass
    # u.save()
    # prntDebug(result)
    
    send_for_validation(shareData, None, func)
    return result





def add_bill(b, func, special=None, country=None, iden=None):
    prntDebug('----add bill')
    shareData = []
    dt_now = now_utc()
    today = dt_now - datetime.timedelta(hours=dt_now.hour, minutes=dt_now.minute, seconds=dt_now.second, microseconds=dt_now.microsecond)
    country = Region.objects.filter(modelType='country', Name='Canada').first()
    if not log:
        log = create_share_object(func, country, special=special, dt=now_utc(), iden=iden)

    ParliamentNumber = b.find('ParliamentNumber').text
    SessionNumber = b.find('SessionNumber').text
    # try:
    #     gov = Government.objects.filter(Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)[0]
    # except:
    #     gov = Government(Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    #     gov.save()
    #     gov.end_previous()
    
    gov, govU, govData, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    if gov_is_new:
        from blockchain.models import round_time
        gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
        gov.migrate_data()
        gov.LogoLinks = gov_logo_links
        gov, govU, gov_is_new, log = save_and_return(gov, govU, log)
        # shareData.append(gov.end_previous(func))
        # gov, govU, govData, gov_is_new, shareData = save_and_return(gov, govU, govData, gov_is_new, shareData, func)
    prntDebug(gov)
    gov_iden = b.find('Id').text
    
    # <Id>13088301</Id>
    # <NumberCode>C-424</NumberCode>
    # <NumberPrefix>C</NumberPrefix>
    # <Number>424</Number>
    originChamber = b.find('OriginatingChamberName').text
    # b.find('OriginatingChamberName').text.replace(' of Commons', '')
    if originChamber == 'House of Commons':
        originChamber = 'House'
    numCode = b.find('NumberCode').text
    # bill, billU, billData, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden, NumberCode=numCode)
    bill, billU, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, Chamber=originChamber, NumberCode=numCode, GovIden=gov_iden)

    prntDebug('got bill, bill_is_new:', bill_is_new)
    # time.sleep(10)
    # try:
    #     bill = Bill.objects.filter(Government_obj=gov, GovIden=gov_iden)[0]
    #     prntDebug('bill found')
    #     new_bill = False
    #     v = None
    # except:
    #     bill = Bill(Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden)
    #     bill.LegisLink = 'http://www.parl.ca/LegisInfo/en/bill/%s-%s/%s' %(b.find('ParliamentNumber').text, b.find('SessionNumber').text, b.find('NumberCode').text)
    #     r = requests.get(bill.LegisLink, verify=False)
    #     soup = BeautifulSoup(r.content, 'html.parser')
    #     # span = soup.find('span', {'class':'session-date-range'}).text
    #     # prntDebug(span)
    #     # a = span.find(', to ')
    #     # d = span[:a]
    #     # # prntDebug(d)
    #     # dt = datetime.datetime.strptime(d, '%B %d, %Y')
    #     # prntDebug(dt)
    #     # bill.started = dt
    #     bill.NumberCode = b.find('NumberCode').text
    #     prntDebug(bill.NumberCode)
    #     bill.save()
    #     bill.create_post()
    url = 'http://www.parl.ca/LegisInfo/en/bill/%s-%s/%s' %(b.find('ParliamentNumber').text, b.find('SessionNumber').text, b.find('NumberCode').text)
    if bill_is_new:

        bill.LegisLink = url
        bill.NumberPrefix = b.find('NumberPrefix').text
        bill.Number = b.find('Number').text
        versions = None
        def versionizer(version, completed_dt):
            try:
                completed_dt = timezonify('est', parse(completed_dt)).isoformat()
            except Exception as e:
                prnt('parse bill dt fail 2568', str(e))
            return {'version':version, 'current':None, 'status':None, 'started_dt':None, 'completed_dt':completed_dt}
        if originChamber == 'Senate':
            versions = [versionizer('Senate First Reading', b.find('PassedSenateFirstReadingDateTime').text), versionizer('Senate Second Reading', b.find('PassedSenateSecondReadingDateTime').text), versionizer('Senate Third Reading', b.find('PassedSenateThirdReadingDateTime').text), 
                        versionizer('House First Reading', b.find('PassedHouseFirstReadingDateTime').text), versionizer('House Second Reading', b.find('PassedHouseSecondReadingDateTime').text), versionizer('House Third Reading', b.find('PassedHouseThirdReadingDateTime').text), 
                        versionizer('Royal Assent', b.find('ReceivedRoyalAssentDateTime').text)]
            billU.data['Status'] = 'Senate First Reading'

        elif originChamber == 'House':
            versions = [versionizer('House First Reading', b.find('PassedHouseFirstReadingDateTime').text), versionizer('House Second Reading', b.find('PassedHouseSecondReadingDateTime').text), versionizer('House Third Reading', b.find('PassedHouseThirdReadingDateTime').text), 
                        versionizer('Senate First Reading', b.find('PassedSenateFirstReadingDateTime').text), versionizer('Senate Second Reading', b.find('PassedSenateSecondReadingDateTime').text), versionizer('Senate Third Reading', b.find('PassedSenateThirdReadingDateTime').text), 
                        versionizer('Royal Assent', b.find('ReceivedRoyalAssentDateTime').text)]
            billU.data['Status'] = 'House First Reading'
        if versions:
            billU.data['billVersions'] = versions
        # billU.data['Status'] = 'Introduced'
        prntDebug('bill created')
        # bill.NumberPrefix = b.find('NumberPrefix').text
        bill.Number = b.find('Number').text
        # bill.LongTitle = b.find('LongTitleEn').text
        # prntDebug(bill.LongTitle)
        # bill.LongTitleFr = b.find('LongTitleFr').text
        if re.search('[a-zA-Z]', b.find('ShortTitle').text):
            bill.ShortTitle = b.find('ShortTitle').text
        bill.Title = b.find('LongTitleEn').text
        bill.BillDocumentTypeName = b.find('BillDocumentTypeName').text
        bill.IsGovernmentBill = b.find('IsGovernmentBill').text
        # bill.chamber = b.find('OriginatingChamberName').text.replace(' of Commons', '')
        prntDebug(bill.chamber)
        if b.find('OriginatingChamberOrganizationId').text == '2':  #senate
            prntDebug('senate')
            person_govId = b.find('SponsorSenateSystemAffiliationId').text
        else:
            prntDebug('house')
            person_govId = b.find('SponsorPersonId').text
        person = Person.objects.filter(Region_obj=country, GovIden=person_govId).first()
        if not person:
            first_name = b.find('SponsorPersonOfficialFirstName').text
            last_name = b.find('SponsorPersonOfficialLastName').text
            full_name = f'{first_name} {last_name}'
            
            person, personU, person_is_new = get_model_and_update('Person', GovIden=person_govId, Country_obj=log.Region_obj, Region_obj=log.Region_obj)
            if person_is_new:
                personU.data['FirstName'] = first_name
                personU.data['LastName'] = last_name
                personU.data['FullName'] = full_name
                person, personU, person_is_new, log = save_and_return(person, personU, log)

        bill.Person_obj = person
        bill.SponsorPersonName = b.find('SponsorPersonName').text
        bill.SponsorCode = person_govId
        bill.save()

    err = 2
    billU.data['data_link'] = url

    if False:
        # bill.LegisLink = 
        # new_bill = True
        # # origin = b.find('OriginatingChamberName').text
        # versions = ['House First Reading', 'House Second Reading','House Third Reading', 'Senate First Reading', 'Senate Second Reading', 'Senate Third Reading', 'Royal Assent']
        # billData['billVersions'] = []
        # for version in versions:
        #     billData['billVersions'].append({'version':version, 'current':False, 'started_dt':None, 'completed_dt':None})
            
            # try:
            #     v = BillVersion.objects.filter(Bill_obj=bill, version=version)[0]
            # except:
            #     v = BillVersion(Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, Bill_obj=bill, version=version, NumberCode=bill.NumberCode)
            #     if origin == 'Senate':
            #         if version == 'Senate First Reading':
            #             v.empty = False
            #             v.Current = True
            #         else:
            #             v.empty = True
            #     else:
            #         if version == 'House First Reading':
            #             v.empty = False
            #             v.Current = True
            #         else:
            #             v.empty = True
            #     v.save()
            #     v.create_post()
        # if origin == 'Senate':
        #     try:
        #         v = BillVersion.objects.filter(bill=bill, version='Senate First Reading')[0]
        #     except:
        #         v = BillVersion(bill=bill, version='Senate First Reading', code=bill.NumberCode)
        #         v.save()
        #         v.create_post()
        # else:
        #     try:
        #         v = BillVersion.objects.filter(bill=bill, version='House First Reading')[0]
        #     except:
        #         v = BillVersion(bill=bill, version='House First Reading', code=bill.NumberCode)
        #         v.save()
        #         v.create_post()
        # v.current = True
        # v.empty = False
        # # v.save()
        # prntDebug('bill created')
        # # bill.NumberPrefix = b.find('NumberPrefix').text
        # bill.Number = b.find('Number').text
        # # bill.LongTitle = b.find('LongTitleEn').text
        # # prntDebug(bill.LongTitle)
        # # bill.LongTitleFr = b.find('LongTitleFr').text
        # if re.search('[a-zA-Z]', b.find('ShortTitle').text):
        #     bill.ShortTitle = b.find('ShortTitle').text
        # bill.Title = b.find('LongTitleEn').text
        # # bill.StatusId = b.find('StatusId').text
        # if billData['Status'] != b.find('StatusNameEn').text:
        #     updatedStatus = True
        # else:
        #     updatedStatus = False
        # billData['Status'] = b.find('StatusNameEn').text
        # # bill.StatusNameFr = b.find('StatusNameFr').text
        # # bill.LatestCompletedMajorStageId = b.find('LatestCompletedMajorStageId').text
        # # billData['LatestCompletedMajorStageName'] = b.find('LatestCompletedMajorStageName').text
        # billData['LatestCompletedBillStageNameWithChamberSuffix'] = b.find('LatestCompletedMajorStageNameWithChamberSuffix').text
        # # billData['LatestCompletedMajorStageChamberName'] = b.find('LatestCompletedMajorStageChamberName').text
        # # bill.OngoingStageId = b.find('OngoingStageId').text
        # billData['OngoingStageName'] = b.find('OngoingStageNameEn').text
        # # bill.LatestCompletedBillStageId = b.find('LatestCompletedBillStageId').text
        # billData['LatestCompletedBillStageName'] = b.find('LatestCompletedBillStageName').text
        # billData['LatestCompletedBillStageChamberName'] = b.find('LatestCompletedBillStageChamberName').text
        # billData['LatestCompletedBillStageDateTime'] = datetime.datetime.fromisoformat(b.find('LatestCompletedBillStageDateTime').text)
        # # try:
        #     date_time = datetime.datetime.strptime(b.find('LatestCompletedBillStageDateTime').text[:b.find('LatestCompletedBillStageDateTime').text.find('.')], '%Y-%m-%dT%H:%M:%S')
        #     if '-04:00' in b.find('LatestCompletedBillStageDateTime').text:
        #         date_time = date_time.replace(tzinfo=pytz.UTC)
        #     bill.LatestCompletedBillStageDateTime = date_time
        # except Exception as e:
        #     prntDebug(str(e))
        # try: 
        #     bill.parliament = Parliament.objects.filter(country='Canada', organization='Federal', ParliamentNumber= bill.ParliamentNumber, SessionNumber=bill.SessionNumber)[0]
        # except:
        #     parl = Parliament(country='Canada', organization='Federal', ParliamentNumber= bill.ParliamentNumber, SessionNumber=bill.SessionNumber, start_date=datetime.datetime.now())
        #     parl.save()
        #     parl.end_previous('Canada', 'Federal')
        # #     bill.parliament = parl
        # bill.BillDocumentTypeName = b.find('BillDocumentTypeName').text
        # bill.IsGovernmentBill = b.find('IsGovernmentBill').text
        # # bill.chamber = b.find('OriginatingChamberName').text.replace(' of Commons', '')
        # prntDebug(bill.chamber)
        # bill.IsSenateBill = b.find('IsSenateBill').text
        # bill.IsHouseBill = b.find('IsHouseBill').text
        # bill.SponsorSenateSystemAffiliationId = b.find('SponsorPersonId').text
        # bill.SponsorPersonId = b.find('SponsorPersonId').text
        # bill.SponsorPersonOfficialFirstName = b.find('SponsorPersonOfficialFirstName').text
        # bill.SponsorPersonOfficialLastName = b.find('SponsorPersonOfficialLastName').text
        # bill.SponsorPersonName = b.find('SponsorPersonName').text
        # bill.SponsorPersonShortHonorific = b.find('SponsorPersonShortHonorific').text
        # bill.SponsorAffiliationTitle = b.find('SponsorAffiliationTitle').text
        # bill.SponsorAffiliationRoleName = b.find('SponsorAffiliationRoleName').text
        # bill.SponsorConstituencyName = b.find('SponsorConstituencyName').text
        # prntDebug(bill.SponsorPersonId)
        # prntDebug(bill.SponsorSenateSystemAffiliationId)
        # prntDebug(bill.SponsorPersonOfficialFirstName)
        # prntDebug(bill.SponsorPersonOfficialLastName)
        # prntDebug(bill.SponsorAffiliationTitle)
        #     try:

                
        # <SponsorSenateSystemAffiliationId>235254</SponsorSenateSystemAffiliationId>
        # <SponsorPersonId>120079</SponsorPersonId>
        # <SponsorPersonOfficialFirstName>Pierre</SponsorPersonOfficialFirstName>
        # <SponsorPersonOfficialLastName>Moreau</SponsorPersonOfficialLastName>


        
        # <SponsorSenateSystemAffiliationId />
        # <SponsorPersonId>98079</SponsorPersonId>
        # <SponsorPersonOfficialFirstName>Dane</SponsorPersonOfficialFirstName>
        # <SponsorPersonOfficialLastName>Lloyd</SponsorPersonOfficialLastName>

        #     if b.find('OriginatingChamberOrganizationId').text == '2':  #senate
        #         prntDebug('senate')
        #         person_govId = b.find('SponsorSenateSystemAffiliationId').text
        #         # bill, billU, billData, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden, NumberCode=numCode)

        #         # role = Role.objects.filter(Position=b.find('SponsorAffiliationTitle').text, Region_obj=country, Person_obj__FirstName__icontains=b.find('SponsorPersonOfficialFirstName').text, Person_obj__LastName=b.find('SponsorPersonOfficialLastName').text)[0]
        #         # # prntDebug(r)
        #         # bill.Person_obj = role.Person_obj
        #         # # bill, billU, billData, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden, NumberCode=numCode)

        #     else:
        #         prntDebug('house')
        #         person_govId = b.find('SponsorPersonId').text
        #         # person = Person.objects.filter(Region_obj=country, gov_iden=b.find('SponsorPersonId').text)[0]
        #         # bill.Person_obj = person
        #     # except:
        #     # try:
        #     #     p = Person.objects.filter(FirstName=b.find('SponsorPersonOfficialFirstName').text, LastName=b.find('SponsorPersonOfficialLastName').text)[0]
        #     # except:
        #     #     p = Person(FirstName=b.find('SponsorPersonOfficialFirstName').text, LastName=b.find('SponsorPersonOfficialLastName').text)
        #     #     # p.Region_obj = 
        #     #     p.save()
        #     #     # p.create_post()
        #     person = Person.objects.filter(Region_obj=country, GovIden=person_govId).first()
        #     if not person:

        # # <SponsorPersonOfficialFirstName>Dane</SponsorPersonOfficialFirstName>
        # # <SponsorPersonOfficialLastName>Lloyd</SponsorPersonOfficialLastName>
        #         first_name = b.find('SponsorPersonOfficialFirstName').text
        #         last_name = b.find('SponsorPersonOfficialLastName').text
        #         full_name = f'{first_name} {last_name}'
                
        #         # personUpdate = Update.objects.filter(Region_obj=country, id__startswith=get_model_prefix('Person'), data__contains={'FullName': full_name}).first()
        #         # if personUpdate:
        #         #     person, personU, person_is_new = get_model_and_update('Person', id=personUpdate.pointerId, Country_obj=country, Region_obj=country)
        #         # else:
        #         person, personU, person_is_new = get_model_and_update('Person', GovIden=person_govId, Country_obj=log.Region_obj, Region_obj=log.Region_obj)
        #         if person_is_new:
        #             personU.data['FirstName'] = first_name
        #             personU.data['LastName'] = last_name
        #             personU.data['FullName'] = full_name
        #             person.GovIden = person_govId
        #             # must save person before profile info can be assigned
        #             person, personU, person_is_new, log = save_and_return(person, personU, log)

                    
        #         # person, personU, person_is_new = get_model_and_update('Person', id=personUpdate.pointerId, Country_obj=country, Region_obj=country)

        #         # person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=country, Government_obj=gov, Country_obj=country, GovIden=person_govId, FirstName=b.find('SponsorPersonOfficialFirstName').text, LastName=b.find('SponsorPersonOfficialLastName').text)
        #         # person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)
        #     # if person_is_new:
        #     #     shareData.append(save_obj_and_update(person, personU, personData, person_is_new))
        #     #     person, personU, personData, person_is_new = get_model_and_update('Person', Region_obj=country, Government_obj=gov, Country_obj=country, FirstName=b.find('SponsorPersonOfficialFirstName').text, LastName=b.find('SponsorPersonOfficialLastName').text)
            
        #     # role, roleU, roleData, role_is_new = get_model_and_update('Role', Region_obj=country, Government_obj=gov, Country_obj=country, Position=b.find('SponsorAffiliationTitle').text, Person_obj=person)

        #     # role, roleU, roleData, role_is_new, shareData = save_and_return(role, roleU, roleData, role_is_new, shareData, func)
        #     # shareData.append(save_obj_and_update(role, roleU, roleData, role_is_new))
        #     # try:
        #     #     r = Role.objects.filter(Position=b.find('SponsorAffiliationTitle').text, Person_obj=p)[0]
        #     # except:
        #     #     r = Role(Position=b.find('SponsorAffiliationTitle').text, Person_obj=p)
        #     #     # r.Region_obj =
        #     #     r.save()
        #     bill.Person_obj = person
        #     bill.SponsorPersonName = b.find('SponsorPersonName').text
        #     bill.SponsorCode = person_govId
            
            # if b.find('OriginatingChamberOrganizationId').text == '2':  #senate
            #     prntDebug('senate')
            #     person, personU, personData, person_is_new = get_model_and_update('Person', Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden, NumberCode=numCode)
            
            # else:
            #     prntDebug('house')
        ...
    
    prntDebug('0000')
    if 'Status' not in billU.data or billU.data['Status'] != b.find('StatusNameEn').text:
        updatedStatus = True
    else:
        updatedStatus = False
    date_time = None
    if b.find('LatestBillEventDateTime').text:
        prntDebug('002')
        # billData['LatestBillEventDateTime'] = b.find('LatestBillEventDateTime').text[:b.find('LatestBillEventDateTime').text.find('.')]
        # date_time = datetime.datetime.fromisoformat(billData['LatestBillEventDateTime'])
        # # bill.LatestBillEventTypeName = b.find('LatestBillEventTypeName').text
        

        date_time = datetime.datetime.strptime(b.find('LatestBillEventDateTime').text[:b.find('LatestBillEventDateTime').text.find('.')], '%Y-%m-%dT%H:%M:%S')
        # billData['LatestBillEventDateTime'] = date_time
        date_time = timezonify('est', date_time)
        billU.data['LatestBillEventDateTime'] = date_time.isoformat()
        billU.DateTime = date_time
        # if bill_is_new:
        #     bill.DateTime = date_time
        # # prntDebug(date_time)
        # if '-04:00' in b.find('LatestBillEventDateTime').text:
        #     date_time = date_time.replace(tzinfo=pytz.UTC)
        #     if date_time > bill.LatestBillEventDateTime:
        #         bill.LatestBillEventDateTime = date_time
        # else:
        #     bill.LatestBillEventDateTime = date_time
        #         # bill.LatestBillEventDateTime = b.find('LatestBillEventDateTime').text
        prntDebug('Latest Time: %s' %(billU.data['LatestBillEventDateTime']))
    prntDebug('001')


    stage_dts = {'House First Reading':b.find('PassedHouseFirstReadingDateTime').text,
    'House Second Reading':b.find('PassedHouseSecondReadingDateTime').text,
    'House Third Reading':b.find('PassedHouseThirdReadingDateTime').text,
    'Senate First Reading':b.find('PassedSenateFirstReadingDateTime').text,
    'Senate Second Reading':b.find('PassedSenateSecondReadingDateTime').text,
    'Senate Third Reading':b.find('PassedSenateThirdReadingDateTime').text,
    'Royal Assent':b.find('ReceivedRoyalAssentDateTime').text,
    }


    if updatedStatus:
        prntDebug('a')
        billU.data['Status'] = b.find('StatusNameEn').text
        prntDebug('b')
        # bill.StatusNameFr = b.find('StatusNameFr').text
        # bill.LatestCompletedMajorStageId = b.find('LatestCompletedMajorStageId').text
        # billData['LatestCompletedMajorStageName'] = b.find('LatestCompletedMajorStageName').text
        billU.data['LatestCompletedBillStageNameWithChamberSuffix'] = b.find('LatestCompletedMajorStageNameWithChamberSuffix').text
        # billData['LatestCompletedMajorStageChamberName'] = b.find('LatestCompletedMajorStageChamberName').text
        # bill.OngoingStageId = b.find('OngoingStageId').text
        # billU.data['OngoingStageName'] = b.find('OngoingStageNameEn').text
        # bill.LatestCompletedBillStageId = b.find('LatestCompletedBillStageId').text
        billU.data['LatestCompletedBillStageName'] = b.find('LatestCompletedBillStageName').text
        billU.data['LatestCompletedBillStageChamberName'] = b.find('LatestCompletedBillStageChamberName').text
        billU.data['LatestCompletedBillStageDateTime'] = b.find('LatestCompletedBillStageDateTime').text

        billU.data['LatestBillEventChamberName'] = b.find('LatestBillEventChamberName').text
        billU.data['LatestBillEventNumberOfAmendments'] = b.find('LatestBillEventNumberOfAmendments').text
        # bill.LatestBillEventMeetingNumber = b.find('LatestBillEventMeetingNumber').text
        # bill.LatestBillEventAdditionalInformationEn = b.find('LatestBillEventAdditionalInformationEn').text
        # bill.LatestBillEventAdditionalInformationFr = b.find('LatestBillEventAdditionalInformationFr').text
        if not date_time:
            date_time = datetime.datetime.strptime(b.find('LatestCompletedBillStageDateTime').text[:b.find('LatestCompletedBillStageDateTime').text.find('.')], '%Y-%m-%dT%H:%M:%S')
            date_time = timezonify('est', date_time)
            billU.data['LatestBillEventDateTime'] = date_time.isoformat()
            billU.DateTime = date_time

        prev_stage = b.find('LatestCompletedBillStageName').text
        current_stage = b.find('OngoingStageNameEn').text
        for v in billU.data['billVersions']:
            prnt(v['version'])
            exists = False
            if not v['completed_dt'] and v['version'] in stage_dts and stage_dts[v['version']]:
                try:
                    v['completed_dt'] = timezonify('est', parse(stage_dts[v['version']])).isoformat()
                except Exception as e:
                    prnt('parse bill dt fail 8632', str(e))
            if v['version'] == current_stage:
                exists = True
                v['current'] = True
                v['status'] = 'Current'
                if not v['started_dt']:
                    v['started_dt'] = date_time.isoformat()
            elif v['current'] == True or v['version'] == prev_stage:
                v['current'] = False
                v['status'] = 'Passed'
                if not v['completed_dt']:
                    prev_dt = datetime.datetime.strptime(b.find('LatestCompletedBillStageDateTime').text[:b.find('LatestCompletedBillStageDateTime').text.find('.')], '%Y-%m-%dT%H:%M:%S')
                    prev_dt = timezonify('est', prev_dt)
                    v['completed_dt'] = prev_dt.isoformat()

        if not exists:
            prnt('not exists')
            inserted = False
            versionHistory = billU.data['billVersions']
            billU.data['billVersions'] = []
            for v in versionHistory:
                if v['status'] == 'Passed':
                    billU.data['billVersions'].append(v)
                else:
                    if not inserted:
                        billU.data['billVersions'].append({'version':current_stage, 'current':True, 'status':'Current', 'started_dt':date_time.isoformat(), 'completed_dt':None})
                        inserted = True
                    billU.data['billVersions'].append(v)



        # if 'billVersions' in billU.data:
        # statuses = {'introduced':'Introduced', 'received in the house':'in house', 'passed/agreed to in house':'Passed House', 'received in the senate':'in senate',
        #             'passed/agreed to in senate':'Passed Senate', 'resolving differences':'Resolving Differences', 'presented to president':'To President', 'vetoed by president':'Vetoed by President',
        #             'passed house over veto':'pass house veto', 'passed senate over veto':'pass senate veto', 'the objections of the president to the contrary notwithstanding failed':'Failed to pass over veto', 'became public law':'Became Law'
        #             }
        # prnt('actions in reverse')
        # for i in list(reversed(actions.findall('item'))):
        #     prnt()
        #     # prnt(i)
        #     # prnt()
        #     txt = i.find('text')
        #     try:
        #         prnt(f'text: {txt.text}')
        #         # prnt(f'type: {type.text}')
        #     except Exception as e:
        #         prnt(str(e))
        #     actionDate = i.find('actionDate')
        #     actionTime = i.find('actionTime')
        #     if actionTime is not None:
        #         dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}-{actionTime.text}', '%Y-%m-%d-%H:%M:%S'))
        #     else:
        #         dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}', '%Y-%m-%d'))
        #     prnt(dt)
        #     if txt is not None:
        #         prnt('txt',txt.text)
        #         passed_house_veto = False
        #         passed_senate_veto = False
        #         for key, value in statuses.items():
        #             if key in txt.text.lower():
        #                 prnt('FOUND',key)
        #                 if value == 'in house':
        #                     if bill.Chamber == 'House':
        #                         value = 'Introduced'
        #                     elif bill.Chamber == 'Senate':
        #                         value = 'Passed Senate'
        #                 elif value == 'in senate':
        #                     if bill.Chamber == 'Senate':
        #                         value = 'Introduced'
        #                     elif bill.Chamber == 'House':
        #                         value = 'Passed House'
        #                 elif value == 'pass house veto':
        #                     passed_house_veto = True
        #                     value = None
        #                     if passed_senate_veto:
        #                         value = 'Passed over veto'
        #                 elif value == 'pass senate veto':
        #                     passed_senate_veto = True
        #                     value = None
        #                     if passed_house_veto:
        #                         value = 'Passed over veto'
        #                 if value:
        #                     prnt('val',value)
        #                     exists = False
        #                     for v in billU.data['billVersions']:
        #                         prnt(v['version'])
        #                         if v['version'] == value:
        #                             exists = True
        #                             v['current'] = True
        #                             v['status'] = 'Current'
        #                             v['started_dt'] = dt.isoformat()
        #                         elif v['current'] == True:
        #                             v['current'] = False
        #                             v['status'] = 'Passed'
        #                             v['completed_dt'] = dt.isoformat()
        #                     if not exists:
        #                         prnt('not exists')
        #                         inserted = False
        #                         versionHistory = billU.data['billVersions']
        #                         billU.data['billVersions'] = []
        #                         for v in versionHistory:
        #                             if v['status'] == 'Passed':
        #                                 billU.data['billVersions'].append(v)
        #                             else:
        #                                 if not inserted:
        #                                     billU.data['billVersions'].append({'version':value, 'current':True, 'status':'Current', 'started_dt':dt.isoformat(), 'completed_dt':None})
        #                                     inserted = True
        #                                 billU.data['billVersions'].append(v)


remove 'added' from convert_to_dict
remove chrome for testing on lois
reboot everything
???
profit

            
    


    prntDebug('111')
    def convert_reading_time(item):
        prntDebug('convert')
        try:
            prntDebug(b.find(item).text)
            return datetime.datetime.fromisoformat(b.find(item).text).astimezone(pytz.utc) 
        except:
            return None
        # if '.' in b.find(item).text:
        #     date_time = datetime.datetime.strptime(b.find(item).text[:b.find(item).text.find('.')], '%Y-%m-%dT%H:%M:%S')
        #     if '-04:00' in b.find(item).text or '-05:00' in b.find(item).text:
        #         date_time = date_time.replace(tzinfo=pytz.UTC)
        # else:
        #     try:
        #         date_time = datetime.datetime.strptime(b.find(item).text, '%Y-%m-%dT%H:%M:%S%z')
        #     except:
        #         date_time = datetime.datetime.strptime(b.find(item).text, '%Y-%m-%dT%H:%M:%S')
        # return date_time
    # if not bill_is_new:
    # prntDebug('bill is new')
    # prntDebug(b.find('PassedHouseFirstReadingDateTime').text)
    # prntDebug(convert_reading_time('PassedHouseFirstReadingDateTime'))
    # prntDebug('else11', date_time, today)
    # if b.find('PassedHouseFirstReadingDateTime').text and convert_reading_time('PassedHouseFirstReadingDateTime') < today:
    #     prntDebug('if', convert_reading_time('PassedHouseFirstReadingDateTime'), date_time)
    #     if convert_reading_time('PassedHouseFirstReadingDateTime') < date_time:
    #         billU.data['LatestBillEventDateTime'] = b.find('PassedHouseFirstReadingDateTime').text
    #     else:
    #         billU.data['LatestBillEventDateTime'] = datetime.datetime.isoformat(date_time)
    # else:
    #     # if date_time < today:
    #     billU.data['LatestBillEventDateTime'] = datetime.datetime.isoformat(date_time)
    #     # else:
    #     #     billData['LatestBillEventDateTime'] = datetime.datetime.isoformat(today)
    #     # v.save()
    #     # bill.PassedSenateFirstReadingDateTime = date_time
    
    prntDebug('------------SVE BILLL---------')
    bill, billU, billData, bill_is_new, shareData = save_and_return(bill, billU, billData, bill_is_new, shareData, func)
    # prntDebug(bill)
    prntDebug('done save bill')
    # prntDebug('112')
    def currentize_version(billData, version, dt, shareData):
        dt = datetime.datetime.fromisoformat(dt)
        prntDebug('currentize_version:', version)
        for v in billData['billVersions']:
            if v['version'] == version:
                v['status'] = 'Current'
                v['current'] = True
                v['started_dt'] = today.isoformat()
                billV, billVU, billVData, billV_is_new = get_model_and_update('BillVersion', Bill_obj=bill, Version=version, NumberCode=numCode, Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin)
                # prntDebug('bv1')
                # prntDebug('func', func)
                # prntDebug('shared', shareData)
                if not billV.DateTime:
                    billV.DateTime = dt
                billV, billVU, billVData, billV_is_new, shareData = save_and_return(billV, billVU, billVData, billV_is_new, shareData, func)
                # prntDebug('bv2')
            elif 'status' in v and v['status'] == 'current':
                v['status'] = 'Passed'
                v['current'] = False
                v['completed_dt'] = today.isoformat()
        return billData, shareData
        
        # vs = BillVersion.objects.filter(bill=bill)
        # for v in vs:
        #     if v.version == version:
        #         # prntDebug(version)
        #         v.current = True
        #         v.empty = False
        #         v.dateTime = bill.LatestBillEventDateTime
        #     else:
        #         v.current = False
        #     v.save()
        # try:
        #     v = BillVersion.objects.filter(bill=bill, version=version)[0]  
        # except:
        #     v = BillVersion(bill=bill, version=version, code=bill.NumberCode)
        #     v.save()
        # v.create_post()
        # v.current = True
        # v.empty = False
        # billData['DateTime'] = bill.LatestBillEventDateTime
        # v.save()
    prntDebug('222')
    # if b.find('PassedHouseFirstReadingDateTime').text and not 'PassedFirstChamberFirstReadingDateTime' in billU.data:
    #     # prntDebug('222a')
    #     billU.data['PassedFirstChamberFirstReadingDateTime'] = b.find('PassedHouseFirstReadingDateTime').text
    #     # prntDebug('222b')
    #     billData, shareData = currentize_version(billData, 'House Second Reading', billU.data['PassedFirstChamberFirstReadingDateTime'], shareData)
    # if b.find('PassedHouseSecondReadingDateTime').text and not 'PassedFirstChamberSecondReadingDateTime' in billU.data:
    #     billU.data['PassedFirstChamberSecondReadingDateTime'] = b.find('PassedHouseSecondReadingDateTime').text
    #     billData, shareData = currentize_version(billData, 'House Third Reading', billU.data['PassedFirstChamberSecondReadingDateTime'], shareData)
    # if b.find('PassedHouseThirdReadingDateTime').text and not 'PassedFirstChamberThirdReadingDateTime' in billU.data:
    #     billU.data['PassedFirstChamberThirdReadingDateTime'] = b.find('PassedHouseThirdReadingDateTime').text
    #     if not 'PassedSecondChamberFirstReadingDateTime' in billU.data:
    #         billData, shareData = currentize_version(billData, 'Senate First Reading', billU.data['PassedFirstChamberThirdReadingDateTime'], shareData)
    #     else:
    #         for v in billU.data['billVersions']:
    #             if v['version'] == 'House Third Reading':
    #                 v['status'] = 'Passed'
    #                 v['completed_dt'] = today.isoformat()
    #                 break
    #         # try:
    #         #     v = BillVersion.objects.filter(bill=bill, version='House Third Reading')[0]
    #         # except:
    #         #     v = BillVersion(bill=bill, version='House Third Reading', code=bill.NumberCode)
    #         #     v.save()
    #         #     v.create_post()
    #         # v.dateTime = bill.LatestBillEventDateTime
    #         # v.current = False
    #         # v.save()
    # if b.find('PassedSenateFirstReadingDateTime').text and not 'PassedSenateFirstReadingDateTime' in billData:
    #     billData['PassedSecondChamberFirstReadingDateTime'] = b.find('PassedSenateFirstReadingDateTime').text
    #     billData, shareData = currentize_version(billData, 'Senate Second Reading', billData['PassedSecondChamberFirstReadingDateTime'], shareData)
    # if b.find('PassedSenateSecondReadingDateTime').text and not 'PassedSenateSecondReadingDateTime' in billData:
    #     billData['PassedSecondChamberSecondReadingDateTime'] = b.find('PassedSenateSecondReadingDateTime').text
    #     billData, shareData = currentize_version(billData, 'Senate Third Reading', billData['PassedSecondChamberSecondReadingDateTime'], shareData)
    # if b.find('PassedSenateThirdReadingDateTime').text:
    #     prntDebug(b.find('PassedSenateThirdReadingDateTime').text)
    #     billData['PassedSecondChamberThirdReadingDateTime'] = b.find('PassedSenateThirdReadingDateTime').text
    #     if not 'PassedFirstChamberFirstReadingDateTime' in billData:
    #         billData, shareData = currentize_version(billData, 'House First Reading', billData['PassedSecondChamberThirdReadingDateTime'], shareData)
    #     else:
    #         for v in billData['billVersions']:
    #             if v['version'] == 'Senate Third Reading':
    #                 v['status'] = 'Passed'
    #                 v['completed_dt'] = today.isoformat()
    #                 break
    #         # try:
    #         #     v = BillVersion.objects.filter(bill=bill, version='Senate Third Reading')[0]
    #         # except:
    #         #     v = BillVersion(bill=bill, version='Senate Third Reading', code=bill.NumberCode)
    #         #     v.save()
    #         #     v.create_post()
    #         # v.dateTime = bill.LatestBillEventDateTime
    #         # v.current = False
    #         # v.save()
    # if b.find('ReceivedRoyalAssentDateTime').text:
    #     billU.data['ReceivedRoyalAssentDateTime'] = b.find('ReceivedRoyalAssentDateTime').text
    #     billData, shareData = currentize_version(billData, 'Royal Assent', billData['ReceivedRoyalAssentDateTime'], shareData)
    prntDebug('3333')
    # billU.data['PassedFirstChamberFirstReading'] = b.find('PassedFirstChamberFirstReading').text
    # billU.data['PassedFirstChamberSecondReading'] = b.find('PassedFirstChamberSecondReading').text
    # billData['PassedFirstChamberThirdReading'] = b.find('PassedFirstChamberThirdReading').text
    # billData['PassedSecondChamberFirstReading'] = b.find('PassedSecondChamberFirstReading').text
    # billData['PassedSecondChamberSecondReading'] = b.find('PassedSecondChamberSecondReading').text
    # billData['PassedSecondChamberThirdReading'] = b.find('PassedSecondChamberThirdReading').text
    # billData['ReceivedRoyalAssent'] = b.find('ReceivedRoyalAssent').text
    # billData['BillFormName'] = b.find('BillFormName').text
    # billData['Notes'] = b.find('Notes').text
    # billData['IsSessionOngoing'] = b.find('IsSessionOngoing').text
    # bill.save()
    # get_text = False
    def get_text(billU, reading):
        prntDebug('getting text...', reading)
        # 'https://www.parl.ca/DocumentViewer/en/44-1/bill/C-294/first-reading'
        url = 'https://www.parl.ca/DocumentViewer/en/%s-%s/bill/%s/%s' %(gov.GovernmentNumber, gov.SessionNumber, bill.NumberCode, reading)
        prntDebug(url)
        r = requests.get(url, verify=False)
        prntDebug('link received')
        soup = BeautifulSoup(r.content, 'html.parser')
        prntDebug()
        # prntDebug(soup)
        # prntDebug()
        try:
            import hashlib
            def section_code(text, length=7):
                # return as 7 char unique string
                hash_object = hashlib.sha256(text.encode())
                hash_int = int(hash_object.hexdigest(), 16)
                return str(hash_int % 10**7).zfill(length)
            
            def case_insensitive_search(tag):
                # prntDebug('case_insensitive_search')
                # prntDebug(str(tag)[:500])
                # prntDebug()
                # if 'summary' in str(tag).lower():
                #     prntDebug('found')
                #     time.sleep(3)
                # else:
                #     prntDebug('not found')
                return tag.name == 'h2' and re.search('summary', tag.string, re.IGNORECASE)
            prntDebug('1')
            try:
                sum = soup.find(case_insensitive_search)
                prntDebug('2')
            except:
                sum = soup.find("h2", string="SUMMARY")
            prntDebug('2a')
            par = sum.parent
            text = str(par).replace(str(sum), '')
            prntDebug('3')
            def alter_rem(text, num, increase): #increase text size
                try:
                    match_list = []
                    for i in re.finditer('font-size:', str(text)):
                        match_list.insert(0,i)
                    for match in match_list:
                        q = str(text)[match.end():].find(';')
                        size = str(text)[match.end():match.end()+q]
                        if 'rem' in size:
                            x = size.replace('rem', '')
                            x = float(x)
                            if increase == 1:
                                newX = 1
                            else:
                                newX = x * increase
                            text = str(text)[:match.end()] + str(newX) + 'rem' + str(text)[match.end()+q:]
                        num += 1
                    return text
                except Exception as e:
                    # prntDebug(str(e))
                    return text
            text = alter_rem(text, 0, 1)
            text = text.replace('font-size:1rem;', '')
            text = text.replace('RECOMMENDATION', ' ')
            prntDebug('4')
            if not billU.extra:
                billU.extra = {}
            # billV.Summary = text
            # prntDebug('summ:', billV.Summary[:100])
            publication = soup.find('div', {'class':'publication-container-content'})
            sidebar = soup.find('div', {'class':'publication-container-explorer'})
            toc = soup.find('div', {'id':'TableofContent'})
            script = publication.find('script')
            final = str(publication).replace(str(sidebar), '').replace(str(toc), '').replace(str(script), '')
            # prntDebug('get text')
            # if bill.NumberCode != 'C-86' or bill.ParliamentNumber != '42' or bill.SessionNumber != '1':
            finalText = alter_rem(final, 0, 1.30)
            # else:
            #     prntDebug('skip processing')
            prntDebug('next')
            toc_d = []
            for match in re.finditer('<h2', str(finalText)):
                q = str(finalText)[match.end():].find('>')
                # prntDebug(text[match.end():match.end()+q])
                w = str(finalText)[match.end():match.end()+q]

                e = str(finalText)[match.end()+q:].find('</h2>')
                full_section = str(finalText)[match.end()+q+1:match.end()+q+e]

                html = str(finalText)[match.start():match.end()+q]
                string =  re.sub('<[^<]+?>', '', r)

                # toc_d[string] = html

                code = section_code(full_section)
                # tag_start = str(finalText)[match.end():]
                q = str(finalText)[match.end():].find('>')
                tag_full = str(finalText)[match.end():match.end()+q]
                if 'id=' not in tag_full:
                    replaced_tag = str(finalText)[:match.end()] + f' id="{code}" ' + str(finalText)[match.end():]
                    finalText = finalText.replace(tag_full, replaced_tag)
                    toc_d.append({string : {'code':code, 'html':replaced_tag}})
                else:
                    toc_d.append({string : {'code':code, 'html':tag_full}})

            billText = BillText.objects.filter(pointerId=billU.pointerId, data__TextHtml=str(finalText)).first()
            if not billText:
                billText = BillText(pointerId=billU.pointerId)
                billText.data['TextHtml'] = str(finalText)
                billText.data['TextNav'] = toc_d
                billText.data['url'] = url

            # billV.TextHtml = str(final)
            # prntDebug('str', str(final)[:100])
            # billV.TextNav = json.dumps(dict(toc_d))
            prntDebug('done')
            time.sleep(5)
            return billU, billText
        except Exception as e:
            prntDebug(str(e))
            time.sleep(10)
            prntDebug('old document type')
            a = soup.find("a", string="Complete Document")['href']
            section_list = []
            sections = soup.find_all('a', {'class':'DefaultTableOfContentsSectionLink'})
            sum_link = None
            for s in sections:
                if 'Summary' in s.text:
                    sum_link = s['href']
                section_list.append(s.text)
            sections = soup.find_all('a', {'class':'DefaultTableOfContentsFile Link'})
            for s in sections:
                section_list.append(s.text)
            prntDebug(section_list)
            # prntDebug('')
            def alter_pt(text, num):
                try:
                    match_list = []
                    for i in re.finditer('font-size:', str(text)):
                        match_list.insert(0,i)
                    for match in match_list:
                        # if n == num:
                        q = str(text)[match.end():].find(';')
                        size = str(text)[match.end():match.end()+q]
                        if 'pt' in size:
                            n = size.replace('pt', '')
                            n = float(n)
                            text = str(text)[:match.end()] + ';' + str(text)[match.end()+q:]
                        num += 1
                    return text
                except Exception as e:
                    # prntDebug(str(e))
                    return text
            def alter_line_height(text, num):
                try:
                    match_list = []
                    for i in re.finditer('font-size:', str(text)):
                        match_list.insert(0,i)
                    for match in match_list:
                        q = str(text)[match.end():].find(';')
                        size = str(text)[match.end():match.end()+q]
                        if 'pt' in size:
                            n = size.replace('pt', '')
                            n = float(n)
                            text = str(text)[:match.end()] + ';' + str(text)[match.end()+q:]
                        num += 1
                    return text
                except Exception as e:
                    # prntDebug(str(e))
                    return text
            if sum_link:
                try:
                    r = requests.get('https://www.parl.ca' + sum_link, verify=False)
                    soup = BeautifulSoup(r.content, 'html.parser')
                    sum = soup.find("div", string="SUMMARY")
                    par = sum.parent
                    html = str(par).replace(str(sum), '')
                    html = alter_pt(html, 0)
                    html = alter_line_height(html, 0)
                    bill.summary = html
                except:
                    pass
            r = requests.get('https://www.parl.ca' + a, verify=False)
            prntDebug('link received')
            soup = BeautifulSoup(r.content, 'html.parser')
            final = soup.find('div', {'class':'publication-container-content'})
            # centers = soup.find_all('div', attrs={'text-align':'Center'})
            centers = soup.find_all('div',style=lambda value: value and 'text-align:Center' in value)
            # prntDebug(centers)
            toc_d = {}
            for c in centers:
                if c.text in section_list:
                    html = str(c).replace('\\"', "'")
                    # html = html.replace('="', "='").replace('">', "'>")
                    
                    toc_d[c.text] = str(c)
            time.sleep(5)
            return str(final), toc_d
    
    # try:
    #     billVersion = BillVersion.objects.filter(Bill_obj=bill, version=version)
    # except:
    #     pass
    # if bill_is_new:
    #     pass

    # prntDebug('get lastest version')
    # for v in billData['billVersions']:
    #     prntDebug(v)
    #     if 'status' in v and v['status'] == 'Current':
    #         version = v['version']
    #         break
    # time.sleep(10)

    prntDebug('------------SVE BILLL---------')
    # bill, billU, billData, bill_is_new, /shareData = save_and_return(bill, billU, billData, bill_is_new, shareData, func)
    # prntDebug(bill)
    bill, billU, bill_is_new, log = save_and_return(bill, billU, log)
    prntDebug('done save bill')
    # prntDebug('get bill version', version)
    # billV, billVU, billVData, billV_is_new = get_model_and_update('BillVersion', Bill_obj=bill, Version=version, NumberCode=numCode, Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin)

    # C-86 / 42-1 is a giant bill that crashes the system when processing
    # if bill.NumberCode != 'C-86' or bill.ParliamentNumber != '42' or bill.SessionNumber != '1':
        # if not bill.first_reading_html:
    
    if not billV.TextHtml:
        prntDebug('billv is new')
        billV.DateTime = date_time
        if 'LatestCompletedBillStageName' in billU.data and 'Second' in billU.data['LatestCompletedBillStageName']:
        # if bill.bill_text_version != 'Second':
            try:
                billU, billText = get_text(billU, 'second-reading')
                if billText: 
                    do_save = False
                    if billText.id == '0' or not billText.signature:
                        do_save = True
                    if dt is not None:
                        if 'date' not in billText.data or billText.data['date'] != dt.isoformat():
                            # prnt('isdt',dt)
                            billText.data['date'] = dt.isoformat()
                            do_save = True
                    if actionType is not None:
                        if 'bill_text_version' not in billText.data or billText.data['bill_text_version'] != actionType.text:
                            billText.data['bill_text_version'] = actionType.text
                            do_save = True
                    if do_save:
                        billText.save(region=country)
                        log.updateShare(billText)
                    textFound = True
                    billU.data['billText_obj'] = billText.id 
            except Exception as e:
                prntDebug('get bill text fail 353',str(e))
    # if b.find('PassedFirstChamberThirdReading').text == 'true':
        elif 'LatestCompletedBillStageName' in billU.data and 'Third' in billU.data['LatestCompletedBillStageName']:
        # if bill.bill_text_version != 'Third':
            try:
                billV = get_text(billU, 'third-reading')
                # final, toc_d = get_text('third-reading')
                # bill.bill_text_html = str(final)
                # bill.bill_text_nav = json.dumps(dict(toc_d))
                # bill.bill_text_version = 'Third'
            except Exception as e:
                prntDebug('get bill text fail 3453',str(e))
        elif 'LatestCompletedBillStageName' in billU.data and 'Royal Assent' in billU.data['LatestCompletedBillStageName']:
        # if bill.bill_text_version != 'Royal':
            try:
                billV = get_text(billU, 'royal-assent')
                # final, toc_d = get_text('royal-assent')
                # bill.bill_text_html = str(final)
                # bill.bill_text_nav = json.dumps(dict(toc_d))
                # bill.bill_text_version = 'Royal'
            except Exception as e:
                prntDebug('get bill text fail 2345',str(e))
        else:
            try:
                billV = get_text(billU, 'first-reading')
                # billV.TextHtml = str(final)
                # billV.TextNav = json.dumps(dict(toc_d))
                # bill.bill_text_version = 'First'
            except Exception as e:
                prntDebug('get bill text fail 5343',str(e))
        billData['Summary'] = billV.Summary
    prntDebug('444')
    body = str(bill.Title)
    if bill_is_new and bill.Person_obj:
        # prntDebug('send alerts')
        notification, notificationU, notificationData, notification_is_new = get_model_and_update('Notification', title=f'{bill.Person_obj.FullName} has sponsored bill {bill.NumberCode}', link=str(bill.get_absolute_url()), targetUsers={'follow_person' : bill.Person_obj.id}, pointerId=bill.id, pointerType=bill.object_type, Country_obj=country, Region_obj=country, chamber=origin)
        notification, notificationU, notificationData, notification_is_new, shareData = save_and_return(notification, notificationU, notificationData, notification_is_new, shareData, func)


        # n = Notification(title='%s has sponsored bill %s' %(bill.Person_obj.FullName, bill.NumberCode), link=str(bill.get_absolute_url()))
        # # n.save()
        # for u in User.objects.filter(follow_Person_objs=bill.Person_obj):
        #     u.alert('%s has sponsored bill %s' %(bill.Person_obj.FullName, bill.NumberCode), str(bill.get_absolute_url()), body)
    # if new_bill:
    #     bill.getSpren(False)
    # if bill.ReceivedRoyalAssentDateTime:
    #     if not bill.royal_assent_html:
    #         try:
    #             final, toc_d = get_text('royal-assent')
    #             bill.royal_assent_html = str(final)
    #             bill.royal_assent_nav = json.dumps(dict(toc_d))
    #         except Exception as e:
    #             prntDebug(str(e))
    #             # u = User.objects.filter(username='Sozed')[0]
    #             # title = 'royal alert fail %s' %(bill.NumberCode)
    #             # u.alert(title, str(bill.get_absolute_url()), str(e))
        



    # prntDebug('saving bill')
    # shareData.append(save_obj_and_update(bill, billU, billData, bill_is_new))
    # prntDebug('bill saved')
    # if bill_is_new:
    #     bill, billU, billData, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin, GovIden=gov_iden, NumberCode=numCode)
    #     billV.Bill_obj = bill
    prntDebug('save billv')
    # shareData.append(save_obj_and_update(billV, billVU, billVData, billV_is_new))
    billV, billVU, billVData, billV_is_new, shareData = save_and_return(billV, billVU, billVData, billV_is_new, shareData, func)

    # prntDebug('version', version)
    billVersions = get_dynamic_model('BillVersion', list=True, Bill_obj=bill)
    for bV in billVersions:
        # prntDebug()
        # prntDebug(bV)
        billV, billVU, billVData, billV_is_new = get_model_and_update('BillVersion', obj=bV)
        # prntDebug(billVData)
        if version == billV.Version:
            billVData['status'] = 'Current'
        elif 'status' in billVData and billVData['status'] == 'Current':
            billVData['status'] = 'Passed'
        billV, billVU, billVData, billV_is_new, shareData = save_and_return(billV, billVU, billVData, billV_is_new, shareData, func)
    # prntDebug('done versions')
    # bill, billU, billData, bill_is_new, shareData = save_and_return(bill, billU, billData, bill_is_new, shareData, func)
    # # prntDebug(bill)
    # prntDebug('get bill version', version)
    # billV, billVU, billVData, billV_is_new = get_model_and_update('BillVersion', Bill_obj=bill, Version=version, NumberCode=numCode, Government_obj=gov, Country_obj=country, Region_obj=country, chamber=origin)

    
    if updatedStatus:
        if billData['Status'] != 'Royal assent received':
            if User.objects.filter(follow_Bill_objs=bill).count() > 0:
            #     for u in User.objects.filter(follow_Bill_objs=bill):
            #         title = 'Bill %s updated' %(bill.NumberCode)
            #         u.alert(title, str(bill.get_absolute_url()), body + '\n' + billData['Status'], obj=bill, share=False)
                notification, notificationU, notificationData, notification_is_new = get_model_and_update('Notification', title=f'Bill {bill.NumberCode} updated - {body}', link=str(bill.get_absolute_url()), targetUsers={'follow_bill' : bill.id}, pointerId=bill.id, pointerType=bill.object_type, Country_obj=country, Region_obj=country, chamber=origin)
                notification, notificationU, notificationData, notification_is_new, shareData = save_and_return(notification, notificationU, notificationData, notification_is_new, shareData, func)
        elif 'Royal assent received' in billData['Status']:
            # n = Notification(title=f'Bill {bill.NumberCode} has reached Royal Assent - {body}', link=str(bill.get_absolute_url()), pointerType=bill.object_type, pointerId=bill.id)
            # n.save(share=False)
            # for u in User.objects.all():
            #     title = 'Bill %s has reached Royal Assent' %(bill.NumberCode)
            #     u.alert(title, str(bill.get_absolute_url()), body, obj=bill, share=False)
            notification, notificationU, notificationData, notification_is_new = get_model_and_update('Notification', title=f'Bill {bill.NumberCode} has reached Royal Assent - {body}', link=str(bill.get_absolute_url()), targetUsers={'all_in_country' : country.id}, pointerId=bill.id, pointerType=bill.object_type, Country_obj=country, Region_obj=country, chamber=origin)
            notification, notificationU, notificationData, notification_is_new, shareData = save_and_return(notification, notificationU, notificationData, notification_is_new, shareData, func)
    
    return shareData, gov
    
# dont use
def get_house_votes(m):
    prntDebug('-----get house votes')
    url = 'https://www.ourcommons.ca/members/en/votes/%s/%s/%s' %(m.ParliamentNumber, m.SessionNumber, m.vote_number)
    m.gov_url = url
    prntDebug(url)
    r = requests.get(url, verify=False)
    soup = BeautifulSoup(r.content, 'html.parser')
    title = soup.find('div', {'class':'mip-vote-title-section'})
    # prntDebug(title)
    p = title.find('p')
    sita = p.text.find('No. ')+len('No. ')
    sitb = p.text[sita:].find(' - ')
    sitting = p.text[sita:sita+sitb]
    m.sitting = int(sitting)
    date = p.text[sita+sitb+len(' - '):]
    date_time = datetime.datetime.strptime(date, '%A, %B %d, %Y')
    m.date_time = date_time
    block = soup.find('div', {'class':'ce-mip-vote-block'})
    h = block.find('h2').text
    bill_code = h.replace('Bill ', '')
    try:
        bill = Bill.objects.get(ParliamentNumber=m.ParliamentNumber, SessionNumber=m.SessionNumber, NumberCode=bill_code)
    except:
        bill_url = 'https://www.parl.ca/LegisInfo/en/bill/%s-%s/%s/xml' %(m.ParliamentNumber, m.SessionNumber, bill_code)
        r = requests.get(bill_url, verify=False)
        root = ET.fromstring(r.content)
        bill_data = root.find('Bill')
        get_bill(bill_data)
        gov_iden = bill_data.find('Id').text
        bill = Bill.objects.get(gov_iden=gov_iden)
    m.bill_id = bill.id
    a = soup.find('a', {'class':'ce-mip-mp-tile'})
    b = a['href'].find('(')+1
    c = a['href'][b:].find(')')
    sponsor_link = a['href'][b:b+c]
    try:
        s = Person.objects.filter(gov_profile_page__icontains=sponsor_link)[0]
        m.sponsor = s
    except Exception as e:
        prntDebug(str(e))
    desc = soup.find('div', {'id':'mip-vote-desc'})
    m.subject = desc.text
    text = soup.find('div', {'id':'mip-vote-text-collapsible-text'})
    m.motion_text = text.text
    # m.save()
    sum = soup.find('div', {'class':'mip-vote-summary-section'})
    row = sum.find('div', {'class':'row'})
    divs = row.find_all('div')
    for d in divs:
        # prntDebug(d)
        if 'Results' in d.text:
            m.result = d.text.replace('Results: ', '')
        elif 'Yea:' in d.text:
            m.yeas = int(d.text.replace('Yea: ', ''))
        elif 'Nay:' in d.text:
            m.nays = int(d.text.replace('Nay: ', ''))
        elif 'Paired:' in d.text:
            m.pairs = int(d.text.replace('Paired: ', ''))
        elif 'Total:' in d.text:
            m.total_votes = int(d.text.replace('Total: ', ''))
    m.save()
    xml = url + '/xml'
    prntDebug(xml)
    tries = 0
    root = None
    while tries < 3 and root == None:
        try:
            tries += 1
            r = requests.get(xml, verify=False)
            root = ET.fromstring(r.content)
        except Exception as e:
            prntDebug(str(e))
            time.sleep(4)
    voters = root.findall('VoteParticipant')
    for v in voters:
        ParliamentNumber = v.find('ParliamentNumber').text
        SessionNumber = v.find('SessionNumber').text
        DecisionEventDateTime = v.find('DecisionEventDateTime').text
        '2022-10-26T17:50:00'
        date_time = datetime.datetime.strptime(DecisionEventDateTime, '%Y-%m-%dT%H:%M:%S')
        DecisionDivisionNumber = v.find('DecisionDivisionNumber').text
        PersonShortSalutation = v.find('PersonShortSalutation').text
        ConstituencyName = v.find('ConstituencyName').text
        VoteValueName = v.find('VoteValueName').text
        PersonOfficialFirstName = v.find('PersonOfficialFirstName').text
        PersonOfficialLastName = v.find('PersonOfficialLastName').text
        ConstituencyProvinceTerritoryName = v.find('ConstituencyProvinceTerritoryName').text
        CaucusShortName = v.find('CaucusShortName').text
        IsVoteYea = v.find('IsVoteYea').text
        IsVoteNay = v.find('IsVoteNay').text
        IsVotePaired = v.find('IsVotePaired').text
        DecisionResultName = v.find('DecisionResultName').text
        PersonId = v.find('PersonId').text
        prntDebug(PersonOfficialLastName, ',', PersonOfficialFirstName)
        try:
            v = Vote.objects.filter(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, motion_id=m.id, PersonId=PersonId)[0]
        except:
            v = Vote()
            v.ParliamentNumber = ParliamentNumber
            v.SessionNumber = SessionNumber
            v.motion_id = m.id
            v.bill_id = bill.id
            v.PersonId = PersonId
            try:
                p = Person.objects.filter(gov_iden=PersonId)[0]
                v.person_id = p.id
            except Exception as e:
                prntDebug(str(e))
        v.DecisionEventDateTime = date_time
        v.DecisionDivisionNumber = DecisionDivisionNumber
        v.PersonShortSalutation = PersonShortSalutation
        v.ConstituencyName = ConstituencyName
        v.VoteValueName = VoteValueName
        v.PersonOfficialFirstName = PersonOfficialFirstName
        v.PersonOfficialLastName = PersonOfficialLastName
        v.ConstituencyProvinceTerritoryName = ConstituencyProvinceTerritoryName
        v.CaucusShortName = CaucusShortName
        v.IsVoteYea = IsVoteYea
        v.IsVoteNay = IsVoteNay
        v.IsVotePaired = IsVotePaired
        v.DecisionResultName = DecisionResultName
        v.save()

def get_live_house_votes(m):
    pass

def get_recent_bills(special=None, dt=now_utc(), func=None, iden=None):
    prntDebug('---------------------bills')
    country = Region.objects.filter(modelType='country', Name='Canada').first()
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country).first()

    shareData = []
    url = 'https://www.parl.ca/LegisInfo/en/overview/xml/recentlyintroduced'
    r = requests.get(url, verify=False)
    root = ET.fromstring(r.content)
    bills = root.findall('Bill')
    for b in bills:
        ShortTitle = b.find('ShortTitle').text
        prntDebug(ShortTitle)
        try:
            data, gov = get_bill(b, func)
            for d in data:
                shareData.append(d)
            # break
        except Exception as e:
            prntDebug(str(e))
        # break
    # share_all_with_network(shareData)
    return shareData, gov
    

#dont use
def get_house_votes():
    url = 'https://www.ourcommons.ca/members/en/votes'
    r = requests.get(url, verify=False)
    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', {'id':'global-votes'})
    tbody = table.find('tbody')
    trs = tbody.find_all('tr')
    count = 0
    for tr in trs:
        count += 1
        a = tr.find('a')
        link = 'https://www.ourcommons.ca' + a['href']
        'https://www.ourcommons.ca/members/en/votes/44/1/2'
        b =  link.find('votes/')+len('votes/')
        c = link[b:].find('/')
        parliament = link[b:b+c]
        d = link[b+c+1:].find('/')
        session = link[b+c+1:b+c+1+d]
        vote_number = a.text.replace('No. ', '')
        try:
            m = Motion.objects.filter(gov_url=link, vote_number=vote_number)[0]
        except:
            m = Motion()
            m.gov_url = link
            m.ParliamentNumber = parliament
            m.SessionNumber = session
            m.vote_number = vote_number
            m.is_official = True
            m.save()
            m.create_post()
            get_house_votes(m)
        if count > 3:
            break
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()


def get_bills(special=None, dt=now_utc(), iden=None, period='recent'):
    prntDebug('get bills', period)
    func = 'get_bills'
    shareData = []
    country = Region.objects.filter(modelType='country', Name='Canada').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    if not special:
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')



    
    driver = None
    if target_links:
        if not target_dt:
            target_dt = dt
        updates = Update.objects.filter(pointerId__startswith=get_model_prefix('Bill'), Region_obj=country, data__data_link__in=target_links, created__gte=target_dt)
        for u in updates:
            if u.data['data_link'] in target_links:
                if u.validated or u.created > now_utc() - datetime.timedelta(minutes=60):
                    target_links.remove(u.data['data_link'])

        for link in target_links:
            if link:
                log, driver = add_bill(url=link, log=log, update_dt=target_dt, driver=driver, country=country, ref_func=func)
                if link != target_links[-1]:
                    time.sleep(2)



                    
            # xml = 'https://www.parl.ca/LegisInfo/en/bill/%s-%s/%s/xml' %(parl, sess, code)
            prntDebug(xml)
            if billU == None or billData['Status'] != b.find('StatusNameEn').text or 'LatestBillEventDateTime' not in billData or billData['LatestBillEventDateTime'] == None:
            # if period == 'alltime' and bill == None or period != 'alltime':
                time.sleep(2)
                # prntDebug(xml)
                r2 = requests.get(xml, verify=False)
                root2 = ET.fromstring(r2.content)
                bills2 = root2.findall('Bill')
                for bill in bills2:
                    try:
                        data, gov = get_bill(bill, func)
                        for d in data:
                            shareData.append(d)
                    except Exception as e:
                        prntDebug(str(e))


    else:
        if period == 'alltime':
            url = 'https://www.parl.ca/LegisInfo/en/bills/xml?parlsession=all'
        elif period == 'recent':
            url = 'https://www.parl.ca/LegisInfo/en/overview/xml/recentlyintroduced'
        else:
            prntDebug('get session bills')
            # this parliment or this session, not sure yet
            url = 'https://www.parl.ca/LegisInfo/en/bills/xml'

        r = requests.get(url, verify=False)
        root = ET.fromstring(r.content)
        bills = root.findall('Bill')


        links = []
        for b in bills[:100]:
            # prntDebug(b.find('StatusNameEn').text)
            ShortTitle = b.find('LongTitleEn').text
            # prntDebug(ShortTitle)
            code = b.find('NumberCode').text
            parl = b.find('ParliamentNumber').text
            sess = b.find('SessionNumber').text
            xml = 'https://www.parl.ca/LegisInfo/en/bill/%s-%s/%s/xml' %(parl, sess, code)


            # for a in ass:
            if xml:
                links.append(xml)

        updates = Update.objects.filter(pointerId__startswith=get_model_prefix('Bill'), Region_obj=country, data__data_link__in=links, created__gte=pub_dt)
        for u in updates:
            if u.data['data_link'] in links:
                if u.validated or u.created > now_utc() - datetime.timedelta(minutes=60):
                    links.remove(u.data['data_link'])


            # while i >= 0:
            #     item = item_list[i]
            #     i -= 1
            #     # prnt('i',i)
            #     pubDate = item.find('pubDate')
            #     pub_dt = datetime.datetime.strptime(pubDate.text, "%a, %d %b %Y %H:%M:%S %z")
        while len(links) > 0:
            # if len(links) > 200:
            target_links = links[:50]

            queue = django_rq.get_queue('low')
            queue.enqueue(get_bills, dt=dt, target_links=target_links, target_dt=pub_dt, job_timeout=runTimes[func], result_ttl=3600)
            if len(links) > 50:
                links = links[50:]
            else:
                links = []



        for b in bills[:20]:
            # prntDebug(b.find('StatusNameEn').text)
            ShortTitle = b.find('LongTitleEn').text
            # prntDebug(ShortTitle)
            code = b.find('NumberCode').text
            parl = b.find('ParliamentNumber').text
            sess = b.find('SessionNumber').text
            
            gov, govU, govData, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=parl, SessionNumber=sess, Region_obj=country)
            if gov_is_new:
                shareData.append(gov.end_previous(func))
                gov, govU, govData, gov_is_new, shareData = save_and_return(gov, govU, govData, gov_is_new, shareData, func)
            prntDebug(gov)
            try:
                date_time = datetime.datetime.fromisoformat(b.find('LatestCompletedBillStageDateTime').text).replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
                # date_time = datetime.datetime.strptime(b.find('LatestCompletedBillStageDateTime').text[:b.find('LatestCompletedBillStageDateTime').text.find('.')], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
                # if '-04:00' in b.find('LatestCompletedBillStageDateTime').text:
                #     bill_date_time = date_time.replace(tzinfo=pytz.UTC)
                # bill.LatestCompletedBillStageDateTime = date_time
            except Exception as e:
                prntDebug(str(e))
                bill_date_time = None
            prntDebug(code, parl, sess)
            try:
                billU = Update.objects.filter(Bill_obj__NumberCode=code, Government_obj=gov, Country_obj=country, Region_obj=country)[0]
                billData = json.loads(billU.data)
            except:
                billU = None
                billData = None
            xml = 'https://www.parl.ca/LegisInfo/en/bill/%s-%s/%s/xml' %(parl, sess, code)
            prntDebug(xml)
            if billU == None or billData['Status'] != b.find('StatusNameEn').text or 'LatestBillEventDateTime' not in billData or billData['LatestBillEventDateTime'] == None:
            # if period == 'alltime' and bill == None or period != 'alltime':
                time.sleep(2)
                # prntDebug(xml)
                r2 = requests.get(xml, verify=False)
                root2 = ET.fromstring(r2.content)
                bills2 = root2.findall('Bill')
                for bill in bills2:
                    try:
                        data, gov = get_bill(bill, func)
                        for d in data:
                            shareData.append(d)
                    except Exception as e:
                        prntDebug(str(e))
        prntDebug('done')
        send_for_validation(shareData, gov, func)

def get_federal_candidates(num):
    prntDebug('get federal candidates', num)
    url = 'https://lop.parl.ca/sites/ParlInfo/default/en_CA/ElectionsRidings/Elections'
    try:
        prntDebug("opening browser")
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_experimental_option( "prefs",{'profile.managed_default_content_settings.javascript': 2})
        # chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        caps = DesiredCapabilities().CHROME
        # caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
        caps["pageLoadStrategy"] = "eager"   # Do not wait for full page load
        driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    except Exception as e:
        prntDebug(str(e))
    prntDebug('getting link')
    driver.get(url)
    # prntDebug('link retreived')
    toFillList = []
    timeout = 30
    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="gridContainer"]/div/div[6]/div/div/div[1]/div/table/tbody/tr[1]/td[2]'))
    WebDriverWait(driver, timeout).until(element_present)
    # num = 1
    xpath = '//*[@id="gridContainer"]/div/div[6]/div/div/div[1]/div/table/tbody/tr'
    one = xpath + '[%s]' %(num)
    tr = driver.find_element(By.XPATH, one)
    parliamentNum = tr.text.replace('Parliament: ', '')
    prntDebug('parliament', parliamentNum)
    td = tr.find_element(By.CLASS_NAME, "dx-datagrid-group-closed")
    td.click()
    prntDebug('clicked')
    time.sleep(1)
    num += 1
    two = xpath + '[%s]' %(num)
    tr = driver.find_element(By.XPATH, two)
    title = tr.text.replace('Type of Election: ', '')
    td = tr.find_element(By.CLASS_NAME, "dx-datagrid-group-closed")
    td.click()
    prntDebug('clicked')
    time.sleep(1)
    num += 1
    three = xpath + '[%s]' %(num)
    tr = driver.find_element(By.XPATH, three)
    try:
        date = tr.text.replace('Date of Election: ', '').replace(' Profile', '')
        date_time = datetime.datetime.strptime(date, '%Y-%m-%d')
    except:
        date_time = None
    try:
        e = Election.objects.filter(level='Federal', type=title, end_date=date_time)[0]
    except:
        e = Election(level='Federal', type=title, end_date=date_time)
        e.save()
    e.Parliament = int(parliamentNum)
    td = tr.find_element(By.CLASS_NAME, "dx-datagrid-group-closed")
    td.click()
    prntDebug('clicked')
    time.sleep(2)
    def get_list(driver):
        data = driver.find_elements(By.CLASS_NAME, "dx-data-row")
        for d in data:
            # time.sleep(1)
            tds = d.find_elements(By.CSS_SELECTOR, "td")
            for t in tds:
                if t.get_attribute('aria-colindex') == '4':
                    try:
                        img = t.find_element(By.CSS_SELECTOR, "img").get_attribute('src')
                    except:
                        img = None
                elif t.get_attribute('aria-colindex') == '5':
                    province = t.text
                elif t.get_attribute('aria-colindex') == '6':
                    a = t.find_element(By.CSS_SELECTOR, "a")
                    con_link = a.get_attribute('href')
                    constituency = a.text
                elif t.get_attribute('aria-colindex') == '7':
                    try:
                        a = t.find_element(By.CSS_SELECTOR, "a")
                        person_link = a.get_attribute('href')
                        name = a.text
                    except:
                        person_link = None
                        name = t.text
                elif t.get_attribute('aria-colindex') == '9':
                    occupation = t.text
                elif t.get_attribute('aria-colindex') == '10':
                    try:
                        a = t.find_element(By.CSS_SELECTOR, "a")
                        party_link = a.get_attribute('href')
                        alt_caucus = a.text
                    except:
                        party_link = None
                        alt_caucus = t.text
                    caucus = alt_caucus.replace(' Party of Canada', '').replace(' of Canada', '')
                elif t.get_attribute('aria-colindex') == '11':
                    result = t.text
                    # cant print text on headless for unknown reason
                    z = str(t.get_attribute('outerHTML'))
                    x = z.find('>')
                    c = z[x+1:].find('<')
                    result = z[x+1:x+1+c]
                elif t.get_attribute('aria-colindex') == '12':
                    vote_count = t.text
                    # cant print text on headless for unknown reason
                    z = str(t.get_attribute('outerHTML'))
                    x = z.find('>')
                    c = z[x+1:].find('<')
                    vote_count = z[x+1:x+1+c]
            a = name.find(', ')
            last_name = name[:a]
            first_name = name[a+2:]
            prntDebug(first_name, last_name)
            try:
                p = Person.objects.filter(first_name=first_name, last_name=last_name)[0]
                # break
            except:
                p = Person()
                # p.Region_obj = 
                p.first_name = first_name
                p.last_name = last_name
                p.save()
                p.create_post()
            if p.parl_ca_small_img != img:
                p.parl_ca_small_img = img
                p.save()
            try:
                con = Riding.objects.filter(Q(name=constituency)|Q(alt_name=constituency.replace('-', '')))[0]
            except:
                try:
                    prov = Province.objects.filter(name=province)[0]
                except:
                    prov = Province()
                    prov.name = province
                    prov.save()
                con = Riding()
                con.name = constituency
                con.alt_name = constituency.replace('-', '')
                con.province = prov
                con.province_name = prov.name
                con.parlinfo_link = con_link
                con.save()
                con.create_post()
                # con.fillout()
                toFillList.append(con)
            if con.parlinfo_link != con_link:
                con.parlinfo_link = con_link
                con.save()
            try:
                party = Party.objects.filter(Q(name=caucus)|Q(alt_name=alt_caucus), level='Federal')[0]
            except:
                party = Party()
                party.name = caucus
                party.alt_name = alt_caucus
                party.level = 'Federal'
                party.parlinfo_link = party_link
                party.save()
                party.create_post()
                # party.fillout()
                toFillList.append(party)
            if party.parlinfo_link != party_link:
                party.parlinfo_link = party_link
                party.save()
            try:
                r = Role.objects.filter(person=p, position='Election Candidate', group='General Election', end_date=date_time)[0]
            except:
                r = Role()
                # r.Region_obj = 
                r.person = p
                r.person_name = '%s %s' %(p.first_name, p.last_name)
                r.position = 'Election Candidate'
                r.group = 'General Election'
            r.end_date = date_time
            r.party_name = caucus
            r.province_name = province
            r.constituency_name = constituency
            r.riding = con
            r.party = party
            r.election = e
            r.occupation = occupation
            r.result = result
            # prntDebug(vote_count)
            # prntDebug(int(vote_count.replace(',','')))
            r.vote_count = int(vote_count.replace(',',''))
            r.parlinfo_link = person_link
            r.save()
    # prntDebug('get_list')        
    get_list(driver)
    n = 2
    # completed = 'notCompleted'
    while driver.find_element(By.CLASS_NAME, "dx-next-button") and 'disable' not in driver.find_element(By.CLASS_NAME, "dx-next-button").get_attribute('class'):
        prntDebug('')
        prntDebug('page ', n)
        next = driver.find_element(By.CLASS_NAME, "dx-next-button")
        next.click()
        time.sleep(2)
        get_list(driver)
        n += 1
    # if 'disable' in driver.find_element(By.CLASS_NAME, "dx-next-button").get_attribute('class'):
    #     completed = 'isCompleted'
    prntDebug('done1')
    driver.quit()
    prntDebug('-------toFillList----------')
    for i in toFillList:
        if i.parlinfo_link or not i.wikipedia:
            i.fillout()
    driver.quit()
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()
    
def get_all_federal_candidates():
    num = 44
    for n in range(num):
        n+=1
        get_federal_candidates(n)
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()

def get_house_committees(object_type='committee', value='latest'):
    get_house_hansard_or_committee(object_type, value)
    get_house_committee_list('latest')
    get_house_committee_work('latest')

def get_house_hansard_or_committee(object_type, value, func):
    shareData = []
    country = Region.objects.filter(modelType='country', Name='Canada')[0]
    # gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country)[0]
    xml = 'https://www.ourcommons.ca/PublicationSearch/en/?PubType=37&xml=1'
    is_hansard = False
    is_committee = False
    if object_type == 'hansard' and value == 'latest':
        prntDebug('---------------------housee hansard')
        # prntDebug('is hansard')
        is_hansard = True
        # xml = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=from2022-10-31to2022-10-31&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=150000&PubType=37&xml=1'
        xml = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=150000&PubType=37&xml=1'
    elif object_type == 'committee' and value == 'latest':
        # prntDebug('is committee')
        is_committee = True
        # xml = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=from2022-10-31to2022-10-31&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=150000&PubType=40017&xml=1'
        xml = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=150000&PubType=40017&xml=1'
    elif object_type == 'committee':
        # prntDebug('build database')
        xml = value
        # xml = 'https://www.ourcommons.ca/PublicationSearch/en/?PubType=40017&xml=1&parlses=from2023-03-01to2023-04-01'
        is_committee = True
    elif object_type == 'hansard':
        # prntDebug('build database')
        xml = value
        # xml = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=from2002-05-02to2002-05-02&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=2000000&PubType=37&xml=1'
        is_hansard = True
    prntDebug(xml)
    # fail
    # start_time = datetime.datetime.now()
    # prntDebug('start', start_time)
    r = requests.get(xml, verify=False)
    prntDebug('received')
    # end_time = datetime.datetime.now() - start_time
    # prntDebug('end11', end_time)
    # mb = to_megabytes(r)
    # prntDebug('mb', mb)
    root = ET.fromstring(r.content)
    # mb = to_megabytes(root)
    # prntDebug('mb', mb)
    # time.sleep(3)
    # prntDebug('----root')
    publications = root.find('Publications')
    # prntDebug(publications)
    pubs = publications.findall('Publication')
    for p in reversed(pubs):
        # prntDebug(p.tag)
        Title = p.attrib['Title']
        prntDebug(Title)
        # prntDebug(len(Title))
        pub_iden = p.attrib['Id']
        date = p.attrib['Date']
        # '2022-10-28'
        xTime = p.attrib['Time']
        # Publication_date_time = None
        Parliament = p.attrib['Parliament']
        Session = p.attrib['Session']
        # try:
        #     gov = Government.objects.filter(Country_obj=country, gov_level='Federal', GovernmentNumber=Parliament, SessionNumber=Session, Region_obj=country)[0]
        # except:
        #     gov = Government(Country_obj=country, gov_level='Federal', GovernmentNumber=Parliament, SessionNumber=Session, Region_obj=country)
        #     gov.save()
        #     gov.end_previous()
        gov, govU, govData, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=Parliament, SessionNumber=Session, Region_obj=country)
        if gov_is_new:
            shareData.append(gov.end_previous(func))
            gov, govU, govData, gov_is_new, shareData = save_and_return(gov, govU, govData, gov_is_new, shareData, func)
        # Organization = p.attrib['Organization']
        # PdfURL = p.attrib['PdfURL']
        # IsAudioOnly = p.attrib['IsAudioOnly']
        # IsTelevised = p.attrib['IsTelevised']
        # TypeId = p.attrib['TypeId']
        # HtmlURL = p.attrib['HtmlURL']
        # MeetingIsForSenateOrganization = p.attrib['MeetingIsForSenateOrganization']
        if value == 'latest':
            new = False
        else:
            new = True
        if is_hansard:
            date_A = datetime.datetime.strptime('%s' %(date), '%Y-%m-%d').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
            date_time = datetime.datetime.strptime('%s/%s' %(date, xTime), '%Y-%m-%d/%H:%M').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
            try:
                meeting = Meeting.objects.filter(meeting_type='Debate', DateTime__gte=date_A, DateTime__lt=date_A + datetime.timedelta(days=1), Title=Title, chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)[0]
                meeting, meetingU, meetingData, meeting_is_new = get_model_and_update('Meeting', obj=meeting)
            except:
                meeting, meetingU, meetingData, meeting_is_new = get_model_and_update('Meeting', meeting_type='Debate', DateTime=date_time, Title=Title, chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
            
            # debate, debateU, debateData, debate_is_new = get_model_and_update('Meeting', meeting_type='debate', DateTime__gte=date_A, DateTime__lt=date_A + datetime.timedelta(days=1), chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
            # debate.Title=Title
            # debate.DateTime=date_time
            if 'has_transcript' not in meetingData or meetingData['has_transcript'] == False:
                new = True
                meetingData['has_transcript'] = False
            if meeting_is_new:
                
                try:
                    A = Agenda.objects.filter(DateTime__gte=date_time, DateTime__lt=date_time + datetime.timedelta(hours=12), chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)[0]
                    A, Au, AData, A_is_new = get_model_and_update('Agenda', obj=A)
                except:
                    A, Au, AData, A_is_new = get_model_and_update('Agenda', DateTime=date_time, chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                    A, Au, AData, A_is_new, shareData = save_and_return(A, Au, AData, A_is_new, shareData, func)
                meeting.Agenda_obj = A    
            
            # try:
            #     H = Hansard.objects.filter(DateTime__gte=date_A, DateTime__lt=date_A + datetime.timedelta(days=1), ParliamentNumber=Parliament, SessionNumber=Session, Organization='House')[0]
            #     prntDebug('hansard found')
            #     H.Title=Title
            #     H.DateTime=date_time
            #     if not H.has_transcript:
            #         new = True
            # except:
            #     try:
            #         A = Agenda.objects.filter(date_time__gte=date_time, date_time__lt=date_time + datetime.timedelta(days=1), organization='House', gov_level='Federal')[0]
            #         prntDebug('agenda found')
            #     except:
            #         prntDebug('create agenda')
            #         A = Agenda(date_time=date_time, organization='House', gov_level='Federal')
            #         A.save()
            #         A.create_post()
            #     try:
            #         H = Hansard.objects.filter(agenda=A)[0]
            #         if not H.has_transcript:
            #             new = True
            #     except:
            #         H = Hansard(agenda=A, Title=Title, ParliamentNumber=Parliament, SessionNumber=Session, Publication_date_time=date_time, Organization='House')
            #         new = True
            #         H.save()
            #         H.create_post() 
                # H = Hansard(Title=Title, ParliamentNumber=Parliament, SessionNumber=Session, Publication_date_time=date_time, Organization='House')
                # new = True
                prntDebug('hansard created')
            meeting.GovPage = 'https://www.ourcommons.ca/DocumentViewer/en/%s-%s/house/sitting-%s/hansard' %(Parliament, Session, meeting.Title.replace('Hansard - ',''))
        elif is_committee:
            a = Title.find(' - ')+len(' - ')
            b = Title[a:].find('-')
            code = Title[a:a+b]
            try:
                committee = Committee.objects.filter(code=code.upper(), ParliamentNumber=44, SessionNumber=1)[0]
            except:
                committee = Committee(code=code.upper(), Organization='House', Title=p.attrib['Organization'], ParliamentNumber=44, SessionNumber=1)
                committee.save()
                committee.create_post()
            try:
                date_time_start = datetime.datetime.strptime('%s' %(date), '%Y-%m-%d')
                dt_plus_one = date_time_start + datetime.timedelta(days=1)
                H = CommitteeMeeting.objects.filter(committee=committee, date_time_start__range=[datetime.datetime.strftime(date_time_start, '%Y-%m-%d'), datetime.datetime.strftime(dt_plus_one, '%Y-%m-%d')], ParliamentNumber=Parliament, SessionNumber=Session)[0]
                prntDebug('committeeM found')
                # H.code = code
                if not H.Title:
                    H.Title = Title
            except:
                H = CommitteeMeeting(committee=committee, Title=Title, code=code, Organization='House', ParliamentNumber=Parliament, SessionNumber=Session)
                H.has_transcript = True
                prntDebug('committeeM created')
                new = True
        meeting.DateTime = datetime.datetime.strptime('%s-%s' %(date, xTime), '%Y-%m-%d-%H:%M').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
        # meeting.ParliamentNumber = int(p.attrib['Parliament'])
        # meeting.SessionNumber = int(p.attrib['Session'])
        # H.Title = p.attrib['Title']
        meeting.PublicationId = pub_iden
        # H.Organization = p.attrib['Organization']
        meetingData['PdfURL'] = p.attrib['PdfURL']
        meetingData['IsAudioOnly'] = int(p.attrib['IsAudioOnly'])
        meetingData['IsTelevised'] = int(p.attrib['IsTelevised'])
        meeting.TypeId = int(p.attrib['TypeId'])
        # H.ItemId = p.attrib['Id']
        meetingData['HtmlURL'] = p.attrib['HtmlURL']
        meetingData['MeetingIsForSenateOrganization'] = p.attrib['MeetingIsForSenateOrganization']
        # prntDebug('saving')
        # H.Terms = []
        if 'Terms' in meetingData:
            meeting_terms = json.loads(meetingData['Terms'])
        else:
            meeting_terms = {}
        # H.save()
        # H.create_post()
        # prntDebug('saved')
        meeting, meetingU, meetingData, meeting_is_new, shareData = save_and_return(meeting, meetingU, meetingData, meeting_is_new, shareData, func)
        items = p.findall('PublicationItems')
        if new or meetingData['has_transcript'] == False:
        # if new or H.object_type == 'hansard' and H.completed_model == False:
            for item in items:
                it = item.findall('PublicationItem')
                for i in it:
                    ItemId = i.attrib['Id']
                    # prntDebug('itemdid', ItemId)
                    EventId = i.attrib['EventId']
                    Date = i.attrib['Date']
                    Hour = i.attrib['Hour']
                    Minute = i.attrib['Minute']
                    Second = i.attrib['Second']
                    # '2022-10-31-11:03:49'
                    # prntDebug('---1')
                    # dt = '%s:%s:%s' %(Hour, Minute, Second)
                    # prntDebug(dt)
                    # Item_date_time = datetime.datetime.strptime(dt, '%H:%M:%S')
                    # prntDebug(Item_date_time)
                    # prntDebug('---2')
                    dt = '%s-%s:%s:%s' %(Date, Hour, Minute, Second)
                    prntDebug(dt)
                    Item_date_time = datetime.datetime.strptime(dt, '%Y-%m-%d-%H:%M:%S').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
                    if is_hansard:
                        statement, statementU, statementData, statement_is_new = get_model_and_update('Statement', ItemId=ItemId, EventId=EventId, DateTime=Item_date_time, Meeting_obj=meeting, chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                        # try:
                        #     h = HansardItem.objects.filter(ItemId=ItemId, EventId=EventId, Item_date_time=Item_date_time)[0]
                        #     # prntDebug('----handsard--found')
                        # except:
                        #     h = HansardItem(ItemId=ItemId, EventId=EventId, Item_date_time=Item_date_time)
                        #     # prntDebug('----hansard--created')
                        # h.hansard = H
                    elif is_committee:
                        try:
                            h = CommitteeItem.objects.filter(committeeMeeting=H, EventId=EventId, Item_date_time=Item_date_time)[0]
                            # prntDebug('----handsard--found')
                        except:
                            h = CommitteeItem(committeeMeeting=H, ItemId=ItemId, EventId=EventId, Item_date_time=Item_date_time, meeting_title=H.Title)
                            # prntDebug('----hansard--created')
                        # h.committeeMeeting = H
                    # h.hansardId = H.id
                    statementData['VideoURL'] = i.attrib['VideoURL'] + '&vt=watch&autoplay=true'
                    # h.Sequence = i.attrib['Sequence']
                    try:
                        statementData['Page'] = i.attrib['Page']
                    except:
                        pass
                    try:
                        statement.PdfPage = i.attrib['PdfPage']
                    except:
                        pass
                    statementData['TypeId'] = i.attrib['TypeId']
                    # h.FacebookLink = i.attrib['FacebookLink']
                    # h.TwitterLink = i.attrib['TwitterLink']
                    # h.Title = p.attrib['Title']
                    # prntDebug(h.Title)
                    statementData['PublicationId'] = int(p.attrib['Id'])
                    # prntDebug(int(p.attrib['Id']))
                    date = p.attrib['Date']
                    # '2022-10-28-11:00'# prntDebug('----')
                    person = i.find('Person')
                    try:
                        Id = person.attrib['Id']
                    except: 
                        Id = None
                    # prntDebug('before name')
                    # IsMember = person.attrib['IsMember']
                    try:
                        ProfileUrl = person.find('ProfileUrl').text
                    except:
                        ProfileUrl = None
                    # prntDebug(ProfileUrl)
                    FirstName = person.find('FirstName').text
                    # prntDebug(FirstName)
                    LastName = person.find('LastName').text
                    # prntDebug(LastName)
                    # Honorific = person.find('Honorific').text
                    # URLFullName = person.find('URLFullName').text
                    # Constituency = person.find('Constituency').text
                    # Caucus = person.find('Caucus').text
                    # Province = person.find('Province').text
                    
                    try:
                        Image = person.find('Image').text
                    except:
                        Image = None

                    try:
                        if Id:
                        # if IsMember == '1':
                            # prntDebug('has id', Id)
                            profile, profileU, profileData, profile_is_new = get_model_and_update('Person', GovIden=Id, Country_obj=country, Region_obj=country)
                        # try:
                        #     profile = Person.objects.filter(GovIden=Id, Country_obj=country)[0]
                        #     prntDebug(profile)
                        # except:
                        #     prntDebug('except')
                        else:
                            profile, profileU, profileData, profile_is_new = get_model_and_update('Person', FirstName=FirstName, LastName=LastName, Country_obj=country, Region_obj=country)
                            
                            # try:
                            #     profile = Person.objects.filter(FirstName=FirstName, LastName=LastName, Country_obj=country)[0]
                            #     # profile = profiles[0] #to cause fail if return none
                            # except:
                            #     profile = Person.objects.filter(FirstName__icontains=FirstName, LastName=LastName, Country_obj=country)[0]
                                # profile = profiles[0] #to cause fail if return none
                            # prntDebug(profiles)
                            # prntDebug('next')
                            # for profile in profiles:
                            try:
                                # prntDebug(profile)
                                # r = None
                                r = Role.objects.filter(Person_obj=profile, Position='Member of Parliament')[0]
                                prntDebug(r)
                                if ProfileUrl:
                                    profileData['GovProfilePage'] = ProfileUrl
                                    # profile.save()
                                    try:
                                        mpData = get_MP(profile, profileU, profileData, profile_is_new, func)
                                        for d in mpData:
                                            shareData.append(d)
                                    except Exception as e:
                                        prntDebug(str(e))
                                # prntDebug('break')
                                # break
                            except Exception as e:
                                prntDebug(str(e))
                            # if not r:
                            #     prntDebug('looking for candidates')
                            #     # for profile in profiles:
                            #     try:
                            #         prntDebug(profile)
                            #         # r = Role.objects.filter(person=profile, position='Election Candidate', group='General Election', result__icontains='Elected')[0]
                            #         prntDebug(r)
                            #         if ProfileUrl:
                            #             profile.gov_profile_page = ProfileUrl
                            #             profile.save()
                            #             try:
                            #                 get_MP(profile)
                            #             except Exception as e:
                            #                 prntDebug(str(e))
                            #         # prntDebug('break')
                            #         # break
                            #     except Exception as e:
                            #         prntDebug(str(e))
                            # if not r:
                            #     fail
                        # if not profile.party_name:
                        #     try:
                        #         get_MP(profile)
                        #     except Exception as e:
                        #         prntDebug(str(e))
                        # else:
                        #     prntDebug('no id')
                        #     profile, profileU, profileData, profile_is_new = get_model_and_update('Person', FirstName=FirstName, LastName=LastName, Country_obj=country, Region_obj=country)
                            # profile = Person.objects.filter(first_name=FirstName, last_name=LastName, gov_iden=0)[0]
                        # prntDebug('----person--found')
                    except Exception as e:
                        prntDebug(str(e))
                        prntDebug('create person')
                        profile, profileU, profileData, profile_is_new = get_model_and_update('Person', FirstName=FirstName, LastName=LastName, Country_obj=country, Region_obj=country)
                            # profile = Person(gov_iden=Id)
                            # # p.Region_obj = 
                            # profile.first_name = FirstName
                            # profile.last_name = LastName
                        if Id:
                            profile.GovProfilePage = ProfileUrl
                            profile.GovIden = Id
                            # profile.save()
                            # profile.create_post()
                            try:
                                mpData = get_MP(profile, profileU, profileData, profile_is_new, func)
                                for d in mpData:
                                    shareData.append(d)
                            except Exception as e:
                                prntDebug(str(e))
                        # else:
                        #     prntDebug('no id')
                        #     profile, profileU, profileData, profile_is_new = get_model_and_update('Person', FirstName=FirstName, LastName=LastName, Country_obj=country, Region_obj=country)
                        #     # profile = Person(first_name=FirstName, last_name=LastName)
                        #     # # p.Region_obj = 
                        #     # profile.save()
                        #     # profile.create_post()
                        if Image:
                            profile.PhotoLink = Image
                        # profile.save()
                        # prntDebug('----person--created')
                    profile, profileU, profileData, profile_is_new, shareData = save_and_return(profile, profileU, profileData, profile_is_new, shareData, func)
                    statement.Person_obj = profile
                    statement.PersonName = profile.FullName
                    # if profile not in H.people.all():
                    # H.people.add(profile)
                    # prntDebug('2')
                    # try:
                    #     if profile not in H.people:
                    #         H.people.append(profile)
                    # except Exception as e:
                    #     # prntDebug(' e', str(e))
                    #     H.people = []
                    #     if profile not in H.people:
                    #         H.people.append(profile)
                    # prntDebug('aaa')
                    statement.OrderOfBusiness = i.find('OrderOfBusiness').text
                    statement.SubjectOfBusiness = i.find('SubjectOfBusiness').text
                    # try:
                    if statement.SubjectOfBusiness:
                        if 'subjects' in meetingData:
                        # try:
                            meetingData['subjects'].append(statement.SubjectOfBusiness)
                        else:
                            meetingData['subjects'] = [statement.SubjectOfBusiness]
                            # statement.subjects.append(h.SubjectOfBusiness)
                    # except Exception as e:
                    #     # prntDebug(' e', str(e))
                    #     H.subjects = []
                    #     if h.SubjectOfBusiness not in H.subjects:
                    #         H.subjects.append(h.SubjectOfBusiness)
                    statementData['EventType'] = i.find('EventType').text
                    # prntDebug('-_-_-_-')
                    XmlContent = i.find('XmlContent')
                    try:
                        # prntDebug('try')
                        Intervention = XmlContent.find('Intervention')
                        # prntDebug('intervention')
                        try:
                            statementData['Type'] = Intervention.attrib['Type']
                        except:
                            pass
                        # prntDebug(Intervention.attrib['ToC'])
                        try:
                            ToCText = Intervention.attrib['ToCText']
                        except:
                            pass
                        # prntDebug(Intervention.attrib['id'])
                        try:
                            PersonSpeaking = Intervention.find('PersonSpeaking')
                            # h.person_name  = PersonSpeaking.find('Affiliation').text
                        except:
                            pass
                        # prntDebug('b')
                        # prntDebug(Affiliation.text)
                        Content = Intervention.find('Content')
                        FloorLanguage = Content.find('FloorLanguage')
                        # prntDebug('c')
                        try:
                            statement.Language = FloorLanguage.attrib['language']
                        except:
                            pass
                        ParaText = Content.findall('ParaText')
                        # h.wordCount = len(''.join(Content.itertext())) 
                        statement.Content = ''
                        for pt in ParaText:
                            Content = ET.tostring(pt).decode()
                            # prntDebug(str(Content))
                            statement.Content = statement.Content + '\n' + str(Content)
                        # h.Content = h.Content.decode("utf-8")
                        # prntDebug(statement.Content)
                        string =  re.sub('<[^<]+?>', '', statement.Content)
                        words = re.findall(r'\w+', string)
                        # prntDebug(words)
                        statement.word_count = len(words)
                        # prntDebug(statement.word_count)
                    except Exception as e:
                        prntDebug('except', str(e))
                        # h.save()
                        SubjectOfBusiness = XmlContent.find('SubjectOfBusiness')
                        SubjectOfBusinessContent = SubjectOfBusiness.find('SubjectOfBusinessContent')
                        FloorLanguage = SubjectOfBusinessContent.find('FloorLanguage')
                        # prntDebug(FloorLanguage.attrib['language'])
                        try:
                            statement.Language = FloorLanguage.attrib['language']
                        except:
                            pass
                        # prntDebug('1')
                        WrittenQuestionResponse = SubjectOfBusinessContent.findall('WrittenQuestionResponse')
                        # prntDebug('writtenquestionnresponse found')
                        statement.word_count = 0
                        statementData['questions'] = []
                        for Quest in WrittenQuestionResponse:
                            question = {}
                            QuestionId = Quest.find('QuestionID')
                            QuestionNumber = ''.join(QuestionId.itertext())
                            question['QuestionId'] = QuestionId
                            question['QuestionNumber'] = QuestionNumber
                            # try:
                            #     q = Question.objects.filter(HansardTitle=H.Title, Parliament=H.ParliamentNumber, Session=H.SessionNumber, QuestionNumber=QuestionNumber)[0]
                            # except:
                            #     q = Question(HansardTitle=H.Title, Parliament=H.ParliamentNumber, Session=H.SessionNumber, QuestionNumber=QuestionNumber)
                            #     q.save()
                            # if q not in h.questions.all():
                            #     h.questions.add(q)
                            # try:
                            #     if q not in h.questions:
                            #         h.questions.append(q)
                            # except Exception as e:
                            #     # prntDebug(' e', str(e))
                            #     h.questions = []
                            #     if q not in h.questions:
                            #         h.questions.append(q)
                            # h.question = q
                            # prntDebug(ET.tostring(q))
                            try:
                                Questioner = Quest.find('Questioner')
                                # prntDebug('aa')
                                QuestionerName = Questioner.find('Affiliation').text
                            except:
                                QuestionerName = None
                            # prntDebug('bb')
                            if '. ' in QuestionerName:
                                a = QuestionerName.find('. ')
                            else:
                                a = 0
                            if '(' in QuestionerName:
                                b = QuestionerName[a:].find('(')
                            else:
                                b = len(QuestionerName[a:])
                            name = QuestionerName[a:a+b].split()
                            # # prntDebug('quesiton', name)
                            # try:
                            #     qp = Person.objects.filter(Q(first_name__in=name)&Q(last_name__in=name)).exclude(gov_iden=0).first()
                            #     q.questioner = qp
                            # except Exception as e:
                            #     prntDebug(str(e))
                                # fail
                            # prntDebug('---33')
                            # q.questioner_name = 
                            question['QuestionerName'] = '%s %s' %(name[1], name[2])
                            QuestionContent = Quest.find('QuestionContent')
                            ParaText = QuestionContent.findall('ParaText')
                            question['QuestionContent'] = ''
                            for pt in ParaText:
                                # prntDebug(pt)
                                # prntDebug(ET.tostring(pt))
                                Content = ET.tostring(pt).decode()
                                question['QuestionContent'] = question['QuestionContent'] + '\n' + str(Content)
                            string =  re.sub('<[^<]+?>', '', question['QuestionContent'])
                            words = re.findall(r'\w+', string)
                            try:
                                statement.word_count = statement.word_count + len(words)
                            except:
                                statement.word_count = len(words)
                            response = {}
                            try:
                                # prntDebug('cc')
                                Responder = Quest.find('Responder')
                                ResponderName = Responder.find('Affiliation').text
                                if '. ' in ResponderName:
                                    a = ResponderName.find('. ')
                                else:
                                    a = 0
                                if '(' in ResponderName:
                                    b = QuestionerName[a:].find('(')
                                else:
                                    b = len(ResponderName[a:])
                                name = ResponderName[a:a+b].split()
                                # prntDebug('responder', name)
                                # try:
                                #     qr = Person.objects.filter(Q(first_name__in=name)&Q(last_name__in=name)).exclude(gov_iden=0).first()
                                #     q.responer = qr
                                # except:
                                #     pass
                                response['ResponderName'] = '%s %s' %(name[1], name[2])
                            except:
                                pass
                            # prntDebug('---4')
                            try:
                                ResponseContent = Quest.find('ResponseContent')
                                # prntDebug('responsecontent found')
                                ParaText = ResponseContent.findall('ParaText')
                                response['ResponseContent'] = ''
                                for pt in ParaText:
                                    # prntDebug(pt)
                                    # prntDebug(ET.tostring(pt))
                                    Content = ET.tostring(pt).decode()
                                    response['ResponseContent'] = response['ResponseContent'] + '\n' + str(Content)
                                string =  re.sub('<[^<]+?>', '', response['ResponseContent'])
                                words = re.findall(r'\w+', string)
                                try:
                                    statement.word_count = statement.word_count + len(words)
                                except:
                                    statement.word_count = len(words)
                            except:
                                try:
                                    ProceduralText = SubjectOfBusinessContent.find('ProceduralText').text
                                    # Content = ET.tostring(ProceduralText).decode()
                                    question['QuestionContent'] = question['QuestionContent'] + '\n' + str(ProceduralText)
                                except:
                                    pass
                            question['response'] = response
                            statementData['questions'].append(question)
                            # q.save()
                                    #     prntDebug(pt.text)
                                    #     try:
                                    #         document = pt.find('Document')
                                    #         prntDebug(document.text)
                                    #         prntDebug('DOCUMENT')
                                    #     except:
                                    #         pass
                                    #     quote = pt.find('Quote')
                                    #     try:
                                    #         QuotePara = quote.find('QuotePara')
                                    #         prntDebug('QUOTE')
                                    #         prntDebug(QuotePara.text)
                                    #     except:
                                    #         pass
                                    #     prntDebug(pt.text)
                                    #     ParaText2 = pt.findall('ParaText')
                                    #     prntDebug(ParaText2)
                                    #     for pt2 in ParaText2:
                                    #         prntDebug(pt2.text)
                                    # prntDebug(XmlContent.text)
                    statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData, func)
                    try:
                        # prntDebug('----555')
                        IndexEntries = i.find('IndexEntries')
                        Terms = IndexEntries.findall('Term')
                        # prntDebug(Terms)
                        statement.Terms_array = []
                        s_terms = []
                        for t in Terms:
                            # prntDebug(t.attrib['Id'])
                            # prntDebug(t.attrib['IsProceduralTerm'])
                            text = t.text
                            s_terms.append(text)
                            # if not text in meeting_terms:
                            #     meeting_terms[text] = 1
                            # else:
                            #     meeting_terms[text] += 1
                            try:
                                a = text.find(', ')
                                b = text[:a]
                                bill = Bill.objects.filter(NumberCode=b, Country_obj=country, Government_obj=gov).filter(Q(chamber='Senate')|Q(chamber='House'))[0]
                                bill, billU, billData, bill_is_new = get_model_and_update('Bill', obj=bill)
                                prntDebug(bill)
                                LatestBillEventDateTime = datetime.datetime.fromisoformat(billData['LatestBillEventDateTime'])
                                if meeting.DateTime > LatestBillEventDateTime:
                                    billData['LatestBillEventDateTime'] = datetime.datetime.isoformat(meeting.DateTime)
                                    bill, billU, billData, bill_is_new, shareData = save_and_return(bill, billU, billData, bill_is_new, shareData, func)
                                # h.bills.add(bill)
                                # h.save()
                                statement = statement.add_term(text, bill)
                            except Exception as e:
                                # h.save()
                                statement = statement.add_term(text, None)
                        for text in s_terms:
                            if not text in meeting_terms:
                                meeting_terms[text] = 1
                            else:
                                meeting_terms[text] += 1

                    except Exception as e:
                        prntDebug('e3', str(e))
                        if 'findall' not in str(e):
                            fail
                        # break
                    # prntDebug('next')
                    # h.save()
                    # h.create_post()
                    # shareData.append(save_obj_and_update(statement, statementU, statementData, statement_is_new))
                    # if not s_terms:
                        # x = Statement.objects.filter(id=statement.id)[0]
                        # if x.keyword_array:
                    for k in statement.keyword_array:
                        # text = k[0].upper() + k[1:]
                        if not k in meeting_terms:
                            meeting_terms[k] = 1
                        else:
                            meeting_terms[k] += 1
            meetingData['has_transcript'] = True
            meetingData = meeting.apply_terms(meeting_terms, meetingData)
            # try:
            #     d = json.loads(H.TermsText)
            #     for t in list(d.items()):
            #         topic_link = '%s?topic=%s' %(H.get_absolute_url(), t)
            #         followers = User.objects.filter(follow_topic__contains=t)
            #         for f in followers:
            #             try:
            #                 n = Notification.objects.filter(user=f, link=topic_link)[0]
            #             except:
            #                 f.alert('%s was discussed in the %s' %(t, H.Organization), topic_link, '%s the %s' %(H.Publication_date_time.strftime('%A'), get_ordinal(int(H.Publication_date_time.strftime('%d')))))
            # except Exception as e:
            #     prntDebug(str(e))
            if is_hansard:
                people = Statement.objects.filter(Meeting_obj=meeting)
            elif is_committee:
                people = CommitteeItem.objects.filter(committeeMeeting=H)
            H_people = {}
            for p in people:
                # prntDebug(p)
                # prntDebug(p.person)
                # prntDebug(p.person.id)
                if not p.Person_obj.id in H_people:
                    H_people[p.Person_obj.id] = 1
                else:
                    H_people[p.Person_obj.id] += 1
            H_people = sorted(H_people.items(), key=operator.itemgetter(1), reverse=True)
            # if is_hansard:
            #     # prntDebug('--------------------assign notifications')
            #     for p in H.people.all():
            #         # prntDebug(p)
            #         # r = Role.objects.filter(position='Member of Parliament', person=p)[0]
            #         # users = User.objects.filter(riding=r.riding)
            #         # for u in users:
            #         #     u.alert('%s %s spoke in Parliament %s' %(p.first_name, p.last_name, H.Publication_date_time.weekday()), '%s?speaker=%s' %(H.get_absolute_url(), p.id))
            #         users = User.objects.filter(follow_person=p)
            #         for u in users:
            #             u.alert('%s %s spoke in Parliament' %(p.first_name, p.last_name), '%s?speaker=%s' %(H.get_absolute_url(), p.id), '%s the %s' %(H.Publication_date_time.strftime('%A'), get_ordinal(int(H.Publication_date_time.strftime('%d')))))
            H_people = dict(H_people)
            meetingData['People_json'] = json.dumps(H_people)
            if is_hansard:
                meetingData['VideoURL'] = Statement.objects.filter(Meeting_obj=meeting).last().VideoURL
                # sprenderize(H)
            meetingData['completed_model'] = True
            meeting, meetingU, meetingData, meeting_is_new, shareData = save_and_return(meeting, meetingU, meetingData, meeting_is_new, shareData, func)

            # H.save()
            # H.create_post()
            prntDebug('saved')
            # break
    return shareData, gov

# def get_house_committees():
#     get_house_hansard_or_committee('committee', 'latest')
#     get_house_committee_list('latest')
#     get_house_committee_work('latest')

def get_house_committee_list(day):
    # url = 'https://www.ourcommons.ca/Committees/en/Meetings?meetingDate=2022-10-31'
    # r = requests.get(url)
    # soup = BeautifulSoup(r.content, 'html.parser')
    # container = soup.find('div', {'id':'meeting-accordion'})
    # date = container.find('div', {'class':'grouping-header'})
    # prntDebug(date.text)
    # items = container.find_all('div', {'class':'accordion-item'})
    # for item in items:
    #     acron = item.find('span', {'class':'meeting-acronym'})
    #     timerange = item.find('div', {'class':'the-time'})
    #     title = item.find('div', {'class':'studies-activities-item'})
    #     h4 = item.find('h4', {'class':'meeting-card-committee-details-name'})
    #     title_link = h4.find('a')
    #     studies = item.find('div', {'class':'meeting-card-studiesactivities-title'})
    #     study = item.find('a', {'class':'current-study'})
    #     evidence = item.find('a', {'class':'btn-meeting-evidence'})
    #     minutes = item.find('a', {'class':'btn-meeting-minutes'})
    #     preview = item.find('div', {'class':'meeting-card-media-preview'})
    #     preview_src = preview.find('img')['src']
    #     try:
    #         embed = preview.find('button', {'class':'video-play-button'})['data-player-url']
    #     except:
    #         embed = None
    #     prntDebug(acron.text)
    #     prntDebug(timerange.text)
    #     prntDebug(title.text)
    #     prntDebug(h4.text.strip())
    #     prntDebug(title_link['href'])
    #     prntDebug(studies.text)
    #     prntDebug(study['href'])
    #     try:
    #         prntDebug(evidence['href'])
    #     except:
    #         prntDebug('no evidence')
    #     try:
    #         prntDebug(minutes['href'])
    #     except:
    #         prntDebug('no mins')
    #     prntDebug(preview_src)
    #     prntDebug(embed)
    #     com_title = h4.text.strip()
    #     a = com_title.find(' (')
    #     com_title = com_title[:a]

    prntDebug('--------------------house committees')
    parl = Parliament.objects.filter(country='Canada', organization='Federal')[0]
    try:
        if day == 'latest':
            url = 'https://www.ourcommons.ca/Committees/en/Meetings'
        else:
            url = day
        # prntDebug(url)
        r = requests.get(url, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        container = soup.find('div', {'id':'meeting-accordion'})
        date = container.find('div', {'class':'grouping-header'})
        prntDebug(date.text)
        items = container.find_all('div', {'class':'accordion-item'})
        for item in items:
            # prntDebug('-----------------------------')
            iden = item['id'].replace('meeting-item-', '')
            date = item['class'][1].replace('meeting-item-', '')
            acron = item.find('span', {'class':'meeting-acronym'})
            timerange = item.find('div', {'class':'the-time'})
            dt = timerange.text
            a = dt.find(' - ')
            start = dt[:a].replace('.','')
            prntDebug('start', start)
            b = dt[a:].find(' (')
            end = dt[a+3:a+b].replace('.', '')
            date_time_start = datetime.datetime.strptime(date + ' - ' + start, '%Y-%m-%d - %I:%M %p')
            date_time_end = datetime.datetime.strptime(date + ' - ' + end, '%Y-%m-%d - %I:%M %p')
            dt_plus_one = date_time_start + datetime.timedelta(days=1)

            titles = item.find_all('div', {'class':'studies-activities-item'})
            title = ''
            for t in titles:
                if not title:
                    title = t.text
                elif t.text not in title:
                    title = title + '\n' + t.text

            h4 = item.find('h4', {'class':'meeting-card-committee-details-name'})
            title_link = h4.find('a')
            location = item.find('div', {'class':'meeting-location'})
            webcast = item.find('i', {'class':'icon-web-video-cast'})
            television = item.find('i', {'class':'icon-television'})
            speaker = item.find('i', {'class':'icon-speaker'})
            studies = item.find('div', {'class':'meeting-card-studiesactivities-title'})
            study = item.find('a', {'class':'current-study'})
            evidence = item.find('a', {'class':'btn-meeting-evidence'})
            minutes = item.find('a', {'class':'btn-meeting-minutes'})
            preview = item.find('div', {'class':'meeting-card-media-preview'})
            preview_src = preview.find('img')['src']
            try:
                embed = preview.find('button', {'class':'video-play-button'})['data-player-url']
            except:
                embed = None
            # prntDebug(date)
            # prntDebug(date)
            # prntDebug(iden)
            # prntDebug(acron.text)
            # prntDebug(timerange.text)
            prntDebug(title)
            # prntDebug(h4.text.strip())
            # prntDebug(title_link['href'])
            # prntDebug(location.text.strip())
            # if webcast:
            #     prntDebug(webcast)
            # else:
            #     prntDebug('no webcast')
            # if television:
            #     prntDebug(television)
            # else:
            #     prntDebug('no television')
            # if speaker:
            #     prntDebug(speaker)
            # else:
            #     prntDebug('no speaker')
            # prntDebug(studies.text)
            # prntDebug(study['href'])
            # try:
            #     prntDebug(evidence['href'])
            # except:
            #     prntDebug('no evidence')
            # try:
            #     prntDebug(minutes['href'])
            # except:
            #     prntDebug('no mins')
            # prntDebug(preview_src)
            # prntDebug(embed)
            com_title = h4.text.strip()
            a = com_title.find(' (')
            com_title = com_title[:a]
            # prntDebug(com_title) 

            try:
                committee = Committee.objects.filter(code=acron.text, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
            except:
                committee = Committee(code=acron.text, Title=com_title, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)
                committee.save()
                committee.create_post()
            try:
                com = CommitteeMeeting.objects.filter(committee=committee, code=acron.text, date_time_start__range=[datetime.datetime.strftime(date_time_start, '%Y-%m-%d'), datetime.datetime.strftime(dt_plus_one, '%Y-%m-%d')])[0]
                prntDebug('com found')
                # prntDebug(com)
            except Exception as e:
                com = CommitteeMeeting(code=acron.text, committee=committee, date_time_start=date_time_start, Organization='House', ParliamentNumber=committee.ParliamentNumber, SessionNumber=committee.SessionNumber)
                # com.Publication_date_time = datetime.datetime.strptime('2022-10-31', '%Y-%m-%d')
                com.save()
                com.create_post()
                prntDebug('com created')
                # prntDebug(str(e))
            # dt = timerange.text
            # a = dt.find(' - ')
            # start = dt[:a].replace('.','')
            # prntDebug('start', start)
            # b = dt[a:].find(' (')
            # end = dt[a+3:a+b].replace('.', '')
            if 'Bill' in title:
                a = title.find('Bill')+len('Bill ')
                if ', ' in title:
                    b = title[a:].find(',')
                    code = title[a:a+b]
                else:
                    code = title[a:]
                try:
                    bill = Bill.objects.filter(NumberCode=code)[0]
                    com.bill = bill
                    prntDebug('BIll', bill)
                except Exception as e:
                    prntDebug(str(e))
            com.date_time_start = date_time_start
            com.date_time_end = date_time_end
            prntDebug(com.date_time_start)
            prntDebug(com.date_time_end)
            com.ItemId = iden
            com.Title = title
            # com.Organization = h4.text.strip()
            com.timeRange = timerange.text
            com.location = location.text.strip()
            # prntDebug('https://www.ourcommons.ca' + title_link['href'])
            com.govURL = 'https://www.ourcommons.ca' + title_link['href']
            com.studies = 'https://www.ourcommons.ca' + study['href']
            if evidence:
                com.evidence = evidence['href']
            if minutes:
                com.minutes = minutes['href']
            com.previewURL = 'https://www.ourcommons.ca' + preview_src
            if webcast or television or speaker:
                x = 'http://www.ourcommons.ca/embed/en/m/%s?ml=en&vt=watch&autoplay=true' %(com.ItemId)
                time.sleep(1)
                r = requests.get(x, verify=False)
                com.embedURL = r.url
            com.save()
            prntDebug('saved')
            # r = requests.get('https://www.ourcommons.ca' + title_link['href'])
            # soup = BeautifulSoup(r.content, 'html.parser')
            # chair = soup.find('span', {'class':'committee-member-card'})
            # a = chair.find('a')['href']
            # # prntDebug('chaired by')
            # prntDebug(a)
            # if a.startswith('//'):
            #     a = a[2:]
            # prntDebug(a)
            # prntDebug('should be:')
            # prntDebug('https://www.ourcommons.ca/Members/en/marc-garneau(10524)')
            # span = chair.find('span', {'class':'member-info'})
            # first_name = span.find('span', {'class':'first-name'}).text
            # last_name = span.find('span', {'class':'last-name'}).text
            # prntDebug(first_name, last_name)
            # try:
            #     p = Person.objects.filter(gov_profile_page=a)
                
            #     # p = r.person
            # except Exception as e:
            #     prntDebug(str(e))
            #     try:
            #         p = Person.objects.filter(first_name=first_name, last_name=last_name)[0]
            #     except Exception as e:
            #         prntDebug(str(e))
            #         p = None
            # prntDebug(p)
            # prntDebug(p.gov_profile_page)
            # prntDebug(p.gov_iden)
            # com_title = com.Organization
            # a = com_title.find(' (')
            # com_title = com_title[:a]
            # prntDebug('--%s--' %(com_title))
            try:
                if not committee.chair:
                    r = Role.objects.filter(group=com_title, current=True, affiliation='Chair')[0]
                    if r.person:
                        committee.chair = r
                    committee.save()
            except Exception as e:
                prntDebug(str(e))
                # try:
                #     r = Role.objects.filter(group=com_title)
                #     for i in r:
                #         prntDebug(i.affiliation)
                # except Exception as e:
                #     prntDebug(str(e))
            prntDebug('-------------------')
            # break
    except Exception as e:
        prntDebug(str(e))
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()

def get_house_committee_work(value):   
    prntDebug('--------------------house committee work')
    def runFunc(url):
        r = requests.get(url, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {'class':'allcommittees-studiestable'})
        tbody = table.find('tbody')
        trs = tbody.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            code = tds[0].find('a').text.strip()
            prntDebug('---',code,'----')
            activity = tds[1].text.strip()
            prntDebug(activity)
            event = tds[2]
            try:
                a = 'https:' + event.find('a')['href']
            except:
                a = None
            event = re.sub(' +', ' ', event.text.strip())
            # prntDebug(event)
            # prntDebug(a)
            date = tds[3].text.strip()
            prntDebug(date)
            dt = datetime.datetime.strptime(date, '%A, %B %d, %Y')
            try:
                agendaItem = AgendaItem.objects.filter(date_time=dt, text='Government Orders')[0]
                # now = datetime.datetime.now()
                dt = dt.replace(hour=agendaItem.hour, minute=agendaItem.minute)
            except:
                pass
            # com = Committee.objects.filter(code=com)[0]
            prntDebug(dt)
            parl = Parliament.objects.filter(start_date__lte=dt, country='Canada', organization='Federal')[0]
            # prntDebug(parl)
            try:
                comMeeting = CommitteeMeeting.objects.filter(code=code, Title=activity, event=event)[0]
                # comItem = CommitteeItem.objects.filter(committeeCode=com, eventTitle=event, Item_date_time__year=dt.year, Item_date_time__month=dt.month, Item_date_time__day=dt.day)[0]
                prntDebug('meeting found')
            except:
                prntDebug('creating meeting')
                if code != 'SSRS':
                    prntDebug(code)
                    com = Committee.objects.filter(code=code, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
                    comMeeting = CommitteeMeeting(Organization='House', committee=com, code=code, Title=activity, event=event, date_time_start=dt, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)
                    if 'Bill' in activity:
                        prntDebug('bill:')
                        x = activity.find('Bill')+len('Bill ')
                        # prntDebug(x)
                        if ',' in activity[x:]:
                            y = activity[x:].find(',')
                            z = activity[x:x+y]   
                        elif '-' in activity[x:]:
                            y = activity[x:].find('-')
                            if ' ' in activity[x+y:]:
                                w = activity[x+y:].find(' ')
                                z = activity[x+y-1:x+y+w]   
                            else:
                                z = activity[x+y-1:]   
                        prntDebug(z)
                        bill = Bill.objects.filter(NumberCode=z, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
                        comMeeting.bill = bill
                        prntDebug(bill)
                    if a:
                        # url = 'https://www.ourcommons.ca/DocumentViewer/en/44-1/HUMA/report-7/'
                        prntDebug(a)
                        time.sleep(1)
                        r = requests.get(a, verify=False)
                        soup = BeautifulSoup(r.content, 'html.parser')
                        try:
                            btn_toc = soup.find('a', {'class':'btn-toc'})['href']
                            prntDebug('TOC found')
                            r = requests.get('https://www.ourcommons.ca' + btn_toc, verify=False)
                            soup = BeautifulSoup(r.content, 'html.parser')
                            try:
                                sum_link = soup.find("a", string="LIST OF RECOMMENDATIONS")['href']
                            except:
                                sum_link = soup.find("a", string="SUMMARY")['href']
                            # prntDebug(sum_link)
                            comMeeting.reportLink = 'https://www.ourcommons.ca' + sum_link
                            r = requests.get(comMeeting.reportLink, verify=False)
                            soup = BeautifulSoup(r.content, 'html.parser')
                            div = soup.find('div', {'class':'WordSection1'})
                            paras = div.find_all('p')
                            content = ''
                            for p in paras:
                                if str(p) != '<p> </p>':
                                    # content = content + re.sub(' +', ' ', p.text.strip()) + '\n\n'
                                    content = content + str(p)
                            # # prntDebug('-----')
                            # # prntDebug(content.strip())
                            # # prntDebug('------')
                            comMeeting.report = content.strip()
                        except Exception as e:
                            prntDebug(str(e))
                            comMeeting.reportLink = a
                            # body = soup.find('div', {'class':'report-body'})
                            tables = soup.find_all('table')
                            content = ''
                            paragraph = ''
                            paragraph2 = ''
                            # td = tables[0].find('td')
                            for table in tables:
                                content = content + str(table)
                            #     if re.sub(' +', ' ', table.text.strip()) not in content:
                            #         content = content + re.sub(' +', ' ', table.text.strip()) + '\n\n'
                            #         paras = table.find_all('p')
                            #         for p in paras:
                            #             paragraph = paragraph + p.text
                            #             paragraph2 = paragraph2 + re.sub(' +', ' ', p.text.strip()) + '\n\n'
                            # content = content.replace(paragraph, '')
                            # report = content + '\n\n' + paragraph2
                            # # prntDebug('------')
                            # # prntDebug(report)
                            # # prntDebug('------')
                            if '<' in content and '>' in content:
                                x = content.find('>')
                                content = content[:x] + 'style="font-size:100%;"' + content[x:]
                            comMeeting.report = content
                    comMeeting.save()
                    comMeeting.create_post()
                    prntDebug('saved')
                time.sleep(3)
            prntDebug('-----------')
    if value == 'latest':
        # url = 'https://www.ourcommons.ca/Committees/en/Work?refineByEvents=&pageNumber=1&refineByCommittees='
        url = 'https://www.ourcommons.ca/Committees/en/Work?show=allwork&parl=44&ses=1&refineByEvents=Creation,ReportPresented,ReportGovernmentResponse,ReportConcurred,ReportNegatived,ReportWithdrawn&pageNumber=1&pageSize=20'
        runFunc(url)
    elif value == 'session':
        url = 'https://www.ourcommons.ca/Committees/en/Work?parl=44&ses=1&refineByCommittees=&refineByCategories=&refineByEvents=Creation,ReportPresented,ReportGovernmentResponse,ReportConcurred,ReportNegatived&sortBySelected=LatestEvents&show=allwork&pageNumber=1&pageSize=0'
        # url = 'https://www.ourcommons.ca/Committees/en/Work?show=allwork&parl=44&ses=1&refineByEvents=ReportGovernmentResponse&pageNumber=1'
        runFunc(url)
    elif value == 'all':
        parls = ['44', '43', '42', '41', '40', '39', '38', '37']
        for parl in parls:
            prntDebug('---------------------------------')
            prntDebug(parl)
            prntDebug('--------------------------------')
            time.slee(3)
            url = 'https://www.ourcommons.ca/Committees/en/Work?parl=%s&ses=0&refineByCommittees=&refineByCategories=&refineByEvents=Creation,ReportPresented,ReportGovernmentResponse,ReportConcurred,ReportNegatived&sortBySelected=LatestEvents&show=allwork&pageNumber=1&pageSize=0' %(parl)
            runFunc(url)
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()


def get_all_house_motions():
    prntDebug('-----get all house motions')
    sessions = ['44-1', '43-2', '43-1', '42-1', '41-2', '41-1', '40-3', '40-2', '40-1', '39-2','39-1','38-1']
    sessions = ['39-1','38-1']
    # sessions = ['44-1']
    for s in sessions:
        prntDebug(s)
        url = 'https://www.ourcommons.ca/members/en/votes/xml?parlSession=%s' %(s)
        r = requests.get(url, verify=False)
        root = ET.fromstring(r.content)
        motions = root.findall('Vote')
        # count = 0
        for motion in motions:
            m = add_motion(motion)
            prntDebug('-----------')
        time.sleep(2)

def add_motion(motion, shareData, func):
    country = Region.objects.filter(modelType='country', Name='Canada')[0]
    # count += 1
    ParliamentNumber = motion.find('ParliamentNumber').text
    SessionNumber = motion.find('SessionNumber').text
    
    gov, govU, govData, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    if gov_is_new:
        shareData.append(gov.end_previous(func))
        gov, govU, govData, gov_is_new, shareData = save_and_return(gov, govU, govData, gov_is_new, shareData, func)

    DecisionEventDateTime = motion.find('DecisionEventDateTime').text
    # date_time = datetime.datetime.strptime(motion.find('DecisionEventDateTime').text, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
    date_time = datetime.datetime.fromisoformat(DecisionEventDateTime).replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
    DecisionDivisionNumber = motion.find('DecisionDivisionNumber').text
    DecisionDivisionSubject = motion.find('DecisionDivisionSubject').text
    DecisionResultName = motion.find('DecisionResultName').text
    DecisionDivisionNumberOfYeas = motion.find('DecisionDivisionNumberOfYeas').text
    DecisionDivisionNumberOfNays = motion.find('DecisionDivisionNumberOfNays').text
    DecisionDivisionNumberOfPaired = motion.find('DecisionDivisionNumberOfPaired').text
    DecisionDivisionDocumentTypeName = motion.find('DecisionDivisionDocumentTypeName').text
    DecisionDivisionDocumentTypeId = motion.find('DecisionDivisionDocumentTypeId').text
    BillNumberCode = motion.find('BillNumberCode').text
    # prntDebug(DecisionDivisionNumber)
    prntDebug('BillNumberCode', BillNumberCode)
    prntDebug('date_time', date_time)
    # prntDebug(DecisionDivisionSubject)
    prntDebug(DecisionDivisionNumber)
    try:
        motion, motionU, motionData, motion_is_new = get_model_and_update('Motion', VoteNumber=DecisionDivisionNumber, Country_obj=country, Government_obj=gov, Region_obj=country)
        # m = Motion.objects.filter(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, vote_number=DecisionDivisionNumber)[0]
        prntDebug('motion found')
        if motion_is_new or motionData['TotalVotes'] == 0:
            prntDebug('rerunning')
            fail
        return None, shareData
    except:
        time.sleep(2)
        # try:
        #     m = Motion.objects.filter(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, vote_number=DecisionDivisionNumber)[0]
        # except:
        #     m = Motion(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, vote_number=DecisionDivisionNumber)
        motion.DateTime = date_time
        motion.Yeas = DecisionDivisionNumberOfYeas
        motion.Nays = DecisionDivisionNumberOfNays
        motion.Present = DecisionDivisionNumberOfPaired
        motion.DecisionType = DecisionDivisionDocumentTypeName
        # motion.DecisionDivisionDocumentTypeId = DecisionDivisionDocumentTypeId
        motion.Result = DecisionResultName
        motion.Subject = DecisionDivisionSubject
        motion.billCode = BillNumberCode
        motion.chamber = 'House'
        motion.is_official = True
        try:
            # b = Bill.objects.filter(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, NumberCode=BillNumberCode)[0]
            # m.bill = b
            bill = Bill.objects.filter(NumberCode=BillNumberCode, Government_obj=gov, Country_obj=country, Region_obj=country)[0]
            motion.Bill_obj = bill
            prntDebug(bill)
        except Exception as e:
            prntDebug(str(e))
            bill = None
            # time.sleep(10)
        vote_url = 'https://www.ourcommons.ca/members/en/votes/%s/%s/%s' %(ParliamentNumber, SessionNumber, DecisionDivisionNumber)
        prntDebug(vote_url)
        motion.GovUrl = vote_url
        # vote_url = 'https://www.ourcommons.ca/members/en/votes/44/1/210'
        r = requests.get(vote_url, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        # prntDebug(soup)
        # prntDebug(sponsor_link)
        try:
            sponsor_link = soup.find('a', {'class':'ce-mip-mp-tile'})['href']
            s = Person.objects.filter(GovProfilePage__icontains=sponsor_link)[0]
            motion.Sponsor_obj = s
        except:
            pass
        # sub = soup.find('div', {'id':'mip-vote-desc'}).text
        # prntDebug(sub)
        text = str(soup.find('div', {'id':'mip-vote-text-collapsible-text'}))
        # prntDebug(text)
        motion.MotionText = text
        motion, motionU, motionData, motion_is_new, shareData = save_and_return(motion, motionU, motionData, motion_is_new, shareData, func)
        # prntDebug('1')
        # block = soup.find('div', {'class':'ce-mip-vote-block'})
        # ass = block.find_all('a')
        # for a in ass:
        #     if 'View this Bill' in a.text: 
        #         prntDebug(a['href'])
        # m.save()
        # prntDebug('motion saved')
        # m.create_post()

        vote_xml = 'https://www.ourcommons.ca/members/en/votes/%s/%s/%s/xml' %(ParliamentNumber, SessionNumber, DecisionDivisionNumber)
        prntDebug(vote_xml)
        r = requests.get(vote_xml, verify=False)
        root = ET.fromstring(r.content)
        votes = root.findall('VoteParticipant')
        vote_count = 0
        prntDebug('run votes')
        for vote in votes:
            vote_count += 1
            ParliamentNumber = vote.find('ParliamentNumber').text
            SessionNumber = vote.find('SessionNumber').text
            DecisionEventDateTime = vote.find('DecisionEventDateTime').text
            '2022-11-03T15:30:00'
            DecisionDivisionNumber = vote.find('DecisionDivisionNumber').text
            PersonShortSalutation = vote.find('PersonShortSalutation').text
            ConstituencyName = vote.find('ConstituencyName').text
            VoteValueName = vote.find('VoteValueName').text
            PersonOfficialFirstName = vote.find('PersonOfficialFirstName').text
            PersonOfficialLastName = vote.find('PersonOfficialLastName').text
            ConstituencyProvinceTerritoryName = vote.find('ConstituencyProvinceTerritoryName').text
            CaucusShortName = vote.find('CaucusShortName').text
            IsVoteYea = vote.find('IsVoteYea').text
            IsVoteNay = vote.find('IsVoteNay').text
            IsVotePaired = vote.find('IsVotePaired').text
            DecisionResultName = vote.find('DecisionResultName').text
            PersonId = vote.find('PersonId').text
            # prntDebug(PersonOfficialLastName)
            # prntDebug(VoteValueName)
            vote, voteU, voteData, vote_is_new = get_model_and_update('Vote', Motion_obj=motion, vote_number=DecisionDivisionNumber, PersonId=PersonId, Country_obj=country, Government_obj=gov, Region_obj=country)
            # try:
            #     v = Vote.objects.filter(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, VoteNumber=DecisionDivisionNumber, PersonId=PersonId)[0]
            # except:
            #     v = Vote(ParliamentNumber=ParliamentNumber, SessionNumber=SessionNumber, vote_number=DecisionDivisionNumber, PersonId=PersonId)
            try:
                p = Person.objects.filter(GovIden=PersonId, Country_obj=country)[0]
                vote.Person_obj = p
            except:
                p = None
            prntDebug('p,bill', p, bill)
            # if p and bill:
            #     try:
            #         post = Post.objects.filter(Bill_obj=bill)[0]
            #         prntDebug()
            #         prntDebug('create Interation')
            #         interaction, interactionU, interactionData, interaction_is_new = get_model_and_update('Interaction', Person_obj=p, Post_obj=post)
            #         interaction, interactionU, interactionData, interaction_is_new, shareData = save_and_return(interaction, interactionU, interactionData, interaction_is_new, shareData, func)
            #         prntDebug('done interaction')
            #         # if interaction_is_new:
            #         #     interaction.calculate_vote(VoteValueName, True)
            #         # else:
            #         #     interaction.calculate_vote(VoteValueName, False)

            #         # try:
            #         #     interaction = Interaction.objects.filter(post=post, person=p)[0]
            #         #     reaction.calculate_vote(VoteValueName, True)
            #         # except:
            #         #     reaction = Interaction(post=post, person=p)
            #         #     reaction.save()
            #         #     reaction.calculate_vote(VoteValueName, False)
            #     except Exception as e:
            #         prntDebug(str(e))
            #         pass
            # try:
            #     r = Role.objects.filter(person=p, position='Member of Parliament', current=True)[0]
            #     r.attendanceCount += 1
            #     r.attendancePercent = int((r.attendanceCount/total_motions)*100)
            #     r.save()
            # except:
            #     pass
            # vote.person = p
            # vote.
            # vote.PersonShortSalutation = PersonShortSalutation
            vote.ConstituencyName = ConstituencyName
            vote.VoteValue = VoteValueName
            # vote.PersonOfficialFirstName = PersonOfficialFirstName
            # vote.PersonOfficialLastName = PersonOfficialLastName
            vote.PersonFullName = PersonOfficialFirstName + ' ' + PersonOfficialLastName
            vote.ConstituencyProvStateName = ConstituencyProvinceTerritoryName
            vote.CaucusName = CaucusShortName
            vote.IsVoteYea = IsVoteYea
            vote.IsVoteNay = IsVoteNay
            vote.Present = IsVotePaired
            # vote.DecisionResultName = DecisionResultName
            # prntDebug('DecisionEventDateTime', DecisionEventDateTime)
            vote.DateTime = date_time
            # v.save()
            # v.create_post()
            # prntDebug('')
            vote, voteU, voteData, vote_is_new, shareData = save_and_return(vote, voteU, voteData, vote_is_new, shareData, func)
            # break
        motion.TotalVotes = vote_count
        motionData['TotalVotes'] = vote_count
        motion, motionU, motionData, motion_is_new, shareData = save_and_return(motion, motionU, motionData, motion_is_new, shareData, func)
        # m.save()
        prntDebug('done', vote_count)
        # prntDebug(m.total_votes)
        # prntDebug(count)
        prntDebug('')
        return motion, gov, shareData


    # if count >= 5:
    #     break

def get_house_expenses():
    def run(url):
        r = requests.get(url, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        container = soup.find('div', {'class':'data-table-container'})
        trs = container.find_all('tr')
        for tr in trs:
            if tr != trs[0]:
                tds = tr.find_all('td')
                # prntDebug(tds[0].text.strip())
                # prntDebug(tds[1].text.strip())
                # prntDebug(tds[3].text.strip())
                # prntDebug(tds[4].text.strip())
                # prntDebug(tds[5].text.strip())
                # prntDebug(tds[6].text.strip())
                name = tds[0].text.strip()
                a = name.find(', ')
                last_name = name[:a]
                first_name = name[a+2:].replace('Hon. ', '').replace('Right ', '')
                prntDebug(first_name, last_name)
                con = tds[1].text.strip()
                # prntDebug(con)
                try:
                    riding = Riding.objects.filter(Q(name=con)|Q(alt_name=con.replace('—','')))[0]
                    r = Role.objects.filter(person__last_name=last_name, person__first_name=first_name, position='Member of Parliament', current=True, riding=riding)[0]
                    total = float(tds[3].text.strip().replace('$', '').replace(',','').replace('(','').replace(')','')) + float(tds[4].text.strip().replace('$', '').replace(',','').replace('(','').replace(')','')) + float(tds[5].text.strip().replace('$', '').replace(',','').replace('(','').replace(')','')) + float(tds[6].text.strip().replace('$', '').replace(',','').replace('(','').replace(')','')) 
                    prntDebug(total)
                    r.quarterlyExpenseReport = total
                    r.save()
                except Exception as e:
                    prntDebug(str(e))
                prntDebug('')
    try:
        url = 'https://www.ourcommons.ca/ProactiveDisclosure/en/members/%s/4' %(datetime.datetime.now().year)
        run(url)
    except Exception as e:
        prntDebug(str(e))
        try:
            url = 'https://www.ourcommons.ca/ProactiveDisclosure/en/members/%s/3' %(datetime.datetime.now().year)
            run(url)
        except Exception as e:
            prntDebug(str(e))
            try:
                url = 'https://www.ourcommons.ca/ProactiveDisclosure/en/members/%s/2' %(datetime.datetime.now().year)
                run(url)
            except Exception as e:
                prntDebug(str(e))
                try:
                    url = 'https://www.ourcommons.ca/ProactiveDisclosure/en/members/%s/1' %(datetime.datetime.now().year)
                    run(url)
                except Exception as e:
                    prntDebug(str(e))
                    prntDebug('fail fail')
    
def add_senate_hansard(link, reprocess, func):
    prntDebug('add senate hansard')
    prntDebug(link)
    shareData = []
    country = Region.objects.filter(modelType='country', Name='Canada')[0]
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country)[0]
    try:
        meetingU = Update.objects.filter(Meeting_obj__GovPage=link)[0]
        prntDebug(meetingU.Meeting_obj)
        meetingData = json.loads(meetingU.data)
        if reprocess or 'has_transcript' not in meetingData or meetingData['has_transcript'] == False:
            fail
    except:
        prntDebug('adding')
        # a = 'https://sencanada.ca/en\content\sen\chamber\441\debates\076db_2022-11-01-e'
        # a = 'https://sencanada.ca/en/content/sen/chamber/441/debates/076db_2022-11-01-e'
        r = requests.get(link)
        soup = BeautifulSoup(r.content, 'html.parser')
        portal = soup.find('div', {'id':'portal-middle'})
        hs = portal.find_all('h2')
        for h in hs:
            # prntDebug(h.text)
            nums = re.findall(r'\d+', h.text)
            Title = 'Volume %s, Issue %s' %(nums[2], nums[3])
            prntDebug(Title)
            break
        prntDebug('')
        content = soup.find('div', {'id':'content-viewer-document'})
        center = content.find('center')
        # prntDebug(center.text)
        h3 = center.find('h3')
        # prntDebug(h3)
        dtime = center.find_next_sibling().find_next_sibling().text
        # prntDebug(dtime)
        # 'The Senate met at 2 p.m., the Speaker in the chair.'
        dt = h3.text + dtime.replace('.','')
        prntDebug(dt)
        try:
            date_time = datetime.datetime.strptime(dt, '%A, %B %d, %YThe Senate met at %I %p, the Speaker in the chair').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
            date = date_time.replace(hour=0)
        except Exception as e:
            # prntDebug(dt)
            prntDebug(str(e))
            # fail
            div = soup.find('div', {'id':'portal-middle'})
            h2 = div.find_all('h2')[1]
            span = h2.find('span')
            prntDebug(h2.text.replace(span.text,''))
            date = datetime.datetime.strptime(h2.text.replace(span.text,''), '%A, %B %d, %Y').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
            date_time = date.replace(hour=14)
            # date_time = datetime.datetime.now()
        prntDebug('date_time', date_time)
        # try:
        #     A = Agenda.objects.filter(organization='Senate', date_time__gte=date, date_time__lt=date+datetime.timedelta(days=1))[0]
        # except:
        #     A = Agenda(organization='Senate', gov_level='Federal', date_time=date_time)
        #     A.save()
        # try:
        #     H = Hansard.objects.filter(Publication_date_time__gte=date, Publication_date_time__lt=date+datetime.timedelta(days=1), Organization='Senate')[0]
        #     prntDebug('hansard found')
        #     H.ParliamentNumber=nums[1]
        #     H.SessionNumber=nums[0]
        #     H.Title=Title
        #     H.gov_page = link
        #     H.agenda = A
        #     H.save()
        # except:
        #     H = Hansard(ParliamentNumber=nums[1], SessionNumber=nums[0], Title=Title, Publication_date_time=date_time, Organization='Senate', agenda=A)
        #     H.gov_page = link
        #     H.save() 
        #     H.create_post() 
        #     prntDebug('hansard created')
        try:
            meeting = Meeting.objects.filter(meeting_type='Debate', GovPage=link, DateTime__gte=date, DateTime__lt=date+datetime.timedelta(days=1), chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)[0]
            meeting, meetingU, meetingData, meeting_is_new = get_model_and_update('Meeting', obj=meeting)
        except:
            meeting, meetingU, meetingData, meeting_is_new = get_model_and_update('Meeting', meeting_type='Debate', GovPage=link, DateTime=date_time, Title=Title, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
            meeting, meetingU, meetingData, meeting_is_new, shareData = save_and_return(meeting, meetingU, meetingData, meeting_is_new, shareData, func)
        if 'Terms' in meetingData:
            meeting_terms = json.loads(meetingData['Terms'])
        else:
            meeting_terms = {}
        
        def get_text(nexth1, title_text, date_time, meeting_terms, num, shareData):
            prntDebug('get text')
            try:
                while nexth1.name == "h2" or nexth1.name == "p" or nexth1.name == 'blockquote' or nexth1.name == 'center' or nexth1.name == 'div':  
                    if nexth1.name == 'h2':
                        prntDebug()
                        prntDebug()
                        prntDebug(nexth1.text)
                        subtext = '%s' %(nexth1.text.strip())
                        next_div = nexth1.find_next_sibling()
                        # prntDebug(next_div.name)
                        statement = None
                        s_terms = []
                        senators = {}
                        blockquote = None
                        while next_div.name == "p" or next_div.name == 'blockquote':
                            # prntDebug(next_div.text)
                            # prntDebug('p')
                            try:
                                date_time = datetime.datetime.strptime(date_time.strftime('%Y-%m-%d') + '-' + next_div.text, '%Y-%m-%d-(%H%M)').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
                                prntDebug(date_time)
                            except Exception as e:
                                # prntDebug(str(e))
                                person = None
                                # statement = None
                                if next_div.name == 'p':
                                    try:
                                        bold = next_div.find('b')
                                        # prntDebug(bold.text)
                                        if 'Hon' in bold.text:
                                            prntDebug('---a')
                                            # prntDebug(bold.text)
                                            if statement:
                                                statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData, func)
                                                for term in s_terms:
                                                    statement = statement.add_term(term[0], term[1])
                                                    if not term[0] in meeting_terms:
                                                        meeting_terms[term[0]] = 1
                                                    else:
                                                        meeting_terms[term[0]] += 1
                                                s_terms = []
                                                for k in statement.keyword_array:
                                                    if not k in meeting_terms:
                                                        meeting_terms[k] = 1
                                                    else:
                                                        meeting_terms[k] += 1
                                            # prntDebug(str(next_div.text)[:50])
                                            a = None
                                            a = bold.text.find('(')
                                            name = bold.text[:a].replace('Hon. ', '').replace(':', '').replace('The', '').replace('the','')
                                            # prntDebug(name)
                                            if 'Speaker pro tempore' in name:
                                                name = 'Speaker pro tempore'
                                                last_name = name
                                                get_name_by = 'title'
                                            elif 'Speaker' in name:
                                                name = 'Speaker'
                                                last_name = name
                                                get_name_by = 'title'
                                            elif 'Senators' in name:
                                                name = name
                                                last_name = name
                                                get_name_by = 'None'
                                            else:
                                                name_split = name.split()
                                                first_name = name_split[0]
                                                last_name = name_split[-1]
                                                get_name_by = 'name'
                                            # prntDebug(name)
                                            if get_name_by == 'name':
                                                # person, personU, personData, person_is_new = get_model_and_update('Person', FirstName=first_name, LastName=last_name, Country_obj=country, Region_obj=country, chamber=chamber)
                                                try:
                                                    person = Person.objects.filter(Q(FirstName__icontains=first_name)&Q(LastName__icontains=last_name, Country_obj=country, Region_obj=country, chamber='Senate'))[0]
                                                except Exception as e:
                                                    # prntDebug(str(e))
                                                    person = None
                                            elif get_name_by == 'title':
                                                try:
                                                    # role, roleU, roleData, role_is_new = get_model_and_update('Role', Person_obj=person, Position='Senator', gov_level='Federal', Country_obj=country, Region_obj=country, chamber=chamber)
                                                    roleU = Update.objects.filter(Role_obj__Position='Senator', Role_obj__Title=name, data__icontains='"Current": true', Role_obj__gov_level='Federal', Country_obj=country)[0]
                                                    # role = Role.objects.filter(position='Senator', current=True, title=name)
                                                    person = roleU.Role_obj.Person_obj
                                                except Exception as e:
                                                    # prntDebug(str(e))
                                                    person = None
                                            else:
                                                person = None
                                            # prntDebug(name)
                                            # prntDebug(person)
                                            # try:
                                            #     if person:
                                            #         s = Statement.objects.filter(Person_obj=person, Meeting_obj=meeting, Content__icontains=str(next_div))[0]
                                            #         # prntDebug('found1')
                                            #     else:    
                                            #         s = Statement.objects.filter(Meeting_obj=meeting, Content__icontains=str(next_div))[0]
                                            #     # h.Content = ''
                                            #     statement, statementU, statementData, statement_is_new = get_model_and_update('Statement', obj=s)
                                            # except Exception as e:
                                                # prntDebug(str(e))
                                            # s = Statement(Meeting_obj=meeting, DateTime=date_time, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
                                            
                                            # s.save(share=False)
                                            statement, statementU, statementData, statement_is_new = get_model_and_update('Statement', new_model=True, Meeting_obj=meeting, DateTime=date_time, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
                                            # prntDebug('statement created')
                                            # prntDebug('statement_is_new', statement_is_new)
                                            # time.sleep(1)
                                            if person:
                                                statement.Person_obj = person
                                                # H.people.add(person)
                                                statement.PersonName = 'Hon. %s' %(person.FullName)
                                            else:
                                                statement.PersonName = name
                                            # prntDebug(h.id)
                                            # time.sleep(1)
                                            # h.hansardId = H.id
                                            senators[last_name] = person
                                            statement.Content = statement.Content + '\n' + str(next_div)
                                            string =  re.sub('<[^<]+?>', '', statement.Content)
                                            words = re.findall(r'\w+', string)
                                            statement.word_count = len(words)
                                            # if title_text and title_text != '':
                                            #     if not title_text in meeting_terms:
                                            #         meeting_terms[title_text] = 1
                                            #     else:
                                            #         meeting_terms[title_text] += 1
                                            #     # prntDebug(title_text)
                                            if subtext and subtext != '':
                                            #     if not subtext in meeting_terms:
                                            #         meeting_terms[subtext] = 1
                                            #     else:
                                            #         meeting_terms[subtext] += 1
                                                # prntDebug(subtext)
                                                if subtext[-4:] == 'Bill' or subtext[:7] == 'Bill to':
                                                    try:
                                                        b = subtext.replace(' Bill','').replace('Bill to ','').replace("’", "'")
                                                        # prntDebug(b)
                                                        bill = Bill.objects.filter(Government_obj=gov, Country_obj=country).filter(Q(LongTitle__icontains=b)|Q(Title__icontains=b)).filter(Q(chamber='Senate')|Q(chamber='House'))[0]
                                                        prntDebug(bill)
                                                        bill, billU, billData, bill_is_new = get_model_and_update('Bill', obj=bill)
                                                        LatestBillEventDateTime = datetime.datetime.fromisoformat(billData['LatestBillEventDateTime'])
                                                        if meeting.DateTime > LatestBillEventDateTime:
                                                            billData['LatestBillEventDateTime'] = datetime.datetime.isoformat(meeting.DateTime)
                                                            bill, billU, billData, bill_is_new, shareData = save_and_return(bill, billU, billData, bill_is_new, shareData, func)
                                
                                                        # if date_time:
                                                        #     try:
                                                        #         agendaTime = AgendaTime.objects.filter(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)[0]
                                                        #         input_time = False
                                                        #     except:
                                                        #         agendaTime = AgendaTime(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)
                                                        #         input_time = True
                                                        #         agendaTime.save()
                                                        #     # prntDebug(agendaTime)
                                                        # else:
                                                        #     agendaTime = None
                                                        # try:
                                                        #     agendaItem = AgendaItem.objects.filter(agenda=A, text=b)[0]
                                                        # except Exception as e:
                                                        #     # prntDebug(str(e))
                                                        #     agendaItem = AgendaItem(agenda=A, position=num, agendaTime=agendaTime, gov_level=A.gov_level, organization=A.organization)
                                                        #     agendaItem.text = b
                                                        #     if input_time:
                                                        #         agendaItem.date_time = date_time
                                                        # agendaItem.bill = bill
                                                        # agendaItem.save()
                                                        # prntDebug(agendaItem)
                                                        # agendaItem.agenda.bills.add(bill)
                                                        # agendaItem.agenda.save()
                                                        # h.save()
                                                        # h.add_term(subtext, bill)
                                                        # statement = statement.add_term(subtext, bill)
                                                        s_terms.append([subtext, bill])
                                                        # sozed.alert('%s-STEP TWO' %(bill.NumberCode), None)
                                                        # try:
                                                        #     bill.LatestBillEventDateTime = date_time
                                                        #     # prntDebug(bill.LatestBillEventDateTime)
                                                        #     bill.save()
                                                        #     bill.update_post_time()
                                                        # except Exception as e:
                                                        #     prntDebug('FailGetBIll-%s' %(str(e)))
                                                    except Exception as e:
                                                        prntDebug(str(e))
                                                        prntDebug('Bill not found')
                                                        # statement = statement.add_term(subtext, None)
                                                        s_terms.append([subtext, None])

                                                else:
                                                    # statement = statement.add_term(subtext, None)
                                                    s_terms.append([subtext, None])

                                            statement.OrderOfBusiness = title_text
                                            if blockquote:
                                                statement.SubjectOfBusiness = blockquote
                                            else:
                                                statement.SubjectOfBusiness = subtext
                                            # try:
                                            if title_text and title_text != '' and title_text not in statement.Terms_array:
                                                # h.Terms.append(title_text)
                                                # statement = statement.add_term(title_text, None)
                                                s_terms.append([title_text, None])
                                            if subtext and subtext != '' and subtext not in statement.Terms_array:
                                                # h.Terms.append(subtext)
                                                # done higher up
                                                pass
                                            if blockquote and blockquote not in statement.Terms_array:
                                                # h.Terms.append(blockquote)
                                                # statement = statement.add_term(blockquote, None)
                                                s_terms.append([blockquote, None])
                                            # except Exception as e:
                                            #     # prntDebug(str(e))
                                            #     h.Terms = []
                                            #     if title_text and title_text != '' and title_text not in h.Terms:
                                            #         h.Terms.append(title_text)
                                            #     if subtext and subtext != '' and subtext not in h.Terms:
                                            #         h.Terms.append(subtext)
                                            #     if blockquote and blockquote not in h.Terms:
                                            #         h.Terms.append(blockquote)
                                            # h.save()
                                            # h.create_post()
                                            # statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData)
                                            # for k in statement.keyword_array:
                                            #     if not k in meeting_terms:
                                            #         meeting_terms[k] = 1
                                            #     else:
                                            #         meeting_terms[k] += 1
                                        elif 'Senator' in bold.text:
                                            prntDebug('senator')
                                            if statement:
                                                statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData, func)
                                                for term in s_terms:
                                                    statement = statement.add_term(term[0], term[1])
                                                    if not term[0] in meeting_terms:
                                                        meeting_terms[term[0]] = 1
                                                    else:
                                                        meeting_terms[term[0]] += 1
                                                s_terms = []
                                                for k in statement.keyword_array:
                                                    if not k in meeting_terms:
                                                        meeting_terms[k] = 1
                                                    else:
                                                        meeting_terms[k] += 1
                                            last_name = bold.text.replace('Senator ', '').replace(':','').replace(' ','')
                                            person = senators[last_name]
                                            # prntDebug(person)
                                            # prntDebug(str(next_div.text)[:50])
                                            # if get_name_by == 'name':
                                            #     # person, personU, personData, person_is_new = get_model_and_update('Person', FirstName=first_name, LastName=last_name, Country_obj=country, Region_obj=country, chamber=chamber)
                                            #     try:
                                            #         person = Person.objects.filter(Q(FirstName__icontains=first_name)&Q(LastName__icontains=last_name, Country_obj=country, Region_obj=country, chamber='Senate'))[0]
                                            #     except Exception as e:
                                            #         # prntDebug(str(e))
                                            #         person = None
                                            # elif get_name_by == 'title':
                                            #     try:
                                            #         # role, roleU, roleData, role_is_new = get_model_and_update('Role', Person_obj=person, Position='Senator', gov_level='Federal', Country_obj=country, Region_obj=country, chamber=chamber)
                                            #         roleU = Update.objects.filter(Role_obj__Position='Senator', Role_obj__Title=name, data__icontains='"Current": true', Role_obj__gov_level='Federal', Country_obj=country)[0]
                                            #         # role = Role.objects.filter(position='Senator', current=True, title=name)
                                            #         person = roleU.Role_obj.Person_obj
                                            #     except Exception as e:
                                            #         # prntDebug(str(e))
                                            #         person = None
                                            # else:
                                            #     person = None


                                            # try:
                                            #     if person:
                                            #         s = Statement.objects.filter(Person_obj=person, Meeting_obj=meeting, Content__icontains=str(next_div))[0]
                                            #         # prntDebug('found1')
                                            #     else:    
                                            #         s = Statement.objects.filter(Meeting_obj=meeting, Content__icontains=str(next_div))[0]
                                            #     # h.Content = ''
                                            #     statement, statementU, statementData, statement_is_new = get_model_and_update('Statement', obj=s)
                                            # except Exception as e:
                                            #     # prntDebug(str(e))
                                            # s = Statement(Meeting_obj=meeting, DateTime=date_time, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
                                            
                                            # s.save(share=False)
                                            statement, statementU, statementData, statement_is_new = get_model_and_update('Statement', new_model=True, Meeting_obj=meeting, DateTime=date_time, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
                                            # prntDebug('h created')
                                            # prntDebug('statement created22')
                                            # prntDebug('statement_is_new', statement_is_new)
                                            # time.sleep(1)
                                            # s_terms = []
                                            if person:
                                                statement.Person_obj = person
                                                # H.people.add(person)
                                                statement.PersonName = 'Hon. %s' %(person.FullName)
                                            else:
                                                statement.PersonName = 'Senator %s' %(last_name)


                                            # try:
                                            #     if person:
                                            #         # prntDebug(person)
                                            #         h = HansardItem.objects.filter(person=person, hansard=H, Content__icontains=str(next_div))[0]
                                            #     else:
                                            #         h = HansardItem.objects.filter(hansard=H, Content__icontains=str(next_div))[0]
                                            #     # prntDebug('senator h found')
                                            #     h.Content = ''
                                            # except Exception as e:
                                            #     # prntDebug('senexcept11', str(e))
                                            #     h = HansardItem(person=person, hansard=H)
                                            #     if person:
                                            #         h.person = person
                                            #         h.person_name = 'Hon. %s' %(person.get_name())
                                            #         H.people.add(person)
                                            #     else:
                                            #         h.person_name = 'Hon. %s' %(person)
                                            statement.Content = statement.Content + '\n' + str(next_div)
                                            string =  re.sub('<[^<]+?>', '', statement.Content)
                                            words = re.findall(r'\w+', string)
                                            statement.word_count = len(words)
                                            # if title_text and title_text != '':
                                            #     if not title_text in meeting_terms:
                                            #         meeting_terms[title_text] = 1
                                            #     else:
                                            #         meeting_terms[title_text] += 1
                                            # if subtext and subtext != '':
                                            #     if not subtext in meeting_terms:
                                            #         meeting_terms[subtext] = 1
                                            #     else:
                                            #         meeting_terms[subtext] += 1
                                            statement.OrderOfBusiness = title_text
                                            if blockquote:
                                                statement.SubjectOfBusiness = blockquote
                                            else:
                                                statement.SubjectOfBusiness = subtext
                                            if not statement.Terms_array: 
                                                statement.Terms_array = []
                                            # try:
                                            if title_text and title_text != '' and title_text not in statement.Terms_array:
                                                # h.Terms.append(title_text)
                                                # statement = statement.add_term(title_text, None)
                                                s_terms.append([title_text, None])
                                            if subtext and subtext != '' and subtext not in statement.Terms_array:
                                                # h.Terms.append(subtext)
                                                # statement = statement.add_term(subtext, None)
                                                s_terms.append([subtext, None])
                                            if blockquote and blockquote not in statement.Terms_array:
                                                # h.Terms.append(blockquote)
                                                # statement = statement.add_term(blockquote, None)
                                                s_terms.append([blockquote, None])
                                            # except Exception as e:
                                            #     # prntDebug(str(e))
                                            #     h.Terms = []
                                            #     if title_text and title_text != '' and title_text not in h.Terms:
                                            #         h.Terms.append(title_text)
                                            #     if subtext and subtext != '' and subtext not in h.Terms:
                                            #         h.Terms.append(subtext)
                                            #     if blockquote and blockquote not in h.Terms:
                                            #         h.Terms.append(blockquote)
                                            # h.save()
                                            # h.create_post()
                                            # prntDebug('sen saved', h.id)
                                            # statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData)
                                            # for k in statement.keyword_array:
                                            #     if not k in meeting_terms:
                                            #         meeting_terms[k] = 1
                                            #     else:
                                            #         meeting_terms[k] += 1
                                    except Exception as e:
                                        # prntDebug('exception 1111', str(e))
                                        # prntDebug(str(next_div.text)[:50])
                                        try:
                                            statement.Content = statement.Content + '\n' + str(next_div)
                                            string =  re.sub('<[^<]+?>', '', statement.Content)
                                            words = re.findall(r'\w+', string)
                                            statement.word_count = len(words)
                                            # h.save()
                                            # prntDebug('saved')
                                            # statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData)
                                            # for k in statement.keyword_array:
                                            #     if not k in meeting_terms:
                                            #         meeting_terms[k] = 1
                                            #     else:
                                            #         meeting_terms[k] += 1
                                        except Exception as e:
                                            prntDebug('22222',str(e))
                                            # prntDebug(str(next_div.text)[:50])
                                            # time.sleep(5)
                                            # if person not senator
                                            if not statement:
                                            # try:
                                            #     s = Statement.objects.filter(Meeting_obj=meeting, Content__icontains=next_div)[0]
                                            # except Exception as e:
                                                # prntDebug(str(e))
                                                # s = Statement(Meeting_obj=meeting, DateTime=date_time, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
                                                statement, statementU, statementData, statement_is_new = get_model_and_update('Statement', new_model=True, Meeting_obj=meeting, DateTime=date_time, chamber='Senate', Government_obj=gov, Country_obj=country, Region_obj=country)
                                                # h = HansardItem(hansard=H)
                                                prntDebug('item created')
                                            statement.PersonName = None
                                            statement.Content = statement.Content + '\n' + str(next_div)
                                            string =  re.sub('<[^<]+?>', '', statement.Content)
                                            words = re.findall(r'\w+', string)
                                            statement.word_count = len(words)
                                                # s.save(share=False)
                                                # h.create_post()
                                    
                                else:
                                    blockquote = next_div.text.strip()
                                    # prntDebug(blockquote)
                            next_div = next_div.find_next_sibling()
                        # prntDebug(senators)
                        # prntDebug('----')
                        
                        # prntDebug('passed while P')
                        if statement:
                            statement, statementU, statementData, statement_is_new, shareData = save_and_return(statement, statementU, statementData, statement_is_new, shareData, func)
                            for term in s_terms:
                                statement = statement.add_term(term[0], term[1])
                                if not term[0] in meeting_terms:
                                    meeting_terms[term[0]] = 1
                                else:
                                    meeting_terms[term[0]] += 1
                            s_terms = []
                            for k in statement.keyword_array:
                                if not k in meeting_terms:
                                    meeting_terms[k] = 1
                                else:
                                    meeting_terms[k] += 1
                            statement = None
                        time.sleep(5)
                    nexth1 = nexth1.find_next_sibling()
                    # prntDebug('next', nexth1)
            except Exception as e:
                prntDebug(str(e))
            # prntDebug('---done get text')
            return date_time, meeting_terms, shareData
        # H_terms = {}
        precursors = h3.find_all_next('h2')
        num = 0
        for precursor in precursors:
            num += 1
            if not precursor.find_previous_sibling() or precursor.find_previous_sibling().name == 'h1':
                prntDebug('-----------break----------')
                break
            else:
                nexth1 = precursor.find_next_sibling()
                # prntDebug(nexth1)
                title_text = precursor.text.strip()
                # prntDebug(title_text)
                date_time, meeting_terms, shareData = get_text(nexth1, title_text, date_time, meeting_terms, num, shareData)
        h1s = content.find_all('h1')
        if h1s:
            num = 0
            for h1 in h1s:
                # prntDebug('-----------------')
                num += 1
                prntDebug(h1.text, '-----------', num)
                prntDebug('date', date_time)
                nexth1 = h1.find_next_sibling()
                title_text = h1.text.strip()
                # if date_time:
                #     try:
                #         agendaTime = AgendaTime.objects.filter(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)[0]
                #         input_time = False
                #     except:
                #         agendaTime = AgendaTime(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)
                #         input_time = True
                #         agendaTime.save()
                #     prntDebug(agendaTime)
                # else:
                #     agendaTime = None
                # try:
                #     agendaItem = AgendaItem.objects.filter(agenda=A, agendaTime=agendaTime, text=title_text)[0]
                # except Exception as e:
                #     # prntDebug(str(e))
                #     agendaItem = AgendaItem(agenda=A, position=num, agendaTime=agendaTime, gov_level=A.gov_level, organization=A.organization)
                #     agendaItem.text = title_text
                #     if input_time:
                #         agendaItem.date_time = date_time
                # agendaItem.position = num
                # agendaItem.save()
                # prntDebug(agendaItem, '----------', agendaItem.position)
                # H_terms[title_text] = 1
                date_time, meeting_terms, shareData = get_text(nexth1, title_text, date_time, meeting_terms, num, shareData)
        else:
            num = 0
            h2s = content.find_all('h2')
            for h2 in h2s:
                num += 1
                try:
                    # prntDebug(h2)
                    prntDebug('----------',h2.text)
                    title_text = h2.text.strip()
                    # try:
                    #     agendaItem = AgendaItem.objects.filter(agenda=A, agendaTime=agendaTime, text=title_text)[0]
                    # except Exception as e:
                    #     # prntDebug(str(e))
                    #     agendaItem = AgendaItem(agenda=A, position=num, agendaTime=agendaTime, gov_level=A.gov_level, organization=A.organization)
                    #     agendaItem.text = title_text
                    #     # if input_time:
                    #     #     agendaItem.date_time = date_time
                    #     agendaItem.save()
                    # prntDebug(agendaItem)
                    date_time, meeting_terms, shareData = get_text(h2, title_text, date_time, meeting_terms, num, shareData)
                    prntDebug('break')
                    break
                except Exception as e:
                    prntDebug('!!!!!!!!!!!!!!!!!!', str(e))
        # prntDebug('done all get text')
        # H.has_transcript = True
        # H.apply_terms(H_terms)
        meetingData['has_transcript'] = True
        meetingData = meeting.apply_terms(meeting_terms, meetingData)

        people = Statement.objects.filter(Meeting_obj=meeting)
        # prntDebug('people', people)
        # people = HansardItem.objects.filter(hansard=H)
        H_people = {}
        for p in people:
            try:
                if not p.Person_obj.id in H_people:
                    H_people[p.Person_obj.id] = 1
                else:
                    H_people[p.Person_obj.id] += 1
            except:
                pass
        H_people = sorted(H_people.items(), key=operator.itemgetter(1),reverse=True)
        H_people = dict(H_people)
        meetingData['People_json'] = json.dumps(H_people)
        # H.peopleText = json.dumps(H_people)
        # H.save()
        meetingData['completed_model'] = True
        meeting, meetingU, meetingData, meeting_is_new, shareData = save_and_return(meeting, meetingU, meetingData, meeting_is_new, shareData, func)
    return shareData, gov
        # sprenderize(H)

def add_senate_motion(tr, shareData, func):
    # num = 1
    country = Region.objects.filter(modelType='country', Name='Canada')[0]
    # gov, govU, govData, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=ParliamentNumber, SessionNumber=SessionNumber, Region_obj=country)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal', Region_obj=country)[0]
    td = tr.find_all('td')
    dt = td[0]['data-order']
    # prntDebug(dt)
    date_time = datetime.datetime.strptime(dt[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
    # prntDebug(date_time)
    link = 'https://sencanada.ca' + td[1].find('a')['href']
    # prntDebug(link)
    # 'https://sencanada.ca/en/in-the-chamber/votes/details/593588/44-1'
    a = link.find('/details/')+len('/details/')
    b = link[a:].find('/')
    motion_iden = link[a:a+b]
    text = td[1]['data-order']
    prntDebug(text)
    # prntDebug('')
    try:
        bill_link = td[2].find('a')['href']
        prntDebug(bill_link)
    except Exception as e:
        prntDebug(str(e))
        # prntDebug('no bill')
    # prntDebug('')
    try: 
        motion, motionU, motionData, motion_is_new = get_model_and_update('Motion', GovUrl=link, Country_obj=country, Government_obj=gov, Region_obj=country)
        # m = Motion.objects.filter(gov_url=link)[0]
        prntDebug('motion found')
        if motion_is_new or motionData['TotalVotes'] == 0:
            prntDebug('rerunning')
            fail
        return None, shareData
    except:
        try:
            billId = bill_link[bill_link.find('billId=')+len('billId='):]
            bill = Bill.objects.filter(GovIden=billId, Government_obj=gov, Country_obj=country, Region_obj=country)[0]
        except Exception as e:
            prntDebug(str(e))
            bill = None
        # m = Motion(gov_url=link, date_time=date_time, bill=bill)
        motion.DateTime = date_time
        if bill:
            motion.Bill_obj = bill
            motion.billCode = bill.NumberCode
        # m.ParliamentNumber = 44
        # m.SessionNumber = 1
        motion.chamber = 'Senate'
        motion.VoteNumber = motion_iden
        # if bill:
        motion.Subject = text
        # prntDebug(text)
        # m.save()
        # m.create_post()
        r = requests.get(motion.GovUrl)
        soup = BeautifulSoup(r.content, 'html.parser')
        # prntDebug(soup)
        div = soup.find('div', {'class':'sc-vote-details-summary-table'})
        col = div.find_all('div', {'class':'sc-vote-details-summary-table-col'})
        yeas = col[0].find_all('div', {'class':'sc-vote-details-summary-table-col-cell'})[1].text
        # prntDebug(yeas)
        motion.Yeas = int(yeas)
        nays = col[1].find_all('div', {'class':'sc-vote-details-summary-table-col-cell'})[1].text
        # prntDebug(nays)
        motion.Nays = int(nays)
        abs = col[2].find_all('div', {'class':'sc-vote-details-summary-table-col-cell'})[1].text
        # prntDebug(abs)
        motion.Absentations = int(abs)
        totals = col[3].find_all('div', {'class':'sc-vote-details-summary-table-col-cell'})[1].text
        # prntDebug(totals)
        motion.TotalVotes = int(totals)
        result = col[4].find_all('div', {'class':'sc-vote-details-summary-table-col-cell-tall'})[0].text
        # prntDebug(result)
        motion.Result = result
        # prntDebug('')
        # m.save()
        motion, motionU, motionData, motion_is_new, shareData = save_and_return(motion, motionU, motionData, motion_is_new, shareData, func)

        table = soup.find('div',{'class':'table-responsive'})
        tbody = table.find('tbody')
        trs = tbody.find_all('tr')
        vote_count = 0
        for tr in trs:
            vote_count += 1
            td = tr.find_all('td')
            a = td[0].find('a')
            person_link = a['href']
            # person_name_unstripped = a.text
            person_name = a.text.strip()
            prntDebug(person_name)
            a = person_name.find(', ')
            last_name = person_name[:a]
            first_name = person_name[a+2:]
            a = person_link.find('/senator/')+len('/senator/')
            b = person_link[a:].find('/')
            iden = person_link[a:a+b]
            # prntDebug(iden)

            
            try:
                # person, personU, personData, person_is_new = get_model_and_update('Person', )
                person = Person.objects.filter(GovIden=iden)[0]
                # v.person = p
            except Exception as e:
                # prntDebug(str(e))
                try:
                    roleUpdate = Update.objects.filter(Role_obj__Position='Senator', Role_obj__Person_obj__FirstName__icontains=first_name, Role_obj__Person_obj__LastName__icontains=last_name, data__icontains='"Current": true')[0]
                    # r = Role.objects.filter(Position='Senator', Person_obj__FirstName__icontains=first_name, Person_obj__LastName__icontains=last_name)[0]
                    person, personU, personData, person_is_new = get_model_and_update('Person', obj=roleUpdate.Role_obj.Person_obj)
                    if not person.GovIden:
                        person.GovIden = iden
                        personData['GovIden'] = iden
                        person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)

                except Exception as e:
                    prntDebug(str(e))
                    person, personU, personData, person_is_new = get_model_and_update('Person', FirstName=first_name, LastName=last_name, Country_obj=country, Region_obj=country)
                    person, personU, personData, person_is_new, shareData = save_and_return(person, personU, personData, person_is_new, shareData, func)



            vote, voteU, voteData, vote_is_new = get_model_and_update('Vote', Motion_obj=motion, Person_obj=person, Country_obj=country, Government_obj=gov, Region_obj=country)
            
            
            # try:
            #     v = Vote.objects.filter(motion=m, PersonOfficialFullName=person_name)[0]
            #     # v.PersonOfficialFullName = person_name
            # except:
            #     v = Vote(motion=m, PersonOfficialFullName=person_name)
            #     try:
            #         p = Person.objects.filter(gov_iden=iden)[0]
            #         v.person = p
            #     except Exception as e:
            #         prntDebug(str(e))
            #         try:
            #             r = Role.objects.filter(position='Senator', person__first_name__icontains=first_name, person__last_name__icontains=last_name)[0]
            #             if not r.person.gov_iden:
            #                 r.person.gov_iden = iden
            #                 r.person.save()
            #             v.person = r.person
            #         except Exception as e:
            #             prntDebug(str(e))
            if td[3]['data-order'] == 'aaa':
                # prntDebug('yea')
                vote.IsVoteYea = 'True'
                vote.VoteValueName = 'Yea'
            if td[4]['data-order'] == 'aaa':
                # prntDebug('nay')
                vote.IsVoteNay = 'True'
                vote.VoteValueName = 'Nay'
            if td[5]['data-order'] == 'aaa':
                # prntDebug('absentation')
                vote.IsVoteAbsentation = 'True'
                vote.VoteValueName = 'Absentation'
            # v.save() 
            vote.DateTime = date_time
            if person and bill:
                try:
                    post = Post.objects.filter(Bill_obj=bill)[0]
                    interaction, interactionU, interactionData, interaction_is_new = get_model_and_update('Interaction', Person_obj=person, Post_obj=post)
                    interaction, interactionU, interactionData, interaction_is_new, shareData = save_and_return(interaction, interactionU, interactionData, interaction_is_new, shareData, func)
                    prntDebug('done interaction')
                    # if interaction_is_new:
                    #     interaction.calculate_vote(VoteValueName, True)
                    # else:
                    #     interaction.calculate_vote(VoteValueName, False)
                    # try:
                    #     reaction = Reaction.objects.filter(Post_obj=post, Person_obj=person)[0]
                    #     reaction.calculate_vote(v.VoteValueName, True)
                    # except:
                    #     reaction = Reaction(post=post, person=v.person)
                    #     reaction.save()
                    #     reaction.calculate_vote(v.VoteValueName, False)
                except Exception as e:
                    prntDebug(str(e))
                    pass   
            vote, voteU, voteData, vote_is_new, shareData = save_and_return(vote, voteU, voteData, vote_is_new, shareData, func)
            
        time.sleep(2)
    motion.TotalVotes = vote_count
    motionData['TotalVotes'] = vote_count
    motion, motionU, motionData, motion_is_new, shareData = save_and_return(motion, motionU, motionData, motion_is_new, shareData, func)
    prntDebug('done')
    return gov, shareData

def get_senate_committee_transcript(committeeMeeting):
    prntDebug('--------getting transcript------------')
    prntDebug(committeeMeeting.transcriptURL)
    time.sleep(3)
    r = requests.get(committeeMeeting.transcriptURL)
    soup = BeautifulSoup(r.content, 'html.parser')
    ps = soup.find_all('p')
    speakers = {}
    # currentChair = None
    for p in ps:
        # prntDebug('-----------------')
        # prntDebug(p.text)
        # prntDebug(p['class'])
        samePerson = False
        try:
            if 'center' in p['class']:
                prntDebug('has center class')
        except:
            # prntDebug('log')
            bold = p.find('b')
            if bold:
                div = bold
                # prntDebug('----New speaker----')
                # prntDebug(bold)
                title = bold.text
                # if ', ' in bold.text and 'Hon.' in bold.text or ', ' in bold.text and 'Mr.' in bold.text or ', ' in bold.text and 'Mrs.' in bold.text or ', ' in bold.text and 'Ms.' in bold.text:
                # if ', ' in bold.text and len(bold.text) > 20:
                if ', ' in bold.text and bold.text[-1] == ':' and not '(' in bold.text and not '"' in bold.text or ', ' in bold.text and bold.text[-2] == ':'  and not '(' in bold.text and not '"' in bold.text:
                    # prntDebug('else')
                    text = bold.text.replace('Hon. ', '').replace('The Hon. ', '').replace('Mr. ', '').replace('Mrs. ', '').replace('Ms. ', '').replace('Hon.\xa0', '').replace('The Hon.\xa0', '').replace('Mr.\xa0', '').replace('Mrs.\xa0', '').replace('Ms.\xa0', '').replace(': ', '').strip()
                    a = text.find(',')
                    name = text[:a]
                    name = name.split()
                    prntDebug(name)
                    last_name = name[-1]
                    # prntDebug(last_name)
                    first_name = text[:a].replace(last_name, '').strip()
                    try:
                        person = Person.objects.filter(first_name__icontains=first_name, last_name=last_name)[0]
                    except:
                        prntDebug('creating person')
                        # time.sleep(2)
                        person = Person(first_name=first_name, last_name=last_name)
                        # p.Region_obj = 
                        person.save()
                        person.create_post()
                    # prntDebug(person)
                elif 'Deputy Chair' in bold.text:
                    prntDebug('dep')
                    name = bold.text.replace('Deputy Chair ', '').replace(':', '')
                    name = name.split()
                    prntDebug(name)
                    last_name = name[-1]
                    # first_name = bold.text.replace(last_name, '').strip()
                    if last_name in str(p.text).replace(str(bold.text), ''):
                        x = str(p.text).replace(str(bold.text), '').replace('Senator ','')
                        y = x.find(last_name)
                        z = x[:y].find('. ')+len('. ')
                        first_name = x[z:y].strip()
                    else:
                        first_name = name[0]
                    if '(Deputy Chair) in the chair' in p.text:
                        # prntDebug('tmp chair')
                        try:
                            r = Role.objects.filter(position='Senator', person__last_name__icontains=last_name)[0]
                            person = r.person
                            committeeMeeting.currentChair = person
                            committeeMeeting.save()
                        except:
                            try:
                                person = Person.objects.filter(first_name__icontains=first_name, last_name=last_name)[0]
                            except:
                                prntDebug('creating person')
                                person = Person(first_name=first_name, last_name=last_name)
                                # p.Region_obj = 
                                person.save()
                                person.create_post()            
                        # prntDebug('temp chair found')
                        # time.sleep(2)
                    else:
                        try:
                            r = Role.objects.filter(committee_key=committeeMeeting.committee, title='Deputy Chair')[0]
                            person = r.person
                            last_name = person.last_name
                        except:
                            try:
                                person = Person.objects.filter(first_name__icontains=first_name, last_name=last_name)[0]
                            except:
                                prntDebug('creating person')
                                person = Person(first_name=first_name, last_name=last_name)
                                # p.Region_obj = 
                                person.save()
                                person.create_post()
                            try:
                                r = Role.objects.filter(position='Senator', person=person)[0]
                            except:
                                r = Role(position='Senator', person=person, current=False)
                                # r.Region_obj =
                                r.save()

                    # prntDebug(person)
                elif 'The Chair' in bold.text:
                    prntDebug('chair')
                    # prntDebug(committeeMeeting.committee)
                    if committeeMeeting.currentChair:
                        person = committeeMeeting.currentChair
                    else:
                        # if last_name in str(p).replace(str(bold),''):
                        #     x = str(p).replace(str(bold), '')
                        #     y = x.find(last_name)
                        #     first_name = x[:y].strip()
                        # else:
                        #     first_name = name[0]
                        try:
                            r = Role.objects.filter(committee_key=committeeMeeting.committee, title='Chair')[0]
                            person = r.person
                        except:
                            try:
                                person = Person.objects.filter(first_name__icontains=first_name, last_name=last_name)[0]
                            except:
                                prntDebug('creating person')
                                person = Person(first_name=first_name, last_name=last_name)
                                # p.Region_obj = 
                                person.save()
                                person.create_post()
                            try:
                                r = Role.objects.filter(position='Senator', person=person)[0]
                            except:
                                r = Role(position='Senator', person=person, current=False)
                                # r.Region_obj =
                                r.save()
                    last_name = person.last_name
                    # prntDebug(person)
                elif 'Hon. Senators' in bold.text or 'An Hon. Senator' in bold.text:
                    # prntDebug('some senators')
                    samePerson = True
                    div = ''
                elif 'Senator' in bold.text:
                    # prntDebug('senator')
                    # prntDebug(p.text)
                    try:
                        name = bold.text.replace('Senator ', '').replace(':', '')
                        name = name.split()
                        # prntDebug(name)
                        last_name = name[-1]
                    except: #for errors in print
                        a = p.text.find(':')
                        name = p.text[:a].replace('Senator ', '')
                        name = name.split()
                        # prntDebug(name)
                        last_name = name[-1]
                    if last_name in str(p.text).replace(str(bold.text),''):
                        x = str(p.text).replace(str(bold.text), '').replace('Senator ','')
                        y = x.find(last_name)
                        z = x[:y].find('. ')+len('. ')
                        first_name = x[z:y].strip()
                    else:
                        first_name = name[0]
                    try:
                        r = Role.objects.filter(position='Senator', person__last_name__icontains=last_name)[0]
                        person = r.person
                        prntDebug(person)
                        if '(Chair) in the chair' in p.text:
                            # prntDebug('tmp chair')
                            committeeMeeting.currentChair = person
                            committeeMeeting.save()
                            # prntDebug('temp chair found')
                            # time.sleep(2)
                    except Exception as e:
                        try:
                            person = Person.objects.filter(first_name__icontains=first_name, last_name=last_name)[0]
                        except:
                            prntDebug('creating person')
                            prntDebug(first_name)
                            person = Person(first_name=first_name, last_name=last_name)
                            # p.Region_obj = 
                            person.save()
                            person.create_post()
                        try:
                            r = Role.objects.filter(position='Senator', person=person)[0]
                        except:
                            r = Role(position='Senator', person=person, current=False)
                            # r.Region_obj =
                            r.save()
                    if '(Chair) in the chair' in p.text:
                        # prntDebug('tmp chair')
                        committeeMeeting.currentChair = person
                        committeeMeeting.save()
                        # prntDebug('temp chair found')
                        # time.sleep(2)
                    # prntDebug(person)
                elif 'Mr.' in bold.text or 'Mrs.' in bold.text or 'Ms.' in bold.text:
                    prntDebug('Mr')
                    last_name = bold.text.replace('Mr. ', '').replace('Mrs. ', '').replace('Ms. ', '').replace('Mr.\xa0', '').replace('Mrs.\xa0', '').replace('Ms.\xa0', '').replace(': ', '').strip()
                    # prntDebug(last_name)
                    # prntDebug(speakers)
                    try:
                        person = speakers[last_name]
                        # prntDebug(person)
                    except Exception as e:
                        prntDebug(str(e))
                        # prntDebug(speakers)
                        name = last_name.split()
                        # prntDebug(name)
                        last_name = name[-1]
                        # prntDebug(last_name)
                        a = bold.text.find(last_name)
                        first_name = bold.text[:a].strip()
                        try:
                            person = Person.objects.filter(first_name__icontains=first_name, last_name=last_name)[0]
                        except:
                            prntDebug('creating person')
                            person = Person(first_name=first_name, last_name=last_name)
                            # p.Region_obj = 
                            person.save()
                            person.create_post()
                # elif ':' in bold.text and not 'Subject' in bold.text:
                #     prntDebug('unkown person')
                #     name = bold.text.replace(': ','')
                #     prntDebug(name)
                #     try:
                #         person = Person.objects.filter(last_name=name)[0]
                #     except:
                #         prntDebug('creating person')
                #         person = Person(last_name=name)
                #         person.save()
                    # person = None

                else:
                    # prntDebug('same')
                    samePerson = True
                    div = ''
                    # last_name = 'Unknown'
                # prntDebug(person)
                speakers[last_name] = person
                # prntDebug(speakers)
                # prntDebug('1')
                if not samePerson:
                    try:
                        # prntDebug('2')
                        content = str(p).replace(str(div), '')
                        c = CommitteeItem.objects.filter(committeeMeeting=committeeMeeting, person=person, Content__icontains=content)[0]
                        # prntDebug('cItem found')
                    except Exception as e:
                        # prntDebug(str(e))
                        # prntDebug('creating committeeItem')
                        if person:
                            c = CommitteeItem(committeeMeeting=committeeMeeting, person=person)
                        else:
                            c = CommitteeItem(committeeMeeting=committeeMeeting)
                        c.person_name = title.replace(': ','')
                        c.Content = ''
                        c.save()
            try: 
                # skip preamble with try/except
                if str(p).replace(str(div), '') not in c.Content:
                    try:
                        c.Content = c.Content + '\n' + str(p).replace(str(div), '')
                    except:
                        c.Content = str(p).replace(str(div), '')
                    committeeMeeting.people.add(person)
                    string =  re.sub('<[^<]+?>', '', c.Content)
                    words = re.findall(r'\w+', string)
                    c.wordCount = len(words)
                    c.meeting_title = committeeMeeting.Title
                    c.save() 
                    c.create_post()
                    # prntDebug('saved')
            except Exception as e:
                prntDebug(str(e))
    committeeMeeting.has_transcript = True
    prntDebug('has_transcript', committeeMeeting.has_transcript)
    people = CommitteeItem.objects.filter(committeeMeeting=committeeMeeting)
    C_people = {}
    for p in people:
        try:
            if not p.person.id in C_people:
                C_people[p.person.id] = 1
            else:
                C_people[p.person.id] += 1
        except Exception as e:
            prntDebug(str(e))
    C_people = sorted(C_people.items(), key=operator.itemgetter(1),reverse=True)
    C_people = dict(C_people)
    committeeMeeting.peopleText = json.dumps(C_people)
    committeeMeeting.save()
    prntDebug('comMeeting saved')
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()
    prntDebug('done')
    
def scrape_senate_committee_list(driver, session):
    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="table-print"]/div[1]'))
    WebDriverWait(driver, 10).until(element_present)

    table = driver.find_element(By.XPATH, '//*[@id="table-print"]/div[1]')
    tbody = table.find_element(By.CSS_SELECTOR, 'tbody')
    trs = tbody.find_elements(By.CSS_SELECTOR, 'tr')
    committees = {}
    com_transcript = {}
    # videos = {}
    x = session.find('-')
    parl = session[:x]
    sess = session[x+len('-'):]
    prntDebug(parl)
    prntDebug(sess)
    time.sleep(3)
    for tr in trs:
        bill = None
        # prntDebug(tr.get_attribute('innerHTML'))
        tds = tr.find_elements(By.CSS_SELECTOR, 'td')
        dt = tds[0].find_element(By.CSS_SELECTOR, 'a')
        prntDebug(dt.text)
        # prntDebug(dt.get_attribute('href'))
        try:
            
            date_time = datetime.datetime.strptime(dt.text, '%b %d, %Y\n%I:%M %p %Z')
        except:
            date_time = datetime.datetime.strptime(dt.text, '%b %d, %Y\n%I:%M %p local time')
        # prntDebug(d)
        com = tds[1].find_element(By.CSS_SELECTOR, 'a')
        prntDebug(com.text)
        prntDebug(com.get_attribute('href'))
        com_link = com.get_attribute('href')
        a = com_link.find('committees/') + len('committees/')
        b = com_link[a:].find('/')
        code = com_link[a:a+b]
        # prntDebug(code)
        prntDebug(code.upper())
        try:
            studies_a = tds[2].find_element(By.CSS_SELECTOR, 'ul')
            studies_b = studies_a.find_element(By.CSS_SELECTOR, 'li')
            text = studies_b.text
            if 'Bill' in text:
                a = text.find(', ')
                b = text[:a].replace('Bill ', '')
                try:
                    bill = Bill.objects.filter(NumberCode=b).filter(ParliamentNumber=parl, SessionNumber=sess).filter(Q(OriginatingChamberName='Senate')|Q(OriginatingChamberName__icontains='House'))[0]
                    prntDebug(bill)
                except:
                    pass
            studies_c = studies_b.find_elements(By.CSS_SELECTOR, 'ul')
            for c in studies_c:
                text = text.replace(c.text, '').strip()
            # prntDebug(text.strip())
        except:
            text = None
        # prntDebug('----')
        if '(Special Joint)' in com.text:
            org = '(Special Joint)'
        else:
            org = 'Senate'
        try:
            committee = Committee.objects.filter(code=code.upper(), Organization=org, ParliamentNumber=parl, SessionNumber=sess)[0]
        except:
            committee = Committee(code=code.upper(), Organization=org, Title=com.text, govURL=com.get_attribute('href'), ParliamentNumber=parl, SessionNumber=sess)
            committee.save()
            committee.create_post()
        try:
            # start_time = datetime.datetime.strftime(date_time, '%Y-%m-%-d')
            # end_time = datetime.datetime.strftime(date_time, '%Y-%m-%-d') + datetime.timedelta(days=1)
            comMeeting = CommitteeMeeting.objects.filter(committee=committee, govURL=dt.get_attribute('href'))[0]
            prntDebug('meeting found')
            if bill and not comMeeting.bill:
                comMeeting.bill = bill
                comMeeting.save()
            if not comMeeting.Title:
                comMeeting.Title = text
                comMeeting.save()
        except Exception as e:
            prntDebug(str(e))
            comMeeting = CommitteeMeeting(committee=committee, Organization=org, date_time_start=date_time, Title=text, govURL=dt.get_attribute('href'), ParliamentNumber=committee.ParliamentNumber, SessionNumber=committee.SessionNumber)
            if bill:
                comMeeting.bill = bill
            comMeeting.save()
            comMeeting.create_post()
        # prntDebug(tds[4].get_attribute('innerHTML'))
        links = tds[4].find_elements(By.CSS_SELECTOR, 'a')
        # prntDebug(len(links))
        for l in links:
            # prntDebug(l.get_attribute('title'))
            if 'Video' in l.get_attribute('title'):
                # prntDebug('video')
                # prntDebug(l.get_attribute('href'))
                # prntDebug(l.get_attribute('href') + '&viewMode=3')
                comMeeting.embedURL = l.get_attribute('href') + '&viewMode=3'
                comMeeting.embedURL = comMeeting.embedURL.replace('http', 'https').replace('XRender', 'Harmony')
                # videos[com.text] = l.get_attribute('href')
                if not comMeeting.timeRange:
                    try:
                        time.sleep(2)
                        r = requests.get(l.get_attribute('href'))
                        soup = BeautifulSoup(r.content, 'html.parser')
                        dt = soup.find('div', {'id':'scheduledtime'})
                        comMeeting.timeRange = dt.text
                    except:
                        pass
            if 'Transcripts' in l.get_attribute('title'):
                # prntDebug('transcripts')
                com_transcript[comMeeting] = l.get_attribute('href')
            if 'Interim' in l.get_attribute('title'):
                # prntDebug('interim')
                # prntDebug(l.get_attribute('href'))
                com_transcript[comMeeting] = l.get_attribute('href')
            if 'Audio' in l.get_attribute('title'):
                # prntDebug('audio')
                # prntDebug(l.get_attribute('href'))
                comMeeting.embedURL = l.get_attribute('href') + '&viewMode=3'
                try:
                    if not comMeeting.timeRange:
                        time.sleep(1)
                        r = requests.get(l.get_attribute('href'))
                        soup = BeautifulSoup(r.content, 'html.parser')
                        dt = soup.find('div', {'id':'scheduledtime'})
                        # prntDebug(dt.text)
                        comMeeting.timeRange = dt.text
                except Exception as e:
                    prntDebug(str(e))
            # else:
            #     prntDebug('none')
        comMeeting.save()
        # prntDebug(comMeeting.timeRange)
        # prntDebug(comMeeting.embedURL)
        committees[committee] = com.get_attribute('href')
        prntDebug('------------------------')
    

    prntDebug('getting members')
    starting_url = driver.current_url
    for key, value in committees.items():
        # prntDebug('getting members')
        # script = "window.open('" + value + "' ,'_blank');"
        # driver.execute_script(script)
        # windows = driver.window_handles
        # driver.switch_to.window(windows[1])
        try:
            if not key.chair and key.Organization != '(Special Joint)':
                prntDebug(key)
                prntDebug(value)
                driver.get(value)
                
                element_present = EC.presence_of_element_located((By.CLASS_NAME, 'sc-committee-members-dynamic-content-list'))
                WebDriverWait(driver, 4).until(element_present)
                content = driver.find_element(By.CLASS_NAME, 'sc-committee-members-dynamic-content-list')
                people = content.find_elements(By.CLASS_NAME, 'col-md-8')
                for p in people:
                    try:
                        h = p.find_element(By.CSS_SELECTOR, 'h3')
                        # prntDebug(h.text)
                        title = h.text
                    except:
                        # prntDebug('no position')
                        title = 'Member'
                    a = p.find_element(By.CSS_SELECTOR, 'a')
                    # prntDebug(a.get_attribute('href'))
                    # prntDebug(a.text)
                    try:
                        senator = Role.objects.filter(gov_page=a.get_attribute('href'))[0]
                        try:
                            r = Role.objects.filter(person=senator.person, committee_key=key)[0]
                            r.current = True
                            r.group = key.Title
                            r.save()
                        except:
                            r = Role(person=senator.person, committee_key=key, position='Committee Member', title=title, group=key.Title, current=True)
                            # r.Region_obj =
                            r.save()
                        key.members.add(r)
                        if title == 'Chair':
                            key.chair = r
                        key.save()
                    except Exception as e:
                        prntDebug(str(e))
                        # person = None
            
                    
                # time.sleep(3)
                # driver.close()
                # prntDebug('---------------')
                time.sleep(3)
            else:
                # prntDebug(key.chair.person)
                prntDebug('--')
        except Exception as e:
            prntDebug(str(e))
    if driver.current_url != starting_url:
        driver.get(starting_url)
    prntDebug('getting transcripts')
    for key, value in com_transcript.items():
        if key.has_transcript == False:
            prntDebug(key)
            prntDebug(key.date_time_start)
            key.transcriptURL = value
            # key.save()
            try:
                get_senate_committee_transcript(key)
            except Exception as e:
                prntDebug(str(e))
            time.sleep(2)
    driver.quit()
    prntDebug('done senate committee scrape')
        # break

# def get_upcoming_senate_committees():
#     get_senate_committees(upcoming='upcoming')

def get_senate_committees(upcoming='past'):
    prntDebug('---------------------senate committees ', upcoming)
    parl = Parliament.objects.filter(country='Canada', organization='Federal').first()
    session = '%s-%s' %(parl.ParliamentNumber, parl.SessionNumber)
    url = 'https://sencanada.ca/en/committees/allmeetings/#?TabSelected=%s&filterSession=%s&PageSize=50' %(upcoming, session)
    # url = 'https://sencanada.ca/en/committees/allmeetings/#?TabSelected=PAST&filterSession=44-1&PageSize=10&SortOrder=DATEDESC&p=11'
    prntDebug("opening browser")
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    driver.get(url)
    # prntDebug('received link')
    # time.sleep(5)
    # try:
    # except:
    #     pass
    scrape_senate_committee_list(driver, session)
    prntDebug('done senate committee list')
    driver.quit()
    # get all
    # s = session
    # run = True
    # while run:
    #     arrows = driver.find_elements(By.CLASS_NAME, 'sen-pagination-buttons-arrow')
    #     if arrows:
    #         for arrow in arrows:
    #             a = arrow.find_element(By.CSS_SELECTOR, 'a')
    #             # prntDebug(a.get_attribute('aria-label'))
    #             if a.get_attribute('aria-label') == 'Next':
    #                 link = a.get_attribute('href')
    #                 scrape_senate_committee_list(driver, s)
    #                 prntDebug('click')
    #                 # arrow.click()
    #                 driver.get(link)
    #                 run = True
    #             else:
    #                 scrape_senate_committee_list(driver, s)
    #                 run = False
    #         time.sleep(5)
    #     else:
    #         scrape_senate_committee_list(driver, s)
    #         run = False
    get_senate_committees(upcoming='upcoming')

def get_all_senate_committees():
    sessions = ['44-1', '43-2', '43-1', '42-1', '41-2', '41-1', '40-3', '40-2', '40-1', '39-2','39-1','38-1', '37-3','37-2','37-1','36-2','36-1','35-2','35-1']
    # sessions = ['40-3', '40-2', '40-1', '39-2','39-1','38-1', '37-3','37-2','37-1','36-2','36-1','35-2','35-1']
    
    # url = 'https://sencanada.ca/en/committees/allmeetings/#?TabSelected=PAST&filterSession=44-1&PageSize=10&SortOrder=DATEDESC&p=11'
    prntDebug("opening browser")
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    for s in sessions:
        url = 'https://sencanada.ca/en/committees/allmeetings/#?filterSession=%s&PageSize=50&SortOrder=DATEDESC&p=1' %(s)
        prntDebug(url, '------------------------------------------------------')
        driver.get(url)
        element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="table-print"]/div[1]'))
        WebDriverWait(driver, 10).until(element_present)
        # try:
        #     next = driver.find_element(By.CLASS_NAME, 'sen-pagination-buttons-arrow')
        # except:
        #     next = None
        run = True
        while run:
            prntDebug('waiting 10...')
            time.sleep(10)
            next = None
            arrows = driver.find_elements(By.CLASS_NAME, 'sen-pagination-buttons-arrow')
            if arrows:
                for arrow in arrows:
                    a = arrow.find_element(By.CSS_SELECTOR, 'a')
                    if a.get_attribute('aria-label') == 'Next':
                        next = a.get_attribute('href')
            prntDebug('start scrape')
            scrape_senate_committee_list(driver, s)
            if next:
                prntDebug(next, '--------next-----------------')
                driver.get(next)
                element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="table-print"]/div[1]'))
                WebDriverWait(driver, 10).until(element_present)
                prntDebug(driver.current_url)
            else:
                run = False



        # run = True
        # while run:
        #     arrows = driver.find_elements(By.CLASS_NAME, 'sen-pagination-buttons-arrow')
        #     if arrows:
        #         for arrow in arrows:
        #             a = arrow.find_element(By.CSS_SELECTOR, 'a')
        #             # prntDebug(a.get_attribute('aria-label'))
        #             if a.get_attribute('aria-label') == 'Next':
        #                 link = a.get_attribute('href')
        #                 scrape_senate_committee_list(driver, s)
        #                 prntDebug('click')
        #                 # arrow.click()
        #                 driver.get(link)
        #                 run = True
        #             else:
        #                 scrape_senate_committee_list(driver, s)
        #                 run = False
        #         time.sleep(5)
        #     else:
        #         scrape_senate_committee_list(driver, s)
        #         run = False
        #         # prntDebug('stop')
        prntDebug('----------next session')
    driver.quit()

def get_senate_committee_work(value='latest'):
    prntDebug('----------------------senate work')
    if value == 'alltime':
        pass
    else:
        url = 'https://sencanada.ca/en/committees/reports/'
    prntDebug("opening browser")
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    driver.get(url)
    element_present = EC.presence_of_element_located((By.CLASS_NAME, 'widget-committees-reports'))
    WebDriverWait(driver, 10).until(element_present)
    reports = driver.find_element(By.CLASS_NAME, 'widget-committees-reports')
    lis = reports.find_elements(By.CSS_SELECTOR, 'li')
    if value == 'latest':
        lis = lis[:20]
    for li in lis:
        a = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
        prntDebug(a)
        b = li.text.find('\n')
        c = li.text[b+len('\n'):].find('\n')
        activity = li.text[:b]
        # prntDebug('---')
        com = li.text[b+len('\n'):b+len('\n')+c].replace('The Standing Senate Committee on ', '').replace('The Standing Committee on ', '').replace('The Standing Joint Committee for ', '')
        prntDebug('-------', com)
        event = li.text[b+len('\n')+c+len('\n'):]
        d = event.find(' - ')
        eventTitle = event[:d]
        prntDebug(event)
        date = event[d+len(' - '):]
        # prntDebug(date)
        dt = datetime.datetime.strptime(date, '%B %Y')
        # prntDebug(dt)
        # prntDebug('')
        parl = Parliament.objects.filter(country='Canada', organization='Federal', start_date__lte=dt)[0]
        # prntDebug(parl)
        try:
            comMeeting = CommitteeMeeting.objects.filter(reportLink=a)[0]
            prntDebug('meeting found')
        except:
            try:
                prntDebug('creating meeting')
                com = Committee.objects.filter(Title__icontains=com, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
                comMeeting = CommitteeMeeting(Organization='Senate', committee=com, reportLink=a, Title=activity, event=eventTitle, date_time_start=dt, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)
                if 'Bill' in activity:
                    prntDebug('bill:')
                    x = activity.find('Bill')+len('Bill ')
                    if ',' in activity[x:]:
                        y = activity[x:].find(',')
                        z = activity[x:x+y]   
                    elif '-' in activity[x:]:
                        y = activity[x:].find('-')
                        if ' ' in activity[x+y:]:
                            w = activity[x+y:].find(' ')
                            z = activity[x+y-1:x+y+w]   
                        else:
                            z = activity[x+y-1:]   
                    # prntDebug(z)
                    bill = Bill.objects.filter(NumberCode=z, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
                    comMeeting.bill = bill
                    prntDebug(bill)
                time.sleep(2)
                r = requests.get(a)
                soup = BeautifulSoup(r.content, 'html.parser')
                containers = soup.find_all('div', {'class':'container'})
                for container in containers:
                    if 'Report of the committee' in container.text:
                        # h3 = container.find("h3", string="Report of the committee")
                        div = container.find('div')
                        first_p = div.find('p')
                        # prntDebug(p.text)
                        try:
                            dt = datetime.datetime.strptime(first_p.text, '%A, %B %d, %Y')
                        except:
                            dt = datetime.datetime.strptime(first_p.text, '%B %d, %Y')
                        comMeeting.date_time_start = dt
                        prntDebug(dt)
                        prntDebug('---------------------------------')
                        content = str(div).replace(str(first_p), '')
                        # prntDebug(content)
                        comMeeting.report = content
                comMeeting.save()
                comMeeting.create_post()
            except Exception as e:
                prntDebug(str(e))
                prntDebug('timeout 20s')
                # time.sleep(20)
    driver.quit()

def get_senate_agendas(value='latest'):
    prntDebug('-------------------senate agenda')
    parl = Parliament.objects.filter(country='Canada', organization='Federal')[0]
    dt = datetime.datetime.now()
    l = 'https://senparlvu.parl.gc.ca/Harmony/en/View/EventListView/%s%s%s/307' %(dt.year, dt.month, dt.day)
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    # caps["pageLoadStrategy"] = "eager"   # Do not wait for full page load
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    # prntDebug(self.parlinfo_link)
    driver.get(l)
    def action(driver):
        element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="divEventList"]/div[2]/div[1]'))
        WebDriverWait(driver, 10).until(element_present)
        # signIn = driver.find_element(By.XPATH, '//*[@id="right-content"]/a')
        # r = requests.get(l)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # prntDebug(soup)
        divs = soup.find_all('div', {'class':'divEvent'})
        for div in divs:
            a = div.find('a')
            prntDebug(a['href'])
            x = a['href'].rfind('/')+len('/')
            code = a['href'][x:]
            date = a.find('div', {'class':'eventDate'}).text
            prntDebug(date)
            '--Thu, Feb 9, 2023 --'
            time = a.find('div', {'class':'eventTime'}).text
            prntDebug(time)
            x = time.find('-')
            st = time[:x]
            et = time[x+len('-'):]
            start_time = datetime.datetime.strptime(date + '--' + st, '%a, %b %d, %Y --%I:%M %p')
            prntDebug(start_time)
            end_time = datetime.datetime.strptime(date + '--' + et, '%a, %b %d, %Y --%I:%M %p')
            prntDebug(end_time)
            vid = 'https://senparlvu.parl.gc.ca/Harmony/en/PowerBrowser/PowerBrowserV2/%s%s%s/-1/%s?viewMode=3&globalStreamId=16' %(start_time.year, start_time.month, start_time.day, code)
            # parl = Parliament.objects.filter(start_time__lte=start_time)[0]
            try:
                agenda = Agenda.objects.filter(organization='Senate', date_time=start_time)[0]
            except:
                agenda = Agenda(organization='Senate', gov_level='Federal', date_time=start_time)
                agenda.end_date_time = end_time
                agenda.VideoURL = vid
                agenda.videoCode = code
                agenda.save()
                agenda.create_post()
            try:
                H = Hansard.objects.filter(agenda=agenda)[0]
            except:
                H = Hansard(agenda=agenda, Publication_date_time=start_time, Organization='Senate')
                H.ParliamentNumber=parl.ParliamentNumber
                H.SessionNumber=parl.SessionNumber
                H.save()
                H.create_post() 

            prntDebug('')
        prntDebug('done page')
    run = True
    while run:
        action(driver)
        if value == 'session':
            try:
                time.sleep(3)
                next = driver.find_element(By.XPATH, '//*[@id="btnNext"]').click()
            except:
                run = False
        else:
            run = False
    driver.quit()
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()

def get_all_agendas():
    'https://www.ourcommons.ca/en/parliamentary-business/2001-01-29'
    # today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    start_date = '%s-%s-%s' %(2001, 1, 29)
    #rerun committee hansards from here
    # start_date = '%s-%s-%s' %(2020, 10, 15)
    start_date = '%s-%s-%s' %(2023, 3, 1)
    # start_date = '%s-%s-%s' %(2021, 7, 20)
    #run rest from here
    # start_date = '%s-%s-%s' %(2022, 4, 5)
    prntDebug(start_date)
    day = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    # prntDebug(isinstance(day, str))
    # prntDebug(day)
    plus_day = 1
    while day <= datetime.datetime.now():
        # prntDebug(day)
        # weekno = day.weekday()
        # prntDebug('day', weekno)
        # if weekno < 5:
        # prntDebug(isinstance(day, datetime))
        # prntDebug(isinstance(day, str))
        # prntDebug(isinstance(day, str))
        # year_date = dt + datetime.timedelta(days=plus_day)
        # year = year_date.year
        # prntDebug(year)
        # plus_day = 1
        # time.sleep(1)
        # u = 'https://www.ourcommons.ca/en/parliamentary-business/2022-12-12'


        day = datetime.datetime.strftime(day, '%Y-%m-%d')
        prntDebug(day)
        # url = 'https://www.ourcommons.ca/en/parliamentary-business/%s' %(day)
        # prntDebug('---------getting agenda')
        # prntDebug(url)
        # time.sleep(2)
        # try:
        #     A = Agenda.objects.filter(date_time=day, organization='House', gov_level='Federal')[0]
        #     prntDebug('agenda found')
        # except:
        #     prntDebug('agenda not found')
        # get_agenda(url)
        # prntDebug('')
        # prntDebug('-------getting debate hansard')
        # debate_url = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=from%sto%s&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=2000000&PubType=37&xml=1' %(day, day)
        # # debate_url = 'https://www.ourcommons.ca/PublicationSearch/en/?View=D&Item=&ParlSes=from2002-05-02to2002-05-02&oob=&Topic=&Proc=&Per=&Prov=&Cauc=&Text=&RPP=15&order=&targetLang=&SBS=0&MRR=2000000&PubType=37&xml=1'
        # prntDebug(debate_url)
        # time.sleep(2)
        # try:
        #     get_house_hansard_or_committee('hansard', debate_url)
        # except Exception as e:
        #     prntDebug('not found')
        #     prntDebug(str(e))
        # com_url = 'https://www.ourcommons.ca/Committees/en/Meetings?meetingDate=%s' %(day) 
        # prntDebug('----------getting house committee list')
        # prntDebug(com_url)
        # time.sleep(2)
        # get_house_committee_list(com_url)
        # time.sleep(2)
        han_url = 'https://www.ourcommons.ca/PublicationSearch/en/?PubType=40017&xml=1&parlses=from%sto%s' %(day, day)
        prntDebug('-----------getting committee hansard')
        prntDebug(han_url)
        try:
            get_house_hansard_or_committee('committee', han_url)
        except Exception as e:
            prntDebug('not found')
            prntDebug(str(e))
        # prntDebug('')
        prntDebug('-------------------------------------------------------------------')
        day = datetime.datetime.strptime(day, '%Y-%m-%d')
        day = datetime.datetime.strftime(day + datetime.timedelta(days=plus_day), '%Y-%m-%d')
        prntDebug('next', day)
        day = datetime.datetime.strptime(day, '%Y-%m-%d')
        
def get_federal_match(request, person):
    parl = Parliament.objects.filter(country='Canada', organization='Federal')[0]
    reactions = Reaction.objects.filter(user=request.user, post__post_type='bill').filter(post__bill__province=None).order_by('-post__date_time')
    votes = {}
    my_votes = {}
    return_votes = []
    vote_matches = 0
    total_matches = 0
    match_percentage = None
    for r in reactions:
        try:
            bill = r.post.bill
            if r.isYea:
                votes[bill] = 'Yea'
            elif r.isNay:
                votes[bill] = 'Nay'
            # prntDebug(r.isYea, r.isNay)
        except:
            pass
    matched = []
    def match_vote(m, person, votes, bill, vote_matches, total_matches, return_votes):
        try:
            v = Vote.objects.filter(motion=m, person=person).order_by('-motion__date_time')[0]
            total_matches += 1
            return_votes.append(v)
            if v.VoteValueName == votes[bill]:
                vote_matches += 1
                # prntDebug('match')
            return 'match', vote_matches, total_matches, return_votes
        except Exception as e:
            pass
        return 'nomatch', vote_matches, total_matches, return_votes
    for bill in votes:
        # prntDebug('------', bill)
        # prntDebug(billVersion)
        # prntDebug(votes[billVersion])
        try:
            motions = Motion.objects.filter(bill=bill, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber).order_by('-date_time')
            for m in motions:
                my_votes[m.id] = votes[bill]
                result, vote_matches, total_matches, return_votes = match_vote(m, person, votes, bill, vote_matches, total_matches, return_votes)
                if result == 'match':
                    matched.append(m)
                    break
        except Exception as e:
            prntDebug(str(e))
    # prntDebug(vote_matches, '/', total_matches)
    try:
        match_percentage = int((vote_matches / total_matches) * 100)
    except Exception as e:
        match_percentage = None
    # prntDebug(match_percentage)
    return match_percentage, total_matches, vote_matches, my_votes, return_votes
