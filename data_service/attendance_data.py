"""
Attendance Data Extraction Service
"""
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List


class AttendanceDataService:
    """Service for extracting and storing attendance data"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.base_url = 'https://vtopcc.vit.ac.in/vtop'
        self.data_dir = 'data'
        self.data_file = os.path.join(self.data_dir, 'attendance-data.json')
        
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_csrf_token(self) -> Optional[str]:
        """Extract CSRF token from current page"""
        try:
            response = self.session.get(f"{self.base_url}/content")
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            return csrf_input['value'] if csrf_input else None
        except Exception:
            return None
    
    def _get_authorized_id(self) -> Optional[str]:
        """Extract authorized ID from current page"""
        try:
            response = self.session.get(f"{self.base_url}/content")
            soup = BeautifulSoup(response.text, 'html.parser')
            auth_input = soup.find('input', {'id': 'authorizedIDX'})
            return auth_input['value'] if auth_input else None
        except Exception:
            return None
    
    def extract_attendance(self, semester_id: str) -> Optional[List[Dict[str, Any]]]:
        """Extract attendance data from VTOP"""
        csrf_token = self._get_csrf_token()
        authorized_id = self._get_authorized_id()
        
        if not csrf_token or not authorized_id:
            print("[AttendanceData] Failed to get required tokens")
            return None
        
        # Correct payload format
        post_data = {
            '_csrf': csrf_token,
            'semesterSubId': semester_id,
            'authorizedID': authorized_id,
            'x': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/processViewStudentAttendance",
                data=post_data,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"[AttendanceData] HTTP {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the table
            table = soup.find('table', class_='table')
            if not table:
                print("[AttendanceData] Attendance table not found")
                return None
            
            attendance_list = []
            
            # Get all data rows (skip header)
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 14:  # Skip summary rows
                    continue
                
                attendance_obj = {}
                
                # Sl.No (index 0)
                attendance_obj['slNo'] = cells[0].get_text(strip=True)
                
                # Course Code (index 1)
                attendance_obj['courseCode'] = cells[1].get_text(strip=True)
                
                # Course Title (index 2)
                attendance_obj['courseTitle'] = cells[2].get_text(strip=True)
                
                # Course Type (index 3)
                attendance_obj['courseType'] = cells[3].get_text(strip=True)
                
                # Slot (index 4)
                slot_text = cells[4].get_text(strip=True)
                attendance_obj['slot'] = slot_text
                
                # Faculty Name (index 5) - contains multiple <p> tags
                faculty_cell = cells[5]
                faculty_ps = faculty_cell.find_all('p')
                if len(faculty_ps) >= 3:
                    attendance_obj['facultyId'] = faculty_ps[0].get_text(strip=True)
                    attendance_obj['facultyName'] = faculty_ps[1].get_text(strip=True)
                    attendance_obj['facultySchool'] = faculty_ps[2].get_text(strip=True)
                elif len(faculty_ps) >= 2:
                    attendance_obj['facultyId'] = faculty_ps[0].get_text(strip=True)
                    attendance_obj['facultyName'] = faculty_ps[1].get_text(strip=True)
                    attendance_obj['facultySchool'] = ''
                else:
                    attendance_obj['facultyId'] = ''
                    attendance_obj['facultyName'] = faculty_cell.get_text(strip=True)
                    attendance_obj['facultySchool'] = ''
                
                # Attendance Type (index 6)
                attendance_obj['attendanceType'] = cells[6].get_text(strip=True)
                
                # Registration Date/Time (index 7)
                attendance_obj['registrationDateTime'] = cells[7].get_text(strip=True)
                
                # Attendance Date (index 8)
                attendance_obj['attendanceDate'] = cells[8].get_text(strip=True)
                
                # Attended Classes (index 9)
                try:
                    attendance_obj['attendedClasses'] = int(cells[9].get_text(strip=True))
                except ValueError:
                    attendance_obj['attendedClasses'] = 0
                
                # Total Classes (index 10)
                try:
                    attendance_obj['totalClasses'] = int(cells[10].get_text(strip=True))
                except ValueError:
                    attendance_obj['totalClasses'] = 0
                
                # Attendance Percentage (index 11)
                try:
                    attendance_obj['attendancePercentage'] = int(cells[11].get_text(strip=True))
                except ValueError:
                    attendance_obj['attendancePercentage'] = 0
                
                # Status (index 12)
                attendance_obj['status'] = cells[12].get_text(strip=True)
                
                # Extract class ID from View link (index 13)
                view_link = cells[13].find('a')
                if view_link and 'onclick' in view_link.attrs:
                    onclick = view_link['onclick']
                    # Extract class ID from onclick="javascript:processViewAttendanceDetail('CH2025260502216','F2+TF2');"
                    import re
                    match = re.search(r"processViewAttendanceDetail\('([^']+)'", onclick)
                    if match:
                        attendance_obj['classId'] = match.group(1)
                
                attendance_list.append(attendance_obj)
            
            return attendance_list if attendance_list else None
                
        except Exception as e:
            print(f"[AttendanceData] Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_attendance(self, attendance_data: List[Dict[str, Any]], semester_id: str) -> bool:
        """Save attendance data to JSON file with timestamps"""
        try:
            now = datetime.now()
            
            # Calculate statistics
            total_subjects = len(attendance_data)
            total_attended = sum(item.get('attendedClasses', 0) for item in attendance_data)
            total_classes = sum(item.get('totalClasses', 0) for item in attendance_data)
            overall_percentage = int((total_attended / total_classes * 100)) if total_classes > 0 else 0
            
            data_to_save = {
                'attendance': attendance_data,
                'metadata': {
                    'semesterId': semester_id,
                    'totalSubjects': total_subjects,
                    'totalAttendedClasses': total_attended,
                    'totalClasses': total_classes,
                    'overallPercentage': overall_percentage,
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
            print(f"[AttendanceData] Failed to save data: {e}")
            return False
    
    def get_saved_attendance(self) -> Optional[Dict[str, Any]]:
        """Load saved attendance data from file"""
        if not os.path.exists(self.data_file):
            return None
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[AttendanceData] Failed to load saved data: {e}")
            return None
    
    def run(self, semester_id: str) -> bool:
        """Execute attendance extraction and save"""
        attendance = self.extract_attendance(semester_id)
        if attendance:
            return self.save_attendance(attendance, semester_id)
        return False
