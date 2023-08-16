import time
import json
import threading
from datetime import datetime, timedelta

import requests

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service

from gui import Ui_MainWindow
from PyQt5.QtWidgets import QMainWindow, QApplication


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(551, 479)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.profiles = DolphinAPI().get_profiles()

        self.ui.profile.addItems(list(self.profiles.keys()))

        self.ui.first_date.setDate(datetime.now())
        self.ui.second_date.setDate(datetime.now())

        self.ui.start.clicked.connect(self.start)

        Logging().debug('Interface is loaded')

    def start(self):
        Logging().debug('Start button is pressed')

        data = {
            "subreddits": self.ui.subreddits.toPlainText().split('\n'),
            "profile_id": self.profiles[self.ui.profile.currentText()]
        }

        if self.ui.use_date.isChecked():
            data["first_date"] = self.ui.first_date.text()
            data["second_date"] = self.ui.second_date.text()
        else:
            data["first_date"] = datetime.now().strftime('%d.%m.%Y')

        Logging().info(str(data))

        threading.Thread(target=Worker, kwargs=data).start()


class Worker:
    def __init__(self, **kwargs):
        Logging().debug('Worker started')

        self.dates = []
        self.all_posts = []
        self.authors = []

        if "second_date" in kwargs:
            date_format = "%d.%m.%Y"

            start_date = datetime.strptime(kwargs["first_date"], date_format)
            end_date = datetime.strptime(kwargs["second_date"], date_format)
        else:
            start_date = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
            end_date = start_date - timedelta(days=30)

        current_date = start_date
        while end_date <= current_date:
            self.dates.append(end_date.strftime('%Y-%m-%d'))

            end_date += timedelta(days=1)

        Logging().info(str(self.dates))

        self.start_browser(kwargs["profile_id"])

        for subreddit in kwargs["subreddits"]:
            link = subreddit + 'new/' if subreddit.endswith('/') else subreddit + '/new/'

            self.get_posts(link=link)

        for post in self.all_posts:
            self.get_comments(link=post)

        with open('../data/data.json', 'w') as json_file:
            json.dump({"data": self.authors}, json_file)

        time.sleep(666)

    def start_browser(self, profile_id: str):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('debuggerAddress', f'127.0.0.1:{DolphinAPI().start_profile(profile_id)}')

        self.driver = webdriver.Chrome(service=Service('../chromedriver.exe'), options=options)
        self.actions = ActionChains(self.driver)

        self.driver.maximize_window()

        Logging().debug('Browser started')

    def get_posts(self, link: str):
        date_format = "%Y-%m-%d"

        self.driver.get(link)

        Logging().debug(f'Redirected to {link}')

        while True:

            posts = None
            while not posts:

                posts = self.driver.execute_script("""
                    return document.getElementsByClassName('Post');
                """)

            for post in posts:
                try:
                    href = self.driver.execute_script("return arguments[0].getElementsByTagName('a')[1].href;", post)
                    relative_time = self.driver.execute_script(
                        """return arguments[0].querySelector("[data-testid='post_timestamp']").textContent;""", post)
                except:
                    continue
                if "week" in relative_time:
                    weeks = int(relative_time.split()[0])
                    time_difference = timedelta(weeks=weeks)
                elif "day" in relative_time:
                    days = int(relative_time.split()[0])
                    time_difference = timedelta(days=days)
                elif "hour" in relative_time:
                    hours = int(relative_time.split()[0])
                    time_difference = timedelta(hours=hours)
                elif "minute" in relative_time:
                    minutes = int(relative_time.split()[0])
                    time_difference = timedelta(minutes=minutes)
                elif "second" in relative_time:
                    seconds = int(relative_time.split()[0])
                    time_difference = timedelta(seconds=seconds)
                else:
                    continue

                post_date = datetime.now() - time_difference

                Logging().info(f"Post time - {post_date}")

                if href not in self.all_posts:
                    self.all_posts.append(href)

                    self.actions.scroll_to_element(post).perform()

                if post_date > datetime.strptime(self.dates[0], date_format):
                    continue
                elif post_date < datetime.strptime(self.dates[-1], date_format):
                    return Logging().info(str(self.all_posts))
            time.sleep(5)
            new_posts = self.driver.execute_script("return document.getElementsByClassName('Post');")

            if len(new_posts) == len(posts):
                break
    def get_comments(self, link: str):
        has_more = True

        self.driver.get(link)

        Logging().debug(f'Redirected to {link}')

        last_last_height = 0
        last_height = 0

        while has_more:
            counter = 0
            while True:

                height = int(self.driver.execute_script("""
                    let body = document.body,
                        html = document.documentElement;
                    
                    let height = Math.max( body.scrollHeight, body.offsetHeight, 
                                           html.clientHeight, html.scrollHeight, html.offsetHeight );
                    
                    return height;
                """))

                Logging().info(f'Page height - {height}')

                if last_height == height:
                    if counter == 3:
                        break
                    else:
                        counter += 1
                        time.sleep(2)
                    if last_last_height == 6:
                        has_more = False
                    last_last_height += 1
                else:
                    last_height = height
                    last_last_height = 0

                    time.sleep(2)

            time.sleep(1)

            more_comments_button = self.driver.execute_script("""
                return document.querySelectorAll("[id*='moreComments']");
            """)

            if more_comments_button:
                Logging().info('Button +')

                for button in more_comments_button:
                    try:
                        self.actions.click(button).perform()
                    except:
                        continue

                    time.sleep(0.2)
            else:
                Logging().info('Button -')

                has_more = False

        authors = self.driver.execute_script("""
            let authors = [];
            let comments = document.querySelectorAll("[class*='Comment']");
            
            for (let comment of comments) {
                author_element = comment.querySelector('[data-testid="comment_author_link"]');
                if (author_element) {
                    author = author_element.textContent;
                    if (author !== "AutoModerator") {
                        authors.push(author);
                    }
                }
            }
            
            return authors;
        """)

        self.authors.extend(authors)


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
        headers = {
            "Authorization": f"Bearer {self.token}"
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
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        resp = requests.get(f"http://localhost:3001/v1.0/browser_profiles/{profile_id}/stop", headers=headers)

        if b"error" in resp.content:
            time.sleep(5)

            self.stop_profile(profile_id)

    def get_profiles(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        profiles = requests.get('https://anty-api.com/browser_profiles', headers=headers).json()["data"]

        return {profile["name"]: str(profile["id"]) for profile in profiles}


if __name__ == "__main__":
    with open('log.txt', 'w+') as f:
        f.write('')

    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()
