# Search Logic Inconsistency Issues

This document tracks the differences between frontend and CLI (`search-ads find --context ... --local`) search implementations that cause different results for the same query.

---
## Issue 0: Vecotr embed is not used or only in some special condition in the frontend. This will casue no search results.


## Issue 1: Different Query Used for Vector Search

**Severity**: High

**Description**: The frontend and CLI use different queries when performing vector similarity search.

- **Frontend** (`src/web/routers/ai.py:377-383`): Uses the **original user query** for vector search
- **CLI** (`src/cli/main.py:462-467`): Uses the **AI-extracted `search_query`** for vector search

**Impact**: The CLI may lose semantic nuance from the original context. For example:
- Original: `"I need a foundational paper about dark matter halos"`
- AI-extracted: `"dark matter halos"`

The word "foundational" is lost, changing what papers are considered relevant.

**Recommendation**: Modify `_search_local_database()` in `src/cli/main.py` to use the original context for vector search, matching frontend behavior.

---

## Issue 2: Different Ranking Algorithms

**Severity**: High

**Description**: Results are ranked using completely different methods.

- **Frontend** (`src/web/routers/ai.py:548-603`): Uses **LLM-based re-ranking** of top 30 results with context awareness
- **CLI** (`src/cli/main.py:381`): Sorts by **citation count only** (`papers.sort(key=lambda p: p.citation_count or 0, reverse=True)`)

**Impact**:
- Frontend returns contextually relevant papers
- CLI returns popular papers (high citation count) regardless of relevance to the specific query

**Recommendation**: Enable LLM ranking in CLI local mode. The code path exists (`main.py:513-531`) but may not activate properly with `--local` flag.

---

## Issue 3: Different Result Limits

**Severity**: Medium

**Description**: The number of results retrieved differs significantly.

- **Frontend**: Retrieves `limit=20` results
- **CLI**: Retrieves `top_k=5` results (from intermediate pool of `top_k * 10 = 50`)

**Impact**: CLI users see fewer results, reducing chance of finding relevant papers.

**Recommendation**: Make CLI `--local` default limit consistent with frontend, or add a `--limit` flag.

---

## Issue 4: CLI Keyword Fallback Not in Frontend

**Severity**: Low

**Description**: CLI has a keyword-based fallback search that frontend lacks.

- **CLI** (`src/cli/main.py:357-382`): If vector search returns no results, falls back to keyword matching on title/abstract
- **Frontend**: No keyword fallback; relies solely on vector search

**Impact**: CLI may return results when frontend returns nothing, but these keyword results may be less relevant.

**Recommendation**: Consider adding keyword fallback to frontend, or document this as intentional behavior difference.

---

## Issue 5: Filter Application Timing

**Severity**: Low

**Description**: Author and year filters are applied at different stages.

- **Frontend** (`src/web/routers/ai.py:377-383`): Filters applied during vector search query
- **CLI** (`src/cli/main.py:470-482`): Filters applied post-search on retrieved results

**Impact**: CLI may filter out relevant papers after retrieval, wasting search capacity. Frontend filters during search, getting more filtered results.

**Recommendation**: Apply filters at query level in CLI for consistency.

---

## Files Involved

| Component | File | Key Lines |
|-----------|------|-----------|
| Frontend Search | `frontend/src/pages/SearchPage.tsx` | 57-168 |
| Frontend API | `frontend/src/lib/api.ts` | 698-740 |
| Backend AI Search | `src/web/routers/ai.py` | 330-623 |
| CLI Find Command | `src/cli/main.py` | 285-547 |
| Vector Store | `src/db/vector_store.py` | 210-263 |
| LLM Client | `src/core/llm_client.py` | 157-478 |

---

## Priority Order for Fixes

1. **Issue 1** - Use original query for vector search in CLI
2. **Issue 2** - Enable LLM ranking in CLI local mode
3. **Issue 3** - Align result limits
4. **Issue 5** - Consistent filter application
5. **Issue 4** - Evaluate if keyword fallback should be added to frontend
