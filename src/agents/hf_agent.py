import os
import json
import logging
from pathlib import Path
from huggingface_hub import InferenceClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#* Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#* define job key words
COMPANY_RECRUITING_KEYWORDS = [
    "human resources",
    "hr department",
    "recruitment team",
    "talent team",
    "talent acquisition",
    "people operations",
    "hiring manager",
    "recruiter",
    "staffing",
    "career portal"
]
JOB_BOARD_KEYWORDS = [
    "linkedin jobs",
    "indeed",
    "glassdoor",
    "handshake",
    "jobstreet",
    "careerbuilder",
    "ziprecruiter",
    "monster",
    "wellfound",
    "greenhouse",
    "lever",
    "smartrecruiters",
    "workday",
    "myjobmag",
    "brighter monday"
]
DEADLINE_KEYWORDS = [
    "deadline",
    "closing date",
    "closing",
    "application closes",
    "apply before",
    "submit by",
    "last date",
    "before",
    "due date"
]
QUALIFICATION_KEYWORDS = [
    "requirements",
    "qualifications",
    "skills",
    "experience",
    "responsibilities",
    "duties",
    "preferred",
    "mandatory",
    "bachelor",
    "masters",
    "degree",
    "certification",
    "years of experience",
    "proficient",
    "knowledge of",
    "expertise"
]
SALARY_KEYWORDS = [
    "salary",
    "compensation",
    "pay",
    "hourly",
    "annual salary",
    "benefits",
    "package",
    "allowance",
    "remuneration",
    "bonus",
    "ksh",
    "usd",
    "$",
    "€",
    "£"
]
EMPLOYMENT_TYPE_KEYWORDS = [
    "full-time",
    "part-time",
    "contract",
    "temporary",
    "permanent",
    "internship",
    "remote",
    "hybrid",
    "on-site",
    "freelance",
    "consultancy"
]
KEYWORDS = COMPANY_RECRUITING_KEYWORDS + JOB_BOARD_KEYWORDS + DEADLINE_KEYWORDS + QUALIFICATION_KEYWORDS + SALARY_KEYWORDS + EMPLOYMENT_TYPE_KEYWORDS


#* Define the various scopes/permissions to use with the Gmail API
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
]

DEFAULT_MAX_EMAILS = 10


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    MODEL_ID: str
    GOOGLE_API_KEY: str
    APP_NAME: str
    USER_ID: str
    SESSION_ID: str
    GOOGLE_GENAI_USE_VERTEXAI: bool
    HF_API_KEY: str
    GOOGLE_CREDENTIALS_PATH: str = "credentials\\credentials.json"
    GOOGLE_TOKEN_PATH: str = "token.json"
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )


def get_credentials() -> Credentials:
    """
    Get the login credentials for various scopes.
    
    Returns cached credentials if valid, refreshes expired ones,
    or prompts for new login if needed.
    
    Returns:
        Credentials: Valid Google OAuth2 credentials
        
    Raises:
        FileNotFoundError: If credentials file not found
    """
    settings = Settings()
    creds = None
    
    #* Check if cached token exists and is valid
    if os.path.exists(settings.GOOGLE_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(
                settings.GOOGLE_TOKEN_PATH, SCOPES
            )
            logger.info("Loaded cached credentials from token file")
        except Exception as e:
            logger.warning(f"Failed to load cached credentials: {e}")
            creds = None
    
    #* Refresh or obtain new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            #* Load credentials from user file
            if not os.path.exists(settings.GOOGLE_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Credentials file not found at {settings.GOOGLE_CREDENTIALS_PATH}. "
                    "Please ensure GOOGLE_CREDENTIALS_PATH is set correctly in .env"
                )
            
            logger.info("Initiating new OAuth2 flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GOOGLE_CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        #* Save credentials for future use
        try:
            with open(settings.GOOGLE_TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info(f"Saved credentials to {settings.GOOGLE_TOKEN_PATH}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    return creds


def retrieve_emails(max_results: int = DEFAULT_MAX_EMAILS) -> List[str]:
    """
    Retrieve email messages from a Gmail account inbox.
    
    Args:
        max_results: Maximum number of emails to retrieve (default: 10)
        
    Returns:
        List of email snippets as strings
        
    Raises:
        HttpError: If Gmail API call fails
        ValueError: If no messages found in inbox
    """
    try:
        #* Enforce default and reasonable limits
        max_results = max(1, min(max_results, 100))
        
        credentials = get_credentials()
        email_messages = []
        
        #* Create Gmail API service
        service = build("gmail", "v1", credentials=credentials)
        
        #* Retrieve message list
        results = service.users().messages().list(
            userId="me",
            labelIds="INBOX",
            maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        
        if not messages:
            logger.warning("No messages found in inbox")
            return []
        
        logger.info(f"Retrieved {len(messages)} message(s) from inbox")
        
        #* Fetch full message details
        for message in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", 
                    id=message["id"]
                ).execute()
                snippet = msg.get('snippet', '')
                email_messages.append(snippet)
            except HttpError as e:
                logger.error(f"Failed to retrieve message {message['id']}: {e}")
                continue
        
        return email_messages
    
    except HttpError as error:
        logger.error(f"Gmail API error occurred: {error}")
        raise
    
    except Exception as error:
        import traceback
        
        logger.info("\nFULL TRACEBACK:")
        traceback.print_exc()
        raise

def classify_emails(emails: List[str]) -> Dict[str, Any]:
    """
    Classify a list of emails to their respective categories to see if there
    are job related emails

    Args:
        emails (List[str]): List of emails to classify

    Returns:
        Dict[str, Any]: Dictionary with classification results
        
    Raises:
        ValueError: If no emails provided
    """
    
    logger.info(f'Classifying a list {len(emails)} email(s)')

    classified = {
        'job_emails': [email for email in emails if any(keyword.lower() in email.lower() for keyword in KEYWORDS)],
        'non_job_emails': [email for email in emails if not any(keyword.lower() in email.lower() for keyword in KEYWORDS)]
    }
    
    logger.info(f'Found {len(classified["job_emails"])} job email(s) and {len(classified["non_job_emails"])} non-job email(s)')
    return classified


def build_tool_definition() -> List[Dict[str, Any]]:
    """
    Build the JSON schema tool for all tools.
    
    Returns:
        List of Dictionaries containing tool definition in JSON schema format
    """

    return [
        {
            "type": "function",
            "function": {
                "name": "retrieve_emails",
                "description":
                    """
                    Retrieve mail messages from a Gmail inbox.
                    
                    Important.
                    The returned emails MUST be passed
                    to the classify_emails tool.
                    Never classify emails yourself.
                    """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description":
                                "Maximum number of emails to retrieve",
                            "default":
                                DEFAULT_MAX_EMAILS
                        }
                    },
                    "required": [],
                    "additionalProperties": False
                }
            }
        },

        {
            "type": "function",
            "function": {
                "name": "classify_emails",
                "description":
                    """
                    Classify emails returned by the retrieve_emails tool into categories.
                    
                    This tool MUST be called after retrieve_emails""",
                    
                "parameters": {
                    "type": "object",
                    "properties": {
                        "emails": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description":
                                "List of emails to classify"
                        }
                    },
                    "required": ["emails"],
                    "additionalProperties": False
                }
            }
        }
    ]


