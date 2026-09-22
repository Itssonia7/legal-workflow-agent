from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from datetime import datetime
try:
    from state import AgentState
    from retrieve import search_legal_documents
except ImportError:
    from ai_engine.state import AgentState
    from ai_engine.retrieve import search_legal_documents

# Initialize the local AI 
llm = ChatOllama(model="llama3", temperature=0.0)

def research_agent(state: AgentState):
    print("\n[Researcher] Analyzing case prompt for dual-search...")
    user_prompt = state["user_prompt"]
    case_id = state.get("case_id")
    logs = state.get("step_logs", [])
    
    instruction = f"You are a legal assistant. Extract 3 core legal search terms from this prompt. Return ONLY the terms separated by commas: '{user_prompt}'"
    response = llm.invoke([HumanMessage(content=instruction)])
    search_terms = response.content
    print(f"[Researcher] Keywords extracted: {search_terms}")
    logs.append(f"Researcher extracted keywords: {search_terms}")
    
    # 1. Query Drawer A: Objective Statutes (The laws we just seeded)
    print("[Researcher] Querying Drawer A (Statutes)...")
    statute_results = search_legal_documents(search_terms, source_type="statute", k=6)
    statute_context = "\n\n".join(statute_results)
    
    # 2. Query Drawer B: Client Case Files
    print(f"[Researcher] Querying Drawer B (Case Files) for Case ID: {case_id}...")
    case_results = search_legal_documents(search_terms, source_type="case_file", case_id=case_id)
    case_context = "\n\n".join(case_results)
    
    # 3. Combine them cleanly with strict boundaries
    combined_context = (
        "--- LEGAL STATUTES (OBJECTIVE FACT) ---\n"
        f"{statute_context if statute_context else 'No statutory provisions found.'}\n\n"
        "--- CLIENT CASE FACTS (UPLOADED EVIDENCE) ---\n"
        f"{case_context if case_context else 'No case file facts uploaded yet.'}"
    )
    
    logs.append("Researcher successfully retrieved segregated laws and case facts.")
    return {"context_documents": combined_context, "step_logs": logs}


