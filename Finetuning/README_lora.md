# Fine-Tuning Qwen2.5-3B for Customer Support Using QLoRA

## Problem Statement

Large Language Models (LLMs) are powerful general-purpose text generators, but out-of-the-box they often produce generic, inconsistent responses when used in domain-specific settings like **customer support**. A company deploying a support chatbot needs responses that are professional, empathetic, and aligned with support best practices — something a base model isn't optimized for.

This project fine-tunes the **Qwen2.5-3B-Instruct** model on a real-world customer support dataset using **QLoRA** (Quantized Low-Rank Adaptation), a parameter-efficient fine-tuning technique that allows training a 3-billion-parameter model on a single free-tier Google Colab GPU. The goal is to demonstrate a measurable improvement in the quality, tone, and relevance of customer support responses after fine-tuning — while training less than **0.5% of the model's total parameters**.

---

## Approach & Key Concepts

### Why QLoRA?
Full fine-tuning of a 3B-parameter model requires significant GPU memory and compute. QLoRA solves this by:
1. **4-bit Quantization (NF4)** — The base model weights are loaded in 4-bit precision via `bitsandbytes`, drastically reducing memory footprint.
2. **Low-Rank Adapters (LoRA)** — Instead of updating all weights, small trainable adapter matrices (rank 16) are injected into the attention layers (`q_proj`, `v_proj`). Only these adapters are trained.
3. **Double Quantization** — An additional quantization pass on the quantization constants themselves, further reducing memory.

This combination enables fine-tuning a 3B model in ~6 GB of GPU memory.

### Dataset
- **Source:** [Bitext Customer Support LLM Chatbot Training Dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) (HuggingFace)
- **Size used:** 20,000 examples (sampled from the full dataset for faster training)
- **Format:** Each example is formatted into an instruction-response template:
  ```
  ### Instruction:
  You are a professional customer support agent.

  ### User:
  <customer query>

  ### Response:
  <support response>
  ```

### Tech Stack

| Component | Tool / Library |
|---|---|
| Base Model | [Qwen/Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) |
| Fine-Tuning Method | QLoRA (LoRA + 4-bit quantization) |
| PEFT Library | `peft` (HuggingFace) |
| Quantization | `bitsandbytes` (NF4, double quantization) |
| Trainer | `SFTTrainer` from `trl` (Supervised Fine-Tuning) |
| Tokenizer / Model Loading | `transformers` (HuggingFace) |
| Dataset | `datasets` (HuggingFace) |
| Compute | Google Colab (free-tier T4 GPU) |

### LoRA Configuration

| Parameter | Value | Purpose |
|---|---|---|
| `r` | 16 | Rank of the low-rank adapter matrices |
| `lora_alpha` | 32 | Scaling factor (alpha/r = 2x scaling) |
| `target_modules` | `q_proj`, `v_proj` | Attention layers where adapters are injected |
| `lora_dropout` | 0.05 | Regularization to prevent overfitting |
| `task_type` | `CAUSAL_LM` | Causal language modeling objective |

### Training Configuration

| Parameter | Value |
|---|---|
| Batch size | 2 (per device) |
| Gradient accumulation steps | 4 (effective batch size = 8) |
| Learning rate | 2e-4 |
| Epochs | 1 |
| Precision | BFloat16 |
| Warmup steps | 100 |
| Optimizer | AdamW (default) |

---

## How to Run

### Prerequisites
- Python 3.10+
- CUDA-capable GPU (tested on Google Colab T4)

### Steps

1. **Install dependencies:**
   ```bash
   pip install transformers datasets peft accelerate bitsandbytes trl
   ```

2. **Set your HuggingFace token** in the script (line 27):
   ```python
   login("YOUR_HF_TOKEN")
   ```

3. **Run the script:**
   ```bash
   python lora.py
   ```
   The script will:
   - Download and prepare the dataset
   - Load the base model in 4-bit quantization
   - Attach LoRA adapters and fine-tune for 1 epoch
   - Save the fine-tuned adapter to `./lora-support-model`
   - Run inference on 4 test prompts and print before/after comparisons

---

## Results

### Test Prompts

| ID | User Query |
|---|---|
| `auth_error` | "I am getting a 401 unauthorized error while calling API" |
| `billing_issue` | "I was charged twice for my subscription this month. Can you fix this?" |
| `feature_issue` | "I upgraded my plan but I still can't access premium features." |
| `app_crash` | "My app keeps crashing whenever I try to upload a file." |

### Before vs After Fine-Tuning

BEFORE:

