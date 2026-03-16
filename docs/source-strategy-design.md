# Source Strategy Design Draft

## Status

Draft for implementation planning. This document proposes product and technical changes to improve candidate acquisition quality before improving downstream ranking quality.

## Context

The current `news-fetcher` pipeline is:

`fetch -> normalize -> dedup -> cluster -> rank -> diversify -> summarize -> output`

That pipeline is already suitable for correctness and basic ranking behavior. The next product gap is earlier in the funnel: many configured sources only expose their newest items, so the system often starts with a weak candidate pool. If acquisition is weak, post-fetch ranking can only choose the best among whatever happened to be fetched, not the best items a reader would have wanted to see.

This design therefore treats source strategy as a first-class concern.

## 1. Problem Statement

### Hot content vs valuable-to-read content

`Hot content` means content that is currently fresh, rapidly shared, or prominently surfaced by an upstream platform.

`Valuable-to-read content` means content that is actually worth a reader's attention. That can include:

- high-information updates
- consequential events
- technically important releases or changelogs
- strong explainers or analyses
- broadly corroborated developments
- niche items that match a user's interests

These overlap, but they are not the same objective. A platform can make something hot because it is recent, sensational, or broadly viral. A reader may still prefer something less viral but more decision-relevant or more information-dense.

### Why post-fetch ranking alone is insufficient

Improving only downstream ranking is insufficient when the candidate pool is weak.

Common failure mode:

1. The source only exposes the latest 20-50 items.
2. Those items are mostly routine, low-signal, or redundant.
3. The ranker scores them correctly relative to each other.
4. The final output is still mediocre because stronger candidates were never fetched.

In other words, ranking quality is upper-bounded by acquisition quality. A good ranker cannot recover articles that were never in the pool.

### Two-layer model

The product should use a two-layer model:

1. `Upstream candidate acquisition quality`
   - Fetch the best available candidates from each source type using the strongest observable upstream signal.
   - Prefer explicit source-level strategies such as trending, frontpage, curated, changelog, or community-ranked over a generic "latest" fetch when those strategies exist.
2. `Downstream reading-value selection`
   - After candidate acquisition, apply deduplication, clustering, ranking, diversity, and explanation to choose what is most worth reading.

The first layer determines whether the pool contains good options at all. The second layer determines which of those options to show.

## 2. Source Taxonomy

The taxonomy below is intentionally practical. It focuses on what the system can usually observe from outside the platform, not on internal ranking algorithms we cannot inspect.

| Source type | Typical current signal | Stronger acquisition strategy | Is high-value candidate capture realistic? | Fallback when not realistic | Difficulty / risk |
| --- | --- | --- | --- | --- | --- |
| Plain RSS / Atom media feeds | Reverse-chronological items, publish time, title, summary | Usually limited. If the publisher offers multiple feeds, choose better feed classes: topic feeds, editor picks, most-read feeds, newsletters, or section feeds instead of one global latest feed | Low to medium. Only realistic when the publisher exposes non-latest feed variants | Treat as `latest`; lower source contribution caps; rely on cross-source corroboration and downstream rerank | Low difficulty, low product upside unless better feed variants exist |
| Official blogs / changelogs / release feeds | Publish time, title, sometimes category labels | Prefer release notes, changelog feeds, security advisories, "what's new", tagged product feeds, or versioned release pages instead of general blog feeds | High for domains where official updates are inherently valuable | If only latest exists, keep as `latest` but assign strong source/topic weights because official updates can still be important | Low to medium difficulty, low risk |
| Community-ranked sources (HN / Reddit-like) | Score, comments, rank position, age, frontpage/new/best listing | Fetch from ranked listing endpoints or pages: frontpage, best, top for time window, rising, topical communities | High. These sources often expose public ranking or engagement proxies directly | If APIs are unavailable, scrape public list pages conservatively; otherwise fall back to latest plus stronger downstream source weighting | Medium difficulty, medium operational risk if scraping is required |
| Platform-trending sources (Bilibili / YouTube-like) | View count, like count, comment count, rank position, "trending" pages, sometimes category charts | Prefer public trending/popular/category charts, creator feeds for trusted channels, or engagement-proxy snapshots over plain upload chronology | Medium. Realistic only when public trend surfaces or stable engagement metadata are observable | Use `high_engagement_proxy` from recent uploads, limit per-source contribution, and treat popularity as one signal not the objective | Medium to high difficulty, medium to high fragility |
| HTML pages without explicit ranking metadata | Link order on page, section placement, headings, timestamps | Use page structure as weak editorial signal: homepage hero slots, above-the-fold cards, repeated section presence, pinned badges | Low to medium. Depends on whether page layout encodes editorial ordering | Fall back to constrained `frontpage` or `latest` extraction, then lean on downstream rerank and source caps | Medium difficulty, high brittleness to layout changes |
| Curated / editorial sources | Manually selected headlines, newsletter issues, editor's picks, digests | Fetch curated lists directly; treat inclusion itself as a ranking signal | High. Curation is often the value signal | If curation is sparse, combine with topic-specific latest feeds from same publisher | Low to medium difficulty, low risk |
| Aggregator frontpages | Rank/order on landing page, labels, topical sections | Fetch the frontpage or category frontpage rather than raw article feeds; preserve visible ordering metadata | Medium to high when frontpage ordering is explicit | If the page is unstable or incomplete, use latest feed plus aggregator/domain weighting | Medium difficulty, medium risk |
| Search/discovery result pages | Query-result ordering, sometimes recency filters | Use targeted query strategies for known topics/entities only, not as general crawling | Medium for narrow topics, low for general ranking | Restrict to corroboration and gap-filling, not primary ingestion | High complexity and scope risk |

