


# from unittest.result import failfast
from django.db import models
from django.db.models import Q, Avg

import django_rq
from rq import Queue
from worker import conn

from accounts.models import UserData
from legis.models import Government,Agenda,BillText,Bill,Meeting,Statement,Motion,Vote,Election,Party,Person,District
from posts.models import Post, Update, GenericModel, Region
from posts.views import get_ordinal
# from posts.utils import sprenderize
from utils.models import *
# from utils.cronjobs import finishScript, create_share_object
from blockchain.models import logEvent, logError, return_test_result

# from firebase_admin.messaging import Notification as fireNotification
# from firebase_admin.messaging import Message as fireMessage
# from fcm_django.models import FCMDevice
import datetime
from dateutil.parser import parse
import requests
import feedparser
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import xmltodict
import pytz
import time
import re
import random
import string
import json
# import lxml
# from collections import OrderedDict
# from operator import itemgetter
import operator
import calendar
import wikipedia

from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

state_list = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DC': 'District of Columbia',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'HI': 'Hawaii',
    'IA': 'Iowa',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'MA': 'Massachusetts',
    'MD': 'Maryland',
    'ME': 'Maine',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MO': 'Missouri',
    'MS': 'Mississippi',
    'MT': 'Montana',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'NE': 'Nebraska',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NV': 'Nevada',
    'NY': 'New York',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VA': 'Virginia',
    'VT': 'Vermont',
    'WA': 'Washington',
    'WI': 'Wisconsin',
    'WV': 'West Virginia',
    'WY': 'Wyoming'
}

runTimes = {
    'initialize_region' : 2000,
    'get_bills' : 600, 'add_bill': 120, 
    'get_house_motions' : 600, 'add_house_motion': 300, 
    'get_senate_motions' : 600, 'add_senate_motion': 150, 
    'get_house_debates' : 1200, 'get_senate_debates' : 1200, 'add_official_debate_transcript': 420,
    'get_house_persons' : 500, 'get_senate_persons' : 300,
    'get_senate_committees' : 200, 
    'get_house_committees' : 1000, 'get_upcoming_senate_committees' : 200,
    'get_general_election_candidates' : 300, 'get_general_elections_results' : 200,
    }


typical = ['get_house_agendas', 'get_senate_agendas', 'get_todays_xml_agenda',
    'get_house_committees', 'get_senate_committees',
    ]

functions = {
    "2025-03-13" : [
    # {'date' : ['x'], 'dayOfWeek' : [6,2], 'hour' : [4], 'cmds' : ['get_house_persons', 'get_senate_persons', 'get_general_election_candidates']},
    # {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : ['x'], 'cmds' : ['get_bills'] },
    # {'date' : ['x'], 'dayOfWeek' : ['x'], 'hour' : [2,4,6,8,10,12,14,16,1,8,20,22,24], 'cmds' : ['get_house_debates', 'get_house_motions']},
    # {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [1,3,5,7,9,11,13,15,17,19,21,23], 'cmds' : ['get_senate_debates', 'get_senate_motions']},
    {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [2, 8, 10, 12, 14, 16, 18, 22], 'cmds' : ['get_bills'] },
    {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [1, 5, 17, 21], 'cmds' : ['get_house_debates', 'get_house_motions']},
    {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [3, 7, 19, 23], 'cmds' : ['get_senate_debates', 'get_senate_motions']},
    ],
    # "2024-12-21" : [
    # # first of the month
    # #  {'date' : [1], 'dayOfWeek' : ['x'], 'hour' : [2], 'cmds' : ['get_house_expenses']},
    # # saturday 2 am
    # {'date' : ['x'], 'dayOfWeek' : [6,2], 'hour' : [2], 'cmds' : ['get_house_persons', 'get_senate_persons', 'get_general_election_candidates']},
    # # mon - sat
    # #  {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [8, 10, 12, 18, 24], 'cmds' : typical },
    # {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [2, 8, 10, 12, 14, 16, 18, 22], 'cmds' : ['get_bills'] },
    # {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [2, 6, 18, 22], 'cmds' : ['get_house_debates', 'get_house_motions']},
    # {'date' : ['x'], 'dayOfWeek' : [0,1,2,3,4,5], 'hour' : [4, 8, 20, 24], 'cmds' : ['get_senate_debates', 'get_senate_motions']},
    # ],
}



approved_models = {
        # 'get_house_agendas' : ['Government', 'Agenda', 'AgendaTime', 'AgendaItem', 'Meeting'],
            'initialize_region' : ['Government', 'Person', 'Party', 'District', 'Region'],
            'get_house_persons' : ['Government', 'Person', 'Party', 'District', 'Region'],
            'get_senate_persons' : ['Person', 'Party', 'Region'],
            'get_bills' : ['Bill', 'BillText', 'Committee', 'Meeting', 'GenericModel', 'Government', 'Notification'],
            'get_house_debates' : ['Meeting', 'Statement', 'Agenda', 'Bill', 'BillText', 'GenericModel', 'Government', 'Committee', 'Notification'],
            'get_senate_debates' : ['Meeting', 'Statement', 'Agenda', 'Bill', 'BillText', 'GenericModel', 'Government', 'Committee', 'Notification'],
            'get_house_motions' : ['Government', 'Motion', 'Vote', 'Bill', 'BillText', 'Committee', 'Meeting', 'GenericModel', 'Notification'],
            'get_senate_motions' : ['Motion', 'Vote', 'Bill', 'BillText', 'Government', 'Committee', 'Meeting', 'GenericModel', 'Notification'],
            'get_general_election_candidates' : ['Election', 'Person', 'Party', 'Notification'],
            'get_general_elections_results' : ['Election', 'Person', 'Party', 'Notification'],
            'get_user_region' : ['District', 'Region', 'Party', 'Person'],
            }

def find_party(party_short=None, party_name=None):
    # prnt('find_party',party_short,party_name)
    party_list = {
        'Republican':{'short':'R','alt':None},
        'Democratic':{'short':'D','alt':'Democrat'},
        'Libertarian':{'short':'L','alt':None},
        'Independent':{'short':'I','alt':None},
        'Green':{'short':'G','alt':None},
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

gov_logo_links = {"House": "img/usa/house.svg.png", "Senate": "img/usa/senate.svg.png"}

# get_wiki = True
get_wiki = not testing()


def initialize_region(special=None, dt=now_utc(), iden=None):
    get_house_persons(special=special, iden=iden)
    get_senate_persons(special=special, iden=iden)
        

def get_house_persons(special=None, dt=now_utc(), iden=None):
    func = 'get_house_persons'
    gov = None
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')
    modded_country = None
    if not country.Office_array or 'Congressional Representative' not in country.Office_array:
        modded_country = country.propose_modification()
        modded_country.add_office('Congressional Representative')
        log.updateShare(modded_country)
    if not country.Chamber_array or 'House' not in country.Chamber_array:
        if not modded_country:
            modded_country = country.propose_modification()
        modded_country.add_chamber('House')
        log.updateShare(modded_country)
        
    starting_url = 'https://www.house.gov/representatives'

    new_members = []
    try:
        
        driver, driver_service = open_browser(starting_url)

        element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="by-state"]/div/div/div[2]'))
        WebDriverWait(driver, 10).until(element_present)
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
        '118th Congress, 2nd Session · '
        div = soup.find('div', {'id':'house-in-session'}).text
        a = div.find(' Congress, ')
        b = div[a+len(' Congress, '):].find(' Session')
        cong = div[:a]
        sess = div[a+len(' Congress, '):a+len(' Congress, ')+b]
        cong = cong.replace('st','').replace('nd','').replace('rd','').replace('th','')
        sess = sess.replace('st','').replace('nd','').replace('rd','').replace('th','')
        prnt(cong, sess)
        cong = int(cong)
        sess = int(sess)
        prnt(cong, sess)

        gov, govU, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', gov_type='Congress', GovernmentNumber=cong, SessionNumber=sess, Region_obj=country)
        if gov_is_new:
            from blockchain.models import round_time
            gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
            gov.migrate_data()
            gov.LogoLinks = gov_logo_links
            # prev = gov.end_previous(func)
            # if prev:
            #     log.updateShare(prev)
            gov, govU, gov_is_new, log = save_and_return(gov, govU, log)
        prnt('gov',gov)
        content = soup.find('div', {'class':'view-content'})
        tables = content.find_all('table', {'class':'table'})
        congressmen = []
        for table in tables:
            state_name = table.find('caption').text.strip()
            # prnt('------------------')
            # prnt(state_name)
            for key, value in state_list.items():
                if value == state_name:
                    AbbrName = key
                    # prnt(AbbrName)
                    break
            state = Region.valid_objects.filter(Name=state_name, AbbrName=AbbrName, nameType='State', modelType='provState', ParentRegion_obj=country).first()
            # if state:
            if not state:
                state = Region(func=func, Name=state_name, AbbrName=AbbrName, nameType='State', modelType='provState', ParentRegion_obj=country)
                # state.add_office('Congressional Representative')
                state.update_data()
                log.updateShare(state)

            tbody = table.find('tbody')
            trs = tbody.find_all('tr')
            for tr in trs:
                tds = tr.find_all('td')
                district_name = tds[0].text.replace('st','').replace('nd','').replace('rd','').replace('th','').strip()
                # if isinstance(district_name, int):
                try:
                    isint = int(district_name)
                    # prnt('isint')
                    district_name = 'District ' + district_name
                except:
                    # prnt('not int')
                    ...
                # prnt(district_name)

                district = District.objects.filter(Name=district_name, Country_obj=country, Region_obj=country, ProvState_obj=state, gov_level='Federal', nameType='Congressional District').first()
                if district:
                    if not district.Office_array or 'Congressional Representative' not in district.Office_array:
                        modded_district = district.propose_modification()
                        modded_district.add_office('Congressional Representative')
                        log.updateShare(modded_district)
                else:
                    district = District(func=func, Name=district_name, Country_obj=country, Region_obj=country, ProvState_obj=state, gov_level='Federal', nameType='Congressional District')
                    try:
                        dNum = get_ordinal(int(district_name))
                    except:
                        dNum = district_name
                    if get_wiki:
                        try:
                            time.sleep(1)
                            search_name = dNum + ' congressional district of ' + state_name
                            prnt('search_name',search_name)
                            title = wikipedia.search(search_name)[0].replace(' ', '_')
                            district.Wiki = 'https://en.wikipedia.org/wiki/' + title
                            prnt('district.Wiki',district.Wiki)
                            # district.update_data()
                        except Exception as e:
                            prnt(str(e))
                    district.add_office('Congressional Representative')
                    log.updateShare(district)

                representative = tds[1]
                x = representative.text.find(', ')
                z = representative.text[x+2:].find('(link is external)')
                first_name = representative.text[x+2:x+2+z].strip()
                last_name = representative.text[:x].strip()
                prnt(first_name, last_name)
                a = representative.find('a')
                website = a['href']
                # prnt(website)
                party_short = tds[2].text.strip()
                party_name, party_short, alt_name = find_party(party_short=party_short)

                party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=country, Region_obj=country, gov_level='Federal')
                if party_is_new:
                    if get_wiki:
                        try:
                            time.sleep(1)
                            search_name = party_name + ' american federal political party'
                            prnt(search_name)
                            link = wikipedia.search(search_name)[0].replace(' ', '_')
                            party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                            prnt('party.Wiki',party.Wiki)
                        except Exception as e:
                            prnt('party:',str(e))
                            pass
                    party, partyU, party_is_new, log = save_and_return(party, partyU, log)

                officeRoom = tds[3].text.strip()
                phone = tds[4].text.strip()
                try:
                    assignments = tds[5].text.strip()
                    # prnt(assignments)
                except:
                    assignments = None

                personUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__Websites__contains=[website], validated=True).first()
                if personUpdate:
                    person, personU, person_is_new = get_model_and_update('Person', id=personUpdate.pointerId, Country_obj=country, Region_obj=country)
                    if person_is_new:
                        m = {'first':first_name, 'last':last_name, 'website':website, 'party':party, 'state':state, 'district':district, 'officeRoom':officeRoom, 'phone':phone, 'assignments':assignments}
                        new_members.append(m)
                    personU.data['Chamber'] = 'House'
                    personU.data['District_id'] = district.id
                    personU.data['ProvState_id'] = state.id
                    personU.data['FirstName'] = first_name
                    personU.data['LastName'] = last_name
                    personU.data['FullName'] = first_name + ' ' + last_name
                    personU.data['Position'] = 'Congressional Representative'
                    personU.data['gov_level'] = 'Federal'
                    personU.data['Telephones'] = [phone]
                    personU.data['Party_id'] = party.id
                    person.update_role(personU, data={'role':'Congressional Representative','current':True, 'gov_level':'Federal', 'officeName':officeRoom})
                    if not person.GovIden:
                        prnt('no govIden')
                        m = {'first':first_name, 'last':last_name, 'website':website, 'party':party, 'state':state, 'district':district, 'officeRoom':officeRoom, 'phone':phone, 'assignments':assignments}
                        new_members.append(m)
                    if assignments:
                        for assignment in assignments.split('|'):
                            data = {'role':assignment, 'current':True, 'gov_level':'Federal', 'Chamber':'House', 'Government_id':gov.id}
                            person.update_role(personU, data=data)
                    person, personU, person_is_new, log = save_and_return(person, personU, log)
                    congressmen.append(person.id)
                else:
                    m = {'first':first_name, 'last':last_name, 'website':website, 'party':party, 'state':state, 'district':district, 'officeRoom':officeRoom, 'phone':phone, 'assignments':assignments}
                    new_members.append(m)
            # break

        if new_members:
            new_members = sorted(new_members, key=lambda item: item['last'].lower())

            prnt(len(new_members))
            prnt('^ new members')
            # url1 = f'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22chamber%22%3A%22House%22%2C%22congress%22%3A%22{}%22%7D'
            # url2 = f'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22chamber%22%3A%22House%22%2C%22congress%22%3A%22{}%22%7D'
            url = f'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22{gov.GovernmentNumber}%22%2C%22chamber%22%3A%22House%22%7D'
            prnt('url',url)

            url2 = f'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22{gov.GovernmentNumber}%22%2C%22chamber%22%3A%22House%22%7D&page=2'
            prnt('url2',url2)
            try:
                driver.get(url)
                prnt('loaded')
                element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
                WebDriverWait(driver, 10).until(element_present)
                prnt('ready1')

                soup1 = BeautifulSoup(driver.page_source, 'html.parser')

                driver.get(url2)
                prnt('loaded2')
                element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
                WebDriverWait(driver, 10).until(element_present)
                prnt('ready12')
                soup2 = BeautifulSoup(driver.page_source, 'html.parser')

            except Exception as e:
                prnt('fail957184',str(e))

            close_browser(driver, driver_service)

            def get_data(soup, log):
                main = soup.find('div', {'id':'main'})
                lis = main.find_all('li', {'class':'expanded'})
                for li in lis:
                    if li.text and 'Present' in li.text:
                        try:
                            if not new_members:
                                prnt('new_members done')
                                break
                        except:
                            pass
                        searchText = remove_accents(li.text).replace(' ','')
                        found = False
                        for m in new_members:
                            required = [f"{m['last']}", f"{m['first']}", m['state'].Name, m['district'].Name.replace('District ',''), m['party'].Name, 'Present']
                            for i in required:
                                if i.replace(' ','') not in searchText:
                                    found = False
                                    break
                                else:
                                    found = True
                            if found:
                                prnt('FOUND')
                                prnt(m)
                                new_members.remove(m)
                        #         break
                        # if found:
                                # prnt('-')
                                heading = li.find('span', {'class':'result-heading'})
                                try:
                                    img = 'https://www.congress.gov' + li.find('img')['src']
                                    prnt('firstImg:',img)
                                except Exception as e:
                                    prnt('find image fail',str(e))
                                    img = None
                                listing_name = remove_accents(heading.find('a').text)
                                x = listing_name.find(', ')
                                z = listing_name[x+2:].find(' - ')
                                first_name = listing_name[x+2:x+2+z].strip()
                                last_name = listing_name[:x].strip()

                                link = heading.find('a')['href']
                                
                                prnt(link)
                                # '''https://www.congress.gov/member/jerry-carl/C001054?q=%7B%22search%22%3A%22carl%22%7D&s=1&r=1'''
                                q = link.find('?')
                                w = link[:q].rfind('/')
                                code = link[w+1:q]
                                link = link[:q]
                                # prnt(code)
                                # person_GovIden = code
                                person, personU, person_is_new = get_model_and_update('Person', GovIden=code, Country_obj=country, Region_obj=country)
                                if not img:
                                    img = 'https://www.congress.gov/img/member/%s_200.jpg' %(code.lower())
                                profile = li.find('div', {'class':'member-profile'})
                                spans = profile.find_all('span', {'class':'result-item'})
                                # prnt(spans)
                                start_date = None
                                for span in spans:
                                    if 'Served' in span.text:
                                        # prnt('served')
                                        z = span.text.find('House: ')+len('House: ')
                                        x = span.text[z:].find('-')
                                        # prnt('yeay',int(span.text[z:z+x].strip()))
                                        dt = datetime.datetime(year=int(span.text[z:z+x].strip()), month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                                        start_date = timezonify('est', dt)
                                        # rep.StartDate = start_date
                                        break
                                if person_is_new and get_wiki:
                                    try:
                                        time.sleep(1)
                                        search_name = m['state'].Name + ' congressional representative ' + first_name + ' ' + last_name
                                        prnt(search_name)
                                        title = wikipedia.search(search_name)[0].replace(' ', '_')
                                        u = 'https://en.wikipedia.org/wiki/' + title
                                        person.Wiki = u
                                    except Exception as e:
                                        prnt(str(e))
                                person.GovProfilePage = 'https://www.congress.gov' + link
                                personU.data['Websites'] = [m['website']]
                                personU.data['Chamber'] = 'House'
                                personU.data['District_id'] = m['district'].id
                                personU.data['ProvState_id'] = m['state'].id
                                personU.data['FirstName'] = first_name
                                personU.data['LastName'] = last_name
                                personU.data['FullName'] = first_name + ' ' + last_name
                                personU.data['Position'] = 'Congressional Representative'
                                personU.data['gov_level'] = 'Federal'
                                personU.data['Telephones'] = [m['phone']]
                                personU.data['Party_id'] = m['party'].id
                                personU.data['PhotoLink'] = img
                                # prnt('2')
                                data = {'role':'Congressional Representative','current':True, 'gov_level':'Federal', 'officeName':m['officeRoom']}
                                if start_date:
                                    data['StartDate'] = dt_to_string(start_date)
                                person.update_role(personU, data=data)

                                if 'assignments' in m and m['assignments']:
                                    for assignment in m['assignments'].split('|'):

                                        data = {'role':assignment,'current':True,'gov_level':'Federal', 'Chamber':'House','Government_id':gov.id}
                                        person.update_role(personU, data=data)
                                person, personU, person_is_new, log = save_and_return(person, personU, log)
                                congressmen.append(person.id)
                                break
                return log

            log = get_data(soup1, log)
            log = get_data(soup2, log)
        else:
            close_browser(driver, driver_service)


        prnt(new_members)
        prnt('^ not found members')
        if new_members:
            logEvent('not found members', func='get_house_persons', code='37463', region=country, extra={'missing':new_members})
        # prnt('congressmen',congressmen)
        prntDev('congressmen len',len(congressmen))

        prnt('remove previous congressmen')
        # previousCongressmen = []
        # oldReps = Role.objects.filter(gov_level='Federal', Position='Congressional Representative').exclude(Person_obj__in=congressmen)
        repUpdates = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, extra__roles__contains=[{'role':'Congressional Representative','current':True, 'gov_level':'Federal'}]).exclude(pointerId__in=congressmen)
        prnt('repUpdates',repUpdates)
        for u in repUpdates:
            prnt('removing:::',u.pointerId)
            update = u.create_next_version()
            if 'Position' in update.data and update.data['Position'] == 'Congressional Representative':
                del update.data['Position']
            update.Pointer_obj.update_role(update, role='Congressional Representative', current=False)
            update, u_is_new = update.save_if_new(func=func)
            if u_is_new:
                log.updateShare(update)
        prnt('done')
    
    except Exception as e:
        prnt('oops ',str(e))
        logError(f'scrapeAssignment fail: {str(e)}', code='97534', func='get_house_persons', region=country)
        # time.sleep(7)
    close_browser(driver, driver_service)
    return finishScript(log, gov, special)

