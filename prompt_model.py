from ollama import generate
from dotenv import load_dotenv
from google import genai

def ollama_model(ai_model, msg):
	try:
		res = generate(model=ai_model, prompt=msg).response
	except Exception as e:
		res = e
	return res

def gemini_model(ai_model, msg):
	try:
		load_dotenv()
		client = genai.Client()

		res = client.models.generate_content(model=ai_model, contents=msg).text
	except Exception as e:
		res = e
	return res

def prompt_model(model: str, prompt: str) -> str :
	match model:
		case "llama3.1"| "phi3"| "deepseek-r1" | "tinyllama":
			return ollama_model(model, prompt)
		case "gemini-2.5-flash" | "gemini-2.5-flash-lite" | "gemini-3-flash-preview":
			return gemini_model(model, prompt)
		case _:
			return(f"Error: model not found \"{model}\"")
	return "Error: unexpected error"
