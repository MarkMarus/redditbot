import time
import json
import random
import traceback
import threading
import multiprocessing
from datetime import datetime

import requests

import subprocess

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

from gui import Ui_MainWindow as GuiWindow

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QScrollArea, QLabel, QCheckBox


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(630, 481)

        self.profiles = DolphinAPI().get_profiles()

        self.ui = GuiWindow()
        self.ui.setupUi(self)

        threading.Thread(target=self.update_labels).start()

        self.ui.start_btn.clicked.connect(lambda: threading.Thread(target=self.start_worker).start())
        self.ui.profiles_btn.clicked.connect(self.start_profiles)
        self.ui.clear_btn.clicked.connect(self.clear_users)

        Logging().debug('Interface is loaded')

    def update_labels(self):
        while True:

            while True:

                try:
                    with open('../data/sender.json') as json_file:
                        data = json.load(json_file)

                    break
                except:
                    pass

            self.ui.accounts_in_work.setText(str(data["accounts_in_work"]))
            self.ui.messages_sent.setText(str(data["messages_sent"]))
            self.ui.accounts_used.setText(str(data["accounts_used"]))

            time.sleep(0.1)

    def start_worker(self):
        messages = self.ui.list_messages.toPlainText().split('-')
        limit = int(self.ui.limit.text())
        delay = float(self.ui.delay.text().replace(',', '.'))

        with open('../data/checked_profiles.txt') as f:
            profiles = [line.strip() for line in f.readlines() if line.strip()]

        while True:

            try:
                with open('../data/sender.json', 'r') as json_file:
                    data = json.load(json_file)
                    data["accounts_in_work"] = len(profiles)
                    data["messages_sent"] = 0
                    data["accounts_used"] = 0

                break
            except:
                pass

        while True:

            try:
                with open('../data/sender.json', 'w') as json_file:
                    json.dump(data, json_file, indent=4)

                break
            except:
                pass

        used_messages = []

        for profile_name, profile_id in self.profiles.items():

            if profile_id in profiles:
                random_message = random.choice(messages)

                if random_message not in used_messages:
                    used_messages.append(random_message)

                    proc = multiprocessing.Process(target=Worker, args=(random_message, profile_id, limit, delay, profile_name))
                    proc.start()
                    proc.join()

    def start_profiles(self):
        self.prf_window = Prf()

        self.prf_window.setFixedSize(260, 600)
        self.prf_window.setWindowTitle("Profiles")

        self.prf_window.show()

    def clear_users(self):
        with open('users.txt', 'w+') as f:
            f.write('')


class Prf(QMainWindow):
    def __init__(self):
        super(Prf, self).__init__()

        self.centralWidget = QWidget(self)

        self.scrollArea = QScrollArea(self.centralWidget)
        self.scrollArea.setGeometry(0, 0, 261, 601)
        self.scrollArea.setWidgetResizable(True)

        self.profiles = DolphinAPI().get_profiles()

        profile_names = list(self.profiles.keys())

        placeholders = {
            "name": 20,
            "checkBox": 34
        }

        self.label = QLabel(self.scrollArea)

        font = QtGui.QFont()
        font.setPointSize(16)

        with open('../data/checked_profiles.txt') as f:
            checked = [line.strip() for line in f.readlines()]

        for name in profile_names:

            label_name = QLabel(self.label)
            label_name.setGeometry(20, placeholders["name"], 181, 41)
            label_name.setText(name)
            label_name.setFont(font)

            check_box = QCheckBox(self.label)
            check_box.setGeometry(210, placeholders["checkBox"], 20, 20)
            check_box.stateChanged.connect(lambda state, check=check_box, name=name: self.checkbox_state(check, name))

            if self.profiles[name] in checked:
                check_box.setCheckState(QtCore.Qt.CheckState.Checked)

            for k in placeholders.keys():
                placeholders[k] += 50

        self.label.setText("\n\n\n\n" * len(profile_names))

        self.scrollArea.setWidget(self.label)

        self.setCentralWidget(self.centralWidget)

    def checkbox_state(self, check_box: QCheckBox, name: str):
        try:
            with open('../data/checked_profiles.txt') as f:
                checked = [line.strip() for line in f.readlines()]

            if check_box.isChecked():
                if self.profiles[name] not in checked:
                    checked.append(self.profiles[name])
            else:
                if self.profiles[name] in checked:
                    checked.remove(self.profiles[name])

            with open('../data/checked_profiles.txt', 'w', encoding='utf-8') as f:
                for line in checked:
                    f.write(line + '\n')
        except:
            print(traceback.format_exc())


