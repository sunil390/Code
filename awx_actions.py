# --- awx_actions.py ---
import requests
import time
import re
from config import AWX_HOST, AWX_API_TOKEN_READ, AWX_API_TOKEN_WRITE, VERIFY_SSL

# (All functions: launch_job_template, wait_for_job_completion, get_job_output, parse_job_summary, parse_mainframe_log_from_ansible_output are identical to the previous version and remain correct)
# ...
def launch_job_template(template_id, extra_vars=None):
    url = f"{AWX_HOST}/api/v2/job_templates/{template_id}/launch/"
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN_WRITE}', 'Content-Type': 'application/json'}
    payload = {'extra_vars': extra_vars} if extra_vars else {}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15, verify=VERIFY_SSL)
        response.raise_for_status()
        return response.json().get("job")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to launch job {template_id}. Details: {e}")
        return None

def wait_for_job_completion(job_id):
    url = f"{AWX_HOST}/api/v2/jobs/{job_id}/"
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN_READ}'}
    while True:
        try:
            response = requests.get(url, headers=headers, verify=VERIFY_SSL)
            response.raise_for_status()
            status = response.json().get("status")
            if status in ["successful", "failed", "error", "canceled"]:
                return status
            time.sleep(10)
        except requests.exceptions.RequestException:
            return "error"

def get_job_output(job_id):
    url = f"{AWX_HOST}/api/v2/jobs/{job_id}/stdout/?format=txt"
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN_READ}'}
    try:
        response = requests.get(url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
        return "Error fetching job stdout."

def parse_job_summary(raw_output):
    if not raw_output: return ""
    summary_lines = []
    in_mainframe_log = False
    pattern = re.compile(r"^(PLAY \[|TASK \[|PLAY RECAP|ok:|changed:|fatal:|failed:|skipping:|unreachable:|.*\s*:\s*ok=.*changed=.*)")
    for line in raw_output.splitlines():
        if "--- BEGIN MAINFRAME JOB LOG ---" in line:
            in_mainframe_log = True
            continue
        if "--- END MAINFRAME JOB LOG ---" in line:
            in_mainframe_log = False
            continue
        if not in_mainframe_log and pattern.match(line.strip()):
            summary_lines.append(line.strip())
    return "\n".join(summary_lines)

def parse_mainframe_log_from_ansible_output(ansible_log):
    try:
        start_marker = "--- BEGIN MAINFRAME JOB LOG ---"
        end_marker = "--- END MAINFRAME JOB LOG ---"
        start_index = ansible_log.find(start_marker)
        if start_index == -1: return None
        end_index = ansible_log.find(end_marker, start_index)
        if end_index == -1: return None
        content_start = start_index + len(start_marker)
        log_content = ansible_log[content_start:end_index]
        formatted_log = log_content.replace('\\n', '\n')
        return formatted_log.strip()
    except Exception as e:
        print(f"Error parsing mainframe log: {e}")
        return None