# GitHub CodeQL Scanning Results Exporter

This repository provides a tool to export GitHub CodeQL scanning results to an Excel file. The exported file contains
two sheets: `Summary` and `Details`.

## Summary Sheet

The `Summary` sheet provides a high-level overview of the scanning results. It includes the following information:

- Types of Vulnerabilities: This column lists the different types of vulnerabilities identified during the CodeQL scan.
- Severity Level: This column indicates the severity level of each vulnerability.
- Number of Appearances in Code: This column shows the total number of times each vulnerability appears in the codebase.

## Details Sheet

The `Details` sheet contains detailed information extracted from the GitHub CodeQL dashboard. It provides a
comprehensive view of all the vulnerabilities found during the scan.

## Usage

To use this tool, follow the instructions below:

1. Clone the repository
2. Navigate to the repository directory
3. Modify the `.env` file in the root directory and define the following variables:

```plaintext
GITHUB_ACCESS_TOKEN=your_access_token
GITHUB_OWNER=your_github_owner
GITHUB_REPO=your_github_repo
```

Make sure to replace `your_access_token`, `your_github_owner`, and `your_github_repo` with the appropriate values.

4. Install the required dependencies: `pip install -r ./requirements.txt`
5. Run the exporter script: `python ./get_codeql_scan_result.py`

The script will export the CodeQL scanning results to an Excel file named `codeql_scan_result.xlsx`.

## License

MIT License