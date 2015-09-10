#!/usr/bin/python3
import praw
import time
import datetime
import calendar
import json
import re
import copy
import glob
import sys
sys.path.append("/home/sds/python/utils/")
import sdsOAuth2Util
from collections import OrderedDict

MYUSERNAME="booksawards"
count               = 0
nextOAuthUpdate     = 0
mostRecentMondayUTC = 0
previousMondayUTC   = 0
CURRENTDATE = "%s-%s-%s" % (datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
users = {}
xtotals = {}
previousTotals = {}
optIns = []


#==============================================================
def init ():
    r = praw.Reddit("BookAwards - UserPoints /u/boib")
    r.config.decode_html_entities = True
    return r



#==============================================================
def newUser ():
    """
        Create data struct for a new user.
    """

    userDict = {}
    userTotals = {}

    # wayr is a single permalink url
    # users['username']['wayr'] = "https://www.reddit.com/comments/%s/_/%s" % (wayrFullname[3:], c.id)
    userDict['wayr'] = ""

    # rec is a list of multiple permalink urls.  in a single thread, there could be multiple urls
    # userDict['rec'].append("https://www.reddit.com/comments/%s/_/%s" % (recFullname[3:], reply.id))
    userDict['rec'] = []

    # new is dict of posts.  for each post, one new comment is possible
    # userDict['new'][c.link_id] = "https://www.reddit.com/comments/%s/_/%s" % (c.link_id[3:], c.id)
    userDict['new'] = {}

    # ama is dict of posts.  for each post, one comment is possible
    # userDict['ama'][c.link_id] = "https://www.reddit.com/comments/%s/_/%s" % (c.link_id[3:], c.id)
    userDict['ama'] = {}

    userTotals['wayr']  = 0
    userTotals['rec']   = 0
    userTotals['new']   = 0
    userTotals['ama']   = 0
    userTotals['total'] = 0

    return userDict, userTotals


#==============================================================
def calcPreviousTotals(weekNumber):

    global previousTotals

    # testing...
    if weekNumber == 0:
        weekNumber = 1

    # maintain a 12 week window.  totals prior to 12 weeks ago are not counted
    if weekNumber > 12:
        startWeek = weekNumber - 12
    else:
        startWeek = 0

    # filename format:
    #   weeknumber-year-month-day-totals.json

    for i in range(startWeek, weekNumber):
        print ("startWeek: %d  weekNumber: %d  i: %d" % (startWeek, weekNumber, i))
        print("Getting json files: " + "%d-*.json" % (i))
        files = glob.glob("%d-*.json" % (i))
        if len(files) != 1:
            print("\nERROR! files = %s\n" % (files))
            quit()

        with open(files[0], 'r') as fp:
            tmpTotals=json.load(fp)
            fp.close()

        if len(previousTotals) == 0:
            previousTotals = copy.deepcopy(tmpTotals)
        else:
            for x in tmpTotals:
                if x in previousTotals:
                    previousTotals[x]['ama']   += tmpTotals[x]['ama']
                    previousTotals[x]['new']   += tmpTotals[x]['new']
                    previousTotals[x]['wayr']  += tmpTotals[x]['wayr']
                    previousTotals[x]['rec']   += tmpTotals[x]['rec']
                    previousTotals[x]['total'] += tmpTotals[x]['total']
                else:
                    previousTotals[x] = copy.deepcopy(tmpTotals[x])



#==============================================================
def setFlair (r, uname, text):

    if uname in optIns:
        print ("Setting flair %s for %s" % (text, uname))
        r.set_flair("books", uname, text, "points-1")
    else:
        print ("No flair %s for %s" % (text, uname))



#==============================================================
def getOptIns (r):

    global optIns

    pp="participationpointsoptin"
    sr = r.get_subreddit("books")
    wp = sr.get_wiki_page(pp)


    # strip off the user count
    o = re.search("\*\*.*\*\*\n\n?(.*)", wp.content_md, re.DOTALL)
    if o:
        mystr = o.group(1)
    else:
        mystr = wp.content_md

    # get rid of "* "
    mystr = mystr.replace("* ", "")

    # add new users
    optIns = mystr.split()













# get wayr
#   get 2nd most recent ama
#   award point for all root comments
#   log title - wayr-date-post id
#       1st line: url, title
#       username - http://www.reddit.com/comments/TID/_/CID
#   data - data['username'][generated permalink]


#==============================================================
def getWayr (r):
    """
        1) Get the 2nd most recent WAYR thread (last week's).  The most recent one is still active.
        2) loop thru comments, save non-deleted, non-removed comments.
        3) log results in /r/BooksAwardsLog
    """

    global users
    global xtotals
    global nextOAuthUpdate
    global count

    # get 2nd most recent wayr
    srch = r.search("flair:weeklythread title:\"what books are you reading\"", sort="new", subreddit="books", period="month")
    first = True
    for x in srch:
        if first:
            first = False
            continue
        break


    # save the thread ID and the thread title
    wayrFullname = x.fullname
    wayrTitle = x.title

    print("WAYR: get_info")
    info = r.get_info(thing_id=wayrFullname)
    info.replace_more_comments()
    comments=info.comments
    print ("WAYR: running")

    ok = True
    print("scan: ***************** number of comments = %s" % len(comments))

    for c in comments:

        # refresh oauth if it's close to an hour
        if time.time() > nextOAuthUpdate:
            sdsOAuth2Util.refresh(r, MYUSERNAME)
            nextOAuthUpdate = time.time() + (45*60)


        # ignore comments that are a week old.  they should be using the new thread
        if (c.created_utc - info.created_utc) > (60*60*24*7):
            # print ("\nThis is too old (%s)" % c.permalink)
            continue

        # ignore mod distinguished comments
        if c.distinguished:
            continue

        # if the comment is deleted, author will be blank
        if c.author and c.author.name:
            count += 1
            print ("%d " % (count), end="")
            sys.stdout.flush()

            if c.author.name not in users:
                users[c.author.name], xtotals[c.author.name] = newUser()

            # wayrData[c.author.name] = "https://www.reddit.com/comments/%s/_/%s" % (wayrFullname[3:], c.id)
            users[c.author.name]['wayr'] = "https://www.reddit.com/comments/%s/_/%s" % (wayrFullname[3:], c.id)
            xtotals[c.author.name]['wayr'] = 1


    txt="###### %s\n###### http://redd.it/%s \n###### %d\n---\n" % (wayrTitle, wayrFullname[3:], count)
    for i in users:
        if users[i]['wayr']:
            txt += "* [%s](%s)\n" % (i.replace("_", "\_"), users[i]['wayr'])

    r.submit("booksawardslog", "WAYR-%s-%s" % (CURRENTDATE, wayrFullname[3:]), text=txt)
    print("\nWAYR: Done")



#==============================================================
def getRec(r):
    """
        1) There are two valid "recommendation threads.
            From last week's thread, get the comments staring from last monday 12amGMT
            to thread post time+one week.
            From this week's thread, get the comments from the thread's post time
            to this monday 12amGMT.

        2) Get comments that are replies to requests for recommendation.  Those will be
            comments that reply to a root comment.

        3) log results in /r/BooksAwardsLog


    """

    global users
    global xtotals
    global nextOAuthUpdate
    global count

    # update oauth token
    if time.time() > nextOAuthUpdate:
        sdsOAuth2Util.refresh(r, MYUSERNAME)
        nextOAuthUpdate = time.time() + (45*60)

    print("\nStarting REC")
    recThreadList=[]
    # get the two most recent rec threads (within the time window)
    srch = r.search("flair:weeklythread title:\"weekly recommendation\"", sort="new", subreddit="books", period="month")
    for x in srch:

        if x.created_utc < mostRecentMondayUTC:
            recThreadList.append(x)
            print("REC: " + x.title)

            if len(recThreadList) == 2:
                break

    for x in range(2):
        recFullname = recThreadList[x].fullname
        print("\nREC: get_info " + recThreadList[x].title)
        info = r.get_info(thing_id=recFullname)
        info.replace_more_comments()
        comments=info.comments
        print ("REC: running %d" % (x + 1))

        if x == 0:

            # we're running the most recent rec thread, so we want all comments from
            # start-of-thread until monday 12am utc
            startTimeLimit = info.created_utc
            endTimeLimit = mostRecentMondayUTC

        else:

            # we're running the previous rec thread so we want all comments from
            # one week ago (monday 12am utc) until the start of the next rec thread (thurs 9am utc)
            startTimeLimit = previousMondayUTC
            endTimeLimit = info.created_utc + (60*60*24*7)



        print("scan: ***************** number of comments = %s" % len(comments))

        for c in comments:

            # update oauth token
            if time.time() > nextOAuthUpdate:
                sdsOAuth2Util.refresh(r, MYUSERNAME)
                nextOAuthUpdate = time.time() + (45*60)

            # ignore mod distinguished comments
            if c.distinguished:
                continue

            # We only want replies to ROOT comments.  Ignore a comment if it's not ROOT
            if not c.is_root:
                print("Found a non root comment (%s)" % c.permalink)
                continue

            # loop thru the replies to a ROOT comment
            for reply in c.replies:

                # we should not be getting a MoreComments object.  Ignore if found
                if isinstance(reply, praw.objects.MoreComments):
                    print("\nFOUND MORE COMMENTS")
                    #moreComments = reply.comments(update=True)
                    #recData = doMoreComments(recData, moreComments, c.fullname, wayrFullname[3:])
                    continue

                # This reply's parent ID should be the ROOT comment ID
                # and verify the reply hasn't been deleted
                if reply.parent_id == c.fullname and reply.author and reply.author.name:

                    # ignore mod distinguished comments
                    if reply.distinguished:
                        continue

                    # verify the comment is in the time window
                    if reply.created_utc > startTimeLimit and reply.created_utc < endTimeLimit:

                        # if a new author, set the data type as a 'list'
                        if reply.author.name not in users:
                            # recData[reply.author.name] = []
                            users[reply.author.name], xtotals[reply.author.name] = newUser()

                        count += 1
                        print ("%d " % (count), end="")
                        sys.stdout.flush()
                        # recData[reply.author.name].append("https://www.reddit.com/comments/%s/_/%s" % (recFullname[3:], reply.id))
                        users[reply.author.name]['rec'].append("https://www.reddit.com/comments/%s/_/%s" % (recFullname[3:], reply.id))
                        xtotals[reply.author.name]['rec'] += 1



    txt="###### %s\n###### http://redd.it/%s \n###### %d\n---\n" % ("Recommendation Threads", recFullname[3:], count)
    for i in users:
        if len(users[i]['rec']) > 0:
            txt += "* [**%s**](/u/%s) " % (i.replace("_", "\_"), i)
            for j in users[i]['rec']:
                txt += "[Link](%s) " % (j)
            txt += "\n"

    r.submit("booksawardslog", "REC <%s> %s" % (CURRENTDATE, recFullname[3:]), text=txt)
    print("\nREC: Done")




# get new
#   get new posts < monday 12am gmt && > week ago monday 12am GMT
#   get all comments (root and not root) if made within 60 minutes of post datetime
#   only get replies if root comment is not within time
#==============================================================
def getReplyData (replies, startTime):

    global users
    global xtotals
    global count
    global nextOAuthUpdate

    for c in replies:
        if (c.created_utc - startTime) > (60*60):
            #print ("\nThis is too old (%s)" % c.permalink)
            print (" X ", end=""); sys.stdout.flush()
            continue
        if c.distinguished:
            continue
        if c.author and c.author.name:
            count += 1
            print ("%d " % (count), end=""); sys.stdout.flush()

            if c.author.name not in users:
                users[c.author.name], xtotals[c.author.name] = newUser()
                #newData[c.author.name] = {}
            #newData[c.author.name][c.link_id] = "https://www.reddit.com/comments/%s/_/%s" % (c.link_id[3:], c.id)

            if c.link_id not in users[c.author.name]['new']:
                xtotals[c.author.name]['new'] += 1
                users[c.author.name]['new'][c.link_id] = "https://www.reddit.com/comments/%s/_/%s" % (c.link_id[3:], c.id)

        if c.replies:
            getReplyData(c.replies, startTime)



#==============================================================
def getCommentsFromPost (r, post):

    global users
    global xtotals
    global count
    global nextOAuthUpdate

    info = r.get_info(thing_id=post.fullname)
    info.replace_more_comments()
    comments=info.comments

    t = datetime.datetime.utcfromtimestamp(info.created_utc)
    print("\ngetCommentsFromPost: %s  (%d-%d-%d)" % (post.short_link, t.year, t.month, t.day))
    for c in comments:

        if time.time() > nextOAuthUpdate:
            print("\nRefreshing OAuth token\n")
            sdsOAuth2Util.refresh(r, MYUSERNAME)
            nextOAuthUpdate = time.time() + (45*60)

        if (c.created_utc - info.created_utc) > (60*60):
            #print ("\nThis is too old (%s)" % c.permalink)
            print (" X ", end=""); sys.stdout.flush()
            continue
        if c.distinguished:
            continue
        if c.author and c.author.name:
            count += 1
            print ("%d " % (count), end=""); sys.stdout.flush()

            if c.author.name not in users:
                #newData[c.author.name] = {}
                users[c.author.name], xtotals[c.author.name] = newUser()

            if c.link_id not in users[c.author.name]['new']:
                xtotals[c.author.name]['new'] += 1
                users[c.author.name]['new'][c.link_id] = "https://www.reddit.com/comments/%s/_/%s" % (post.fullname[3:], c.id)

        if c.replies:
            getReplyData(c.replies, info.created_utc)





#==============================================================
def getNew (r):

    global users
    global xtotals
    global count
    global nextOAuthUpdate

    print ("Week range: %d - %d" % (int(mostRecentMondayUTC), int(previousMondayUTC)))
    print ("Week range: %s - %s" % (datetime.datetime.utcfromtimestamp(mostRecentMondayUTC), datetime.datetime.utcfromtimestamp(previousMondayUTC)))

    # get all posts between 1 week ago monday and most recent monday
    sr = r.get_subreddit("books")
    newposts = sr.get_new(limit=1000)
    postList = []
    print("getNew: Getting one week of posts")
    for x in newposts:
        postauthor = "[deleted]"
        if x.author and x.author.name:
            postauthor = x.author.name

        if x.created_utc > mostRecentMondayUTC:
            continue

        if x.created_utc < previousMondayUTC:
            break

        count += 1
        postList.append(x)

    print("getNew: Got %d posts" % count)

    for x in postList:
        getCommentsFromPost(r, x)


    part = 0
    thiscount = 0
    txt=""
    postCnt = 0

    for i in users:
        if len(users[i]['new']) > 0:
            postCnt += 1

            if i in optIns:
                optInPerson = "XXX"
            else:
                optInPerson = ":::"

            txt += "* [**%s**](/u/%s) %s " % (i.replace("_", "\_"), i, optInPerson)
            for j in users[i]['new']:
                txt += "[Link](%s) " % (users[i]['new'][j])
            txt += "\n"

        if postCnt > 200:
            part += 1
            title = "Points for New Comments Part: %d" % (part)
            r.submit("booksawardslog", title + "[%s]" % (CURRENTDATE), text=txt)
            txt = ""
            postCnt = 0

    print("\nNEW: Done")



# get ama and spotlight
#   get all ama posts for the past seven days
#   all root comments count (just like wayr)

#==============================================================
def getAMA (r):
    global users
    global xtotals
    global count
    global nextOAuthUpdate
    global mostRecentMondayUTC
    global previousMondayUTC


    print("\nAMA: Started")

    # get AMA posts
    amaList = []
    txt=""
    srch = r.search("flair:ama", sort="new", subreddit="books", period="month")
    for x in srch:

        if x.created_utc > mostRecentMondayUTC:
            continue

        if x.created_utc < previousMondayUTC:
            break

        amaList.append(x)

    print ("Found %d AMA posts" % (len(amaList)))

    for x in amaList:
        print("\n* Working on: " + x.title)
        txt += x.title + "\n\n"

        print("AMA: get_info")
        info = r.get_info(thing_id=x.fullname)
        info.replace_more_comments()
        comments=info.comments
        print ("AMA: running")

        for c in comments:

            if time.time() > nextOAuthUpdate:
                print("\nRefreshing OAuth token\n")
                sdsOAuth2Util.refresh(r, MYUSERNAME)
                nextOAuthUpdate = time.time() + (45*60)

            if c.created_utc > mostRecentMondayUTC:
                print ("\nThis is too old (%s)" % c.permalink)
                continue
            if c.distinguished:
                continue

            if c.author and c.author.name:
                if c.author.name not in users:
                    users[c.author.name], xtotals[c.author.name] = newUser()

                count += 1
                print ("%d " % (count), end="")
                sys.stdout.flush()

                if c.link_id not in users[c.author.name]['ama']:
                    xtotals[c.author.name]['ama'] += 1
                    users[c.author.name]['ama'][c.link_id] = "https://www.reddit.com/comments/%s/_/%s" % (c.link_id[3:], c.id)


    txt += "---\n\n"
    cnt = 0
    part = 0
    for i in users:

        if len(users[i]['ama']) == 0:
            continue

        cnt += 1
        txt += "* [%s](/u/%s) ::: " % (i.replace("_", "\_"), i)

        for j in users[i]['ama']:
            txt += "[link](%s) " % (users[i]['ama'][j])

        txt += "\n"

        if cnt > 200:
            part += 1
            cnt = 0
            r.submit("booksawardslog", "AMAs [%s] part %d" % (CURRENTDATE, part), text=txt)
            txt = ""

    if txt:
        r.submit("booksawardslog", "AMAs [%s] part %d" % (CURRENTDATE, part+1), text=txt)

    print("\nAMA: Finished")


#==============================================================
def results (weekNumber, monday):

    print ("\nStarting TOTALS")

    onePointers = []

    for x in xtotals:
        xtotals[x]['total'] = xtotals[x]['wayr'] + xtotals[x]['rec'] + xtotals[x]['new'] + xtotals[x]['ama']

    # filename format:
    #   weeknumber-year-month-day-totals.json

    fname = "%d-%d-%d-%d-totals.json" % (weekNumber, monday.year, monday.month, monday.day)
    with open(fname, 'w') as fp:
        json.dump(xtotals, fp)
    fp.close()

    for x in previousTotals:
        if x in xtotals:
            xtotals[x]['ama']  += previousTotals[x]['ama']
            xtotals[x]['new']  += previousTotals[x]['new']
            xtotals[x]['wayr'] += previousTotals[x]['wayr']
            xtotals[x]['rec']  += previousTotals[x]['rec']
            xtotals[x]['total']+= previousTotals[x]['total']
        else:
            xtotals[x] = copy.deepcopy(previousTotals[x])


    fname = "alltotals.json"
    with open(fname, 'w') as fp:
        json.dump(xtotals, fp)
    fp.close()

    totals = OrderedDict(sorted(xtotals.items(), key=lambda kv: kv[1]['total'], reverse=True))

    txt  = "User|WAYR|REC|AMA|NEW|Total\n"
    txt += "---|---|---|---|---|---\n"

    notOptInTxt  = "User|WAYR|REC|AMA|NEW|Total\n"
    notOptInTxt += "---|---|---|---|---|---\n"

    if weekNumber > 11:
        threshold = 3 * 12
    else:
        threshold = 3 * (weekNumber+1)

    print("\nThreshold is %d" % (threshold))
    for i in totals:
        if totals[i]['total'] < threshold:
            onePointers.append(i)

        if i in optIns:
            setFlair(r, i, str(totals[i]['total']))

            if totals[i]['total'] > threshold:
                txt += "%s|%d|%d|%d|%d|%d\n" % (i.replace("_", "\_"),
                                                totals[i]['wayr'],
                                                totals[i]['rec'],
                                                totals[i]['ama'],
                                                totals[i]['new'],
                                                totals[i]['total'])

        else:
            if totals[i]['total'] > threshold:
                notOptInTxt += "%s|%d|%d|%d|%d|%d\n" % (i.replace("_", "\_"),
                                                totals[i]['wayr'],
                                                totals[i]['rec'],
                                                totals[i]['ama'],
                                                totals[i]['new'],
                                                totals[i]['total'])



#    txt += "\n\n---\n\nOne Pointers:\n\n"
#    for i in onePointers:
#        txt += "%s " % (i.replace("_", "\_"))

    txt += "\n"
    notOptInTxt += "\n"

    sr = r.get_subreddit("booksawardslog")
    sr.edit_wiki_page("test", txt)
    sr.edit_wiki_page("test1", notOptInTxt)

    print("Totals Finished")


#==============================================================
if __name__=='__main__':


    testing = False
    initialRunDate = calendar.timegm(datetime.date(2015,8,24).timetuple())
    weekNumber = 0

    if len(sys.argv) < 2:
        print ("Not testing or running.  You know what to do.\n")
        quit()

    if sys.argv[1] == "testing":
        testing = True
    if sys.argv[1] != "running" and not testing:
        print ("Not testing or running.  You know what to do.\n")
        quit()

    r = init()
    if time.time() > nextOAuthUpdate:
        sdsOAuth2Util.refresh(r, MYUSERNAME)
        nextOAuthUpdate = time.time() + (45*60)

    getOptIns(r)

    # get the time window
    # get the most recent monday, 12am UTC
    # what's today?  0=monday, 6=sunday
    weekday = datetime.date.weekday(datetime.date.today())

    # subtract weekday from todays date to get most recent monday
    monday = datetime.date.today() - datetime.timedelta(days=weekday)

    # get the 12am UTC for the most recent monday
    mostRecentMondayUTC = calendar.timegm(monday.timetuple())

    # get the previous monday - one week ago
    previousMondayUTC = (mostRecentMondayUTC - (60*60*24*7))

    if testing:
        previousMondayUTC = (mostRecentMondayUTC - (60*60*24*2))

    print ("Week range: %d - %d" % (int(mostRecentMondayUTC), int(previousMondayUTC)))
    print ("Week range: %s - %s" % (datetime.datetime.utcfromtimestamp(mostRecentMondayUTC), datetime.datetime.utcfromtimestamp(previousMondayUTC)))

    # get the totals from previous weeks
    weekNumber = int((mostRecentMondayUTC - initialRunDate)/int(60*60*24*7))
    #print("mostRecentMondayUTC: %d  initialRunDate: %d  weekNumber: %d" % (mostRecentMondayUTC, initialRunDate, weekNumber))
    calcPreviousTotals(weekNumber)

    getWayr(r)
    getRec(r)
    getNew(r)
    getAMA(r)
    print ("Count: %d" % count)
    results(weekNumber, monday)
    quit()


