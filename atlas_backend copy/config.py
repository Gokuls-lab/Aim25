import os

# --- LLM CONFIGURATION ---
# Use a model good at following instructions. 
# Recommended: "qwen2.5:7b" or "llama3.2" or "mistral"
#"qwen3:4b-instruct-2507-q4_K_M qwen3:1.7b"
MODEL_NAME = "qwen3:4b-instruct-2507-q4_K_M" 
TIMEOUT = 120 # Seconds for LLM generation

# --- BROWSER CONFIGURATION ---
# Path to your Brave Browser executable
# Linux Default: "/opt/brave.com/brave/brave"
# Mac Default: "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
# Windows Default: "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
BRAVE_PATH = "/opt/brave.com/brave/brave"

# Path to your User Profile (Keep this to reuse cookies/logins)
USER_DATA_DIR = os.path.expanduser("~/.config/BraveSoftware/Brave-Browser")
PROFILE_DIR = "Default"

# --- OUTPUT ---
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)