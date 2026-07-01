import os
import re
import psycopg2
import pandas as pd
import chromadb
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from ollama import Client
from flashrank import Ranker, RerankRequest
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase Admin SDK
current_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(current_dir, "firebase-key.json")

cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- 1. CORE OFFLINE VANNA PIPELINE CLASS ---
class MyPrivateVanna:
    def __init__(self, model_name="qwen3.5:9b"):
        self.model_name = model_name
        self.chroma_client = chromadb.PersistentClient(path="./vanna_knowledge_base")
        self.collection = self.chroma_client.get_or_create_collection("vanna_collection")
        self.conn = None

    def connect_to_postgres(self, host, dbname, user, password="", port=5432):
        self.conn = psycopg2.connect(host=host, database=dbname, user=user, password=password, port=port)
        print(f"Connected successfully to database: {dbname}")

    def generate_sql(self, question):
        # 1. Instruct Ollama to translate the entire sentence to Indonesian
        translation_prompt = (
            f"You are a bilingual database administrator translation assistant.\n"
            f"Context: The user is querying the database of ITS university (Institut Teknologi Sepuluh Nopember)"
            f"Task: Convert the user's data request into a natural, grammatically correct Indonesian sentence "
            f"using formal database schema and academic data warehouse terminology.\n\n"
            f"User Request: {question}\n"
            f"CRITICAL: Output ONLY the translated Indonesian sentence. Do not include introductory text, explanations, or quotes."
        )
        
        indonesian_sentence = ""
        try:
            res = ollama_client.chat(model=self.model_name, messages=[{"role": "user", "content": translation_prompt}])
            indonesian_sentence = res["message"]["content"].strip().strip('"').strip("'")
            print(f"🌐 [TRANSLATION LAYER] Input: '{question}' ──> Chroma Query: '{indonesian_sentence}'")
        except Exception as e:
            print(f"⚠️ Translation layer failed, using original query. Error: {e}")
            indonesian_sentence = question

        # 2. Query ChromaDB using the Indonesian sentence
        chroma_results = self.collection.query(query_texts=[indonesian_sentence], n_results=20)
        
        if not chroma_results["documents"] or not chroma_results["documents"][0]:
            schema_context = ""
        else:
            raw_docs = chroma_results["documents"][0]
            raw_ids = chroma_results["ids"][0]
            
            passages = [
                {"id": doc_id, "text": doc_text} 
                for doc_id, doc_text in zip(raw_ids, raw_docs)
            ]
            
            # 3. Use FlashRank to pick the top choices out of the 20 results
            rerank_request = RerankRequest(query=indonesian_sentence, passages=passages)
            rerank_results = ranker.rerank(rerank_request)
            
            top_passages = rerank_results[:3]
            schema_context = "\n\n".join([p["text"] for p in top_passages])
            
            print("\n" + "═"*60)
            print("schema_context: ",schema_context) #debug
            print(" 🎯 [RE-RANKER ACTIVE] CHROME TABLES SORTED BY SEMANTIC RELEVANCE:")
            for idx, p in enumerate(top_passages):
                print(f"   {idx+1}. ID: {p['id']} (Score: {p['score']:.4f})")
            print("═"*60)

        # 4. Synthesize the main LLM Prompt
        prompt = (
            f"You are a PostgreSQL expert database translator.\n"
            f"Review the provided database layout options and select the appropriate columns to answer the user request.\n\n"
            f"Database Structural Options:\n"
            f"{schema_context}\n\n"
            f"Task: Convert this request into a clean PostgreSQL query string: {question}\n\n"
            f"CRITICAL RULES:\n"
            f"1. You MUST ALWAYS include the correct schema name prefix before the table name (e.g., 'akademik.table').\n"
            f"2. DEDUPLICATION RULE: Whenever the user asks for a 'list', 'all options', or unique categories, you MUST utilize the `DISTINCT` keyword to prevent duplicate rows from polluting the output grid.\n"
            f"3. Whenever necessary, use 'WHERE' keyword to cross search from the tables needed.\n"
            f"4. Output ONLY the raw executable SQL inside a markdown block wrapper:\n"
            f"```sql\n"
            f"SELECT ... FROM ...;\n"
            f"```\n"
            f"5. Do not write explanations, introductions, or warnings. Output ONLY the code block."
        )

        print("\n" + "="*60)
        print(" 🔥 [LIVE STREAM DEBUGGER] OLLAMA IS EXAMINING RE-RANKED BLUEPRINTS:")
        print("="*60)

        raw_content = ""
        try:
            response_stream = ollama_client.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}], stream=True)
            for chunk in response_stream:
                token = chunk["message"]["content"]
                raw_content += token
                print(token, end="", flush=True)
        except Exception as e:
            print(f"\n🚨 [OLLAMA ENGINE CRASH]: {e}")

        print("\n" + "="*60)

        # Extract code from markdown block
        print("raw_content: ",raw_content) #debug
        sql = raw_content.strip()
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        # Sanitize query comments
        sql = re.sub(re.compile(r"--.*?\n"), "", sql + "\n")
        sql = re.sub(re.compile(r"--.*?$"), "", sql)
        sql = " ".join(sql.split()).strip()

        # Fallback if query output is corrupt
        if not sql or len(sql) < 10 or "SELECT" not in sql.upper():
            sql = "SELECT * FROM akademik.dim_bidang_studi LIMIT 5;"

        return sql
   
    def run_sql(self, sql):
        if not self.conn: 
            raise Exception("Database connection is missing!")
        return pd.read_sql_query(sql, self.conn)


