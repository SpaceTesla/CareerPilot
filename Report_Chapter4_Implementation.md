# Chapter 4 — Implementation / Methodology / Proposed Approach

---

## 4.1 System Architecture Diagram (Detailed Explanation)

### High-Level Architecture

CareerPilot follows a **three-tier client-server architecture** deployed via Docker Compose, comprising a React-based frontend, a FastAPI backend, and a PostgreSQL database with vector extension support.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                  │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Next.js 15 Frontend (Port 3000)                │   │
│   │   ┌───────────┐  ┌────────────┐  ┌──────────────────────┐  │   │
│   │   │  Landing  │  │  Dashboard │  │  React Query Cache   │  │   │
│   │   │   Page    │  │   Pages    │  │  (localStorage sync) │  │   │
│   │   └───────────┘  └────────────┘  └──────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  HTTP / SSE (Server-Sent Events)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                               │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              FastAPI Backend (Port 8000)                    │   │
│   │                                                             │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │   │
│   │  │ Resume   │ │Analysis  │ │  Jobs    │ │ Applications │  │   │
│   │  │ Router   │ │ Router   │ │  Router  │ │   Router     │  │   │
│   │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │   │
│   │       └────────────┴────────────┴───────────────┘          │   │
│   │                         │                                   │   │
│   │              ┌──────────▼──────────┐                        │   │
│   │              │   Service Layer     │                        │   │
│   │  ┌───────────┴─────────────────────┴───────────┐           │   │
│   │  │  AnalysisService  │  JobMatchingService      │           │   │
│   │  │  ResumeService    │  AutomationService       │           │   │
│   │  │  ChatService      │  InterviewService        │           │   │
│   │  └───────────────────┴──────────────────────────┘           │   │
│   │                         │                                   │   │
│   │   ┌─────────────────────▼──────────────────────┐           │   │
│   │   │           AI / Agent Layer                 │           │   │
│   │   │  ┌─────────────┐    ┌─────────────────┐   │           │   │
│   │   │  │  LangGraph  │    │  LangChain      │   │           │   │
│   │   │  │  Agent      │    │  Tool Executor  │   │           │   │
│   │   │  │  (Stateful) │    │                 │   │           │   │
│   │   │  └──────┬──────┘    └────────┬────────┘   │           │   │
│   │   │         └──────────┬──────────┘            │           │   │
│   │   │                    ▼                       │           │   │
│   │   │         Google Gemini 2.5 Flash            │           │   │
│   │   │         (LLM + Vision)                     │           │   │
│   │   └────────────────────────────────────────────┘           │   │
│   │                         │                                   │   │
│   │   ┌─────────────────────▼──────────────────────┐           │   │
│   │   │    Browser Automation Layer                │           │   │
│   │   │    Playwright + Chromium (Stealth Mode)    │           │   │
│   │   └────────────────────────────────────────────┘           │   │
│   └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  SQLAlchemy ORM
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                   │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │           PostgreSQL 16 + pgvector (Port 5432)              │   │
│   │                                                             │   │
│   │  ┌───────────────┐  ┌────────────────────────────────────┐  │   │
│   │  │  Relational   │  │     Vector Store (pgvector)        │  │   │
│   │  │  Tables (9)   │  │  skills_embedding VECTOR(768)      │  │   │
│   │  │               │  │  Cosine Similarity Search (<=>)    │  │   │
│   │  └───────────────┘  └────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│   External APIs: JSearch (RapidAPI) │ Tavily │ Google Gemini         │
└──────────────────────────────────────────────────────────────────────┘
```

### Architecture Explanation

**Client Layer:**
The frontend is built with Next.js 15 using the App Router paradigm. It communicates with the backend over HTTP REST for standard requests and Server-Sent Events (SSE) for streaming responses (chat and auto-fill progress). TanStack React Query manages all server state with a localStorage persistence layer, enabling instant dashboard loads on revisit.

**Application Layer:**
The FastAPI backend exposes 12 route modules. Each route delegates business logic to a service class. Services in turn use the AI/Agent layer (LangGraph + LangChain + Gemini) for intelligence tasks and the Browser Automation layer (Playwright) for portal interactions. The Repository pattern abstracts all database access.

**AI / Agent Layer:**
A LangGraph stateful agent graph orchestrates multi-step reasoning. Each node in the graph performs a discrete task (load resume, analyze strengths, suggest improvements, compute metrics, aggregate score). LangChain tools are invoked within nodes. Google Gemini 2.5 Flash serves as the underlying LLM for both text generation and vision (screenshot analysis).

**Data Layer:**
PostgreSQL 16 with the pgvector extension serves as the single source of truth. Structured data (users, sessions, applications) lives in relational tables. Resume skill profiles are additionally stored as 768-dimensional embedding vectors for semantic similarity search.

---

## 4.2 UML Diagrams

### 4.2.1 Data Flow Diagram (DFD) — Level 0 (Context Diagram)

```
                        ┌─────────────┐
                        │             │
         Resume PDF ───►│             │◄─── Job Seeker (User)
                        │             │
     Analysis Results ◄─│  CareerPilot│───► Chat Messages
                        │   System    │
      Job Matches ◄─────│             │◄─── Feedback (helpful/not)
                        │             │
    Interview Q&A ◄─────│             │───► Application Status
                        │             │
                        └──────┬──────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
            Google Gemini  JSearch API  Tavily API
             (LLM/Vision)  (Job Data)  (Web Search)
