# --- generate_qr.py ---
# This script is for administrators to generate a QR code for a user.
# Run this script once from your terminal: python generate_qr.py

import pyotp
import qrcode
from config import USER_SECRETS

# --- Configuration ---
# Change this to the username you want to generate a QR code for.
# This username MUST match a key in the USER_SECRETS dictionary in config.py.
USERNAME_TO_SETUP = "sunil"
ISSUER_NAME = "AMAI Chatbot" # This name will appear in the Authenticator App.

def generate_qr_code(username):
    """Generates a QR code for a given username and saves it as an image."""
    
    if username not in USER_SECRETS:
        print(f"Error: User '{username}' not found in USER_SECRETS in config.py.")
        print("Please add the user and a new secret key first.")
        # To generate a new secret, use: pyotp.random_base32()
        return

    secret = USER_SECRETS[username]
    
    # Generate the provisioning URI
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=ISSUER_NAME
    )
    
    # Create the QR code image
    img = qrcode.make(uri)
    
    # Save the image to a file
    filename = f"{username}_login_qr.png"
    img.save(filename)
    
    print("--- Google Authenticator Setup ---")
    print(f"Successfully generated QR code for user '{username}'.")
    print(f"File saved as: {filename}")
    print("\nNext Steps:")
    print("1. Open the Google Authenticator app on your phone.")
    print("2. Tap the '+' button to add a new account.")
    print(f"3. Scan the QR code image in '{filename}'.")
    print("4. You are now ready to log in to the chatbot!")

if __name__ == "__main__":
    generate_qr_code(USERNAME_TO_SETUP)