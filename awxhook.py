import requests
import time
import json
import hmac
import hashlib
import uuid
import warnings

# --- Configuration ---
AWX_HOST = "https://awx.znext.com"
AWX_API_TOKEN = "5xwQwIO5m7EDTKEHqIenYgFsNTWrPv" # Must be a valid token

# --- SCRIPT CONSTANTS --- https://awx.znext.com/api/v2/job_templates/14/github/
JOB_TEMPLATE_ID = 14
AWX_WEBHOOK_URL = f"{AWX_HOST}/api/v2/job_templates/{JOB_TEMPLATE_ID}/github/"

#
# >>>>> CRITICAL STEP <<<<<
# Paste the NEWLY REGENERATED secret key for Job Template 13 here.
#
AWX_WEBHOOK_SECRET = "sIp3aHXTi9oW7Tq3ZWvslc7TevjDQ1KIGC7jXJ1vb4ncsh85t8"

# SSL verification setting
VERIFY_SSL = False
if not VERIFY_SSL:
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)


def trigger_awx_job():
    """Triggers the AWX job and prints debug information."""
    print("--- Preparing Webhook Trigger ---")
    
    # 1. Define the exact payload
    payload = {"ref": "refs/heads/main"}
    request_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    # 2. Print debug information
    # We mask most of the secret for security, but this confirms it's not empty.
    print(f"Using Secret Key (first 4 chars): {AWX_WEBHOOK_SECRET[:4]}...")
    print(f"Exact Request Body to be Signed: {request_body.decode()}")

    # 3. Calculate the signature
    signature_hash = hmac.new(AWX_WEBHOOK_SECRET.encode('utf-8'), request_body, hashlib.sha256)
    signature = f"sha256={signature_hash.hexdigest()}"
    print(f"Calculated Signature Sent in Header: {signature}")

    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': 'push',
        'X-GitHub-Delivery': str(uuid.uuid4()),
        'X-Hub-Signature-256': signature,
        'Authorization': f'Bearer {AWX_API_TOKEN}'
    }
    
    print(f"\nSending POST request to: {AWX_WEBHOOK_URL}")

    try:
        response = requests.post(AWX_WEBHOOK_URL, data=request_body, headers=headers, timeout=15, verify=VERIFY_SSL)
        response.raise_for_status()

        print("\nSUCCESS: Webhook accepted by AWX!")
        job_data = response.json()
        job_id = job_data.get("job")
        print(f"Successfully triggered job. Job ID: {job_id}")
        return job_id

    except requests.exceptions.HTTPError as e:
        print(f"\n!!!!!!!! FATAL ERROR !!!!!!!!")
        print(f"ERROR DETAILS: {e}")
        print(f"RESPONSE BODY: {e.response.text}")
        print("\nTROUBLESHOOTING:")
        print("1. Did you REGENERATE the key in the AWX UI and SAVE the template?")
        print("2. Is the `AWX_WEBHOOK_SECRET` in the script an EXACT match to the new key?")
        print("3. Check for a firewall or proxy (see Step 3 below).")
        return None
    except requests.exceptions.RequestException as e:
        print(f"A network or connection error occurred: {e}")
        return None

# --- Main execution block ---
if __name__ == "__main__":
    trigger_awx_job()