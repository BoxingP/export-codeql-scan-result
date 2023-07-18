import requests


class GitHubAPI(object):
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'Bearer {access_token}'
        }

    def get(self, url):
        return requests.get(url, headers=self.headers)

    def put(self, url, payload):
        return requests.put(url, json=payload, headers=self.headers)
