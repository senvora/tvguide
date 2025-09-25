import os
import requests
from collections import defaultdict

# === CONFIGURATION ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "senvora"
REPO_NAME = "tvguide"

# === HEADERS ===
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# === DEPLOYMENT CLEANUP ===
def fetch_deployments():
    deployments = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/deployments?per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        deployments.extend(data)
        page += 1
    return deployments

def mark_deployment_inactive(deployment_id):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/deployments/{deployment_id}/statuses"
    payload = {"state": "inactive"}
    response = requests.post(url, headers=HEADERS, json=payload)
    return response.status_code == 201

def delete_deployment(deployment_id):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/deployments/{deployment_id}"
    response = requests.delete(url, headers=HEADERS)
    if response.status_code == 204:
        print(f"🗑️ Deleted deployment {deployment_id}")
    else:
        print(f"❌ Failed to delete deployment {deployment_id}: {response.status_code} - {response.text}")

# === WORKFLOW RUN CLEANUP ===
def fetch_successful_workflow_runs():
    runs = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs?per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        batch = response.json().get("workflow_runs", [])
        if not batch:
            break
        runs += [r for r in batch if r.get("conclusion") == "success"]
        page += 1
    return runs

def delete_workflow_run(run_id):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}"
    response = requests.delete(url, headers=HEADERS)
    if response.status_code == 204:
        print(f"🗑️ Deleted workflow run {run_id}")
    else:
        print(f"❌ Failed to delete workflow run {run_id}: {response.status_code} - {response.text}")

# === MAIN CLEANUP ===
def cleanup_deployments():
    print("🔍 Fetching deployments...")
    deployments = fetch_deployments()
    deployments.sort(key=lambda d: d["created_at"], reverse=True)
    to_delete = deployments[1:]  # Keep only the latest deployment

    if not to_delete:
        print("✅ No old deployments to delete.")
        return

    print(f"🧹 Cleaning up {len(to_delete)} old deployments...")
    for dep in to_delete:
        dep_id = dep["id"]
        if mark_deployment_inactive(dep_id):
            delete_deployment(dep_id)
        else:
            print(f"⚠️ Could not mark deployment {dep_id} as inactive, skipping delete.")

def cleanup_workflows():
    print("\n🔍 Fetching successful workflow runs...")
    runs = fetch_successful_workflow_runs()
    grouped_runs = defaultdict(list)

    for run in runs:
        grouped_runs[run["name"]].append(run)

    for name, run_group in grouped_runs.items():
        run_group.sort(key=lambda r: r["created_at"], reverse=True)
        to_delete = run_group[1:]  # Keep only the latest run

        if not to_delete:
            continue

        print(f"\n🧹 Cleaning up {len(to_delete)} old successful runs for workflow: {name}")
        for run in to_delete:
            delete_workflow_run(run["id"])

# === ENTRY POINT ===
if __name__ == "__main__":
    if not GITHUB_TOKEN:
        raise EnvironmentError("❌ GITHUB_TOKEN environment variable is missing.")

    cleanup_deployments()
    cleanup_workflows()
