# Data Management and Sharing Plan
## NSF CISE CORE (IIS) — CopernicusAI Knowledge Engine

**Principal Investigator:** Gary Welz | **Project Period:** 36 months | **Page Limit:** 2 pages maximum

---

## 1. Data Types Generated

**Research Data:** Structured metadata objects (JSON for papers, videos, briefings, diagrams, audio); cross-modal linking data; evaluation metrics (user study data, usability metrics); collaborative validation data; system performance data (grounding rates, citation integrity); algorithmic evaluation data.

**Software/Code:** Metadata schema definitions, cross-modal linking algorithms, reliability mechanisms (multi-checker workflows, citation verification), evaluation frameworks, API integrations. All under version control (Git/GitHub).

**Documentation:** Technical documentation (architecture, API, deployment); evaluation reports; user guides; research publications and presentations.

**User Study Data:** Anonymized usage analytics, survey/interview data, task-based evaluation data, collaborative validation patterns. All anonymized before analysis; no PII stored without consent.

---

## 2. Data Standards and Formats

**Metadata:** JSON Schema for structured objects; DOI/arXiv IDs for papers; Mermaid for process diagrams; standard transcript and audio formats.

**Code:** Git/GitHub; inline documentation and README; unit and integration tests; MIT License for open-source components.

**Data Formats:** JSON (metadata), CSV (evaluation metrics); Python/TypeScript/JavaScript (code); Markdown/PDF (documentation).

---

## 3. Data Storage and Preservation

**Storage:** Google Cloud Storage (GCS) for structured data, media, and datasets; Firestore for metadata and relationships; GitHub for code. Automated backups to GCS with versioning.

**Preservation:** Deliverables preserved in GCS; code in GitHub with public access for open-source components; documentation in repositories and separate systems; anonymized evaluation and user study data preserved for future research.

**Retention:** Research data retained at least 3 years post-project (NSF requirement). Code maintained in active repositories. User study data: anonymized data retained 3 years post-project; raw data destroyed after anonymization.

---

## 4. Data Sharing and Access

**Open Source (MIT License):** Metadata schemas, cross-modal linking algorithms, process visualization tools, evaluation frameworks, API specifications. Public access via GitHub (https://github.com/garywelz/copernicusai-research) and Hugging Face Spaces.

**Publicly Accessible:** Enhanced CopernicusAI platform, technical documentation, user guides, anonymized evaluation datasets. Publications via arXiv and institutional repositories.

**Timeline:** Incremental sharing during project; core open-source release by Year 2; full documentation and evaluation reports within 6 months of project completion; ongoing repository updates.

**Controlled Access:** Production systems and APIs with authentication and rate limiting. Anonymized user study data available upon request for research purposes.

---

## 5. Privacy and Security

**Privacy:** All user data anonymized before analysis; no PII without explicit consent; informed consent for user studies; compliance with GDPR (international) and FERPA (educational data where applicable).

**Security:** Role-based access control; encryption at rest and in transit (HTTPS/TLS); secure authentication; continuous monitoring; standard anonymization for user study data.

**IRB:** All human subjects research compliant with IRB requirements; secure storage and transmission; access limited to authorized research team.

---

## 6. Responsibilities and Compliance

**PI (Gary Welz):** Overall responsibility for data management and sharing; compliance with NSF policy; data quality and integrity; coordination of sharing and preservation.

**NSF Compliance:** Practices align with NSF data management and sharing policy. Annual and final reports will document data management activities, data generated and shared, and publication of results. Resources (GCP budgeted ~$78K over 3 years, GitHub, documentation systems) are adequate for these requirements.

---

**Prepared by:** Gary Welz, PI | **Date:** December 2025
