import argparse
import os
import re
import sys
import fitz
from transformers import AutoTokenizer

import chromadb.telemetry.product.posthog
chromadb.telemetry.product.posthog.Posthog.capture = lambda self, event, *a, **kw: None

try:
    TOKENIZER = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2', local_files_only=True)
except Exception:
    TOKENIZER = None

ACT_CONFIGS = {
    "BNS_2023.pdf": {
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "legal_era": "post-2024-criminal-codes",
        "official_sections_count": 358,
        "partial_coverage": False,
        "covered_range": "1-358",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+\(1\)\s+This\s+Act\s+may\s+be\s+called\s+the\s+Bharatiya\s+Nyaya\s+Sanhita',
        "known_repealed_ranges": [],
        "text_as_of": "as enacted 2023-12-25",
        "latest_amendment_cited": "2023-12-25",
        "source_dataset": "official_pdf"
    },
    "BNSS_2023.pdf": {
        "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "legal_era": "post-2024-criminal-codes",
        "official_sections_count": 531,
        "partial_coverage": False,
        "covered_range": "1-531",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+\(1\)\s+This\s+Act\s+may\s+be\s+called\s+the\s+Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita',
        "known_repealed_ranges": [],
        "text_as_of": "as enacted 2023-12-25",
        "latest_amendment_cited": "2023-12-25",
        "source_dataset": "official_pdf"
    }
}

RETAINED_HF_ACTS = {
    "Code of Criminal Procedure Act, 1973": {
        "act_name": "Code of Criminal Procedure, 1973",
        "legal_era": "pre-2024-criminal-codes",
        "partial_coverage": False,
        "unverified_currency": True,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Negotiable Instruments Act, 1881": {
        "act_name": "Negotiable Instruments Act, 1881",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": True,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "max_section": 142,
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Indian Contract Act, 1872": {
        "act_name": "Indian Contract Act, 1872",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Code of Civil Procedure, 1908": {
        "act_name": "Code of Civil Procedure, 1908",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Consumer Protection Act, 2019": {
        "act_name": "Consumer Protection Act, 2019",
        "legal_era": "retained-central-act",
        "partial_coverage": False,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Limitation Act, 1963": {
        "act_name": "Limitation Act, 1963",
        "legal_era": "retained-central-act",
        "partial_coverage": False,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Hindu Marriage Act, 1955": {
        "act_name": "Hindu Marriage Act, 1955",
        "legal_era": "retained-central-act",
        "partial_coverage": False,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Transfer of Property Act, 1882": {
        "act_name": "Transfer of Property Act, 1882",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Registration Act, 1908": {
        "act_name": "Registration Act, 1908",
        "legal_era": "retained-central-act",
        "partial_coverage": False,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Advocates Act, 1961": {
        "act_name": "Advocates Act, 1961",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Constitution of India, 1949": {
        "act_name": "Constitution of India, 1949",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
        "max_section": 30,
        "source_dataset": "hf_mratanusarkar_indian_laws"
    }
}

SKIPPED_ACTS = [
    ("Indian Penal Code, 1860", "Excluded: pre-2024 code replaced by BNS 2023; not in current priority scope"),
    ("Bharatiya Sakshya Adhiniyam, 2023", "Excluded: BSA_2023.pdf is a Bill ('THE BHARATIYA SAKSHYA (SECOND) BILL, 2023'), not enacted Act"),
    ("Indian Evidence Act, 1872", "Excluded: Evidence_Act_1872.pdf is MISSING from data/statute_pdfs/"),
    ("Information Technology Act, 2000", "Excluded: pre-2008 dataset text missing Sections 43A, 66C, 66D, 66E, 66F, 67A"),
    ("Specific Relief Act, 1963", "Excluded: pre-2018 dataset text; Section 10 states pre-2018 discretionary rule"),
    ("Right to Information Act, 2005", "Excluded: not in current priority statute list")
]

