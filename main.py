import os
import uuid
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client
from google import genai
from google.genai import types

app = FastAPI(title="Zero-Cost Online AI Video Director")

# Process tasks sequentially in the cloud container to preserve free tier stability
executor = ThreadPoolExecutor(max_workers=1)
ONLINE_JOBS = {}

# Connect Database Registry using the cloud environment secrets you copied
supabase: Client = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_KEY", ""))

class EditRequest(BaseModel):
    video_url: str  # Direct stream/download link from Google Drive or open web address
    project_name: str = "viral_edit"

def online_pipeline_runner(job_id: str, video_url: str, project_name: str):
    ONLINE_JOBS[job_id] = {"status": "Processing", "step": "Initializing streaming download container..."}
    local_raw = f"/tmp/raw_{job_id}.mp4"
    local_out = f"/tmp/output_{job_id}.mp4"
    
    try:
        # Step 1: Stream video file from your open link directly into the temporary cloud disk space
        import urllib.request
        urllib.request.urlretrieve(video_url, local_raw)
            
        # Step 2: Push tracking channels to Gemini 1.5 Pro Window via the File API
        ONLINE_JOBS[job_id]["step"] = "Uploading video tracks into Gemini 1.5 Pro Window..."
        ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        video_file = ai_client.files.upload(file=local_raw)
        
        while video_file.state.name == "PROCESSING":
            time.sleep(10)
            video_file = ai_client.files.get(name=video_file.name)
            
        # Step 3: Invoke model to execute pacing and asset retention script
        ONLINE_JOBS[job_id]["step"] = "🧠 Gemini 1.5 Pro is analyzing visual tracks, retention pacing, and sound markers..."
        response = ai_client.models.generate_content(
            model='gemini-1.5-pro',
            contents=[video_file, "Analyze this video for map overlays, visual pacing, and sound markers."],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Save structural edit workflow JSON directly into your free Supabase text database registry
        ONLINE_JOBS[job_id]["step"] = "💾 Registering edit workflow blueprint into Supabase records..."
        supabase.table("video_jobs").insert({
            "job_id": job_id,
            "project_name": project_name,
            "edit_blueprint": response.text,
            "status": "Completed"
        }).execute()
        
        # Clean up temporary cloud file systems
        ai_client.files.delete(name=video_file.name)
        
        ONLINE_JOBS[job_id] = {
            "status": "Success",
            "message": "AI Director has formulated your retention edit timeline!",
            "blueprint": response.text
        }
        
    except Exception as e:
        ONLINE_JOBS[job_id] = {"status": "Failed", "error": str(e)}
    finally:
        for p in [local_raw, local_out]:
            if os.path.exists(p): os.remove(p)

@app.post("/v1/edit")
def trigger_online_edit(req: EditRequest):
    job_id = str(uuid.uuid4())
    executor.submit(online_pipeline_runner, job_id, req.video_url, req.project_name)
    return {"job_id": job_id, "status": "Queued on Cloud Server"}

@app.get("/v1/status/{job_id}")
def get_online_status(job_id: str):
    if job_id not in ONLINE_JOBS:
        raise HTTPException(status_code=404, detail="Tracking ID record missing.")
    return ONLINE_JOBS[job_id]
