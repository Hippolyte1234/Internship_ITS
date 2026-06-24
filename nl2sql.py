import chromadb
import ollama
import vanna
import psycopg2
import pandas as pd

class MyPrivateVanna:
    def __init__(self, model_name="qwen2.5:3b"):
        # Initialize your local Chroma Vector DB folder mapping
        self.chroma_client = chromadb.PersistentClient(path="./vanna_knowledge_base")
        self.collection = self.chroma_client.get_or_create_collection("vanna_collection")
        self.model_name = model_name
        self.conn = None

    def connect_to_postgres(self, host, dbname, user, password="", port=5432):
        self.conn = psycopg2.connect(
            host=host, database=dbname, user=user, password=password, port=port
        )
        print(f"Connected successfully to database: {dbname}")

    def train_on_live_schema(self, schemas):
        print(f"Harvesting metadata from live catalog for schemas: {schemas}...")
       
        # Safe format handling for SQL IN arrays
        schema_list_str = ", ".join([f"'{s}'" for s in schemas])
       
        query = f"""
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema IN ({schema_list_str})
            ORDER BY table_schema, table_name, ordinal_position;
        """
       
        try:
            df = pd.read_sql_query(query, self.conn)
            if df.empty:
                print("🚨 WARNING: No tables or columns found in those schemas! Check permissions.")
                return

            # Group columns by each specific table so they get separate vector IDs
            grouped = df.groupby(['table_schema', 'table_name'])
           
            print(f"Found {len(grouped)} total tables. Committing to vector memory split loops...")

            for (schema, table), group in grouped:
                # Build a clean structural document profile for THIS table only
                table_profile = f"Table Profile: {schema}.{table}\nColumns:\n"
                for _, row in group.iterrows():
                    table_profile += f"  - {row['column_name']} ({row['data_type']})\n"
               
                # Create a completely unique tracking ID for this table record
                unique_id = f"schema_{schema}_{table}_definition"
               
                # Save into ChromaDB safely
                self.collection.upsert(
                    documents=[table_profile],
                    metadatas=[{"type": "ddl", "schema": schema, "table": table}],
                    ids=[unique_id]
                )
                print(f" -> Trained vector index for table structural node: {schema}.{table}")

            # Also seed contextual language mappings directly for translation support
            translation_glossary = (
                "Business Terminology Translation Glossary for itsdw:\n"
                "- 'students', 'student list', 'pupils', or 'undergraduates' maps directly to 'akademik.dim_mahasiswa'.\n"
                "- 'teachers', 'lecturers', 'staff', 'employees', or 'working personnel' maps directly to 'kepegawaian.dim_pegawai'.\n"
                "- 'time', 'date', or 'calendar' maps directly to 'public.dim_waktu'."
            )
            self.collection.upsert(
                documents=[translation_glossary],
                metadatas=[{"type": "documentation"}],
                ids=["business_language_synonym_glossary"]
            )
            print("\nSuccessfully populated business term translations to local store!")
            print(f"Total active records currently in vector storage: {self.collection.count()}")
           
        except Exception as e:
            print(f"Error reading database blueprint catalog: {e}")

if __name__ == "__main__":
    vn = MyPrivateVanna(model_name="qwen2.5:3b")
    vn.connect_to_postgres(host="10.199.16.221", dbname='itsdw', user='ai_llm', password='!Donald_Babatan57')
   
    # Execute the database training sequence
    vn.train_on_live_schema(['akademik', 'kepegawaian', 'public'])