class Worker:
    def __init__(self, message: str, profile_id: str, limit: int, delay: float, profile_name: str):
        Logging().debug(f'[{profile_name}] Worker started')

        self.profile_id = profile_id
        self.profile_name = profile_name

        self.message = [msg for msg in message.split('\n') if msg]

        self.delay = delay

        self.limit = limit
        self.current_messages_value = 0

        self.error = False

        self.start_browser()

        while True:

            try:
                with open('../data/data.json') as json_file:
                    usernames = json.load(json_file)["data"]

                break
            except:
                pass

        for username in usernames:

            self.username = username

            is_in_list = self.get_user()
            if is_in_list:
                continue

            if self.error:
                self.add_used_account()

                threading.Thread(target=self.show_error_window).start()

                break

            if self.current_messages_value == self.limit:
                self.add_used_account()

                Logging().info(f'[{self.profile_name}] Limit reached')

                break
            else:
                self.current_messages_value += 1

            self.create_chat()

            time.sleep(random.uniform(5, self.delay))

        Logging().info(f'[{self.profile_name}] Complete')

        DolphinAPI().stop_profile(self.profile_id)

    def show_error_window(self):
        subprocess.call('python3 win.py', shell=True)

    def start_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('debuggerAddress', f'127.0.0.1:{DolphinAPI().start_profile(self.profile_id)}')

        self.driver = webdriver.Chrome(service=Service('../chromedriver'), options=options)
        self.actions = ActionChains(self.driver)

        self.driver.maximize_window()

        Logging().debug(f'[{self.profile_name}] Browser started')

    def add_used_account(self):
        while True:

            try:
                with open('../data/sender.json', 'r') as json_file:
                    data = json.load(json_file)
                    data["accounts_used"] += 1
                    
                break
            except:
                pass

        while True:

            try:
                with open('../data/sender.json', 'w') as json_file:
                    json.dump(data, json_file, indent=4)

                break
            except:
                pass

    def add_message(self):
        while True:

            try:
                with open('../data/sender.json', 'r') as json_file:
                    data = json.load(json_file)
                    data["messages_sent"] += 1

                break
            except:
                pass

        while True:

            try:
                with open('../data/sender.json', 'w') as json_file:
                    json.dump(data, json_file, indent=4)

                break
            except:
                pass

    def add_user(self):
        while True:

            try:
                with open('users.txt', 'r') as f:
                    users = [line.strip() for line in f.readlines() if line.strip()]

                break
            except:
                pass

        if self.username not in users:
            users.append(self.username)

        while True:

            try:
                with open('users.txt', 'w') as f:
                    for line in users:
                        f.write(line + '\n')

                break
            except:
                pass

    def get_user(self) -> bool:
        while True:

            try:
                with open('users.txt', 'r') as f:
                    users = [line.strip() for line in f.readlines() if line.strip()]

                break
            except:
                pass

        if self.username not in users:
            users.append(self.username)

            return False
        else:
            return True

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

                Logging().info(f'[{self.profile_name}] Create chat button clicked')

                self.input_username()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

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

                Logging().info(f'[{self.profile_name}] Username inserted')

                self.click_user()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

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

                Logging().info(f'[{self.profile_name}] User clicked')

                self.click_start()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

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

                Logging().info(f'[{self.profile_name}] Chat started')

                self.set_message()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

    def set_message(self):
        now = time.time()

        textarea = None
        while textarea is None:

            try:
                textarea = self.driver.execute_script("""
                    try {
                        return document.querySelector('rs-app').shadowRoot.querySelector('rs-direct-chat').shadowRoot.querySelector('rs-message-composer').shadowRoot.querySelector('textarea');
                    } catch (error) {
                        return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-overlay-manager > rs-room').shadowRoot.querySelector('rs-message-composer').shadowRoot.querySelector('textarea');
                    }
                """)

                textarea.click()

                for message in self.message:
                    textarea.send_keys(message)
                    time.sleep(0.2)

                    textarea.send_keys(Keys.SHIFT + Keys.ENTER)
                    time.sleep(0.5)

                time.sleep(1)

                Logging().info(f'[{self.profile_name}] Message inserted')

                self.send_message()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

    def send_message(self):
        now = time.time()

        button = None
        while button is None:

            try:
                button = self.driver.execute_script("""
                    try {
                        return document.querySelector('rs-app').shadowRoot.querySelector('rs-direct-chat').shadowRoot.querySelector('rs-message-composer').shadowRoot.querySelectorAll('button')[1];
                    } catch (error) {
                        return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-overlay-manager > rs-room').shadowRoot.querySelector('rs-message-composer').shadowRoot.querySelectorAll('button')[1];
                    }
                """)

                button.click()

                Logging().info(f'[{self.profile_name}] Message sent')

                self.check_limit_error()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

    def check_limit_error(self):
        now = time.time()

        error = None
        while error is None:

            try:
                error = self.driver.execute_script("""
                    try {
                        let limit_errors = document.getElementsByTagName('faceplate-toast');
                        if (limit_errors) {
                            for (let limit_error of limit_errors) {
                                if (!limit_error.textContent.includes('Unable to invite')) {
                                    return limit_error;
                                }
                            }
                        } else {
                            throw new Error('limit_error is null');
                        };
                    } catch (error) {
                        let tags = document.querySelector('rs-app').shadowRoot.querySelector('rs-room-overlay-manager > rs-room').shadowRoot.querySelector('rs-timeline').shadowRoot.querySelector('rs-virtual-scroll-dynamic').shadowRoot.querySelectorAll('rs-timeline-event');
                        let last_message = tags[tags.length - 1].shadowRoot.querySelector('[class="error"]');
                        console.log(last_message);
                        if (last_message) {
                            return last_message;
                        }
                    }
                """)

                if not error:
                    if time.time() - now >= 5:
                        Logging().info(f'[{self.profile_name}] No error')

                        self.add_message()
                        self.add_user()

                        break

                    continue

                Logging().info(f'[{self.profile_name}] Error')

                self.error = True

                return
            except:
                if time.time() - now >= 5:
                    Logging().info(f'[{self.profile_name}] No limit error')

                    self.add_message()
                    self.add_user()

                    break


