import threading
import requests
from requests_oauthlib import OAuth1Session
import pyalexa
import flask
import json
import sign
import time

BASE_RESPONSE = {
    "version": "1",
    "response": {}
}

with open(".scorekeeper_keys") as f:
    keys = json.load(f)

TWITTER_APP_KEY = keys["api_key"]
TWITTER_APP_KEY_SECRET = keys["api_secret"]
TWITTER_ACCESS_TOKEN = keys["access_token"]
TWITTER_ACCESS_TOKEN_SECRET = keys["token_secret"]

APP_ID = keys["app_id"]

twitter = OAuth1Session(
    TWITTER_APP_KEY,
    client_secret=TWITTER_APP_KEY_SECRET,
    resource_owner_key=TWITTER_ACCESS_TOKEN,
    resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET
)

api = flask.Flask(__name__)

skill = pyalexa.Skill(app_id=APP_ID)

SIGN = sign.Sign("192.168.4.105", 8800)

def get_points():
    points = {}
    try:
        with open('.points') as p:
            points = json.load(p)
    except FileNotFoundError:
        with open('.points', 'w') as p:
            json.dump({}, p)
    return points

def add_point(person):
    points = get_points()
    person = person.lower()
    if person in points:
        points[person] += 1
    else:
        points[person] = 1

    with open('.points', 'w') as p:
        json.dump(points, p)

def points_for(person):
    return get_points().get(person.lower(), 0)

def trim_reason(reason):
    if reason and reason.lower().startswith("for "):
        reason = reason[4:]
    return reason

def do_tweet(person, reason):
    r = twitter.post("https://api.twitter.com/1.1/statuses/update.json",
                      data={"status": "Crazy point to {}: {}".format(person.title(), trim_reason(reason))})
    print("Status:", r.text)
    print("Person", person, "\nReason", reason)

def _display_thread():
    time.sleep(2.5)
    texts = ["{}: {}".format(*i) for i in
             sorted(get_points().items(), key=lambda n:n[1], reverse=True)]

    for text in texts:
        SIGN.new_message(text, priority=1.8, lifetime=1.8)
        time.sleep(1.75)

def do_display():
    threading.Thread(target=_display_thread).start()

@skill.launch
def launch(request):
    descs = ["{} has {} point{}".format(k, v, '' if v == 1 else 's') for (k, v) in
             sorted(get_points().items(), key=lambda n:n[1], reverse=True) if v]

    pretty_scores = "There are no scores yet."
    if len(descs) == 1:
        pretty_scores = ';'.join(descs)
    elif len(descs) > 1:
        pretty_scores = ';'.join(descs[:-1]) + '; and ' + descs[-1]

    do_display()

    return request.response(end=True, speech="Here is the Hackaf\xE9 score breakdown: " + pretty_scores)

@skill.end
def end(request):
    return request.response(end=True)

@skill.intent("Point", "ConfirmPerson", "GiveReason")
def main(request):
    request.save_slots()

    # Save each slot if it's 
    if not request.data().get("Person"):
        return request.response("Who should I give a point to?")

    if not request.data().get("Reason"):
        return request.response("What's the reason?")

    return request.response("Should I give {} a point for {}?".format(
        request.data().get("Person"),
        trim_reason(request.data().get("Reason"))))

@skill.intent("ConfirmPoint")
def confirm_point(request):
    if request.data().get("Confirmed").lower() in (
            "yes", "yeah", "ok", "okay", "yep", "yup"):

        person = request.data().get("Person")
        reason = request.data().get("Reason")
        num_points = points_for(person)

        do_tweet(person, reason)

        return request.response("{} now has {} point{}!".format(person, num_points, "" if num_points == 1 else "s"), end=True)
    else:
        return request.response(end=True)

@skill.intent("Score")
def score(request):
    person = request.intent.slots.get("Person")
    if person:
        add_point(person)
        num_points = points_for(person)
        return request.response("{} now has {} point{}!".format(person, num_points, "" if num_points == 1 else "s"), end=True)
    return request.response("Whose score do you want to hear?")

get_points()

api.add_url_rule('/', 'pyalexa', skill.flask_target, methods=['POST'])
api.run('0.0.0.0', port=80, debug=True)
