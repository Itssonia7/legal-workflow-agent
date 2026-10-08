import os
import tiktoken
import chromadb
from chromadb.utils import embedding_functions
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

def smart_extract_text(file_path: str) -> list[Document]:
    extracted_text = ""
    file_ext = file_path.lower().split('.')[-1]
    
    if file_ext in ['jpg', 'jpeg', 'png']:
        print(f"Running OCR on image: {file_path}")
        extracted_text = pytesseract.image_to_string(Image.open(file_path))
        
    elif file_ext == 'pdf':
        print(f"Converting Scanned PDF to images for OCR: {file_path}")
        pages = convert_from_path(file_path)
        for page_num, page_image in enumerate(pages):
            print(f"Running OCR on page {page_num + 1}...")
            extracted_text += pytesseract.image_to_string(page_image) + "\n\n"
            
    return [Document(page_content=extracted_text, metadata={"source": file_path, "type": "ocr_processed"})]

def process_legal_document(pdf_path, case_id=None, doc_id=None):
    print(f"Loading document: {pdf_path}...")
    
    # Task 1: Load Document (Smart OCR Routing)
    file_ext = pdf_path.lower().split('.')[-1]
    
    if file_ext in ['jpg', 'jpeg', 'png']:
        documents = smart_extract_text(pdf_path)
    elif file_ext == 'pdf':
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
        # Scanned PDF Fallback
        if not documents or not documents[0].page_content.strip():
            print("No text found in PDF. Assuming scanned, falling back to OCR...")
            documents = smart_extract_text(pdf_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    # Task 2: Split using token-based counting & legal-aware separators
    encoder = tiktoken.get_encoding("cl100k_base")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=40,
        length_function=lambda text: len(encoder.encode(text)),
        separators=[
            "\nChapter ",        # Biggest legal boundary (group of sections)
            "\nSection ",        # Main legal unit
            "\nArticle ",        # Used in Constitution/international law
            "\nSchedule ",       # Tables/appendices at the end
            "\nOrder ", "\nRule ",  # Used in CrPC, CPC procedural law
            "\nClause ",         # Sub-divisions within a section
            "\nExplanation",     # IPC-style explanations after sections
            "\nProviso",         # "Provided that..." exceptions
            "\nIllustration",    # IPC-style examples
            "\n\n",              # Paragraph break
            "\n",                # Line break
            ". ",                # Sentence boundary
            " ",                 # Word boundary
            ""                   # Character (last resort)
        ]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Successfully split into {len(chunks)} chunks.")

    # Task 3: Save to ChromaDB using native client
    print("Saving to ChromaDB using native client...")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "chroma_db")

    client = chromadb.PersistentClient(path=DB_PATH)
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    
    # Initialize collection with cosine space setting
    collection = client.get_or_create_collection(
        name="legal_knowledge_vault",
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 1. Clean up existing chunks for this specific document ID (Idempotency check)
    if doc_id:
        collection.delete(where={"document_id": str(doc_id)})
        
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
        if doc_id:
            meta["document_id"] = str(doc_id)
        metadatas.append(meta)
        
    # Generate unique chunk IDs based on Document ID
    if doc_id:
        ids = [f"doc_chunk_{doc_id}_{i}" for i in range(len(chunks))]
    else:
        ids = [f"doc_{os.path.basename(pdf_path)}_{i}" for i in range(len(chunks))]
    
    # Add directly to native ChromaDB collection
    collection.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    
    print("Ingestion complete! Vectors stored in ./chroma_db")

def delete_document_vectors(doc_id):
    """Deletes all chunks associated with a document_id from ChromaDB."""
    if not doc_id:
        return
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="legal_knowledge_vault",
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"}
    )
    collection.delete(where={"document_id": str(doc_id)})
    print(f"[ChromaDB] Deleted chunks for document_id={doc_id}")

if __name__ == "__main__":
    sample_pdf = "sample.pdf" 
    
    if os.path.exists(sample_pdf):
        process_legal_document(sample_pdf)
    else:
        print(f"Please add a '{sample_pdf}' file to this folder to test the ingestion.")