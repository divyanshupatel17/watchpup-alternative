"""
Profile Information Extraction Service
"""
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any


class ProfileInfoService:
    """Service for extracting and storing student profile information"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.base_url = 'https://vtopcc.vit.ac.in/vtop'
        self.data_dir = 'data'
        self.data_file = os.path.join(self.data_dir, 'profile-info-data.json')
        
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_csrf_token(self) -> Optional[str]:
        """Extract CSRF token from current page"""
        try:
            response = self.session.get(f"{self.base_url}/content")
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            return csrf_input['value'] if csrf_input else None
        except Exception as e:
            print(f"[ProfileInfo] Failed to get CSRF token: {e}")
            return None
    
    def _get_authorized_id(self) -> Optional[str]:
        """Extract authorized ID from current page"""
        try:
            response = self.session.get(f"{self.base_url}/content")
            soup = BeautifulSoup(response.text, 'html.parser')
            auth_input = soup.find('input', {'id': 'authorizedIDX'})
            return auth_input['value'] if auth_input else None
        except Exception as e:
            print(f"[ProfileInfo] Failed to get authorized ID: {e}")
            return None
    
    def extract_profile(self) -> Optional[Dict[str, Any]]:
        """Extract student profile information from VTOP"""
        csrf_token = self._get_csrf_token()
        authorized_id = self._get_authorized_id()
        
        if not csrf_token or not authorized_id:
            print("[ProfileInfo] Failed to get required tokens")
            return None
        
        post_data = {
            'verifyMenu': 'true',
            'authorizedID': authorized_id,
            '_csrf': csrf_token,
            'nocache': str(int(datetime.now().timestamp() * 1000))
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/studentsRecord/StudentProfileAllView",
                data=post_data,
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            if 'personal information' not in response.text.lower():
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            profile = {}
            
            name_element = soup.find('p', style=lambda x: x and 'font-weight: bold' in x)
            if name_element:
                profile['name'] = name_element.get_text(strip=True)
            
            labels = soup.find_all('label', class_=lambda x: x and 'col-form-label' in x)
            for label in labels:
                label_text = label.get_text(strip=True).upper()
                next_element = label.find_next_sibling()
                
                if not next_element:
                    continue
                
                value = next_element.get_text(strip=True)
                
                if 'REGISTER NUMBER' in label_text:
                    profile['registerNumber'] = value
                elif 'VIT EMAIL' in label_text:
                    profile['vitEmail'] = value
                elif 'PROGRAM' in label_text and 'BRANCH' in label_text:
                    profile['program'] = value
                    parts = value.split(' - ')
                    profile['branch'] = ' - '.join(parts[1:]) if len(parts) > 1 else value
                elif 'SCHOOL NAME' in label_text:
                    profile['schoolName'] = value
            
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).upper()
                    value = cells[1].get_text(strip=True)
                    
                    if 'BLOCK NAME' in label:
                        profile['hostelBlock'] = value
                    elif 'ROOM NO' in label:
                        profile['roomNumber'] = value
                    elif 'BED TYPE' in label:
                        profile['bedType'] = value
                    elif 'MESS' in label:
                        profile['messName'] = value
                    elif 'DATE OF BIRTH' in label or 'DOB' in label:
                        profile['dateOfBirth'] = value
            
            if profile.get('name'):
                return profile
            else:
                return None
                
        except Exception as e:
            print(f"[ProfileInfo] Extraction failed: {e}")
            return None
    
    def save_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Save profile data to JSON file with timestamps"""
        try:
            now = datetime.now()
            
            data_to_save = {
                'profile': profile_data,
                'metadata': {
                    'lastUpdated': now.isoformat(),
                    'lastUpdatedHuman': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'extractionTimestamp': int(now.timestamp() * 1000)
                }
            }
            
            existing_data = None
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass
            
            if existing_data:
                data_to_save['previousUpdate'] = existing_data.get('metadata', {})
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"[ProfileInfo] Failed to save data: {e}")
            return False
    
    def get_saved_profile(self) -> Optional[Dict[str, Any]]:
        """Load saved profile data from file"""
        if not os.path.exists(self.data_file):
            return None
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ProfileInfo] Failed to load saved data: {e}")
            return None
    
    def run(self) -> bool:
        """Execute profile extraction and save"""
        profile = self.extract_profile()
        if profile:
            return self.save_profile(profile)
        return False
