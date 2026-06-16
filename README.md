AI-Based Smart Support Ticket Resolution System

An intelligent support ticket analysis and recommendation system that uses AI + LLMs to:
Automatically analyze support tickets
Predict ticket category, priority, and tags
Recommend relevant knowledge base (KB) articles
Detect content gaps
Provide an analytics dashboard for tracking system performance

This project includes a Flask backend, a Streamlit analytics dashboard, and a beautiful front-end interface for uploading tickets and viewing AI-powered insights.

🌐 Live Deployment
Service :
AI Ticket Analyzer - https://ai-ticket-resolution-system.onrender.com 
Admin Panel - https://ai-ticket-resolution-system.onrender.com/admin 

Demo Credentials
Username - admin
Password - changeme

🚀 Features - 
🧠 AI Ticket Analyzer
Extracts key information from PDF/txt/CSV support tickets
Predicts category, priority, and tags
Suggests solution summary
Recommends relevant KB articles
Shows similar tickets using embeddings

📊 Analytics Dashboard (Streamlit)
Ticket trends over time
Ticket distribution by category
Priority breakdown (High/Medium/Low)
Most frequent tags (Word Cloud)
Knowledge Base articles count
Content gaps visualized
Downloadable CSVs of insights

🔐 Admin Panel
View latest LLM logs
Download CSV/JSONL files
View feedback & gaps
Manage data files (feedback, processed tickets, KB articles)

🏗️ Project Structure
AI_Ticker_Support/
│
├── app.py                     # Flask backend
├── dashboard.py               # Streamlit dashboard
├── static/                    # Front-end CSS, JS
├── templates/                 # HTML pages
│   ├── index.html             # Ticket upload UI
│   ├── admin_logs.html        # Admin panel
│
├── data/
│   ├── feedback.csv
│   ├── knowledge_base.csv
│   ├── content_gaps.csv
│   ├── llm_logs.jsonl
│   └── processed_tickets.csv
│
├── venv/                      # Virtual environment
└── README.md

🛠️ Tech Stack
Backend
Python
Flask
Pandas
NumPy
OpenAI LLM APIs
tiktoken
PyPDF2

Frontend
HTML/CSS
Jinja2 Templates
Tailwind-like custom UI styling
Dashboard
Streamlit
Plotly
Matplotlib
WordCloud

⚙️ Installation & Setup (Full Guide)
1️⃣ Clone the repo
git clone <your-repo-url>
cd AI_Ticker_Support-main

2️⃣ Create & activate virtual environment
python -m venv venv

Windows:
venv\Scripts\activate

Mac/Linux:
source venv/bin/activate

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Add your OpenAI API key

Create .env file:
OPENAI_API_KEY=your_key_here

5️⃣ Run the Flask backend
python app.py

Backend will start on:
http://localhost:5000

6️⃣ Run the analytics dashboard
Open a second terminal:
streamlit run dashboard.py

Dashboard opens at:
http://localhost:8501

🧪 Screenshots
🔵 Dashboard — Analytics Overview
![Screenshot_14-11-2025_222219_localhost](https://github.com/user-attachments/assets/71477b52-678d-4a32-8507-a54e422eca39)

🟢 AI Ticket Analyzer — Upload & Analysis UI
![Screenshot_14-11-2025_222254_localhost](https://github.com/user-attachments/assets/5f4b65ee-6243-4c02-8e6f-3697ad3314d9)

🟣 Admin Panel — Logs & Feedback
![Screenshot_14-11-2025_222317_localhost](https://github.com/user-attachments/assets/fdaa80ed-8772-4726-81c5-febaebbec3b1)

🔌 API Endpoints Overview
POST /analyze
Analyze ticket content.

POST /feedback
Save finalized category/tags/priority.

GET /admin/api/feedback
Fetch feedback data (dashboard use).

GET /admin/api/gaps
Fetch content gaps.

GET /admin/api/knowledge_base
Fetch KB articles.

🚧 Future Improvements
Real-time ticket classification API
Multi-agent architecture (classifier, summarizer, KB-retriever)
User authentication for dashboard
Auto-detect and update KB articles
SQL database instead of CSV

📄 License
This project is licensed under the MIT License.