### Source-type guidance

#### Plain RSS / Atom media feeds

This is the repo's current default and remains useful for broad coverage. The limitation is structural: many feeds only expose recent posts. For these, no algorithmic rerank will recover stories that were never included upstream.

Practical guidance:

- prefer narrower feeds over one giant general feed
- prefer editor-picked or most-read variants when publishers expose them
- avoid over-trusting a plain latest feed as a proxy for importance

#### Official blogs / changelogs / release feeds

These are different from general news. They often contain lower volume but much higher actionability. A release note, security advisory, or deprecation notice may be more worth reading than a viral discussion about it.

Practical guidance:

- model them explicitly as official/update-oriented sources
- weight inclusion as higher intent and higher information density
- do not require broad social corroboration for these to rank well

#### Community-ranked sources

These are some of the best candidates for upstream quality improvement because they already expose public collective judgment signals.

Practical guidance:

- capture list type (`frontpage`, `best`, `top`, `rising`, subreddit/community frontpage)
- preserve rank position, score, and comment count as acquisition metadata
- treat them as candidate generators, not final truth

#### Platform-trending sources

These platforms may expose a trending page or public engagement counters, but the system should not assume knowledge of internal recommendation logic.

Practical guidance:

- use only observable metadata
- snapshot engagement over time when possible
- distinguish raw popularity from reading value
- prefer trusted-channel acquisition for domains where creator quality matters

#### HTML pages without ranking metadata

This is the weakest and most brittle category. Often the only available signals are DOM order and layout prominence.

Practical guidance:

- use layout position only as a weak proxy
- keep extraction rules simple and observable
- cap contribution from these sources unless stronger evidence exists

## 3. Candidate Strategy Model

The config should separate `source_type` from `candidate_strategy`.

- `source_type` describes what the source is
- `candidate_strategy` describes how to acquire candidates from it

This allows multiple sources of the same type to be handled differently. For example, one RSS source may remain `latest`, while another uses an `editor_picks` feed.

### Proposed strategy vocabulary

| Strategy | Meaning | Best fit | Notes |
| --- | --- | --- | --- |
| `latest` | Fetch newest available items in source order | Plain RSS, simple blogs, fallback mode | Baseline strategy, weakest proxy for reading value |
| `frontpage` | Fetch items from a page/list where visible ordering is editorial or platform-defined | Homepages, HN frontpage-like lists, editorial landing pages | Preserve list position as metadata |
| `trending` | Fetch items from a platform's explicit trending/popular surface | Video/social platforms, some aggregators | Use only if the platform exposes a public trending surface |
| `curated` | Fetch from an intentionally selected list | Newsletters, editor's picks, curated digests | Inclusion itself is a strong signal |
| `release` | Fetch official product updates, changelogs, advisories | Vendor blogs, package releases, release feeds | Often low-volume and high-value |
| `community_ranked` | Fetch from public rank/score pages | HN/Reddit-like sources | Capture score, comments, position, age |
| `high_engagement_proxy` | Fetch recent items, then rank them within the source by observable engagement metrics | Platforms with public counters but no trending feed | Useful fallback, but noisy and gameable |
| `section_frontpage` | Fetch a topic/category landing page, not only raw chronology | Publisher verticals, topic portals | Better than global latest when topic pages are editorially maintained |
| `corroboration_only` | Fetch mainly to detect repeated coverage, not to contribute many top results directly | Long-tail feeds, low-signal sources | Good for weak sources that still help confirm stories |

