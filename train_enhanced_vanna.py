import ollama
import chromadb

# 1. Initialize Clients
chroma_client = chromadb.PersistentClient(path="./vanna_knowledge_base")
collection = chroma_client.get_or_create_collection("vanna_collection")
MODEL_NAME = "qwen3.5:9b"

# 2. Define your raw table catalog data
# This simulates the data you pull from your information_schema or DDL files
database_tables = {
    "akademik.rep_perbandingan_jumlah_mahasiswa_lintas_periode": "Table comparing student counts across different academic periods.",
    "akademik.dim_bidang_studi": "Dimension table listing all fields of study / departments.",
    "akademik.dim_mahasiswa": "Master dimension table containing student profile records.",
    "kepegawaian.dim_satuan_kerja": "Dimension table for university work units and departments.",
    "public.dim_waktu": "Time dimension table containing calendar dates, months, and years."
}

def generate_ai_metadata(table_name, raw_definition):
    """Uses the 9B model to automatically generate clean bilingual semantic anchors."""
    prompt = (
        f"You are a data warehouse metadata specialist.\n"
        f"Analyze this table name and definition from an Indonesian university database system:\n"
        f"Table: {table_name}\n"
        f"Definition: {raw_definition}\n\n"
        f"Generate a dense list of search keywords, business terms, and user intents that would match this table.\n"
        f"Include both English and Indonesian variations (e.g., cross-reference terms like 'topics' to 'bidang studi', or 'trends' to 'perbandingan').\n\n"
        f"CRITICAL: Output ONLY the list of terms separated by commas. No formatting, no chat text, no markdown."
    )
    
    try:
        res = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
        return res["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Error generating metadata for {table_name}: {e}")
        return ""

# 3. Execution Training Loop
print("🚀 Starting Automated LLM Vector Enrichment Training...")
print("="*60)

for table_name, raw_definition in database_tables.items():
    print(f"🧠 AI is analyzing structure for: {table_name}...")
    
    # Let the 9B model automatically deduce the synonyms on the fly
    ai_synonyms = generate_ai_metadata(table_name, raw_definition)
    print(f"✨ Generated Metadata: '{ai_synonyms}'")
    
    # Combine the original blueprint layout with the AI's synthetic text tags
    enriched_document = (
        f"Database Table String: {table_name}\n"
        f"Raw Definition: {raw_definition}\n"
        f"Semantic Synonyms & Intent Hooks: {ai_synonyms}"
    )
    
    # Save the highly-optimized text vector block straight into ChromaDB
    collection.upsert(
        documents=[enriched_document],
        metadatas=[{"schema_type": "table_definition"}],
        ids=[f"schema_{table_name.replace('.', '_')}_definition"]
    )
    print(f"✅ Saved vector block to ChromaDB for {table_name}.\n" + "-"*40)

print("="*60)
print("🎉 Vector Base training complete! ChromaDB is now highly context-aware.")