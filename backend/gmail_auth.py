import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read only scope - we never send or delete emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """
    Returns an authenticated Gmail API service object.
    First run: opens browser for user to log in.
    After that: uses saved token.pickle automatically.
    """
    creds = None

    # Check if we already have a saved token from previous login
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, make user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired but refreshable - refresh silently
            creds.refresh(Request())
        else:
            # First time - open browser for login
            flow = InstalledAppFlow.from_client_secrets_file(
                'gmail_credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token so user doesn't have to log in next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def test_gmail_connection():
    """
    Tests Gmail connection by searching for bill-related emails.
    """
    print("Starting Gmail OAuth flow...")
    service = get_gmail_service()
    print("Gmail connected successfully!")

    # Search for bill and receipt emails
    query = 'subject:(invoice OR receipt OR order OR bill) newer_than:30d'
    
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=10
    ).execute()

    messages = results.get('messages', [])

    if not messages:
        print("No bill emails found in last 30 days")
        print("Try forwarding a Swiggy or Amazon email to your inbox")
    else:
        print(f"\nFound {len(messages)} bill-related emails!")
        print("First 5 email IDs:")
        for msg in messages[:5]:
            print(f"  {msg['id']}")
        print("\nGmail OAuth is working correctly.")


if __name__ == "__main__":
    test_gmail_connection()