"""
Internship Coach MCP Server with Google Sheets & Calendar Integration
Matches Akshaya's exact sheet format
"""

import asyncio
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import PyPDF2
import os.path
import pickle
from datetime import datetime, timedelta
import json

# Google API setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar'
]
SPREADSHEET_ID = '1g_I4LbNcg9Uw0NBVLfoMmjFmvcXQDEfkjw0QK0biqk4'
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_NAME = 'Internship & Job Tracker'  # Your main sheet
HEADER_ROW = 15  # Row 15 is your header
DATA_START_ROW = 16  # Data starts at row 16

class InternshipCoach:
    def __init__(self):
        self.creds = None
        self.sheets_service = None
        self.calendar_service = None
        # Define your resume paths here
        self.resume_map = {
            "resume://software-engineering": os.path.join(SCRIPT_DIR, "resumes", "swe-resume.txt"),
            "resume://data-science": os.path.join(SCRIPT_DIR, "resumes", "ds-resume.txt"),
            "resume://machine-learning": os.path.join(SCRIPT_DIR, "resumes", "ml-resume.txt"),
            "resume://cyber": os.path.join(SCRIPT_DIR, "resumes", "cyber-resume.txt"),
            "resume://materials-science": os.path.join(SCRIPT_DIR, "resumes", "matsci-resume.txt")
        }
        
    def authenticate_google(self):
        """Authenticate with Google Sheets and Calendar APIs"""
        token_path = os.path.join(SCRIPT_DIR, 'token.pickle')
        creds_path = os.path.join(SCRIPT_DIR, 'credentials.json')
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.calendar_service = build('calendar', 'v3', credentials=self.creds)
    
    def _read_pdf(self, file_path: str) -> str:
        """Helper to read PDF files"""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def _read_text_file(self, file_path: str) -> str:
        """Helper to read text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
        
    async def recommend_resume(self, company: str, position: str, job_description: str = ""):
        """
        Recommend which resume version to use for a specific application.
        Analyzes the position title, company, and optional job description to suggest
        the most appropriate resume from your available versions.
        
        Args:
            company: Company name
            position: Position title
            job_description: Optional job description text for analysis
            
        Returns:
            dict with recommendation, reasoning, and alternatives
        """
        
        position_lower = position.lower()
        jd_lower = job_description.lower() if job_description else ""
        
        # Keywords for each resume type
        swe_keywords = [
            'software', 'engineer', 'developer', 'backend', 'frontend', 'full stack',
            'fullstack', 'web dev', 'mobile', 'ios', 'android', 'coding', 'programming',
            'java', 'python', 'c++', 'javascript', 'react', 'node', 'api', 'system design',
            'swe', 'sde', 'software development'
        ]
        
        data_keywords = [
            'data', 'analytics', 'analyst', 'business intelligence', 'bi',
            'sql', 'tableau', 'power bi', 'visualization', 'reporting',
            'metrics', 'dashboard', 'excel', 'statistics'
        ]
        
        ml_keywords = [
            'machine learning', 'ml', 'ai', 'artificial intelligence', 'deep learning',
            'neural network', 'nlp', 'computer vision', 'tensorflow', 'pytorch',
            'scikit-learn', 'model', 'training', 'inference', 'data science',
            'research', 'phd', 'kaggle'
        ]
        
        cyber_keywords = [
            'cyber', 'security', 'infosec', 'penetration', 'vulnerability',
            'threat', 'soc', 'incident response', 'firewall', 'encryption',
            'compliance', 'risk', 'authentication', 'network security',
            'malware', 'forensics', 'ceh', 'cissp'
        ]
        
        matsci_keywords = [
            'materials', 'chemistry', 'chemical', 'polymer', 'nanomaterial',
            'characterization', 'synthesis', 'lab', 'research', 'microscopy',
            'spectroscopy', 'semiconductor', 'metallurgy', 'biomaterial',
            'composite', 'crystallography'
        ]
        
        # Calculate scores for each category
        swe_score = sum(1 for keyword in swe_keywords if keyword in position_lower or keyword in jd_lower)
        data_score = sum(1 for keyword in data_keywords if keyword in position_lower or keyword in jd_lower)
        ml_score = sum(1 for keyword in ml_keywords if keyword in position_lower or keyword in jd_lower)
        cyber_score = sum(1 for keyword in cyber_keywords if keyword in position_lower or keyword in jd_lower)
        matsci_score = sum(1 for keyword in matsci_keywords if keyword in position_lower or keyword in jd_lower)
        
        # Find the highest score
        scores = {
            "resume://software-engineering": swe_score,
            "resume://data-science": data_score,
            "resume://machine-learning": ml_score,
            "resume://cyber": cyber_score,
            "resume://materials-science": matsci_score
        }
        
        max_score = max(scores.values())
        
        # Handle ties or no clear winner
        top_resumes = [uri for uri, score in scores.items() if score == max_score]
        
        recommendation = None
        reasoning = []
        alternatives = []
        confidence = "high"
        
        if max_score == 0:
            # No keywords matched - default to most general
            recommendation = "resume://software-engineering"
            reasoning.append("⚠️ No clear keyword matches found in position or description")
            reasoning.append("Defaulting to software engineering resume as most general tech resume")
            alternatives = [
                {"uri": "resume://data-science", "reason": "Use if role involves data analysis"},
                {"uri": "resume://machine-learning", "reason": "Use if role involves ML/AI work"},
                {"uri": "resume://cyber", "reason": "Use if role is security-focused"},
                {"uri": "resume://materials-science", "reason": "Use if role is materials/chemistry-focused"}
            ]
            confidence = "low"
            reasoning.append("💡 Consider providing the full job description for better analysis")
        
        elif len(top_resumes) > 1:
            # Tie - pick based on hierarchy: ML > Cyber > SWE > Data > MatSci
            priority_order = [
                "resume://machine-learning",
                "resume://cyber", 
                "resume://software-engineering",
                "resume://data-science",
                "resume://materials-science"
            ]
            
            for uri in priority_order:
                if uri in top_resumes:
                    recommendation = uri
                    break
            
            reasoning.append(f"Multiple resume types tied with {max_score} keyword matches")
            reasoning.append(f"Recommending {recommendation.split('://')[-1]} as primary")
            
            for uri in top_resumes:
                if uri != recommendation:
                    alternatives.append({
                        "uri": uri,
                        "reason": f"Equally strong match ({scores[uri]} keywords)"
                    })
            confidence = "medium"
        
        else:
            # Clear winner
            recommendation = top_resumes[0]
            resume_type = recommendation.split('://')[-1]
            reasoning.append(f"✅ Strong match for {resume_type} ({max_score} keyword matches)")
            
            # Add specific reasoning based on type
            if recommendation == "resume://software-engineering":
                reasoning.append("Focus on: coding skills, software projects, technical stack")
            elif recommendation == "resume://data-science":
                reasoning.append("Focus on: data analysis, SQL, visualization, business insights")
            elif recommendation == "resume://machine-learning":
                reasoning.append("Focus on: ML models, research, algorithms, frameworks (TensorFlow/PyTorch)")
            elif recommendation == "resume://cyber":
                reasoning.append("Focus on: security tools, vulnerabilities, compliance, threat analysis")
            elif recommendation == "resume://materials-science":
                reasoning.append("Focus on: lab experience, characterization, research, publications")
            
            # Add runner-up alternatives
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for uri, score in sorted_scores[1:3]:  # Next 2 highest
                if score > 0:
                    alternatives.append({
                        "uri": uri,
                        "reason": f"Consider if role emphasizes {uri.split('://')[-1]} ({score} keywords)"
                    })
        
        # Company-specific insights
        company_lower = company.lower()
        if any(term in company_lower for term in ['google', 'meta', 'facebook', 'amazon', 'microsoft', 'apple', 'netflix']):
            reasoning.append(f"🏢 {company} is a major tech company - roles are usually well-defined")
        
        if any(term in company_lower for term in ['defense', 'lockheed', 'raytheon', 'northrop', 'booz allen']):
            if recommendation != "resume://cyber":
                reasoning.append("⚠️ Defense contractors often value security clearance/cyber skills")
        
        if any(term in company_lower for term in ['openai', 'deepmind', 'anthropic', 'hugging face']):
            if recommendation != "resume://machine-learning":
                reasoning.append("⚠️ AI research companies typically prefer ML-focused resumes")
        
        return {
            "recommended_resume": recommendation,
            "resume_name": recommendation.split('://')[-1],
            "confidence": confidence,
            "reasoning": reasoning,
            "alternatives": alternatives,
            "analysis": {
                "keyword_scores": {
                    "software_engineering": swe_score,
                    "data_science": data_score,
                    "machine_learning": ml_score,
                    "cybersecurity": cyber_score,
                    "materials_science": matsci_score
                },
                "company": company,
                "position": position,
                "jd_provided": bool(job_description)
            }
        }
        
    
    
    async def list_resources(self) -> list:
        """
        List all available resume versions for tailored application strategies.
        
        Returns a list of different resume versions optimized for different
        roles or industries, allowing for selection of the most appropriate
        resume for each specific internship application.
        """
        return [
            {
                "uri": "resume://software-engineering",
                "name": "Software Engineering Resume",
                "mimeType": "text/plain",
                "description": "Resume tailored for software engineering and development roles, emphasizing coding projects, technical skills, and relevant coursework."
            },
            {
                "uri": "resume://data-science",
                "name": "Data Science Resume",
                "mimeType": "text/plain",
                "description": "Resume optimized for data science and analytics positions, highlighting statistical analysis, ML projects, and data tools."
            },
            {
                "uri": "resume://general-tech",
                "name": "General Tech Resume",
                "mimeType": "text/plain",
                "description": "Versatile resume suitable for various technical roles, product management, or when unsure of specific focus area."
            }
        ]

    async def read_resource(self, uri: str) -> str:
        """
        Read and return the content of a specified resume version.
        
        Args:
            uri: The unique resource identifier (e.g., "resume://software-engineering")
        
        Returns:
            The content of the requested resource as a string. For resumes,
            this includes the full text that can be analyzed to provide
            personalized recommendations for job applications, interview prep,
            and career development.
        
        Raises:
            ValueError: If the requested resource URI is not recognized
        """
        if uri in self.resume_map:
            file_path = self.resume_map[uri]
            
            # Check if file exists
            if not os.path.exists(file_path):
                return f"Resume file not found at: {file_path}\nPlease add your resume file to this location."
            
            # Read based on file extension
            if file_path.endswith('.pdf'):
                return self._read_pdf(file_path)
            else:  # Assume text file (.txt, .md, etc.)
                return self._read_text_file(file_path)
        
        raise ValueError(f"Unknown resource: {uri}. Available resources: {', '.join(self.resume_map.keys())}")
    
    async def call_tool(self, name: str, arguments: dict):
        """Route tool calls to appropriate methods"""
        if name == "get_applications":
            return await self.get_applications(**arguments)
        elif name == "add_application":
            return await self.add_application(**arguments)
        elif name == "update_status":
            return await self.update_application_status(**arguments)
        elif name == "update_details":
            return await self.update_application_details(**arguments)
        elif name == "schedule_interview":
            return await self.add_interview_to_calendar(**arguments)
        elif name == "get_upcoming_interviews":
            return await self.get_upcoming_interviews(**arguments)
        elif name == "create_study_schedule":
            return self.generate_study_schedule(**arguments)
        elif name == "get_interview_prep":
            return self.get_interview_prep(**arguments)
        elif name == "recommend_resume":
            return self.recommend_resume(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def get_applications(self, status_filter: Optional[str] = None, applied_only: Optional[bool] = False):
        """
        Fetch applications from sheet. The applications considered "applied" are those 
        that are either submitted, rejected, or have a technical, phone screen, 
        or interview scheduled. Applications in progress are applications 
        that have not fully filled out, and need to be filled in soon.
        Columns: A=Company, B=Position, C=Date Applied, D= Referral, 
                E=Application Status, F=Details, G=Applicant Portal
        
        Args:
            status_filter: Filter by specific status
            applied_only: If True, only return applications with status 
                        'Submitted', 'Rejected', 'Phone Screen/HireVue', 
                        'Technical', or 'Interview'
        """
        # Statuses that count as "applied"
        APPLIED_STATUSES = {
            'submitted', 
            'rejected', 
            'phone screen/hirevue', 
            'technical',
            'interview'
        }
        
        sheet = self.sheets_service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A{DATA_START_ROW}:G'
        ).execute()
        
        rows = result.get('values', [])
        applications = []
        
        for i, row in enumerate(rows, start=DATA_START_ROW):
            if not row or len(row) == 0 or not row[0]:  # Skip empty rows
                continue
                
            app = {
                'row': i,
                'company': row[0] if len(row) > 0 else '',
                'position': row[1] if len(row) > 1 else '',
                'date_applied': row[2] if len(row) > 2 else '',
                'referral_source': row[3] if len(row) > 3 else '',
                'status': row[4] if len(row) > 4 else '',
                'details': row[5] if len(row) > 5 else '',
                'portal': row[6] if len(row) > 6 else ''
            }
            
            # Filter by applied_only if requested
            if applied_only:
                if app['status'].lower().strip() not in APPLIED_STATUSES:
                    continue
            
            # Filter by specific status if requested
            if status_filter:
                if app['status'].lower() == status_filter.lower():
                    applications.append(app)
            else:
                applications.append(app)
        
        return applications
    
    def is_applied(self, status: str) -> bool:
        """
        Check if an application counts as "applied" based on status.
        
        APPLIED statuses:
        - Submitted
        - Rejected  
        - Phone Screen/HireVue
        - Technical
        - Interview (or any interview-related status)
        
        NOT APPLIED:
        - In Progress
        - Blank/Empty
        - Any other status
        
        Args:
            status: The application status string
            
        Returns:
            bool: True if the application is considered "applied", False otherwise
        """
        if not status or status.strip() == "":
            return False
        
        # Normalize the status
        status_lower = status.lower().strip()
        
        # Define applied statuses
        APPLIED_STATUSES = {
            'submitted',
            'rejected',
            'phone screen',
            'hirevue',
            'phone screen/hirevue',
            'technical',
            'interview'
        }
        
        # Check exact matches first
        if status_lower in APPLIED_STATUSES:
            return True
        
        # Check if status contains interview-related keywords
        if 'interview' in status_lower:
            return True
        
        # Check for phone screen variations
        if 'phone screen' in status_lower or 'hirevue' in status_lower:
            return True
        
        # Check for technical assessment variations
        if 'technical' in status_lower:
            return True
        
        # Everything else (including "In Progress") is NOT applied
        return False

    async def get_applications(self, status_filter: Optional[str] = None, applied_only: Optional[bool] = False):
        """
        Fetch applications from sheet. 
        
        APPLIED = Submitted, Rejected, Technical, Phone Screen/HireVue, or any interview status
        NOT APPLIED = In Progress, blank, or any other status
        
        Args:
            status_filter: Filter by specific status (case-insensitive)
            applied_only: If True, only return applications that count as "applied"
        """
        sheet = self.sheets_service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A{DATA_START_ROW}:G'
        ).execute()
        
        rows = result.get('values', [])
        applications = []
        
        for i, row in enumerate(rows, start=DATA_START_ROW):
            if not row or len(row) == 0 or not row[0]:  # Skip empty rows
                continue
                
            app = {
                'row': i,
                'company': row[0] if len(row) > 0 else '',
                'position': row[1] if len(row) > 1 else '',
                'date_applied': row[2] if len(row) > 2 else '',
                'referral_source': row[3] if len(row) > 3 else '',
                'status': row[4] if len(row) > 4 else '',
                'details': row[5] if len(row) > 5 else '',
                'portal': row[6] if len(row) > 6 else ''
            }
            
            # Filter by applied_only if requested
            if applied_only and not self.is_applied(app['status']):
                continue
            
            # Filter by specific status if requested
            if status_filter:
                if app['status'].lower().strip() == status_filter.lower().strip():
                    applications.append(app)
            else:
                applications.append(app)
        
        return applications
    
    async def add_application(self, company: str, position: str, 
                            date_applied: str, referral_source: str,
                            status: str = "In Progress", details: str = "",
                            portal: str = ""):
        """Add new application matching your sheet format"""
        sheet = self.sheets_service.spreadsheets()
        
        # Format: Company | Position | Date Applied | Referral | Status | Details | Portal
        values = [[company, position, date_applied, referral_source, status, details, portal]]
        body = {'values': values}
        
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A{DATA_START_ROW}:G',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return f"✅ Added: {position} at {company} (Status: {status})"
    
    async def update_application_status(self, row_num: int, new_status: str):
        """Update application status (Column E)"""
        sheet = self.sheets_service.spreadsheets()
        range_name = f'{SHEET_NAME}!E{row_num}'
        body = {'values': [[new_status]]}
        
        result = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return f"✅ Updated row {row_num} to: {new_status}"
    
    async def update_application_details(self, row_num: int, details: str):
        """Update details column (Column F)"""
        sheet = self.sheets_service.spreadsheets()
        range_name = f'{SHEET_NAME}!F{row_num}'
        body = {'values': [[details]]}
        
        result = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return f"✅ Updated details for row {row_num}"
    
    async def add_interview_to_calendar(self, company: str, position: str,
                                       interview_date: str, interview_time: str,
                                       duration_minutes: int = 60,
                                       notes: str = ""):
        """
        Add interview to Google Calendar
        Args:
            company: Company name
            position: Position title
            interview_date: Date in YYYY-MM-DD format
            interview_time: Time in HH:MM format (24-hour)
            duration_minutes: Interview duration
            notes: Additional notes
        """
        try:
            # Parse datetime
            start_datetime = datetime.strptime(
                f"{interview_date} {interview_time}", 
                "%Y-%m-%d %H:%M"
            )
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            
            # Create event
            event = {
                'summary': f'Interview: {position} at {company}',
                'description': f'Position: {position}\nCompany: {company}\n\n{notes}',
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'America/New_York',  # Adjust to your timezone
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},        # 1 hour before
                    ],
                },
            }
            
            event = self.calendar_service.events().insert(
                calendarId='primary', 
                body=event
            ).execute()
            
            return f"📅 Interview scheduled: {company} on {interview_date} at {interview_time}\nCalendar link: {event.get('htmlLink')}"
        
        except Exception as e:
            return f"❌ Error scheduling interview: {str(e)}"
    
    async def get_upcoming_interviews(self, days_ahead: int = 14):
        """Get upcoming interviews from calendar"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            future = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=future,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime',
                q='Interview'  # Search for events with "Interview" in title
            ).execute()
            
            events = events_result.get('items', [])
            
            interviews = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                interviews.append({
                    'summary': event['summary'],
                    'start': start,
                    'description': event.get('description', ''),
                    'link': event.get('htmlLink', '')
                })
            
            return interviews
        
        except Exception as e:
            return f"❌ Error fetching interviews: {str(e)}"
    
    def generate_study_schedule(self, interview_date: str, topics: list[str], 
                               days_available: int):
        """Generate personalized study schedule"""
        schedule = []
        topics_per_day = max(1, len(topics) // max(1, days_available))
        
        interview_dt = datetime.strptime(interview_date, "%Y-%m-%d")
        
        for i in range(0, len(topics), topics_per_day):
            day_topics = topics[i:i+topics_per_day]
            day_num = i // topics_per_day + 1
            study_date = datetime.now() + timedelta(days=day_num-1)
            
            schedule.append({
                'day': day_num,
                'date': study_date.strftime("%Y-%m-%d"),
                'topics': day_topics,
                'morning': [f"Review {topic} fundamentals (1 hour)" for topic in day_topics],
                'afternoon': [f"Practice {day_topics[0]} problems (2 hours)"],
                'evening': ["Mock interview or review mistakes (1 hour)"]
            })
        
        return schedule
    
    def get_interview_prep_plan(self, position: str):
        """Generate interview prep based on position keywords"""
        position_lower = position.lower()
        
        # Detect role type from position
        if any(term in position_lower for term in ['software', 'swe', 'engineer', 'development']):
            role_type = 'software'
        elif any(term in position_lower for term in ['data', 'analytics', 'ds']):
            role_type = 'data'
        elif any(term in position_lower for term in ['cyber', 'security', 'infosec']):
            role_type = 'cybersecurity'
        elif any(term in position_lower for term in ['ml', 'machine learning', 'ai']):
            role_type = 'ml'
        else:
            role_type = 'general'
        
        prep_plans = {
            'software': {
                'topics': [
                    'Data Structures (Arrays, LinkedLists, Trees, Graphs, HashMaps)',
                    'Algorithms (Sorting, Searching, Dynamic Programming)',
                    'System Design Basics',
                    'OOP Concepts',
                    'Time & Space Complexity'
                ],
                'resources': [
                    'LeetCode (focus on Medium problems)',
                    'NeetCode roadmap',
                    'Cracking the Coding Interview',
                    'System Design Primer (GitHub)'
                ],
                'daily_practice': '2-3 LeetCode problems, 1 system design question',
                'mock_interviews': '2 per week'
            },
            'data': {
                'topics': [
                    'SQL (Joins, Subqueries, Window Functions, CTEs)',
                    'Pandas (DataFrames, GroupBy, Merge, Pivot)',
                    'Statistics (Distributions, Hypothesis Testing, A/B Testing)',
                    'Data Visualization (Matplotlib, Seaborn, Tableau)',
                    'Python fundamentals'
                ],
                'resources': [
                    'Mode Analytics SQL Tutorial',
                    'Pandas Documentation + Practice',
                    'Kaggle Datasets',
                    'DataCamp SQL Track',
                    'Storytelling with Data (book)'
                ],
                'daily_practice': '2 SQL challenges, analyze 1 dataset',
                'mock_interviews': '1-2 per week with case studies'
            },
            'cybersecurity': {
                'topics': [
                    'Network Security (TCP/IP, Firewalls, VPNs)',
                    'Cryptography basics',
                    'Common vulnerabilities (OWASP Top 10)',
                    'Security tools (Wireshark, Nmap, Metasploit)',
                    'Incident response process'
                ],
                'resources': [
                    'TryHackMe or HackTheBox',
                    'OWASP documentation',
                    'CompTIA Security+ study materials',
                    'Cybrary courses'
                ],
                'daily_practice': 'Complete 1-2 CTF challenges',
                'mock_interviews': '1 per week + technical scenarios'
            },
            'ml': {
                'topics': [
                    'ML Algorithms (Linear/Logistic Regression, Trees, Neural Nets)',
                    'Model Evaluation (Precision, Recall, F1, ROC-AUC)',
                    'Feature Engineering',
                    'Deep Learning basics',
                    'Python (NumPy, Scikit-learn, TensorFlow/PyTorch)'
                ],
                'resources': [
                    'Andrew Ng ML Course (Coursera)',
                    'Hands-On ML with Scikit-Learn (book)',
                    'Kaggle Competitions',
                    'Fast.ai course'
                ],
                'daily_practice': 'Work on 1 Kaggle dataset, implement 1 algorithm',
                'mock_interviews': '1-2 per week'
            },
            'general': {
                'topics': [
                    'Company research',
                    'STAR method for behavioral questions',
                    'Technical fundamentals for role',
                    'Past projects deep-dive'
                ],
                'resources': [
                    'Glassdoor interview reviews',
                    'Company website & recent news',
                    'LinkedIn company page'
                ],
                'daily_practice': 'Practice behavioral stories, review resume',
                'mock_interviews': '2 behavioral per week'
            }
        }
        
        return prep_plans.get(role_type, prep_plans['general'])

# Initialize MCP server
app = Server("internship-coach")
coach = InternshipCoach()
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_applications",
            description="Fetch applications. APPLIED = Submitted, Rejected, Technical, Phone Screen/HireVue, or interview statuses. In Progress or blank = NOT applied.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string", 
                        "description": "Filter by status (Submitted, In Progress, Rejected, Phone Screen/HireVue, Technical, etc.)"
                    }
                }
            }
        ),
        Tool(
            name="add_application",
            description="Add new internship application to tracking sheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name"},
                    "position": {"type": "string", "description": "Position title"},
                    "date_applied": {"type": "string", "description": "Date applied (M/D/YY format)"},
                    "referral_source": {"type": "string", "description": "How you applied (LinkedIn/Online, Internal Referral, Handshake, etc.)"},
                    "status": {"type": "string", "description": "Application status (default: In Progress)"},
                    "details": {"type": "string", "description": "Additional details or notes"},
                    "portal": {"type": "string", "description": "Applicant portal link"}
                },
                "required": ["company", "position", "date_applied", "referral_source"]
            }
        ),
        Tool(
            name="update_status",
            description="Update application status in sheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "row_num": {"type": "number", "description": "Row number in sheet (starts at 16)"},
                    "new_status": {"type": "string", "description": "New status"}
                },
                "required": ["row_num", "new_status"]
            }
        ),
        Tool(
            name="update_details",
            description="Update details/notes for an application",
            inputSchema={
                "type": "object",
                "properties": {
                    "row_num": {"type": "number", "description": "Row number in sheet"},
                    "details": {"type": "string", "description": "Details to add"}
                },
                "required": ["row_num", "details"]
            }
        ),
        Tool(
            name="schedule_interview",
            description="Add interview to Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name"},
                    "position": {"type": "string", "description": "Position title"},
                    "interview_date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "interview_time": {"type": "string", "description": "Time (HH:MM in 24-hour format)"},
                    "duration_minutes": {"type": "number", "description": "Duration in minutes (default: 60)"},
                    "notes": {"type": "string", "description": "Additional notes"}
                },
                "required": ["company", "position", "interview_date", "interview_time"]
            }
        ),
        Tool(
            name="get_upcoming_interviews",
            description="Get upcoming interviews from calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "number", "description": "Days to look ahead (default: 14)"}
                }
            }
        ),
        Tool(
            name="create_study_schedule",
            description="Generate personalized study schedule for interview prep",
            inputSchema={
                "type": "object",
                "properties": {
                    "interview_date": {"type": "string", "description": "Interview date (YYYY-MM-DD)"},
                    "topics": {"type": "array", "items": {"type": "string"}, "description": "Topics to study"},
                    "days_available": {"type": "number", "description": "Days until interview"}
                },
                "required": ["interview_date", "topics", "days_available"]
            }
        ),
        Tool(
            name="get_interview_prep",
            description="Get customized interview prep plan based on position",
            inputSchema={
                "type": "object",
                "properties": {
                    "position": {"type": "string", "description": "Position title"}
                },
                "required": ["position"]
            }
        ),
        Tool(
            name="recommend_resume",
            description="Recommend which resume version to use for a specific application. Analyzes the position title, company, and optional job description to suggest the most appropriate resume from your available versions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Name of the company you are applying to."},
                    "position": {"type": "string", "description": "Job title of the position you are targeting."},
                    "job_description": {"type": "string", "description": "Optional: full job description text to help the recommendation."}
                },
                "required": ["company", "position"]
            }
        )
    ]

@app.list_resources()
async def list_resources():
    """Expose available resources including the user's resume for personalized coaching."""
    return await coach.list_resources()

@app.read_resource()
async def read_resource(uri: str):
    """Retrieve resource content to provide context-aware internship guidance."""
    return await coach.read_resource(uri)

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    try:
        result = await coach.call_tool(name, arguments)
        
        # Convert result to TextContent
        if isinstance(result, str):
            return [TextContent(type="text", text=result)]
        elif isinstance(result, (dict, list)):
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        else:
            return [TextContent(type="text", text=str(result))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Run the MCP server"""
    coach.authenticate_google()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())