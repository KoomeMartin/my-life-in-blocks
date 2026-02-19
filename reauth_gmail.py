"""
Re-authentication script for Google Calendar + Gmail API
This will open a browser window to grant BOTH Calendar and Gmail permissions

This script replaces fix_gmail_auth.py and handles both services.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required: Calendar + Gmail (BOTH services)
SCOPES = [
    # Calendar scopes
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    
    # Gmail scopes
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def reauth_gmail():
    """Re-authenticate with BOTH Calendar and Gmail scopes"""
    print("=" * 60)
    print("🔐 RE-AUTHENTICATING WITH GOOGLE SERVICES")
    print("=" * 60)
    print()
    print("This will grant permissions for:")
    print("  📅 Google Calendar (read/write)")
    print("  📧 Gmail (send emails)")
    print()
    
    creds = None
    
    # Delete old token if it exists (force fresh authentication)
    if os.path.exists('token.json'):
        print("⚠️ Found existing token.json")
        print("   Deleting to ensure fresh authentication with all scopes...")
        try:
            os.remove('token.json')
            print("✅ Old token deleted")
        except Exception as e:
            print(f"⚠️ Could not delete old token: {e}")
        print()
    
    # Start OAuth flow
    print("🌐 Starting OAuth authentication flow...")
    print()
    print("📋 Permissions that will be requested:")
    print("   ✅ Google Calendar - Full access")
    print("   ✅ Google Calendar Events - Create/Edit/Delete")
    print("   ✅ Gmail - Send emails")
    print("   ✅ Gmail - Compose emails")
    print("   ✅ Gmail - Modify emails")
    print("   ✅ Gmail - Read profile")
    print()
    print("🔓 A browser window will open shortly...")
    print("   Please sign in and grant ALL requested permissions")
    print()
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        print()
        print("✅ Authentication successful!")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Make sure credentials.json exists")
        print("  2. Make sure both Calendar API and Gmail API are enabled")
        print("  3. Check Google Cloud Console for API status")
        return False
    
    # Save the credentials
    try:
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ Saved new token.json with BOTH Calendar and Gmail permissions")
    except Exception as e:
        print(f"❌ Failed to save token: {e}")
        return False
    
    print()
    print("=" * 60)
    print("🧪 TESTING BOTH SERVICES")
    print("=" * 60)
    print()
    
    # Test Calendar API
    print("1️⃣ Testing Calendar API...")
    try:
        calendar_service = build('calendar', 'v3', credentials=creds)
        calendars = calendar_service.calendarList().list().execute()
        calendar_count = len(calendars.get('items', []))
        print(f"✅ Calendar API working! Found {calendar_count} calendars")
        
        # Show calendar names
        if calendar_count > 0:
            print("   Calendars:")
            for cal in calendars.get('items', [])[:3]:  # Show first 3
                print(f"     • {cal.get('summary', 'Unknown')}")
    except Exception as e:
        print(f"❌ Calendar API test failed: {e}")
        print("   This means Calendar permissions are missing!")
        return False
    
    print()
    
    # Test Gmail API
    print("2️⃣ Testing Gmail API...")
    try:
        gmail_service = build('gmail', 'v1', credentials=creds)
        profile = gmail_service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress', 'Unknown')
        print(f"✅ Gmail API working! Authenticated as: {email}")
    except Exception as e:
        print(f"❌ Gmail API test failed: {e}")
        print("   This means Gmail permissions are missing!")
        return False
    
    print()
    print("=" * 60)
    print("✅ RE-AUTHENTICATION COMPLETE - BOTH SERVICES WORKING")
    print("=" * 60)
    print()
    print("🎉 You can now:")
    print("  📅 Access Google Calendar")
    print("  📧 Send emails via Gmail")
    print()
    print("Next steps:")
    print("  1. Run: python main.py")
    print("  2. Test calendar queries and email features")
    print()
    
    return True
    
    return True


if __name__ == "__main__":
    try:
        success = reauth_gmail()
        if not success:
            print()
            print("❌ Re-authentication failed")
            print()
            print("Troubleshooting:")
            print("  1. Make sure credentials.json exists")
            print("  2. Make sure BOTH Calendar API and Gmail API are enabled:")
            print("     - Go to: https://console.cloud.google.com/apis/library")
            print("     - Enable: Google Calendar API")
            print("     - Enable: Gmail API")
            print("  3. Try deleting token.json and running again")
            print("  4. Check that your OAuth consent screen is configured")
            exit(1)
        else:
            print("✅ Success! Your token.json now has BOTH Calendar and Gmail permissions.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
