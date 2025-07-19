# --- ai_analysis.py ---
# This module simulates an AI analysis of a mainframe job log.

import re

def analyze_sysout(sysout_text: str) -> str:
    """
    Analyzes a mainframe sysout log for key information and returns a
    formatted summary.

    Args:
        sysout_text: The complete mainframe job log as a string.

    Returns:
        A formatted markdown string with the analysis.
    """
    if not sysout_text:
        return "The provided sysout log is empty. No analysis can be performed."

    # --- Data Extraction using Regular Expressions ---
    
    # Find the job name and return code (RC)
    rc_match = re.search(r"\$HASP395\s+(\w+)\s+ENDED\s+-\s+RC=(\d+)", sysout_text)
    job_name = rc_match.group(1) if rc_match else "Unknown"
    return_code = rc_match.group(2) if rc_match else "Unknown"

    # Find start and end times
    start_time_match = re.search(r"IEF403I\s+\w+\s+-\s+STARTED\s+-\s+TIME=([\d.]+)", sysout_text)
    end_time_match = re.search(r"IEF404I\s+\w+\s+-\s+ENDED\s+-\s+TIME=([\d.]+)", sysout_text)
    start_time = start_time_match.group(1) if start_time_match else "N/A"
    end_time = end_time_match.group(1) if end_time_match else "N/A"

    # Check for ABENDs
    abend_match = re.search(r"ABEND\s*=\s*(S[0-9A-F]{3})", sysout_text, re.IGNORECASE)
    abend_code = abend_match.group(1) if abend_match else None

    # --- AI Inference and Summary Generation ---

    # Determine overall status
    if abend_code:
        status = "🔴 **Failed (Abend)**"
        conclusion = f"The job failed with an ABEND code **{abend_code}**. This indicates a critical error that halted execution."
    elif return_code == "0000":
        status = "🟢 **Successful**"
        conclusion = f"The job completed successfully with a return code of **{return_code}**, indicating no errors."
    elif return_code != "Unknown":
        status = f"🟡 **Warning/Check**"
        conclusion = f"The job finished with a return code of **{return_code}**. While it did not abend, this code suggests potential warnings or issues that may need review."
    else:
        status = "⚪ **Unknown**"
        conclusion = "The final status of the job could not be determined from the log."

    # Build the response in Markdown format
    analysis = f"""
### 🧠 **AI Log Analysis**

Here's my analysis of the job log for **{job_name}**:

**1. Overall Status:** {status}
   - **Conclusion:** {conclusion}

**2. Execution Details:**
   - **Start Time:** `{start_time}`
   - **End Time:** `{end_time}`
   - **Final Return Code (RC):** `{return_code}`

**3. Key Observations:**
"""
    if not abend_code and return_code == "0000":
        analysis += "- All steps appear to have executed normally.\n"
        analysis += "- No error or warning messages were detected in the standard sections.\n"
    
    if abend_code:
        analysis += f"- An **ABEND ({abend_code})** was detected. You should examine the steps immediately preceding the `IEF404I` (ENDED) message to find the cause of the failure.\n"
    
    if "ICH70001I" in sysout_text:
        analysis += "- Security authorization via RACF was successful.\n"

    analysis += "- Review the complete log for any application-specific messages or unexpected output."

    return analysis