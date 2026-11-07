# Notices

## ai-knowledge-graph

Parts of `tools/brain/kgcore.py` are adapted from [ai-knowledge-graph](https://github.com/robert-mcdermott/ai-knowledge-graph) by Robert McDermott, licensed under the Apache License, Version 2.0 (<https://www.apache.org/licenses/LICENSE-2.0>), as read at commit `4709a05` (2026-09-12):

- the S-P-O extraction prompt (`prompts/main_prompts.py`), shortened and changed to keep the document's language and forbid outside knowledge;
- the English singularisation rule (`entity_standardization._singularize`);
- the taxonomy inference rule (`[inference] taxonomy`), extended to head-first languages;
- the graph index, entity matching and neighbourhood retrieval (`query.GraphIndex`, `match_entities`, `retrieve_subgraph`), changed to rank by trust and to match Unicode words.

Changes: rewritten for the Python standard library, with provenance and trust on every triple, incremental builds from the vault, and no visualisation. The export (`brain kg export`) writes ai-knowledge-graph's JSON shape so its tools can read the brain's graph.
