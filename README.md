Internship Coach MCP Server
AI-powered internship application tracker with Google Sheets and Calendar integration.

Setup
1. Install Dependencies
bash
pip install -r requirements.txt
2. Google Cloud Setup
Go to Google Cloud Console
Create a new project: internship-coach
Enable APIs:
Google Sheets API
Google Calendar API
Create OAuth 2.0 credentials (Desktop app)
Download credentials.json and place in this directory
3. Configure Spreadsheet
Update SPREADSHEET_ID in internship_coach_mcp.py:

python
SPREADSHEET_ID = 'your-spreadsheet-id-here'
4. Configure Claude Desktop
Edit ~/Library/Application Support/Claude/claude_desktop_config.json (Mac) or equivalent:

json
{
  "mcpServers": {
    "internship-coach": {
      "command": "python",
      "args": ["/full/path/to/internship_coach_mcp.py"]
    }
  }
}
5. First Run
Start Claude Desktop
Browser will open for Google authentication
Grant permissions
token.pickle will be created
You're ready to go!
Usage
Talk naturally to Claude:

"Add my Microsoft application to the tracker"
"Show me all my In Progress applications"
"Schedule my Google interview for next Tuesday at 2pm"
"Create a study schedule for my Amazon interview"
Features
✅ Google Sheets integration
✅ Google Calendar scheduling
✅ Interview prep plans
✅ Study schedule generation
✅ Status tracking
✅ Natural language interface
Security
NEVER commit these files:

credentials.json (OAuth client secret)
token.pickle (Your access token)
These are listed in .gitignore

Troubleshooting
"Can't find credentials.json": Make sure it's in the same directory as the script

"Authentication failed": Delete token.pickle and re-authenticate

"Sheet not found": Check your SPREADSHEET_ID is correct

Support
For issues, check:

Google Sheets API Docs
Google Calendar API Docs
MCP Documentation
