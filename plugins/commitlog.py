from github import Github
import pickle
import os
import sys

import header
import keys

COMMIT_FILE = os.getcwd() + "/dataStores/latestcommit.pickle"

async def latest_commit(client):
    gh = Github(keys.GITHUB_PERSONAL_ACCESS_TOKEN)
    repo = gh.get_repo("ifSomeday/KaedeBot")
    commits = repo.get_commits()
    commit = commits[0]
    
    if(not commit.sha == __get_latest_commit() and sys.platform.startswith("linux")):
        mess = commit.commit.message + "\n```\n" + "\n".join(file.filename + " +" + str(file.additions) + "|-" + str(file.deletions) + "" for file in commit.files) + "\n```\n" + ""
        await client.send_message(client.get_channel(header.COMMIT_LOG_CHANNEL), mess)
        __save_latest_commit(commit.sha)
   

def __get_latest_commit():
    if(os.path.isfile(COMMIT_FILE)):
        with open(COMMIT_FILE, "rb") as f:
            return(pickle.load(f))
    else:
        return("")

def __save_latest_commit(sha):
    with open(COMMIT_FILE, "wb") as f:
        pickle.dump(sha, f)