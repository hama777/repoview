import requests
import os
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 25/08/04 v1.03 utcnowのワーニング対処
version = "0.03"

appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "/repoview.conf"
checkdate = appdir + "/checkdate.txt"

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_repositories(username, token):
    url = f"https://api.github.com/users/{username}/repos"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()
    return [repo['name'] for repo in response.json()]

def get_commit_counts(username, repo_name, token, since, until):
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    headers = {"Authorization": f"token {token}"}
    params = {"since": since, "until": until}
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return len(response.json())

def read_config() : 
    global username,proxy,token,debug
    global ftp_host,ftp_user,ftp_pass,ftp_url
    if not os.path.isfile(conffile) :
        debug = 1 
        return

    conf = open(conffile,'r', encoding='utf-8')
    username = conf.readline().strip()
    token = conf.readline().strip()
    proxy  = conf.readline().strip()
    ftp_host = conf.readline().strip()
    ftp_user = conf.readline().strip()
    ftp_pass = conf.readline().strip()
    ftp_url = conf.readline().strip()
    debug = int(conf.readline().strip())
    print(ftp_url)

    conf.close()

def write_datetime() :
    s = datetime.now().strftime("%Y/%m/%d %H:%M:%S") + "\n"
    f = open(checkdate,"w",encoding='utf-8')
    f.write(s)
    f.close()
    

def main():
    read_config()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return
    
    repositories = get_repositories(username, token)
    check_days = 29
    if debug == 1 :
        check_days = 5
    start_date = datetime.now().date() - timedelta(days=check_days)
    
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

    write_datetime()

if __name__ == "__main__":
    main()