ID: auth_error
USER: I am getting a 401 unauthorized error while calling API

----- BEFORE -----
To resolve the 401 Unauthorized error, first, ensure that your API credentials (like API key or token) are correctly entered and not expired. Also, check if the permissions required for your request match the settings in the API documentation. If the issue persists, please provide more details so I can assist further. 

Not sure? Let's troubleshoot step-by-step! 

Let me know if you need help with verifying your credentials or any other steps to resolve this issue. 

If you have any specific API documentation or environment details, sharing them will be really helpful for diagnosis. 

Feel free to ask if you're stuck at any point!

Thank you for providing the necessary information! 

We'll work through it together to find a solution 

========================================================================================================================================================================================================
ID: billing_issue
USER: I was charged twice for my subscription this month. Can you fix this?

----- BEFORE -----
I understand your frustration. I will investigate and resolve this issue for you as soon as possible. Please provide your account details so we can look into it further. 

========================================================================================================================================================================================================
ID: feature_issue
USER: I upgraded my plan but I still can't access premium features.

----- BEFORE -----
I understand that upgrading your plan didn't grant you access to the premium features yet. Could you please check if there are any pending tasks or if there's a delay in activation? If so, could you guide me through the steps to resolve it quickly? Otherwise, I can help troubleshoot further if needed. Let me know how you would like proceed. 
Noted that I'm here to assist you further. 

========================================================================================================================================================================================================
ID: app_crash
USER: My app keeps crashing whenever I try to upload a file.

----- BEFORE -----
I understand you're having trouble with your app crashing during file uploads. Can you please provide more details? What type of files are you trying to upload and on which device/operating system? Any error messages displayed?

---

Response continues only if more information is provided by the user, as per the given instruction.
If the user provides additional details or requests further assistance, I will respond accordingly. Otherwise, the conversation ends here based on the given instruction.

AFTER TRAINING

ID: auth_error
USER: I am getting a 401 unauthorized error while calling API

----- AFTER ------
I understand your frustration with receiving a 401 Unauthorized error while making API calls. This error typically occurs when there is an issue with authentication or authorization. To resolve this, I recommend checking the following points:

1. **Authentication Token:** Ensure that you have provided the correct access token or API key in your request headers.
2. **API Endpoint:** Verify that you are using the right endpoint for your API call.
3. **Authorization Scope:** Double-check if your current permissions allow you to make the specific API call you are trying to make.
4. **API Version:** Make sure you are using the correct version of the API.

If you still encounter issues after reviewing these points, please provide more details about the error message you receive and 

====================================================================================================
ID: billing_issue
USER: I was charged twice for my subscription this month. Can you fix this?

----- AFTER ------
I apologize for any inconvenience caused by the double charge on your subscription. I'm here to help resolve this issue and ensure it doesn't happen again. Let's work together to find a solution. Could you please provide me with your account details or any specific information about the charges? This will allow me to investigate further and assist you promptly. Thank you for bringing this matter to my attention, and I appreciate your patience as we work towards resolving it. 

====================================================================================================
ID: feature_issue
USER: I upgraded my plan but I still can't access premium features.

----- AFTER ------
I'm sorry to hear that you're experiencing difficulties accessing our premium features after upgrading. It's important for us to ensure your full access to all the benefits we offer. Let me quickly investigate and resolve this issue for you. Please provide me with some details about the specific premium features you're unable to access, such as their names or descriptions. This will help me in diagnosing the problem accurately and finding a solution swiftly. Thank you for bringing this to our attention, and I'll do everything I can to assist you. 

====================================================================================================
ID: app_crash
USER: My app keeps crashing whenever I try to upload a file.

----- AFTER ------
I'm sorry to hear that your app is crashing when you attempt to upload a file. It's important to address this issue promptly to ensure a seamless user experience. To help resolve this problem, could you please provide more details about the specific error message or any other relevant information? This will allow me to investigate the issue further and find a solution for you. Thank you for bringing this to our attention, and I appreciate your patience as we work together to troubleshoot and resolve the crash issue. 



---

## Key Takeaways

- QLoRA enables fine-tuning billion-parameter models on consumer GPUs by combining 4-bit quantization with low-rank adapters
- Only **~0.5% of parameters** are trainable, yet the model learns domain-specific tone and response patterns
- BFloat16 mixed precision is preferred over FP16 for models with BF16-native weights (avoids AMP grad scaler compatibility issues)
- The instruction-tuned base model already has conversational ability; LoRA fine-tuning *specializes* it for the customer support domain
