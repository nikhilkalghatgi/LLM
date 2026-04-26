# 🧠 Patient Sentiment Analysis Using NLP & LLMs

This project analyzes open-ended patient reviews to predict sentiment (positive or negative) using Natural Language Processing (NLP) techniques and Large Language Models (LLMs).

## 🚀 Project Overview

- **Goal**: Classify patient feedback based on sentiment
- **Dataset**: 996 hospital reviews with labeled sentiment
- **Techniques used**:
  - Text cleaning and preprocessing (NLTK, regex)
  - Exploratory Data Analysis (word clouds, word frequencies, review length)
  - Feature extraction with TF-IDF
  - Sentiment classification using:
    - Logistic Regression (baseline)
    - distilBERT LLM from Hugging Face (zero-shot)

## 🗂️ Project Structure

<pre><code>
patient-sentiment-healthcare/
├── data/
│ ├── dataset_hospital_reviews.csv #raw
│ └── dataset_hospital_reviews_cleaned.csv #processed
├── notebooks/
│ ├── 01_data_cleaning_and_eda.ipynb # Data cleaning + EDA
│ └── 02_modeling_and_llm_comparison.ipynb # Model training + LLM comparison
├── README.md
</code></pre>

## 📊 Results Summary

### Logistic Regression (TF-IDF)

- Accuracy: 0.86
- High precision on positive class
- Poor recall on negative class

### distilBERT (LLM)

- Accuracy: 0.78
- Much better at identifying negative reviews
- Balanced recall across classes

## 🧪 Example Review

> "Wait hour despite appointment isn’t first time happened understanding manage appointment queue it’s random unorganised lot scope improve"

--> Detected as **NEGATIVE** by distilBERT

## 🛠️ Tech Stack

- Python, Pandas, Scikit-learn, NLTK, Matplotlib, Seaborn
- Hugging Face Transformers (distilBERT)
- Google Colab (for LLM execution)

## 📁 How to Run

1. Open `02_modeling_and_llm_comparison.ipynb` in [Google Colab](https://colab.research.google.com/)
2. Mount your Google Drive and upload the cleaned dataset (or use the one provided)
3. Run the cells to explore, train, and evaluate both models

