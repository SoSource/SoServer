# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
import os
import time
from selenium.webdriver.support.ui import WebDriverWait 
from selenium import webdriver 

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By 
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
# # Path to ChromeDriver
# chrome_driver_path = "/home/sozed/chrome-for-testing/chromedriver-linux64/chromedriver"  # Update this path

# # Set up Chrome options
# options = webdriver.ChromeOptions()
# options.binary_location = "/home/sozed/chrome-for-testing/chrome-linux64/chrome"  # Update this path

# # Initialize WebDriver
# service = Service(chrome_driver_path)
# driver = webdriver.Chrome(service=service, options=options)

# # Example: Open Google
# driver.get("https://www.google.com")
# print(driver.title)

# # Close the browser
# driver.quit()
from utils.models import open_browser

# import platform
# import os
# if platform.system() == 'Darwin':       # macOS
#     # subprocess.call(('open', filepath))
#     device_system = 'mac'
# elif platform.system() == 'Windows':    # Windows
#     device_system = 'windows'
#     # os.startfile(filepath)
# else:                                   # linux variants
#     device_system = 'linux'

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service

# if device_system == 'linux':
#     chrome_binary_path = os.path.expanduser("~/chrome-for-testing/chrome-linux64/chrome")
#     chromeDriver_path = os.path.expanduser("~/chrome-for-testing/chromedriver-linux64/chromedriver")
# elif device_system == 'mac':
#     chrome_binary_path = "../chrome-for-testing/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
#     chromeDriver_path = "../chrome-for-testing/chromedriver-mac-arm64/chromedriver"
# elif device_system == 'mac':
#     chrome_binary_path = "../chrome-for-testing/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
#     chromeDriver_path = "../chrome-for-testing/chromedriver-mac-arm64/chromedriver"

# options = webdriver.ChromeOptions()

# options.add_argument('--no-sandbox')
# options.add_argument("--headless")
# options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
# options.binary_location = chrome_binary_path

# service = Service(chromeDriver_path)
# driver = webdriver.Chrome(service=service, options=options)


# def open_browser(url=None, headless=True):
#     print("--opening browser")
    

#     # from selenium import webdriver
#     # from selenium.webdriver.chrome.service import Service

#     # if device_system == 'linux':
#     # chrome_binary_path = os.path.expanduser("~/chrome-for-testing/chrome-linux64/chrome")
#     # chromeDriver_path = os.path.expanduser("~/chrome-for-testing/chromedriver-linux64/chromedriver")
#     # elif device_system == 'mac':
#     chrome_binary_path = "../chrome-for-testing/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
#     chromeDriver_path = "../chrome-for-testing/chromedriver-mac-arm64/chromedriver"
#     # elif device_system == 'mac':
#     #     chrome_binary_path = "../chrome-for-testing/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
#     #     chromeDriver_path = "../chrome-for-testing/chromedriver-mac-arm64/chromedriver"

#     # from selenium import webdriver
#     # from selenium.webdriver.chrome.service import Service

#     options = webdriver.ChromeOptions()
#     options.add_argument('--no-sandbox')
#     if headless:
#         options.add_argument("--headless")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
#     options.binary_location = chrome_binary_path

#     service = Service(chromeDriver_path)
#     driver = webdriver.Chrome(service=service, options=options)

#     # driver.get(url)
#     # print(driver.title)
#     # driver.quit()

#     # chrome_options = Options()
#     # chrome_options.add_argument('--no-sandbox')
#     # chrome_options.add_argument("--headless")
#     # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
#     # driver = webdriver.Chrome(options=chrome_options)
#     # caps = DesiredCapabilities().CHROME
#     # caps["pageLoadStrategy"] = "normal"  #  Waits for full page load
#     # driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
#     if url:
#         driver.get(url)
#     return driver



driver = open_browser(headless=False)

url = 'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22118%22%2C%22chamber%22%3A%22House%22%7D'

url2 = 'https://www.congress.gov/search?pageSize=250&q=%7B%22source%22%3A%22members%22%2C%22congress%22%3A%22118%22%2C%22chamber%22%3A%22House%22%7D&page=2'
try:
    driver.get(url)
    print('loaded')
    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
    WebDriverWait(driver, 10).until(element_present)
    print('ready1')

    soup1 = BeautifulSoup(driver.page_source, 'html.parser')
except Exception as e:
    print('fail95718422',str(e))
try:
    driver.get(url2)
    print('loaded2')
    element_present = EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
    WebDriverWait(driver, 10).until(element_present)
    print('ready12')
    soup2 = BeautifulSoup(driver.page_source, 'html.parser')

except Exception as e:
    print('fail957184',str(e))
time.sleep(10)
driver.quit()


# driver.get("https://www.google.com")
# print(driver.title)
# driver.quit()




# o ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
# transformers 4.46.3 requires tokenizers<0.21,>=0.20, but you have tokenizers 0.15.2 which is incompatible.

# output--0:41:00.711252--:ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
# transformers 4.46.3 requires tokenizers<0.21,>=0.20, but you have tokenizers 0.15.2 which is incompatible.





# [eta]
# o 2024-11-21 07:30:33 (3.40 MB/s) - ‘chromedriver-linux64.zip’ saved [9925053/9925053]


# output--0:43:36.637275--:2024-11-21 07:30:33 (3.40 MB/s) - ‘chromedriver-linux64.zip’ saved [9925053/9925053]


# [eta]
# --has break
# -self.command_index 152
# -command: ['unzip', 'chromedriver-linux64.zip', '-d', '~/chrome-for-testing'] (153/188)- 
# o Archive:  chromedriver-linux64.zip

# output--0:43:36.643842--:Archive:  chromedriver-linux64.zip

# o checkdir:  cannot create extraction directory: ~/chrome-for-testing
#            No such file or directory

# output--0:43:36.644056--:checkdir:  cannot create extraction directory: ~/chrome-for-testing
#            No such file or directory

# --has break
# -self.command_index 153
# -command: ['export', 'PATH=$PATH:$HOME/chrome-for-testing/chrome-linux64/'] (154/188)- 
#  Exception in thread Thread-162 (read_output):
#  Traceback (most recent call last):
#    File "/usr/lib/python3.12/threading.py", line 1073, in _bootstrap_inner
#      self.run()
#    File "/usr/lib/python3.12/threading.py", line 1010, in run
#      self._target(*self._args, **self._kwargs)
#    File "/home/sozed/sonode/start.py", line 3712, in read_output
#      self.run_commands()
#    File "/home/sozed/sonode/start.py", line 3562, in run_commands
#      self.run_command(cmd)
#    File "/home/sozed/sonode/start.py", line 3637, in run_command
#      self.current_process = subprocess.Popen(command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, text=True)
#                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#    File "/usr/lib/python3.12/subprocess.py", line 1026, in __init__
#      self._execute_child(args, executable, preexec_fn, close_fds,
#    File "/usr/lib/python3.12/subprocess.py", line 1955, in _execute_child
#      raise child_exception_type(errno_num, err_msg, err_filename)
#  FileNotFoundError: [Errno 2] No such file or directory: 'export'
