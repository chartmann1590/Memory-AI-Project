# 🧠 Memory AI Project

Welcome to the **Memory AI Project** — a smart, innovative solution combining local AI technology with memory transcription, summarization, task management, speaker tagging, chat capabilities, and Single Sign-On (SSO) authentication.

## 🚀 Features

- **User Authentication** 🔐
  - Secure user login and registration.
  - Supports local accounts and Single Sign-On (SSO) with Authentik.

- **Audio Recording and Transcription** 🎙️
  - Record audio directly from your browser.
  - Automatic transcription using OpenAI Whisper.

- **Summarization and Analysis** 📖
  - Summarize transcribed audio with Ollama.
  - Extract actionable TODOs automatically.

- **Task Management** ✅
  - Add, complete, and archive tasks easily.
  - Intuitive dashboard to manage tasks and recordings.

- **Speaker Tagging** 🗣️
  - Easily tag and identify speakers within audio recordings.

- **Chat with Recordings** 💬
  - Start chat sessions referencing selected transcriptions.
  - Interact naturally with the integrated AI for detailed insights.

- **Responsive and User-Friendly Interface** 🎨
  - Clean, Bootstrap-based design for optimal usability.

---

## 📥 Setup Instructions

### 🛠️ Prerequisites
Ensure the following software is installed:

- Python 3.8+
- pip
- Ollama

### 📂 Clone the Repository

```bash
git clone https://github.com/yourusername/memory-ai-project.git
cd memory-ai-project
```

### 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

### ⚙️ Environment Configuration
Create a `.env` file based on the provided `.env` template:

```env
SECRET_KEY=your_secret_key
SQLALCHEMY_DATABASE_URI=sqlite:///site.db
AUTHENTIK_SSO_URL=your_authentik_url
AUTHENTIK_CLIENT_ID=your_authentik_client_id
AUTHENTIK_CLIENT_SECRET=your_authentik_client_secret
AUTHENTIK_REDIRECT_URI=your_authentik_redirect_uri
OLLAMA_API_URL=your_ollama_api_url
OLLAMA_MODEL=your_ollama_model
```

### 🗃️ Database Initialization

```bash
python run.py
```

This automatically creates the database and necessary tables.

### 🌐 Running the Application

```bash
python run.py
```

Visit `http://localhost:5000` to access the application.

---

## 📚 Project Structure
```
memory-ai-project/
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── chat.py
│   ├── dashboard.py
│   ├── models.py
│   └── templates/
│       ├── base.html
│       ├── chat.html
│       ├── chat_session.html
│       ├── dashboard.html
│       ├── index.html
│       ├── login.html
│       ├── new_chat.html
│       ├── recording_edit.html
│       ├── recording_view.html
│       ├── register.html
│       └── sso_callback.html
├── config.py
├── requirements.txt
├── .env
└── run.py
```

---

## 🤝 Contribution
Contributions are welcome! Please submit a pull request or open an issue to discuss changes or improvements.

---

## 📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

---

✨ **Happy Coding!** ✨