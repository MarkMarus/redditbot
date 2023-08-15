import requests

import time
from datetime import datetime


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
