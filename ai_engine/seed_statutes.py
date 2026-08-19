import os
from datasets import load_dataset
import chromadb
from chromadb.utils import embedding_functions

def seed_huggingface_statutes():
    print("\n[📥 Dataset Loader] Fetching 'mratanusarkar/Indian-Laws' from Hugging Face...")
    
    # 1. Load the dataset
    dataset = load_dataset("mratanusarkar/Indian-Laws", split="train")
    print(f"[✅ Dataset Loader] Successfully downloaded {len(dataset)} legal records.")

    # 2. Configure ChromaDB Persistent Client
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    
    # Use default all-MiniLM-L6-v2 embeddings or compatible local function
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name="legal_knowledge_vault",
        embedding_function=embedding_func
    )

    documents = []
    metadatas = []
    ids = []

    print("[⚙️ Processing] Parsing statutory records and building context headers...")
    
    # Ingest a sample or full set (e.g., first 500 for rapid local validation)
    sample_size = min(len(dataset), 500)
    
    for i in range(sample_size):
        row = dataset[i]
        
        # Handle field names from the dataset (fallback gracefully)
        act_name = row.get("Act", row.get("act_name", row.get("act_title", "Indian Statute")))
        section_no = row.get("Section", row.get("section", f"Section {i+1}"))
        title = row.get("Title", row.get("title", ""))
        content = row.get("Description", row.get("content", row.get("text", row.get("law", ""))))
        
        if not content or len(content.strip()) < 10:
            continue

        # Format context header according to the Section 4.A blueprint
        formatted_chunk = (
            f"Act: {act_name}\n"
            f"Section: {section_no} - {title}\n"
            f"Content: {content.strip()}"
        )

        metadata = {
            "source_type": "statute",
            "act_name": str(act_name),
            "section_no": str(section_no),
            "legal_era": "pre-2024",
            "is_active": True
        }

        documents.append(formatted_chunk)
        metadatas.append(metadata)
        ids.append(f"statute_hf_{i}")

    # 3. Batch insert into ChromaDB
    print(f"[💾 ChromaDB] Ingesting {len(documents)} structured statute vectors...")
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
            ids=ids[i:i + batch_size]
        )
        print(f" -> Stored batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}")

    print("\n[🎉 Success] Statutory database seeding complete!")

if __name__ == "__main__":
    seed_huggingface_statutes()