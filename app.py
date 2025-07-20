# --- app.py ---
# Main Streamlit application with robust state management.

import streamlit as st
import warnings
import pyotp
import base64  # Import the base64 library
from config import VERIFY_SSL, USER_SECRETS
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
    if username in USER_SECRETS:
        totp = pyotp.TOTP(USER_SECRETS[username])
        return totp.verify(code)
    return False

# --- Main Application ---
if not st.session_state.get("authenticated", False):
    # --- LOGIN SCREEN ---
    st.title("AMAI - Login")
    with st.form("login_form"):
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
    # --- MAIN CHATBOT APPLICATION ---
    with st.sidebar:
        st.title("Atos Mainframe AIOps")
        st.markdown(f"Welcome, **{st.session_state.username}**!")
        st.markdown("---")
        # Replaced the markdown link with a st.link_button for a consistent UI
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
        
        # --- ROBUST IMAGE EMBEDDING ---
        # 1. Encode the image to base64
        img_base64 = get_image_as_base64("image.png")
        
        # 2. Embed directly using HTML in st.markdown
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

    # --- NEW: Main Chat Rendering Loop ---
    # This loop is now responsible for drawing the entire chat history, including all components.
    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            # Render the main content/header of the message
            st.markdown(message["content"])

            # If the message has sysout data, render the expander and button
            if message.get("sysout"):
                with st.expander("View Mainframe Job Sysout"):
                    st.code(message["sysout"], language="text")
                    # When button is clicked, it will trigger the analysis logic below
                    if st.button("🤖 Analyze Sysout with AI", key=f"analyze_{message['job_id']}"):
                        with st.spinner("🧠 Activating AI analysis pipeline..."):
                            analysis_result = analyze_sysout(message["sysout"])
                            # Update the message in-place with the analysis result
                            st.session_state.messages[index]["analysis"] = analysis_result
                            st.rerun() # Rerun to display the new analysis

            # If the message has a full log, render its expander
            if message.get("full_log"):
                with st.expander("View Full Ansible Execution Log"):
                    st.code(message["full_log"], language="bash")
            
            # If an analysis has been generated for this message, render it
            if message.get("analysis"):
                st.markdown(message["analysis"])


    # --- NEW: Chat Input and Job Execution Logic ---
    # This block now only handles creating new messages, not rendering them.
    if prompt := st.chat_input("What mainframe task would you like to do?"):
        # Add user's prompt to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # RAG-based Template Selection
        template_name, template_id = find_template_by_similarity(prompt)
        extra_vars = None

        # Parameter extraction
        if template_name == "joboutput":
            try:
                command_parts = prompt.lower().split()
                jobname_index = command_parts.index("jobname")
                jobname_param = command_parts[jobname_index + 1]
                extra_vars = {"jobname": jobname_param}
            except (ValueError, IndexError):
                template_id = None # Invalidate if parameter is missing
                error_msg = {"role": "assistant", "content": "Could not find a value for the `jobname` parameter. Usage: `... jobname MYJOB01 ...`"}
                st.session_state.messages.append(error_msg)
        
        # Job Execution
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
                    # Fixed a typo in the function call below
                    full_ansible_log = get_job_output(job_id) or ""
                    header = f"**Job {job_id} (`{template_name}`) finished: {final_status.upper()}**"
                    
                    # Create the new structured message object
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
        
        # Rerun the script to display the new message created above
        st.rerun()