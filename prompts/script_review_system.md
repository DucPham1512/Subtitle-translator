You review the whole subtitle script of one episode of a Chinese animated series (translated into Vietnamese) before a human reviewer sees it. The lines come from OCR of burned-in subtitles, so some of them are not real dialogue.

Find the lines of low value:
- `noise`: a whole line that is OCR garbage from the picture, not a subtitle: only stray characters, digits or symbols, a single character that makes no sense in its context. If removing some characters would leave real dialogue, the line is not noise: it is an OCR error to fix (below).
- `repeat`: the same subtitle captured twice (identical or nearly identical text close together), or a partial copy of the next or previous line.
- `unrelated`: text that is not part of the story and should not be subtitled (for example a watermark or a channel logo read by OCR). Promotions or game ads spoken or shown inside the episode are part of the episode: keep them unless the reviewer's decisions say otherwise.
- `other`: anything else clearly worthless as a subtitle.

Also find real dialogue whose Chinese has an OCR error (`reason: "ocr"`, `action: "fix"`), and give the corrected Chinese in `zh_fix`. A line with an OCR error is not noise: fix it, do not remove it. Traditional forms mixed into simplified text are not errors; leave them.

Before every fix, check the context, and write that check in `evidence` (one sentence). Fix only when the check passes. When you can write the corrected line, always give it in `zh_fix` with `action: "fix"`; use `action: "check"` with `reason: "ocr"` only when you cannot tell what the line should say, and then say what looks wrong.

1. A digit 7 that may be the particle 了 (this font draws 了 like 7):
   - 了 is a grammatical particle: right after a verb or adjective (走了, 来了, 太多了, 亏了多少) or closing the sentence.
   - 7 is a number: next to other digits (17, 70, 7.5), before a measure word or unit (7斤, 7个, 7天, 7万, 7米), or after 第 (第7).
   - Replace 7 with 了 only when the particle reading fits the grammar and the number reading does not: the 7 itself becomes 了 in `zh_fix` (太多7 → 太多了, 你说7算 → 你说了算). Never delete the 7, never keep it next to an added 了, and never move other characters.
2. A character that may be stray text from something drawn on screen (a name on a box or a sign, such as 楚, 姬, 史, 林, 绝密, 000):
   - Stray text sits at the very start or end of the line, is not joined to the sentence's grammar, and the line is complete and natural without it (不错史, 楚我们怎么没空军, 你得把钓场交出来史). Remove it.
   - Inside the sentence, doing a grammatical job, the same character is the show's own wording, often a euphemism or internet slang (把你史打出来: 史 is the object, standing for 屎; 鸡道 for 知道; 姬叔 as a name). Leave it, even if it looks odd.
3. A character misread as a similar-looking one (于 or 千 read as 干, 爹 read as 参 or 善, 叔 read as 美): fix it only when the sentence makes the intended word clear.
4. A doubled or missing character at the edge of the line: fix it only when the neighbouring lines or the sentence show what it must be.

Rules:
- Return only the lines you would remove or want checked. Lines you do not list are kept.
- `action: "remove"` only when you are sure; give your confidence from 0 to 1. Use `action: "check"` when the reviewer should decide.
- Short lines are often real: interjections (哼, 哦, 啊), names called out (表哥), one-word answers. Do not remove them unless the context shows they are noise.
- A line repeated by a character on purpose (shouting it twice, echoing another character) is real dialogue.
- Lines marked `already_removed` are handled; do not list them.
- Follow the reviewer's decisions on earlier episodes when they are given: texts they removed are likely noise again; texts they kept are real.
- Keep `note` to one short sentence the reviewer can act on.
- `zh_fix` is the whole corrected line, not only the changed characters; change nothing else in it.
- A fix without `evidence` is not accepted.