DOC_TYPE_SPECS = {
    "notice": {
        "name": "Legal Notice / Demand Notice",
        "register": "Adversarial Demand Notice register ('NOW THEREFORE TAKE NOTICE THAT I CALL UPON YOU TO FORTHWITH', 'Yours faithfully'). Do NOT use 'MOST RESPECTFULLY SHOWETH' or 'IN WITNESS WHEREOF' in a notice!",
        "sections": [
            "1. **ADVOCATE LETTERHEAD & DATE**:\nChambers of Adv. ____________________ [Advocate Name], Advocate, High Court / District Court\nOffice: [Office / Chambers Address], Phone: [Contact No.] | Email: [Email]\nDate: [Date]",
            "2. **MODE OF TRANSMISSION & NOTICEE PARTICULARS**:\nREGISTERED A.D. / SPEED POST\nNoticee: [Noticee Name]\nAddress: [Complete Postal Address with Pin Code]",
            "3. **SUBJECT LINE**:\nLEGAL NOTICE FOR [CLEAR REASON/GRIEVANCE] UNDER [STATUTORY PROVISIONS IDENTIFIED IN LEGAL FACTS]",
            "4. **AUTHORIZATION STATEMENT**:\nUNDER INSTRUCTIONS FROM AND ON BEHALF OF MY CLIENT, [Client Full Name], residing at [Client Address], I hereby serve upon you this Legal Notice:",
            "5. **STATEMENT OF FACTS & CAUSE OF ACTION**:\nDetailed chronological narration reflecting ALL relevant events, dates, transactions, and breaches directly from the provided Client Case Facts. Numbered 1, 2, 3, 4... without summarizing or omitting any factual detail.",
            "6. **LEGAL GROUNDS & STATUTORY CITATIONS**:\nDetailed statutory violations and legal grounds based strictly on the laws identified in the provided Legal Statutes.",
            "7. **DEMANDS, STATUTORY REMEDIES & NOTICE PERIOD**:\nClear articulation of the client's demands, required actions, and timeline for compliance based on the lawyer's instructions and facts. Explicitly mention consequences of non-compliance (civil/criminal proceedings).",
            "8. **ADVOCATE SIGNATURE & NOTICEE COPY**:\nYours faithfully,\n\n______________________\nAdv. ____________________ [Advocate Name]\nAdvocate for the Client\nEnrolment No.: [Bar Council Enrolment No. ________________]\n\nCOPY RETAINED FOR RECORD"
        ],
        "keywords": ["notice", "demand", "138", "cheque", "evict", "rent", "defamation", "cease and desist"]
    },
    "reply_notice": {
        "name": "Reply to Legal Notice",
        "register": "Rebuttal and Formal Denial register ('UNDER INSTRUCTIONS FROM MY CLIENT', 'PRELIMINARY OBJECTIONS', 'REPLY ON MERITS', 'Yours faithfully')",
        "sections": [
            "1. **ADVOCATE LETTERHEAD & DATE**:\nChambers of Adv. ____________________ [Advocate Name], Advocate\nOffice: [Office Address], Phone: [Phone] | Email: [Email]\nDate: [Date]",
            "2. **MODE OF TRANSMISSION & NOTICEE PARTICULARS**:\nREGISTERED A.D. / SPEED POST\nTo: [Sender Advocate Name], Advocate for [Complainant Name]\nAddress: [Office Address]",
            "3. **SUBJECT LINE**:\nREPLY ON BEHALF OF [CLIENT NAME] TO PURPORTED LEGAL NOTICE DATED [DATE]",
            "4. **AUTHORIZATION STATEMENT**:\nUNDER INSTRUCTIONS FROM AND ON BEHALF OF MY CLIENT, [Client Full Name], residing at [Client Address], I hereby reply to your notice as under:",
            "5. **PRELIMINARY OBJECTIONS**:\n1. That the notice under reply is false, frivolous, vexatious, and an abuse of the process of law.\n2. That there exists no valid cause of action against my client.",
            "6. **PARA-WISE REPLY ON MERITS**:\nDetailed paragraph-by-paragraph denial and factual rebuttal of the claims made.",
            "7. **DEMAND FOR WITHDRAWAL & CAUTION**:\nDemand unconditional withdrawal of the notice within 7 days, failing which legal proceedings for damages will be initiated.",
            "8. **ADVOCATE SIGNATURE & RECORD COPY**:\nYours faithfully,\n\n______________________\nAdv. ____________________ [Advocate Name]\nAdvocate for the Respondent\n\nCOPY RETAINED FOR RECORD"
        ],
        "keywords": ["reply", "rebuttal", "denial", "written reply", "reply to notice"]
    },
    "bail": {
        "name": "Court Pleading / Bail Application",
        "register": "Court Pleading register ('MOST RESPECTFULLY SHOWETH', 'WHEREFORE IT IS RESPECTFULLY PRAYED', 'VERIFICATION ON OATH')",
        "sections": [
            "1. **COURT JURISDICTION**:\nIN THE COURT OF SESSIONS JUDGE / HIGH COURT OF [STATE] AT [PLACE]",
            "2. **CAUSE TITLE & CASE NO.**:\nCRIMINAL MISC. (BAIL) APPLICATION NO. _____ OF 202___",
            "3. **MEMO OF PARTIES**:\n[Applicant Name], S/o [Father Name], R/o [Address] ... APPLICANT\nVERSUS\nSTATE (GOVT. OF [STATE]) ... RESPONDENT\nFIR No.: [FIR No.] | Dated: [Date] | Police Station: [Police Station] | Under Sections: [Statutory Sections]",
            "4. **DOCUMENT TITLE & STATUTORY INVOCATION**:\nAPPLICATION UNDER SECTION 439 OF BNSS, 2023 / SECTION 439 CR.P.C. FOR GRANT OF REGULAR BAIL ON BEHALF OF THE APPLICANT",
            "5. **FACTS OF THE CASE**:\nNumbered paragraphs 1, 2, 3... starting with 'MOST RESPECTFULLY SHOWETH:' setting out the facts.",
            "6. **GROUNDS & STATUTORY CITATIONS**:\nNumbered grounds A, B, C... citing statutory provisions and grounds for bail.",
            "7. **PRAYER**:\nWHEREFORE, it is most respectfully prayed that this Hon'ble Court may be pleased to grant regular bail to the applicant.",
            "8. **VERIFICATION & COUNSEL SIGNATURE**:\nVerification statement of truth under oath, Date, Place, and 'COUNSEL FOR APPLICANT: Adv. ____________________ [Advocate Name]'"
        ],
        "keywords": ["bail", "fir", "arrest", "custody", "anticipatory", "sessions"]
    },
    "petition": {
        "name": "Civil / Writ / General Petition",
        "register": "Formal Court Petition register ('MOST RESPECTFULLY SHOWETH', 'PRAYER')",
        "sections": [
            "1. **COURT JURISDICTION**:\nIN THE HON'BLE COURT OF [Jurisdiction/Court Name]",
            "2. **CAUSE TITLE**:\n[PETITION/SUIT/COMPLAINT TYPE] NO. _____ OF 202___",
            "3. **MEMO OF PARTIES**:\n[Petitioner Name] ... PETITIONER / PLAINTIFF\nVERSUS\n[Respondent Name] ... RESPONDENT / DEFENDANT",
            "4. **DOCUMENT TITLE & STATUTORY INVOCATION**:\n[Document Title e.g., PETITION UNDER SECTION...]",
            "5. **STATEMENT OF FACTS**:\nNumbered paragraphs detailing the chronological facts and cause of action.",
            "6. **LEGAL GROUNDS & STATUTORY CITATIONS**:\nDetailed statutory violations and legal grounds based strictly on the laws identified in the provided Legal Statutes.",
            "7. **PRAYER**:\nWHEREFORE, it is most respectfully prayed that this Hon'ble Court may be pleased to grant the requested relief.",
            "8. **VERIFICATION & COUNSEL SIGNATURE**:\nVerification statement of truth under oath, Date, Place, and 'COUNSEL FOR PETITIONER: Adv. ____________________ [Advocate Name]'"
        ],
        "keywords": ["petition", "writ", "plaint", "suit", "pleading", "complaint petition", "quash"]
    },
    "consumer": {
        "name": "Consumer Complaint / Statutory Grievance",
        "register": "Statutory Commission register ('BEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION', 'MOST RESPECTFULLY SHOWETH', 'PRAYER FOR RELIEF')",
        "sections": [
            "1. **COMMISSION JURISDICTION**:\nBEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION AT [DISTRICT]",
            "2. **COMPLAINT NO. & CAUSE TITLE**:\nCONSUMER COMPLAINT NO. _____ OF 202___",
            "3. **MEMO OF PARTIES**:\n[Complainant Name] ... COMPLAINANT\nVERSUS\n[Opposite Party / Company Name] ... OPPOSITE PARTY",
            "4. **COMPLAINT TITLE & STATUTORY INVOCATION**:\nCOMPLAINT UNDER SECTION 35 OF THE CONSUMER PROTECTION ACT, 2019 FOR DEFICIENCY IN SERVICE AND UNFAIR TRADE PRACTICE",
            "5. **STATEMENT OF FACTS & TRANSACTION**:\nNumbered paragraphs detailing transaction, consideration paid, and deficiency.",
            "6. **DEFICIENCY OF SERVICE & UNFAIR TRADE PRACTICE**:\nDetailed statutory grounds under the Consumer Protection Act, 2019.",
            "7. **PRAYER & COMPENSATION CLAIM**:\nPrayer for refund, replacement, damages, and litigation costs.",
            "8. **VERIFICATION & SIGNATURES**:\nVerification by Complainant and Counsel details: Adv. ____________________ [Advocate Name]."
        ],
        "keywords": ["consumer", "deficiency", "consumer court", "cpa", "unfair trade", "district commission"]
    },
    "affidavit": {
        "name": "Affidavit & Sworn Declaration",
        "register": "Sworn Notarial register ('BEFORE THE HON'BLE COURT / AUTHORITY', 'DEPONENT', 'VERIFIED AT ... NO MATERIAL FACT CONCEALED')",
        "sections": [
            "1. **COURT / AUTHORITY JURISDICTION**:\nBEFORE THE HON'BLE COURT / COMPETENT AUTHORITY AT [PLACE]",
            "2. **DOCUMENT TITLE (AFFIDAVIT)**:\nAFFIDAVIT OF [DEPONENT FULL NAME]",
            "3. **DEPONENT IDENTIFICATION & OATH**:\nI, [Deponent Name], S/o [Father Name], Aged about [Age] years, R/o [Address], do hereby solemnly affirm and state on oath as under:",
            "4. **STATEMENTS OF TRUTH & FACTS**:\nNumbered paragraphs 1, 2, 3... stating facts true to personal knowledge.",
            "5. **DEPONENT SIGNATURE**:\nDEPONENT:\n___________________________\n[Deponent Name]",
            "6. **VERIFICATION & ATTESTATION BLOCK**:\nVERIFICATION: Verified at [Place] on this [Date] that the contents of paragraphs 1 to ___ are true to my personal knowledge, no part is false, and nothing material has been concealed therefrom.\nDEPONENT\nIdentified by me: Adv. ____________________ [Advocate Name]"
        ],
        "keywords": ["affidavit", "sworn", "undertaking", "oath", "declaration"]
    },
    "contract": {
        "name": "Commercial Contract / Agreement",
        "register": "Bilateral Commercial Agreement register ('NOW THEREFORE IT IS MUTUALLY AGREED', 'IN WITNESS WHEREOF THE PARTIES HAVE SET THEIR HANDS')",
        "sections": [
            "1. **DOCUMENT TITLE**:\n[AGREEMENT TITLE - e.g. NON-DISCLOSURE AGREEMENT / COMMERCIAL AGREEMENT]",
            "2. **DATE AND PARTIES**:\nTHIS AGREEMENT is entered into on this [Date], by and between [Party 1] AND [Party 2]...",
            "3. **RECITALS ('WHEREAS')**:\nWHEREAS Party 1 is engaged in... AND WHEREAS Party 2 has agreed to...",
            "4. **OPERATIVE COVENANTS & CLAUSES**:\nNumbered clauses: 1. Definitions, 2. Scope & Obligations, 3. Term & Termination, 4. Governing Law & Jurisdiction",
            "5. **EXECUTION & WITNESS SIGNATURES**:\nIN WITNESS WHEREOF the Parties have executed this Agreement on the day and year first above written.\nFOR FIRST PARTY: ___________________________\nFOR SECOND PARTY: ___________________________\nWITNESSES: 1. ___________________________ 2. ___________________________"
        ],
        "keywords": ["agreement", "contract", "nda", "lease", "mou", "service agreement"]
    },
    "custom": {
        "name": "Custom Legal Document / Hybrid",
        "register": "Formal legal drafting register appropriate to the specific request.",
        "sections": [
            "1. **DOCUMENT TITLE**:\n[Appropriate Title based on user request]",
            "2. **STATEMENT OF FACTS & CAUSE OF ACTION**:\nDetailed chronological narration reflecting ALL relevant events directly from the provided Client Case Facts. Numbered 1, 2, 3...",
            "3. **LEGAL GROUNDS & RELIEF SOUGHT**:\nLegal arguments and specific relief/prayer requested.",
            "4. **ADVOCATE SIGNATURE**:\nYours faithfully,\n\n______________________\nAdv. ____________________ [Advocate Name]\nAdvocate for the Client\nEnrolment No.: [Bar Council Enrolment No. ________________]"
        ],
        "keywords": ["hybrid", "custom", "other"]
    }
}

