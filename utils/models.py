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
# from scrapers.canada.federal import *
# import scrapers.canada.ontario.provincial as ontario



# from firebase_admin.messaging import Notification as fireNotification
# from firebase_admin.messaging import Message as fireMessage
# from fcm_django.models import FCMDevice
import datetime
from zoneinfo import ZoneInfo
from datetime import date
from django.utils import timezone
# import requests
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
from selenium.webdriver.chrome.service import Service
# from fake_useragent import UserAgent

from utils.locked import dt_to_string



import platform
import os
if platform.system() == 'Darwin':       # macOS
    # subprocess.call(('open', filepath))
    device_system = 'mac'
elif platform.system() == 'Windows':    # Windows
    device_system = 'windows'
    # os.startfile(filepath)
else:                                   # linux variants
    device_system = 'linux'

runTimes = {
    'daily_summarizer' : 500,
    'send_notifications' : 200,
    'check_elections': 200,
    'updateTop': 200,
}

functions = [
     {'day' : 'x', 'dayOfWeek' : 'x', 'hour' : 'x', 'cmds' : ['updateTop']},
     {'day' : 'x', 'dayOfWeek' : 'x', 'hour' : 8, 'cmds' : ['daily_summarizer', 'check_elections']},
     {'day' : 'x', 'dayOfWeek' : 'x', 'hour' : 12, 'cmds' : ['check_elections']},
     {'day' : 'x', 'dayOfWeek' : 'x', 'hour' : 18, 'cmds' : ['send_notifications','check_elections']},
     {'day' : 'x', 'dayOfWeek' : 'x', 'hour' : 24, 'cmds' : ['check_elections']},

]


import gzip
from io import BytesIO
import base64

def compress_data(data):
    # prnt('compressing...')
    if isinstance(data, str):
        # prnt('opt1')
        data = data.encode('utf-8')  # Only encode if it's a string
    elif isinstance(data, dict) or isinstance(data, list):
        # prnt('opt2')
        data = json.dumps(data).encode('utf-8')
    # json_data = json.dumps(data)
    # # if isinstance(json_data, str):
    # #     prnt('json_data', 'is str')
    # json_bytes = json_data.encode('utf-8')
    
    # # Compress the byte data using gzip
    # compressed_data = gzip.compress(json_bytes)

    compressed_data = gzip.compress(data)
    return base64.b64encode(compressed_data).decode('utf-8')
    # return compressed_data

def decompress_data(base64_data):
    # prnt('decompressing...')
    try:
        compressed_data = base64.b64decode(base64_data)
        decompressed_bytes = gzip.decompress(compressed_data)
        json_data = decompressed_bytes.decode('utf-8')
        data = json.loads(json_data)
        return data
    except Exception as e:
        prntDebug('decompress_data error',str(e))
        try:
            return json.loads(base64_data)
        except:
            return base64_data

def is_debug():
    debugging = False
    try:
        # from blockchain.models import get_operatorData
        operatorData = get_operatorData()
        if operatorData['myNodes'][operatorData['local_nodeId']]['meta']['debug'] == True:
            return True
        else:
            prnt('whats up debug:',operatorData['myNodes'][operatorData['local_nodeId']]['meta']['debug'])
            prnt('wdb2', operatorData['start_local_install'])
    except Exception as e:
        prnt('fial9593',str(e))
    try:
        if 'start_local_install' in operatorData and operatorData['start_local_install'] == True:
            return True
    except Exception as e:
        prnt('fial9634',str(e))
    return debugging    

def is_test_env():
    # prntn('---is_test_env')

    # from blockchain.models import get_operatorData
    operatorData = get_operatorData(return_test=False)
    try:
        if 'isTesting' in operatorData and operatorData['myNodes'][operatorData['local_nodeId']]['settings']['isTesting']:
            return True
    except:
        pass
    import os
    current_dir = os.getcwd()
    
    while True:
        sfolder_path = os.path.join(current_dir, 'sonet')
        # prntn(sfolder_path)
        if os.path.isdir(sfolder_path):
            file_path = os.path.join(sfolder_path, 'settings/local.py')
            # prnt('return true')
            return os.path.isfile(file_path)
        
        parent_dir = os.path.dirname(current_dir)
        
        # If current_dir is the root directory, stop the loop
        if current_dir == parent_dir:
            break
        
        current_dir = parent_dir
    
    return False

def timezonify(tz, dt):
    if tz.lower() in ['est', 'newyork', 'washington', 'dc']:
        tz = 'America/New_York'
    elif tz.lower() in ['toronto', 'ottawa']:
        tz = 'America/Toronto'
    else:
        tz = 'UTC'
    if dt.tzinfo is None:
        local_dt = dt.replace(tzinfo=ZoneInfo(tz))
    else:
        local_dt = dt.astimezone(ZoneInfo(tz))
    return local_dt

_testing = None
_debugging = None

def testing():
    global _testing
    if _testing is None:
        _testing = is_test_env()
    return _testing

def debugging():
    global _debugging
    if _debugging is None:
        _debugging = is_debug()  # Compute the value only once
    return _debugging

import logging
logger = logging.getLogger("django")

# def my_view(request):
    # logger.info("This is a debug message")
    # return HttpResponse("Check logs")

def prnt(*args):
    # logger.info("This is a debug message")
    msg = ','.join(f"{i}" for i in args)
    # print(f'p1:{msg}')
    logger.info(f'~:{msg}')

def prntDev(*args):
    if testing():
        msg = '*' + ','.join(str(i) for i in args)
        # print(f'p2:{msg}')
        logger.info(f'~:{msg}')
        # prnt('#',','.join(f"{i}" for i in args))

def prntDebug(*args):
    if debugging() or testing():
        msg = '#' + ','.join(str(i) for i in args)
        # msg = '*,'.join(f"{i}" for i in args)
        # print(f'p3:{msg}')
        logger.info(f'~:{msg}')
        # prnt('*',','.join(f"{i}" for i in args))
    else:
        msg = '#' + ','.join(str(i) for i in args)
        # msg = '*,'.join(f"{i}" for i in args)
        # print(f'p3:{msg}')
        logger.info(f'~:{msg}')
        prnt('not debug above:')

def prntn(*args):
    # logger.info("This is a debug message")
    msg = ','.join(f"{i}" for i in args)
    # print(f'p1:{msg}')
    logger.info(f'\n~:{msg}')

def prntDevn(*args):
    if testing():
        msg = '*' + ','.join(str(i) for i in args)
        # print(f'p2:{msg}')
        logger.info(f'\n~:{msg}')
        # prnt('#',','.join(f"{i}" for i in args))

def prntDebugn(*args):
    if debugging() or testing():
        msg = '#' + ','.join(str(i) for i in args)
        # msg = '*,'.join(f"{i}" for i in args)
        # print(f'p3:{msg}')
        logger.info(f'\n~:{msg}')
        # prnt('*',','.join(f"{i}" for i in args))

def string_to_dt(dt_str):
    if isinstance(dt_str, datetime.datetime):
        return dt_str
    if isinstance(dt_str, str):
        if 'Z' in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            # print(dt)
            return dt
        return datetime.datetime.fromisoformat(dt_str)
    return None

def list_all_scrapers():
    import sys
    import os
    from pathlib import Path
    current_directory = Path(__file__).parent.parent
    sibling_folder = current_directory / 'scrapers'
    sys.path.append(str(sibling_folder))
    all_files = []
    for root, dirs, files in os.walk(sibling_folder):
        for file in files:
            if file.endswith('.py'):
                all_files.append(os.path.join(root, file))
    return all_files



def open_browser(url=None, headless=True, chrome_testing=False):
    prnt("--opening browser", url)
    # ua = UserAgent()
    # user_agent = ua.random
    def chrome_for_testing():

        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options

        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        if headless:
            options.add_argument("--headless")

        if device_system == 'linux':
            chrome_binary_path = os.path.expanduser("~/chrome-for-testing/chrome-linux64/chrome")
            chromeDriver_path = os.path.expanduser("~/chrome-for-testing/chromedriver-linux64/chromedriver")
        elif device_system == 'mac':
            chrome_binary_path = "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            chromeDriver_path = "/usr/local/bin/chromedriver"
            options.add_argument("--disable-breakpad")  # Disables crashpad crash reporter
            options.add_argument("--no-default-browser-check")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-logging")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Prevent logs
            # chrome_binary_path = "../chrome-for-testing/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            # chromeDriver_path = "../chrome-for-testing/chromedriver-mac-arm64/chromedriver"
        # elif device_system == 'mac':
        #     chrome_binary_path = "../chrome-for-testing/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        #     chromeDriver_path = "../chrome-for-testing/chromedriver-mac-arm64/chromedriver"

        # options.add_argument(f"user-agent={user_agent}")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
        options.binary_location = chrome_binary_path
        service = Service(chromeDriver_path)
        return webdriver.Chrome(service=service, options=options), service
    
    def normal_chrome(attempt=1):

        try:
            # Chrome options
            chrome_options = Options()
            chrome_options.binary_location = "/usr/bin/google-chrome"  # Explicit Chrome binary path
            chrome_options.add_argument('--no-sandbox')
            if headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
            chrome_options.add_argument('--remote-debugging-port=9222')

            # Desired capabilities
            caps = DesiredCapabilities().CHROME.copy()
            caps["pageLoadStrategy"] = "normal"

            # Chromedriver initialization
            service = webdriver.chrome.service.Service("/usr/local/bin/chromedriver")  # Explicit Chromedriver path
            driver = webdriver.Chrome(service=service, options=chrome_options)


            # chrome_options = Options()
            # chrome_options.add_argument('--no-sandbox')
            # if headless:
            #     chrome_options.add_argument("--headless")
            # chrome_options.binary_location = os.path.expanduser("/usr/local/bin/chrome")
            # chrome_options.add_argument(f"user-agent={user_agent}")
            # chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            # # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # # chrome_options.add_experimental_option("useAutomationExtension", False)
            # driver = webdriver.Chrome(options=chrome_options)
            # # caps = DesiredCapabilities().CHROME
            # # caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
            # # driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
            return driver, service
        except Exception as e:
            prnt('fail38572',str(e))
#             session not created: This version of ChromeDriver only supports Chrome version 131
# Current browser version is 136.0.7103.92 with binary path /usr/bin/google-chrome
            version_err = '''Message: session not created: This version of ChromeDriver only supports Chrome version'''
            install_err = '''Unable to obtain driver for chrome'''
            if version_err in str(e):
                # Current browser version is 136.0.7103.92 with binary path /usr/bin/google-chrome'''
                x = str(e).find('Current browser version is ')+len('Current browser version is ')
                y = str(e)[x:].find(' ')
                required_version = str(e)[x:x+y]
                prnt('required_version',required_version)
                if attempt == 1:
                    update_chromeDriver(required_version)
                    return normal_chrome(attempt=2)
            elif install_err in str(e):
                if attempt == 1:
                    update_chromeDriver()
                    return normal_chrome(attempt=2)


    
    if chrome_testing or device_system == 'mac':
        driver, service = chrome_for_testing()
    else:
        driver, service = normal_chrome()

    if url:
        driver.get(url)


    return driver, service

def close_browser(driver, service=None):
    driver.quit()
    try:
        service.stop()
    except Exception:
        pass

def update_chromeDriver(required_version=None):
    prnt('update_chromeDriver',required_version)
    if platform.system() == 'Darwin': 
        # import requests
        # r = requests.get('https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE')
        # if r.status_code == 200:
        #     stable_ver = r.content.decode('utf-8')
            # chrome_link = f'https://storage.googleapis.com/chrome-for-testing-public/{stable_ver}/mac-arm64/chrome-mac-arm64.zip'
        driver_link = f'https://storage.googleapis.com/chrome-for-testing-public/{required_version}/mac-arm64/chromedriver-mac-arm64.zip'

        group = subprocess.check_output("id -gn", shell=True).decode().strip()
        import getpass
        username = getpass.getuser()
        commands = [
            ['wget', '-O', '/tmp/chromedriver_mac64.zip', driver_link],
            ['unzip', '/tmp/chromedriver_mac64.zip', '-d', '/tmp'],
            ['sudo', '-S', 'mv', '/tmp/chromedriver', '/usr/local/bin/'],
            ['sudo', '-S', 'chown', f'{username}:{group}', '/usr/local/bin/chromedriver'],
            ['sudo', '-S', 'chmod', '+x', '/usr/local/bin/chromedriver'],
            ['rm', '/tmp/chromedriver_mac64.zip'],
        ]
    else:
        if not required_version:
            required_version = '131.0.6778.85'
        commands = [
            ['wget', '-O', '/tmp/chromedriver-linux64.zip', f'https://storage.googleapis.com/chrome-for-testing-public/{required_version}/linux64/chromedriver-linux64.zip'],
            ["sudo", "-S", "apt", "install", "zip"],
            # ["unzip", "/tmp/chromedriver-linux64.zip", "-y"],
            ["unzip", "-o", "/tmp/chromedriver-linux64.zip", "-d", "/tmp"],
            ["sudo", "-S", "mv", "/tmp/chromedriver-linux64/chromedriver", "/usr/local/bin/"],
            ["sudo", "-S", "chown", "root:root", "/usr/local/bin/chromedriver"],
            ["sudo", "-S", "chmod", "+x", "/usr/local/bin/chromedriver"],
            ["sudo", "-S", "rm", "/tmp/chromedriver-linux64.zip"],
        ]

    import subprocess
    # from blockchain.models import get_operatorData
    operatorData = get_operatorData()
    systemPass = operatorData['systemPass']
    for cmd in commands:
        prnt('cmd',cmd)
        result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
        prnt('result',result)


def create_job(job_func, job_timeout=60, worker='low', clear_chrome_job=False, **kwargs):
    prnt('create_job',job_func)
    if isinstance(worker, str):
        queue = django_rq.get_queue(worker)
    else:
        queue = worker
    queue.enqueue(job_func, **kwargs, job_timeout=job_timeout, result_ttl=3600)

    if clear_chrome_job:
        from utils.cronjobs import clear_chrome
        queue.enqueue(clear_chrome, job_timeout=10)

def remove_accents(input_str):
    import unicodedata
    normalized_str = unicodedata.normalize('NFD', input_str)
    filtered_str = ''.join(
        char for char in normalized_str 
        if unicodedata.category(char) != 'Mn'
    )
    return unicodedata.normalize('NFC', filtered_str)

def get_timeData(obj, sort='created', querying=False, descending=True, first_string=False):
    # prntDebug('-get_timeData', obj)
    # from posts.models import has_field

    if sort == 'created':
        x = ['created', 'DateTime']
    elif sort == 'updated':
        x = ['last_updated', 'DateTime', 'created']
    if querying or first_string:
        # prntDebug('fields::',obj._meta.fields)
        # prnt('x',x)
        z = 0
        for i in reversed(x):
            # prnt('I',i)
            if not has_field(obj, i):
                # prntDebug('removing ',i)
                # x.pop(z)
                x.remove(i)
            # else:
            #     prntDebug('has field', i)
            z += 1
        if first_string:
            return x[0]
        if descending:
            x = ['-' + item for item in x]
        # prntDebug('returning',x)
        return x
    else:
        for i in x:
            if has_field(obj, i):
                return getattr(obj, i)
    return None

def chunk_list(data, chunk_size=500):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def chunk_dict(data, chunk_size=500):
    if isinstance(data, dict):
        keys = list(data.keys())
        for i in range(0, len(keys), chunk_size):
            yield {key: data[key] for key in keys[i:i + chunk_size]}
    elif isinstance(data, list):
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]





def now_utc():
    return datetime.datetime.now(pytz.utc)   

def is_timezone_aware(dt):
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

def baseline_time():
    from blockchain.models import Sonet
    return Sonet.objects.first().created


