# HireSignal Demo Walkthrough (2 Minutes)

This guide walks judges through a **complete end-to-end demo** of HireSignal in under 2 minutes.

## Prerequisites (Setup Time: ~1 min)

```bash
# Clone and enter directory
git clone https://github.com/remin-franklin-eliyas/hiresignal.git
cd hiresignal

# Setup environment
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install ".[dev]"

# Verify tests pass
pytest -q
```

Once setup is done, you're ready for the live demo.

---

## 2-Minute Live Demo Flow

### **Minute 0:00–0:10 — Problem Statement**

> *"Imagine you're a recruiter. A hiring post just hit its applicant cap in 14 minutes. You have 200 CVs but no time to fairly evaluate them all. HireSignal solves this: it validates, scores, and ranks candidates automatically—and explains why."*

### **Minute 0:10–0:20 — Start the API**

```bash
# Terminal 1: Start the API server
uvicorn app.main:app --reload
```

Show that the server starts cleanly (no errors, logging is clean).

**Point out:**
- ✅ Server starts without hardcoded secrets
- ✅ Logging shows initialization with PII redaction active
- ✅ Health check endpoint is available

### **Minute 0:20–0:35 — Send Sample Notifications**

```bash
# Terminal 2: Test webhook
curl -X POST "http://localhost:8000/graph/notifications?validationToken=demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "value": [
      {
        "subscriptionId": "demo-sub-1",
        "clientState": "client-state",
        "changeType": "created",
        "resource": "users/recruiter@example.com/messages/message-1",
        "resourceData": {"@odata.type": "#Microsoft.Graph.Message", "id": "message-1"}
      }
    ]
  }'
```

**Explain what's happening:**
- ✅ Webhook receives Outlook change notification
- ✅ HireSignal validates webhook signature (clientState check)
- ✅ Would fetch CVs from Graph (mocked in this demo to avoid live auth)
- ✅ Scores candidates with versioned rubric
- ✅ Saves audit records (hashed, no PII)

**Response:**
```json
{
  "status": "queued",
  "accepted_attachments": 1,
  "scored_candidates": 1,
  "audited_candidates": 1,
  "rubric_version": "2026.06.10"
}
```

### **Minute 0:35–0:45 — View Audit Trail**

```bash
# Show SQLite audit records
sqlite3 hiresignal.db "SELECT candidate_hash, overall_score, created_at FROM candidate_score_audit LIMIT 3;"
```

**Point out:**
- ✅ Candidate identifiers are 64-char hashes (SHA-256, no PII)
- ✅ Only scores and reasoning stored (no raw CV text)
- ✅ Timestamps for audit trail
- ✅ Automatically cleaned up after 90 days

### **Minute 0:45–1:00 — Reasoning Breakdown API**

```bash
# Get detailed reasoning for a candidate
curl http://localhost:8000/teams/explain?jobId=backend-ai-engineer-2026-06&candidateHash=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

**Point out:**
- ✅ Returns full scoring breakdown
- ✅ Per-criterion scores + reasoning
- ✅ Hashed candidate ID (recruiter can look up who it is in Teams)
- ✅ No personal data exposed

**Sample Response:**
```json
{
  "candidate_hash": "aaa...",
  "overall_score": 88,
  "skills_match": {
    "score": 90,
    "reasoning": "Strong Python, FastAPI, Azure AI experience demonstrated."
  },
  "experience_relevance": {
    "score": 85,
    "reasoning": "5+ years production API development, cloud deployment expertise."
  },
  "role_fit": {
    "score": 80,
    "reasoning": "Clear cross-functional communication and problem-solving skills."
  }
}
```

### **Minute 1:00–1:20 — Security & Compliance Highlights**

```bash
# Show PII redaction in logs
tail -50 /tmp/hiresignal.log | grep REDACTED

