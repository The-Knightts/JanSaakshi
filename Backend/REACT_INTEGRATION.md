# JanSaakshi Production API - React Integration Guide

## Quick Start

### 1. Run the API
```bash
cd Backend
uvicorn main_real_app:app --reload --host 0.0.0.0 --port 8000
```

### 2. API Endpoints for React

#### **POST /ask** - Main Query Endpoint
Ask any question about meetings

**Request:**
```javascript
fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: "What is planned with Bombay Gymkhana?",
    prompt: "Focus on budget and timeline",  // Optional custom prompt
    ward: "Ward 37"  // Optional ward filter
  })
})
```

**Response:**
```json
{
  "success": true,
  "summary": "Detailed AI-generated summary...",
  "meetings": [
    {
      "meeting_id": "MEET-20250115-ABC",
      "objective": "Infrastructure planning",
      "meeting_date": "2025-01-15",
      "ward": "Ward 37",
      "venue": "Bombay Gymkhana",
      "attendees_present": ["John Doe", "Jane Smith"],
      "projects_discussed_list": ["Road repair", "Drainage"]
    }
  ],
  "count": 1
}
```

---

#### **POST /upload-pdf** - Upload Meeting Minutes
Upload PDF to extract and store meeting data

**Request:**
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

fetch('http://localhost:8000/upload-pdf', {
  method: 'POST',
  body: formData
})
```

**Response:**
```json
{
  "success": true,
  "message": "PDF processed successfully",
  "meeting_id": "MEET-20250115-ABC",
  "data": { /* extracted meeting data */ }
}
```

---

#### **GET /meetings** - List All Meetings
Get list of meetings with optional filtering

**Request:**
```javascript
fetch('http://localhost:8000/meetings?limit=20&ward=Ward%2037')
```

**Response:**
```json
{
  "success": true,
  "meetings": [ /* array of meetings */ ],
  "count": 5
}
```

---

#### **GET /meeting/{meeting_id}** - Get Specific Meeting
Fetch details of a single meeting

**Request:**
```javascript
fetch('http://localhost:8000/meeting/MEET-20250115-ABC')
```

---

#### **GET /health** - Health Check
Check API status

**Request:**
```javascript
fetch('http://localhost:8000/health')
```

**Response:**
```json
{
  "status": "healthy",
  "meetings_count": 42
}
```

---

## React Example Component

```jsx
import { useState } from 'react';

function MeetingSearch() {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input 
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask about meetings..."
      />
      <button onClick={handleSearch} disabled={loading}>
        {loading ? 'Searching...' : 'Search'}
      </button>

      {result && result.success && (
        <div>
          <h3>Summary</h3>
          <p>{result.summary}</p>
          
          <h3>Meetings Found: {result.count}</h3>
          {result.meetings.map(meeting => (
            <div key={meeting.meeting_id}>
              <h4>{meeting.objective}</h4>
              <p>Date: {meeting.meeting_date}</p>
              <p>Ward: {meeting.ward}</p>
              <p>Venue: {meeting.venue}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default MeetingSearch;
```

---

## Features

✅ **Fast & Lightweight** - Optimized for production  
✅ **Smart Search** - Finds meetings using any keyword  
✅ **OCR Support** - Extracts text from PDF meeting minutes  
✅ **AI Summaries** - Detailed, friendly summaries  
✅ **Custom Prompts** - Ask specific questions  
✅ **CORS Enabled** - Works with React frontend  
✅ **Clean API** - Simple, predictable responses  

---

## Environment Setup

Create `.env` file:
```
SARVAM_API_KEY=your_api_key_here
SARVAM_API_URL=https://api.sarvam.ai/v1/chat/completions
SARVAM_MODEL=your_model_name
SARVAM_DOC_LANGUAGE=en-IN
```

---

## Production Deployment

```bash
# Install dependencies
pip install fastapi uvicorn python-multipart sarvamai python-dotenv

# Run production server
uvicorn main_real_app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Notes

- All responses include `success: true/false` for easy error handling
- Meeting data is automatically parsed (JSON arrays for attendees/projects)
- Smart keyword extraction works without "meeting" keyword
- Supports custom prompts for focused queries
- Fast execution with minimal complexity