def get_senate_persons(special=None, dt=now_utc(), iden=None):
    func = 'get_senate_persons'
    log = []
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    prnt(country)


    # if country.add_office('Senator') or country.add_chamber('Senate'):
    #     country.update_data()
    #     log.updateShare(country)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')
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
    
    url = 'https://www.senate.gov/general/contact_information/senators_cfm.xml'
    r = requests.get(url)
    root = ET.fromstring(r.content)
    last_updated = root.find('last_updated')
    prnt(last_updated.text)
    driver = None
    driver_service = None
    senators = []
    new_senators = []
    for member in root.findall('member'):
        member_full = member.find('member_full').text
        last_name = member.find('last_name').text
        first_name = member.find('first_name').text
        party_short = member.find('party').text
        state_short = member.find('state').text
        address = member.find('address').text
        phone = member.find('phone').text
        email = member.find('email').text
        website = member.find('website').text
        member_class = member.find('class').text
        bioguide_id = member.find('bioguide_id').text

        state = Region.valid_objects.filter(AbbrName=state_short, Name=state_list[state_short], nameType='State', modelType='provState', ParentRegion_obj=country).first()
        # if state:
        #     if state.add_office('Senator'):
        #         state.update(share=False)
        #         log.updateShare(state)
        if not state:
            state = Region(func=func, AbbrName=state_short, Name=state_list[state_short], nameType='State', modelType='provState', ParentRegion_obj=country)
            state.update(share=False)
            log.updateShare(state)
        party_name, party_short, alt_name = find_party(party_short=party_short)

        party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=country, Region_obj=country, gov_level='Federal')
        if party_is_new:
            if get_wiki:
                try:   
                    search_name = party_name + ' american federal political party'
                    link = wikipedia.search(search_name)[0].replace(' ', '_')
                    party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                except:
                    pass
            party, partyU, party_is_new, log = save_and_return(party, partyU, log)

        person, personU, person_is_new = get_model_and_update('Person', GovIden=bioguide_id, Country_obj=country, Region_obj=country)
        # prnt('person found:',person, personU)
        personU.data['Chamber'] = 'Senate'
        # personU.data['District_id'] = district.id
        personU.data['ProvState_id'] = state.id
        personU.data['FirstName'] = first_name
        personU.data['LastName'] = last_name
        personU.data['FullName'] = first_name + ' ' + last_name
        personU.data['Position'] = 'Senator'
        personU.data['gov_level'] = 'Federal'
        personU.data['Telephones'] = [phone]
        personU.data['Email'] = email
        personU.data['Party_id'] = party.id
        personU.data['Class'] = member_class
        personU.data['member_detail'] = remove_accents(member_full)
        person.update_role(personU, data={'role':'Senator','current':True, 'gov_level':'Federal'})
    
    
        # person.Position = 'Senator'
        # person.Chamber = 'Senate'
        # person.Telephones = [phone]
        # person.Party_obj = party
        person, personU, person_is_new, log = save_and_return(person, personU, log)

        # rep, repU, rep_is_new = get_model_and_update('Role', gov_level='Federal', Person_obj=person, Position='Senator', Chamber='Senate', Country_obj=country, Region_obj=country)
        if person_is_new or not person.GovProfilePage or not person.GovIden or not 'PhotoLink' in personU.data:
            s = {'person_obj':person, 'personU':personU, 'person_is_new':person_is_new, 'first':first_name, 'last':last_name, 'website':website, 'party':party, 'state':state, 'bioguide_id':bioguide_id}
            new_senators.append(s)
        prnt(f"Member Full: {member_full}")
        prnt(f"Last Name: {last_name}")
        prnt(f"First Name: {first_name}")
        prnt(f"Party: {party}")
        prnt(f"State: {state}")
        prnt(f"Address: {address}")
        prnt(f"Phone: {phone}")
        prnt(f"Email: {email}")
        prnt(f"Website: {website}")
        prnt(f"Class: {member_class}")
        prnt(f"Bioguide ID: {bioguide_id}")
        prnt("")
        senators.append(person.id)
                
    if new_senators:
        new_senators = sorted(new_senators, key=lambda item: item['last'].lower())
        # prnt(new_senators)
        # https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22119%22%2C%22chamber%22%3A%22Senate%22%7D
        url = f'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22{gov.GovernmentNumber}%22%2C%22chamber%22%3A%22Senate%22%7D'
        try:
            driver, driver_service = open_browser(url)
            prnt('loaded')
            element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
            WebDriverWait(driver, 10).until(element_present)
            prnt('ready1')

            soup1 = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            prnt(str(e))

        close_browser(driver, driver_service)


        def get_data(soup, log):
            prnt('get data')
            main = soup.find('div', {'id':'main'})
            lis = main.find_all('li', {'class':'expanded'})
            for li in lis:
                if li.text and 'Present' in li.text:
                    if not new_senators:
                        prnt('new_senators done')
                        break
                    searchText = remove_accents(li.text).replace(' ','')
                    # if 'Vance' in searchText:
                    # prnt(searchText)
                    # if 'Budd' in searchText:
                    #     time.sleep(10)
                    found = False
                    for m in new_senators:
                        # prnt(searchText)
                        required = [f"{remove_accents(m['last'])}", f"{remove_accents(m['first'])}", m['state'].Name, m['party'].Name, 'Senator', 'Present']
                        # prnt(required)
                        for i in required:
                            # prnt(i)
                            if i.replace(' ','') not in searchText:
                                # prnt('not found')
                                found = False
                                break
                            else:
                                # prnt('found')
                                found = True
                        if found:
                            prnt('FOUND')
                            prnt(m)
                            # if 'Budd' in searchText:
                            #     time.sleep(10)
                            new_senators.remove(m)
                    #         break
                    # if found:
                            prnt('-')
                            heading = li.find('span', {'class':'result-heading'})
                            try:
                                img = 'https://www.congress.gov' + li.find('img')['src']
                            except:
                                img = None
                            listing_name = remove_accents(heading.find('a').text)
                            x = listing_name.find(', ')
                            z = listing_name[x+2:].find(' - ')
                            first = listing_name[x+2:x+2+z].strip()
                            last = listing_name[:x].strip()

                            link = heading.find('a')['href']
                            
                            prnt(link)
                            # '''https://www.congress.gov/member/jerry-carl/C001054?q=%7B%22search%22%3A%22carl%22%7D&s=1&r=1'''
                            q = link.find('?')
                            w = link[:q].rfind('/')
                            code = link[w+1:q]
                            link = link[:q]
                            prnt(code)
                            person = m['person_obj']
                            personU = m['personU']
                            person_is_new = m['person_is_new']

                            if not img:
                                img = 'https://www.congress.gov/img/member/%s_200.jpg' %(code.lower())
                            prnt(img)
                            # person.PhotoLink = img
                            # rep.PhotoLink = img
                            # rep.GovPage = link

                            profile = li.find('div', {'class':'member-profile'})
                            spans = profile.find_all('span', {'class':'result-item'})
                            start_date = None
                            for span in spans:
                                if 'Served' in span.text:
                                    z = span.text.find('Senate: ')+len('Senate: ')
                                    x = span.text[z:].find('-')
                                    start_date = timezonify('est', datetime.datetime(year=int(span.text[z:z+x].strip()), month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
                                    # rep.StartDate = start_date
                                    break
                            # break
                            if person_is_new and get_wiki:
                                try:
                                    time.sleep(1)
                                    search_name = m['state'].Name + ' Senator ' + m['first'] + ' ' + m['last']
                                    prnt(search_name)
                                    title = wikipedia.search(search_name)[0].replace(' ', '_')
                                    u = 'https://en.wikipedia.org/wiki/' + title
                                    person.Wiki = u
                                except Exception as e:
                                    prnt(str(e))
                            # 'https://www.congress.gov/member/tammy-baldwin/B001230'
                    
                            # prnt('1')
                            person.GovProfilePage = 'https://www.congress.gov' + link
                            personU.data['Websites'] = [m['website']]
                            personU.data['Chamber'] = 'Senate'
                            # personU.data['District_id'] = m['district'].id
                            personU.data['ProvState_id'] = m['state'].id
                            personU.data['FirstName'] = m['first']
                            personU.data['LastName'] = m['last']
                            personU.data['FullName'] = m['first'] + ' ' + m['last']
                            personU.data['Position'] = 'Senator'
                            personU.data['gov_level'] = 'Federal'
                            # personU.data['Telephones'] = [m['phone']]
                            personU.data['Party_id'] = m['party'].id
                            personU.data['PhotoLink'] = img
                            # prnt('2')
                            data = {'role':'Senator','current':True,'gov_level':'Federal'}
                            if start_date:
                                data['StartDate'] = dt_to_string(start_date)
                            person.update_role(personU, data=data)
                            # prnt('3')

                            #     # person, personU, person_is_new = get_model_and_update('Person', Website=website, FirstName=first, LastName=last, Country_obj=country, Region_obj=country)
                            # person.Position = 'Senator'
                            # person.GovProfilePage = link
                            # # person.Telephone = m['phone']
                            # person.Party_obj = m['party']
                            # # person.District_obj = m['district']
                            person, personU, person_is_new, log = save_and_return(person, personU, log)
                            # rep, repU, rep_is_new = get_model_and_update('Role', gov_level='Federal', Person_obj=person, Position='Congressional Representative', Chamber='House', District_obj=district, Country_obj=country, Region_obj=country, ProvState_obj=state)
                            # rep.Telephone = m['phone']
                            # repU.Party_obj = m['party']
                            # # repU.District_obj = m['district']
                            # repU.ProvState_obj = m['state']
                            # repU.data['Current'] = True
                            # # repData['OfficeName'] = m['officeRoom']
                            # rep, repU, rep_is_new, log = save_and_return(rep, repU, rep_is_new, log)

                            # for assignment in m['assignments'].split('|'):
                            #     rol, rolU, rol_is_new = get_model_and_update('Role', Title=assignment, gov_level='Federal', Person_obj=person, Position=assignment, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                            #     rolU.data['Current'] = True
                            #     rol, rolU, rol_is_new, log = save_and_return(rol, rolU, rol_is_new, log)

                            # congressmen.append(person)
                            senators.append(person.id)
                            break
                    # if not found:
                    #     prnt('NOTFOND')
                    #     prnt(searchText)
                    #     prnt()
            return log

        log = get_data(soup1, log)
        prnt('done new senators')
        if new_senators:
            logEvent('not found senators', func='get_senate_persons', code='3847', region=country, extra={'missing':new_senators})

    prnt('remove previous senators')
    # # prnt('sens',senators)
    # xRoles = Role.objects.filter(gov_level='Federal', Position='Senator', Country_obj=country).exclude(Person_obj__in=senators).order_by('Person_obj__id').distinct('Person_obj__id')
    # prnt('xroles',xRoles,'\n')
    # # time.sleep(5)
    # repUpdates = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in xRoles], data__contains={'Current': True})
    # prnt(repUpdates)
    # # time.sleep(5)
    # for u in repUpdates:
    #     # prnt('-----')
    #     # prnt(u.Pointer_obj)
    #     update = u.create_next_version()
    #     # updateData = json.loads(update.data)
    #     update.data['Current'] = False
    #     # update.data = json.dumps(updateData)
    #     update, u_is_new = update.save_if_new(share=False)
    #     if update and u_is_new:
    #         log.updateShare(update)

    repUpdates = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, extra__roles__contains=[{'role':'Senator', 'current':True, 'gov_level':'Federal'}]).exclude(pointerId__in=senators)
    prnt('repUpdates',repUpdates)
    for u in repUpdates:
        prnt('removing:::',u.pointerId)
        update = u.create_next_version()
        if 'Position' in update.data and update.data['Position'] == 'Senator':
            del update.data['Position']
        update.Pointer_obj.update_role(update, role='Senator', current=False)
        update, u_is_new = update.save_if_new(func=func)
        if u_is_new:
            log.updateShare(update)
    prnt('done remove previous')
    # time.sleep(10)
    # if driver:
    #     close_browser(driver, driver_service)
    return finishScript(log, gov, special)

# not used
def get_senator_details(driver, personId):
            
    url = f'https://bioguide.congress.gov/search/bio/{personId}'
    driver.get(url)
    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/div[2]/div/div[1]'))
    WebDriverWait(driver, 10).until(element_present)

    photoSrc = driver.find_element(By.XPATH, '//*[@id="root"]/div/div/div[2]/div/div[1]/div[1]/div[3]/div/img').get_attribute('src')
    photoLink = 'https://bioguide.congress.gov' + photoSrc

    serving = driver.find_element(By.XPATH, '//*[@id="profile-overview--desktop"]/div/div[2]/div[2]/span[2]').text.replace('(','').replace(')','').strip()
    # "(2007 – Present)"
    a = serving.find('–')
    startYearTxt = serving[:a].strip()
    startingYear = datetime.strptime(startYearTxt, '%Y')

    bio = driver.find_element(By.XPATH, '//*[@id="Biography"]/div').text
    # x = 'https://bioguide.congress.gov/photo/3b76ebb14cbdc3c0e07d89e5d84e1075.jpg'
    # close_browser(driver, driver_service)
    return photoLink, startingYear, bio

def get_bills(special=None, dt=now_utc(), iden=None, target_dt=None, target_links=None):
    func = 'get_bills'
    log = []
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent(f'scrapeAssignment target_links:{len(target_links) if target_links else 0}', region=country, func=func, log_type='Tasks')
        # logEvent('scrapeAssignment: ' + country.Name + '/' + func, log_type='Tasks')

    driver = None
    driver_service = None
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
                log, driver, driver_service = add_bill(url=link, log=log, update_dt=target_dt, driver=driver, driver_service=driver_service, country=country, ref_func=func)
                if link != target_links[-1]:
                    time.sleep(2)
            
    else:
        xml = 'https://www.govinfo.gov/rss/billstatus-batch.xml'
        r = requests.get(xml)
        root = ET.fromstring(r.content)
        # prnt(root)
        # rss = root.find('rss')
        channel = root.find('channel')
        # prnt(channel.findall('item'))
        # item_list = list(channel.findall('item'))
        item_list = list(reversed(channel.findall('item')))

        i = 0

        def check_item_updates(item, i, log, driver=None, driver_service=None):
            pubDate = item.find('pubDate')
            pub_dt = datetime.datetime.strptime(pubDate.text, "%a, %d %b %Y %H:%M:%S %z")
            # prnt(pubDate.text)
            desc = item.find('description')
            # prnt(desc.text)
            soup = BeautifulSoup(desc.text, 'html.parser')


            ass = soup.find_all('a')
            links = []
            for a in ass:
                if a['href']:
                    links.append(a['href'])
            updates = Update.objects.filter(pointerId__startswith=get_model_prefix('Bill'), Region_obj=country, data__data_link__in=links, created__gte=pub_dt)
            for u in updates:
                if u.data['data_link'] in links:
                    if u.validated or u.created > now_utc() - datetime.timedelta(minutes=60):
                        links.remove(u.data['data_link'])

            # first_link = soup.find_all('a')[0]
            # update = Update.objects.filter(pointerId__startswith=get_model_prefix('Bill'), Region_obj=country, created__gte=pub_dt).first()
            prnt('links',links)
            if testing():
                x = 1
            else:
                x = 1 # adjust here for shorter runtime, but less lookback
            if not links and i < x:
                i += 1
                check_item_updates(item_list[i], i, log, driver, driver_service)
            else:
                max_bills_run = 20
                while i >= 0:
                    item = item_list[i]
                    i -= 1
                    # prnt('i',i)
                    pubDate = item.find('pubDate')
                    pub_dt = datetime.datetime.strptime(pubDate.text, "%a, %d %b %Y %H:%M:%S %z")
                    while len(links) > 0:
                        # if len(links) > 200:
                        target_links = links[:max_bills_run]

                        queue = django_rq.get_queue('low')
                        queue.enqueue(get_bills, target_links=target_links, target_dt=pub_dt, job_timeout=runTimes[func], result_ttl=3600)
                        if len(links) > max_bills_run:
                            links = links[max_bills_run:]
                        else:
                            links = []
            return log, driver, driver_service
                    
        # prnt('item_list[i]',item_list[i])
        log, driver, driver_service = check_item_updates(item_list[i], i, log)   

    if driver:
        close_browser(driver, driver_service)

    return finishScript(log, gov, special)

billTypes = {'hr':{'chamber':'House','billType':'Bill','prefix':'H.R.','legisLink':'https://www.congress.gov/bill/xxx-congress/house-bill/'},
        'hres':{'chamber':'House','billType':'Resolution','prefix':'H.Res.','legisLink':'https://www.congress.gov/bill/xxx-congress/house-resolution/'},
        'hconres':{'chamber':'House','billType':'Concurrent Resolution','prefix':'H.Con.Res.','legisLink':'https://www.congress.gov/bill/xxx-congress/house-concurrent-resolution/'},
        'hamdt':{'chamber':'House','billType':'Amendment','prefix':'H.Amdt','legisLink':'https://www.congress.gov/amendment/xxx-congress/house-amendment/'},
        'sconres':{'chamber':'Senate','billType':'Concurrent Resolution','prefix':'S.Con.Res.','legisLink':'https://www.congress.gov/bill/xxx-congress/senate-concurrent-resolution/'},
        'samdt':{'chamber':'Senate','billType':'Amendment','prefix':'S.Amdt','legisLink':'https://www.congress.gov/amendment/xxx-congress/senate-amendment/'},
        'hjres':{'chamber':'House','billType':'Joint Resolution','prefix':'H.J.Res.','legisLink':'https://www.congress.gov/bill/xxx-congress/house-joint-resolution/'},
        'sjres':{'chamber':'Senate','billType':'Joint Resolution','prefix':'S.J.Res.','legisLink':'https://www.congress.gov/bill/xxx-congress/senate-joint-resolution/'},
        'sres':{'chamber':'Senate','billType':'Resolution','prefix':'S.Res.','legisLink':'https://www.congress.gov/bill/xxx-congress/senate-resolution/'},
        's':{'chamber':'Senate','billType':'Bill','prefix':'S.','legisLink':'https://www.congress.gov/bill/xxx-congress/senate-bill/'}
        }



# {'err': "'NoneType' object has no attribute 'text'", 'reg': 'USA', 'code': '59278154', 'func': 'get_bills', 'extra': 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/s/BILLSTATUS-118s4869.xml'}

# 2025-01-03T07:28:01.704424+00:00 -- {'err': 'failed to get_text', 'code': '65434', 'func': 'add_bill', 'extra': "{'err': 'Message: \\nStacktrace:\\n#0 0x647b71ba931a <unknown>\\n#1 0x647b716bf6e0 <unknown>\\n#2 0x647b7170e3e6 <unknown>\\n#3 0x647b7170e681 <unknown>\\n#4 0x647b71753b04 <unknown>\\n#5 0x647b7173248d <unknown>\\n#6 0x647b71750ed7 <unknown>\\n#7 0x647b71732203 <unknown>\\n#8 0x647b71700cc0 <unknown>\\n#9 0x647b71701c9e <unknown>\\n#10 0x647b71b76d0b <unknown>\\n#11 0x647b71b7ac92 <unknown>\\n#12 0x647b71b63b3c <unknown>\\n#13 0x647b71b7b807 <unknown>\\n#14 0x647b71b490df <unknown>\\n#15 0x647b71b98578 <unknown>\\n#16 0x647b71b98740 <unknown>\\n#17 0x647b71ba8196 <unknown>\\n#18 0x7158edc9ca94 <unknown>\\n#19 0x7158edd29c3c <unknown>\\n', 'url.text': 'https://www.govinfo.gov/content/pkg/BILLS-118sres82is/xml/BILLS-118sres82is.xml'}"}
# 2025-01-03T07:23:17.678446+00:00 -- {'err': "('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))", 'reg': 'USA', 'code': '59278154', 'func': 'get_bills', 'extra': 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/s/BILLSTATUS-118s3575.xml'}


def add_bill(url=None, log=[], update_dt=now_utc(), driver=None, driver_service=None, special=None, country=None, ref_func=None):
    func = 'add_bill'
    if not country:
        country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    if not log:
        log = create_share_object(func, country, special=special, dt=now_utc(), iden=None)
    err = 'start'
    try:
        if not url:
            return log, driver, driver_service
            url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118hr7024.xml'
            url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hres/BILLSTATUS-118hres1414.xml'
            url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hres/BILLSTATUS-119hres41.xml'
            url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118hr4217.xml'
            url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118hr6928.xml'
            # url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118s288.xml'
            url = 'https://www.congress.gov/bill/118th-congress/senate-bill/288'
        prnt('\n----ADD BILL')
        # prnt('link:',link)
        # href = links[-1]['href']
        prnt('href:',url)
        r = requests.get(url)
        # prntDebug('received r', r.content)
        root = ET.fromstring(r.content)
        billXML = root.find('bill')
        try:
            billNum = billXML.find('number').text
        except:
            billNum = billXML.find('billNumber').text
        try:
            type = billXML.find('type').text
        except:
            type = billXML.find('billType').text
        prnt(billNum)
        try:
            updateDate = billXML.find('updateDate').text
        except:
            pass
        try:
            updateDateIncludingText = billXML.find('updateDateIncludingText').text
            originChamberCode = billXML.find('originChamberCode').text
        except:
            pass
        originChamber = billXML.find('originChamber').text
        introducedDate = billXML.find('introducedDate').text
        congress = billXML.find('congress').text
        prnt(congress)
        billType = billTypes[type.lower().replace('.','')]['billType']
        billPrefix = billTypes[type.lower().replace('.','')]['prefix']
        billCode = billPrefix + billNum
        legisLink = billTypes[type.lower().replace('.','')]['legisLink'] + billNum
        prnt(legisLink)
        from posts.views import get_ordinal
        legisLink = legisLink.replace('xxx', get_ordinal(congress))
        prnt(legisLink)

        err = 0

        try:
            prnt(f'billNum: {billNum.text}')
            prnt(f'updateDate: {updateDate.text}')
            prnt(f'updateDateIncludingText: {updateDateIncludingText.text}')
            prnt(f'originChamber: {originChamber.text}')
            prnt(f'type: {type.text}')
            prnt(f'introducedDate: {introducedDate.text}')
            prnt(f'congress: {congress.text}')
            prnt(f'billCode: {billCode}')
        except Exception as e:
            prnt(str(e))

        
            
        gov = Government.objects.filter(Country_obj=country, gov_level='Federal', GovernmentNumber=int(congress)).first()
        if not gov:
            gov = Government(Country_obj=country, gov_level='Federal', gov_type='Congress', GovernmentNumber=int(congress), Region_obj=country)
            from blockchain.models import round_time
            gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
            gov.migrate_data()
            gov.LogoLinks = gov_logo_links
            gov.save()
            log.updateShare(gov)
        err = 1
        
        bill, billU, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, Chamber=originChamber, NumberCode=billCode, BillDocumentTypeName=billType)
        new_bill = bill_is_new
        if bill_is_new:
            bill.LegisLink = legisLink
            bill.NumberPrefix = billPrefix
            bill.Number = billNum
            bill.save()
        if 'Status' not in billU.data:
            billU.data['Status'] = 'Introduced'
        if 'billVersions' not in billU.data:
            versions = None
            def versionizer(version, current=None):
                if not current and version == 'Introduced':
                    current = True
                return {'version':version, 'current':current, 'status':None, 'started_dt':None, 'completed_dt':None}
            if originChamber == 'Senate':
                if type.lower() == 'sres':
                    versions = [versionizer('Introduced'), versionizer('Agreed to in Senate')]
                elif type.lower() == 'sjres':
                    versions = [versionizer('Introduced'), versionizer('Passed Senate'), versionizer('Passed House'), versionizer('To President'), versionizer('Became Law')]
                elif type.lower() == 'sconres':
                    versions = [versionizer('Introduced'), versionizer('Agreed to in Senate'), versionizer('Agreed to in House')]
                elif type.lower() == 's':
                    versions = [versionizer('Introduced'), versionizer('Passed Senate'), versionizer('Passed House'), versionizer('To President'), versionizer('Became Law')]

            elif originChamber == 'House':
                if type.lower() == 'hres':
                    versions = [versionizer('Introduced'), versionizer('Agreed to in House')]
                elif type.lower() == 'hjres':
                    versions = [versionizer('Introduced'), versionizer('Passed House'), versionizer('Passed Senate'), versionizer('To President'), versionizer('Became Law')]
                elif type.lower() == 'hconres':
                    versions = [versionizer('Introduced'), versionizer('Agreed to in House'), versionizer('Agreed to in Senate')]
                elif type.lower() == 'hr':
                    versions = [versionizer('Introduced'), versionizer('Passed House'), versionizer('Passed Senate'), versionizer('To President'), versionizer('Became Law')]
            if versions:
                billU.data['billVersions'] = versions
        err = 2
        billU.data['data_link'] = url

        prnt('\ncommittees')
        committees = billXML.find('committees')
        if committees:
            items = committees.findall('item')
            for i in items:
                prnt('---')
                systemCode = i.find('systemCode')
                name = i.find('name')
                chamber = i.find('chamber')
                type = i.find('type')
                try:
                    prnt(f'systemCode: {systemCode.text}')
                    prnt(f'name: {name.text}')
                    prnt(f'chamber: {chamber.text}')
                    prnt(f'type: {type.text}')
                except Exception as e:
                    prnt(str(e))

                activities = i.find('activities')
                if activities:
                    for x in activities.findall('item'):
                        name = x.find('name')
                        date = x.find('date')
                        try:
                            prnt(f'name: {name.text}')
                            prnt(f'date: {date.text}')
                        except Exception as e:
                            prnt(str(e))
                
                xml_str = ET.tostring(i, encoding='unicode')
                committee_data = xmltodict.parse(xml_str)
                prntn("committee_data",committee_data)
                committee_data = committee_data['item']

                if not billU.extra:
                    billU.extra = {}
                if 'committees' not in billU.extra:
                    billU.extra['committees'] = []
                if committee_data not in billU.extra['committees']:
                    billU.extra['committees'].append(committee_data)


        err = 3
        prnt('\ncommitteeReports')
        committeeReports = billXML.find('committeeReports')
        if committeeReports:
            if 'committeeReports' not in billU.data:
                billU.data['committeeReports'] = []
            for c in committeeReports:
                try:
                    report_url = None
                    citation = c.find('citation').text
                    # <citation>H. Rept. 118-353</citation>
                    a = citation.find('-')+len('-')
                    num = citation[a:]
                    from posts.views import get_ordinal
                    prnt(f'citation: {citation}')
                    report_url = f"https://www.congress.gov/congressional-report/{get_ordinal(gov.GovernmentNumber)}-congress/{bill.Chamber.lower()}-report/{num}/1"
                    # if report_url not in billU.data['committeeReports']:
                    #     billU.data['committeeReports'].append(report_url)
                except Exception as e:
                    prnt('billfail385',str(e))
                
                xml_str = ET.tostring(c, encoding='unicode')
                committeeReport_data = xmltodict.parse(xml_str)
                prntn("committeeReport_data",committeeReport_data)
                if 'item' in committeeReport_data:
                    committeeReport_data = committeeReport_data['item']
                if report_url and 'report_url' not in committeeReport_data:
                    committeeReport_data['report_url'] = report_url

                if not billU.extra:
                    billU.extra = {}
                if 'committeeReports' not in billU.extra:
                    billU.extra['committeeReports'] = []
                if committeeReport_data not in billU.extra['committeeReports']:
                    billU.extra['committeeReports'].append(committeeReport_data)
        err = 4
        prnt('\nrelatedBills')
        relatedBills = billXML.find('relatedBills')
        if relatedBills:
            if 'relatedBills' not in billU.data:
                billU.data['relatedBills'] = []
            # for b in relatedBills:
            #     prnt('---')
            for i in relatedBills.findall('item'):
                prnt('---')
                try:
                    title = i.find('title').text
                    congress = i.find('congress').text
                    number = i.find('number').text
                    type = i.find('type').text
                    if not any(d.get('title') == title for d in billU.data['relatedBills']):
                        rBill = Bill.objects.filter(Number=number, NumberPrefix__iexact=type.lower(), Government_obj__GovernmentNumber=int(congress))
                        if rBill:
                            r_data = {'billId':rBill.id, 'billNumber':rBill.NumberCode, 'title':title, 'congress':rBill.Government_obj.get_gov_num()}
                            if r_data not in billU.data['relatedBills']:
                                billU.data['relatedBills'].append(r_data)
                        else:
                            r_data = {'billNumber':f'{type}{number}', 'congress':congress, 'title':title}
                            if r_data not in billU.data['relatedBills']:
                                billU.data['relatedBills'].append(r_data)
                    prnt(f'title: {title}')
                    prnt(f'congress: {congress}')
                    prnt(f'number: {number}')
                    prnt(f'type: {type}')
                except Exception as e:
                    prnt(str(e))

                latestAction = i.find('latestAction')
                if latestAction:
                    for x in latestAction:
                        actionDate = x.find('actionDate')
                        text = x.find('text')
                        try:
                            prnt(f'actionDate: {actionDate.text}')
                            prnt(f'text: {text.text}')
                        except Exception as e:
                            prnt(str(e))

                relationshipDetails = i.find('relationshipDetails')
                if relationshipDetails:
                    for x in relationshipDetails.findall('item'):
                        type = x.find('type')
                        identifiedBy = x.find('identifiedBy')
                        try:
                            prnt(f'type: {type.text}')
                            prnt(f'identifiedBy: {identifiedBy.text}')
                        except Exception as e:
                            prnt(str(e))
        err = 5
        prnt('\nactions')
        actions = billXML.find('actions')
        if actions:
            prnt('action_url',url)
            # newAction = True
            previous_dt = None
            if not 'actionHistory' in billU.data:
                billU.data['actionHistory'] = []
            
            for i in actions.findall('item'):
                xml_str = ET.tostring(i, encoding='unicode')
                action_data = xmltodict.parse(xml_str)
                prntn("action_data",action_data)
                action_data = action_data['item']

                if not billU.extra:
                    billU.extra = {}
                if 'billActions' not in billU.extra:
                    billU.extra['billActions'] = []
                if action_data not in billU.extra['billActions']:
                    billU.extra['billActions'].append(action_data)


                # prntn('ACTION---',i.text)
                actionChamber = None
                actionDate = i.find('actionDate')
                actionTime = i.find('actionTime')
                # <actionDate>2024-01-31</actionDate>
                # <actionTime>20:33:22</actionTime>
                if actionTime is not None:
                    dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}-{actionTime.text}', '%Y-%m-%d-%H:%M:%S'))
                else:
                    dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}', '%Y-%m-%d'))
                prnt('dt',dt)
                x = {'dt':dt_to_string(dt)}
                # try:
                #     actionCode = i.find('actionCode').text
                #     prnt(f'actionDate: {actionDate.text}')
                #     prnt(f'actionCode: {actionCode}')
                #     prnt(f'actionTime: {actionTime.text}')
                # except Exception as e:
                #     prnt(str(e))
                #     actionCode = ''
                
                
                calendarNumber = i.find('calendarNumber')
                if calendarNumber:
                    calendar = calendarNumber.find('calendar')
                    try:
                        prnt(f'calendar: {calendar.text}')
                    except:
                        pass
                
                committees = i.find('committees')
                if committees:
                    for z in committees.findall('item'):
                        systemCode = z.find('systemCode')
                        name = z.find('name')
                        try:
                            prnt(f'name: {name.text}')
                            prnt(f'systemCode: {systemCode.text}')
                        except Exception as e:
                            prnt(str(e))

                try:
                    actionText = i.find('text')
                    # prnt('actionText0',actionText)
                    x['text'] = actionText.text
                except Exception as e:
                    prnt('actionfail 385',str(e))
                    actionText = None
                try:
                    type = i.find('type')
                    x['type'] = type.text
                except:
                    pass
                # try:
                #     distinction = i.find('actionCode').text
                #     # logError('actioncode found', code='8643', func='add_bill', region='Usa', extra={'distinction':distinction,'url':url})
                # except Exception as e:
                #     # try:
                #     #     distinction = i.find('sourceSystem').text
                #     #     logError('actioncode found', code='98764', func='add_bill', region='Usa', extra={'distinction':distinction,'url':url})
                #     # except Exception as e:
                #     distinction = ''
                #     # logError('distinction not found', code='0863', func='add_bill', region='Usa', extra={'e':str(e),'url':url})
                
                # prnt('actionText1',actionText)
                sourceSystem = i.find('sourceSystem')
                if sourceSystem:
                    name = sourceSystem.find('name')
                    code = sourceSystem.find('code')
                    if actionText == None:
                        actionText = sourceSystem.find('actionText')
                        prnt('actionText1.5',actionText)
                    try:
                        # if not distinction or str(distinction) == '\\n':
                        #     distinction = code.text
                        prnt(f'name: {name.text}')
                        prnt(f'code: {code.text}')
                    except Exception as e:
                        prnt('fail58305',str(e))

                try:
                    distinction = actionText.text
                    actionText = actionText.text
                except Exception as e:
                    prnt('fail47242',str(e))
                    if i.find('actionCode'):
                        distinction = i.find('actionCode').text
                        actionText = ''
                    elif type:
                        distinction = type.text
                        actionText = ''
                    else:
                        distinction = 'x'
                        actionText = ''

                recordedVotes = i.find('recordedVotes')
                if recordedVotes:
                    for v in recordedVotes.findall('recordedVote'):
                        # prnt('---')
                        rollNumber = v.find('rollNumber')
                        url = v.find('url')
                        chamber = v.find('chamber')
                        congress = v.find('congress')
                        date = v.find('date')
                        sessionNumber = v.find('sessionNumber')
                        # try:
                        #     prnt(f'rollNumber: {rollNumber.text}')
                        #     prnt(f'url: {url.text}')
                        #     prnt(f'chamber: {chamber.text}')
                        #     prnt(f'congress: {congress.text}')
                        #     prnt(f'date: {date.text}')
                        #     prnt(f'sessionNumber: {sessionNumber.text}')
                        # except Exception as e:
                        #     prnt(str(e))

                # billU.data['actionHistory'].append(x)
                actionChamber = originChamber
                if actionText:
                    if 'house' in actionText.lower():
                        actionChamber = 'House'
                    elif 'senate' in actionText.lower():
                        actionChamber = 'Senate'
                    elif 'president' in actionText.lower():
                        actionChamber = 'Executive'
                # billAction = GenericModel.objects.filter(type='BillAction', pointerId=bill.id, DateTime=dt, distinction=distinction, Chamber=actionChamber, Government_obj=gov, Country_obj=country, Region_obj=country).first()
                # if not billAction:
                # #     newAction = False
                # # else:
                #     billAction = GenericModel(type='BillAction', func=func, pointerId=bill.id, DateTime=dt, distinction=distinction, Data={'Text': actionText, 'Code':bill.NumberCode}, Chamber=actionChamber, Government_obj=gov, Country_obj=country, Region_obj=country)
                #     billAction.save()
                #     log.updateShare(billAction)
                if not bill.DateTime or dt < bill.DateTime:
                    prnt('x')
                    bill.DateTime = dt
                # previous_dt = dt
                # prnt('reviousdt',previous_dt)
                
            if 'billVersions' in billU.data:
                statuses = {'introduced':'Introduced', 'received in the house':'in house', 'passed/agreed to in house':'Passed House', 'submitted in house':'in house', 'submitted in senate':'in senate', 'received in the senate':'in senate',
                            'referred to the house':'in house', 'referred to the senate': 'in senate',
                            'passed/agreed to in senate':'Passed Senate', 'resolving differences':'Resolving Differences', 'presented to president':'To President', 'vetoed by president':'Vetoed by President',
                            'passed house over veto':'pass house veto', 'passed senate over veto':'pass senate veto', 'the objections of the president to the contrary notwithstanding failed':'Failed to pass over veto', 'became public law':'Became Law'
                            }
                prnt('actions in reverse')
                for i in list(reversed(actions.findall('item'))):
                    prnt()
                    # prnt(i)
                    # prnt()
                    txt = i.find('text')
                    try:
                        prnt(f'text: {txt.text}')
                        # prnt(f'type: {type.text}')
                    except Exception as e:
                        prnt(str(e))
                    actionDate = i.find('actionDate')
                    actionTime = i.find('actionTime')
                    if actionTime is not None:
                        dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}-{actionTime.text}', '%Y-%m-%d-%H:%M:%S'))
                    else:
                        dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}', '%Y-%m-%d'))
                    prnt(dt)
                    if txt is not None:
                        prnt('txt',txt.text)
                        passed_house_veto = False
                        passed_senate_veto = False
                        for key, value in statuses.items():
                            if key in txt.text.lower():
                                prnt('FOUND',key)
                                if value == 'in house':
                                    if bill.Chamber == 'House':
                                        value = 'Introduced'
                                    elif bill.Chamber == 'Senate':
                                        value = 'Passed Senate'
                                elif value == 'in senate':
                                    if bill.Chamber == 'Senate':
                                        value = 'Introduced'
                                    elif bill.Chamber == 'House':
                                        value = 'Passed House'
                                elif value == 'pass house veto':
                                    passed_house_veto = True
                                    value = None
                                    if passed_senate_veto:
                                        value = 'Passed over veto'
                                elif value == 'pass senate veto':
                                    passed_senate_veto = True
                                    value = None
                                    if passed_house_veto:
                                        value = 'Passed over veto'
                                if value:
                                    prnt('val',value)
                                    billU.data['Status'] = value
                                    exists = False
                                    for v in billU.data['billVersions']:
                                        prnt(v['version'])
                                        if v['version'] == value:
                                            exists = True
                                            v['current'] = True
                                            v['status'] = 'Current'
                                            if not v['started_dt']:
                                                v['started_dt'] = dt_to_string(dt)
                                        elif v['current'] == True:
                                            v['current'] = False
                                            v['status'] = 'Passed'
                                            if not v['completed_dt']:
                                                v['completed_dt'] = dt_to_string(dt)
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
                                                    billU.data['billVersions'].append({'version':value, 'current':True, 'status':'Current', 'started_dt':dt_to_string(dt), 'completed_dt':None})
                                                    inserted = True
                                                billU.data['billVersions'].append(v)
                    # else:
                    #     prnt('not txt',txt.text)
                # time.sleep(5)
        err = 6


        prnt('\nsponsors')
        sponsors = billXML.find('sponsors')
        if sponsors:
            if not 'cosponsors' in billU.data:
                billU.data['cosponsors'] = []
            if not 'sponsor_parties' in billU.data:
                billU.data['sponsor_parties'] = {}
            for i in sponsors.findall('item'):
                prnt('---')
                bioguideId = i.find('bioguideId')
                fullName = i.find('fullName')
                firstName = i.find('firstName')
                lastName = i.find('lastName')
                middleName = i.find('middleName')
                party = i.find('party')
                state = i.find('state')
                district = i.find('district')
                isByRequest = i.find('isByRequest')
                try:
                    person = Person.objects.filter(GovIden=bioguideId.text, Country_obj=country).first()
                    prnt('p',person)
                    if not bill.Person_obj and not bill.SponsorCode:
                        try:
                            bill.Party_obj = Party.objects.filter(ShortName__iexact=party.text, gov_level='Federal', Region_obj=country).first()
                        except:
                            pass
                        if person:
                            try:
                                personU = person.Update_obj
                                bill.Person_obj = person
                                if not bill.Party_obj:
                                    bill.Party_obj = Party.objects.filter(id=personU.data['Party_id'], gov_level='Federal', Region_obj=country).first()
                            except:
                                pass
                            try:
                                bill.District_obj = District.objects.filter(id=personU.data['District_id'], gov_level='Federal', Region_obj=country).first()
                            except:
                                pass
                        else:
                            bill.SponsorPersonName = firstName.text + ' ' + lastName.text
                            bill.SponsorCode = bioguideId.text
                        if bill.Party_obj:
                            if bill.Party_obj.ShortName not in billU.data['sponsor_parties']:
                                billU.data['sponsor_parties'][bill.Party_obj.ShortName] = {'colr':bill.Party_obj.Color, 'count':1}
                            else:
                                billU.data['sponsor_parties'][bill.Party_obj.ShortName]['count'] += 1
                    else:
                        if not person:
                            p_name = fullName.text
                            pu = Update.objects.filter(Region_obj=country, id__startswith=get_model_prefix('Person'), data__contains={'FullName': p_name}).first()
                            if pu and pu.Pointer_obj:
                                person = pu.Pointer_obj
                        if person:
                            if person != bill.Person_obj:
                                personU = person.Update_obj
                                if not any(p['obj_id'] == person.id for p in billU.data['cosponsors']):
                                    sponsor_dic = {'obj_id':person.id, 'fullName':personU.data['FullName']}
                                    if 'Party_id' in personU.data and personU.data['Party_id']:
                                        prty = Party.objects.filter(id=personU.data['Party_id']).first()
                                        if prty:
                                            sponsor_dic['prty_colr'] = prty.Color
                                    billU.data['cosponsors'].append(sponsor_dic)
                                    if prty.ShortName not in billU.data['sponsor_parties']:
                                        billU.data['sponsor_parties'][prty.ShortName] = {'colr':prty.Color, 'count':1}
                                    else:
                                        billU.data['sponsor_parties'][prty.ShortName]['count'] += 1
                        else:
                            if not any(p['fullName'] == p_name for p in billU.data['cosponsors']):
                                billU.data['cosponsors'].append({'obj_id':None, 'fullName':p_name})
                        

                    prnt(f'bioguideId: {bioguideId.text}')
                    prnt(f'fullName: {fullName.text}')
                    prnt(f'firstName: {firstName.text}')
                    prnt(f'lastName: {lastName.text}')
                    prnt(f'middleName: {middleName.text}')
                    prnt(f'party: {party.text}')
                    prnt(f'state: {state.text}')
                    prnt(f'district: {district.text}')
                    prnt(f'isByRequest: {isByRequest.text}')
                except Exception as e:
                    prnt(str(e))
        err = 7
        prnt('\ncosponsors')
        cosponsors = billXML.find('cosponsors')
        if cosponsors:
            if not 'cosponsors' in billU.data:
                billU.data['cosponsors'] = []
            if not 'sponsor_parties' in billU.data:
                billU.data['sponsor_parties'] = {}
            for i in cosponsors.findall('item'):
                prnt('---')
                bioguideId = i.find('bioguideId')
                fullName = i.find('fullName')
                firstName = i.find('firstName')
                lastName = i.find('lastName')
                middleName = i.find('middleName')
                party = i.find('party')
                state = i.find('state')
                district = i.find('district')
                sponsorshipDate = i.find('sponsorshipDate')
                isOriginalCosponsor = i.find('isOriginalCosponsor')
                try:
                    person = Person.objects.filter(GovIden=bioguideId.text, Country_obj=country).first()
                    # prnt('p',person)
                    if not person:
                        p_name = fullName.text
                        pu = Update.objects.filter(Region_obj=country, id__startswith=get_model_prefix('Person'), data__contains={'FullName': p_name}).first()
                        if pu and pu.Pointer_obj:
                            person = pu.Pointer_obj
                    if person:
                        if person != bill.Person_obj:
                            personU = person.Update_obj
                            if not any(p['obj_id'] == person.id for p in billU.data['cosponsors']):
                                sponsor_dic = {'obj_id':person.id, 'fullName':personU.data['FullName']}
                                if 'Party_id' in personU.data and personU.data['Party_id']:
                                    prty = Party.objects.filter(id=personU.data['Party_id']).first()
                                    if prty:
                                        sponsor_dic['prty_colr'] = prty.Color
                                billU.data['cosponsors'].append(sponsor_dic)
                                if prty.ShortName not in billU.data['sponsor_parties']:
                                    billU.data['sponsor_parties'][prty.ShortName] = {'colr':prty.Color, 'count':1}
                                else:
                                    billU.data['sponsor_parties'][prty.ShortName]['count'] += 1
                    else:
                        if not any(p['fullName'] == p_name for p in billU.data['cosponsors']):
                            billU.data['cosponsors'].append({'obj_id':None, 'fullName':p_name})


                    prnt(f'bioguideId: {bioguideId.text}')
                    prnt(f'fullName: {fullName.text}')
                    prnt(f'firstName: {firstName.text}')
                    prnt(f'lastName: {lastName.text}')
                    prnt(f'middleName: {middleName.text}')
                    prnt(f'party: {party.text}')
                    prnt(f'state: {state.text}')
                    prnt(f'district: {district.text}')
                    prnt(f'sponsorshipDate: {sponsorshipDate.text}')
                    prnt(f'isOriginalCosponsor: {isOriginalCosponsor.text}')
                except Exception as e:
                    prnt(str(e))
        err = 8
        prnt('\ncboCostEstimates')
        cboCostEstimates = billXML.find('cboCostEstimates')
        if cboCostEstimates:
            for i in cboCostEstimates.findall('item'):
                prnt('---')
                pubDate = i.find('pubDate')
                title = i.find('title')
                url = i.find('url')
                description = i.find('description')
                try:
                    prnt(f'pubDate: {pubDate.text}')
                    prnt(f'title: {title.text}')
                    prnt(f'url: {url.text}')
                    prnt(f'description: {description.text}')
                except Exception as e:
                    prnt(str(e))
                
                xml_str = ET.tostring(i, encoding='unicode')
                cboCostEstimates_data = xmltodict.parse(xml_str)
                prntn("cboCostEstimates_data",cboCostEstimates_data)
                if 'item' in cboCostEstimates_data:
                    cboCostEstimates_data = cboCostEstimates_data['item']

                if not billU.extra:
                    billU.extra = {}
                if 'cboCostEstimates' not in billU.extra:
                    billU.extra['cboCostEstimates'] = []
                if cboCostEstimates_data not in billU.extra['cboCostEstimates']:
                    billU.extra['cboCostEstimates'].append(cboCostEstimates_data)
        err = 9
        prnt('\nlaws')
        laws = billXML.find('laws')
        if laws:
            for i in laws.findall('item'):
                prnt('---')
                type = i.find('type')
                number = i.find('number')
                try:
                    prnt(f'type: {type.text}')
                    prnt(f'number: {number.text}')
                except Exception as e:
                    prnt(str(e))

                xml_str = ET.tostring(i, encoding='unicode')
                laws_data = xmltodict.parse(xml_str)
                prntn("laws_data",laws_data)
                if 'item' in laws_data:
                    laws_data = laws_data['item']

                if not billU.extra:
                    billU.extra = {}
                if 'laws' not in billU.extra:
                    billU.extra['laws'] = []
                if laws_data not in billU.extra['laws']:
                    billU.extra['laws'].append(laws_data)
        err = 10
        prnt('\npolicyArea')
        policyArea = billXML.find('policyArea')
        if policyArea:
            if 'subjects' not in billU.data:
                billU.data['subjects'] = []
            name = policyArea.find('name')
            try:
                if name.text not in billU.data['subjects']:
                    billU.data['subjects'].append(name.text)
                prnt(f'name: {name.text}')
            except Exception as e:
                prnt(str(e))
        err = 11
        prnt('\nsubjects')
        subjects = billXML.find('subjects')
        if subjects:
            if 'subjects' not in billU.data:
                billU.data['subjects'] = []
            legislativeSubjects = subjects.find('legislativeSubjects')
            if legislativeSubjects:
                for i in legislativeSubjects.findall('item'):
                    prnt('---')
                    name = i.find('name')
                    try:
                        if name.text not in billU.data['subjects']:
                            billU.data['subjects'].append(name.text)
                        prnt(f'name: {name.text}')
                    except Exception as e:
                        prnt(str(e))
            # policyArea = subjects.find('policyArea')
            # if policyArea:
            #     name = policyArea.find('name')
            #     try:
            #         # billU.data['subjects'].append(name.text)
            #         prnt(f'name: {name.text}')
            #     except Exception as e:
            #         prnt(str(e))
        err = 12
        prnt('\nsummaries')
        summaries = billXML.find('summaries')
        if summaries:
            for s in summaries.findall('summary')[-1:]:
                prnt('---')
                versionCode = s.find('versionCode')
                actionDate = s.find('actionDate')
                actionDesc = s.find('actionDesc')
                updateDate = s.find('updateDate')
                text = s.find('text')
                try:
                    dt = timezonify('est', datetime.datetime.strptime(f'{actionDate.text}', '%Y-%m-%d'))
                    billU.data['Summary'] = text.text
                    billU.data['summary_dt'] = dt_to_string(dt)
                    billU.data['summary_description'] = actionDesc.text
                    prnt(f'versionCode: {versionCode.text}')
                    prnt(f'actionDate: {actionDate.text}')
                    prnt(f'actionDesc: {actionDesc.text}')
                    prnt(f'updateDate: {updateDate.text}')
                    prnt(f'text: {text.text}')
                except Exception as e:
                    prnt(str(e))
        err = 13
        prnt('\ntitle')
        title = billXML.find('title')
        bill.Title = title.text
        titles = billXML.find('titles')
        if titles:
            for i in titles.findall('item'):
                prnt('---')
                titleType = i.find('titleType')
                title = i.find('title')
                chamberCode = i.find('chamberCode')
                chamberName = i.find('chamberName')
                billTextVersionName = i.find('billTextVersionName')
                billTextVersionCode = i.find('billTextVersionCode')
                try:
                    prnt(f'titleType: {titleType.text}')
                    prnt(f'title: {title.text}')
                    prnt(f'billTextVersionName: {billTextVersionName.text}')
                    prnt(f'billTextVersionCode: {billTextVersionCode.text}')
                    prnt(f'chamberCode: {chamberCode.text}')
                    prnt(f'chamberName: {chamberName.text}')
                except Exception as e:
                    prnt(str(e))
        err = 14  
        prnt('\namendments')
        amendments = billXML.find('amendments')
        if amendments:
            for a in amendments.findall('amendment'):
                prnt('---')
                number = a.find('number')
                congress = a.find('congress')
                type = a.find('type')
                description = a.find('description')
                updateDate = a.find('updateDate')
                latestAction = a.find('latestAction')

                xml_str = ET.tostring(a, encoding='unicode')
                amendments_data = xmltodict.parse(xml_str)
                prntn("amendments_data",amendments_data)
                if 'item' in amendments_data:
                    amendments_data = amendments_data['item']

                if not billU.extra:
                    billU.extra = {}
                if 'amendments' not in billU.extra:
                    billU.extra['amendments'] = []
                if amendments_data not in billU.extra['amendments']:
                    billU.extra['amendments'].append(amendments_data)

                if latestAction:
                    actionDate = latestAction.find('actionDate')
                    text = latestAction.find('text')
                    actionTime = latestAction.find('actionTime')
                    try:
                        prnt(f'number: {number.text}')
                        prnt(f'congress: {congress.text}')
                        prnt(f'type: {type.text}')
                        prnt(f'description: {description.text}')
                        prnt(f'updateDate: {updateDate.text}')
                        prnt(f'latestAction: {latestAction.text}')
                        prnt(f'actionDate: {actionDate.text}')
                        prnt(f'text: {text.text}')
                        prnt(f'actionTime: {actionTime.text}')
                    except Exception as e:
                        prnt(str(e))

                sponsors = a.find('sponsors')
                if sponsors:
                    for i in sponsors.findall('item'):
                        prnt('---')
                        bioguideId = i.find('bioguideId')
                        fullName = i.find('fullName')
                        firstName = i.find('firstName')
                        lastName = i.find('lastName')
                        middleName = i.find('middleName')
                        party = i.find('party')
                        state = i.find('state')
                        district = i.find('district')
                        try:
                            prnt(f'bioguideId: {bioguideId.text}')
                            prnt(f'fullName: {fullName.text}')
                            prnt(f'firstName: {firstName.text}')
                            prnt(f'lastName: {lastName.text}')
                            prnt(f'middleName: {middleName.text}')
                            prnt(f'party: {party.text}')
                            prnt(f'state: {state.text}')
                            prnt(f'district: {district.text}')
                        except Exception as e:
                            prnt(str(e))

                submittedDate = a.find('submittedDate')
                chamber = a.find('chamber')
                try:
                    prnt(f'submittedDate: {submittedDate.text}')
                    prnt(f'chamber: {chamber.text}')
                except Exception as e:
                    prnt(str(e))

                amendedBill = a.find('amendedBill')
                if amendedBill:
                    congress = amendedBill.find('congress')
                    type = amendedBill.find('type')
                    originChamber = amendedBill.find('originChamber')
                    originChamberCode = amendedBill.find('originChamberCode')
                    number = amendedBill.find('number')
                    title = amendedBill.find('title')
                    updateDateIncludingText = amendedBill.find('updateDateIncludingText')
                    try:
                        prnt(f'congress: {congress.text}')
                        prnt(f'type: {type.text}')
                        prnt(f'originChamber: {originChamber.text}')
                        prnt(f'originChamberCode: {originChamberCode.text}')
                        prnt(f'number: {number.text}')
                        prnt(f'title: {title.text}')
                        prnt(f'updateDateIncludingText: {updateDateIncludingText.text}')
                    except Exception as e:
                        prnt(str(e))

                links = a.find('links')
                if links:
                    for link in links.findall('link'):
                        prnt('---')
                        name = link.find('name')
                        url = link.find('url')
                        try:
                            prnt(f'name: {name.text}')
                            prnt(f'url: {url.text}')
                        except Exception as e:
                            prnt(str(e))

                actions = a.find('actions')
                if actions:
                    count = actions.find('count')
                    for action in actions.findall('actions'):
                        prnt('---')
                        for i in action.findall('item'):
                            prnt('---')
                            actionDate = i.find('actionDate')
                            actionTime = i.find('actionTime')
                            text = i.find('text')
                            type = i.find('type')
                            try:
                                actionCode = i.find('actionCode').text
                                prnt(f'actionDate: {actionDate.text}')
                                prnt(f'actionTime: {actionTime.text}')
                                prnt(f'actionCode: {actionCode}')
                                prnt(f'text: {text.text}')
                                prnt(f'type: {type.text}')
                            except Exception as e:
                                prnt(str(e))
                                actionCode = ''

                            sourceSystem = i.find('sourceSystem')
                            if sourceSystem:
                                name = sourceSystem.find('name')
                                code = sourceSystem.find('code')
                                try:
                                    prnt(f'name: {name.text}')
                                    prnt(f'systemCode: {systemCode.text}')
                                except Exception as e:
                                    prnt(str(e))
        err = 15
        prnt('\ntextVersions')
        def get_text(bill, billU, soup):
            prnt('gettext')
            import hashlib

            def section_code(text, length=7):
                # return as 7 char unique string
                hash_object = hashlib.sha256(text.encode())
                hash_int = int(hash_object.hexdigest(), 16)
                return str(hash_int % 10**7).zfill(length)
            

            body = soup.find('body')
            finalText = str(body)
            for s in body.find_all(class_='lbexTocSectionOLC'):
                finalText.replace(str(s),'')
            if not billU.extra:
                billU.extra = {}

            toc_d = []
            for s in body.find_all(class_='lbexHangWithMargin'):
                if 'SECTION ' in s.text or 'SEC. ' in s.text:
                    code = section_code(s.text)
                    x = str(s).find('class="')+len('class="')
                    m = str(s)[:x] + code + ' ' + str(s)[x:]
                    finalText = finalText.replace(str(s), m)
                    toc_d.append({s.text : {'code':code, 'html':m}})

            if toc_d == []:
                for s in body.find_all(class_='lbexHeaderAppropIntermediate'):
                    code = section_code(str(s))
                    x = str(s).find('class="')+len('class="')
                    m = str(s)[:x] + code + ' ' + str(s)[x:]
                    finalText = finalText.replace(str(s), m)
                    toc_d.append({s.text : {'code':code, 'html':m}})
            if toc_d == []:
                for s in body.find_all(class_='lbexTocSectionIRCBold'):
                    code = section_code(str(s))
                    x = str(s).find('class="')+len('class="')
                    m = str(s)[:x] + code + ' ' + str(s)[x:]
                    finalText = finalText.replace(str(s), m)
                    toc_d.append({s.text : {'code':code, 'html':m}})

            if finalText:
                billText = BillText.objects.filter(pointerId=bill.id, data__TextHtml=finalText).first()
                if not billText:
                    billText = BillText(pointerId=bill.id)
                    billText.data['TextHtml'] = finalText
                    billText.data['TextNav'] = toc_d
                    # billText.save()
            else:
                billText = None


            # billU.extra['TextHtml'] = finalText
            # billU.extra['TextNav'] = toc_d
            billU.data['has_text'] = True
            return bill, billU, billText


        textVersions = billXML.find('textVersions')
        if textVersions:
            textFound = False
            for i in textVersions.findall('item'):
                if textFound:
                    break
                prnt('---')
                actionType = i.find('type')
                date = i.find('date')
                # <type>Engrossed Amendment Senate</type>
                # <date>2020-11-16T05:00:00Z</date>
                dt = None
                if billU.extra and 'bill_text_version' in billU.extra and actionType is not None and billU.extra['bill_text_version'] == actionType.text:
                    textFound = True
                    break
                try:
                    dt = timezonify('est', datetime.datetime.strptime(date.text, "%Y-%m-%dT%H:%M:%SZ"))
                    prnt(f'actionType: {actionType.text}')
                    prnt(f'date: {date.text}')
                except Exception as e:
                    prnt(str(e))
                formats = i.find('formats')
                if formats:
                    for x in formats.findall('item'):
                        url = x.find('url')
                        try:
                            prnt('getting text', url.text)

                            if not driver:
                                script_test_error(special, "opening browser")
                                driver, driver_service = open_browser()
                            driver.get(url.text)
                            element_present = EC.presence_of_element_located((By.TAG_NAME, 'body'))
                            WebDriverWait(driver, 10).until(element_present)
                            # r = requests.get(url.text)
                            # soup = BeautifulSoup(r.content, 'lxml')
                            soup = BeautifulSoup(driver.page_source, 'html.parser')
                            bill, billU, billText = get_text(bill, billU, soup)
                            prnt(f'url: {url.text}')
                            if billText: 
                                billText.data['url'] = url.text
                                do_save = False
                                if billText.id == '0' or not billText.signature:
                                    do_save = True
                                if dt is not None:
                                    if 'date' not in billText.data or billText.data['date'] != dt_to_string(dt):
                                        # prnt('isdt',dt)
                                        billText.data['date'] = dt_to_string(dt)
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
                            break
                        except Exception as e:
                            prnt('bill text err 553', str(e))
                            logError('failed to get_text', code='65434', func='add_bill', extra={'err':str(e), 'url.text':url.text})
        updated_bill = False
        prnt('\n--latestaction')
        latestAction = billXML.find('latestAction')
        if latestAction:
            actionDate = latestAction.find('actionDate')
            text = latestAction.find('text')
            if text is not None:
                if 'LatestBillEvent' in billU.data and billU.data['LatestBillEvent'] != text.text:
                    updated_bill = True
                billU.data['LatestBillEvent'] = text.text
            if actionDate is not None:
                dt = timezonify('est', datetime.datetime.strptime(actionDate.text, '%Y-%m-%d'))
                billU.data['LatestBillEventDateTime'] = dt_to_string(dt)
                billU.DateTime = dt
            try:
                prnt(f'actionDate: {actionDate.text}')
                prnt(f'text: {text.text}')
            except Exception as e:
                prnt(str(e))
        err = 16
        # billU.data['last_updated'] = update_dt_to_string(dt)
        bill, billU, bill_is_new, log = save_and_return(bill, billU, log)
        if new_bill and bill.Person_obj:
            script_test_error(special, 'send alerts')
            notification, notificationU, notification_is_new = get_model_and_update('Notification', Title=f'{bill.Person_obj.get_field("FullName")} has sponsored bill {bill.NumberCode}', Link=str(bill.get_absolute_url()), targetUsers={'follow_person' : bill.Person_obj.id}, pointerId=bill.id, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
            notification, notificationU, notification_is_new, log = save_and_return(notification, notificationU, log)
        err = 17
        try:
            if updated_bill or new_bill:
                script_test_error(special, 'send alerts 2')
                if len(bill.Title) > 65:
                    title = bill.Title[:65] + '...'
                else:
                    title = bill.Title
                if billU.data['Status'] != 'Became Law':
                    if bill.Person_obj:
                        person_id = bill.Person_obj.id
                    else:
                        person_id = bill.SponsorCode
                    if UserData.objects.filter(Q(follow_topics__contains=bill.id)|Q(follow_topics__contains=person_id)).count() > 0:
                        notification, notificationU, notification_is_new = get_model_and_update('Notification', Title=f'Bill {bill.NumberCode} updated - {title}', Link=str(bill.get_absolute_url()), targetUsers={'follow_bill' : bill.id, 'follow_person' : person_id}, pointerId=bill.id, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
                        notification, notificationU, notification_is_new, log = save_and_return(notification, notificationU, log)
                elif 'Became Law' in billU.data['Status']:
                    notification, notificationU, notification_is_new = get_model_and_update('Notification', Title=f'Bill {bill.NumberCode} has become Law - {title}', Link=str(bill.get_absolute_url()), targetUsers={'all_in_country' : country.id}, pointerId=bill.id, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
                    notification, notificationU, notification_is_new, log = save_and_return(notification, notificationU, log)
        except Exception as e:
            prnt('create notify fail4344',str(e))
            logError(str(e), code='875167', func='add_bill')
            pass
        err = 'fini'
    except Exception as e:
        prnt('add_bill fail 371956',str(e))
        logError(e, code='68264', func=ref_func, region=country, extra={'url':url,'err':str(err)})

    return log, driver, driver_service



def get_bills2(special=None, dt=now_utc(), iden=None):
    func = 'get_bills'
    log = []
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')

    log = add_bills(log, func, gov, country, special=special)
    # try:
    #     close_browser(driver, driver_service)
    # except:
    #     pass
    return finishScript(log, gov, special)

def add_bills2(log, func, gov, country, targets=None, driver=None, special=None, dt=now_utc(), iden=None):
    script_test_error(special, f'add_bills {targets}')
    base_url = 'https://www.congress.gov'
    if targets:
        searchTerm = 'H.R.1'
        for t in targets:
            if not searchTerm:
                searchTerm = t
            else:
                searchTerm = searchTerm + '%2C+' + t
        # url = base_url + '/search?q={"congress":"%s","source":"legislation","search":"%s"}'%(gov.GovernmentNumber, target)
        # https://www.congress.gov/search?q={"congress":"118","source":"legislation","search":"S.4768,S.4765"}
        url = base_url + f'/quick-search/legislation?wordsPhrases=&wordVariants=on&congressGroups%5B0%5D=0&congresses%5B0%5D={gov.GovernmentNumber}&legislationNumbers={searchTerm}&legislativeAction=&sponsor=on&representative=&senator='
        # url = base_url + f'/quick-search/legislation?wordsPhrases=&wordVariants=on&congressGroups%5B0%5D=0&congresses%5B0%5D=118&legislationNumbers=hr.1%2C+h.r.7024&legislativeAction=&sponsor=on&representative=&senator='
    else:
        # url = base_url + f'/search?q=%7B%22source%22%3A%22legislation%22%2C%22search%22%3A%22congressId%3A{gov.GovernmentNumber}+AND+billStatus%3A%5C%22Introduced%5C%22%22%7D&pageSort=latestAction'
        url = base_url + f'/search?q=%7B%22source%22%3A%22legislation%22%2C%22search%22%3A%22congressId%3A{gov.GovernmentNumber}%22%7D&pageSort=latestAction%3Adesc'
        # url = base_url + '/search?q={"source":"legislation","search":"congressId:%s AND billStatus:\"Introduced\""}&pageSort=latestAction' %(gov.GovernmentNumber)
        # url = base_url + '/search?q={"source":"legislation","search":"congressId:118 AND billStatus:\"Introduced\""}&pageSort=latestAction'
        # url = 'https://www.congress.gov/search?q=%7B%22source%22%3A%22legislation%22%2C%22search%22%3A%22congressId%3A118%22%7D&pageSort=latestAction'
        # url = base_url + '/search?q={%22congress%22:%22118%22,%22source%22:%22legislation%22,%22search%22:%22congressId:%s%20AND%20billStatus:\%22Introduced\%22%22}&pageSort=latestAction%3Adesc' %(gov.GovernmentNumber)
    
        # 'https://www.congress.gov/advanced-search?raw=%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22is%22%2C%22value%22%3A%22118%22%7D%7D%5D%7D%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22contains%22%2C%22value%22%3A%22%22%7D%7D%5D%7D%5D&pageSort=latestAction%3Adesc'
    
    
    script_test_error(special, url)
    foundBills = []
    bill = None
    get_updates = []
    try:
        if not driver:
            script_test_error(special, "opening browser")
            driver, driver_service = open_browser()
            # chrome_options = Options()
            # chrome_options.add_argument('--no-sandbox')
            # # chrome_options.add_argument("--headless")
            # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
            # driver = webdriver.Chrome(options=chrome_options)
            # caps = DesiredCapabilities().CHROME
            # caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
            # driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
        driver.get(url)
        script_test_error(special, 'laoded')
        # time.sleep(5)
        element_present = EC.presence_of_element_located((By.CLASS_NAME, 'basic-search-results-lists'))
        WebDriverWait(driver, 10).until(element_present)
        script_test_error(special, 'ready')
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # time.sleep(5)
        def get_text(bill, billU, bill_is_new, link):
            script_test_error(special, f'get_text {link}')
            time.sleep(10)
            driver.get(base_url + link)
            element_present = EC.presence_of_element_located((By.ID, 'content'))
            WebDriverWait(driver, 10).until(element_present)
            # prnt('ready')
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            if 'amendment' in link.lower() or '/text' not in link.lower():
                if 'amendment' in link.lower():
                    # try:
                    div = soup.find('div', {'class':'main-wrapper'})
                    h2 = div.find('h2', {'class':'primary'})
                    summary = str(div).replace(str(h2), '').replace('h3','p').replace('Shown Here:<br/>','').strip()
                    billU.data['Summary'] = summary
                else:
                    try:
                        div = soup.find('div', {'id':'bill-summary'})
                        selector = div.find('div', {'class':'cdg-summary-wrapper'})
                        summary = str(div).replace(str(selector), '').replace('h3','p').replace('Shown Here:<br/>','').strip()
                        for p in div.find_all('p'):
                            if bill.Title in p.text:
                                summary = summary.replace(str(p),'')
                    except Exception as e:
                        # prnt(str(e))
                        div = soup.find('div', {'id':'main'})
                        summary = div.text.strip()
                    prnt(summary[:750])
                    billU.data['Summary'] = summary

                tabs = soup.find('ul', {'class':'tabs_links'})
                lis = tabs.find_all('li')
                for li in lis:
                    if 'Text' in li.text:
                        a = li.find('a')
                        script_test_error(special, base_url + a['href'])
                        time.sleep(1)
                        driver.get(base_url + a['href'])

                        element_present = EC.presence_of_element_located((By.ID, 'main'))
                        WebDriverWait(driver, 10).until(element_present)
                        # prnt('ready')
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        break

            try:
                div = soup.find('div', {'id':'bill-summary'})
                selector = div.find('div', {'class':'cdg-summary-wrapper'})
                finalText = str(div).replace(str(selector), '')
                for i in div.find_all(class_='lbexBlockNeutral'):
                    finalText = finalText.replace(str(i),'')

            except Exception as e:
                # prnt(str(e))
                div = soup.find('div', {'id':'main'})
                h2 = div.find('h2')
                finalText = div.text.replace(h2.text, '').strip()
            prnt()
            script_test_error(special, f'finalText {finalText[:50]}', wait=2)
            billU.text['TextHtml'] = finalText.replace('Shown Here:<br/>','')

            toc_d = []
            for s in div.find_all(class_='lbexHangWithMargin'):
                if 'SECTION ' in s.text or 'SEC. ' in s.text:
                    toc_d.append({s.text : str(s)})

            if toc_d == []:
                for s in div.find_all(class_='lbexHeaderAppropIntermediate'):
                    toc_d.append({s.text : str(s)})
            if toc_d == []:
                for s in div.find_all(class_='lbexTocSectionIRCBold'):
                    toc_d.append({s.text : str(s)})

            # prnt('toc_d',toc_d)
            billU.extra['TextNav'] = toc_d
            billU.data['has_text'] = True
            version = soup.find('select', {'id':'textVersion'})
            script_test_error(special, f'version {version}')
            if version:
                options = version.find_all('option')
                billU.data['bill_text_version'] = options[0].text
            return bill, billU, bill_is_new


        row = soup.find('ol', {'class':'basic-search-results-lists'})
        lis = row.find_all('li', {'class':'expanded'})
        n = 1
        fails = 0
        for li in lis:
            if fails >= 3:
                script_test_error(special, 'fail3-1')
                break
            try:
                script_test_error(special, n)
                n+=1
                new_bill = False
                # div = li.find('span', {'class':'visualIndicator'})
                # words = div.text.split(' ')
                # billType = ''
                # for word in words:
                #     billType = billType + word[0] + word[1:].lower()
                #     if len(words) > 1:
                #         billType = billType + ' '

                heading = li.find('span', {'class':'result-heading'})
                script_test_error(special, heading)
                ahref = heading.find('a')
                script_test_error(special, ahref)
                billCode = ahref.text
                if targets and billCode not in targets:
                    pass
                else:
                    billLink = ahref['href']
                    a = billLink.find('?')
                    billLink = base_url + billLink[:a]
                    chamber = 'None'
                    'JOINT RESOLUTION  S.J.Res.38'
                    'RESOLUTION S.Res.518 '
                    'RESOLUTION H.Res.956'
                    'JOINT RESOLUTION H.J.Res.98'
                    'LAW'
                    'BILL'
                    if 'H.R.' in ahref.text:
                        chamber = 'House'
                        billType = 'Bill'
                    elif 'H.Res.' in ahref.text:
                        chamber = 'House'
                        billType = 'Resolution'
                    elif 'H.Con.Res.' in ahref.text:
                        chamber = 'House'
                        billType = 'Concurrent Resolution'
                    elif 'H.Amdt.' in ahref.text:
                        chamber = 'House'
                        billType = 'Amendment'
                    elif 'S.Con.Res.' in ahref.text:
                        chamber = 'Senate'
                        billType = 'Concurrent Resolution'
                    elif 'S.Amdt.' in ahref.text:
                        chamber = 'Senate'
                        billType = 'Amendment'
                    elif 'H.J.Res.' in ahref.text:
                        chamber = 'House'
                        billType = 'Joint Resolution'
                    elif 'S.J.Res' in ahref.text:
                        chamber = 'Senate'
                        billType = 'Joint Resolution'
                    elif 'S.Res' in ahref.text:
                        chamber = 'Senate'
                        billType = 'Resolution'
                    elif 'S.' in ahref.text:
                        chamber = 'Senate'
                        billType = 'Bill'
                    script_test_error(special, chamber + billType)
                    script_test_error(special, ahref.text)
                    script_test_error(special, ahref['href'])
                    header = heading.text.replace(ahref.text,'').replace(' — ','')
                    script_test_error(special, header)
                    x = header.find(' ')
                    cong = header[:x].replace('st','').replace('nd','').replace('rd','').replace('th','')
                    cong = int(cong)
                    y = header.find(' (')
                    year = header[y+1:].replace('(','').replace(')','').strip()
                    try:
                        title = li.find('span', {'class':'result-title'}).text.strip()
                        script_test_error(special, title)
                    except:
                        title = chamber + ' ' + billType + ' ' + ahref.text
                    items = li.find_all('span', {'class':'result-item'})
                    bill, billU, bill_is_new = get_model_and_update('Bill', Government_obj=gov, Country_obj=country, Region_obj=country, Chamber=chamber, Title=title, NumberCode=billCode, BillDocumentTypeName=billType)
                    bill.LegisLink = billLink
                    z = ahref.text.rfind('.')+1
                    bill.Number = ahref.text[z:]
                    bill.NumberPrefix = ahref.text[:z]
                    if bill_is_new:
                        billU.data['Status'] = 'Introduced'
                        new_bill = True
                        billU.data['billVersions'] = []
                            
                    old_latest = ''
                    fetchText = False
                    latestVersion = None
                    for item in items:
                        if 'Sponsor:' in item.text:
                            script_test_error(special, 'get sponsor')
                            sponsorItem = item
                            sponsors = sponsorItem.find_all('a')
                            sponsor = sponsors[0]
                            script_test_error(special, sponsor.text)
                            sponsorLink = sponsor['href']
                            '''https://www.congress.gov/member/david-trone/T000483?q=%7B%22search%22%3A%22congressId%3A118+AND+billStatus%3A%5C%22Introduced%5C%22%22%7D'''
                            script_test_error(special, sponsorLink)
                            q = sponsorLink.find('?q=')
                            if q > 0:
                                w = sponsorLink[:q].rfind('/')
                                code = sponsorLink[w+1:q]
                                sponsorLink = sponsorLink[:q]
                            else:
                                w = sponsorLink.rfind('/')
                                code = sponsorLink[w+1:]
                            script_test_error(special, code)
                            if not bill.Person_obj:
                                sponsorPerson = Person.objects.filter(GovIden=code, Country_obj=country).first()
                                if sponsorPerson:
                                    bill.Person_obj = sponsorPerson
                                    bill.SponsorPersonName = sponsorPerson.FullName
                                    script_test_error(special, sponsorPerson)
                                else:
                                    # script_test_error(special)
                                    x = sponsor.text.find(' [')
                                    sponsorName = sponsor.text[:x]
                                    bill.SponsorPersonName = sponsorName
                                    script_test_error(special, f'sponsorName: {sponsorName}')
                            script_test_error(special, sponsorItem.text)
                            if not bill.Person_obj:
                                time.sleep(5)
                            txt = sponsorItem.text.replace('Sponsor: ', '').replace(sponsor.text,'')
                            try:
                                cosponsors = sponsors[1]
                                script_test_error(special, f"cosposonors: {cosponsors.text}--{cosponsors['href']}")
                                txt = txt.replace('Cosponsors: ', '').replace('(%s)'%(cosponsors.text),'')
                                if not 'cosponsors' in billU.data:
                                    billU.data['cosponsors'] = []
                            except:
                                cosponsors = None
                            date_txt = txt.replace('(','').replace(')','').replace('Introduced ','').replace('Private Legislation','').replace('Offered ','').replace('Sponsor:\n', '').strip()
                            script_test_error(special, '--%s--' %(date_txt))
                            day = timezonify('est', datetime.datetime.strptime(date_txt, '%m/%d/%Y'))
                            script_test_error(special, day)
                            bill.Started = day
                            if bill_is_new:
                                bill.save()
                    
                            try:
                                if cosponsors and 'cosponsors' in billU.data and int(cosponsors.text) != len(billU.data['cosponsors']):
                                    prnt('cosponsors',cosponsors)
                                    prnt('int(cosponsors.text)',int(cosponsors.text))
                                    prnt("len(billU.data['cosponsors'])",len(billU.data['cosponsors']))
                                    script_test_error(special, base_url + cosponsors['href'])
                                    time.sleep(2)
                                    driver.get(base_url + cosponsors['href'])
                                    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
                                    WebDriverWait(driver, 10).until(element_present)
                                    cosponsor_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    div = cosponsor_soup.find('div', {'id':'main'})
                                    trs = div.find_all('tr')
                                    for tr in trs:
                                        try:
                                            td = tr.find('td')
                                            a = td.find('a')['href']
                                            x = a.rfind('/')
                                            code = a[x+1:]
                                            script_test_error(special, code)
                                            coPerson = Person.objects.filter(GovIden=code, Country_obj=country).first()
                                            if coPerson:
                                                script_test_error(special, coPerson)
                                                c = {'obj_type':'Person', 'obj_id':coPerson.id, 'fullName':coPerson.FullName, 'localLink':coPerson.get_absolute_url()}
                                                if c not in billU.data['cosponsors']:
                                                    billU.data['cosponsors'].append(c)
                                                # if coPerson not in bill.CoSponsor_objs.all():
                                                #     bill.CoSponsor_objs.add(coPerson)
                                            
                                        except Exception as e:
                                            script_test_error(special, str(e))

                            except Exception as e:
                                script_test_error(special, str(e))
                        elif 'Committees:' in item.text:
                            script_test_error(special, 'get committees')
                            committeeItem = item
                            committees = committeeItem.text.replace('Committees: ','')
                            if ';' in committees:
                                coms = committees.split(';')
                            else:
                                coms = ['%s' %(committees)]
                            org = None
                            billU.data['inCommittees'] = []
                            for c in coms:
                                # prnt('c',c)
                                if 'House - ' in c:
                                    org = 'House'
                                    c_title = c.replace('House - ','').replace(';','').strip()
                                elif 'Senate - ' in c:
                                    org = 'Senate'
                                    c_title = c.replace('Senate - ','').replace(';','').strip()
                                script_test_error(special, f'{org} + {c_title}')
                                committee, committeeU, committee_is_new = get_model_and_update('Committee', Title=c_title, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country)
                                committee, committeeU, committee_is_new, log = save_and_return(committee, committeeU, log)
                                # try:
                                #     committee = Committee.objects.filter(Title=c_title, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country)[0]
                                # except:
                                #     committee = Committee(Title=c_title, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country)
                                #     committee.save()
                                #     committee.create_post()
                                billU.data['inCommittees'].append(committee.id)
                        elif 'Committee Report:' in item.text:
                            script_test_error(special, 'get report')
                            committeeReport = item
                            reportLinks = committeeReport.find_all('a')
                            for rLink in reportLinks:
                                script_test_error(special, f'report {rLink.text}')
                                script_test_error(special, rLink['href'])
                                meetingLink = base_url + rLink['href']
                                meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', meeting_type='Committee', Title=rLink.text.strip(), GovPage=meetingLink, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country)
                                if meeting_is_new:
                                # try:
                                #     comMeetting = CommitteeMeeting.objects.filter(govURL=meetingLink)[0]
                                # except:
                                #     comMeetting = CommitteeMeeting(govURL=meetingLink, ParliamentNumber=congress.ParliamentNumber, SessionNumber=congress.SessionNumber)
                                #     comMeetting.save()
                                #     comMeetting.create_post()
                                    script_test_error(special, meetingLink)
                                    time.sleep(1)
                                    driver.get(meetingLink)
                                    element_present = EC.presence_of_element_located((By.ID, 'report'))
                                    WebDriverWait(driver, 10).until(element_present)

                                    report_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    overview = report_soup.find('div', {'class':'overview'})
                                    trs = overview.find_all('tr')
                                    for tr in trs:
                                        if 'Accompanies' in tr.text:
                                            NumberCode = tr.find('a').text
                                            script_test_error(special, NumberCode)
                                            bill = Bill.objects.filter(Government_obj=gov, Country_obj=country, NumberCode=NumberCode).first()
                                            if bill:
                                                meetingU.data['bills'] = [bill.id]
                                        elif 'Committees' in tr.text:
                                            a = tr.find('a')
                                            title = a.text
                                            org = None
                                            if 'House' in title:
                                                org = 'House'
                                            elif 'Senate' in title:
                                                org = 'Senate'
                                            title = title.replace('House ','').replace('Senate ','').replace(' Committee','')

                                            committee2, committee2U, committee2_is_new = get_model_and_update('Committee', Title=title, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country)
                                            committee2, committee2U, committee2_is_new, log = save_and_return(committee2, committee2U, log)
                                            if committee2_is_new:
                                                committee2.govURL = base_url + a['href']
                                            else:
                                                committee2U.data['govURL'] = base_url + a['href']
                                            # try:
                                            #     committee = Committee.objects.filter(title=title, Organization=org)[0]
                                            #     if not committee.govURL:
                                            #         committee.govURL = base_url + a['href']
                                            #         committee.save()
                                            # except:
                                            #     committee = Committee(Title=title, Organization=org, ParliamentNumber=congress.ParliamentNumber, SessionNumber=congress.SessionNumber)
                                            #     committee.save()
                                            #     committee.create_post()
                                            meeting.Committee_obj = committee2
                                            # comMeetting.committee = committee
                                            # comMeetting.Organization = org
                                            script_test_error(special, f'{org} - {title}')
                                    div = report_soup.find('div', {'id':'report'})
                                    pre = div.find('pre')
                                    # prnt(pre)
                                    meetingU.data['Report'] = str(pre)
                                    # comMeetting.save()
                                    meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, meeting_is_new, log)
                        elif 'Latest Action:' in item.text:
                            script_test_error(special, 'get action')
                            latest = item
                            actionsLinks = latest.find_all('a')
                            for alink in actionsLinks:
                                if 'Actions' in alink.text:
                                    actionsLink = alink
                            txt = latest.text.replace('Latest Action:','').replace('(All Actions)','').strip()
                            script_test_error(special, txt)
                            if '(Roll no' in txt:
                                z = txt.find('(Roll no')
                                txt = txt[:z].strip()
                            a = txt.find(' - ')
                            prnt('a',a)
                            if a and a > 0 and a < 10:
                                b = txt[a+3:].find(' ')
                                dt = txt[a+3:a+3+b]
                            else:
                                b = txt.find(' ')
                                dt = txt[:b]
                            script_test_error(special, f'dt: {dt.strip()}')
                            try:
                                day = timezonify('est', datetime.datetime.strptime(dt.strip(), '%m/%d/%Y'))
                            except:
                                day = timezonify('est', datetime.datetime.strptime(dt.strip(), '%m/%d/%y'))
                            script_test_error(special, f'latest_day: {day}')
                            # bill.LatestBillEventDateTime = day
                            billU.data['LatestBillEventDateTime'] = dt_to_string(day)
                            # if bill_is_new:
                            #     bill.DateTime = day
                            latest = txt.replace(dt,'').strip()
                            try:
                                old_latest = billU.data['LatestBillEvent']
                            except:
                                old_latest = None
                            billU.data['LatestBillEvent'] = latest
                            if old_latest != latest or bill_is_new:
                                billU.data['DateTime'] = dt_to_string(day)
                            # if '...' in txt or old_latest != latest or bill_is_new:
                                # if base_url not in actionsLink['href']:
                                #     actions_url = base_url + actionsLink['href']
                                # else:
                                #     actions_url = actionsLink['href']
                                if 'all-actions' in actionsLink['href']:
                                    actions_url = base_url + actionsLink['href']
                                    option = 1
                                elif 'actions' in actionsLink['href']:
                                    actions_url = base_url + actionsLink['href']
                                    option = 2
                                else:
                                    actions_url = bill.LegisLink + '/all-actions'
                                    option = 1
                                script_test_error(special, actions_url)
                                time.sleep(1)
                                driver.get(actions_url)
                                script_test_error(special, 'loaded')
                                if option == 1:
                                    element_present = EC.presence_of_element_located((By.ID, 'main'))
                                    WebDriverWait(driver, 10).until(element_present)
                                    script_test_error(special, 'ready')
                                    actions_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    main = actions_soup.find('div', {'id':'main'})
                                elif option == 2:
                                    element_present = EC.presence_of_element_located((By.ID, 'content'))
                                    WebDriverWait(driver, 10).until(element_present)
                                    script_test_error(special, 'ready')
                                    actions_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    main = actions_soup.find('div', {'class':'main-wrapper'})

                                tbody = main.find('tbody')
                                trs = tbody.find_all('tr')
                                for tr in reversed(trs):
                                    # prnt(tr)
                                    dt = tr.find('td', {'class':'date'}).text
                                    # 07/11/2024-11:28am
                                    prnt(dt)
                                    try:
                                        date = timezonify('est', datetime.datetime.strptime(dt.strip(), '%m/%d/%Y-%I:%M%p'))
                                    except:
                                        date = timezonify('est', datetime.datetime.strptime(dt.strip(), '%m/%d/%Y'))
                                    script_test_error(special, date)
                                    org = bill.Chamber
                                    actions = tr.find('td', {'class':'actions'})
                                    txt = actions.text.strip()
                                    try:
                                        span = actions.find('span')
                                        if 'House' in span.text:
                                            org = 'House'
                                        elif 'Senate' in span.text:
                                            org = 'Senate'
                                        txt = actions.text.replace(span.text,'').strip()
                                        script_test_error(special, span.text.strip())
                                        if span.text:
                                            txt = txt + '\n' + span.text.strip()
                                    except:
                                        pass
                                    script_test_error(special, txt)
                                    script_test_error(special, '')
                                    billAction = GenericModel.objects.filter(type='BillAction', pointerId=bill.id, DateTime=date, Text__contains={'Text': txt}, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country).first()
                                    if not billAction:
                                        billAction = GenericModel(type='BillAction', func=func, pointerId=bill.id, DateTime=date, Text={'Text': txt, 'Code': bill.NumberCode}, Chamber=org, Government_obj=gov, Country_obj=country, Region_obj=country)
                                        billAction.save()
                                        log.updateShare(billAction)
                                        script_test_error(special, 'created bill action\n')
                                if bill_is_new:
                                    tertiary_sections = actions_soup.find_all('div', {'class':'tertiary_section'})
                                    script_test_error(special, f'tertiary_sections: {len(tertiary_sections)}')
                                    for t in tertiary_sections:
                                        if 'Policy Area:' in t.text:
                                            try:
                                                subject = t.find_all('li')[0].text.strip()
                                                subjects = [subject]
                                                a = t.find('a')
                                                script_test_error(special, a['href'])
                                                if a and 'subjects' in a['href']:
                                                    script_test_error(special, base_url + a['href'])
                                                    time.sleep(1)
                                                    driver.get(base_url + a['href'])
                                                    element_present = EC.presence_of_element_located((By.ID, 'main'))
                                                    WebDriverWait(driver, 10).until(element_present)
                                                    subjects_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                                    main = subjects_soup.find('div', {'id':'main'})
                                                    lis = main.find_all('li')
                                                    for i in lis:
                                                        subjects.append(i.text.strip())
                                                # bill.Subjects = json.dumps(subjects)
                                                billU.data['subjects'] = subjects
                                                script_test_error(special, f'subjects: {subjects}')
                                                break
                                            except Exception as e:
                                                script_test_error(special, str(e))

                                    script_test_error(special, '', wait=1)
                        elif 'Amends Bill' in item.text:
                            a = item.find('a')
                            href = a['href']
                            z = href.find('?')
                            relatedBillLink = base_url + href[:z]
                            billU.data['relatedBills'] = [{'NumberCode':a.text.strip(), 'link':relatedBillLink}]
                            rBill = Bill.objects.filter(Country_obj=country, LegisLink=relatedBillLink).first()
                            if rBill:
                                billU.data['relatedBills'][0]['localLink'] = rBill.get_absolute_url()
                                billU.data['relatedBills'][0]['obj_id'] = rBill.id
                        elif 'Tracker:' in item.text:
                            script_test_error(special, 'tracker')
                            trackerItem = item
                            p = trackerItem.find('p', {'class':'hide_fromsighted'})
                            script_test_error(special, p.text)
                            
                            current_status = p.text.replace('This bill has the status ','')

                            if 'billVersions' in billU.data:
                                versionHistory = billU.data['billVersions']
                            else:
                                versionHistory = None
                            billU.data['billVersions'] = []
                            script_test_error(special, f'versionHistory {versionHistory}')
                            stat_leg = trackerItem.find('ol', {'class':'stat_leg'})
                            # prnt('stat_leg',stat_leg)
                            ordered_list = stat_leg.find_all('li')
                            for i in ordered_list:
                                # prnt('i',i)
                                current = False
                                officialStatus = None
                                try:
                                    status = i.get('class')[0]
                                    script_test_error(special, f'status {status}')
                                    try:
                                        x = i.find('div', {'class':'sol-step-info'})
                                        version = i.text.replace(x.text,'')
                                    except:
                                        version = i.text
                                except:
                                    status = None
                                    version = i.text

                                script_test_error(special, f'version {version}')
                                if status == 'selected':
                                    latestVersion = version
                                    # billU.data['current_version'] = version
                                    billU.data['DateTime'] = dt_to_string(day)
                                    started_dt = dt_to_string(day)
                                    completed_dt = None
                                    current = True
                                    officialStatus = 'Current'
                                    # billV, billVU, billVData, billV_is_new = get_model_and_update('BillVersion', Bill_obj=bill, Version=version, NumberCode=bill.NumberCode, Government_obj=gov, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
                                    # if billV_is_new:
                                    #     billV.DateTime = day
                                    # billV, billVU, billVData, billV_is_new, log = save_and_return(billV, billVU, billVData, billV_is_new, log)
                                elif status == 'passed':
                                    officialStatus = 'Passed'
                                    completed_dt = dt_to_string(day)
                                    started_dt = None
                                else:
                                    started_dt = None
                                    completed_dt = None
                                found = False
                                if versionHistory:
                                    for v in versionHistory:
                                        script_test_error(special, v)
                                        if v['version'] == version:
                                            v['current'] = current
                                            if officialStatus:
                                                v['status'] = officialStatus
                                            if status == 'passed' and not v['completed_dt']:
                                                v['completed_dt'] = dt_to_string(day)
                                            elif status == 'selected' and not v['started_dt']:
                                                v['started_dt'] = dt_to_string(day)
                                            billU.data['billVersions'].append(v)
                                            found = True
                                            break
                                        found = False
                                script_test_error(special, 'next')
                                d = version.replace(' ', '') + '_DateTime'
                                script_test_error(special, d)
                                if not found:
                                    billU.data['billVersions'].append({'version':version, 'current':current, 'status':officialStatus, 'started_dt':started_dt, 'completed_dt':completed_dt})

                                if status == 'passed' and d not in billU.data or status == 'selected' and d not in billU.data:
                                    billU.data[d] = dt_to_string(day)
                                    # currentize_version(bill, version, day, log)
                            if 'current_version' not in billU.data:
                                billU.data['current_version'] = None
                            if latestVersion and billU.data['current_version'] != latestVersion:
                                billU.data['current_version'] = latestVersion
                                updated = True
                                prnt('updated', latestVersion, billU.data['current_version'])
                            else:
                                updated = False

                    if 'fail' not in str(latestVersion).lower() and 'veto' not in str(latestVersion).lower() and updated:
                        if bill.id == '0':
                            bill.save()
                            # bill, billU, bill_is_new , log = save_and_return(bill, billU, bill_is_new , log)
                        get_updates.append(bill.id)
                    #     billV, billVU, billVData, billV_is_new = get_model_and_update('BillVersion', Bill_obj=bill, Version=latestVersion, Government_obj=gov, Country_obj=country, Region_obj=country)
                    #     possible1 = '''A summary is in progress'''
                    #     possible2 = '''after text becomes available'''
                    #     possible3 = '''text has not been received'''
                    #     if not billV.TextHtml or possible1 in billV.Summary or possible2 in billV.TextHtml or possible3 in billV.TextHtml:
                    #         billV, billVU, billVData, billV_is_new = get_text(billV, billVU, billVData, billV_is_new, billLink)
                    #     prnt('saving bill')
                    #     billV, billVU, billVData, billV_is_new, log = save_and_return(billV, billVU, billVData, billV_is_new, log)

                    # bill.save()
                    # bill.update_post_time()
                    # from blockchain.models import convert_to_dict
                    # prnt(convert_to_dict(bill))
                    # prnt(bill_is_new)
                    # prnt('----------------')
                    bill, billU, bill_is_new, log = save_and_return(bill, billU, bill_is_new , log)
                    script_test_error(special, f'finish bill {bill}\n')
                    if not targets and new_bill and bill.Person_obj:
                        script_test_error(special, 'send alerts')
                        notification, notificationU, notification_is_new = get_model_and_update('Notification', Title=f'{bill.Person_obj.FullName} has sponsored bill {bill.NumberCode}', Link=str(bill.get_absolute_url()), targetUsers={'follow_person' : bill.Person_obj.id}, pointerId=bill.id, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
                        notification, notificationU, notification_is_new, log = save_and_return(notification, notificationU, log)

                    try:
                        if not targets:
                            if updated or new_bill:
                                script_test_error(special, 'send alerts 2')
                                if billU.data['Status'] != 'Became Law':
                                    if User.objects.filter(follow_Bill_objs=bill).count() > 0:
                                        notification, notificationU, notification_is_new = get_model_and_update('Notification', Title=f'Bill {bill.NumberCode} updated - {bill.Title}', Link=str(bill.get_absolute_url()), targetUsers={'follow_bill' : bill.id}, pointerId=bill.id, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
                                        notification, notificationU, notification_is_new, log = save_and_return(notification, notificationU, log)
                                elif 'Became Law' in billU.data['Status']:
                                    notification, notificationU, notification_is_new = get_model_and_update('Notification', Title=f'Bill {bill.NumberCode} has become Law - {bill.Title}', Link=str(bill.get_absolute_url()), targetUsers={'all_in_country' : country.id}, pointerId=bill.id, Country_obj=country, Region_obj=country, Chamber=bill.Chamber)
                                    notification, notificationU, notification_is_new, log = save_and_return(notification, notificationU, log)
                    except:
                        pass

                    # if targets:
                    foundBills.append(bill)
                    # prnt('fin bill', billU.data['billVersions'])
                    # from blockchain.models import convert_to_dict
                    # prnt(convert_to_dict(bill))
                    # prnt(bill_is_new)
                    # time.sleep(5)
            except Exception as e:
                script_test_error(special, f'oops {str(e)}', wait=7)
                fails += 1
    except Exception as e:
        script_test_error(special, f'oops2 {str(e)}', wait=7)
        # time.sleep(5)
        # close_browser(driver, driver_service)
    prnt('FOUNDBILLS:\n',foundBills)
    prnt('getupdates',get_updates)
    time.sleep(10)
    if fails >= 3:
        script_test_error(special, f'fail wait 30')
        time.sleep(30)
    fails = 0
    try:
        if targets:
            searchTerm = ''
            for b in foundBills:
                if not searchTerm:
                    searchTerm = b.NumberCode
                else:
                    searchTerm = searchTerm + '%2C+' + b.NumberCode
            hasTextUrl = base_url + f'/quick-search/legislation-text?wordsPhrases=&congressGroups%5B0%5D=0&congresses%5B0%5D={gov.GovernmentNumber}&legislationNumbers={searchTerm}&billTextVersionTypes%5B0%5D=all&pageSort=date%3Adesc'
        # hasTextUrl = base_url + f'/quick-search/legislation-text?wordsPhrases=&congressGroups%5B0%5D=0&congresses%5B0%5D=118&legislationNumbers=H.R.6213.RH%2C+H.Res.1389.IH&billTextVersionTypes%5B0%5D=all&pageSort=date%3Adesc'
        else:
            hasTextUrl = base_url + f'/quick-search/legislation-text?wordsPhrases=&congressGroups%5B0%5D=0&congresses%5B0%5D={gov.GovernmentNumber}&legislationNumbers=&chamberOfOriginHouse=on&chamberOfOriginSenate=on&billTextVersionTypes%5B0%5D=all&pageSort=date%3Adesc'
        script_test_error(special, hasTextUrl)
        time.sleep(1)
        driver.get(hasTextUrl)
        # script_test_error(special, 'laoded')
        element_present = EC.presence_of_element_located((By.CLASS_NAME, 'quick-search-results-lists'))
        WebDriverWait(driver, 10).until(element_present)
        # script_test_error(special, 'ready')
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        row = soup.find('ol', {'class':'quick-search-results-lists'})
        lis = row.find_all('li')
        script_test_error(special, f'llis {len(lis)}')
        for li in lis:
            if fails >= 3:
                script_test_error(special, 'fail3-2')
                break
            link = li.find('a')['href']
            # script_test_error(special, link)
            a = link.find('/text')
            billLink = base_url + link[:a]
            # script_test_error(special, f'billLink {billLink}')
            for b in foundBills:
                if b.LegisLink == billLink:
                    try:
                        # bill = Bill.objects.filter(Country_obj=country, LegisLink=billLink)[0]
                        bill, billU, bill_is_new = get_model_and_update('Bill', obj=b)
                        if 'TextHtml' not in billU.text or billU.text['TextHtml'] == '' or bill.id in get_updates:
                            if bill.id in get_updates:
                                prnt('bill is in get_updates')
                            if 'TextHtml' not in billU.text:
                                prnt('no text')
                            elif billU.text['TextHtml'] == '':
                                prnt('text blank')
                            script_test_error(special, 'get_text', wait=2)
                            try:
                                bill, billU, bill_is_new = get_text(bill, billU, bill_is_new, link[:a])
                                bill, billU, bill_is_new , log = save_and_return(bill, billU, log)
                                try:
                                    get_updates.remove(bill.id)
                                except:
                                    pass
                            except Exception as e:
                                script_test_error(special, str(e), wait=10)
                                fails += 1
                    except Exception as e:
                        script_test_error(special, str(e), wait=10)
                    break
    except Exception as e:
        script_test_error(special, str(e), wait=(10))
    # close_browser(driver, driver_service)
    if targets:
        return log, foundBills, fails, driver, driver_service
    else:
        close_browser(driver, driver_service)
        return log
# not used
def get_live_house_debates(special=None, dt=now_utc(), iden=None):
    func = 'get_live_house_debates'
    log = []
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')

    url = 'https://live.house.gov/'
    url = 'https://live.house.gov/?date=2024-07-25'

    try:
        driver, driver_service = open_browser(url)
        # prnt("opening browser")
        # chrome_options = Options()
        # chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
        # driver = webdriver.Chrome(options=chrome_options)
        # caps = DesiredCapabilities().CHROME
        # caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
        # driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
        # driver.get(url)

        element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="activity-table"]/tbody'))
        WebDriverWait(driver, 10).until(element_present)

        soup = BeautifulSoup(driver.page_source, 'html.parser')    
    except Exception as e:
        prnt(str(e))

    # close_browser(driver, driver_service)

    dt = soup.find('span', {'class':'display-date'})
    # WEDNESDAY, JANUARY 10, 2024
    today = timezonify('est', datetime.datetime.strptime(dt.text, '%A, %B %d, %Y'))
    # utc_datetime = pytz.utc.localize(today)
    # est = pytz.timezone('US/Eastern')
    # est_today = utc_datetime.astimezone(est)

    prnt(today)
    
    table = soup.find('table', {'id':'activity-table'})
    body = table.find('tbody')
    trs = body.find_all('tr')
    A = None
    started = False
    ended = False
    position = 0
    for tr in reversed(trs):
        position += 1
        tds = tr.find_all('td')
        timeText = tds[0].text
        # 10:00:09 AM
        item_time = timezonify('est', datetime.datetime.strptime(dt.text + '/' + timeText, '%A, %B %d, %Y/%I:%M:%S %p'))
        billText = tds[1].text
        content = tds[2].text
        prnt(item_time)
        # prnt(billText)
        # prnt(content)
        # prnt()
        if not A:
            A = Agenda.objects.filter(DateTime__gte=date, DateTime__lt=today + datetime.timedelta(days=1), Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country).first()
            if A:
                A, Au, A_is_new = get_model_and_update('Agenda', obj=A)
            else:
                A, Au, A_is_new = get_model_and_update('Agenda', DateTime=today, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                if A_is_new:
                    A, Au, A_is_new, log = save_and_return(A, Au, log)
                # Au.data['CurrentStatus'] = 'Adjourned'

        if 'convened' in content.lower():
            started = True
            Au.data['CurrentStatus'] = 'In Session'
        elif 'adjourn' in content.lower():
            ended = True
            Au.data['CurrentStatus'] = 'Adjourned'
            Au.data['EndDateTime'] = item_time
            # A.save()

        
        # agendaTime, agendaTimeU, agendaTimeData, agendaTime_is_new = get_model_and_update('AgendaTime', DateTime=item_time, Agenda_obj=A, Country_obj=country, Government_obj=gov, Chamber=A.Chamber, Region_obj=country)
        # agendaTime, agendaTimeU, agendaTimeData, agendaTime_is_new, log = save_and_return(agendaTime, agendaTimeU, agendaTimeData, agendaTime_is_new, log)

        agendaItem, agendaItemU, agendaItem_is_new = get_model_and_update('AgendaItem', position=position, Agenda_obj=A, DateTime=item_time, Country_obj=country, Government_obj=gov, Chamber=A.Chamber, Region_obj=country)

                    # try:
        # try:
        #     agendaItem = AgendaItem.objects.filter(agenda=A, date_time=item_time, gov_level=A.gov_level, organization=A.organization)[0]
        # except Exception as e:
        #     # prnt(str(e))
        #     agendaItem = AgendaItem(agenda=A, date_time=item_time, position=position, gov_level=A.gov_level, organization=A.organization)
        if billText:
            bill = Bill.objects.filter(NumberCode=billText, Government_obj=gov).first()
            if bill:
                agendaItem.Bill_obj = bill
        agendaItem, agendaItemU, agendaItem_is_new, log = save_and_return(agendaItem, agendaItemU, log)
        


    # try:
    #     meeting = Meeting.objects.filter(meeting_type='Debate', DateTime__gte=date_A, DateTime__lt=date_A + datetime.timedelta(days=1), Title=Title, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)[0]
    #     meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', obj=meeting)
    # except:
    #     meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', meeting_type='Debate', DateTime=date_time, Title=Title, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
    
    
    meeting = Meeting.objects.filter(Agenda_obj=A).first()
    if meeting:
        meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', obj=meeting)
    if started:
        if not meeting or meeting and meetingU.data['completed_model'] == False:
            text = driver.find_element(By.XPATH, '//*[@id="transcript"]')
            text.click()
            prnt('----clicked')
            element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="transcript-table"]/tbody'))
            WebDriverWait(driver, 10).until(element_present)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            close_browser(driver, driver_service)
            dt = soup.find('span', {'class':'display-date'})
            # WEDNESDAY, JANUARY 10, 2024
            date = timezonify('est', datetime.datetime.strptime(dt.text, '%A, %B %d, %Y'))
            prnt(date)
            table = soup.find('table', {'id':'transcript-table'})
            body = table.find('tbody')
            trs = body.find_all('tr')
            recognizedState = None
            theSpeaker = None
            meeting_terms = {}
            for tr in trs:
                ItemId = tr['data-uniqueid']
                tds = tr.find_all('td')
                name = tds[0].text
                timeText = tds[1].text
                # 10:00:09 AM
                date_time = timezonify('est', datetime.datetime.strptime(dt.text + '/' + timeText, '%A, %B %d, %Y/%I:%M:%S %p'))
                content = tds[2].text.replace('[...]', '')
                if 'RECOGNIZES' in content or 'RECOGNIZED' in content or 'RECOGNITION' in content:
                    for state in state_list.values():
                        if state.upper() in content:
                            recognizedState = state
                            break

                if not meeting:
                    meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', Agenda_obj=A, meeting_type='Debate', DateTime=date_time, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                    if meeting_is_new:
                        meetingU.data['completed_model'] = False
                        day = datetime.datetime.strftime(datetime.datetime.strptime(dt.text, '%A, %B %d, %Y'), '%Y-%B-%d')
                        meeting.GovPage = url + '?date=%s' %(day)
                        meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)

                prnt(date_time)
                person = None
                first_name = None
                last_name = None
                title = None
                if '. ' in name:
                    a = name.find('. ')+2
                    last_name = name[a:]
                else:
                    names = name.split()
                    last_name = names[-1]
                    first_name = names[0]
                # elif 'The Clerk' in name or 'The Speaker Pro Tempore' in name or 
                if 'The Speaker' in name:
                    title = 'The Speaker'
                    if not theSpeaker:
                        speakerRs = Role.objects.filter(gov_level='Federal', Position='Speaker of the House', Country_obj=country)
                        rUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in speakerRs], data__contains='"Current": true').first()
                        if rUpdate:
                            theSpeaker = speakerRs.filter(id=rUpdate.pointerId).first().Person_obj
                        else:
                            theSpeaker = None
                    person = theSpeaker

                # if title:
                #     try:
                #         rUpdate = Update.objects.filter(Country_obj=country, pointerType='Role', Role_obj__gov_level='Federal', Role_obj__Position='Speaker of the House', data__contains='"Current": true')[0]
                    
                #         person = rUpdate.Role_obj.Person_obj
                #     except:
                #         person = None
                if not person:
                    if first_name:
                        r = Role.objects.filter(Position='Congressional Representative').filter(Person_obj__LastName__icontains=last_name, Person_obj__FirstName__icontains=first_name).order_by('-created')
                    else:
                        r = Role.objects.filter(Position='Congressional Representative').filter(Person_obj__LastName__icontains=last_name).order_by('-created')
                    if r.count() > 1:
                        rU = None
                        if recognizedState:
                            refined_rs = r.filter(ProvState_obj__Name=recognizedState, Country_obj=country)
                            rU = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in refined_rs], data__contains='"Current": true').first()
                        else:
                            refined_rs = r.filter(Country_obj=country)
                            rU = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in refined_rs], data__contains='"Current": true', Country_obj=country).first()
                        if rU:
                            person = refined_rs.filter(id=rU.pointerId).first().Person_obj
                        else:
                            person = r[0].Person_obj
                    elif r.count() == 1:
                        person = r[0].Person_obj

                    else:
                        personName = name
                        # try:
                        #     if first_name:
                        #         person = Person.objects.filter(FirstName__icontains=first_name, LastName__icontains=last_name, Country_obj=country)[0]
                        #     else:
                        #         person = Person.objects.filter(LastName__icontains=last_name, Country_obj=country)[0]
                        # except:
                        #     person, personU, person_is_new = get_model_and_update('Person', FirstName=first_name, LastName=last_name, Country_obj=country)
                        #     # personData['GovernmentPosition'] = 'Congressional Representative'
                        #     if person_is_new:
                        #         person, personU, person_is_new, log = save_and_return(person, personU, person_is_new, log)
                if person:
                    personName = person.FullName

                statement, statementU, statement_is_new = get_model_and_update('Statement', Content=content, PersonName=personName, ItemId=ItemId, Person_obj=person, DateTime=date_time, Meeting_obj=meeting, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                statement.order = ItemId
                if statement_is_new:
                    statement, statementU, statement_is_new, log = save_and_return(statement, statementU, log)
                
                # if statement.keyword_array:
                #     for text in statement.keyword_array[:10]:
                #         if not text in meeting_terms:
                #             meeting_terms[text] = 1
                #         else:
                #             meeting_terms[text] += 1
                            
                
            meetingU.data['has_transcript'] = True
            meetingU = meeting.apply_terms(meetingU=meetingU)
            # people = Statement.objects.filter(Meeting_obj=meeting).exclude(Person_obj=None)
            # H_people = {}
            # for p in people:
            #     if not p.Person_obj.id in H_people:
            #         H_people[p.Person_obj.id] = 1
            #     else:
            #         H_people[p.Person_obj.id] += 1
            # H_people = sorted(H_people.items(), key=operator.itemgetter(1), reverse=True)
            # H_people = dict(H_people)
            # meetingU.data['People_json'] = json.dumps(H_people)
            if Au.data['CurrentStatus'] ==' Adjourned':
                meetingU.data['completed_model'] = True
            meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)
    try:
        close_browser(driver, driver_service)
    except:
        pass
    return finishScript(log, gov, special)

