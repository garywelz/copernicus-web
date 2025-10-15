# Add this to your main.py in cloud-run-backend

@app.get("/api/glmp/processes")
async def list_glmp_processes():
    """List all available GLMP processes from GCS"""
    try:
        # List files in glmp-v2 directory
        bucket_name = "regal-scholar-453620-r7-podcast-storage"
        prefix = "glmp-v2/"
        
        # Use Google Cloud Storage client
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        processes = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                process_name = blob.name.replace(prefix, '').replace('.json', '')
                processes.append({
                    'id': process_name,
                    'name': process_name.replace('-', ' ').title(),
                    'file_path': blob.name,
                    'url': f"gs://{bucket_name}/{blob.name}"
                })
        
        return {"processes": processes, "count": len(processes)}
        
    except Exception as e:
        print(f"❌ Error listing GLMP processes: {e}")
        raise HTTPException(status_code=500, detail="Failed to list processes")

@app.get("/api/glmp/processes/{process_id}")
async def get_glmp_process(process_id: str):
    """Get a specific GLMP process flowchart"""
    try:
        bucket_name = "regal-scholar-453620-r7-podcast-storage"
        file_path = f"glmp-v2/{process_id}.json"
        
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Download and parse JSON
        json_content = blob.download_as_text()
        process_data = json.loads(json_content)
        
        return {
            "process_id": process_id,
            "data": process_data,
            "mermaid_code": process_data.get('mermaid_syntax', ''),
            "metadata": {
                "title": process_data.get('title', process_id),
                "description": process_data.get('description', ''),
                "category": process_data.get('category', ''),
                "version": process_data.get('version', '1.0')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching GLMP process: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch process")
