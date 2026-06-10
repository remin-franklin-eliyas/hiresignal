Data Protection and Compliance

This document outlines PII (personally identifiable information) handling,
data protection, logging practices, and audit retention for HireSignal.

1) Data Classification

**PII NOT Stored**
- Candidate names
- Email addresses (candidate or recruiter)
- Phone numbers
- Dates of birth
- SSNs or government IDs
- Address information
- CV text content or extracted text
- Raw attachment content

**Audit Data Stored (Hashed/Anonymized)**
- Candidate hash (SHA-256 of filename + message ID): immutable 64-char hex
- Source event hash (SHA-256 of message ID): immutable 64-char hex
- Job ID: string identifier for the position
- Rubric version: version of scoring criteria applied
- Scores: numerical evaluation (0-100) per criterion
- Reasoning: summarized scoring rationale (criterion-specific, non-identifying)
- Manual review flag: boolean
- Timestamps: created_at in ISO 8601 UTC

**Why This Design**
- Scores and reasoning allow auditing of hiring decisions
- Hashed identifiers prevent linkage to individuals without additional data
- No CV content or personal details retained post-processing
- Regulatory compliance: GDPR/CCPA/CFAA considerations

2) Logging and Output

**What Is NOT Logged**
- CV content or extracted document text
- Candidate email addresses or identifiers
- Message IDs or raw attachment content
- API credentials, tokens, or secrets

**What IS Logged (At INFO/DEBUG Levels)**
- Pipeline progress: "processed X attachments, scored Y candidates"
- Errors: generic descriptions ("attachment extraction failed", not file contents)
- Retry attempts: attempt count and backoff (transient errors)
- Operational metrics: record counts, API latencies

**PII Redaction Filter**
- All logs pass through automatic redaction filter (app.services.pii_redaction)
- Patterns redacted: emails, phone numbers, SSNs, credit cards, API keys, tokens
- Sensitive strings replaced with [REDACTED]
- Applied to: message text, args, exception details

**Logging Configuration**
- Set via LOG_LEVEL environment variable (default: INFO)
- Production: INFO only; DEBUG off unless troubleshooting
- Configure log aggregation (e.g., Azure Monitor, Splunk) with field-level redaction

3) Audit Retention and Deletion

**Default Retention Period**
- 90 days from creation (configured via AUDIT_RETENTION_DAYS)
- Applies to SQLite audit store; Fabric/Lakehouse managed separately

**Cleanup Process**
- Run manually: `python -m app.cli audit cleanup`
- Run scheduled: add to maintenance cron/pipeline
- Soft deletes only (no archive retention)

**Record Deletion**
- Records older than retention period deleted from SQLite
- Deletion is permanent; no audit trail of deletion itself
- Recommend Fabric audit retention aligned with retention days

**Compliance Notes**
- Right to be forgotten (GDPR): candidate hash does not link back to individual
- Data minimization: no content stored, only scores and reasoning
- Deletion policy ensures no indefinite retention

4) Communication and Output

**Teams Adaptive Card Posting**
- Posts shortlist (candidate hash prefix + score) to Teams channel
- Includes criterion scores and reasoning (not raw CV content)
- No PII in card; hashes not linkable without original message ID
- Card is ephemeral; Teams retention policy applies separately

**API Responses**
- POST /graph/notifications: returns IngestionResult (counts, status, reason)
- GET /teams/explain: returns audit record (hashed candidate, scores, reasoning)
- No raw CV or personal data in any API response

5) Implementation

**PII Handling Module**
- app/services/pii_redaction.py: RedactionFilter, SensitivePatterns
- app/services/audit_retention.py: AuditRetentionPolicy, cleanup service
- app/pipeline/privacy.py: hash_candidate_identifier() for consistent hashing

**Configuration**
- app/core/config.py: AUDIT_RETENTION_DAYS, LOG_LEVEL
- app/main.py: setup_logging() on startup

**Testing**
- tests/test_pii_redaction.py: verify redaction patterns
- tests/test_audit_retention.py: verify deletion logic

6) Incident Response

**If PII is Accidentally Logged**
1. Check log aggregation system; delete from retention (if possible)
2. Rotate any exposed credentials immediately
3. Review RedactionFilter patterns; add new patterns if needed
4. Audit recent logs for similar leakage
5. Document and report per org policy

**If Unauthorized Audit Access**
1. Check audit trail (created_at timestamps)
2. Determine scope (which records accessed, date range)
3. Notify affected candidates/organization per policy
4. Rotate database credentials and secrets

7) Compliance Checklist

- [ ] AUDIT_RETENTION_DAYS configured per org policy (default: 90)
- [ ] LOG_LEVEL set to INFO in production (never DEBUG persistently)
- [ ] Log aggregation configured with field-level PII redaction
- [ ] Scheduled audit cleanup task set up (weekly recommended)
- [ ] Fabric audit retention aligned with SQLite retention
- [ ] Secrets injected via Key Vault, not .env files
- [ ] API responses reviewed for PII leakage
- [ ] Teams channel access restricted to authorized users
- [ ] Incident response procedure documented

