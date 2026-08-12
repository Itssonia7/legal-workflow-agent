# ai_engine/rag_pipeline.py
"""
End-to-end RAG pipeline testing script.
"""
from retrieve import search_legal_documents
from generate import generate_legal_answer


def ask_legal_question(query: str) -> str:
    """
    Connects Search and Generation together.
    """
    # Step A: Search ChromaDB using retrieve.py
    print(f"\n[1/2] Searching ChromaDB for: '{query}'...")
    chunks = search_legal_documents(query, k=5)

    # Step B: Generate Answer using generate.py
    print("[2/2] Generating answer with Llama 3...")
    answer = generate_legal_answer(query, chunks)

    return answer


if __name__ == "__main__":
    # Test one question at a time to prevent Mac GPU Out-of-Memory errors.
    # Simply uncomment the question you want to test!

    # Test 1: Timelines
    question = "What is the time limit for providing information concerning life or liberty?"

    # Test 2: Exemptions
    # question = "Are there any exemptions under the RTI Act?"

    # Test 3: Anti-Hallucination
    # question = "What is the recipe for a chocolate cake?"

    # Test 4: Penalties / Fines
    # question = "What is the penalty for not providing information under the Act?"
    # question = "penalty for not providing information"

    # Test 5: Who designates Public Information Officers?
    # question = "Who has the power to designate Public Information Officers?"

    answer = ask_legal_question(question)
    
    print("\n" + "="*50)
    print(f"QUESTION: {question}")
    print(f"ANSWER:\n{answer}")
    print("="*50 + "\n")

# if __name__ == "__main__":
#     # A list of test queries to run sequentially
#     test_queries = [
#         "What is the time limit for providing information concerning life or liberty?",
#         "Are there any exemptions under the RTI Act?",
#         "What is the recipe for a chocolate cake?"  # Anti-hallucination test!
#     ]
    
#     for question in test_queries:
#         answer = ask_legal_question(question)
        
#         print("\n" + "="*50)
#         print(f"QUESTION: {question}")
#         print(f"ANSWER:\n{answer}")
#         print("="*50 + "\n")