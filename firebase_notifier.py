import json
import os
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

def get_access_token():
    """
    Hämta access token från Firebase Service Account
    """
    # Läs service account från miljövariabel (GitHub Secret)
    service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT', '{}'))
    
    if not service_account_info:
        print("⚠️  FIREBASE_SERVICE_ACCOUNT saknas!")
        return None
    
    # Skapa credentials
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/firebase.messaging']
    )
    
    # Hämta access token
    credentials.refresh(Request())
    return credentials.token

def send_notification(title, body, data=None):
    """
    Skicka push-notifikation via Firebase Cloud Messaging (V1 API)
    
    Args:
        title: Notifikationens titel
        body: Notifikationens meddelande
        data: Extra data (dict) att skicka med
    """
    try:
        # Hämta access token
        access_token = get_access_token()
        if not access_token:
            print("❌ Kunde inte hämta access token")
            return False
        
        # Hämta project ID från service account
        service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT', '{}'))
        project_id = service_account_info.get('project_id')
        
        if not project_id:
            print("❌ Kunde inte hitta project_id")
            return False
        
        # FCM V1 API endpoint
        url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
        
        # Headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Meddelande - skickas till ett TOPIC som alla appar kan prenumerera på
        message = {
            'message': {
                'topic': 'ramelia_updates',  # Alla appar prenumererar på detta topic
                'notification': {
                    'title': title,
                    'body': body
                },
                'android': {
                    'priority': 'high',
                    'notification': {
                        'sound': 'default',
                        'click_action': 'FLUTTER_NOTIFICATION_CLICK'
                    }
                }
            }
        }
        
        # Lägg till extra data om det finns
        if data:
            message['message']['data'] = data
        
        # Skicka request
        response = requests.post(url, headers=headers, json=message)
        
        if response.status_code == 200:
            print(f"✅ Notifikation skickad: {title}")
            print(f"📱 Meddelande: {body}")
            return True
        else:
            print(f"❌ Fel vid skickning: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Fel vid notifikation: {e}")
        import traceback
        traceback.print_exc()
        return False

def notify_ramelia_change(old_data, new_data):
    """
    Skicka notifikation om Ramelias lotstid har ändrats
    
    Args:
        old_data: Tidigare data (list av dict)
        new_data: Ny data (list av dict)
    """
    if not new_data:
        print("ℹ️  Ingen ny data att notifiera om")
        return
    
    # Skapa sammanfattning av ändringar
    summary = []
    for item in new_data:
        area = item.get('dispatch_area', 'Okänt område')
        row_data = item.get('row_data', 'Ingen data')
        summary.append(f"{area}: {row_data}")
    
    # Skicka notifikation
    title = "🚢 Ramelia - Lotstid uppdaterad!"
    body = "\n".join(summary[:2])  # Max 2 rader för att inte bli för långt
    
    # Extra data som appen kan använda
    data = {
        'type': 'ramelia_update',
        'timestamp': new_data[0].get('timestamp', ''),
        'count': str(len(new_data))
    }
    
    send_notification(title, body, data)