def build_prompts() -> tuple[str, str]:
    """
    Build system and user prompts for the agent.
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = f"""
    You are a helpful assistant that retrieves emails from a Gmail account using the Gmail API, then
    classifies those emails to job and non-job emails using the provided tools.

    You MUST follow this workflow:
    - When asked to retrieve emails, call the retrieve_emails function
    - The max_results parameter accepts integers from 1 to 100 (default: {DEFAULT_MAX_EMAILS})
    - If the user doesn't specify how many emails to retrieve, use the default of {DEFAULT_MAX_EMAILS}
    - Wait for the tool output and do NOT analyze the emails yourself.
    - Pass the retrieved email through classify_emails, wait for the output then you may answer.
    - Always be helpful and provide clear feedback about what you're doing

    """
    
    user_prompt = """
    Please help retrieve 20 mail messages from my Gmail account.
    """
    
    return system_prompt, user_prompt


def execute_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """
    Execute a tool call from the agent response.
    
    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        
    Returns:
        Result of the tool execution
        
    Raises:
        ValueError: If tool not found in registry
    """
    tool_registry: Dict[str, callable] = {
        "retrieve_emails": retrieve_emails,
        "classify_emails": classify_emails
    }
    
    if tool_name not in tool_registry:
        raise ValueError(
            f"Tool '{tool_name}' not found in registry. "
            f"Available tools: {', '.join(tool_registry.keys())}"
        )
    
    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
    tool_function = tool_registry[tool_name]
    return tool_function(**tool_args)


def main() -> None:
    """
    Main agent execution function.
    
    Orchestrates the workflow of:
    1. Loading settings and initializing HF client
    2. Building prompts and tools
    3. Calling the LLM with tool use
    4. Executing tool calls
    5. Displaying results
    """

    #* Initialize settings and client
    settings = Settings()
    logger.info(f"Initializing HF client with model: {settings.MODEL_ID}")
    
    client = InferenceClient(
        model=settings.MODEL_ID,
        token=settings.HF_API_KEY
    )
    
    #* Build tool definitions and prompts
    tools = build_tool_definition()
    system_prompt, user_prompt = build_prompts()
    
    #* Create messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    
    running =True
    
    while running:
        #* Call LLM with tool use
        logger.info("Calling LLM with tool use enabled")
        response = client.chat_completion(
            model=settings.MODEL_ID,
            messages=messages,
            tools=tools,
            tool_choice='auto'
        )
        
        #* Append the assistant's message to history
        messages.append({
            "role": "assistant",
            "content": response.choices[0].message.content
        })
        
        #* Extract and validate tool calls
        tool_calls = response.choices[0].message.tool_calls
        
        #* if the LLM didn't request a tool, it has finished it's task
        if not tool_calls:
            logger.warning("No tool calls found in LLM response")
            print("Assistant:", response.choices[0].message.content)
            running = False
            break
        
        logger.info(tool_calls)
        logger.info(f"Found {len(tool_calls)} tool call(s) in response")
        running = False
        
        # #*TODO: TOOL ORCHASTRATION
        #* Execute each tool call
        output = None
        for tool_call in tool_calls:
            try:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                logger.info(function_args)
                logger.info(f"Processing tool call: {function_name}")
                
                #* execute the python function based on the name
                #* and format the output into a valid Json array
                output = execute_tool_call(function_name,function_args)
                formatted_output = json.dumps(output)
                
                #* append the execution result to the converstion history
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": formatted_output
                    }
                )
                
                logger.info(f"Tool execution successful. Appended results for {function_name} to conversation history")
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                running = False
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                running = False
                
        classified_emails = classify_emails(output)



if __name__ == "__main__":
    main()

