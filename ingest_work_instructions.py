# --- ingest_work_instructions.py ---
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
            CREATE TABLE IF NOT EXISTS work_instructions (
                id SERIAL PRIMARY KEY,
                error_code VARCHAR(10),
                title TEXT,
                resolution_steps TEXT,
                embedding VECTOR(384)
            );
        """)
        conn.commit()
        print("Database table 'work_instructions' is ready.")

def ingest_data():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to PostgreSQL. Check connection settings.\n{e}")
        return

    setup_database_table(conn)
    df = pd.read_csv("work_instructions.csv")
    print(f"Found {len(df)} documents to ingest.")
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE work_instructions RESTART IDENTITY;")
        for index, row in df.iterrows():
            text_to_embed = f"Title: {row['title']}\nResolution: {row['resolution_steps']}"
            embedding = model.encode(text_to_embed)
            # --- THIS IS THE FIX ---
            cur.execute(
                "INSERT INTO work_instructions (error_code, title, resolution_steps, embedding) VALUES (%s, %s, %s, %s)",
                (row['error_code'], row['title'], row['resolution_steps'], str(embedding.tolist()))
            )
        print(f"Ingested {len(df)} work instructions.")
    conn.commit()
    conn.close()
    print("\nWork instruction ingestion complete.")

if __name__ == "__main__":
    ingest_data()