def string_to_64_char_hash(s): #unused?
    import hashlib
    hash_object = hashlib.sha256(s.encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    return hex_dig

def generate_keyPair(password): # unused?
    prnt('gen keypair')
    get_keys = '''
    function createKeys(){   
    const curve = new elliptic.ec('secp256k1');
    let keyPair = curve.keyFromPrivate('%s');
    let privKey = keyPair.getPrivate("hex");
    const publicKey = keyPair.getPublic();
    const publicKeyHex = keyPair.getPublic().encode('hex');
    return [privKey, publickKeyHex];
    }
    createKeys()
    ''' %(password)

    from pythonmonkey import eval as js_eval
    with open("elliptic.js", "r") as file:
        elliptic_js_code = file.read()

    full_js_code = elliptic_js_code + "\n" + get_keys

    keys = js_eval(full_js_code)
    prnt('result', keys)
    return keys


def process_received_dp(data, msg='unspecified', skip_log_check=False, override_completed=False):
    prnt('process_received_dp')
    from blockchain.models import DataPacket
    if isinstance(data, str) and get_pointer_type(data) == 'DataPacket':
        dp = DataPacket.objects.filter(id=data).first()
        prntDebug('dp0',dp)
        if not dp:
            return {}
        data = dp.data
    elif isinstance(data, str) and get_pointer_type(data) == 'EventLog':
        dp = DataPacket.objects.filter(id=data).first()
        prntDebug('dp1',dp)
        if not dp:
            return {}
        data = dp.data
    elif isinstance(data, models.Model) and data.object_type == 'DataPacket':
        dp = data
        data = dp.data
        prntDebug('data2',dp)
    elif isinstance(data, list):
        prntDebug('list',str(data)[:250])
        return {'data':{'content':data}}
    elif data:
        prnt('returing data',str(data)[:250])
        return {'data':{'content':data}}
    else:
        # prntDebug('else')
        dp = None
        data = {}
    if dp and 'process' not in dp.func and not override_completed:
        return {} 
    
    if dp:
        if skip_log_check:
            proceed = True
        else:
            x = 1
            proceed = False
            sig = dp.data['signature']
            pubKey = dp.data['pubKey']
            received_hashed = dp.data['hashed']
            del dp.data['signature']
            del dp.data['pubKey']
            del dp.data['hashed']
            import hashlib
            from utils.locked import sort_for_sign, verify_data
            hashed = hashlib.md5(str(sort_for_sign(dp.data)).encode('utf-8')).hexdigest()
            dp.data['signature'] = sig
            dp.data['pubKey'] = pubKey
            dp.data['hashed'] = received_hashed
            # prntDebug('hashed',hashed,received_hashed)
            x = 2
            if hashed == received_hashed:
                x = 3
                from accounts.models import UserPubKey
                upk = UserPubKey.objects.filter(publicKey=pubKey).first()
                if upk:
                    x = 4
                    if not upk.end_life_dt or upk.end_life_dt > string_to_dt(dp.data['dt']):
                        x = 5
                        if verify_data(hashed, upk, sig):
                        # if upk.verify(hashed, sig):
                            x = 6
                            proceed = True
        if not proceed:
            dp.completed(f'{msg}-x:{x}')
            prntDebug('r1')
            return None
        prntDebug('r2')
        return {'dp':dp, 'data':data}
    prntDebug('r3')
    return {'data':data}

def err(err, code):
    return err + str(code)

def to_datetime(value):
    """Convert a value to a datetime object if it's a string."""
    if isinstance(value, datetime.datetime):
        return value
    elif isinstance(value, str):
        from dateutil.parser import parse
        return parse(value)
    else:
        raise ValueError("Value must be a datetime object or a string")


def str_to_hash(text):
    import hashlib
    text_bytes = str(text).encode('utf-8')
    sha256_hash = hashlib.sha256(text_bytes).hexdigest()
    return sha256_hash

def hash_to_int(hash_string, length):
    filtered_hash = re.sub(r'[^a-fA-F0-9]', '', hash_string)
    hash_int = int(filtered_hash, 16)
    if length == 0:
        return 0
    else:
        return hash_int % length

def date_to_int(date):
    if isinstance(date, str):
        date = string_to_dt(date)
    if not testing():
        # from accounts.models import Sonet
        from blockchain.models import Sonet
        start_dt = Sonet.objects.first().created
    else:
        start_dt = now_utc() - datetime.timedelta(weeks=1)
    time_difference = date - start_dt
    minutes_difference = time_difference.total_seconds() /60/60
    return int(minutes_difference)

def round_time(dt=None, dir='down', amount='hour'):
    if not dt:
        dt = now_utc()
    if isinstance(dt, str):
        dt = string_to_dt(dt)
    def reduce_hours(dt, hr):
        dt = dt - datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
        hour = dt.hour
        while hour % hr != 0:
            hour -= 1
        dt = dt.replace(hour=hour)
        return dt
    def round_mins(dt, mins, dir='down'):
        r = dt - datetime.timedelta(minutes=(dt.minute % mins), seconds=dt.second, microseconds=dt.microsecond)
        if dir == 'up':
            r = r  + datetime.timedelta(minutes=mins)
        return r
    if dir == 'down':
        if amount == 'hour':
            return dt - datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
        elif amount == 'evenhour':
            return reduce_hours(dt, 2)
        elif amount == '10mins':
            return round_mins(dt, 10)
        elif 'hours' in amount:
            x = amount.find('-')
            hr = int(amount[:x])
            return reduce_hours(dt, hr)
        elif amount == 'day':
            return dt - datetime.timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
        elif amount == 'week':
            return (dt - datetime.timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif amount == 'month':
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif dir == 'up':
        if amount == '10mins':
            return round_mins(dt, 10, dir='up')



def get_operator_obj(obj, operatorData=None):
    # prnt('get_operator_obj', obj)
    use_keyRing = False
    # prnt('platform.system()',platform.system())
    if platform.system() not in ['Darwin', 'Windows']:
        use_keyRing = True
    # prnt('use_keyRing',use_keyRing)
    SERVICE_NAME = "Sonet"
    KEY_NAME = obj
    result = None
    if use_keyRing:
        # import keyring
        # result = keyring.get_password(SERVICE_NAME, KEY_NAME)
        # prnt('result1',result)
        if result:
            result = json.loads(result)
    # except Exception as e:
    #     prntDebug('fail75398',str(e))
    if not result:
        if not operatorData:
            operatorData = get_operatorData()
        # prnt('operatorData4824',operatorData)
        if obj.lower() == 'keypair':
            pubkey = operatorData['pubKey']
            privkey = operatorData['privKey']
            result = {'pubKey':pubkey,'privKey':privkey}
        elif obj.lower() == 'userid':
            result = operatorData['user_id']
        elif obj.lower() == 'local_nodeid':
            result = operatorData['local_nodeId']
        # if use_keyRing:
        #     keyring.set_password(SERVICE_NAME, KEY_NAME, json.dumps(result))
        # prnt('result2',result)
    # prnt("Key loaded securely from keyring")
    return result

def get_operatorData(return_test=True):
    # prnt('get_operatorData')
    try:
        home = os.path.expanduser("~")
        operator_path = os.path.join(home, "Sonet", ".data")
        with open(f"{operator_path}/operatorData.json", 'rb') as file:
            encrypted_data = file.read()
            data_string = decrypt(encrypted_data)
            json_obj = json.loads(data_string)
    except Exception as e:
        # prnt(str(e))
        json_obj = {}
        if return_test and testing():
            json_obj = {'pubKey': '0473aabdbd6dbbf2f8fb60fd3ce0bc7035d558e1c4e980c29b7c86e8bdda99ca7dd4275edc8ece06c301cc6788d137ea66f3969a46d84d636eefdaf4d2fb8bfd3a',
            'privKey':'071a850b47b4eff030e3617988c9134e11212dd574b05f5bfb47c805634e09fa','debug':True} # this will not work for you
    # prnt('json_obj',json_obj)
    return json_obj

def write_operatorData(data):
    try:
        current_data = get_operatorData()
        data = {**current_data, **data}
    except:
        pass
    data_string = json.dumps(data, indent=4)
    encrypted_data = encrypt(data_string)
    home = os.path.expanduser("~")
    operator_path = os.path.join(home, "Sonet", ".data")
    with open(f"{operator_path}/operatorData.json", 'wb') as file:
        file.write(encrypted_data)

def load_key():
    # prnt('load_key')
    system = platform.system()
    if system == 'Windows':
        file_path = "../.data/soSecret.key"
    elif system in ('Linux', 'Darwin'):  # Darwin is macOS
        file_path = "../.data/.soSecret.key"
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        prnt('fail583650',str(e))

def encrypt(text):
    key = load_key()
    from cryptography.fernet import Fernet
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(text.encode())
    return cipher_text

def decrypt(text):
    # prnt('decrypt', text)
    key = load_key()
    from cryptography.fernet import Fernet
    cipher_suite = Fernet(key)
    decrypted_text = cipher_suite.decrypt(text).decode()
    return decrypted_text

def script_test_error(testing, err, wait=False, log=None):
    if testing:
        prnt(err)
        if wait:
            time.sleep(wait)
    elif log:
        from blockchain.models import logEvent
        logEvent('scrapeAssignment: ' + log[0].Name + ' ' + log[1] + ' ' + err + ' ' + now_utc(), log_type='Tasks')

def to_megabytes(instance):
    from django.core.serializers import serialize
    import sys
    if not isinstance(instance, dict) and not isinstance(instance, str):
        data = serialize('json', [instance])
    else:
        data = instance
    size_in_bytes = sys.getsizeof(data)
    size_in_kilobytes = size_in_bytes / 1024 
    size_in_megabytes = size_in_kilobytes / 1024
    return size_in_megabytes

def get_latest_dataPacket(chain='All'):
    prnt('---get_latest_dataPacket',chain)
    from blockchain.models import UserChains, NodeChain_genesisId, DataPacket
    self_node = get_self_node()
    # chainId = chain
    if isinstance(chain, models.Model):
        if chain.genesisType == 'Region' or get_pointer_type(chain.genesisId) == UserChains or chain.genesisId == NodeChain_genesisId:
            chain = 'All'
    elif is_id(chain):
        if get_pointer_type(chain) in ['Region', 'User', 'Node']:
            chain = 'All'
    dataPacket = DataPacket.objects.filter(chainId=chain, func='share', created__gte=now_utc()-datetime.timedelta(days=7)).first()
    if not dataPacket:
        try:
            dataPacket = DataPacket(chainId=chain, Node_obj=self_node, func='share')
            dataPacket.save()
        except Exception as e:
            prnt('fail130678',str(e))
            return None
    if dataPacket and not dataPacket.Node_obj and self_node:
        dataPacket.Node_obj = self_node
        dataPacket.save()
    return dataPacket

def get_node_list(sort='-last_updated'):
    from blockchain.models import Node
    # nu = NodeReview.objects.exclude(deactivated=True).distinct('pointerId').order_by(sort)
    nodes = Node.objects.exclude(activated_dt=None).filter(suspended_dt=None).order_by(sort)
    node_list = []
    for node in nodes:
        node_list.append(node)
    return nodes

def get_self_node(operatorData=None):
    # prntDev('---get_self_node')
    from blockchain.models import Node
    if not operatorData:
        operatorData = get_operatorData()
    try:
        try:
            self_node_id = operatorData['myNodes'][operatorData['local_nodeId']]['nodeData']['id']
            return Node.objects.filter(id=self_node_id).first()
        except:
            pass
        if testing():
            return Node.objects.first()
    except Exception as e:
        prnt('fail46036',str(e))
    return None

def get_user(node=None, user_id=None, node_id=None, public_key=None, obj=None, target=None, request_missing=True):
    # prnt('get user, id:',user_id, 'public_key:', public_key,'node',node, 'node_id',node_id,'obj',obj,'target',target)
    from accounts.models import User, UserPubKey
    from blockchain.models import Node, connect_to_node
    user = None
    operatorData = None
    if user_id:
        model_type = get_pointer_type(user_id)
        if model_type == 'User':
            user = User.objects.filter(id=user_id).first()
        else:
            obj = get_dynamic_model(model_type, id=user_id)
            if obj and obj.publicKey:
                public_key = obj.publicKey
    if not user and obj:
        if isinstance(obj, models.Model):
            public_key = obj.publicKey
        elif isinstance(obj, dict):
            if 'publicKey' in obj:
                public_key = obj['publicKey']
    if not user and public_key:
        upk = UserPubKey.objects.filter(publicKey=public_key).first()
        if upk:
            user = upk.User_obj
    if not user and node_id:
        node = Node.objects.filter(id=node_id).first()
        if node:
            user = node.User_obj
    if not user and node:
        user = User.objects.filter(id=node.User_obj.id).first()
        if not user:
            if not operatorData:
                operatorData = get_operatorData()
            user = User.objects.filter(id=operatorData['user_id']).first()
    if not user and request_missing:
        try:
            if not operatorData:
                operatorData = get_operatorData()
            if not target:
                nodes = operatorData['ip_master_list']
                random.shuffle(nodes)
                for i in node:
                    if i != operatorData['ip_address']:
                        target = i
                        break
            
            from utils.locked import sign_obj
            userData = json.dumps(sign_obj(operatorData['userData']))
            upkData = json.dumps(sign_obj(operatorData['upkData']))
            nodeData = get_self_node(operatorData=operatorData)
            signedNode = sign_obj(nodeData)
            selfNode = json.dumps(signedNode)
            signedRequest = json.dumps(sign_obj({'type':'User','items' : 'All', 'index' : 0,'dt':dt_to_string(round_time(dt=now_utc(), dir='down', amount='evenhour')),'obj_updated_on_node':None}))
            data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
            success, response = connect_to_node(target, 'blockchain/request_data', data)
            if success:
                user = get_user(node=node, user_id=user_id, public_key=public_key, request_missing=False)
        except Exception as e:
            prnt('fail4902756',str(e))
            if testing():
                user = User.objects.all().first()
    return user

def get_node(id=None, ip_address=None, publicKey=None):
    # prnt('--get_node',id,ip_address,publicKey)
    from blockchain.models import Node
    if id:
        return Node.objects.filter(id=id).first()
    elif ip_address:
        return Node.objects.filter(ip_address=ip_address).first()
    elif publicKey: # not recommended
        user = get_user(public_key=publicKey)
        return Node.objects.filter(User_obj=user).first()

def accessed(node=None, response_time=None, update_data=None):
    # prnt('accessed', node)
    if node:
        node.accessed(response_time=response_time)
    return node

def deactivate(node=None, update_data=None):
    from blockchain.models import Node, NodeReview
    update = None
    if update_data: # i think dont do this
        # last_accessed = NodeReview.objects.exclude(accessed=None).filter(pointerId=update_data['pointerId'])[0]
        try:
            node = Node.objects.filter(id=update_data['TargetNode_obj']).first()
            suspended_dt = convert_to_datetime(update_data['suspended_dt'])
            if node.get_last_accessed().accessed < suspended_dt:
                nodeUpdates = NodeReview.objects.exclude(suspended_dt=None).filter(TargetNode_obj__id=update_data['TargetNode_obj']) # suspended_dt removed from nodeReview
                for update in nodeUpdates:
                    update.delete()
                update = NodeReview()
                for field in update_data:
                    setattr(update, field, update_data[field])
                update.save()
        except:
            pass
    elif node:
        node.deactivate()
    return update

# def update_peer_list(new_node_list):
    # old_nodes = get_node_list()
    updated_nodes = []
    for n in new_node_list:
        try:
            node = Node.objects.filter(id=n['obj']['obj_dict']['id'])[0]
        except:
            node = Node()
            for field in n:
                setattr(node, field, n[field])
            node.save()
        try:
            node_failures = n['obj']['obj_dict']['related']['references']
            for failure in node_failures:
                try:
                    f = NodeReview.objects.filter(id=failure['id'])[0]
                except:
                    f = NodeReview()
                    for field in n:
                        setattr(f, field, n[field])
                    f.save()
        except Exception as e:
            prnt(str(e))
        updated_nodes.append(node)
    # for node in old_nodes:
    #     if node not in updated_nodes:
    #         node.delete_with_failures()

def find_or_create_chain_from_json(genesisId=None, obj=None): # not used?
    from blockchain.models import Node, Blockchain, request_items
    if genesisId:
        blockchain = Blockchain.objects.filter(genesisId=genesisId).first()
    if not blockchain:
        # from utils.models import get_pointer_type, find_or_create_chain_from_object
        genesisObj = get_dynamic_model(get_pointer_type(genesisId), id=genesisId)
        if not genesisObj:
            request_items([genesisId], Node.objects.exclude(activated_dt=None).filter(supportedChains_array__contains=genesisId, suspended_dt=None))
            genesisObj = get_dynamic_model(get_pointer_type(genesisId), id=genesisId)
        if genesisObj:
            blockchain, obj, secondChain = find_or_create_chain_from_object(genesisObj)
    return blockchain

def convert_to_datetime(data): # repeated above, both used
    if isinstance(data, datetime.datetime):
        return data
    try:
        dt = datetime.datetime.strptime(data, 'datetime.datetime(%Y, %m, %d, %H, %M, tzinfo=<%Z>)')
    except:
        dt = string_to_dt(data)
    return dt


def modelData_to_hash(obj): # seems unused
    if not isinstance(obj, dict):
        data = convert_to_dict(obj)
    else:
        data = obj
    del data['hash']
    del data['updated_on_node']
    del data['signature']
    del data['publicKey']
    return hashlib.sha256(str(data).encode()).hexdigest()

def sigData_to_hash(obj):
    import hashlib
    from utils.locked import get_signing_data
    # prntDebug('get_sigData_to_hash')
    data = get_signing_data(obj)
    text_bytes = str(data).encode('utf-8')
    hashed = hashlib.sha256(text_bytes).hexdigest()
    return hashed

#  'type': 'Standing'}]}}
# '<' not supported between instances of 'tuple' and 'str'



    # if str(data).startswith('{'):
    #     if not isinstance(data, dict):
    #         data = dict(data)
    #     r = {key: sort_dict(value) for key, value in sorted(data.items())}
    #     return r
    # elif str(data).startswith('['):
    #     if not isinstance(data, list):
    #         data = list(data)
    #     return [sort_dict(item) for item in data]
    # else:
    #     return data



def data_sort_priority(entry, version=None):
    # prnt('data_sort_priority')
    # sort received data in order for adding to database
    type_order = {'User': 0, 'UserPubKey': 1, 'Validator': 2, 'Node':3, 'NodeReview': 4, 'Sonet':4, 'UserTransaction':5, 'Block':6, 'Region':7,
                'District':8, 'Government':9, 'Person':10, 'Update':11, 'Party':12, 
                'Bill':13, 'Committee':14, 'Meeting':15, 'Statement':16, 'Motion':17, 'Vote':18, 'Agenda':19, 'BillText':20}
    
    def parse_datetime(value):
        if isinstance(value, str) and value.lower() != 'none':
            try:
                return string_to_dt(value).timestamp()
            except ValueError:
                pass  # Invalid date format, will return inf
        return float('inf')  # Fallback

    if isinstance(entry, dict):
        # prnt('is dict', str(entry)[:100])
        type_priority = type_order.get(entry.get('object_type', ''), float('inf'))
        datetime_keys = ['created', 'last_updated']
        # datetime_priority = next(
        #     (entry[key] for key in datetime_keys if key in entry and entry[key] is not (None, 'None')),
        #     float('inf')  # Fallback for missing datetime values
        # )
        datetime_priority = next(
            (parse_datetime(entry[key]) for key in datetime_keys if key in entry and entry[key] not in (None, 'None')),
            float('inf')
        )
                
    elif is_id(entry):
        # prnt('is iden', str(entry)[:100])
        type_priority = type_order.get(get_pointer_type(entry), float('inf'))
        datetime_priority = float('inf')
    elif isinstance(entry, list):
        # prnt('is list', str(entry)[:100])
        # from utils.models import get_app_name
        result = sorted(entry, key=lambda x: type_order.get(get_app_name(model_name=x, am_i_model=True), float('inf')))
        datetime_priority = float('inf')
        return result
    return (type_priority, datetime_priority)


def exists_in_worker(func, arg, queue=None, queue_name=None, currently_running_only=False, job_count=1):
    prntDebugn('exists_in_worker',func,arg,queue,currently_running_only)
    from rq.job import Job
    from django_rq import get_connection, get_scheduler, get_queue
    from rq.worker import Worker
    if queue_name and not queue:
        queue = get_queue(queue_name)
    connection = get_connection(queue.name)
    found_jobs = 0
    try:
        for w in Worker.all(connection): # get current running jobs
            job_id = w.get_current_job_id()
            if job_id:
                # prntDebug('job_id',job_id)
                job = Job.fetch(job_id, connection=w.connection)
                # prntDebug('job',job)
                if job:
                    # prntDebug('job.func_name',job.func_name)
                    if job.func_name.endswith(func):
                        # prntDebug('cont1',job.kwargs.values(),job.args)
                        if arg in job.kwargs.values() or str(arg) in str(job.args):
                            # prntDebug('cont2 true')
                            found_jobs += 1
            if found_jobs >= job_count:
                prntDebug('return 2 true')
                return True
    except Exception as e:
        prnt('fail exists in worker 34952',str(e))
    if not currently_running_only:
        # prntDebug('running2')
        job_ids = queue.job_ids
        for job_id in job_ids:
            # prntDebug('job_id2',job_id)
            job = queue.fetch_job(job_id)
            # prntDebug('job2',job)
            if job:
                # prntDebug('job.func_name',job.func_name)
                if job.func_name.endswith(func):
                    # prntDebug('cont3',job.kwargs.values(),job.args)
                    if arg in job.kwargs.values() or str(arg) in str(job.args):
                        # prntDebug('cont4 true')
                        found_jobs += 1
                        # return True
            if found_jobs >= job_count:
                prntDebug('return 4 true')
                return True
        
        try:
            scheduler = get_scheduler(queue.name, connection)
            # prnt('scheduler',scheduler)
            scheduled_jobs = scheduler.get_jobs()
            for job in scheduled_jobs:
                # prntDebug('job3',job)
                # prntDebug('job.func_name',job.func_name)
                if job.func_name.endswith(func):
                    if arg in job.kwargs.values() or str(arg) in str(job.args):
                        # prntDebug('cont5 true')
                        found_jobs += 1
                if found_jobs >= job_count:
                    prntDebug('return 5 true')
                    return True
        except Exception as e:
            prnt('exists in worker fail3633',str(e))
    # prntDebug('cont6')

    from django_rq import get_scheduler, get_queue
    from rq.job import Job

    # def check_job_status(job_id, queue_name='main'):
        # Get scheduler and queue

    scheduler = get_scheduler(queue.name)
    # queue = get_queue(queue.name)
    
    # Check if job is scheduled
    scheduled_jobs = list(scheduler.get_jobs())
    scheduled_job = next((job for job in scheduled_jobs if job.id == job_id), None)
    
    # if scheduled_job:
    #     print(f"Job {job_id} is scheduled.")
    # else:
    #     print(f"Job {job_id} is not scheduled.")
    # prntDebug('cont7')
    
    # Check if job is running
    running_jobs = queue.get_jobs()
    running_job = next((job for job in running_jobs if job.id == job_id), None)
    
    # if running_job:
    #     print(f"Job {job_id} is currently running.")
    # else:
    #     print(f"Job {job_id} is not running.")

    if found_jobs >= job_count:
        prntDebug('return 6 true')
        return True
    prntDebug('cont8 false')

    return False



def create_share_object(func, region, special, dt=now_utc(), iden=None):
    prnt('create_share_object', func, special, region, dt)
    from blockchain.models import DataPacket, send_for_validation
    log = None
    if iden:
        log = DataPacket.objects.filter(id=iden).first()
    if not log:

        job_dt = round_time(dt=dt, dir='down', amount='hour')
        job_iden = f'{func} - {region.id} - {dt_to_string(dt)}'
        log = DataPacket(func=f'scrape assignment - {func}')
        if iden:
            log.id = iden
        else:
            from utils.locked import hash_obj_id
            log.id = hash_obj_id(log, verify=False, specific_data=job_iden, return_data=False, model=None, version=None)
        log.created = job_dt
        log.Node_obj = get_self_node()
        log.data['func'] = func
        log.data['created'] = dt_to_string(job_dt)
        log.data['region_name'] = region.Name
        log.data['shareData'] = []
        log.Region_obj = region
    log.data['special'] = special
    log.save()
    try:
        # from utils.models import create_job
        if special == 'super':
            create_job(super_share, job_timeout=300, worker='low', clear_chrome_job=False, log=log.id)
        else:
            create_job(send_for_validation, job_timeout=300, worker='low', clear_chrome_job=False, log=log.id)
    except Exception as e:
        prnt('Error creating share object 457834', str(e)) 
    return log

def finishScript(log, gov=None, special=None, func=None, log_event=True, send_off=True):
    # from utils.models import is_id
    from blockchain.models import DataPacket, logEvent, return_test_result, send_for_validation
    if is_id(log):
        log = DataPacket.objects.filter(id=log).first()
    if not log:
        return None
    prnt('finishScript', log.data['func'], gov, special)
    if gov and isinstance(gov, models.Model):
        gov_id = gov.id
    else:
        gov_id = None
    if 'shareData' in log.data:
        r = len(log.data['shareData'])
        if not gov_id:
            gov_prefix = get_model_prefix('Government')
            for i in log.data['shareData']:
                if isinstance(i, str):
                    if i.startswith(gov_prefix):
                        gov = i
                        gov_id = i
                        break
                elif isinstance(i, models.Model):
                    if i.object_type == 'Government':
                        gov = i
                        gov_id = gov.id
                        break
    else:
        r = 'unknown'
    log.data['content_length'] = r
    do_save = False
    if gov_id:
        if 'gov_id' not in log.data or log.data['gov_id'] != gov_id:
            log.data['gov_id'] = gov_id
            do_save = True
    if 'special' in log.data:
        special = log.data['special']
        do_save = True
    if 'finished' not in log.data:
        log.data['finished'] = dt_to_string(now_utc())
        do_save = True
    if do_save:
        log.save()
    if log_event and r:
        logEvent(f'finishScript: {log.data["region_name"]} {log.data["func"]} -item count: {r}')
    if special == 'testing':
        return return_test_result(log)
    elif special == 'super':
        items, completed = super_share(log, gov, val_type=log.data['func'])
        return completed
    elif log.data['shareData']:
        # if worker:
        #     from utils.models import create_job
        #     create_job(send_for_validation, job_timeout=job_time, worker=worker, clear_chrome_job=False, log=log.id, gov=gov)
        if send_off:
            return send_for_validation(log, gov)
    else:
        log.delete()
    return None




# only used one in accounts.views
def check_dataPacket(obj):
    from blockchain.models import Blockchain
    # from posts.models import has_field
    if has_field(obj, 'blockchainId'):
        chainId = obj.blockchainId
    elif has_field(obj, 'blockchainType'):
        chain = Blockchain.objects.filter(genesisType=obj.blockchainType, genesisId=obj.id).first()
        if chain:
            chainId = chain.id
        else:
            chainId = 'All'
    else:
        chainId = 'All'
    dataPacket = get_latest_dataPacket(chainId)
    if not obj:
        return False
    elif obj.id in dataPacket.data:
        return True
    else:
        return False






def has_field(model, field_name, exclude_method=False):
    if exclude_method:
        try:
            return any([f.name for f in model._meta.get_fields() if f.name == field_name])
        except Exception as e:
            prnt('err 6892',str(e))
    return hasattr(model, field_name)

def has_method(model, method_name):
    return callable(getattr(model, method_name, None))


def get_model_prefix(obj):
    # returns 'sta', 'vot' etc.
    if isinstance(obj, dict):
        return get_app_name(obj['object_type'], return_prefix=True)
    elif isinstance(obj, str):
        return get_app_name(obj, return_prefix=True)
    else:
        return get_app_name(obj.object_type, return_prefix=True)
    
def get_pointer_type(iden):
    # prntDebug('---get_pointer Type')
    if isinstance(iden, models.Model):
        return iden.object_type
    elif isinstance(iden, dict):
        return iden['object_type']
    elif isinstance(iden, str) and get_app_name(model_name=iden, am_i_model=True) == iden:
        return iden
    if not iden or 'So' not in iden:
        return None
    x = iden.find('So')
    prefix = iden[:x]
    return get_app_name(prefix=prefix) 

def get_chain_type(iden):
    # prnt('get_chain_type Type')
    if isinstance(iden, models.Model):
        iden = iden.id
        if has_field(iden, 'blockchainType'):
            return iden.blockchainType
    elif isinstance(iden, dict):
        iden = iden['id']
        if 'blockchainType' in iden:
            return iden['blockchainType']
    if not iden or 'So' not in iden:
        return None
    m = get_model(iden)()
    if has_field(m, 'blockchainType'):
        return m.blockchainType
    return None

def get_chainName(obj):
    if obj.object_type == 'Region':
        return obj.Name
    elif obj.object_type == 'User':
        return obj.display_name
    elif obj.object_type == 'Wallet':
        return obj.User_obj.display_name
    elif obj.object_type == 'Sonet':
        return 'Sonet'
    elif has_field(obj, 'blockchainId'):
        from blockchain.models import Blockchain
        chain = Blockchain.objects.filter(id=obj.blockchainId).first()
        if chain:
            return chain.genesisName
    return None

def seperate_by_type(obj_list, include_only={}, exclude={}):
    prntDebug('seperate_by_type')
    prntDebug('obj_list',obj_list)
    prntDebug('include_only',include_only)
    prntDebug('exclude',exclude)
    # from blockchain.models import data_sort_priority
    obj_types = {}
    models = {}
    skipping_models = []
    if not obj_list:
        return obj_types
    obj_list = sorted(obj_list, key=data_sort_priority)
    for i in obj_list:
        skip = False
        objType = None
        value = None
        if is_id(i):
            objType = get_pointer_type(i)
            value = i
            if objType not in models:
                model = get_model(objType)
                models[objType] = model
            else:
                model = models[objType]
        elif isinstance(i, models.Model):
            objType = i.object_type
            value = i.id
            model = i
        if value and objType not in skipping_models:
            if objType in obj_types:
                obj_types[objType].append(value)
            else:
                if include_only:
                    if 'has_field' in include_only:
                        for field in include_only['has_field']:
                            if not has_field(model, field):
                                skip = True
                    if not skip and 'has_method' in include_only:
                        for method in include_only['has_method']:
                            if not has_method(model, method):
                                skip = True
                if not skip and exclude:
                    if 'fields' in exclude:
                        if isinstance(exclude['fields'], dict):
                            for field_name, value in exclude['fields'].items():
                                if has_field(model, field_name) and getattr(model, field_name) == value:
                                    skip = True
                                    break
                        if isinstance(exclude['fields'], list):
                            for field in exclude['fields']:
                                if has_field(model, field):
                                    skip = True
                                    break
                if skip:
                    skipping_models.append(objType)
                if objType and value and not skip:
                    if objType in obj_types:
                        obj_types[objType].append(value)
                    else:
                        obj_types[objType] = [value]
    return obj_types

def is_locked(obj):
    # prnt('check is_locked')
    try:
        if has_field(obj, 'validation_error') and obj.validation_error:
            return False
        if has_field(obj, 'Block_obj') and obj.Block_obj and obj.Block_obj.validated:
            return True
        if has_field(obj, 'Validator_obj') and obj.Validator_obj and obj.Validator_obj.is_valid:
            return True
        if has_field(obj, 'ReceiverBlock_obj'):
            if obj.ReceiverBlock_obj and obj.ReceiverBlock_obj.validated:
                return True
            if obj.SenderBlock_obj and obj.SenderBlock_obj.validated:
                return True
        if has_field(obj, 'validated') and obj.validated:
            return True
    except Exception as e:
        prnt('is_locked fail9673945',str(e))
        from blockchain.models import logError
        from utils.locked import convert_to_dict
        logError(str(e), code='9673945', func='is_locked', extra={'dict':str(convert_to_dict(obj))[:500]})
    # prnt('not locked')
    return False


def parse_input(value):
    try:
        if str(value) == '[]':
            return []
    except:
        pass
    try:
        import ast
        parsed_value = ast.literal_eval(value)
        return parsed_value
    except:
        pass
    try:
        parsed_value = json.loads(value)
        return parsed_value
    except:
        pass
    return value

def is_id(obj):
    if isinstance(obj, str) and any(obj[i:i+2] == 'So' and obj[i+2:].isalnum() and 12 <= len(obj[i+2:]) <= 22 for i in range(len(obj) - 1)):
    # if isinstance(obj, str) and 'So' in obj and any(char.isdigit() for char in obj):
        return True
    return False


def get_model_fields(obj=None):
    # prnt('get_model_fields')
    # for use when updating model fields
    model_list = get_app_name(return_model_list=True)
    # prntn('continue here')
    # prnt('model_list',model_list)
    # for v in model_list:
    #     prnt('v',v)
    # prnt()
    for key in model_list:
        # prnt('key',key)
        if key != 'apps':
            model = get_model(key)
            obj = model() 
            objFields = {'object_type':obj.object_type} # latestModel not included
            if has_field(model,'is_modifiable'):
                objFields['is_modifiable'] = obj.is_modifiable
            if has_field(model,'blockchainType'):
                objFields['blockchainType'] = obj.blockchainType
            if has_field(model,'secondChainType'):
                objFields['secondChainType'] = obj.secondChainType
            if has_field(model,'iden_length'):
                objFields['iden_length'] = obj.iden_length
            from django.forms.models import model_to_dict
            objFields.update(model_to_dict(obj))
            # prnt('obj',obj)
            # prnt('obj.get_version_fields()',obj.get_version_fields())
            if has_method(obj, 'get_version_fields'):
                fields = obj.get_version_fields()
            else:
                fields = {}
            if objFields != fields:
                prnt(key)
                # prnt('old',fields)
                prnt(f' return {objFields}')
                prnt()


_appInfo = None

def get_app_info(rerun=False):
    # prnt('get_app_info')
    global _appInfo
    if _appInfo is None or rerun:
        # prnt('running 1')
        import importlib
        from django.conf import settings
        from blockchain.models import Plugin
        app_dict = {'apps':{}}
        plugins = Plugin.objects.exclude(Block_obj=None)
        if plugins:
            # supported_apps = [p.app_name for p in plugins]
            # plugin_prefixes = {p.app_name:{'plugin_prefix':p.plugin_prefix,'model_prefixes':p.model_prefixes} for p in plugins}
            for plug in plugins:
                app = plug.app_name
                app_dict['apps'][plug.app_name] = []
                for key, value in plug.model_prefixes.items():
                    if key not in app_dict['apps'][plug.app_name]:
                        app_dict['apps'][plug.app_name].append(key)
                    # if plug.app_name in plugin_prefixes and plugin_prefixes[plug.app_name]:
                    if plug.plugin_prefix and plug.plugin_prefix != '0':
                        text = f'{plug.plugin_prefix}{value}'
                    else:
                        text = f'{value}'
                    app_dict[key] = text
            _appInfo = app_dict
        else:
            from blockchain.models import default_apps
            supported_apps = default_apps
            plugin_prefixes = {}

            for app in settings.INSTALLED_APPS:
                try:
                    # prnt('app_config.name',app)
                    if app in supported_apps:
                        models_module = importlib.import_module(f"{app}.models")
                        if hasattr(models_module, "model_prefixes"):
                            prefixes = getattr(models_module, "model_prefixes")
                            if isinstance(prefixes, dict):
                                app_dict['apps'][app] = []
                                for key, value in prefixes.items():
                                    if key not in app_dict['apps'][app]:
                                        app_dict['apps'][app].append(key)
                                    if app in plugin_prefixes and plugin_prefixes[app]:
                                        text = f'{plugin_prefixes[app]}{value}'
                                    else:
                                        text = f'{value}'
                                    app_dict[key] = text

                except ModuleNotFoundError:
                    continue
                except Exception:
                        continue
        if plugins:
            _appInfo = app_dict
        else:
            # prnt('app_dict',app_dict)
            return app_dict

            # return app_dict

                # return model_prefixes_list
            # prnt('loading apps')
            # prefixes = get_all_model_prefixes()
            # prnt()
            # for d in prefixes:
            #     prnt(d)

                
            # this func needs to be rerun when new plugin committed to block successfully
            # if no plugins found above, get apps accounts, blockchain, posts
        

            # from django.apps import apps
            # import importlib

            # for app_config in apps.get_app_configs():
            #     try:
            #         importScript = f'scrapers.{country_name}.{provState_name}.{name}'
            #         # Try to import the module where `myDict` is expected (e.g., in app/my_dict.py)
            #         module = importlib.import_module(f"{app_config.name}.model_prefixes")
                    
            #         # Try to get the `myDict` variable from that module
            #         if hasattr(module, "myDict"):
            #             all_my_dicts[app_config.name] = getattr(module, "myDict")
            #     except ModuleNotFoundError:
            #         # Skip if the app doesn't have my_dict.py
            #         continue
            #     except Exception as e:
            #         print(f"Error loading myDict from {app_config.name}: {e}")
    # prnt('_appInfo',_appInfo)
    return _appInfo



# contains model id prefixes, would be better under models themselves
def get_app_name(model_name=None, prefix=None, return_prefix=False, return_model_list=False, am_i_model=False):
    # prnt('get_app_name',model_name,prefix,return_prefix)
    models = {'Sonet':{'prefix':'oh','app_name':'blockchain'},'User':{'prefix':'usr','app_name':'accounts'},'UserData':{'prefix':'udat','app_name':'accounts'},
            'UserPubKey':{'prefix':'upk','app_name':'accounts'},'UserVerification':{'prefix':'uver','app_name':'accounts'},'SuperSign':{'prefix':'sup','app_name':'accounts'},
            'UserTransaction':{'prefix':'utra','app_name':'transactions'},'Wallet':{'prefix':'wal','app_name':'transactions'},'Notification':{'prefix':'not','app_name':'accounts'},
            'UserNotification':{'prefix':'unot','app_name':'accounts'},'UserAction':{'prefix':'act','app_name':'accounts'},'UserVote':{'prefix':'uvot','app_name':'accounts'},
            'UserSavePost':{'prefix':'usvp','app_name':'accounts'},'UserFollow':{'prefix':'ufol','app_name':'accounts'},'CustomFCM':{'prefix':'fcm','app_name':'accounts'},
            'DataPacket':{'prefix':'dat','app_name':'blockchain'},'Node':{'prefix':'nod','app_name':'blockchain'},'NodeReview':{'prefix':'nrev','app_name':'blockchain'},
            'Block':{'prefix':'blo','app_name':'blockchain'},'Validator':{'prefix':'val','app_name':'blockchain'},'Blockchain':{'prefix':'cha','app_name':'blockchain'},
            'EventLog':{'prefix':'elog','app_name':'blockchain'},
            'Government':{'prefix':'gov','app_name':'legis'},'Agenda':{'prefix':'agn','app_name':'legis'},'Bill':{'prefix':'bil','app_name':'legis'},'BillText':{'prefix':'btxt','app_name':'legis'},
            'Meeting':{'prefix':'mtg','app_name':'legis'},'Statement':{'prefix':'sta','app_name':'legis'},'Committee':{'prefix':'com','app_name':'legis'},
            'Motion':{'prefix':'mot','app_name':'legis'},'Vote':{'prefix':'vot','app_name':'legis'},'Election':{'prefix':'ele','app_name':'legis'},
            'Party':{'prefix':'prt','app_name':'legis'},'Person':{'prefix':'per','app_name':'legis'},'District':{'prefix':'dis','app_name':'legis'},
            # 'Recap':{'prefix':'rec','app_name':'legis'},
            'Post':{'prefix':'pst','app_name':'posts'},'Update':{'prefix':'upd','app_name':'posts'},'Spren':{'prefix':'spr','app_name':'posts'},
            'GenericModel':{'prefix':'gen','app_name':'posts'},'Keyphrase':{'prefix':'key','app_name':'posts'},'KeyphraseTrend':{'prefix':'kytr','app_name':'posts'},
            'Region':{'prefix':'reg','app_name':'posts'}
    }
    models = get_app_info()
    if model_name and not return_prefix and not am_i_model:
        # prnt('here1',model_name)
        for app_name in models['apps']:
            # prnt('app_name',app_name)
            if model_name in models['apps'][app_name]:
                return app_name
        # if model_name in models:
        #     app_name = models[model_name]['app_name']
        #     return app_name
    elif model_name and return_prefix:
        if model_name in models:
            # prefix = models[model_name]['prefix']
            return models[model_name]
        else:
            prnt('hey qhat, model_name:',model_name)
            prnt(models)
    elif prefix:
        for m in models:
            if models[m] == prefix:
                return m
    # elif return_chain_type:
    #     prefix = prefix[:3]
    #     for m in models:
    #         if prefix in models[m]['prefix']:
    #             return m
    elif return_model_list:
        return models
    elif am_i_model and model_name in models['apps']:
        return model_name
    # prnt('None resp',model_name,prefix,return_prefix)
    return ''

def get_model(obj_type):
    # prntDebug('-get_model', obj_type)
    if not obj_type or not isinstance(obj_type, str):
        return None
    if any(char.isdigit() for char in obj_type):
        obj_type = get_pointer_type(obj_type)
    app_name = get_app_name(obj_type)
    if app_name and obj_type:
        from django.apps import apps
        return apps.get_model(app_name, obj_type)
    return None

def dynamic_bulk_create(model_name=None, model=None, items=[], return_items=False):
    prntDebug('dynamic_bulk_create', model_name)
    from blockchain.models import logError, logEvent
    if not model:
        model = get_model(model_name)
    if not model:
        return None
    if model.object_type == 'Post':
        model_manager = 'all_objects'
    else:
        model_manager = 'objects'
    try:
        getattr(model, model_manager).bulk_create(items)
    except Exception as e:
        prnt('d create err:',model_name,str(e))
        for i in items:
            saved, err = compensate_save(i, model, return_err=True)
            if not saved:
                logError(err, code='5689', func='dynamic_bulk_create', extra={'iden':i.id})
    if return_items:
        return items
    return None

def dynamic_bulk_update(model_name=None, model=None, update_data={}, items_field_update=[], items=[], return_items=False, **kwargs):
    prntDebug('dynamic_bulk_update',model_name, model, len(update_data), len(items))
    # update_data requires kwargs - performs lookup - will not return items
    # rest is interchangable
    # not receiving update_data or items_field_update will update entire model
    # must receive model_name or model
    from blockchain.models import logError, logEvent
    # logEvent(f'-dynamic_bulk_update model_name:{model_name} update_fields:{update_data} items_field_update:{items_field_update} items:{str(items)[:500]} kwargs:{kwargs}')
    if not model_name and not model:
        return None
    err = 'A'
    if not model:
        model = get_model(model_name)
    if not model:
        return None
    if not update_data and not items_field_update:
        items_field_update = [
            field.name for field in model._meta.get_fields()
            if field.concrete and not field.auto_created and field.name != 'id'
        ]
    if model.object_type == 'Post':
        err = err + 'a'
        model_manager = 'all_objects'
    else:
        err = err + 'b'
        model_manager = 'objects'
    err = err + str(len(items))
    try:
        err = err + 'B'
        if update_data and kwargs:
            err = err + 'C'
            update_data['updated_on_node'] = now_utc()
            getattr(model, model_manager).filter(**kwargs).update(**update_data)
            # model.objects.filter(**kwargs).update(**update_data)
            items = 'N/A'
            err = err + 'fini1'
        elif items_field_update:
            if 'updated_on_node' not in items_field_update:
                items_field_update.append('updated_on_node')
                now = now_utc()
                for i in items:
                    i.updated_on_node = now
            err = err + 'E'
            # logEvent(f'dynamic_bulk_update---{items}')
            if not items and kwargs:
                err = err + 'e'
                items = getattr(model, model_manager).filter(**kwargs)
            if items:
                err = err + 'F'
                try:
                    err = err + str(len(items))
                    err = err + 'f'
                    # logEvent(f'dynamic_bulk_update22222---{items}')
                    getattr(model, model_manager).bulk_update(items, items_field_update)
                    err = err + 'fini2'
                except Exception as e:
                    err = err + 'G'
                    if compensate_save_handle(str(e)):
                    # if compensate_save(str(e), model, create_obj=False, context={'from':'dynamic_bulk_update1','err':str(err),'model':str(model),'dict':[convert_to_dict(q) for q in items[:20]]}):
                        err = err + 'I'
                        bulk_update_fields_no_foreignKey = [
                            field.name for field in model._meta.get_fields()
                            if field.concrete and not field.auto_created and field.name not in ['id', 'is_staff', 'password', 'groups', 'user_permissions'] and '_obj' not in field.name
                        ]
                        bulk_update_fields_only_foreignKey = [
                            field.name for field in model._meta.get_fields()
                            if field.concrete and not field.auto_created and field.name not in ['id', 'is_staff', 'password', 'groups', 'user_permissions'] and '_obj' in field.name
                        ]
                        logError(str(e), code='947262', func='dynamic_bulk_update', extra={'bulk_update_fields_no_foreignKey':bulk_update_fields_no_foreignKey,'bulk_update_fields_only_foreignKey':bulk_update_fields_only_foreignKey})
                        from django.db import transaction
                        err = err + 'J'
                        with transaction.atomic():
                            err = err + 'K'
                            getattr(model, model_manager).bulk_update(items, bulk_update_fields_no_foreignKey)
                            err = err + 'L'
                            getattr(model, model_manager).bulk_update(items, bulk_update_fields_only_foreignKey)
                            err = err + 'finixxx'
                            # logError('passed', code='4834764', func='dynamic_bulk_update')

        # logEvent(f'dynamic_bulk_update complete r: {err}')
        if return_items:
            return items
        return None
    except Exception as e:
        err = err + 'H'
        from utils.locked import convert_to_dict
        if compensate_save_handle(str(e), context={'from':'dynamic_bulk_update2','err':str(err),'model':str(model),'dict':[convert_to_dict(q) for q in items[:20]]}):
            return dynamic_bulk_update(model=model, items_field_update=items_field_update, update_data=update_data, items=items, return_items=return_items, **kwargs)
        return None


def compensate_save(obj, model, return_err=False, context=None, *args, **kwargs):
    from blockchain.models import logError
    if context:
        from utils.locked import convert_to_dict
        logError('context', code='5736', func='compensate_save', extra={'model':str(model),'obj':str(convert_to_dict(obj))[:500],'context':context})
    try:
        super(model, obj).save(*args, **kwargs)
        if return_err:
            return True, None
        return True
    except Exception as e:
        # logError(e, code='97532', func='compensate_save', extra={'obj':str(convert_to_dict(obj))[:500]})
        if compensate_save_handle(str(e), create_obj=True, context=obj):
            try:
                super(model, obj).save(*args, **kwargs)
                if return_err:
                    return True, None
                return True
            except Exception as e:
                logError(e, code='027431', func='compensate_save', extra={'iden':obj.id})
        if return_err:
            return False, str(e)
        return False



def compensate_save_handle(err, create_obj=True, context=None):
    from blockchain.models import logError, logMissing
    err = str(err)
    if 'violates foreign key constraint' in err:
        x = err.find('DETAIL:  Key (')+len('DETAIL:  Key (')
        z = err[x:].find('_obj')
        q = x+z
        model_name = err[x:q]
        y = err[q:].find('_id)=(')+len('_id)=(')
        v = err[q+y:].find(') is not present')
        iden = err[q+y:q+y+v]
        if not iden:
            prnt('iden not found in compensate save')
            return False
        check_result = check_missing_data(iden, retrieve_missing=True, log_missing=True, downstream_worker=False)
        prnt('check_result',check_result)
        if check_result and 'found_idens' in check_result and iden in check_result['found_idens']:
            return True
        elif create_obj:
            prnt('create obj')
            logMissing(iden)
            prnt('go creation')
            prnt(iden)
            obj = create_dynamic_model(iden, id=iden)
            prnt('c obj',obj)
            obj.save()
            prnt('created obj', obj)
        logError(err, code='78644', func='compensate_save_handle solved', extra={'iden':iden,'model_name':model_name})
        return True
    elif 'bulk_update() can only be used with concrete fields' in err:
        logError(err, code='4689', func='compensate_save_handle')
        return True 
    else:
        if context:
            from utils.locked import convert_to_dict
            logError(err, code='77543', func='compensate_save_handle skipped1', extra=str(convert_to_dict(context))[:500])
        else:
            logError(err, code='4578', func='compensate_save_handle skipped2', extra=context)

    # django.db.utils.IntegrityError: insert or update on table "blockchain_block" violates foreign key constraint "blockchain_block_Transaction_obj_id_3955a2d5_fk_accounts_"
    # DETAIL:  Key (Transaction_obj_id)=(utraSo23821f7a02d44806b50dcc2aa453a482) is not present in table "accounts_usertransaction".
    return False


def get_dynamic_model(model_name, list=False, order_by=None, exclude={}, **kwargs):
    # Post model uses special model_manager, only returns validated objs normally
    prntDebug(f'get_dynamic_model:{model_name} exclude:{exclude}, list:{list}, order_by:{order_by},')
    model = None
    if isinstance(model_name, str):
        model = get_model(model_name)
    elif isinstance(model_name, models.Model) or issubclass(model_name, models.Model):
        model = model_name
    if not model:
        return [] if list else None
    creation_fields = ['created','created_dt']
    if order_by and order_by in creation_fields:
        for f in creation_fields:
            if has_field(model, f):
                order_by = f
    try:
        del kwargs['object_type']
    except:
        pass
    if list:
        if list == True:
            try:
                if order_by:
                    return model.objects.filter(**kwargs).exclude(**exclude).order_by(order_by)
                else:
                    return model.objects.filter(**kwargs).exclude(**exclude)
            except Exception as e:
                prntDebug('fail48476', str(e))
                return []
        else:
            try:
                if order_by:
                    return model.objects.filter(**kwargs).exclude(**exclude).order_by(order_by)[list[0]:list[1]]
                else:
                    return model.objects.filter(**kwargs).exclude(**exclude)[list[0]:list[1]]
            except model.DoesNotExist:
                return []
            
    else:
        try:
            if order_by:
                return model.objects.filter(**kwargs).exclude(**exclude).order_by(order_by).first()
            else:
                return model.objects.filter(**kwargs).exclude(**exclude).first()
        except Exception as e:
            # prnt(str(e))
            return None

def create_dynamic_model(model_name, **kwargs):
    # prnt('create_dynamic_model',model_name)
    model = get_model(model_name)
    try:
        del kwargs['object_type']
    except:
        pass
    obj = model(**kwargs)
    return obj

def get_or_create_model(model_name, return_is_new=False, **kwargs):
    # prnt('get_or_create_model')
    is_new = False
    obj = get_dynamic_model(model_name, **kwargs)
    if not obj:
        try:
            obj = create_dynamic_model(model_name, **kwargs)
            is_new = True
        except Exception as e:
            prnt('fail7853189',str(e))
    elif obj:
        if has_field(obj, 'Validator_obj'):
            if not obj.Validator_obj or not obj.Validator_obj.is_valid:
                prnt('get_create_is_new',obj)
                is_new = True
    if return_is_new:
        return obj, is_new
    return obj

def get_model_and_update(model_name, dt=None, obj=None, new_model=True, **kwargs):
    # prnt('get model and update', model_name)
    from posts.models import Update
    if not obj and not kwargs:
        return None, None, None
    if not obj:
        obj = get_dynamic_model(model_name, **kwargs)
        if obj and has_field(obj, 'Validator_obj'):
            if obj.Validator_obj:
                new_model = False
        if not obj:
            obj = create_dynamic_model(model_name, **kwargs)
    u = Update(pointerId=obj.id)
    update = u.create_next_version(obj=obj)
    return obj, update, new_model

def save_and_return(obj, update, log):
    # prntn('-----save and return, obj',obj, 'update:',update)
    func = log.data['func']
    created = string_to_dt(log.data['created'])
    def confer(obj):
        field_names = [field.name for field in obj._meta.fields]
        query_kwargs = {field: getattr(obj, field) for field in field_names}
        match = get_dynamic_model(obj.object_type, list=False, **query_kwargs)
        return False if match else True
    
    new_obj = True
    if is_locked(obj):
        prnt('forbidden save 482674', obj)
        new_obj = False
    elif has_field(obj, 'Validator_obj'):
        if obj.Validator_obj == None:
            new_obj = True
        else:
            new_obj = False
    elif has_field(obj, 'Block_obj') and obj.Block_obj:
        new_obj = False
    # elif has_field(obj, 'Block_obj') and obj.Block_obj == None:
    #     new_obj = confer(obj)
    elif has_field(obj, 'proposed_modification'):
        if obj.id != '0':
            new_obj = False
        obj = obj.propose_modification()
    # else:
    #     new_obj = confer(obj)
    if new_obj:
        if func:
            obj.func = func
        obj.created = created
        if obj.id != '0' and has_method(obj, 'get_hash_to_id'):
            from utils.locked import hash_obj_id
            hashed_id = hash_obj_id(obj)
            if obj.id != hashed_id:
                from blockchain.models import logEvent
                logEvent(f'changed_id: old_id{obj.id}, new_id:{hashed_id}')
                obj.id = hashed_id
        if has_method(obj, 'update_data'):
            obj.update_data()
        else:
            obj.save()
        if obj.id not in log.data['shareData']:
            log.updateShare(obj)

    # skipUpdate = ['Region', 'District', 'Party', 'Person'] # models not locked to chain - dont require update object
    if has_field(obj, 'Block_obj'):
        if update:
            if update.data != {}:
                has_data = True
            else:
                has_data = False
                for f in update._meta.fields:
                    if '_obj' in str(f.name) or str(f.name) == 'data':
                        attr = getattr(update, f.name)
                        if not attr or attr == {}:
                            pass
                        else:
                            has_data = True
            if has_data:
                update.pointerId = obj.id 
                update.Region_obj = obj.Region_obj
                if not update.DateTime and has_field(obj, 'DateTime'):
                    update.DateTime = obj.DateTime
                elif not update.DateTime and has_field(obj, 'created'):
                    update.DateTime = obj.created
                # if not update.DateTime and has_field(obj, 'added'):
                #     update.DateTime = obj.added
                if func:
                    update.func = func
                update.created = created

                update, u_is_new = update.save_if_new()
                if u_is_new and not is_locked(update):
                    log.updateShare(update)

    return obj, update, new_obj, log

def superDelete(obj, force_delete=False):
    prnt('superdelete',obj)
    if has_field(obj, 'Block_obj') and not obj.Block_obj or has_field(obj, 'Block_obj') and obj.Block_obj.validated == False or force_delete:
        from posts.models import GenericModel, Update, Post, Keyphrase
        try:
            gos = GenericModel.objects.filter(pointerId=obj.id)
            for g in gos:
                g.delete(force_delete=force_delete)
        except:
            pass
        try:
            updates = Update.objects.filter(pointerId=obj.id)
            for u in updates:
                u.delete()
        except:
            pass
        try:
            p = Post.all_objects.filter(pointerId=obj.id).first()
            p.delete()
        except:
            pass
        try:
            keys = Keyphrase.objects.filter(pointerId=obj.id)
            for k in keys:
                k.delete()
        except:
            pass
        try:
            from accounts.models import Notification
            notifications = Notification.objects.filter(pointerId=obj.id)
            for n in notifications:
                n.delete(force_delete=force_delete)
        except:
            pass
        model = get_model(obj.object_type)
        super(model, obj).delete()
        prnt('deleted')
        return True
    return False




def sync_model(xModel, jsonContent, skip_fields=[], do_save=True, node_block_data={}, force_sync=False):
    # from utils.models import 
    from utils.locked import verify_obj_to_data, convert_to_dict, get_node_assignment

    # prntDebug(jsonContent)
    proceed_to_sync = False
    updatedDB = False
    try:
        received_data = json.loads(jsonContent)
    except:
        received_data = jsonContent
    iden = 'unknown'
    try:
        if 'id' in received_data:
            iden = received_data['id']
    except:
        pass
    prnt('**syncing',iden, xModel)
    # if 'added' in received_data:
    #     dt = received_data['added']
    if 'created' in received_data:
        dt = received_data['created']
    # elif 'created_dt' in received_data:
    #     dt = received_data['created_dt']
    else:
        dt = now_utc()
    is_valid, user = verify_obj_to_data(xModel, received_data, return_user=True)
    if not is_valid:
        prnt('is_not_validA:',is_valid)
        prntDebug('xmodel',str(convert_to_dict(xModel))[:500],'\ndata',str(received_data)[:500])
        return xModel, is_valid, False
    try:
        if is_locked(xModel):
            return xModel, is_valid, False
        if not force_sync:
            if has_field(xModel, 'last_updated') and xModel.last_updated and 'last_updated' in received_data:
                if not isinstance(xModel.last_updated, datetime.datetime):
                    last_updated = string_to_dt(xModel.last_updated)
                else:
                    last_updated = xModel.last_updated
                if 'Validator_obj' in received_data and received_data['Validator_obj'] or 'Block_obj' in received_data and received_data['Block_obj']:
                    pass
                elif string_to_dt(received_data['last_updated']) <= last_updated:
                    prnt('previously updated - skipping sync')
                    return xModel, is_valid, False

    except Exception as e:
        prnt('fail130584',str(e))
        pass
    userTypes = ['User', 'UserPubKey', 'Wallet', 'Transaction', 'UserVote', 'SavePost', 'Follow']
    if is_valid:  
        if user.is_superuser and user.assess_super_status(dt=dt):
            proceed_to_sync = True
        elif xModel.object_type == 'Spren' or xModel.object_type == 'SprenItem':
            # get list of Nodes with ai_capable, xModel.publicKey should match node.User_obj.get_keys()
            pass
        # elif not has_field(xModel, 'added'):
        elif xModel._meta.app_label.lower() not in ['posts', 'legis']:
            # not task assigned object
            proceed_to_sync = True
        if not proceed_to_sync:
            prnt('x2 not yet good')
            if 'func' in received_data and received_data['func'].lower() == 'super' and received_data['publicKey'] in get_superuser_keys(data=received_data):
                proceed_to_sync = True
            elif received_data['object_type'] == 'Validator' and received_data['validatorType'] == 'Block':
                proceed_to_sync = True
            else:
                # verify which nodes were assigned to scrape and validate this data, should verify creatorNode as well as validatorNode are correct - currently only checks validatorNode
                
                prnt('node_block_data',node_block_data)
                creator_nodes, validator_nodes = get_node_assignment(dt=received_data['created'], chainId=received_data['blockchainId'], func_name=received_data['func'], node_block_data=node_block_data, strings_only=False)
                # creator_nodes, validator_nodes = get_scraping_order(dt=received_data['created'], chainId=received_data['blockchainId'], func_name=received_data['func'], node_block_data=node_block_data, strings_only=False)
                prnt('validator_nodes',validator_nodes)
                if received_data['object_type'] == 'Validator':
                    prnt('p1',received_data['CreatorNode_obj'])
                    if received_data['CreatorNode_obj'] in any(v.id for v in validator_nodes):
                        prnt('p2')
                        proceed_to_sync = True
                elif 'validatorNodeId' in received_data and received_data['validatorNodeId'] in any(v.id for v in validator_nodes):
                    if 'proposed_modification' in received_data and user.id in any(v.User_obj.id for v in validator_nodes):
                        proceed_to_sync = True
                    else:
                        from blockchain.models import Node
                        creator_node = Node.objects.filter(id=received_data['creatorNodeId']).first()
                        if user.id in any(c.User_obj.id for c in creator_nodes):
                            proceed_to_sync = True
                elif received_data['publicKey'] in get_superuser_keys(data=received_data):
                    # reduntant
                    proceed_to_sync = True

        if proceed_to_sync:
            prntDebug('proceed_to_sync...')
            xModel, updatedDB = set_model_attr(xModel, received_data, user, dt, skip_fields=skip_fields)
            if not updatedDB:
                prnt('obj not updated')
            else:
                # from blockchain.models import get_signing_data
                # prnt('sign_data',get_signing_data(xModel))
                if not verify_obj_to_data(xModel, xModel, record_error=False):
                    prnt('failed re verification',str(received_data)[:300])
                    updatedDB = False
                    proceed_to_sync = False

                else:
                    prnt('-xModel sync, attempt save')
                    if has_field(xModel, 'Block_obj'):
                        xModel.Block_obj = None
                    if has_field(xModel, 'validated'):
                        xModel.validated = None
                    if has_field(xModel, 'blockchainType') and xModel.blockchainType == xModel.object_type:
                        chain, xModel, secondChain = find_or_create_chain_from_object(xModel)
                        if chain and has_field(xModel, 'blockchainId') and not xModel.blockchainId:
                            xModel.blockchainId = chain.id
                    if do_save:
                        if has_method(xModel, 'save_if_new'):
                            xModel, is_new = xModel.save_if_new()
                        else:
                            xModel.save()
                        prnt('-sync_model saved',xModel)
                    else:
                        prnt('do not save')
    prnt('-return sync:',xModel, proceed_to_sync, updatedDB, is_valid)
    return xModel, proceed_to_sync, updatedDB

def sync_and_share_object(obj, received_json):
    # sync and share user created objs. ie: User, UserVote, SavePost, Node
    try:
        data = json.loads(received_json)
    except:
        data = received_json
    obj, valid_obj, updatedDB = sync_model(obj, data)
    # prnt('sync/share2',obj, valid_obj,updatedDB)
    if valid_obj and updatedDB:
        share_with_network(obj)
    return obj, valid_obj

def set_model_attr(obj, data, user=None, dt=None, skip_user_check=False, skip_fields=[]):
    # from blockchain.models import sort_dict
    import decimal
    from django.contrib.contenttypes.models import ContentType
    from utils.locked import sort_dict
    prnt('set_model_attr',obj)
    prntDebug('user',user)
    updatedDB = False
    fields = obj._meta.fields
    debug = False
    if debug:
        prnt('fields',fields)
        prnt('data',data)
    def extract_user(obj):
        prnt('extract_user')
        user = None
        if not user:
            prnt('1')
            if has_field(obj, 'User_obj'):
                prnt('2')
                user = obj.User_obj
            elif has_field(obj, 'Node_obj'):
                prnt('3')
                user = obj.Node_obj.User_obj
            elif has_field(obj, 'CreatorNode_obj'):
                prnt('4')
                user = obj.CreatorNode_obj.User_obj
            elif has_field(obj, 'Super_User_obj'):
                prnt('5')
                user = obj.Super_User_obj
        if not user:
            prnt('6')
            # from blockchain.models import get_user
            iden = data['id']
            pubKey = data['publicKey']
            prnt('iden',iden)
            prnt('pubKey',pubKey)
            if data['object_type'] == 'User':
                prnt('2')
                user = get_user(user_id=iden)
            if not user:
                prnt('8')
                user = get_user(public_key=pubKey)
        return user
    superFields = ['is_supported', 'isVerified', 'is_superuser', 'is_staff', 'is_admin', 'fcm_capable', 'ai_capable', 'validated']
    for f in fields:
        try:
            if f.name not in data:
                if debug:
                    prnt('skip',f.name)
            elif f.name not in skip_fields:
                if debug:
                    prnt('sync:',f.name, data[f.name])
                if f.name in superFields:
                    if not skip_user_check and not user:
                        user = extract_user(obj)
                    prntDebug('user',user)
                    if not skip_user_check and user and user.assess_super_status(dt=dt):
                        if debug:
                            prnt('super')
                        if str(getattr(obj, f.name)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, data[f.name])
                    else:
                        if debug:
                            prnt('super pass 95684')
                        attr = getattr(obj, f.name)
                        setattr(obj, f.name, attr)
                    
                else:
                    if str(data[f.name]) == 'None':
                        if getattr(obj, f.name) != None:
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, None)
                    elif str(data[f.name]).lower() == 'true' or str(data[f.name]).lower() == 'false':
                        if str(getattr(obj, f.name)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, data[f.name])
                    elif '_obj' in str(f.name):
                        if debug:
                            prnt('is _obj')
                        id_field = str(f.name) + '_id'
                        if not getattr(obj, id_field) and data[f.name] or str(getattr(obj, id_field)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                try:
                                    prnt('--UDP:',str(getattr(obj, id_field)), str(data[f.name]))
                                except Exception as e:
                                    prnt(str(e))
                        setattr(obj, id_field, data[f.name])
                    elif f.__class__.__name__ == 'ArrayField' or isinstance(data[f.name], list) or '_array' in f.name:
                        if debug:
                            prnt('is array or list')
                        if str(sort_dict(getattr(obj, f.name))) != str(sort_dict(data[f.name])):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(sort_dict(getattr(obj, f.name))), str(data[f.name]))
                        setattr(obj, f.name, data[f.name])
                    elif f.name == 'pointerKey':
                        # pointer = get_dynamic_model(data['pointerId'], id=data['pointerId'])
                        setattr(obj, f.name, ContentType.objects.get_for_model(get_model(data['pointerId'])))
                    elif f.__class__.__name__ == 'IntegerField' or isinstance(data[f.name], int):
                        if debug:
                            prnt('is int')
                        if str(getattr(obj, f.name)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, int(data[f.name]))
                    elif f.__class__.__name__ == 'DecimalField' or isinstance(data[f.name], decimal.Decimal):
                        if debug:
                            prnt('is decimal')
                        if str(getattr(obj, f.name)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, decimal.Decimal(data[f.name]))
                    elif str(data[f.name]) == "[]":
                        if debug:
                            prnt('== []')
                        if str(getattr(obj, f.name)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, "[]")
                    elif str(data[f.name]).startswith('[') and str(data[f.name]).endswith(']'):
                        if debug:
                            prnt('starts with []', json.dumps(data[f.name]))
                        if str(getattr(obj, f.name)) != str(data[f.name]):
                            updatedDB = True
                            if debug:
                                prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                        setattr(obj, f.name, json.dumps(data[f.name]))
                    elif f.__class__.__name__ == 'DateTimeField':
                        try:
                            if not getattr(obj, f.name) and data[f.name] or str(dt_to_string(getattr(obj, f.name))) != str(data[f.name]):
                                updatedDB = True
                        except:
                            updatedDB = True
                        setattr(obj, f.name, str(data[f.name]))
                    elif f.__class__.__name__ == 'CharField' or f.__class__.__name__ == 'TextField':
                        if debug:
                            prnt('is string')
                        if len(str(data[f.name])) < 10000000:
                            if str(getattr(obj, f.name)) != str(data[f.name]):
                                updatedDB = True
                                if debug:
                                    prnt('--UDP:',str(getattr(obj, f.name)), str(data[f.name]))
                            setattr(obj, f.name, str(data[f.name]))
                    else:
                        if debug:
                            prnt('sync esle')
                        if len(str(data[f.name])) < 10000000:
                            # from utils.models import parse_input
                            fieldData = sort_dict(parse_input(data[f.name]))
                            if str(sort_dict(getattr(obj, f.name))) != str(fieldData) and str(getattr(obj, f.name)) != str(data[f.name]):
                                updatedDB = True
                                if debug:
                                    prnt('--UDP:',str(sort_dict((getattr(obj, f.name)))), str(data[f.name]))
                            setattr(obj, f.name, fieldData)
                    if debug:
                        prnt('updatedDB::',updatedDB)
        except Exception as e:
            prnt('fsyncattr4937',f.name,str(e))
            pass
    return obj, updatedDB

def super_sync(target, received_data, do_save=False, skip_fields=['latestModel'], if_empty_fields=[]):
    prntDebug('--super_sync',skip_fields)
    dt = None
    if isinstance(received_data, dict):
        # if 'added' in received_data:
        #     dt = received_data['added']
        if 'created' in received_data:
            dt = received_data['created']
        # elif 'created_dt' in received_data:
        #     dt = received_data['created_dt']
    # elif isinstance(received_data, models.Model):
    #     if has_method(received_data,'added'):
    #         dt = received_data.added
    #     elif has_method(received_data,'created'):
    #         dt = received_data.created
    #     elif has_method(received_data,'created_dt'):
    #         dt = received_data.created_dt
    if not dt:
        dt = now_utc()

    target, updatedDB = set_model_attr(target, received_data, dt=dt, skip_fields=skip_fields)
    # if isinstance(received, models.Model):
    #     fields = target._meta.fields
    #     for f in fields:
    #         if f.name not in skip_fields:
    #             try:
    #                 skip = False
    #                 if f.name in if_empty_fields:
    #                     x = getattr(target, f.name)
    #                     if x:
    #                         skip = True
    #                 if not skip:
    #                     attr = getattr(received, f.name)
    #                     if f.name != 'id' or getattr(target, f.name) == '0':
    #                         setattr(target, f.name, attr)
    #             except Exception as e:
    #                 prnt('fail483659',str(e))
    # elif isinstance(received, dict):
    #     for key in received:
    #         if key not in skip_fields:
    #             try:
    #                 skip = False
    #                 if key in if_empty_fields:
    #                     x = getattr(target, key)
    #                     if x:
    #                         skip = True
    #                 if not skip:
    #                     if key != 'id' or getattr(target, key) == '0':
    #                         setattr(target, key, received[key])
    #             except Exception as e:
    #                 prnt('fail271434',str(e))
    if has_field(target, 'blockchainType') and target.blockchainType == target.object_type:
        chain, target, secondChain = find_or_create_chain_from_object(target)
        if chain and has_field(target, 'blockchainId') and not target.blockchainId:
            target.blockchainId = chain.id
    if do_save:
        target.save()
    else:
        target.updated_on_node = now_utc()
    return target


def find_or_create_chain_from_object(obj, recheck_chain=False):
    prntDebug('-find_or_create_chain_from_object',obj)

    def get_secondChain(obj, blockchain, secondChain, obj_is_model):     
        if obj_is_model and has_field(obj, 'secondChainType') or not obj_is_model and 'secondChainType' in obj:
            prntDebug('find secondChain')
            if obj_is_model and obj.object_type == 'UserTransaction' or not obj_is_model and 'object_type' in obj and obj['object_type'] == 'UserTransaction': # wallet chain
                if obj_is_model:
                    if obj.SenderWallet_obj:
                        secondChain = obj.SenderWallet_obj.get_chain()
                        blockchain = obj.ReceiverWallet_obj.get_chain()
                else:
                    if 'SenderWallet_obj' in obj and obj['SenderWallet_obj']:
                        secondChain = Blockchain.objects.filter(genesisId=obj['SenderWallet_obj']).first()
                    blockchain = Blockchain.objects.filter(genesisId=obj['ReceiverWallet_obj']).first()
            elif obj_is_model and obj.object_type == 'UserVote': # not used
                blockchain = Blockchain.objects.filter(genesisType=obj.blockchainType, genesisId=obj.User_obj.id).first()
                pointer = get_dynamic_model(obj.pointerId, id=obj.pointerId)
                secondChain, pointer, ignore = find_or_create_chain_from_object(pointer)
            else:
                prnt('chain else')
                if obj_is_model:
                    schainType = obj.secondChainType
                    prnt('schainType',schainType)
                    s_obj = schainType+'_obj'
                    fields = obj._meta.fields
                    if any(f.name == s_obj for f in fields):
                        genId = getattr(obj, s_obj).id
                        secondChain = Blockchain.objects.filter(genesisId=genId).first()
                else:
                    schainType = obj['secondChainType']
                    s_obj = schainType+'_obj'
                    if any(f == s_obj for f in obj):
                        secondChain = Blockchain.objects.filter(genesisId=obj[s_obj]).first()
                if not secondChain:
                    if schainType.startswith(get_model_prefix('Blockchain')):
                        secondChain = Blockchain.objects.filter(id=schainType).first()
                    else:
                        secondChain = Blockchain.objects.filter(genesisId=schainType).first()
                if not secondChain and schainType == 'Sonet':
                    prnt('get 2')
                    secondChain = Blockchain.objects.filter(genesisType='Sonet').first()
                    prnt('secondChain',secondChain)
                    if not secondChain:
                        sonet = Sonet.objects.first()
                        if sonet:
                            secondChain = Blockchain(genesisId=sonet.id, genesisType='Sonet', genesisName='Sonet', created=sonet.created)
                            secondChain.save()
        return blockchain, secondChain
    
    if isinstance(obj, dict):
        obj_is_model = False
    else:
        obj_is_model = True
    from blockchain.models import Blockchain, Sonet, NodeChain_genesisId, selectableChains, mandatoryChains
    blockchain = None
    secondChain = None
    ChainTypes = selectableChains + mandatoryChains
    if not recheck_chain and obj_is_model and has_field(obj, 'blockchainId') and obj.blockchainId:
        blockchain = Blockchain.objects.filter(id=obj.blockchainId).first()
        if blockchain:
            blockchain, secondChain = get_secondChain(obj, blockchain, secondChain, obj_is_model)
            prntDebug('done find chain p2', blockchain, obj, secondChain)
            return blockchain, obj, secondChain
    if obj_is_model and has_field(obj, 'proposed_modification') and obj.proposed_modification or not obj_is_model and 'proposed_modification' in obj and obj['proposed_modification']:
        return None, obj, None # proposals are not committed to chain, commit after modification completed
    elif obj_is_model and not has_field(obj, 'blockchainType') or not obj_is_model and 'blockchainType' not in obj:
        return None, obj, None
    elif obj_is_model and has_field(obj, 'blockchainType') and obj.blockchainType == 'NoChain' or not obj_is_model and 'blockchainType' in obj and obj['blockchainType'] == 'NoChain':
        return blockchain, obj, secondChain
    elif obj_is_model and 'User' in obj.object_type or obj_is_model and obj.blockchainType in ChainTypes or not obj_is_model and 'blockchainType' in obj and obj['blockchainType'] in ChainTypes or not obj_is_model and 'object_type' in obj and obj['blockchainType'] == 'User':
        if obj_is_model and obj.object_type == 'User' or not obj_is_model and 'object_type' in obj and obj['object_type'] == 'User':
            if obj_is_model:
                obj_id = obj.id
                created_time = obj.created
            else:
                obj_id = obj['id']
                created_time = string_to_dt(obj['created'])
            blockchain = Blockchain.objects.filter(genesisId=obj_id).first()
            if not blockchain:
                blockchain = Blockchain(genesisId=obj_id, genesisType='User', genesisName=obj.display_name, created=created_time)
                blockchain.save()
            elif blockchain.genesisName != obj.display_name:
                blockchain.genesisName = obj.display_name
                blockchain.save()
            if has_field(obj, 'blockchainId') and not obj.blockchainId:
                obj.blockchainId = blockchain.id
            prnt('user created chain:',blockchain)
        elif obj_is_model and obj.blockchainType == obj.object_type or not obj_is_model and 'blockchainType' in obj and 'object_type' in obj and obj['object_type'] == obj['blockchainType']:
            if obj_is_model:
                object_type = obj.object_type
                obj_id = obj.id
                # if has_field(obj, 'added'):
                #     added_time = obj.added
                # elif has_field(obj, 'created_dt'):
                #     added_time = obj.created_dt
                if has_field(obj, 'created'):
                    created_time = obj.created
            else:
                object_type = obj['object_type']
                obj_id = obj['id']
                # if 'added' in obj:
                #     added_time = string_to_dt(obj['added'])
                # elif 'created_dt' in obj:
                #     added_time = string_to_dt(obj['created_dt'])
                if 'created' in obj:
                    created_time = string_to_dt(obj['created'])
            blockchain = Blockchain.objects.filter(genesisId=obj_id).first()
            if not blockchain:
                blockchain = Blockchain(genesisId=obj_id, genesisType=object_type, genesisName=get_chainName(obj), created=created_time)
                blockchain.save()
            elif blockchain.genesisName != get_chainName(obj):
                blockchain.genesisName = get_chainName(obj)
            if has_field(obj, 'blockchainId') and not obj.blockchainId:
                obj.blockchainId = blockchain.id
        elif obj_is_model and 'User' in obj.object_type or not obj_is_model and 'object_type' in obj and 'User' in obj['object_type']:
            if obj_is_model:
                u_obj = 'User_obj'
                for f in [f.name for f in obj._meta.fields if u_obj in f.name]:
                    genId = getattr(obj, f).id
                    blockchain = Blockchain.objects.filter(genesisId=genId).first()
                    if blockchain:
                        break
            else:
                u_obj = 'User_obj'
                for f in [f for f in obj if u_obj in f]:
                    genId = obj[f]
                    blockchain = Blockchain.objects.filter(genesisId=genId).first()
                    if blockchain:
                        break
        elif obj_is_model and obj.blockchainType == 'Region' or not obj_is_model and 'blockchainType' in obj and obj['blockchainType'] == 'Region':
            region = None
            if obj_is_model and has_field(obj, 'Government_obj') and obj.Government_obj:
                # broadcast dict objs do not include Government_obj data, will fail here if attempted
                if obj.Government_obj.gov_level == 'Federal':
                    region = obj.Country_obj
            if obj_is_model and not region or not obj_is_model and 'Government_obj' not in obj:
                if obj_is_model:
                    region = obj.Region_obj
                else:
                    from posts.models import Region
                    region = Region.valid_objects.filter(id=obj['Region_obj']).first()
            if region:
                blockchain = Blockchain.objects.filter(genesisId=region.id).first()
                if not blockchain:
                    blockchain = Blockchain(genesisId=region.id, genesisType='Region', genesisName=region.Name, created=region.created)
                    blockchain.save()
                elif blockchain.genesisName != get_chainName(region):
                    blockchain.genesisName = get_chainName(region)
                    blockchain.save()
        elif obj_is_model and obj.blockchainType == 'Nodes' or not obj_is_model and 'blockchainType' in obj and obj['blockchainType'] == 'Nodes':
            blockchain = Blockchain.objects.filter(genesisId=NodeChain_genesisId).first()
            if not blockchain:
                sonet = Sonet.objects.first()
                blockchain = Blockchain(genesisId=NodeChain_genesisId, genesisType='Nodes', genesisName='Nodes', created=sonet.created)
                blockchain.save()
        # elif obj_is_model and obj.blockchainType in ChainTypes or not obj_is_model and 'blockchainType' in obj and obj['blockchainType'] in ChainTypes:
        #     ...

    blockchain, secondChain = get_secondChain(obj, blockchain, secondChain, obj_is_model)

    prntDebug('done find chain', blockchain, obj, secondChain)
    return blockchain, obj, secondChain

def get_data(items_list, include_related=False, return_model=False, verify_data=True, result_as_dict=False, include_deletions=False, special_request={}):
    prntDebug('--get data sgtart',len(items_list),'result_as_dict',result_as_dict,'return_model',return_model)
    from blockchain.models import Validator, EventLog
    from utils.locked import verify_obj_to_data, convert_to_dict
    mb_size = 0
    modelObjs = []
    obj_types = {}
    iden_list = []
    not_found = []
    not_valid = []
    if result_as_dict:
        storedData = {}
    else:
        storedData = []
    if not items_list:
        return storedData, not_found, not_valid
    def add_to_list(objType, value):
        # prnt('add_to_list',objType,value)
        if objType and value and is_id(value):
            if objType in obj_types:
                if value not in obj_types[objType]:
                    obj_types[objType].append(value)
            else:
                obj_types[objType] = [value]
            iden_list.append(value)

    def add_to_return_list(obj, target_list_or_dict):
        # prntDebug('-add_to_return_list', obj)
        if return_model:
            if isinstance(target_list_or_dict, dict):
                if obj.object_type not in target_list_or_dict:
                    target_list_or_dict[obj.object_type] = {}
                target_list_or_dict[obj.object_type][obj.id] = obj
            else:
                target_list_or_dict.append(obj)
        else:
            if isinstance(target_list_or_dict, dict):
                if obj.object_type not in target_list_or_dict:
                    target_list_or_dict[obj.object_type] = {}
                target_list_or_dict[obj.object_type][obj.id] = convert_to_dict(obj)
            else:
                target_list_or_dict.append(convert_to_dict(obj))
        return target_list_or_dict

    if isinstance(items_list, dict):
        for key, value in items_list.items():
            if key == 'All' or key == 'Nodes' or key == 'New':
                # node block
                objType = 'Node'
                for i in value:
                    add_to_list(objType, i)
                break
            elif key != 'meta':
                objType = get_pointer_type(key)
                if objType:
                    if is_id(key):
                        add_to_list(objType, key)
                    elif isinstance(value, list):
                        for i in value:
                            if is_id(i):
                                add_to_list(objType, i)
                    elif isinstance(value, dict):
                        if 'id' in value:
                            add_to_list(objType, value['id'])
                        else:
                            add_to_list(objType, key)
                    elif isinstance(value, str) and is_id(value):
                        add_to_list(objType, value)
            
    elif isinstance(items_list, list):
        if isinstance(items_list[0], dict):
            for i in items_list:
                if 'object_type' in i:
                    add_to_list(i['object_type'], i['id'])
                else:
                    for key, value in i.items():
                        if key == 'All' or key == 'Nodes' or key == 'New':
                            # node block
                            objType = 'Node'
                            for i in value:
                                add_to_list(objType, i)
                            break
                        elif key != 'meta':
                            objType = get_pointer_type(key)
                            if objType:
                                if is_id(key):
                                    add_to_list(objType, key)
                                elif isinstance(value, list):
                                    for i in value:
                                        add_to_list(objType, i)
                                elif isinstance(value, dict):
                                    if 'id' in value:
                                        add_to_list(objType, value['id'])
                                    else:
                                        add_to_list(objType, key)
                                elif isinstance(value, str):
                                    add_to_list(objType, value)
        elif isinstance(items_list[0], models.Model):
            for i in items_list:
                modelObjs.append(i)
                iden_list.append(i.id)
        elif isinstance(items_list[0], str):
            for i in items_list:
                if is_id(i):
                    add_to_list(get_pointer_type(i), i)

    if include_related:
        validators = Validator.objects.filter(data__has_any_keys=iden_list).exclude(id__in=iden_list)
        for obj in validators:
            if not verify_data or verify_obj_to_data(obj, obj):
                storedData = add_to_return_list(obj, storedData)
                mb_size += to_megabytes(obj)
            else:
                not_valid = add_to_return_list(obj, not_valid)
    for obj in modelObjs:
        if not verify_data or not has_field(obj, 'signature') or verify_obj_to_data(obj, obj):
            storedData = add_to_return_list(obj, storedData)
            mb_size += to_megabytes(obj)
        else:
            not_valid = add_to_return_list(obj, not_valid)

    for obj_type in obj_types:
        prnt(' searching obj_types[obj_type]',obj_type, len(obj_types[obj_type]))
        if special_request:
            prntDebug('special_request',special_request)
            model = get_model(obj_type)
            if 'exclude' in special_request and has_field(model, next(iter(special_request['exclude'].keys()))):
                objs = get_dynamic_model(model, list=True, exclude=special_request['exclude'], id__in=obj_types[obj_type])
            else:
                objs = get_dynamic_model(obj_type, list=True, id__in=obj_types[obj_type])
        else:
            objs = get_dynamic_model(obj_type, list=True, id__in=obj_types[obj_type])
        if objs:
            for obj in objs:
                if not verify_data or not has_field(obj, 'signature') or verify_obj_to_data(obj, obj):
                    storedData = add_to_return_list(obj, storedData)
                    mb_size += to_megabytes(obj)
                else:
                    not_valid = add_to_return_list(obj, not_valid)
                obj_types[obj.object_type].remove(obj.id)
    if include_related:
        from posts.models import Update
        updates = Update.objects.filter(pointerId__in=iden_list).exclude(id__in=iden_list).distinct('pointerId').order_by('-pointerId', '-created')
        for obj in updates:
            if not verify_data or verify_obj_to_data(obj, obj):
                storedData = add_to_return_list(obj, storedData)
                mb_size += to_megabytes(obj)
            else:
                not_valid = add_to_return_list(obj, not_valid)
            try:
                obj_types[obj.object_type].remove(obj.id)
            except:
                pass
        notifications = get_dynamic_model('Notification', list=True, pointerId__in=iden_list)
        for obj in notifications:
            if not verify_data or verify_obj_to_data(obj, obj):
                storedData = add_to_return_list(obj, storedData)
                mb_size += to_megabytes(obj)
            else:
                not_valid = add_to_return_list(obj, not_valid)
            try:
                obj_types[obj.object_type].remove(obj.id)
            except:
                pass

    # prntDebug('get data step3')
    for obj_type, idList in obj_types.items():
        for i in idList:
            not_found.append(i)
    if include_deletions:
        delLogs = []
        if not_found:
            delLogs = EventLog.objects.filter(type='Deletion_Log', data__has_any_key=not_found)
            prnt('delLogs:',delLogs.count())
            not_found_list = not_found
            for log in delLogs:
                for i in not_found_list:
                    if i in log:
                        not_found.remove(i)
            if not return_model:
                return storedData, not_found, not_valid, [convert_to_dict(d) for d in delLogs]
        return storedData, not_found, not_valid, delLogs
    
    prnt('results: data:',len(storedData), 'not_found:',len(not_found),'not_valid:',len(not_valid),'mb_size', mb_size)
    return storedData, not_found, not_valid

def get_all_objects(items):
    # prnt('get_all_objects')
    x = []
    data = {}
    for i in items:
        m = get_pointer_type(i)
        if m:
            if m not in data:
                data[m] = []
            data[m].append(i)
    for object_type, id_list in data.items():
        objs = get_dynamic_model(object_type, list=True, id__in=id_list)
        if objs:
            x = x + list(objs)
    return x
    

def super_share(log=None, gov=None, func=None, val_type='super', job_id=None, adjust_created_time=True):
    # super_share can handle a single scrape function or a singular item at a time, not items for multiple chains
    # from blockchain.models import get_scraperScripts, get_latest_dataPacket, get_self_node, Validator, sigData_to_hash, get_operatorData, get_user, logEvent, DataPacket, convert_to_dict
    prnt('---super_share', gov, 'func:', func,'log1:',log)
    from blockchain.models import DataPacket, logEvent, get_scraperScripts, Validator
    items = []
    job_time = None
    
    if is_id(log):
        log = DataPacket.objects.filter(id=log).first()
    if not log:
        return 0, False
    if isinstance(log, list):
        items = log
    if isinstance(log, models.Model):
        if log.object_type == 'DataPacket' and 'shareData' in log.data:
            if log.data['shareData']:
                func = log.data['func']
                items = get_all_objects(log.data['shareData'])
                prnt('func:',func)
                if 'created' in log.data:
                    job_time = string_to_dt(log.data['created'])
                job_id = log.id
                # go.delete()
        else:
            items = [log]
    if not job_time:
        job_time = round_time(dt=now_utc(), dir='down', amount='hour')
    logEvent(f'--super_share func:{func} log:{log.id if log and isinstance(log, models.Model) else"none"} items:{len(items)}')
    prnt('log2:',log)
    operatorData = get_operatorData()
    # prntDebug('operatorData',operatorData)
    self_node = get_self_node(operatorData=operatorData)
    prnt('self_node', self_node)
    prnt('items length:',len(items))
    is_super = False
    if self_node:
        is_super = self_node.User_obj.assess_super_status()
    else:
        user = get_user(obj=items[0])
        if user:
            is_super = user.assess_super_status()
    prnt('log3:',log)
    prnt('is_super',is_super)
    if is_super and len(items) > 0:
        dataPacket = None
        blockchain = None
        validator = None
        approved_funcs = []
        if not isinstance(items, list):
            items = [items]
        if not gov:
            for i in items:
                if i.object_type == 'Government':
                    gov = i
                    break
                elif has_field(i, 'Government_obj') and i.Government_obj:
                    gov = i.Government_obj
                    break
        if gov:
            prnt('hasgov',gov)
            if is_id(gov):
                gov = get_dynamic_model('Government', id=gov)
            scraperScripts = get_scraperScripts(gov)
            approved_models = scraperScripts.approved_models
            model_types = []
            exceptions = ['Update', 'Notification']
            for i in items:
                if not i or not isinstance(i, models.Model):
                    items.remove(i)
                elif i.object_type not in model_types:
                    if i.object_type == 'Update' and get_pointer_type(i.pointerId) not in model_types:
                        model_types.append(get_pointer_type(i.pointerId))
                    elif i.object_type not in exceptions:
                        model_types.append(i.object_type)
            for key, value in approved_models.items():
                result = all(item in value for item in model_types)
                if result:
                    approved_funcs.append(key)
            prnt('approved_funcs:',approved_funcs)
            prnt('func',func)
        if gov:
            logEvent('superValidate: ' + gov.Country_obj.Name + ' ' + func, log_type='Tasks')
            chainId = 'All'
            blockchain, obj, receiverChain = find_or_create_chain_from_object(gov)
            if blockchain:
                chainId = blockchain.id
                dataPacket = get_latest_dataPacket(blockchain.id)
        else:
            logEvent('superValidate: ' + 'gov' + ' ' + func, log_type='Tasks')
        prnt('log4:',log)
        if func == 'set_object' or func in approved_funcs:
            prnt('proceed to validate')
            prnt('items',items)
            from utils.locked import sign_obj, convert_to_dict
            processed_data = {'obj_ids':[],'hashes':{}}
            for i in items:
                prnt('i',i)
                proceed = True
                if has_method(i, 'required_for_validation'):
                    for c in i.required_for_validation():
                        if not getattr(i, c):
                            prnt('FAIL PROCeed',i.id,c,getattr(i, c),'\n\n')
                            proceed = False
                            break
                if proceed:
                    prnt('proceed')
                    obj = None
                    if has_field(i, 'Validator_obj') and i.Validator_obj:
                        if has_field(i, 'signature') and i.signature:
                            processed_data['hashes'][i.id] = sigData_to_hash(i)
                    elif has_field(i, 'validated') and i.validated:
                        if has_field(i, 'signature') and i.signature:
                            processed_data['hashes'][i.id] = sigData_to_hash(i)
                    prnt('pro2')
                    prnt('self_node',self_node)
                    i.func = 'super'
                    i.creatorNodeId = self_node.id
                    i.validatorNodeId = self_node.id
                    if has_field(i, 'proposed_modification') and i.proposed_modification:
                        prnt('handle proposed_modification')
                        modded_obj = i
                        prnt('modded_obj',modded_obj)
                        obj = get_or_create_model(modded_obj.object_type, id=modded_obj.proposed_modification)
                        prnt('obj',obj)
                        if not obj.Name or obj.Name == modded_obj.Name:
                            prnt('super sync')
                            if not obj.created:
                                obj.created = job_time
                            # prntn('convert_to_dict(modded_obj)',convert_to_dict(modded_obj))
                            # prntn('convert_to_dict(obj)',convert_to_dict(obj))
                            obj = super_sync(obj, convert_to_dict(modded_obj), skip_fields=['latestModel','id'])
                            prntn('done sync',convert_to_dict(obj))
                            obj.proposed_modification = None
                            obj.Validator_obj = None
                            obj.save()
                            obj = sign_obj(obj, operatorData=operatorData)
                            super(get_model(modded_obj.object_type), modded_obj).delete()
                    elif not has_field(i, 'Block_obj') or not i.Block_obj or not i.Block_obj.validated:
                        if adjust_created_time or not i.created:
                            i.created = job_time
                        obj = sign_obj(i, operatorData=operatorData)
                    if obj:
                        if not blockchain:
                            prnt('get blockchain')
                            chainId = 'All'
                            if has_field(obj, 'blockchainType'):
                                # from utils.models import find_or_create_chain_from_object
                                blockchain, obj, receiverChain = find_or_create_chain_from_object(obj)
                                if blockchain:
                                    chainId = blockchain.id

                        if not dataPacket:
                            prnt('get datapacket')
                            dataPacket = get_latest_dataPacket(chainId)
                            prnt('dataPacket',dataPacket)

                        if not validator:
                            prnt('get validator')
                            # validator = Validator.objects.filter(data__has_key=obj.id, CreatorNode_obj=self_node, func='super', is_valid=True).first()
                            # if not validator:
                            validator = Validator(jobId=job_id, CreatorNode_obj=self_node, validatorType=val_type, func='super', is_valid=True)
                            if blockchain:
                                validator.blockchainType=blockchain.genesisType
                                validator.blockchainId=blockchain.id
                            validator.save()
                                # validator = Validator.objects.create(blockchainType=blockchain.genesisType, blockchainId=blockchain.id, CreatorNode_obj=self_node, validatorType='scraper', func='super', is_valid=True)
                        processed_data['obj_ids'].append(obj.id)

                        obj_hash = sigData_to_hash(obj)
                        validator.data[obj.id] = obj_hash
                        obj.Validator_obj = validator
                        obj.save()
                        processed_data['hashes'][obj.id] = obj_hash
            prnt('log6:',log)
            prnt('super next')
            if validator:
                prnt('log6.1')
                from posts.models import Post, Update, update_post
                validator = sign_obj(validator, operatorData=operatorData)
                prnt('log6.2')
                if dataPacket:
                    prnt('log6.3')
                    processed_data['obj_ids'].append(validator.id)
                    processed_data['hashes'][validator.id] = sigData_to_hash(validator)
                    dataPacket.add_item_to_share(processed_data['hashes'])
                    prnt('log6.4')
                if blockchain:
                    prnt('log6.5')
                    blockchain.add_item_to_queue(validator)
                    print('validate posts')
                prnt('log6.6')
                prnt("get_model_prefix('Update')",get_model_prefix('Update'),"get_model_prefix('Notification')",get_model_prefix('Notification'),"get_model_prefix('BillText')",get_model_prefix('BillText'))
                prefixes = [get_model_prefix('Update'),get_model_prefix('Notification')]
                btxt = get_model_prefix('BillText')
                if btxt:
                    prefixes.append(btxt)
                pointerIdens = [i for i in processed_data['obj_ids'] if not i.startswith(tuple(prefixes))]
                prnt('pointerIdens',pointerIdens)
                while pointerIdens:
                    posts = Post.all_objects.filter(pointerId__in=pointerIdens[:500]).exclude(validated=True)
                    to_queue = []
                    if testing():
                        for p in posts:
                            p.validated = True
                            p, updated_fields = update_post(p=p, save_p=True)
                            to_queue.append(p.pointerId)
                    else:
                        for p in posts:
                            validated = p.validate(validator=validator)
                            if validated:
                                to_queue.append(p.pointerId)
                            else:
                                pointer = p.get_pointer()
                                if pointer and pointer.Validatod_obj == validator:
                                    pointer.Validatod_obj = None
                                    pointer.save()
                    if blockchain and to_queue:
                        blockchain.add_item_to_queue(to_queue)
                    if len(pointerIdens) >= 500:
                        pointerIdens = pointerIdens[500:]
                    else:
                        pointerIdens = []
                updateIdens = [u for u in processed_data['obj_ids'] if u.startswith(get_model_prefix('Update'))]
                prnt('updateIdens',updateIdens)
                updates = Update.objects.filter(validated=False, id__in=updateIdens)
                to_queue = []
                if testing():
                    for u in updates:
                        u.validated = True
                        super(Update, u).save()
                        u.sync_with_post()
                        to_queue.append(u)
                
                else:
                    for u in updates:
                        validated = u.validate(validator=validator)
                        if validated:
                            to_queue.append(u)
                if blockchain and to_queue:
                    blockchain.add_item_to_queue(to_queue)
                from accounts.models import Notification
                notiIdens = [u for u in processed_data['obj_ids'] if u.startswith(get_model_prefix('Notification'))]
                prnt('notiIdens',notiIdens)
                notifications = Notification.objects.filter(validated=False, id__in=notiIdens)
                to_queue = []
                for n in notifications:
                    validated = n.validate(validator=validator)
                    if validated:
                        to_queue.append(n)
                if blockchain and to_queue:
                    blockchain.add_item_to_queue(to_queue)
                chains = {}
                from blockchain.models import script_created_modifiable_models
                for m in script_created_modifiable_models:
                    prefix = get_model_prefix(m)
                    if prefix:
                        mIdens = [u for u in processed_data['obj_ids'] if u.startswith(prefix)]
                        prnt('mIdens',mIdens)
                        objs = get_dynamic_model(m, list=True, id__in=mIdens)
                        for o in objs:
                            chain, o, secondChain = find_or_create_chain_from_object(o)
                            if chain:
                                if chain not in chains:
                                    chains[chain] = []
                                chains[chain].append(o)
                if chains:
                    for chain in chains:
                        chain.add_item_to_queue(chains[chain])

                prnt('log7:',log)
                if log and isinstance(log, models.Model) and log.object_type == 'DataPacket':
                    try:
                        log.completed(completed='all')
                    except Exception as e:
                        prnt('del log fail',str(e))
                prnt('completed super share','items length:',len(items),'func:',func, 'updates:',updates.count(), 'posts:',posts.count())
                return items, True
            elif dataPacket:
                dataPacket.add_item_to_share(processed_data['hashes'])
            prnt('step3')
    if log and isinstance(log, models.Model) and log.object_type == 'DataPacket':
        try:
            log.completed(completed='all')
        except Exception as e:
            prnt(str(e))
    prnt('skipped super share', func)
    prnt('items length:',len(items))
    return items, False


def share_with_network(item, post=None, datapacket=None, share_node=False):
    prnt('--share with network',item)
    # from blockchain.models import get_latest_dataPacket
    if item.object_type != 'DataPacket': 
        chain = 'All'
        if has_field(item, 'blockchainType'):
            chain, item, receiverChain = find_or_create_chain_from_object(item)
            if chain:
                chain.add_item_to_queue(item)
            
        if item.object_type != 'Node' or share_node:
            prnt('get datatotsharfe')
            if not datapacket:
                datapacket = get_latest_dataPacket(chain)
            if datapacket:
                datapacket.add_item_to_share(item)
                prnt('shared')
    prnt('done share w netwrok')


def get_operator_pubKey(operatorData=None):
    if not operatorData:
        # from blockchain.models import get_operatorData
        operatorData = get_operatorData()
    return operatorData['pubKey']

def get_superuser_keys(dt=None, data=None):
    from accounts.models import User, UserPubKey
    superusers = User.objects.filter(is_superuser=True)
    prntDev('superusers--keys',superusers)
    if not superusers:
        for u in User.objects.all():
            # from blockchain.models import convert_to_dict
            ...
    x = []
    if dt:
        if not isinstance(dt, datetime.datetime):
            dt = string_to_dt(dt)
    elif data:
        if 'last_updated' in data:
            dt = data['last_updated']
        elif 'created' in data:
            dt = data['created']
        # elif 'created_dt' in data:
        #     dt = data['created_dt']
        # elif 'added' in data:
        #     dt = data['added']
        else:
            return None
        dt = string_to_dt(dt)
    for su in superusers:
        if su.assess_super_status(dt=dt):
            x.append(su)
    if dt:
        upks = UserPubKey.objects.filter(User_obj__in=x).filter(Q(end_life_dt__lte=dt)|Q(end_life_dt=None))
    else:
        upks = UserPubKey.objects.filter(User_obj__in=x, end_life_dt=None)
    return [upk.publicKey for upk in upks]


def check_missing_data(obj, retrieve_missing=True, log_missing=True, downstream_worker=False):
    prnt('check_missing_data', str(obj)[:100])
    from blockchain.models import Block
    result = {}
    if not obj:
        return result
    if is_id(obj):
        # if id is block:
        # get block by id
        # else
        block = Block.objects.filter(data__has_key=obj, validated=True).first()
        if block:
            found_idens = block.check_contents(retrieve_missing=retrieve_missing, log_missing=log_missing, downstream_worker=downstream_worker)
            result['block_id'] = block.id
            result['found_idens'] = found_idens
        else:
            return None
    elif isinstance(obj, models.Model):
        if obj.object_type == 'Block':
            found_idens = obj.check_contents(retrieve_missing=retrieve_missing, log_missing=log_missing, downstream_worker=downstream_worker)
            result['block_id'] = block.id
            result['found_idens'] = found_idens
        else:
            block = Block.objects.filter(data__has_key=obj.id, validated=True).first()
            if block:
                found_idens = block.check_contents(retrieve_missing=retrieve_missing, log_missing=log_missing, downstream_worker=downstream_worker)
                result['block_id'] = block.id
                result['found_idens'] = found_idens
            else:
                return None
    elif isinstance(obj, list):
        blocks = Block.objects.filter(data__has_any_key=obj, validated=True)
        result['block_ids'] = []
        result['found_idens'] = []
        for block in blocks:
            found_idens = block.check_contents(retrieve_missing=retrieve_missing, log_missing=log_missing, downstream_worker=downstream_worker)
            result['block_ids'].append(block.id)
            result['found_idens'] += found_idens

    return result


def initial_save(item, share=False, len=None):
    prntn('---initial save', item)
    from utils.locked import hash_obj_id
    now = now_utc()
    if has_field(item, 'latestModel'):
        item.modelVersion = item.latestModel
    # if has_field(item, 'added') and not item.added:
    #     item.added = now
    if has_field(item, 'created') and not item.created:
        # from blockchain.models import round_time
        item.created = round_time(dt=now, dir='down', amount='hour')
    # elif has_field(item, 'created_dt') and not item.created_dt:
    #     item.created_dt = now
    if has_field(item, 'DateTime'):
        if item.DateTime:
            # prntDebug('does not have dateTime')
            # if has_field(item, 'created'):
            #     from blockchain.models import round_time
            #     item.DateTime = round_time(dt=item.created, dir='down', amount='hour')
            # # elif has_field(item, 'created_dt'):
            # #     item.DateTime = round_time(dt=item.created_dt, dir='down', amount='hour')
        # else:
            if not isinstance(item.DateTime, datetime.datetime):
                item.DateTime = string_to_dt(item.DateTime)
            if not is_timezone_aware(item.DateTime):
                item.DateTime = item.DateTime.replace(tzinfo=ZoneInfo("America/New_York")) # should get tz by region_obj
            item.DateTime = item.DateTime.astimezone(ZoneInfo("UTC"))

    if has_field(item, 'last_updated') and not item.last_updated:
        item.last_updated = now
    if has_field(item, 'Region_obj') and not item.Region_obj and has_field(item, 'Country_obj'):
        item.Region_obj = item.Country_obj
    set_id = 'pre'
    if item.id == '0':
        # if testing():
        #     prntDebug('id_data',hash_obj_id(item, return_data=True))
        item.id = hash_obj_id(item, len=len)
        prnt('newId:', item.id, item.object_type)
        set_id = item.id
        # time.sleep(2)
    if has_field(item, 'blockchainType') and not item.blockchainType == 'NoChain':
        chain, item, secondChain = find_or_create_chain_from_object(item)
        if chain and has_field(item, 'blockchainId'):
            item.blockchainId = chain.id
    try:
        # item.save()
        super(get_model(item.object_type), item).save()
    except Exception as e:
        from blockchain.models import logError
        from django.forms.models import model_to_dict
        code = '8643'
        model_data = model_to_dict(item)
        prnt('INITIAL SAVE Error:', str(e), '\n', model_data)
        delay = False
        extra = {}
        try:
            from utils.locked import convert_to_dict
            extra = {'initial_save':hash_obj_id(item, return_data=True),'initial_save_id':hash_obj_id(item),'set_id':set_id, 'item_dict':str(convert_to_dict(item))[:1000]}
            if has_field(item,'Data'):
                extra['item_data'] = item.Data
            if has_field(item,'func'):
                extra['initial_func'] = item.func
            if 'duplicate key value violates unique constraint' in str(e): # genericModels have this issue, especially with bill creation, not sure why
                duplicate_item = get_dynamic_model(item.object_type, id=item.id)
                extra['duplicate_item'] = hash_obj_id(duplicate_item, return_data=True)
                extra['duplicate_item_id'] = hash_obj_id(duplicate_item)
                if has_field(duplicate_item,'func'):
                    extra['dup_func'] = duplicate_item.func
                if has_field(duplicate_item,'Data'):
                    extra['dup_data'] = duplicate_item.Data
                code = '64214'
                logError(e, code=code, func='initial save', region='x', extra=extra)
        except Exception as e:
            try:
                try:
                    prnt('error 49354',str(e))
                except Exception as w:
                    prnt('error 9378',str(w))
                prntDebug('initial save error 76423')
                extra['err'] = '484762!!!~!'
                e = 'AHHH!'
                code = '97632'
                logError(e, code=code, func='initial save', region='x', extra=extra)
            except Exception as e:
                try:
                    prnt('error 8734',str(e))
                except Exception as w:
                    prnt('error 1234',str(w))
                e = 'IDGAF'
                prnt('initial save error 12358 AHHHHH!')
                extra['err'] = 'AHHHHH'
                code = '48354'
                logError(e, code=code, func='initial save', region='x', extra=extra)
        if delay:
            time.sleep(15)
    if has_method(item, 'boot'):
        try:
            prnt('try create post', item)
            p = item.boot()
        except Exception as e:
            prnt('create post fail', str(e))
            p = False
    if share:
        share_with_network(item)
    prnt('done initial save', item)
    return item


def save_mutable_fields(obj, *args, **kwargs):
    prntDev('--save_mutable_fields',obj)
    if not has_field(obj, 'Validator_obj') or obj.Validator_obj != None:
        from blockchain.models import logError
        if has_field(obj, 'Block_obj') and obj.Block_obj:
            from utils.locked import check_commit_data, get_commit_data
            if not check_commit_data(obj, obj.Block_obj.data[obj.id]):
            # sigHash = sigData_to_hash(obj)
            # if sigHash not in str(obj.Block_obj.data):
                prnt('commit_data has CHANGED')
                logError('commit_data has CHANGED', code='7532', func='save_mutable_fields', extra={'commit_data':get_commit_data(obj)})
                return False
        if has_method(obj, 'get_hash_to_id') and obj.object_type != 'Update':
            from utils.locked import hash_obj_id
            if obj.id != hash_obj_id(obj):
                prnt('IMMUTABLE field has CHANGED')
                logError('IMMUTABLE field has CHANGED', code='6432', func='save_mutable_fields', extra={'get_hash_to_id':obj.get_hash_to_id()})
                return False
        if has_field(obj, 'signature') and obj.signature != '':
            from utils.locked import verify_obj_to_data
            if not verify_obj_to_data(obj, obj):
                prnt('-Not Valid Save')
                logError('-Not Valid Save', code='3579', func='save_mutable_fields')
                return False
    prntDev('-saving...',obj)
    model = get_model(obj.object_type)
    super(model, obj).save(*args, **kwargs)
    return True

skipwords = [
    "shouldn't", 'needn', 'before', 'we', 'are', 'after', 'because', 'haven', 'and', 'itself', 'all', 'o', 'but', 'any', 'again', 'aren', 'she', "you'll", 
    'himself', 'didn', 'under', 'wasn', 's', 'yours', 'very', "aren't", "won't", 'don', 'how', 'him', "mustn't", 'more', 't', 'off', 'ours', "it's", 'into', 
    'same', 'myself', 'at', "wouldn't", 'they', 'only', 'so', 'down', 'yourselves', 'both', 'each', 'who', 'themselves', 'yourself', 'as', 'up', 'not', 'above', 
    'this', 'will', 'was', 'here', 'does', 'for', 'such', 'there', 'should', 'by', 'mustn', 're', 'is', "isn't", "she's", "weren't", 'y', 'he', 'between', 
    'where', 'on', 'am', 'other', 'now', 'too', "haven't", 'some', 'd', 'being', 'then', 'hasn', "hadn't", 'in', 'having', 'i', 'which', "mightn't", 'were', 
    'wouldn', 'our', 'to', 'until', 'with', 'most', 'if', 'those', 'their', 'nor', 'of', 'doesn', "wasn't", 'do', 'that', 'once', 'than', 'ain', 'isn', 'its', 
    'these', 'had', 'your', 'can', 'you', 'shouldn', "you're", 'doing', 'it', 'while', 'the', 'll', 'or', 'hadn', "doesn't", 'his', 've', 'about', 'through', 'own', 
    'mightn', 'further', 'hers', "didn't", 'm', "that'll", "hasn't", "you'd", 'me', 'have', 'what', 'did', 'over', 'whom', "you've", 'has', 'why', "needn't", 
    'couldn', 'below', "don't", 'an', 'no', 'ourselves', 'out', 'won', 'her', 'be', 'from', "shan't", 'been', 'herself', "should've", 'just', 'ma', 'when', 'shan', 
    "couldn't", 'few', 'during', 'against', 'a', 'them', 'weren', 'theirs', 'my', 'statement',
    'SENATORS’ STATEMENTS','Orders of the Day', 'Question Period', 'Petitions', "Members' Statements", 'ORDERS OF THE DAY', 'SENATORS’ STATEMENTS', 'ROUTINE PROCEEDINGS', 
    'Oral questions', 'QUESTION PERIOD','QUESTION PERIOD', 'Government bills', 'Oral Questions', 'Adjournment Proceedings', 'Adjournment','adjourned',
    'Oral questions', 'Statements by Members', 'Government bills','ORDERS OF THE DAY', 'QUESTION PERIOD', 'ROUTINE PROCEEDINGS','Opposition motions',  
    'act', 'acts', 'statutes', 'legislature', 'schedule', 'tax','taxes','taxation','taxable','taxation','taxapyer','taxed','taxing','income','incomes',
    'bill amends the', 'enactment grants', 'enactment grants the', 'Opposition motions','declaration','minute','remark','remarks','minutes','yields',
    'this enactment grants', 'enactment amends the','this enactment amends','Royal Assent','unanimous','consent','motion','move','issues',
    'this acts amends', 'act amends the', 'act amends', 'amends','amendment','political', 'without objection', 'objection ordered',
    'enactment', 'enactment amends', 'provisions', 'intermediary', 'Introduction of Visitors', 'gentlemen', 'gentleman','gentlewoman','congress','yeas nays',
    'intermediaries', 'regulation', 'regulations', 'regulations to', 'Members’ Statements','gentlelady','one minute','recognized','time expired','two minutes','yield',
    'also amends', 'consequential amendments', 'amendments to', 'amendments', 'Business of the Senate','seconds','state','met',
    'amends', 'makes consequential amendments', 'enactment provides', 'Visitor in the Gallery','monday','tuesday','wednesday','thursday','friday','saturday','sunday',
    'provides', 'canada', 'council', 'councils', 'government','hon', 'Points of order','clerk','tempore','appoint',
    'senators','agreed','committee','senate','report','reports','presented', 'Report stage',
    'canadians','sector','legislation','bill','province','canadian','member', 'Visitors in the Gallery',
    'minister','ministers','madam','speaker','house','senator','statements','Third reading and adoption',
    'question','mr','mrs','ms','colleague','conservative','conservatives','liberal','called','thereupon','president',
    'liberals','ndp','mp','mps','chair','members','canada bill','proceedings','parliament',
    'canada bill','canada enacts','department','is amended','canada act','amended',
    'district','electoral','the province','province of','amend','amended','canadian bill',
    'parliamentary','commons','legislative','federal','provincial','sencanada','repealed',
    'ca','exemption','pursuant','provinces','repeal','commencement','day','laws','canada obligations',
    'ontario','ontario enacts','ontario regulation','schedule ontario','ontario act','enacted','policies','issued','agreements','documents','code','may',
    'amends the','agreement','exempt','law','federal provincial','provision','month','canadian charter',
    'amending','consultations','is repealed','comply','parliamentarians','municiapl','the parliament',
    'act canada','an assault','parliamentarians act','parliament of','of parliament',
    'canada implementation','insertion','canada official','provincial legislation','section',
    'to canada','of parliamentarians','to amend','act canadian','parliament report','proceeding',
    'canada council','municipal act','statutes of','amend the','province will','province law',
    'canadian council', 'implement', 'stage',
    'order','debate','opposition','leader','party','honourable','questions','vote','policy','secratary',
    'honour','representative','governments','bills','please','thank','municipalities','colleagues',
    'national','committees','official','third','second','parliamentarian','assent','politicians','Second reading',
    'representatives','parliaments','oh','None','none','points of order','The Senate',"Private Members' Bills",
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
    ]



def run_database_maintenance():
    # from django.db import connection
    # with connection.cursor() as cursor:
    #     cursor.execute("VACUUM FULL;")
    #     cursor.execute("REINDEX DATABASE so_data;")

    # run 
    cmd = ['psql', '-U', 'sozed (or whatever admin user)', '-d', 'so_data', '-c', '"VACUUM FULL;"']
    # psql -U sozed (or whatever admin user) -d so_data -c "REINDEX DATABASE so_data;"
    # result = subprocess.run(cmd, input=systemPass, text=True)
    pass


def get_keywords_old(obj, text):
    prnt('get keyowrds')
    # logEvent('get keyowrds', code='4674')
    # stop_words = set(stopwords.words('english'))
    # stop_words_french = set(stopwords.words('french'))
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
            import multiprocessing
            multiprocessing.set_start_method("spawn", force=True)
            prntDebug('s2')
            from keybert import KeyBERT
            import os
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            prntDebug('s3')
            kw_model = KeyBERT()
            prntDebug('s4')
            stop_w = []
            # from posts.models import skipwords
            for i in skipwords:
                stop_w.append(i)
            spares = {}
            obj.keyword_array = []
            prntDebug('s5')
            x = kw_model.extract_keywords(text, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
            prntDebug('s6')
            n = 0
            terms = ''
            for i, r in x:
                if i not in stop_w and i not in obj.keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
                    n += 1
                    terms = terms + i + ' '
            prntDebug('s7')
            prntDebug('obj.keyword_array 1',obj.keyword_array)
            x = kw_model.extract_keywords(text, top_n=7, keyphrase_ngram_range=(1, 1), stop_words=stop_w)
            prntDebug('s8')
            n = 0
            for i, r in x:
                if i not in stop_w and not i.isnumeric():
                    if i in str(terms):
                        if i in spares:
                            spares[i] += 1
                        else:
                            spares[i] = 1
                    elif n < 7:
                        obj.keyword_array.append(i)
                        stop_w.append(i)
                        n += 1
            if spares:
                for term, count in spares.items():
                    matches = 0
                    for i in obj.keyword_array:
                        if term in i:
                            matches += 1
                    if count > matches or matches > 2:
                        for i in obj.keyword_array:
                            if term in i:
                                obj.keyword_array.remove(i)
                        obj.keyword_array.append(term)
            prntDebug('s9')
            prntDebug('obj.keyword_array 2',obj.keyword_array)
        
        except Exception as e:
            prnt('get_keywords fail', str(e))
            from blockchain.models import logEvent
            logEvent(e, code='59385', func='get_keywords', extra={'obj':obj.id}, log_type='Errors')
            # time.sleep(10)
        finish_time = datetime.datetime.now() - start_time
        prnt('keywords time:',finish_time)
    # logEvent('done get keyowrds', code='765343')
    return obj


def get_keywords_old2(obj, text):
    prnt('get keyowrds')
    # logEvent('get keyowrds', code='4674')
    # stop_words = set(stopwords.words('english'))
    # stop_words_french = set(stopwords.words('french'))
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

            from nltk.corpus import stopwords
            import nltk
            # print('3')
            nltk.download("stopwords")
            nltk_stopwords = set(stopwords.words("english"))
            custom_stopwords = {"example", "discussion", "important"}
            stop_w = set(skipwords)

            final_stopwords = nltk_stopwords | stop_w | spacy_stopwords
            # prnt('final_stopwords isinst list',isinstance(final_stopwords, list))
            # prnt('final_stopwords isinst set',isinstance(final_stopwords, set))
            # prnt('final_stopwords isinst dict',isinstance(final_stopwords, dict))



            
            def extract_keywords(text, n=3, top_n=6):
                kw_extractor = yake.KeywordExtractor(n=n, top=top_n, stopwords=final_stopwords)
                keywords = [kw[0] for kw in kw_extractor.extract_keywords(text)]
                return keywords

            # # keyphrases5 = extract_keywords(text, n=5, top_n=10)
            # keyphrases4 = extract_keywords(text, n=4, top_n=15)
            # keyphrases3 = extract_keywords(text, n=3, top_n=20)
            # keyphrases2 = extract_keywords(text, n=2, top_n=20)
            # keyphrases1 = extract_keywords(text, n=1, top_n=20)
            # # prntn('extracted keywords5:',keyphrases5)
            # prntn('extracted keywords4:',keyphrases4)
            # prntn('extracted keywords3:',keyphrases3)
            # prntn('extracted keywords2:',keyphrases2)
            # prntn('extracted keywords1:',keyphrases1)

            # keyps = keyphrases1[:4] + keyphrases2[:4] + keyphrases3[:4] + keyphrases4[:4]
            # # keypshorts = keyphrases1 + keyphrases2 + keyphrases3 + keyphrases4 + keyphrases5 

            # # finalks = []
            # # for k in keyphrases1[:5]:
            # #     if k not in finalks:
            # #         finalks.append(k)
            # # for k in keyphrases2[:7]:
            # #     if k not in finalks:
            # #         finalks.append(k)
            # # for k in keyphrases3[:7]:
            # #     if k not in finalks:
            # #         finalks.append(k)
            # # for k in keyphrases4[:7]:
            # #     if k not in finalks:
            # #         finalks.append(k)
            # # for k in keyphrases5[:7]:
            # #     if k not in finalks:
            # #         finalks.append(k)


            # # save all keyphrases as Keyphrase()
            # # match popular like this:
            # # matchingKeys = Keyphrase.objects.filter(key__iexact__in=keyphrases3)

            # # run some word reduction like below
            # # pick the top ones and assign to obj for public dispaly
            # # remember, all keyphrases need to be accessible by each node, not jsut ppublicly displayed keys


            # # python -m spacy download en_core_web_sm
            # # # prnt('extracted keywords6:',keywords)
            # # n = 0
            # # # terms = ''
            # keys = [keyphrases1, keyphrases2, keyphrases3]
                    

            # import yake
            # from collections import defaultdict


            # from collections import Counter
            # sub_phrase_counts = Counter(keyps)
            # prntn('keyps',sub_phrase_counts)

            spares = {}
            obj.keyword_array = []
            prntDebug('s4')
            x = extract_keywords(text, n=5, top_n=2)
            prntDebug('s4.1')
            n = 0
            terms = ''
            for i in x:
                if i not in stop_w and i not in obj.keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
            prntDebug('s5')
            prntDebug('s4')
            x = extract_keywords(text, n=4, top_n=2)
            prntDebug('s4.1')
            n = 0
            terms = ''
            for i in x:
                if i not in obj.keyword_array and i not in stop_w and i not in obj.keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
            prntDebug('s5')
            prntDebug('obj.keyword_array 00',obj.keyword_array)
            # x = kw_model.extract_keywords(text, top_n=6, keyphrase_ngram_range=(2, 2), stop_words=stop_w)
            x = extract_keywords(text, n=2, top_n=3)
            prntDebug('s6')
            n = 0
            terms = ''
            for i in x:
                if i not in stop_w and i not in obj.keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
                    obj.keyword_array.append(i)
                    n += 1
                    terms = terms + i + ' '
            prntDebug('s7')
            prntDebug('obj.keyword_array 1',obj.keyword_array)
            # x = kw_model.extract_keywords(text, top_n=7, keyphrase_ngram_range=(1, 1), stop_words=stop_w)
            x = extract_keywords(text, n=1, top_n=7)
            prntDebug('s8')
            n = 0
            for i in x:
                if i not in stop_w and not i.isnumeric():
                    if i in str(terms):
                        if i in spares:
                            spares[i] += 1
                        else:
                            spares[i] = 1
                    elif n < 7:
                        obj.keyword_array.append(i)
                        stop_w.add(i)
                        n += 1
            if spares:
                prnt('spares',spares)
                for term, count in spares.items():
                    matches = 0
                    for i in obj.keyword_array:
                        if term in i:
                            matches += 1
                    if count > matches or matches > 2:
                        for i in obj.keyword_array:
                            if term in i:
                                obj.keyword_array.remove(i)
                        obj.keyword_array.append(term)



            # def generate_sub_phrases(keyphrase, max_length=2):
            #     words = keyphrase.split()
            #     sub_phrases = []
                
            #     for length in range(max_length, 0, -1):
            #         for i in range(len(words) - length + 1):
            #             sub_phrases.append(" ".join(words[i:i + length]))
            #             # prnt('xx'," ".join(words[i:i + length]))
            #     # prnt('sub_phrases',max_length,sub_phrases)
            #     return sub_phrases
            
            # def remove_stopswords_from_ends(key, matches):
            #     try:
            #         new_key = None
            #         if key and key.split()[0] and key.split()[0] in final_stopwords:
            #             new_key = key.replace(key.split()[0], '')
            #             # prnt('key.split()[0]',key.split()[0], 'key:',key, 'new_key:',new_key)
            #         if key and key.split()[-1] and key.split()[-1] in final_stopwords:
            #             new_key = key.replace(key.split()[-1], '')
            #             # prnt('key.split()[-1]',key.split()[-1],'key:',key, 'new_key:',new_key)
            #         if new_key and new_key.strip():
            #             matches.append(new_key.strip())
            #     except Exception as e:
            #         prnt('fail1A', key, str(e))
            #     return matches

            # all_sub_phrases_final = []
            # for keyphrases in keys:
            #     all_sub_phrases = []
            #     for keyphrase in keyphrases:
            #         all_sub_phrases.extend(generate_sub_phrases(keyphrase, max_length=3))
            #     for key in all_sub_phrases:
            #         all_sub_phrases_final = remove_stopswords_from_ends(key, all_sub_phrases_final)
            # sub_phrase_counts = Counter(all_sub_phrases_final)
            # prntn('sub_phrase_counts2',sub_phrase_counts)
            # top1 = []
            # top2 = []
            # top3 = []
            # top4 = []
            # for k, v in sub_phrase_counts.items():
            #     r = remove_stopswords_from_ends(k, [])
            #     if r:
            #         k = r[0]
            #         length = len(k.split())
            #         if length == 2 and k not in top2:
            #             top2.append(k)
            #         elif length == 3 and k not in top3:
            #             top3.append(k)
            #         elif length == 4 and k not in top4:
            #             top4.append(k)
            #         elif length == 1 and k not in top1:
            #             top1.append(k)
            # prnt()
            # prnt('top1',top1)
            # prnt('top2',top2)
            # prnt('top3',top3)
            # prnt('top4',top4)

            # all_sub_phrases_final = []
            # for keyphrases in keys:
            #     all_sub_phrases = []
            #     for keyphrase in keyphrases:
            #         all_sub_phrases.extend(generate_sub_phrases(keyphrase, max_length=3))
            #     for key in all_sub_phrases:
            #         all_sub_phrases_final = remove_stopswords_from_ends(key, all_sub_phrases_final)
            # sub_phrase_counts = Counter(all_sub_phrases_final)
            # prntn('sub_phrase_counts3',sub_phrase_counts)
            # top1 = []
            # top2 = []
            # top3 = []
            # top4 = []
            # for k, v in sub_phrase_counts.items():
            #     r = remove_stopswords_from_ends(k, [])
            #     if r:
            #         k = r[0]
            #         length = len(k.split())
            #         if length == 2 and k not in top2:
            #             top2.append(k)
            #         elif length == 3 and k not in top3:
            #             top3.append(k)
            #         elif length == 4 and k not in top4:
            #             top4.append(k)
            #         elif length == 1 and k not in top1:
            #             top1.append(k)
            # prnt()
            # prnt('top1',top1)
            # prnt('top2',top2)
            # prnt('top3',top3)
            # prnt('top4',top4)


            # all_sub_phrases = []
            # for keyphrase, value in sub_phrase_counts.items():
            #     all_sub_phrases.extend(generate_sub_phrases(keyphrase, max_length=4))
            # sub_phrase_counts = Counter(all_sub_phrases)
            # prntn('sub_phrase_counts4',[i for i, v in sub_phrase_counts.items() if i not in final_stopwords])
            # for keyphrase, value in sub_phrase_counts.items():
            #     all_sub_phrases.extend(generate_sub_phrases(keyphrase, max_length=3))
            # sub_phrase_counts = Counter(all_sub_phrases)
            # prntn('sub_phrase_counts3',[i for i, v in sub_phrase_counts.items() if i not in final_stopwords])
            # for keyphrase, value in sub_phrase_counts.items():
            #     all_sub_phrases.extend(generate_sub_phrases(keyphrase, max_length=2))
            # sub_phrase_counts = Counter(all_sub_phrases)
            # prntn('sub_phrase_counts2',[i for i, v in sub_phrase_counts.items() if i not in final_stopwords])
            # for keyphrase, value in sub_phrase_counts.items():
            #     all_sub_phrases.extend(generate_sub_phrases(keyphrase, max_length=1))
            # sub_phrase_counts = Counter(all_sub_phrases)
            # prntn('sub_phrase_counts1',[i for i, v in sub_phrase_counts.items() if i not in final_stopwords])


            # # def reduce_phrases(sub_phrase_counts, rounds=3, min_occurrence=2):
            # #     # Start with all sub-phrases
            # #     current_phrases = list(sub_phrase_counts.keys())
                
            # #     for round_num in range(rounds):
            # #         # Count sub-phrase occurrences
            # #         round_counts = Counter(current_phrases)
                    
            # #         # Filter out those below the min_occurrence threshold
            # #         filtered_phrases = [phrase for phrase, count in round_counts.items() if count >= min_occurrence]
                    
            # #         # If the number of phrases left is 1 or fewer, break early
            # #         if len(filtered_phrases) <= 1:
            # #             break
                    
            # #         # Generate new sub-phrases from the filtered ones for the next round
            # #         next_round_phrases = []
            # #         for phrase in filtered_phrases:
            # #             next_round_phrases.extend(generate_sub_phrases(phrase, max_length=len(phrase.split()) - 1))
                    
            # #         current_phrases = next_round_phrases
                
            # #     return filtered_phrases

            # # # Step 4: Apply the reduction process
            # # final_keywords = reduce_phrases(sub_phrase_counts, rounds=4)
            # # print("Final keywords:", final_keywords)


            # # def merge_keywords(keywords, n=2):
            # #     # Create a dictionary to store n-grams
            # #     ngram_dict = defaultdict(int)
                
            # #     # Process each keyword
            # #     for kw in keywords:
            # #         # Generate n-grams from the keyword
            # #         ngrams = tuple(kw.split()[:n])  # Take the first n words
            # #         ngram_dict[ngrams] += 1
                
            # #     # Return reduced list by taking the most frequent n-gram
            # #     merged_keywords = [ " ".join(ngram) for ngram in ngram_dict.keys()]
                
            # #     return merged_keywords

            # # # Example keywords from YAKE
            # # # keywords = ['union troops make', 'saw union troops', 'union troops disembarked', 'union troops destroyed', 'pursuit union troops']

            # # # Apply merging
            # # reduced_keywords = merge_keywords(keywords, n=2)
            # # prnt('reduced_keywords yake2:',reduced_keywords)
            # # reduced_keywords = merge_keywords(keywords, n=3)
            # # prnt('reduced_keywords yake3:',reduced_keywords)

            # # try:
            # #     import spacy

            # #     # Load SpaCy's English model
            # #     nlp = spacy.load("en_core_web_sm")

            # #     def lemmatize_keywords(keywords):
            # #         lemmatized_keywords = []
                    
            # #         for kw in keywords:
            # #             doc = nlp(kw)
            # #             lemmatized_keywords.append(" ".join([token.lemma_ for token in doc]))
                    
            # #         return lemmatized_keywords

            # #     # Example keywords from YAKE
            # #     # keywords = ['union troops make', 'saw union troops', 'union troops disembarked', 'union troops destroyed', 'pursuit union troops']

            # #     # Apply lemmatization
            # #     reduced_keywords = lemmatize_keywords(keywords)
            # #     prnt('reduced_keywords spacy',reduced_keywords)
            # # except Exception as e:
            # #     prnt('spacy fail', str(e))

            # # try:
            # #     from fuzzywuzzy import fuzz
            # #     from fuzzywuzzy import process

            # #     def reduce_repeats(keywords):
            # #         unique_keywords = []
                    
            # #         for keyword in keywords:
            # #             if not any(fuzz.ratio(keyword, existing_keyword) > 80 for existing_keyword in unique_keywords):
            # #                 unique_keywords.append(keyword)
                    
            # #         return unique_keywords

            # #     # Example keywords from YAKE
            # #     # keywords = ['union troops make', 'saw union troops', 'union troops disembarked', 'union troops destroyed', 'pursuit union troops']

            # #     # Apply the reduction function
            # #     reduced_keywords = reduce_repeats(keywords)
            # #     # prnt(reduced_keywords)
            # #     prnt('reduced_keywords fuzzywuzzy',reduced_keywords)
            # # except Exception as e:
            # #     prnt('fuzz fail', str(e))


            # # obj.keyword_array = []
            # # for i in reduced_keywords:
            # #     # prnt('i',i)
            # #     if i not in stop_w and i not in obj.keyword_array and n <= 3 and not i.replace(' ','').isnumeric():
            # #         # prnt('y',i)
            # #         obj.keyword_array.append(i)


            prntDebug('s9')
            prntDebug('obj.keyword_array 2',obj.keyword_array)
        
        except Exception as e:
            prnt('get_keywords fail', str(e))
            from blockchain.models import logEvent
            logEvent(e, code='59385', func='get_keywords', extra={'obj':obj.id}, log_type='Errors')
            # time.sleep(10)
        finish_time = datetime.datetime.now() - start_time
        prnt('keywords time:',finish_time)
    # logEvent('done get keyowrds', code='765343')
    return obj


# not used
def reindex_model(model):
    # table_name = model._meta.db_table
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT indexname FROM pg_indexes WHERE tablename = '{model._meta.db_table}';")
        indexes = cursor.fetchall()

    for index in indexes:
        index_name = index[0]
        prnt(f"Found index: {index_name}")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT 1 FROM pg_class WHERE relname = '{index_name}';")
                result = cursor.fetchone()

            if result:
                prnt(f"Reindexing index: {index_name}")
                with connection.cursor() as cursor:
                    cursor.execute(f"REINDEX INDEX {index_name};")
                prnt(f"Successfully reindexed {index_name}")
            else:
                prnt(f"Index {index_name} does not exist in pg_class, skipping.")
        except Exception as e:
            prnt(f"Error during reindexing {index_name}: {e}")




# Example of usage:
# reindex_model(MyModel)

# from django.db import connection
# from django.db.models import Index
# from django.contrib.postgres.indexes import GinIndex

# def reindex_model(model_class):
#     try:
#         # Reindex GinIndexes (e.g., for JSONField)
#         gin_indexes = [index for index in model_class._meta.indexes if isinstance(index, GinIndex)]
#         for gin_index in gin_indexes:
#             index_name = gin_index.name
#             prnt(f"Reindexing GinIndex: {index_name}")
#             with connection.cursor() as cursor:
#                 cursor.execute(f"REINDEX INDEX {index_name};")
        
#         # Reindex regular db_index fields (e.g., for CharField, IntegerField)
#         for field in model_class._meta.get_fields():
#             if getattr(field, 'db_index', False):
#                 index_name = f"{model_class._meta.db_table}_{field.name}_idx"
#                 prnt(f"Reindexing db_index: {index_name}")
#                 with connection.cursor() as cursor:
#                     cursor.execute(f"REINDEX INDEX {index_name};")
    
#     except Exception as e:
#         prnt(f"Error during reindexing: {e}")

# # Example usage
# reindex_model(YourModel)


# def reindex_model(model_class, entire_table=False):
#     from django.db import connection
#     from django.db.models import Index
#     from django.contrib.postgres.indexes import GinIndex
#     """
#     Reindexes both Gin indexes and regular db_index fields for a given model.
#     """
#     try:
#         indexes = model_class._meta.indexes
        
#         gin_indexes = [index for index in indexes if isinstance(index, GinIndex)]
#         for gin_index in gin_indexes:
#             index_name = gin_index.name
#             prnt(f"Reindexing GinIndex: {index_name}")
#             with connection.cursor() as cursor:
#                 cursor.execute(f"REINDEX INDEX {index_name};")

#         regular_indexes = [index for index in indexes if not isinstance(index, GinIndex)]
#         for regular_index in regular_indexes:
#             index_name = regular_index.name
#             prnt(f"Reindexing regular index: {index_name}")
#             with connection.cursor() as cursor:
#                 cursor.execute(f"REINDEX INDEX {index_name};")

#         if entire_table:
#             # Optional: Reindex the entire table (if needed)
#             cursor.execute(f"REINDEX TABLE {model_class._meta.db_table};")

#     except Exception as e:
#         prnt(f"Error during reindexing: {e}")
#         from blockchain.models import logEvent
#         logEvent(e, func='reindex_model', log_type='Errors')


# from your_app.models import YourModel
# enqueue_reindex(YourModel)



# from django.db import connection

# def check_index_size():
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT indexname, pg_size_pretty(pg_total_relation_size(indexrelid))
#             FROM pg_stat_user_indexes
#             WHERE relname = 'your_table_name';
#         """)
#         rows = cursor.fetchall()
#         for row in rows:
#             prnt(f"Index: {row[0]}, Size: {row[1]}")

# from django.core.management import call_command

# @shared_task
# def maintain_db_task():
#     call_command('maintain_db')

# # your_app/management/commands/maintain_db.py
# from django.core.management.base import BaseCommand
# from django.db import connection

# class Command(BaseCommand):
#     help = 'Reindex and vacuum/analyze the database'

#     def handle(self, *args, **kwargs):
#         # Reindex specific index
#         self.stdout.write("Reindexing specific index...")
#         with connection.cursor() as cursor:
#             cursor.execute("REINDEX INDEX gin_index_jsonb_ops;")
#         self.stdout.write(self.style.SUCCESS("Reindexed specific index"))

#         # Vacuum and Analyze table
#         self.stdout.write("Vacuuming and analyzing table...")
#         with connection.cursor() as cursor:
#             cursor.execute("VACUUM ANALYZE your_table_name;")
#         self.stdout.write(self.style.SUCCESS("Vacuumed and analyzed table"))

#         # Add any other maintenance steps here

#         self.stdout.write(self.style.SUCCESS("Database maintenance completed"))






# x = ['last_updated', 'DateTime', 'created', 'created', 'added']
# prnt('x',x)
# for i in x:
#     prntDebug('I',i)
#     if not has_field(obj, i):
#         prntDebug('removing ',i)
#         x.remove(i)
#     else:
#         prntDebug('has field', i)

# x,['last_updated', 'DateTime', 'created', 'created', 'added']
#  * I,last_updated
#  * has field,last_updated
#  * I,DateTime
#  * removing ,DateTime
#  * I,created
#  * has field,created
#  * I,added
#  * has field,added



def get_object_size_in_mb(data, do_serial=False):
    # Serialize the object to JSON
    if do_serial:
        from django.core.serializers import serialize
        serialized_data = serialize('json', [data])  # Wrap the object in a list
    else:
        serialized_data = data
    # Calculate the size in bytes
    size_in_bytes = len(serialized_data.encode('utf-8'))
    # Convert to megabytes
    size_in_mb = size_in_bytes / (1024 * 1024)
    return size_in_mb

# BIG Fail cannot access local variable 'driver' where it is not associated with a value
# brew upgrade chromedriver --cask

# # not used
# def update_database():
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

# def daily_summarizer(today):
#     prnt('run daily')
#     # sozed = User.objects.get(username='Sozed')
#     # sozed.alert('%s-%s' %(datetime.datetime.now(), 'minute run', 'body'))
#     if not today:
#         # today = date.today() - datetime.timedelta(days=16)
#         today = date.today()
#     thisMorning = datetime.datetime.combine(today, datetime.datetime.min.time())
#     yesterdayMorning = today - datetime.timedelta(days=1)
#     prnt(thisMorning)
#     prnt(yesterdayMorning)
#     try:
#         houseHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization='House')[0]
#     except:
#         houseHansard = None
#     try:
#         senateHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization='Senate')[0]
#     except:
#         senateHansard = None
#     prnt('hnsards:')
#     prnt(houseHansard)
#     prnt(senateHansard)

#     def run(item, houseHansard, senateHansard):
#         prnt('------run', today)
#         houseTopics = [('None', 0)]
#         senateTopics = [('None', 0)]
#         provTopics = [('None', 0)]
#         user = None
#         province= None
#         line2 = ''
#         line3 = ''
#         line4 = ''
#         line5 = ''
#         line6 = ''
#         text1 = ''
#         text2 = ''
#         text3 = ''
#         text4 = ''
#         text5 = ''
#         text6 = ''
#         if houseHansard:
#             houseTopics = houseHansard.list_all_terms()
#         if senateHansard:
#             senateTopics = senateHansard.list_all_terms()
#         if not item:
#             prnt('not item')
#             if houseHansard and senateHansard:
#                 line1 = 'The House and Senate were in session'
#             elif houseHansard:
#                 line1 = 'The House was in session'
#             elif senateHansard:
#                 line1 = 'The Senate was in session'
#             # prnt(line1)
#             latestBills = Bill.objects.filter(LatestBillEventDateTime__gte=yesterdayMorning, LatestBillEventDateTime__lte=thisMorning).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true'))
#             # if latestBills.count() > 1:
#             line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s, %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode, latestBills[0].ShortTitle) 
#             # elif latestBills.count() > 0:
#             #     line2 = "<a href='/bill?date=%ss'>%s Bills</a> were discussed including <a href='%s'>Bill %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode) 
#             # prnt(line2)
#             latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate'))
#             passedMotions = 0
#             for m in latestMotions:
#                 if m.yeas > m.nays:
#                     passedMotions += 1
#             if latestMotions.count() > 1:
#                 line3 = "<a href='/motions?date=%s'>%s Motions</a> were held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
#                 text3 = "%s Motions were held, %s Passed" %(latestMotions.count(), passedMotions)
            
#             elif latestMotions.count() == 1:
#                 line3 = "<a href='/motions?date=%s'>%s Motion</a> was held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
#                 text3 = "%s Motion was held, %s Passed" %(latestMotions.count(), passedMotions)
            
#             topTopics = {}
#             if houseHansard:
#                 for key, value in houseTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(houseHansard.get_absolute_url(), key)]
#             if senateHansard:
#                 for key, value in senateTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(senateHansard.get_absolute_url(), key)]

#             topTopics = sorted(topTopics.items(), key=operator.itemgetter(1),reverse=True)
#             # prnt(topTopics)
#             if len(topTopics) > 0:
#                 q = list(topTopics)
#                 line6 = "<a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a> and <a href='/topic/%s?date=%s'>(%s) %s</a>" %(q[0][0], yesterdayMorning, q[0][1][0], q[0][0], q[1][0], yesterdayMorning, q[1][1][0], q[1][0],  q[2][0], yesterdayMorning, q[2][1][0], q[2][0], q[3][0], yesterdayMorning, q[3][1][0], q[3][0])
#             # prnt(line6)
#         elif item.object_type == 'province':
#             # prnt('item province')
#             province = item
#             try:
#                 provHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization=province.name +'-Assembly')[0]
#                 provTopics = provHansard.list_all_terms()
#             except:
#                 provHansard = None
#             if houseHansard and senateHansard and provHansard:
#                 line1 = 'The House, Senate and Assembly were in session'
#             elif houseHansard and provHansard:
#                 line1 = 'The House and Assembly were in session'
#             elif provHansard and senateHansard:
#                 line1 = 'The Senate and Assembly were in session'
#             elif houseHansard and senateHansard:
#                 line1 = 'The House and Senate were in session'
#             elif provHansard:
#                 line1 = 'The Assembly was in session'
#             elif houseHansard:
#                 line1 = 'The House was in session'
#             elif senateHansard:
#                 line1 = 'The Senate was in session'

#             latestBills = Bill.objects.filter(LatestBillEventDateTime__gte=yesterdayMorning, LatestBillEventDateTime__lte=thisMorning).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true')|Q(province=province))
#             # if latestBills.count() > 1:
#             #     line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s</a> and <a href='%s'>Bill %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode, latestBills[1].get_absolute_url(), latestBills[1].NumberCode) 
#             # elif latestBills.count() > 0:
#             line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s, %s</a>" %(yesterdayMorning, latestBills.count(), latestBills[0].get_absolute_url(), latestBills[0].NumberCode, latestBills[0].ShortTitle) 
            
#             latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate')|Q(OriginatingChamberName=province.name +'-Assembly'))
#             passedMotions = 0
#             for m in latestMotions:
#                 if m.yeas > m.nays:
#                     passedMotions += 1
#             if latestMotions.count() > 1:
#                 line3 = "<a href='/motions?date=%s'>%s Motions</a> were held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
#                 text3 = "%s Motions were held, %s Passed" %(latestMotions.count(), passedMotions)
            
#             elif latestMotions.count() == 1:
#                 line3 = "<a href='/motions?date=%s'>%s Motion</a> was held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
#                 text3 = "%s Motion was held, %s Passed" %(latestMotions.count(), passedMotions)
            
            
#             topTopics = {}
#             if houseHansard:
#                 # prnt(houseTopics)
#                 for key, value in houseTopics:
#                     if key not in skipwords:
#                         # prnt('--%s--' %(key))
#                         topTopics[key] = [value, "%s/?topic=%s" %(houseHansard.get_absolute_url(), key)]
#             if senateHansard:
#                 for key, value in senateTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(senateHansard.get_absolute_url(), key)]
#             if provHansard:
#                 for key, value in provTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(provHansard.get_absolute_url(), key)]
#             topTopics = sorted(topTopics.items(), key=operator.itemgetter(1),reverse=True)
#             if len(topTopics) > 0:
#                 q = list(topTopics)
#                 line6 = "<a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a> and <a href='/topic/%s?date=%s'>(%s) %s</a>" %(q[0][0], yesterdayMorning, q[0][1][0], q[0][0], q[1][0], yesterdayMorning, q[1][1][0], q[1][0],  q[2][0], yesterdayMorning, q[2][1][0], q[2][0], q[3][0], yesterdayMorning, q[3][1][0], q[3][0])

#         elif item.object_type == 'user':
#             # prnt('item user')
#             user = item
#             try:
#                 province = user.province
#             except:
#                 pass
#             try:
#                 provHansard = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Organization=province.name +'-Assembly')[0]
#                 provTopics = provHansard.list_all_terms()
#             except:
#                 provHansard = None
#             if houseHansard and senateHansard and provHansard:
#                 line1 = 'The House, Senate and Assembly were in session'
#             elif houseHansard and provHansard:
#                 line1 = 'The House and Assembly were in session'
#             elif provHansard and senateHansard:
#                 line1 = 'The Senate and Assembly were in session'
#             elif houseHansard and senateHansard:
#                 line1 = 'The House and Senate were in session'
#             elif provHansard:
#                 line1 = 'The Assembly was in session'
#             elif houseHansard:
#                 line1 = 'The House was in session'
#             elif senateHansard:
#                 line1 = 'The Senate was in session'
            
#             latestBills = Bill.objects.filter(LatestBillEventDateTime__gte=yesterdayMorning, LatestBillEventDateTime__lte=thisMorning).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true')|Q(province=province))
#             matchedBills = []
#             # prnt('start')
#             for b in latestBills:
#                 if b in user.follow_bill.all():
#                     matchedBills.append(b)
#             # prnt(matchedBills)
#             if len(matchedBills) == 0:
#                 for b in latestBills[:2]:
#                     matchedBills.append(b)
#             # prnt(matchedBills)
#             if len(matchedBills) > 1:
#                 line2 = "<a href='/bills?date=%s'>%s Bills</a> were discussed including <a href='%s'>Bill %s, %s</a>" %(yesterdayMorning, latestBills.count(), matchedBills[0].get_absolute_url(), matchedBills[0].NumberCode, matchedBills[0].ShortTitle) 
#                 text2 = "%s Bills were discussed including Bill %s, %s" %(latestBills.count(), matchedBills[0].NumberCode, matchedBills[1].ShortTitle) 
#             elif len(matchedBills) > 0:
#                 line2 = "<a href='%s'>Bill %s, %s</a> was discussed" %(matchedBills[0].get_absolute_url(), matchedBills[0].NumberCode, matchedBills[0].ShortTitle) 
#                 text2 = "Bill %s was discussed, %s" %(matchedBills[0].NumberCode, matchedBills[0].ShortTitle) 
            
#             if provHansard:
#                 latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate')|Q(OriginatingChamberName=province.name +'-Assembly'))
#             else:
#                 latestMotions = Motion.objects.filter(date_time__gte=yesterdayMorning, date_time__lte=thisMorning).filter(Q(OriginatingChamberName='House')|Q(OriginatingChamberName='Senate'))
#             passedMotions = 0
#             for m in latestMotions:
#                 if m.yeas > m.nays:
#                     passedMotions += 1
#             if latestMotions.count() > 1:
#                 line3 = "<a href='/motions?date=%s'>%s Motions</a> were held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
#                 text3 = "%s Motions were held, %s Passed" %(latestMotions.count(), passedMotions)
            
#             elif latestMotions.count() == 1:
#                 line3 = "<a href='/motions?date=%s'>%s Motion</a> was held, %s Passed" %(yesterdayMorning, latestMotions.count(), passedMotions)
#                 text3 = "%s Motion was held, %s Passed" %(latestMotions.count(), passedMotions)
            

#             topTopics = {}
#             if houseHansard:
#                 for key, value in houseTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(houseHansard.get_absolute_url(), key)]
#             if senateHansard:
#                 for key, value in senateTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(senateHansard.get_absolute_url(), key)]
#             if provHansard:
#                 for key, value in provTopics:
#                     if key not in skipwords:
#                         topTopics[key] = [value, "%s/?topic=%s" %(provHansard.get_absolute_url(), key)]
#             original_topTopics = topTopics
#             topTopics = sorted(topTopics.items(), key=operator.itemgetter(1),reverse=True)
            
#             matchedKeys = {}
#             # prnt(user.get_follow_topics())
#             keys = []
#             if len(user.get_follow_topics()) > 0:
#                 n = 0
#                 for key in user.get_follow_topics():
#                     # prnt(key)
#                     if key in topTopics:
#                         matchedKeys[key] = topTopics[key][0][0]
#                         n += 1
#                         if n == 3:
#                             break
#                 if n < 3 and user.keywords:
#                     firstKeys = user.keywords
#                     counter = Counter(firstKeys)
#                     userKeys = counter.most_common(300)
#                     # prnt(userKeys)
#                     # for topic in topTopics:
#                     #     # prnt(topic[0])
#                     #     if topic[0] in user.keywords and topic[0] not in skipwords:
#                     #         # prnt(topic[0], topic[1][0])
#                     #         matchedKeys[topic[0]] = topic[1][0]
#                     #         n += 1
#                     #         if n == 3:
#                     #             break
#                     topicList = []
#                     for t in topTopics:
#                         if t[0] not in topicList:
#                             topicList.append(t[0])
#                     for key in userKeys:
#                         # prnt(key[0])
#                         if key[0] in topicList:
#                             matchedKeys[key[0]] = original_topTopics[key[0]][0]
#                             n += 1
#                             if n == 3:
#                                 break
#                 # prnt(matchedKeys)
#                 keys = list(matchedKeys)
#                 # prnt(keys)
#                 for key in keys[:3]:
#                     line4 = line4 + "<a href='/topic/%s?date=%s'>(%s) %s</a>, " %(key, yesterdayMorning, matchedKeys[key], key)
#                     text4 = text4 + "(%s) %s, " %(matchedKeys[key], key)

#                 x = line4.rfind(',')
#                 if len(matchedKeys) > 1:
#                     w = ' were'
#                 else:
#                     w = ' was'
#                 if line4:
#                     line4 = line4[:x] + '%s discussed' %(w)
#                     if len(matchedKeys) > 1:
#                         x = line4.rfind(',')
#                         line4 = line4[:x] + ' and ' + line4[x+1:]

#                     x = text4.rfind(',')
#                     text4 = text4[:x] + '%s discussed' %(w)
#                     if len(matchedKeys) > 1:
#                         x = text4.rfind(',')
#                         text4 = text4[:x] + ' and ' + text4[x+1:]

#                 # if len(keys) == 3:
#                 #     line4 = "<a href='/topic/%s'>(%s) %s</a>, <a href='/topic/%s'>(%s) %s</a> and <a href='/topic/%s'>(%s) %s</a> were discussed" %(keys[0][0], keys[0][1], keys[0][0], keys[1][0], keys[1][1], keys[1][0], keys[2][0], keys[2][1], keys[2][0])
#                 # elif len(keys) == 2:
#                 #     line4 = "<a href='/topic/%s'>(%s) %s</a> and <a href='/topic/%s'>(%s) %s</a> were discussed" %(keys[0][0], keys[0][1], keys[0][0], keys[1][0], keys[1][1], keys[1][0])
#                 # elif len(keys) == 1:
#                 #     line4 = "<a href='/topic/%s'>(%s) %s</a> was discussed" %(keys[0][0], keys[0][1], keys[0][0])
#             # prnt('----', topTopics)
#             if len(topTopics) > 0:
#                 q = []
#                 n = 0
#                 for t in topTopics:
#                     # prnt(t)
#                     if t[0] not in keys and t[0] not in skipwords:
#                         # prnt('append')
#                         q.append(t)
#                         n += 1
#                         if n == 4:
#                             break
#                 # prnt(q)z]
#                 # q = list(topTopics)
#                 line6 = "<a href='/topic/%s?date=%s'>(%s) %s,</a> <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>, <a href='/topic/%s?date=%s'>(%s) %s</a>" %(q[0][0], yesterdayMorning, q[0][1][0], q[0][0], q[1][0], yesterdayMorning, q[1][1][0], q[1][0],  q[2][0], yesterdayMorning, q[2][1][0], q[2][0], q[3][0], yesterdayMorning, q[3][1][0], q[3][0])
#                 text6 = "(%s) %s, (%s) %s, (%s) %s, (%s) %s" %(q[0][1][0], q[0][0], q[1][1][0],  q[1][0], q[2][1][0], q[2][0], q[3][1][0], q[3][0])

#             # prnt(user.follow_person.all())
#             if user.follow_person.all().count() > 0:
#                 if provHansard:
#                     hansards = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Q(Organization='Senate')|Q(Organization='House')|Q(Organization=province.name +'-Assembly'))
#                 else:
#                     hansards = Hansard.objects.filter(Publication_date_time__gte=yesterdayMorning, Publication_date_time__lte=thisMorning, has_transcript=True).filter(Q(Organization='Senate')|Q(Organization='House'))
#                 personMatches = {}
#                 for person in user.follow_person.all():
#                     # prnt(person)
#                     try:
#                         # prnt(hansards)
#                         hansardItem = HansardItem.objects.filter(hansard__in=hansards, person=person)[0]
#                         # prnt(hansardItems)
#                         personMatches[person] = '%s?speaker=%s&date=%s' %(hansardItem.hansard.get_absolute_url(), person.id, yesterdayMorning)
#                     except Exception as e: 
#                         prnt(str(e))
#                 people = list(personMatches)
#                 # prnt(personMatches)
#                 if len(people) > 1:
#                     for person in people[:4]:
#                         personLink = personMatches[person]
#                         line5 = line5 + "<a href='/%s'>%s</a>, " %(personLink, str(person.get_name()))
#                         text5 = text5 + "%s, " %(str(person.get_name())) 
#                     x = line5.rfind(',')
#                     line5 = line5[:x] + ' spoke in Parliament'
#                     x = line5.rfind(',')
#                     line5 = line5[:x] + ' and ' + line5[x+1:]

#                     x = text5.rfind(',')
#                     text5 = text5[:x] + ' spoke in Parliament'
#                     x = text5.rfind(',')
#                     text5 = text5[:x] + ' and ' + text5[x+1:]

#                     # line5 = "<a href='%s'>%s</a> and <a href='%s'>%s</a> spoke in Parliament" %(people[0][1], people[0][0].get_name(), people[1][1], people[1][0].get_name())
#                     # text5 = "%s and %s spoke in Parliament" %(people[0][0].get_name(), people[1][0].get_name())
#                 elif len(people) == 1:
#                     # prnt('2,', people)
#                     person = people[0]
#                     personLink = personMatches[people[0]]
#                     # prnt(person)
#                     try:
#                         terms = {}
#                         hansardItems = HansardItem.objects.filter(hansard__in=hansards, person=person)
#                         for hansardItem in hansardItems:
#                             # prnt(hansardItem)
#                             for t in hansardItem.Terms:
#                                 # prnt(t)
#                                 if t not in skipwords:
#                                     if t not in terms:
#                                         terms[t] = 1
#                                     else:
#                                         terms[t] += 1
#                         # prnt(terms)
#                         H_terms = sorted(terms.items(), key=operator.itemgetter(1),reverse=True)
                        
#                         # prnt('222')
#                         # prnt(H_terms)
#                         # prnt(person.id)
#                         # prnt(H_terms[0])
#                         termLink = "%s?topic=%s&speaker=%s&date=%s" %(hansardItems[0].hansard.get_absolute_url(), H_terms[0][0], person.id, yesterdayMorning)
#                         # prnt(termLink)
#                         if len(H_terms) > 1:
#                             total = len(H_terms) - 1
#                             line5 = "<a href='%s'>%s</a> spoke on <a href='%s'>%s</a> and %s other topics" %(personLink, person.get_name(), termLink, H_terms[0][0], total)
#                             text5 = "%s spoke on %s and %s other topics" %(person.get_name(), H_terms[0][0], total)
#                         else:
#                             line5 = "<a href='%s'>%s</a> spoke on <a href='%s'>%s</a>" %(personLink, person.get_name(), termLink, H_terms[0][0])
#                             text5 = "%s spoke on %s" %(person.get_name(), H_terms[0][0])
#                         # prnt('---------------------',line5)
#                     except Exception as e:
#                         prnt(str(e))

#         code = '<li>' + line1 + '</li>' + '\n<br>' 
#         if line2:
#             code = code + '<li>' + line2 + '</li>' + '\n' 
#         if line3:
#             code = code + '<li>' + line3 + '</li>' + '\n'
#         if user:
#             if line4:
#                 code = code + '<li>' + line4 + '</li>' + '\n'
#             if line5:
#                 code = code + '<li>' + line5 + '</li>' + '\n'
#         code = code + '<br>' + '<li>Top Topics:</li>' + '\n' + '<li>' + line6 + '</li>'

#         text = line1 + '\n\n' 
#         if text2:
#             text = text + text2 + '\n' 
#         if text3:
#             text = text + text3 + '\n'
#         if user:
#             if text4:
#                 text = text + text4 + '\n' 
#             if text5:
#                 text = text + text5 + '\n'
#         text = text + '\n' + 'Top Topics:' + '\n' + text6 
#         return code, text


#     thisMorning = datetime.datetime.combine(today, datetime.datetime.min.time())
#     yesterday = thisMorning - datetime.timedelta(days=1)
#     try:
#         code, text = run(None, houseHansard, senateHansard)
#         try:
#             daily = Daily.objects.filter(date_time=thisMorning - datetime.timedelta(days=1), organization='Federal')[0]
#         except:
#             daily = Daily(date_time=thisMorning - datetime.timedelta(days=1), organization='Federal')
#         daily.content = code
#         daily.create_post()
#         try:
#             n = Notification.objects.filter(title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())[0]
#         except:
#             n = Notification(title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())
#         # n.save()
#         # n.created = yesterday    
#             n.save()
#     except Exception as e:
#         prnt('FFAAAIILLL1111111', str(e))

#     for p in Province.objects.filter(is_supported=True):
#         try:
#             code, text = run(p, houseHansard, senateHansard)
#             try:
#                 daily = Daily.objects.filter(date_time=thisMorning - datetime.timedelta(days=1), organization=p.name)[0]
#             except:
#                 daily = Daily(date_time=thisMorning - datetime.timedelta(days=1), organization=p.name)
#             daily.content = code
#             daily.create_post()
#             try:
#                 n = Notification.objects.filter(province=p, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())[0]
#             except:
#                 n = Notification(province=p, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())
#             # n.save()
#             # n.created = yesterday    
#                 n.save()
#         except Exception as e:
#             prnt('FFAAAIILLL1122222222', str(e))

#     for u in User.objects.all():
#         try:
#             code, text = run(u, houseHansard, senateHansard)
#             try:
#                 alert = False
#                 daily = Daily.objects.filter(date_time=thisMorning - datetime.timedelta(days=1), user=u)[0]
#             except:
#                 alert = True
#                 daily = Daily(date_time=thisMorning - datetime.timedelta(days=1), user=u)
#             daily.content = code
#             daily.create_post()
#             # try:
#             #     n = Notification.objects.filter(user=u, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())[0]
#             # except:
#             #     n = Notification(user=u, title='%s in Parliament' %(yesterdayMorning), link=daily.get_absolute_url())
#             # # n.save()
#             # # n.created = yesterday    
#             #     n.save()
#             if alert:
#                 u.alert('Yesterday in Parliament', daily.get_absolute_url(), text)
        
#         except Exception as e:
#             prnt('FFAAAIILL3333333331', str(e))
#     # prnt('1------')
#     # prnt(code)
#     # prnt('2------')
#     # prnt(text)

# def send_notifications(value):
#     prnt('running send notifications')
#     parl = Parliament.objects.filter(organization='Federal')[0]
#     if value == None:
#         users = User.objects.filter(receiveNotifications=True).order_by('-last_login')
#     else:
#         users = User.objects.filter(username=value).order_by('-last_login')
#     # prnt(users)
#     for u in users:
#         # prnt(u)
#         exclude_list = []
#         notifs = UserNotification.objects.filter(user=u)[:100]
#         for n in notifs:
#             exclude_list.append(n.link)
#         if u.province:
#             prov = Parliament.objects.filter(organization=u.province.name)[0]
#         else:
#             prov = None
#         # try:
#         try:
#             # find something of interest
#             counter = Counter(u.keywords)
#             commonKeys = counter.most_common()
#             # prnt(commonKeys)
#             bills = Bill.objects.exclude(absolute_url__in=exclude_list).filter(Q(IsHouseBill='true')|Q(IsSenateBill='true')|Q(province=u.province)).filter(keywords__overlap=u.keywords).exclude(bill_text_html=None).filter(LatestBillEventDateTime__gte=datetime.datetime.now()-datetime.timedelta(days=30)).order_by('?')
#             querylist = {}
#             for b in bills:
#                 q = [s for s in commonKeys if any(xs in s for xs in b.keywords)]
#                 for w in q:
#                     if w[0] not in skipwords:
#                         if b in querylist:
#                             querylist[b] += w[1]
#                         else:
#                             querylist[b] = w[1]

#             querylist = sorted(querylist.items(), key=operator.itemgetter(1),reverse=True)
#             bill = querylist[0]
#         except:
#         # if bills.count() == 0:
#             if prov:
#                 bill = Bill.objects.filter(Q(parliament=parl)|Q(parliament=prov)).exclude(absolute_url__in=exclude_list).exclude(bill_text_html=None).order_by('?')[0]
#             else:
#                 bill = Bill.objects.filter(parliament=parl).exclude(absolute_url__in=exclude_list).exclude(bill_text_html=None).order_by('?')[0]
#         title = "%s Bill %s" %(bill.OriginatingChamberName.replace('-',' '), bill.NumberCode)
#         # title = 'Bill %s' %(bill.NumberCode)
#         if bill.ShortTitle:
#             body = str(bill.ShortTitle)
#         else:
#             body = str(bill.LongTitleEn)
#         # prnt('u.alert')
#         u.alert(title=title, link=bill.get_absolute_url(), body=body)
#             # fcm_device.send_message(Message(notification=Notification(title=title), data={"click_action" : "FLUTTER_NOTIFICATION_CLICK","link" : b.get_absolute_url()}))
#             # prnt('break')
#             # break
#         # except Exception as e:
#         #     prnt(str(e))

# def check_elections():
#     elections = Election.objects.filter(end_date__lt=datetime.datetime.today(), ongoing=True)
#     for q in elections:
#         q.ongoing = False
#         q.save()


# def tester_queue():
#     start_time = datetime.datetime.now()
#     prnt(start_time)
#     prnt('\n')

#     tester()
#     # ontario.get_all_hansards('latest')
#     # get_senate_hansards('latest')
#     # start_date = '%s-%s-%s' %(2023, 2, 9)
#     # day = datetime.datetime.strptime(start_date, '%Y-%m-%d')
#     # start_day = datetime.datetime.strftime(day, '%Y-%m-%d')
#     # end_date = '%s-%s-%s' %(2023, 2, 22)
#     # day = datetime.datetime.strptime(end_date, '%Y-%m-%d')
#     # end_day = datetime.datetime.strftime(day, '%Y-%m-%d')

#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(get_agenda, 'https://www.ourcommons.ca/en/parliamentary-business/', job_timeout=200)

#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(tester, job_timeout=7200)

#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(get_all_agendas, job_timeout=7200)
    
#     # queue = django_rq.get_queue('default')
#     # queue.enqueue(get_house_hansard_or_committee, 'hansard', 'latest', job_timeout=1000)
    
#     # jt = Person.objects.filter(first_name='Justin', last_name='Trudeau')[0]
#     # keywords = Keyphrase.objects.filter(text=jt.first_last())
#     # for k in keywords:
#     #     prnt(k)
#     # # get_all_MPs('alltime')
#     # # get_senators()
#     # # set_party_colours()
#     # # get_all_bills('latest')
#     # get_all_bills('alltime')
#     # get_all_agendas() #includes house committees and house hansards
#     # get_committee_work('latest')
#     # get_latest_house_motions()
#     # # # get_all_house_motions()
#     # get_senate_motions('latest')

#     # # get_all_senate_committees()
#     # get_latest_senate_committees('past')
#     # get_senate_committee_work('latest')
#     # get_senate_hansards('latest')
#     # get_senate_agenda('latest')
#     # # get_all_past_mps()
#     prnt('\n')
#     prnt('done')
#     end_time = datetime.datetime.now()
#     prnt(end_time - start_time)


# def tester():
#     prnt('test success')
#     start_time = datetime.datetime.now()
    
    
#     # versions = ['First Reading','Second Reading','Third Reading','Royal Assent']
#     # for version in versions:
#     #     try:
#     #         v = BillVersion.objects.filter(bill=bill, version=version)[0]
#     #     except:
#     #         v = BillVersion(bill=bill, version=version, code=bill.NumberCode, province=prov)
#     #         if version == 'First Reading':
#     #             v.current = True
#     #             v.empty = False
#     #         v.save()
#     #         v.create_post()
    
#     # versions = ['House First Reading', 'House Second Reading','House Third Reading', 'Senate First Reading', 'Senate Second Reading', 'Senate Third Reading', 'Royal Assent']
#     # for version in versions:
#     #     try:
#     #         v = BillVersion.objects.filter(bill=bill, version=version)[0]
#     #     except:
#     #         v = BillVersion(bill=bill, version=version, code=bill.NumberCode)
#     #         if origin == 'Senate':
#     #             if version == 'Senate First Reading':
#     #                 v.empty = False
#     #                 v.current = True
#     #             else:
#     #                 v.empty = True
#     #         else:
#     #             if version == 'House First Reading':
#     #                 v.empty = False
#     #                 v.current = True
#     #             else:
#     #                 v.empty = True
#     #         v.save()
#     #         v.create_post()
#     try:
#         c = Country.objects.filter(name='USA')[0]
#         prnt(c)
#     except:
#         c = Country(name='USA')
        
#         prnt(c, 'created')
#     c.menu_items = []
#     c.menu_items.append('Bills')
#     c.menu_items.append('Debates')
#     c.menu_items.append('Rolls')
#     # c.menu_items.append('Committees')
#     c.menu_items.append('Officials')
#     c.menu_items.append('Elections')
#     c.save()


#     # updateTop()
    
#     # start_date = '%s-%s-%s' %(2023, 12, 1)
#     # prnt(start_date)
#     # day = datetime.datetime.strptime(start_date, '%Y-%m-%d')
#     # hansards = Hansard.objects.filter(Publication_date_time__gte=day)
#     # def run(b):
#     #     if b.summarySpren:
#     #         try:
#     #             spren = Spren.objects.filter(bill=b, type='summary')[0]
#     #         except:
#     #             spren = Spren(bill=b, type='summary')
#     #         spren.content = b.summarySpren
#     #         spren.save()
#     #     if b.steelmanSprenFor:
#     #         try:
#     #             spren = Spren.objects.filter(bill=b, type='steelfor')[0]
#     #         except:
#     #             spren = Spren(bill=b, type='steelfor')
#     #         spren.content = b.steelmanSprenFor
#     #         spren.save()
#     #     if b.steelmanSprenAgainst:
#     #         try:
#     #             spren = Spren.objects.filter(bill=b, type='steelagainst')[0]
#     #         except:
#     #             spren = Spren(bill=b, type='steelagainst')
#     #         spren.content = b.steelmanSprenAgainst
#     #         spren.save()
#     #     # b.getSpren(False)

#     # parl1 = Parliament.objects.filter(country='Canada', organization='Ontario')[0]
#     # parl2 = Parliament.objects.filter(country='Canada', organization='Federal')[0]
#     # bills1 = Bill.objects.filter(parliament=parl1)
#     # prnt(bills1.count())
#     # time.sleep(3)
#     # for b in bills1:
#     #     run(b)
#     # bills2 = Bill.objects.filter(parliament=parl2)
#     # prnt(bills2.count())
#     # time.sleep(3)
#     # for b in bills2:
#     #     run(b)

    
#     # hansard = Hansard.objects.exclude(Organization='Senate').exclude(Organization='House').order_by('-Publication_date_time')[0]
#     # hansard = Hansard.objects.filter(Organization='Senate').order_by('-Publication_date_time')[2]
#     # hansard = Hansard.objects.filter(Organization='House').order_by('-Publication_date_time')[2]
#     # x = 0
#     # for hansard in hansards:
#     #     n = 0
#     #     t = 0
#     #     for topic in hansard.Terms:
#     #         t += 1
#     #         search = ['%s'%(topic)]
#     #         posts = Post.objects.filter(hansardItem__hansard=hansard).filter(Q(hansardItem__Terms__overlap=search)|Q(hansardItem__keywords__overlap=search)).select_related('hansardItem__person', 'hansardItem').order_by('date_time')
#     #         num_tokens, text = makeText(posts)
#     #         if posts.count() >= 5 and num_tokens >= 600 or num_tokens > 1200:
#     #             prnt(topic, num_tokens, posts.count())
#     #             # summarize_topic(hansard, topic)
#     #             try:
#     #                 spren = Spren.objects.filter(hansard=hansard, topic=topic)[0]
#     #             except:
#     #                 spren = Spren(hansard=hansard, topic=topic)
#     #                 spren.type = 'summary'
#     #                 spren.content = 'TBD'
#     #                 spren.date_time = hansard.Publication_date_time
#     #                 spren.create_post()
#     #             n += 1
#     #             x += 1
#     #     prnt('end', n, t)

#     # prnt('fini', x)
#     # prnt('---------------------senate hansards')
#     # debate = 'https://sencanada.ca/en/in-the-chamber/debates/'
#     # r = requests.get(debate)
#     # soup = BeautifulSoup(r.content, 'html.parser')
#     # links = soup.find_all('a')
#     # n = 0
#     # for a in links:
#     #     if '\content' in a['href'] and '\debates' in a['href'] and n <= 43:
#     #         n += 1
#     #         link = 'https://sencanada.ca' + a['href'].replace('\\','/')
#     #         add_senate_hansard(link, True)
#     # reactions = Reaction.objects.exclude(person=None).filter(user=None)
#     # for r in reactions:
#     #     # prnt(r)
#     #     r.delete()
#     # bs = Bill.objects.all().order_by('-LatestBillEventDateTime')
#     # bs = Bill.objects.filter(NumberCode='C-18', ParliamentNumber='44')
#     # for b in bs:
#     #     prnt(b)
#     #     p = Post.objects.filter(bill=b)
#     #     for i in p:
#     #         i.total_nays = 0
#     #         i.total_yeas = 0
#     #         i.total_votes = 0
#     #         i.save()
#     # prnt('done step 1')
#     # time.sleep(5)
#     # for b in bs:
#     #     prnt()
#     #     prnt(b)
#     #     b.NumberCode = b.NumberCode.strip()
#     #     b.save()
#     #     vs = BillVersion.objects.filter(bill=b)
#     #     for v in vs:
#     #         if v.empty:
#     #             v.delete()
#     #         else:
#     #             try:
#     #                 p = Post.objects.filter(billVersion=v)[0]
#     #             except:
#     #                 v.create_post()
#         # prnt('next')
#         # try:
#         #     def func(motion):
#         #         votes = Vote.objects.filter(motion=motion)
#         #         # prnt(votes.count())
#         #         x = 0
#         #         z = 0
#         #         f = 0
#         #         n = 0
#         #         for v in votes:
#         #             # prnt(v)
#         #             x += 1
#         #         # try:
#         #             if v.person:
#         #                 z += 1
#         #                 # prnt(v.person)
#         #                 post = Post.objects.filter(bill=motion.bill)[0]
#         #                 try:
#         #                     reaction = Reaction.objects.filter(post=post, person=v.person)[0]
#         #                     reaction.calculate_vote(v.VoteValueName, True)
#         #                     f += 1
#         #                 except:
#         #                     reaction = Reaction(post=post, person=v.person)
#         #                     reaction.save()
#         #                     reaction.calculate_vote(v.VoteValueName, False)
#         #                     n += 1
#         #         prnt(str(z)+'/'+str(x)+'||'+str(f)+'/'+str(n))
#         #         post = Post.objects.filter(bill=motion.bill)[0]
#         #         prnt(post.total_yeas, post.total_nays, post.total_votes)
#         #     motion = Motion.objects.filter(bill=b).order_by('date_time')
#         #     for m in motion:
#         #         prnt(m)
#         #         func(m)
#         #     # if motion.OriginatingChamberName == 'House':
#         #     #     motion = Motion.objects.filter(bill=b, OriginatingChamberName='Senate')[0]
#         #     #     prnt(motion)
#         #     #     func(motion)
#         #     # elif motion.OriginatingChamberName == 'Senate':
#         #     #     motion = Motion.objects.filter(bill=b, OriginatingChamberName='House')[0]
#         #     #     prnt(motion)
#         #     #     func(motion)

#         # except Exception as e:
#         #     prnt(str(e))

    
    
#     prnt('done', datetime.datetime.now() - start_time)
    

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
#                 from posts.utils import summarize_topic
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

# def set_party_colours():
#     try:
#         p = Party.objects.get(name='Liberal')
#         p.colour = '#ED2E38'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Conservative')
#         p.colour = '#002395'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='NDP')
#         p.colour = '#FF5800'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Bloc Québécois')
#         p.colour = '#0088CE'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.filter(name='Green Party')[0]
#         p.colour = '#427730'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Progressive Senate Group')
#         p.colour = '#ED2E38'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Canadian Senators Group')
#         p.colour = '#386B67'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Independent Senators Group')
#         p.colour = '#845B87'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Conservative Party of Canada')
#         p.colour = '#002395'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.filter(name='Progressive Conservative Party of Ontario')[0]
#         p.colour = '#002395'
#         p.save()
#     except Exception as e:
#         prnt(str(e))
#     try:
#         p = Party.objects.get(name='New Democratic Party of Ontario')
#         p.colour = '#FF5800'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.get(name='Ontario Liberal Party')
#         p.colour = '#ED2E38'
#         p.save()
#     except:
#         pass
#     try:
#         p = Party.objects.filter(name='Green Party of Ontario')[0]
#         p.colour = '#427730'
#         p.save()
#     except:
#         pass
#     prnt('done party colours')

