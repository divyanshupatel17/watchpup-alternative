"""
Marks Data Extraction Service
"""
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List


class MarksDataService:
    """Service for extracting and storing marks data"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.base_url = 'https://vtopcc.vit.ac.in/vtop'
        self.data_dir = 'data'
        self.data_file = os.path.join(self.data_dir, 'marks-data.json')
        
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
    
    def extract_marks(self, semester_id: str) -> Optional[Dict[str, Any]]:
        """Extract marks data from VTOP"""
        csrf_token = self._get_csrf_token()
        authorized_id = self._get_authorized_id()
        
        if not csrf_token or not authorized_id:
            print("[MarksData] Failed to get required tokens")
            return None
        
        # Correct payload format
        post_data = {
            'authorizedID': authorized_id,
            'semesterSubId': semester_id,
            '_csrf': csrf_token
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/examinations/doStudentMarkView",
                data=post_data,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"[MarksData] HTTP {response.status_code}")
                return None
            
            if 'no data found' in response.text.lower():
                print("[MarksData] No marks data found")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find('div', {'id': 'fixedTableContainer'})
            
            if not container:
                print("[MarksData] Marks container not found")
                return None
            
            courses_data = []
            
            # Find the main table
            main_table = container.find('table', class_='customTable')
            if not main_table:
                return None
            
            # Get all rows
            rows = main_table.find_all('tr', recursive=False)
            
            i = 1  # Skip header row
            while i < len(rows):
                row = rows[i]
                
                # Check if this is a course info row
                if 'tableContent' in row.get('class', []):
                    cells = row.find_all('td')
                    
                    # If this row has 9 cells, it's a course header
                    if len(cells) == 9:
                        course_info = {
                            'slNo': cells[0].get_text(strip=True),
                            'classNumber': cells[1].get_text(strip=True),
                            'courseCode': cells[2].get_text(strip=True),
                            'courseTitle': cells[3].get_text(strip=True),
                            'courseType': cells[4].get_text(strip=True),
                            'courseSystem': cells[5].get_text(strip=True),
                            'faculty': cells[6].get_text(strip=True),
                            'slot': cells[7].get_text(strip=True),
                            'courseMode': cells[8].get_text(strip=True),
                            'assessments': []
                        }
                        
                        # Next row should contain the marks table
                        i += 1
                        if i < len(rows):
                            marks_row = rows[i]
                            inner_table = marks_row.find('table', class_='customTable-level1')
                            
                            if inner_table:
                                # Parse assessment marks
                                inner_rows = inner_table.find_all('tr')
                                
                                # Skip header row, process data rows
                                for inner_row in inner_rows[1:]:
                                    if 'tableContent-level1' in inner_row.get('class', []):
                                        mark_cells = inner_row.find_all(['td', 'output'])
                                        
                                        if len(mark_cells) >= 10:
                                            assessment = {}
                                            
                                            # Extract from output tags
                                            outputs = inner_row.find_all('output')
                                            if len(outputs) >= 10:
                                                assessment['slNo'] = outputs[0].get_text(strip=True)
                                                assessment['markTitle'] = outputs[1].get_text(strip=True)
                                                
                                                try:
                                                    assessment['maxMark'] = float(outputs[2].get_text(strip=True))
                                                except (ValueError, AttributeError):
                                                    assessment['maxMark'] = None
                                                
                                                try:
                                                    assessment['weightagePercentage'] = float(outputs[3].get_text(strip=True))
                                                except (ValueError, AttributeError):
                                                    assessment['weightagePercentage'] = None
                                                
                                                assessment['status'] = outputs[4].get_text(strip=True)
                                                
                                                try:
                                                    assessment['scoredMark'] = float(outputs[5].get_text(strip=True))
                                                except (ValueError, AttributeError):
                                                    assessment['scoredMark'] = None
                                                
                                                try:
                                                    assessment['weightageMark'] = float(outputs[6].get_text(strip=True))
                                                except (ValueError, AttributeError):
                                                    assessment['weightageMark'] = None
                                                
                                                class_avg = outputs[7].get_text(strip=True)
                                                try:
                                                    assessment['classAverage'] = float(class_avg) if class_avg else None
                                                except (ValueError, AttributeError):
                                                    assessment['classAverage'] = None
                                                
                                                strength = outputs[8].get_text(strip=True)
                                                try:
                                                    assessment['markPostedStrength'] = int(strength) if strength else None
                                                except (ValueError, AttributeError):
                                                    assessment['markPostedStrength'] = None
                                                
                                                assessment['remark'] = outputs[9].get_text(strip=True)
                                                
                                                course_info['assessments'].append(assessment)
                        
                        courses_data.append(course_info)
                
                i += 1
            
            return {'courses': courses_data} if courses_data else None
                
        except Exception as e:
            print(f"[MarksData] Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_marks(self, marks_data: Dict[str, Any], semester_id: str) -> bool:
        """Save marks data to JSON file with timestamps"""
        try:
            now = datetime.now()
            
            courses = marks_data.get('courses', [])
            
            # Calculate statistics
            total_courses = len(courses)
            total_assessments = sum(len(course.get('assessments', [])) for course in courses)
            
            data_to_save = {
                'courses': courses,
                'metadata': {
                    'semesterId': semester_id,
                    'totalCourses': total_courses,
                    'totalAssessments': total_assessments,
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
            print(f"[MarksData] Failed to save data: {e}")
            return False
    
    def get_saved_marks(self) -> Optional[Dict[str, Any]]:
        """Load saved marks data from file"""
        if not os.path.exists(self.data_file):
            return None
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[MarksData] Failed to load saved data: {e}")
            return None
    
    def run(self, semester_id: str) -> bool:
        """Execute marks extraction and save"""
        marks = self.extract_marks(semester_id)
        if marks:
            return self.save_marks(marks, semester_id)
        return False
