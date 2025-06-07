
# from unittest.result import failfast
from django.db import models
from django.db.models import Q, Avg

import django_rq
from rq import Queue
from worker import conn

from accounts.models import *
from posts.models import *
from posts.views import get_ordinal
from posts.utils import sprenderize


import sys
import gc
import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pytz
import time
import datefinder
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



party_colours = {
    'provState' : {
        'Progressive Conservative Party of Ontario' : '#002395',
        'New Democratic Party of Ontario' : '#FF5800',
        'Ontario Liberal Party' : '#ED2E38',
        'Green Party of Ontario' : '#427730',

    }
}



def get_MPP(url):
    print('------get MPP')
    root = 'https://www.ola.org'
    url = root + url
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    person = None
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find('div', {'id':'content'})
    img = 'https://www.ola.org' + content.find('img')['src']
    # print(img)
    # try:
    #     region = soup.find('div', {'class':'region-sidebar-second'})
    #     map_link = 'https://www.ola.org' + region.find('img')['src']
    # except:
    #     map_link = None
    # print(map_link)
    containers = content.find_all('div', {'class':'views-element-container'})
    for container in containers:
        # print(container)
        # print('----')
        try:
            name = container.find('h2', {'class':'field-content'}).text
            # print(name)
            # last = name.split()[-1].strip()
            # first = name.replace(last, '').strip()
            hon = False
            if 'Hon' in name:
                hon = True
                name = name.replace('Hon. ', '')
            # region_name = name_region[a+len(' ('):a+b]

            # print(name.strip())
            # print(region_name)
            last = name.split()[-1].strip()
            first = name.replace(last, '').strip()
            # print(last)
            # print(first)
            name = name.strip()
            try:
                person = Person.objects.filter(gov_profile_page=url)[0]
                person.first_name = first
                person.last_name = last
                print(person)
            except Exception as e:
                # print(str(e))
                try:
                    person = Person.objects.filter(first_name=first, last_name=last)[0]
                    person.gov_profile_page=url
                except Exception as e:
                    print('creating person')
                    # print(str(e))
                    person = Person(first_name=first, last_name=last, gov_profile_page=url, province_name='Ontario')
                    # person.Region_obj = 
                    person.save()
                    person.create_post()
            if hon:
                person.honorific = 'Hon. '
            person.parliamentary_position = 'Member of Provincial Parliament'
            person.province_name ='Ontario'
            person.logo = img
            person.save()
        except Exception as e:
            pass
        try:
            p = container.find('p', {'class':'riding'})
            a = p.find('a')
            map_link = root + a['href']
            region_name = a.text.strip()
            # print(region_name)
            # print(map_link)
            try:
                district = District.objects.filter(name=region_name, province_name='Ontario')[0]
                # print(district)
            except:
                # print('creating district')
                district = District(name=region_name, province_name='Ontario', province=prov)
                search_name = region_name + ' ontario provincial electoral district'
                title = wikipedia.search(search_name)[0].replace(' ', '_')
                district.wikipedia = 'https://en.wikipedia.org/wiki/' + title
                district.save()
                district.create_post()
            district.map_link = map_link
            district.save()
            # print('save2')
            if 'Vacant' in name:
                try:
                    MPP = Role.objects.filter(position='MPP', person=person, district=district, parliament=parl)[0]
                    # print(MPP)
                except:
                    print('creating MPP')
                    MPP = Role(position='MPP', person=person, gov_page=url, district=district, parliament=parl)
                    # person.Region_obj = 
                    MPP.person_name = name
                MPP.current = True
                MPP.logo = img
                MPP.save()
            
            else:
                try:
                    MPP = Role.objects.filter(position='MPP', person=person, parliament=parl)[0]
                    # print(MPP)
                except:
                    print('creating MPP')
                    MPP = Role(position='MPP', person=person, gov_page=url, parliament=parl)
                    # person.Region_obj = 
                    MPP.person_name = name
                MPP.province_name = 'Ontario'
                MPP.district_name = region_name
                MPP.district = district
                MPP.current = True
                MPP.logo = img
                MPP.save()
                print('MPP saved')
        except Exception as e:
            pass
        try:
            row = container.find('div', {'class':'views-row'})
            coloursquare = row.find('div', {'class':'colour-square'})
            print(coloursquare.style) #required, causes exception if doesn't exist
            party_name = row.text.strip()
            # print(party_name)
            try:
                party = Party.objects.filter(name=party_name, province=prov, level='provincial')[0]
                # print(party)
            except:
                # print('creating party')
                party = Party(name=party_name, province=prov, province_name=prov.name, level='provincial')     
                search_name = party.name + ' ontario provincial party'
                link = wikipedia.search(search_name)[0].replace(' ', '_')
                party.wikipedia = 'https://en.wikipedia.org/wiki/' + link
                party.save()
                party.create_post()
            person.party = party
            person.party_name = party.name
            MPP.party = party
            MPP.party_name = party.name
            MPP.save()
            person.save()
        except Exception as e:
            pass
    container = soup.find('div', {'class':'mpptabscontent-region'})
    # print(container)
    # containers = extra.find_all('div', {'class':'views-element-container'})
    # for container in containers:
    div = container.find('div', {'class':'container-fluid'})
    cols = div.find_all('div', {'class':'col-md'})
    for col in cols:
        if 'email address' in col.text:
            try:
                # print('1aaaa')
                # print(div.text)
                # row = div.find('div', {'class':'row'})
                # for r in row:
                email = col.find('div', {'class':'block-views-blockmember-mpp-address'})
                a = email.find('a')
                # print(a.text)
                MPP.email = a.text.strip()
                MPP.save()
            except Exception as e:
                print(str(e))
        elif 'Constituency office' in col.text:
            try:
                # print('2aaaa', '\n')
                # div = container.find('div', {'class':'container-fluid'})
                office = col.find('div', {'class':'views-field-field-office-type'})
                # print(office.text)
                # print('1a1a1a1a1a1a1a1a1')
                addr = col.find('div', {'class':'views-field-nothing'})
                # addr = addr.replace('<br/>', '')
                # print(addr)
                addr = addr.text
                # print(addr)
                t = addr.find('Tel.:')
                f = addr.find('Fax:')
                # print('1111111')
                # print(addr[:t].replace('\n\n\n', ''))
                # print('--')
                address = addr[:t].strip()
                MPP.address = address
                # print('-------')
                tele = addr[t+len('Tel.: '):t+len('Tel.: ')+12].strip()
                MPP.telephone = tele
                fax = addr[f+len('Fax:'):f+len('Fax: ')+12].strip()
                MPP.fax = fax
                MPP.save()
            except Exception as e:
                print(str(e))
    return MPP


def get_current_MPPs():
    print('get current mpps')
    current_mpps = []
    root = 'https://www.ola.org'
    url = root + '/en/members/current'
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find('div', {'class':'view-content'})
    mlist = soup.find_all('div', {'class':'member-list-row'})
    # trs = tbody.find_all('tr')
    for tr in mlist:
        # print(tr)
        a = tr.find('h3').find('a')
        # print(root + a['href'])
        try:
            person = get_MPP(a['href'])
            current_mpps.append(person)
            # print(current_mpps)
            time.sleep(2)
        except Exception as e:
            print(str(e))
            time.sleep(10)
        # print('')
        # break
    print('len:', len(current_mpps))
    # print(current_mpps)
    if len(current_mpps) > 50:
        print('updating current')
        # print(current_mpps)
        mpps = Role.objects.filter(position='MPP', province_name='Ontario', current=True)
        for r in mpps:
            # print(p.person)
            if r in current_mpps:
                # print('current')
                pass
            else:
                r.current = False
                r.save()
                # print('not-current')
        # print('done')
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()


