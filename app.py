# --- app.py ---
# Main Streamlit application with robust state management.

import streamlit as st
import warnings
import pyotp
import base64  # Import the base64 library
# MODIFIED: Import the new ENABLE_TOTP flag
from config import VERIFY_SSL, USER_SECRETS, ENABLE_TOTP
from awx_actions import (
    launch_job_template,
    wait_for_job_completion,
    get_job_output,
    parse_mainframe_log_from_ansible_output,
    parse_job_summary
)
from ai_analysis import hybrid_analysis_pipeline as analyze_sysout
from template_selector import find_template_by_similarity

# --- Page Configuration ---
# The theme is now controlled by .streamlit/config.toml
st.set_page_config(page_title="AMAIO", layout="wide")

if not VERIFY_SSL:
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)

# --- Helper Functions ---
def get_image_as_base64(file):
    """Reads an image file and returns it as a base64 encoded string."""
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def check_login(username, code):
    """Verifies the TOTP code for a given user."""
    if username in USER_SECRETS:
        totp = pyotp.TOTP(USER_SECRETS[username])
        return totp.verify(code)
    return False

# --- Main Application ---
if not st.session_state.get("authenticated", False):
    st.title("AMAI - Login")

    # --- MODIFIED: Conditional Login Logic ---
    if ENABLE_TOTP:
        # --- TOTP LOGIN (Enabled) ---
        with st.form("login_form_totp"):
            username = st.text_input("Username").lower()
            otp_code = st.text_input("Authenticator Code", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if check_login(username, otp_code):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or authenticator code.")
    else:
        # --- SIMPLE USERNAME LOGIN (TOTP Disabled) ---
        st.info("TOTP is disabled. Please log in with a valid username from the configuration.")
        with st.form("login_form_simple"):
            username = st.text_input("Username").lower()
            submitted = st.form_submit_button("Login")
            if submitted:
                # Check if the username exists in the secrets dictionary
                if username in USER_SECRETS:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username. Please enter a username defined in config.py.")

else:
    # --- MAIN CHATBOT APPLICATION (No changes needed here) ---
    with st.sidebar:
        st.title("Atos Mainframe AIOps")
        st.markdown(f"Welcome, **{st.session_state.username}**!")
        st.markdown("---")
        st.link_button("AWX", "https://awx.znext.com")
        st.info("This chatbot Infuses AI into Mainframe Operations.")

        st.write("")
        st.write("")
        st.write("")

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()

        st.write("")
        st.write("")
        st.write("")

        img_base64 = get_image_as_base64("image.png")
        st.markdown(
            f"""
            <div style="padding-left: 1mm;">
                <img src="data:image/png;base64,{img_base64}" width="100">
            </div>
            """,
            unsafe_allow_html=True
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("sysout"):
                with st.expander("View Mainframe Job Sysout"):
                    st.code(message["sysout"], language="text")
                    if st.button("🤖 Analyze Sysout with AI", key=f"analyze_{message['job_id']}"):
                        with st.spinner("🧠 Activating AI analysis pipeline..."):
                            analysis_result = analyze_sysout(message["sysout"])
                            st.session_state.messages[index]["analysis"] = analysis_result
                            st.rerun()

            if message.get("full_log"):
                with st.expander("View Full Ansible Execution Log"):
                    st.code(message["full_log"], language="bash")
            
            if message.get("analysis"):
                st.markdown(message["analysis"])

    if prompt := st.chat_input("What mainframe task would you like to do?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        template_name, template_id = find_template_by_similarity(prompt)
        extra_vars = None

        if template_name == "joboutput":
            try:
                command_parts = prompt.lower().split()
                jobname_index = command_parts.index("jobname")
                jobname_param = command_parts[jobname_index + 1]
                extra_vars = {"jobname": jobname_param}
            except (ValueError, IndexError):
                template_id = None
                error_msg = {"role": "assistant", "content": "Could not find a value for the `jobname` parameter. Usage: `... jobname MYJOB01 ...`"}
                st.session_state.messages.append(error_msg)
        
        if not template_id:
            if 'error_msg' not in locals():
                error_msg = {"role": "assistant", "content": "Sorry, I couldn't find a matching job template for your request."}
                st.session_state.messages.append(error_msg)
        else:
            with st.spinner(f"Found template '{template_name}'. Launching job..."):
                job_id = launch_job_template(template_id, extra_vars)
            
            if job_id:
                with st.spinner(f"Job {job_id} is running..."):
                    final_status = wait_for_job_completion(job_id)
                
                if final_status:
                    full_ansible_log = get_job_output(job_id) or ""
                    header = f"**Job {job_id} (`{template_name}`) finished: {final_status.upper()}**"
                    
                    new_message = {"role": "assistant", "content": header, "full_log": full_ansible_log, "job_id": job_id}

                    if template_name == 'joboutput':
                        mainframe_sysout = parse_mainframe_log_from_ansible_output(full_ansible_log)
                        if mainframe_sysout:
                            new_message["sysout"] = mainframe_sysout
                        else:
                            new_message["content"] += "\n\n⚠️ Could not parse mainframe sysout from the Ansible log."
                    else:
                        summary = parse_job_summary(full_ansible_log)
                        if summary:
                            new_message["content"] += f"\n\n---\n#### Execution Summary\n```bash\n{summary}\n```"

                    st.session_state.messages.append(new_message)
            else:
                error_msg = {"role": "assistant", "content": "Error launching the job. Check the terminal for details."}
                st.session_state.messages.append(error_msg)
        
        st.rerun()
