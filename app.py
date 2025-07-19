# --- app.py ---
# Main Streamlit application with Google Authenticator login.

import streamlit as st
import warnings
import pyotp
from config import TEMPLATE_MAPPING, VERIFY_SSL, USER_SECRETS
from awx_actions import (
    launch_job_template,
    wait_for_job_completion,
    get_job_output,
    parse_mainframe_log_from_ansible_output,
    parse_job_summary
)
# --- IMPORT THE NEW ANALYSIS FUNCTION ---
from ai_analysis import analyze_sysout

# --- Page Configuration ---
st.set_page_config(
    page_title="AMAI",
    layout="wide"
)

# Suppress SSL warnings if verification is disabled
if not VERIFY_SSL:
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)

# --- Helper Functions (Defined at the top to prevent NameError) ---
def check_login(username, code):
    """Verifies the TOTP code for a given user."""
    if username in USER_SECRETS:
        secret = USER_SECRETS[username]
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    return False

def find_template_from_text(text, mapping):
    """Finds the first matching template name in the user's text."""
    for name, template_id in mapping.items():
        if name in text.lower():
            return name, template_id
    return None, None


# --- Main Application ---
if not st.session_state.get("authenticated", False):
    # --- LOGIN SCREEN ---
    st.title("AMAI - Login")
    st.markdown("Please enter your credentials to access the chatbot.")

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
        st.title("Atos Mainframe AI")
        st.markdown(f"Welcome, **{st.session_state.username}**!")
        st.markdown("---")
        st.markdown("### [AWX](https://awx.znext.com)")
        st.markdown("---")
        st.info("This chatbot executes AWX job templates using natural language.")
        st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()
        st.markdown("### AMAI")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("What AWX job would you like to run?"):
        # Clear previous sysout when a new prompt is submitted
        if "last_sysout" in st.session_state:
            del st.session_state.last_sysout
            
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            command_parts = prompt.lower().split()
            trigger_word = command_parts[0]
            template_name, template_id, extra_vars, error_message = (None, None, None, None)

            if trigger_word == "joboutput":
                template_name = "joboutput"
                template_id = TEMPLATE_MAPPING.get(template_name)
                if len(command_parts) > 1:
                    extra_vars = {"jobname": command_parts[1]}
                else:
                    error_message = "This command requires a job name. Usage: `joboutput <job_name>`"
            else:
                template_name, template_id = find_template_from_text(prompt, TEMPLATE_MAPPING)

            if error_message:
                st.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
            elif not template_name:
                response = "Sorry, I couldn't identify a valid job. Please use `joboutput <name>` or mention one of: siddcuf, sidcom2, siddcub."
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                with st.spinner(f"Found '{template_name}'. Launching job..."):
                    job_id = launch_job_template(template_id, extra_vars)

                if job_id:
                    with st.spinner(f"Job {job_id} is running..."):
                        final_status = wait_for_job_completion(job_id)

                    if final_status:
                        header = f"**Job {job_id} (`{template_name}`) finished: {final_status.upper()}**"
                        
                        with st.spinner("Fetching and parsing job output..."):
                            full_ansible_log = get_job_output(job_id) or ""
                        
                        st.markdown(header)
                        final_response_for_history = header
                        
                        if template_name == 'joboutput':
                            mainframe_sysout = parse_mainframe_log_from_ansible_output(full_ansible_log)
                            # Store the latest sysout in the session state for the button to use
                            st.session_state.last_sysout = mainframe_sysout
                            
                            if mainframe_sysout:
                                with st.expander("View Mainframe Job Sysout", expanded=False):
                                    st.code(mainframe_sysout, language='text')
                                    # The "Analyze" button is now placed inside the expander
                                    st.button("🤖 Analyze Sysout with AI", key=f"analyze_{job_id}")
                                
                                with st.expander("View Full Ansible Execution Log"):
                                    st.code(full_ansible_log, language='bash')
                                
                                main_content = f"\n\n<details><summary>View Mainframe Job Sysout</summary>\n\n```text\n{mainframe_sysout}\n```\n\n</details>"
                                expander_content = f"\n\n<details><summary>View Full Ansible Execution Log</summary>\n\n```bash\n{full_ansible_log}\n```\n\n</details>"
                                final_response_for_history += main_content + expander_content
                            else:
                                st.warning("Could not parse mainframe sysout from the Ansible log.")
                                st.code(full_ansible_log, language='bash')
                                final_response_for_history += f"\n\n```bash\n{full_ansible_log}\n```"
                        
                        else: # Logic for other non-sysout jobs
                            summary = parse_job_summary(full_ansible_log)
                            if summary.strip():
                                st.markdown("---\n#### Execution Summary")
                                st.code(summary, language='bash')
                                final_response_for_history += f"\n\n---\n#### Execution Summary\n```bash\n{summary}\n```"
                            
                            with st.expander("View Full Job Log"):
                                st.code(full_ansible_log, language='text')
                            
                            expander_content = f"\n\n<details><summary>View Full Job Log</summary>\n\n```text\n{full_ansible_log}\n```\n\n</details>"
                            final_response_for_history += expander_content

                        st.session_state.messages.append({"role": "assistant", "content": final_response_for_history})

                else:
                    error_response = "Error launching the job. Check terminal for details."
                    st.markdown(error_response)
                    st.session_state.messages.append({"role": "assistant", "content": error_response})

    # --- NEW LOGIC: Handle the button click for AI analysis ---
    # This checks if any of our dynamically created "analyze" buttons were clicked.
    for key, value in st.session_state.items():
        if key.startswith("analyze_") and value: # If a button was clicked
            if "last_sysout" in st.session_state and st.session_state.last_sysout:
                with st.chat_message("assistant"):
                    with st.spinner("🧠 AI is analyzing the log..."):
                        analysis_result = analyze_sysout(st.session_state.last_sysout)
                        st.markdown(analysis_result)
                        st.session_state.messages.append({"role": "assistant", "content": analysis_result})
            else:
                 with st.chat_message("assistant"):
                    st.warning("Could not find the sysout to analyze. Please run the job again.")

            # Reset the button's state to False
            st.session_state[key] = False