# Show audit cleanup policy
python -m app.cli audit cleanup --help
```

**Point out:**
- ✅ Automatic PII redaction: emails, phones, SSNs, API keys all masked
- ✅ Retention policy: default 90 days
- ✅ Cleanup CLI for compliance
- ✅ No hardcoded secrets in code

### **Minute 1:20–1:50 — Teams Integration (Optional)**

If you have Teams set up:

```bash
# Set Teams channel ID
export TEAMS_CHANNEL_ID=teamId/channelId

# Restart API (will post to Teams on ingestion)
uvicorn app.main:app
```

**Show the Teams card:**
- Ranked shortlist with scores
- Criterion-by-criterion breakdown
- "Explain" button links to `/teams/explain`
- "Request Review" for manual escalation

### **Minute 1:50–2:00 — Wrap-Up**

Show the architecture diagram from README:

```
Outlook → Graph API → Extract → Rubric → Score → Audit + Teams
```

**Key Messages:**
1. ✅ **Solves real pain:** Rapidly validates + ranks applicants
2. ✅ **Explainable:** Every score has reasoning; no black box
3. ✅ **Secure:** No PII stored; automatic log redaction; 90-day retention
4. ✅ **Production-ready:** No hardcoded secrets; proper secret injection; comprehensive tests
5. ✅ **Hackathon-ready:** Demo runs in <2 min, passes 44 tests, deployed in Docker

---

## Alternative: Automated Demo

Run the complete walkthrough script:

```bash
bash scripts/demo-walkthrough.sh
```

This automates all steps and completes in ~2 minutes.

---

## Test Coverage

Show test results:

```bash
pytest -q
# Output: 44 passed
```

Key tests:
- ✅ E2E ingestion (extract → score → audit → Teams)
- ✅ PII redaction (emails, phones, SSNs masked in logs)
- ✅ Audit retention (cleanup of old records)
- ✅ Teams posting (retry logic, Adaptive Card formatting)
- ✅ Health endpoints

---

## Troubleshooting Demo Issues

| Issue | Fix |
|-------|-----|
| "Port 8000 in use" | `lsof -i :8000` then `kill -9 <PID>` |
| "Settings validation error" | Ensure `.env` is set up: `cp .env.example .env` |
| "SQLite locked" | Delete `hiresignal.db` and restart |
| "Graph auth fails" | Expected (needs real Azure app). Shows fallback scoring works. |
| "Tests fail" | Run `pip install ".[dev]"` to ensure all deps installed |

---

## Key Files for Judges

| File | Purpose |
|------|---------|
| `README.md` | Overview, architecture, quick start |
| `docs/pii-compliance.md` | PII handling, retention, incident response |
| `docs/secrets.md` | Secret injection, Key Vault guidance |
| `app/main.py` | FastAPI app, logging setup |
| `app/pipeline/ingestion.py` | Main workflow (validate → score → audit) |
| `app/services/pii_redaction.py` | Logging redaction filter |
| `app/services/audit_retention.py` | Retention policy + cleanup |
| `tests/test_pii_compliance.py` | PII & retention tests |
| `config/job_rubric.sample.json` | Versioned scoring rubric |
| `.github/copilot-instructions.md` | Project context for Copilot |

---

## Demo Success Checklist

- [ ] API starts without errors
- [ ] Health endpoint responds with `{"status": "ok"}`
- [ ] Webhook accepts notifications (returns result JSON)
- [ ] SQLite stores audit records (no PII, only hashes)
- [ ] `/teams/explain` returns scoring breakdown
- [ ] Logs contain no sensitive data (all [REDACTED])
- [ ] Tests pass: `pytest -q` → 44 passed
- [ ] Architecture is clear: GitHub Copilot integration → Outlook → Teams
- [ ] Security story is clear: hashes, redaction, retention

---

**Total Demo Time:** ~2 minutes  
**Setup Time (one-time):** ~3 minutes  
**Judges See:** Real-time CV validation, ranking, explainable AI, compliance-first architecture