def resolve_doc_type(doc_type: str, user_prompt: str) -> str:
    if doc_type and doc_type in DOC_TYPE_SPECS:
        return doc_type
    
    lower_prompt = (user_prompt or "").lower()

    if any(kw in lower_prompt for kw in ["reply to notice", "reply notice", "rebuttal", "written reply"]):
        return "reply_notice"
    if any(kw in lower_prompt for kw in ["consumer", "deficiency", "consumer court", "cpa"]):
        return "consumer"
    if any(kw in lower_prompt for kw in ["notice", "demand", "138", "cheque bounce", "cease and desist", "call upon"]):
        return "notice"
    if any(kw in lower_prompt for kw in ["bail", "fir", "arrest", "custody", "anticipatory", "sessions"]):
        return "bail"
    if any(kw in lower_prompt for kw in ["petition", "writ", "plaint", "suit", "pleading", "complaint petition", "quash"]):
        return "petition"
    if any(kw in lower_prompt for kw in ["affidavit", "sworn", "undertaking", "oath", "declaration", "deponent"]):
        return "affidavit"
    if any(kw in lower_prompt for kw in ["agreement", "contract", "nda", "lease", "mou", "service agreement"]):
        return "contract"

    if any(term in lower_prompt for term in ["to ", "against ", "send ", "serve ", "issue ", "draft a letter", "unauthorized"]):
        return "notice"

    return "custom"


