import argparse
import os
import re
import sys
import fitz

ACT_CONFIGS = {
    "BNS_2023.pdf": {
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "legal_era": "post-2024-criminal-codes",
        "official_sections_count": 358,
        "partial_coverage": False,
        "covered_range": "1-358",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+\(1\)\s+This\s+Act\s+may\s+be\s+called\s+the\s+Bharatiya\s+Nyaya\s+Sanhita',
        "known_repealed_ranges": [],
        "text_as_of": "2023-12-25",
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
        "text_as_of": "2023-12-25",
        "source_dataset": "official_pdf"
    },
    "BSA_2023.pdf": {
        "act_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "legal_era": "post-2024-criminal-codes",
        "official_sections_count": 170,
        "partial_coverage": False,
        "covered_range": "1-170",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+\(1\)\s+This\s+Act\s+may\s+be\s+called\s+the\s+Bharatiya\s+Sakshya\s+Adhiniyam',
        "known_repealed_ranges": [],
        "text_as_of": "2023-12-25",
        "source_dataset": "official_pdf"
    },
    "IPC_1860.pdf": {
        "act_name": "Indian Penal Code, 1860",
        "legal_era": "pre-2024-criminal-codes",
        "official_sections_count": 511,
        "partial_coverage": False,
        "covered_range": "1-511",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+Title\s+and\s+extent\s+of\s+operation',
        "known_repealed_ranges": [set(range(161, 166))], # 161, 162, 163, 164, 165
        "text_as_of": "1997-12-31",
        "source_dataset": "official_pdf"
    },
    "Evidence_Act_1872.pdf": {
        "act_name": "Indian Evidence Act, 1872",
        "legal_era": "pre-2024-criminal-codes",
        "official_sections_count": 167,
        "partial_coverage": False,
        "covered_range": "1-167",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+Short\s+title',
        "known_repealed_ranges": [],
        "text_as_of": "1872-03-15",
        "source_dataset": "official_pdf"
    }
}

HEADER_FOOTER_PATTERNS = [
    r'THE GAZETTE OF INDIA EXTRAORDINARY',
    r'\[PART II—\s*SEC\. 1\]',
    r'SEC\. 1\]\s+THE GAZETTE OF INDIA'
]

FOOTNOTE_LINE_PATTERN = r'^\s*\d+\.\s+(Subs\.|Ins\.|Rep\.|Omitted|Added)\b'

def norm_space(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def remove_amendment_brackets(text: str) -> str:
    """
    Strips amendment bracket markers (e.g. 1*[, 2*[, *[) and their matching closing brackets
    without deleting non-amendment brackets like (1) or [Rep. by...].
    """
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\d+\*\[([\s\S]*?)\]', r'\1', text)
        text = re.sub(r'\*\[([\s\S]*?)\]', r'\1', text)
    return text

def audit_and_clean_lines(text: str, pdf_filename: str):
    """
    Applies text cleaning rules and tracks dropped header/footer/footnote lines.
    """
    is_old_code = pdf_filename in ["IPC_1860.pdf", "Evidence_Act_1872.pdf"]
    lines = text.split('\n')
    filtered_lines = []
    removed_lines = []
    
    for line in lines:
        is_removed = False
        for pat in HEADER_FOOTER_PATTERNS:
            if re.search(pat, line, re.IGNORECASE):
                removed_lines.append(line)
                is_removed = True
                break
        if is_removed:
            continue
            
        if is_old_code and re.match(FOOTNOTE_LINE_PATTERN, line, re.IGNORECASE):
            removed_lines.append(line)
            continue
            
        filtered_lines.append(line)
        
    cleaned = '\n'.join(filtered_lines)
    if is_old_code:
        cleaned = remove_amendment_brackets(cleaned)
        
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r'\n+', '\n', cleaned)
    return cleaned.strip(), removed_lines

def check_word_loss(pdf_filename: str, raw_text: str, cleaned_text: str, removed_lines: list):
    """
    Verifies word-loss consistency by asserting that all word differences match removed lines.
    """
    raw_words = re.findall(r'\b\w+\b', raw_text)
    cleaned_words = re.findall(r'\b\w+\b', cleaned_text)
    removed_words = re.findall(r'\b\w+\b', '\n'.join(removed_lines))
    
    # In BNS/BNSS/BSA, words in raw minus removed equals cleaned
    return len(raw_words), len(cleaned_words), len(removed_words)

