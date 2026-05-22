# Project Rules

## Evidence

**NEVER ASSUME SOMETHING, ALWAYS FIND A PROOF OF WHAT YOU ARE SAYING.**

Applies to every claim you make in this project: technical facts, library behavior, algorithm correctness, performance characteristics, third-party API behavior, "industry standard" claims, anything.

Concretely, before stating something as fact:
- If it's about code in this repo: read the code. Quote the file and line.
- If it's about a library, framework, or tool: read its docs, source, or run it. Link the source.
- If it's about an algorithm or technique: cite the paper, the open-source implementation, or derive it from first principles in the message.
- If it's about how another product works (nonograms.com, Sudoku.com, etc.): find a reference, screenshot, reverse-engineering writeup, or interview. Do not infer from "it probably works like X".
- If you cannot find proof: say so explicitly. "I don't know" and "I couldn't verify this" are correct answers. Guessing dressed up as fact is not.

When summarizing research or design decisions in writing, include the sources inline so future-you and the user can audit the reasoning.

This rule overrides any habit toward confident-sounding answers. Confidence without evidence is the failure mode to avoid.

## Uncertainty

**IF YOU ARE NOT 100% SURE OF SOMETHING, DO NOT ASSUME AND DO NOT WRITE CODE FOR IT. ASK FIRST.**

When uncertainty appears, stop and ask the user rather than picking a plausible-looking answer and moving on. This includes:
- Algorithm choice: if two approaches both seem reasonable and you don't have evidence one is correct for this case, ask.
- API or library behavior you haven't verified: ask or go verify, do not guess.
- Domain rules (game rules, business logic, UX intent): if the spec is silent or ambiguous, ask. Do not invent a rule.
- File/module/architecture placement when conventions don't clearly dictate it: ask.
- Anything the user said that could be interpreted two ways: ask which they meant.

Writing speculative code "to show what it might look like" is not allowed unless the user explicitly asks for a sketch. Speculative code wastes the user's review time and creates pressure to keep it.

The acceptable responses to uncertainty are: ask the user, do research and cite findings, or say "I don't know" explicitly. Never silently fill the gap with a guess.