def get_MPP_old(url):
    print('------get MPP')
    if url:
        pass
    else:
        url = 'https://www.ola.org/en/members/all/dawn-gallagher-murphy'
    # url = 'https://www.ola.org/en/members/all/jess-dixon'
    url = 'https://www.ola.org' + url
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    person = None
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find('div', {'id':'content'})
    img = 'https://www.ola.org' + content.find('img')['src']
    try:
        region = soup.find('div', {'class':'region-sidebar-second'})
        map_link = 'https://www.ola.org' + region.find('img')['src']
    except:
        map_link = None
    containers = content.find_all('div', {'class':'views-element-container'})
    for container in containers:
        # print(container)
        # print('------------')
        try:
            h2 = container.find('h2')
            # print(h2)
            if not h2:
                name_region = container.find('h1').text
                print(name_region)
                a = name_region.rfind(' (')
                b = name_region[a:].find(')')
                name = name_region[:a]
                hon = False
                if 'Hon' in name:
                    hon = True
                    name = name.replace('Hon. ', '')
                region_name = name_region[a+len(' ('):a+b]
                print(name.strip())
                print(region_name)
                last = name.split()[-1].strip()
                first = name.replace(last, '').strip()
                try:
                    person = Person.objects.filter(gov_profile_page=url)[0]
                    person.first_name = first
                    person.last_name = last
                    print(person)
                except Exception as e:
                    # print(str(e))
                    try:
                        person = Person.objects.filter(first_name=first, last_name=last)[0]
                        person.gov_profile_page=url
                    except Exception as e:
                        print('creating person')
                        # print(str(e))
                        person = Person(first_name=first, last_name=last, gov_profile_page=url, province_name='Ontario')
                        # person.Region_obj = 
                        person.save()
                        person.create_post()
                if hon:
                    person.honorific = 'Hon. '
                person.parliamentary_position = 'Member of Provincial Parliament'
                person.province_name ='Ontario'
                person.logo = img
                person.save()
                # print('save1')
                try:
                    district = District.objects.filter(name=region_name, province_name='Ontario')[0]
                    # print(district)
                except:
                    # print('creating district')
                    district = District(name=region_name, province_name='Ontario', province=prov)
                    search_name = region_name + ' ontario provincial electoral district'
                    title = wikipedia.search(search_name)[0].replace(' ', '_')
                    district.wikipedia = 'https://en.wikipedia.org/wiki/' + title
                    district.save()
                    district.create_post()
                district.map_link = map_link
                district.save()
                # print('save2')
                try:
                    MPP = Role.objects.filter(position='MPP', person=person, parliament=parl)[0]
                    print(MPP)
                except:
                    print('creating MPP')
                    MPP = Role(position='MPP', person=person, gov_page=url, parliament=parl)
                    # r.Region_obj = 
                    MPP.province_name = 'Ontario'
                    MPP.person_name = name
                MPP.district_name = region_name
                MPP.district = district
                MPP.current = True
                MPP.logo = img
                MPP.save()
                print('MPP saved')
            div = container.find('div', {'class':'view-content'})
            rows = div.find_all('div', {'class':'views-row'})
            if 'parliamentary roles' in h2.text:
                # print('roles')
                for r in rows:
                    # print('roles')
                    # print(r.text.strip())
                    try:
                        role = Role.objects.filter(person=person, parliament=parl, position=r.text.strip())[0]
                    except:
                        role = Role(person=person, current=True, parliament=parl, position=r.text.strip())
                        role.save()
            elif 'party' in h2.text:
                # print('party!!!!')
                for r in rows:
                    # print(r.text.strip())
                    try:
                        party = Party.objects.filter(name=r.text.strip(), province=prov, level='provincial')[0]
                        # print(party)
                    except:
                        # print('creating party')
                        party = Party(name=r.text.strip(), province=prov, province_name=prov.name, level='provincial')     
                        search_name = party.name + ' ontario provincial party'
                        link = wikipedia.search(search_name)[0].replace(' ', '_')
                        party.wikipedia = 'https://en.wikipedia.org/wiki/' + link
                        party.save()
                        party.create_post()
                    person.party = party
                    person.party_name = party.name
                    MPP.party = party
                    MPP.party_name = party.name
                    MPP.save()
                    person.save()
                    # print('person party:',person.party)
            elif 'Contact' in h2.text:
                # print('contacgt')
                try:
                    node = container.find('div', {'class':'node__content'})
                    email = node.find('div', {'class':'field--name-field-email-address'})
                    # print('email:',email.text.strip())
                    MPP.email = email.text.strip()
                    MPP.save()
                except Exception as e:
                    # print(str(e))
                    pass
                try:
                    # print(node)
                    # print('')
                    contact = node.find('div', {'class':'field--name-field-contact'})
                    articles = contact.find_all('article')
                    for a in articles:
                        if 'Constituency office' in a.text:
                            # print(a)
                            div = a.find('div', {'class':'node__content'})
                            divs = div.find_all('div', {'class':'field'})
                            # print('con')
                            info = ''
                            for d in divs:
                                # print(d['class'])
                                toll_free = ''
                                if 'field--name-field-number' in d['class']:
                                    # print('tele')
                                    # print(d.text.replace('Tel.', '').strip())
                                    MPP.telephone = d.text.replace('Tel.', '').strip()
                                elif 'field--name-field-fax-number' in d['class']:
                                    # print('faxx')
                                    # print(d.text.replace('Fax', '').strip())
                                    MPP.fax = d.text.replace('Fax', '').strip()
                                elif 'field--name-field-toll-free-number' in d['class']:
                                    # print('toll free')
                                    toll_free = d.text.strip()
                                else:
                                    if d.text == 'ON':
                                        info = info + ' ' + d.text + ' '
                                    elif 'Toll' in d.text:
                                        pass
                                    elif '@' in d.text:
                                        pass
                                    else:
                                        info = info + d.text
                            # print(info)
                            if info:
                                MPP.address = info.replace(MPP.email, '').replace(toll_free, '')
                                MPP.save()
                        # print('')

                except Exception as e:
                    # print(str(e))
                    pass
            # else:
            #     print('other')
            #     print(h2.text)
                # for r in rows:
                #     print(r.text)
        except Exception as e:
            print(str(e))
            pass
    print('done')
    return MPP
            # try:
            #     # print(c)
            #     node = container.find('div', {'class':'node__content'})
            #     email = node.find('div', {'class':'field--name-field-email-address'})
            #     print(email.text)
            #     contact = node.find('div', {'class':'field--name-field-contact'})
            #     articles = contact.find_all('article')
            #     for a in articles:
            #         div = a.find('div', {'class':'view-content'})
            #         divs = div.find_all('div')
            #         for d in divs:
            #             print(d.text)
            #     print('d')
            # except Exception as e:
            #     print(str(e))
        # try:
        #     MPP.save()
        #     person.save()
        #     # print('saved')
        # except Exception as e:
        #     print(str(e))
        # print('---------------')
        # print('')
        
