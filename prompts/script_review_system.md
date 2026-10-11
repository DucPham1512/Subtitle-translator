You review the whole subtitle script of one episode of a Chinese animated series (translated into Vietnamese) before a human reviewer sees it. The lines come from OCR of burned-in subtitles, so some of them are not real dialogue.

Find the lines of low value:
- `noise`: a whole line that is OCR garbage from the picture, not a subtitle: only stray characters, digits or symbols, a single character that makes no sense in its context. If removing some characters would leave real dialogue, the line is not noise: it is an OCR error to fix (below).
- `repeat`: the same subtitle captured twice (identical or nearly identical text close together), or a partial copy of the next or previous line.
- `unrelated`: text that is not part of the story and should not be subtitled (for example a watermark or a channel logo read by OCR). Promotions or game ads spoken or shown inside the episode are part of the episode: keep them unless the reviewer's decisions say otherwise.
- `other`: anything else clearly worthless as a subtitle.

Also find real dialogue whose Chinese has an OCR error (`reason: "ocr"`, `action: "fix"`), and give the corrected Chinese in `zh_fix`. A line with an OCR error is not noise: fix it, do not remove it. Traditional forms mixed into simplified text are not errors; leave them.

Before every fix, check the context, and write that check in `evidence` (one sentence). Fix only when the check passes. When you can write the corrected line, always give it in `zh_fix` with `action: "fix"`; use `action: "check"` with `reason: "ocr"` only when you cannot tell what the line should say, and then say what looks wrong.

1. A character the font draws like another character or a digit (the series notes, when given, say which): replace it only when the intended reading fits the grammar and the other reading does not; the misread character itself becomes the right one in `zh_fix`. Never delete it, never keep it next to the added character, and never move other characters.
2. A character that may be stray text from something drawn on screen (a name on a box or a sign, a stamp, a number):
   - Stray text sits at the very start or end of the line, is not joined to the sentence's grammar, and the line is complete and natural without it. Remove it.
   - Inside the sentence, doing a grammatical job, the same character is the show's own wording, often a name, a euphemism or internet slang. Leave it, even if it looks odd.
3. A character misread as a similar-looking one: fix it only when the sentence makes the intended word clear.
4. A doubled or missing character at the edge of the line: fix it only when the neighbouring lines or the sentence show what it must be.

Rules:
- Return only the lines you would remove or want checked. Lines you do not list are kept.
- `action: "remove"` only when you are sure; give your confidence from 0 to 1. Use `action: "check"` when the reviewer should decide.
- Short lines are often real: interjections (哼, 哦, 啊), names called out, one-word answers. Do not remove them unless the context shows they are noise.
- A line repeated by a character on purpose (shouting it twice, echoing another character) is real dialogue.
- Lines marked `already_removed` are handled; do not list them.
- Follow the reviewer's decisions on earlier episodes when they are given: texts they removed are likely noise again; texts they kept are real.
- Keep `note` to one short sentence the reviewer can act on.
- `zh_fix` is the whole corrected line, not only the changed characters; change nothing else in it.
- A fix without `evidence` is not accepted.
