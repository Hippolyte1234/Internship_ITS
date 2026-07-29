import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from ollama import Client
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

ollama_client = Client(host='http://127.0.0.1:11434', timeout=1800.0)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Firebase Admin SDK
current_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(current_dir, "firebase-key.json")

cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

class MyGateway:
    def __init__(self, model_name):
        self.llm = ollama_client
        self.model_name = model_name

    def pipeline(self,question):
        res = ollama_client.chat(model=self.model_name, messages=[{"role": "user", "content": question}])
        return res["message"]["content"]


mg = MyGateway(model_name="qwen3.5:9b")

@app.route('/ask-ai', methods=['POST'])
def ask_ai():
    try:
        payload = request.get_json()
        chat_history = payload.get("history", [])

        session_id = payload.get("session_id") or str(uuid.uuid4())

        if not chat_history:
            return jsonify({"error": "No prompt history found."}), 400

        user_question = chat_history[-1]["content"]
        print(f"\n[SERVER API]: Processing user question: '{user_question}'")

        answer = mg.pipeline(user_question)
        print(f"[SERVER API]: Resulting Ollama Answer-> {answer}")

        # Handles the firestore collections writing
        # 1. Append the assistant's new response to the local chat history list
        updated_history = list(chat_history)
        updated_history.append({ "role": "assistant", "content": answer})

        # 2. Add these lines to write to Firestore
        if db is not None:
            # Generate a clean short title from the first question
            session_title = user_question
            if len(session_title) > 40:
                session_title = session_title[:37] + "..."

            # THIS is the part that implicitly creates the collection and document
            session_ref = db.collection("chat_sessions").document(session_id)
            session_ref.set({
                "session_id": session_id,
                "title": session_title,
                "updated_at": datetime.now(timezone.utc),
                "history": updated_history
            })
            print(f"[SERVER]: Syncing session {session_id} to Firestore.")

        return jsonify({
            "message": {
                "role": "assistant",
                "content": answer,
            },
            "session_id": session_id
        })

    except Exception as e:
        # Added a quick error catch here just in case something fails!
        print(f"[ERROR]: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5053, debug=True)