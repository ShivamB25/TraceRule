# Writing Style: Anti-AI-Slop Guidelines

Consolidated from 4 skills: de-slopify, not-ai-writer, stop-slop, humanizer.
Apply to ALL prose in this project (README, docs, comments, commit messages).

## Hard rules (always fix)

### Vocabulary bans
Never use: delve, tapestry, symphony, realm, comprehensive, holistic, intricate,
meticulous, impressively, vibrant, profound, nestled, breathtaking, groundbreaking,
pivotal, showcase, underscore, foster, harness, leverage, orchestrate, elevate,
unlock, unleash, bolster, catalyze, demystify, elucidate, garnish.

Replace with plain English. "examine" not "delve into". "complete" not "comprehensive".
"complex" not "intricate". "careful" not "meticulous".

### Em dash overuse
Replace most em dashes with commas, semicolons, colons, or split into two sentences.
One or two per document is fine. Five is a pattern.

### Banned phrase patterns
- "Here's why" / "Here's why it matters" / "Here's the thing" — just explain directly
- "It's not X, it's Y" / "It's not just X, it's also Y" — rewrite without the formula
- "Let's dive in" / "Let's get started" — just start
- "At its core" / "Fundamentally" / "In essence" — delete or rephrase
- "It's worth noting that" / "It's important to remember" — just state the fact
- "Moreover" / "Furthermore" / "Additionally" / "Consequently" — use sparingly or delete
- "serves as" / "stands as" / "marks a" — use "is"
- "I hope this helps" / "Certainly!" / "Great question!" — never in docs

### Structural tells
- Rule of three overuse: don't force ideas into groups of three
- Negative parallelisms: "Not only...but..." — rewrite
- Synonym cycling: don't swap synonyms for the same noun every sentence
- Identical paragraph structure: vary it
- Excessive bold in inline text: use sparingly
- Bolded-header bullet lists ("**Feature:** description") — convert to prose or plain bullets
- Every heading in Title Case: use sentence case

### Filler phrases (always cut)
- "In order to" → "To"
- "Due to the fact that" → "Because"
- "At this point in time" → "Now"
- "Has the ability to" → "Can"
- "It is important to note that" → (delete, just state it)

### Hedging (cut excessive qualification)
- "It could potentially possibly be argued" → "The policy may affect"
- Don't stack qualifiers. One hedge per claim maximum.

## Soft rules (use judgment)

### Sentence rhythm
Mix lengths. Short sentence. Then a longer one that takes its time. Don't write
five 12-word sentences in a row. Fragments are OK for emphasis.

### Voice
- Use contractions naturally (it's, won't, can't) in informal docs
- Be direct. "The scanner runs SQL" not "The scanner is designed to execute SQL queries"
- Have opinions in design docs. "We chose X because Y" not "X was selected"
- Use specific numbers and names, not vague claims

### Technical docs specifically
- Technical accuracy beats style. Don't sacrifice correctness.
- Code examples are fine as-is. Focus editing on prose paragraphs.
- Lists and tables are fine when they genuinely organize information.
- Keep structure when it serves the reader. Remove it when it's decorative.

## Scoring rubric (quick self-check before shipping)

| Dimension    | Question                          |
|-------------|-----------------------------------|
| Directness  | Am I stating things or announcing them? |
| Rhythm      | Do sentence lengths vary?         |
| Trust       | Am I explaining things the reader already knows? |
| Authenticity | Would a human engineer write it this way? |
| Density     | Can I cut anything without losing meaning? |

## Process for editing existing docs

1. Read the full document
2. Search for banned vocabulary and phrases (grep if needed)
3. Count em dashes — if more than 2-3, replace most
4. Check paragraph structure — break up identical patterns
5. Cut filler phrases and excessive hedging
6. Verify technical accuracy wasn't harmed
7. Read aloud — if it sounds like a press release, rewrite
