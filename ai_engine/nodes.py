from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from state import AgentState

# Initialize the local AI 
llm = ChatOllama(model="llama3", temperature=0.0)

def research_agent(state: AgentState):
    print("\n[🤖 Researcher Agent] Analyzing case prompt...")
    user_prompt = state["user_prompt"]
    
    instruction = f"You are a legal assistant. Extract 3 core legal search terms from this prompt. Return ONLY the terms separated by commas: '{user_prompt}'"
    response = llm.invoke([HumanMessage(content=instruction)])
    
    search_terms = response.content
    print(f"[🔍 Researcher Agent] Keywords extracted: {search_terms}")
    
    print("[📚 Researcher Agent] Querying ChromaDB (Simulated)...")
    mock_context = f"Relevant precedents and statutes found regarding: {search_terms}."
    
    return {"context_documents": mock_context}


def drafter_agent(state: AgentState):
    print("\n[✍️ Drafter Agent] Generating legal document...")
    user_prompt = state["user_prompt"]
    context_documents = state["context_documents"]
    critic_feedback = state.get("critic_feedback", "")

    # 1. Build the prompt using the context from the Researcher
    prompt_text = f"""You are an expert legal drafter. 
Task: {user_prompt}
Precedents/Facts to include: {context_documents}
"""
    
    # 2. If the Critic rejected a previous draft, force the Drafter to fix it
    if critic_feedback:
        prompt_text += f"\nRevisions required by Critic: {critic_feedback}"

    prompt_text += "\nWrite the legal document draft now. Keep it brief for this test."

    # 3. Generate the document
    response = llm.invoke([HumanMessage(content=prompt_text)])
    print("[✍️ Drafter Agent] Draft generated successfully.")
    
    # 4. Return the new draft and increment the revision counter
    new_count = state.get("revision_count", 0) + 1
    return {
        "current_draft": response.content, 
        "revision_count": new_count
    }


# --- Quick Local Test ---
if __name__ == "__main__":
    # 1. Initial State
    test_state = AgentState(
        user_prompt="Draft a brief 2-sentence bail application for a non-bailable offense.",
        context_documents="",
        current_draft="",
        critic_feedback="",
        revision_count=0,
        is_approved=False
    )
    
    # 2. Run Researcher and update state
    research_update = research_agent(test_state)
    test_state.update(research_update)
    
    # 3. Run Drafter and update state
    draft_update = drafter_agent(test_state)
    test_state.update(draft_update)
    
    print("\n--- Final Draft Output ---")
    print(test_state["current_draft"])