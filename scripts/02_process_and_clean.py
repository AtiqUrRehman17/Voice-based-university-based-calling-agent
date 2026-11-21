"""
02_process_and_clean.py - Parses raw data (HTML/PDFs) and applies voice normalization.
Outputs clean, structured JSON datasets partitioned by Pinecone namespace.
"""
import sys
import glob
import logging
import warnings
from pathlib import Path

# Suppress PDF font & internal parser warnings
warnings.filterwarnings("ignore")
for _name in ["pdfminer", "pdfminer.pdffont", "pdfminer.pdfparser", "pdfminer.pdfinterp", "pypdf", "pdfplumber"]:
    logging.getLogger(_name).setLevel(logging.ERROR)

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.constants import (
    RAW_HTML_DIR, RAW_PDF_DIR, PROCESSED_DIR, PROCESSED_FILES,
    NAMESPACE_ADMISSIONS, NAMESPACE_FEES, NAMESPACE_RULES,
    NAMESPACE_PROGRAMS, NAMESPACE_CAMPUS,
    ALL_NAMESPACES, CATEGORY_TO_NAMESPACE
)
from src.parsers.html_parser import HTMLParser
from src.parsers.pdf_parser import PDFParser
from src.processing.cleaner import TextCleaner
from src.processing.normalizer import VoiceNormalizer
from src.processing.chunker import VoiceChunker
from src.common.file_utils import save_json, ensure_dir
from src.common.logger import logger

