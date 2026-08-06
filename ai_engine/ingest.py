import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def process_legal_document(pdf_path):
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
    
    # Task 3: Generate embeddings and save to ChromaDB
    print("Generating embeddings and saving to ChromaDB...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    
    print("Ingestion complete! Vectors stored in ./chroma_db")

if __name__ == "__main__":
    sample_pdf = "sample.pdf" 
    
    if os.path.exists(sample_pdf):
        process_legal_document(sample_pdf)
    else:
        print(f"Please add a '{sample_pdf}' file to this folder to test the ingestion.")