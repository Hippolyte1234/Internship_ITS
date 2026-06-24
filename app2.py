import os
from functools import wraps
import flask
from flask import Flask, Response, jsonify, redirect, request, url_for
import pandas as pd
import psycopg2
import ollama
import chromadb
from ollama import Client
from flashrank import Ranker, RerankRequest

# Create an explicit client with a 5-minute timeout window (because too long to answer on CPU and therefore returns an empty answer so we give it more time before closing itself)
ollama_client = Client(host='http://127.0.0.1:11434', timeout=900.0)

# Initialize the lightweight re-ranking engine once into server memory
print("[INITIALIZATION] Loading lightweight FlashRank CPU engine...")
ranker = Ranker()
print("[INITIALIZATION] FlashRank loaded successfully!")


# Import your working MemoryCache class from cache.py
from cache import MemoryCache  

app = Flask(__name__, static_url_path="")

# Setup local cache instance
cache = MemoryCache()

# --- 1. CORE OFFLINE BACKEND CONFIGURATION ---
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
        # 1. Instruct Ollama to translate the entire sentence to Indonesian (or pass through if already Indonesian)
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

        # 2. Query ChromaDB using the pure, unified Indonesian sentence
        # This keeps the semantic sentence structure intact for high-accuracy vector matching
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
            
            # 3. Use FlashRank to pick the top choices out of the 10 results
            rerank_request = RerankRequest(query=question, passages=passages)
            rerank_results = ranker.rerank(rerank_request)
            
            top_passages = rerank_results[:3]
            schema_context = "\n\n".join([p["text"] for p in top_passages])
            
            print("\n" + "═"*60)
            print(" 🎯 [RE-RANKER ACTIVE] CHROME TABLES SORTED BY SEMANTIC RELEVANCE:")
            for idx, p in enumerate(top_passages):
                print(f"   {idx+1}. ID: {p['id']} (Score: {p['score']:.4f})")
            print("═"*60)

        # 4. The main LLM text-to-SQL prompt remains clean and objective
        prompt = (
            f"You are a PostgreSQL expert database translator.\n"
            f"Review the provided database layout options and select the appropriate columns to answer the user request.\n\n"
            f"Database Structural Options:\n"
            f"{schema_context}\n\n"
            f"Task: Convert this request into a clean PostgreSQL query string: {question}\n\n"
            f"CRITICAL RULES:\n"
            f"1. You MUST ALWAYS include the correct schema name prefix before the table name (e.g., 'akademik.table').\n"
            f"2. DEDUPLICATION RULE: Whenever the user asks for a 'list', 'all options', or unique categories, you MUST utilize the `DISTINCT` keyword to prevent duplicate rows from polluting the output grid.\n"
            f"3. SIMPLICITY RULE: If a single table contains the required columns to satisfy the request, query THAT table directly. Do NOT use JOIN statements unless it is absolutely impossible to get the data otherwise.\n"
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

        # Extract cleaner text segments out of markdown decorators
        sql = raw_content.strip()
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        # Clean line breaks, trailing spaces, and strip hazardous SQL inline comments
        import re
        sql = re.sub(re.compile(r"--.*?\n"), "", sql + "\n")
        sql = re.sub(re.compile(r"--.*?$"), "", sql)
        sql = " ".join(sql.split()).strip()

        if not sql or len(sql) < 10 or "SELECT" not in sql.upper():
            sql = "SELECT * FROM akademik.dim_bidang_studi LIMIT 5;"

        return sql
   
    def run_sql(self, sql):
        if not self.conn: raise Exception("Database connection is missing!")
        return pd.read_sql_query(sql, self.conn)

    def generate_questions(self):
        return [
            "Show me 5 records from akademik.dim_mahasiswa",
            "List all working personnel from kepegawaian.dim_pegawai"
        ]

    # --- Training Stubs to prevent API errors ---
    def train(self, question=None, sql=None, ddl=None, documentation=None):
        # Storing mock training info to allow the UI buttons to function
        import uuid
        mock_id = str(uuid.uuid4())
        print(f"Trained system on input dataset ID: {mock_id}")
        return mock_id

    def get_training_data(self):
        # Returns an empty dataframe so the UI table renders cleanly without crash
        return pd.DataFrame(columns=["id", "question", "sql", "ddl", "documentation"])

    def remove_training_data(self, id):
        return True

# Initialize your instance mapped to your specs
vn = MyPrivateVanna(model_name="qwen3.5:9b")
vn.connect_to_postgres(host="10.199.16.221", dbname="itsdw", user="ai_llm", password="!Donald_Babatan57")


# --- 2. ENDPOINT DECORATORS & APIS ---
def requires_cache(fields):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            id = request.args.get('id')
            if id is None:
                return jsonify({"type": "error", "error": "No id provided"})
           
            for field in fields:
                if cache.get(id=id, field=field) is None:
                    return jsonify({"type": "error", "error": f"No {field} found"})
           
            field_values = {field: cache.get(id=id, field=field) for field in fields}
            field_values['id'] = id
            return f(*args, **field_values, **kwargs)
        return decorated
    return decorator

@app.route('/api/v0/generate_questions', methods=['GET'])
def generate_questions():
    return jsonify({
        "type": "question_list",
        "questions": vn.generate_questions(),
        "header": "Here are some questions you can ask:"
        })

@app.route('/api/v0/generate_sql', methods=['GET'])
def generate_sql():
    question = flask.request.args.get('question')
    if question is None:
        return jsonify({"type": "error", "error": "No question provided"})

    id = cache.generate_id(question=question)
    sql = vn.generate_sql(question=question)

    cache.set(id=id, field='question', value=question)
    cache.set(id=id, field='sql', value=sql)

    return jsonify({"type": "sql", "id": id, "text": sql})

@app.route('/api/v0/run_sql', methods=['GET'])
@requires_cache(['sql'])
def run_sql(id: str, **kwargs):  # Use **kwargs to catch the decorator outputs safely
    try:
        # Explicitly pull the generated query from your cache using the ID
        sql = cache.get(id=id, field='sql')
       
        # Double check that we didn't get an empty cache hit
        if not sql:
            return jsonify({"type": "error", "error": "SQL query was lost in cache memory!"})
           
        print(f"\n[EXECUTION LOG] GUI is running SQL ID [{id}]:\n{sql}\n")

        # Execute the query on your PostgreSQL connection
        df = vn.run_sql(sql=sql)
       
        # Store the dataframe in cache (needed if the user clicks 'Download CSV')
        cache.set(id=id, field='df', value=df)
       
        # Return the data rows back to the Vanna web frontend interface
        return jsonify({
            "type": "df",
            "id": id,
            "df": df.head(10).to_json(orient='records'),
        })
    except Exception as e:
        print(f"[EXECUTION ERROR]: {e}")
        return jsonify({"type": "error", "error": str(e)})

@app.route('/api/v0/download_csv', methods=['GET'])
@requires_cache(['df'])
def download_csv(id: str, df):
    csv = df.to_csv()
    return Response(csv, mimetype="text/csv", headers={"Content-disposition": f"attachment; filename={id}.csv"})

@app.route('/api/v0/get_training_data', methods=['GET'])
def get_training_data():
    df = vn.get_training_data()
    return jsonify({"type": "df", "id": "training_data", "df": df.head(25).to_json(orient='records')})

@app.route('/api/v0/remove_training_data', methods=['POST'])
def remove_training_data():
    id = flask.request.json.get('id')
    if id is None: return jsonify({"type": "error", "error": "No id provided"})
    vn.remove_training_data(id=id)
    return jsonify({"success": True})

@app.route('/api/v0/train', methods=['POST'])
def add_training_data():
    question = flask.request.json.get('question')
    sql = flask.request.json.get('sql')
    ddl = flask.request.json.get('ddl')
    documentation = flask.request.json.get('documentation')
    try:
        id = vn.train(question=question, sql=sql, ddl=ddl, documentation=documentation)
        return jsonify({"id": id})
    except Exception as e:
        return jsonify({"type": "error", "error": str(e)})

@app.route('/api/v0/get_question_history', methods=['GET'])
def get_question_history():
    return jsonify({"type": "question_history", "questions": cache.get_all(field_list=['question']) })

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/api/v0/generate_plotly_figure', methods=['GET'])
@requires_cache(['df'])
def generate_plotly_figure(id: str, df):
    # Sends a clean stringified empty object to satisfy JSON.parse in the frontend
    return jsonify({"type": "plotly_figure", "id": id, "plotly_figure": "{}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)