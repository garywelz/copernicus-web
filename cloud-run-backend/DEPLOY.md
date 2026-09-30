# Deploying copernicus-podcast-api

`cloudbuild.yaml` in this directory builds and pushes the container image
only. It does **not** deploy. This is deliberate: it used to also run
`gcloud run deploy` with no `--no-traffic` flag, which sent every
successful build straight to 100% of live traffic with no review step in
between. Deploy this service by hand, in gated steps, every time.

## Procedure

1. **Build from a clean checkout of the reviewed commit** — never the
   working folder, which may have local changes or be on the wrong branch:
   ```bash
   git worktree add ../copernicus-web-deploy-<label> <commit-or-tag>
   cd ../copernicus-web-deploy-<label>/cloud-run-backend
   gcloud builds submit . --project regal-scholar-453620-r7 \
     --tag gcr.io/regal-scholar-453620-r7/copernicus-podcast-api:<label>
   ```

2. **Read the image digest** (never deploy by mutable tag):
   ```bash
   gcloud container images describe \
     gcr.io/regal-scholar-453620-r7/copernicus-podcast-api:<label> \
     --format="value(image_summary.digest)"
   ```

3. **Deploy by digest, with only `--image`, `--no-traffic`, and `--tag`.**
   Do not pass env vars, scaling, CPU, memory, timeout, cpu-boost,
   concurrency, ingress, service account, or auth flags — the deployed
   revision must inherit every other setting unchanged from the service's
   current configuration, not restate it (restating settings is how they
   drift):
   ```bash
   gcloud run deploy copernicus-podcast-api \
     --image gcr.io/regal-scholar-453620-r7/copernicus-podcast-api@sha256:<digest> \
     --no-traffic \
     --tag <label> \
     --region us-central1 \
     --project regal-scholar-453620-r7
   ```

4. **Diff the new and old revision specs.** Record which revision is
   currently serving traffic before you start. The only acceptable
   difference is the image (plus revision name, tag, timestamps, and
   deployer-identity/status-message metadata). If anything else differs —
   env vars, min/max instances, concurrency, CPU, memory, timeout,
   cpu-boost, service account, secrets, VPC or Cloud SQL settings, probes —
   stop; do not move traffic:
   ```bash
   gcloud run revisions describe <old-revision> --region us-central1 \
     --project regal-scholar-453620-r7 --format=yaml > old.yaml
   gcloud run revisions describe <new-revision> --region us-central1 \
     --project regal-scholar-453620-r7 --format=yaml > new.yaml
   diff -u old.yaml new.yaml
   ```

5. **Smoke-test the tagged URL against the live one.** At minimum:
   - `/health` on both — expect the same healthy response.
   - `/api/public/podcasts?limit=200` on both — compare the **sorted list
     of episode IDs**, not just the count. They must be identical.

6. **Move traffic only after Gary approves.**
   ```bash
   gcloud run services update-traffic copernicus-podcast-api \
     --region us-central1 --project regal-scholar-453620-r7 \
     --to-revisions=<new-revision>=100
   ```

7. **Check logs** for `severity>=ERROR` on the new revision for at least
   10 minutes after cutover, and confirm the request count/response codes
   look normal.

8. **Keep the previous revision** — do not delete it. It is the rollback
   path. Rollback is one command:
   ```bash
   gcloud run services update-traffic copernicus-podcast-api \
     --region us-central1 --project regal-scholar-453620-r7 \
     --to-revisions=<old-revision>=100
   ```

Clean up the worktree when done: `git worktree remove <path>`.

See `governance/BULLETIN.md` entry 009 for the worked example this
procedure was extracted from.
