import chromadb
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Load model and connect to database
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
vector_store = Chroma(
    client=client,
    collection_name="legal_collection",
    embedding_function=embeddings
)


def search_legal_documents(query: str, k: int = 5) -> list:
    """
    Search ChromaDB for legal text chunks relevant to the query.

    Args:
        query: Plain-English legal question
        k: Number of matching chunks to return (default 5)

    Returns:
        List of document objects from ChromaDB
    """
    results = vector_store.similarity_search(query, k=k)
    return results


# --- Interactive mode (only runs when you execute this file directly) ---
if __name__ == "__main__":
    while True:
        query = input("\nAsk a question about the RTI Act (or type 'exit' to quit): ")
        if query.lower() == 'exit':
            break

        results = search_legal_documents(query)

        print(f"\n--- Results for: '{query}' ---")
        for i, doc in enumerate(results):
            print(f"\n[Result {i+1}]")
            print(doc.page_content[:500] + "...")