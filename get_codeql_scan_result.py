import re
from pathlib import Path

import pandas as pd
from decouple import config as decouple_config

from github_repo import GitHubRepo


def export_details_to_excel(writer, dataframe):
    workbook = writer.book
    worksheet_name = 'Details (VULs in Code)'
    if worksheet_name in workbook.sheetnames:
        workbook[worksheet_name].clear()
    else:
        workbook.add_worksheet(worksheet_name)
    dataframe.to_excel(writer, sheet_name=worksheet_name, index=False)
    worksheet = writer.sheets[worksheet_name]
    column_widths = [45, 13, 105, 65, 13, 65, 65, 65, 65]
    for i, width in enumerate(column_widths):
        worksheet.set_column(i, i, width)


def export_summary_to_excel(writer, dataframe):
    workbook = writer.book
    worksheet_name = 'Summary'
    if worksheet_name in workbook.sheetnames:
        workbook[worksheet_name].clear()
    else:
        workbook.add_worksheet(worksheet_name)
    dataframe.to_excel(writer, sheet_name=worksheet_name, index=False)
    worksheet = writer.sheets[worksheet_name]
    column_widths = [45, 25, 26]
    for i, width in enumerate(column_widths):
        worksheet.set_column(i, i, width)


def process_details(dataframe):
    df_details = pd.DataFrame({
        'Types of Vulnerabilities': dataframe['types_of_vulnerabilities'],
        'Severity Level': dataframe['severity_level'],
        'Summary': dataframe['summary'],
        'Location Path': dataframe['location_path'],
        'Location Line': dataframe['location_line'],
        'Detailed Description': dataframe['detailed_description'],
        'Recommendation': dataframe['recommendation'],
        'Example': dataframe['example'],
        'References': dataframe['references']
    })
    return df_details


def generate_summary(dataframe):
    counts = dataframe.groupby('types_of_vulnerabilities').size()
    df_summary = pd.DataFrame(counts, columns=['Number of Appears in Code']).reset_index()
    df_summary.columns = ['Types of Vulnerabilities', 'Number of Appears in Code']
    severity_mapping = \
        dataframe[['types_of_vulnerabilities', 'severity_level']].drop_duplicates().set_index(
            'types_of_vulnerabilities')[
            'severity_level']
    df_summary['Severity Level'] = df_summary['Types of Vulnerabilities'].map(severity_mapping)
    df_summary = df_summary.reindex(columns=['Types of Vulnerabilities', 'Severity Level', 'Number of Appears in Code'])
    df_summary['Severity Level'] = pd.Categorical(df_summary['Severity Level'],
                                                  categories=decouple_config('SEVERITY_LEVEL_ORDER',
                                                                             cast=lambda x: x.split(',')), ordered=True)
    df_summary = df_summary.sort_values('Severity Level')
    df_summary = df_summary.reset_index(drop=True)
    level_totals = df_summary.groupby('Severity Level')['Types of Vulnerabilities'].nunique()
    appear_totals = df_summary.groupby('Severity Level')['Number of Appears in Code'].sum()
    appear_total_count = appear_totals.sum()
    total_severity_levels = []
    for index in level_totals.index:
        if level_totals.loc[index] != 0:
            total_severity_levels.append(f'{index}: {level_totals.loc[index]}')
    severity_levels_string = ', '.join(total_severity_levels)
    total_row = pd.Series(['Total', severity_levels_string, appear_total_count], index=df_summary.columns)
    df_summary = pd.concat([df_summary, pd.DataFrame([total_row])], ignore_index=True)
    return df_summary


def extract_help_info(info):
    title = info.split('\n')[0].split('#')[1].strip()
    description = re.search(r"#.*?\n(.*?)\n\n## Recommendation", info, re.DOTALL).group(1).strip()
    recommendation = re.search(r"## Recommendation\n(.*?)\n\n(?:## Example|\n## References|$)", info, re.DOTALL).group(
        1).strip()
    example_match = re.search(r"## Example\n(.*?)\n\n(?:## References|$)", info, re.DOTALL)
    example = example_match.group(1).strip() if example_match else ""
    references_match = re.search(r"## References\n(.*)", info, re.DOTALL)
    references = references_match.group(1).strip() if references_match else ""
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


def process_alerts():
    github_repo = GitHubRepo(decouple_config('GITHUB_ACCESS_TOKEN'), decouple_config('GITHUB_OWNER'),
                             decouple_config('GITHUB_REPO'))
    df_alerts = pd.DataFrame(
        columns=['number', 'state', 'types_of_vulnerabilities', 'severity_level', 'rule_id', 'summary', 'location_path',
                 'location_line', 'detailed_description', 'recommendation', 'example', 'references'])
    security_ids = github_repo.get_open_alert_ids()
    for security_id in security_ids:
        security_details = github_repo.get_alert_details(security_id)
        df_alerts = pd.concat([df_alerts, pd.DataFrame([parse_details(security_details)])], ignore_index=True)
    return df_alerts


def build_output_path(directory):
    repo_name = decouple_config('GITHUB_REPO').lower().replace('-', '_')
    output_filename = decouple_config('OUTPUT_FILE')
    return Path(directory, f'{repo_name}_{output_filename}')


def create_output_directory():
    output_directory = Path('/', *decouple_config('OUTPUT_DIRECTORY', cast=lambda x: x.split(','))).resolve().absolute()
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def get_result():
    output_directory = create_output_directory()
    output_path = build_output_path(output_directory)
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_alerts = process_alerts()
        df_summary = generate_summary(df_alerts)
        export_summary_to_excel(writer, df_summary)
        df_details = process_details(df_alerts)
        export_details_to_excel(writer, df_details)


if __name__ == '__main__':
    get_result()
