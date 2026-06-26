import os
import json
from huggingface_hub import InferenceClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class Settings(BaseSettings):
    MODEL_ID: str
    GOOGLE_API_KEY: str
    APP_NAME: str
    USER_ID: str
    SESSION_ID: str
    GOOGLE_GENAI_USE_VERTEXAI: bool
    HF_API_KEY: str
    
    model_config = SettingsConfigDict(
            env_file='.env',
            env_file_encoding='utf-8'
    )

#*TODO: define our tools

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

def retrieve_emails(max_results: int)-> List[str]:
    """
    Retrieve the mail messages from a gmail account and list them.
    """
    credentials = get_credentials()
    email_messages = []
    
    #* create an email service using Gmail API
    #* get all the mail messages
    try:
        service = build("gmail", "v1", credentials=credentials)
        results = service.users().messages().list(
            userId="me",
            labelIds="INBOX",
            maxResults=max_results
        ).execute()
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
        
        
#* initialize the client using the model Id
#* and the hf api key
settings = Settings()
client = InferenceClient(
    model=settings.MODEL_ID,
    token=settings.HF_API_KEY
)

#* wrap the tools to json schema
search_tools = {
        "type": "function",
        "function": {
            "name": "retrieve_emails",
            "description": " Retrieve the mail messages from a gmail account and list them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results":{
                        "type": "integer",
                        "description": "Maximum number of emails to retrieve."
                    }
                },
                "required": ["max_results"],
                "additionalProperties": False
            }
        }
        }
    
#* define the system and user messages
SYSTEM_PROMPT = """
    You are a helpful assistant that retrieves emails from a gmail account using the Gmail API.
    You have access to retrieve_emails() function that you can use as a tool to retrieve
    the number of emails (not all of them, number of emails to be provided by the use
    if not provided default to a maximum of ten emails) from a gmail account.
    
"""

USER_PROMPT = """
    Please help retrieve mail messages from my gmail account.
"""

#* create messages using the above prompts
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": USER_PROMPT}
]

#* LLM calls
response = client.chat_completion(
    model=settings.MODEL_ID,
    messages=messages,
    tools=[search_tools],
    tool_choice='auto'
)

tool_registry = {
    "retrieve_emails": retrieve_emails
}

tools = response.choices[0].message.tool_calls
if not tools:
    raise ValueError(
        'No tools found in the response. Please check the response and try again.'
    )
    
for tool in tools:
    function_name = tool.function.name
    function_args = tool.function.arguments
    
    if function_name not in tool_registry:
        raise ValueError(
            'Tool not found in the tools registry. Please check the tool name and try again.'
        )
        
        
    #* Perform function calls
    function = tool_registry[function_name]
    output = function(**json.loads(function_args))

    print(output)