def add_house_motion(motion, motionU, motion_is_new, bill, country, log):
    prnt('add_house_motion')
    func = 'add_house_motion'
    motion, motionU, motion_is_new, log = save_and_return(motion, motionU, log)
    url = motion.GovUrl
    # url = 'https://clerk.house.gov/Votes/2024345'
    try:
        r = requests.get(url)
    except Exception as e:
        prnt('fail49582',str(e))
        r = None
        logEvent('add_house_motion FAIL 29482: ' + country.Name + '/' + str(e), log_type='Errors')
    if r:
        soup = BeautifulSoup(r.content, 'html.parser')

        section = soup.find('section', {'class':'content'})
        detail = section.find('h1', {'id':'pageDetail'})
        h1 = detail.text
        x = h1.find('Roll Call ')+len('Roll Call ')
        z = h1[x:].find(' | ')
        RC_num =h1[x:x+z]
        prnt(RC_num)
        span = detail.find('span', {'class':'legisNum'})
        # prnt(span)
        # a = span.find('a')
        # prnt(a)
        # prnt(a['href'])

        panel = soup.find('div', {'class':'panel'})
        detail = panel.find('div', {'class':'detailPage'})
        first_col = detail.find('div',{'class':'roll-call-first-col'})
        first = first_col.find('div', {'class':'first-row'}).text
        prnt(first)
        '''

                                    Jul 10, 2024, 05:22 PM 
                                | 
        118th Congress, 2nd Session                '''
        
        q = first.find('|')
        w = first[:q].strip()
        # prnt(w)
        date_time = timezonify('est', datetime.datetime.strptime(w, '%b %d, %Y, %I:%M %p'))
        prnt(z)

        first_row = first_col.find('p', {'class':'roll-call-first-row'}).text
        x = first_row.find('Vote Question: ')+len('Vote Question: ')
        vote_question = first_row[x:]

        descriptions = first_col.find_all('p',{'class':'roll-call-description'})
        vote_type = descriptions[1].text
        x = vote_type.find('Vote Type: ')+len('Vote Type: ')
        vType = vote_type[x:]
        prnt(vType)
        status = descriptions[2].text
        x = status.find('Status: ')+len('Status: ')
        result = status[x:]
        prnt(result)
        prnt()
        # sec_col = detail.find('div',{'class':'roll-call-second-col'})
        # divs = sec_col.find_all('div', {'class':'capitalize'})
        # d = divs[0]
        motion.DateTime = date_time
        motion.DecisionType = vType
        
        all_votes = soup.find('div', {'class':'all-votes'})
        tbody = all_votes.find('tbody', {'id':'member-votes'})
        if tbody:
            trs = tbody.find_all('tr')
            yeas = 0
            nays = 0
            present = 0
            np = 0
            unknown = 0
            total = 0
            result_data = {'Parties':[], 'Votes':[], 'PartyData':{}}
            try:
                for tr in trs:
                    # prnt(tr)
                    skip = tr.find('td', {'id':'nomatch'})
                    prnt(skip)
                    if skip:
                        pass
                    else:
                        a = tr.find('a', {'class':'library-link'})
                        prnt(a['href'])
                        if 'members/' in a['href'].lower():
                            x = a['href'].lower().rfind('members/')+len('members/')
                            member_code = a['href'][x:]
                        elif '=' in a['href']:
                            x = a['href'].rfind('=')
                            member_code = a['href'][x+1:]
                        else:
                            member_code = a['href'][-7:]
                        prnt('member_code',member_code)
                        memberName = tr.find('td', {'data-label':'member'}).text
                        partyName = tr.find('td', {'data-label':'party'}).text
                        found = False
                        for i in result_data['Parties']:
                            if i['Name'] == partyName:
                                i['Count'] += 1
                                found = True
                                break
                        if not found:
                            result_data['Parties'].append({'Name':partyName, 'Count':1})
                        # if partyName in result_data['Parties']:
                        #     result_data['PartyCount'][partyName] += 1
                        # else:
                        #     result_data['PartyCount'][partyName] = 1
                        stateName = tr.find('td', {'data-label':'state'}).text
                        p = Person.objects.filter(GovIden__iexact=member_code, Country_obj=country).first()
                        person, personU, person_is_new = get_model_and_update('Person', obj=p)
                        if person:
                            prnt('person,', person)
                            vote, voteU, vote_is_new = get_model_and_update('Vote', Motion_obj=motion, Person_obj=person, PersonFullName=f'{personU.data["LastName"]}, {personU.data["FirstName"]}', ConstituencyProvStateName=stateName, CaucusName=partyName, Chamber='House', Country_obj=country, Government_obj=motion.Government_obj, Region_obj=country)
                            if 'District_id' in personU.data:
                                vote.District_obj = District.objects.filter(id=personU.data['District_id']).first()
                        else:
                            vote, voteU, vote_is_new = get_model_and_update('Vote', Motion_obj=motion, PersonFullName=memberName, ConstituencyProvStateName=stateName, CaucusName=partyName, Chamber='House', Country_obj=country, Government_obj=motion.Government_obj, Region_obj=country)
                        prnt('vote:',vote)
                        vote.Party_obj = Party.objects.filter(Q(Name=partyName)|Q(AltName=partyName)|Q(ShortName=partyName)).first()
                        vote.Chamber = 'House'
                        vote.DateTime = date_time
                        vote.PersonId = member_code
                        vote.IsVoteNay = False
                        vote.IsVoteYea = False
                        vote.IsVotePresent = False
                        vote.IsVoteAbsent = False
                        voteValue = tr.find('td', {'data-label':'vote'}).text
                        vote.VoteValue = voteValue
                        if voteValue.lower() == 'no' or voteValue.lower() == 'nay':
                            vote.IsVoteNay = True
                            nays += 1
                        elif voteValue.lower() == 'aye' or voteValue.lower() == 'yea':
                            vote.IsVoteYea = True
                            yeas += 1
                        elif voteValue.lower() == 'present':
                            vote.IsVotePresent = True
                            present += 1
                        elif voteValue.lower() == 'not voting':
                            vote.IsVoteAbsent = True
                            np += 1
                        else:
                            unknown += 1
                        found = False
                        for i in result_data['Votes']:
                            if i['Vote'] == voteValue:
                                i['Count'] += 1
                                found = True
                                break
                        if not found:
                            result_data['Votes'].append({'Vote':voteValue, 'Count':1})
                        # if voteValue in result_data['Votes']:
                        #     result_data['Votes'][voteValue] += 1
                        # else:
                        #     result_data['Votes'][voteValue] = 1
                        
                        total += 1
                        # prnt('voteValue',voteValue)
                        vote, voteU, vote_is_new, log = save_and_return(vote, voteU, log)
                        # prnt('---nextvote---\n')
                prnt('done votes')
                motion.Yeas = yeas
                motion.Nays = nays
                motion.Present = present
                motion.Absent = np
                motion.TotalVotes = total
                motion.result_data = result_data
                prnt('result_data:',result_data)
                
                for i in result_data['Parties']:
                    party_name = i['Name']
                    count = i['Count']
                    party = Party.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').filter(Q(Name=party_name)|Q(AltName=party_name)).first()
                    if party:
                        # p = {'obj_type':'Party', 'obj_id':party.id, 'Name':party.Name, 'Color':party.Color, 'gov_level':party.gov_level, 'Count':count}
                        i['Color'] = party.Color
                        i['obj_id'] = party.id
                sorted_votes = sorted(result_data['Votes'], key=lambda item: item['Count'], reverse=True)
                result_data['Votes'] = sorted_votes
                sorted_parties = sorted(result_data['Parties'], key=lambda item: item['Count'], reverse=True)
                result_data['Parties'] = sorted_parties
                prnt('yeas',yeas)
                prnt('nays',nays)
                prnt('present',present)
                prnt('np',np)
                prnt('unknown',unknown)
                prnt('total',total)
                motion.Result = result
                motion.Subject = vote_question
                if bill:
                    motion.billCode = bill.NumberCode
                    motion.Bill_obj = bill
                motion.is_official = True
                time.sleep(2)
            except Exception as e:
                prnt('vote fail:',str(e))
                logEvent(f'add_house_motion FAIL {str(e)}', region=country, code='6532', func=func, log_type='Errors')
                time.sleep(7)
        motion, motionU, motion_is_new, log = save_and_return(motion, motionU, log)
        prnt()
    return log

