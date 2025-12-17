import ollama
import json
import re
import config

class LLMEngine:
    def __init__(self):
        self.model = config.MODEL_NAME

    def generate(self, prompt, system_prompt="You are a helpful research assistant."):
        """Standard text generation."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0,
                    'num_ctx': 4096 # Ensure enough context for search results
                }
            )
            return response['message']['content']
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return "Error generating response."

    def generate_json(self, prompt):
        """Forces JSON output from the LLM."""
        full_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown formatting."
        response = self.generate(full_prompt, system_prompt="You are a JSON generator. Output only raw JSON.")
        
        # Cleaner: Extract JSON if wrapped in markdown
        cleaned = response.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex extraction
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            print(f"⚠️ JSON Parse Failed. Raw: {cleaned[:50]}...")
            return {}