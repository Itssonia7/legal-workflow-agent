import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import chromadb.telemetry.product.posthog
chromadb.telemetry.product.posthog.Posthog.capture = lambda self, event, *a, **kw: None

try:
    import torch
    import transformers
except Exception:
    pass

import argparse
import json
import sys
import chromadb
from chromadb.utils import embedding_functions

from sentence_transformers import SentenceTransformer
class PyTorchEmbeddingFunction:
    def __init__(self):
        path = '/home/sonia/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
        self.model = SentenceTransformer(path)
    def __call__(self, input):
        return self.model.encode(input).tolist()

def run_evaluation(eval_path="ai_engine/statute_eval.json", chroma_path="scratch/eval_chroma_db", collection_name="legal_knowledge_vault", store_label="NEW FORMAT STORE"):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    if not os.path.exists(eval_path):
        print(f"[ERROR] Evaluation dataset file {eval_path} not found.", flush=True)
        sys.exit(1)

    with open(eval_path, "r") as f:
        eval_queries = json.load(f)

    client = chromadb.PersistentClient(path=chroma_path)
    emb_func = embedding_functions.DefaultEmbeddingFunction()
    coll = client.get_collection(name=collection_name, embedding_function=emb_func)

    category_results = {}
    query_details = []

    print(f"\n=========================================================")
    print(f" STATUTE RETRIEVAL BENCHMARK EVALUATION ({store_label})")
    print(f" Path: {chroma_path} | Total Vector Count: {coll.count()}")
    print(f"=========================================================\n", flush=True)

    for idx, item in enumerate(eval_queries, 1):
        query = item["query"]
        cat = item["category"]
        expected = item["expected"]

        try:
            res = coll.query(query_texts=[query], n_results=8)
            print(f"DONE Q{idx:02d}", flush=True)
        except Exception as e:
            print(f"[Error querying '{query}']: {e}", flush=True)
            res = {}
        
        docs = res["documents"][0] if res and res.get("documents") else []
        metas = res["metadatas"][0] if res and res.get("metadatas") else []
        dists = res["distances"][0] if res and res.get("distances") else []

        if cat not in category_results:
            category_results[cat] = {"total": 0, "hit1": 0, "hit4": 0, "hit8": 0}
        category_results[cat]["total"] += 1

        rank_found = "NOT IN TOP 8"
        top3_retrieved = []

        for rank, (meta, dist) in enumerate(zip(metas[:3], dists[:3]), 1):
            act_n = meta.get("act_name", "Unknown")
            sec_n = str(meta.get("section_no", "")).strip()
            top3_retrieved.append((act_n, sec_n, round(dist, 4)))

        if not expected:
            # Negative query / Unrelated / Not covered
            top_dist = dists[0] if dists else 999.0
            is_correct = top_dist > 1.15
            if is_correct:
                category_results[cat]["hit1"] += 1
                category_results[cat]["hit4"] += 1
                category_results[cat]["hit8"] += 1
                rank_found = "CORRECT REJECTION (dist > 1.15)"
            else:
                rank_found = f"FALSE POSITIVE (dist={top_dist:.4f})"
        else:
            hit1, hit4, hit8 = False, False, False
            for rank, (meta, dist) in enumerate(zip(metas, dists), 1):
                act = str(meta.get("act_name", "") or "")
                sec = str(meta.get("section_no", "") or "").strip()
                
                match = False
                for exp_act, exp_sec in expected:
                    if str(exp_act).lower() in act.lower() and str(exp_sec).strip() == sec:
                        match = True
                        break
                if match:
                    if rank_found == "NOT IN TOP 8":
                        rank_found = f"Rank {rank}"
                    if rank <= 1: hit1 = True
                    if rank <= 4: hit4 = True
                    if rank <= 8: hit8 = True

            if hit1: category_results[cat]["hit1"] += 1
            if hit4: category_results[cat]["hit4"] += 1
            if hit8: category_results[cat]["hit8"] += 1

        query_details.append({
            "idx": idx,
            "query": query,
            "category": cat,
            "expected": expected,
            "rank_found": rank_found,
            "top3": top3_retrieved
        })

    print("--- 1. FULL QUERY-BY-QUERY BREAKDOWN (ALL 42 QUERIES) ---")
    for qd in query_details:
        exp_str = str(qd['expected']) if qd['expected'] else "None (Negative Query)"
        derivation = " [Derived from Memory: Retained HF Act]" if qd['category'] == 'retained_hf_acts' else " [Derived from PDF Text]" if qd['expected'] else ""
        print(f"Q{qd['idx']:02d} [{qd['category']}]: '{qd['query']}'")
        print(f"     Expected: {exp_str}{derivation}")
        print(f"     Found:    {qd['rank_found']}")
        print(f"     Top-3:    {qd['top3']}")
        print("-" * 45)

    print("\n--- 2. CATEGORY ACCURACY SUMMARY ---")
    print(f"{'Category':<32s} | {'Total':<5s} | {'Hit@1':<8s} | {'Hit@4':<8s} | {'Hit@8':<8s}")
    print("-" * 75)
    for cat, stats in category_results.items():
        tot = stats["total"]
        h1 = (stats["hit1"] / tot) * 100
        h4 = (stats["hit4"] / tot) * 100
        h8 = (stats["hit8"] / tot) * 100
        print(f"{cat:<32s} | {tot:<5d} | {h1:6.1f}%   | {h4:6.1f}%   | {h8:6.1f}%")

    print("\n--- 3. TOP-8 DISTANCES FOR 8 SPECIFIC TARGET QUERIES ---")
    target_queries = [
        "anticipatory bail",
        "punishment for murder",
        "cheating",
        "dowry death",
        "dishonoured cheque",
        "electronic evidence admissibility",
        "maintenance for wife",
        "bail by High Court"
    ]

    for tq in target_queries:
        res = coll.query(query_texts=[tq], n_results=8)
        print(f"\nTarget Query: '{tq}'")
        if res and res.get("documents"):
            for rank, (meta, dist) in enumerate(zip(res["metadatas"][0], res["distances"][0]), 1):
                act = meta.get("act_name", "Unknown")
                sec = meta.get("section_no", "")
                title = meta.get("title", "")
                print(f"  Rank {rank} [Dist: {dist:.4f}] {act} (Sec {sec}): {title[:60]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Statute Retrieval Benchmark")
    parser.add_argument("--eval-file", default="ai_engine/statute_eval.json", help="Path to evaluation dataset")
    parser.add_argument("--chroma-path", default="scratch/eval_chroma_db", help="Path to ChromaDB vector store")
    parser.add_argument("--collection", default="legal_knowledge_vault", help="Collection name")
    parser.add_argument("--label", default="NEW FORMAT STORE", help="Store label")
    args = parser.parse_args()

    run_evaluation(eval_path=args.eval_file, chroma_path=args.chroma_path, collection_name=args.collection, store_label=args.label)
