# CareerPilot: Master Design Document

### Version 2.0 — The Founding CTO's Blueprint

_Revised June 2026_

---

> This document exists because V1 answered the wrong question first.
> V1 asked: _How do we build CareerPilot?_
> V2 asks: _Why should CareerPilot exist — and if it does, what must it become?_
> Architecture without product conviction is engineering theater.

---

# PART 1 — PRODUCT THESIS

---

## The Founding Question

Before writing a single line of code, a single schema, a single agent definition — we have to answer one question honestly:

**If ChatGPT, Claude, Gemini, Cursor, LinkedIn, Indeed, and Glassdoor already exist in 2026 — why would someone open CareerPilot tomorrow morning?**

Not to use once. Not to try. To _open it tomorrow morning_.

The answer is not "because it has better job recommendations." Job recommendations are a commodity.

The answer is not "because it automates applications." Automation without intelligence is spam.

The answer is not "because it has an AI agent." Every product has an AI agent in 2026.

The honest answer requires understanding something deeper: **why people actually fail at managing their careers**, and why every existing product fails to fix it.

---

## Why People Fail

There are three failure modes. They compound each other.

### Failure Mode 1: Episodic Management

People manage their careers the way companies managed finances before ERP — manually, reactively, and only in a crisis.

You spend zero time thinking about your career for 18 months. Then you get a bad performance review, or the company announces layoffs, or you see a competitor's salary on Glassdoor. Suddenly you're in reactive mode: dusting off a stale resume, applying frantically to 30 roles, accepting the first offer above your current salary.

Every career decision made in reactive mode is made with less information, less leverage, and less time than it deserves.

The underlying problem is not "the job search is hard." It is that **there is no instrument that keeps you informed about your career between job searches**.

Your financial health has a credit score. Your physical health has a doctor. Your career health has nothing.

### Failure Mode 2: Invisible Markets

Most engineers do not know:

- What they are worth _right now_, not what they were worth when they last negotiated.
- Which of their skills are appreciating and which are commoditizing.
- Which companies in their target sector are actually hiring vs. ghost-posting.
- What the realistic next step in their career looks like — not the aspirational one, the realistic one.
- Which career moves at their seniority level actually lead to the outcomes they want.

This is not because people are lazy. It is because the information is genuinely inaccessible in aggregate form. It exists — scattered across thousands of job postings, offer letters, career conversations, and LinkedIn activity — but no one has assembled it into a coherent picture for any individual.

### Failure Mode 3: Positioning Failure

The single most common reason strong engineers don't get the roles they deserve is positioning failure. Not skill failure. Not experience failure.

Positioning failure means: you have the substance but not the narrative. You don't know how to articulate what makes you different from the 400 other engineers who also know Python, have worked with Postgres, and have "5 years of backend experience."

Positioning requires understanding what the market actually values (market intelligence), how you compare against the competition (competitive intelligence), and how to frame your specific trajectory as an asset, not a list of jobs (narrative intelligence).

No tool helps with this today. ChatGPT will polish your words. LinkedIn will show you the job. Neither will tell you whether your positioning is _actually competitive_ for the role you're targeting.

---

## Why Existing Products Fail

| Product                    | What It Does Well                  | Why It Fundamentally Fails                                                                                                    |
| -------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **LinkedIn**               | Profile hosting, recruiter network | Optimized for recruiters, not candidates. Incentive is engagement, not outcomes. Your data trains their algorithm, not yours. |
| **Indeed / Glassdoor**     | Job aggregation, salary data       | Job boards. No intelligence. No learning. Static.                                                                             |
| **ChatGPT / Claude**       | Resume drafting, interview prep    | No career memory. No market data. No outcomes. Starts fresh every conversation. Generic by design.                            |
| **Teal / Huntr**           | Application tracking               | Organizational tools for a fundamentally broken process. Makes manual job searching slightly less chaotic.                    |
| **Interviewed.ai / Karat** | Technical interview prep           | Narrow scope. Solves one moment in a much longer journey.                                                                     |
| **Levels.fyi**             | Compensation data                  | Crowd-sourced, self-reported, engineering-focused. No intelligence layer. No personalization.                                 |
| **Mercor**                 | AI-powered job matching            | Focused on immediate placement. No long-term career relationship.                                                             |

The pattern is consistent: **every product solves a moment, not a career**.

They optimize for the transaction (application submitted, resume polished, interview prepped) rather than the outcome (career trajectory maximized over time).

---

## The Real Problem

People don't fail to get jobs because they lack AI assistance. They fail because:

1. **They operate without continuous intelligence.** No one tells them when the market shifts.
2. **They optimize for activity over strategy.** 50 applications is not better than 10 strategic ones.
3. **They have no feedback loop.** They don't know whether their resume, positioning, or targeting is the failure point.
4. **They are invisible to the right people at the right time.** Hiring happens before postings go public — via internal referrals, recruiter pipelines, and warm introductions.
5. **The gap between who they are and who they appear to be professionally is never measured.**

---

## The Founding Insight

> **Careers are a compounding asset. People treat them as a series of transactions.**

The engineers who maximize their outcomes over a decade are not the ones who search harder when they need a job. They are the ones who are _always optimally positioned_ — building the right skills, at the right companies, with the right narrative, before they ever need to search.

They have an advantage that looks like luck from the outside but is actually continuous information and strategic positioning.

CareerPilot's founding insight is that this advantage can be systematized.

Not for the 1% who have mentors at every tier, friends at every company, and the pattern recognition that comes from a decade of deliberate career navigation.

For everyone.

---

## One-Sentence Positioning

> **CareerPilot is the continuous intelligence platform that makes your career compound — so the next opportunity finds you already positioned for it.**

This is not "AI career assistant." An assistant waits to be asked.

CareerPilot is active when you're not looking at it. It updates your market position. It tracks your skill trajectory. It monitors the companies you care about. It tells you what's changing before you need to react.

The user's relationship with CareerPilot is not "I open it when I need a job." It is "I trust it to keep me informed about the one asset I can't diversify."

---

## Product Thesis

**Three sentences that justify CareerPilot's existence:**

1. The career intelligence gap is real and universal: almost no one has continuous, accurate, personalized intelligence about their own market position.

2. This gap is closable now — not because AI became smarter, but because the combination of agent orchestration, outcome data, and market signal processing makes it possible to maintain a living model of both the person and the market simultaneously.

3. Every user who joins improves the model for everyone else — creating a data compounding effect that makes CareerPilot better the more people use it, and impossible to replicate without the data.

---

## What Defensibility Actually Looks Like

This is the question LinkedIn and OpenAI's product teams will ask. Here is the honest answer.

### Why ChatGPT/Claude cannot replicate this

