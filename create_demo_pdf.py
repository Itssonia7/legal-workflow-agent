import fitz

def create_pdf():
    # Create a new document
    doc = fitz.open()
    
    # Create a new A4 page
    page = doc.new_page()
    
    # Define text content
    text = (
        "LEGAL CASE STATEMENT OF FACTS\n"
        "CASE REFERENCE: LWA/2026/RK-09\n\n"
        "CLIENT PROFILE:\n"
        "Name: Rajesh Kumar\n"
        "Address: Flat 405, Green Glen Layout, Bangalore, Karnataka - 560103\n"
        "Card Reference: Aadhaar Card ID 1234-5678-9012\n\n"
        "STATEMENT OF INCIDENT:\n"
        "1. The client, Rajesh Kumar, is a resident of India and a registered holder of Aadhaar card number 1234-5678-9012.\n"
        "2. On June 12th, 2026, the client engaged the services of \"SecureAuth Verification Services\" (the Respondent) solely for the purpose of biometric identity verification required for a new mobile SIM card registration.\n"
        "3. During this process, the client's core biometric information, specifically his fingerprints and iris scans, were collected by the Respondent.\n"
        "4. On July 10th, 2026, the client discovered that his core biometric information and identity details had been unauthorizedly shared and transferred by the Respondent to a third-party private marketing entity named \"Apex Data Systems\".\n"
        "5. The sharing of this sensitive personal data was carried out without the consent or knowledge of the client, violating the trust and terms under which the data was collected.\n"
        "6. The client is seeking legal remedy against SecureAuth Verification Services for the unauthorized sharing of biometric data in violation of Section 29 and Section 30 of the Aadhaar (Targeted Delivery of Financial and other Subsidies, Benefits and Services) Act, 2016."
    )
    
    # Define insertion rectangle (margins: 50pt left/right/top/bottom)
    rect = fitz.Rect(50, 50, 545, 792)
    
    # Insert text box with comfortable size and font
    page.insert_textbox(rect, text, fontsize=11, fontname="Helvetica")
    
    # Save the document
    output_filename = "aadhaar_violation_facts.pdf"
    doc.save(output_filename)
    doc.close()
    print(f"Successfully generated demo PDF: {output_filename}")

if __name__ == "__main__":
    create_pdf()
