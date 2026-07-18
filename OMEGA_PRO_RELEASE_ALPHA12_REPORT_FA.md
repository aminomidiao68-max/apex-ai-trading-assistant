# Release Alpha 12 — Supply Chain & Security

## Gateها
- pip-audit strict: صفر آسیب‌پذیری شناخته‌شده
- Bandit Medium/High: صفر؛ B608 فقط برای SQL fragmentهای hard-coded allowlisted با توضیح مستند مستثنا است
- Python CycloneDX SBOM reproducible
- Android source CycloneDX SBOM با Syft/Anchore
- Canonical OpenAPI SHA-256 fingerprint
- APK provenance manifest با برچسب صریح debug و `production_release_signed=false`
- Artifact upload فقط پس از Gateها

## Dependency upgrades
- FastAPI 0.139.2
- python-dotenv 1.2.2
- requests 2.34.2
- cryptography 49.0.0

## صداقت انتشار
APK فعلی Debug است و Production release-signed معرفی نمی‌شود. Testnet و Live execution خاموش‌اند. SBOM و Audit مجوز Live صادر نمی‌کنند.
