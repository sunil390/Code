import requests
import time
import json
import warnings
import re

# --- Configuration ---
AWX_HOST = "https://awx.znext.com"
AWX_API_TOKEN = "5xwQwIO5m7EDTKEHqIenYgFsNTWrPv" # Ensure it has 'Write' scope
JOB_TEMPLATE_ID = 14 # The ID of the Job Template you want to run


# Optional: Extra variables for the job run
EXTRA_VARS = {
    "ansible_user": "service_account",
    "deployment_target": "production",
    "some_other_variable": "value123"
}

# SSL verification setting
VERIFY_SSL = False
if not VERIFY_SSL:
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)


def launch_job_template(template_id, extra_vars=None):
    """Launches a job template using the REST API and returns the job ID."""
    print(f"--- Launching Job Template ID: {template_id} via REST API ---")
    launch_url = f"{AWX_HOST}/api/v2/job_templates/{template_id}/launch/"
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN}', 'Content-Type': 'application/json'}
    payload = {'extra_vars': extra_vars} if extra_vars else {}
    if extra_vars:
        print(f"Sending with Extra Variables: {json.dumps(extra_vars)}")
    try:
        response = requests.post(launch_url, headers=headers, json=payload, timeout=15, verify=VERIFY_SSL)
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data.get("job")
        if job_id:
            print(f"Successfully launched job. Job ID: {job_id}")
            return job_id
        return None
    except requests.exceptions.RequestException as e:
        print(f"\nFATAL ERROR during launch: {e}")
        return None

def wait_for_job_completion(job_id):
    """Polls the AWX API to wait for the job to complete."""
    if not job_id: return None
    print(f"\n--- Waiting for job {job_id} to complete ---")
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN}'}
    job_url = f"{AWX_HOST}/api/v2/jobs/{job_id}/"
    while True:
        try:
            response = requests.get(job_url, headers=headers, verify=VERIFY_SSL)
            response.raise_for_status()
            job_status = response.json().get("status")
            print(f"Current job status: {job_status}")
            if job_status in ["successful", "failed", "error", "canceled"]:
                return job_status
            time.sleep(15)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while checking job status: {e}")
            return "error"

def get_job_output(job_id):
    """Retrieves the plain text standard output of the completed job."""
    if not job_id: return "No job ID provided."
    print(f"\n--- Fetching output for job {job_id} ---")
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN}'}
    stdout_url = f"{AWX_HOST}/api/v2/jobs/{job_id}/stdout/?format=txt"
    try:
        response = requests.get(stdout_url, headers=headers, verify=VERIFY_SSL)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching job output: {e}")
        return "Error fetching job output."

def parse_job_summary(raw_output):
    """
    Parses raw job output to extract Play/Task headers, task status, and the final recap.
    """
    summary_lines = []
    
    # This pattern matches all the lines we care about.
    pattern = re.compile(
        r"^(PLAY \[|TASK \[|PLAY RECAP|"  # Headers
        r"ok:|changed:|fatal:|failed:|skipping:|unreachable:|"  # Task status lines
        r".*\s*:\s*ok=.*changed=.*)"  # Final host recap line
    )
    
    for line in raw_output.splitlines():
        stripped_line = line.strip()
        if pattern.match(stripped_line):
            summary_lines.append(stripped_line)
            
    return "\n".join(summary_lines)

# --- Main execution block ---
if __name__ == "__main__":
    job_id_to_monitor = launch_job_template(JOB_TEMPLATE_ID, extra_vars=EXTRA_VARS)

    if job_id_to_monitor:
        final_status = wait_for_job_completion(job_id_to_monitor)
        
        if final_status:
            raw_job_output = get_job_output(job_id_to_monitor)
            parsed_summary = parse_job_summary(raw_job_output)
            
            print("\n" + "="*20 + " JOB SUMMARY " + "="*20)
            print(f"Job Overall Status: {final_status.upper()}")
            print("-" * 53)
            print("Execution Summary:")
            if parsed_summary:
                print(parsed_summary)
            else:
                print("No play/task summary found in output.")
            print("=" * 53)