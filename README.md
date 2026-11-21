# UST Bannu Voice-RAG Pipeline

A production-grade, voice-optimized Web Scraping and Retrieval-Augmented Generation (RAG) system for the **University of Science and Technology Bannu (USTB)**, built on **Pinecone Namespaces**.

Designed as the factual brain for an autonomous voice admissions advisor.

---

## 1. Architecture: Multi-Namespace Vector Store

Rather than pooling all university data into one generic vector index, data is strictly isolated into **4 dedicated Pinecone Namespaces** under the `ustb-voice-kb` index:

```
Pinecone Index: "ustb-voice-kb"
 │
 ├── Namespace: "admissions"
 │    └── Eligibility criteria, ETEA / Entry tests, quotas, merit calculation, deadlines
 │
 ├── Namespace: "fees"
 │    └── Tuition fees per semester, admission dues, challan submission (HBL/NBP), hostel dues
 │
 ├── Namespace: "programs-classes"
 │    └── Degrees offered (BS, MS, PhD), departments, duration, morning vs. evening shifts
 │
 └── Namespace: "campus-admin"
      └── Main campus location (Admin Block), admission office landlines, hostel facilities, buses
```

### Why Namespaces for Voice Agents?
1. **Zero Cross-Domain Hallucinations:** A question about class timings will never accidentally pull fee figures.
2. **Sub-20ms Retrieval:** Searching small, domain-specific namespaces yields high semantic precision with near-zero latency.
3. **TTS Normalization:** Raw currency symbols (`Rs. 45,000/-`) are converted into natural spoken phrasing (`45,000 Pakistani Rupees`) to ensure crisp Text-to-Speech pronunciation.

---

## 2. Directory Layout

```text
ustb-voice-agent/
├── config/
│   ├── constants.py            # Target URLs, namespace names, acronym dictionary
│   └── settings.py             # Loads .env, Pinecone API keys & embedding setup
├── data/
│   ├── raw/                    # Downloaded HTML pages & PDF circulars
│   └── processed/              # Voice-normalized JSON datasets partitioned by namespace
├── src/
│   ├── scraper/                # Web crawler and PDF downloader
│   ├── parsers/                # HTML parser & PDF table extractor
│   ├── processing/             # Voice normalizer, text cleaner, and atomic chunker
│   ├── rag/                    # Pinecone manager, multi-provider embedder, indexer, retriever
│   └── common/                 # Pydantic schemas, logging, file utilities
├── scripts/
│   ├── 01_run_scraper.py       # Scrapes ustb.edu.pk and downloads PDFs
│   ├── 02_process_and_clean.py # Generates clean, voice-normalized chunks
│   ├── 03_build_pinecone_index.py # Embeds & upserts chunks into Pinecone namespaces
│   └── 04_test_retrieval.py    # Automated & interactive query latency tester
└── tests/                      # Pytest unit tests for all components
```

---

## 3. Quickstart & Usage

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
Ensure your `.env` file contains your Pinecone credentials:
```env
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=ustb-voice-kb
```

*(Note: The system automatically detects your Pinecone index dimension. If dimension is 384, it uses the local, free `all-MiniLM-L6-v2`. If 1536, it uses `text-embedding-3-small` with your OpenAI key).*

### Step 3: Scrape UST Bannu Website & PDFs
```bash
python scripts/01_run_scraper.py
```
*Saves raw HTML into `data/raw/html/` and fee/prospectus PDFs into `data/raw/pdfs/`.*

### Step 4: Process, Clean & Normalize for Voice
```bash
python scripts/02_process_and_clean.py
```
*Outputs 4 clean JSON files in `data/processed/` (`admissions.json`, `fees.json`, `programs_classes.json`, `campus_admin.json`).*

### Step 5: Upsert Vectors into Pinecone Namespaces
```bash
python scripts/03_build_pinecone_index.py
```
*Embeds all records and uploads them directly into the 4 namespaces inside your `ustb-voice-kb` index.*

### Step 6: Test Retrieval & Latency
Run the automated test suite:
```bash
python scripts/04_test_retrieval.py
```
Or start an interactive terminal session:
```bash
python scripts/04_test_retrieval.py --interactive
```

---

## 4. Running Unit Tests
```bash
pytest tests/
```