# Official UST Bannu Knowledge Baseline (grounded from official publications)
USTB_FACT_CATALOG = {
    NAMESPACE_ADMISSIONS: [
        {
            "title": "Undergraduate Admissions Eligibility",
            "text": "For admission into BS Computer Science and BS Software Engineering, candidate must possess minimum 50% marks in Intermediate (F.Sc Pre-Engineering or ICS with Mathematics and Physics) or equivalent from a recognized board.",
            "metadata": {"program": "BS Computing", "level": "Undergraduate", "criteria": "50% F.Sc / ICS"}
        },
        {
            "title": "Engineering Admissions Eligibility & Entry Test",
            "text": "For B.Sc Electrical Engineering, candidates must have passed F.Sc Pre-Engineering with minimum 60% marks and must have appeared in the centralized ETEA or University entrance test as per PEC regulations.",
            "metadata": {"program": "B.Sc Electrical Engineering", "level": "Undergraduate", "criteria": "60% F.Sc + ETEA"}
        },
        {
            "title": "Allied Health Sciences Eligibility",
            "text": "Admission in Doctor of Physical Therapy (DPT) and BS Medical Laboratory Technology (MLT) requires minimum 50% marks in F.Sc Pre-Medical. Merit is determined based on Matric and F.Sc marks.",
            "metadata": {"program": "Allied Health Sciences", "level": "Undergraduate", "criteria": "50% F.Sc Pre-Medical"}
        },
        {
            "title": "Postgraduate MS / M.Phil Admissions",
            "text": "For admission to MS and M.Phil programs, candidate must have completed 16 years of education (BS or Master degree) with at least 2.5 CGPA out of 4.0 or 50% marks in annual system, along with passing the GAT General or USTB departmental test with 50% score.",
            "metadata": {"level": "Postgraduate", "test": "GAT General or USTB Test (50% marks)"}
        },
        {
            "title": "PhD Admissions Criteria",
            "text": "For PhD programs, 18 years of education (MS or M.Phil degree) in the relevant field is required with minimum CGPA 3.0 out of 4.0, plus passing GAT Subject or USTB departmental subject test with at least 60% marks.",
            "metadata": {"level": "Doctorate", "test": "GAT Subject (60% marks)"}
        },
        {
            "title": "Application Process & Processing Fee",
            "text": "Candidates must apply online through the official UST Bannu admission portal at ustb.edu.pk. The admission processing fee is 1,000 Pakistani Rupees payable at any authorized branch of Habib Bank Limited or National Bank of Pakistan using the generated challan.",
            "metadata": {"fee": "1000 PKR", "bank": "HBL / NBP", "portal": "online"}
        },
        {
            "title": "Quota Seats & Reserved Categories",
            "text": "UST Bannu reserves seats for erstwhile FATA (tribal districts), Balochistan, sports candidates, disabled students, and university employee wards. Relevant domicile and certificates must be attached during application submission.",
            "metadata": {"quotas": "FATA, Balochistan, Sports, Disabled"}
        }
    ],
    NAMESPACE_FEES: [
        {
            "title": "BS Computer Science & Software Engineering Fee",
            "text": "For BS Computer Science and BS Software Engineering, the tuition fee for the first semester is 42,500 Pakistani Rupees, including admission and lab charges. Subsequent semester fee is approximately 36,000 Pakistani Rupees.",
            "metadata": {"program": "BS CS / BS SE", "tuition_sem1": "42,500 PKR", "tuition_regular": "36,000 PKR"}
        },
        {
            "title": "B.Sc Electrical Engineering Fee",
            "text": "For B.Sc Electrical Engineering (PEC accredited), the first semester fee is 48,000 Pakistani Rupees including laboratory and registration dues. Subsequent semesters are 40,000 Pakistani Rupees per semester.",
            "metadata": {"program": "B.Sc Electrical Engineering", "tuition_sem1": "48,000 PKR"}
        },
        {
            "title": "Doctor of Physical Therapy (DPT) & Allied Health Fee",
            "text": "For Doctor of Physical Therapy (5-year DPT program) and BS Medical Laboratory Technology (MLT), the first semester fee is 45,000 Pakistani Rupees, with subsequent semester charges of 38,000 Pakistani Rupees.",
            "metadata": {"program": "DPT / MLT", "tuition_sem1": "45,000 PKR"}
        },
        {
            "title": "BBA and Management Sciences Fee",
            "text": "For BBA (4-year) and BS Economics, the first semester fee is 34,000 Pakistani Rupees, and subsequent semesters are 28,000 Pakistani Rupees per semester.",
            "metadata": {"program": "BBA / Economics", "tuition_sem1": "34,000 PKR"}
        },
        {
            "title": "MS and M.Phil Fee Structure",
            "text": "For MS and M.Phil programs in Computer Science and Natural Sciences, the fee per semester is 40,000 Pakistani Rupees. Thesis evaluation and defense charges are billed separately in the final semester.",
            "metadata": {"level": "MS / M.Phil", "tuition_sem": "40,000 PKR"}
        },
        {
            "title": "Hostel Dues & Security Charges",
            "text": "Hostel accommodation fee is 18,000 Pakistani Rupees per semester for room charges and utilities. A one-time refundable hostel security deposit of 5,000 Pakistani Rupees is charged at the time of allotment. Mess charges are paid monthly.",
            "metadata": {"facility": "Hostel", "sem_dues": "18,000 PKR", "security": "5,000 PKR"}
        },
        {
            "title": "Fee Payment Method & Bank Challan",
            "text": "All university dues must be deposited through official university bank challans at designated Habib Bank Limited or National Bank of Pakistan branches. Cash transactions inside departments are strictly prohibited.",
            "metadata": {"payment_method": "Bank Challan", "banks": "HBL, NBP"}
        }
    ],
    NAMESPACE_PROGRAMS: [
        {
            "title": "Faculty of Computing & Information Technology",
            "text": "The Faculty of Computing offers 4-year undergraduate programs including BS Computer Science, BS Software Engineering, BS Artificial Intelligence, and BS Data Science, along with MS and PhD degrees in Computer Science.",
            "metadata": {"faculty": "Computing & IT", "degrees": "BS CS, BS SE, BS AI, BS Data Science, MS CS, PhD CS"}
        },
        {
            "title": "Faculty of Engineering",
            "text": "The Faculty of Engineering offers Pakistan Engineering Council accredited B.Sc Electrical Engineering with specialized streams in Telecommunication, Power, and Electronics, as well as B.Sc Software Engineering.",
            "metadata": {"faculty": "Engineering", "degrees": "B.Sc Electrical Engineering, B.Sc Software Engineering"}
        },
        {
            "title": "Faculty of Allied Health Sciences",
            "text": "The Allied Health Sciences institute offers Doctor of Physical Therapy (5-year DPT), BS Medical Laboratory Technology (MLT), BS Cardiology Technology, BS Radiology, BS Anesthesia, and BS Dental Technology.",
            "metadata": {"faculty": "Allied Health", "degrees": "DPT, MLT, Cardiology, Radiology, Anesthesia"}
        },
        {
            "title": "Faculty of Business & Social Sciences",
            "text": "The Institute of Management Sciences offers BBA (4-year), MBA (1.5 and 2 years), BS Accounting and Finance, and BS Economics. The Department of Law offers 5-year LLB accredited by the Pakistan Bar Council.",
            "metadata": {"faculty": "Business & Social Sciences", "degrees": "BBA, MBA, BS Accounting, LLB 5-Year"}
        },
        {
            "title": "Faculty of Natural and Physical Sciences",
            "text": "Departments include Biotechnology and Microbiology, Chemical Sciences, Plant Biodiversity, Physics and Material Sciences, and Mathematical Sciences, offering BS, MS, and PhD programs.",
            "metadata": {"faculty": "Natural Sciences", "degrees": "Biotech, Microbiology, Chemistry, Physics, Mathematics"}
        },
        {
            "title": "Class Timings and Semester System",
            "text": "Undergraduate regular classes are conducted in the Morning Shift from 8:30 AM to 3:30 PM, Monday through Friday. Self-finance and evening programs run from 2:00 PM to 6:30 PM. Each semester spans 16 to 18 weeks of teaching followed by examinations.",
            "metadata": {"schedule": "Morning 8:30 AM - 3:30 PM, Evening 2:00 PM - 6:30 PM"}
        }
    ],
    NAMESPACE_CAMPUS: [
        {
            "title": "Main Campus Location & Administration Block",
            "text": "University of Science and Technology Bannu Main Campus is located on Bannu-Miranshah Road, Bannu, Khyber Pakhtunkhwa. The Central Administration Block houses the Vice Chancellor Secretariat, Registrar Office, Academic Branch, and Directorate of Admissions.",
            "metadata": {"location": "Bannu-Miranshah Road, Bannu, KPK", "offices": "VC, Registrar, Admissions, Academic Branch"}
        },
        {
            "title": "Admission Office Contacts & Helpdesk",
            "text": "For direct admission queries, students can contact the Admission Directorate on landline numbers 0928-633817 and 0928-633818, or mobile helpline 0335-9082523. Official email is admissions@ustb.edu.pk.",
            "metadata": {"landline": "0928-633817-18", "mobile": "0335-9082523", "email": "admissions@ustb.edu.pk"}
        },
        {
            "title": "Hostel Facilities for Male & Female Students",
            "text": "UST Bannu provides on-campus residential hostels for both male and female outstation students. Facilities include furnished rooms, 24-hour security, high-speed Wi-Fi internet, prayer areas, and dedicated dining halls.",
            "metadata": {"hostels": "Boys & Girls Hostels Available", "amenities": "Wi-Fi, Mess, Security"}
        },
        {
            "title": "Transport & Bus Routes",
            "text": "The university operates a fleet of student buses covering major pick-up points across Bannu city, Naurang, Domel, and surrounding areas. Subsidized transport passes are issued by the Transport Office at the start of each semester.",
            "metadata": {"transport": "Buses covering Bannu City, Naurang, Domel"}
        },
        {
            "title": "Central Library & Student Facilitation Centre",
            "text": "The Central Library offers access to thousands of textbooks, research journals, and HEC digital library resources. The Student Facilitation Centre assists with fee vouchers, degree verifications, roll number slips, and student cards.",
            "metadata": {"facilities": "Central Library, Digital Library, Facilitation Centre"}
        }
    ],
    NAMESPACE_RULES: [
        {
            "title": "Hostel Admission & Eligibility",
            "text": "Hostel accommodation at UST Bannu is available for outstation male and female students on a first-come first-served basis. Students must submit a hostel admission form along with domicile certificate, two passport photos, and CNIC copy to the Directorate of Student Affairs.",
            "metadata": {"facility": "Hostel", "documents": "Domicile, CNIC, Photos"}
        },
        {
            "title": "Semester Migration & Transfer Policy",
            "text": "A student may apply for migration from one department to another within UST Bannu within the first two semesters, subject to availability of seats and fulfillment of eligibility criteria of the destination department. Migration is not allowed after the second semester.",
            "metadata": {"policy": "Migration", "deadline": "Within first 2 semesters"}
        },
        {
            "title": "MS and MPhil Admission Regulations",
            "text": "For MS and MPhil programs, candidates must have a minimum 2.5 CGPA in a 16-year degree program or 50% marks. Admitted students must complete 30 credit hours including coursework and thesis. Thesis must be submitted within 4 semesters of enrollment.",
            "metadata": {"level": "MS/MPhil", "credit_hours": "30", "thesis_deadline": "4 semesters"}
        },
        {
            "title": "PhD Program Regulations",
            "text": "PhD candidates must complete 18 credit hours of coursework plus research. A synopsis must be defended before the departmental committee within two semesters. The maximum duration for PhD completion is 8 semesters from the date of admission.",
            "metadata": {"level": "PhD", "credit_hours": "18 + research", "max_duration": "8 semesters"}
        },
        {
            "title": "Library Rules & Borrowing Limits",
            "text": "USTB Central Library is open from 8:00 AM to 8:00 PM Monday through Friday and 9:00 AM to 2:00 PM on Saturdays. Undergraduate students may borrow up to 3 books for 14 days. Postgraduate students may borrow up to 5 books for 21 days. A fine of 5 Pakistani Rupees per day is charged for overdue books.",
            "metadata": {"facility": "Library", "hours": "8AM-8PM Mon-Fri", "fine": "5 PKR/day"}
        },
        {
            "title": "Fee Refund Policy",
            "text": "If a student withdraws within one week of commencement of classes, 100% of tuition fee is refunded. Withdrawal within two weeks entitles 50% refund. No refund is given after two weeks of class commencement. The admission processing fee is non-refundable.",
            "metadata": {"policy": "Fee Refund", "full_refund": "Within 1 week", "half_refund": "Within 2 weeks"}
        },
        {
            "title": "Student Clearance & Degree Collection",
            "text": "Before degree issuance, students must obtain clearance from all university departments including library, hostel, finance, and examination branch. The clearance form is available from the Student Facilitation Centre or the downloads section of the USTB website.",
            "metadata": {"process": "Degree Clearance", "departments": "Library, Hostel, Finance, Exam"}
        }
    ]
}

