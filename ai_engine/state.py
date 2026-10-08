from typing import TypedDict, List

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
    step_logs: List[str]     # Progress updates for the frontend UI
    case_id: str             # The active case file ID to isolate document context
    doc_type: str            # Document archetype: 'bail', 'notice', 'affidavit', 'contract', 'auto'
    user_feedback: str       # Lawyer's direct revision instructions (Human-in-the-Loop)
    previous_draft: str      # Previous draft text before lawyer requested changes