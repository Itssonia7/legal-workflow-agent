import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import research_agent, drafter_agent, critic_agent

# 1. Define the conditional routing logic
def route_draft(state: AgentState):
    """
    This function acts as the traffic director after the Critic finishes.
    If approved, we end the pipeline. If rejected, we send it back to the Drafter.
    """
    if state.get("is_approved", False):
        return "approve"
    else:
        return "revise"

# 2. Initialize the LangGraph
workflow = StateGraph(AgentState)

# 3. Add all our agents as nodes in the graph
workflow.add_node("researcher", research_agent)
workflow.add_node("drafter", drafter_agent)
workflow.add_node("critic", critic_agent)

# 4. Connect the nodes together (The Assembly Line)
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "drafter")
workflow.add_edge("drafter", "critic")

# 5. Add the cyclic verification loop
workflow.add_conditional_edges(
    "critic", 
    route_draft, 
    {
        "approve": END,          # If the router returns "approve", stop execution
        "revise": "drafter"      # If the router returns "revise", loop back to drafter
    }
)

# 6. Compile the graph into a runnable application
app = workflow.compile()

# --- Quick Local Test ---
if __name__ == "__main__":
    print("🚀 Booting Autonomous Legal Pipeline...\n")
    
    # We only need to provide the initial user prompt. 
    # The agents will fill in the rest of the state automatically.
    initial_state = {
        "user_prompt": "Draft a brief 2-sentence bail application for a non-bailable offense.",
        "context_documents": "",
        "current_draft": "",
        "critic_feedback": "",
        "revision_count": 0,
        "is_approved": False
    }
    
    # Run the compiled graph!
    for output in app.stream(initial_state, {"recursion_limit": 5}):
        for key, value in output.items():
            print(f"\n--- Finished Node: {key} ---")