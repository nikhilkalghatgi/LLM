from transformers import BertTokenizer, BertForSequenceClassification
import torch

# 1. Load the fine-tuned model from the checkpoint directory
model_path = "./results/checkpoint-32"
model = BertForSequenceClassification.from_pretrained(model_path)

# 2. Load the matching tokenizer
# Since we didn't explicitly save a custom tokenizer in the fine-tuning script,
# we just use the original 'bert-base-uncased' tokenizer.
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

def predict_sentiment(text):
    # 3. Tokenize the input text
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    # 4. Run the model
    with torch.no_grad():
        outputs = model(**inputs)

    # 5. Interpret the output
    logits = outputs.logits
    pred = torch.argmax(logits, dim=1).item()
    
    # In our fine-tuning script, we assumed standard IMDB mapping:
    # 1 is Positive, 0 is Negative (usually).
    return "Positive" if pred == 1 else "Negative"

if __name__ == "__main__":
    # Test our fine-tuned inference
    test_texts = [
        "This movie was absolutely fantastic! I loved every minute of it.",
        "A complete waste of time. The acting was terrible."
    ]

    for text in test_texts:
        sentiment = predict_sentiment(text)
        print(f"Text: '{text}'")
        print(f"Predicted Sentiment: {sentiment}\n")