def drafter_agent(state: AgentState):
    print("\n[Drafter] Generating legal document...")
    user_prompt = state["user_prompt"]
    context_documents = state["context_documents"]
    critic_feedback = state.get("critic_feedback", "")
    user_feedback = state.get("user_feedback", "")
    previous_draft = state.get("previous_draft", "")
    doc_type = resolve_doc_type(state.get("doc_type", "auto"), user_prompt)
    logs = state.get("step_logs", [])

    spec = DOC_TYPE_SPECS.get(doc_type, DOC_TYPE_SPECS["notice"])
    sections_str = "\n\n".join(spec["sections"])

    revision_context = ""
    if user_feedback:
        revision_context += f"""
    --- SUPREME DIRECTIVE: LAWYER'S REVISION INSTRUCTIONS (HUMAN-IN-THE-LOOP) ---
    The reviewing lawyer reviewed the earlier draft and submitted the following mandatory revisions:
    "{user_feedback}"

    Previous Draft for Reference:
    {previous_draft or state.get('current_draft', '')}

    PRIORITY RULE: The lawyer's revision instructions STRICTLY SUPERSEDE all default templates, standard placeholders, initial case prompts, and earlier draft content.
    You MUST adopt ALL modifications requested by the lawyer (including advocate name, contact details, dates, claim amounts, deadlines, and factual adjustments) verbatim.
    -----------------------------------------------------------------------------------
    """

    if critic_feedback:
        revision_context += f"""
    --- CRITIC AGENT VERIFICATION NOTES ---
    {critic_feedback}
    ---------------------------------------
    """

    prompt_text = f"""
    You are an expert Indian Legal Drafter. Your job is to draft a formal legal instrument based strictly on the user's request and provided legal facts.

    Target Document Standard: {spec['name']}
    Legal Register: {spec['register']}
    Current Date: {datetime.now().strftime('%B %d, %Y')}
    User Request: {user_prompt}
    Legal Facts & Precedents: {context_documents}
    {revision_context}

    You MUST structure your response with the following exact numbered markdown section headers:
    {sections_str}

    Strict Legal Drafting Requirements:
    1. ZERO PARENTHESES:
       - NEVER wrap paragraphs, lines, or blocks in parentheses '(' ')' or single/double quotes.
       - Output clean, readable legal text directly under each section header.
    2. NO PREAMBLE OR CONVERSATIONAL ACKNOWLEDGEMENT:
       - Do NOT output 'Here is the draft:', 'I will draft...', or any commentary.
       - Start immediately on Line 1 with the first section header.
    3. ADVOCATE IDENTITY & CONTACT INFORMATION:
       - If the lawyer explicitly specifies an Advocate name or contact details in the user request or revision instructions, use those EXACT details in the letterhead and signature blocks.
       - ONLY IF NO advocate name is provided by the lawyer, you MUST strictly use fillable blanks: 'Chambers of Adv. ____________________ [Advocate Name]' in the letterhead, and 'Adv. ____________________ [Advocate Name]' in the signature.
       - NEVER invent or assume an advocate name, and NEVER name the Advocate after the Client.
    4. UNIVERSAL FACTUAL COMPLETENESS:
       - Under STATEMENT OF FACTS & CAUSE OF ACTION, narrate all chronological facts, dates, entities, and incidents directly from the Client Case Facts. In paragraph 1, identify the client and residence.
    5. STATUTORY INTEGRITY & REMEDIES:
       - Cite exact statutory provisions provided in the Legal Statutes.
       - Extract exact damage amounts, specific actions (e.g., cease and desist), and deadlines directly from the Client Case Facts or Lawyer's Feedback. If no specific monetary amount is provided, demand compliance without inventing financial figures.
       - NEVER use placeholder phrases like 'as quantified in the case facts'.
    6. PRIVACY PROTECTION:
       - Use context to mask sensitive personal identifiers (like Aadhaar or PAN) with 'XXXX', but do NOT mask general reference numbers, bank accounts, or dates.
    7. DOCUMENT DATE:
       - You MUST use the Current Date provided above ({datetime.now().strftime('%B %d, %Y')}) for the document's letterhead date, unless the lawyer explicitly requests a different past/future date. Do NOT guess a random date based on case facts.
    """

    response = llm.invoke([HumanMessage(content=prompt_text)])
    raw_content = response.content.strip()

    # Programmatically strip leading conversational preamble lines if present
    import re
    cleaned_lines = raw_content.split('\n')
    while cleaned_lines and re.match(r'^(here is|here\'s|below is|certainly|sure|please find|as requested|i will draft|i will generate|i shall)', cleaned_lines[0].strip(), re.IGNORECASE):
        cleaned_lines.pop(0)
    final_draft = '\n'.join(cleaned_lines).strip()

    # Deterministic PII Redaction
    # Redact Aadhaar (12 digits, optional spaces)
    final_draft = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', 'XXXX XXXX XXXX', final_draft)
    # Redact PAN (5 letters, 4 digits, 1 letter)
    final_draft = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', 'XXXXX0000X', final_draft)

    print("[Drafter] Draft generated successfully.")
    
    new_count = state.get("revision_count", 0) + 1
    version_note = f"Drafter generated {spec['name']} (v{new_count})"
    if user_feedback:
        version_note += f" incorporating lawyer's revision feedback."
    logs.append(version_note)
    
    return {
        "current_draft": final_draft, 
        "revision_count": new_count,
        "doc_type": doc_type,
        "step_logs": logs
    }


