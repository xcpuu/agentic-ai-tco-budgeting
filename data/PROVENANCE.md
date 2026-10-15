# Provenance of HAL traces used in the Paper A pilot (E1)

Source: Holistic Agent Leaderboard, SWE-bench Verified Mini (https://hal.cs.princeton.edu/swebench_verified_mini), scaffold SWE-Agent v1.0, one run per task, 50 tasks. Traces were downloaded from the leaderboard's Traces links on 11 October 2026 and decrypted with HAL's published procedure (hal-decrypt.sh). The decrypted JSON files and the original downloads were then deleted; per-task CSVs derived from them are in this folder (hal_swebench_mini_per_task.csv).

| File name (original download) | Run ID | Model | Used | Size (bytes) | SHA-256 of original |
|---|---|---|---|---|---|
| swebench_verified_mini_1744505272_UPLOAD.json.encrypted | 1744505272 | Gemini 2.0 Flash | yes | 359874472 | 6cbf83f324a66d1f999db9ec006fc3efcc2e6c54dea6268bfee60590d06ab6bd |
| swebench_verified_mini_my_agento4mini20250416_1745279519_UPLOAD.json.encrypted | 1745279519 | o4-mini (not used) | no | 1605121392 | c27dae949c508ec30a5ac14ed6c399d791f47d30e4577d9387e7de4d104c2a76 |
| swebench_verified_mini_my_agenttogether_aideepseekaideepseekv3_1744923150_UPLOAD.json.encrypted | 1744923150 | DeepSeek V3 | yes | 67332976 | 30509f8e74f05f3b23bec3b2001f7524fcc3e8d8696c25b87e628783d0b64afa |
| swebench_verified_mini_sweagentclaudeopus4120250805_1754580585_UPLOAD.json.encrypted | 1754580585 | Claude Opus 4.1 (run labelled High on the leaderboard) | yes | 347949052 | ce4ccedac7ddccc2f39ef98056bd9129ae2ef7c335afd918dc1f332a02c83a78 |
| swebench_verified_mini_sweagentclaudesonnet4520250929_1761962167_UPLOAD.json.encrypted | 1761962167 | Claude Sonnet 4.5 (not used) | no | 945911068 | 549cf76d3b5640b82e085509f4f9323d71d6906ea8fbd432e17d71733916c3ae |
| swebench_verified_mini_sweagentclaudesonnet4520250929_1762053095_UPLOAD.json.encrypted | 1762053095 | Claude Sonnet 4.5 (not used) | no | 1018767016 | 3111989f7024f1a3ce345eb2f921bfc908ae90ffd0e2b8d291d1b2afc706abe3 |

Cost recomputation: see hal_to_csv.py (list prices, tokens from litellm.completion records only). To reproduce, re-download the three 'yes' files from the leaderboard and run hal_decrypt_json.py, hal_to_csv.py and eval_budget_coverage.py (seed 20261004).

## Addendum: USACO (primary pilot set)

Source: HAL USACO leaderboard, scaffold Episodic + Semantic, 307 tasks, one run per task. Downloaded 11 October 2026; decrypted by streaming (hal_stream_extract.py, HMAC verified) so no decrypted file was written. Per-task CSV: hal_usaco_per_task.csv (hal_calls_to_csv.py: outer litellm spans only, list prices). The o4-mini Low file was not among the downloads and was not used.

| File name (original download) | Run ID | Model | Size (bytes) | SHA-256 of original |
|---|---|---|---|---|
| usaco_usaco_episodic__semantic_claude37sonnet20250219_1744648510_UPLOAD.json.encrypted | 1744648510 | Claude 3.7 Sonnet | 1061533808 | 5d6adb9e762b2c6754fb2c0c80e12c1d6475b4d894820442aff98e875ebe4d51 |
| usaco_usaco_episodic__semantic_deepseekaideepseekv3_1744580934_UPLOAD.json.encrypted | 1744580934 | DeepSeek V3 | 714694368 | eddbbea1bb2f0068dbe597eb451befd4e23815b967673a37956f05e1a6d33dd2 |
| usaco_usaco_episodic__semantic_geminigemini20flash_1756136853_UPLOAD.json.encrypted | 1756136853 | Gemini 2.0 Flash | 4206866088 | f8c1f2dea511c830e9349cbb9bea48b9814f3a2e0bb5f1d8a07451d8d08dd8b1 |
| usaco_usaco_episodic__semantic_gpt4120250414_1744661741_UPLOAD.json.encrypted | 1744661741 | GPT-4.1 | 668861468 | 8d12da0e64da1f5d32142f8a22d2eb123609c086c4309e6c7b15333fbcfbfcc4 |

Reproduce: hal_stream_extract.py, hal_calls_to_csv.py, eval_budget_coverage.py --group-col group (seed 20261004, 20 splits).
