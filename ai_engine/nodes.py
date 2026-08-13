from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from state import AgentState
from retrieve import search_legal_documents

# Initialize the local AI 
llm = ChatOllama(model="llama3", temperature=0.0)

def research_agent(state: AgentState):
    print("\n[🤖 Researcher Agent] Analyzing case prompt...")
    user_prompt = state["user_prompt"]
    logs = state.get("step_logs", [])
    
    instruction = f"You are a legal assistant. Extract 3 core legal search terms from this prompt. Return ONLY the terms separated by commas: '{user_prompt}'"
    response = llm.invoke([HumanMessage(content=instruction)])
    
    search_terms = response.content
    print(f"[🔍 Researcher Agent] Keywords extracted: {search_terms}")
    logs.append(f"Researcher extracted keywords: {search_terms}")
    
    print("[📚 Researcher Agent] Querying ChromaDB (Real)...")
    real_results = search_legal_documents(search_terms)
    context = "\n\n".join([doc.page_content for doc in real_results])
    logs.append("Researcher successfully retrieved relevant legal precedents from the vault.")
    
    return {"context_documents": context, "step_logs": logs}


def drafter_agent(state: AgentState):
    print("\n[✍️ Drafter Agent] Generating legal document...")
    user_prompt = state["user_prompt"]
    context_documents = state["context_documents"]
    critic_feedback = state.get("critic_feedback", "")
    logs = state.get("step_logs", [])

    prompt_text = f"""
    You are an expert Indian Legal Drafter. Your job is to draft a formal legal document based on the user's request and the provided legal facts.

    User Request: {user_prompt}
    Legal Facts & Precedents: {context_documents}
    Critic Feedback (if any): {critic_feedback}

    You MUST structure your response using Markdown with the following exact sections:
    1. **COURT JURISDICTION**: (e.g., "IN THE HIGH COURT OF JUDICATURE...")
    2. **DOCUMENT TITLE**: (e.g., "BAIL APPLICATION UNDER SECTION 439 BNSS")
    3. **FACTS OF THE CASE**: (Summarize the specific situation)
    4. **GROUNDS & STATUTORY CITATIONS**: (You MUST use the exact laws mentioned in the Legal Facts provided)
    5. **PRAYER**: (The final relief sought by the client)

    Do not include any pleasantries, conversational text, or introductions. Output ONLY the legal document.
    """
    
    if critic_feedback:
        prompt_text += f"\nRevisions strictly required by Critic: {critic_feedback}"

    response = llm.invoke([HumanMessage(content=prompt_text)])
    print("[✍️ Drafter Agent] Draft generated successfully.")
    
    new_count = state.get("revision_count", 0) + 1
    logs.append(f"Drafter created document version {new_count}.")
    
    return {
        "current_draft": response.content, 
        "revision_count": new_count,
        "step_logs": logs
    }


def critic_agent(state: AgentState):
    print("\n[🧐 Critic Agent] Evaluating the draft...")
    user_prompt = state["user_prompt"]
    current_draft = state["current_draft"]
    context_documents = state["context_documents"]
    logs = state.get("step_logs", [])

    prompt_text = f"""
    You are a Senior Legal Editor and Fact-Verifier. Your job is to rigorously review the drafted legal document against the original request and provided legal facts.

    Legal Facts Provided: {context_documents}
    Drafted Document to Review: {current_draft}

    Evaluation Rules:
    1. Check if the draft contains all 5 required sections: COURT JURISDICTION, DOCUMENT TITLE, FACTS OF THE CASE, GROUNDS & STATUTORY CITATIONS, and PRAYER.
    2. Check if all statutory citations mentioned in the draft actually exist in the Legal Facts Provided.
    3. Check if any facts or claims were completely invented/hallucinated.

    Instructions:
    - If the document meets all 3 rules perfectly, respond with ONLY the word: APPROVED
    - If the document fails any rule, respond with: REJECTED: <list concise, specific instructions telling the Drafter what to fix>
    """
    
    response = llm.invoke([HumanMessage(content=prompt_text)])
    evaluation = response.content.strip()

    if evaluation.startswith("APPROVED"):
        print("[✅ Critic Agent] Draft approved!")
        logs.append("Critic verified all facts and approved the final document.")
        return {"is_approved": True, "critic_feedback": "", "step_logs": logs}
    else:
        print(f"[❌ Critic Agent] Draft rejected. Feedback: {evaluation}")
        logs.append("Critic found errors. Sending back to Drafter for revision.")
        return {"is_approved": False, "critic_feedback": evaluation, "step_logs": logs}


# --- Quick Local Test ---
if __name__ == "__main__":
    test_state = AgentState(
        user_prompt="Draft a bail application for a client accused of theft.",
        context_documents="Section 379 IPC relates to punishment for theft. The punishment is imprisonment for a term which may extend to three years, or with fine, or with both. It is a cognizable and non-bailable offense.",
        current_draft="",
        critic_feedback="",
        revision_count=0,
        is_approved=False,
        step_logs=[]  # Initializing the empty list here for the test
    )
    
    print("\n--- Testing Drafter ---")
    draft_update = drafter_agent(test_state)
    test_state.update(draft_update)
    
    print("\n--- Testing Critic ---")
    critic_update = critic_agent(test_state)
    test_state.update(critic_update)
    
    print(f"\n--- Final Status ---")
    print(f"Approved: {test_state['is_approved']}")
    print("\n--- Frontend UI Logs ---")
    for log in test_state['step_logs']:
        print(f" -> {log}")