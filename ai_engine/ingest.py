import os
import hashlib
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
    
    
    file_ext = pdf_path.lower().split('.')[-1]
    
    if file_ext in ['jpg', 'jpeg', 'png']:
        documents = smart_extract_text(pdf_path)
    elif file_ext == 'pdf':
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
       
        if not documents or not documents[0].page_content.strip():
            print("No text found in PDF. Assuming scanned, falling back to OCR...")
            documents = smart_extract_text(pdf_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
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
    
    # 1. Fetch existing chunk IDs for this document (if updating an existing doc)
    existing_ids = set()
    if doc_id:
        try:
            existing = collection.get(where={"document_id": str(doc_id)})
            if existing and existing.get("ids"):
                existing_ids = set(existing["ids"])
        except Exception as e:
            print(f"[Ingest] Notice checking existing chunks for doc_id {doc_id}: {e}")
        
    # 2. Build Content-Addressed Chunk IDs from individual chunk text hashes
    texts = []
    metadatas = []
    new_ids = []
    
    for chunk in chunks:
        clean_text = chunk.page_content.strip()
        if not clean_text:
            continue
            
        chunk_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:12]
        if doc_id:
            chunk_id = f"doc_{doc_id}_chunk_{chunk_hash}"
        else:
            chunk_id = f"doc_{os.path.basename(pdf_path)}_{chunk_hash}"
            
        texts.append(clean_text)
        new_ids.append(chunk_id)
        
        meta = {
            "source_type": "case_file",
            "source_file": os.path.basename(pdf_path),
            "chunk_hash": chunk_hash
        }
        if case_id:
            meta["case_id"] = str(case_id)
        if doc_id:
            meta["document_id"] = str(doc_id)
        metadatas.append(meta)

    # 3. Incremental Upsert: ChromaDB preserves existing chunk vectors, embedding only new/modified chunks
    if new_ids:
        collection.upsert(
            documents=texts,
            metadatas=metadatas,
            ids=new_ids
        )
        print(f"Upserted {len(new_ids)} content-addressed chunks into ChromaDB.")
    
    # 4. Prune stale chunks that no longer exist in the updated revision
    stale_ids = existing_ids - set(new_ids)
    if stale_ids:
        collection.delete(ids=list(stale_ids))
        print(f"[Ingest] Pruned {len(stale_ids)} stale chunk(s) for Document ID {doc_id}.")
    
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