def get_current_MPPs_old():
    current_mpps = []
    url = 'https://www.ola.org/en/members/current'
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    tbody = soup.find('tbody')
    trs = tbody.find_all('tr')
    for tr in trs:
        td = tr.find_all('td')
        a = td[0].find('a')
        # print(a['href'])
        # print(a.text)
        # print(td[1].text)
        # print(td[2].text)
        try:
            person = get_MPP(a['href'])
            current_mpps.append(person)
            # print(current_mpps)
            time.sleep(2)
        except Exception as e:
            print(str(e))
            time.sleep(10)
        print('')
    # print('len:', len(current_mpps))
    # print(current_mpps)
    if len(current_mpps) > 50:
        print('updating current')
        # print(current_mpps)
        mpps = Role.objects.filter(position='MPP', province_name='Ontario', current=True)
        for r in mpps:
            # print(p.person)
            if r in current_mpps:
                # print('current')
                pass
            else:
                r.current = False
                r.save()
                # print('not-current')
        # print('done')

def get_bill(bill, new_bill):
    # try:
    #     bill = Bill.objects.filter(legis_link=url)
    # except:
    #     bill = Bill(legis_link=url)

    r = requests.get(bill.legis_link)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    sponsors = soup.find_all('div', {'class':'views-field-field-member'})
    for s in sponsors:
        m = s.find('a')
        print(m['href'])
        u = m['href'].replace('(','').replace(')','')
        url = 'https://www.ola.org/en' + m['href']
        try:
            sponsor = Person.objects.filter(gov_profile_page__icontains=u)[0]
            # print(sponsor)
            if not bill.person:
                bill.person = sponsor
                bill.SponsorPersonOfficialFirstName = sponsor.first_name
                bill.SponsorPersonOfficialLastName = sponsor.last_name
                bill.SponsorPersonName = sponsor.first_last()
                bill.SponsorPersonShortHonorific = sponsor.honorific
                bill.SponsorAffiliationTitle = 'MPP'
                bill.SponsorAffiliationRoleName = 'MPP'
                bill.SponsorConstituencyName = sponsor.constituency_name
            else:
                if sponsor not in bill.co_sponsors.all() and sponsor != bill.person:
                    bill.co_sponsors.add(sponsor)
            # print('done sponsor')
        except Exception as e:
            print(str(e))
            pass
        
    # print('----')
    status = soup.find('p', {'class':'views-field-field-current-status-1'})
    # print(status.text.replace('Current status:', '').strip())
    try:
        updatedStatus = False
        if status.text.replace('Current status:', '').strip() != bill.StatusNameEn:
            updatedStatus = True
        bill.LatestCompletedMajorStageNameWithChamberSuffix = status.text.replace('Current status:', '').strip()
        bill.StatusNameEn = status.text.replace('Current status:', '').strip()
    except Exception as e:
        print(str(e))
    try:
        div = soup.find('div', {'class':'WordSection1'})
        # print(div.text)
        sums = []
        summary = ''
        # print('----')
        children = div.find_all(recursive=False)
        if 'EXPLANATORY' in div.text and 'NOTE' in div.text:
            # sections = div.find_all('p', {'class':'section'})
            for child in children:
                # print(child['class'])
                if 'section' not in child['class'] and 'schedule' not in child['class'] and 'partnum' not in child['class'] and 'paragraph' not in child['class']:
                    break
                if 'schedule' in child['class']:
                    sums.append(child)
                else:
                    sums.append(child)
                    # print(child.text)
                    summary = summary + str(child)
            # for s in sections:
            #     sums.append(s)
            #     print(s.text)
            # e = div.find('p', {'class':'schedule'})
            # sums.append(e)
        bill.summary = summary
        # print('____---- ')
        text = ''
        for child in children:
            if child not in sums:
                text = text + str(child) + '\n'
        # print(text)
        
        # print('---')
        final = text
        toc_d = {}
        for match in re.finditer('<p class="headnote"', str(final)):
            q = str(final)[match.end():].find('>')
            # print(text[match.end():match.end()+q])
            w = str(final)[match.end():match.end()+q]
            e = str(final)[match.end()+q:].find('</p>')+len('</p>')
            r = str(final)[match.end()+q+1:match.end()+q+e]
            html = str(final)[match.start():match.end()+q+e]
            string =  re.sub('<[^<]+?>', '', r)
            toc_d[string] = html

        if bill.ReceivedRoyalAssent == 'true' and bill.bill_text_version != 'Royal':
            bill.bill_text_html = text
            bill.bill_text_nav = json.dumps(dict(toc_d))
            bill.bill_text_version = 'Royal'
        if bill.PassedFirstChamberThirdReading == 'true' and bill.bill_text_version != 'Third':
            bill.bill_text_html = text
            bill.bill_text_nav = json.dumps(dict(toc_d))
            bill.bill_text_version = 'Third'
        elif bill.PassedFirstChamberSecondReading == 'true' and bill.bill_text_version != 'Second':
            bill.bill_text_html = text
            bill.bill_text_nav = json.dumps(dict(toc_d))
            bill.bill_text_version = 'Second'
        elif bill.PassedFirstChamberFirstReading == 'true' and bill.bill_text_version != 'First':
            bill.bill_text_html = text
            bill.bill_text_nav = json.dumps(dict(toc_d))
            bill.bill_text_version = 'First'
        # bill.save()
    except Exception as e:
        print(str(e))
    
    prov = Province.objects.filter(name='Ontario')[0]
    if new_bill and bill.person:
        # print('send alerts')
        n = Notification(province=prov, title='%s %s has sponsored bill %s' %(bill.person.first_name, bill.person.last_name, bill.NumberCode), link=bill.get_absolute_url())
        n.save()
        for u in User.objects.filter(follow_person=bill.person):
            u.alert('%s %s has sponsored bill %s' %(bill.person.first_name, bill.person.last_name, bill.NumberCode), str(bill.get_absolute_url()), bill.ShortTitle)
    if new_bill:
        bill.getSpren(False)
    if updatedStatus:
        if 'Royal Assent' not in bill.StatusNameEn:
            for u in User.objects.filter(follow_bill=bill):
                title = 'Bill %s updated' %(bill.NumberCode)
                u.alert(title, str(bill.get_absolute_url()), bill.ShortTitle + '\n' + bill.StatusNameEn)
        elif 'Royal Assent' in bill.StatusNameEn:
            n = Notification(province=prov, title='Bill %s has reached Royal Assent - %s' %(bill.NumberCode, bill.ShortTitle), link=str(bill.get_absolute_url()))
            n.save()
            for u in User.objects.filter(province=prov):
                title = 'Bill %s has reached Royal Assent' %(bill.NumberCode)
                u.alert(title, bill.get_absolute_url(), bill.ShortTitle)

    #     for u in User.objects.filter(follow_bill=bill):
    #         title = 'Bill %s updated' %(bill.NumberCode)
    #         u.alert(title, str(bill.get_absolute_url()), bill.ShortTitle + '\n' + bill.StatusNameEn)
    # if bill.ReceivedRoyalAssent == 'true':
    #     if not bill.royal_assent_html:
    #         try:
    #             bill.royal_assent_html = text
    #             bill.royal_assent_nav = json.dumps(dict(toc_d))
    #             n = Notification(title='Bill %s has reached Royal Assent' %(bill.NumberCode), link=str(bill.get_absolute_url()))
    #             n.save()
    #             #already alerted users following bill
    #             prov = Province.objects.filter(name='Ontario')[0]
    #             for u in User.objects.filter(province=prov).exclude(follow_bill=bill):
    #                 title = 'Bill %s has reached Royal Assent' %(bill.NumberCode)
    #                 u.alert(title, str(bill.get_absolute_url()), bill.ShortTitle)
    #         except Exception as e:
    #             print(str(e))
    #             u = User.objects.filter(username='Sozed')[0]
    #             title = 'royal alert fail %s' %(bill.NumberCode)
    #             u.alert(title, str(bill.get_absolute_url()), str(e))
    return bill
    # print(toc_d)




