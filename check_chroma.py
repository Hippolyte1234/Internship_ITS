import chromadb

chroma_client = chromadb.PersistentClient(path="./vanna_knowledge_base")
collection = chroma_client.get_or_create_collection("vanna_collection")

# Retrieve everything to see what tables are indexed
all_data = collection.get()
ids = all_data.get("ids", [])

print("\n📋 All Table Schemas Stored inside ChromaDB:")
print("="*50)
table_schemas = sorted(list(set([i for i in ids if "schema_" in i])))
for schema_id in table_schemas:
    print(f" 🔹 {schema_id}")
print("="*50)