```

### 4.2.2 DFD — Level 1 (Main Processes)

```
User
 │
 │ [1] Upload Resume (PDF)
 ▼
┌─────────────────────┐
│  1.0 Resume         │──── Raw Text ────►┌─────────────────────┐
│  Processing         │                   │  2.0 AI Analysis    │
│  Pipeline           │◄── Parsed JSON ───│  Engine (LangGraph) │
└─────────┬───────────┘                   └──────────┬──────────┘
          │                                          │
          │ Store Profile                            │ Store Analysis
          ▼                                          ▼
   ┌──────────────┐                          ┌──────────────┐
   │  D1:         │                          │  D2:         │
   │  resume_     │                          │  analysis_   │
   │  profiles    │                          │  history     │
   └──────────────┘                          └──────────────┘
          │                                          │
          │ Skill Embedding                          │ Score + Grade
          ▼                                          ▼
   ┌──────────────┐     Job Query            ┌──────────────────────┐
   │  D3: pgvector│──────────────────────────►  3.0 Job Matching    │
   │  embeddings  │◄─ Similarity Scores ─────│  Service             │
   └──────────────┘                          └──────────┬───────────┘
                                                        │
                                              JSearch / Tavily API
                                                        │
                                              ┌─────────▼───────────┐
                                              │  Job Recommendations │
                                              │  (ranked by match   │
                                              │   score)            │
                                              └─────────────────────┘

User
 │
 │ [2] Chat Message
 ▼
┌─────────────────────┐
│  4.0 Chat Service   │──► Gemini LLM (stream) ──► Token chunks (SSE)
│  (LangChain LCEL)   │
└─────────────────────┘

User
 │
 │ [3] Auto-Fill Request
 ▼
┌─────────────────────┐
│  5.0 Automation     │──► Playwright Browser
│  Service            │──► Gemini Vision (screenshot analysis)
│  (Background Task)  │──► Form Filling
└─────────────────────┘
          │
          │ Progress Updates
          ▼
    Frontend (SSE Poll)
```

### 4.2.3 Activity Diagram — Resume Upload to Dashboard

```
      ┌─────────────────┐
      │   START         │
      └────────┬────────┘
               │
               ▼
      ┌─────────────────────┐
      │  User drags & drops │
      │  resume (PDF)       │
      └────────┬────────────┘
               │
               ▼
      ┌─────────────────────┐
      │  POST /resume/      │
      │  upload/async       │
      └────────┬────────────┘
               │
               ▼
      ┌─────────────────────┐         ┌──────────────────────────┐
      │  Backend returns    │         │  Background Pipeline:    │
      │  job_id immediately │         │  1. PDF → Markdown       │
      └────────┬────────────┘         │  2. TextCleaner          │
               │                      │  3. SectionSplitter      │
               ▼                      │  4. Structured Parsers   │
      ┌─────────────────────┐         │  5. Gemini Enrichment    │
      │  Frontend polls     │         │  6. Compute Embeddings   │
      │  GET /resume/jobs/  │         │  7. Store in PostgreSQL  │
      │  {job_id} (1.5s)    │         └──────────────────────────┘
      └────────┬────────────┘
               │
          ┌────▼────┐
          │ status? │
          └────┬────┘
        ┌──────┴──────┐
   processing       completed
        │               │
        └──────►poll    ▼
                ┌───────────────────────┐
                │  Prefetch (parallel): │
                │  - Analysis Overview  │
                │  - Job Recommendations│
                │  - Career Path        │
                │  - Interview Prep     │
                │  - Courses            │
                └──────────┬────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │  Navigate to         │
                │  /dashboard/overview │
                └──────────┬───────────┘
                           │
                           ▼
                        ┌──────┐
                        │  END │
                        └──────┘
