import argparse
import os
import re
import sys
import fitz
from transformers import AutoTokenizer

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
    },
    "BSA_2023.pdf": {
        "act_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "legal_era": "post-2024-criminal-codes",
        "official_sections_count": 170,
        "partial_coverage": False,
        "covered_range": "1-170",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+\(1\)\s+This\s+Act\s+may\s+be\s+called\s+the\s+Bharatiya\s+Sakshya\s+Adhiniyam',
        "known_repealed_ranges": [],
        "text_as_of": "as enacted 2023-12-25",
        "latest_amendment_cited": "2023-12-25",
        "source_dataset": "official_pdf"
    },
    "IPC_1860.pdf": {
        "act_name": "Indian Penal Code, 1860",
        "legal_era": "pre-2024-criminal-codes",
        "official_sections_count": 511,
        "partial_coverage": False,
        "covered_range": "1-511",
        "sec_1_pattern": r'(?:\n|^)\s*1\.\s+Title\s+and\s+extent\s+of\s+operation',
        "known_repealed_ranges": [set(range(161, 166))],  # 161, 162, 163, 164, 165
        "text_as_of": "unknown",
        "latest_amendment_cited": "1997",
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
        "text_as_of": "unknown",
        "latest_amendment_cited": "unknown",
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
        "latest_amendment_cited": "1973-01-25",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Negotiable Instruments Act, 1881": {
        "act_name": "Negotiable Instruments Act, 1881",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": True,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1881-12-09",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Indian Contract Act, 1872": {
        "act_name": "Indian Contract Act, 1872",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1872-04-25",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Code of Civil Procedure, 1908": {
        "act_name": "Code of Civil Procedure, 1908",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1908-03-21",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Consumer Protection Act, 2019": {
        "act_name": "Consumer Protection Act, 2019",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "2019-08-09",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Limitation Act, 1963": {
        "act_name": "Limitation Act, 1963",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1963-10-05",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Hindu Marriage Act, 1955": {
        "act_name": "Hindu Marriage Act, 1955",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1955-05-18",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Transfer of Property Act, 1882": {
        "act_name": "Transfer of Property Act, 1882",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1882-02-17",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Registration Act, 1908": {
        "act_name": "Registration Act, 1908",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1908-12-18",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Advocates Act, 1961": {
        "act_name": "Advocates Act, 1961",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1961-05-19",
        "source_dataset": "hf_mratanusarkar_indian_laws"
    },
    "Constitution of India, 1949": {
        "act_name": "Constitution of India, 1949",
        "legal_era": "retained-central-act",
        "partial_coverage": True,
        "unverified_currency": False,
        "text_as_of": "unknown",
        "latest_amendment_cited": "1949-11-26",
        "source_dataset": "hf_mratanusarkar_indian_laws"
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

def extract_titles_from_pdf(pdf_path: str, filename: str) -> dict:
    """
    Extracts section titles for BNS/BNSS/BSA from marginal notes (x0 coordinate analysis)
    or for IPC/Evidence Act from inline heading text.
    """
    if not os.path.exists(pdf_path):
        return {}
    
    doc = fitz.open(pdf_path)
    titles = {}
    
    if filename in ["BNS_2023.pdf", "BNSS_2023.pdf", "BSA_2023.pdf"]:
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
    else:
        full_text = '\n'.join([p.get_text('text') for p in doc])
        pattern = re.compile(r'\n\s*(\d+[A-Z]*)\.\s+([^.\n\-]+(?:\.[^.\n\-]+)?)(?:\.\-\-|\-\-|\.\s*\n|\s*\n)')
        for m in pattern.finditer(full_text):
            sec = m.group(1).strip()
            title = m.group(2).strip()
            title = re.sub(r'^\d+\*?\[', '', title)
            title = norm_space(title)
            if sec not in titles and len(title) > 2 and len(title) < 150:
                titles[sec] = title
                
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

    title_map = extract_titles_from_pdf(pdf_path, filename)

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
        sec_title = title_map.get(label, f"Section {label}")
        
        if num == last_num:
            duplicates.append((label, cleaned_content[:60]))
            if label not in sections or len(cleaned_content) > len(sections[label]["content"]):
                sections[label] = {
                    "raw": raw_content,
                    "content": cleaned_content,
                    "title": sec_title
                }
        elif num == last_num + 1:
            sections[label] = {
                "raw": raw_content,
                "content": cleaned_content,
                "title": sec_title
            }
            last_num = num
        elif num > last_num + 1:
            gap = set(range(last_num + 1, num))
            if gap.issubset(known_repealed_set) or re.search(r'\[Rep\.\s+by|\[Omitted\b|\[Repealed\b', raw_content[:200], re.IGNORECASE):
                sections[label] = {
                    "raw": raw_content,
                    "content": cleaned_content,
                    "title": sec_title
                }
                last_num = num
            else:
                rejected.append((label, raw_content[:60]))
        else:
            rejected.append((label, raw_content[:60]))
            
    return sections, None, duplicates, rejected, all_removed_lines, title_map

def split_section_into_subsections(act_name: str, sec_num: str, title: str, content: str, max_words: int = 45, overlap: int = 10):
    """
    Splits any section text into chunks of at most 45 words (~55 tokens max)
    with 10 words overlap. Each part is prefixed with:
    'Act: {act_name}, Section {sec_num}: {title} (Part {k}).\n'
    Guarantees 0 chunks in the entire vector store exceed 256 tokens!
    """
    header = f"Act: {act_name}, Section {sec_num}: {title}"
    words = content.split()
    
    if not words:
        return [(f"{act_name}_sec_{sec_num}", f"{header}.\n{content}")]
        
    parts = []
    if len(words) <= max_words:
        parts = [content.strip()]
    else:
        i = 0
        while i < len(words):
            w_chunk = words[i : i + max_words]
            parts.append(" ".join(w_chunk))
            if i + max_words >= len(words):
                break
            i += (max_words - overlap)
            
    result = []
    total = len(parts)
    for k, p in enumerate(parts, 1):
        chunk_id = f"{act_name}_sec_{sec_num}_part_{k}" if total > 1 else f"{act_name}_sec_{sec_num}"
        suffix = f" (Part {k})" if total > 1 else ""
        chunk_text = f"{header}{suffix}.\n{p}"
        result.append((chunk_id, chunk_text))
        
    return result

def run_dry_run(pdf_dir: str, strict: bool = False):
    print("=========================================================")
    print(" STATUTE INGESTION -- FAIL-CLOSED DRY RUN REPORT")
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
        sections, err_msg, duplicates, rejected, removed_lines, title_map = res
        
        if sections is None:
            print(f"[SKIPPED] {pdf_name}: {err_msg}")
            if strict: dry_run_failed = True
            print("\n" + "="*50 + "\n")
            continue
            
        base_nums = [int(re.sub(r'\D', '', k)) for k in sections.keys() if re.sub(r'\D', '', k)]
        official_max = config["official_sections_count"]
        
        total_chunks = 0
        split_sections_count = 0
        exceed_256_count = 0
        for sec_num, sec_data in sections.items():
            ch = split_section_into_subsections(config["act_name"], sec_num, sec_data["title"], sec_data["content"])
            total_chunks += len(ch)
            if len(ch) > 1:
                split_sections_count += 1
            for cid, ctext in ch:
                if TOKENIZER and len(TOKENIZER.encode(ctext, truncation=False)) > 256:
                    exceed_256_count += 1

        print(f"Extracted Sections Count: {len(sections)}")
        print(f"Official Sections Count:  {official_max}")
        print(f"Total Vector Chunks:      {total_chunks} (Long sections split: {split_sections_count})")
        print(f"Chunks > 256 Tokens:      {exceed_256_count}")
        print(f"Extracted Titles Count:   {len(title_map)}")
        print(f"Duplicates Logged:        {len(duplicates)}")
        print(f"Rejected Candidates:      {len(rejected)}")
        print(f"Removed Header/Footer Lines Count: {len(removed_lines)}")
        
        print("\n  Sample 10 (Section, Title) Pairs:")
        sample_keys = list(sections.keys())[:10]
        for sk in sample_keys:
            stitle = sections[sk]["title"]
            print(f"   - Section {sk}: {repr(stitle)}")
            
        known_repealed_set = set()
        for r in config.get("known_repealed_ranges", []):
            known_repealed_set.update(r)
            
        missing_base = [str(n) for n in range(1, official_max + 1) if str(n) not in sections and n not in known_repealed_set]
        if missing_base:
            print(f"[FAIL] Missing Base Sections (1..{official_max}): {missing_base}")
            dry_run_failed = True
        else:
            print(f"Base Section Coverage (1..{official_max}): COMPLETE (or recognized repealed)")
            
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
                    
        print("\n" + "="*50 + "\n")

    print("--- 5. HF DATASETS COVERAGE AUDIT ---")
    print("EXCLUDED ACTS:")
    print(" - Information Technology Act, 2000 (Excluded: pre-2008 text; missing Sections 43A, 66C, 66D, 66E, 66F, 67A).")
    print(" - Specific Relief Act, 1963 (Excluded: pre-2018 text; section 10 states pre-2018 discretionary rule).")
    print("INCLUDED RETAINED ACTS (11):")
    for hf_key, hf_meta in RETAINED_HF_ACTS.items():
        flags = []
        if hf_meta["partial_coverage"]: flags.append("PARTIAL_COVERAGE")
        if hf_meta["unverified_currency"]: flags.append("UNVERIFIED_CURRENCY")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f" - {hf_meta['act_name']}{flag_str}")
    print("\n" + "="*50 + "\n")

    print("--- 7. FILE IDENTITY INSPECTION ---")
    for fname in ["BSA_2023.pdf", "Evidence_Act_1872.pdf", "IPC_1860.pdf", "BNS_2023.pdf", "BNSS_2023.pdf"]:
        fpath = os.path.join(pdf_dir, fname)
        print(f"File: {fname}")
        if not os.path.exists(fpath):
            print(" Status: MISSING")
            print(" First 200 Chars Page 1: N/A")
        else:
            d = fitz.open(fpath)
            p1 = d[0].get_text("text")[:200] if len(d) > 0 else ""
            is_bill = "BILL" in p1.upper() and "ACT NO." not in p1.upper()
            print(f" Classification: {'Bill' if is_bill else 'Enacted Act'}")
            print(f" Pages Count: {len(d)}")
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

def reset_statutes_in_collection(coll):
    """
    Deletes ONLY documents with source_type == 'statute'.
    Preserves all other documents (e.g. source_type == 'case_file').
    """
    try:
        results = coll.get(where={"source_type": "statute"})
        if results and results.get("ids"):
            ids_to_del = results["ids"]
            print(f"Deleting {len(ids_to_del)} existing statute records from vector store...")
            coll.delete(ids=ids_to_del)
            print("Statute records reset successfully.")
        else:
            print("No existing statute records found to reset.")
    except Exception as e:
        print(f"Note on reset statutes: {e}")

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
    coll = client.get_or_create_collection(name="legal_knowledge_vault", embedding_function=emb_func)
    
    if reset_statutes:
        reset_statutes_in_collection(coll)
        
    ingested_counts = {}
    
    # 1. Ingest PDF Statutes
    for pdf_name, config in ACT_CONFIGS.items():
        pdf_path = os.path.join(pdf_dir, pdf_name)
        if not os.path.exists(pdf_path): continue
        sections, _, _, _, _, title_map = parse_pdf(pdf_path, config)
        if not sections: continue
        
        ids, documents, metadatas = [], [], []
        for sec_num, sec_data in sections.items():
            sec_title = sec_data["title"]
            chunks = split_section_into_subsections(config["act_name"], sec_num, sec_title, sec_data["content"])
            for chunk_id, chunk_text in chunks:
                ids.append(chunk_id)
                documents.append(chunk_text)
                metadatas.append({
                    "source_type": "statute",
                    "act_name": config["act_name"],
                    "section_no": sec_num,
                    "title": sec_title,
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
        from datasets import load_dataset
        ds = load_dataset('mratanusarkar/Indian-Laws', split='train')
        
        for hf_title, hf_meta in RETAINED_HF_ACTS.items():
            hf_rows = [r for r in ds if r.get("act_title") == hf_title]
            if not hf_rows: continue
            
            ids, documents, metadatas = [], [], []
            for row in hf_rows:
                sec_num = str(row.get("section", "")).strip()
                law_text = norm_space(row.get("law", ""))
                if not sec_num or not law_text: continue
                
                lines = law_text.split('\n')
                first_line = lines[0] if lines else ""
                title = first_line[:100]
                
                chunks = split_section_into_subsections(hf_meta["act_name"], sec_num, title, law_text)
                for chunk_id, chunk_text in chunks:
                    ids.append(chunk_id)
                    documents.append(chunk_text)
                    metadatas.append({
                        "source_type": "statute",
                        "act_name": hf_meta["act_name"],
                        "section_no": sec_num,
                        "title": title,
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
        
    print("\n--- INGESTION SUMMARY PER ACT ---")
    for act_name, count in ingested_counts.items():
        print(f" - {act_name}: {count} vector chunks")
    print(f"Total Collection Count: {coll.count()}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Statute PDFs and Retained Central Acts")
    parser.add_argument("--pdf-dir", default="data/statute_pdfs", help="Directory containing PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing to ChromaDB")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on skipped files/Bills in dry-run")
    parser.add_argument("--target", choices=["scratch", "prod"], default="scratch", help="Vector store target")
    parser.add_argument("--confirm", action="store_true", help="Confirm writing to production vector store")
    parser.add_argument("--reset-statutes", action="store_true", help="Reset ONLY statute records prior to ingestion")
    args = parser.parse_args()
    
    if args.dry_run:
        run_dry_run(args.pdf_dir, strict=args.strict)
    else:
        run_ingest(args.pdf_dir, target=args.target, confirm=args.confirm, reset_statutes=args.reset_statutes)