# --- 2. INITIALIZE GLOBAL SERVICES ---
print("[INITIALIZATION] Loading lightweight FlashRank CPU engine...")
ranker = Ranker()
print("[INITIALIZATION] FlashRank loaded successfully!")

# Timeout configurations to protect slow model generation steps on local CPU
ollama_client = Client(host='http://127.0.0.1:11434', timeout=1800.0)

# Instantiate and configure Vanna to point to the specific university DW
vn = MyPrivateVanna(model_name="qwen3.5:9b")
vn.connect_to_postgres(host="10.199.16.221", dbname="itsdw", user="ai_llm", password="!Donald_Babatan57")


# --- 3. UNIFIED CHAT API ENDPOINT ---
query_cache = {}

@app.route('/ask-ai', methods=['POST'])
def ask_ai():
    try:
        payload = request.get_json()
        chat_history = payload.get("history", [])

        session_id = payload.get("session_id") or str(uuid.uuid4())
        
        if not chat_history:
            return jsonify({"error": "No prompt history found."}), 400

        # Extract the user's latest message
        user_question = chat_history[-1]["content"]
        print(f"\n[SERVER API]: Processing database question: '{user_question}'")

        # 1. Pipeline Action: Turn text to clean SQL using offline translation + Vector match + Re-ranker
        sql_query = vn.generate_sql(user_question)
        print(f"[SERVER API]: Resulting SQL Statement -> {sql_query}")

        # 2. Pipeline Action: Execute query on the Postgres database connection
        df = vn.run_sql(sql_query)

        #store the id to retrieve easily later for download_csv
        query_id = str(uuid.uuid4())
        records = []

        # Convert DataFrame results to serialized JSON records
        records = []
        if df is not None:
            query_cache[query_id] = df

            # We cap at the top 100 rows to avoid crashing the client-side UI
            records = df.head(10).to_dict(orient="records")

        # 3. Structure Assistant Reply (Markdown format with syntax block tags)
        ai_reply = f"**Generated SQL Query:**\n```sql\n{sql_query}\n```\n\n**Query Database Results:**\n"
        if len(records) == 0:
            ai_reply += "No matching records found for this database query."
        else:
            ai_reply += f"Query executed successfully. Displaying **{len(records)}** row(s) below."

        print("records: ",records)

        # Handles the firestore collections writing
        # 1. Append the assistant's new response to the local chat history list
        updated_history = list(chat_history)
        updated_history.append({ "role": "assistant", "content": ai_reply })

        # 2. Add these lines to write to Firestore
        if db is not None:
            # Generate a clean short title from the first question
            session_title = chat_history[0]["content"] if len(chat_history) > 0 else user_question
            if len(session_title) > 40:
                session_title = session_title[:37] + "..."

            # THIS is the part that implicitly creates the collection and document
            session_ref = db.collection("chat_sessions").document(session_id)
            session_ref.set({
                "session_id": session_id,
                "title": session_title,
                "updated_at": datetime.utcnow(),
                "history": updated_history
            })
            print(f"[SERVER]: Syncing session {session_id} to Firestore.")

        return jsonify({
            "message": {
                "role": "assistant",
                "content": ai_reply,
                "query_id": query_id,
                "raw_data": records
            }
        })
        
        

    except Exception as e:
        print(f"[PIPELINE ERROR DETECTED]: {str(e)}")

        return jsonify({
            "error": "Failed to complete AI database pipeline transaction",
            "details": str(e)
        }), 500

@app.route('/download-csv', methods=['GET'])
def download_csv():
    try:
        # 1. Grab the unique query cache ID from the URL parameters (?id=...)
        query_id = request.args.get('id')
        if not query_id:
            return jsonify({"error": "No query ID provided."}), 400
        
        # Safely bind to the global query_cache dictionary defined at the top of your server file
        global query_cache

        print(f"\n[SERVER CSV DOWNLOAD]: Retrieving dataset reference [{query_id}] from in-memory cache...")
        
        # 2. Retrieve the pre-computed DataFrame from cache to avoid hitting the database again
        if query_id not in query_cache:
            return jsonify({"error": "Cached dataset has expired or was not found. Please re-run your prompt query."}), 404

        df=query_cache[query_id]
            
        # Convert DataFrame to a raw CSV format
        csv_data = df.to_csv(index=False)
        
        # Return CSV file with attachment headers to trigger the browser's download prompt
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=query_results.csv"}
        )
    except Exception as e:
        print(f"[CSV DOWNLOAD ERROR]: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Running on local loopback interface (Port 5050) to route traffic from HTML frontend
    app.run(host='127.0.0.1', port=5050, debug=True)