def get_current_bills():
    # print('get ontario bills')
    prov = Province.objects.filter(name='Ontario')[0]
    # parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    url = 'https://www.ola.org/en/legislative-business/bills/current'
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    div = soup.find('div', {'class':'node__content'})
    # print(div.text)
    # 'The 43rd Parliament, 1st Session began on August 8, 2022.'
    t = div.text
    a = t.find(' Parliament, ')
    parl = t[:a].replace('The ', '').replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
    b = t.find(' Session ')
    sess = t[a+len(' Parliament, '):b].replace('The ', '').replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
    # print(parl, sess)
    try:
        c = t.find('began')
        began = t[c:].strip()
        # print(began)
        d = began.rfind(',')
        e = began[d-2:d]
        if e[0] == ' ':
            e = '0' + e[1]
            began = began[:d-1] + e + began[d:]
        dt = datetime.datetime.strptime(began, 'began on %B %d, %Y.')
        print(dt)
    except Exception as e:
        print(str(e))
        dt = datetime.datetime.now()
    try:
        parl = Parliament.objects.filter(country='Canada', organization='Ontario', ParliamentNumber=parl, SessionNumber=sess)[0]
    except:
        parl = Parliament(country='Canada', organization='Ontario', ParliamentNumber=parl, SessionNumber=sess, start_date=dt)
        parl.save()
        parl.end_previous('Canada', 'Ontario')
    content = soup.find('div', {'class':'view-content'})
    rows = content.find_all('div', {'class':'views-row'})
    num = 0
    for row in rows:
        if num >= 0:
            num += 1
            # print(num)
            title = row.find('div', {'class':'views-field-field-frontend-title'})
            # print(title)
            a = title.find('a')['href']
            # print(a)
            billTitle = title.text.replace('Bill ', '')
            print(billTitle)
            x = billTitle.find(', ')
            y = billTitle[x+2:].find(',')
            numberCode = billTitle[:x]
            numberCode = numberCode.strip()
            billTitle = billTitle[x+2:]
            url = 'https://www.ola.org' + a
            try: 
                bill = Bill.objects.filter(legis_link=url)[0]
                new_bill = False
                # bill.ShortTitle=billTitle
                # bill.NumberCode=numberCode
                # bill.has_senate = False
                bill.OriginatingChamberName='%s-Assembly'%(prov.name)
            except:
                bill = Bill(legis_link=url, NumberCode=numberCode, ShortTitle=billTitle, parliament=parl, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber, province=prov, OriginatingChamberName='%s-Assembly'%(prov.name), IsHouseBill='true', has_senate = False)  
                bill.save()
                bill.create_post()
                new_bill = True
                versions = ['First Reading','Second Reading','Third Reading','Royal Assent']
                for version in versions:
                    try:
                        v = BillVersion.objects.filter(bill=bill, version=version)[0]
                    except:
                        v = BillVersion(bill=bill, version=version, code=bill.NumberCode, province=prov)
                        if version == 'First Reading':
                            v.current = True
                            v.empty = False
                        v.save()
                        v.create_post()
                
                print('bill created')
            # sponsors = row.find('div', {'class':'views-field-field-sponsor'})
            # lis = sponsors.find_all('li')
            # for li in lis:
            #     print(li.text.strip())
            def currentize_version(bill, version, dt):
                # print('currentize: ', version)
                versions = BillVersion.objects.filter(bill=bill)
                for v in versions:
                    if v.version == version:
                        v.current = True
                        v.empty = False
                        v.dateTime = dt
                    else:
                        v.current = False
                    v.save()
                try:
                    v = BillVersion.objects.filter(bill=bill, version=version)[0]
                except:
                    v = BillVersion(bill=bill, version=version, code=bill.NumberCode, province=prov)
                    v.save()
                    v.create_post()
                v.current = True
                v.empty = False
                v.dateTime = dt
                v.save()
            table = row.find('div', {'class':'views-field-field-status-table'})
            # print(table)
            trs = table.find_all('tr')
            first = True
            latest = None
            # print(len(trs))
            # n = 0
            for tr in reversed(trs[1:]):
                # if first:
                #     first = False
                # else:
                # print('----------------___')
                # print(tr)
                # n += 1
                # print(n)
                tds = tr.find_all('td')
                # print(len(tds))
                for td in reversed(tds):
                    try:
                        'March 7, 2023'
                        dt = datetime.datetime.strptime(td.text + ' 12', '%B %d, %Y %H')
                        # print(dt)
                        # if not latest:
                        latest = dt
                    except Exception as e:
                        # print(str(e))
                        # print(td.text)
                        pass
                if tds and tr == trs[1] or new_bill:
                    if 'First Reading' in tds[1].text:
                        bill.PassedFirstChamberFirstReadingDateTime = dt
                        bill.PassedFirstChamberFirstReading = 'true'
                        bill.LatestCompletedBillStageDateTime = dt
                        # bill.started = dt
                        currentize_version(bill, 'First Reading', dt)
                    if 'Second Reading' in tds[1].text:
                        bill.PassedFirstChamberSecondReadingDateTime = dt
                        bill.PassedFirstChamberSecondReading = 'true'
                        bill.LatestCompletedBillStageDateTime = dt
                        currentize_version(bill, 'Second Reading', dt)
                    if 'Third Reading' in tds[1].text:
                        bill.PassedFirstChamberThirdReadingDateTime = dt
                        bill.PassedFirstChamberThirdReading = 'true'
                        bill.LatestCompletedBillStageDateTime = dt
                        currentize_version(bill, 'Third Reading', dt)
                    if 'Royal Assent' in tds[1].text:
                        bill.ReceivedRoyalAssentDateTime = dt
                        bill.ReceivedRoyalAssent = 'true'
                        bill.LatestCompletedBillStageDateTime = dt
                        currentize_version(bill, 'Royal Assent', dt)
            bill.LatestBillEventDateTime = latest
            # print('latest: ', latest)
            if latest > (datetime.datetime.now() - datetime.timedelta(days=1)) or new_bill:
                time.sleep(2)       
                bill = get_bill(bill, new_bill)
                bill.save()
                bill.update_post_time()
            else:
                bill.save()
            print('-----------------')
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()

