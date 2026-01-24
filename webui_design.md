# Search-ADS Web UI Design

A next-generation reference management interface that leverages AI, semantic search, and knowledge graphs to surpass traditional tools like Zotero, Mendeley, and Papers.

---

## Vision & Goals

### Vision
Create the most intelligent reference management system for researchers—one that doesn't just store papers, but **understands your research**, **discovers connections**, and **actively helps you write better papers**.

### Design Principles
1. **Intelligence First**: Every feature should leverage the LLM and semantic search capabilities
2. **Visual Knowledge**: Make the citation network visible and explorable
3. **Contextual Actions**: Right action, right place, right time
4. **Keyboard-Driven**: Power users shouldn't need a mouse
5. **Offline Capable**: Full functionality with local database

### Why Better Than Zotero?

| Feature | Zotero | Search-ADS |
|---------|--------|------------|
| Paper Discovery | Manual search | AI-powered recommendations based on your research |
| Search | Keyword only | Semantic search across abstracts + full PDFs |
| Citation Graph | None | Interactive visualization with expansion |
| Writing Integration | Generic | LaTeX-native with citation type analysis |
| Context Understanding | None | LLM analyzes what kind of citation you need |
| PDF Intelligence | Basic text | Vector-embedded semantic search |
| Recommendations | None | "Papers like this" and "Gap in your library" |

---

## Navigation & View Switching