```

### 4.2.4 Activity Diagram — LangGraph Analysis Pipeline

```
      ┌─────────────────────────────────┐
      │   GET /analysis/overview        │
      │   user_id passed in query       │
      └────────────────┬────────────────┘
                       │
                       ▼
      ┌─────────────────────────────────┐
      │  Node 1: ResumeLoader           │
      │  Fetch resume_profile from DB   │
      │  Load raw_data JSON             │
      └────────────────┬────────────────┘
                       │
          ┌────────────┼─────────────┐
          │ parallel   │   parallel  │ parallel
          ▼            ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌──────────────┐
   │ Node 2:    │ │ Node 3:  │ │ Node 4:      │
   │ Strengths  │ │ Improve- │ │ Metrics      │
   │ Analysis   │ │ ments    │ │ Extraction   │
   │ (Gemini)   │ │ (Gemini) │ │ (Gemini)     │
   └──────┬─────┘ └────┬─────┘ └──────┬───────┘
          └────────────┼───────────────┘
                       │ merge state
                       ▼
      ┌─────────────────────────────────┐
      │  Node 5: ScoreAggregation       │
      │  Compute overall_score (0-100)  │
      │  Assign grade (A/B/C/D/F)       │
      │  Compute section_scores         │
      └────────────────┬────────────────┘
                       │
                       ▼
      ┌─────────────────────────────────┐
      │  Node 6: OutputFormatting       │
      │  Structure final JSON response  │
      │  Store in analysis_history      │
      └────────────────┬────────────────┘
                       │
                       ▼
      ┌─────────────────────────────────┐
      │  Return to Frontend             │
      │  Cache in React Query           │
      │  Cache in localStorage          │
      └─────────────────────────────────┘
```

### 4.2.5 Activity Diagram — Browser Automation (Auto-Fill)

```
      ┌──────────────────────────────┐
      │  POST /applications/auto-fill│
      │  { url, portal, user_id }    │
      └───────────────┬──────────────┘
                      │
                      ▼
      ┌──────────────────────────────┐
      │  Create background task      │
      │  Return task_id (immediate)  │
      └───────────────┬──────────────┘
                      │
            ┌─────────▼──────────┐
            │ Background Thread  │
            └─────────┬──────────┘
                      │
                      ▼
      ┌──────────────────────────────┐
      │  Load portal_session         │
      │  (saved cookies/localStorage)│
      └───────────────┬──────────────┘
                      │
                      ▼
      ┌──────────────────────────────┐
      │  Launch Playwright Chromium  │
      │  Apply stealth patches:      │
      │  - Spoof navigator.webdriver │
      │  - Randomize fingerprint     │
      └───────────────┬──────────────┘
                      │
                      ▼
      ┌──────────────────────────────┐
      │  Navigate to job URL         │
      │  Capture screenshot          │
      └───────────────┬──────────────┘
                      │
                      ▼
      ┌──────────────────────────────┐
      │  Send screenshot to          │
      │  Gemini Vision               │
      │  → Identify form fields      │
      │  → Map to resume data        │
      └───────────────┬──────────────┘
                      │
                      ▼
      ┌──────────────────────────────┐      ┌───────────────────┐
      │  For each form field:        │─────►│  Update task      │
      │  - Fill with resume value    │      │  progress in DB   │
      │  - Human-like typing delay   │      └───────────────────┘
      │  - Capture screenshot        │
      └───────────────┬──────────────┘
                      │
                      ▼
           ┌──────────────────┐
           │  All fields done?│
           └──────┬─────┬─────┘
                 No    Yes
                  │      │
                  ↑      ▼
                  │   ┌──────────────────────────┐
                  │   │  Save portal_session     │
                  │   │  (cookies for reuse)     │
                  │   │  Set status = completed  │
                  │   └──────────────────────────┘
                  │
              (loop back)
