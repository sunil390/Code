# --- config.py ---

# Your AWX Server Address
AWX_HOST = "https://awx.znext.com"

# Your API Tokens (created in the AWX UI under Users -> Tokens)
# One token must have 'Write' scope, the other must have 'Read' scope.
AWX_API_TOKEN_WRITE = "5xwQwIO5m7EDTKEHqIenYgFsNTWrPv"  
AWX_API_TOKEN_READ = "H28UFcTNzzamB9hRFYx39NdXQYfzmP"

# This is our "knowledge base" mapping template names to their IDs
TEMPLATE_MAPPING = {
    "siddcuf": 14,
    "joboutput": 15, # This needs an additional parameter Jobname
    "sidcom2": 16,
    "siddcub": 17,
}

# SSL verification setting
VERIFY_SSL = False

# --- User Authentication Configuration ---
# This is our simulated user database. In a real application,
# this would be a secure database table.
# The key is the username, and the value is their unique secret key.
# Use the generate_qr.py script to create a secret and QR code for a new user.
USER_SECRETS = {
    "sunil": "JBSWY3DPEHPK3PXP" # This is an example secret.
}