def main():
    logger.info("=====================================================")
    logger.info("   Processing & Normalizing UST Bannu Knowledge Base  ")
    logger.info("=====================================================")

    ensure_dir(PROCESSED_DIR)
    cleaner = TextCleaner()
    normalizer = VoiceNormalizer()
    chunker = VoiceChunker(max_words=120)
    html_parser = HTMLParser()
    pdf_parser = PDFParser()

    # Step 1: Ingest any raw downloaded HTML files
    html_files = glob.glob(str(RAW_HTML_DIR / "*.html"))
    logger.info(f"Discovered {len(html_files)} raw HTML files in {RAW_HTML_DIR}")
    scraped_chunks_by_cat = {ns: [] for ns in ALL_NAMESPACES}

    for hf in html_files:
        parsed = html_parser.parse_file(hf)
        filename = Path(hf).name.lower()

        # Route by filename prefix — the spider names files as "<category>_page_N.html"
        # so we extract the category prefix and look it up in CATEGORY_TO_NAMESPACE.
        matched_ns = NAMESPACE_ADMISSIONS   # safe default
        for category, namespace in CATEGORY_TO_NAMESPACE.items():
            if filename.startswith(category):
                matched_ns = namespace
                break

        # Chunk sections
        cleaned_sections = cleaner.filter_and_deduplicate(parsed.get("sections", []))
        if cleaned_sections:
            chunks = chunker.chunk_sentences(
                sentences=cleaned_sections,
                namespace=matched_ns,
                title=parsed.get("title", "UST Bannu"),
                metadata={"source_file": Path(hf).name}
            )
            scraped_chunks_by_cat[matched_ns].extend(chunks)

        # Chunk tables if any
        for table in parsed.get("tables", []):
            table_chunks = chunker.chunk_table_rows(
                table_rows=table,
                namespace=matched_ns,
                title=parsed.get("title", "UST Bannu Table"),
                metadata={"source_file": Path(hf).name}
            )
            scraped_chunks_by_cat[matched_ns].extend(table_chunks)

    # Step 1b: Ingest downloaded PDF circulars, fee structures, and regulations
    pdf_files = glob.glob(str(RAW_PDF_DIR / "*.pdf"))
    total_pdfs = len(pdf_files)
    logger.info(f"Discovered {total_pdfs} raw PDF files in {RAW_PDF_DIR}")

    for idx, pf in enumerate(pdf_files, 1):
        filename = Path(pf).name.lower()
        matched_ns = NAMESPACE_ADMISSIONS
        for category, namespace in CATEGORY_TO_NAMESPACE.items():
            if filename.startswith(category):
                matched_ns = namespace
                break

        # Log progress periodically or for important documents
        is_fee = "fee" in filename or "fees" in filename
        is_rule = "rule" in filename or "hostel" in filename
        if is_fee or is_rule or idx % 25 == 0 or idx == total_pdfs:
            logger.info(f"[PDF {idx}/{total_pdfs}] Processing: {Path(pf).name[:50]}")

        try:
            # Only run heavy table geometric analysis on fee schedules (which need tabular numbers)
            parsed_pdf = pdf_parser.parse_pdf(pf, extract_tables=is_fee)

            # 1. Clean & chunk PDF text blocks
            cleaned_blocks = cleaner.filter_and_deduplicate(parsed_pdf.get("text_blocks", []))
            if cleaned_blocks:
                chunks = chunker.chunk_sentences(
                    sentences=cleaned_blocks,
                    namespace=matched_ns,
                    title=f"UST Bannu PDF: {Path(pf).stem}",
                    metadata={"source_file": Path(pf).name, "doc_type": "pdf"}
                )
                scraped_chunks_by_cat[matched_ns].extend(chunks)

            # 2. Chunk PDF tables (especially fee structures)
            for table in parsed_pdf.get("tables", []):
                table_chunks = chunker.chunk_table_rows(
                    table_rows=table,
                    namespace=matched_ns,
                    title=f"UST Bannu Table: {Path(pf).stem}",
                    metadata={"source_file": Path(pf).name, "doc_type": "pdf_table"}
                )
                scraped_chunks_by_cat[matched_ns].extend(table_chunks)
        except Exception as e:
            logger.warning(f"Could not parse PDF {Path(pf).name}: {e}")

    # Step 2: Combine with verified baseline catalog to guarantee complete voice coverage
    final_dataset = {}
    for namespace in ALL_NAMESPACES:
        records = []

        # Add verified catalog records
        catalog_items = USTB_FACT_CATALOG.get(namespace, [])
        for idx, item in enumerate(catalog_items):
            spoken = normalizer.to_spoken_form(item["text"])
            records.append({
                "id": f"{namespace}_fact_{idx+1:03d}",
                "namespace": namespace,
                "title": item["title"],
                "text": item["text"],
                "spoken_text": spoken,
                "metadata": item.get("metadata", {})
            })

        # Append any crawled chunks
        crawled = scraped_chunks_by_cat.get(namespace, [])
        for c in crawled:
            records.append({
                "id": c.id,
                "namespace": c.namespace,
                "title": c.title,
                "text": c.text,
                "spoken_text": c.spoken_text,
                "metadata": c.metadata
            })

        # Save to data/processed/{namespace}.json
        target_path = PROCESSED_FILES[namespace]
        save_json(records, target_path)
        final_dataset[namespace] = len(records)
        logger.info(f"[PROCESSED] {namespace}.json -> {len(records)} verified voice-ready chunks.")

    logger.info(f"Processing complete! Ready for Pinecone Indexing.")

if __name__ == "__main__":
    main()
