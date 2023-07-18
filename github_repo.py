import base64

from decouple import config as decouple_config

from github_api import GitHubAPI


class GitHubRepo(object):
    def __init__(self, access_token, owner, repo):
        self.api = GitHubAPI(access_token)
        self.owner = owner
        self.repo = repo

    def get_alert_details(self, alert_id):
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}/code-scanning/alerts/{alert_id}'
        response = self.api.get(url)
        if response.status_code == 200:
            alert_details = response.json()
            return alert_details
        else:
            print(f'Failed to retrieve CodeQL alert details: {response.text}')
            return None

    def filter_alerts(self, alerts):
        open_alert_ids = []
        severity_levels = decouple_config('SEVERITY_LEVEL_TO_REPORT', cast=lambda x: x.split(','))
        for alert in alerts:
            if (
                    alert['state'] == 'open'
                    and alert['rule'].get('security_severity_level') is not None
                    and alert['rule'].get('security_severity_level') in severity_levels
            ):
                open_alert_ids.append(alert['number'])
        return open_alert_ids

    def get_open_alert_ids(self):
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}/code-scanning/alerts'
        response = self.api.get(url)
        open_alert_ids = []
        if response.status_code == 200:
            alerts = response.json()
            open_alert_ids.extend(self.filter_alerts(alerts))
            while 'next' in response.links:
                next_page_url = response.links['next']['url']
                response = self.api.get(next_page_url)
                if response.status_code == 200:
                    alerts = response.json()
                    open_alert_ids.extend(self.filter_alerts(alerts))
                else:
                    print(f'Failed to retrieve next page of CodeQL alerts: {response.text}')
                    break
        else:
            print(f'Failed to retrieve CodeQL alerts: {response.text}')
        return open_alert_ids

    def commit_file(self, branch, file, path, message):
        with open(file, 'r', encoding='utf-8') as file:
            file_content = file.read()
        encoded_content = base64.b64encode(file_content.encode()).decode()
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}'
        response = self.api.get(url)
        if response.status_code == 200:
            file_data = response.json()
            sha = file_data['sha']
            payload = {
                'message': message,
                'content': encoded_content,
                'branch': branch,
                'sha': sha
            }
            response = self.api.put(url, payload)
            if response.status_code == 200:
                print('File updated successfully.')
            else:
                print(f'Error: {response.status_code} - {response.json()["message"]}')
        elif response.status_code == 404:
            payload = {
                'message': message,
                'content': encoded_content,
                'branch': branch
            }
            response = self.api.put(url, payload)
            if response.status_code == 201:
                print('File created successfully.')
            else:
                print(f'Error: {response.status_code} - {response.json()["message"]}')
        else:
            print(f'Error: {response.status_code} - {response.json()["message"]}')

    def get_default_branch(self):
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}'
        response = self.api.get(url)
        if response.status_code == 200:
            repository_info = response.json()
            return repository_info['default_branch']
        else:
            return ''

    def get_languages_info(self):
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}/languages'
        response = self.api.get(url)
        languages = []
        if response.status_code == 200:
            languages_data = response.json()
            for language, bytes_count in languages_data.items():
                languages.append(language)
        else:
            print(f'Failed to fetch repository languages. Error: {response.text}')
        return list(map(str.lower, languages))