HEADER_FOOTER_PATTERNS = [
    r'THE GAZETTE OF INDIA EXTRAORDINARY',
    r'\[PART II—\s*SEC\. 1\]',
    r'SEC\. 1\]\s+THE GAZETTE OF INDIA'
]

def norm_space(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def extract_titles_from_pdf(pdf_path: str, filename: str) -> dict:
    if not os.path.exists(pdf_path):
        return {}
    
    doc = fitz.open(pdf_path)
    titles = {}
    sec_pattern = re.compile(r'^\s*(\d+[A-Z]*)\.\s+')
    
    for pno in range(len(doc)):
        page = doc[pno]
        blocks = page.get_text('blocks')
        margin_blocks = []
        main_sec_blocks = []
        
        for b in blocks:
            x0, y0, x1, y1, text, bno, btype = b
            clean_t = text.strip()
            if not clean_t: continue
            
            if x0 < 110 or x0 > 480:
                if not re.match(r'^\d+$', clean_t) and 'GAZETTE OF INDIA' not in clean_t:
                    margin_blocks.append((y0, clean_t))
            else:
                m = sec_pattern.match(clean_t)
                if m:
                    sec_label = m.group(1)
                    main_sec_blocks.append((y0, sec_label))
                    
        for sec_y0, sec_label in main_sec_blocks:
            if sec_label not in titles:
                best_title = None
                min_diff = 35.0
                for my0, mtext in margin_blocks:
                    diff = abs(my0 - sec_y0)
                    if diff < min_diff:
                        min_diff = diff
                        best_title = norm_space(mtext)
                if best_title:
                    if best_title.endswith('.'): best_title = best_title[:-1]
                    titles[sec_label] = best_title
                    
    return titles

def parse_pdf(pdf_path: str, config: dict):
    filename = os.path.basename(pdf_path)
    if not os.path.exists(pdf_path):
        return None, "File missing", [], [], [], {}
    
    doc = fitz.open(pdf_path)
    full_text = "\n".join([page.get_text("text") for page in doc])
    
    first_page_text = doc[0].get_text("text") if len(doc) > 0 else ""
    if re.search(r'\bBILL\b', first_page_text[:400], re.IGNORECASE) and not re.search(r'ACT NO\.\s+\d+', first_page_text[:400], re.IGNORECASE):
        return None, "Document is a Bill", [], [], [], {}

    sec_1_matches = list(re.finditer(config["sec_1_pattern"], full_text, re.IGNORECASE))
    if not sec_1_matches:
        return None, "Section 1 heading pattern not found", [], [], [], {}
    
    start_pos = sec_1_matches[-1].start()
    obj_match = re.search(r'\n\s*STATEMENT OF OBJECTS AND REASONS', full_text, re.IGNORECASE)
    end_pos = obj_match.start() if obj_match else len(full_text)
    
    body_text = "\n" + full_text[start_pos:end_pos]
    
    # Cut at SCHEDULE or THE FIRST SCHEDULE before section splitting
    sched_match = re.search(r'\n\s*(?:THE\s+)?FIRST\s+SCHEDULE\b|\n\s*SCHEDULE\s+I\b|\n\s*THE\s+SCHEDULE\b', body_text, re.IGNORECASE)
    schedule_text = ""
    if sched_match:
        schedule_start = sched_match.start()
        schedule_text = body_text[schedule_start:].strip()
        body_text = body_text[:schedule_start].strip()

    title_map = extract_titles_from_pdf(pdf_path, filename)
    pattern = r'\n\s*(\d+[A-Z]*)\.\s*'
    raw_chunks = re.split(pattern, body_text)
    
    sections = {}
    duplicates = []
    rejected = []
    
    last_num = 0
    i = 1
    while i < len(raw_chunks) - 1:
        label = raw_chunks[i].strip()
        raw_content = raw_chunks[i+1].strip()
        i += 2
        
        m = re.match(r'^(\d+)([A-Z]*)$', label)
        if not m:
            rejected.append((label, raw_content[:60]))
            continue
            
        num = int(m.group(1))
        suffix = m.group(2)
        
        cleaned_content = norm_space(raw_content)
        sec_title = title_map.get(label, f"Section {label}")
        
        if num == last_num:
            duplicates.append((label, cleaned_content[:60]))
            if label not in sections or len(cleaned_content) > len(sections[label]["content"]):
                sections[label] = {
                    "raw": raw_content,
                    "content": cleaned_content,
                    "title": sec_title
                }
        elif num == last_num + 1 or num > last_num:
            sections[label] = {
                "raw": raw_content,
                "content": cleaned_content,
                "title": sec_title
            }
            last_num = num
        else:
            rejected.append((label, raw_content[:60]))

    if schedule_text:
        sched_title = f"{config['act_name']} First Schedule"
        sections["Schedule_1"] = {
            "raw": schedule_text,
            "content": norm_space(schedule_text[:4000]),
            "title": sched_title
        }
            
    return sections, None, duplicates, rejected, [], title_map

def reset_statutes_in_collection(client, coll_name="legal_knowledge_vault"):
    """
    Deletes ONLY documents with source_type == 'statute'.
    Preserves all other documents (e.g. source_type == 'case_file').
    """
    try:
        coll = client.get_collection(coll_name)
        non_statutes = coll.get(where={"source_type": {"$ne": "statute"}})
        non_statute_ids = non_statutes.get("ids", [])
        non_statute_docs = non_statutes.get("documents", [])
        non_statute_metas = non_statutes.get("metadatas", [])
        
        client.delete_collection(coll_name)
        new_coll = client.get_or_create_collection(coll_name)
        
        if non_statute_ids:
            new_coll.upsert(ids=non_statute_ids, documents=non_statute_docs, metadatas=non_statute_metas)
            print(f"Statute records reset successfully. Preserved {len(non_statute_ids)} non-statute records.")
        else:
            print("Statute records reset successfully. Collection recreated cleanly.")
        return new_coll
    except Exception as e:
        print(f"Note on reset statutes: {e}")
        return client.get_or_create_collection(coll_name)

def run_ingest(pdf_dir: str, target: str, confirm: bool, reset_statutes: bool = False):
    if target == "prod" and not confirm:
        print("[ERROR] Production ingest refused! Must specify --target prod --confirm to write to production ai_engine/chroma_db.")
        sys.exit(1)
        
    db_path = "scratch/eval_chroma_db" if target == "scratch" else os.path.join(os.path.dirname(__file__), "chroma_db")
    print(f"Target vector store directory: {db_path}")
    
    import chromadb
    from chromadb.utils import embedding_functions
    
    client = chromadb.PersistentClient(path=db_path)
    emb_func = embedding_functions.DefaultEmbeddingFunction()
    
    if reset_statutes:
        coll = reset_statutes_in_collection(client, "legal_knowledge_vault")
    else:
        coll = client.get_or_create_collection(name="legal_knowledge_vault", embedding_function=emb_func)
        
    ingested_counts = {}
    
    # 1. Ingest PDF Statutes (BNS & BNSS)
    for pdf_name, config in ACT_CONFIGS.items():
        pdf_path = os.path.join(pdf_dir, pdf_name)
        if not os.path.exists(pdf_path): continue
        sections, _, _, _, _, title_map = parse_pdf(pdf_path, config)
        if not sections: continue
        
        ids, documents, metadatas = [], [], []
        for sec_num, sec_data in sections.items():
            sec_title = sec_data["title"]
            sec_id = f"{config['act_name']}_sec_{sec_num}"
            full_text = sec_data["content"]
            word_count = len(full_text.split())
            
            doc_str = f"Act: {config['act_name']}, Section {sec_num}: {sec_title}.\n{full_text}"
            
            ids.append(sec_id)
            documents.append(doc_str)
            metadatas.append({
                "source_type": "statute",
                "act_name": config["act_name"],
                "section_no": sec_num,
                "title": sec_title,
                "section_words": word_count,
                "partial_coverage": config["partial_coverage"],
                "unverified_currency": config.get("unverified_currency", False),
                "legal_era": config["legal_era"],
                "text_as_of": config["text_as_of"],
                "latest_amendment_cited": config.get("latest_amendment_cited", "unknown"),
                "source_dataset": config["source_dataset"]
            })
            
        if ids:
            coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
            ingested_counts[config["act_name"]] = len(ids)

    # 2. Ingest Retained HF Acts
    print("\nIngesting retained HuggingFace dataset statutes...")
    try:
        from datasets import Dataset
        ds_arrow = "/home/sonia/.cache/huggingface/datasets/mratanusarkar___indian-laws/default/0.0.0/46e97a9abe88585bb678ec041374c7f756f98c23/indian-laws-train.arrow"
        if os.path.exists(ds_arrow):
            ds = Dataset.from_file(ds_arrow)
        else:
            from datasets import load_dataset
            ds = load_dataset('mratanusarkar/Indian-Laws', split='train')
        
        for hf_title, hf_meta in RETAINED_HF_ACTS.items():
            hf_rows = [r for r in ds if r.get("act_title") == hf_title]
            if not hf_rows: continue
            
            ids, documents, metadatas = [], [], []
            max_sec_limit = hf_meta.get("max_section")
            
            for row in hf_rows:
                sec_num = str(row.get("section", "")).strip()
                law_text = norm_space(row.get("law", ""))
                if not sec_num or not law_text: continue
                
                # Check section limit for partial acts (e.g. NI Act 1-142, Constitution 1-30)
                if max_sec_limit:
                    m_sec = re.match(r'^(\d+)', sec_num)
                    if m_sec and int(m_sec.group(1)) > max_sec_limit:
                        continue
                        
                lines = law_text.split('\n')
                first_line = lines[0] if lines else ""
                title = first_line[:100]
                
                sec_id = f"{hf_meta['act_name']}_sec_{sec_num}"
                word_count = len(law_text.split())
                doc_str = f"Act: {hf_meta['act_name']}, Section {sec_num}: {title}.\n{law_text}"
                
                ids.append(sec_id)
                documents.append(doc_str)
                metadatas.append({
                    "source_type": "statute",
                    "act_name": hf_meta["act_name"],
                    "section_no": sec_num,
                    "title": title,
                    "section_words": word_count,
                    "partial_coverage": hf_meta["partial_coverage"],
                    "unverified_currency": hf_meta["unverified_currency"],
                    "legal_era": hf_meta["legal_era"],
                    "text_as_of": hf_meta["text_as_of"],
                    "latest_amendment_cited": hf_meta.get("latest_amendment_cited", "unknown"),
                    "source_dataset": hf_meta["source_dataset"]
                })
                    
            if ids:
                coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
                ingested_counts[hf_meta["act_name"]] = len(ids)
    except Exception as e:
        print(f"HF Dataset Ingestion Error: {e}")
        
    print("\n--- INGESTION SUMMARY PER ACT (ONE RECORD PER SECTION) ---")
    for act_name, count in ingested_counts.items():
        print(f" - {act_name}: {count} section records")
    print(f"Total Collection Count: {coll.count()}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Statute PDFs and Retained Central Acts")
    parser.add_argument("--pdf-dir", default="data/statute_pdfs", help="Directory containing PDFs")
    parser.add_argument("--target", choices=["scratch", "prod"], default="scratch", help="Vector store target")
    parser.add_argument("--confirm", action="store_true", help="Confirm writing to production vector store")
    parser.add_argument("--reset-statutes", action="store_true", help="Reset ONLY statute records prior to ingestion")
    args = parser.parse_args()
    
    run_ingest(args.pdf_dir, target=args.target, confirm=args.confirm, reset_statutes=args.reset_statutes)
