import os
import chromadb

# Get the directory where this script is located
base_dir = os.path.dirname(os.path.abspath(__file__))

# Point directly to the chroma_db folder in the same directory
db_path = os.path.join(base_dir, "chroma_db")

print(f"Connecting to database at: {db_path}...")
client = chromadb.PersistentClient(path=db_path)

try:
    collection = client.get_collection("legal_knowledge_vault")
    
    # 1. Fetch case file chunks (specifically sample.pdf)
    pdf_results = collection.get(where={"source_file": "sample.pdf"}, limit=3)
    
    # 2. Fetch statute chunks
    statute_results = collection.get(where={"source_type": "statute"}, limit=2)
    
    print("\n" + "=" * 60)
    print("📄 CASE FILE CHUNKS (sample.pdf, etc.)")
    print("=" * 60)
    if not pdf_results['documents']:
        print("No PDF case file chunks found in the database.")
    else:
        for idx, doc in enumerate(pdf_results['documents']):
            meta = pdf_results['metadatas'][idx]
            print(f"\n[Chunk {idx+1}] File: {meta.get('source_file')} | ID: {pdf_results['ids'][idx]}")
            print("-" * 40)
            print(doc)
            print("-" * 50)
            
    print("\n" + "=" * 60)
    print("⚖️ STATUTE CHUNKS")
    print("=" * 60)
    if not statute_results['documents']:
        print("No statute chunks found in the database.")
    else:
        for idx, doc in enumerate(statute_results['documents']):
            meta = statute_results['metadatas'][idx]
            print(f"\n[Chunk {idx+1}] Act: {meta.get('act_name')} | Section: {meta.get('section_no')}")
            print("-" * 40)
            print(doc)
            print("-" * 50)
            
except Exception as e:
    print(f"Error accessing collection: {e}")
