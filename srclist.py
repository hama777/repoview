#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 24/12/20 v0.01 結果をhtmlに出力する
version = "0.01"     

out =  ""
logf = ""
appdir = os.path.dirname(os.path.abspath(__file__))
conffile = appdir + "/repoview.conf"
resultfile = appdir + "/srclist.htm" 
templatefile = appdir + "/repo_templ.htm"
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#   全情報
#     キー  repo名  値  file_data 
#                      file_data  キー filename  値  attr  キー  line  cdate message
repo_info = {}

def main():
    read_config()

    if not proxy == "noproxy" :
        os.environ['https_proxy'] = proxy

    if not token:
        print("Error: GitHub token is not set in the environment variables.")
        return

    repositories = get_repositories(username, token)
    
    n = 0 
    for repo_name in repositories:
        n += 1
        print(f"\nRepository: {repo_name}")
        files = get_files_in_repository(username, repo_name, token)
        
        file_data = {}
        for file_path in files:
            line_count, last_commit_date, last_commit_message = get_file_details(username, repo_name, file_path, token)
            #print(f"{file_path}: {line_count} lines, Last Commit: {last_commit_date}, Message: {last_commit_message}")
            attr = {}            
            attr['line'] = line_count
            attr['cdate'] = last_commit_date
            attr['message'] = last_commit_message
            file_data[file_path] = attr

        repo_info[repo_name] = file_data

    print(repo_info)

    parse_template()

def output_srclist() :
    for reponame,file_data in repo_info.items() :
        for filen,attr in file_data.items() :
            line = attr['line']
            out.write(f'<tr><td>{reponame}</td><td>{filen}</td><td>{attr["line"]}</td><td>{attr["cdate"]}</td><td>{attr["message"]}</td></tr>\n')

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

def parse_template() :
    global out 
    f = open(templatefile , 'r', encoding='utf-8')
    out = open(resultfile,'w' ,  encoding='utf-8')
    for line in f :
        if "%srclist%" in line :
            output_srclist()
            continue
        # if "%version%" in line :
        #     s = line.replace("%version%",version)
        #     out.write(s)
        #     continue
        # if "%today%" in line :
        #     output_current_date(line)
        #     continue
        out.write(line)

    f.close()
    out.close()

def read_config() : 
    global username,proxy,token,debug
    if not os.path.isfile(conffile) :
        debug = 1 
        return

    conf = open(conffile,'r', encoding='utf-8')
    username = conf.readline().strip()
    token = conf.readline().strip()
    proxy  = conf.readline().strip()
    debug = int(conf.readline().strip())
    conf.close()



if __name__ == "__main__":
    main()
