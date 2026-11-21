# Knowledge graphs for code: a survey, and how the brain's script graph compares

**Question.** Is there something like a knowledge graph, but for code? Which technologies exist, how do they compare, and how does the script library's code graph (ADR-21, [script-library.md](../script-library.md)) sit among them?

**Short answer.** Yes, and it is an active research field. The ideas range from symbol indexes that power "go to definition" (LSIF, SCIP, Kythe, Glean, stack graphs), through program graphs built for analysis and security (the code property graph, CodeQL), and RDF knowledge graphs of code (CodeOntology, GraphGen4Code), to graphs built for LLM agents (Aider's repo map, CodexGraph, RepoGraph, LocAgent). Nearly all of them target application languages (C, Java, Python, TypeScript). None treats **operating systems** as part of the graph, and shell and PowerShell are poorly covered. The brain's script graph is deliberately small: rules over shell, PowerShell and Python files, triples with provenance and trust, and the OS as a first-class dimension.

Status: survey written 21/11/2026. Sources marked † were checked online for this survey; the rest are cited from the literature as widely known, with their venue, and should be checked before being quoted elsewhere.

## 1. What a "code knowledge graph" can mean

A knowledge graph is a set of `(subject, predicate, object)` facts with typed entities. Applied to code, the entities and edges can be taken at five levels, each richer and more expensive than the one before:

| Level | Nodes | Edges | Built by | Answers |
| --- | --- | --- | --- | --- |
| L0 · tag index | definitions (functions, classes) | none, or "defined in file" | ctags, tree-sitter tag queries | "where is X defined?" |
| L1 · symbol graph | symbols, occurrences, files | definition ↔ reference, implements, imports | compilers or indexers (LSIF, SCIP, Kythe, Glean, stack graphs) | go to definition, find references, across repositories |
| L2 · program graph | AST nodes, statements, variables | syntax, control flow, data flow, dependence | compiler front ends (code property graph, CodeQL, Doop) | "can user input reach this `exec`?" |
| L3 · code knowledge graph (RDF) | code entities **and** docs, forum posts, libraries | calls, documented by, discussed in, uses API | static analysis + linking (CodeOntology, GraphGen4Code) | "which code uses this API, and what do people say about it?" |
| L4 · graph for LLM agents | files, classes, functions, or lines | contains, calls, imports, inherits | tree-sitter or ASTs, then graph queries or ranking by an agent | "which code should the model read to fix this issue?" |

## 2. The technologies

### 2.1 Symbol graphs for navigation (L1)

- **LSIF** (Language Server Index Format, Microsoft, 2019): a dump of what a language server knows (definitions, references, hovers) as a graph of vertices and edges in JSON lines, so a code host can answer without running the server.
- **SCIP** † (SCIP Code Intelligence Protocol, Sourcegraph, 2022): a Protobuf format Sourcegraph recommends over LSIF for new indexers; organised per document with human-readable symbol strings, which makes it smaller and easier to update. Sourcegraph still accepts LSIF. Indexers exist for Go, TypeScript/JavaScript, C/C++, Java/Kotlin/Scala, Python, Ruby and C#.
- **Kythe** (Google, open source): a language-agnostic graph schema of nodes and edges (`defines/binding`, `ref`, `childof`…) filled by per-language indexers that hook into the compiler; it powers cross-references in Google's code search.
- **Glean** † (Meta, open-sourced August 2021): per-language indexers write typed *facts* into RocksDB-backed databases; **Angle**, a declarative logic language in the Datalog family, queries them and can derive language-neutral views. Meta reports first results in milliseconds on its monorepo.
- **Stack graphs** † (GitHub; Creager and van Antwerpen, arXiv:2211.01224, 2022): an extension of scope graphs (Néron et al., ESOP 2015) that resolves name bindings within and across repositories, built by purely syntactic analysis with tree-sitter, so a file is indexed once and never re-indexed because another file changed. They power GitHub's precise code navigation.

**Strength:** precise, incremental, battle-tested at very large scale. **Limit:** they answer navigation questions only; they hold no purpose, no provenance, no link to anything outside the code.

### 2.2 Program graphs for analysis (L2)

- **Code property graph (CPG)** † (Yamaguchi, Golde, Arp, Rieck, IEEE S&P 2014): one graph that merges the abstract syntax tree, the control-flow graph and the program dependence graph. Vulnerability classes become graph traversals; the authors report that almost all Linux kernel vulnerabilities of 2012 could be described this way. **Joern** is the open-source implementation, now covering C/C++, Java, JavaScript, Python and more.
- **CodeQL** (Semmle, now GitHub; Avgustinov et al., "QL: Object-oriented Queries on Relational Data", ECOOP 2016): code is extracted into a relational database and queried with QL, a Datalog-based object-oriented language. It powers GitHub code scanning.
- **Doop / Soufflé**: points-to and call-graph analysis of Java written as Datalog rules (Bravenboer and Smaragdakis, OOPSLA 2009; Soufflé, CAV 2016).
- **Program graphs for machine learning**: Allamanis, Brockschmidt and Khademi ("Learning to Represent Programs with Graphs", ICLR 2018) add data-flow edges ("last use", "last write") to the AST and train graph neural networks on them; GraphCodeBERT (Guo et al., ICLR 2021) feeds data-flow edges into a transformer.

**Strength:** semantics (what data flows where), which is what security and correctness need. **Limit:** a compiler-grade front end per language, heavy infrastructure, and shell scripts are mostly out of reach.

### 2.3 RDF knowledge graphs of code (L3)

- **CodeOntology** (Atzeni and Atzori, ISWC 2017): an OWL ontology of Java and an RDF extractor, so code can be queried with SPARQL alongside other linked data.
- **GraphGen4Code** † (Abdelaziz, Dolby, McCusker, Srinivas, K-CAP 2021, arXiv:2002.09440): data and control flow of 1.3 million Python files from GitHub, linked to the documentation of 2,300 modules and to 47 million forum posts; over 2 billion triples, as named RDF graphs. Use cases: program search, code understanding, bug detection, automation.
- **Software Heritage graph** (Pietri, Spinellis, Zacchiroli, MSR 2019): the Merkle DAG of almost all public source code and its history; content-addressed, which is the same idea as the script log's sha256.

**Strength:** code linked to knowledge about code, open standards (RDF, SPARQL). **Limit:** built for research at web scale; nothing about who generated a file, or how far to trust it.

### 2.4 Graphs for LLM agents (L4)

- **Aider's repository map** †: tree-sitter extracts definition and reference tags, files are linked by shared identifiers, and PageRank personalised toward the files in the chat ranks what to show the model within a token budget. Cheap and effective; the closest relative of the brain's design.
- **CodexGraph** † (Liu et al., NAACL 2025, arXiv:2408.03910): the repository is loaded into a graph database and the LLM agent *writes graph queries* to fetch structure-aware context. Evaluated on CrossCodeEval, SWE-bench and EvoCodeBench, for Python only.
- **RepoGraph** † (Ouyang et al., ICLR 2025, arXiv:2410.14684): a plug-in graph whose nodes are lines of code and whose edges are dependencies between them, filtered to project-specific relations; it improved all four SWE-bench methods it was added to.
- **LocAgent** † (Chen et al., ACL 2025, arXiv:2503.09089): a directed heterogeneous graph of files, classes and functions with import, invocation and inheritance edges, indexed in seconds; agents search it with multi-hop tools to find the code an issue touches. A fine-tuned 32B open model came close to proprietary models at about 86% lower cost (the authors' figures).
- **Survey** † (Tao, Qin, Liu, "Retrieval-Augmented Code Generation: A Survey with Focus on Repository-Level Approaches", arXiv:2510.04905, 2025): classifies graph-based and non-graph retrieval for repository-level generation; the entry point to this literature.
- Related general methods the brain already uses or cites: GraphRAG (Edge et al., Microsoft, 2024) and HippoRAG (Gutiérrez et al., NeurIPS 2024), whose Personalized PageRank over a knowledge graph is the brain's optional `[search] graph_weight` signal.

**Strength:** designed for the job an AI assistant does: find the relevant code before writing more. **Limit:** research prototypes, mostly Python, mostly one repository; trust and provenance are not modelled.

### 2.5 Shell and PowerShell specifically

The graphs above barely cover scripts. What exists is analysis, not graphs: **tree-sitter-bash** and the **PowerShell AST** (`System.Management.Automation.Language`) parse scripts; **ShellCheck** and **PSScriptAnalyzer** lint them; **NL2Bash** (Lin et al., LREC 2018) pairs English descriptions with Bash commands; **explainshell** and **tldr-pages** map commands to their documentation. No tool links a Linux script to its macOS, Red Hat and Windows equivalents, or tells which commands exist on which system.

## 3. Comparison

| | Level | Graph model | Extraction | Query | Languages | Incremental | Provenance / trust | Infrastructure | OS dimension |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ctags | L0 | none | regex / tree-sitter | grep | 40+ | per file | no | none | no |
| LSIF / SCIP | L1 | document-centric symbols | compiler indexers | code host API | ~10 major | per upload | no | indexer per language + host | no |
| Kythe | L1 | node/edge schema | compiler hooks | xrefs service | C++, Java, Go… | build-driven | no | heavy | no |
| Glean | L1–L2 | typed facts | indexers | Angle (Datalog-like) | many | yes | no | server, RocksDB | no |
| Stack graphs | L1 | scope graph | tree-sitter rules | path finding | Python, JS/TS, Java… | per file | no | moderate | no |
| CPG / Joern | L2 | property graph | front ends | Scala DSL / traversals | C/C++, Java, JS, Python… | partial | no | JVM | no |
| CodeQL | L2 | relational | extractors | QL (Datalog) | ~10 | per build | no | CLI + DB | no |
| GraphGen4Code | L3 | RDF named graphs | WALA analysis + linking | SPARQL | Python | batch | source URLs only | triple store | no |
| Aider repo map | L4 | file graph | tree-sitter tags | PageRank | 100+ via tree-sitter | per file | no | none | no |
| CodexGraph | L4 | graph DB | AST | Cypher, written by the LLM | Python | batch | no | Neo4j | no |
| RepoGraph | L4 | line-level graph | tree-sitter | ego-graph retrieval | Python | batch | no | none | no |
| LocAgent | L4 | heterogeneous graph | AST | agent tools, multi-hop | Python | seconds per repo | no | none | no |
| **Brain script graph** | L1-lite + L4 | triples (JSONL in git) | rules (regex) | `brain kg ask`: seeds + 2 hops; search with optional PPR | sh, bash, zsh, PowerShell, batch, Python | per document hash | **yes**: source, kind, method, trust on every fact | none (standard library) | **yes** |

## 4. Where the brain's implementation sits

What the script library builds (`tools/brain/scripts.py`, `scripts.documents`):

```text
script <name> → in topic        → 52.xx <topic>
script <name> → purpose         → <one line>
script <name> → runs on         → <OS label>          one per variant
script <name> → calls on <os>   → <command>           first word of each pipeline stage, cmdlets, native programs
script <name> → imports         → <module>            Python
script <name> → not for         → <OS label>          from not_applicable
```

It joins the brain's existing graph (`vault/_kg/triples.jsonl`), so scripts connect to notes, projects and conversations through shared entities: a command node such as `firewall-cmd` links every script that calls it, on every OS.

### 4.1 Compared with the literature

| Property | Brain script graph | Closest relative | Comment |
| --- | --- | --- | --- |
| Granularity | script and command | Aider (file and tag), LocAgent (file, class, function) | Scripts are small: the unit of reuse is the whole script, not its functions |
| Extraction | regular-expression rules, no execution, no LLM | tree-sitter in Aider, stack graphs, RepoGraph, LocAgent | Rules miss commands built in variables (`$CMD arg`), aliases, here-documents, `eval`, and commands inside functions defined in other files |
| Semantics | none (no data or control flow) | CPG, CodeQL | Enough to answer "which script, which OS, which tool"; not "is this script safe" |
| Storage | sorted JSONL in git | GraphGen4Code (RDF), Glean (RocksDB), CodexGraph (Neo4j) | Readable diffs, no server; does not scale past ~10⁵ triples comfortably, which a personal library will not reach |
| Query | entity match, 2 hops, Personalized PageRank in search | Angle, QL, Cypher, SPARQL | No query language: an agent cannot ask "scripts that call `dnf` but have no Windows variant" in one query; `brain script list --os` and `brain check` cover the common cases |
| Provenance | every fact has source, method and trust; every file has generated_by, prompt and sha256 | none in the surveyed systems | The brain's distinctive part: a fact from a script (`system`) never mixes with the owner's notes (`owner`) or an agent's claim |
| Cross-OS parity | first-class: variants, `required_os`, `not_applicable`, `avoid` lint | none | No surveyed system models it |
| Evaluation | unit tests (`tests/test_scripts.py`); no retrieval benchmark yet | SWE-bench, CrossCodeEval, Loc-Bench | `brain eval` measures note search; scripts need their own questions (see P6) |

### 4.2 Strengths and weaknesses, plainly

**Strong:** costs nothing to run, works offline, keeps every script with who made it and from which request, puts the OS in the model, enforces parity with `brain check`, and reuses the brain's existing graph, trust model and search.

**Weak:** extraction is lexical, so commands reached indirectly are missed and a few false commands slip through; there is no data flow, no call graph between scripts (`source lib.sh`, `Import-Module`), no equivalence between commands across systems, and no query language.

## 5. Proposals (not adopted; they go through [design-suggestions.md](../design-suggestions.md))

| # | Proposal | From | Cost | Measure before adopting |
| --- | --- | --- | --- | --- |
| P1 | Optional tree-sitter-bash and PowerShell AST extraction, falling back to the rules when not installed | stack graphs, Aider, LocAgent | an optional dependency | precision and recall of `calls` on 50 hand-labelled scripts, rules vs parser |
| P2 | `sources` edges for `source`/`.`, dot-sourcing and `Import-Module`, giving a call graph between scripts | LocAgent's import edges | small | number of scripts with an unresolved dependency |
| P3 | An owner-curated command equivalence table (`apt ↔ dnf ↔ brew ↔ winget`, `systemctl ↔ launchctl ↔ Get-Service`, `ufw ↔ firewall-cmd ↔ pf ↔ New-NetFirewallRule`) as triples, so an agent can draft a missing variant and `brain check` can compare variants | NL2Bash, tldr-pages | a table to maintain | share of SC-03 gaps an agent closes with a variant that passes the owner's test |
| P4 | ShellCheck and PSScriptAnalyzer findings as `lint` facts on each variant | CodeQL, CPG (analysis results as graph data) | optional tools | findings per variant over time |
| P5 | `tested` per OS with date and machine; a tested variant ranks above an untested one | the brain's grades | small | how often an untested variant is reused |
| P6 | Script questions in `vault/_eval/questions.md` so `brain eval` measures recall@k on the library | SWE-bench, Loc-Bench | the owner's questions | recall@8 ≥ 0.8 before any ranking change |

## References

† checked online for this survey.

1. † Yamaguchi, F., Golde, N., Arp, D., Rieck, K. Modeling and Discovering Vulnerabilities with Code Property Graphs. IEEE S&P 2014, pp. 590–604. https://mlsec.tu-berlin.de/docs/2014-ieeesp.pdf
2. † Abdelaziz, I., Dolby, J., McCusker, J., Srinivas, K. A Toolkit for Generating Code Knowledge Graphs (GraphGen4Code). K-CAP 2021. https://arxiv.org/abs/2002.09440 · https://wala.github.io/graph4code
3. † Liu, X., Lan, B., et al. CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases. NAACL 2025, pp. 142–160. https://aclanthology.org/2025.naacl-long.7/
4. † Ouyang, S., et al. RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph. ICLR 2025. https://arxiv.org/abs/2410.14684
5. † Chen, Z., et al. LocAgent: Graph-Guided LLM Agents for Code Localization. ACL 2025. https://arxiv.org/abs/2503.09089
6. † Tao, Y., Qin, Y., Liu, Y. Retrieval-Augmented Code Generation: A Survey with Focus on Repository-Level Approaches. arXiv:2510.04905, 2025. https://arxiv.org/abs/2510.04905
7. † Sourcegraph. SCIP – a better code indexing format than LSIF. https://sourcegraph.com/blog/announcing-scip
8. † Creager, D., van Antwerpen, H. Stack graphs: name resolution at scale. arXiv:2211.01224, 2022. https://github.com/github/stack-graphs
9. † Meta Engineering. Indexing code at scale with Glean. 19/12/2024. https://engineering.fb.com/2024/12/19/developer-tools/glean-open-source-code-indexing/
10. † Aider repository map: tree-sitter tags, a file graph, Personalized PageRank, a token budget; as described by its ports (RepoMapper, https://github.com/Cryect/RepoMapper) and aider's own `aider/repomap.py`.
11. Néron, P., Tolmach, A., Visser, E., Wachsmuth, G. A Theory of Name Resolution. ESOP 2015.
12. Avgustinov, P., de Moor, O., et al. QL: Object-oriented Queries on Relational Data. ECOOP 2016.
13. Bravenboer, M., Smaragdakis, Y. Strictly Declarative Specification of Sophisticated Points-to Analyses (Doop). OOPSLA 2009.
14. Allamanis, M., Brockschmidt, M., Khademi, M. Learning to Represent Programs with Graphs. ICLR 2018.
15. Guo, D., et al. GraphCodeBERT: Pre-training Code Representations with Data Flow. ICLR 2021.
16. Atzeni, M., Atzori, M. CodeOntology: RDF-ization of Source Code. ISWC 2017.
17. Pietri, A., Spinellis, D., Zacchiroli, S. The Software Heritage Graph Dataset. MSR 2019.
18. Lin, X. V., Wang, C., Zettlemoyer, L., Ernst, M. D. NL2Bash: A Corpus and Semantic Parser for Natural Language Interface to the Linux Operating System. LREC 2018.
19. Edge, D., et al. From Local to Global: A Graph RAG Approach to Query-Focused Summarization. Microsoft Research, arXiv:2404.16130, 2024.
20. Gutiérrez, B. J., et al. HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models. NeurIPS 2024.
