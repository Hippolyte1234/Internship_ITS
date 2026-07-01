import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
# Enable CORS so our browser index.html can query this service directly
CORS(app, resources={r"/*": {"origins": "*"}})

# Determine the absolute directory where history_service.py resides
current_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(current_dir, "firebase-key.json")

print("[HISTORY SERVICE] Connecting to Cloud Firebase Firestore...")
try:
    # Safe initialization prevents duplicate app registration errors on hot-reloads
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    print("[HISTORY SERVICE] Connected to Firestore database successfully!")
except Exception as err:
    db = None
    print(f"\n🚨 [CRITICAL ERROR]: Could not connect to Firebase: {err}\n")

# --- ENDPOINT 1: GET ALL CHAT SESSIONS (METADATA ONLY) ---
@app.route('/get-sessions', methods=['GET'])
def get_sessions():
    if db is None:
        return jsonify({"error": "Database service is offline"}), 503
    try:
        sessions_ref = db.collection("chat_sessions")
        # Sort history items showing the latest updated chats first
        query = sessions_ref.order_by("updated_at", direction=firestore.Query.DESCENDING)
        docs = query.stream()

        sessions = []
        for doc in docs:
            data = doc.to_dict()
            sessions.append({
                "session_id": data.get("session_id"),
                "title": data.get("title", "Untitled Session"),
                "updated_at": data.get("updated_at").isoformat() if data.get("updated_at") else None
            })

        return jsonify({"sessions": sessions})
    except Exception as e:
        print(f"[ERROR FETCHING SESSIONS]: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT 2: GET FULL CONVERSATION DETAILS ---
@app.route('/get-session/<session_id>', methods=['GET'])
def get_session_details(session_id):
    if db is None:
        return jsonify({"error": "Database service is offline"}), 503
    try:
        session_ref = db.collection("chat_sessions").document(session_id)
        doc = session_ref.get()

        if not doc.exists:
            return jsonify({"error": f"Session {session_id} not found"}), 404

        return jsonify(doc.to_dict())
    except Exception as e:
        print(f"[ERROR FETCHING SESSION {session_id}]: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("[HISTORY SERVICE] Starting on http://127.0.0.1:5051...")
    app.run(host='127.0.0.1', port=5051, debug=True)