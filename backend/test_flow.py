"""End-to-end flow test for CareerPilot API."""
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = "http://localhost:8000"
RESUME_PATH = "/tmp/resume_1.pdf"  # copied into container


def req(method, path, body=None, headers=None):
    url = BASE + path
    h = headers or {}
    data = json.dumps(body).encode() if body else None
    if data and "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}


def multipart_upload(path, filepath):
    """Minimal multipart/form-data upload."""
    import os
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    with open(filepath, "rb") as f:
        file_data = f.read()
    filename = os.path.basename(filepath)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())


def check(label, result, key=None):
    ok = "error" not in result if key is None else key in result
    status = "✅" if ok else "❌"
    val = result.get(key, "") if key else ""
    print(f"{status} {label}: {val if val else json.dumps(result)[:120]}")
    return ok


# ── 1. Health check ────────────────────────────────────────────────────────
print("\n=== 1. Health ===")
res = req("GET", "/health")
check("Health", res, "status")

# ── 2. Upload resume ───────────────────────────────────────────────────────
print("\n=== 2. Upload Resume ===")
upload = multipart_upload("/resume/upload", RESUME_PATH)
if "error" in upload:
    print(f"❌ Upload failed: {upload}")
    sys.exit(1)
user_id = upload.get("user_id")
profile_id = upload.get("profile_id")
print(f"✅ Uploaded → user_id={user_id}  profile_id={profile_id}")
print(f"   status={upload.get('status')}  name={upload.get('personal_info', {}).get('name', 'N/A')}")

# ── 3. Analysis overview ───────────────────────────────────────────────────
print("\n=== 3. Analysis Overview ===")
res = req("GET", f"/analysis/overview?user_id={user_id}")
check("Overview", res, "overall_score")
print(f"   overall_score={res.get('overall_score')}  strengths_count={len(res.get('strengths', []))}")

# ── 4. Skills gap ──────────────────────────────────────────────────────────
print("\n=== 4. Skills Gap (Backend Developer) ===")
res = req("GET", f"/analysis/skills-gap?user_id={user_id}&role=Backend+Developer")
check("Skills gap", res, "gap_score")
print(f"   gap_score={res.get('gap_score')}  missing={res.get('missing_skills', [])[:3]}")

# ── 5. Career path ─────────────────────────────────────────────────────────
print("\n=== 5. Career Path ===")
res = req("GET", f"/analysis/career-path?user_id={user_id}")
check("Career path", res, "current_role")
print(f"   current_role={res.get('current_role')}  next_steps={len(res.get('next_steps', []))}")

# ── 6. Job recommendations ────────────────────────────────────────────────
print("\n=== 6. Job Recommendations ===")
res = req("GET", f"/jobs/recommendations?user_id={user_id}&limit=5")
check("Jobs", res, "jobs")
jobs = res.get("jobs", [])
print(f"   total_found={res.get('total_found')}  returned={len(jobs)}")
if jobs:
    j = jobs[0]
    print(f"   top job: {j.get('title')} @ {j.get('company')} [{j.get('url', '')[:60]}]")

# ── 7. Track a job application ────────────────────────────────────────────
print("\n=== 7. Track Application ===")
job_url = jobs[0].get("url", "https://example.com/job/1") if jobs else "https://example.com/job/1"
job_title = jobs[0].get("title", "Software Engineer") if jobs else "Software Engineer"
company = jobs[0].get("company", "ACME") if jobs else "ACME"
app = req("POST", "/applications", {
    "user_id": user_id,
    "job_title": job_title,
    "company": company,
    "job_url": job_url,
    "status": "applied",
    "notes": "Applied via CareerPilot test"
})
check("Create application", app, "id")
app_id = app.get("id")
print(f"   app_id={app_id}  status={app.get('status')}")

# ── 8. List applications ──────────────────────────────────────────────────
print("\n=== 8. List Applications ===")
res = req("GET", f"/applications?user_id={user_id}")
check("List applications", res, "applications")
print(f"   total={res.get('total')}  by_status={res.get('by_status')}")

# ── 9. Update application status ─────────────────────────────────────────
print("\n=== 9. Update Application → interviewing ===")
res = req("PATCH", f"/applications/{app_id}?user_id={user_id}", {"status": "interviewing"})
check("Update application", res, "status")
print(f"   new status={res.get('status')}")

# ── 10. Submit feedback (thumbs up on job) ────────────────────────────────
print("\n=== 10. Submit Feedback (helpful) ===")
res = req("POST", "/feedback", {
    "user_id": user_id,
    "item_type": "job",
    "item_identifier": job_url,
    "feedback": "helpful"
})
check("Submit feedback", res, "id")
print(f"   feedback_id={res.get('id')}  value={res.get('feedback')}")

# ── 11. Get feedback list ─────────────────────────────────────────────────
print("\n=== 11. Get Feedback ===")
res = req("GET", f"/feedback?user_id={user_id}&item_type=job")
check("Get feedback", res, "feedback")
print(f"   total={res.get('total')}  items={[f['feedback'] for f in res.get('feedback', [])]}")

# ── 12. ATS score ─────────────────────────────────────────────────────────
print("\n=== 12. ATS Score ===")
jd = "We are looking for a Python backend developer with FastAPI, PostgreSQL, Docker and REST API experience."
res = req("POST", "/ats/score", {"user_id": user_id, "job_description": jd})
check("ATS score", res, "ats_score")
print(f"   ats_score={res.get('ats_score')}  matched_keywords={res.get('matched_keywords', [])[:5]}")

# ── 13. Chat message ──────────────────────────────────────────────────────
print("\n=== 13. Chat ===")
res = req("POST", "/chat", {"user_id": user_id, "message": "What are my top skills?"})
check("Chat", res, "response")
print(f"   response_preview={str(res.get('response', ''))[:120]}")

print("\n=== ALL TESTS COMPLETE ===")
