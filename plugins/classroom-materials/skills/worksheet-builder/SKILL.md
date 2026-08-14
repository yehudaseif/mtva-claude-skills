---
name: worksheet-builder
description: Turn a source text into classroom-ready material — worksheets with answer keys, differentiated reading-level variants, vocabulary sets, quizzes, and study guides — as editable Word documents. Use when a teacher supplies a chapter, article, source sheet, or unit outline and wants student-facing material built from it.
---

# Worksheet Builder

A source text goes in; material a teacher can walk into a classroom with comes
out. The teacher edits it afterwards — that is expected, and the output should
be easy to edit rather than clever.

Word documents, via the built-in `docx` skill. `.docx` because teachers need to
change a question five minutes before the lesson. Only produce a PDF when the
user explicitly asks for one.

## Read the source first

Read the whole text before writing a single question. Then say, in two or three
lines, what you understand it to be — its subject, its difficulty, its length,
and anything that shapes the material (it's a primary source; it's a translation;
it assumes prior chapters; it contains Hebrew).

If the source is thin or the request is ambiguous, ask before generating. The
questions to ask, in order of how much they change the output:

1. **Year group and reading level.** Everything follows from this.
2. **What is it for** — homework, in-class, assessment, revision, a substitute
   teacher covering the lesson?
3. **How long** should it take a student?
4. **Anything to avoid** — a topic handled elsewhere, a text the class hasn't
   reached, a translation the school doesn't use.

One round of questions, not an interrogation. If the user has given enough to
proceed sensibly, proceed and state your assumptions at the top of your reply.

## Writing questions that are worth answering

The failure mode is a page of questions whose answers can be copied straight
out of the text without reading it. Avoid that deliberately:

- **Build a ladder.** Open with two or three retrieval questions so every
  student can start, then move to inference, then to at least one question with
  no single right answer.
- **Ask about the text, not around it.** "What does the author assume the reader
  already believes?" beats "What year was this written?"
- **Vary the form.** Short answer, a passage to annotate, one thing to compare,
  something to justify.
- **Never write a question the source can't answer.** Check each one against the
  text before it ships.

## The answer key

Always generate one, on its own page, and say what page it starts on so the
teacher can detach it.

- Give the actual expected answer, not "answers will vary" — for open questions,
  give two or three genuinely different strong responses so the teacher has a
  marking range.
- Include the line or paragraph each answer comes from. That's what makes the
  key usable while marking at speed.

## Differentiated versions

This is the highest-value thing here, because it's the version that never gets
made by hand. When asked for one:

- **Same content, same questions, different access.** Do not cut the intellectual
  demand — shorten sentences, define hard vocabulary inline, break multi-part
  questions into steps, add a sentence starter where a student would otherwise
  stall on a blank page.
- **Keep the answer key identical.** If the key has to change, the versions have
  drifted apart and the class is no longer doing the same lesson.
- Never label the file or the header in a way a student would read as a
  downgrade. `chapter3-worksheet-B.docx`, not `chapter3-easy.docx`. This matters
  and is not negotiable.
- Ask whether an extension version is wanted too — the same text with harder
  questions for students who finish early.

## Layout

Teachers photocopy these. Design for that:

- Leave real writing space. A question with two blank lines under it gets a
  two-line answer; the space is the instruction.
- One page if it can be one page. Number the questions.
- A header line with space for name, class, and date.
- No colour dependence — it will be printed in black and white.
- Vocabulary in a boxed list, not scattered through the prose.

## Hebrew and mixed-script text

- Never mix Hebrew and Latin characters inside a single word or token — the
  bidirectional rendering breaks and brackets migrate to the wrong side. Keep
  Hebrew words whole and standalone, or transliterate.
- Ask which transliteration convention the school uses rather than picking one.
- If the source has a facing translation, ask whether students should see both.

## Before handing it over

State plainly what you have and have not checked. You have checked the
questions against the source. You have **not** checked them against the
curriculum, the exam board, or what the class covered last week — the teacher
owns that. Say so in a line rather than implying the material is ready to
photocopy unread.
