# ExitLens

Describe a consumer problem in plain words ("my headphones stopped working after two weeks"). TinyFish web agents visit the live seller and brand sites, find the real policy pages, and ExitLens returns a checklist where every step links to its source quote. Every quote is checked by code against the fetched page text; anything that fails shows **Could not verify**. Guidance only, not legal advice.

## Run it (3 minutes)

```bash
cd exitlens
./run.sh            # first run creates .env, then exits
# edit .env: put your TINYFISH_API_KEY (and optionally ANTHROPIC_API_KEY)
./run.sh            # open http://localhost:8000
```

Windows (no bash): `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`, copy `.env.example` to `.env`, then `python -m uvicorn backend.app:app --port 8000`.

**Test without spending credits:** set `EXITLENS_MODE=fixture` in `.env`. It uses fictional "ShopEasy" and "Acme Audio" pages (a loud banner shows in the UI). Try: *"My Acme Audio headphones stopped working after two weeks, bought from ShopEasy"*. **For the real demo set `EXITLENS_MODE=live`.**

Run the tests: `python -m pytest tests -q`

## How it works (maps to the PRD)

| Stage | File | What happens |
|---|---|---|
| 1 Understand | `pipeline.py`, `llm.py`, `heuristics.py` | Claude parses the case (or rule-based fallback). Asks one follow-up if the seller is missing |
| 2 Discover | `discovery.py` | TinyFish **Search**, then keeps only official domains, drops coupon/blog sites |
| 3 Read | `pipeline.py`, `tinyfish.py` | Parties run **in parallel**. **Fetch** first; if the policy is not on the page, a browser **Agent** navigates to it (tiered to save credits) |
| 4 Verify | `verify.py` | Code only: quote must appear in the page text and the URL must be on the official site |
| 5 Plan | `plan.py`, `dates.py` | Checklist built from verified facts only. Deadlines computed in code |
| Extras | `pipeline.py` | Claim email draft, Claim Helper (agent fills the form, stops before submit), policy watch, chatbot-vs-ExitLens panel |

Live progress uses Server-Sent Events (`/api/cases/{id}/events`). Results are cached in SQLite (`CACHE_TTL`) so repeated demo runs cost almost nothing.

## Things to know before the finale

- **Nothing here was run against the real TinyFish API** (it could not be reached from where this was built). The endpoints follow docs.tinyfish.ai, and all TinyFish calls live in `backend/tinyfish.py`. If a field name differs, that is the only file to fix. Run one real case first and send me any error.
- **Backend is Starlette** (the engine under FastAPI), and the frontend is plain HTML/JS with no build step, so there is nothing to compile.
- **Policy watch** compares a fingerprint of each page on demand ("Check now"). It does not use TinyFish Monitor, because its API was not documented where I looked. You can swap it in later.
- **Claim Helper** needs a real run to confirm the agent stops before submit. Test it on a harmless form with dummy details first.
- Claude key is optional. Without it, extraction uses simple sentence rules, so results are rougher. Add `ANTHROPIC_API_KEY` for better quality, and for the chatbot comparison panel.
- Hero demo checklist: pick one brand and one retailer, run it the day before and the morning of, keep two backup cases, check your TinyFish wallet balance.
- Keep `.env` out of GitHub, slides and screenshots.