```

---

## 4.3 Proposed Algorithms and Techniques

### 4.3.1 Resume Parsing Algorithm (Multi-Stage NLP Pipeline)

**Objective:** Convert an unstructured PDF resume into a structured JSON object with clearly identified sections.

**Technique:** Rule-based section detection combined with regex parsing and LLM-based enrichment.

**Stages:**

**Stage 1 — PDF to Markdown Conversion**
PyMuPDF4LLM is used to convert the PDF into Markdown while preserving structural hints (headings, bullet points, tables). This is preferred over plain text extraction because Markdown retains section hierarchy.

**Stage 2 — Text Cleaning**
The `TextCleaner` module normalizes the extracted text:
- Collapses consecutive whitespace and blank lines
- Removes page numbers, headers/footers, watermarks
- Standardizes bullet point characters (•, -, *, →) to a uniform format
- Strips non-printable Unicode characters

**Stage 3 — Section Splitting**
The `SectionSplitter` identifies section boundaries using a keyword dictionary:
```
SECTION_KEYWORDS = {
  "contact":        ["contact", "personal information", "profile"],
  "skills":         ["skills", "technical skills", "competencies", "technologies"],
  "experience":     ["experience", "work history", "employment", "professional experience"],
  "education":      ["education", "academics", "qualifications", "degrees"],
  "projects":       ["projects", "personal projects", "academic projects"],
  "achievements":   ["achievements", "awards", "honors", "accomplishments"],
  "co_curricular":  ["activities", "extracurricular", "co-curricular", "volunteering"]
}
```
The algorithm scans lines for keyword matches (case-insensitive, fuzzy), marks section boundaries, and splits the document into labeled text blocks.

**Stage 4 — Structured Parsing**
Each section block is parsed by a dedicated parser:
- `ExperienceParser`: Extracts company name, job title, date range, and bullet points using regex date patterns and positional heuristics
- `EducationParser`: Extracts institution, degree, field, GPA, and graduation year
- `SkillsParser`: Tokenizes skills, groups by category (languages, frameworks, tools, databases, cloud)

**Stage 5 — LLM Enrichment (Gemini)**
The partially structured JSON is sent to Gemini with a validation prompt. Gemini:
- Fills in missing fields (e.g., infers job title from context)
- Resolves ambiguities (e.g., distinguishes internship from full-time)
- Extracts implicit information (e.g., calculates total years of experience)
- Validates the structure against a Pydantic schema

---

### 4.3.2 Semantic Job Matching Algorithm (Vector Similarity Search)

**Objective:** Rank job postings by relevance to the candidate's skill profile beyond simple keyword overlap.

**Technique:** Cosine similarity in a 768-dimensional embedding space using pgvector.

**Algorithm:**

```
Step 1: EMBEDDING GENERATION (at resume upload time)
  skills_text = concatenate(parsed_skills, job_titles, tech_stack_from_projects)
  resume_embedding = EmbeddingsService.encode(skills_text)
  → 768-dimensional float vector
  → Store in resume_profiles.skills_embedding (pgvector VECTOR(768))

Step 2: JOB DATA RETRIEVAL
  IF jsearch_api_key is set:
    jobs = JSearchAPI.query(role=inferred_target_role, location=user_location)
  ELSE:
    jobs = TavilyAPI.search(query="{role} jobs {location} site:linkedin.com OR site:indeed.com")

Step 3: JOB EMBEDDING
  FOR each job in jobs:
    job_text = concatenate(job.title, job.description, job.required_skills)
    job_embedding = EmbeddingsService.encode(job_text)

Step 4: SIMILARITY SCORING
  FOR each job:
    match_score = cosine_similarity(resume_embedding, job_embedding)
              = (resume_embedding · job_embedding) /
                (||resume_embedding|| × ||job_embedding||)

Step 5: RANKING & FILTERING
  ranked_jobs = sort(jobs, key=match_score, descending=True)
  return ranked_jobs[:limit]
```

**Why cosine similarity?**
Cosine similarity measures the angle between two vectors regardless of magnitude, making it robust to resumes of varying lengths. A resume with fewer skills still gets accurately ranked if those skills semantically overlap with the job requirements.

---

### 4.3.3 LangGraph Multi-Step Analysis Algorithm

**Objective:** Produce a comprehensive resume analysis (score, grade, strengths, weaknesses, improvements) through structured, stateful multi-step LLM reasoning.

**Technique:** Directed acyclic agent graph with shared state, implemented in LangGraph.

**Graph State Object:**
```
AgentState {
  user_id:         str
  resume_profile:  dict        ← loaded in Node 1
  strengths:       list[str]   ← populated in Node 2
  improvements:    list[str]   ← populated in Node 3
  metrics:         dict        ← populated in Node 4
  overall_score:   float       ← computed in Node 5
  grade:           str         ← computed in Node 5
  section_scores:  dict        ← computed in Node 5
  final_output:    dict        ← formatted in Node 6
}
```

**Graph Traversal:**
```
START
  │
  ▼
