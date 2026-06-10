# Google Cloud Storage CORS (Biology + Mathematics databases)

If `biology-database-table.html` or `mathematics-database-table.html` is **embedded** in another website (iframe, LMS, Notion preview), the browser performs a **cross-origin** request to `storage.googleapis.com`. The bucket must allow that origin.

Opening the HTML **directly** in a tab (`https://storage.googleapis.com/.../biology-database-table.html`) usually works without CORS because `fetch('./metadata.json')` is same-origin.

## Apply CORS to the bucket

1. Edit `cors.json` in this folder (add your site origins to `origin`).

2. Run (replace bucket if you use a different one):

```bash
gsutil cors set cors.json gs://regal-scholar-453620-r7-podcast-storage
```

3. Verify:

```bash
gsutil cors get gs://regal-scholar-453620-r7-podcast-storage
```

## Example `cors.json`

See `cors.json` next to this file. Wildcard `"origin": ["*"]` allows any site to read public objects (simplest for public educational content). For stricter setups, list only `https://yourdomain.com`.

## References

- [Configuring CORS on buckets](https://cloud.google.com/storage/docs/configuring-cors)
