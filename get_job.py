import requests
import json
import warnings

# --- Configuration ---
# All necessary details are hardcoded here for this standalone test.
AWX_HOST = "https://awx.znext.com"
AWX_API_TOKEN_READ = "H28UFcTNzzamB9hRFYx39NdXQYfzmP"  # Your Read Token
JOB_ID = 140
VERIFY_SSL = False

# Suppress only the single InsecureRequestWarning from urllib3 needed for VERIFY_SSL=False
if not VERIFY_SSL:
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)


def fetch_and_print_artifact(job_id):
    """
    Connects to the AWX API and attempts to fetch, parse, and print the
    'job_output' artifact for a specific job ID.
    """
    print(f"[*] Attempting to fetch artifact for Job ID: {job_id}...")
    
    # Construct the exact URL for the artifacts endpoint
    url = f"{AWX_HOST}/api/v2/jobs/{job_id}/artifacts/"
    headers = {'Authorization': f'Bearer {AWX_API_TOKEN_READ}'}

    try:
        # Make the GET request to the AWX API
        response = requests.get(url, headers=headers, verify=VERIFY_SSL, timeout=20)

        # --- Step 1: Check the HTTP Response ---
        # If the status is anything other than 200 (OK), we have a problem.
        if response.status_code != 200:
            print(f"\n[!!!] FAILED: The AWX server responded with an error.")
            print(f"      - Status Code: {response.status_code}")
            print(f"      - URL: {url}")
            print(f"      - Response Body: {response.text}")
            return

        print("[+] API call successful (HTTP 200). Now parsing the response...")

        # --- Step 2: Parse the Artifact Data ---
        # The response body is a JSON object.
        api_response_data = response.json()
        artifacts = api_response_data.get("results")

        if not artifacts:
            print("\n[!!!] FAILED: The API response was successful, but the 'results' list is empty.")
            print("      This means AWX reports NO artifacts for this job.")
            return

        # --- Step 3: Extract the Specific 'job_output' ---
        # The actual data we want is nested inside several layers.
        try:
            # Navigate through the nested structure
            artifact_data = artifacts[0]['artifact_data']
            raw_data_string = artifact_data['job_output']
            
            print("[+] Successfully found the 'job_output' key in the artifact.")
            print("[*] Now attempting to parse its content as JSON...")
            
            # The content of 'job_output' is a string that is ALSO JSON. We must parse it.
            parsed_list = json.loads(raw_data_string)
            content_lines = parsed_list[0]['content']

            # --- Step 4: Display the Final, Clean Output ---
            print("\n" + "="*50)
            print("    CLEAN JOB LOG OUTPUT    ")
            print("="*50 + "\n")
            # Join the list of log lines into a single block of text
            print("\n".join(content_lines))
            print("\n" + "="*50)
            print("[SUCCESS] Artifact fetched and parsed successfully.")
            
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            # This block will run if the data structure is not what we expect.
            print(f"\n[!!!] FAILED: Found an artifact, but its structure was unexpected.")
            print(f"      - Error Type: {type(e).__name__}")
            print(f"      - Error Details: {e}")
            print("\n" + "-"*50)
            print("RAW ARTIFACT DATA RECEIVED:")
            # Print the raw data to show exactly what we received from AWX
            print(json.dumps(artifacts[0], indent=2))
            print("-"*50)

    except requests.exceptions.RequestException as e:
        print(f"\n[!!!] FAILED: A network error occurred.")
        print(f"      - Error: {e}")


# --- Main execution block ---
if __name__ == "__main__":
    print("--- Standalone AWX Artifact Fetcher ---")
    fetch_and_print_artifact(JOB_ID)
    print("\n--- Script Finished ---")