Node 1: load_resume(state)
  state.resume_profile = DB.fetch(user_id)
  IF not found → raise ResumeNotFoundError
  │
  ├──► Node 2: analyze_strengths(state)  ─────┐
  │    prompt = PromptTemplates.STRENGTHS      │
  │    response = Gemini.generate(prompt,      │ (parallel
  │               resume_profile)              │  execution
  │    state.strengths = parse_list(response)  │  via
  │                                            │  asyncio.gather)
  ├──► Node 3: suggest_improvements(state) ───┤
  │    prompt = PromptTemplates.IMPROVEMENTS   │
  │    response = Gemini.generate(prompt,      │
  │               resume_profile)              │
  │    state.improvements = parse_list(resp)   │
  │                                            │
  └──► Node 4: extract_metrics(state) ────────┘
       state.metrics = {
         years_of_experience: ...,
         skill_count: ...,
         project_count: ...,
         leadership_indicators: ...
       }
  │
  ▼
Node 5: aggregate_score(state)
  base_score = weighted_average({
    experience_score:   weight=0.30,
    skills_score:       weight=0.25,
    projects_score:     weight=0.20,
    education_score:    weight=0.15,
    achievements_score: weight=0.10
  })
  penalty = count(critical_missing_sections) × 5
  state.overall_score = clamp(base_score - penalty, 0, 100)
  state.grade = score_to_grade(state.overall_score)
  │
  ▼
Node 6: format_output(state)
  state.final_output = {
    overall_score, grade, strengths, weaknesses,
    improvements, section_scores, metrics
  }
  DB.save(analysis_history, state.final_output)
  │
  ▼
END → return state.final_output
```

---

### 4.3.4 ATS (Applicant Tracking System) Scoring Algorithm

**Objective:** Evaluate how well a resume will pass through Applicant Tracking Systems for a specific job description.

**Technique:** Keyword extraction + semantic overlap scoring using Gemini.

**Algorithm:**
```
INPUT: resume_text, job_description

Step 1: Extract keywords from job description
  jd_keywords = Gemini.extract_keywords(job_description)
  → returns: required_skills, preferred_skills, action_verbs, industry_terms

Step 2: Match against resume
  FOR each keyword in jd_keywords:
    IF keyword in resume_text (exact match):
      exact_matches.add(keyword)
    ELIF semantic_similarity(keyword, resume_text) > threshold:
      semantic_matches.add(keyword)
    ELSE:
      missing_keywords.add(keyword)

Step 3: Compute ATS score
  exact_score    = len(exact_matches) / len(jd_keywords) × 100
  semantic_bonus = len(semantic_matches) / len(jd_keywords) × 20
  ats_score      = min(exact_score + semantic_bonus, 100)

Step 4: Return
  {
    ats_score,
    matched_keywords:  exact_matches ∪ semantic_matches,
    missing_keywords:  missing_keywords,
    recommendation:    "Add these keywords to improve ATS pass rate"
  }
```

---

### 4.3.5 RAG (Retrieval-Augmented Generation) for Career Guidance Chat

**Objective:** Ensure AI career coach responses are grounded in the user's actual resume, not generic advice.

**Technique:** Chunk-retrieve-generate pattern.

**Algorithm:**
```
Step 1: INDEXING (at resume upload time)
  chunks = split(resume_text, chunk_size=512, overlap=64)
  FOR each chunk:
    embedding = EmbeddingsService.encode(chunk)
    vector_store.upsert(chunk, embedding, metadata={section, user_id})

Step 2: RETRIEVAL (at query time)
  query_embedding = EmbeddingsService.encode(user_message)
  relevant_chunks = pgvector.similarity_search(
    query_embedding, top_k=3, filter={user_id}
  )

Step 3: GENERATION
  context = join(relevant_chunks)
  prompt = f"""
    You are a career advisor. Use the following resume context to answer:
    Context: {context}
    
    Question: {user_message}
    
    Answer specifically based on this resume.
  """
  response_stream = Gemini.stream(prompt)
  yield response_stream  ← SSE tokens to frontend
```

---

### 4.3.6 Playwright Stealth Automation Algorithm

**Objective:** Automatically fill job application forms on real portals while evading bot detection.

**Technique:** Headless browser with fingerprint spoofing + Gemini Vision for dynamic field detection.

**Algorithm:**
```
Step 1: STEALTH INITIALIZATION
  browser = Playwright.launch(headless=True)
  context = browser.new_context(
    user_agent = random_realistic_user_agent(),
    viewport   = random_viewport(),  # e.g. 1366×768, 1920×1080
    locale     = "en-US",
    timezone   = random_timezone()
  )
  page = context.new_page()
  page.evaluate("Object.defineProperty(navigator, 'webdriver', {get: () => false})")

