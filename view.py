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

# 25/11/10 v1.00 総行数グラフ表示
version = "1.00"     

out =  ""
logf = ""
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "/repoview.conf"
resultfile = appdir + "/srclist.htm" 
templatefile = appdir + "/repo_templ.htm"
dailyfile =  appdir + "/daily.txt"    #  日付ごと repo ごとのソース行数
repodatafile =  appdir + "/repodata.txt"   #  repoの情報を保存
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

total_line = {}    #  日付ごとの総行数   キー  日付(yy/mm/dd 文字列)   値  ソース行総行数

def main():
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")
    read_config()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy
    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return

    read_repodata()
    read_dailydata()

    parse_template()
    ftp_upload()

def read_repodata() :
    global repo_line
    with open(repodatafile) as f:
        for line in f:
            line = line.rstrip()
            data = line.split("\t")
            repo_data = {}
            repo_data['num_file'] = int(data[1])
            repo_data['line'] = int(data[2])
            repo_data['last_update'] = data[3]
            repo_line[data[0]] = repo_data

# repodatafile を読んで  all_past_data を作成する
def read_dailydata() :
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
            past_data[data[1]] = (int(data[2]),int(data[3]) )

    all_past_data[prev_dt] = past_data

def line_count_graph() :
    for k,repo in all_past_data.items() :
        sum = 0 
        for name,info in repo.items() :
            sum += info[1]  # 行数
        out.write(f"['{k}',{sum}],")

def output_srclist() :
    prev_repo = ""
    total_line  = 0
    num_file = 0 
    with open(srcdatafile) as f:
        for line in f:
            line = line.rstrip()
            (repo,filen,linecnt,mod_date,message) = line.split("\t")
            if repo != prev_repo :   #  同じrepoの時は最初の行のみ repo名を表示
                if prev_repo != "" :
                    out.write(f'<tr><td class=all>合計</td><td class=all>{num_file}</td><td class=all align="right">{total_line}</td>'
                              f'<td class=all></td><td class=all></td></tr>\n')
                total_line  = 0
                num_file = 0 
                prev_repo = repo
                reponame = repo
            else :              
                reponame = ""
            total_line += int(linecnt)
            num_file += 1

            out.write(f'<tr><td>{reponame}</td><td>{filen}</td><td align="right">{linecnt}</td>'
                      f'<td>{mod_date}</td><td>{message}</td></tr>\n')

    out.write(f'<tr><td class=all>合計</td><td class=all>{num_file}</td><td class=all align="right">{total_line}</td>'
              f'<td class=all></td><td class=all></td></tr>\n')

def output_repolist() : 
    sum_line = 0 
    sum_files = 0 
    for reponame,repo_data in repo_line.items():
        num_file = repo_data['num_file']
        line = repo_data['line']
        sum_line += line
        sum_files += num_file
        last_update_str = repo_data['last_update'] 
        #last_update_str = last_update.strftime("%y/%m/%d %H:%M")
        out.write(f'<tr><td>{reponame}</td><td align="right">{num_file}</td>'
                  f'<td align="right">{line}</td><td>{last_update_str}</td></tr>')

    out.write(f'<tr><td class=all>合計</td><td class=all align="right">{sum_files}</td>'
              f'<td class=all align="right">{sum_line}</td><td class=all>--</td></tr>')

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
        if "%line_count_graph%" in line :
            line_count_graph()
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

    conf.close()

def ftp_upload() : 
    if debug == 1 :
        return 
    with FTP_TLS(host=ftp_host, user=ftp_user, passwd=ftp_pass) as ftp:
        ftp.storbinary('STOR {}'.format(ftp_url), open(resultfile, 'rb'))

if __name__ == "__main__":
    main()