def get_weekly_agenda():
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    url = 'https://www.ola.org/en/legislative-business/video'
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', {'class':'table'})
    trs = table.find_all('tr')
    times = []
    first_line = True
    def next_weekday(d, weekday):
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0: # Target day already happened this week
            days_ahead += 7
        return d + datetime.timedelta(days_ahead)
    def convert_to_num(day):
        if day == 'Monday':
            return 0
        elif day == 'Tuesday':
            return 1
        elif day == 'Wednesday':
            return 2
        elif day == 'Thursday':
            return 3
        elif day == 'Friday':
            return 4
        elif day == 'Saturday':
            return 5
        elif day == 'Sunday':
            return 6
    for tr in trs:
        print('----------')
        position = 0
        n = 0
        ths = tr.find_all('th')
        for th in ths:
            print(th.text)
            if first_line:
                if n > 0:
                    '9 a.m.'
                    '10:15 a.m.'
                    try:
                        dt = datetime.datetime.strptime(th.text.replace('.',''), '%I %p')
                    except:
                        dt = datetime.datetime.strptime(th.text.replace('.',''), '%I:%M %p')
                    times.append(dt)
            else:
                # position += 1
                dayNum = convert_to_num(th.text)
                nextDate = next_weekday(datetime.datetime.now().replace(hour=9, minute=00, second=00, microsecond=00), dayNum)
                # print(nextDate)
                # Agenda()
                try:
                    A = Agenda.objects.filter(province=prov, organization='Ontario-Assembly', date_time__gte=nextDate, date_time__lt=nextDate + datetime.timedelta(days=1))[0]
                except:
                    A = Agenda(province=prov, organization='Ontario-Assembly', gov_level='Assembly', date_time=nextDate)
                    A.save()
                    A.create_post()
                    try:
                        H = Hansard.objects.filter(agenda=A)[0]
                    except:
                        H = Hansard(agenda=A, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber, Publication_date_time=nextDate, Organization='Ontario-Assembly')
                        H.save()
                        H.create_post() 
            n += 1
        n = 0
        tds = tr.find_all('td')
        for td in tds:
            # AgendaTime()
            newdatetime = nextDate.replace(hour=times[n].hour, minute=times[n].minute, second=00, microsecond=00)
            try:
                agendaTime = AgendaTime.objects.filter(agenda=A, date_time=newdatetime, gov_level=A.gov_level, organization=A.organization)[0]
                print('agedatime found')
            except Exception as e:
                print(str(e))
                agendaTime = AgendaTime(agenda=A, date_time=newdatetime, gov_level=A.gov_level, organization=A.organization)
                agendaTime.save()
                print('agendatime created')
            try:
                agendaItem = AgendaItem.objects.filter(agenda=A, agendaTime=agendaTime, date_time=newdatetime, gov_level=A.gov_level, organization=A.organization)[0]
                print('i found')
            except Exception as e:
                print(str(e))
                agendaItem = AgendaItem(agenda=A, agendaTime=agendaTime, date_time=newdatetime, position=position, gov_level=A.gov_level, organization=A.organization)
                agendaItem.save()
                print('i created')
            try:
                position += 1
                p = td.find('p')        
                if p:
                    text = list(p.stripped_strings)
                    for t in text:
                        # AgendaItem
                        title = t.replace(' \xa0','').replace('\xa0','').replace('•', '')
                        print(newdatetime, t.replace(' \xa0','').replace('\xa0','').replace('•', ''))
                        try:
                            agendaItem = AgendaItem.objects.filter(agenda=A, agendaTime=agendaTime, text=title)[0]
                            print('it found')
                        except:
                            agendaItem = AgendaItem(agenda=A, agendaTime=agendaTime, position=position, text=title)
                            agendaItem.save()
                            print('it craeted')
                else:
                    # AgendaItem
                    print(newdatetime, td.text)
                    try:
                        agendaItem = AgendaItem.objects.filter(agenda=A, agendaTime=agendaTime, text=td.text)[0]
                        print('item found')
                    except:
                        agendaItem = AgendaItem(agenda=A, agendaTime=agendaTime, position=position, text=td.text)
                        agendaItem.save()
                        print('item created')
            except Exception as e:
                print(str(e))
                pass
            try:
                if td['colspan'] and td['colspan'] == '2':
                    n += 1
            except Exception as e:
                pass
            n += 1
        first_line = False
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()