def get_house_motions(special=None, dt=now_utc(), iden=None, target={}):
    func = 'get_house_motions'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, extra=target, log_type='Tasks')
    if target and 'url' in target and 'motion_num' in target:
        if 'gov_id' in target:
            gov = Government.objects.filter(id=target['gov_id']).first()
        else:
            gov = Government.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').first()
        bill = None
        if 'bill_id' in target:
            bill = Bill.objects.filter(id=target['bill_id']).first()
        motion, motionU, motion_is_new = get_model_and_update('Motion', VoteNumber=target['motion_num'], GovUrl=target['url'], Chamber='House', Country_obj=country, Government_obj=gov, Region_obj=country)
        if motion_is_new or not motion.Result:
            log = add_house_motion(motion, motionU, motion_is_new, bill, country, log)

    else:
        proceed = True
        gov = Government.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').first()
        motion = Motion.objects.filter(Country_obj=country, Chamber='House', DateTime__gte=dt-datetime.timedelta(hours=24)).exclude(TotalVotes=0).first()
        if special or not motion:
            starting_url = 'https://clerk.house.gov/Votes'
            try:
                driver, driver_service = open_browser(starting_url)

                element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="votes"]'))
                WebDriverWait(driver, 10).until(element_present)

                soup = BeautifulSoup(driver.page_source, 'html.parser')
            except Exception as e:
                prnt(str(e))
                proceed = False
                logEvent(str(e)[:100], region=country, code='09751', func=func, extra={})
            if proceed:
                section = soup.find('section', {'class':'content'})
                currentCongress = section.find('div', {'id':'currentCongress'}).text.replace('st','').replace('nd','').replace('rd','').replace('th','')
                currentSession = section.find('div', {'id':'currentSession'}).text.replace('st','').replace('nd','').replace('rd','').replace('th','')

                gov, govU, gov_is_new = get_model_and_update('Government', Country_obj=country, gov_level='Federal', GovernmentNumber=int(currentCongress), SessionNumber=int(currentSession), Region_obj=country)
                if gov_is_new:
                    from blockchain.models import round_time
                    gov.DateTime = timezonify('est', round_time(dt=now_utc(), dir='down', amount='day'))
                    gov.migrate_data()
                    gov.LogoLinks = gov_logo_links
                    # log.updateShare(gov.end_previous(func))
                    gov, govU, gov_is_new, log = save_and_return(gov, govU, log)


                member_info = soup.find('div', {'id':'member-info'})
                menus = member_info.find_all('div', {'class':'dropdown-menu_right'})
                # lis = menus[0].find_all('li', {'role':'listitem'})

                def get_leadership(lis):
                    for li in lis:
                        try:
                            if 'Speaker of the House' in li.text:
                                fullName = li.text.replace('Rep. ', '').replace('Speaker of the House', '').strip()
                                position = 'Speaker of the House'
                            elif 'Majority Leader' in li.text:
                                fullName = li.text.replace('Rep. ', '').replace('Majority Leader', '').replace('(','').replace(')','').replace('Democratic Leader', '').replace('Republican Leader', '').strip()
                                position = 'Majority Leader'
                            elif 'Majority Whip' in li.text:
                                fullName = li.text.replace('Rep. ', '').replace('Majority Whip', '').strip()
                                position = 'Majority Whip'
                            elif 'Minority Leader' in li.text:
                                fullName = li.text.replace('Rep. ', '').replace('Minority Leader', '').replace('(','').replace(')','').replace('Democratic Leader', '').replace('Republican Leader', '').strip()
                                position = 'Minority Leader'
                            elif 'Minority Whip' in li.text:
                                fullName = li.text.replace('Rep. ', '').replace('Minority Whip', '').strip()
                                position = 'Minority Whip'
                            names = fullName.split(' ')
                            prnt(names[0], names[-1], position)
                            personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Country_obj=country, data__Role__contains=position, data__FirstName__icontains=names[0], data__LastName__icontains=names[-1]).first()
                            # person = Person.objects.filter(Position=position, Country_obj=country, FirstName__icontains=names[0], LastName__icontains=names[-1]).first()
                            prnt('found')
                                # rUpdate = Update.objects.filter(Country_obj=country, pointerType='Role', Role_obj__Position=position, Role_obj__Person_obj__FirstName__icontains=names[0], Role_obj__Person_obj__LastName__icontains=names[-1], data__contains='"Current": true')[0]
                            if not personU:
                                personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Country_obj=country, data__Position__contains='Congressional Representative', data__FirstName__icontains=names[0], data__LastName__icontains=names[-1], extra__roles__contains={'Congressional Representative':{'current':True}}).first()
                                
                                # leaderRoles = Role.objects.filter(Position='Congressional Representative', Person_obj__FirstName__icontains=names[0], Person_obj__LastName__icontains=names[-1])
                                # rUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in leaderRoles], data__contains={'Current': True}).first()
                                if personU:
                                    personU.data['Role'] = position
                                    personU.pointer_obj.update_role(personU, position, current=True)
                                    # person = leaderRoles.filter(id=rUpdate.pointerId).first().Person_obj
                                    # person.Position = position
                                    personU.func = func
                                    personU.save_if_new()
                                    log.updateShare(personU)
                                    prnt('added')
                                    # rol, rolU, rol_is_new = get_model_and_update('Role', Title=position, gov_level='Federal', Person_obj=person, Position=position, Chamber='House', Government_obj=motion.Government_obj, Country_obj=country, Region_obj=country)
                                    # rolU.data['Current'] = True
                                    # rol, rolU, rol_is_new, log = save_and_return(rol, rolU, rol_is_new, log)
                                    oldRoles = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Country_obj=country, data__Role__contains=position, ).exclude(id=personU.Pointer_obj.id)
                                    for r in oldRoles:
                                        if 'Role' in r.data and r.data['Role'] == position:
                                            del r.data['Role']
                                        r.pointer_obj.update_role(personU, position, current=False)
                                        r.func = func
                                        r.save_if_new()
                                        log.updateShare(r)

                                    # oldRoles = Role.objects.filter(Position=position, Chamber='House', Country_obj=country, gov_level='Federal').exclude(id=rol.id)
                                    # oldrUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in oldRoles], data__contains={'Current': True}).first()
                                    # if oldrUpdate:
                                    #     # data = json.loads(oldrUpdate.data)
                                    #     oldrUpdate.data['Current'] = False
                                    #     # oldrUpdate.data = json.dumps(data)
                                    #     oldrUpdate.func = func
                                    #     oldrUpdate.save()
                                    #     log.updateShare(oldrUpdate)
                                    #     previousPerson = oldRoles.filter(id=oldrUpdate.pointerId).first().Role_obj.Person_obj
                                    #     if previousPerson.Position == position:
                                    #         previousPerson.Position = ''
                                    #         previousPerson.func = func
                                    #         previousPerson.update_data()
                                    #         log.updateShare(previousPerson)


                        except:
                            pass

                get_leadership(menus[0].find_all('li', {'role':'listitem'}))
                get_leadership(menus[1].find_all('li', {'role':'listitem'}))

                prnt()
                # retrieveBills = []
                foundBills = []
                votes = section.find('div', {'id':'votes'})
                role_calls = votes.find_all('div', {'class':'role-call-vote'})
                if special == 'testing' or testing():
                    role_calls = role_calls[:2]
                for m in role_calls:
                    header = m.find('div', {'class':'heading'})
                    motion_link = header.find_all('a')[0]
                    motion_num = motion_link.text
                    if len(header.find_all('a')) > 1:
                        bill_link = header.find_all('a')[1]
                        a = bill_link.text.rfind(' ')
                        a = bill_link['href'].find('bill/')+len('bill/')
                        b = bill_link['href'][a:].find('/')
                        bCongress = bill_link['href'][a:a+b]
                        c = bill_link['href'][a+b+1:].find('/')
                        bill_prefix = bill_link['href'][a+b+1:a+b+1+c]
                        bill_code = bill_link.text.replace(' ', '')
                        # bill_prefix = bill_link['href'][:a].replace(' ','')
                        prnt(bill_link['href'])
                        bill = Bill.objects.filter(Country_obj=country, Government_obj__GovernmentNumber=int(bCongress), NumberCode=bill_code).first()
                        if bill:
                            foundBills.append(bill)
                        else:
                            prnt('get bill')
                            # if bill_code not in retrieveBills:
                                # retrieveBills.append(bill_code)
                            time.sleep(1)
                            url = f'https://www.govinfo.gov/bulkdata/BILLSTATUS/{bCongress}/{bill_prefix.lower()}/BILLSTATUS-{bCongress}{bill_code.replace(".","").lower()}.xml'
                            log, driver, driver_service = add_bill(url=url, log=log, driver=driver, driver_service=driver_service, country=country, ref_func=func)
                            bill = Bill.objects.filter(Country_obj=country, Government_obj__GovernmentNumber=int(bCongress), NumberCode=bill_code).first()
                            if bill:
                                foundBills.append(bill)
                    
                try:
                    close_browser(driver, driver_service)
                except:
                    pass

                for m in role_calls:
                    # consider checking only last few days by date instead of all 10 listed
                    header = m.find('div', {'class':'heading'})
                    motion_link = header.find_all('a')[0]
                    motion_num = motion_link.text
                    bill = None
                    if len(header.find_all('a')) > 1:
                        bill_link = header.find_all('a')[1]
                        a = bill_link['href'].find('bill/')+len('bill/')
                        b = bill_link['href'][a:].find('/')
                        bCongress = bill_link['href'][a:a+b]
                        bill_code = bill_link.text.replace(' ', '')
                        prnt(bill_link['href'])
                        for bill in foundBills:
                            if bill.NumberCode == bill_code and bill.Government_obj.GovernmentNumber == int(bCongress):
                                break
                                
                    detail = m.find('div', {'class':'detail-button'})
                    mLink = 'https://clerk.house.gov' + detail.find('a')['href']
                    prnt(mLink)
                    target = {'url':mLink, 'motion_num':motion_num, 'gov_id':gov.id}
                    if bill:
                        target['bill_id'] = bill.id
                    queue = django_rq.get_queue('low')
                    queue.enqueue(get_house_motions, special=special, target=target, job_timeout=runTimes[func], result_ttl=3600)
                    # motion, motionU, motion_is_new = get_model_and_update('Motion', VoteNumber=motion_num, GovUrl=mLink, Chamber='House', Country_obj=country, Government_obj=gov, Region_obj=country)
                    # if motion_is_new or not motion.Result:
                    #     # time.sleep(1)
                    #     log = add_house_motion(motion, motionU, motion_is_new, bill, country, log)
    return finishScript(log, gov, special)

