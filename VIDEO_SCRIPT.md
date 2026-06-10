# Demo Video Script (2 Minutes)

Use this script to deliver a polished 2-minute demo for judges, stakeholders, or recording.

---

## **Intro (15 seconds)**

> *"Hi! I'm here to show you HireSignal — a Microsoft 365 Copilot that solves a real recruiter pain point.*
>
> *Imagine this: Your hiring post just hit the applicant cap in 14 minutes. You have 200 CVs to review, but only a few hours to build a shortlist. You need to fairly evaluate each candidate AND explain why you're accepting or rejecting them.*
>
> *HireSignal automates this. It validates CVs, scores candidates against a versioned rubric, ranks them, and posts an explainable shortlist to Teams—all in seconds.*"

---

## **Demo Setup (20 seconds)**

**Show on screen:**

```bash
cd hiresignal
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"
pytest -q  # Show: 44 passed ✓
```

> *"The project passes 44 tests—E2E ingestion, PII redaction, audit retention, and Teams integration. All automated."*

---

## **Start the API (10 seconds)**

**Show on screen:**

```bash
uvicorn app.main:app --reload
```

> *"Starting the FastAPI backend. Notice the logs show clean initialization—no errors, PII redaction is active.*"

**Highlight:**
- ✅ No hardcoded secrets
- ✅ Logging initialized with auto-redaction
- ✅ Ready to receive webhooks

---

## **Send Test Notification (15 seconds)**

**Show on screen (in another terminal):**

```bash
curl -X POST "http://localhost:8000/graph/notifications" \
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

> *"The webhook received an Outlook change notification, validated it, extracted CVs (mocked here to avoid needing live Graph auth), scored each candidate, and audited the results. All in one request."*

---

## **Show Audit Trail (10 seconds)**

**Show on screen:**

```bash
sqlite3 hiresignal.db "SELECT candidate_hash, overall_score, created_at FROM candidate_score_audit LIMIT 3;"
```

**Output (example):**
```
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|88|2026-06-10T12:34:56.789012
```

> *"Here's the audit trail. Notice—no personal data. The candidate is identified by a 64-character hash (SHA-256). Their score (88) and timestamp are recorded. No raw CV text, no email, no name."*

---

## **Get Reasoning Breakdown (10 seconds)**

**Show on screen:**

```bash
curl 'http://localhost:8000/teams/explain?jobId=backend-ai-engineer-2026-06&candidateHash=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
```

**Response (formatted):**
```json
{
  "overall_score": 88,
  "skills_match": {
    "score": 90,
    "reasoning": "Strong Python, FastAPI, Azure AI experience."
  },
  "experience_relevance": {
    "score": 85,
    "reasoning": "5+ years production APIs, cloud deployment."
  },
  "role_fit": {
    "score": 80,
    "reasoning": "Clear cross-functional skills."
  }
}
```

> *"Any recruiter can click the 'Explain' button to see the full breakdown. Why did this candidate score 88? Because they have strong technical skills, relevant experience, and good role fit. Transparent, explainable, fair."*

---

## **Security Highlights (20 seconds)**

**Show on screen (optional terminal tail):**

```bash
# All logs redact PII automatically
grep REDACTED /tmp/hiresignal.log

# Example output:
# Email: [REDACTED]
# Phone: [REDACTED]
# API Key: [REDACTED]
```

> *"Here's what makes HireSignal production-ready:*
>
> *1. **Zero PII stored** — Candidates are hashed, CVs are discarded after scoring.*
>
> *2. **Automatic log redaction** — Every log entry scans for emails, phones, SSNs, API keys. Found anything? [REDACTED].*
>
> *3. **Audit retention** — Records kept for 90 days by default, then permanently deleted. Fully configurable.*
>
> *4. **No hardcoded secrets** — All credentials injected via environment variables or Azure Key Vault. `.env` only for local dev.*"*

---

## **Architecture Summary (15 seconds)**

**Show diagram from README:**

```
Outlook → Graph API → Extract → Rubric → Score → Audit + Teams
```

> *"The flow is straightforward:*
>
> *1. Recruiter sends emails with CVs*
> *2. Our webhook detects them via Microsoft Graph*
> *3. We extract text (PDF/DOCX)*
> *4. We score against a versioned rubric (skills, experience, role-fit)*
> *5. We store hashed audit records and post to Teams*
>
> *The whole thing is built on Teams AI Library + Microsoft Graph API + FastAPI + SQLite/Fabric. No vendor lock-in except Microsoft 365 itself."*

---

## **Wrap-Up (10 seconds)**

> *"To summarize:*
>
> ✅ *Solves a real problem — Recruiters can fairly rank 200 CVs in seconds*
>
> ✅ *Explainable AI — Every score has reasoning, no black box*
>
> ✅ *Security-first — PII hashed, logs redacted, 90-day retention*
>
> ✅ *Production-ready — Tests pass, Docker works, secrets managed*
>
> *The project is in the GitHub repo, fully documented, and ready for the June 14 deadline.*
>
> *Thanks!"*

---

## Key Talking Points

| Topic | Sound Bite |
|-------|-----------|
| **Problem** | "200 CVs in 14 minutes. Recruiters need to triage AND explain." |
| **Solution** | "Automated ranking with explainable reasoning posted to Teams." |
| **Accuracy** | "Versioned JSON rubric for repeatable, fair evaluation." |
| **Explainability** | "Every score has reasoning; recruiters know why candidates ranked." |
| **Security** | "No PII stored—only hashes, scores, reasoning. Logs auto-redacted." |
| **Compliance** | "90-day audit trail, incident response policy, zero hardcoded secrets." |
| **Tech** | "Teams AI Library + Graph API + FastAPI + SQLite/Fabric. Fully typed." |
| **Demo Time** | "End-to-end in under 2 minutes." |

---

## Backup Talking Points (If Asked)

**Q: Why not just use LinkedIn's ranking API?**  
A: We need on-premise control, explainability, and compliance. This is built on our rubric, not a black-box third-party service.

**Q: How does it handle diverse CV formats?**  
A: We support PDF and DOCX. For other formats (images, PDFs scanned from fax), we queue for manual review.

**Q: What if Azure AI Foundry is down?**  
A: We have a deterministic fallback scorer. Demo uses this by default—production can use both.

**Q: How do you prevent bias?**  
A: The rubric is versioned and explicit. All scores are logged with reasoning. Bias audits can review historical decisions.

**Q: Can this scale?**  
A: Yes. SQLite is for demo; production uses Fabric Lakehouse. Teams webhooks are async and retry-safe.

---

## Demo Checklist

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install ".[dev]"`)
- [ ] Tests pass (`pytest -q` → 44 passed)
- [ ] `.env` is set up (can use defaults)
- [ ] API starts without errors
- [ ] Webhook endpoint responds
- [ ] SQLite database has sample records
- [ ] `/teams/explain` returns scoring breakdown
- [ ] Logs contain no sensitive data (all [REDACTED])

---

**Total Time:** 2 minutes  
**Setup Time (one-time):** ~3 minutes  
**Impact:** Shows production-grade AI for recruiting with compliance built-in