def get_hansard(url):
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    if not url:
        url = 'https://www.ola.org/en/legislative-business/house-documents/parliament-%s/session-%s/%s/hansard' %(parl.ParliamentNumber, parl.SessionNumber, datetime.datetime.now().strftime('%Y-%m-%d'))
        # url = 'https://www.ola.org/en/legislative-business/house-documents/parliament-43/session-1/2023-05-30/hansard'
    print(url)
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    transcript = soup.find('div',{'id':'transcript'})
    paras = transcript.find_all('p')
    print(len(paras))
    new = False
    a = url.find('session-')+len('session-1/')
    b = url[a:].find('/')
    dt = url[a:a+b]
    for p in paras:
        # print(p)
        if 'The House met at' in p.text:
            print(p.text)
            st = p.text.replace('The House met at ','')
            # print(st)
            # print(url[a:a+b] + '-' + st)
            date_time = datetime.datetime.strptime(dt + '-' + st, '%Y-%m-%d-%H%M.')
            print(date_time)
            date = date_time.replace(hour=0, minute=00, second=00, microsecond=00)
            try:
                A = Agenda.objects.filter(date_time__gte=date, date_time__lt=date + datetime.timedelta(days=1), organization='Ontario-Assembly')[0]
            except:
                A = Agenda(date_time=date_time, gov_level='Assembly', organization='Ontario-Assembly')
                A.province = prov
                A.save()
                A.create_post()
                new = True
            # A.save()
            try:
                H = Hansard.objects.filter(agenda=A)[0]
            except:
                H = Hansard(agenda=A, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber, Publication_date_time=date_time, Organization='Ontario-Assembly')
                H.province = prov
                H.gov_page = url
                H.save()
                # H.create_post()
            # H.save()
            print(H.has_transcript)
            if not H.has_transcript:
                for i in AgendaTime.objects.filter(agenda=A):
                    i.delete()
                for i in AgendaItem.objects.filter(agenda=A):
                    i.delete()
                for i in HansardItem.objects.filter(hansard=H):
                    i.delete()
            try:
                h = HansardItem.objects.filter(hansard=H)[0]
                print('Items found')
            except:
                new = True 
        if p.has_attr('class') and p['class'][0] == 'speakerStart':
            print(p.text)
            print('break')
            break

    if new:
        # print(transcript)
        children = transcript.findChildren(recursive=False)
        print(children)
        H_terms = {}
        H_people = {}
        h = None
        text = ''
        speaker = ''
        title = ''
        subtitle = ''
        num = 0
        for child in children:
            num += 1
            if child.has_attr('id') and child['id'][0] == 'toc':
                print('toc')
            elif child.has_attr('class') and child['class'][0] == 'timeStamp':
                # date_time = child.text
                date_time = datetime.datetime.strptime(dt + '-' + child.text, '%Y-%m-%d-%H%M')
                print(date_time)
            elif child.has_attr('class') and child['class'][0] == 'speakerStart':
                # # print(child)
                # print(title)
                # print(subtitle)
                # print(speaker)
                # print(text, '\n-------------------')
                # print()
                try:
                    string =  re.sub('<[^<]+?>', '', h.Content)
                    words = re.findall(r'\w+', string)
                    h.wordCount = len(words)
                    h.save()
                except:
                    pass
                strong = child.find('strong')
                # print(strong)
                speaker = strong.text
                text = str(child).replace(str(strong), '')
                if speaker == 'Interjection:':
                    h.Content = h.Content + str(child) + '\n'
                else:
                    # pass
                    try:
                        a = speaker.find('(')
                        b = speaker[a+1:].rfind(')')
                        name = speaker[a+1:a+1+b]
                    except:
                        name = speaker
                    person_name = name.replace('Mme ','').replace('Miss ','').replace('Ms. ','').replace('Mrs. ','').replace('Mr. ','').replace('MPP ','').replace(':','').replace('Hon. ','')
                    names = person_name.split()
                    try:
                        r = Role.objects.filter(position='MPP', province_name=prov.name).filter(Q(person__full_name__icontains=person_name)|Q(person__first_name__icontains=names[0], person__last_name__icontains=names[-1]))[0]
                        person = r.person
                    except:
                        try:
                            person = Person.objects.filter(province_name=prov.name).filter(Q(full_name__icontains=person_name)|Q(first_name__icontains=names[0], last_name__icontains=names[-1]))[0]
                        except:
                            person = None
                    try:
                        h = HansardItem.objects.filter(hansard=H, Item_date_time=date_time, person=person)[0]
                    except:
                        h = HansardItem(hansard=H, Item_date_time=date_time, person=person)
                        h.person_name = speaker.replace(':','')
                        h.OrderOfBusiness = title
                        h.Content = text
                        h.Terms = []
                        h.save()
                        if title:
                            h.add_term(title, None)
                        if subtitle:
                            if 'Act' in subtitle:
                                try:
                                    print(subtitle)
                                    if ' / ' in subtitle:
                                        a = subtitle.find(' / ')
                                        subtitle = subtitle[:a]
                                    bill = Bill.objects.filter(Q(LongTitleEn__icontains=subtitle)|Q(ShortTitle__icontains=subtitle)).filter(ParliamentNumber=H.ParliamentNumber, SessionNumber=H.SessionNumber).filter(OriginatingChamberName='Ontario-Assembly')[0]
                                    print(bill)
                                    if date_time:
                                        try:
                                            agendaTime = AgendaTime.objects.filter(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)[0]
                                            input_time = False
                                        except:
                                            agendaTime = AgendaTime(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)
                                            input_time = True
                                            agendaTime.save()
                                        # print(agendaTime)
                                    else:
                                        agendaTime = None
                                    try:
                                        agendaItem = AgendaItem.objects.filter(agenda=A, text=subtitle)[0]
                                    except Exception as e:
                                        # print(str(e))
                                        agendaItem = AgendaItem(agenda=A, position=num, agendaTime=agendaTime, gov_level=A.gov_level, organization=A.organization)
                                        agendaItem.text = subtitle
                                        if input_time:
                                            agendaItem.date_time = date_time
                                    agendaItem.bill = bill
                                    agendaItem.save()
                                    print(agendaItem)
                                    agendaItem.agenda.bills.add(bill)
                                    agendaItem.agenda.save()
                                    h.bill = bill
                                    h.add_term(subtitle, bill)
                                    # sozed.alert('%s-STEP TWO' %(bill.NumberCode), None)
                                    try:
                                        bill.LatestBillEventDateTime = date_time
                                        # print(bill.LatestBillEventDateTime)
                                        bill.save()
                                        bill.update_post_time()
                                    except Exception as e:
                                        print('FailGetBIll-%s' %(str(e)))
                                except Exception as e:
                                    print(str(e))
                                    print('Bill not found')
                                    h.add_term(subtitle, None)
                            else:
                                h.add_term(subtitle, None)
                        h.save()
                        h.create_post()
                        try:
                            if not person.id in H_people:
                                H_people[person.id] = 1
                            else:
                                H_people[person.id] += 1
                        except:
                            pass
                        try:
                            if subtitle and not subtitle in H_terms:
                                H_terms[subtitle] = 1
                            else:
                                H_terms[subtitle] += 1
                        except:
                            pass
                        try:
                            if title and not title in H_terms:
                                H_terms[title] = 1
                            else:
                                H_terms[title] += 1
                        except:
                            pass
            elif child.name == 'h2':
                title = child.text.strip()
                try:
                    agendaTime = AgendaTime.objects.filter(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)[0]
                    input_time = False
                except Exception as e:
                    # print(str(e))
                    agendaTime = AgendaTime(agenda=A, date_time=date_time, gov_level=A.gov_level, organization=A.organization)
                    agendaTime.save()
                    input_time = True
                try:
                    agendaItem = AgendaItem.objects.filter(agenda=A, agendaTime=agendaTime, text=title)[0]
                except Exception as e:
                    # print(str(e))
                    agendaItem = AgendaItem(agenda=A, position=num, agendaTime=agendaTime, gov_level=A.gov_level, organization=A.organization)
                    agendaItem.text = title
                    if input_time:
                        agendaItem.date_time = date_time
                    agendaItem.save()
            elif child.name == 'h3':
                subtitle = child.text.strip()
                # if not subtitle in H_terms:
                #     H_terms[subtitle] = 1
                # else:
                #     H_terms[subtitle] += 1
            elif child.name == 'p':
                if h:
                    h.Content = h.Content + str(child) + '\n'
        h.save()
        H.has_transcript = True
        H.apply_terms(H_terms)
        # try:
        # d = json.loads(H.TermsText)
        # for t in list(d.items()):
        #     topic_link = '%s?topic=%s' %(H.get_absolute_url(), t)
        #     followers = User.objects.filter(follow_topic__contains=t, province=prov)
        #     for f in followers:
        #         try:
        #             n = Notification.objects.filter(user=f, link=topic_link)[0]
        #         except:
        #             f.alert('%s was discussed in the Ontario Assembly' %(t), topic_link, '%s the %s' %(H.Publication_date_time.strftime('%A'), get_ordinal(int(H.Publication_date_time.strftime('%d')))))
        # except Exception as e:
        #     print(str(e))
        H_people = sorted(H_people.items(), key=operator.itemgetter(1),reverse=True)
        # for p in H.people.all():
        #     users = User.objects.filter(follow_person=p)
        #     for u in users:
        #         u.alert('%s %s spoke in Parliament' %(p.first_name, p.last_name), '%s?speaker=%s' %(H.get_absolute_url(), p.id), '%s the %s%s' %(H.Publication_date_time.strftime('%A'), H.Publication_date_time.strftime('%d'), get_ordinal(int(H.Publication_date_time.strftime('%d')))))
        H_people = dict(H_people)
        H.peopleText = json.dumps(H_people)
        H.completed_model = True
        H.save()
        H.create_post()
        # sprenderize(H)
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()
        
        


