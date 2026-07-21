ollama_client = Client(host='http://127.0.0.1:11434', timeout=1800.0)

def __init__(self, model_name="qwen3.5:9b"):
	self.model_name = model_name