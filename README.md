# Omar Ibrahim

I build open-source tools for multilingual NLP, retrieval evaluation, and
reliable language systems. I am especially interested in failures that clean
benchmarks miss: mixed scripts, decomposed Unicode, keyboard substitutions,
and other orthographic variation found in real text.

## Selected work

### [OrthoDrift](https://github.com/omar07ibrahim/orthodrift)

OrthoDrift finds minimal grapheme-level changes that make a retriever lose the
relevant document. Its first research lane is Azerbaijani retrieval.

The current implementation includes provenance-preserving Unicode mutations,
deterministic BM25 experiments, reduction to minimal counterexamples, and
replayable JSONL evidence with environment-aware verification. It is a typed
Python package tested on Python 3.11 through 3.14 and licensed under Apache-2.0.
