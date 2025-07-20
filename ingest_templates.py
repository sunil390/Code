# --- ingest_templates.py ---
import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer

# --- Configuration ---
DB_NAME = "amai_knowledge_db"
DB_USER = "amai_user"
DB_PASSWORD = "Amazone@9" # <-- SET YOUR DB PASSWORD
DB_HOST = "192.168.2.226"
DB_PORT = "5432"

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

def setup_database_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS awx_job_templates (
                id SERIAL PRIMARY KEY,
                template_id INT NOT NULL,
                template_name VARCHAR(255) NOT NULL,
                description TEXT,
                embedding VECTOR(384)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS awx_templates_embedding_idx ON awx_job_templates USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);")
        conn.commit()
        print("Database table 'awx_job_templates' is ready.")

def ingest_template_data():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to PostgreSQL. Check connection settings.\n{e}")
        return

    setup_database_table(conn)
    df = pd.read_csv("awx_templates_kb.csv")
    print(f"Found {len(df)} templates to ingest.")
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE awx_job_templates RESTART IDENTITY;")
        for index, row in df.iterrows():
            text_to_embed = f"Template Name: {row['template_name']}. Purpose: {row['description']}"
            embedding = model.encode(text_to_embed)
            # --- THIS IS THE FIX ---
            # Convert the list to its string representation before passing it to the driver.
            cur.execute(
                "INSERT INTO awx_job_templates (template_id, template_name, description, embedding) VALUES (%s, %s, %s, %s)",
                (row['template_id'], row['template_name'], row['description'], str(embedding.tolist()))
            )
        print(f"Ingested {len(df)} templates.")
    conn.commit()
    conn.close()
    print("\nTemplate ingestion complete.")

if __name__ == "__main__":
    ingest_template_data()