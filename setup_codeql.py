import json
from pathlib import Path

from decouple import config as decouple_config

from github_repo import GitHubRepo


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


github_repo = GitHubRepo(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'),
                         decouple_config('GITHUB_REPO'))
languages_info = github_repo.get_languages_info()
codeql_config_local_path = generate_codeql_yml(languages_info)
repo_branch = github_repo.get_default_branch()
codeql_config_repo_path = '/'.join(
    decouple_config('CODEQL_CONFIG_REPO', cast=lambda x: x.split(',')) + [decouple_config('CODEQL_CONFIG_FILE')])
commit_message = 'Create or update codeql.yml file.'
github_repo.commit_file(repo_branch, codeql_config_local_path, codeql_config_repo_path, commit_message)
