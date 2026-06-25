# -*- coding: utf-8 -*-


# !pip install -q transformers datasets peft accelerate bitsandbytes trl

from datasets import load_dataset

dataset = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset", split="train")

dataset = dataset.shuffle(seed=42).select(range(20000))  # keep small for Colab

def format_example(example):
    return {
        "text": f"""### Instruction:
You are a professional customer support agent.

### User:
{example['instruction']}

### Response:
{example['response']}"""
    }

dataset = dataset.map(format_example)

from huggingface_hub import login
login("YOUR TOKEN")

dataset[0]

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "Qwen/Qwen2.5-3B-Instruct" #  "mistralai/Mistral-7B-Instruct-v0.1" # "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    torch_dtype=torch.float16
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto"
)

from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",    # Do not train any bias terms, "all" - train all bias, "lora-only" - only for layers where LoRA is applied
    task_type="CAUSAL_LM"  # GPT-style training - text generation
    # task_type="SEQ_CLS"   # classification (BERT)
    # task_type="SEQ_2_SEQ_LM"   # translation (T5 (text to text transfer transformer), BART)
    # task_type="FEATURE_EXTRACTION"   # embeddings
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

from transformers import TrainingArguments
from trl import SFTTrainer

training_args = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    logging_steps=50,
    num_train_epochs=1,
    fp16=False,
    bf16=True,
    save_steps=200,
    warmup_steps=100,
    report_to="none"  # ML flow
)

def formatting_func(example):
    return example["text"]

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    formatting_func=lambda x: x["text"],
    args=training_args,
)

model.config.use_cache = False
trainer.train()
model.save_pretrained("lora-support-model")
tokenizer.save_pretrained("lora-support-model")

from transformers import pipeline

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=200  # how many tokens the model is allowed to generate as output.
)

prompts = [
    {
        "id": "auth_error",
        "user": "I am getting a 401 unauthorized error while calling API"
    },
    {
        "id": "billing_issue",
        "user": "I was charged twice for my subscription this month. Can you fix this?"
    },
    {
        "id": "feature_issue",
        "user": "I upgraded my plan but I still can't access premium features."
    },
    {
        "id": "app_crash",
        "user": "My app keeps crashing whenever I try to upload a file."
    }
]

def build_prompt(user_query):
    return f"""### Instruction:
You are a professional customer support agent.
Answer ONLY once. Do not continue the conversation.

### User:
{user_query}

### Response:
"""

def run_inference(pipe, prompts):
    results = []

    for item in prompts:
        prompt = build_prompt(item["user"])

        output = pipe(
            prompt,
            max_new_tokens=150,
            return_full_text=False
        )[0]["generated_text"]

        # clean unwanted continuation
        clean_output = output.split("### User:")[0].strip()

        results.append({
            "id": item["id"],
            "user": item["user"],
            "response": clean_output
        })

    return results

pre_results = run_inference(pipe, prompts)
for i in range(len(prompts)):
    print("=" * 200)
    print(f"ID: {pre_results[i]['id']}")
    print(f"USER: {pre_results[i]['user']}\n")

    print("----- BEFORE -----")
    print(pre_results[i]["response"], "\n")

post_results = run_inference(pipe, prompts)
for i in range(len(prompts)):
    print("=" * 100)
    print(f"ID: {pre_results[i]['id']}")
    print(f"USER: {pre_results[i]['user']}\n")


    print("----- AFTER ------")
    print(post_results[i]["response"], "\n")
