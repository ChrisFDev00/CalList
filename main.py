import os
import pickle
import datetime
import boto3
import time
import json

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TOKEN_FILE = 'sec/token.pickle'


def load_config():
    with open('config.json', 'r') as file:
        return json.load(file)


def load_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    return creds


def save_credentials(creds):
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)


def create_sns():
    sns_client = boto3.client('sns', region_name='us-east-2')
    return sns_client


def main():
    client = create_sns()
    config = load_config()
    topic_arn = config['SNS_TOPIC_ARN']

    messages = ['First Test Message', 'Second Test Message']

    for message in messages:
        response = client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject='Test Subject'
        )
        print(response)

        # Wait for 5 seconds before sending the next message, except for the last one
        if message != messages[-1]:
            time.sleep(5)

    creds = load_credentials()
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('sec/client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        save_credentials(creds)

    service = build('calendar', 'v3', credentials=creds)

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    start_of_day = datetime.datetime.combine(tomorrow, datetime.time.min).isoformat() + 'Z'
    end_of_day = datetime.datetime.combine(tomorrow, datetime.time.max).isoformat() + 'Z'

    now = datetime.datetime.utcnow().isoformat() + 'Z'

    events_result = (service.events().list(calendarId='primary', timeMin=start_of_day,
                                           timeMax=end_of_day, maxResults=10,
                                           singleEvents=True, orderBy='startTime')
                     .execute())

    calendar_list = service.calendarList().list().execute()

    for calendar in calendar_list.get('items', []):
        print(calendar.get('summary'))

    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


if __name__ == '__main__':
    main()
