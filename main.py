import sys
from prompt_model import prompt_model

def main():
	argc = len(sys.argv)

	if argc == 1:
		print(f"{prompt_model("tinyllama", "introduce yourself")}")
		return

	if argc != 3:
		print("Usage: uv run main.py <model> <prompt>")
		return

	model = sys.argv[1]
	prompt = sys.argv[2]

	result = prompt_model(model, prompt)
	print(result)

if __name__ == "__main__":
	main()
