from datetime import datetime
from imap_tools import MailBox, AND

from config import IMAP_SERVER,EMAIL_USER,EMAIL_PASS,SENDER_EMAIL,EMAIL_SUBJECT

def list_folders():
    with MailBox(IMAP_SERVER).login(EMAIL_USER, EMAIL_PASS) as mailbox:
        for folder in mailbox.folder.list():
            # Most modern versions of imap_tools use .name 
            # This is the "Full Path" name you need for mailbox.folder.set()
            print(f"Direct Name: '{folder.name}'")


# create query string from arguments
def create_query(arguments):
    parts = []

    if arguments.get('uid'):
        return f"UID {arguments['uid']}"
    
    # 2. Priority: Specific Message-ID
    if arguments.get('message_id'):
        # Gmail uses rfc822msgid to search the Message-ID header
        parts.append(f'rfc822msgid:\\"{arguments["message_id"]}\\"')
    else:
        if arguments.get('sender'):
            parts.append(f"from:{arguments['sender']}")
        
        if arguments.get('subject'):
            # Use single quotes for the f-string and double quotes for the Gmail subject
            # This avoids using backslashes entirely
            parts.append(f'subject:\\"{arguments["subject"]}\\"')
        
        if arguments.get('before'):
            parts.append(f"before:{arguments['before']}")
        
        if arguments.get('after'):
            parts.append(f"after:{arguments['after']}")
        
        if arguments.get('attachments'):
            parts.append('has:attachment')

    if not parts:
        return 'ALL' # Default fallback if no arguments provided

    # Join the parts into the internal Gmail search string
    gmail_filter = " ".join(parts)
    
    # Return the command with the filter wrapped in quotes
    return f'X-GM-RAW "{gmail_filter}"'



#returns a Generator for emails.
def fetch_emails(arguments):

    print("🚀 Connecting to Mailbox...")

    query = create_query(arguments)
    
    if(arguments.get('folder') == None):
        folder='[Gmail]/All Mail'
    else:
        folder = arguments.get('folder')

    with MailBox(IMAP_SERVER).login(EMAIL_USER, EMAIL_PASS) as mailbox:
        if not mailbox.folder.exists(folder):
            print("Folder does not exist")
            return
        mailbox.folder.set(folder)
        print(f"Debug:  {query}")
        for msg in mailbox.fetch(query,reverse=True):
            yield msg


if __name__ == "__main__":
    arguments = {
        "folder":"[Gmail]/All Mail",
        "sender":"alvyhall@aol.com",
        "subject":"Sonic Twist",
        "before":"12/31/25",
        #"after":"12/31/2024",
        "attachments":True,
        "exclude":("re:","fwd:")
    }
    emails = fetch_emails(arguments)
    
    for msg in emails:
        print( msg.subject )
