import requests
import json
import re
import time
import base64
import matplotlib.pyplot as plot

####### SETTING VARIABLES ##########
_RELOAD = False # If true, always fetches all messages again

BASE_GROUPME_URL = "https://api.groupme.com/v3/"
# .groupme.env should be a file with the first line being your groupme api token (can be base64 encoded)
with open(".groupme.env") as f:
    token = f.readline().strip()
    try:
        a = bytes(token, "ascii")
        GROUPME_API_TOKEN = str(base64.b64decode(a))[2:-1]
        if not GROUPME_API_TOKEN.isalnum():
            GROUPME_API_TOKEN = token
    except:
        GROUPME_API_TOKEN = token

def bootstrap():
    request_url = BASE_GROUPME_URL + "groups?token=" + GROUPME_API_TOKEN
    r = requests.get(request_url)
    data = json.loads(r.text)["response"]
    new_directory = {group["name"]: group["id"] for group in data}
    with open("dir.txt", "w") as f:
        f.write(json.dumps(new_directory))
    print("Finished setting up.")
# dir.txt should be the json dumped map of group name to group ID
with open("dir.txt") as f:
    GROUP_DIR = json.loads(f.readline().strip())
print_dir = lambda: [print(x) for x in GROUP_DIR.keys()]

############################################################
############### FETCH AND LOAD MESSAGES ####################
############################################################ 
# Fetches all messages given a group id and writes them to a local file
def fetch_all_messages(group_id):
    ret_msgs = []
    new_url = BASE_GROUPME_URL + "groups/" + str(group_id) + "/messages?limit=100&token=" + GROUPME_API_TOKEN

    print(new_url)
    r = requests.get(new_url)
    r_json = json.loads(r.text)
    print(r_json["response"]["messages"][0].keys())

    ret_msgs += r_json["response"]["messages"]

    while r_json["response"]["count"] > 0:
        next_url = new_url + "&before_id=" + ret_msgs[-1]["id"]
        print(next_url)
        r = requests.get(next_url)
        if not r.text:
            break
        r_json = json.loads(r.text)
        ret_msgs += r_json["response"]["messages"]

    with open("messages/all_messages_for_" + str(group_id) + ".txt", "w") as f:
        f.write(json.dumps(ret_msgs))
    return ret_msgs

# Fetches all messages for all groups and writes them to local files
def fetch_all_messages_for_all_groups():
    all_messages = []
    for g_id in GROUP_DIR.values():
        all_messages += fetch_all_messages(g_id)
    with open("messages/all_messages_for_all.txt", "w") as f:
        f.write(json.dumps(all_messages))
    return all_messages

# Fetches all messages given a group name by looking up the group ID from a locally cached directory
def fetch_messages_from_name(group_name):
    return fetch_all_messages(GROUP_DIR[group_name])

# Loads all messages from a saved file generated by fetch_all_messages
# TODO: BUG, it seems like duplicate messages get loaded.
def load_messages(group_id, load_recent=_RELOAD):
    all_messages = []
    with open("messages/all_messages_for_" + str(group_id) + ".txt") as f:
        for line in f:
            all_messages += json.loads(line)

    if load_recent and group_id != "all":
        new_url = BASE_GROUPME_URL + "groups/" + str(group_id) + "/messages?limit=100&token=" + GROUPME_API_TOKEN + "&after_id=" + all_messages[0]["id"]
        # print(new_url)
        r = requests.get(new_url)
        r_json = json.loads(r.text)
        if len(r_json["response"]["messages"]) > 0:
            all_messages = r_json["response"]["messages"] + all_messages
            with open("messages/all_messages_for_" + str(group_id) + ".txt", "w") as f:
                f.write(json.dumps(all_messages))
            print("New messages for this group!")
        else:
            print("No new messages")

    return all_messages

def load_all_messages(load_recent=_RELOAD):
    if load_recent:
        all_messages = []
        for g_id in GROUP_DIR.values():
            all_messages += load_messages(g_id, True)
        with open("messages/all_messages_for_all.txt", "w") as f:
            f.write(json.dumps(all_messages))
        return all_messages
    else:
        with open("messages/all_messages_for_all.txt") as f:
            all_messages = []
            for line in f:
                all_messages += json.loads(line)
        return all_messages

# Loads all messages from a saved file by looking up the group ID from a locally cached directory
def load_from_group_name(group_name):
    return load_messages(GROUP_DIR[group_name])

###################################################################
####################### UTILITY FUNCTIONS #########################
###################################################################
# Given a dictionary mapping to integers, prints the items sorted in descending order based on value
def sort_print(mapthing):
    print(sorted(list(mapthing.items()), key=lambda x:-x[1]))

# Given a dictionary mapping to integers, prints the items sorted in descending order line by line
def lps(mapthing):
    for p in sorted(list(mapthing.items()), key=lambda x:-x[1]):
        print(p[0] + ":",  p[1])

# Given an iterable, prints it line by line
def iter_print(listtthing):
    if type(listtthing) is dict:
        for k, v in listtthing.items():
            print(k, v)
    else:
        for item in listtthing:
            print(item)

# Converts unix time into a long string of local time for me (Most likely PT)
def convert_time(epoch_time):
    return time.strftime('%Y-%m-%d - %B %A - %I:%M:%S%p %c', time.localtime(epoch_time))

# Splits a string into a list of words (alphanumeric and single quote)
def word_split(string):
    return [i.lower() for i in re.findall(r"[\w]+", string)]