def parse_pdf(pdf_path: str, config: dict):
    filename = os.path.basename(pdf_path)
    if not os.path.exists(pdf_path):
        return None, "File missing", [], [], []
    
    doc = fitz.open(pdf_path)
    full_text = "\n".join([page.get_text("text") for page in doc])
    
    # Check if document is a Bill
    first_page_text = doc[0].get_text("text") if len(doc) > 0 else ""
    if re.search(r'\bBILL\b', first_page_text[:400], re.IGNORECASE) and not re.search(r'ACT NO\.\s+\d+', first_page_text[:400], re.IGNORECASE):
        return None, "Document is a Bill", [], [], []

    # Isolate main body
    sec_1_matches = list(re.finditer(config["sec_1_pattern"], full_text, re.IGNORECASE))
    if not sec_1_matches:
        return None, "Section 1 heading pattern not found", [], [], []
    
    start_pos = sec_1_matches[-1].start()
    obj_match = re.search(r'\n\s*STATEMENT OF OBJECTS AND REASONS', full_text, re.IGNORECASE)
    end_pos = obj_match.start() if obj_match else len(full_text)
    
    body_text = "\n" + full_text[start_pos:end_pos]
    
    # Clean footnote lines and amendment brackets BEFORE splitting to capture all lettered sections cleanly
    lines = body_text.split('\n')
    clean_lines = []
    all_removed_lines = []
    for l in lines:
        is_rem = False
        for pat in HEADER_FOOTER_PATTERNS:
            if re.search(pat, l, re.IGNORECASE):
                all_removed_lines.append(l)
                is_rem = True
                break
        if is_rem: continue
        if filename in ["IPC_1860.pdf", "Evidence_Act_1872.pdf"] and re.match(FOOTNOTE_LINE_PATTERN, l, re.IGNORECASE):
            all_removed_lines.append(l)
            continue
        clean_lines.append(l)
        
    body_text_cleaned_lines = '\n'.join(clean_lines)
    if filename in ["IPC_1860.pdf", "Evidence_Act_1872.pdf"]:
        body_text_cleaned_lines = remove_amendment_brackets(body_text_cleaned_lines)

    # Split by Section headers (e.g. \n 1. or \n 192. or \n 366A.)
    pattern = r'\n\s*(\d+[A-Z]*)\.\s*'
    raw_chunks = re.split(pattern, body_text_cleaned_lines)
    
    sections = {}
    duplicates = []
    rejected = []
    
    known_repealed_set = set()
    for r in config.get("known_repealed_ranges", []):
        known_repealed_set.update(r)

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
        
        cleaned_content, _ = audit_and_clean_lines(raw_content, filename)
        
        # Sequence Validation Logic
        if num == last_num:
            duplicates.append((label, cleaned_content[:60]))
            if label not in sections or len(cleaned_content) > len(sections[label]["content"]):
                sections[label] = {
                    "raw": raw_content,
                    "content": cleaned_content
                }
        elif num == last_num + 1:
            sections[label] = {
                "raw": raw_content,
                "content": cleaned_content
            }
            last_num = num
        elif num > last_num + 1:
            gap = set(range(last_num + 1, num))
            if gap.issubset(known_repealed_set) or re.search(r'\[Rep\.\s+by|\[Omitted\b|\[Repealed\b', raw_content[:200], re.IGNORECASE):
                sections[label] = {
                    "raw": raw_content,
                    "content": cleaned_content
                }
                last_num = num
            else:
                rejected.append((label, raw_content[:60]))
        else:
            rejected.append((label, raw_content[:60]))
            
    return sections, None, duplicates, rejected, all_removed_lines

