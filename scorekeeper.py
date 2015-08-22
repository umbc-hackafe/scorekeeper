import requests
from requests_oauthlib import OAuth1Session
import flask
import json

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

twitter = OAuth1Session(
    TWITTER_APP_KEY,
    client_secret=TWITTER_APP_KEY_SECRET,
    resource_owner_key=TWITTER_ACCESS_TOKEN,
    resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET
)

api = flask.Flask(__name__)

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

def do_tweet(person, reason):
    if reason:
        if reason.lower().startswith("for "):
            reason = reason[4:]
    r = twitter.post("https://api.twitter.com/1.1/statuses/update.json",
                      data={"status": "Crazy point to {}: {}".format(person.title(), reason)})
    print("Status:", r.text)
    print("Person", person, "\nReason", reason)

@api.route('/', methods=['POST', 'GET'])
def alexa():
    data = flask.request.data
    if data:
        data = json.loads(data.decode('UTF-8'))
    else:
        raise ValueError("Invalid arguments; no data")

    with open('/tmp/alexa_test', 'a+') as f:
        print("Data  : " + json.dumps(data, indent=2, separators=(',', ': ')) + '\n')

    request = data["request"]
    req_type = request["type"]
    session_id = data["session"]["sessionId"]

    attrs = {"person": None, "reason": None}
    attrs.update(data["session"].get("attributes", {}))

    if req_type == "LaunchRequest":
        resp = dict(BASE_RESPONSE)
        resp["response"] = {
            "shouldEndSession": False
        }
        return flask.jsonify(resp)
    elif req_type == "SessionEndedRequest":
        resp = dict(BASE_RESPONSE)
        resp["response"] = {
            "shouldEndSession": True
        }
        return flask.jsonify(resp)
    elif req_type == "IntentRequest":
        # TODO validate timestamp
        if "intent" in request:
            intent = request["intent"]
            name = intent['name']
            slots = intent['slots']

            if name == "Point" or name == "ConfirmPerson":
                for slot in slots.values():
                    slot_name = slot["name"]
                    slot_val = slot.get("value", None)

                    if slot_name == "Person":
                        attrs["person"] = slot_val
                    elif slot_name == "Reason":
                        attrs["reason"] = slot_val

                if attrs["reason"] and attrs["person"]:
                    resp = dict(BASE_RESPONSE)
                    resp["response"] = {
                        "outputSpeech": {
                            "type": "PlainText",
                            "text": "Should I give {} a point for {}?".format(
                                attrs["person"], attrs["reason"])
                        },
                        "shouldEndSession": False
                    }
                    resp["sessionAttributes"] = attrs
                    return flask.jsonify(resp)
                elif not attrs["person"]:
                    print("Didn't get a name, reprompting")
                    resp = dict(BASE_RESPONSE)
                    resp["response"] = {
                            "outputSpeech": {
                                "type": "PlainText",
                                "text": "Who should I give a point to?"
                            },
                        "shouldEndSession": False
                    }
                    resp["sessionAttributes"] = attrs
                    return flask.jsonify(resp)
                elif not attrs["reason"]:
                    print("Prompting for a reason")
                    resp = dict(BASE_RESPONSE)
                    resp["response"] = {
                        "outputSpeech": {
                            "type": "PlainText",
                            "text": "What's the reason?"
                        },
                        "shouldEndSession": False
                    }
                    resp["sessionAttributes"] = attrs
                    return flask.jsonify(resp)
            elif name == "GiveReason":
                for slot in slots.values():
                    slot_name = slot["name"]
                    slot_val = slot.get("value", None)

                    if slot_name == "Reason":
                        attrs["reason"] = slot_val
                if attrs["reason"] and attrs["person"]:
                    resp = dict(BASE_RESPONSE)
                    resp["response"] = {
                        "outputSpeech": {
                            "type": "PlainText",
                            "text": "Should I give {} a point for {}?".format(
                                attrs["person"], attrs["reason"])
                        },
                        "shouldEndSession": False
                    }
                    resp["sessionAttributes"] = attrs
                    return flask.jsonify(resp)
                elif not attrs["person"]:
                    print("Didn't get a name, reprompting")
                    resp = dict(BASE_RESPONSE)
                    resp["response"] = {
                            "outputSpeech": {
                                "type": "PlainText",
                                "text": "Who should I give a point to?"
                            },
                        "shouldEndSession": False
                    }
                    resp["sessionAttributes"] = attrs
                    return flask.jsonify(resp)
                elif not attrs["reason"]:
                    print("Prompting for a reason")
                    resp = dict(BASE_RESPONSE)
                    resp["response"] = {
                        "outputSpeech": {
                            "type": "PlainText",
                            "text": "What's the reason?"
                        },
                        "shouldEndSession": False
                    }
                    resp["sessionAttributes"] = attrs
                    return flask.jsonify(resp)
            elif name == "ConfirmPoint":
                for slot in slots.values():
                    slot_name = slot["name"]
                    slot_val = slot.get("value", None)
                    confirmed = False

                    if slot_name == "Confirmed":
                        confirmed = (slot_val.lower() == "yes")

                    if confirmed:
                        add_point(attrs["person"])
                        num_points = points_for(attrs["person"])
                        resp = dict(BASE_RESPONSE)
                        resp["response"] = {
                            "outputSpeech": {
                                "type": "PlainText",
                                "text": "{} now has {} point{}!".format(attrs["person"], num_points, "" if num_points == 1 else "s")
                            },
                        "shouldEndSession": True
                        }
                        do_tweet(attrs["person"],
                                 attrs["reason"])
                        resp["sessionAttributes"] = attrs
                        return flask.jsonify(resp)
                    else:
                        resp = dict(BASE_RESPONSE)
                        resp["response"] = {
                            "shouldEndSession": True
                        }
                        resp["sessionAttributes"] = attrs
                        return flask.jsonify(resp)

    return {'args': repr(args), 'kwargs': repr(kwargs)}

get_points()
api.run('0.0.0.0', port=80, debug=True)
