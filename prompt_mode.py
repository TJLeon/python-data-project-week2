def prompt_model(model: str, prompt: str) -> str :
	match model:
		case "llama3.1":
			pass
		case "phi3":
			pass
		case "deepseek-r1":
			pass
		case "gemini-2.5-flash":
			pass
		case "gemini-2.5-flash-lite":
			pass
		case "gemini-3-flash-preview":
			pass
		case _:
			raise ValueError(f"Error: model not found \"{model}\"")
	return
