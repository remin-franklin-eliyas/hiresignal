Secrets and deployment

This document explains recommended ways to manage secrets for HireSignal in
production and CI, and why `.env` should be used only for local development.

1) Overview

- Local development: use `.env` copied from `.env.example`. The codebase loads
  `.env` only when `ENVIRONMENT=local` (default).
- CI: inject secrets with GitHub Secrets (see README). The CI workflow appends
  secrets into a generated `.env` for demo steps.
- Production: do NOT use `.env` files. Use a secret store (Azure Key Vault,
  HashiCorp Vault, or platform-provided secret managers) and inject values into
  environment variables at runtime.

2) Azure Key Vault (recommended for Azure deployments)

- Create an Azure Key Vault and add secrets:
  - GRAPH_CLIENT_SECRET
  - AZURE_AI_FOUNDRY_API_KEY
  - FABRIC_AUDIT_TOKEN
  - FABRIC_AUDIT_ENDPOINT (optional)
  - TEAMS channel IDs or integration tokens if needed

- Grant the application identity (Managed Identity) `get`/`list` permissions to
  the Key Vault secrets.

- At runtime, configure the platform (App Service, Azure Container Apps,
  AKS) to fetch secrets and set them as environment variables for the process.

- Alternatively, use a secrets sidecar or an init step to render env vars from
  Key Vault securely.

3) GitHub Secrets (for CI and non-production deployments)

- In your repository: Settings -> Secrets and variables -> Actions -> New
  repository secret.
- Add the following secrets as needed:
  - GRAPH_CLIENT_SECRET
  - GRAPH_CLIENT_ID
  - GRAPH_TENANT_ID
  - GRAPH_WEBHOOK_CLIENT_STATE
  - GRAPH_MONITORED_USER_ID

- The CI uses these secrets to populate a temporary `.env` for demo/Smoke
  tests; the values are never persisted in the repo.

4) Removing `.env` reliance in production

- `app/core/config.py` is implemented to only load `.env` when
  `ENVIRONMENT=local`. In production set `ENVIRONMENT=production` (or any
  non-local value) and provide configuration via environment variables.

5) Runtime recommendations

- Always run the app with the least privileges required for the Graph API
  scopes.
- Rotate secrets regularly and use short-lived credentials where possible.
- Audit and monitor secret access in your cloud provider.

6) Quick checklist for production

- [ ] Create Key Vault and add required secrets.
- [ ] Configure app runtime to expose secrets as environment variables.
- [ ] Set `ENVIRONMENT=production` in the runtime environment.
- [ ] Verify the app starts without reading a local `.env` file.

