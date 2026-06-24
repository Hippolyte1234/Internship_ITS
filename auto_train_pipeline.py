import psycopg2
import ollama
import chromadb

# 1. Configurations
DB_CONFIG = {
    "host": "10.199.16.221",
    "database": "itsdw", 
    "user": 'ai_llm',
    "password": '!Donald_Babatan57',
    "port": 5432
}
MODEL_NAME = "qwen3.5:9b"  # Your local 9B model tag
CHROMA_PATH = "./vanna_knowledge_base"

# 2. Connect to Clients
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("🐘 Connected to PostgreSQL successfully.")
except Exception as e:
    print(f"🚨 Connection failed: {e}")
    exit()

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection("vanna_collection")


# 🚨 CLEAR OLD DATA: Wipe the old English vector payloads first
print("🗑️ Purging old collection entries to prepare for clean Indonesian vectors...")
all_ids = collection.get()["ids"]
if all_ids:
    collection.delete(ids=all_ids)
    print(f"✅ Cleared {len(all_ids)} old records.")


# 3. Pull the entire catalog directly from information_schema
print("🔍 Scanning database catalogs for schemas: 'akademik', 'kepegawaian', 'public'...")
query = """
SELECT 
    table_schema, 
    table_name, 
    column_name, 
    data_type
FROM 
    information_schema.columns
WHERE 
    table_schema IN ('akademik', 'kepegawaian', 'public')
ORDER BY 
    table_schema, table_name, ordinal_position;
"""

cur.execute(query)
rows = cur.fetchall()

# Group columns into their respective tables automatically
database_catalog = {}
for schema, table, column, dtype in rows:
    full_table_name = f"{schema}.{table}"
    if full_table_name not in database_catalog:
        database_catalog[full_table_name] = []
    database_catalog[full_table_name].append(f"  - {column} ({dtype})")

print(f"📦 Found {len(database_catalog)} total tables automatically.")
print("=" * 60)

# 4. LLM-Assisted Automated Vector Enrichment Loop
for table_name, columns in database_catalog.items():
    # Construct a clean text string layout of the real columns
    columns_structure = "\n".join(columns)
    raw_blueprint = f"Table: {table_name}\nColumns:\n{columns_structure}"
    
    print(f"🧠 Ollama 9B is analyzing data structural assets for: {table_name}...")
    
    prompt = (
        f"Anda adalah seorang data warehouse architect berpengalaman di Indonesia.\n"
        f"Analisis tabel PostgreSQL berikut beserta kolom-kolomnya:\n\n"
        f"{raw_blueprint}\n\n"
        f"Tugas: Hasilkan daftar kata kunci (synonyms) dan istilah bisnis dalam Bahasa Indonesia "
        f"yang paling mungkin diketik oleh pengguna saat mencari data dari tabel ini.\n\n"
        f"ATURAN KETAT:\n"
        f"1. FOKUS BAHASA: Gunakan Bahasa Indonesia formal dan informal/singkatan kampus yang umum "
        f"(contoh: prodi, jurusan, matkul, dosen, pegawai, mhs, nilai, perbandingan, tren, laporan).\n"
        f"2. LARANGAN: Jangan gunakan kata-kata bahasa Inggris umum seperti 'master data', 'lookup', 'table', 'dimension'.\n"
        f"3. FORMAT: Output HANYA berupa kata-kata tunggal atau frasa pendek (2-3 kata) yang dipisahkan dengan koma.\n"
        f"4. DILARANG membuat kalimat panjang atau penjelasan. Langsung ke daftar kata kuncinya saja."
    )
    
    ai_synonyms = ""
    try:
        res = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
        ai_synonyms = res["message"]["content"].strip().replace("\n", " ")
        print(f"✨ AI-Generated Synonyms: '{ai_synonyms}'")
    except Exception as e:
        print(f"⚠️ Metadata extraction skipped for {table_name}: {e}")
        ai_synonyms = "database asset"

    # Stitch the extracted DDL layout and the AI-generated context tokens together
    enriched_document = (
        f"Database Table Definition Asset:\n"
        f"{raw_blueprint}\n"
        f"Semantic Keywords & Translation Encodings: {ai_synonyms}"
    )
    
    # Save directly to your vector base collection
    doc_id = f"schema_{table_name.replace('.', '_')}_definition"
    collection.upsert(
        documents=[enriched_document],
        metadatas=[{"type": "schema_ddl"}],
        ids=[doc_id]
    )
    print(f"✅ Indexed {table_name} into ChromaDB.\n" + "-" * 40)

# 5. Cleanup
cur.close()
conn.close()
print("=" * 60)
print("🎉 Vector Base training complete! Everything was queried, analyzed, and stored autonomously.")