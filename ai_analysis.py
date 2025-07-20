# --- ai_analysis.py ---
import re
import psycopg2
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from config import GEMINI_API_KEY

# --- Configuration ---
DB_NAME = "amai_knowledge_db"
DB_USER = "amai_user"
DB_PASSWORD = "Amazone@9" # <-- SET YOUR DB PASSWORD
DB_HOST = "192.168.2.226"
DB_PORT = "5432"

try:
    genai.configure(api_key=GEMINI_API_KEY)
    llm = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    llm = None

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def _extract_error_from_log(sysout_text: str) -> str | None:
    if not llm: return "Gemini AI model not configured."
    abend_match = re.search(r"(S[0-9A-F]{3}|U\d{4})", sysout_text)
    if abend_match: return abend_match.group(1)
    prompt = f"Find the most important error code or abend code from this mainframe log. Examples: S0C7, U4088, RC=08. If the job is successful (RC=0000), return 'RC=0000'. Return ONLY the code. LOG:\n{sysout_text[:4000]}"
    try:
        response = llm.generate_content(prompt)
        error_code = response.text.strip()
        print(f"LLM Triage identified: {error_code}")
        return error_code
    except Exception as e:
        print(f"LLM Triage Error: {e}")
        return None

def _query_vector_db(query_text: str) -> str:
    if query_text == "RC=0000": return "The job was successful (RC=0000). No knowledge base lookup needed."
    query_embedding = embedding_model.encode(query_text)
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    results_text = ""
    with conn.cursor() as cur:
        # --- THIS IS THE FIX ---
        cur.execute("SELECT title, resolution_steps FROM work_instructions ORDER BY embedding <=> %s LIMIT 2", (str(query_embedding.tolist()),))
        results = cur.fetchall()
    conn.close()
    if not results: return "No specific work instructions were found for this error in the knowledge base."
    results_text += "Relevant Work Instructions Found:\n"
    for title, resolution_steps in results:
        results_text += f"- Title: {title}\n  Resolution: {resolution_steps}\n"
    print("Found relevant documents in Vector DB.")
    return results_text

def _synthesize_final_answer(sysout_text: str, kb_results: str) -> str:
    if not llm: return "Gemini AI model not configured."
    master_prompt = f"""You are an expert z/OS Mainframe Systems Programmer. Analyze the job log and internal documentation to provide a clear resolution plan.
    Provide: Executive Summary, Root Cause Analysis, and a Step-by-Step Resolution Plan.
    ---
    BEGIN Original Job Log:
    {sysout_text}
    ---
    END Original Job Log.
    ---
    BEGIN Internal Knowledge Base:
    {kb_results}
    ---
    END Internal Knowledge Base.
    """
    try:
        print("Synthesizing final answer with LLM...")
        response = llm.generate_content(master_prompt)
        return response.text
    except Exception as e:
        print(f"LLM Synthesis Error: {e}")
        return "An error occurred while generating the final AI analysis."

def hybrid_analysis_pipeline(sysout_text: str) -> str:
    if not sysout_text: return "Log is empty."
    error_code = _extract_error_from_log(sysout_text)
    if not error_code: return "Could not determine the primary error."
    if error_code == "RC=0000": return "✅ **AI Analysis:** The job log indicates a successful completion (RC=0000)."
    kb_results = _query_vector_db(error_code)
    final_analysis = _synthesize_final_answer(sysout_text, kb_results)
    return f"### 🧠 **AI-Powered Analysis for '{error_code}'**\n\n" + final_analysis