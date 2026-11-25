# B prompt catalog

[prompt_v1.0.yaml](prompt_v1.0.yaml) preserves the B legacy researcher and
collaboration prompt catalog from [commit 6817a5a](https://github.com/298994923/TradingAgents-Teamwork/commit/6817a5a221124a950c537e65d0429ad94ac5f88d).
The original bytes are retained for experiment provenance.

The catalog digests describe canonical JSON mappings of catalog entries.
The main workflow loads its research prompts from the Python agent templates.
The CLI receipt records the hash of the template used for that call and the
hash of the actual input, which can include B's context compaction. Use that
receipt when checking what a main-branch run sent.