def add_official_debate_transcript(country, gov, chamber, log, url, driver=None, driver_service=None):
    prnt('add_official_debate_transcript')
    func = 'add_official_debate_transcript'
    # url = 'https://www.govinfo.gov/app/details/CREC-2024-07-15/context'
    # url = 'https://www.govinfo.gov/app/details/CREC-2024-07-09/context'
    prnt(url)
    meeting = None
    proceed = True
    if not driver:
        driver, driver_service = open_browser()
    try:
        driver.get(url)
        prnt('loaded')
        element_present = EC.presence_of_element_located((By.CLASS_NAME, 'table'))
        WebDriverWait(driver, 10).until(element_present)
        prnt('ready1')

        content = driver.find_element(By.XPATH, '//*[@id="contentdetaildocinContextview"]')
        panels = content.find_elements(By.CLASS_NAME, 'panel-default')
        for panel in panels:
            if chamber in panel.text:
                panel.click()
                prnt('clicked', chamber)
                element_id = panel.get_attribute('id').replace('panel','')
                target_id = 'collapseOne' + element_id
                prnt('panel_path',target_id)
                element_present = EC.presence_of_element_located((By.XPATH, f'//*[@id="{target_id}"]/div/table[1]'))
                WebDriverWait(driver, 10).until(element_present)
                
                break
            # elif chamber == 'House' and 'House' in panel.text:
            #     panel.click()
            #     prnt('clicked', chamber)
            #     element_present = EC.presence_of_element_located((By.XPATH, '/html/body/div[10]/div/div[2]/div[2]/div[1]/div[3]/div/div/div/div[2]/div/div/div/div[4]/div[2]/div/table[1]'))
            #     WebDriverWait(driver, 10).until(element_present)
            #     break
    except Exception as e:
        prnt('failed load page 4063', str(e))
        proceed = False
        logEvent('error loading page', region=country, code='598252', log_type='Errors', func=func, extra={'url':url, 'err':str(e)[:200]})
    if proceed:
        try:
            prnt('ready2')
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # close_browser(driver, driver_service)

            def clean_text(text):
                # Replace single newlines with a space, but leave double newlines
                subbedText = re.sub(r'(?<!\n)\n(?!\n|\s)', ' ', text)
                while '[[Page' in subbedText:
                    a = subbedText.find('[[Page')
                    b = subbedText[a:].find(']]')+len(']]')
                    subbedText = subbedText[:a].strip() + ' ' + subbedText[a+b:].strip()
                return re.sub(r'\n{3,}', '\n\n', subbedText.strip())

            def find_first_title(text):
                pattern = r'  (Mr\.|Mrs\.|Ms\.|The ACTING PRESIDENT pro tempore\.|The PRESIDING OFFICER\.|The PRESIDING OFFICER |\[Rollcall Vote No\.|The SPEAKER\.|The SPEAKER |The SPEAKER pro tempore\.|The SPEAKER pro tempore )\s+(\b(?!President\b)(?!Speaker\b)\w+)'
                match = re.search(pattern, text)
                
                if match:
                    if 'The ACTING PRESIDENT pro tempore' in match.group() or 'The PRESIDING OFFICER.' in match.group() or 'Rollcall Vote No' in match.group() or 'The SPEAKER pro tempore.' in match.group() or 'The SPEAKER.' in match.group():
                        a = match.group().find('. ')
                        return match.group()[:a]
                    else:
                        return match.group()
                else:
                    # pattern = r'  (Mr\.|Mrs\.|Ms\.|The ACTING PRESIDENT pro tempore\.|The PRESIDING OFFICER\.|The PRESIDING OFFICER |\[Rollcall Vote No\.)'
                    # match = re.search(pattern, text)
                    # if match:
                    #     return match.group()
                    # else:
                    return None
                    
            def make_statement(speaker, quote, subtitle, order, log):
                prnt('statement by:', speaker)
                party = None
                district = None


                def check_mentioned_state(text, dictionary, n=5):
                    first_words = set(text.split()[:n])
                    for value in dictionary.values():
                        if value in first_words:
                            return value 
                    return None
                reg_id = None
                mentioned_state = check_mentioned_state(quote, state_list)
                if mentioned_state:
                    reg = Region.objects.filter(ParentRegion_obj=country, Name__iexact=mentioned_state).first()
                    if reg:
                        reg_id = reg.id


                if speaker:
                    speaker = speaker.strip()
                    officers = {'the president officer':'The Presiding Officer', 'the acting president pro tempore':'The Acting President pro tempore', 'the speaker pro tempore':'The Speaker pro tempore', 'the speaker':'The Speaker'}
                    if speaker.lower() in officers:
                        prnt('in offce')
                        speaker = officers[speaker.lower()]
                        prnt(speaker)
                        personName = speaker
                        speaker_obj = None
                    elif 'Rollcall' in speaker:
                        prnt('presiding officer speakers:')
                        personName = 'Presiding Officer'
                        speaker_obj = None
                        quote = '[Rollcall Vote No. ' + quote
                    else:
                        prnt('speaker:', speaker)
                        personName = speaker
                        speakerName = speaker.replace('Mr. ','').replace('Mrs. ','').replace('Ms. ','').strip()
                        # prnt('speakerName',speakerName)
                        if reg_id:
                            personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__LastName__icontains=speakerName, data__ProvState_id__contains=reg_id, extra__roles__contains=[{'current':True,'gov_level':'Federal'}])

                        else:
                            personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__LastName__icontains=speakerName, extra__roles__contains=[{'current':True,'gov_level':'Federal'}]).first()
                        # prnt('personU',personU)
                        # sRoles = Role.objects.filter(Position=position, Person_obj__LastName__icontains=speakerName, Country_obj=country)
                        # rU = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in sRoles], data__contains={'Current': True}).first()
                        if personU:
                            # speaker_obj = sRoles.filter(id=rU.pointerId).first().Person_obj
                            speaker_obj = personU.Pointer_obj
                            try:
                                party = Party.objects.filter(id=personU.data['Party_id']).first()
                            except:
                                pass
                            try:
                                district = District.objects.filter(id=personU.data['District_id']).first()
                            except:
                                pass
                        else:
                            speaker_obj = None
                        prnt('next')
                elif proTempore or chairAppointee:
                    prnt('pro/chair')
                    if proTempore:
                        # prnt('proTempore',proTempore)
                        personName = proTempore.data['FullName']
                        speaker_obj = proTempore.Pointer_obj
                        try:
                            party = Party.objects.filter(id=proTempore.data['Party_id']).first()
                        except:
                            pass
                        try:
                            district = District.objects.filter(id=proTempore.data['District_id']).first()
                        except:
                            pass
                    else:
                        # prnt('chairAppointee',chairAppointee)
                        personName = chairAppointee
                        speaker_obj = None
                else:
                    prnt('else1')
                    if chamber == 'Senate':
                        personName = 'Presiding Officer'
                        speaker_obj = None
                    elif chamber == 'House':
                        personName = 'The Speaker'
                        speaker_obj = None
                # if regarding:
                #     prnt('regarding',regarding)
                # prnt('stage 2','-----')

                # Split into lines and ignore empty ones, but keep spacing
                lines = quote.splitlines()

                # Get the first non-empty line (without stripping spaces)
                first_line = next((line for line in lines if line.strip()), '')

                # print(repr(first_line))  # Output: '  First line with spaces  '


                # first_line = quote.splitlines('\n')[0].replace('\n','')
                # prntDebug('first_line',first_line, isinstance(first_line, int))
                # left_spaces = first_line.lstrip()
                left_spaces = len(first_line) - len(first_line.lstrip())
                # prnt('left_spaces',left_spaces)
                first_line_length = len(first_line.strip()) + (left_spaces*2)
                # prnt('first_line_length',first_line_length)
                # prnt(' stage 2a')
                if left_spaces >= 3 and first_line_length >= 70 and first_line_length <= 74: # line is centered (71 chars total)
                    prntDebug('next1')
                    first_empty_line = None
                    for line_num, line in enumerate(quote):
                        if not line.strip():
                            prntDebug('next2')
                            prntDebug('line_num',line_num, isinstance(line_num, int))
                            first_empty_line = line_num + 1
                            break
                    if first_empty_line and first_empty_line >= 1 and first_empty_line <= 2:
                        subtitle = first_line.strip()
                        prnt('new subtitle',subtitle)
                        quote = quote.replace(first_line, '').strip()
                prnt('stage 3')
                
                content = clean_text(quote)
                prnt('-')
                statement, statementU, statement_is_new = get_model_and_update('Statement', Content=content, PersonName=personName, Person_obj=speaker_obj, DateTime=starting_dt, source_link=statementLink, Meeting_obj=meeting, order=order, Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country)
                
                statement.Party_obj = party
                statement.District_obj = district
                order += 1
                statement.SubjectOfBusiness = subtitle
                if not subtitle in meeting_terms:
                    meeting_terms[subtitle] = 1
                else:
                    meeting_terms[subtitle] += 1
                # if 'subjects' in meetingU.data:
                #     meetingU.data['subjects'].append(statement.SubjectOfBusiness)
                # else:
                #     meetingU.data['subjects'] = [statement.SubjectOfBusiness]
                if regarding:
                    statement = statement.add_term(regarding, bill)
                    # statement.SubjectOfBusiness = regarding
                    # if 'subjects' in meetingU.data:
                    #     meetingU.data['subjects'].append(regarding)
                    # else:
                    #     meetingU.data['subjects'] = [regarding]
                statement, statementU, statement_is_new, log = save_and_return(statement, statementU, log)
                if statement.keyword_array:
                    for text in statement.keyword_array[:10]:
                        if '.' in text:
                            z = text.rfind('.')
                            q = text[:z].replace('.','').lower()
                            if q in billTypes:
                                if not statement.bill_dict or text not in statement.bill_dict:
                                    if not statement.bill_dict:
                                        statement.bill_dict = {}
                                    b = Bill.objects.filter(NumberCode__iexact=text, Region_obj=country).first()
                                    if b:
                                        statement.bill_dict[b.NumberCode] = {'obj_id':b.id}
                        if not text in meeting_terms:
                            meeting_terms[text] = 1
                        else:
                            meeting_terms[text] += 1
                return order, log


            
            tables = soup.find_all('table', {'class':'table'})
            prnt('tables')
            order = 1
            next_meeting = None
            last_item = False
            chairAppointee = None
            proTempore = None
            starting_dt = None
            meetingTitle = None
            meeting_terms = {}
            if chamber == 'Senate':
                position = 'Senator'
            elif chamber == 'House':
                position = 'Congressional Representative'
            for table in tables:
                err = 1
                # prnt('\n',table)
                if last_item:
                    prnt('last_item break')
                    break
                td = table.find_all('td')
                subtitle = ''
                try:
                    err = 2
                    link = None
                    p = td[0].find('p')
                    if p:
                        p = p.text
                        # prnt(p)
                        a = p.find(' - ')+len(' - ')
                        subtitle = p[a:].replace('(Executive Session)','').replace('(Executive Calendar)','').strip()
                        prnt('subtitle', subtitle)
                        
                        p = td[1].find('p')
                        if p:
                            p = p.text
                            # prnt(p)
                            words = p.split(' ')
                            previousIsCaps = None
                            wordIsTitle = False
                            speaker = None
                            personName = ''
                            regarding = None
                            bill = None
                            if not starting_dt:
                                err = 3
                                try:
                                    dt = p.replace('Congressional Record. ','').strip()
                                    # starting_dt = datetime.datetime.strptime(dt, '%B %d, %Y')
                                    starting_dt = parse(dt)
                                    starting_dt = timezonify('est', starting_dt)
                                    prnt('starting_dt',starting_dt)
                                except Exception as e:
                                    prnt(str(e))
                                    pass
                            if 'Regarding' in p and starting_dt:
                                err = 4
                                a = p.find('Regarding ')+len('Regarding ')
                                pattern = r' (Mr\.|Mrs\.|Ms\.)'
                                match = re.search(pattern, p)
                                if match:
                                    b = p[a:].find(match.group())
                                else:
                                    b = p[a:].find(starting_dt.strftime("%B"))
                                bill_code = p[a:a+b].strip()
                                if bill_code.endswith('.'):
                                    bill_code = bill_code[:-1]
                                a = bill_code.rfind(' ')
                                bill_prefix = bill_code[:a].replace(' ','')
                                regarding = bill_code.replace(' ','')
                                prnt('regarding',regarding)
                                bill = Bill.objects.filter(NumberCode=regarding, Government_obj=gov, Country_obj=country).first()
                                if not bill:
                                    err = 5

                                    def fetch_bill(govNum, log, driver, driver_service):
                                        try:
                                            time.sleep(1.5)
                                            bill_url = f'https://www.govinfo.gov/bulkdata/BILLSTATUS/{govNum}/{bill_prefix.replace(".","").lower()}/BILLSTATUS-{govNum}{regarding.replace(".","").lower()}.xml'
                                            return add_bill(url=bill_url, log=log, driver=driver, country=country, ref_func=func)
                                        except Exception as e:
                                            prnt('fail45356',str(e))
                                            return log, driver, driver_service

                                    log, driver, driver_service = fetch_bill(gov.GovernmentNumber, log, driver, driver_service)
                                    bill = Bill.objects.filter(NumberCode=regarding, Government_obj=gov, Country_obj=country).first()
                                    if not bill:
                                        log, driver, driver_service = fetch_bill(gov.GovernmentNumber - 1, log, driver, driver_service)
                                        bill = Bill.objects.filter(NumberCode=regarding, Government_obj__GovernmentNumber=gov.GovernmentNumber-1, Country_obj=country).first()
                                        if not bill:
                                            log, driver, driver_service = fetch_bill(gov.GovernmentNumber - 2, log, driver, driver_service)
                                            bill = Bill.objects.filter(NumberCode=regarding, Government_obj__GovernmentNumber=gov.GovernmentNumber-2, Country_obj=country).first()

                                    
                            err = 6
                            for word in words:
                                if word == 'Mr.' or word == 'Mrs.' or word == 'Ms.':
                                    title = word
                                    wordIsTitle = True
                                elif wordIsTitle:
                                    word = word.replace('.','').replace(',','')
                                    speaker = title + ' ' + word
                                    # prnt('person:', word)
                                    previousIsCaps = word
                                    wordIsTitle = False
                                elif previousIsCaps and word.isupper():
                                    word = word.replace('.','').replace(',','')
                                    fullName = title + ' ' + previousIsCaps + ' ' + word
                                    if previousIsCaps in speaker:
                                        speaker = fullName
                                    # prnt('person:', fullName)
                                else:
                                    previousIsCaps = None
                                    wordIsTitle = False
                            # prnt()
                            err = 7
                            links = td[1].find_all('a')
                            for link in links:
                                if 'Text' in link.text:
                                    err = 8
                                    statementLink = 'https://www.govinfo.gov' + link['href']
                                    statement = Statement.objects.filter(Meeting_obj=meeting, source_link=statementLink).order_by('-order').first()
                                    if statement:
                                        order = statement.order + 1
                                    else:
                                        err = 9
                                        if not meeting:
                                            meeting, meetingU, meeting_is_new = get_model_and_update('Meeting', GovPage=url, meeting_type='Debate', Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country)
                                            meeting.hide_time = 'hour'
                                            meetingU.data['has_transcript'] = True
                                            if meeting_is_new:
                                                meetingU.data['completed_model'] = False
                                                meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)
                                        # statement, statementU, statement_is_new = get_model_and_update('Statement', Content=content, ItemId=ItemId, Person_obj=person, DateTime=date_time, Meeting_obj=meeting, Chamber='House', Government_obj=gov, Country_obj=country, Region_obj=country)
                                        prnt('statementLink',statementLink)
                                        time.sleep(1.5)
                                        r = requests.get(statementLink)
                                        bs = BeautifulSoup(r.content, 'html.parser')
                                        pre = bs.find('pre').text
                                        pre = pre.replace('____________________','').replace('[Senate]','')
                                        if '...' in subtitle:
                                            newSub = subtitle[:40]
                                            a = pre.find(newSub)
                                            # prnt(a)
                                            b = pre[a:].find('\n\n')
                                            subtitle = pre[a:a+b]
                                            prnt('new subtitle:', subtitle)
                                        if subtitle in pre:
                                            a = pre.find(subtitle)+len(subtitle)
                                            prnt('found')
                                        else:
                                            a = pre.find('.gov]')+len('.gov]')
                                            prnt('not found')
                                        prnt('-----')
                                        subtitle = subtitle.replace('-Continued','')
                                        if len(subtitle) > 150:
                                            subtitle = subtitle[:150] + '...'
                                        prnt(subtitle)
                                        err = 10
                                        text = pre[a:].replace('______','')
                                        if subtitle == 'APPOINTMENT OF ACTING PRESIDENT PRO TEMPORE':
                                            err = 11
                                            a = text.find('hereby appoint the Honorable ')+len('hereby appoint the Honorable ')
                                            b = text[a:].find(', ')
                                            chairAppointee = text[a:a+b].strip()
                                            names = chairAppointee.split(' ')
                                            personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__FirstName__icontains=names[0], data__LastName__icontains=names[-1], extra__roles__contains=[{'role':'Senator','current':True}]).first()
                                            
                                            # xSens = Role.objects.filter(Position='Senator', Person_obj__FirstName__icontains=names[0], Person_obj__LastName__icontains=names[-1], Country_obj=country)
                                            # rU = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in xSens], data__contains={'Current': True}).first()
                                            # prnt('presiding officer speakers:')
                                            if personU:
                                                proTempore = personU
                                                prnt('Acting President pro tempore!!:', proTempore.data['FullName'], names)
                                            else:
                                                prnt('Acting President pro tempore not found:',  names)
                                                pass

                                            content = clean_text(text.replace('The PRESIDING OFFICER. ',''))
                                            if proTempore and proTempore.Pointer_obj:
                                                statement, statementU, statement_is_new = get_model_and_update('Statement', Content=content, PersonName=chairAppointee, Person_obj=proTempore.Pointer_obj, DateTime=starting_dt, source_link=statementLink, Meeting_obj=meeting, order=order, Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country)
                                            else:
                                                statement, statementU, statement_is_new = get_model_and_update('Statement', Content=content, PersonName=chairAppointee, DateTime=starting_dt, source_link=statementLink, Meeting_obj=meeting, order=order, Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country)

                                            try:
                                                statement.Party_obj = Party.objects.filter(id=proTempore.data['Party_id']).first()
                                            except:
                                                pass
                                            try:
                                                statement.District_obj = District.objects.filter(id=proTempore.data['District_id']).first()
                                            except:
                                                pass
                                            statement.order = order
                                            order += 1
                                            statement.SubjectOfBusiness = subtitle
                                            if not subtitle in meeting_terms:
                                                meeting_terms[subtitle] = 1
                                            else:
                                                meeting_terms[subtitle] += 1
                                            # if 'subjects' in meetingU.data:
                                            #     meetingU.data['subjects'].append(statement.SubjectOfBusiness)
                                            # else:
                                            #     meetingU.data['subjects'] = [statement.SubjectOfBusiness]
                                            if regarding:
                                                statement = statement.add_term(regarding, bill)
                                                # statement.SubjectOfBusiness = regarding
                                                # if 'subjects' in meetingU.data:
                                                #     meetingU.data['subjects'].append(regarding)
                                                # else:
                                                #     meetingU.data['subjects'] = [regarding]
                                            err = 12
                                            statement, statementU, statement_is_new, log = save_and_return(statement, statementU, log)
                                            if statement.keyword_array:
                                                for text in statement.keyword_array[:10]:
                                                    if '.' in text:
                                                        z = text.rfind('.')
                                                        q = text[:z].replace('.','').lower()
                                                        if q in billTypes:
                                                            if not statement.bill_dict or text not in statement.bill_dict:
                                                                if not statement.bill_dict:
                                                                    statement.bill_dict = {}
                                                                b = Bill.objects.filter(NumberCode__iexact=text, Region_obj=country).first()
                                                                if b:
                                                                    statement.bill_dict[b.NumberCode] = {'obj_id':b.id}
                                                    if not text in meeting_terms:
                                                        meeting_terms[text] = 1
                                                    else:
                                                        meeting_terms[text] += 1
                                            err = 13
                                            # if statement.keyword_array:
                                            #     for text in statement.keyword_array[:10]:
                                            #         if not text in meeting_terms:
                                            #             meeting_terms[text] = 1
                                            #         else:
                                            #             meeting_terms[text] += 1
                                        else:
                                            if subtitle in ['House of Representatives', 'Senate'] or ' met at ' in subtitle:
                                                err = 14
                                                if not meetingTitle:
                                                    a = pre.find('Congressional Record ')+len('Congressional Record ')
                                                    b = pre[a:].find(' (')
                                                    meetingTitle = pre[a:a+b]
                                                    meeting.Title = meetingTitle
                                                    meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)
                                                a = None
                                                if 'The Senate met at ' in text:
                                                    a = text.strip().find('The Senate met at ')+len('The Senate met at ')
                                                elif 'The House met at ' in text:
                                                    a = text.strip().find('The House met at ')+len('The House met at ')
                                                if a:
                                                    err = 15
                                                    b = None
                                                    if 'a.m.' in text:
                                                        b = text.strip()[a:].find('a.m.')+len('a.m.')
                                                        hour = text.strip()[a:a+b]
                                                    elif 'p.m.' in text:
                                                        b = text.strip()[a:].find('p.m.')+len('p.m.')
                                                        hour = text.strip()[a:a+b]
                                                    elif 'noon' in text:
                                                        # if '12' in text:
                                                        #     text = text.replace('12 ','')
                                                        # b = text[a:].find('noon')+len('')
                                                        hour = '12 p.m.'
                                                    if starting_dt:
                                                        err = 16
                                                        if hour:
                                                            err = 17
                                                            working_dt = dt + ' ' + hour
                                                            working_dt = working_dt.replace('.','').replace('seconds','second')
                                                            prnt('working_dt',working_dt)
                                                            # logError('get debate time test', code='48367423', func='add_official_debate_transcript', region=country, extra=str(working_dt))
                                                            try:
                                                                starting_dt = parse(working_dt)
                                                            except:
                                                                try:
                                                                    starting_dt = datetime.datetime.strptime(working_dt, '%B %d, %Y %I %p')
                                                                except:
                                                                    try:
                                                                        starting_dt = datetime.datetime.strptime(working_dt, '%B %d, %Y %I:%M %p')
                                                                    except:
                                                                        try:
                                                                            starting_dt = datetime.datetime.strptime(working_dt, '%B %d, %Y %I:%M and %S second %p')
                                                                        except:
                                                                            try:
                                                                                starting_dt = datetime.datetime.strptime(working_dt, '%B %d, %Y %I and %S second %p')
                                                                            except:
                                                                                try:
                                                                                    starting_dt = datetime.datetime.strptime(working_dt, '%B %d, %Y %I')
                                                                                except:
                                                                                    # December 26, 2024 2:30 and 1 second pm
                                                                                    # December 30, 2024 12:30 and 1 second pm
                                                                                    # December 26, 2024 2:30 and 1 second pm
                                                                                    # December 23, 2024 9:53 and 24 seconds am
                                                                                    # December 27, 2024 noo
                                                                                    # January 2, 2025 12 and 46 second pm
                                                                                    # January 27, 2025 12
                                                                                    # January 29, 2025 12
                                                                                    logError('get starting time fail', code='487153', func='add_official_debate_transcript', region=country, extra=str(working_dt))
                                                                                    pass
                                                        err = 18
                                                        try:
                                                            starting_dt = timezonify('est', starting_dt)
                                                        except Exception as e:
                                                            prnt(str(e))
                                                        prnt('starting_dt222',starting_dt)
                                                        meeting.DateTime = starting_dt
                                                        meetingU.DateTime = starting_dt
                                                        # meetingU.data['DateTime'] = starting_dt_to_string(dt)
                                                        meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)
                                                        err = 18
                                            if 'adjourned until' in text:
                                                err = 19
                                                prnt('adjourned until')
                                                # prnt(text)
                                                last_item = True
                                                def is_month(word):
                                                    days_of_week = list(calendar.month_name)
                                                    return word in days_of_week

                                                def is_day_of_week(word):
                                                    days_of_week = [day.lower() for day in calendar.day_name]
                                                    days_abbrev = [day.lower() for day in calendar.day_abbr]
                                                    return word.lower() in days_of_week or word.lower() in days_abbrev


                                                working_text = text.replace('\n', '').strip()
                                                a = working_text.rfind('adjourned until ')+len('adjourned until ')
                                                x = working_text[a:]
                                                words = x.split(' ')
                                                date_string = ''
                                                match = False
                                                next_meeting_dt = None
                                                if 'noon' in x:
                                                    if 'tomorrow' in x and meeting.DateTime:
                                                        next_day = meeting.DateTime + datetime.timedelta(days=1)
                                                        next_meeting_dt = next_day.replace(hour=12, minute=0, second=0, microsecond=0)
                                                    else:
                                                        day_of_week = None
                                                        date_num = None
                                                        month = None
                                                        for word in words:
                                                            if is_month(word):
                                                                month = word.lower()
                                                            elif is_day_of_week(word):
                                                                day_of_week = word.lower()
                                                            elif isinstance(word, int):
                                                                date_num = word
                                                        if month and day_of_week and date_num:
                                                            date_string = f'{month} {date_num} {now_utc().year} at 12 PM'
                                                if not next_meeting_dt and not date_string:
                                                    for word in words:
                                                        word = word.replace(',','')
                                                        # prnt(word)
                                                        if is_month(word):
                                                            # prnt('match')
                                                            match = True
                                                        if match:
                                                            date_string = date_string + ' ' + word
                                                err = 20
                                                date_string = date_string.replace('.','').strip()
                                                prnt('date_string',date_string)
                                                if not next_meeting_dt and date_string:
                                                    err = 21
                                                    date_string = date_string.replace(' for morning-hour debate','')
                                                    # until 3 p.m. on Monday, September 9;
                                                    # date_string,January 22 2025 at 10 am for morning-hour debate
                                                    # it stand adjourned until 12 noon on Monday, January 27;
                                                    # stand adjourned until noon tomorrow for morning-hour debate and 2 p.m. for legislative business.
                                                    # t stand adjourned until 10 a.m. on Tuesday, January 28; that following the prayer and pledge, the Journal of proceedings be approved to d
                                                    try:
                                                        next_meeting_dt = datetime.datetime.strptime(date_string, '%B %d %Y at %I %p')
                                                    except Exception as e:
                                                        prnt(str(e))
                                                        logError('get next_meeting_dt fail', code='8364', func='add_official_debate_transcript', region=country, extra={'link':link,'dt_sting':str(date_string)})
                                                        #  'get next_meeting_dt fail', 'reg': 'USA', 'code': '8364', 'func': 'add_official_debate_transcript', 'extra': "Pursuant to H Res 43 and without objection Members will now proceed to the rotunda to attend the inaugural ceremonies for the President and Vice President of the United States Thereupon at 10 o'clock and 6 minutes am the Members of the House preceded by the Sergeant at Arms and the Speaker pro tempore proceeded to the rotunda of the Capitol"}
                                                        try:
                                                            next_meeting_dt = datetime.datetime.strptime(date_string, '%B %d %Y at %I:%M %p')
                                                        except Exception as e:
                                                            prnt(str(e))
                                                            next_meeting_dt = None
                                                    if next_meeting_dt:
                                                        next_meeting_dt = timezonify('est', next_meeting_dt)
                                                        prnt('next_meeting_dt',next_meeting_dt)
                                                    err = 22
                                                if next_meeting_dt:
                                                    err = 23
                                                    # nextUrl = f"https://www.govinfo.gov/app/details/CREC-{next_meeting_dt.strftime('%Y-%m-%d')}/context"
                                                    # next_meeting, next_meetingU, next_meetingData, next_meeting_is_new = get_model_and_update('Meeting', GovPage=nextUrl, meeting_type='Debate', Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country)
                                                    # next_meeting.hide_statement_time = 'hour'
                                                    # next_meeting.DateTime = timezonify('est', next_meeting_dt)
                                                    # if next_meeting_is_new:
                                                    #     next_meetingU.data['completed_model'] = False
                                                    #     next_meeting, next_meetingU, next_meetingData, next_meeting_is_new, log = save_and_return(next_meeting, next_meetingU, next_meetingData, next_meeting_is_new, log)
                                                    A = Agenda.objects.filter(DateTime=next_meeting_dt, Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country).first()
                                                    if not A:
                                                        A = Agenda(DateTime=next_meeting_dt, Chamber=chamber, Government_obj=gov, Country_obj=country, Region_obj=country, func=log.data['func'])
                                                        A.save()
                                                        log.updateShare(A)
                                                    prnt(A)
                                            if '  Mr.' in text or '  Mrs.' in text or '  Ms.' in text or '  The PRESIDING OFFICER' in text or '  The ACTING PRESIDENT pro tempore.' in text or '[Rollcall Vote No' in text or '  the speaker' in text.lower():
                                                err = 24
                                                prnt('FOUND INSTANCE')
                                                x = find_first_title(text)
                                                # prnt('x',x)
                                                nextSpeaker = x
                                                snippedText = text
                                                while x:
                                                    err = 25
                                                    a = snippedText.find(x)
                                                    firstQuote = snippedText[:a].strip()
                                                    if firstQuote:
                                                        err = 26
                                                        # right_stripped = line.rstrip()
                                                        # prnt('firstQuote',firstQuote)
                                                        snippedText = snippedText.replace(firstQuote, '', 1)
                                                        order, log = make_statement(speaker, firstQuote, subtitle, order, log)
                                                        x = find_first_title(snippedText)
                                                        # prnt('x',x)
                                                        nextSpeaker = x
                                                    else:
                                                        err = 27
                                                        prnt('else')
                                                        a2 = a+len(x)
                                                        b = snippedText[a2:].find('. ')+len('. ')
                                                        snippedText = snippedText[a2+b:]
                                                        x = find_first_title(snippedText)
                                                        # prnt('x',x)
                                                        prnt('x',x)
                                                        if x:
                                                            a = snippedText.find(x)
                                                            prnt('--')
                                                            # prnt('aaa',a)
                                                            if snippedText[:a].endswith(':\n'):
                                                                # prnt('heree')
                                                                b = snippedText.find('\n\n')
                                                                # prnt('b',b)
                                                                # prnt('check:', snippedText[:b])
                                                                snippedText = snippedText[:b].strip()
                                                                x = find_first_title(snippedText[b:])
                                                                # prnt('x',x)
                                                        speaker = nextSpeaker
                                                        nextSpeaker = x
                                                    # prnt()
                                                err = 28
                                                order, log = make_statement(speaker, snippedText, subtitle, order, log)

                                            else:
                                                err = 29
                                                order, log = make_statement(speaker, text, subtitle, order, log)
                                        prnt('--next')
                                        prnt()
                                        time.sleep(1)
                except Exception as e:
                    prnt('fart1', str(e))
                    logEvent(str(e), region=country, code='58362', func=func, extra={'err':err,'url':url,'subtitle':subtitle,'link':link}, log_type='Errors')

                    #  {'0': "unsupported operand type(s) for +: 'int' and 'str'", 'reg': 'USA', 'func': 'add_official_debate_transcript', 'extra': '{\'url\': \'https://www.govinfo.gov/app/details/CREC-2025-01-21/context\', \'subtitle\': \'ADJOURNMENT\', \'link\': <a class="btn btn-sm btn-format" href="/content/pkg/CREC-2025-01-21/html/CREC-2025-01-21-pt1-PgH255.htm" target="_blank"> Text</a>}'}
                    # time.sleep(5)
        except Exception as e:
            prnt('failed debate get 49845', str(e))
            logEvent(str(e)[:250], region=country, code='39586', log_type='Errors', func=func, extra={'url':url})
            pass
        #     prnt('oops',str(e))
        # close_browser(driver, driver_service)
    if meeting:
        prnt('order_count', order)
        meeting, meetingU, meeting_is_new = meeting.apply_terms(meeting, meetingU, meeting_is_new)
        if 'statement_count' in meetingU.data and meetingU.data['statement_count'] > 0:
            meetingU.data['completed_model'] = True
        # if starting_dt:
        #     meetingU.data['DateTime'] = starting_dt_to_string(dt)
        # meetingU.data['Title'] = meetingTitle
        # prnt('starting_dt',starting_dt)
        meeting, meetingU, meeting_is_new, log = save_and_return(meeting, meetingU, log)
    return log, driver, driver_service

