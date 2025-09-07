# Dependency Review Checklist

Updated: 2025-09-08

Purpose: Enforce secure, minimal, and approved third-party Python dependencies.

## 1. Pre-Addition Validation
- [ ] Is the standard library sufficient? (If yes, do not add.)
- [ ] Clear functional justification documented.
- [ ] No existing dependency already provides this capability.
- [ ] User (owner) double-confirmation received (link to approval note / issue ID).

## 2. Package Health
- [ ] Actively maintained (>= 1 release in last 12 months).
- [ ] Open issues & PRs reasonable (no critical security issues open >30 days).
- [ ] License is permissive (MIT / Apache-2.0 / BSD / similar).
- [ ] Maintainer reputation acceptable (not a single-purpose throwaway unless justified).

## 3. Security
- [ ] Check for known CVEs (e.g., via `pip audit` / Safety / osv.dev query).
- [ ] Pin exact version in `requirements.txt`.
- [ ] No installation of packages via direct VCS refs unless justified.
- [ ] No usage of deprecated or unmaintained transitive dependencies (scan tree if complex).

## 4. Footprint & Risk
- [ ] Minimal dependency chain (list transitive deps count: __ ).
- [ ] Binary wheels acceptable / reproducible (fallback to source build evaluated if needed).
- [ ] Import surface minimal (only import required modules).

## 5. Implementation
- [ ] Added to `requirements.txt` with exact version.
- [ ] Added justification comment (one short line) next to entry.
- [ ] Added/updated tests to cover new functionality enabled by dependency.

## 6. Post-Addition Monitoring
- [ ] Added to periodic review list.
- [ ] Security watch set (optional).
- [ ] Removal path documented (how to revert if issue found).

## 7. Removal (If Decommissioning)
- [ ] Confirm no modules import it.
- [ ] Remove from `requirements.txt`.
- [ ] Run tests (should pass).
- [ ] Update documentation / changelog.

---
Template Usage: Copy this checklist into PR / issue and fill before merging.
