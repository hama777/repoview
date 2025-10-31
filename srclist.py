#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import os
import pytz
import datetime
from datetime import datetime
from datetime import date,timedelta
from ftplib import FTP_TLS
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 25/10/31 v2.00 情報取得専用とした
version = "2.00"     

out =  ""
logf = ""
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "/repoview.conf"
resultfile = appdir + "/srclist.htm" 
templatefile = appdir + "/repo_templ.htm"
dailyfile =  appdir + "/daily.txt"    #  日付ごと repo ごとのソース行数
repodatafile = appdir + "/repodata.txt"       #  repoの情報を保存
srcdatafile = appdir + "/srcdata.txt"       #  ソースの行数等のテータを保存
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#   全情報
#     キー  repo名  値  file_data 
#                      file_data  キー filename  値  attr  キー  line  cdate message
repo_info = {}

#   repoごとの 全行数、ファイル数、最終更新日 を保持する
#     キー  repo名  値  repo_data  キー  line  num_file  last_update
repo_line = {}

#   過去の情報   キー  日付   値   past_data(辞書)
#       past_data   キー  repo名   値   ソース数、行数 のリスト
all_past_data = {}

all_line = 0      # 全行数
all_num_file = 0  # 全ファイル数
total_line = {}    #  日付ごとの総行数   キー  日付   値  ソース行総行数

def main():
    global  all_line, all_num_file
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")

    date_settings()
    read_config()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return

    read_repodata()

    repositories = get_repositories(username, token)
    n = 0 
    all_line = 0 
    all_num_file = 0 
    for repo_name in repositories:
        n += 1
        if debug == 1 and n > 3 :     #  debug 
            break 
        print(f"\nRepository: {repo_name}")

        files = get_files_in_repository(username, repo_name, token)
        
        file_data = {}
        total_line = 0 
        num_file = 0
        last_update =  datetime(2000, 1, 1, 0, 0, 0)   # 最新更新日 初期値として 2000/01/01 を設定
        for file_path in files:
            line_count, last_commit_date, last_commit_message = get_file_details(username, repo_name, file_path, token)
            attr = {}            
            dt = datetime.strptime(last_commit_date, "%Y-%m-%dT%H:%M:%SZ")
            dt = dt + timedelta(hours=9)    #  JST にするため 9時間加算
            attr['line'] = line_count
            attr['cdate'] = dt
            attr['message'] = last_commit_message
            file_data[file_path] = attr
            total_line += line_count
            all_line += line_count
            num_file += 1 
            all_num_file += 1
            if dt > last_update :
                last_update = dt

        repo_info[repo_name] = file_data
        repo_data = {}
        repo_data['line'] = total_line
        repo_data['num_file'] = num_file
        repo_data['last_update'] = last_update
        repo_line[repo_name] = repo_data

    output_repolist()
    output_srclist()

# dailyfile を読んで  all_past_data を作成する
#    TODO:  all_past_data は未使用
def read_repodata() :
    global all_past_data
    prev_dt = ""
    past_data = {}
    with open(dailyfile) as f:
        for line in f:
            line = line.rstrip()
            data = line.split("\t")
            dt = data[0]
            if prev_dt == "" :
                prev_dt = dt
            if dt != prev_dt :
                all_past_data[prev_dt] = past_data
                past_data = {}
                prev_dt = dt
            past_data[data[1]] = (data[2],data[3] )

    all_past_data[prev_dt] = past_data

# TODO:  将来的には srcdata.txt に出力するのみにし、表示は別機能でおこなう
def output_srclist() :
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")
    prev_repo = ""
    fp = open(srcdatafile,"w")
    for repo,file_data in repo_info.items() :

        for filen,attr in file_data.items() :
            if repo != prev_repo :   #  同じrepoの時は最初の行のみ repo名を表示
                prev_repo = repo
                reponame = repo
            else :              
                reponame = ""

            dt_str = attr["cdate"].strftime("%y/%m/%d %H:%M")
            repo_data = repo_line[repo]
            total_line = repo_data['line']
            num_file = repo_data['num_file']
            fp.write(f'{repo}\t{filen}\t{attr["line"]}\t{dt_str}\t{attr["message"]}\n')

    fp.close()

def output_repolist() : 
    sum_line = 0 
    sum_files = 0 
    dailyf = open(dailyfile,"a")
    fp = open(repodatafile,"w")
    for reponame,repo_data in repo_line.items():
        num_file = repo_data['num_file']
        line = repo_data['line']
        sum_line += line
        sum_files += 1
        last_update = repo_data['last_update'] 
        last_update_str = last_update.strftime("%y/%m/%d %H:%M")
        fp.write(f'{reponame}\t{num_file}\t{line}\t{last_update_str}\n')

        dailyf.write(f'{today_yymmdd}\t{reponame}\t{num_file}\t{line}\n')
    dailyf.close()

def get_repositories(username, token):
    url = f"https://api.github.com/users/{username}/repos"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    repos = response.json()
    return [repo['name'] for repo in repos]

def get_files_in_repository(username, repo_name, token):
    url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/main?recursive=1"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 404 :
        url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/master?recursive=1"
        response = requests.get(url, headers=headers, verify=False)

    response.raise_for_status()

    tree = response.json().get('tree', [])
    return [item['path'] for item in tree if item['type'] == 'blob']

def get_file_details(username, repo_name, file_path, token):
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    file_data = response.json()
    file_content = requests.get(file_data['download_url'],verify=False).text
    line_count = len(file_content.splitlines())

    commit_url = f"https://api.github.com/repos/{username}/{repo_name}/commits?path={file_path}&per_page=1"
    commit_response = requests.get(commit_url, headers=headers, verify=False)
    commit_response.raise_for_status()
    commits = commit_response.json()

    if commits:
        last_commit_date = commits[0]['commit']['committer']['date']
        last_commit_message = commits[0]['commit']['message']
    else:
        last_commit_date = "Unknown"
        last_commit_message = "No commit message"

    return line_count, last_commit_date, last_commit_message

def date_settings():
    global today_yymmdd
    today_datetime = datetime.today()
    d = today_datetime.strftime("%m/%d %H:%M")
    today_yymmdd = today_datetime.strftime("%y/%m/%d")

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

if __name__ == "__main__":
    main()
