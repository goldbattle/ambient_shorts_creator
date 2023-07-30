# Import general libraries
import sys
import json
import signal
import string
import requests

# global variable which sets if we should terminate
terminated_requested = False


def signal_handler(sig, frame):
    global terminated_requested
    terminated_requested = True
    print('terminate requested!!!!!')


def setup_signal_handle():
    signal.signal(signal.SIGINT, signal_handler)

def webvtt_time_string(seconds):
    minutes = seconds / 60
    seconds = seconds % 60
    hours = int(minutes / 60)
    minutes = int(minutes % 60)
    return '%i:%02i:%06.3f' % (hours, minutes, seconds)

def get_valid_filename(filename):
    valid_chars = "-_%s%s" % (string.ascii_letters, string.digits)
    filename = filename.lower().replace(' ', '_')
    return ''.join(c for c in filename if c in valid_chars)

def send_pushover_message(auth, text):
    if auth["pushover_enable"]:
        payload = {"message": text, "user": auth["pushover_user_key"], "token": auth["pushover_app_key"] }
        resp = requests.post('https://api.pushover.net/1/messages.json', data=payload, headers={'User-Agent': 'Python'})
        if not resp.ok:
            print("[error]: bad response from pushover: ")
            print(resp)
