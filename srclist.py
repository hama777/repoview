#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import os
import pytz
from datetime import datetime
from datetime import date,timedelta
from ftplib import FTP_TLS
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 25/06/27 v1.02 repoの行数などをファイルに出力する
version = "1.02"     

out =  ""
logf = ""
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "/repoview.conf"
resultfile = appdir + "/srclist.htm" 
templatefile = appdir + "/repo_templ.htm"
repodatafile =  appdir + "/repodata.txt"    #  日付ごと repo ごとのソース行数
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#   全情報
#     キー  repo名  値  file_data 
#                      file_data  キー filename  値  attr  キー  line  cdate message
repo_info = {}

#   repoごとの 全行数、ファイル数、最終更新日 を保持する
#     キー  repo名  値  repo_data  キー  line  num_file  last_update
repo_line = {}
all_line = 0      # 全行数
all_num_file = 0  # 全ファイル数

def main():
    global  all_line, all_num_file
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")
    read_config()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return

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

    #print(repo_line)
    parse_template()
    ftp_upload()

def output_srclist() :
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")
    prev_repo = ""
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
            out.write(f'<tr><td>{reponame}</td><td>{filen}</td><td align="right">{attr["line"]}</td>'
                      f'<td>{dt_str}</td><td>{attr["message"]}</td></tr>\n')

        out.write(f'<tr><td class=all>合計</td><td class=all  align="right">{num_file}</td>'
                  f'<td class=all align="right">{total_line}</td>'
                  f'<td class=all>---</td><td class=all>---</td></tr>\n')

def output_repolist() : 
    sum_line = 0 
    sum_files = 0 
    repof = open(repodatafile,"a")
    for reponame,repo_data in repo_line.items():
        num_file = repo_data['num_file']
        line = repo_data['line']
        sum_line += line
        sum_files += 1
        last_update = repo_data['last_update'] 
        last_update_str = last_update.strftime("%y/%m/%d %H:%M")
        out.write(f'<tr><td>{reponame}</td><td align="right">{num_file}</td>'
                  f'<td align="right">{line}</td><td>{last_update_str}</td></tr>')

        repof.write(f'{today_yymmdd}\t{reponame}\t{num_file}\t{line}\n')
    out.write(f'<tr><td class=all>合計</td><td class=all align="right">{sum_files}</td>'
              f'<td class=all align="right">{sum_line}</td><td class=all>--</td></tr>')
    repof.close()

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

def output_current_date(s):
    global today_yymmdd
    today_datetime = datetime.today()
    d = today_datetime.strftime("%m/%d %H:%M")
    s = s.replace("%today%",d)
    out.write(s)
    today_yymmdd = today_datetime.strftime("%y/%m/%d")

def parse_template() :
    global out 
    f = open(templatefile , 'r', encoding='utf-8')
    out = open(resultfile,'w' ,  encoding='utf-8')
    for line in f :
        if "%srclist%" in line :
            output_srclist()
            continue
        if "%repolist%" in line :
            output_repolist()
            continue
        if "%version%" in line :
            s = line.replace("%version%",version)
            out.write(s)
            continue
        if "%today%" in line :
            output_current_date(line)
            continue
        out.write(line)

    f.close()
    out.close()

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

def ftp_upload() : 
    if debug == 1 :
        return 
    with FTP_TLS(host=ftp_host, user=ftp_user, passwd=ftp_pass) as ftp:
        ftp.storbinary('STOR {}'.format(ftp_url), open(resultfile, 'rb'))

if __name__ == "__main__":
    main()
