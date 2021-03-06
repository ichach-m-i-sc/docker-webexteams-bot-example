#!/usr/bin/env python
#  -*- coding: utf-8 -*-

# 3rd party imports ------------------------------------------------------------
# Flask help can be found here:
# http://flask.pocoo.org/
from __future__ import print_function

from flask import Flask, request
from webexteamssdk import WebexTeamsAPI, Webhook

#required by Calendar API
from calendar_integration import CalendarIntegration, CalendarQuery
import datetime
import pickle
import re
import os.path
import calendar
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#duckduckgo
from duckduckpy import query

from test_text_analysis.ParserICHack import ParserICHack

# local imports ----------------------------------------------------------------
from helpers import (read_yaml_data,
                     get_ngrok_url,
                     find_webhook_by_name,
                     delete_webhook, create_webhook)

flask_app = Flask(__name__)
teams_api = None

def print_events(webhook_obj, events):
    room = teams_api.rooms.get(webhook_obj.data.roomId)
    message = teams_api.messages.get(webhook_obj.data.id)
    person = teams_api.people.get(message.personId)
    email = person.emails[0]
    if not events:
        print('No upcoming events found.')
        teams_api.messages.create(room.id, text='You don\'t have any events.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        dt_start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ')
        start = dt_start.ctime()
        
        print(start, event['summary'])
        teams_api.messages.create(room.id, text='{} {}'.format(start, event['summary']))



# Create a python decorator which tells Flask to execute this method when the "/teamswebhook" uri is hit
# and the HTTP method is a "POST" request. 
@flask_app.route('/teamswebhook', methods=['POST'])
def teamswebhook():

    # Only execute this section of code when a POST request is sent, as a POST indicates when a message
    # has been sent and therefore needs processing.
    if request.method == 'POST':
        json_data = request.json
        print("\n")
        print("WEBHOOK POST RECEIVED:")
        print(json_data)
        print("\n")

        # Pass the JSON data so that it can get parsed by the Webhook class
        webhook_obj = Webhook(json_data)

        # Obtain information about the request data such as room, message, the person it came from 
        # and person's email address. 
        room = teams_api.rooms.get(webhook_obj.data.roomId)
        message = teams_api.messages.get(webhook_obj.data.id)
        person = teams_api.people.get(message.personId)
        email = person.emails[0]

        print("NEW MESSAGE IN ROOM '{}'".format(room.title))
        print("FROM '{}'".format(person.displayName))
        print("MESSAGE '{}'\n".format(message.text))

        # Message was sent by the bot, do not respond.
        # At the moment there is no way to filter this out, there will be in the future
        me = teams_api.people.me()
        if message.personId == me.id:
            return 'OK'
        else:
            pass
        if message.text[:8] == "@answer ":
            query_string = message.text[7:]
            # print(query_string)
            response = query(query_string)
            # print(str(response).encode('utf-8'))
            # print(str(response.abstract_url).encode('utf-8'))
            url = response.abstract_url
            # print(str(response.related_topics[0].url).encode('utf-8'))
            # teams_api.messages.create(room.id, text=response.related_topics[0].text)
            if response.abstract_text:
                teams_api.messages.create(room.id, text=response.abstract_text)
            else:
                teams_api.messages.create(room.id, text=response.related_topics[0].text)
            teams_api.messages.create(room.id, text='Read more: {}'.format(url))
        elif message.text[:10] == "@calendar ":
            if message.text == "@calendar tomorrow":
                events = CalendarQuery.tomorrow(ci)
                print_events(webhook_obj, events)
            elif re.match('@calendar\snext\s\d+', message.text) is not None:
                num_events = int(message.text.rsplit(' ', 1)[1])
                events = CalendarQuery.next_events(ci, num_events)
                print_events(webhook_obj, events)
            elif message.text == "@calendar next":
                events = CalendarQuery.next_events(ci, 10)
                print_events(webhook_obj, events)
            elif message.text == "@calendar today":
                events = CalendarQuery.today(ci)
                print_events(webhook_obj, events)
        elif message.text[:13] == "@availability":
            if message.text == "@availability":
                best_dates, people_that_agree = parser.get_best_date()
                if not best_dates:
                    teams_api.messages.create(room.id, text='There is no availability information available.')
                else:
                    teams_api.messages.create(room.id, text='The best day for a meeting is: {}'.format(str(best_dates[0])))
                    if people_that_agree:
                        teams_api.messages.create(room.id, text='The following teammates confirmed they are available: {}'.format(', '.join(list(set(people_that_agree)))))

            if message.text == "@availability reset":
                parser.reset_date()
            if re.match('@availability\screate\s-start\s\d+\s-end\s\d+', message.text) is not None:
                parts = message.text.split(' ')
                start_time = datetime.datetime.combine(parser.get_best_date()[0][0], datetime.datetime.min.time()) + datetime.timedelta(hours = int(parts[3]))
                end_time = datetime.datetime.combine(parser.get_best_date()[0][0], datetime.datetime.min.time()) + datetime.timedelta(hours = int(parts[5]))
                existing_events = ci.get_events(start_time=start_time, end_time=end_time)
                print(start_time)
                print(end_time)
                if existing_events:
                    teams_api.messages.create(room.id, text='An event already exists at that time.')
                    print_events(webhook_obj,existing_events)
                else:
                    ci.add_event(summary = "Meeting by @calendar_bot", start_time = start_time, end_time = end_time)
                    teams_api.messages.create(room.id, text='Meeting setup succesful.')

        else:
            print(parser.extract(message.text))
            parser.manage_text(message.text)
            print(parser.get_best_date())

if __name__ == '__main__':

    ci = CalendarIntegration()
    ci.authorize_api()

    parser = ParserICHack()

    # Read the configuration that contains the bot access token
    config = read_yaml_data('/opt/config/config.yaml')['hello_bot']
    teams_api = WebexTeamsAPI(access_token=config['teams_access_token'])

    # Get some required NGrok information
    ngrok_url = get_ngrok_url()

    # Define the name of webhook
    webhook_name = 'hello-bot-wb-hook'

    # Find any existing webhooks with this name and if this already exists then delete it
    dev_webhook = find_webhook_by_name(teams_api, webhook_name)
    if dev_webhook:
        delete_webhook(teams_api, dev_webhook)

    # Create a new teams webhook with the name defined above 
    create_webhook(teams_api, webhook_name, ngrok_url + '/teamswebhook')

    # Host flask web server on port 5000
    flask_app.run(host='0.0.0.0', port=5000)
