from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MODEL_NAME = "qwen3.5:9b"  

OLLAMA_API = "http://localhost:11434/api/chat"

@app.route('/ask-ai', methods=['POST'])
def ask_ai():
    # 1. Grab the array of message histories sent from the website browser
    conversation_history = request.json.get("history", [])
    
    print(f"\n[SERVER LOG]: Processing chat turn #{len(conversation_history)}")
    
    # 2. Package the full history array into Ollama's native endpoint framework
    payload = {
        "model": MODEL_NAME,
        "messages": conversation_history, # Sends the entire chain of past dialogue
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=900)
        print(f"[OLLAMA RESPONSE CODE]: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[OLLAMA ERROR DETAIL]: {response.text}")
            return jsonify({"error": f"Ollama error: {response.text}"}), response.status_code
            
        return jsonify(response.json())
        
    except requests.exceptions.ConnectionError:
        print("[ERROR]: Ollama is not running in the background! Please open the Ollama application first.")
        return jsonify({"error": "Ollama is not running on port 11434"}), 500
    except Exception as e:
        print(f"[OTHER ERROR]: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050)

