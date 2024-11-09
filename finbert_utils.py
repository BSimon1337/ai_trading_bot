from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Tuple


# Set the device to GPU if available, otherwise CPU
device = "cuda:0" if torch.cuda.is_available() else "cpu"
print("Using device:", device)


# Load the tokenizer and model and move the model to the GPU
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").to(device)
labels = ["positive", "negative", "neutral"]

def estimate_sentiment(news):
    if news:
        # Tokenize input and move tokens to the correct device
        tokens = tokenizer(news, return_tensors="pt", padding=True).to(device)

        # Perform inference on the model, which is on the GPU
        result = model(tokens["input_ids"], attention_mask=tokens["attention_mask"])["logits"]

        # Move the result to CPU for further processing, if needed
        result = torch.nn.functional.softmax(torch.sum(result, 0), dim=-1)
        probability = result[torch.argmax(result)]
        sentiment = labels[torch.argmax(result)]
        return probability, sentiment
    else:
        return 0, labels[-1]

if __name__ == "__main__":
    tensor, sentiment = estimate_sentiment(['markets responded negatively to the news!', 'traders were displeased!'])
    print(tensor, sentiment)
    print("CUDA available:", torch.cuda.is_available())