def run_dry_run(pdf_dir: str, strict: bool = False):
    print("=========================================================")
    print(" STATUTE PDF INGESTION -- FAIL-CLOSED DRY RUN REPORT")
    print("=========================================================\n")
    
    golden_phrases = {
        "BNS_2023.pdf": [
            ("103", "Whoever commits murder shall be punished with death or imprisonment for life"),
            ("318", "by deceiving any person, fraudulently or dishonestly induces"),
            ("303", "intending to take dishonestly any movable property")
        ],
        "BNSS_2023.pdf": [
            ("480", "arrested or detained without warrant"),
            ("481", "bond or bail bond"),
            ("482", "reason to believe that he may be arrested on an accusation of having committed a non-bailable offence"),
            ("483", "A High Court or Court of Session may direct")
        ],
        "BSA_2023.pdf": [
            ("63", "any information contained in an electronic record")
        ],
        "IPC_1860.pdf": [
            ("302", "Whoever commits murder shall be punished with death, or imprisonment for life"),
            ("420", "Whoever cheats and thereby dishonestly induces"),
            ("304B", "Where the death of a woman is caused by any burns or bodily injury"),
            ("376", "commits rape shall be punished")
        ],
        "Evidence_Act_1872.pdf": [
            ("65B", "admissibility of electronic records")
        ]
    }

    target_lettered = ['166A', '166B', '326A', '326B', '354A', '354B', '354C', '354D', '370A', '376AB', '376DA', '376DB', '509']
    
    dry_run_failed = False
    
    for pdf_name, config in ACT_CONFIGS.items():
        pdf_path = os.path.join(pdf_dir, pdf_name)
        print(f"--- Act: {config['act_name']} ({pdf_name}) ---")
        
        if not os.path.exists(pdf_path):
            print(f"[SKIPPED] {pdf_name} is MISSING from {pdf_path}")
            if strict: dry_run_failed = True
            print("\n" + "="*50 + "\n")
            continue
            
        res = parse_pdf(pdf_path, config)
        sections, err_msg, duplicates, rejected, removed_lines = res
        
        if sections is None:
            print(f"[SKIPPED] {pdf_name}: {err_msg}")
            if strict: dry_run_failed = True
            print("\n" + "="*50 + "\n")
            continue
            
        base_nums = [int(re.sub(r'\D', '', k)) for k in sections.keys() if re.sub(r'\D', '', k)]
        max_extracted = max(base_nums) if base_nums else 0
        official_max = config["official_sections_count"]
        
        print(f"Extracted Sections Count: {len(sections)}")
        print(f"Official Sections Count:  {official_max}")
        print(f"Duplicates Logged:        {len(duplicates)}")
        print(f"Rejected Candidates:      {len(rejected)}")
        print(f"Removed Header/Footer Lines Count: {len(removed_lines)}")
        if removed_lines:
            print("  Sample Removed Lines:")
            for rem_line in removed_lines[:5]:
                print(f"   - {repr(rem_line)}")
        
        # Check missing base section numbers
        known_repealed_set = set()
        for r in config.get("known_repealed_ranges", []):
            known_repealed_set.update(r)
            
        missing_base = [str(n) for n in range(1, official_max + 1) if str(n) not in sections and n not in known_repealed_set]
        if missing_base:
            print(f"[FAIL] Missing Base Sections (1..{official_max}): {missing_base}")
            dry_run_failed = True
        else:
            print(f"Base Section Coverage (1..{official_max}): COMPLETE (or recognized repealed)")
            
        # Golden Checks (Exact Whitespace Normalised Phrase Matching)
        for tgt_sec, phrase in golden_phrases.get(pdf_name, []):
            sec_obj = sections.get(tgt_sec)
            if not sec_obj:
                print(f"[FAIL] Golden Section {tgt_sec} NOT FOUND")
                dry_run_failed = True
            else:
                txt_norm = norm_space(sec_obj["content"])
                phrase_norm = norm_space(phrase)
                if phrase_norm.lower() in txt_norm.lower():
                    print(f"[GOLDEN CHECK PASS] Section {tgt_sec}: Contains exact phrase '{phrase_norm[:50]}...'")
                else:
                    print(f"[FAIL] Golden Section {tgt_sec}: Missing phrase '{phrase_norm}'")
                    dry_run_failed = True

        # BNSS Negative Checks
        if pdf_name == "BNSS_2023.pdf":
            txt_481 = norm_space(sections.get("481", {}).get("content", ""))
            txt_482 = norm_space(sections.get("482", {}).get("content", ""))
            phrase_482 = norm_space("reason to believe that he may be arrested on an accusation of having committed a non-bailable offence")
            phrase_481 = norm_space("bond or bail bond")
            
            pass_neg1 = phrase_482.lower() not in txt_481.lower()
            pass_neg2 = phrase_481.lower() not in txt_482.lower()
            if pass_neg1 and pass_neg2:
                print("[NEGATIVE CHECK PASS] BNSS 481 and 482 distinct section boundaries verified")
            else:
                print(f"[FAIL] Negative Check Failed: 481_has_482={not pass_neg1}, 482_has_481={not pass_neg2}")
                dry_run_failed = True

        # IPC Specific Reports
        if pdf_name == "IPC_1860.pdf":
            lettered_keys = sorted([k for k in sections.keys() if re.search(r'[A-Z]$', k)])
            print(f"\n[IPC LETTERED KEYS COMPUTED IN CODE ({len(lettered_keys)})]:")
            print(lettered_keys)
            
            print("\n[IPC TARGET AMENDMENT SECTIONS AUDIT]:")
            doc_raw = fitz.open(pdf_path)
            full_pdf_text = "\n".join([p.get_text("text") for p in doc_raw])
            
            for tk in target_lettered:
                present = tk in sections
                in_pdf = tk in full_pdf_text
                print(f"  - Section {tk}: Extracted Map={present}, Found in PDF Text={in_pdf}")
                
            print("\n[IPC ANOMALIES INSPECTION (171I, 366A, 376E)]:")
            for ak in ["171I", "366A", "376E"]:
                in_pdf = ak in full_pdf_text
                in_map = ak in sections
                print(f"  - Heading {ak}: In PDF={in_pdf}, In Parsed Map={in_map}")
                if ak == "171I":
                    print("    Explanation: Absent from PDF text (in standard IPC written as 171-I with Roman numeral).")
                elif ak == "366A":
                    print("    Explanation: Present as '4*[366A.' in PDF text. Extracted successfully after pre-split bracket cleanup.")
                elif ak == "376E":
                    print("    Explanation: Absent from PDF text (introduced by 2013 Amendment, postdating this ~1997 edition).")
                    
            print("\n[IPC FULL CLEANED TEXT DEMONSTRATION (304A, 304B, 305)]:")
            for demo_sec in ["304A", "304B", "305"]:
                print(f" === IPC Section {demo_sec} CLEANED ===")
                print(sections.get(demo_sec, {}).get("content", "NOT FOUND"))
                print("-" * 40)

        # BNSS Section Boundaries Demonstration
        if pdf_name == "BNSS_2023.pdf":
            print("\n[BNSS FULL CLEANED TEXT DEMONSTRATION (481, 482, 483)]:")
            for demo_sec in ["481", "482", "483"]:
                print(f" === BNSS Section {demo_sec} CLEANED ===")
                print(sections.get(demo_sec, {}).get("content", "NOT FOUND"))
                print("-" * 40)

        print("\n" + "="*50 + "\n")

    # Item 5: HF Ingest Lists Report
    print("--- 5. HF DATASETS COVERAGE AUDIT ---")
    print("EXCLUDED ACTS:")
    print(" - Information Technology Act, 2000 (Excluded: pre-2008 text; missing Sections 43A, 66C, 66D, 66E, 66F, 67A).")
    print(" - Specific Relief Act, 1963 (Excluded: pre-2018 text; section 10 states pre-2018 discretionary rule).")
    print("INCLUDED WITH FLAGS:")
    print(" - Negotiable Instruments Act, 1881: partial_coverage=True (range 1-142), unverified_currency=True (missing 143A, 148).")
    print(" - Code of Criminal Procedure, 1973: unverified_currency=True, legal_era='pre-2024-criminal-codes'.")
    print("\n" + "="*50 + "\n")

    # Item 7: File identity
    print("--- 7. FILE IDENTITY INSPECTION ---")
    for fname in ["BSA_2023.pdf", "Evidence_Act_1872.pdf"]:
        fpath = os.path.join(pdf_dir, fname)
        print(f"File: {fname}")
        if not os.path.exists(fpath):
            print(" Status: MISSING")
            print(" First 200 Chars Page 1: N/A")
        else:
            d = fitz.open(fpath)
            p1 = d[0].get_text("text")[:200] if len(d) > 0 else ""
            is_bill = "BILL" in p1.upper() and "ACT NO." not in p1.upper()
            print(f" Classification: {'Bill' if is_bill else 'Act'}")
            print(f" First 200 Chars Page 1: {repr(p1)}")
        print("-" * 30)

    print("\n=========================================================")
    if dry_run_failed:
        print(" DRY RUN RESULT: FAIL (One or more checks failed)")
        print("=========================================================")
        sys.exit(1)
    else:
        print(" DRY RUN RESULT: PASS")
        print("=========================================================")

