from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from state import AgentState

# Initialize the local AI 
llm = ChatOllama(model="llama3", temperature=0.0)

def research_agent(state: AgentState):
    print("\n[🤖 Researcher Agent] Analyzing case prompt...")
    user_prompt = state["user_prompt"]
    
    # 1. Ask Llama 3 to generate smart search keywords based on the lawyer's prompt
    instruction = f"You are a legal assistant. Extract 3 core legal search terms from this prompt. Return ONLY the terms separated by commas: '{user_prompt}'"
    response = llm.invoke([HumanMessage(content=instruction)])
    
    search_terms = response.content
    print(f"[🔍 Researcher Agent] Keywords extracted for database search: {search_terms}")
    
    # 2. Simulate ChromaDB retrieval (Member 2 will replace this with real vector queries later)
    print("[📚 Researcher Agent] Querying ChromaDB (Simulated)...")
    mock_context = f"Relevant precedents and statutes found regarding: {search_terms}."
    
    # 3. Return the new data to update the LangGraph State
    return {"context_documents": mock_context}

# --- Quick Local Test ---
# This block only runs if you execute this specific file directly
if __name__ == "__main__":
    # We create a dummy state to test just this agent
    test_state = AgentState(
        user_prompt="Draft a bail application for a client accused of a non-bailable offense under Section 302.",
        context_documents="",
        current_draft="",
        critic_feedback="",
        revision_count=0,
        is_approved=False
    )
    
    # Run the agent and see what it returns
    updated_state_data = research_agent(test_state)
    print("\n--- Data Passed to Next Agent ---")
    print(f"Context Documents: {updated_state_data['context_documents']}\n")