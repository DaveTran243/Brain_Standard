# Search questions · the yardstick for brain search

The owner writes this file; an AI never does (BRD section 9, metric M1). `brain eval` (milestone M1) runs every
question through `brain search` and reports recall@8 and MRR: whether the right note is among the first 8 results,
and how high.

How to write it:
- About 30 questions, in Vietnamese and English mixed, the way you would really ask them. Six per section below.
- After the arrow, the vault path of the note that answers it. Several notes: separate them with `;`.
- A question the brain has no answer to: write `none` after the arrow (it checks the search says "not found").
- Keep a question even when search gets it wrong; that is what the file is for.

Line format: `- <question> → <path>` e.g. `- johnny decimal giữ gì ổn định? → 30-Knowledge/permanent/johnny-decimal.md`

## 1 · Information: one fact from one note

## 2 · Across notes: the answer needs two or more notes

## 3 · Time: when something happened or was decided

## 4 · Updates: a fact that changed; the newest note is the right one

## 5 · Not in the brain: the answer is `none`
