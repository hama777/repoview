import requests
import os
import calendar
import datetime
from datetime import date
#from datetime import date
#from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 25/10/16 v0.10 以前のデータはキャッシュを利用する
version = "0.10"

appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "/repoview.conf"
checkdate = appdir + "/checkdate.txt"
templatefile = appdir + "/cmt_templ.htm"
resultfile = appdir + "/commit.htm"
chachefile = appdir + "/cache.txt"

commit_info = {}  # コミット情報   辞書  キー  repo名  値  コミット数

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def main_proc():
    date_settings()
    read_config()
    read_chache()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return

    parse_template()
#    write_datetime()

def monthly_commit_count() :
    yy = 2025
    today_date = date.today()   
    today_mm = today_date.month
    cf = open(chachefile,'w')
    for mm in range(1,13) :
        if mm > today_mm :
            break
        key = (yy - 2000) * 100 + mm    #  yy は西暦4桁なので2桁になおす
        if key in monthly_commit :
            data = monthly_commit[key]
            count = data[0]
            repo = data[1]
            print("from cache")
        else :
            start_date =  date(yy, mm, 1)
            last_day = calendar.monthrange(yy, mm)[1]   # 月の最終日
            final_date = date(yy, mm, last_day)
            dic_info = get_period_commit_info(start_date,final_date)
            count = dic_info['count']
            repo = dic_info['repo']
        out.write(f'<tr><td align="right">{yy}/{mm:02d}</td><td align="right">{count}</td><td align="right">{repo}</td></tr>\n')
        cf.write(f'{yy}/{mm:02d}\t{count}\t{repo}\n')
    
    cf.close()

def read_chache() :
    global monthly_commit
    today_key = (today_yy - 2000) * 100 + today_mm
    monthly_commit = {}
    with open(chachefile) as f:
        for line in f:
            line = line.rstrip()    # 改行を削除
            data = line.split("\t")
            yymm = data[0].split("/")
            yy = int(yymm[0]) - 2000
            mm = int(yymm[1])
            key = yy * 100 + mm
            if key == today_key :    # 今月分は除く
                break
            monthly_commit[key] = (data[1],data[2])

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

#   未使用
def write_datetime() :
    s = datetime.now().strftime("%Y/%m/%d %H:%M:%S") + "\n"
    f = open(checkdate,"w",encoding='utf-8')
    f.write(s)
    f.close()

#   指定した期間のコミット情報を返す
#   結果は辞書  キー  count 値  コミット数   キー  repo  値  対象repo数
def get_period_commit_info(start_date,end_date) :
    count = 0 
    count_repo = 0 
    repositories = get_repositories(username, token)

    since = f"{start_date}T00:00:00Z"
    until = f"{end_date}T23:59:59Z"
    for repo in repositories:
        n = get_commit_counts(username, repo, token, since, until)
        count += n
        if n > 0 :
            count_repo += 1
    c_info = {}
    c_info['count'] = count
    c_info['repo'] = count_repo
    return c_info

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

def date_settings():
    global  today_date,today_mm,today_dd,today_yy,today_datetime,today_hh

    today_datetime = datetime.datetime.today()   # datetime 型
    today_date = datetime.date.today()           # date 型
    today_mm = today_date.month
    today_dd = today_date.day
    today_yy = today_date.year         #  4桁
    today_hh = today_datetime.hour     #  現在の 時

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

def parse_template() :
    global out 
    f = open(templatefile , 'r', encoding='utf-8')
    out = open(resultfile,'w' ,  encoding='utf-8')
    for line in f :
        if "%monthly_commit_count%" in line :
            monthly_commit_count()
            continue
        if "%version%" in line :
            s = line.replace("%version%",version)
            out.write(s)
            continue
        out.write(line)

    f.close()
    out.close()

if __name__ == "__main__":
    main_proc()
