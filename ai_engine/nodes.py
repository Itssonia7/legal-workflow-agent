from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from state import AgentState
from retrieve import search_legal_documents

# Initialize the local AI 
llm = ChatOllama(model="llama3", temperature=0.0)

def research_agent(state: AgentState):
    print("\n[🤖 Researcher Agent] Analyzing case prompt...")
    user_prompt = state["user_prompt"]
    
    instruction = f"You are a legal assistant. Extract 3 core legal search terms from this prompt. Return ONLY the terms separated by commas: '{user_prompt}'"
    response = llm.invoke([HumanMessage(content=instruction)])
    
    search_terms = response.content
    print(f"[🔍 Researcher Agent] Keywords extracted: {search_terms}")
    
        # Query real ChromaDB using your function
    print("[📚 Researcher Agent] Querying ChromaDB (Real)...")
    real_results = search_legal_documents(search_terms)
    context = "\n\n".join([doc.page_content for doc in real_results])
    
    return {"context_documents": context}


def drafter_agent(state: AgentState):
    print("\n[✍️ Drafter Agent] Generating legal document...")
    user_prompt = state["user_prompt"]
    context_documents = state["context_documents"]
    critic_feedback = state.get("critic_feedback", "")

    prompt_text = f"""You are an expert legal drafter. 
Task: {user_prompt}
Precedents/Facts to include: {context_documents}
"""
    
    if critic_feedback:
        prompt_text += f"\nRevisions required by Critic: {critic_feedback}"

    prompt_text += "\nWrite the legal document draft now. Keep it brief for this test."

    response = llm.invoke([HumanMessage(content=prompt_text)])
    print("[✍️ Drafter Agent] Draft generated successfully.")
    
    new_count = state.get("revision_count", 0) + 1
    return {
        "current_draft": response.content, 
        "revision_count": new_count
    }


def critic_agent(state: AgentState):
    print("\n[🧐 Critic Agent] Evaluating the draft...")
    user_prompt = state["user_prompt"]
    current_draft = state["current_draft"]

    # 1. Prompt the Critic to act as a strict reviewer
    prompt_text = f"""You are a strict senior legal partner reviewing a junior's draft.
Original Request: {user_prompt}
Current Draft: {current_draft}

If the draft is perfect and meets all requirements, respond exactly with the word "APPROVED".
If it needs work, respond with "REJECTED:" followed by a short instruction on what to fix.
"""
    
    # 2. Get the evaluation
    response = llm.invoke([HumanMessage(content=prompt_text)])
    evaluation = response.content.strip()

    # 3. Parse the evaluation to update the LangGraph state
    if evaluation.startswith("APPROVED"):
        print("[✅ Critic Agent] Draft approved!")
        return {"is_approved": True, "critic_feedback": ""}
    else:
        print(f"[❌ Critic Agent] Draft rejected. Feedback: {evaluation}")
        return {"is_approved": False, "critic_feedback": evaluation}


# --- Quick Local Test ---
if __name__ == "__main__":
    test_state = AgentState(
        user_prompt="Draft a brief 2-sentence bail application for a non-bailable offense.",
        context_documents="",
        current_draft="",
        critic_feedback="",
        revision_count=0,
        is_approved=False
    )
    
    # Run Researcher
    research_update = research_agent(test_state)
    test_state.update(research_update)
    
    # Run Drafter
    draft_update = drafter_agent(test_state)
    test_state.update(draft_update)
    
    # Run Critic
    critic_update = critic_agent(test_state)
    test_state.update(critic_update)
    
    print(f"\n--- Final Status ---")
    print(f"Approved: {test_state['is_approved']}")
    if not test_state['is_approved']:
        print(f"Feedback to fix next round: {test_state['critic_feedback']}")