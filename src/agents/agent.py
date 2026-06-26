from __future__ import print_function

import os.path

from typing import List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.adk.agents import Agent
from huggingface_hub import InferenceClient

#* define the various scopes/permissions to use with the Gmail API
SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.labels",
        ]

def get_credentials():
    """
    Get the log in credentials for various scopes.
    """
    creds = None
    creds_file_loc = 'C:\\Users\\User\\Desktop\\job_scout\\credentials\\credentials.json'
    #* see if there was another log before the current one
    #* if true, use that logs credentials
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    #* 
    if not creds or not creds.valid:
        #* If there are no (valid) credentials available, let the user log in.
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            #* load the credentials from user file
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_file_loc, SCOPES
            )
            creds = flow.run_local_server(port=0)
            
        #* write the credentials into a file for later use
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds



def retrieve_emails()-> List[str]:
    """
    Retrieve the mail messages from a gmail account and list them.
    """
    email_messages = []
    
    #* get the log in credentials
    creds = get_credentials()
    
    #* create an email service using Gmail API
    #* get all the mail messages
    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", labelIds="INBOX").execute()
        messages = results.get("messages", [])
        
        if not messages:
            raise ValueError(
                'No messages found, please check the mail address and try again later.'
            )
            
        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            msg = msg['snippet']
            email_messages.append(msg)
        return email_messages
    

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")
        
        
root_agent = Agent(
    name='email_extractor_agent',
    model = "gemini-2.5-flash",
    instruction=(
        '''You are an agent that logs into a user email and
        extracts all the mail messages from their inbox'''
    ),
    description=(
        '''An agent to extract emial messages from users email'''
    ),
    tools = [retrieve_emails]
)
        
# if __name__ == "__main__":
#     messages = retrieve_emails()
#     print(messages[:10])