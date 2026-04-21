JD_PROMPT = """
You are an expert ATS system analyzing Job Descriptions.

IMPORTANT:
- Return ONLY valid JSON
- No explanation
- No markdown
- No extra text
- Response MUST start with '{' and end with '}'

Return STRICT JSON:
{
  "title": "",
  "primary_skills": [],
  "good_to_have": [],
  "must_have_keywords": [],
  "experience_min_years": 0,
  "experience_max_years": 0,
  "location": "",
  "employment_type": "",
  "seniority_level": ""
}
RULES
TITLE:
- Extract exact job title from JD
SKILLS EXTRACTION RULES
GENERAL RULE:
- Extract skills ONLY from job description content
- Remove duplicates
- Exclude soft skills (communication, teamwork, leadership, etc.)
- Normalize skill names (e.g., AWS EC2 → AWS, RESTful services → REST API)

STRICT CLASSIFICATION RULE (MOST IMPORTANT)
- Each skill MUST belong to ONLY ONE category:
  either PRIMARY or GOOD_TO_HAVE (never both)

- PRIMARY SKILLS (MUST HAVE):
  - Skills explicitly marked as "Must have", "Required", "Mandatory"
  - Core technical skills required for job execution
  - Skills essential for day-to-day development or system design

- GOOD TO HAVE:
  - Skills explicitly marked as "Preferred", "Nice to have", "Plus"
  - Optional, secondary, or supporting technologies
  - Example: WebSocket, log4j2, Basic UI Knowledge, testing tools, monitoring tools

STRICT SECTION BOUNDARY RULE
- If JD contains clearly labeled sections:
    - "Must have" → PRIMARY
    - "Good to have" → GOOD_TO_HAVE

- If sections are unclear or mixed:
    - Use ONLY explicit keywords ("must", "required", "preferred")
    - Do NOT guess based on formatting, alignment, or position
ANTI-ASSUMPTION RULE (CRITICAL)
- Do NOT infer skill importance from proximity in text
- Do NOT assign category based on row alignment or formatting
- Do NOT upgrade GOOD_TO_HAVE to PRIMARY unless explicitly stated
- Do NOT hallucinate skills or restructure meaning
MUST HAVE KEYWORDS
- Extract only core architectural/technical concepts:
  API Development, Microservices, Cloud, Agile, System Design

EXPERIENCE RULES
- "2-4 years" → min=2, max=4
- "3+ years" → min=3, max=0
- "Minimum 5 years" → min=5, max=0
- "Fresher" → min=0, max=0
- Not mentioned → min=0, max=0

LOCATION RULE
- Extract if explicitly mentioned
EMPLOYMENT TYPE
- Full-time, Contract, Internship
SENIORITY LEVEL
- Junior, Mid, Senior, Lead
FINAL SAFETY RULES
- Do NOT hallucinate any field
- If not found → return "" or []
- Ensure consistency between primary_skills and good_to_have
- A skill cannot appear in both lists
JD:
{text}
"""
RESUME_PROMPT = """
You are an expert resume parsing system.

IMPORTANT:
- Return ONLY valid JSON
- No explanation
- No extra text
- Response MUST start with '{' and end with '}'

Return STRICT JSON ONLY:
{
  "name": "",
  "email": "",
  "phone": "",
  "total_years_experience": 0.0,
  "location": "",
  "skills": [],
  "experience": [
    {
      "role": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "description": ""
    }
  ],
  "education": [
    {
      "degree": "",
      "institute": "",
      "year": ""
    }
  ]
}

------------------------------------------------------------
TOTAL EXPERIENCE RULE
------------------------------------------------------------

- Look for phrases like:
  "5+ years of experience", "Around 11 Years", "Total 8 years"
- Convert to float (e.g., 5+ years → 5.0, 8.5 years → 8.5)
- If mentioned in summary/profile → this is mandatory to extract

------------------------------------------------------------
LAYOUT NORMALIZATION RULE (VERY IMPORTANT)
------------------------------------------------------------

- Resume text may come from PDF/OCR with broken formatting
- Ignore visual structure (columns, spacing, alignment)
- Treat all text as continuous stream
- Reconstruct meaning using context, not position

------------------------------------------------------------
TABLE HANDLING RULE (CRITICAL)
------------------------------------------------------------

- Resumes may contain tables or column-based layouts

SKILLS IN TABLES:
- Extract skills from ALL table formats (Technical Skills, Core Skills, Matrix, Grid)
- Do NOT skip skills due to column layout
- Read table row-wise first, then infer columns if needed

EXPERIENCE IN TABLES:
- Each row represents one experience entry
- Map fields carefully:
  role, company, start_date, end_date, description
- If data is split across columns, infer mapping using labels and context
- Do NOT merge multiple rows into one experience

------------------------------------------------------------
SKILLS EXTRACTION (GLOBAL DEEP SCAN)
------------------------------------------------------------

- Extract skills from ALL sections:
  1. Technical Skills / Summary sections
  2. Professional Experience bullet points
  3. Project descriptions
  4. Certifications and training

DUAL EXTRACTION:
- Explicit: directly mentioned technologies/tools
- Semantic: infer skills from context ONLY when strongly supported
- Do NOT overgeneralize tools into frameworks
- Do NOT assume technologies not explicitly mentioned
- Prefer precision over recall

INCLUDE:
- Programming languages, frameworks, tools, cloud, databases, core concepts

NORMALIZATION:
- AWS EC2 / S3 → AWS
- RESTful services → REST API

RULES:
- Remove duplicates
- Exclude soft skills (communication, teamwork, leadership)

------------------------------------------------------------
EXPERIENCE RULES
------------------------------------------------------------

- Extract all job roles separately
- Infer role if missing from context

DATES:
- Allowed formats: Jan 2024, 2024, Present
- Use "Present" for current role
- DO NOT calculate duration inside experience entries

------------------------------------------------------------
ANTI-LOSS RULE (VERY IMPORTANT)
------------------------------------------------------------

- Do NOT skip any section due to formatting issues
- Do NOT rely on visual layout
- Do NOT ignore table data or columns
- Always extract maximum possible structured data

------------------------------------------------------------
GENERAL RULES
------------------------------------------------------------

- Do NOT hallucinate
- If unknown → ""
- If not found → []

------------------------------------------------------------

Resume Text:
{text}
"""
SKILL_EXTRACTION_PROMPT = """
You are an expert resume skill extraction engine.

Extract ALL technical skills from the resume text.

------------------------------------------------------------
INCLUDE
------------------------------------------------------------

- Programming languages
- Frameworks
- Tools
- Databases
- Cloud platforms
- Core concepts (OOPs, Design Patterns, Multithreading, etc.)

------------------------------------------------------------
EXTRACTION STRATEGY (VERY IMPORTANT)
------------------------------------------------------------

Perform deep scanning across ALL sections:
- Technical Skills
- Work Experience
- Project descriptions
- Certifications

Extract:
1. Explicit skills → directly mentioned technologies
2. Context-based skills → ONLY when clearly supported by strong evidence

------------------------------------------------------------
NORMALIZATION RULES
------------------------------------------------------------

- Normalize variations into standard forms:
  - "aws ec2", "s3" → "AWS"
  - "restful services" → "REST API"
  - "oops concepts" → "OOPs"

- Ensure consistent casing (e.g., "java" → "Java")

- Remove duplicates

------------------------------------------------------------
CONTROLLED INFERENCE RULE (CRITICAL)
------------------------------------------------------------

Infer higher-level concepts ONLY when there is STRONG supporting evidence.

VALID INFERENCE EXAMPLES:
- AWS EC2, S3 → AWS
- Multiple AWS services → Cloud
- REST API → Web Services
- Multithreading → Concurrency

STRICT RESTRICTIONS:
- Do NOT infer tools or frameworks unless explicitly mentioned
- Do NOT assume libraries (e.g., log4j2, Hibernate) without direct evidence
- Do NOT overgeneralize technologies

IMPORTANT DISTINCTIONS:
- Web Services ≠ WebSocket
- Logging ≠ log4j2
- HTML/CSS ≠ UI Design (unless explicitly stated)
- Spring ≠ Spring Boot (unless explicitly mentioned)

------------------------------------------------------------
ANTI-HALLUCINATION RULE
------------------------------------------------------------

- Do NOT add skills that are not present or clearly implied
- Do NOT guess missing technologies
- Prefer missing a skill over adding an incorrect one

------------------------------------------------------------
FINAL OUTPUT RULES
------------------------------------------------------------

- Return ONLY a valid JSON array
- No explanation
- No extra text
- No markdown

------------------------------------------------------------

Resume:
{text}
"""
CLASSIFY_PROMPT = """
You are an expert job role classifier.
IMPORTANT:
- Answer ONLY with 'TECH' or 'NON-TECH'
- No explanation
- Output must be exactly one word
CRITERIA:
TECH:
- Development, QA, DevOps, Cloud, Data, AI/ML, Cybersecurity, IT systems
NON-TECH:
- BPO, Customer Support, Sales, HR, Marketing, Admin
RULES:
- Coding/tools/systems → TECH
- Voice/chat support only → NON-TECH
- Technical Support:
  - With tools → TECH
  - Only calls → NON-TECH
FINAL:
- Any technical signal → TECH
- Else → NON-TECH
ROLE:
{role_name}
DESCRIPTION:
{description}
"""
SKILL_MAPPER_PROMPT = """
You are a high-precision Technical Skill Mapping Engine for ATS systems.

Your goal is to map candidate skills to JD requirements using semantic similarity, technical equivalence, and controlled categorical inference.

------------------------------------------------------------
INPUTS
------------------------------------------------------------
JD REQUIREMENTS: {jd_requirements}
CANDIDATE SKILLS: {candidate_skills}

------------------------------------------------------------
TASK
------------------------------------------------------------
1. Map each JD skill to the most relevant candidate skill (if exists).
2. Perform "Category-to-Tool" mapping ONLY when the relationship is strong and industry-standard.
3. Apply controlled inference: Only infer relationships that are widely accepted and technically accurate.
4. Allow one candidate skill to satisfy multiple JD skills if it genuinely covers those domains.

------------------------------------------------------------
MANDATORY INFERENCE RULES (CONTROLLED)
------------------------------------------------------------
Apply inference ONLY when the relationship is strong and commonly accepted:

- Java / C++ / C# → OOPS Concepts, Object Oriented Programming, Multithreading.
- Spring Boot / Django / Express / NestJS → REST API, Microservices, Web Services.
- SQL / MySQL / PostgreSQL / Oracle → Relational Databases, RDBMS.
- React / Angular / Vue → Frontend Development, JavaScript, Web Technologies.
- AWS / Azure / GCP → Cloud Platforms, Cloud Computing.

------------------------------------------------------------
⚠️ CROSS-ECOSYSTEM CONSTRAINTS (CRITICAL)
------------------------------------------------------------
Do NOT match skills across fundamentally different ecosystems or technology stacks.

INVALID matches include:
- Java ↔ C#
- Java ↔ .NET
- Python ↔ Java
- SQL ↔ NoSQL
- Docker ↔ Kubernetes (related but NOT equivalent)

Rules:
- Only match within the SAME ecosystem or clearly compatible technologies.
- If ecosystems differ → DO NOT MATCH (even if semantically similar).
- Prefer strict correctness over broad similarity.

------------------------------------------------------------
CATEGORY & TOOL RELATIONSHIP
------------------------------------------------------------
- Category mapping is allowed ONLY when:
  - The candidate tool clearly belongs to that category
  - The mapping is widely accepted in industry

VALID examples:
- AWS → Cloud
- MySQL → Database
- Docker → Containerization

INVALID examples:
- Kubernetes → Docker
- SQL → NoSQL
- React → Angular (different frameworks)

------------------------------------------------------------
ALIAS HANDLING
------------------------------------------------------------
- AWS → Amazon Web Services
- Azure → Microsoft Azure
- Kubernetes → K8s
- REST API → RESTful services, Web APIs
- CI/CD → Pipelines, Jenkins, GitHub Actions, GitLab CI, Azure DevOps

------------------------------------------------------------
IMPORTANT CONSTRAINTS
------------------------------------------------------------
- Do NOT map unrelated technologies.
- Do NOT force matches.
- Prefer precision over recall.
- If unsure, DO NOT include the match.
- Every match MUST have a confidence score.

------------------------------------------------------------
SCORING RULES (CRITICAL)
------------------------------------------------------------
- Assign a confidence score between 0 and 1.
- Use:
  - 0.9+ → Exact or near-exact match
  - 0.7–0.89 → Strong semantic match
  - 0.5–0.69 → Weak but acceptable match
  - <0.5 → DO NOT include

------------------------------------------------------------
OUTPUT RULES
------------------------------------------------------------
- Return ONLY valid JSON.
- No explanations.
- No extra text.
- No markdown.

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------
{
  "matches": [
    {
      "jd_skill": "Exact skill from JD REQUIREMENTS",
      "candidate_skill": "Best matching representative tool/skill",
      "score": 0.78
    }
  ]
}
"""