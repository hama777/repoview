import requests
import os
import calendar
import datetime
import pandas as pd
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
    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return
    read_chache()
    create_df_monthly_commit()

    parse_template()
    write_chache()
#    write_datetime()

#   月別コミット情報 df_monthly_commit を作成する
def create_df_monthly_commit() :
    global df_monthly_commit    # 月ごとのコミット数 df  カラム yymm 年月  count コミット数  repo リポ数

    yy = 2025    #  暫定
    today_date = date.today()   
    today_mm = today_date.month
    rows = []
    for mm in range(1,13) :
        if mm > today_mm :
            break
        key = (yy - 2000) * 100 + mm    #  yy は西暦4桁なので2桁になおす
        if key in monthly_commit :
            data = monthly_commit[key]
            count = data[0]
            repo = data[1]
        else :
            start_date =  date(yy, mm, 1)
            last_day = calendar.monthrange(yy, mm)[1]   # 月の最終日
            final_date = date(yy, mm, last_day)
            dic_info = get_period_commit_info(start_date,final_date)
            count = dic_info['count']
            repo = dic_info['repo']
        rows.append([key, count , repo])

    df_monthly_commit = pd.DataFrame(rows, columns=["yymm", "count", "repo"])

#   月別コミット数グラフ
def commit_graph() :
    for _,row in df_monthly_commit.iterrows() :
        yymm = row["yymm"]
        count = row["count"]
        out.write(f"['{yymm}',{count}],") 

#   月別コミット数、リポジトリ情報
def monthly_commit_count() :
    for _,row in df_monthly_commit.iterrows() :
        yymm = row["yymm"]
        count = row["count"]
        repo = row["repo"]
        out.write(f'<tr><td align="right">{yymm}</td><td align="right">{count}</td><td align="right">{repo}</td></tr>\n')

def read_chache() :
    global monthly_commit

    monthly_commit = {}
    if not os.path.isfile(chachefile) :   # キャッシュファイルがなければ何もしない
        return
    today_key = (today_yy - 2000) * 100 + today_mm
    with open(chachefile) as f:
        for line in f:
            line = line.rstrip()    # 改行を削除
            data = line.split("\t")
            key = int(data[0])
            if key == today_key :    # 今月分は除く
                break
            monthly_commit[key] = (data[1],data[2])

def write_chache() :
    cf = open(chachefile,'w')
    for _,row in df_monthly_commit.iterrows() :
        yymm = row["yymm"]
        count = row["count"]
        repo = row["repo"]
        cf.write(f'{yymm}\t{count}\t{repo}\n')
    
    cf.close()

#   リポジトリ情報取得
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
#   未使用
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
        if "%commit_graph%" in line :
            commit_graph()
            continue
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
