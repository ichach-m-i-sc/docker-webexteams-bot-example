import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = {'READ_ONLY' : 'https://www.googleapis.com/auth/calendar'}

class CalendarIntegration(object):
    def __init__(self):
        self.calendar = None
    
    def authorize_api(self):
         # Connecting to G Calendar
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token, encoding="utf8")
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES['READ_ONLY'])
                creds = flow.run_console()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.calendar = build('calendar', 'v3', credentials=creds)

    def get_events(self, max_events=100, start_time=0, end_time=None):
        now_utc = datetime.datetime.utcnow().isoformat() + 'Z'
        if not start_time:
            start_time = now_utc
        else:
            start_time = start_time.isoformat() + 'Z'
        if end_time:
            end_time = end_time.isoformat() + 'Z'
        events_result = self.calendar.events().list(calendarId='primary', timeMin=start_time, timeMax=end_time,
                                                maxResults=max_events, singleEvents=True,
                                                orderBy='startTime').execute()
        events = events_result.get('items', [])
        return events

    def add_event(self, start_time, end_time, summary, location = None, description= None):
        start_time_formatted = start_time.isoformat() + 'Z'
        end_time_formatted = end_time.isoformat() + 'Z'
        event_body = {'summary' : summary, 'location' : location,
        'description' : description, 'start' : {'dateTime' : start_time_formatted}, 
        'end': {'dateTime' : end_time_formatted}}
        print(event_body)
        event = self.calendar.events().insert(calendarId='primary', body=event_body).execute()

class CalendarQuery(object):
    @staticmethod
    def next_events(calendar, max_events):
        return calendar.get_events(max_events = max_events)

    @staticmethod
    def tomorrow(calendar):
        tomorrow = datetime.datetime.today().replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
        return calendar.get_events(start_time = tomorrow, end_time = tomorrow + datetime.timedelta(minutes=1439))

    @staticmethod
    def today(calendar):
        today = datetime.datetime.today()
        return calendar.get_events(start_time = today, end_time = today.replace(hour=0, minute=0, second=0) + datetime.timedelta(minutes=1439))

    @staticmethod
    def create_event(calendar):
        pass