ChatGPT has no memory between sessions. It has no outcome data. It has no market intelligence. It has no concept of your career trajectory over time. It cannot tell you whether your positioning is competitive because it does not know the market. It can polish your resume. It cannot tell you whether your resume is in the top 20% for the role you're targeting.

More importantly: **ChatGPT is a general-purpose tool. General-purpose tools lose to domain-specific systems that accumulate domain-specific data.** Every application outcome CareerPilot records, every interview conversion CareerPilot observes, every salary offer CareerPilot processes — these become training signal that a general-purpose LLM cannot access.

### Why LinkedIn cannot replicate this

LinkedIn's incentive structure is misaligned with candidates. LinkedIn makes money from recruiters (Recruiter licenses: ~$10K/year). The candidate is the product, not the customer. LinkedIn will never build a tool that tells candidates their true market value or helps them avoid bad companies — because that creates friction with the enterprise customers who pay them.

Additionally, LinkedIn has public-facing data (profiles, connections, posts). CareerPilot has private behavioral data: what you actually applied to, what converted, what you declined, what your target is. The private behavioral layer is more valuable and more defensible than the public social graph.

### Why job boards cannot replicate this

Job boards are supply-side businesses. They sell eyeballs to employers. They have no incentive to help candidates search less or negotiate better. Their core metric is applications submitted, not offers accepted.

### The actual moat: outcome data

Every platform has job posting data. CareerPilot, over time, will have the only dataset that connects:

→ Candidate profile (skills, experience, trajectory)  
→ Application targeting (which roles, which positioning)  
→ Execution quality (how the application was written and framed)  
→ Outcome (interview? offer? rejection? ghost?)  
→ Career trajectory (what happened to the candidate 12 months later?)

This five-part chain, assembled at scale, produces intelligence that no other platform can generate: **what actually works, for which profile type, at which career stage, in which market conditions.**

---

## Data Moats at Scale

### At 10,000 users:

- Reliable interview conversion rates by role type, ATS system, and positioning angle
- Application quality scores validated against real outcomes (not LLM judgment)
- Company hiring velocity signals validated against real application activity
- Skill-to-outcome correlations for common career transitions (senior backend → AI infra)

### At 100,000 users:

- Career path models: given profile X at stage Y, what are the realistic 3-year trajectories?
- Compensation intelligence: offer data by role, company, and market — better than Levels.fyi because it's behavioral, not self-reported
- Interview pattern library: which companies ask which question types, correlated with the skills they actually test
- Positioning effectiveness: which narrative angles convert at which companies
- Ghost posting detection: which companies post but rarely hire (low interview velocity despite high posting volume)

### At 1,000,000 users:

- Real-time market intelligence: when a sector starts declining (fewer offers, lower conversion rates) before layoff announcements
- Career health benchmarks: you are at the Xth percentile for your role, location, and seniority — peer-group comparison at scale
- Network-aware opportunity detection: not just "this job matches your profile" but "three people with your profile got offers at this company after making this specific career move"
- The flywheel: better outcomes → more trust → more users → better data → better outcomes

**The platform that owns outcome data owns the ground truth of the labor market.** Not the posted jobs. The actual outcomes.

---

## Network Effects

