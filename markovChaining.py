import praw
import random
import sys
import pickle
import keys
import os
import string
import re

NONWORD = "\n"
d = {}
nd = {}
OLD_TABLE_NAME = os.getcwd() + "/dataStores/memes.pickle"
NEW_TABLE_NAME = os.getcwd() + "/dataStores/newMemes.pickle"
MEME_LOG = os.getcwd() + "/dataStores/memes.log"
meme_array = []
SUBREDDIT = "copypasta"

##TODO: rewrite this not retardedly

def addTable(aList, table):
    word1 = NONWORD
    word2 = NONWORD
    for aString in aList:
        if "http" in aString:
            continue
        for word in aString.split():
            table.setdefault((word1, word2),[]).append(word)
            word1, word2 = word2, word
        table.setdefault((word1, word2),[]).append(NONWORD)
    table.setdefault((word1,word2),[]).append(NONWORD)

def addTable3(aList, table):
    word1 = NONWORD
    word2 = NONWORD
    word3 = NONWORD
    for aString in aList:
        if "http" in aString:
            continue
        for word in aString.split():
            table.setdefault((word1, word2, word3),[]).append(word)
            word1, word2, word3 = word2, word3, word
        table.setdefault((word1, word2, word3),[]).append(NONWORD)
    table.setdefault((word1, word2, word3),[]).append(NONWORD)

def addSingle(string, table):
    word1 = NONWORD
    word2 = NONWORD
    string = string.strip()
    meme_array.append(string)
    for word in string.split():
        table.setdefault((word1, word2), []).append(word)
        word1, word2 = word2, word
    table.setdefault((word1, word2), []).append(NONWORD)

def addSingle3(string, table):
    word1 = NONWORD
    word2 = NONWORD
    word3 = NONWORD
    string = string.strip()
    meme_array.append(string)
    for word in string.split():
        table.setdefault((word1, word2, word3), []).append(word)
        word1, word2, word3 = word2, word3, word
    table.setdefault((word1, word2, word3), []).append(NONWORD)

def dumpTable(table_name, table):
    with open(table_name,'wb') as f:
        pickle.dump(table, f)

def dumpAllTables():
    if(len(meme_array) > 0):
        dumpTable(OLD_TABLE_NAME, d)
        dumpTable(NEW_TABLE_NAME, nd)
        with open(MEME_LOG, "a") as f:
            for m in meme_array:
                f.write(m + "\n")
        meme_array.clear()

def openTable(table_name):
    with open(table_name,'rb') as f:
        return(pickle.load(f))

def printTable():
    print(d)

def clearTable():
    global d
    d.clear()

def generalize(item):
    return(re.sub('[' + string.punctuation + ']', '', item).lower())

##match generalized item, ignoring nones
def matcher(pattern):
    def match(item):
        return(all(p is None or generalize(t) == generalize(p) for p, t in zip(pattern, item)))
    return(match)

def fuzzyGet(pattern, table):
    matches = filter(matcher(pattern), list(table.keys()))
    arr = []
    for m in matches:
        arr += table[m]
    if(len(arr) > 0):
        return(matches, arr)
    else:
        return(None, None)

def generateText(table, builder = None):
    word1, word2 = NONWORD, NONWORD
    for sText in builder:
        word1, word2 = word2, sText
    output = " ".join(builder) + " "
    if(not (word1, word2) in table):
        word1, word2 = NONWORD, NONWORD
        output = ""
    while True:
        newword = random.choice(table[(word1, word2)])
        if(newword == NONWORD):
            return(output)
        elif(len(output + newword + " ") > 2000):
            return(output)
        output += newword + " "
        word1, word2 = word2, newword
    return(output)

def generateText3(table, builder = None):
    word1, word2, word3 = NONWORD, NONWORD, NONWORD
    for sText in builder:
        word1, word2, word3 = word2, word3, sText
    output = " ".join(builder) + " "
    matches, choices = fuzzyGet((word1, word2, word3), table)
    if(choices is None):
        word1, word2, word3 = NONWORD, NONWORD, NONWORD
        matches, choices = fuzzyGet((word1, word2, word3), table)
        output = ""
    while True:
        newword = random.choice(choices)
        if(newword == NONWORD):
            return(output)
        elif(len(output + newword + " ") > 2000):
            return(output)
        output += newword + " "
        word1, word2, word3 = word2, word3, newword
        matches, choices = fuzzyGet((word1, word2, word3), table)
    return(output)

def download(subreddit, num):
    t = []
    r = praw.Reddit(client_id=keys.PRAW_ID, client_secret=keys.PRAW_SECRET, user_agent='python:ThreadTitleDownloader(by /u/WalrusPorn)')
    submissions = r.subreddit(subreddit).top(limit = num)
    for item in submissions:
        item = item.selftext.replace(u'\ufeff', '')
        item += "\n"
        t.append(item)
    return(t)

def init():
    if(os.path.isfile(OLD_TABLE_NAME)):
        global d
        d = openTable(OLD_TABLE_NAME)
    else:
        list = download(SUBREDDIT, 250)
        addTable(list, d)
        dumpTable(OLD_TABLE_NAME, d)

    if(os.path.isfile(NEW_TABLE_NAME)):
        global nd
        nd = openTable(NEW_TABLE_NAME)
    else:
        addSingle("this is a meme", nd)
        dumpTable(NEW_TABLE_NAME, nd)
