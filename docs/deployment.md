# Deployment Guide

Semantic Bridge can be deployed on a free-tier via Render and Neon, or scaled to a professional instance on Google Cloud Run.

---

## 🏗️ Render + Neon (Free Tier)

This project can be deployed on Render's free tier with auto-deploys from GitHub.

### 1) Create a Neon database
1.  Create a free [Neon](https://neon.tech) project and database.
2.  Copy the connection string (e.g. `postgresql://USER:PASSWORD@HOST/DB?sslmode=require`).

### 2) Deploy on Render
1.  Create a [Render](https://render.com) account and connect your GitHub repo.
2.  Create a new Web Service. Render will detect the `render.yaml` for configuration.
3.  Set these environment variables in Render:
    - `DATABASE_URL`
    - `AUTH_JWT_SECRET`
    - `AUTH_ISSUER`
    - `AUTH_AUDIENCE`
4.  Deploy. Render will build using the `Dockerfile` and run the service.

---

## 🚀 Cloud Run + Neon (Professional)

This project can also be deployed to Google Cloud Run for faster startup and horizontal scaling.

### 1) Create GCP resources
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud artifacts repositories create translator-middleware \
  --repository-format=docker \
  --location=us-central1
```

### 2) Add GitHub Secrets
Set these repository secrets in GitHub Actions:
- `GCP_PROJECT_ID` = your GCP project ID
- `GCP_REGION` = region for Cloud Run (e.g. `us-central1`)
- `GCP_ARTIFACT_REPO` = `translator-middleware`
- `GCP_SA_KEY` = contents of `gcp-sa-key.json`
- `DATABASE_URL` = Neon connection string

### 3) Deploy
Push to `main`. The workflow in `.github/workflows/ci-deploy.yml` runs tests and deploys to Cloud Run automatically.

---

## 🧭 Kubernetes Horizontal Scaling (CPU-based)

If you deploy to Kubernetes, apply the sample manifests to scale replicas based on CPU usage:

```bash
kubectl apply -f monitoring/k8s/translator-deployment.yaml
kubectl apply -f monitoring/k8s/translator-hpa.yaml
```

Adjust `averageUtilization` in `monitoring/k8s/translator-hpa.yaml` to change the CPU threshold.

---

## 📚 Essential Env Vars

| Variable | Description |
| :--- | :--- |
| `DATABASE_URL` | Your primary Postgres sink. |
| `REDIS_ENABLED` | Critical for caching OWL ontology hits. |
| `AUTH_JWT_SECRET` | The master key for signing EATs. |
| `SENTRY_DSN` | Required for production error tracking. |

---

**Version 0.1.0** | *Deployment Guide*
