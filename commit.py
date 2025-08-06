import requests
import os
import calendar
from datetime import date
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 25/08/06 v1.05 月ごとのコミット数集計
version = "0.05"

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

    conf.close()

def write_datetime() :
    s = datetime.now().strftime("%Y/%m/%d %H:%M:%S") + "\n"
    f = open(checkdate,"w",encoding='utf-8')
    f.write(s)
    f.close()

#   指定した期間のコミット情報を取得する
#   結果は辞書  commit_info  キー  repo名  値  コミット数
def get_period_info(start_date,end_date) :
    global commit_info

    commit_info = {}
    repositories = get_repositories(username, token)

    since = f"{start_date}T00:00:00Z"
    until = f"{end_date}T23:59:59Z"
    for repo in repositories:
        commit_count = get_commit_counts(username, repo, token, since, until)
        if commit_count > 0:
            commit_info[repo] = commit_count

    print(commit_info)

def main():
    read_config()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return
    
    today_date = date.today()   
    today_mm = today_date.month

    #start_date =  date(2025, 7, 1)
    #end_date =  date(2025, 8, 5)
    #get_period_info(start_date,end_date)

    yy = 2025
    for mm in range(1,13) :
        if mm > today_mm :
            break
        start_date =  date(2025, mm, 1)
        last_day = calendar.monthrange(yy, mm)[1]
        final_date = date(yy, mm, last_day)
        get_period_info(start_date,final_date)

    write_datetime()

if __name__ == "__main__":
    main()