### Proposed config shape

This is a design proposal, not current schema.

```yaml
sources:
  - name: Hacker News Front Page
    url: https://news.ycombinator.com/
    type: html
    source_type: community_ranked
    candidate_strategy: frontpage
    weight: 1.0
    acquisition:
      rank_field: position
      capture:
        - position
        - score
        - comments
        - age
      max_candidates: 40

  - name: Python Insider Releases
    url: https://feeds.feedburner.com/PythonInsider
    type: rss
    source_type: official_blog
    candidate_strategy: release
    weight: 1.2
    acquisition:
      tags:
        include: [release, security]
      max_candidates: 20

  - name: Reuters Tech
    url: https://www.reutersagency.com/feed/?best-topics=tech
    type: rss
    source_type: plain_rss
    candidate_strategy: latest
    weight: 1.0
    acquisition:
      max_candidates: 30
      contribution_limit: 3

  - name: Editorial Digest
    url: https://example.com/editors-picks
    type: html
    source_type: curated_editorial
    candidate_strategy: curated
    weight: 1.1
    selector: main article
    acquisition:
      preserve_page_order: true
      max_candidates: 20
```

### Acquisition metadata to retain

Downstream ranking can only use source-level signals if fetch preserves them.

Recommended per-candidate metadata:

- `candidate_strategy`
- `source_type`
- `source_rank_position`
- `source_section`
- `source_engagement_score`
- `source_comment_count`
- `source_view_count`
- `source_like_count`
- `source_curated_flag`
- `source_official_flag`
- `source_frontpage_timestamp`
- `acquisition_confidence`

Not every source will populate every field. Sparse metadata is acceptable if the schema is stable.

## 4. Fallback Policy

This section is intentionally strict: some sources simply do not provide a better upstream signal than recency. The system should acknowledge that directly instead of pretending ranking can solve it.

### Fallback hierarchy

1. Use the strongest explicit source signal available.
   - Example: trending page, frontpage order, official release feed, editor picks.
2. If no explicit ranking signal exists, use a stronger structural proxy.
   - Example: section homepage order, hero slot position, pinned badges.
3. If no strong proxy exists, fall back to `latest`.
4. When forced to use `latest`, compensate downstream with tighter controls.

### Required fallback controls for weak sources

When a source has only `latest` or otherwise weak acquisition quality, apply one or more of:

- `source weighting`
  - Lower the prior weight for sources known to publish high-volume low-signal items.
- `contribution limits`
  - Cap how many final results the source can contribute.
- `corroboration boost`
  - Increase score when the same development appears across multiple independent sources.
- `topic diversity`
  - Avoid letting a weak but prolific source dominate one topic cluster or the final list.
- `downstream rerank`
  - Let source metadata inform reranking, but do not let it override all other reading-value signals.
- `recency window controls`
  - Narrow the fetch window so that weak latest feeds do not flood the pool.
- `corroboration_only mode`
  - Allow weak sources to help detect story importance without giving them strong direct output share.

### Per-taxonomy fallback policy

| Source type | Preferred fallback |
| --- | --- |
| Plain RSS / Atom latest-only feeds | Keep as `latest`, lower contribution share, use cross-source corroboration and cluster-level scoring |
| Official blogs with no better feed | Still use `latest`, but retain strong official-source weight and do not over-penalize for low corroboration |
| Community sources without stable ranking API | Scrape visible ranked pages if operationally acceptable; otherwise reduce to `latest` with explicit quality downgrade |
| Platform pages without trending access | Use `high_engagement_proxy` on recent items if counters are visible; otherwise treat as weak source and cap heavily |
| HTML pages without metadata | Use page order as weak signal only; prioritize downstream diversity and contribution caps |
| Curated/editorial sources with sparse volume | Combine with other source types, but preserve curated inclusion as a strong positive signal |

### Key rule

If no better acquisition strategy exists, the correct product behavior is not "pretend latest equals best." The correct behavior is "mark this source as weak acquisition, constrain its influence, and rely on stronger sources plus downstream selection."

## 5. Reading-Value Definition

`Worth reading` should be defined as expected reader value, not raw platform popularity.

### Public/shared value signals