Step 2: SESSION RESTORATION
  IF portal_session exists for (user_id, portal):
    context.add_cookies(portal_session.cookies)
    page.evaluate("localStorage.setItem(k, v) for k,v in saved_storage")

Step 3: NAVIGATION + VISION ANALYSIS
  page.goto(job_url)
  screenshot_bytes = page.screenshot()
  form_fields = GeminiVision.analyze(
    image=screenshot_bytes,
    prompt="Identify all form fields, their labels, types, and positions"
  )

Step 4: FIELD FILLING
  resume_data = DB.fetch(resume_profile, user_id)
  field_map = map_fields_to_resume(form_fields, resume_data)

  FOR each (field, value) in field_map:
    element = page.locator(field.selector)
    element.click()
    FOR each char in value:
      element.type(char, delay=random(30, 80))  ← human typing simulation
    update_task_progress(step=field.label, screenshot=page.screenshot())

Step 5: SESSION SAVE
  cookies = context.cookies()
  storage = page.evaluate("JSON.stringify(localStorage)")
  DB.save(portal_sessions, {portal, cookies, storage})
  set_task_status(completed)
```

---

## 4.4 Description of Data Collection Process

### 4.4.1 Resume Data

**Source:** End users upload their own resumes in PDF or Markdown format via the CareerPilot web interface.

**Collection Method:**
- Resumes are submitted via a `multipart/form-data` POST request to `/resume/upload/async`
- Files are processed entirely in-memory; no raw file is persisted to disk
- Extracted structured JSON is stored in the `resume_profiles` table in PostgreSQL
- A 768-dimensional skill embedding vector is computed and stored alongside the profile

**Data Sensitivity:** Resumes contain personally identifiable information (PII). CareerPilot scopes all data by `user_id` — a UUID generated at upload time — ensuring data isolation between users.

### 4.4.2 Job Postings Data

**Source 1 — JSearch API (RapidAPI):**
- Real-time job postings aggregated from Indeed, LinkedIn, Glassdoor, and other boards
- Queried dynamically based on user's inferred target role and location
- Returns: job title, company, description, salary range, application URL, posting date

**Source 2 — Tavily API (Fallback):**
- Web search API used when JSearch API key is not configured
- Searches the live web for job postings using targeted queries
- Results are parsed and normalized to match the JSearch schema

**No static dataset is used.** All job data is fetched in real-time to ensure currency.

### 4.4.3 User Interaction Data

The following interaction data is collected during platform use:

| Data Type | Table | Purpose |
|-----------|-------|---------|
| Chat messages | `messages` | Conversation history for context |
| Analysis results | `analysis_history` | Track improvement over resume iterations |
| Application status | `job_applications` | Kanban board state |
| Recommendation feedback | `recommendation_feedback` | Track helpfulness ratings (thumbs up/down) for jobs and courses |
| Portal sessions | `portal_sessions` | Save browser cookies to avoid repeated logins |
| Processing job status | `resume_processing_jobs` | Track async processing progress |

### 4.4.4 Embedding Data

Skill embeddings are derived from the parsed resume profile:

```
skills_text = skills_list + job_titles + project_technologies
embedding   = GoogleEmbeddingModel.encode(skills_text)
            → VECTOR(768) stored in resume_profiles.skills_embedding
