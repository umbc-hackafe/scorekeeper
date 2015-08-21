import twython
import flask
import json

BASE_RESPONSE = {
    "version": "1",
    "response": {}
}

TWITTER_APP_KEY = 'ntLFB6p6IApzcEECKF4NdHsdJ'
TWITTER_APP_KEY_SECRET = '9AkI8vTZwxPXFrBMzcENZUscp9TEAJyFdXwCVrN3fVFZLifalO' 
TWITTER_ACCESS_TOKEN = '808021956-h3pMy2nfM2afQE6aC8hDTl69bb0JDu2hutYUqdoY'
TWITTER_ACCESS_TOKEN_SECRET = 'RLozX4oMPu7rUpfehHGEv6WZXS8xgbV4RdjjfmgbIgboV'

twitter = twython.Twython(app_key=TWITTER_APP_KEY,
                          app_secret=TWITTER_APP_KEY_SECRET,
                          oauth_token=TWITTER_ACCESS_TOKEN,
                          oauth_token_secret=TWITTER_ACCESS_TOKEN_SECRET)


api = flask.Flask(__name__)

def do_tweet(person, reason):
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

    attrs = data["session"].get("attributes", {})

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
                attrs["person"] = None

                for slot in slots.values():
                    slot_name = slot["name"]
                    slot_val = slot.get("value", None)

                    if slot_name == "Person":
                        attrs["person"] = slot_val
                    elif slot_name == "Reason":
                        attrs["reason"] = slot_val

                if attrs["reason"] == None:
                    attrs["reason"] = "no reason"

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
                else:
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
            elif name == "ConfirmPoint":
                for slot in slots.values():
                    slot_name = slot["name"]
                    slot_val = slot.get("value", None)
                    confirmed = False

                    if slot_name == "Confirmed":
                        confirmed = (slot_val.lower() == "yes")

                    if confirmed:
                        resp = dict(BASE_RESPONSE)
                        resp["response"] = {
                            "outputSpeech": {
                                "type": "PlainText",
                                "text": "Point given to {}".format(attrs["person"])
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

api.run('0.0.0.0', port=80, debug=True)