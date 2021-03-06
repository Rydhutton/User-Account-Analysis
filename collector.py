import praw
import re
from datetime import datetime
from time import sleep
from threading import Thread, active_count as active_thread_count
from objects import User
from db import *

from praw.reddit import Redditor

#Praw data types and attributes: https://praw.readthedocs.io/en/latest/code_overview/praw_models.html
#Spacy data types and attributes: https://spacy.io/api
#MySQL python connector resources: https://dev.mysql.com/doc/connector-python/en/
#Python Regular Expressions: https://docs.python.org/3/library/re.html

# Make sure you install mysql.connector.python and not mysql.connector or you will have issues authenticating on the SQL server

# Requires a MySQL Server Database to run. Once created set SQL_SERVER_IPV4 to your server's address (localhost for local computer)
# Next create 2 users to serve the database
# One user named Ryan with insertion priviledges
# And another user named Admin with DBA permissions


def cleandb():
    # Use to delete any accounts in the database which have been deleted or suspended from reddit
    pw = input("Admin password: ")
    accounts = importusers()
    for line in accounts:
        user = User(username=line[0])
        Redditor = user.get_redditor()
        try:
            _ = Redditor.comment_karma
        except:
            user.delete_from_db(admin_password=pw)

def updatedb():
    accounts = importusers()
    for line in accounts:
        user = User(username=line[0])
        user.save_comments_to_db()
        user.save_posts_to_db()

def sql_exec_userdata(cursor, user):
    try:
        sql = ("INSERT INTO userdata "
                "(username, gender, age, agestamp) "
                "VALUES (%s, %s, %s, %s)")
        val = (user.username, user.gender, user.age, user.agestamp)
        cursor.execute(sql, val)
        return True
    except: return False

def sql_exec_commentdata(cursor, comment):
    try:
        sql = ("INSERT INTO usercommentdata "
                "(username, cid, comment, date) "
                "VALUES (%s, %s, %s, %s)")
        val = (comment.author.name, comment.id, comment.body, unix_utc_toString(comment.created_utc))
        cursor.execute(sql, val)
        return True
    except: return False

def sql_exec_postdata(cursor, post):
    try:
        sql = ("INSERT INTO userpostdata "
                "(username, pid, title, selftext, date) "
                "VALUES (%s, %s, %s, %s, %s)")
        val = (post.author.name, post.id, post.title, post.selftext, unix_utc_toString(post.created_utc))
        cursor.execute(sql, val)
        return True
    except: return False


#********************** COLLECTOR FUNCTIONS ***********************

def login():
    reddit = praw.Reddit("py-bot-master")
    return reddit

def unix_utc_toString(unix_string):
    return datetime.utcfromtimestamp(unix_string).strftime('%Y-%m-%d %H:%M:%S')
               
def collect(subreddit, limit=None):
    if limit == None:
        for submission in subreddit.stream.submissions():
            title = submission.title.lower()
            search = re.search("(i|my|i'm|i am|me) +\(([1-9][0-9][mf])\)", title) # Need to modify the RE to be () or []
            if search:
                target = User(submission.author.name, age_gender=search.group(2), unix_time=submission.created_utc)
                target.save_comments_to_db()
                target.save_posts_to_db()
    else:
        count = 0
        for submission in subreddit.stream.submissions():
            title = submission.title.lower()
            search = re.search("(i|my|i'm|i am|me) +\(([1-9][0-9][mf])\)", title)
            if search:
                count += 1
                target = User(submission.author.name, age_gender=search.group(2), unix_time=submission.created_utc)
                print(target.username)
                target.thread_save_to_db()
            if count >= limit:
                break
        
def prod_run():
    reddit = login()
    r_relationships = reddit.subreddit("Relationships")
    r_dating = reddit.subreddit("dating")
    r_relationship_advice = reddit.subreddit("relationship_advice")
    r_relationships_thread = Thread(target=collect, args=(r_relationships,))
    r_dating_thread = Thread(target=collect, args=(r_dating,))
    r_relationship_advice_thread = Thread(target=collect, args=(r_relationship_advice,))
    r_relationships_thread.daemon = True
    r_dating_thread.daemon = True
    r_relationship_advice_thread.daemon = True
    r_relationships_thread.start()
    r_dating_thread.start()
    r_relationship_advice_thread.start()
    exit_flag = False
    while(exit_flag is False):
        print("number of active threads: " + str(active_thread_count()))
        db = opendb()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM userdata")
        count = cur.fetchone()
        print("number of users collected: " + str(count[0]))
        cur.execute("SELECT COUNT(*) FROM userpostdata")
        count = cur.fetchone()
        print("number of posts collected: " + str(count[0]))
        cur.execute("SELECT COUNT(*) FROM usercommentdata")
        count = cur.fetchone()
        print("number of comments collected: " + str(count[0]))
        if input("Would you like to continue and refresh stats? Y/N") == "N": exit_flag = True


# ******************** MAIN ********************

if __name__ == "__main__":
  prod_run()


# CAN ONLY BE RUN IN PYTHON 3.10+
# cmdline help menu with new search matching
'''
HELP_MENU = {
    "collect: collects incoming stream of users and stores them into userdata",
    "help:    brings up the current help menu"
}

def cmdline():
    def run_command(command: str):
        match command.split:
            case ["collect"]:
                print("collecting... press ctrl + c to exit.")
                collect(login())
            case ["help" | "?"]:
                for line in HELP_MENU:
                    print(line)
            case ["init" | "initialize | makedb", *rest]:
                if "-f" or "-force" in rest:
                    resetdb()
                    initdb()
                else:
                    initdb()
            case ["reset" | "resetdb"]:
                resetdb()
            case _:
                print(f"unknown command: {command!r}.")
    
    while(True):
        cmd = input(">")
        run_command(cmd)
'''
