# Private Engelli.me news admin: deployment configuration

The private admin routes are deliberately unavailable until the required settings are configured. They fail closed and do not affect the public news API.

## Required runtime configuration

Configure these on the Cloud Run service before exposing the page:

- \`REDIS_URL\`: private Redis/Valkey URL for credentials, one-time challenges, login rate limits, and sessions. Use a private network connection and TLS/authentication as supported by the Redis service. Do not point this at a public unauthenticated Redis endpoint.
- \`ADMIN_PASSWORD_HASH\`: PBKDF2-SHA256 fallback password hash. Never store the plaintext password in the repository.
- \`ADMIN_PASSKEY_RP_ID\`: \`engelli.me\`.
- \`ADMIN_PASSKEY_ORIGIN\`: \`https://engelli.me\`.

Generate a password hash locally (this prints a salted hash, not the password):

\`\`\`bash
python -c "import os,hashlib; p=input('Admin password: '); s=os.urandom(16); n=310000; d=hashlib.pbkdf2_hmac('sha256',p.encode(),s,n).hex(); print(f'pbkdf2_sha256\${n}\${s.hex()}\${d}')"
\`\`\`

Store the printed value as the \`ADMIN_PASSWORD_HASH\` Cloud Run environment variable through the secure service settings. Do not paste it into source code, GitHub files, screenshots, or chat.

## First setup

1. Confirm the Redis URL works from the Cloud Run service.
2. Set the four variables above using the secure service configuration.
3. Deploy only after reviewing the feature branch and confirming the configuration.
4. Open \`https://engelli.me/admin/haber-durumu\` and sign in with the fallback password.
5. Click **Bu cihazda Passkey kaydet** and complete the iPhone/Apple passkey prompt. Face ID is handled by iOS; the web app does not receive Face ID data.
6. Test passkey login in a new browser session, fallback login, logout, session expiry, and unauthenticated access.

The admin panel does not launch a news scan. Refresh only reads the latest public GitHub Actions run, the full \`news_ai_log.json\`, the system incidents in that log, and the live news API comparison.

## Safety notes

- The dashboard and its JSON endpoint require an authenticated server-side session.
- Session cookies are \`Secure\`, \`HttpOnly\` and \`SameSite=Strict\`, with a seven-day lifetime.
- Passkey challenges expire after five minutes and are one-use.
- The page and API return \`noindex\` headers. This is an additional indexing hint, not the access control.
- No GitHub token is sent to the browser. The current repository is queried through GitHub's public API.
- This feature branch must not be merged/deployed until the configured Redis connection and WebAuthn package/build checks pass.
