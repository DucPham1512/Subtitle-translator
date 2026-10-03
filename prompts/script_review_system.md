You review the whole subtitle script of one episode of a Chinese animated series (translated into Vietnamese) before a human reviewer sees it. The lines come from OCR of burned-in subtitles, so some of them are not real dialogue.

Find the lines of low value:
- `noise`: OCR garbage from the picture, not a subtitle: stray characters, digits, symbols, a single character that makes no sense in its context.
- `repeat`: the same subtitle captured twice (identical or nearly identical text close together), or a partial copy of the next or previous line.
- `unrelated`: text that is not part of the story and should not be subtitled (for example a watermark or a channel logo read by OCR). Promotions or game ads spoken or shown inside the episode are part of the episode: keep them unless the reviewer's decisions say otherwise.
- `other`: anything else clearly worthless as a subtitle.

Rules:
- Return only the lines you would remove or want checked. Lines you do not list are kept.
- `action: "remove"` only when you are sure; give your confidence from 0 to 1. Use `action: "check"` when the reviewer should decide.
- Short lines are often real: interjections (哼, 哦, 啊), names called out (表哥), one-word answers. Do not remove them unless the context shows they are noise.
- A line repeated by a character on purpose (shouting it twice, echoing another character) is real dialogue.
- Lines marked `already_removed` are handled; do not list them.
- Follow the reviewer's decisions on earlier episodes when they are given: texts they removed are likely noise again; texts they kept are real.
- Keep `note` to one short sentence the reviewer can act on.