def get_house_debates(special=None, dt=now_utc(), iden=None, target={}, driver=None, driver_service=None):
    func = 'get_house_debates'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, extra=target, log_type='Tasks')
    if target and 'link' in target:
        if 'gov_id' in target:
            gov = Government.objects.filter(id=target['gov_id']).first()
        else:
            gov = Government.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').first()
        run_job = True
        meetings = Meeting.objects.filter(Country_obj=country, Chamber='House', meeting_type='Debate', GovPage__icontains=target['link']).order_by('DateTime')
        if meetings:
            meetingsU = Update.objects.filter(pointerId__in=[i.id for i in meetings], data__contains={'completed_model': True}).order_by('DateTime')
            for u in meetingsU:
                if 'statement_count' in u.data and u.data['statement_count'] > 0:
                    if Statement.objects.filter(Meeting_obj__id=u.pointerId).count() == u.data['statement_count']:
                        if u.validated or u.created > now_utc() - datetime.timedelta(minutes=60):
                            run_job = False
        if run_job:
            log, driver, driver_service = add_official_debate_transcript(country, gov, 'House', log, target['link'], driver=driver, driver_service=driver_service)
    else:
        gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()

        # utc = now_utc()
        # def search(day, log, driver):
        #     utc = dt - datetime.timedelta(days=day)
        #     est = pytz.timezone('US/Eastern')
        #     today = utc.astimezone(est)
        #     prnt("EST Time:", today)
        #     link = f"https://www.govinfo.gov/app/details/CREC-{today.strftime('%Y-%m-%d')}/context"
        #     prnt(link)

        #     # change:
        #     # get oldest meeting thats less than 7 days old, start the next day and check every day forward until day of job run
        #     # xMeets = Meeting.objects.filter(Country_obj=country, GovPage=link, Chamber='House', meeting_type='Debate')
        #     # meetingU = Update.objects.filter(Region_obj=country, pointerId__startswith=get_model_prefix('Meeting'), pointerId__in=[i.id for i in xMeets], data__contains={'completed_model': True}).first()
        #     # prnt('meetngu',meetingU)
        #     # if not meetingU:
        #         try:
        #             log, driver = add_official_debate_transcript(country, gov, 'House', log, link, driver=driver)
        #         except Exception as e:
        #             prnt(str(e))
        #         if special:
        #             xMeets = Meeting.objects.filter(Country_obj=country, GovPage=link, Chamber='House', meeting_type='Debate').first()
        #             if not xMeets:
        #                 if day > 0:
        #                     log, driver = search(day-1, log, driver)
        #         else:
        #             if day > 0:
        #                 log, driver = search(day-1, log, driver)
        #     else:
        #         if day > 0:
        #             log, driver = search(day-1, log, driver)
        #     return log, driver
        # if special == 'testing':
        #     log, driver = search(0, log, None, date_range=7)
        # else:
        search_range = 7
        meetings = Meeting.objects.filter(Country_obj=country, Chamber='House', meeting_type='Debate', DateTime__gte=dt-datetime.timedelta(days=7)).order_by('DateTime')
        if meetings:
            meetingsU = Update.objects.filter(pointerId__in=[i.id for i in meetings], data__contains={'completed_model': True}).order_by('DateTime')
            for u in meetingsU:
                if 'statement_count' in u.data and u.data['statement_count'] > 0:
                    if Statement.objects.filter(Meeting_obj__id=u.pointerId).count() == u.data['statement_count']:
                        if u.validated or u.created > now_utc() - datetime.timedelta(minutes=60):
                            dt_difference = dt - u.DateTime
                            search_range = dt_difference.days

        if search_range > 0:
            # from utils.cronjobs import clear_chrome
            while search_range >= 0:
                utc = dt - datetime.timedelta(days=search_range)
                est = pytz.timezone('US/Eastern')
                today = utc.astimezone(est)
                prnt("EST Time:", today)
                link = f"https://www.govinfo.gov/app/details/CREC-{today.strftime('%Y-%m-%d')}/context"
                prnt(link)
                target = {'link': link, 'gov_id':gov.id}
                if not testing():
                    create_job(get_house_debates, job_timeout=runTimes[func], worker='low', clear_chrome_job=True, special=special, target=target)
                else:
                    get_house_debates(special=special, target=target)
                search_range -= 1

        else:
            utc = dt - datetime.timedelta(days=search_range)
            est = pytz.timezone('US/Eastern')
            today = utc.astimezone(est)
            prnt("EST Time:", today)
            link = f"https://www.govinfo.gov/app/details/CREC-{today.strftime('%Y-%m-%d')}/context"
            log, driver, driver_service = add_official_debate_transcript(country, gov, 'House', log, link, driver=driver, driver_service=driver_service)

            
    try:
        close_browser(driver, driver_service)
    except:
        pass
    prnt('all psassed somehoe')
    return finishScript(log, gov, special)

