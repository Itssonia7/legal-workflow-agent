import requests

def check_ollama_health():
    """
    Pings the local Ollama server.
    Returns True if it is awake and responding, False if it is down.
    """
    print("[🏥 System Check] Pinging local Ollama server...")
    try:
        # 11434 is the default port where Ollama runs locally
        response = requests.get("http://localhost:11434/")
        
        if response.status_code == 200:
            print("[🟢 System Check] Ollama is awake and ready!")
            return True
        else:
            print(f"[🔴 System Check] Ollama responded with an error: {response.status_code}")
            return False
            
    except requests.ConnectionError:
        # If it can't connect at all, it will trigger this exception
        print("[🔴 System Check] CRITICAL ERROR: Cannot connect to Ollama.")
        print(" -> Did you forget to run 'ollama serve' in your terminal?")
        return False