def get_motions(url):
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    if url:
        pass
    else:
        # 'https://www.ola.org/en/legislative-business/house-documents/parliament-43/session-1/2023-4-5/votes-proceedings'
        # 'https://www.ola.org/en/legislative-business/house-documents/parliament-43/session-1/2023-04-05/votes-proceedings'
        # 'https://www.ola.org/en/legislative-business/house-documents/parliament-43/session-1/2023-04-05/hansard'
        url = 'https://www.ola.org/en/legislative-business/house-documents/parliament-%s/session-%s/%s/votes-proceedings' %(parl.ParliamentNumber, parl.SessionNumber, datetime.datetime.now().strftime('%Y-%m-%d'))
    print(url)
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    day = soup.find('time', {'class':'datetime'})['datetime']
    a = day.find('T')
    dt = datetime.datetime.strptime(day[:a], '%Y-%m-%d')
    content = soup.find('div', {'class':'votesProceedingsDoc'})
    tables = content.find_all('table')
    get_vote_text = False
    get_next_text = False
    get_votes = False
    for table in tables:
        bill = None
        try:
            timestamp = table.find('h2', {'class':'boldtext'}).text
            day = datetime.datetime.strptime(str(datetime.datetime.strftime(dt, '%Y-%m-%d')) + '//' + str(timestamp.replace('.','')), '%Y-%m-%d//%I:%M %p')
        except Exception as e:
            day = datetime.datetime.strptime(str(datetime.datetime.strftime(dt, '%Y-%m-%d')) + '//9:00 am', '%Y-%m-%d//%I:%M %p')
            pass
        if get_next_text:
            # print('get next text')
            tbody = table.find('tbody')
            try:
                motion = Motion.objects.filter(motion_text=tbody.text, parliament=parl, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
            except:
                motion = Motion(date_time=day, motion_text=tbody.text, parliament=parl, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber, OriginatingChamberName='Ontario-Assembly', province=prov)
                # motion.save()
                # motion.create_post()
            if person:
                motion.sponsor = person.person
            # motion.vote_number = motion.id
            motion.gov_url = url
            # motion.save()
            get_votes = True
            get_next_text = False
        try:
            h4 = table.find('h4').text
            if 'Deferred Votes' in h4:
                get_vote_text = True
            else:
                get_vote_text = False
        except:
            pass
        if get_vote_text:
            # print('get vote text')
            try:
                p = table.find('p')
                if ' moved' in p.text:
                    try:
                        a = p.text.find(' moved')
                        name = p.text[:a].replace('Hon. ', '')
                        person = Role.objects.filter(position='MPP', current=True, province=prov, person__full_name__icontains=name)[0]
                    except:
                        person = None
                    get_vote_text = False
                    get_next_text = True
            except Exception as e:
                print(str(e))
            try:
                strong = p.find('strong')
                # print('strong:', strong)
                if strong:
                    # print(p.text)
                    b = strong.text.replace('Bill ', '')
                    try:
                        bill = Bill.objects.filter(NumberCode=b, province=prov, parliament=parl)[0]
                        print(bill)
                    except:
                        bill = None
                    try:
                        motion = Motion.objects.filter(motion_text=p.text, parliament=parl, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)[0]
                    except:
                        motion = Motion(date_time=day, motion_text=p.text, parliament=parl, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber, OriginatingChamberName='Ontario-Assembly', province=prov)
                        if bill:
                            motion.bill = bill
                            motion.billCode = bill.NumberCode
                        # motion.save()
                        # motion.vote_number = motion.id
                        # motion.save()
                        # motion.create_post()
                    # print(motion)
                    get_vote_text = False
                    get_votes = True
            except Exception as e:
                print(str(e))
        if get_votes:
            def cast_vote(v, text, motion):
                # print('cast vote', v, text)
                r = None
                if '(' in text:
                    a = text.find('(')+1
                    b = text.find(')')
                    district = text[a:b]
                    lastName = text[:a-2]
                    # print(district)
                    # print(lastName)
                    try:
                        r = Role.objects.filter(person__last_name=lastName, district_name=district, position='MPP', current=True)[0]
                    except Exception as e:
                        try:
                            r = Role.objects.filter(person__full_name__icontains=lastName, position='MPP', current=True)[0]
                        except Exception as e:
                            # pass
                            print(lastName)
                            print('r not found1', str(e))
                elif text:
                    lastName = text
                    try:
                        r = Role.objects.filter(person__last_name=lastName, position='MPP', current=True)[0]
                    except Exception as e:
                        try:
                            r = Role.objects.filter(person__full_name__icontains=lastName, position='MPP', current=True)[0]
                        except Exception as e:
                            # pass
                            print(lastName)
                            print('r not found2', str(e))
                if lastName:
                    try:
                        if r:
                            # print(r.district_name)
                            vote = Vote.objects.filter(person=r.person, motion=motion)[0]
                        else:
                            vote = Vote.objects.filter(PersonOfficialLastName=lastName, motion=motion, VoteValueName=v)[0]
                    except:
                        vote = Vote(motion=motion, DecisionEventDateTime=day, VoteValueName=v, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber)
                        if r:
                            vote.person = r.person
                            vote.PersonOfficialFirstName = r.person.first_name
                            vote.PersonOfficialLastName = r.person.last_name
                            vote.PersonOfficialFullName = r.person.full_name
                            vote.ConstituencyName = r.district_name
                        else:
                            vote.PersonOfficialLastName = lastName
                        # print('vote:', v)
                        if v == 'Yea':
                            vote.IsVoteYea='true', 
                            motion.yeas += 1
                        elif v == 'Nay':
                            vote.IsVoteNay='true', 
                            motion.nays += 1
                        motion.total_votes += 1
                        vote.save()
                        vote.create_post()
                    if vote.person and motion.bill:
                        try:
                            post = Post.objects.filter(bill=motion.bill)[0]
                            try:
                                reaction = Reaction.objects.filter(post=post, person=vote.person)[0]
                                reaction.calculate_vote(v, True)
                            except:
                                reaction = Reaction(post=post, person=vote.person)
                                reaction.save()
                                reaction.calculate_vote(v, False)
                        except Exception as e:
                            print(str(e))
                return motion
            h5 = table.find_all('h5')
            save_motion = True
            finish_motion = False
            for h in h5:
                if save_motion:
                    motion.save()
                    motion.vote_number = motion.id
                    motion.create_post()
                    save_motion = False
                    finish_motion = True
                if 'Ayes' in h.text:
                    # print('Aye found')
                    votes = h.find_next_sibling()
                    try:
                        tds = votes.find_all('td')
                        for td in tds:
                            # print('Aye:', td.text)
                            motion = cast_vote('Yea', td.text, motion)
                    except Exception as e:
                        # print('faill111', str(e))
                        pass
                elif 'Nays' in h.text:
                    votes = h.find_next_sibling()
                    try:
                        tds = votes.find_all('td')
                        for td in tds:
                            # print('Nays:', td.text)
                            motion = cast_vote('Nay', td.text, motion)
                    except Exception as e:
                        # print('faill2222', str(e))
                        pass
            
                get_votes = False
                get_vote_text = True
            if finish_motion:
                if motion.yeas > motion.nays:
                    motion.result = 'Carried'
                elif motion.nays > motion.yeas:
                    motion.result = 'Lost'
                # print(motion.result)
                motion.save()
            # print('motion saved')
            # time.sleep(4)
    #     try:
    #         print('motion:', motion, motion.result)
    #     except Exception as e:
    #         print(str(e))
    # for m in Motion.objects.filter(province=prov):
    #     print(m)
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()

def get_all_hansards_and_motions(value):
    print('get all hansards', value)
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(country='Canada', organization='Ontario').first()
    url = 'https://www.ola.org/en/legislative-business/house-documents/parliament-%s/session-%s' %(parl.ParliamentNumber, parl.SessionNumber)
    print(url)
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find_all('p', {'class':'field-content'})
    n = 0
    for p in content:
        n += 1
        print(n)
        if value == 'latest' and n > 1:
            print('break1', n)
            break
        elif value == 'recent' and n > 15:
            print('break2', n)
            break
        try:
            a = p.find('a')
            link = 'https://www.ola.org' + a['href']
            if 'hansard' in link:
                print('hansard',link)
                try:
                    H = Hansard.objects.filter(gov_page=link)[0]
                    if not H.has_transcript:
                        print('fail1')
                        fail
                except:
                    get_hansard(link)
                try:
                    m = Motion.objects.filter(gov_url=link)[0]
                except:
                    print('search for motion1')
                    get_motions(link.replace('hansard', 'votes-proceedings'))
            try:
                link = link.replace('hansard', 'votes-proceedings')
                print('votes', link)
                try:
                    m = Motion.objects.filter(gov_url=link)[0]
                except:
                    print('search for motion2')
                    get_motions(link)
            except Exception as e:
                print('get motion fail', str(e))
        except Exception as e:
            print(str(e))
            pass
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()

def check_elections():
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(organization='Ontario')[0]
    print("opening browser")
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    driver.get('https://voterinformationservice.elections.on.ca/en/election/search?mode=electoralDistrict')
    # time.sleep(5)
    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="electoralDistricts"]'))
    WebDriverWait(driver, 10).until(element_present)
    # r = requests.get('https://voterinformationservice.elections.on.ca/en/election/search?mode=electoralDistrict')
    html_source = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html_source, 'html.parser')
    # print(soup)
    summary = soup.find('div', {'class':'election-summary'})
    print(summary)
    if summary:
        h2 = summary.find('h2')
        print(h2.text)
        if 'by-election' in h2.text:
            print('by-election')
            t = 'by-election'
        else:
            print('election')
            t = 'election'

        matches = datefinder.find_dates(h2.text)
        # dt = matches[0]
        # print(dt)
        # matches = datefinder.find_dates(x)
        for match in matches:
            print(match)
            dt = match
            break
        # match = re.search('(Mon|Tue|Wed|Thu|Fri|Sat|Sun).*?(AM|PM)', h2.text)
        # match_date_and_time = match.group() # Tue, Dec 21, 2021 at 1:51 PM
        # dt = datetime.strptime(match_date_and_time, '%a, %b %d, %Y at %I:%M %p')
        # print(dt)
        ul = summary.find('ul')
        lis = ul.find_all('li')
        for li in lis:
            z = li.text.find(' (')
            district_name = li.text[:z]
            print(district_name)
            try:
                district = District.objects.filter(name=district_name, province_name='Ontario')[0]
                print(district)
            except Exception as e:
                print(str(e))
                print('creating district')
                district = District(name=district_name, province_name='Ontario', province=prov)
                search_name = district_name + ' ontario provincial electoral district'
                title = wikipedia.search(search_name)[0].replace(' ', '_')
                district.wikipedia = 'https://en.wikipedia.org/wiki/' + title
                district.save()
                district.create_post()
                print(district)
            
            try:
                e = Election.objects.filter(end_date=dt, level='Provincial', type=t, province=prov, district=district)[0]
                e.ongoing=True
                e.organization = 'Ontario-Assembly'
                e.save()
                # e.create_post()
            except:
                e = Election(end_date=dt, level='Provincial', parliament=parl, type=t, province=prov, district=district, ongoing=True)
                e.save()
                e.create_post()
                e.send_alerts()
            print(e)
        check_candidates()
    else:
        print('no summary')
        e = Election.objects.filter(level='Provincial', province=prov, ongoing=True)
        for q in e:
            q.ongoing = False
            q.save()
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()