#################################################################
#################### USER ANALYSIS FUNCTIONS ####################
#################################################################
def aggregate_msg_by_user(group_id, load_recent=_RELOAD):
    all_messages = load_messages(group_id, load_recent)

    users = {}
    for msg in all_messages:
        if msg["name"] in users:
            users[msg["name"]].append(msg)
        else:
            users[msg["name"]] = [msg]

    return users

def count_msg_by_user(group_id, load_recent=_RELOAD):
    users = aggregate_msg_by_user(group_id, load_recent)
    return {i: len(users[i]) for i in users}

def likes_per_user(group_id, load_recent=_RELOAD):
    users = aggregate_msg_by_user(group_id, load_recent)
    return {user: sum([len(msg["favorited_by"]) for msg in users[user]]) for user in users}

def likes_per_message_per_user(group_id, load_recent=_RELOAD):
    users = aggregate_msg_by_user(group_id, load_recent)
    likes_per_user = {user: sum([len(msg["favorited_by"]) for msg in users[user]]) for user in users}
    return {user: likes_per_user[user] / len(users[user]) for user in users}


#################################################################
#################### TIME ANALYSIS FUNCTIONS ####################
#################################################################
def time_split(group_id, load_recent=_RELOAD):
    all_messages = load_messages(group_id, load_recent)

    text_and_time = []
    for msg in all_messages:
        converted_msg = {"text": msg["text"]}
        converted_msg["time"] = convert_time(msg["created_at"])
        converted_msg["hour"] = int(time.strftime('%H', time.localtime(msg["created_at"])))
        text_and_time.append(converted_msg)

    return text_and_time

def count_by_hour(group_id, load_recent=_RELOAD):
    text_and_time = time_split(group_id, load_recent)

    hour_counts = {i: 0 for i in range(24)}
    for msg in text_and_time:
        if msg["hour"] in hour_counts:
            hour_counts[msg["hour"]] += 1
        else:
            hour_counts[msg["hour"]] = 1

    return hour_counts

def display_hourly_usage(group_id, load_recent=_RELOAD):
    hourly_counts = count_by_hour(group_id, load_recent)

    ordered_by_hour = sorted(list(hourly_counts.items()), key=lambda x: x[0])
    plot.plot([i[0] for i in ordered_by_hour], [i[1] for i in ordered_by_hour])
    plot.show()
    iter_print(ordered_by_hour)

#################################################################
#################### WORD ANALYSIS FUNCTIONS ####################
#################################################################
def word_count(group_id, load_recent=_RELOAD):
    all_messages = load_messages(group_id)

    word_freq = {}
    for msg in all_messages:
        if msg and "text" in msg and msg["text"]:
            words_used = word_split(msg["text"])
            for word in words_used:
                if word in word_freq:
                    word_freq[word] += 1
                else:
                    word_freq[word] = 1

    return word_freq

def most_liked_words(group_id, load_recent=_RELOAD):
    all_messages = load_messages(group_id)

    word_likes = {}
    for msg in all_messages:
        if msg and "text" in msg and msg["text"]:
            words_used = set(word_split(msg["text"]))
            for word in words_used:
                if word in word_likes:
                    word_likes[word] += len(msg["favorited_by"])
                else:
                    word_likes[word] = len(msg["favorited_by"])

    return word_likes

def popular_words_with_info(group_id, load_recent=_RELOAD):
    all_messages = load_messages(group_id)

    word_likes = {}
    word_present = {}
    for msg in all_messages:
        if msg and "text" in msg and msg["text"]:
            words_used = set(word_split(msg["text"]))
            for word in words_used:
                if word in word_likes:
                    word_likes[word] += len(msg["favorited_by"])
                    word_present[word] += 1
                else:
                    word_likes[word] = len(msg["favorited_by"])
                    word_present[word] = 1

    word_freq = word_count(group_id, load_recent)

    return {word + " was used " +str(word_freq[word]) + ", and was liked " + str(word_likes[word]): word_likes[word] / word_present[word] for word in word_present if word_freq[word] > 1}

def popular_words(group_id, load_recent=_RELOAD):
    all_messages = load_messages(group_id)

    word_likes = {}
    word_present = {}
    for msg in all_messages:
        if msg and "text" in msg and msg["text"]:
            words_used = set(word_split(msg["text"]))
            for word in words_used:
                if word in word_likes:
                    word_likes[word] += len(msg["favorited_by"])
                    word_present[word] += 1
                else:
                    word_likes[word] = len(msg["favorited_by"])
                    word_present[word] = 1

    return {word: word_likes[word] / word_present[word] for word in word_present}

##########################################################
#################### USER INTERACTION ####################
##########################################################

# load_all_messages(True)
# lps(likes_per_message_per_user(41805466))
# r = requests.get(BASE_GROUPME_URL + "groups?token=" + GROUPME_API_TOKEN)
# # print(json.loads(r.text))
# for thing in json.loads(r.text)["response"]:
#     print(thing)
# fetch_all_messages_for_all_groups()

# display_hourly_usage(41805466)
# display_hourly_usage("all")
# hourly_counts = count_by_hour("41805466")
# hourly_counts = count_by_hour("all")

# hourly_counts = sorted(list(hourly_counts.items()), key=lambda x: x[0])
# iter_print(hourly_counts)

# thing = load_messages(19259990)
# for msg in thing:
#     if msg and "text" in msg and msg["text"] and "\xa0" in msg["text"]:
#         print(msg)




#   for msg in msg_all:
#       if "created_at" in msg:
#           msg["time"] = convert_time(msg["created_at"])
#           print(msg["time"])



