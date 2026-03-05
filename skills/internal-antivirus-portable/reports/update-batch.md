# Internal Antivirus — Update Batch Report

- **Batch ID:** `BATCH-YYYYMMDD-HHMM`
- **Generated at (UTC):** `YYYY-MM-DDTHH:MM:SSZ`
- **Policy version:** `v1`
- **Mode:** `strict|assist|change_on_command`
- **Delivery channel:** `local|telegram|...`
- **Delivery chat_id:** `<optional>`
- **Delivery thread_id:** `<optional>`
- **Delivery topic:** `<optional>`

## 1) Summary
- New intel records:
- Candidate rules created:
- Rules promoted to approved:
- Rules promoted to active:
- Decision: `approve | reject | approve low-only | pending`

## 2) Source Coverage
| Source | Records | Confidence avg | Notes |
|---|---:|---:|---|
| nvd.nist.gov |  |  |  |
| cisa.gov |  |  |  |
| github.com/openclaw/openclaw |  |  |  |
| runzero.com |  |  |  |
| bitdefender.com |  |  |  |

## 3) Proposed Rule Changes
### Added
- `RULE_ID` — reason, source, severity

### Modified
- `RULE_ID` — what changed and why

### Removed/Expired
- `RULE_ID` — reason (expired/duplicate/noisy)

## 4) Safety Gates
- Schema validation: `pass/fail`
- Regex ReDoS check: `pass/fail`
- Direct internet->active path detected: `yes/no`
- Any install/exec attempted in intel collector: `yes/no`
- Owner approval token present (if active write): `yes/no`

## 5) Quality Impact
- Recall (high/critical set):
- False-positive rate (clean set):
- New noisy rules flagged:
- Decision on noisy rules:

## 6) Performance Impact
- Fast scan p50/p95:
- Cached scan p50/p95:
- Deep refresh runtime:
- Regression against latency budget: `pass/fail`

## 7) Artifact Reputation Changes
- New bad hashes:
- New trusted hashes:
- Reclassified hashes:

## 8) Required Owner Action
- [ ] Approve all
- [ ] Approve low-only
- [ ] Reject batch
- [ ] Request revision (notes below)

**Owner notes:**

---

## 9) Audit Pointers
- Intel files: `internal-antivirus/staging/intel/...`
- Candidate rules: `internal-antivirus/staging/rules/candidates/...`
- Approved rules: `internal-antivirus/approved/...`
- Active rules: `internal-antivirus/active/...`
- Audit log: `internal-antivirus/reports/audit-YYYY-MM-DD.jsonl`
