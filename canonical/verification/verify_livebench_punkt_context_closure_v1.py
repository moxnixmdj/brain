#!/usr/bin/env python3
import json
import nltk

from canonical.runtime import livebench_punkt_context_closure_v1 as p


def main():
    assert nltk.__version__ == p.PINNED_NLTK_VERSION, nltk.__version__
    tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
    result = p.verify_with_counter(lambda s: len(tokenizer.tokenize(s)))
    with open("livebench_punkt_context_closure_v1_receipt.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(result, sort_keys=True))
    if not result["status"].startswith("PASS__"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
