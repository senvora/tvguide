import os
import requests
from collections import defaultdict

# === CONFIGURATION ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER, REPO_NAME = os.getenv("GITHUB_REPOSITORY").split("/")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# === DEPLOYMENTS ===
def fetch_deployments():
    deployments = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/deployments?per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        deployments.extend(data)
        page += 1
    return deployments

def mark_deployment_inactive(dep_id):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/deployments/{dep_id}/statuses"
    payload = {"state": "inactive"}
    resp = requests.post(url, headers=HEADERS, json=payload)
    return resp.status_code == 201

def delete_deployment(dep_id):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/deployments/{dep_id}"
    resp = requests.delete(url, headers=HEADERS)
    if resp.status_code == 204:
        print(f"🗑️ Deleted deployment {dep_id}")
    else:
        print(f"❌ Failed to delete deployment {dep_id}: {resp.status_code}")

def cleanup_deployments():
    deployments = fetch_deployments()
    deployments.sort(key=lambda d: d["created_at"], reverse=True)
    to_delete = deployments[1:]  # Keep only the latest

    for dep in to_delete:
        dep_id = dep["id"]
        if mark_deployment_inactive(dep_id):
            delete_deployment(dep_id)
        else:
            print(f"⚠️ Could not mark deployment {dep_id} inactive, skipping deletion.")

# === WORKFLOW RUNS ===
def fetch_workflow_runs():
    runs = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs?per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        batch = resp.json().get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
        page += 1
    return runs

def delete_workflow_run(run_id):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}"
    resp = requests.delete(url, headers=HEADERS)
    if resp.status_code == 204:
        print(f"🗑️ Deleted workflow run {run_id}")
    else:
        print(f"❌ Failed to delete workflow run {run_id}: {resp.status_code}")

def cleanup_workflows():
    runs = fetch_workflow_runs()
    for run in runs:
        delete_workflow_run(run["id"])

# === MAIN ENTRY ===
if __name__ == "__main__":
    if not GITHUB_TOKEN:
        raise EnvironmentError("❌ GITHUB_TOKEN missing.")

    print("🧹 Cleaning deployments...")
    cleanup_deployments()

    print("🧹 Cleaning workflow runs...")
    cleanup_workflows()

    print("✅ Cleanup complete. Only latest deployment and initial commit remain.")