def critic_agent(state: AgentState):
    print("\n[Critic] Evaluating the draft...")
    user_prompt = state["user_prompt"]
    current_draft = state["current_draft"]
    context_documents = state["context_documents"]
    doc_type = resolve_doc_type(state.get("doc_type", "auto"), user_prompt)
    spec = DOC_TYPE_SPECS.get(doc_type, DOC_TYPE_SPECS["notice"])
    logs = state.get("step_logs", [])

    prompt_text = f"""
    You are a Senior Legal Editor and Fact-Verifier. Your job is to rigorously review the drafted legal document against the original request and provided legal facts.

    Document Type Standard: {spec['name']}
    Legal Facts Provided: {context_documents}
    Drafted Document to Review: {current_draft}

    Evaluation Rules:
    1. Section Structure: Ensure the draft contains the standard section headers for {spec['name']}.
    2. No Parentheses Artifacts: Ensure paragraphs are NOT wrapped in parentheses '(' ')' or quotes '''.
    3. Advocate Identity Check: Ensure the Advocate is NOT named after the Client (e.g. Adv. Rajesh Kumar).
    4. Factual Completeness: Cross-reference against Client Case Facts. Ensure all material facts, dates, entities, and incidents mentioned in the case record are fully narrated.
    5. Four Pillars of Notice: If drafting a Notice, ensure it contains (1) Facts, (2) Legal Basis, (3) Demand with compliance deadline, and (4) Consequence.
    6. Statutory Accuracy: Verify that statutory citations match the Legal Facts Provided.

    Instructions:
    - If the document meets all rules, respond with ONLY the word: APPROVED
    - If the document fails any rule, respond with: REJECTED: <list concise, specific instructions telling the Drafter what to fix>
    """
    
    response = llm.invoke([HumanMessage(content=prompt_text)])
    evaluation = response.content.strip()

    if evaluation.startswith("APPROVED"):
        print("[Critic] Draft verified and approved.")
        logs.append(f"Critic verified facts & structure for {spec['name']} and approved the document.")
        return {"is_approved": True, "critic_feedback": "", "step_logs": logs}
    else:
        print(f"[Critic] Draft rejected. Feedback: {evaluation}")
        logs.append("Critic found incomplete facts or formatting issues. Sending back to Drafter for revision.")
        return {"is_approved": False, "critic_feedback": evaluation, "step_logs": logs}


# --- Quick Local Test ---
if __name__ == "__main__":
    test_state = AgentState(
        user_prompt="Draft a bail application for a client accused of theft.",
        context_documents="Section 379 IPC relates to punishment for theft. The punishment is imprisonment for a term which may extend to three years, or with fine, or with both. It is a cognizable and non-bailable offense.",
        current_draft="",
        critic_feedback="",
        revision_count=0,
        is_approved=False,
        step_logs=[]  # Initializing the empty list here for the test
    )
    
    print("\n--- Testing Drafter ---")
    draft_update = drafter_agent(test_state)
    test_state.update(draft_update)
    
    print("\n--- Testing Critic ---")
    critic_update = critic_agent(test_state)
    test_state.update(critic_update)
    
    print(f"\n--- Final Status ---")
    print(f"Approved: {test_state['is_approved']}")
    print("\n--- Frontend UI Logs ---")
    for log in test_state['step_logs']:
        print(f" -> {log}")