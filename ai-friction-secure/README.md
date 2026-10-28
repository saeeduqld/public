# AI Friction Chatbot — Private OpenRouter Key

This version does **not** ask participants for an OpenRouter API key or model. A small Python backend stores and uses a private OpenRouter key. Both AI conditions use the **same server-configured model**; the vanilla condition has **no system or developer instructions**.

## Configuration

The hosting owner must configure once (not each participant):

| Variable | Purpose | Where to store |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter credential | Render environment secret, or local untracked `.env` |
| `OPENROUTER_MODEL` | Fixed model for both conditions | Render environment setting, or local `.env` |
| `APP_ACCESS_CODE` | Private pilot access code for coauthors | Render environment secret, or local `.env` |

A browser user sees only **pilot access code** (not the OpenRouter key or model input). The access code prevents anyone on the internet from draining the key's OpenRouter credits. Give coauthors the pilot access code privately. Use a spending-limited OpenRouter key; never include identifying participant or patient data during this pilot.

### Local

1. `cp .env.example .env` (on Windows copy via Explorer)
2. Put your key, model, and access code in `.env` locally — it is ignored by Git.
3. `pip install -r requirements.txt`
4. `uvicorn app:app --host 127.0.0.1 --port 7860`
5. Open `http://127.0.0.1:7860`.

### Render free public hosting

1. Connect the repository at `https://github.com/saeeduqld/public` to Render.
2. Create a **Web Service** using the **Free** instance with **Root Directory** `ai-friction-secure`.
3. **Build command**: `pip install -r requirements.txt`.
4. **Start command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`.
5. Under **Environment**, set `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and `APP_ACCESS_CODE`.
6. Deploy and use the actual `https://<service-name>.onrender.com` URL shown by Render.

No public GitHub file contains your real key. Free Render instances can spin down when idle and can have usage limits. OpenRouter API calls are billed separately. The existing GitHub Pages site is a static demonstration that still asks for a key; use the new Render URL after backend deployment.

## Notes on research design and security

- No transcripts are stored by this backend; the browser can export conversations.
- Friction instructions remain editable in the pilot; vanilla sends no system message.
- Server enforces the selected model and caps completion tokens.
- Server limits calls in memory per connection IP; it is not a production-grade rate limiter. Add a stronger rate limiter before a full study.
- The model provider processes conversation data under its own policies.
- Never commit `.env` or put an OpenRouter key into JavaScript or a public config file.