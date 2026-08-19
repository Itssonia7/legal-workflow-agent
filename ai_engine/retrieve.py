import os
import chromadb
from chromadb.utils import embedding_functions

def search_legal_documents(query: str, source_type: str = None, case_id: str = None, k: int = 3):
    """
    Searches the ChromaDB vector store.
    If source_type is provided (e.g., 'statute' or 'case_file'), it filters the results.
    """
    print(f"[🔍 Retrieval] Searching ChromaDB (Filter: {source_type}, Case: {case_id})...")
    
    # 1. Connect to the exact database we just seeded
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name="legal_knowledge_vault",
        embedding_function=embedding_func
    )
    
    # 2. Build the search parameters
    search_kwargs = {
        "query_texts": [query],
        "n_results": k
    }
    
    # 3. Apply the Metadata Filter if requested
    if source_type:
        if source_type == "case_file" and case_id:
            search_kwargs["where"] = {
                "$and": [
                    {"source_type": "case_file"},
                    {"case_id": str(case_id)}
                ]
            }
        else:
            search_kwargs["where"] = {"source_type": source_type}
        
    results = collection.query(**search_kwargs)
    
    # 4. Extract and return the raw text chunks
    documents = []
    if results['documents'] and len(results['documents']) > 0:
        for doc_text in results['documents'][0]:
            documents.append(doc_text)
            
    return documents