import time
import json
import random
import traceback
import threading
import multiprocessing
from datetime import datetime

import requests

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

from gui import Ui_MainWindow as GuiWindow
from error import Ui_MainWindow as ErrWindow

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QScrollArea, QLabel, QCheckBox


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(630, 481)

        self.ui = GuiWindow()
        self.ui.setupUi(self)

        threading.Thread(target=self.update_labels).start()

        self.ui.start_btn.clicked.connect(self.start_worker)
        self.ui.profiles_btn.clicked.connect(self.start_profiles)

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

        for profile in profiles:
            random_message = random.choice(messages)

            if random_message not in used_messages:
                multiprocessing.Process(target=Worker, args=(random_message, profile, limit, delay)).start()

    def start_profiles(self):
        self.prf_window = Prf()

        self.prf_window.setFixedSize(260, 600)
        self.prf_window.setWindowTitle("Profiles")

        self.prf_window.show()


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


class Error(QMainWindow):
    def __init__(self):
        super(Error, self).__init__()

        self.ui = ErrWindow()
        self.ui.setupUi(self)

        self.setFixedSize(403, 200)


class Worker:
    def __init__(self, message: str, profile_id: str, limit: int, delay: float):
        Logging().debug('Worker started')

        self.profile_id = profile_id
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

            if self.error:
                self.add_used_account()

                threading.Thread(target=self.show_error_window).start()

                break

            if self.current_messages_value == self.limit:
                self.add_used_account()

                Logging().info('Limit reached')

                break
            else:
                self.current_messages_value += 1

            self.username = username

            self.create_chat()

            time.sleep(self.delay)

    def show_error_window(self):
        self.err_window = Error()
        self.err_window.show()

    def start_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('debuggerAddress', f'127.0.0.1:{DolphinAPI().start_profile(self.profile_id)}')

        self.driver = webdriver.Chrome(service=Service('../chromedriver.exe'), options=options)
        self.actions = ActionChains(self.driver)

        self.driver.maximize_window()

        Logging().debug('Browser started')

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
                    data["messages_sent"] += data["messages_sent"]

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

                Logging().info('Create chat button clicked')

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

                Logging().info('Username inserted')

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

                Logging().info('User clicked')

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

                Logging().info('Chat started')

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

                Logging().info('Message inserted')

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

                Logging().info('Message sent')

                self.check_limit_error()
            except:
                if time.time() - now >= 30:
                    return Logging().debug(str(traceback.format_exc()))

    def check_limit_error(self):
        now = time.time()

        limit_error = None
        while limit_error is None:

            try:
                limit_error = self.driver.execute_script("""
                    return document.getElementsByTagName('faceplate-toast')[0];
                """)

                Logging().info('Limit error')

                self.error = True

                return
            except:
                if time.time() - now >= 5:
                    Logging().info('No limit error')

                    break

        self.check_send_error()

    def check_send_error(self):
        now = time.time()

        send_error = None
        while send_error is None:

            try:
                send_error = self.driver.execute_script("""
                    return document.querySelector('rs-app').shadowRoot.querySelector('rs-room-overlay-manager').querySelector('rs-room').shadowRoot.querySelector('main').querySelector('rs-timeline').shadowRoot.querySelector('rs-virtual-scroll-dynamic').shadowRoot.querySelector('rs-timeline-event').getElementsByClassName('error')[0];
                """)

                Logging().info('Send error')

                self.error = True

                return
            except:
                if time.time() - now >= 5:
                    Logging().info('No send error')

                    break

        self.add_message()


class Logging:
    def info(self, message: str):
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now()}] INFO: {message}\n')

    def debug(self, message: str):
        with open('log.txt', 'a', encoding='utf-8') as f:
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
