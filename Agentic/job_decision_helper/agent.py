import os
import sys
from pathlib import Path

# Load env variables from root workspace .env
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent.parent / ".env")

# Ensure required API keys are available
if not os.getenv("GOOGLE_API_KEY"):
    print("Error: GOOGLE_API_KEY not found in .env")
    sys.exit(1)
if not os.getenv("TAVILY_API_KEY"):
    print("Error: TAVILY_API_KEY not found in .env")
    sys.exit(1)

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage

# Import our custom tool list
from tools import tools_list

# Initialize the LLM brain
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # Excellent at tooling and fast
    temperature=0.2
)

# Initialize LangGraph minimal ReAct Agent
agent_executor = create_react_agent(llm, tools_list)

def main():
    print("="*60)
    print("🤖 Agentic Job Decision Helper Started!")
    print("Core Tools Available:")
    print(" -  RAG Retriever (Internal Knowledge)")
    print(" -  Web Search (Tavily Trends)")
    print(" -  Role Analyzer (Skill/Salary Extract)")
    print("\nType 'quit' or 'exit' to end the session.")
    print("="*60)
    
    # Store conversation history state manually for simple CLI usage
    thread_messages = []
    
    while True:
        try:
            user_input = input("\n👤 You: ")
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            if not user_input.strip():
                continue
                
            # Append human message to thread
            thread_messages.append(HumanMessage(content=user_input))
            
            print("\n🤖 Agent is thinking... (Watch out for tool calls)")
            
            # Run the agent node
            response = agent_executor.invoke({"messages": thread_messages})
            
            # Identify any tools invoked during thinking (everything but the final and our original prompt)
            new_messages = response["messages"][len(thread_messages):]
            
            for msg in new_messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        print(f"  🔧 Expected Tool Call: {tool_call['name']}")
            
            final_message = response["messages"][-1]
            if isinstance(final_message, AIMessage):
                print(f"\n{final_message.content}")
                
            # Update our thread memory with the new accumulated messages
            thread_messages = response["messages"]
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
