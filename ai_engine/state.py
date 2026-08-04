from typing import TypedDict

class AgentState(TypedDict):
    """
    This dictionary represents the state of our legal multi-agent system.
    It holds all the information passed between the Researcher, Drafter, and Critic.
    """
    user_prompt: str         # The initial request from the lawyer (e.g., "Draft a bail application")
    context_documents: str   # The legal facts/precedents retrieved from ChromaDB
    current_draft: str       # The document currently being written/edited
    critic_feedback: str     # Notes from the Critic agent if the draft has errors
    revision_count: int      # To ensure the agents don't get stuck in an infinite loop
    is_approved: bool        # Becomes True when the Critic is finally satisfied