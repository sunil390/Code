# --- template_selector.py ---
import psycopg2
from sentence_transformers import SentenceTransformer

# --- Configuration ---
DB_NAME = "amai_knowledge_db"
DB_USER = "amai_user"
DB_PASSWORD = "Amazone@9" # <-- SET YOUR DB PASSWORD
DB_HOST = "192.168.2.226"
DB_PORT = "5432"

model = SentenceTransformer('all-MiniLM-L6-v2')
SIMILARITY_THRESHOLD = 0.5

def find_template_by_similarity(user_prompt: str) -> tuple[str | None, int | None]:
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    except psycopg2.OperationalError:
        return None, None

    query_embedding = model.encode(user_prompt)
    best_match = None
    with conn.cursor() as cur:
        # --- THIS IS THE FIX ---
        cur.execute(
            "SELECT template_name, template_id, 1 - (embedding <=> %s) AS similarity FROM awx_job_templates ORDER BY similarity DESC LIMIT 1",
            (str(query_embedding.tolist()),)
        )
        result = cur.fetchone()
    conn.close()

    if result:
        template_name, template_id, similarity = result
        print(f"Semantic Search: Best match '{template_name}' (Similarity: {similarity:.2f})")
        if similarity >= SIMILARITY_THRESHOLD:
            return template_name, template_id
    return None, None