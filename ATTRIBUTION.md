# Attribution

This repository packages material from upstream sources. Each is listed with its
license and what was taken. If you redistribute this work, these obligations
travel with it.

| Component | Upstream | License | Obligation |
|---|---|---|---|
| `embodied-emotion`, `stated-lesson`, `tidy-closer` in `.claude/hooks/patterns.json` | [NulightJens/humanizer-stack](https://github.com/NulightJens/humanizer-stack) (`skills/structural-humanizer/scripts/structural_scan.py`) | MIT | Keep the copyright and license notice below |
| The surface rule catalog (`inflated-symbolism`, `ai-vocabulary`, `vague-attribution`, and the rest) | [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), via [blader/humanizer](https://github.com/blader/humanizer) | CC BY-SA 4.0 upstream, MIT for the skill | Attribute and share alike |
| Structural thresholds and the convergence rule in `CLAUDE.md` | Russell, Rajendhran, Pham, Iyyer, Wieting, *StoryScope: Investigating Idiosyncrasies in AI Fiction*, COLM 2026 | academic citation | Cite, do not relicense |

## 1. Narrative rules (MIT)

The three narrative rule families in `.claude/hooks/patterns.json` are ported
from `structural_scan.py` in
[NulightJens/humanizer-stack](https://github.com/NulightJens/humanizer-stack),
which is original work in that repository under the MIT License:

```
MIT License

Copyright (c) 2026 Jens Heitmann

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**What changed in the port.** The patterns are theirs; the surrounding machinery
is not. Their scanner counts hits per category against a per-category threshold.
Here the same patterns carry a severity and feed one weighted document score, and
`tidy-closer` is marked `"region": "tail"` so it only fires in the closing
paragraphs rather than being scanned against a separately extracted tail string.

One pattern was deliberately dropped: their `^(?:so|ultimately|…)` line-start
rule also matches a bare "So" opening a sentence, which is common in human
conversational writing. The remaining closers are kept.

## 2. Surface rules (CC BY-SA 4.0 upstream)

The vocabulary lists and named tells trace back to
[Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
maintained by WikiProject AI Cleanup, which is licensed **CC BY-SA 4.0** — a
share-alike license.

Individual words and facts are not copyrightable, but the selection and
arrangement of a catalog can be. The regexes here were written independently, and
the categories they are grouped under follow that article's taxonomy. Treat the
rule catalog as carrying share-alike obligations.

## 3. StoryScope

The structural thresholds, and the convergence rule in `CLAUDE.md`, come from
*StoryScope: Investigating Idiosyncrasies in AI Fiction* (Russell, Rajendhran,
Pham, Iyyer, Wieting; COLM 2026). Figures cited in this repo: 93.2 macro-F1 on
discourse features alone, 93.9 after professional span-level rewriting, embodied
emotion at 81% against 38%, stated theme at 77% against 52%.

A caveat the paper's own authors would insist on, and which
`humanizer-stack`'s README states plainly: StoryScope studied roughly 5,000-word
fiction. Applying its findings to short nonfiction is an inference, not a result
the paper establishes.

## This repository's own work

The hooks, the scoring model, the scope system, and the tests are this
repository's own, released under the MIT License. See [LICENSE](LICENSE).

MIT covers this repository's own work only. It does not and cannot relicense the
upstream material above: the ported narrative rules keep Jens Heitmann's MIT
notice, and the surface rule catalog carries CC BY-SA 4.0 share-alike
obligations from Wikipedia. Both travel with any redistribution.