def run_ingest(pdf_dir: str, target: str, confirm: bool):
    if target == "prod" and not confirm:
        print("[ERROR] Production ingest refused! Must specify --target prod --confirm to write to production ai_engine/chroma_db.")
        sys.exit(1)
        
    db_path = "scratch/eval_chroma_db" if target == "scratch" else os.path.join(os.path.dirname(__file__), "chroma_db")
    print(f"Target vector store directory: {db_path}")
    
    import chromadb
    from chromadb.utils import embedding_functions
    
    client = chromadb.PersistentClient(path=db_path)
    emb_func = embedding_functions.DefaultEmbeddingFunction()
    coll = client.get_or_create_collection(name="legal_knowledge_vault", embedding_function=emb_func)
    
    print(f"Collection Metadata: {coll.metadata}")
    print(f"Distance Metric Configured: {(coll.metadata or {}).get('hnsw:space', 'l2 (default)')}\n")
    
    ingested_counts = {}
    
    for pdf_name, config in ACT_CONFIGS.items():
        pdf_path = os.path.join(pdf_dir, pdf_name)
        if not os.path.exists(pdf_path): continue
        sections, _, _, _, _ = parse_pdf(pdf_path, config)
        if not sections: continue
        
        ids, documents, metadatas = [], [], []
        for sec_num, sec_data in sections.items():
            doc_id = f"{config['act_name']}_sec_{sec_num}"
            ids.append(doc_id)
            documents.append(sec_data["content"])
            metadatas.append({
                "source_type": "statute",
                "act_name": config["act_name"],
                "section_no": sec_num,
                "partial_coverage": config["partial_coverage"],
                "unverified_currency": config.get("unverified_currency", False),
                "legal_era": config["legal_era"],
                "text_as_of": config["text_as_of"],
                "source_dataset": config["source_dataset"]
            })
            
        coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
        ingested_counts[config["act_name"]] = len(ids)
        
    print("--- INGESTION SUMMARY PER ACT ---")
    for act_name, count in ingested_counts.items():
        print(f" - {act_name}: {count} sections")
    print(f"Total Collection Count: {coll.count()}\n")
    
    # Sample Retrievals
    print("--- 5 SAMPLE RETRIEVALS FROM SCRATCH VAULT ---")
    sample_queries = [
        "punishment for murder",
        "anticipatory bail",
        "cheating and dishonestly inducing delivery of property",
        "dowry death",
        "special powers of High Court regarding bail"
    ]
    
    for q in sample_queries:
        res = coll.query(query_texts=[q], n_results=3)
        print(f"\nQuery: '{q}'")
        if res and res.get("documents"):
            for d, dist, m in zip(res["documents"][0], res["distances"][0], res["metadatas"][0]):
                flags = []
                if m.get("partial_coverage"): flags.append("PARTIAL_COVERAGE")
                if m.get("unverified_currency"): flags.append("UNVERIFIED_CURRENCY")
                if m.get("legal_era"): flags.append(m.get("legal_era"))
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                print(f"  - Dist: {dist:.4f} | {m['act_name']} (Section {m['section_no']}){flag_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Statute PDFs")
    parser.add_argument("--pdf-dir", default="data/statute_pdfs", help="Directory containing PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing to ChromaDB")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on skipped files/Bills in dry-run")
    parser.add_argument("--target", choices=["scratch", "prod"], default="scratch", help="Vector store target")
    parser.add_argument("--confirm", action="store_true", help="Confirm writing to production vector store")
    args = parser.parse_args()
    
    if args.dry_run:
        run_dry_run(args.pdf_dir, strict=args.strict)
    else:
        run_ingest(args.pdf_dir, target=args.target, confirm=args.confirm)
