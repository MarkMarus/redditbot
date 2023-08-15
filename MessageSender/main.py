import time
import json
import random
import threading
from datetime import datetime

import requests

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service

# from gui import Ui_MainWindow
from PyQt5.QtWidgets import QMainWindow, QApplication


class Worker:
    def __init__(self):
        Logging().debug('Worker started')

        self.username = 'TomLoton'
        self.profile_id = "134443580"
        self.messages = ['213', '321', '000']

        self.start_browser()

    def start_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('debuggerAddress', f'127.0.0.1:{DolphinAPI().start_profile(self.profile_id)}')

        self.driver = webdriver.Chrome(service=Service('../chromedriver.exe'), options=options)
        self.actions = ActionChains(self.driver)

        self.driver.maximize_window()

        Logging().debug('Browser started')

    def create_chat(self):
        self.driver.get("https://chat.reddit.com")

        now = time.time()

        create_button = None
        while create_button is None:

            try:
                create_button = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('.container > rs-rooms-nav').shadowRoot.querySelector('a');
                """)
                create_button.click()

                time.sleep(3)

                self.input_username()
            except:
                if time.time() - now >= 30:
                    return

    def input_username(self):
        now = time.time()

        input_field = None
        while input_field is None:

            try:
                input_field = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-create').shadowRoot.querySelector('rs-users-multiselect').shadowRoot.querySelector('input');
                """)
                input_field.click()
                input_field.send_keys(self.username)

                time.sleep(3)

                self.click_user()
            except:
                if time.time() - now >= 30:
                    return

    def click_user(self):
        now = time.time()

        user = None
        while user is None:

            try:
                user = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-create').shadowRoot.querySelector('rs-users-multiselect').shadowRoot.querySelector('li');
                """)
                user.click()

                time.sleep(5)

                self.click_start()
            except:
                if time.time() - now >= 30:
                    return

    def click_start(self):
        now = time.time()

        start_btn = None
        while start_btn is None:

            try:
                start_btn = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-create').shadowRoot.querySelector('button');
                """)
                start_btn.click()

                time.sleep(3)
            except:
                if time.time() - now >= 30:
                    return

    def set_message(self):
        message = random.choice(self.messages)

        now = time.time()

        textarea = None
        while textarea is None:

            try:
                textarea = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('rs-direct-chat').shadowRoot.querySelector('rs-message-composer').shadowRoot.querySelector('textarea');
                """)
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                """, textarea, message)
                textarea.click()
                textarea.send_keys(' ')

                time.sleep(1)

                return self.send_message()
            except:
                if time.time() - now >= 30:
                    return

    def send_message(self):
        now = time.time()

        button = None
        while button is None:

            try:
                button = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-overlay-manager > rs-room').shadowRoot.querySelector('rs-message-composer').shadowRoot.querySelectorAll('button')[1];
                """)
                button.click()

                return
            except:
                if time.time() - now >= 30:
                    return


class Logging:
    def info(self, message: str):
        with open('log.txt', 'a') as f:
            f.write(f'[{datetime.now()}] INFO: {message}\n')

    def debug(self, message: str):
        with open('log.txt', 'a') as f:
            f.write(f'[{datetime.now()}] DEBUG: {message}\n')


class DolphinAPI:
    def __init__(self):
        with open('../data/token.txt') as f:
            self.token = f.readline()

    def start_profile(self, profile_id: str):
        with open('../data/token.txt') as f:
            token = f.readline()

        headers = {
            "Authorization": f"Bearer {token}"
        }

        resp = requests.get(f"http://localhost:3001/v1.0/browser_profiles/{profile_id}/start?automation=1",
                            headers=headers)

        if b"initConnectionError" in resp.content:
            return 0
        elif b"automation" not in resp.content:
            self.stop_profile(profile_id)

            time.sleep(5)

            port = self.start_profile(profile_id)
        else:
            port = resp.json()["automation"]["port"]

        return port

    def stop_profile(self, profile_id: str):
        with open('../data/token.txt') as f:
            token = f.readline()

        headers = {
            "Authorization": f"Bearer {token}"
        }

        resp = requests.get(f"http://localhost:3001/v1.0/browser_profiles/{profile_id}/stop", headers=headers)

        if b"error" in resp.content:
            time.sleep(5)

            self.stop_profile(profile_id)

    def get_profiles(self) -> dict:
        with open('../data/token.txt') as f:
            token = f.readline()

        headers = {
            "Authorization": f"Bearer {token}"
        }

        profiles = requests.get('https://anty-api.com/browser_profiles', headers=headers).json()["data"]

        return {profile["name"]: str(profile["id"]) for profile in profiles}


if __name__ == "__main__":
    with open('log.txt', 'w+') as f:
        f.write('')

    Worker()
