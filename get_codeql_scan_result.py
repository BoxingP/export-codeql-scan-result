import os
import re

import pandas as pd
import requests

from decouple import config as decouple_config


def export_details_to_excel(excel_writer, dataframe):
    workbook = excel_writer.book
    worksheet_name = 'Details (VULs in Code)'
    if worksheet_name in workbook.sheetnames:
        workbook[worksheet_name].clear()
    else:
        workbook.add_worksheet(worksheet_name)
    dataframe.to_excel(excel_writer, sheet_name=worksheet_name, index=False)
    worksheet = excel_writer.sheets[worksheet_name]
    column_widths = [45, 13, 105, 65, 13, 65, 65, 65, 65]
    for i, width in enumerate(column_widths):
        worksheet.set_column(i, i, width)


def export_summary_to_excel(excel_writer, dataframe):
    workbook = excel_writer.book
    worksheet_name = 'Summary'
    if worksheet_name in workbook.sheetnames:
        workbook[worksheet_name].clear()
    else:
        workbook.add_worksheet(worksheet_name)
    dataframe.to_excel(excel_writer, sheet_name=worksheet_name, index=False)
    worksheet = excel_writer.sheets[worksheet_name]
    column_widths = [45, 13, 26]
    for i, width in enumerate(column_widths):
        worksheet.set_column(i, i, width)


def extract_help_info(info):
    title = info.split('\n')[0].split('#')[1].strip()
    description = re.search(r"#.*?\n(.*?)\n\n## Recommendation", info, re.DOTALL).group(1).strip()
    recommendation = re.search(r"## Recommendation\n(.*?)\n\n## Example", info, re.DOTALL).group(1).strip()
    example = re.search(r"## Example\n(.*?)\n\n## References", info, re.DOTALL).group(1).strip()
    references = re.search(r"## References\n(.*)", info, re.DOTALL).group(1).strip()
    return {'title': title, 'detailed_description': description, 'recommendation': recommendation, 'example': example,
            'references': references}


def parse_details(details):
    help_info = extract_help_info(details['rule']['help'])
    data = {
        'number': details['number'],
        'state': details['state'],
        'types_of_vulnerabilities': details['rule']['description'],
        'severity_level': details['rule']['security_severity_level'],
        'rule_id': details['rule']['id'],
        'summary': details['most_recent_instance']['message']['text'],
        'location_path': details['most_recent_instance']['location']['path'],
        'location_line': details['most_recent_instance']['location']['start_column'],
        'detailed_description': help_info['detailed_description'],
        'recommendation': help_info['recommendation'],
        'example': help_info['example'],
        'references': help_info['references']
    }
    return data


def get_alert_details(access_token, owner, repo, alert_id):
    url = f"https://api.github.com/repos/{owner}/{repo}/code-scanning/alerts/{alert_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        alert_details = response.json()
        return alert_details
    else:
        print("Failed to retrieve CodeQL alert details:", response.text)
        return None


def get_open_alert_ids(access_token, owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/code-scanning/alerts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)

    open_alert_ids = []
    if response.status_code == 200:
        alerts = response.json()
        open_alert_ids.extend(alert["number"] for alert in alerts if alert["state"] == "open")
        while "next" in response.links:
            next_page_url = response.links["next"]["url"]
            response = requests.get(next_page_url, headers=headers)
            if response.status_code == 200:
                alerts = response.json()
                open_alert_ids.extend(alert["number"] for alert in alerts if alert["state"] == "open")
            else:
                print("Failed to retrieve next page of CodeQL alerts:", response.text)
                break
    else:
        print("Failed to retrieve CodeQL alerts:", response.text)
    return open_alert_ids


output_directory = os.path.abspath(os.sep.join([os.path.abspath(os.sep), decouple_config('OUTPUT_DIRECTORY')]))
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
output_path = os.path.join(output_directory, decouple_config('OUTPUT_FILE'))
writer = pd.ExcelWriter(output_path, engine='xlsxwriter')

df_alerts = pd.DataFrame(
    columns=['number', 'state', 'types_of_vulnerabilities', 'severity_level', 'rule_id', 'summary',
             'location_path', 'location_line', 'detailed_description', 'recommendation', 'example', 'references']
)
security_ids = get_open_alert_ids(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'),
                                  decouple_config('GITHUB_REPO'))
for security_id in security_ids:
    security_details = get_alert_details(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'),
                                         decouple_config('GITHUB_REPO'), security_id)
    df_alerts = pd.concat([df_alerts, pd.DataFrame([parse_details(security_details)])], ignore_index=True)

counts = df_alerts.groupby('types_of_vulnerabilities').size()
df_summary = pd.DataFrame(counts, columns=['Number of Appears in Code']).reset_index()
df_summary.columns = ['Types of Vulnerabilities', 'Number of Appears in Code']
severity_mapping = \
    df_alerts[['types_of_vulnerabilities', 'severity_level']].drop_duplicates().set_index('types_of_vulnerabilities')[
        'severity_level']
df_summary['Severity Level'] = df_summary['Types of Vulnerabilities'].map(severity_mapping)
df_summary = df_summary.reindex(columns=['Types of Vulnerabilities', 'Severity Level', 'Number of Appears in Code'])
export_summary_to_excel(writer, df_summary)

df_details = pd.DataFrame({
    'Types of Vulnerabilities': df_alerts['types_of_vulnerabilities'],
    'Severity Level': df_alerts['severity_level'],
    'Summary': df_alerts['summary'],
    'Location Path': df_alerts['location_path'],
    'Location Line': df_alerts['location_line'],
    'Detailed Description': df_alerts['detailed_description'],
    'Recommendation': df_alerts['recommendation'],
    'Example': df_alerts['example'],
    'References': df_alerts['references']
})
export_details_to_excel(writer, df_details)

writer.close()
