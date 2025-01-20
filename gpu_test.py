import torch

try:
    from transformers import LlamaForCausalLM, LlamaTokenizer
except ImportError:
    print(
        "The 'transformers' module is not installed. Please install it using 'pip install transformers'"
    )
    exit()

try:
    import sentencepiece
except ImportError:
    print(
        "The 'sentencepiece' library is not installed. Please install it using 'pip install sentencepiece'"
    )
    exit()

# Check if GPU is available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load the tokenizer and model
tokenizer = LlamaTokenizer.from_pretrained("huggingface/llama")
model = LlamaForCausalLM.from_pretrained("huggingface/llama")

# Move the model to the GPU
model.to(device)

# Example input
input_text = "Hello, how are you?"
inputs = tokenizer(input_text, return_tensors="pt").to(device)

# Generate output
with torch.no_grad():
    outputs = model.generate(inputs.input_ids, max_length=50)

# Decode and print the output
output_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(output_text)
