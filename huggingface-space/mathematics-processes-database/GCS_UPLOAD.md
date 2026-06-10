# Upload Mathematics Processes Database to Google Cloud Storage

To deploy the Mathematics Processes Database (including the new Euclid's Elements chart) to GCS:

## Prerequisites

- Google Cloud SDK (`gcloud` and `gsutil`) installed
- Authenticated with a project that has access to bucket `regal-scholar-453620-r7-podcast-storage`

## Upload Command

From the `mathematics-processes-database` directory (or its parent):

```bash
# Upload entire mathematics-processes-database folder to GCS
gsutil -m cp -r . gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/

# Or upload only the new/changed files:
gsutil cp metadata.json gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/
gsutil cp processes/geometry_topology/geometry_topology-euclid-elements-i-1-5.json gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/processes/geometry_topology/
gsutil cp processes/geometry_topology/geometry_topology-euclid-elements-i-1-5.html gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/processes/geometry_topology/
gsutil cp processes/discrete_mathematics/discrete_mathematics-binary-search.json gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/processes/discrete_mathematics/
gsutil cp processes/discrete_mathematics/discrete_mathematics-binary-search.html gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/processes/discrete_mathematics/
```

## Set Cache Control (optional)

To avoid stale cached metadata:

```bash
gsutil -h "Cache-Control:no-cache, max-age=0" cp metadata.json gs://regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/
```

## Verify

After upload, the new chart will appear at:

- **Database table**: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/mathematics-database-table.html
- **Euclid chart**: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/processes/geometry_topology/geometry_topology-euclid-elements-i-1-5.html

## New Processes Added (2026-03-15)

- **Euclid's Elements Book I — Propositions 1–5**: Dependency graph of postulates, common notions, and propositions from Euclid's Elements.
- **Binary Search**: NIST DADS algorithm flowchart with GLMP 6-color scheme (including Lavender for decision diamonds).
