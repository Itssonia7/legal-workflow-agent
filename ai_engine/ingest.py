import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def process_legal_document(pdf_path, case_id=None):
    print(f"Loading document: {pdf_path}...")
    
    # Task 1: Load the PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # Task 2: Split the text (1000 size, 200 overlap)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Successfully split into {len(chunks)} chunks.")
    
    import chromadb
    from chromadb.utils import embedding_functions

    # Task 3: Save to ChromaDB using native client
    print("Saving to ChromaDB using native client...")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "chroma_db")

    client = chromadb.PersistentClient(path=DB_PATH)
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name="legal_knowledge_vault",
        embedding_function=embedding_func
    )
    
    # Prepare documents, metadatas, and ids
    texts = [chunk.page_content for chunk in chunks]
    
    metadatas = []
    for chunk in chunks:
        meta = {
            "source_type": "case_file",
            "source_file": os.path.basename(pdf_path)
        }
        if case_id:
            meta["case_id"] = str(case_id)
        metadatas.append(meta)
        
    ids = [f"doc_{os.path.basename(pdf_path)}_{i}" for i in range(len(chunks))]
    
    # Add directly to native ChromaDB collection
    collection.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    
    print("Ingestion complete! Vectors stored in ./chroma_db")

if __name__ == "__main__":
    sample_pdf = "sample.pdf" 
    
    if os.path.exists(sample_pdf):
        process_legal_document(sample_pdf)
    else:
        print(f"Please add a '{sample_pdf}' file to this folder to test the ingestion.")