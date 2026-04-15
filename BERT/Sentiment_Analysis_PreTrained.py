from transformers import pipeline, BertTokenizer, BertForSequenceClassification
import torch

def pipeline1():
    classifier = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )

    text = "I love this product, it's amazing!"

    result = classifier(text)
    print(result)


def pipeline2():
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertForSequenceClassification.from_pretrained("bert-base-uncased")

    text = "I love this!"
    inputs = tokenizer(text, return_tensors="pt")

    outputs = model(**inputs)
    pred = torch.argmax(outputs.logits, dim=1)

    print(pred)

pipeline2()