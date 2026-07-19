# Release Alpha 13 — Play App Signing Gate

- Manual workflow با GitHub Environment `android-release`
- Fail-closed در نبود چهار Secret مربوط به Upload Key
- Keystore فقط در Runner موقت Materialize و همیشه حذف می‌شود
- testReleaseUnitTest + lintRelease + bundleRelease
- jarsigner strict verification
- AAB و provenance با retention محدود
- Gradle از تولید Release بدون Keystore جلوگیری می‌کند
- Play Upload AAB از کلید اصلی App Signing جدا است
- Production/Testnet/Live execution خاموش باقی می‌مانند

تا زمانی که Upload Key توسط مالک ساخته و Secrets مستقیم در GitHub ثبت نشوند، هیچ AAB امضاشده‌ای ادعا نمی‌شود.
