import praw
import random
import sys
import pickle
import os

NONWORD = "\n"
d = {}
TABLE_NAME = os.cwd() + "memes.pickle"
SUBREDDIT = "copypasta"

def addTable(aList):
    word1 = NONWORD
    word2 = NONWORD
    for aString in aList:
        if "http" in aString:
            continue
        for word in aString.split():
            d.setdefault((word1, word2),[]).append(word)
            word1, word2 = word2, word
        d.setdefault((word1, word2),[]).append(NONWORD)
    d.setdefault((word1,word2),[]).append(NONWORD)

def addSingle(string):
    word1 = NONWORD
    word2 = NONWORD
    string = string.strip()
    for word in string.split():
        d.setdefault((word1, word2), []).append(word)
        word1, word2 = word2, word
    d.setdefault((word1, word2), []).append(NONWORD)

##table arg breaks for some reason
def dumpTable(table):
    with open(TABLE_NAME,'wb') as f:
        pickle.dump(d, f)

##table arg breaks for some reason
def openTable(table):
    with open(TABLE_NAME,'rb') as f:
        global d
        d = pickle.load(f)

def printTable():
    print(d)

def clearTable():
    global d
    d.clear()

def generateText():
    word1 = NONWORD
    word2 = NONWORD
    output = ""
    while True:
        newword = random.choice(d[(word1, word2)])
        if(newword == NONWORD):
            return(output)
            sys.exit()
        elif(len(output + newword + " ") > 2000):
            return(output)
            sys.exit()
        output += newword + " "
        word1, word2 = word2, newword
    return(output)


def download(subreddit, num):
    t = []
    r = praw.Reddit(client_id=keys.PRAW_ID, client_secret=keys.PRAW_SECRET, user_agent='python:ThreadTitleDownloader(by /u/WalrusPorn)')
    submissions = r.get_subreddit(subreddit).get_top(limit = num)
    for item in submissions:
        item = item.selftext.replace(u'\ufeff', '')
        item += "\n"
        t.append(item)
    return(t)

def init():
    if(os.path.isfile(TABLE_NAME)):
        print("previous table found... opening")
        openTable(TABLE_NAME)
    else:
        print("no local table.... generating one")
        list = download(SUBREDDIT, 250)
        addTable(list)
        dumpTable(d)
        print("local table created")
