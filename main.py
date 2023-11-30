import os
import pickle
import datetime
import boto3
import logging
import json

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dateutil.parser import parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TOKEN_FILE = 'sec/token.pickle'


def load_aws_credentials():
    try:
        with open('sec/config.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error("Error loading AWS creds: %s", e)
        raise


def load_google_credentials(token_file, scopes):
    creds = None
    # Load from existing
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If invalid, re-auth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('sec/client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        save_google_credentials(creds)

    return creds


def save_google_credentials(token_file, creds):
    try:
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    except Exception as e:
        logging.error("Error saving Google creds: %s", e)
        raise


def create_sns():
    return boto3.client('sns', region_name='us-east-2')


def get_date_tomorrow():
    return datetime.date.today() + datetime.timedelta(days=1)


def publish_aws_message(sns_client, topic_arn, message, date):
    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=date
        )
        logging.info("Published: %s", response)
    except Exception as e:
        logging.error("Error publishing SNS: %s", e)
        raise


def get_calendar_events(service, start, end):
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start,
            timeMax=end,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logging.error("Error fetching calendar events: %s", e)
        raise


def format_events(events):
    agenda = ''
    for event in events:
        if 'dateTime' in event['start']:
            event_time = parse(event['start']['dateTime'])
            time_str = event_time.strftime('%H:%M')
        else:
            time_str = 'All Day'
        agenda += f"{time_str}: {event['summary']}\n"
    return agenda


def main():
    creds = load_google_credentials(TOKEN_FILE, SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    date_tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    start_of_day = datetime.datetime.combine(date_tomorrow, datetime.time.min).isoformat() + 'Z'
    end_of_day = datetime.datetime.combine(date_tomorrow, datetime.time.max).isoformat() + 'Z'

    events = get_calendar_events(service, start_of_day, end_of_day)
    event_info = format_events(events) if events else "Free day"

    aws_config = load_aws_credentials()
    sns_client = create_sns()
    publish_aws_message(sns_client, aws_config['SNS_TOPIC_ARN'], event_info, date_tomorrow.strftime('%m-%d-%Y'))


if __name__ == '__main__':
    main()