```

These embeddings are not user-provided — they are computed by the system and used purely for semantic similarity calculations.

---

## 4.5 Tech Stack

### Languages
| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.13 | Backend API, AI services, automation |
| TypeScript | 5.x | Frontend, type-safe API client |
| SQL | PostgreSQL dialect | Database queries, pgvector operations |

### Frameworks & Libraries

**Backend:**
| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.118+ | REST API framework, async request handling |
| Uvicorn | latest | ASGI server |
| LangChain | 0.3.27 | LLM orchestration, prompt templates, tool execution |
| LangGraph | 0.6.8 | Stateful agent graph execution |
| langchain-google-genai | 2.0.10+ | Google Gemini integration for LangChain |
| SQLAlchemy | 2.x | ORM, async database sessions |
| Pydantic | 2.x | Data validation, schema enforcement |
| Alembic | latest | Database migrations |
| psycopg2 | latest | PostgreSQL driver |
| pgvector | 0.4.1+ | Vector storage & similarity search |
| PyMuPDF4LLM | latest | PDF to Markdown conversion |
| Playwright | 1.51+ | Browser automation |
| python-jose | latest | JWT token handling |
| python-multipart | latest | File upload parsing |

**Frontend:**
| Library | Version | Purpose |
|---------|---------|---------|
| Next.js | 15.5.5 | React framework with App Router |
| React | 19.x | UI library |
| TanStack React Query | 5.56+ | Server state management, caching |
| shadcn/ui | latest | Accessible component library (Radix UI) |
| Tailwind CSS | 4.x | Utility-first styling |
| Recharts | 2.15.4+ | Data visualization (charts, gauges) |
| Framer Motion | latest | UI animations |
| Zod | latest | Runtime schema validation |
| Lucide React | latest | Icon library |
| Sonner | latest | Toast notifications |

### Databases & Storage
| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 16 | Primary relational database |
| pgvector | 0.7+ | Vector extension for embeddings |
| localStorage | Browser API | Client-side query cache persistence |

### AI & External APIs
| Service | Purpose |
|---------|---------|
| Google Gemini 2.5 Flash | Text generation, vision analysis, enrichment |
| Google Embedding Model | 768-dim text embeddings for semantic search |
| JSearch API (RapidAPI) | Real-time job postings |
| Tavily API | Web search for job recommendations (fallback) |

### DevOps & Tooling
| Tool | Purpose |
|------|---------|
| Docker | Containerization of all services |
| Docker Compose | Multi-container orchestration |
| uv / pip | Python package management |
| npm | Node.js package management |
| Alembic | Database schema migrations |
| Playwright Chromium | Pre-installed in Docker for browser automation |

### Development Environment
| Tool | Purpose |
|------|---------|
| Python 3.13 | Backend runtime |
| Node.js 20 (Alpine) | Frontend build & runtime |
| pgvector:pg16 Docker image | Database with vector support pre-installed |

---

## 4.6 Pseudocode

### 4.6.1 Resume Upload and Processing

```
FUNCTION handle_resume_upload(file, user_id, enrich=True):

    // Step 1: Create async job
    job = create_processing_job(user_id, status="queued")
    RETURN { job_id: job.id }  // non-blocking return

    // Step 2: Background processing
    BACKGROUND:
        update_job(job.id, status="processing", progress=10)

        // Detect and convert
        IF file.extension == "pdf":
            markdown_text = pymupdf4llm.to_markdown(file)
        ELSE:
            markdown_text = file.read_text()

        update_job(job.id, progress=30)

        // Clean
        clean_text = TextCleaner.clean(markdown_text)

        // Split sections
        sections = SectionSplitter.split(clean_text)

        // Parse each section
        parsed = {
            contact:      ContactParser.parse(sections["contact"]),
            skills:       SkillsParser.parse(sections["skills"]),
            experience:   ExperienceParser.parse(sections["experience"]),
            education:    EducationParser.parse(sections["education"]),
            projects:     ProjectParser.parse(sections["projects"]),
            achievements: AchievementsParser.parse(sections["achievements"])
        }

        update_job(job.id, progress=60)

        // Enrich with LLM
        IF enrich:
            enriched = GeminiEnricher.enrich(parsed)
            parsed = Validator.validate(enriched)

        update_job(job.id, progress=85)

        // Compute embedding
        skills_text = join(parsed.skills + parsed.experience[].title)
        embedding = EmbeddingsService.encode(skills_text)

        // Store in DB
        profile = DB.insert(resume_profiles, {
            user_id:          user_id,
            raw_data:         parsed,
            skills_embedding: embedding
        })

        update_job(job.id, status="completed", progress=100,
                   profile_id=profile.id)
```

### 4.6.2 Analysis Overview

```
FUNCTION get_analysis_overview(user_id):

    profile = DB.fetch(resume_profiles, WHERE user_id=user_id, ORDER BY created_at DESC)
    IF profile is NULL:
        RAISE ResumeNotFoundError

    // Initialize LangGraph agent state
    state = AgentState(user_id=user_id, resume_profile=profile.raw_data)

    // Run nodes in parallel
    results = await asyncio.gather(
        analyze_strengths_node(state),
        suggest_improvements_node(state),
        extract_metrics_node(state)
    )

    state.strengths    = results[0]
    state.improvements = results[1]
    state.metrics      = results[2]

    // Aggregate score
    section_scores = {
        experience:   score_experience(profile.raw_data.experience),
        skills:       score_skills(profile.raw_data.skills),
        projects:     score_projects(profile.raw_data.projects),
        education:    score_education(profile.raw_data.education),
        achievements: score_achievements(profile.raw_data.achievements)
    }

    overall_score = weighted_average(section_scores, WEIGHTS)
    grade = assign_grade(overall_score)

    output = {
        overall_score:  overall_score,
        grade:          grade,
        strengths:      state.strengths,
        weaknesses:     derive_weaknesses(section_scores),
        improvements:   state.improvements,
        section_scores: section_scores,
        metrics:        state.metrics
    }

    DB.insert(analysis_history, { user_id, profile_id: profile.id, ...output })
    RETURN output
