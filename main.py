import os
import pickle
import datetime
import boto3
import time
import json

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dateutil.parser import parse

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TOKEN_FILE = 'sec/token.pickle'


def load_aws_credentials():
    with open('sec/config.json', 'r') as file:
        return json.load(file)


def load_google_credentials():
    creds = None
    # First, try to load existing credentials from the token file
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, then either refresh or acquire new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('sec/client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        save_google_credentials(creds)

    return creds


def save_google_credentials(creds):
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)


def create_sns():
    sns_client = boto3.client('sns', region_name='us-east-2')
    return sns_client


def get_date_tomorrow():
    return datetime.date.today() + datetime.timedelta(days=1)


def publish_aws_message(message, date):
    config = load_aws_credentials()
    client = create_sns()

    topic_arn = config['SNS_TOPIC_ARN']
    response = client.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=date
    )
    print(response)


def get_calendar_events(start, end):
    creds = load_google_credentials()
    service = build('calendar', 'v3', credentials=creds)
    events_result = (service.events().list(calendarId='primary',
                                           timeMin=start, timeMax=end,
                                           maxResults=10, singleEvents=True,
                                           orderBy='startTime')
                     .execute())
    return events_result.get('items', [])


def main():

    tomorrow = datetime.date.today() + datetime.timedelta(days=2)
    start_of_day = datetime.datetime.combine(tomorrow, datetime.time.min).isoformat() + 'Z'
    end_of_day = datetime.datetime.combine(tomorrow, datetime.time.max).isoformat() + 'Z'

    events = get_calendar_events(start_of_day, end_of_day)

    if not events:
        event_info = "Free day"
        publish_aws_message(event_info, tomorrow.strftime('%m-%d-%Y'))
    else:
        for event in events:
            if 'dateTime' in event['start']:
                event_time = parse(event['start']['dateTime'])
                time_str = event_time.strftime('%H:%M')
            else:
                time_str = 'All Day'

            event_info = "%s: %s" % (time_str, event['summary'])



if __name__ == '__main__':
    main()
