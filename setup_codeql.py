import base64
import json
from pathlib import Path

import requests
from decouple import config as decouple_config


def commit_repo(access_token, owner, repo, branch, file, path, message):
    with open(file, 'r', encoding='utf-8') as file:
        file_content = file.read()
    encoded_content = base64.b64encode(file_content.encode()).decode()
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {access_token}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_data = response.json()
        sha = file_data['sha']
        payload = {
            'message': message,
            'content': encoded_content,
            'branch': branch,
            'sha': sha
        }
        response = requests.put(url, json=payload, headers=headers)
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
        response = requests.put(url, json=payload, headers=headers)
        if response.status_code == 201:
            print('File created successfully.')
        else:
            print(f'Error: {response.status_code} - {response.json()["message"]}')
    else:
        print(f'Error: {response.status_code} - {response.json()["message"]}')


def get_repo_default_branch(access_token, owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}'
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repository_info = response.json()
        return repository_info['default_branch']
    else:
        return ''


def generate_codeql_yml(languages):
    codeql_support = decouple_config('CODEQL_SUPPORTS', cast=lambda x: x.split(','))
    mapping = decouple_config('CODEQL_MAPPING', cast=lambda x: json.loads(x))
    languages = [mapping.get(lang, lang) for lang in languages if mapping.get(lang, lang) in codeql_support]
    variables = {
        'BRANCH_NAME': decouple_config('CODEQL_BRANCH', cast=lambda x: x.split(',')),
        'CRON': decouple_config('CODEQL_CRON'),
        'LANGUAGE': languages
    }
    with open('codeql_template.yml', 'r', encoding='utf-8') as file:
        yml_content = file.read()
    generated_yml_content = yml_content
    for variable, replacement in variables.items():
        if variable in ['BRANCH_NAME', 'LANGUAGE']:
            replacement = ', '.join([f'"{value}"' for value in replacement])
        else:
            replacement = f"'{replacement}'"
        generated_yml_content = generated_yml_content.replace(f'${{{variable}}}', f'{replacement}')
    codeql_config_directory = Path('/', *decouple_config('CODEQL_CONFIG_LOCAL',
                                                         cast=lambda x: x.split(','))).resolve().absolute()
    codeql_config_directory.mkdir(parents=True, exist_ok=True)
    codeql_config_path = Path(codeql_config_directory, decouple_config('CODEQL_CONFIG_FILE'))
    with open(codeql_config_path, 'w', encoding='utf-8') as file:
        file.write(generated_yml_content)
    return codeql_config_path


def get_repo_languages_info(access_token, owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/languages'
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get(url, headers=headers)
    languages = []
    if response.status_code == 200:
        languages_data = response.json()
        for language, bytes_count in languages_data.items():
            languages.append(language)
    else:
        print('Failed to fetch repository languages. Error:', response.text)
    return list(map(str.lower, languages))


languages_info = get_repo_languages_info(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'),
                                         decouple_config('GITHUB_REPO'))
codeql_config_local_path = generate_codeql_yml(languages_info)
repo_branch = get_repo_default_branch(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'),
                                      decouple_config('GITHUB_REPO'))
codeql_config_repo_path = '/'.join(
    decouple_config('CODEQL_CONFIG_REPO', cast=lambda x: x.split(',')) + [decouple_config('CODEQL_CONFIG_FILE')])
commit_message = 'Create or update codeql.yml file.'
commit_repo(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'), decouple_config('GITHUB_REPO'),
            repo_branch, codeql_config_local_path, codeql_config_repo_path, commit_message)
