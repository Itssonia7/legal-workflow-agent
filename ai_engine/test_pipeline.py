from state import AgentState
from nodes import research_agent, drafter_agent, critic_agent
from utils import check_ollama_health

def run_local_test():
    print("===========================================")
    print("   ⚖️  LEGAL AI PIPELINE TEST SUITE  ⚖️   ")
    print("===========================================\n")

    # 1. Run the Safety Shield first
    if not check_ollama_health():
        print("\n[🚨 Alert] Pipeline aborted. Please start Ollama and try again.")
        return

    # 2. Set up a fresh clipboard (AgentState)
    state = AgentState(
        user_prompt="Draft a legal notice for a tenant who has not paid rent for 3 months.",
        context_documents="",
        current_draft="",
        critic_feedback="",
        revision_count=0,
        is_approved=False,
        step_logs=[]
    )

    print("\n🚀 Starting AI Execution...")

    # 3. Run the Researcher
    state.update(research_agent(state))

    # 4. Run the Drafter and Critic in a safe loop
    max_revisions = 3
    
    while state["revision_count"] < max_revisions and not state["is_approved"]:
        print(f"\n--- Drafting Cycle {state['revision_count'] + 1} ---")
        
        # Drafter updates the state
        draft_update = drafter_agent(state)
        state.update(draft_update)
        
        # Critic checks the work
        critic_update = critic_agent(state)
        state.update(critic_update)

    # 5. Print the final results
    print("\n===========================================")
    print("🏆 PIPELINE EXECUTION FINISHED 🏆")
    print("===========================================")
    print(f"Final Approval Status : {state['is_approved']}")
    print(f"Total Revisions Taken : {state['revision_count']}")
    
    print("\n--- Step-by-Step UI Logs ---")
    for log in state['step_logs']:
        print(f" ✅ {log}")

if __name__ == "__main__":
    run_local_test()