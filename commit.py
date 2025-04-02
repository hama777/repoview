import requests
import os
from datetime import datetime, timedelta

def get_repositories(username, token):
    url = f"https://api.github.com/users/{username}/repos"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [repo['name'] for repo in response.json()]

def get_commit_counts(username, repo_name, token, since, until):
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    headers = {"Authorization": f"token {token}"}
    params = {"since": since, "until": until}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return len(response.json())

def main():
    username = ""
    token = ""

    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return
    
    repositories = get_repositories(username, token)
    start_date = datetime.utcnow().date() - timedelta(days=29)
    
    for days_since in range(30):
        date = start_date + timedelta(days=days_since)
        since = f"{date}T00:00:00Z"
        until = f"{date}T23:59:59Z"
        
        commit_data = []
        for repo in repositories:
            commit_count = get_commit_counts(username, repo, token, since, until)
            if commit_count > 0:
                commit_data.append(f"リポジトリ名 {repo} コミット数 {commit_count}")
        
        if commit_data:
            print(f"{date.strftime('%m/%d')} {' '.join(commit_data)}")

if __name__ == "__main__":
    main()
