from google.genai import Client
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from google.auth import default

import base64
import json
import mimetypes
import os


SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.labels",
        # "https://www.googleapis.com/auth/gmail.metadata",
        ]

creds_file_loc = 'C:\\Users\\User\\Desktop\\job_scout\\credentials\\credentials.json'
#* attachment file
tender_notice = "C:\\Users\\User\\Desktop\\Tender notice 2026-2027.pdf"
def get_credentials():
    "Get the log in credentials for various scopes."
    creds = None
    
    #* see if there was another log before the current one
    #* if true, use that logs credentials
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    #* If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file_loc, SCOPES)
            creds = flow.run_local_server(port=0)

        #* Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def create_message():
    try:
        #* get the log in credential and initialize a service
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        #* create the message
        message = EmailMessage()
        message.set_content('This is a draft email, not meant to be sent.')
        message['To'] = 'mwangangiboniface581@gmail.com'
        message['From'] = 'me'
        message['Subject'] = 'Test.'
        msg = 'This is a draft email, not meant to be sent.'
        
        
        #* encode the message
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message_body = {'raw': encoded_message}
        
        #* create the message
        send_message = service.users().messages().send(userId='me', body=message_body).execute()
        print(f'Message ID: {send_message["id"]} sent successfully.\n')
    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None
    return send_message


def get_messages():
    #* check if the credentials are available from previous run
    creds = get_credentials()
    
    try:
        #* Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me").execute()
        messages = results.get("messages", [])
        
        if not messages:
            print("No messages found.")
            return
        
        print("First Five Messages:")

        i = 1
        for message in messages[:5]:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            print(f'Message {i}:')
            print(msg['snippet'])
            print('=============================================')
            i += 1
            break

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")



def create_message_with_attachment():
    #* initialize the service
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)
    #* create the email message
    mime_message = EmailMessage()
    mime_message["From"] = "me"
    mime_message["To"] = "mwangangiboniface581@gmail.com"
    mime_message['Subject'] = "Sample With Attachment"
    mime_message.set_content(
        'Hi, this is automated mail with attachment. Please do not reply.'
    )
    type,_ = mimetypes.guess_type(tender_notice)
    maintype, subtype = type.split("/")

    mime_message.add_attachment(
        open(tender_notice, "rb").read(),
        maintype=maintype,
        subtype=subtype,
        filename=os.path.basename(tender_notice)
    )

    encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
    message_body = {'raw': encoded_message}

    attachment = service.users().messages().send(userId='me', body=message_body).execute()
    print(f'Message ID: {attachment["id"]} sent successfully.\n')
    return attachment


def list_emails():
    creds = get_credentials()
    
    email_service = build('gmail', 'v1', credentials=creds)
    results = email_service.users().messages().list(
                        userId='me', labelIds=['INBOX']
                        ).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print('No messages found.')
    else:
        print('Message snippets:')
        i = 1
        for message in messages:
            msg = email_service.users().messages().get(userId='me', id=message['id']).execute()
            print(f'Message {i}:')
            print(msg['snippet'])
            i += 1

if __name__ == "__main__":
    list_emails()