from datasets import load_dataset
from transformers import BertTokenizer
from transformers import BertForSequenceClassification
from transformers import TrainingArguments
from transformers import Trainer
import torch

dataset = load_dataset("imdb")  # movie reviews
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

def tokenize(example):
    return tokenizer(
        example["text"],
        padding="max_length",
        truncation=True,
        max_length=128
    )

dataset = dataset.map(tokenize, batched=True)
dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])


model = BertForSequenceClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=2  # positive / negative
)



training_args = TrainingArguments(
    output_dir="./results",
    learning_rate=2e-5,
    per_device_train_batch_size=64,
    per_device_eval_batch_size=64,
    num_train_epochs=1,
    eval_strategy="epoch",
    # evaluation_strategy = "steps",
    # eval_steps = 500,
    logging_dir="./logs",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"].shuffle(seed=42).select(range(2000)),  # small subset
    eval_dataset=dataset["test"].select(range(1000)),
)

trainer.train()

trainer.evaluate()



text = "This movie was absolutely fantastic!"

inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

with torch.no_grad():
    outputs = model(**inputs)

logits = outputs.logits
pred = torch.argmax(logits, dim=1).item()

print("Positive" if pred == 1 else "Negative")