The web UI uses a **persistent sidebar navigation** with React Router for client-side routing.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  🔭 Search-ADS                                     [Project ▾] [⚙️] [👤]     │
├────────────┬─────────────────────────────────────────────────────────────────┤
│            │                                                                 │
│  🏠 Home   │                                                                 │
│            │            <-- Current view content -->                         │
│  📚 Library│                                                                 │
│            │                                                                 │
│  🔍 Search │                                                                 │
│            │                                                                 │
│  🕸️ Graph  │                                                                 │
│            │                                                                 │
│  ✏️ Writing│                                                                 │
│            │                                                                 │
│  📥 Import │                                                                 │
│            │                                                                 │
│  ⚙️ Settings│                                                                │
│            │                                                                 │
└────────────┴─────────────────────────────────────────────────────────────────┘
```

**Routes:**
| Path | View | Description |
|------|------|-------------|
| `/` | Dashboard | Smart library overview with stats and recommendations |
| `/library` | Library | Full paper table with sorting, filtering, bulk actions |
| `/library/:bibcode` | Paper Detail | Single paper view with metadata and actions |
| `/search` | Search & Discovery | AI-powered search across library and ADS |
| `/graph` | Knowledge Graph | Interactive citation network visualization |
| `/graph/:bibcode` | Graph (centered) | Graph centered on specific paper |
| `/writing` | Writing Assistant | Paste LaTeX text, get citation suggestions |
| `/import` | Import & Sync | Import from ADS, BibTeX, clipboard |
| `/settings` | Settings | API keys, preferences, database management |

**Implementation:**
- Use **TanStack Router** for type-safe routing
- Sidebar always visible (collapsible on mobile)
- State preserved when switching views (Zustand + TanStack Query cache)
- Browser back/forward navigation works correctly

---

## Core Features

### 1. Smart Library Dashboard

The home view shows your research at a glance with intelligent summaries.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔭 Search-ADS                                    [Project ▾] [⚙️] [👤]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Good morning! Your library has 847 papers across 5 projects.               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🔍 Search your library or discover new papers...              [⌘K]    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │ 📚 Recent Papers    │  │ ⭐ My Papers        │  │ 📊 Your Research    │  │
│  │                     │  │                     │  │                     │  │
│  │ Smith+24 Dark...    │  │ Papers you authored │  │ 142 papers this     │  │
│  │ Jones+23 Stellar... │  │                     │  │ year                │  │
│  │ Chen+23 Galaxy...   │  │ • Smith+24 (45 cit) │  │ 12 my papers        │  │
│  │                     │  │ • Smith+22 (120 cit)│  │ 34 with notes       │  │
│  │ [View All →]        │  │                     │  │                     │  │
│  │                     │  │ [View All →]        │  │ Top topics:         │  │
│  └─────────────────────┘  └─────────────────────┘  │ • Galaxy evolution  │  │
│                                                    │ • Star formation    │  │
│  ┌─────────────────────┐  ┌─────────────────────┐  └─────────────────────┘  │
│  │ 🌟 Recommended      │  │ 📝 Recent Notes     │                           │
│  │                     │  │                     │                           │
│  │ Based on your work  │  │ Chen+23: "Key for   │                           │
│  │ on AGN feedback:    │  │ thesis ch.3..."     │                           │
│  │                     │  │                     │                           │
│  │ • Wang+24 "AGN..."  │  │ Jones+22: "Compare  │                           │
│  │ • Lee+24 "Black..." │  │ with simulations"   │                           │
│  │                     │  │                     │                           │
│  └─────────────────────┘  └─────────────────────┘                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🕸️ Knowledge Graph Preview                               [Expand →]    ││
│  │                                                                         ││
│  │            [Your Recent Paper]                                          ││
│  │           /        |         \                                          ││
│  │     [Ref A]    [Ref B]    [Ref C]                                       ││
│  │        |          |                                                     ││
│  │    [Shared]    [Shared]   ← 12 papers connect your work                 ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **Smart Greeting**: Shows relevant context (time of day, recent activity)
- **Universal Search**: `⌘K` to search everything (papers, PDFs, notes)
- **AI Recommendations**: "Papers you might need" based on your research patterns
- **Research Analytics**: Visualize your library composition
- **Knowledge Graph Preview**: Quick view of paper connections

---

### 2. Paper Library View

A powerful table view with smart filtering, sorting, and bulk operations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Library                                              [+ Add Paper] [Import]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🔍 Search: "galaxy formation"                                          ││
│  │                                                                         ││
│  │ Filters: [Year: 2020-2024 ×] [Project: AGN-paper ×] [Has PDF ×]        ││
│  │          [My Papers ×] [Has Note] [+ Add Filter]                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Showing 47 of 847 papers                    Sort: [Year ▾] [Columns ⚙️]   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ☐ │ Title                    │ Year │ Authors    │ Cited │ PDF │ Embed ││
│  ├───┼──────────────────────────┼──────┼────────────┼───────┼─────┼───────┤│
│  │ ☑ │ Dark Matter Halos in...  │ 2024 │ Smith+3    │ 45    │ ✓   │ ✓     ││
│  │   │ [▼ Expand]               │      │            │       │     │       ││
│  ├───┼──────────────��───────────┼──────┼────────────┼───────┼─────┼───────┤│
│  │ ☐ │ Stellar Evolution in...  │ 2023 │ Jones+2    │ 120   │ ⬇   │ —     ││
│  ├───┼──────────────────────────┼──────┼────────────┼───────┼─────┼───────┤│
│  │ ☐ │ Galaxy Mergers and AGN   │ 2023 │ Chen+5     │ 89    │ —   │ —     ││
│  └───┴──────────────────────────┴──────┴────────────┴───────┴─────┴───────┘│
│                                                                             │
│  Selected: 1    [📥 Download PDFs] [🔗 Embed] [📁 Add to Project] [🗑️ Del] │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Column Specification

| Column | Type | Sortable | Description |
|--------|------|----------|-------------|
| ☐ | Checkbox | No | Multi-select for bulk actions |
| Title | Text | Yes | Paper title (click row to expand abstract) |
| Year | Number | Yes | Publication year |
| Authors | Text | Yes | Collapsed as "Smith+N", expand to see all |
| Citations | Number | Yes | Citation count from ADS |
| Mine | Icon | Yes | ⭐ if marked as user's own paper, — otherwise |
| Note | Icon | Yes | 📝 if paper has a note, — otherwise (hover to preview) |
| PDF | Icon | Yes | ✓ downloaded, ⬇ available, — none |
| Embedded | Icon | Yes | ✓ embedded for search, — not embedded |
| Status | Badge | Yes | Read/Unread/Cited (optional column) |

#### Right-Click Context Menu

```
┌─────────────────────────────┐
│ 📄 View Paper Details       │
│ ─────────────────────────── │
│ 🔗 Find References →        │  (Opens library view with all refs)
│ 📚 Find Citations →         │  (Opens library view with citing papers)
│ ─────────────────────────── │
│ ⭐ Mark as My Paper         │  (Toggle: marks paper as user's own work)
│ 📝 Add/Edit Note...         │  (Opens note editor modal)
│ ─────────────────────────── │
│ 📥 Download PDF             │
│ 🔗 Embed PDF                │
│ 📂 Open PDF                 │
│ ─────────────────────────── │
│ 📁 Add to Project...        │
│ 📋 Copy BibTeX              │
│ 📋 Copy Cite Key            │
│ ─────────────────────────── │
│ 🗑️ Remove from Library      │
└─────────────────────────────┘
```

#### Bulk Actions (for selected papers)

- **Download All PDFs**: Download PDFs for all selected papers
- **Embed All PDFs**: Extract and embed PDF content for semantic search
- **Add to Project**: Add selected papers to one or more projects
- **Mark as My Papers**: Mark selected papers as user's own work
- **Export BibTeX**: Export bibliography entries for selected papers
- **Update Citations**: Refresh citation counts from ADS
- **Remove from Library**: Delete selected papers (with confirmation)

**Features:**

- **Semantic Search**: Not just keywords—understands meaning
- **Smart Filters**: Year range, projects, PDF status, embedded status, citation count, My Papers, Has Note
- **Column Visibility**: Toggle columns on/off via settings button
- **Expandable Rows**: Click to expand and see abstract inline (includes note preview if available)
- **Sortable Columns**: Click column header to sort ascending/descending
- **Virtualized Table**: TanStack Table for smooth scrolling with 1000+ papers
- **Inline Preview**: Hover to see abstract tooltip without leaving the list
- **Note Preview**: Hover over note icon to see note content in tooltip

---

### 3. Paper Detail View

A comprehensive view of a single paper with all actions available.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back to Library                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Dark Matter Halos in Galaxy Formation: A Comprehensive Study    ⭐ MY PAPER│
│  ═══════════════════════════════════════════════════════════════════════════│
│                                                                             │
│  Smith, J. · Johnson, A. · Williams, B.            2024 · ApJ · 996 · 35    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ [📄 View PDF] [📋 Copy BibTeX] [🔗 ADS] [📎 arXiv] [🏷️ Add to Project]│   │
│  │ [⭐ Toggle My Paper]                                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────┬───────────────────────────────────────────────────────┐│
│  │                 │                                                       ││
│  │  📊 Metrics     │  📝 Abstract                                          ││
│  │                 │                                                       ││
│  │  Citations: 45  │  We present a comprehensive study of dark matter      ││
│  │  References: 32 │  halo formation in the context of galaxy evolution.   ││
│  │  Read: Yes ✓    │  Using high-resolution simulations, we demonstrate    ││
│  │  My Paper: ⭐   │  that halo concentration correlates strongly with     ││
│  │                 │  formation time, consistent with theoretical          ││
│  │  ────────────── │  predictions. Our results suggest that...             ││
│  │                 │                                                       ││
│  │  🏷️ Projects    │  [Show full abstract]                                 ││
│  │                 │                                                       ││
│  │  • AGN-paper    │  ────────────────────────────────────────────────     ││
│  │  • thesis       │                                                       ││
│  │  [+ Add]        │  🤖 AI Summary                                        ││
│  │                 │                                                       ││
│  │  ────────────── │  This paper establishes that dark matter halo         ││
│  │                 │  concentration is primarily determined by formation   ││
│  │  📁 Files       │  time. Key for: galaxy evolution intro, DM background ││
│  │                 │                                                       ││
│  │  PDF: ✓ Local   │  Citation type: Foundational                          ││
│  │  Embedded: ✓    │                                                       ││
│  │                 │  ────────────────────────────────────────────────     ││
│  │  [Open PDF]     │                                                       ││
│  │  [Re-embed]     │  📝 Your Note                              [✏️ Edit]  ││
│  │                 │                                                       ││
│  │                 │  This is an important paper for my thesis chapter 3.  ││
│  │                 │  Key finding: halo concentration depends on formation ││
│  │                 │  time. Compare with Jones+22 results.                 ││
│  │                 │                                                       ││
│  │                 │  [Delete Note]                                        ││
│  │                 │                                                       ││
│  └─────────────────┴───────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🕸️ Citation Network                                        [Fullscreen]││
│  │                                                                         ││
│  │              [Citing Paper 1]   [Citing Paper 2]                        ││
│  │                     \               /                                   ││
│  │                      \             /                                    ││
│  │                    [ This Paper ]                                       ││
│  │                   /      |       \                                      ││
│  │            [Ref 1]   [Ref 2]   [Ref 3]                                  ││
│  │               |                   |                                     ││
│  │          [Ref 1.1]            [Ref 3.1]                                 ││
│  │                                                                         ││
│  │  ◉ In library (32)  ○ Not in library (45)  [Expand All] [Add Selected] ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 📚 Related Papers                                         [See All →]  ││
│  │                                                                         ││
│  │ Based on semantic similarity:                                           ││
│  │ • Chen+23 "Galaxy Mergers..." (94% similar) [+ Add]                     ││
│  │ • Wang+22 "Halo Mass Function..." (91% similar) [Already in library]    ││
│  │ • Liu+24 "Dark Matter Substructure..." (89% similar) [+ Add]            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **AI Summary**: LLM-generated summary highlighting key contributions
- **Citation Type**: Automatically classified for writing context
- **Interactive Citation Graph**: Click nodes to explore, add papers directly
- **Related Papers**: Semantic similarity suggestions
- **Quick Actions**: Copy citation, open PDF, view on ADS/arXiv
- **Project Management**: Add/remove from projects
- **My Paper Badge**: Toggle whether this paper is authored by you (⭐ indicator)
- **User Notes**: View, add, edit, or delete personal notes on the paper
- **PDF Status**: Download, embed for search, open in viewer

---

### 4. Knowledge Graph Explorer

A full-screen interactive visualization of your citation network.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Knowledge Graph                              [Filter ▾] [Layout ▾] [Export]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────┐ ┌───────┐│
│  │                                                               │ │ Legend││
│  │                    ●══════════●                               │ │       ││
│  │                   /            \                              │ │ ● Your││
│  │              ●───●              ●───●                         │ │   paper││
│  │             / \                / \                            │ │ ○ In   ││
│  │            ●   ●              ●   ◇                           │ │   lib  ││
│  │                |                  |                           │ │ ◇ Not  ││
│  │                ●                  ◇                           │ │   in   ││
│  │               / \                                             │ │       ││
│  │              ◇   ◇   ← Click to add                           │ │ ━ Cites││
│  │                                                               │ │ ┄ Refs ││
│  │                                                               │ │       ││
│  │  [+] Zoom  [-]  [⟲] Reset  [📍] Center on selection          │ └───────┘│
│  └────────────────────────────────────────────��──────────────────┘         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Selected: Smith+24 "Dark Matter Halos..."                               ││
│  │                                                                         ││
│  │ 45 citations · 32 references · 12 in your library                       ││
│  │                                                                         ││
│  │ [View Paper] [Expand +1 Hop] [Expand +2 Hops] [Add All Refs to Library] ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🔍 Find Connections                                                     ││
│  │                                                                         ││
│  │ Paper A: [Smith+24 Dark Matter...     ▾]                                ││
│  │ Paper B: [Chen+23 Galaxy Mergers...   ▾]                                ││
│  │                                                                         ││
│  │ [Find Path]  →  Connected via 2 papers: Smith → Jones+22 → Chen         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Node Design

Each node in the graph represents a paper with visual encoding:

| Visual Element | Meaning |
|----------------|---------|
| **Shape** | ● Circle = in library, ◇ Diamond outline = not in library |
| **Size** | Proportional to citation count (log scale) |
| **Color** | 🟢 Green = cited in your writing, 🔵 Blue = in library, ⚪ Gray = not in library, 🟡 Yellow = highly cited (>100) |
| **Label** | First author + year (e.g., "Smith+24") |
| **Edge thickness** | Based on citation importance |
| **Edge direction** | Arrow points from citing → cited paper |

**Hover Preview (Tooltip):**

When the mouse cursor moves over a node, display a tooltip with paper details:

```
┌─────────────────────────────────────────────────────────┐
│ Dark Matter Halos in Galaxy Formation                   │
│                                                         │
│ Smith, J. · Johnson, A. · Williams, B.            2024  │
│                                                         │
│ We present a comprehensive study of dark matter halo    │
│ formation in the context of galaxy evolution. Using     │
│ high-resolution simulations, we demonstrate that halo   │
│ concentration correlates strongly with formation...     │
│                                                         │
│ 📊 45 citations · 32 references                         │
└─────────────────────────────────────────────────────────┘
```

- **Title**: Full paper title
- **Authors**: All authors (or first 3 + "et al." if many)
- **Year**: Publication year
- **Abstract**: First 200-300 characters with ellipsis
- **Stats**: Citation and reference counts

**Click Actions:**
- Single click: Select node, show details panel
- Double click: Expand 1 hop (fetch refs/citations)

**Right-Click Context Menu:**

```
┌─────────────────────────────────┐
│ 📄 View Paper Details           │
│ ─────────────────────────────── │
│ 📚 Add to Library...            │  (If not in library)
│ ─────────────────────────────── │
│ 🔗 Expand References (+1 hop)   │
│ 📖 Expand Citations (+1 hop)    │
│ 🔄 Expand Both (+1 hop)         │
│ ─────────────────────────────── │
│ ❌ Remove from Graph            │  (Removes node and its edges)
└─────────────────────────────────┘
```

- **View Paper Details**: Navigate to paper detail view
- **Add to Library**: Opens project selection dropdown (if paper not in library)
- **Expand References**: Fetch and display papers this paper cites
- **Expand Citations**: Fetch and display papers that cite this paper
- **Expand Both**: Fetch both references and citations in one action
- **Remove from Graph**: Remove this node from the current visualization (does not delete from library)

#### Recommended Visualization Library

**Primary: vis.js (vis-network)**
- Easy setup with React wrapper (`react-vis-network-graph`)
- Built-in physics engine for force-directed layout
- Good performance for 100-500 nodes
- Pan, zoom, drag built-in

**Alternative: Cytoscape.js**
- More layout algorithms (hierarchical, radial, dagre)
- Better for complex graphs (500+ nodes)
- Steeper learning curve
- React wrapper: `react-cytoscapejs`

**Features:**

- **Interactive Graph**: Pan, zoom, click to select, drag to rearrange
- **Visual Differentiation**: Shape and color encode library status and importance
- **Hop Expansion**: Expand citation network 1-2 hops at a time
- **Path Finding**: Discover how two papers are connected
- **Bulk Add**: Add all references/citations of a paper to library
- **Multiple Layouts**: Force-directed, hierarchical, radial
- **Filtering**: Show only certain years, projects, or citation counts
- **Export**: Save graph as PNG/SVG image or JSON data

---

### 5. AI-Powered Search & Discovery

The most powerful feature—understanding what you're looking for.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Discover                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ What are you looking for?                                               ││
│  │                                                                         ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ I need a paper that established the connection between AGN          │ ││
│  │ │ feedback and quenching of star formation in massive galaxies        │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ Search mode: [● Natural Language] [○ Keywords] [○ Similar to Paper]     ││
│  │ Search in:   [☑ Your Library] [☑ ADS] [☑ PDF Full-text]                 ││
│  │                                                                         ││
│  │ [🔍 Search]                                                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🤖 AI Analysis                                                          ││
│  │                                                                         ││
│  │ You're looking for a **foundational paper** about AGN feedback's role   ││
│  │ in galaxy quenching. This is likely for an introduction or background   ││
│  │ section.                                                                ││
│  │                                                                         ││
│  │ I found 8 highly relevant papers. The top result (Fabian 2012) is the   ││
│  │ canonical review on this topic with 2,847 citations.                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Results (8 papers)                                              [Export]   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🥇 Fabian 2012                                              98% match   ││
│  │    "Observational Evidence of Active Galactic Nuclei Feedback"         ││
│  │    ARA&A · Citations: 2,847 · Review article                            ││
│  │                                                                         ││
│  │    Why this paper: This is the definitive review establishing the       ││
│  │    AGN feedback paradigm and its role in quenching star formation.      ││
│  │    Highly cited and widely used as the foundational reference.          ││
│  │                                                                         ││
│  │    [📄 View] [+ Add to Library ▾] [📋 Copy Citation]                    ││
│  │               ┌──────────────────────┐                                  ││
│  │               │ Select Project(s):   │                                  ││
│  │               │ ☑ AGN-paper          │                                  ││
│  │               │ ☐ thesis             │                                  ││
│  │               │ ☐ reading-list       │                                  ││
│  │               │ ──────────────────── │                                  ││
│  │               │ [+ Create New...]    │                                  ││
│  │               │ [Add to Selected]    │                                  ││
│  │               └──────────────────────┘                                  ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ 🥈 Croton+06                                                 94% match  ││
│  │    "The many lives of AGN: cooling flows, black holes..."              ││
│  │    MNRAS · Citations: 1,523 · In your library ✓                         ││
│  │                                                                         ││
│  │    Why this paper: First major simulation work showing AGN feedback     ││
│  │    is necessary for reproducing observed galaxy colors.                 ││
│  │                                                                         ││
│  │    [📄 View] [Already in Library ✓] [📋 Copy Citation]                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Load More Results]                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **Natural Language Search**: Describe what you need in plain English
- **AI Analysis**: Explains what type of paper you need and why results match
- **Multi-Source Search**: Library, ADS, and PDF full-text simultaneously
- **Relevance Explanations**: Why each paper is a good match
- **Citation Type Detection**: Knows if you need a review, methodology, etc.
- **Quick Actions**: Add to library, copy citation, view details
- **Search Modes**: Natural language, keywords, or "papers similar to X"

---

### 6. PDF Management (System Viewer)

PDFs open in your system's default viewer (Preview on macOS, Adobe Reader, etc.) for reading and annotation. This leverages mature, feature-rich tools users already know.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Paper Detail View                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📁 PDF Actions                                                             │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  [📂 Open PDF]        Opens in system viewer (Preview, Adobe Reader, etc.)  │
│  [📥 Download PDF]    Download from ADS if not already local                │
│  [🔗 Embed for Search] Extract text for semantic search                     │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  🤖 Ask AI About This Paper                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ What is the main methodology used in this paper?                        ││
│  └────────────────────────────────────��────────────────────────────────────┘│
│  [Ask]                                                                      │
│                                                                             │
│  AI uses the embedded PDF text to answer questions about paper content.     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why system viewer instead of custom?**

- **Rich annotations**: Highlights, notes, shapes, signatures already built-in
- **Familiar interface**: Users know their PDF reader
- **No development cost**: Focus engineering effort elsewhere
- **Annotations persist**: Stored in the PDF file itself

**Features:**

- **Open PDF**: Single click opens in system default viewer
- **AI Q&A**: Ask questions using embedded text (works via modal in paper detail view)
- **Embed for Search**: Extract and index PDF content for semantic search
- **Download**: Fetch PDF from ADS if not already local

---

### 7. Note Editor Modal

A modal dialog for adding and editing notes on papers. Accessible from:
- Right-click context menu → "Add/Edit Note..."
- Paper detail view → "Edit" button in note section
- Library view → Click on note icon

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📝 Note for: Smith+24 "Dark Matter Halos in Galaxy Formation..."      [×]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ This is an important paper for my thesis chapter 3.                     ││
│  │                                                                         ││
│  │ Key findings:                                                           ││
│  │ - Halo concentration depends primarily on formation time                ││
│  │ - Results consistent with theoretical predictions                       ││
│  │ - Compare with Jones+22 for alternative interpretation                  ││
│  │                                                                         ││
│  │ TODO: Read section 4 more carefully for simulation details.             ││
│  │                                                                         ││
│  │                                                                         ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 💡 Tip: Use markdown formatting. Notes are searchable in the library.   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Last updated: 2024-01-15 14:32                                             │
│                                                                             │
│                                      [Delete Note]  [Cancel]  [Save Note]   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **Rich Text Editor**: Supports markdown formatting (bold, lists, headers)
- **Auto-Save**: Optional auto-save as you type (configurable in settings)
- **Searchable**: Notes are indexed and searchable from the library
- **Timestamps**: Shows when note was created and last updated
- **Delete Option**: Remove note with confirmation
- **Keyboard Shortcuts**: `⌘S` to save, `Esc` to cancel

---

### 8. Writing Assistant Panel

A dedicated interface for finding citations by pasting LaTeX text. No file upload needed—just paste your text and get citation suggestions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Writing Assistant                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Paste your LaTeX text:                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Dark matter halos \cite{} follow NFW profiles, though some studies     ││
│  │ \cite{} suggest alternative models. The mass-concentration relation    ││
│  │ \citep{} is well established in simulations.                           ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [🔍 Find Citations]                                                        │
│                                                                             │
│  ───────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  Found 3 empty citations:                                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 1. "...halos \cite{} follow NFW profiles..."                            ││
│  │                                                                         ││
│  │    🤖 Analysis: Foundational paper on NFW density profiles needed       ││
│  │                                                                         ││
│  │    ┌─────────────────────────────────────────────────────────────────┐  ││
│  │    │ ○ Navarro+97 "A Universal Density Profile..." [3,847 cit.]     │  ││
│  │    │   THE canonical NFW paper. Perfect foundational reference.      │  ││
│  │    │                                                                 │  ││
│  │    │ ○ Navarro+96 "The Structure of Cold Dark..." [2,156 cit.]      │  ││
│  │    │   Earlier NFW work, also widely cited.                          │  ││
│  │    └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                         ││
│  │    [Use Selected] [Search More]                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 2. "...some studies \cite{} suggest alternative..."                     ││
│  │    🤖 Analysis: Contrasting paper on alternative DM profiles needed     ││
│  │    ...                                                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ───────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  Output Format: [● BibTeX (.bib)] [○ AASTeX (bibitem)]                      │
│                                                                             │
│  Generated Citations:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ % Selected papers - copy to your .bib file                              ││
│  │                                                                         ││
│  │ @article{1997ApJ...490..493N,                                           ││
│  │   author = {Navarro, Julio F. and Frenk, Carlos S. and White, Simon},  ││
│  │   title = {A Universal Density Profile from Hierarchical Clustering},  ││
│  │   journal = {ApJ},                                                      ││
│  │   year = {1997},                                                        ││
│  │   volume = {490},                                                       ││
│  │   pages = {493-508},                                                    ││
│  │   doi = {10.1086/304888}                                                ││
│  │ }                                                                       ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [📋 Copy to Clipboard] [📥 Add All to Library]                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**

- **Paste-Based Workflow**: No file upload—just paste LaTeX text directly
- **Empty Citation Detection**: Finds `\cite{}`, `\citep{}`, `\citet{}` patterns
- **Context Analysis**: AI analyzes surrounding text to understand citation need
- **Citation Type Classification**: Identifies if you need foundational, methodology, supporting, or contrasting citations
- **Smart Suggestions**: Ranked by relevance with explanations
- **Multiple Output Formats**: BibTeX entries or AASTeX bibitem format
- **One-Click Copy**: Copy formatted citations to clipboard
- **Library Integration**: Optionally add selected papers to your library

---

### 9. Project Management (Simplified)

> **Note**: Full project workspace with LaTeX file linking, gap analysis, and activity tracking is deferred to a future version. Writing workflows are handled via CLI + Claude Code skills.

**Current Project Features:**

Projects are used to organize papers into collections. Available through:
- **Header dropdown**: Switch active project filter
- **Add to Project**: Available in Library view, Search results, and Import
- **CLI commands**: `search-ads project init/list/add-paper/delete`

Basic operations available:
- Create/rename/delete projects
- Add papers to one or more projects
- Filter library view by project
- Export project papers as BibTeX
- View project in Knowledge Graph

---

### 10. Import & Sync

Flexible ways to get papers into your library.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Import Papers                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🔗 From ADS URL or Bibcode                                              ││
│  │                                                                         ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ https://ui.adsabs.harvard.edu/abs/2024ApJ...996...35P/abstract     │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ Options:                                                                ││
│  │ [☑] Auto-expand references (1 hop)                                      ││
│  │ [☐] Auto-expand citations (1 hop)                                       ││
│  │ [☑] Download PDF if available                                           ││
│  │                                                                         ││
│  │ Add to project(s):                                                      ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ ☑ AGN-feedback-paper                                               │ ││
│  │ │ ☐ thesis                                                           │ ││
│  │ │ ☐ reading-list                                                     │ ││
│  │ │ ─────────────────────────────────────────────────────────────────  │ ││
│  │ │ [+ Create New Project...]                                          │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ [Add Paper]                                                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 📁 From BibTeX File                                                     ││
│  │                                                                         ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │                                                                     │ ││
│  │ │              Drag & drop .bib file here                             │ ││
│  │ │                     or click to browse                              │ ││
│  │ │                                                                     │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ Options:                                                                ││
│  │ [☑] Fetch full metadata from ADS                                        ││
│  │ [☐] Download PDFs for all papers                                        ││
│  │                                                                         ││
│  │ Add to project(s):                                                      ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ ☑ AGN-feedback-paper                                               │ ││
│  │ │ ☐ thesis                                                           │ ││
│  │ │ ☐ reading-list                                                     │ ││
│  │ │ ─────────────────────────────────────────────────────────────────  │ ││
│  │ │ [+ Create New Project...]                                          │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ [Import]                                                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 📋 From Clipboard (DOI/arXiv/Bibcode)                                   ││
│  │                                                                         ││
│  │ Paste DOIs, arXiv IDs, or bibcodes (one per line):                      ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ 10.1088/0004-637X/996/1/35                                         │ ││
│  │ │ 2301.12345                                                          │ ││
│  │ │ 2024MNRAS.528.1234J                                                 │ ││
│  │ └────────────────────────────────────────��────────────────────────────┘ ││
│  │                                                                         ││
│  │ [Import 3 Papers]                                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🔄 Sync with Zotero                                         [Coming]   ││
│  │                                                                         ││
│  │ Connect your Zotero library for two-way sync.                           ││
│  │                                                                         ││
│  │ [Connect Zotero Account]                                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **ADS URL/Bibcode**: Primary import method with expansion options
- **BibTeX Import**: Drag-and-drop .bib files
- **Batch Import**: Paste multiple DOIs/arXiv IDs/bibcodes
- **Auto-Expansion**: Optionally fetch references and citations
- **PDF Download**: Automatic download option
- **Zotero Sync**: Future integration with existing libraries

---

### 11. Settings & Configuration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Settings                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  General                                                                    │
│  ───────────────────────────────────────────────────────────────────────    │
│  Theme:              [◉ System] [○ Light] [○ Dark]                          │
│  Default Project:    [None ▾]                                               │
│  PDF Storage:        ~/.search-ads/pdfs/  [Change]                          │
│                                                                             │
│  API Keys                                                                   │
│  ───────────────────────────────────────────────────────────────────────    │
│  ADS API Key:        [••••••••••••••••••••] [Show] [Test]                   │
│  OpenAI API Key:     [••••••••••••••••••••] [Show] [Test]                   │
│  Anthropic API Key:  [••••••••••••••••••••] [Show] [Test]                   │
│                                                                             │
│  LLM Preferences                                                            │
│  ───────────────────────────────────────────────────────────────────────    │
│  Primary LLM:        [◉ Claude] [○ OpenAI]                                  │
│  Fallback LLM:       [◉ OpenAI] [○ None]                                    │
│  Embedding Model:    [text-embedding-3-small ▾]                             │
│                                                                             │
│  Citation Style                                                             │
│  ───────────────────────────────────────────────────────────────────────    │
│  Citation Key Format: [○ bibcode] [◉ author_year] [○ author_year_title]     │
│  Bibliography Style:  [◉ BibTeX (.bib)] [○ AASTeX (bibitem)]                │
│                                                                             │
│  Search Defaults                                                            │
│  ───────────────────────────────────────────────────────────────────────    │
│  Max hops for expansion:     [2 ▾]                                          │
│  Results per search:         [10 ▾]                                         │
│  Min citation count filter:  [0 ▾]                                          │
│  Prefer papers from:         [Any year ▾]                                   │
│                                                                             │
│  Citation Count Updates                                                     │
│  ───────────────────────────────────────────────────────────────────────    │
│  Auto-update interval:       [7 days ▾]  (Never / 1 day / 7 days / 30 days) │
│  Last updated:               3 days ago                                     │
│  Papers needing update:      142 (older than 7 days)                        │
│  [Update All Now]            [Update Selected Project...]                   │
│                                                                             │
│  API Usage                                                                  │
│  ───────────────────────────────────────────────────────────────────────    │
│  Today's ADS calls:     234 / 5000                                          │
│  Today's LLM calls:     45                                                  │
│  [View Usage History]                                                       │
│                                                                             │
│  Database                                                                   │
│  ───────────────────────────────────────────────────────────────────────    │
│  Papers in database:    847                                                 │
│  Vector embeddings:     823 (97%)                                           │
│  PDFs downloaded:       234 (28%)                                           │
│  PDFs embedded:         189 (81% of downloaded)                             │
│  Database size:         1.2 GB                                              │
│                                                                             │
│  [Re-embed All Papers] [Clear All Data] [Export Database]                   │
│                                                                             │
└──────────────────────────────────────────────────────────────────────────���──┘
```

---

## Keyboard Shortcuts

Power users should be able to do everything without touching the mouse.

| Shortcut | Action |
|----------|--------|
| `⌘K` | Global search |
| `⌘N` | Add new paper |
| `⌘I` | Import papers |
| `⌘P` | Switch project |
| `⌘G` | Open graph view |
| `⌘F` | Search in current view |
| `⌘E` | Expand selected paper |
| `⌘D` | Download PDF |
| `⌘C` | Copy citation |
| `⌘B` | Copy BibTeX |
| `⌘/` | Show all shortcuts |
| `Esc` | Close modal/panel |
| `j/k` | Navigate list up/down |
| `Enter` | Open selected item |
| `Space` | Toggle selection |

---

## Technical Architecture

### Frontend Stack
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Framework:     React 18 + TypeScript                                       │
│  State:         Zustand (lightweight) or TanStack Query (for API state)     │
│  Styling:       Tailwind CSS + shadcn/ui components                         │
│  Graph:         D3.js or vis.js for citation network visualization          │
│  PDF:           System viewer (Preview, Adobe Reader, etc.)                 │
│  Tables:        TanStack Table for sortable, filterable lists               │
│  Routing:       React Router or TanStack Router                             │
│  Build:         Vite                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Backend API (FastAPI)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Backend API                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Framework:     FastAPI (already in stack)                                  │
│  Database:      SQLite + SQLModel (existing)                                │
│  Vector Store:  ChromaDB (existing)                                         │
│  Background:    FastAPI BackgroundTasks or Celery for long operations       │
│  WebSocket:     For real-time updates (search progress, graph expansion)    │
│                                                                             │
│  API Structure:                                                             │
│  ├── /api/papers/          - CRUD for papers                                │
│  │   ├── PATCH /{bibcode}/mine  - Toggle "my paper" status                  │
│  │   └── GET /mine         - List all papers marked as mine                 │
│  ├── /api/notes/           - Note management                                │
│  │   ├── GET /{bibcode}    - Get note for a paper                           │
│  │   ├── PUT /{bibcode}    - Create/update note for a paper                 │
│  │   └── DELETE /{bibcode} - Delete note for a paper                        │
│  ├── /api/projects/        - Project management                             │
│  ├── /api/search/          - Search endpoints                               │
│  │   ├── POST /semantic    - Semantic search with LLM                       │
│  │   ├── POST /local       - Local-only search                              │
│  │   └── POST /pdf         - Full-text PDF search                           │
│  ├── /api/graph/           - Citation graph data                            │
│  │   ├── GET /{bibcode}    - Get graph for paper                            │
│  │   └── POST /expand      - Expand graph nodes                             │
│  ├── /api/pdf/             - PDF operations                                 │
│  │   ├── POST /download    - Download PDF                                   │
│  │   ├── POST /embed       - Embed PDF for search                           │
│  │   └── GET /path         - Get local PDF path to open in system viewer    │
│  ├── /api/import/          - Import endpoints                               │
│  │   ├── POST /ads         - Import from ADS                                │
│  │   ├── POST /bibtex      - Import from BibTeX                             │
│  │   └── POST /batch       - Batch import                                   │
│  ├── /api/latex/           - LaTeX integration                              │
│  │   ├── POST /parse       - Parse .tex file for citations                  │
│  │   ├── POST /fill        - Fill citations                                 │
│  │   └── POST /suggest     - Get citation suggestions                       │
│  └── /api/settings/        - User settings                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   User Action                                                               │
│       │                                                                     │
│       ▼                                                                     │
│   React Component ──────────────────┐                                       │
│       │                             │                                       │
│       │ API Call                    │ WebSocket                             │
│       ▼                             │                                       │
│   FastAPI Backend                   │                                       │
│       │                             │                                       │
│       ├── SQLite (metadata) ◄───────┤                                       │
│       │                             │                                       │
│       ├── ChromaDB (vectors) ◄──────┤                                       │
│       │                             │                                       │
│       ├── ADS API (external) ◄──────┤                                       │
│       │                             │                                       │
│       └── LLM API (Claude/OpenAI) ◄─┘                                       │
│              │                                                              │
│              ▼                                                              │
│         Response ──► State Update ──► UI Update                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 4.1: Foundation
**Goal**: Basic paper browsing, management, and API backend

- [ ] FastAPI backend with all API routes (papers, projects, search, import, pdf, settings)
- [ ] React frontend with TanStack Router (sidebar navigation)
- [ ] Library view with TanStack Table (all columns: checkbox, title, year, authors, citations, PDF, embedded, status)
- [ ] Column sorting, filtering, visibility toggle
- [ ] Right-click context menu (view, find refs/citations, download, copy)
- [ ] Bulk actions for selected papers
- [ ] Paper detail view with metadata and actions
- [ ] Project dropdown in header with CRUD operations

**Deliverable**: Functional paper library browser with full table features

### Phase 4.2: Search & Discovery
**Goal**: AI-powered search with library integration

- [ ] Search view with natural language input
- [ ] Semantic search integration (local + ADS)
- [ ] LLM-powered context analysis and ranking
- [ ] "Add to Library" with multi-project selection dropdown
- [ ] Citation type classification display
- [ ] "Why this paper?" explanations in results
- [ ] Writing Assistant panel (paste LaTeX text, get suggestions)
- [ ] BibTeX / AASTeX bibitem output format toggle
- [ ] Copy to clipboard functionality

**Deliverable**: Smart search, discovery, and writing assistant features

### Phase 4.3: Knowledge Graph
**Goal**: Visual citation network exploration

- [ ] vis.js (or Cytoscape.js) graph visualization
- [ ] Node design: shape (circle/diamond), size (citation count), color (library status)
- [ ] Interactive pan/zoom/drag/select
- [ ] Hover tooltips with paper details
- [ ] Click to select, double-click to expand 1 hop
- [ ] Right-click context menu (view, add to library, expand)
- [ ] Expand nodes (+1 hop, +2 hops buttons)
- [ ] Path finding between two papers
- [ ] Multiple layout options (force-directed, hierarchical)
- [ ] Graph filtering (year, project, citation count)
- [ ] Export as PNG/SVG image

**Deliverable**: Fully interactive citation network visualization

### Phase 4.4: Import & Settings
**Goal**: Data import and configuration management

- [ ] Import view with three methods (ADS URL, BibTeX file, clipboard)
- [ ] Project selection (multi-select) during import
- [ ] Settings page with all configuration sections
- [ ] Citation count auto-update settings (interval, manual trigger)
- [ ] Database management (embed all, update all, clear, export)
- [ ] API usage display and history

**Deliverable**: Complete import workflow and settings management

### Phase 4.5: Polish & Performance
**Goal**: Production-ready application

- [ ] Keyboard shortcuts (⌘K search, j/k navigation, etc.)
- [ ] Dark mode toggle
- [ ] Dashboard view with stats, recent papers, recommendations
- [ ] Performance optimization (virtualized lists, lazy loading)
- [ ] Error handling and user feedback (toasts, modals)
- [ ] Loading states and skeleton screens
- [ ] Mobile responsiveness (basic)

**Deliverable**: Polished, performant application

### Future Enhancements (Post-MVP)

- [ ] Full project workspace with LaTeX file linking
- [ ] Gap analysis (missing important papers)
- [ ] Activity timeline and research progress tracking
- [ ] Zotero/Mendeley sync integration

---

## CLI vs Web UI Feature Mapping

All CLI commands should have corresponding Web UI features:

| CLI Command | Web UI Location | Notes |
|-------------|-----------------|-------|
| `seed` | Import view (ADS URL section) | Add paper from ADS URL/bibcode |
| `find` | Search view | AI-powered search with suggestions |
| `get` | Library (right-click → Copy) | Copy cite key, BibTeX, bibitem |
| `show` | Paper detail view | Full paper metadata and actions |
| `fill` | Writing Assistant | Paste LaTeX, get citation suggestions |
| `expand` | Graph view (expand buttons) | Expand refs/citations from nodes |
| `status` | Dashboard + Settings | Database stats, API usage |
| `list-papers` | Library view | Full table with sorting/filtering |
| `mine` | Library (column + right-click), Paper detail | Mark papers as user's own work |
| `note` | Library (column + click), Paper detail, Note modal | Add/edit/delete notes on papers |
| `db clear` | Settings (danger zone) | Clear all data with confirmation |
| `db embed` | Library (bulk action) | Embed selected/all papers |
| `db update` | Settings (citation updates) | Update citation counts |
| `pdf download` | Library (per-paper + bulk) | Download PDF button/action |
| `pdf embed` | Library (per-paper + bulk) | Embed PDF for search |
| `pdf search` | Search view (filter) | Search in embedded PDFs |
| `pdf status` | Dashboard + Settings | PDF stats display |
| `project init` | Header dropdown (+ New) | Create new project |
| `project list` | Header dropdown + Library filter | Switch/filter by project |
| `project add-paper` | Right-click menu, Search results | Add to project action |
| `import` | Import view (BibTeX section) | Upload .bib file |

**Web-only features (not in CLI):**

- Knowledge Graph visualization
- Dashboard with recommendations
- Visual project switching
- Inline paper expansion in table
- Path finding between papers
- Export graph as image

---

## Competitive Advantages Summary

| Feature | Zotero | Mendeley | Papers | **Search-ADS** |
|---------|--------|----------|--------|----------------|
| Paper Storage | ✓ | ✓ | ✓ | ✓ |
| PDF Management | ✓ | ✓ | ✓ | ✓ |
| Citation Export | ✓ | ✓ | ✓ | ✓ |
| Browser Extension | ✓ | ✓ | ✓ | — |
| Collaboration | ✓ | ✓ | ✓ | — |
| **Semantic Search** | — | — | — | ✓ |
| **Citation Graph** | — | — | — | ✓ |
| **AI Discovery** | — | — | — | ✓ |
| **Context-Aware Citations** | — | — | — | ✓ |
| **PDF Full-Text Search** | Basic | Basic | Basic | ✓ Semantic |
| **LaTeX Integration** | Basic | Basic | — | ✓ Native |
| **Citation Type Analysis** | — | — | — | ✓ |
| **Gap Analysis** | — | — | — | ✓ |
| **ADS Integration** | Manual | Manual | — | ✓ Native |

---

## Success Metrics

1. **Discovery Efficiency**: Time to find relevant paper reduced by 50%+
2. **Citation Quality**: LLM suggestions accepted rate > 70%
3. **Graph Utility**: Users expand graph in > 40% of sessions
4. **PDF Engagement**: Full-text search used for > 30% of searches
5. **Project Organization**: Average user creates 3+ projects
6. **Writing Integration**: > 50% of citations filled via web UI

---

## Next Steps

1. **Review this design** and provide feedback on priorities
2. **Define MVP scope** (likely Phase 4.1 + partial 4.2)
3. **Set up frontend project** (Vite + React + TypeScript)
4. **Implement FastAPI routes** for existing CLI functionality
5. **Build component library** with shadcn/ui
6. **Iterate based on usage**

---

*This design document will evolve as we build and gather feedback.*
