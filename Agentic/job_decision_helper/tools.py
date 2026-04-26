from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from rag_pipeline import retrieve_docs, format_retrieved_docs
import re

# 1. RAG Retriever
@tool
def rag_retriever(query: str) -> str:
    """Search the internal knowledge base for job descriptions, blogs, formatting guidelines, and local project tutorials.
    Use this FIRST when answering questions about specific internal project knowledge, career paths, or roles."""
    docs = retrieve_docs(query, k=3)
    return format_retrieved_docs(docs)

# 2. Web Search
# Instantiate the Tavily search tool natively provided by LangChain
web_search = TavilySearchResults(
    max_results=3,
    description="Search the web for the latest global trends, up-to-date industry news, or broad facts not found internally."
)

# 3. Simple Analyzer
@tool
def compare_roles(data: str) -> str:
    """Extract skills, demand, and salary trends from raw text or search results. 
    Use this tool AFTER gathering information using rag_retriever or web_search to structure your findings and compare roles."""
    
    # Fake/heuristic logic: analyze keyword frequency
    keywords = [
        "python", "machine learning", "react", "ai", "sql", "cloud", "aws", "gcp",
        "data science", "engineering", "backend", "frontend", "devops", "llm", "generative ai"
    ]
    
    data_lower = data.lower()
    found_skills = {kw: data_lower.count(kw) for kw in keywords if kw in data_lower}
    
    # Sort skills by frequency
    sorted_skills = sorted(found_skills.items(), key=lambda x: x[1], reverse=True)
    
    # Extracted Salary mentions (look for $xx,xxx or $xxxk)
    salaries = re.findall(r'\$\d{2,3}(?:,\d{3}|k)', data_lower)
    unique_salaries = list(set(salaries))
    
    analysis = "📊 **Role Comparison & Analyzer Results**\n"
    analysis += "Based on the provided data context, here are the extracted analytical trends:\n\n"
    
    if sorted_skills:
        analysis += "**Core Skills Detected (Demand Heatmap):**\n"
        for kw, count in sorted_skills:
            if count > 0:
                analysis += f"- **{kw.title()}**: mentioned {count} time(s)\n"
    else:
        analysis += "- _No targeted core skills detected in provided text._\n"
        
    analysis += "\n**Salary Trends & Compensation Signals:** \n"
    if unique_salaries:
        analysis += f"- Extracted Salary mentions: {', '.join(unique_salaries)}\n"
    else:
        analysis += "- _No explicit salary data found in context._\n"
        
    analysis += "\n**General Guidance:** \n"
    analysis += "- High frequency of AI/LLM generally indicates premium tiers.\n"
    analysis += "- Compare these skills back to the user's current skillset.\n"
    
    return analysis

# List of tools to export
tools_list = [rag_retriever, web_search, compare_roles]