def check_candidates():
    prov = Province.objects.filter(name='Ontario')[0]
    parl = Parliament.objects.filter(organization='Ontario')[0]
    print("opening browser")
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
    driver.get('https://voterservices.elections.on.ca/en/election/candidate-search')
    # time.sleep(5)
    element_present = EC.presence_of_element_located((By.XPATH, '/html/body/app-root/app-candidate-search/div/div/div/main/div/div[2]/div/div/div[2]/div/div[2]/div[1]/button'))
    WebDriverWait(driver, 10).until(element_present)
    search = driver.find_element(By.XPATH, '/html/body/app-root/app-candidate-search/div/div/div/main/div/div[2]/div/div/div[2]/div/div[2]/div[1]/button')
    search.click()

    element_present = EC.presence_of_element_located((By.XPATH, '/html/body/app-root/app-candidate-search/div/div/div/main/div/div[2]/div/div/div[4]/div[2]/table'))
    WebDriverWait(driver, 10).until(element_present)
    table = driver.find_element(By.XPATH, '/html/body/app-root/app-candidate-search/div/div/div/main/div/div[2]/div/div/div[4]/div[2]/table')
    rows = table.find_elements(By.CLASS_NAME, 'show-row-indicator')
    for row in rows:
        name = row.find_element(By.CLASS_NAME, 'candidate-name')
        print(name.text)
        z = name.text.find(', ')
        first_name = name.text[z+2:]
        last_name = name.text[:z]
        try:
            a = name.find_element(By.CSS_SELECTOR, 'a')
            print(a.get_attribute('href'))
            website = a.get_attribute('href')
        except Exception as e:
            website = None
        party = row.find_element(By.CLASS_NAME, 'party')
        party_name = party.get_attribute('innerHTML').strip()
        district = row.find_elements(By.CSS_SELECTOR, 'td')[2]
        district_link = district.find_element(By.CSS_SELECTOR, 'a')
        print(district.text)
        z = district.text.find(' (')
        district_name = district.text[:z].strip()
        print(district_link.get_attribute('href'))

        try:
            person = Person.objects.filter(first_name=first_name, last_name=last_name, province_name='Ontario')[0]
            if person.website != website:
                person.website = website
                person.save()
        except:
            print('creating person')
            person = Person(first_name=first_name, last_name=last_name, province_name='Ontario')
            # person.Region_obj = 
            if website:
                person.website = website
            person.save()
            person.create_post()
        print(person)
        try:
            party = Party.objects.filter(province=prov, name=party_name)[0]
        except:
            party = Party(province=prov, name=party_name, province_name='Ontario')
            party.save()
        print(party)
        try:
            district = District.objects.filter(name=district_name, province_name='Ontario')[0]
            print(district)
        except Exception as e:
            print(str(e))
            fail
            # print('creating district')
            # district = District(name=region_name, province_name='Ontario', province=prov)
            # search_name = region_name + ' ontario provincial electoral district'
            # title = wikipedia.search(search_name)[0].replace(' ', '_')
            # district.wikipedia = 'https://en.wikipedia.org/wiki/' + title
            # district.save()
            # district.create_post()
        # district.map_link = map_link
        # district.save()
        # print('save2')
        
        try:
            e = Election.objects.filter(level='Provincial', province=prov, district=district, ongoing=True)[0]
        except:
            e = Election(level='Provincial', province=prov, district=district, type='Election', ongoing=True)
            e.save()
        try:
            candidate = Role.objects.filter(position='Election Candidate', person=person, district=district, election=e, parliament=parl)[0]
            print(candidate)
            candidate.party = party
            candidate.party_name = party.name
            candidate.website = website
            candidate.save()
        except:
            print('creating MPP')
            candidate = Role(position='Election Candidate', person=person, district=district, election=e, parliament=parl)
            # person.Region_obj = 
            candidate.province_name = 'Ontario'
            candidate.person_name = person.full_name
            candidate.district_name = district_name
            candidate.party = party
            candidate.party_name = party.name
            candidate.website = website
            # candidate.current = True
            candidate.save()
            print('candidate saved')
            print('----------')
    print('done')
    driver.quit()
    # sys.modules[__name__].__dict__.clear()
    # gc.collect()


#not used
def get_ontario_match(request, person):
    parl = Parliament.objects.filter(country='Canada', organization='Ontario')[0]
    prov = Province.objects.filter(name='Ontario')[0]
    reactions = Reaction.objects.filter(user=request.user, post__post_type='bill').filter(post__bill__province=prov).order_by('-post__date_time')
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
            # print(r.isYea, r.isNay)
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
                # print('match')
            return 'match', vote_matches, total_matches, return_votes
        except Exception as e:
            pass
        return 'nomatch', vote_matches, total_matches, return_votes
    for bill in votes:
        # print('------', bill)
        # print(billVersion)
        # print(votes[billVersion])
        try:
            motions = Motion.objects.filter(bill=bill, ParliamentNumber=parl.ParliamentNumber, SessionNumber=parl.SessionNumber).order_by('-date_time')
            for m in motions:
                my_votes[m.id] = votes[bill]
                result, vote_matches, total_matches, return_votes = match_vote(m, person, votes, bill, vote_matches, total_matches, return_votes)
                if result == 'match':
                    matched.append(m)
                    break
        except Exception as e:
            print(str(e))
    # print(vote_matches, '/', total_matches)
    try:
        match_percentage = int((vote_matches / total_matches) * 100)
    except Exception as e:
        match_percentage = None
    # print(match_percentage)
    return match_percentage, total_matches, vote_matches, my_votes, return_votes

