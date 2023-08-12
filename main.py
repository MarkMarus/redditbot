import re
import time
import threading
from datetime import datetime, timedelta

import requests

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ui.parser import Ui_MainWindow
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

        time.sleep(666)

    def start_browser(self, profile_id: str):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('debuggerAddress', f'127.0.0.1:{DolphinAPI().start_profile(profile_id)}')

        self.driver = webdriver.Chrome(service=Service('chromedriver.exe'), options=options)
        self.actions = ActionChains(self.driver)

        self.driver.maximize_window()

        Logging().debug('Browser started')

    def get_posts(self, link: str):
        date_format = "%Y-%m-%d"

        self.driver.get(link)

        Logging().debug(f'Redirected to {link}')

        wait = WebDriverWait(self.driver, 60)

        while True:

            posts = wait.until(
                EC.presence_of_all_elements_located((By.TAG_NAME, 'shreddit-post'))
            )

            Logging().info(f'{len(posts)} posts found')

            for post in posts:

                permalink = 'https://reddit.com' + post.get_attribute('permalink')

                if permalink in self.all_posts:
                    continue

                post_date = datetime.strptime(post.get_attribute('created-timestamp').split('T')[0], date_format)

                Logging().info(f'Post date - {post_date}')

                if post_date > datetime.strptime(self.dates[0], date_format):
                    continue
                elif post_date < datetime.strptime(self.dates[-1], date_format):
                    return Logging().info(str(self.all_posts))

                self.actions.scroll_to_element(post).perform()

                self.all_posts.append(permalink)

                time.sleep(0.1)

    def get_comments(self, link: str):
        comment_ids = []
        last_len = None
        counter = 0

        self.driver.get(link)

        Logging().debug(f'Redirected to {link}')

        while True:

            comments = None
            while comments is None:
                comments = self.driver.execute_script("""
                    return document.querySelector('[class="_1YCqQVO-9r-Up6QPB9H6_4 _1YCqQVO-9r-Up6QPB9H6_4"]').querySelectorAll(':scope > div');
                """)

            Logging().info(f'{len(comments)} comments found')

            for comment in comments:

                try:
                    comment_id = comment.find_element(By.XPATH, './/div[@id]').get_attribute('id')
                except:
                    continue

                if "moreComments" in comment_id:
                    comment.click()
                    time.sleep(2)
                    break
                else:
                    if comment_id in comment_ids:
                        continue

                    try:
                        author = re.findall(r'/user/(.+)/', comment.find_element(By.XPATH, './/a[@data-testid]').get_attribute('href'))[0]
                    except:
                        continue

                    Logging().info(f'Comment author - {author}')

                    if author not in self.authors and author != "AutoModerator":
                        self.authors.append(author)

                        try:
                            self.actions.scroll_to_element(comment).perform()
                        except:
                            pass
                    else:
                        if last_len == len(comment_ids):
                            counter += 1
                        else:
                            last_len = len(comment_ids)

                        if counter >= 20:
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
        with open('data/token.txt') as f:
            self.token = f.readline()

    def start_profile(self, profile_id: str):
        with open('data/token.txt') as f:
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
        with open('token.txt') as f:
            token = f.readline()

        headers = {
            "Authorization": f"Bearer {token}"
        }

        resp = requests.get(f"http://localhost:3001/v1.0/browser_profiles/{profile_id}/stop", headers=headers)

        if b"error" in resp.content:
            time.sleep(5)

            self.stop_profile(profile_id)

    def get_profiles(self) -> dict:
        with open('data/token.txt') as f:
            token = f.readline()

        headers = {
            "Authorization": f"Bearer {token}"
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