def get_senate_debates(special=None, dt=now_utc(), iden=None, target={}, driver=None, driver_service=None):
    func = 'get_senate_debates'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, extra=target, log_type='Tasks')
    
    if target and 'link' in target:
        if 'gov_id' in target:
            gov = Government.objects.filter(id=target['gov_id']).first()
        else:
            gov = Government.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').first()
        log, driver, driver_service = add_official_debate_transcript(country, gov, 'Senate', log, target['link'], driver=driver, driver_service=driver_service)

    # # for link in linkList:
    # if special == 'testing' or testing():
    #     linkList, driver = get_senate_activity('debates')
    #     for link in linkList[:2]:
    #         xMeets = Meeting.objects.filter(GovPage=link, Chamber='Senate', meeting_type='Debate', Country_obj=country)
    #         prnt('xmeets',xMeets)
    #         meetingU = Update.objects.filter(pointerId__startswith=get_model_prefix('Meeting'), pointerId__in=[i.id for i in xMeets], data__contains={'completed_model': True}, validated=True).first()
    #             # meeting = Meeting.objects.filter(GovPage=link, Chamber='Senate', meeting_type='Debate', Country_obj=country)[0]
    #         if not meetingU:
    #             try:
    #                 log, driver = add_official_debate_transcript(country, gov, 'Senate', log, link, driver=driver)
    #             except Exception as e:
    #                 prnt('yikes', str(e))
    #                 time.sleep(10)
    else:
        gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
        meetingU = None
        meetings = Meeting.objects.filter(Country_obj=country, Chamber='Senate', meeting_type='Debate', DateTime__gte=dt-datetime.timedelta(hours=24))
        if meetings:
            meetingU = Update.objects.filter(pointerId__in=[i.id for i in meetings], data__contains={'completed_model': True}, validated=True).first()
        if not meetingU:
            linkList, driver, driver_service = get_senate_activity('debates')
            checkLinks = [link for link in reversed(linkList[:5])]
            # for link in reversed(linkList[:5]):
            meetings = Meeting.objects.filter(Country_obj=country, Chamber='Senate', meeting_type='Debate', GovPage__in=checkLinks).order_by('DateTime')
            if meetings:
                meetingsU = Update.objects.filter(pointerId__in=[i.id for i in meetings], data__contains={'completed_model': True}).order_by('DateTime')
                for u in meetingsU:
                    if 'statement_count' in u.data and u.data['statement_count'] > 0:
                        if u.Pointer_obj.GovPage in checkLinks:
                            if Statement.objects.filter(Meeting_obj__id=u.pointerId).count() == u.data['statement_count']:
                                if u.validated or u.created > now_utc() - datetime.timedelta(minutes=60):
                                    checkLinks.remove(u.Pointer_obj.GovPage)
            if checkLinks:
                if len(checkLinks) == 1:
                    log, driver, driver_service = add_official_debate_transcript(country, gov, 'Senate', log, checkLinks[0], driver=driver, driver_service=driver_service)
                else:
                    for link in checkLinks:
                        target = {'link':link, 'gov_id':gov.id}
                        create_job(get_senate_debates, job_timeout=runTimes[func], worker='low', clear_chrome_job=True, special=special, target=target)


        #         # xMeets = Meeting.objects.filter(Country_obj=country, GovPage=link, Chamber='Senate', meeting_type='Debate')
        #         # meetingU = Update.objects.filter(pointerId__in=[i.id for i in xMeets], data__contains={'completed_model': True}).first()
        #             # meeting = Meeting.objects.filter(GovPage=link, Chamber='Senate', meeting_type='Debate', Country_obj=country)[0]
        #         if not meetingU:
        #             log, driver = add_official_debate_transcript(country, gov, 'Senate', log, link, driver=driver)


        # search_range = 7
        # meetings = Meeting.objects.filter(Country_obj=country, Chamber='Senate', meeting_type='Debate', DateTime__gte=dt-datetime.timedelta(days=7)).order_by('DateTime')
        # if meetings:
        #     meetingsU = Update.objects.filter(pointerId__in=[i.id for i in meetings], data__contains={'completed_model': True}).order_by('DateTime')
        #     for u in meetingsU:
        #         dt_difference = dt - u.DateTime
        #         search_range = dt_difference.days

        # if search_range > 0:
        #     from utils.cronjobs import clear_chrome
        #     while search_range >= 0:
        #         utc = dt - datetime.timedelta(days=search_range)
        #         est = pytz.timezone('US/Eastern')
        #         today = utc.astimezone(est)
        #         prnt("EST Time:", today)
        #         link = f"https://www.govinfo.gov/app/details/CREC-{today.strftime('%Y-%m-%d')}/context"
        #         prnt(link)
        #         target = {'link': link, 'gov_id':gov.id}
        #         create_job(get_house_debates, job_timeout=runTimes[func], worker='low', clear_chrome_job=True, special=special, dt=dt, iden=iden, target=target)
        #         search_range -= 1

        # else:
        #     log, driver = add_official_debate_transcript(country, gov, 'Senate', log, link, driver=driver)
    try:
        close_browser(driver, driver_service)
    except:
        pass
    return finishScript(log, gov, special)

def get_senate_motions(special=None, dt=now_utc(), iden=None, target={}, driver=None, driver_service=None):
    func = 'get_senate_motions'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, extra=target, log_type='Tasks')
    
    if target and 'link' in target:
        if 'gov_id' in target:
            gov = Government.objects.filter(id=target['gov_id']).first()
        else:
            gov = Government.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').first()
        log = add_senate_motion(country, gov, log, target['link'])
    else:
        gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
        motion = Motion.objects.filter(Country_obj=country, Chamber='Senate', DateTime__gte=dt-datetime.timedelta(hours=24)).exclude(TotalVotes=0).first()
        if special or not motion:
            grouping, driver, driver_service = get_senate_activity('motions')
            # foundBills = []
            # if billLinks:
            #     if special == 'testing' or testing():
            #         billLinks = billLinks[:1]
            #     for b in billLinks:
            #         q = b['link'].find('/bill/')
            #         if q:
            #             q += len('/bill/')
            #             govNum = b['link'][q:q+3]
            #             # if str(gov.GovernmentNumber) == str(govNum):
            #                 # log, driver = run_bill_func(b, gov.GovernmentNumber, log, driver)
            #             bill = Bill.objects.filter(Country_obj=country, Government_obj=gov, LegisLink__icontains=b['link'].replace('http','')).first()
            #             if bill:
            #                 foundBills.append(bill)
            #             else:
            #                 if 'house' in b['link'].lower() or 'senate' in b['link'].lower():
            #                     a = b['title'].rfind('.')
            #                     bill_prefix = b['title'][:a].replace(' ','').replace('.','').lower()
            #                     bill_num = b['title'][a:].replace('.','').strip()
            #                     time.sleep(1)
            #                     url = f'https://www.govinfo.gov/bulkdata/BILLSTATUS/{govNum}/{bill_prefix}/BILLSTATUS-{govNum}{bill_prefix}{bill_num}.xml'
            #                     log, driver = add_bill(url=url, log=log, driver=driver, country=country, ref_func=func)
                        
            if True == False:
            # if special == 'testing' or testing():
                for link in motionLinks[:1]:
                    motion = Motion.objects.filter(Country_obj=country, GovUrl=link).exclude(TotalVotes=0).first()
                    prnt('motion found:',motion)
                    if not motion:
                        time.sleep(1)
                        log  = add_senate_motion(country, gov, log, link)
            else:
                get_motions = []
                for group in reversed(grouping):
                    motionLinks = grouping[group]['rollcalls']
                    if motionLinks:
                        motions = Motion.objects.filter(Country_obj=country, GovUrl__in=motionLinks).exclude(TotalVotes=0)
                        for motion in motions:
                            if motion.GovUrl in motionLinks:
                                motionLinks.remove(motion.GovUrl)
                                # get_motions.append(link)


                    for link in motionLinks:
                        # motion = Motion.objects.filter(Country_obj=country, GovUrl=link).exclude(TotalVotes=0).first()
                        # if not motion:
                        if link not in get_motions:
                            get_motions.append(link)
                        billLinks = []
                        billData = grouping[group]['bills']
                        for b in billData:
                            q = b['link'].find('/bill/')
                            if q:
                                q += len('/bill/')
                                govNum = b['link'][q:q+3]
                                if 'house' in b['link'].lower() or 'senate' in b['link'].lower():
                                    a = b['title'].rfind('.')
                                    bill_prefix = b['title'][:a].replace(' ','').replace('.','').lower()
                                    bill_num = b['title'][a:].replace('.','').strip()
                                    # time.sleep(1)
                                    url = f'https://www.govinfo.gov/bulkdata/BILLSTATUS/{govNum}/{bill_prefix}/BILLSTATUS-{govNum}{bill_prefix}{bill_num}.xml'
                                    if url not in billLinks:
                                        billLinks.append(url)
                        if billLinks:
                            billUpdates = Update.objects.filter(pointerId__startswith=get_model_prefix('Bill'), Region_obj=country, data__data_link__in=billLinks)
                            # bill = Bill.objects.filter(Country_obj=country, Government_obj=gov, LegisLink__icontains=b['link'].replace('http','')).first()
                            for u in billUpdates:
                                if u.data['data_link'] in billLinks:
                                    billLinks.remove(u.data['data_link'])

                            for url in billLinks:
                                log, driver, driver_service = add_bill(url=url, log=log, driver=driver, driver_service=driver_service, country=country, ref_func=func)
                                if url != billLinks[-1]:
                                    time.sleep(1)

                if len(get_motions) == 1:
                    log = add_senate_motion(country, gov, log, get_motions[0])
                else:
                    for link in get_motions:
                        target = {'link':link, 'gov_id':gov.id}
                        create_job(get_senate_motions, job_timeout=runTimes[func], worker='low', clear_chrome_job=False, special=special, target=target)
                        # log = add_senate_motion(country, gov, log, link)
                        # if link != get_motions[-1]:
                        #     time.sleep(1)
                try:
                    close_browser(driver, driver_service)
                except:
                    pass
    return finishScript(log, gov, special)

def get_senate_activity(target):
    url = 'https://www.senate.gov/legislative/LIS/floor_activity/all-floor-activity-files.htm'
    try:
        driver, driver_service = open_browser(url)
        element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="floor_activity_table"]/tbody'))
        WebDriverWait(driver, 10).until(element_present)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # close_browser(driver, driver_service)
    except Exception as e:
        prnt('senate activitiy fail 3434', str(e))

    debateLinks = []
    motionLinks = {}
    billLinks = []
    grouping = {}
    tbody = soup.find('tbody')
    trs = tbody.find_all('tr', {'role':'row'})
    group = 0
    for tr in trs:
        group += 1
        grouping[group] = {'rollcalls':[],'bills':[]}
        tds = tr.find_all('td')
        for td in tds:
            try:
                span = td.find('span')
                prnt(span.text)
            except:
                pass
            links = td.find_all('a')
            for link in links:
                if 'Congressional Record' in link.text and target == 'debates':
                    prnt(link.text)
                    prnt(link['href'])
                    debateLinks.append(link['href'])
                elif 'roll_call_vote' in link['href'] and target == 'motions':
                    prnt(link['href'])
                    # motionLinks.append(link['href'])
                    if link['href'] not in grouping[group]['rollcalls']:
                        grouping[group]['rollcalls'].append(link['href'])
                elif 'bill' in link['href'] and 'n/a' not in link.text and target == 'motions':
                    prnt(link['href'])
                    # billLinks.append({'title':link.text.replace(' ',''), 'link':link['href']})
                    bill = {'title':link.text.replace(' ',''), 'link':link['href']}
                    if bill not in grouping[group]['bills']:
                        grouping[group]['bills'].append(bill)
        prnt()
    if target == 'debates':
        return debateLinks, driver, driver_service
    else:
        return grouping, driver, driver_service

def add_senate_motion(country, gov, log, url):
    prnt('add_senate_motion')
    # url = 'https://www.senate.gov/legislative/LIS/roll_call_votes/vote1182/vote_118_2_00128.xml'
    xml = url.replace('htm', 'xml')
    prnt(xml)
    r = requests.get(xml)
    # prnt(r.content)
    root = ET.fromstring(r.content)

    congress = root.find('congress').text
    session = root.find('session').text
    congress_year = root.find('congress_year').text
    vote_number = root.find('vote_number').text
    vote_date = root.find('vote_date').text
    # July 11, 2024, 01:22 PM
    vote_dt = timezonify('est', datetime.datetime.strptime(vote_date, '%B %d, %Y, %I:%M %p'))
    prnt(vote_dt)
    modify_date = root.find('modify_date').text
    vote_question_text = root.find('vote_question_text').text
    vote_document_text = root.find('vote_document_text').text
    vote_result_text = root.find('vote_result_text').text
    question = root.find('question').text
    vote_title = root.find('vote_title').text
    majority_requirement = root.find('majority_requirement').text
    vote_result = root.find('vote_result').text
    prnt(vote_result)
    prnt(congress)
    prnt(session)
    prnt(gov)
    if int(congress) != gov.GovernmentNumber or int(session) != gov.SessionNumber:
        return log

    prnt(f"vote_number: {vote_number}")
    prnt(f"vote_date: {vote_date}")
    prnt(f"vote_question_text: {vote_question_text}")
    prnt(f"vote_result_text: {vote_result_text}")
    prnt(f"question: {question}")
    prnt(f"vote_title: {vote_title}")
    prnt(f"vote_result: {vote_result}")
    prnt("")

    try:
        document = root.find('document')
        document_congress = document.find('document_congress').text
        document_type = document.find('document_type').text
        document_number = document.find('document_number').text
        document_name = document.find('document_name').text
        document_title = document.find('document_title').text
        document_short_title = document.find('document_short_title').text
        prnt(f"document_number: {document_number}")
        bill = Bill.objects.filter(NumberCode=document_name.replace(' ',''), Country_obj=country, Government_obj=gov).first()
    except:
        document_name = None
        bill = None

    try:
        amendment = root.find('amendment')
        amendment_number = amendment.find('amendment_number').text
        amendment_to_amendment_number = amendment.find('amendment_to_amendment_number').text
        amendment_to_amendment_to_amendment_number = amendment.find('amendment_to_amendment_to_amendment_number').text
        amendment_to_document_number = amendment.find('amendment_to_document_number').text
        amendment_to_document_short_title = amendment.find('amendment_to_document_short_title').text
        amendment_purpose = amendment.find('amendment_purpose').text
    except:
        pass

    count = root.find('count')
    yeas = count.find('yeas').text
    nays = count.find('nays').text
    present = count.find('present').text
    absent = count.find('absent').text

    tie_breaker = root.find('tie_breaker')
    by_whom = tie_breaker.find('by_whom').text
    tie_breaker_vote = tie_breaker.find('tie_breaker_vote').text

    motion, motionU, motion_is_new = get_model_and_update('Motion', VoteNumber=vote_number, GovUrl=url, Chamber='Senate', Country_obj=country, Government_obj=gov, Region_obj=country)
    if motion_is_new:
        motion.DateTime = vote_dt
        motion.DecisionType = majority_requirement
        motion.Result = vote_result
        motion.MotionText = vote_document_text
        motion.Subject = vote_question_text
        motion.billCode = document_name
        motion.Bill_obj = bill
        motion.Yeas = yeas
        motion.Nays = nays
        motion.Present = present
        motion.Absent = absent
        motion.is_official = True
        motion.save()
        # motion, motionU, motion_is_new, log = save_and_return(motion, motionU, motion_is_new, log)

        yea_count = 0
        nay_count = 0
        present_count = 0
        np_count = 0
        unknown_count = 0
        total_count = 0

        # party_list = []
        result_data = {'Parties':[], 'Votes':[], 'PartyData':{}}
        members = root.find('members')
        for member in members:
            member_full = member.find('member_full').text
            last_name = member.find('last_name').text
            first_name = member.find('first_name').text
            party_short = member.find('party').text
            stateShort = member.find('state').text
            voteValue = member.find('vote_cast').text
            lis_member_id = member.find('lis_member_id').text

            if party_short == 'R':
                party_name = 'Republican'
            elif party_short == 'D':
                party_name = 'Democrat'
            elif party_short == 'I':
                party_name = 'Independent'
            else:
                party_name = party_short
            found = False
            for i in result_data['Parties']:
                if i['Name'] == party_name:
                    i['Count'] += 1
                    found = True
                    break
            if not found:
                result_data['Parties'].append({'Name':party_name, 'Count':1})
            # if party_name not in party_list:
            #     party_list.append(party_name)

            stateName = state_list[stateShort]
            personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__Position__contains='Senator', data__member_detail__icontains=member_full).first()
            # xSens = Role.objects.filter(Position='Senator', member_detail=member_full, Country_obj=country)
            # rU = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in xSens], data__contains={'Current': True}).first()
            if not personU:
                personU = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__Position__contains='Senator', data__LastName__icontains=last_name, data__FirstName__icontains=first_name).first()

            if personU:
                p = personU.Pointer_obj
                vote, voteU, vote_is_new = get_model_and_update('Vote', Motion_obj=motion, Person_obj=p, PersonFullName=f'{personU.data["LastName"]}, {personU.data["FirstName"]}', Chamber='Senate', ConstituencyProvStateName=stateName, CaucusName=party_name, Country_obj=country, Government_obj=motion.Government_obj, Region_obj=country)
            else:
                p = None
                memberName = last_name + ', ' + first_name
                vote, voteU, vote_is_new = get_model_and_update('Vote', Motion_obj=motion, PersonFullName=memberName, Chamber='Senate', ConstituencyProvStateName=stateName, CaucusName=party_name, Country_obj=country, Government_obj=motion.Government_obj, Region_obj=country)
            prnt('person:',p)

            vote.Party_obj = Party.objects.filter(ShortName=party_short).first()
            # vote.District_obj = District.objects.filter(id=personU.data['District_id']).first()
            vote.DateTime = vote_dt
            vote.PersonId = lis_member_id
            vote.IsVoteNay = False
            vote.IsVoteYea = False
            vote.IsVotePresent = False
            vote.IsVoteAbsent = False
            vote.VoteValue = voteValue
            if voteValue.lower() == 'no' or voteValue.lower() == 'nay':
                vote.IsVoteNay = True
                nay_count += 1
            elif voteValue.lower() == 'aye' or voteValue.lower() == 'yea':
                vote.IsVoteYea = True
                yea_count += 1
            elif voteValue.lower() == 'present':
                vote.IsVotePresent = True
                present_count += 1
            elif voteValue.lower() == 'not voting':
                vote.IsVoteAbsent = True
                np_count += 1
            else:
                unknown_count += 1
            found = False
            for i in result_data['Votes']:
                if i['Vote'] == voteValue:
                    i['Count'] += 1
                    found = True
                    break
            if not found:
                result_data['Votes'].append({'Vote':voteValue, 'Count':1})
            total_count += 1
            vote, voteU, vote_is_new, log = save_and_return(vote, voteU, log)

            # prnt(f"Member Full: {member_full}")
            # prnt(f"Last Name: {last_name}")
            # prnt(f"First Name: {first_name}")
            # prnt(f"Party: {party_short}")
            # prnt(f"State: {stateShort}")
            # prnt(f"vote_cast: {voteValue}")
            # prnt(f"lis_member_id: {lis_member_id}")
            # prnt("")

        for i in result_data['Parties']:
            party_name = i['Name']
            count = i['Count']
            party = Party.objects.filter(Country_obj=country, Region_obj=country, gov_level='Federal').filter(Q(Name=party_name)|Q(AltName=party_name)).first()
            if party:
                i['Color'] = party.Color
                i['obj_id'] = party.id
            # prnt('p',p)
            # result_data['PartyData'][party_name] = p
            # if not p['Name'] in [i['Name'] for i in motion.party_array]:
            #     motion.party_array.append(p)
        sorted_votes = sorted(result_data['Votes'], key=lambda item: item['Count'], reverse=True)
        result_data['Votes'] = sorted_votes
        sorted_parties = sorted(result_data['Parties'], key=lambda item: item['Count'], reverse=True)
        result_data['Parties'] = sorted_parties
        # for party_name in party_list:
        #     try:
        #         party = Party.objects.filter(Name=party_name, Country_obj=country, Region_obj=country, gov_level='Federal')[0]
        #         motion.Party_objs.add(party)
        #     except:
        #         pass
        motion.result_data = result_data
        motion.TotalVotes = total_count
        motion, motionU, motion_is_new, log = save_and_return(motion, motionU, log)
    return log