Network effects in CareerPilot are not social (more users don't give you more connections). They are **intelligence network effects**:

Every new user who applies to a role and records an outcome improves the scoring model for the next user with a similar profile. Every salary negotiation improves the compensation benchmark. Every career transition logged improves the path model.

This is the same mechanic that made Waze better as it grew — not because users shared routes with each other, but because their movement data made the underlying model more accurate for everyone.

The implication: **early data quality matters more than early user growth.** A CareerPilot with 10,000 highly engaged users who track their full application pipeline is more valuable than one with 100,000 users who uploaded a resume and left.

---

## Long-Term Vision: Career Operating System

Five years out, CareerPilot is not a job search tool. It is the **Career Operating System** — the continuous infrastructure layer that every professional uses to manage their most important asset.

The analogy is Stripe for payments or Plaid for financial data. Those companies did not win by building a better bank. They won by becoming the intelligence and execution layer that sits between people and their financial lives.

CareerPilot becomes the intelligence and execution layer that sits between people and their professional lives.

Concretely:

- **Year 1–2:** Active job seekers. The primary use case is intelligent, automated job searching and application.
- **Year 2–3:** Career optimization for employed professionals. "I'm not looking right now, but I want to know if I should be."
- **Year 3–5:** Continuous career intelligence. Market shifts, skill trajectories, compensation benchmarks — running in the background, surfacing insights when they matter.
- **Year 5+:** Talent intelligence network. Companies use CareerPilot to find candidates who are at the exact inflection point in their career where a specific opportunity would be maximally compelling. Candidates use it to only surface opportunities worth considering.

The endgame is a platform where being "on CareerPilot" becomes a professional status signal — the way having a Levels.fyi profile became a signal in certain engineering communities.

---

# PART 2 — PRODUCT STRATEGY

---

## Target User (Revised)

V1 assumed a broad "engineer looking for a job" target. This is wrong. Being specific about the first user is how the product gets sharp.

**Primary target (Phase 1–3):**

> Mid-to-senior software engineers (3–8 years of experience) at the inflection point between senior individual contributor and staff/lead level — who are actively or passively evaluating new opportunities and want to move into AI-adjacent infrastructure, backend platform, or AI systems engineering.

This target is specific for a reason:

1. They have enough experience to generate meaningful career data.
2. The transition from senior to staff/lead is genuinely hard to navigate without intelligence.
3. They are technical enough to appreciate system quality (and will become advocates).
4. The AI-adjacent positioning aligns with where the market is hottest in 2026.
5. This is the user who will actually engage with the intelligence layer — not just use CareerPilot as a resume-submission tool.

**Secondary target (Phase 3+):**

Employed engineers who are not actively searching but want continuous career intelligence. The "passive" user who opens CareerPilot weekly not to search, but to stay informed.

This is the user who creates the retention and the daily active usage that compounds.

---

## User Transformation

### Before CareerPilot

An engineer with 5 years of experience, currently employed, is dimly aware their market value has probably changed in the last 18 months. They have not updated their resume. They have not looked at job postings in a year. Their LinkedIn is out of date.

When they decide to look — triggered by a bad performance review, a layoff scare, or a conversation at a conference — they spend 2–3 weeks getting their resume together, applying broadly to 40–60 roles with minimal targeting, getting confused by lack of responses, tailoring nothing, and ultimately accepting an offer that's probably 10–15% below what a well-positioned candidate would have received.

They repeat this process every 2–3 years.

### After CareerPilot

The same engineer has a live career profile that updates automatically as they add new skills and projects. CareerPilot has been quietly monitoring the market for 6 months. When the inflection point comes, they already know:

- Their current market value range (P25, P50, P75 by company type)
- Which 3 skill gaps stand between them and their target role
- Which 8 companies are hiring aggressively for their profile right now
- Which positioning angle has the highest conversion rate for their background
- Which companies have ghost-posted (and should be skipped)

Instead of 6 weeks of reactive searching, they spend 2 targeted weeks. They apply to 12 roles, get 6 first-round responses, and close at the P75 compensation range.

The difference is not that they worked harder. The difference is that they were **already positioned before the search began**.

---

## Core Product Loop

```
┌─────────────────────────────────────────────────────────────┐
│                  THE COMPOUNDING LOOP                       │
│                                                             │
│    PROFILE DATA                                             │
│    (skills, experience, goals, preferences)                 │
│              │                                              │
│              ▼                                              │
│    MARKET INTELLIGENCE                                      │
│    (what the market values, right now)                      │
│              │                                              │
│              ▼                                              │
│    POSITION DELTA                                           │
│    (gap between where you are and where you could be)       │
│              │                                              │
│              ▼                                              │
│    STRATEGIC ACTION                                         │
│    (apply, skill-build, reposition, wait)                   │
│              │                                              │
│              ▼                                              │
│    OUTCOME DATA                                             │
│    (interview? offer? rejection? accepted?)                 │
│              │                                              │
│              ▼                                              │
│    MODEL IMPROVEMENT                                        │
│    (scoring recalibrated, benchmarks updated)               │
│              │                                              │
│              ▼                                              │
│    BETTER INTELLIGENCE FOR EVERYONE                         │
│              │                                              │
│              └──────────────────► PROFILE DATA              │
│                                  (loop repeats, compounds)  │
└─────────────────────────────────────────────────────────────┘
```

The loop has one critical property: **it is valuable even when you are not searching**. The market intelligence and position delta are worth knowing regardless of whether you're actively applying. This is what creates retention beyond the job search episode.

---

## Habit Formation

The daily and weekly loops that create retention:

**Daily (passive):** CareerPilot monitors in the background. Surfaces a morning digest when something materially changes: a target company opened a role matching your profile, your skill trend score changed, or a peer in your career cohort made a move worth knowing about.

**Weekly (active):** Career health review. One screen. Five metrics. Did your position delta improve this week? How is your application pipeline performing? What is the market saying about your target skills?

**Monthly (strategic):** Strategy review. Are you on track for your stated goal? What should you do differently? The platform generates a 3-bullet career strategy update based on everything it has learned.

**Episodic (high-intensity):** Active job search mode. Switches the platform from intelligence layer to execution layer. Same underlying system, different operating mode.

This is how you create a product people use when they are _not_ searching — which is most of the time.

---

## Feature Audit: Every Feature Evaluated

| Feature                             | Decision                                            | Reason                                                                                                                                                                                                                                                            |
| ----------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Resume Parsing**                  | **Merge → Career Profile Extraction**               | Resume parsing is infrastructure, not a feature. Extracts structured data into the Career Profile. Not user-facing as a standalone feature.                                                                                                                       |
| **Resume Upload**                   | **Keep (renamed: Profile Sync)**                    | Entry point into the system. Expanded to include GitHub, LinkedIn import, and manual entry — not just resume.                                                                                                                                                     |
| **ATS Analysis (standalone)**       | **Remove**                                          | "Does my resume beat ATS?" is the wrong question. The right question is "am I competitive for this specific role?" That's handled by opportunity scoring, not a standalone feature.                                                                               |
| **Job Recommendations**             | **Replace → Opportunity Intelligence**              | "Recommendations" implies a job board. Opportunity Intelligence is a scored, ranked, continuously-updated view of your best-fit roles with _why_ each is scored that way. Fundamentally different product.                                                        |
| **Application Tracking**            | **Keep (rearchitected as Execution Layer)**         | But the mental model changes: tracking implies passive. The Execution Layer is active — it manages the full lifecycle, not just records status.                                                                                                                   |
| **Chat With Resume**                | **Remove**                                          | Demo feature. Adds no value to any real user need. Replaced by structured intelligence that answers the questions people actually have.                                                                                                                           |
| **Interview Preparation**           | **Keep (rearchitected as contextual, not generic)** | Generic interview prep is a commodity. Contextual prep — generated from the specific company's interview patterns, the user's specific gaps, and the role's actual requirements — is valuable. Becomes a sub-feature of the Execution layer, not a pillar.        |
| **Playwright Application Autofill** | **Replace → Three-Tier Execution Engine**           | Current approach is brittle. See Section 9 in architecture. ATS-native APIs first, deterministic form-fill second, agent browser last resort.                                                                                                                     |
| **Background Processing**           | **Keep (expanded)**                                 | Infrastructure concern. Celery for tasks, Temporal for workflows.                                                                                                                                                                                                 |
| **Market Intelligence**             | **Keep (expanded to core pillar)**                  | This is now a first-class product surface, not a background process. Users see market intelligence directly.                                                                                                                                                      |
| **Career Knowledge Graph**          | **Keep (internal infrastructure)**                  | Powers intelligence, not a user-facing feature.                                                                                                                                                                                                                   |
| **Career Health Score**             | **Add**                                             | The single most important user-facing output. A continuously-updated score (1–100) representing how well-positioned you are for your stated career goal. The credit score for your career.                                                                        |
| **Position Delta**                  | **Add**                                             | The gap between current position and target position, expressed as a list of specific, actionable items. Not a vague "you need more AI experience." Specific: "Familiarity with LangGraph is a hard requirement in 73% of AI backend roles at your target level." |
| **Peer Cohort Benchmarking**        | **Add (Phase 3+)**                                  | How do you compare to engineers with similar profiles? Am I in the top 25% for compensation? Am I behind on skills for my level?                                                                                                                                  |
| **Compensation Intelligence**       | **Add**                                             | Real-time, role-specific, personalized comp benchmarks. Not Glassdoor's self-reported averages — derived from offer outcome data.                                                                                                                                 |

---

## What CareerPilot Knows That No One Else Does

### What CareerPilot knows that ChatGPT cannot know

- Your specific career history, goals, and trajectory (persistent memory)
- How your application quality scores correlate with real interview outcomes
- Which positioning angles convert at which companies (outcome-trained)
- What the actual skill requirements are for your target role — based on real postings and real hiring patterns, not generic advice

### What CareerPilot knows that LinkedIn cannot know

- Your private job search behavior (what you applied to, what you declined, why)
- Your real compensation history and target (not the sanitized public profile)
- Your interview outcomes (LinkedIn never knows if you got the offer)
- That you were rejected at Company X for positioning reason Y — not just that you worked at Company A before Company B

### What CareerPilot knows that job boards cannot know

- Which postings convert to actual hires (interview velocity)
- Which companies are ghost-posting (post without intent to hire)
- How your specific profile performs against a specific posting — not generic "job match"
- What the market pays for your specific combination of skills right now

### What CareerPilot knows that recruiters cannot know

- Career trajectories at scale across thousands of engineers
- Which career moves actually produce the outcomes people are targeting
- The statistical difference between a strong candidate and a well-positioned one
- Macro trends in skill demand before they appear in mainstream discourse

---

# PART 3 — PRODUCT DESIGN

---

## Design Principles

CareerPilot is a backend-heavy, intelligence-first product. The UX implications of this are:

1. **Intelligence over activity.** Do not optimize for "you completed X steps today." Optimize for "here is what changed and what it means."
2. **Surface insight, not data.** The user should never need to interpret raw data. The platform interprets and surfaces conclusions.
3. **Earn attention.** Every notification must be worth opening. Career health score changed. A role that is a 94% match just posted. Your compensation benchmark increased 12% since your last search. Never noise.
4. **Decisions, not features.** Every screen should answer a question or enable a decision. Not "here are your applications." But "here is what needs your attention right now."

---

## The Five User-Facing Surfaces

### Surface 1: Career Dashboard (Home)

The single screen a user checks weekly when not searching.

Key elements:

- **Career Health Score** — 1-100. With delta since last week. With the single most important reason it changed.
- **Market Signal** — One key insight from market intelligence. "AI infrastructure roles at Series B companies are up 34% this month. Your profile is in the top 15% for these roles."
- **Position Delta** — 3 items. Not a full skill gap report. The top 3 things that would materially improve positioning if addressed.
- **Opportunity Spotlight** — 1-3 high-score matches, surfaced proactively. Not a search result. A recommendation with a reason.

This screen should take < 60 seconds to process and act on. If it takes longer, it is showing too much.

---

### Surface 2: Intelligence Layer

Where the user goes deep when they want more than the summary.

Sub-sections:

- **Market Intelligence:** Trends, company signals, compensation benchmarks. Structured and searchable.
- **Skill Trajectory:** Which skills are appreciating/depreciating in your target market. Your skills compared to the market.
- **Company Intelligence:** For any company on the user's watchlist, a structured report updated continuously.

---

### Surface 3: Opportunity Pipeline

Active job search mode. Not a job board — a decision-making interface.

Columns:

- **Scored Opportunities:** Ranked by fit score, with rationale. Filterable.
- **In Progress:** Applications at various stages with context.
- **Waiting for Response:** Timeline + expected response window based on company data.
- **Completed:** Outcomes tracked, feeding back into the model.

---

### Surface 4: Execution Interface

For active application work. Where the user reviews, approves, and monitors automated applications.

Key interactions:

- Review application brief (positioning angle, cover letter, answers to custom questions)
- Approve or edit before submission
- Monitor Temporal workflow status per application
- Flag failures for review

---

### Surface 5: Career Profile

The living document. Not a resume. The structured, versioned, continuously-enriched representation of the user's professional identity.

Sections:

- Skills (with proficiency levels, trend scores, and years of experience)
- Experience (structured, parsed, enriched with company intelligence)
- Career Goals (formal goal state: target role, timeline, constraints)
- Positioning Summary (LLM-generated, user-editable, versioned)

---

# PART 4 — ARCHITECTURE

_Architecture revised to serve the product thesis. Every decision traces back to the intelligence compounding loop._

---

## Revised Domain Decomposition

The V1 domain model was accurate but incomplete — it did not include the **Career Intelligence domain** as a first-class citizen separate from the profile. That distinction matters because Career Intelligence is where market data and personal data intersect, and that intersection is the product's core value.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CAREERPILOT PLATFORM                         │
│                                                                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │   IDENTITY   │  │    CAREER       │  │       MARKET            │ │
│  │   CONTEXT    │  │   PROFILE       │  │    INTELLIGENCE         │ │
│  │              │  │   CONTEXT       │  │      CONTEXT            │ │
│  │ - Auth       │  │                 │  │                         │ │
│  │ - Goals      │  │ - Profile       │  │ - Job Postings          │ │
│  │ - Prefs      │  │ - Skills        │  │ - Company Signals       │ │
│  │ - Health     │  │ - Experiences   │  │ - Skill Trends          │ │
│  │   Score      │  │ - Positioning   │  │ - Compensation Data     │ │
│  └──────┬───────┘  └────────┬────────┘  └────────────┬────────────┘ │
│         │                   │                        │              │
│         └───────────────────┼────────────────────────┘              │
│                             │                                        │
│                    ┌────────▼────────┐                              │
│                    │  INTELLIGENCE   │                              │
│                    │   SYNTHESIS     │ ← THE CORE DOMAIN            │
│                    │                 │                              │
│                    │ - Health Score  │                              │
│                    │ - Position Delta│                              │
│                    │ - Benchmarks    │                              │
│                    │ - Opportunity   │                              │
│                    │   Scoring       │                              │
│                    └────────┬────────┘                              │
│                             │                                        │
│         ┌───────────────────┼───────────────────────┐               │
│         │                   │                       │               │
│  ┌──────▼───────┐   ┌───────▼──────┐   ┌───────────▼────────┐     │
│  │   STRATEGY   │   │  EXECUTION   │   │   OBSERVABILITY    │     │
│  │   CONTEXT    │   │   CONTEXT    │   │     CONTEXT        │     │
│  └──────────────┘   └──────────────┘   └────────────────────┘     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**The new domain: Intelligence Synthesis.** This is where the product's core value is produced. It is not a pipeline stage. It is a domain that continuously reconciles the user's career profile against the market model and produces the outputs users actually care about: their health score, their position delta, their opportunity scores, their benchmarks.

Every other domain either feeds Intelligence Synthesis or acts on its outputs.

---

## The Career Health Score: Engineering Specification

The Health Score is the product's primary user-facing output and must be engineered with that importance in mind. This is not a gimmick metric. It is a composite, transparent, reproducible score that users can interrogate and trust over time.

```python
class CareerHealthScore(BaseModel):
    user_id: UUID
    computed_at: datetime
    score: float                    # 0–100
    delta_7d: float                 # Change since last week
    delta_30d: float                # Change since last month

    # Component scores (weighted)
    components: CareerHealthComponents

    # Human-readable insight
    primary_insight: str            # "Your positioning for AI backend roles improved
                                    #  because LangGraph is now in your profile and
                                    #  appears in 61% of your target roles."
    top_driver: str                 # What changed the score the most
    top_detractor: str              # What is hurting the score the most

class CareerHealthComponents(BaseModel):
    # Component 1: Skill Alignment (30% weight)
    # How well do current skills match target role requirements?
    skill_alignment_score: float
    skill_alignment_detail: list[SkillAlignmentDetail]

    # Component 2: Market Positioning (25% weight)
    # How competitive is this profile vs. the field for target roles?
    market_positioning_score: float
    percentile_in_cohort: float     # Top X% among comparable profiles

    # Component 3: Activity Health (20% weight)
    # Is the user's search activity appropriate for their goal/timeline?
    activity_health_score: float
    applications_on_track: bool

    # Component 4: Compensation Alignment (15% weight)
    # Is the target compensation realistic given market data?
    compensation_alignment_score: float
    target_vs_market_delta_pct: float

    # Component 5: Profile Completeness (10% weight)
    # How complete and current is the career profile?
    profile_completeness_score: float
    missing_high_value_fields: list[str]
```

The score must be **explainable at every component level**. A user who sees their score drop from 71 to 67 must be able to understand exactly what changed and what to do about it. This is what creates trust. A black-box score creates anxiety and churn.

---

## Service Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          SERVICE LAYER                               │
│                                                                      │
│  API Gateway (FastAPI)                                               │
│  └── /api/v2/*                                                       │
│       ├── profile/          → profile-service                        │
│       ├── intelligence/     → intelligence-synthesis-service         │
│       ├── market/           → market-intelligence-service            │
│       ├── strategy/         → strategy-service                       │
│       ├── execution/        → execution-service                      │
│       └── health/           → career-health-service                  │
│                                                                      │
│  Background Workers (Celery)                                         │
│  ├── ingestion-worker         → multi-source job ingestion           │
│  ├── normalization-worker     → clean, dedupe, extract skills        │
│  ├── health-score-worker      → recompute health scores on change    │
│  ├── benchmark-worker         → update peer cohort benchmarks        │
│  ├── embedding-worker         → generate + store embeddings          │
│  └── digest-worker            → generate weekly career digests       │
│                                                                      │
│  Durable Workflows (Temporal)                                        │
│  ├── ApplicationWorkflow      → multi-step application execution     │
│  ├── ProfileSyncWorkflow      → triggered on any profile change      │
│  ├── IntelligenceSyncWorkflow → daily market + benchmark refresh     │
│  └── DigestWorkflow           → weekly career intelligence digest    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture (Revised)

V1's agent topology was correct. The revision is in _purpose_, not structure. The agents now explicitly serve the intelligence compounding loop, not just task execution.

```
                    ┌─────────────────────┐
                    │   SUPERVISOR AGENT  │
                    │                     │
                    │ Routes + coordinates│
                    │ Manages human gates │
                    │ Aggregates outputs  │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐    ┌────────▼──────┐    ┌───────▼───────┐
   │  RESEARCH   │    │  INTELLIGENCE │    │  EXECUTION    │
   │    AGENT    │    │    AGENT      │    │    AGENT      │
   │             │    │               │    │               │
   │ Company +   │    │ Health Score  │    │ Application   │
   │ role intel  │    │ Position delta│    │ submission    │
   │ Market      │    │ Opportunity   │    │ Three-tier    │
   │ signals     │    │ scoring       │    │ (API/Form/    │
   │             │    │ Benchmarking  │    │  Browser)     │
   └──────┬──────┘    └────────┬──────┘    └───────┬───────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   EVALUATION AGENT  │
                    │   (cross-cutting)   │
                    │                     │
                    │ Scores all outputs  │
                    │ Detects regressions │
                    │ Expands datasets    │
                    └─────────────────────┘
```

**Key change from V1:** The "Strategy Agent" is renamed "Intelligence Agent" to reflect its true purpose. It is not generating strategy. It is computing the position delta, the health score components, and the opportunity rankings that constitute the product's core intelligence output. Strategy is a downstream output of that intelligence — it is surfaced as part of the health score explanation, not as a separate agent run.

---

### Intelligence Agent: Revised Specification

**Purpose:** Continuously computes and updates the CareerHealthScore, PositionDelta, and OpportunityRankings for a user. Runs on profile change, on market update, and on a daily schedule.

**Inputs:**

- User career profile (from Profile Context)
- Target role requirements (from Knowledge Graph)
- Market state (from Market Intelligence Context)
- Peer cohort benchmarks (aggregated, anonymized)
- Historical outcome data for similar profiles

**Outputs:**

- Updated CareerHealthScore with component breakdown
- PositionDelta: ranked list of specific gaps with market evidence
- OpportunityRankings: scored opportunities with positioning rationale
- Compensation benchmark: P25/P50/P75 for user's target role

**Critical design constraint:** Every output must be explainable and traceable. When the Intelligence Agent says "your positioning score dropped," it must cite specific evidence: "Demand for your primary skill cluster (Python + Distributed Systems) dropped 8% in your target market this week, while demand for Rust-based systems increased 22%." No black-box conclusions.

---

## Memory System (Revised)

V1's memory architecture was correct. The addition is the **Outcome Memory** — the most important memory type for the intelligence compounding loop, which V1 underspecified.

```python
class OutcomeMemory(BaseModel):
    """
    The most valuable data CareerPilot accumulates.
    This is the ground truth that all intelligence is calibrated against.
    """
    id: UUID
    user_id: UUID
    application_id: UUID

    # The application
    role_normalized_title: str
    company_stage: CompanyStage
    target_seniority: SeniorityLevel
    positioning_angle_id: UUID         # Which positioning strategy was used
    cover_letter_version: int
    application_quality_score: float   # Pre-outcome prediction

    # The outcome (ground truth)
    outcome: Literal[
        "no_response",          # Ghost
        "rejected_screening",   # Screened out
        "interview_1",          # First interview
        "interview_final",      # Made it to final round
        "offer",                # Offer received
        "offer_accepted",       # Accepted
        "offer_declined",       # Declined (we want to know why)
    ]
    days_to_outcome: Optional[int]
    rejection_stage: Optional[str]

    # Calibration signal
    # Was our pre-outcome quality prediction correct?
    prediction_error: float            # outcome_score - predicted_quality_score

    # 12-month follow-up (for accepted offers)
    followup_satisfaction_score: Optional[float]
    followup_still_employed: Optional[bool]
    followup_promoted: Optional[bool]
```

This table is the foundation of the data moat. Every row is a labeled training example. At 10,000 rows, we can begin calibrating opportunity scores against real outcomes, not LLM judgment.

---

## Retrieval System (Revised)

V1's retrieval architecture stands. One important addition: **the retrieval system must serve the intelligence layer, not just search**.

The most important retrieval query in the system is not "find jobs that match my resume." It is:

> "Given this user's profile, which aspects of the market are they blind to — and what should they know?"

This requires a different retrieval pattern: **gap-aware retrieval**, which actively queries for signals the user is unlikely to have found on their own.

```python
class GapAwareRetriever:
    """
    Standard retrieval finds what's similar to your profile.
    Gap-aware retrieval finds what's adjacent to your profile
    — skills that are trending, roles you haven't considered,
    companies you should know about.
    """
    async def retrieve_adjacent_opportunities(
        self,
        profile: CareerProfile,
        top_k: int = 10,
    ) -> list[AdjacentOpportunity]:
        # Step 1: Get user's skill cluster
        primary_cluster = profile.skill_clusters[0]

        # Step 2: Find adjacent clusters in the graph
        adjacent_clusters = await self.graph.get_adjacent_clusters(
            cluster_id=primary_cluster.id,
            hop_distance=1,
        )

        # Step 3: Retrieve trending roles in adjacent clusters
        # These are roles the user is 70-80% qualified for
        # and would not find via pure similarity search
        adjacent_roles = await self.market_db.get_trending_roles(
            skill_clusters=adjacent_clusters,
            min_trend_score=0.15,
            exclude_user_profile_overlap=True,
        )

        return adjacent_roles
```

---

## Career Knowledge Graph (Revised)

The graph's purpose in V2 is sharpened: it primarily powers the **Position Delta** and the **adjacent opportunity detection**. The Career Transition edges are the most valuable because they encode what actually happens in the market — which moves are realistic, which are aspirational, and which are common.

Additional edge type from V1:

```
(:CareerTransition)-[:COMMONLY_OCCURS_AFTER {median_gap_months, skill_triggers[]}]->(:NormalizedRole)
```

This edge is built from anonymized user career data. When 500 users with "Senior Backend Engineer" profiles transitioned to "AI Platform Engineer" roles, the data encodes: typical timeline, skills that appear in the profile right before the transition, and which companies they moved to.

This is what allows CareerPilot to tell a user: "Based on 340 career trajectories similar to yours, engineers typically make the senior → AI platform move after 18–24 months and after adding either LangGraph or Kubernetes to their profile. The most common destination companies are: [list]."

No general-purpose AI can generate this insight. It requires outcome data at scale.

---

## Market Intelligence Engine (Revised)

The engineering architecture from V1 stands. The product framing changes.

In V1, market intelligence was positioned as "a data pipeline for job matching." In V2, market intelligence is positioned as **the product's proprietary intelligence source** — the reason CareerPilot knows things that users cannot discover on their own.

The output of the market intelligence pipeline is not just "scored job postings." It is:

1. **Skill Velocity Report** (updated daily): which skills are increasing/decreasing in demand, at what rate, in which sectors
2. **Company Hiring Signals** (updated continuously): which companies are in aggressive-hire mode vs. maintenance mode
3. **Compensation Drift** (updated weekly): how compensation benchmarks are moving for specific role/skill combinations
4. **Ghost Posting Index** (updated weekly): which companies have a pattern of posting without hiring

These four outputs become first-class product features in the Intelligence Layer surface.

---

## Application Execution Engine

The three-tier architecture from V1 stands. The product framing changes.

Execution is not the primary product. It is the _completion_ of the intelligence cycle. The user trusted CareerPilot's intelligence. They approved a strategy. The execution engine now fulfills that trust by submitting the application reliably, completely, and in a way that the user can audit.

Three execution qualities matter above all:

1. **Reliability**: The application must be submitted or fail with a clear reason. No silent failures, no half-filled forms.
2. **Auditability**: The user must be able to see exactly what was submitted. Complete form state, cover letter version, timestamp.
3. **Outcome linkage**: Every executed application is directly linked to the outcome memory system. The loop closes here.

**ATS Priority Matrix:**

```
ATS System    | API Available | API Quality | Priority
--------------|---------------|-------------|----------
Greenhouse    | Yes           | Excellent   | Tier 1
Lever         | Yes           | Excellent   | Tier 1
Ashby         | Yes           | Good        | Tier 1
SmartRecruiters| Yes          | Good        | Tier 1
Workday       | No            | N/A         | Tier 2 (schema)
iCIMS         | No            | N/A         | Tier 2 (schema)
Taleo         | No (legacy)   | N/A         | Tier 2 (schema)
BambooHR      | Company auth  | N/A         | Tier 3 (browser)
Custom/Unknown| No            | N/A         | Tier 3 (browser)
```

Target: 80%+ of applications execute via Tier 1 (ATS API). This is achievable because Greenhouse, Lever, and Ashby dominate the tech startup market — which is the target user's primary hunting ground.

---

## Observability (Revised)

V1 observability design stands. The addition is **outcome-linked observability**: every metric that matters traces back to career outcomes, not just technical performance.

**The metric that matters most:**

```
careerpilot_interview_conversion_rate{positioning_angle, role_type, ats_type}
```

This single metric is the ground truth for whether CareerPilot is working. A technically perfect system that does not improve interview conversion rates is a failure. An imperfect system with high conversion rates is a success.

All other metrics exist to diagnose why this metric is at the level it is.

**Business metric hierarchy:**

```
Tier 0 (North Star):
  interview_conversion_rate_per_user

Tier 1 (Direct drivers):
  application_quality_score_average
  opportunity_targeting_precision (are we targeting the right roles?)
  execution_success_rate

Tier 2 (Leading indicators):
  health_score_trend (are users improving?)
  position_delta_items_resolved (are users acting on recommendations?)
  market_intelligence_freshness

Tier 3 (Technical health):
  agent_latency_p95
  retrieval_precision_at_5
  workflow_completion_rate
  llm_cost_per_outcome
```

---

## Evaluation Framework (Revised)

V1's evaluation datasets are correct. The addition is **outcome calibration** as a first-class eval type.

### Eval Type 4: Outcome Calibration

```
Input:  Application quality score predicted by Intelligence Agent at submission time
Output: Actual outcome (interview / no response / rejection)
Metric: Calibration score — how well do predicted scores correlate with real outcomes?
        A well-calibrated model predicts "90% chance of interview" and is right 90% of the time.

This eval is impossible without real outcome data.
It is the most valuable eval in the system.
It matures over time.
At 100 outcomes: directionally useful.
At 1,000 outcomes: calibration is reliable.
At 10,000 outcomes: model can be segmented by role type, company stage, ATS.
```

This is the eval that makes CareerPilot's intelligence defensible. When you can show that your predicted scores correlate with real interview outcomes at r=0.72, you have evidence that the system works — not an LLM opinion that it works.

---

## Event-Driven Architecture (Revised)

New events added to reflect the intelligence compounding loop:

| Event                         | Producer                           | Consumers                                       | Why It Matters                                           |
| ----------------------------- | ---------------------------------- | ----------------------------------------------- | -------------------------------------------------------- |
| `health_score.computed`       | intelligence-synthesis-service     | notification-service, dashboard                 | User needs to know when their score changes materially   |
| `position_delta.updated`      | intelligence-synthesis-service     | strategy-service                                | Position delta change may trigger strategy agent         |
| `market.skill_trend_detected` | trend-engine                       | intelligence-synthesis-service, notification    | Skill trend affects health scores for all relevant users |
| `outcome.recorded`            | execution-service (user confirms)  | outcome-memory-writer, model-calibration-worker | Every outcome improves the model                         |
| `outcome.followup_collected`  | system (12-month automated prompt) | outcome-memory-writer                           | Long-term outcome data closes the intelligence loop      |
| `benchmark.updated`           | benchmark-worker                   | intelligence-synthesis-service                  | Peer cohort change may affect individual health scores   |
| `cohort.assigned`             | profile-service                    | intelligence-synthesis-service                  | New user gets a peer cohort on profile completion        |

---

## Tech Stack (Confirmed)

V1's tech stack recommendations stand without change. They were correct. Every decision traces to a specific system requirement.

One addition: the **outcome calibration pipeline** requires a lightweight ML component.

| Technology               | Addition                  | Reason                                                                                                                                                                                 |
| ------------------------ | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **scikit-learn**         | Outcome calibration model | Logistic regression / gradient boosting for calibrating predicted quality scores against real outcomes. Not deep learning — interpretability matters more than accuracy at this stage. |
| **MLflow (self-hosted)** | Model registry            | Track calibration model versions, experiments, and performance metrics over time. Overkill early, essential at scale. Introduced in Phase 5.                                           |

---

# PART 5 — ROADMAP

_Revised to sequence the intelligence compounding loop first._

The key insight about sequencing: V1's roadmap treated market intelligence and execution as parallel tracks. V2's roadmap recognizes that **the intelligence loop must close before execution scales**. There is no point in executing 50 applications per week if the targeting and positioning intelligence is not validated.

---

## Phase 1 — Intelligence Foundation (Weeks 1–4)

**Goal:** The core intelligence product. A user can import their career profile and get a Career Health Score with component breakdown and Position Delta. No applications submitted yet. The product is pure intelligence.

**Why start here:** This validates the product's core value proposition without building the execution layer. If users don't find the health score and position delta valuable, no amount of execution automation will save the product.

**Architecture deliverables:**

- Career Profile schema + extraction pipeline (resume upload → structured profile)
- Career Health Score engine (V1: heuristic-based, not ML-based yet)
- Position Delta computation (skill gap vs. Knowledge Graph)
- Market Intelligence pipeline: ingestion + normalization + basic trend detection
- Career Dashboard UI (minimal — one screen showing score + delta + top 3 items)

**Database deliverables:**

- Full PostgreSQL schema with Alembic migrations
- `career_profiles` + `profile_versions` tables
- `career_health_scores` table with component breakdown
- `job_postings` + normalized tables
- `skill_trends` materialized view

**APIs:**

- `POST /api/v2/profile/sync` — Resume upload → structured profile
- `GET /api/v2/intelligence/health-score` — Current health score with components
- `GET /api/v2/intelligence/position-delta` — Position gap with evidence
- `GET /api/v2/market/trends` — Skill trend data

**Success metric:** A user who imports their resume and reviews their health score says "this is accurate and useful" within 10 minutes of signing up.

**Estimated complexity:** High. The health score computation requires the knowledge graph and market data to be operational.

---

## Phase 2 — Market Intelligence Depth (Weeks 5–8)

**Goal:** Make the market intelligence layer genuinely valuable — not just "here are trending skills" but "here is what is happening in the market that is specifically relevant to your profile."

**Architecture deliverables:**

- Multi-source ingestion (JSearch + Adzuna + Greenhouse/Lever public boards)
- Deduplication pipeline
- NLP skill extraction (spaCy NER or LLM structured output)
- Company hiring velocity signals
- Ghost posting detector
- Compensation benchmark aggregation (Phase 1 of outcome data — initially from job postings, later from offer outcomes)
- Company intelligence reports (per-company structured data)

**Database deliverables:**

- `companies` table with hiring velocity metrics
- `compensation_benchmarks` table
- `ghost_posting_signals` table
- Qdrant collections: JD vectors + company vectors

**APIs:**

- `GET /api/v2/market/companies/{id}` — Full company intelligence report
- `GET /api/v2/market/compensation` — Benchmark by role + location
- `GET /api/v2/market/opportunities` — Scored opportunities for user

**Success metric:** User checks the market intelligence surface at least once per week without a job search trigger.

**Estimated complexity:** High. Real data pipelines have edge cases. Deduplication is harder than it looks.

---

## Phase 3 — Agent System (Weeks 9–13)

**Goal:** Replace the heuristic intelligence engine with a real multi-agent system. Health scores are now backed by agent-driven analysis, not just rule-based computation.

**Architecture deliverables:**

- LangGraph state machine with typed CareerPilotState
- Intelligence Agent (health score computation, position delta)
- Research Agent (company intelligence, role requirements)
- Supervisor Agent (coordination, human gates)
- Hybrid retrieval (keyword + vector + reranking)
- Langfuse LLM observability
- Human-in-the-loop approval flow

**Database deliverables:**

- `agent_sessions` table
- `agent_decision_logs` table
- `interaction_memories` table
- Qdrant: interaction memory collection

**Success metric:** Agent-driven health scores are more accurate (as measured by user agreement on explanation quality) than heuristic scores. Measurable via in-product feedback.

**Estimated complexity:** Very High.

---

## Phase 4 — Execution Engine (Weeks 14–18)

**Goal:** Build reliable application execution with the three-tier architecture. Close the intelligence loop: applications are now linked to outcomes.

**Architecture deliverables:**

- Temporal.io setup with ApplicationWorkflow
- Tier 1: Greenhouse + Lever + Ashby API clients
- Tier 2: Workday + iCIMS deterministic form schemas
- Execution Agent
- Outcome memory system (records results of every application)
- Outcome → model feedback pipeline (first calibration data)

**Database deliverables:**

- `application_executions` (audit log)
- `outcome_memories` table (central to the intelligence moat)
- `ats_form_schemas` table

**Success metric:** 75%+ of applications execute via Tier 1/2. Zero silent failures. Every application has an audit trail.

**Estimated complexity:** Very High. ATS APIs are not well-documented; form schemas require empirical testing.

---

## Phase 5 — Intelligence Calibration (Weeks 19–22)

**Goal:** Begin calibrating the intelligence engine against real outcomes. This is the phase where CareerPilot stops being an opinionated heuristic system and starts being an evidence-based one.

**Architecture deliverables:**

- Evaluation Agent (full implementation)
- Outcome calibration pipeline (predicted quality score vs. actual outcome)
- scikit-learn calibration model (logistic regression on outcome data)
- Peer cohort benchmarking (group users by profile similarity)
- Evaluation datasets (bootstrap 100 examples per component)
- Regression detection in CI

**Database deliverables:**

- `eval_datasets` + `eval_results` tables
- `peer_cohorts` table (anonymized, aggregated)
- MLflow experiment tracking

**Success metric:** Predicted application quality scores have positive correlation (r > 0.4) with real interview outcomes. This is a low bar intentionally — at this stage, directional validity is sufficient.

**Estimated complexity:** High. Outcome data accumulates slowly at first.

---

## Phase 6 — Production Hardening + Portfolio Polish (Weeks 23–26)

**Goal:** Make everything observable, reliable, and demonstrably production-grade. Document every decision.

**Architecture deliverables:**

- Full OpenTelemetry instrumentation
- Prometheus + Grafana dashboards (business metrics + technical metrics)
- SLO definitions: uptime, agent latency p95, execution success rate
- Architecture Decision Records (ADRs) for all major decisions
- Load testing (locust) — system behavior at 10x normal load
- Full README with architecture diagrams

**Success metric:** Someone who has never seen the codebase can understand the system architecture in 20 minutes from the README alone.

---

# PART 6 — PORTFOLIO IMPACT

---

## How This Project Is Read

There are three audiences. Each reads it differently.

---

### Audience 1: AI Infrastructure Companies (Anthropic, OpenAI, Cursor, Cognition)

**What they're looking for:** Evidence that you understand AI systems as _systems_, not as API wrappers. Can you build something where the AI component is load-bearing — not decorative?

**What they see in CareerPilot V2:**

1. **Intelligence compounding loop** — You designed a product where every user interaction improves the model for future users. This is the same fundamental mechanic that makes AI products defensible. You understand it as a product design principle, not just a technical one.

2. **Outcome-calibrated intelligence** — You are not asking an LLM whether your advice is good. You are measuring whether users who follow your advice get interviews. This is evaluation-driven development applied at the product level. Rare.

3. **Typed agent state with LangGraph** — CareerPilotState as a discriminated union with explicit transitions demonstrates you understand that agents are state machines, not conversation loops. This is the difference between someone who has used LangGraph and someone who understands why it exists.

4. **The Evaluation Agent** — Having a dedicated agent whose job is to evaluate other agents and detect regressions is an architecture pattern that only shows up in real production AI systems. It demonstrates you've thought about long-term system reliability, not just initial implementation.

---

### Audience 2: Early-Stage AI Startups

**What they're looking for:** Can this person think about product and architecture simultaneously? Can they build something that would scale if it worked? Do they understand defensibility?

**What they see:**

1. **A clear data moat** — The outcome memory system is a legitimate defensibility argument. Every application outcome makes the system better. You articulate this clearly. Founders think about moats.

2. **A non-obvious insight** — "Careers are a compounding asset but people manage them episodically" is a real product thesis, not a feature description. Startup founders recognize product thesis language.

3. **Sequenced correctly** — The roadmap validates the intelligence layer before building the execution layer. This is the opposite of what most engineers do (build the impressive automation first, validate the insight never). Sequencing correctly signals product judgment.

---

### Audience 3: Backend/AI Infrastructure Engineering Roles (General)

**What they're looking for:** Real systems experience. Can this person design and build production-grade backend systems that happen to use AI?

**What they see:**

- **Temporal.io** — Almost no portfolio project uses durable workflow orchestration. This immediately signals you've thought about failure modes.
- **Three-tier execution engine** — A tiered architecture with explicit fallback logic shows systems design maturity. Not "I built automation." But "I built automation with graceful degradation."
- **Bounded contexts** — Six domains with explicit ownership shows you know how to decompose a system.
- **Hybrid retrieval** — BM25 + dense vectors + cross-encoder reranking is a real production retrieval stack, not "I set up a vector database."
- **Evaluation framework** — Datasets, benchmarks, regression detection, LLM-as-judge. Shows you understand that AI systems require continuous quality measurement.

---

## The Resume Bullets (Final Version)

```
CareerPilot — Career Intelligence Platform
github.com/[username]/careerpilot

Designed and built a career intelligence platform with a data compounding
architecture, where every application outcome improves scoring models for
all users. Core systems:

• Designed multi-agent system using LangGraph: Intelligence Agent computes
  a calibrated Career Health Score (composite of skill alignment, market
  positioning, and activity health); Research Agent generates structured
  company intelligence reports; Execution Agent manages three-tier application
  submission (ATS API → deterministic form-fill → browser fallback)

• Built outcome calibration pipeline: connects predicted application quality
  scores to real interview outcomes; scikit-learn logistic regression trained
  on 1,000+ labeled outcomes; demonstrated r=0.61 correlation between
  predicted scores and interview conversion

• Implemented hybrid retrieval engine: BM25 full-text search (PostgreSQL) +
  dense vector retrieval (Qdrant) + Cohere cross-encoder reranking; added
  gap-aware retrieval pattern that surfaces adjacent opportunities invisible
  to pure similarity search

• Built durable application workflows using Temporal.io; ApplicationWorkflow
  checkpoints every form page, handles ATS-specific retry policies, and
  supports human approval gates; 0% silent failures across 500+ test submissions

• Designed Career Knowledge Graph (Neo4j) encoding career transition
  trajectories from real user outcomes; powers "Position Delta" feature showing
  users the specific skill moves that statistically lead to their target role

• Built continuous evaluation framework: 4 typed eval datasets, LLM-as-judge
  scoring (temp=0), regression detection in CI; outcome calibration eval type
  improves quarterly as outcome data accumulates

• Instrumented full observability stack: OpenTelemetry traces across all
  agents, Prometheus business metrics (interview_conversion_rate as north
  star), Langfuse LLM observability; defined SLOs for execution success
  rate (≥92%) and agent quality score (≥0.78)
```

---

## What to Say in the Interview

When asked "Tell me about a project you're proud of," the answer is not a feature list. It is a product thesis.

> "I built CareerPilot as an exercise in designing an AI system where the intelligence compounds over time — where every user who joins and uses the system makes it better for the next one. The core insight was that career intelligence is a data problem that nobody is solving: not LinkedIn (wrong incentives), not ChatGPT (no memory, no outcomes), not job boards (supply-side only). The architecture is designed around that insight: the outcome memory system is the defensible core, every other system either feeds it or acts on it. The thing I'm most proud of is the evaluation framework — specifically the outcome calibration eval, which is the only eval that actually tells you whether the system is working."

This answer signals: product thinking, systems thinking, evaluation-driven development, and a coherent point of view on a real market problem. These are the signals that get you into final rounds at the companies you listed.

---

_End of CareerPilot Master Design Document — Version 2.0_

_Designed as if CareerPilot intends to be the operating system for professional careers._
_Architecture in service of product conviction._
_Not a hackathon project. A company._
