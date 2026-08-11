# ai_engine/generate.py
"""
The LLM Generation Step.
Takes retrieved ChromaDB chunks + user query -> synthesized legal answer.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# Initialize the local LLM (uses Llama 3)
llm = ChatOllama(model="llama3", temperature=0.0)


def generate_legal_answer(query: str, context_chunks: list) -> str:
    """
    Takes a user's legal question and retrieved document chunks,
    then asks the LLM to synthesize a proper legal answer.

    Args:
        query: The user's plain-English legal question
        context_chunks: A list of document objects returned by ChromaDB

    Returns:
        A string containing the LLM's synthesized legal answer.
    """
    # 1. Combine all retrieved chunks into one big context block
    combined_context = "\n\n---\n\n".join(
        [doc.page_content for doc in context_chunks]
    )

    # 2. Build the strict grounding prompt
    prompt = f"""You are a legal research assistant. Answer the user's question 
using ONLY the legal text provided below. 

If the answer is not found in the provided text, say: 
"I could not find relevant information in the available legal documents."

Do NOT make up laws, sections, or penalties that are not in the text.

--- PROVIDED LEGAL TEXT ---
{combined_context}
--- END OF LEGAL TEXT ---

User's Question: {query}

Provide a clear, well-structured legal answer:"""

    # 3. Send to Ollama and return the text content
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content