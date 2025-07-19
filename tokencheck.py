import requests

# --- Configuration ---
AWX_HOST = "https://awx.znext.com"

# Paste the token you copied from the AWX interface here
AWX_API_TOKEN = "lrxhgDZ4V6CHWUlNVgqpM3bxp0XMgP"

# Set the authentication header
headers = {
    'Authorization': f'Bearer {AWX_API_TOKEN}'
}

# Example: Get a list of job templates
def get_job_templates():
    api_url = f"{AWX_HOST}/api/v2/job_templates/"
    try:
        # The 'headers' variable is passed with the request
        response = requests.get(api_url, headers=headers, verify=False) # Use verify=False for self-signed certs
        response.raise_for_status() # Raise an exception for bad status codes

        print("Successfully retrieved job templates:")
        print(response.json())

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

# Run the example function
if __name__ == "__main__":
    get_job_templates()