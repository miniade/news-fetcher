# GitHub Project Discovery for Daily News — v1 Design

## Goal
Add a new discovery path to `news-fetcher` that surfaces **GitHub projects worth attention today** and emits them as normal news items in the daily digest.

## Non-goals
v1 does not aim to:

- perfectly model long-term project quality
- cover all of GitHub comprehensively
- depend on external social/news corroboration
- introduce a brand-new final output format
- rely on opaque ranking models

## Product Definition
A “worth attention today” GitHub project is **not just a repo with fast star growth**.
v1 should rank projects using a combination of:

- **growth**: unusual attention today
- **activity**: signs the project is actively moving
- **quality/maturity**: basic signals that the repo is real and usable
- **newsworthiness**: enough context to justify inclusion in a daily news digest

The output should be a **news item**, not a leaderboard entry.

## High-level Architecture
Use a two-stage model:

1. **GitHub project candidate discovery**
   - discover candidate repos from GitHub signals
   - enrich each candidate with metadata and ranking signals

2. **News item mapping**
   - transform selected candidates into normal `news item` objects
   - feed them into the existing ranking/explanation/output pipeline

This keeps discovery logic separate while maximizing reuse of the current output system.

## Candidate Signals

### Growth signals
Primary entry condition for discovery.

Examples:
- stars gained today
- relative growth versus recent baseline
- optional supporting growth indicators such as forks/watchers if available

### Activity signals
Used to reduce false positives from stale repos receiving temporary attention.

Examples:
- recent commits
- recent release
- recent default-branch update
- optional issue/discussion activity

### Quality / maturity signals
Used for noise reduction.

Examples:
- repository description exists
- topics exist
- license exists
- README/docs presence
- basic repo structure looks legitimate

### Newsworthiness signals
Used to justify why the repo belongs in a daily digest.

Examples:
- today’s growth is meaningfully above baseline
- project belongs to a clearly recognizable theme
- reasons can be expressed in one sentence

## Data Model

### Internal: GitHub project candidate
Suggested fields:

- `repo_full_name`
- `repo_url`
- `owner`
- `name`
- `description`
- `primary_language`
- `topics`
- `stars_total`
- `stars_today`
- `growth_signals`
- `activity_signals`
- `quality_signals`
- `discovery_score`
- `selection_reasons`
- `selection_adjustments`
- `discovered_at`

### Output: news item
Selected candidates should be mapped into the existing news item shape with:

- `title`
- `url`
- `summary`
- `source_type=github_project`
- `selection_reasons`
- `selection_adjustments`
- metadata preserving repo-specific fields

## Ranking Strategy
Use a **rule-based composite score** in v1.

Guiding principles:

- growth is the gateway
- activity and quality reduce noise
- newsworthiness helps final selection and explanation
- explanations must stay human-readable

Do not start with a black-box model.

## Output Strategy
GitHub project discoveries should be rendered as standard news items.

Expected properties:
- title reads like a news headline, not a leaderboard label
- summary explains both what the repo is and why it matters today
- reasons are preserved structurally for later explanation/debugging

## Implementation Plan

### Step 1 — candidate schema
Define the candidate object and source contract.

### Step 2 — candidate acquisition
Build the path that finds repos with meaningful same-day attention.

### Step 3 — metadata enrichment
Add activity, quality, and descriptive signals needed for ranking and explanation.

### Step 4 — ranking and explanation
Compute the v1 score and generate structured reasons.

### Step 5 — news item mapping
Convert selected repos into normal news items.

### Step 6 — integration and caps
Integrate into the existing pipeline, with limits so GitHub project items do not dominate the digest.

## Verification

### Functional
- the system can produce candidate repos for a given day
- selected repos can be emitted as news items

### Quality
- top results are not obviously low-quality noise
- explanations are not reducible to “it gained stars quickly”

### Regression
- existing sources continue to work
- default output remains stable
- absence or disablement of the GitHub project path does not break normal runs

## Proposed Issue Stack

### Issue 1 — Define GitHub project candidate schema and source contract
- Goal: define the internal representation for GitHub project discovery candidates and the contract by which they enter the pipeline
- Deliverables: candidate field list, source contract notes, candidate-to-news-item boundary notes
- Verification: later stages can consume the candidate shape without inventing fields

### Issue 2 — Build same-day GitHub project candidate acquisition
- Goal: create the acquisition path that discovers repositories receiving meaningful same-day attention on GitHub
- Deliverables: candidate acquisition path, initial candidate pool, basic growth metadata
- Verification: a run for a given day yields a non-empty and plausible candidate set

### Issue 3 — Enrich GitHub project candidates with activity, quality, and metadata
- Goal: enrich discovered candidates with the metadata needed for ranking and explanation
- Deliverables: enriched candidate objects, structured activity/quality/descriptive signals
- Verification: enriched candidates contain enough information for explanation beyond raw growth

### Issue 4 — Implement rule-based ranking and explanation for GitHub project discovery
- Goal: rank enriched candidates using a v1 composite score and generate structured selection reasons
- Deliverables: ranked candidate list, structured reasons for inclusion
- Verification: top-ranked results appear reasonable and explainable

### Issue 5 — Map selected GitHub project candidates into normal news items
- Goal: transform selected GitHub project candidates into standard news items that can flow through the existing output pipeline
- Deliverables: candidate-to-news-item mapping, standard news items for GitHub projects
- Verification: generated items read like news entries rather than raw repo records

### Issue 6 — Add integration caps and regression checks for GitHub project items
- Goal: integrate GitHub project news items safely into the daily digest without degrading the existing news experience
- Deliverables: integration limits/caps, mixing policy, regression coverage
- Verification: GitHub project items do not flood the digest and existing sources remain stable

## Open Questions
These can stay open for v1 unless they block implementation:

- exact growth baseline definition
- whether to normalize by repo size/age
- whether to incorporate external corroboration later
- how aggressively GitHub project items should mix with other news categories