These are signals that are often useful for many readers:

- consequence or impact
- information density
- novelty relative to the recent pool
- corroboration across independent sources
- officialness or primary-source status
- editorial selection
- expert/community endorsement
- timeliness for decision-making
- explanatory quality

### User-specific/personal value signals

These are signals that depend on the reader:

- topic interests
- followed companies, projects, regions, or creators
- preferred source types
- reading depth preference: headlines vs explainers vs releases
- tolerance for niche material
- work relevance
- repeat engagement with similar items

### Popularity is one signal, not the objective

Popularity may correlate with value, especially on community-ranked or trending platforms, but it should remain one signal among many.

Why:

- popularity can reward novelty, outrage, or entertainment over substance
- niche but critical updates may have low public engagement
- official releases and advisories can be highly valuable before they are broadly discussed
- different readers need different tradeoffs between broad relevance and personal relevance

### Proposed reading-value objective

At a high level, final ranking should optimize for:

`expected reading value = shared value signals + source/context signals + user-specific value signals - redundancy penalties`

For earlier phases, user-specific signals can be absent. The system can still improve materially by optimizing shared value signals after acquisition quality improves.

## 6. Recommended Roadmap

Priority should favor source acquisition first, because that changes the ceiling for all later ranking work.

### Phase 1: Source and candidate acquisition model

Goals:

- add explicit `source_type` and `candidate_strategy` concepts
- preserve acquisition metadata during fetch/normalize
- support multiple upstream acquisition modes beyond plain latest
- add fallback classifications for weak sources

Expected work:

- config schema extension
- source capability matrix
- fetcher support for ranked list extraction
- candidate metadata plumbing
- contribution-limit and weak-source handling

Why first:

- this increases candidate quality before any sophisticated ranking work
- it also creates better features for later reranking

### Phase 2: Downstream reranking and explainability

Goals:

- use acquisition metadata in cluster/article scoring
- improve cluster-level importance estimation
- make result explanations explicit

Expected work:

- ranker updates to consume source rank position, curated flags, official flags, and corroboration
- clearer explanation fields in output, such as "official release", "frontpage rank #4", or "covered by 5 independent sources"
- better diversity controls by source type and topic

Why second:

- reranking becomes more meaningful once the input pool is better and richer in metadata

### Phase 3: Personalization and reader profile

Goals:

- tailor reading-value selection to user intent
- separate broadly important from personally important

Expected work:

- reader profile config
- topic/entity affinity
- source preference tuning
- explore/save/follow feedback loops

Why third:

- personalization on top of a weak source model would overfit poor candidates
- better acquisition and explainability should come first

## 7. Issue Seeds

These are candidate implementation issues derived from the design.

1. `Extend source config with source_type and candidate_strategy`
   - Add schema support and validation for explicit source taxonomy and acquisition modes.

2. `Preserve acquisition metadata on fetched candidates`
   - Extend article/source models to carry source rank, engagement proxies, curated flags, and acquisition confidence.

3. `Implement frontpage/ranked-list fetch strategy for HTML sources`
   - Support extracting ordered candidates from page structure while preserving visible position metadata.

4. `Add official release/changelog strategy`
   - Introduce source handling optimized for official blogs, advisories, and release feeds.

5. `Add weak-source fallback controls`
   - Implement contribution limits, corroboration-only mode, and source-quality downgrade behavior for latest-only sources.

6. `Update ranker to use acquisition metadata`
   - Incorporate source strategy, source position, officialness, and curated inclusion into downstream scoring.

7. `Add cluster corroboration scoring across independent sources`
   - Improve cluster importance estimates using source diversity and repeated coverage rather than only recency and cluster size.

8. `Expose ranking explanations in output`
   - Add explanation fields so downstream consumers can see why an item ranked highly.

9. `Create fixture set for ranked pages and curated pages`
   - Add deterministic tests for frontpage extraction, curated lists, and weak-source fallback behavior.

10. `Document source strategy examples in README and config example`
   - Provide practical config examples once the schema stabilizes.

## Open Questions

- Should `candidate_strategy` be a single enum per source, or a prioritized list with fallback order?
- How much source-specific extraction logic is acceptable before maintenance cost outweighs quality gains?
- Should weak-source quality be an explicit configured field, inferred heuristically, or both?
- At what stage should cluster-level scoring move ahead of individual-article scoring in the ranking pipeline?
- Which output format should carry ranking explanations first: JSON only, or Markdown as well?
