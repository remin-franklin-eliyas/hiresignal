# Quick Start (30 Seconds)

```bash
# Setup (1 minute, one-time only)
git clone https://github.com/remin-franklin-eliyas/hiresignal.git
cd hiresignal
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"
pytest -q

# Demo (30 seconds)
bash scripts/demo-walkthrough.sh
```

**Or read the full 2-minute walkthrough:**
- See [DEMO.md](DEMO.md) for step-by-step instructions
- See [README.md](README.md) for architecture and features

---

## What You'll See

1. **API starts** — No errors, clean logging
2. **Webhook accepts notifications** — Returns scoring results
3. **Audit trail** — SQLite records with hashed candidates (no PII)
4. **Reasoning breakdown** — Full scoring details per candidate
5. **Tests pass** — 44 tests (E2E, PII redaction, retention policies)

---

## Key Highlights

✅ Real-time CV ranking (Outlook → Teams in seconds)  
✅ Explainable scoring (skills, experience, role-fit breakdown)  
✅ Zero PII stored (hashed candidates, automatic log redaction)  
✅ Production-ready (no hardcoded secrets, Docker, CI/CD)  
✅ Compliance-first (90-day retention, incident response policy)

---

## Demo Points (For Judges)

**Problem:** Recruiter overwhelmed by 200 CVs in 14 minutes  
**Solution:** HireSignal auto-validates, scores, and ranks candidates in Teams  
**Why It Matters:** Explainable AI + compliance + real-world hiring pain  

---

**Hackathon:** Agents League (Microsoft AI Skills Fest 2026)  
**Deadline:** June 14, 2026  
**Status:** ✅ Demo-ready