```

### 4.6.3 Semantic Job Matching

```
FUNCTION get_job_recommendations(user_id, limit=10):

    profile = DB.fetch(resume_profiles, WHERE user_id=user_id)
    resume_embedding = profile.skills_embedding  // VECTOR(768)
    target_role = infer_target_role(profile.raw_data)
    location    = profile.raw_data.contact.location

    // Fetch live jobs
    IF config.JSEARCH_API_KEY is set:
        raw_jobs = JSearchAPI.query(role=target_role, location=location)
    ELSE:
        raw_jobs = TavilyAPI.search(f"{target_role} jobs {location}")

    ranked_jobs = []
    FOR each job in raw_jobs:
        job_text      = job.title + " " + job.description
        job_embedding = EmbeddingsService.encode(job_text)
        match_score   = cosine_similarity(resume_embedding, job_embedding)
        ranked_jobs.append({ ...job, match_score })

    ranked_jobs.sort(key=match_score, reverse=True)
    RETURN ranked_jobs[:limit]
```

### 4.6.4 Streaming Chat

```
FUNCTION stream_chat(message, user_id, session_id):

    profile  = DB.fetch(resume_profiles, WHERE user_id=user_id)
    history  = DB.fetch(messages, WHERE session_id=session_id, LIMIT=10)

    // RAG: retrieve relevant resume chunks
    query_embedding    = EmbeddingsService.encode(message)
    relevant_chunks    = pgvector.similarity_search(query_embedding, top_k=3,
                                                    filter={user_id})
    context = join(relevant_chunks)

    // Build prompt
    prompt = PromptTemplates.CHAT.format(
        resume_context = context,
        chat_history   = format_history(history),
        user_message   = message
    )

    // Save user message
    DB.insert(messages, { session_id, role="user", content=message })

    // Stream from Gemini
    full_response = ""
    YIELD SSE_event("meta", { model: "gemini-2.5-flash", timestamp: now() })

    FOR token in Gemini.stream(prompt):
        full_response += token
        YIELD SSE_event("token", token)

    YIELD SSE_event("end", { total_tokens: len(full_response) })

    // Save assistant message
    DB.insert(messages, { session_id, role="assistant", content=full_response })
```

### 4.6.5 Auto-Fill Browser Automation

```
FUNCTION auto_fill_application(job_url, portal, user_id):

    task = create_task(user_id, status="queued")
    RETURN { task_id: task.id }

    BACKGROUND:
        // Stealth browser setup
        browser = Playwright.launch(headless=True)
        context = browser.new_context(
            user_agent = pick_random_user_agent(),
            viewport   = pick_random_viewport()
        )
        page = context.new_page()
        page.evaluate("navigator.webdriver = false")

        // Restore session if available
        saved_session = DB.fetch(portal_sessions, WHERE user_id, portal)
        IF saved_session:
            context.add_cookies(saved_session.cookies)

        // Navigate and analyze
        page.goto(job_url)
        update_task(task.id, step="Analyzing page", progress=20)
        screenshot = page.screenshot()

        fields = GeminiVision.analyze(screenshot,
            "List all form fields with their labels, input types, and CSS selectors")

        profile = DB.fetch(resume_profiles, WHERE user_id)
        field_map = map_resume_to_fields(profile.raw_data, fields)

        // Fill each field
        FOR i, (field, value) in enumerate(field_map):
            element = page.locator(field.selector)
            element.click()
            element.type_slowly(value, delay_per_char=random(30, 80))

            progress = 20 + int((i / len(field_map)) * 70)
            step_screenshot = page.screenshot()
            update_task(task.id, step=f"Filling: {field.label}",
                        progress=progress, screenshot=step_screenshot)

        // Save session for reuse
        DB.upsert(portal_sessions, {
            user_id:       user_id,
            portal:        portal,
            cookies:       context.cookies(),
            storage_state: page.evaluate("JSON.stringify(localStorage)")
        })

        update_task(task.id, status="completed", progress=100)
```

---

*End of Chapter 4 — Implementation / Methodology / Proposed Approach*