def get_general_election_candidates(special=None, dt=now_utc(), iden=None):
    
    func = 'get_general_election_candidates'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')
    

    to_zone = tz.gettz(country.timezone)
    local_dt = now_utc().astimezone(to_zone)
    today = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    # dayOfWeek = today.weekday()
    # prnt(dayOfWeek)

    def get_presidential(dt, log):
        prnt('get_presidential')
        url = f'https://ballotpedia.org/Presidential_candidates,_{dt.year}'

        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        # prnt(soup)
        election = None
        election_date = None
        get_candidates = None
        # found_images = False
        # candidate_list = []
        infobox = soup.find('table',{'class':'infobox'})
        for tr in infobox.find_all('tr'):
            prnt('1')
            if not election and 'date' in tr.text.lower():
                # prnt('tr.text',tr.text)
                prnt('2')
                x = tr.text.lower().find('date')
                # prnt('x',x)
                dt = tr.text[x:].replace('Date:','').strip()
                # prnt('dt',dt)
                election_date = timezonify('est', datetime.datetime.strptime(dt, '%B %d, %Y'))
                prnt('election_date',election_date)
                prnt()
                election, electionU, election_is_new = get_model_and_update('Election', DateTime=election_date, type='Presidential', gov_level='Federal', Chamber='Executive', Country_obj=country, Region_obj=country, Government_obj=gov)
                electionU.data['url'] = url
                if election_is_new:
                    election, electionU, election_is_new, log = save_and_return(election, electionU, log)
            elif election and 'presidential candidates' in tr.text.lower() and get_candidates == None:
                prnt('3')
                get_candidates = True
            elif election and get_candidates:
                prnt('4')
                get_candidates = False
                candidate_name = None
                person_page = None
                party = None
                thumbnail_link = None
                get_party = True
                get_candidate = False
                for a in tr.find_all('a'):
                    prnt('5')
                    if get_party:
                        prnt('6')
                        party_name = a['title']
                        prnt('party',party_name)
                        party_name, party_short, alt_name = find_party(party_name=party_name)
                        party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=country, Region_obj=country, gov_level='Federal')
                        if party_is_new:
                            if get_wiki:
                                try:
                                    time.sleep(1)
                                    search_name = party_name + ' american federal political party'
                                    prnt(search_name)
                                    link = wikipedia.search(search_name)[0].replace(' ', '_')
                                    party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                                    prnt('party.Wiki',party.Wiki)
                                except Exception as e:
                                    prnt('party:',str(e))
                                    pass
                            party, partyU, party_is_new, log = save_and_return(party, partyU, log)
                        get_party = False
                        get_candidate = True
                    elif get_candidate:
                        prnt('7')
                        person_page = a['href']
                        candidate_text = a.text
                        # candidate_list.append(candidate_text)
                        x = candidate_text.find(' (')
                        y = candidate_text.find(')')
                        party_short = candidate_text[x+2:y]
                        candidate_name = candidate_text[:x]
                        prnt('candidate',candidate_name)
                        prnt('party_short',party_short)

                        #  prnt('candidate_list',candidate_list)
                        image_grid = soup.find('div',{'class':'image-grid'})
                        for div in image_grid.find_all('div',{'class':'bp-card-round'}):
                            name = div.find('div',{'class':'p-4'})
                            if name:
                                if name.text == candidate_text:
                                    icon = div.find('div',{'class':'icon-container-xl'})
                                    if icon:
                                        img = icon.find('img')
                                        thumbnail_link = img['src']
                                        prnt('thumbnail',thumbnail_link)
                                        break
                        get_party = True
                        get_candidate = False
                        prnt()
                if candidate_name:
                    prnt('8')
                    personUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__FullName=candidate_name).first()
                    if not personUpdate:
                        personUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__FirstName__icontains=candidate_name.split(' ')[0], data__LastName__icontains=candidate_name.split(' ')[-1]).first()
                    
                    if personUpdate:
                        # prnt('pers',person)
                        person, personU, person_is_new = get_model_and_update('Person', id=personUpdate.pointerId, Country_obj=country, Region_obj=country)
                    else:
                        person, personU, person_is_new = get_model_and_update('Person', GovIden=candidate_name, Country_obj=country, Region_obj=country)
                    personU.data['FirstName'] = candidate_name.split(' ')[0]
                    personU.data['LastName'] = candidate_name.split(' ')[-1]
                    personU.data['FullName'] = candidate_name
                    # personU.data['Position'] = 'Congressional Representative'
                    # personU.data['gov_level'] = 'Federal'
                    if thumbnail_link:
                        if 'PhotoLink' not in personU.data or personU.data['PhotoLink'] == '':
                            personU.data['PhotoLink'] = thumbnail_link
                    data = {'role':'Presidential Candidate','current':True,'gov_level':'Federal','Election_id':election.id,'election_date':dt_to_string(election_date)}
                    if party:
                        data['Party_id'] = party.id
                    if person_page:
                        data['ballotpedia_link'] = person_page
                    # if start_date:
                    #     data['StartDate'] = dt_to_string(start_date)
                    person.update_role(personU, data=data)
                    # prnt('3')
                    # prnt(model_to_dict(personU))
                    person, personU, person_is_new, log = save_and_return(person, personU, log)
        return log

    def get_congress(dt, log):
        url = f'https://ballotpedia.org/United_States_Congress_elections,_{dt.year}'

        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        election_date = None
        infobox = soup.find('table',{'class':'infobox'})
        for tr in infobox.find_all('tr'):
            if not election_date and 'election date' in tr.text.lower():
                dt = tr.text.replace('Election Date','').strip()
                election_date = timezonify('est', datetime.datetime.strptime(dt, '%B %d, %Y'))
                prnt('election_date',election_date)

        tabs = soup.find_all('div',{'role':'tabpanel'})
        # prnt('tabs',tabs)
        for tab in tabs:
            state = None
            caption = tab.find('caption')
            if caption and 'Candidates - 2024' in caption.text:

                c = caption.text.lower().find('candidates')
                state_chamber = caption.text[:c]
                if 'House' in state_chamber:
                    chamber = 'House'
                    state_name = state_chamber.replace('House','').strip()
                elif 'Senate' in state_chamber:
                    chamber = 'Senate'
                    state_name = state_chamber.replace('Senate','').strip()
                
                if election_date:
                    election, electionU, election_is_new = get_model_and_update('Election', DateTime=election_date, type='Congressional', gov_level='Federal', Chamber=chamber, Country_obj=country, Region_obj=country, Government_obj=gov)
                    electionU.data['url'] = url
                    if election_is_new:
                        election, electionU, election_is_new, log = save_and_return(election, electionU, log)

                    state = Region.valid_objects.filter(Name__icontains=state_name, nameType='State', modelType='provState', ParentRegion_obj=country).first()


                    prnt('\n---',caption.text)
                    tbody = tab.find('tbody')
                    for tr in tbody.find_all('tr'):
                        candidate_name = None
                        person_page = None
                        thumbnail_link = None
                        party = None
                        district = None
                        candidate_status = None
                        for td in tr.find_all('td'):
                            if td['data-cell'] == 'candidate':
                                info = td.find('div',{'class':'widget-candidate-info'})
                                candidate_name = info.text
                                a = info.find('a')
                                person_page = a['href']

                        thumb = td.find('div',{'class':'widget-candidate-thumbnail'})
                        if thumb:
                            img = thumb.find('img')
                            if img:
                                thumbnail_link = img['src']

                        if td['data-cell'] == 'party':
                            span = td.find('span',{'class':'party-affiliation'})
                            if span:
                                party_name = span.text
                                party_name, party_short, alt_name = find_party(party_name=party_name)
                                party, partyU, party_is_new = get_model_and_update('Party', Name=party_name, AltName=alt_name, ShortName=party_short, Country_obj=country, Region_obj=country, gov_level='Federal')
                                if party_is_new:
                                    if get_wiki:
                                        try:
                                            time.sleep(1)
                                            search_name = party_name + ' american federal political party'
                                            prnt(search_name)
                                            link = wikipedia.search(search_name)[0].replace(' ', '_')
                                            party.Wiki = 'https://en.wikipedia.org/wiki/' + link
                                            prnt('party.Wiki',party.Wiki)
                                        except Exception as e:
                                            prnt('party:',str(e))
                                            pass
                                    party, partyU, party_is_new, log = save_and_return(party, partyU, log)

                        if td['data-cell'] == 'office':
                            a = td.find('a')
                            if a:
                                office_name = a.text
                                x = office_name.find(state_name)+len(state_name)
                                district_name = office_name[x:].strip()
                                district = District.objects.filter(Name__iexact=district_name, Country_obj=country, Region_obj=country, ProvState_obj=state, gov_level='Federal', nameType='Congressional District').first()


                        if td['data-cell'] == 'status':
                            if 'on the ballot' in td.text.lower() and 'general' in td.text.lower():
                                candidate_status = td.text
                                for span in td.find_all('span',{'class':'sub-detail'}):
                                    candidate_status = candidate_status.replace(span.text,'')    

                    if candidate_status:
                        prnt('candidate_name',candidate_name)
                        prnt('person_page',person_page)
                        prnt('thumbnail_link',thumbnail_link)
                        prnt('party',party)
                        prnt('district',district)
                        prnt('candidate_status',candidate_status)    
                        prnt('') 
                    if candidate_name:

                        personUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__FullName=candidate_name).first()
                        if not personUpdate:
                            personUpdate = Update.objects.filter(pointerId__startswith=get_model_prefix('Person'), Region_obj=country, data__FirstName__icontains=candidate_name.split(' ')[0], data__LastName__icontains=candidate_name.split(' ')[-1]).first()
                        
                        if personUpdate:
                            person, personU, person_is_new = get_model_and_update('Person', id=personUpdate.pointerId, Country_obj=country, Region_obj=country)
                        else:
                            person, personU, person_is_new = get_model_and_update('Person', GovIden=candidate_name, Country_obj=country, Region_obj=country)
                        # personU.data['District_id'] = m['district'].id
                        # personU.data['ProvState_id'] = m['state'].id
                        personU.data['FirstName'] = candidate_name.split(' ')[0]
                        personU.data['LastName'] = candidate_name.split(' ')[-1]
                        personU.data['FullName'] = candidate_name
                        if thumbnail_link:
                            if 'PhotoLink' not in personU.data or personU.data['PhotoLink'] == '':
                                personU.data['PhotoLink'] = thumbnail_link
                        r = f'{chamber} Candidate'
                        data = {'role':r,'current':True,'gov_level':'Federal','Election_id':election.id,'election_date':dt_to_string(election_date),'ProvState_id':state.id,'status':candidate_status}
                        if party:
                            data['Party_id'] = party.id
                        if person_page:
                            data['ballotpedia_link'] = person_page
                        if district:
                            data['District_id'] = district.id
                        person.update_role(personU, data=data)
                        person, personU, person_is_new, log = save_and_return(person, personU, log)
                    # break
        return log
    
    if today.day <= 7 or special == 'testing':
        log = get_presidential(local_dt, log)
        log = get_congress(local_dt, log)

    else:
        pres_election = Election.objects.filter(DateTime__gte=local_dt + datetime.timedelta(days=90), type='Presidential', gov_level='Federal', Chamber='Executive', Country_obj=country, Region_obj=country).first()
        if pres_election:
            log = get_presidential(local_dt, log)
        
        cong_election = Election.objects.filter(DateTime__gte=local_dt + datetime.timedelta(days=90), type='Congressional', gov_level='Federal', Country_obj=country, Region_obj=country).first()
        if cong_election:
            log = get_congress(local_dt, log)

    return finishScript(log, gov, special)

def get_general_elections_results(special=None, dt=now_utc(), iden=None):

    func = 'get_general_elections_results'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    if special != 'testing':
        logEvent('scrapeAssignment', region=country, func=func, log_type='Tasks')
    

    url = 'https://ballotpedia.org/Election_results,_2024#Results_summary'

    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    # prnt(soup)
    votebox = soup.find('div',{'class':'votebox'})
    header = votebox.find('div',{'race_header'})
    if 'Presidential' in header.text:
        tbody = votebox.find('tbody')
        for tr in tbody.find_all('tr'):
            try:
                prnt()
                td = tr.find_all('td')
                for a in td[2].find_all('a'):
                    prnt(a.text)
                percentage = td[3].find('div',{'class':'percentage_number'})
                if percentage:
                    prnt(percentage.text)
                
                pop_votes = td[4].text
                prnt(pop_votes)
                elec_votes = td[5].text
                prnt(elec_votes)
            except:
                pass
        
    # example prntout

    # Electoral votes

    # Donald Trump
    # J.D. Vance
    # 50.5
    # 19,784,173
    # 168

    # Kamala D. Harris
    # Tim Walz
    # 48.7
    # 19,088,078
    # 92

    # Chase Oliver
    # Mike ter Maat
    # 0.3
    # 120,247
    # 0

    # Jill Stein
    # 0.3
    # 118,108
    # 0

    # Robert F. Kennedy Jr.
    # Nicole Shanahan
    # 0.1
    # 45,191
    # 0

    # Peter Sonski
    # Lauren Onak
    # 0.0
    # 12,893
    # 0
    return finishScript(log, gov, special)



def get_user_region(address=None, city=None, zip_code=None, state=None, special=None, dt=now_utc(), iden=None):
    prnt('run get_user_region')
    func = 'get_user_region'
    country = Region.valid_objects.filter(modelType='country', Name='USA').first()
    log = create_share_object(func, country, special=special, dt=dt, iden=iden)
    gov = Government.objects.filter(Country_obj=country, gov_level='Federal').first()
    # if not special:
    #     logEvent('scrapeAssignment: ' + country.Name + ' ' + func + ' ' + str(now_utc()))
    if not address:
        address = '721 5th avenue'
        city = 'New York City'
        zip_code = '10022'
        state = 'New York'

    try:
        from sonet.special.api_keys import google_civicInfo
    except:
        google_civicInfo = '1111'
    url = f'https://civicinfo.googleapis.com/civicinfo/v2/representatives?address={address} {city}, {state} {zip_code}&key={google_civicInfo}'
    prnt(url)
    r = requests.get(url)
    data = r.json()
        
    context = {'country':[], 'administrativeArea1':[], 'administrativeArea2':[], 'locality':[], 'unknown':[]}

    for i in data['divisions']:
        try:
            level = 'unknown'
            # prnt('division:',data['divisions'][i])
            indices = data['divisions'][i]['officeIndices']
            # for n in indices:
            #     officials = data['officials'][n]
            # prnt('--offices:')
            for n in indices:
                temp = {'division':data['divisions'][i], 'offices':[]}
                officeData = data['offices'][n]
                # prnt('office:',officeData)
                level = officeData['levels'][0]
                # prnt('level:',level)
                office = {'office':officeData, 'officials':[]}
                officialIndices = officeData['officialIndices']
                # prnt('--officials:')
                for o in officialIndices:
                    # prnt(data['officials'][o])
                    office['officials'].append(data['officials'][o])
                temp['offices'].append(office)
                context[level].append(temp)
            # n += 1
            #     prnt()
            # prnt('----')
            # prnt()
        except:
            pass

    prnt('next\n')
    def process_me(level, returnData, log):
        prnt('ROCESS ME:',level)
        if level == 'locality':
            gov_level = 'City'
        elif level == 'administrativeArea2':
            gov_level = 'County'
        elif level == 'administrativeArea1':
            gov_level = 'State'
        elif level == 'country':
            gov_level = 'Federal'

        # "administrativeArea1"
        # "administrativeArea2"
        # "country"
        # "international"
        # "locality"
        # "regional"
        # "special"
        # "subLocality1"
        # "subLocality2"
        if gov_level not in returnData:
            returnData[gov_level] = {}
        for i in context[level]:

            # prnt(i['division'])
            prnt(i['division']['name'])
            for office in i['offices']:
                # prnt(office['office'])
                person = None
                chamber = None
                state = None
                district = None
                region = None
                office_name = office['office']['name']
                if 'U.S. Representative' in office_name:
                    office_name = 'Congressional Representaive'
                    chamber = 'House'
                if 'Senator' in office_name:
                    office_name = 'Senator'
                    chamber = 'Senate'
                if 'President' in office_name:
                    chamber = 'Executive'
                prnt(office_name)
                returnData[gov_level][office_name] = []
                prnt('roles:')
                for r in office['office']['roles']:
                    prnt(r)
                iden = office['office']['divisionId']
                prnt(iden)
                if 'state:' in iden:
                    a = iden.find('state:')+len('state:')
                    b = iden[a:].find('/')
                    if b > 0:
                        state_short_name = iden[a:a+b]
                        prnt('get provstate:', state_short_name)
                    else:
                        state_short_name = iden[a:]
                        prnt('get provstate:', state_short_name)
                    state_name = state_list[state_short_name.upper()]
                    state = Region.valid_objects.filter(Name=state_name, ParentRegion_obj=country, modelType='provState').first()
                    if not state:
                        # if gov_level == 'State' and state.add_office(office_name):
                        #     state.update_data()
                        #     log.updateShare(state)
                    # else:
                        state = Region(Name=state_name, ParentRegion_obj=country, modelType='provState', nameType='State', AbbrName=state_short_name.upper(), Office_array=[office_name], func=func)
                        state.update_data()
                        log.updateShare(state)
                if 'cd:' in iden:
                    a = iden.find('cd:')+len('cd:')
                    district_name = iden[a:]
                    prnt('get congressionsiaonl district', district_name)
                    chamber = 'House'
                    district = District.objects.filter(Name=district_name, ProvState_obj=state, gov_level=gov_level).first()
                    if not district:
                        # if district.add_office(office_name):
                        #     district.update_data()
                        #     log.updateShare(district)
                    # else:
                        district = District(Name=district_name, ProvState_obj=state, gov_level=gov_level, Country_obj=country, Chamber=chamber, nameType='Congressional District', Office_array=[office_name], func=func)
                        district.update_data()
                        log.updateShare(district)
                    elif not district.Office_array or office_name not in district.Office_array:
                        district = district.propose_modification()
                        district.add_office(office_name)
                        log.updateShare(district)
                elif 'sldl:' in iden:
                    a = iden.find('sldl:')+len('sldl:')
                    state_assembly_district = iden[a:]
                    prnt('get state assembly district', state_assembly_district)
                    chamber = 'House'
                    district = District.objects.filter(Name=state_assembly_district, ProvState_obj=state, gov_level=gov_level, Chamber=chamber).first()
                    if not district:
                        # if district.add_office(office_name):
                        #     district.update_data()
                        #     log.updateShare(district)
                    # else:
                        district = District(Name=state_assembly_district, ProvState_obj=state, gov_level=gov_level, Country_obj=country, Chamber=chamber, nameType='Assembly District', Office_array=[office_name], func=func)
                        district.update_data()
                        log.updateShare(district)
                    elif not district.Office_array or office_name not in district.Office_array:
                        district = district.propose_modification()
                        district.add_office(office_name)
                        log.updateShare(district)
                elif 'sldu:' in iden:
                    a = iden.find('sldu:')+len('sldu:')
                    state_senate_district = iden[a:]
                    prnt('get state senate district', state_senate_district)
                    chamber = 'Senate'
                    district = District.objects.filter(Name=state_senate_district, ProvState_obj=state, gov_level=gov_level, Chamber=chamber).first()
                    if not district:
                        # if district.add_office(office_name):
                        #     district.update_data()
                        #     log.updateShare(district)
                    # else:
                        district = District(Name=state_senate_district, ProvState_obj=state, gov_level=gov_level, Country_obj=country, Chamber=chamber, nameType='State District', Office_array=[office_name], func=func)
                        district.update_data()
                        log.updateShare(district)
                    elif not district.Office_array or office_name not in district.Office_array:
                        district = district.propose_modification()
                        district.add_office(office_name)
                        log.updateShare(district)
                elif 'county:' in iden:
                    a = iden.find('county:')+len('county:')
                    # county_name = iden[a:].replace('_',' ').title()
                    county_name = i['division']['name']
                    prnt('get county', county_name)
                    region = Region.valid_objects.filter(Name=county_name, ParentRegion_obj=state, modelType='county').first()
                    if not region:
                        # if region.add_office(office_name):
                        #     region.update_data()
                        #     log.updateShare(region)
                    # else:
                        region = Region(Name=county_name, ParentRegion_obj=state, modelType='county', nameType='County', Office_array=[office_name], func=func)
                        region.update_data()
                        log.updateShare(region)
                    # region.add_office(office_name)
                    elif not region.Office_array or office_name not in region.Office_array:
                        region = region.propose_modification()
                        region.add_office(office_name)
                        log.updateShare(region)
                elif 'place:' in iden:
                    a = iden.find('place:')+len('place:')
                    # locality_name = iden[a:].replace('_',' ').title()
                    locality_name = i['division']['name']
                    prnt('get municpality', locality_name)
                    region = Region.valid_objects.filter(Name=locality_name, ParentRegion_obj=country, modelType='city').first()
                    if not region:
                        # if region.add_office(office_name):
                        #     region.update_data()
                        #     log.updateShare(region)
                    # else:
                        region = Region(Name=locality_name, ParentRegion_obj=country, modelType='city', nameType='City', Office_array=[office_name], func=func)
                        region.update_data()
                        log.updateShare(region)
                    elif not region.Office_array or office_name not in region.Office_array:
                        region = region.propose_modification()
                        region.add_office(office_name)
                        log.updateShare(region)
                prnt('-')
                for p in office['officials']:
                    # prnt(p)
                    if not region:
                        region = country
                    if 'name' in p:
                        person_name = p['name']
                        prnt('----PERSON NASME---',person_name, office_name)
                        z = person_name.find(',')
                        if z > 0:
                            p_name2 = person_name[:z]
                        else:
                            p_name2 = person_name
                        role = None
                        # prnt('!!!!!!')
                        # prnt(office_name)
                        # prnt(country)
                        # prnt(gov_level)
                        # prnt(p_name2)
                        xRoles = Role.objects.filter(Position=office_name, Country_obj=country, gov_level=gov_level, Person_obj__FullName__icontains=p_name2)
                        # prnt(xRoles)
                        roleU = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in xRoles], data__contains={'Current': True}).first()
                        # prnt(roleU)
                        if roleU:
                            # prnt('11')
                            role = xRoles.filter(id=roleU.pointerId).first()
                            # prnt(role)
                            person = role.Person_obj
                        else:
                            # prnt('else')
                            person = Person.objects.filter(FullName__icontains=p_name2, Country_obj=country).first()
                            if not person:
                                names = p_name2.split(' ')
                                person = Person.objects.filter(FirstName__icontains=names[0], LastName__icontains=names[-1], Country_obj=country).first()
                                if not person:
                                    person = Person(FirstName=names[0], LastName=names[-1], FullName=person_name, Country_obj=country, func=func)
                                    person.update_data()
                                    log.updateShare(person)

                        # prnt(person)
                        # prnt('r',role)
                        # person, personU, person_is_new = get_model_and_update('Person', GovIden=bioguide_id, FirstName=first_name, LastName=last_name, Country_obj=country, Region_obj=country)
                        person.Position = office_name
                        # person.GovProfilePage = link
                        # person.Telephone = phone
                        # person.Party_obj = party
                        # person, personU, person_is_new, log = save_and_return(person, personU, person_is_new, log)
                        if role:
                            role, roleU, role_is_new = get_model_and_update('Role', obj=role)
                        else:
                            role, roleU, role_is_new = get_model_and_update('Role', Person_obj=person, Position=office_name, Chamber=chamber, gov_level=gov_level, ProvState_obj=state, Country_obj=country, Region_obj=region, District_obj=district)

                    if 'address' in p:
                        if role_is_new:
                            role.Addresses = []
                        else:
                            roleU.data['Addresses'] = []
                        for a in p['address']:
                            prnt('address:')
                            prnt(a['line1'])
                            prnt(a['city'])
                            prnt(a['state'])
                            prnt(a['zip'])
                            addr = a['line1'] + ' ' + a['city'] + ' ' + a['state'] + ' ' + a['zip']
                            if role_is_new:
                                role.Addresses.append(addr)
                            else:
                                roleU.data['Addresses'].append(addr)
                        # prnt(p['address'])
                    if 'party' in p:
                        party_name = p['party'].replace(' Party','')
                        prnt(party_name)
                        party = Party.objects.filter(Name=party_name, Country_obj=country, gov_level=gov_level).first()
                        if not party:
                            party = Party(Name=party_name, Country_obj=country, gov_level=gov_level, ProvState_obj=state, Region_obj=region, func=func)
                            party.update_data()
                            log.updateShare(party)
                        person.Party_obj = party
                        role.Party_obj = party
                        # if not role_is_new:
                        #     roleU.Party_obj = party
                    if 'phones' in p:
                        prnt('telephone:')
                        for t in p['phones']:
                            prnt(t)
                        person.Telephones = p['phones']
                        role.Telephones = p['phones']
                        if not role_is_new:
                            roleU.data['Telephones'] = p['phones']
                    if 'photoUrl' in p:
                        photo_url = p['photoUrl']
                        prnt(photo_url)
                        person.PhotoLink = photo_url
                        role.PhotoLink = photo_url
                        if not role_is_new:
                            roleU.data['PhotoLink'] = photo_url
                    if 'urls' in p:
                        prnt('urls:')
                        person.Websites = []
                        role.Websites = []
                        for u in p['urls']:
                            prnt(u)
                            if 'wiki' in u:
                                person.Wiki = u
                            else:
                                person.Websites.append(u)
                                role.Websites.append(u)
                            if '.gov' in u:
                                role.GovPage = u
                                if not role_is_new:
                                    roleU.data['GovPage'] = u
                    if 'emails' in p:
                        prnt('emails:')
                        for e in p['emails']:
                            prnt(e)
                        person.Emails = p['emails']
                        role.Emails = p['emails']
                        if not role_is_new:
                            roleU.data['Emails'] = p['emails']
                    if 'channels' in p:
                        prnt('socials:')
                        for c in p['channels']:
                            prnt(c['type'])
                            prnt(c['id'])
                        person.Socials = p['channels']
                        role.Socials = p['channels']
                        if not role_is_new:
                            roleU.data['Socials'] = p['channels']
                    person.func = func
                    person.update_data()
                    roleU.data['Current'] = True
                    roleU.data['Position'] = office_name
                    role, roleU, role_is_new, log = save_and_return(role, roleU, log)
                    # try:
                    xRoles = Role.objects.filter(Position=office_name, Country_obj=country, gov_level=gov_level).exclude(Person_obj=person)
                    previousRoleUs = Update.objects.filter(pointerId__startswith=get_model_prefix('Role'), pointerId__in=[i.id for i in xRoles], data__contains={'Current': True})
                    for u in previousRoleUs:
                        # data = json.loads(u.data)
                        u.data['Current'] = False
                        # u.data = json.dumps(data)
                        u.save()
                        log.updateShare(u)


                    prnt()
                    returnData[gov_level][office_name].append(role.id)
            prnt('-----')
        prnt()
        prnt()
        return returnData, log
    returnData = {}
    returnData, log = process_me('country', returnData, log)
    returnData, log = process_me('administrativeArea1', returnData, log)
    returnData, log = process_me('administrativeArea2', returnData, log)
    returnData, log = process_me('locality', returnData, log)
    prnt(context['unknown'])

    prnt('returnData:', returnData)

    for i in log:
        skip = False
        if i.object_type == 'Update':
            post = Post.objects.filter(pointerId=i.pointerId).first()
            if not post:
                if has_method(i, 'boot'):
                    i.get_pointer().boot()
                    post = Post.objects.filter(pointerId=i.pointerId).first()
                if not post:
                    skip = True
            if not skip and post.Update_obj != i:
                if post.Update_obj:
                    # post.Update_obj.delete()
                    post.Update_obj.log_deletion(data={'replaced_by':i.id})
                # this will need validation and update.sync_with_post
                post.Update_obj = i
                post.DateTime = i.DateTime
                post.save()

    if special:
        return return_test_result(log)
    elif super:
        super_share(log, gov, func)
    else:
        # send_for_validation(log, gov, func)
        return returnData, log


