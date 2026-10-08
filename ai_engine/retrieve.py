import os
import chromadb
from chromadb.utils import embedding_functions

def search_legal_documents(query: str, source_type: str = None, case_id: str = None, k: int = 6):
    """
    Searches the ChromaDB vector store.
    If source_type is provided (e.g., 'statute' or 'case_file'), it filters the results.
    For case_files with a case_id, it retrieves all uploaded evidence chunks across multiple documents.
    """
    print(f"[🔍 Retrieval] Searching ChromaDB (Filter: {source_type}, Case: {case_id})...")
    
    # 1. Connect to the exact database
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name="legal_knowledge_vault",
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 2. Special handling for Case Files: Retrieve ALL evidence uploaded for this specific case
    if source_type == "case_file" and case_id:
        try:
            case_records = collection.get(
                where={
                    "$and": [
                        {"source_type": "case_file"},
                        {"case_id": str(case_id)}
                    ]
                }
            )
            if case_records and case_records.get('documents') and len(case_records['documents']) > 0:
                docs = case_records['documents']
                metas = case_records.get('metadatas') or [{}] * len(docs)
                
                # If total chunks is manageable (<= 15 chunks), include all of them
                if len(docs) <= 15:
                    documents = []
                    for doc_text, meta in zip(docs, metas):
                        src = meta.get('source_file', 'Case Document')
                        documents.append(f"[Document: {src}]\n{doc_text}")
                    print(f"[🔍 Retrieval] Retrieved all {len(documents)} evidence chunks across all uploaded case files for Case ID: {case_id}")
                    return documents
        except Exception as e:
            print(f"[🔍 Retrieval] Notice: collection.get fallback to query: {e}")

    # 3. Standard / Large-scale Vector Search
    search_kwargs = {
        "query_texts": [query],
        "n_results": k
    }
    
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
    
    # 4. Extract and return formatted text chunks with document source
    documents = []
    if results['documents'] and len(results['documents']) > 0:
        docs = results['documents'][0]
        metas = results.get('metadatas', [[]])[0] if results.get('metadatas') else [{}] * len(docs)
        for doc_text, meta in zip(docs, metas):
            src = meta.get('source_file') if isinstance(meta, dict) else None
            if src:
                documents.append(f"[Document: {src}]\n{doc_text}")
            else:
                documents.append(doc_text)
            
    return documents