class Logging:
    def info(self, message: str):
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now()}] INFO: {message}\n')

    def debug(self, message: str):
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now()}] DEBUG: {message}\n')


class DolphinAPI:
    def __init__(self):
        with open('../data/token.txt', encoding='utf-8') as f:
            self.token = f.readline().strip()

    def start_profile(self, profile_id: str):
        headers = {
            "Authorization": "Bearer " + self.token
        }

        resp = requests.get(f"http://localhost:3001/v1.0/browser_profiles/{profile_id}/start?automation=1",
                            headers=headers)

        Logging().info('Start - ' + str(resp.content))

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
        headers = {
            "Authorization": "Bearer " + self.token
        }

        resp = requests.get(f"http://localhost:3001/v1.0/browser_profiles/{profile_id}/stop", headers=headers)

        Logging().info('Stop - ' + str(resp.content))

        if b"error" in resp.content:
            time.sleep(5)

            self.stop_profile(profile_id)

    def get_profiles(self) -> dict:
        headers = {
            "Authorization": "Bearer " + self.token
        }

        profiles = requests.get('https://anty-api.com/browser_profiles', headers=headers).json()["data"]

        return {profile["name"]: str(profile["id"]) for profile in profiles}


if __name__ == "__main__":
    with open('log.txt', 'w+') as f:
        f.write('')

    with open('../data/sender.json', 'w') as json_file:
        json.dump({
            "accounts_in_work": 0,
            "messages_sent": 0,
            "accounts_used": 0
        }, json_file, indent=4)

    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()
