# CodeUtil ⚙️ Bot

![CodeUtil Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)

An advanced Telegram-based **code hosting, file management, and project control bot** with a built-in **FastAPI web editor**.

---

## 📖 Overview

The **CodeUtil ⚙️ Bot** is a powerful Telegram bot built with **Python** and **Telethon**, designed to help users create, manage, edit, deploy, and control code projects directly from Telegram.

It combines a **Telegram bot interface** with a **FastAPI-powered web file editor**, allowing real-time file editing, uploads, downloads, and project lifecycle management using shared secure sessions.

This project is maintained by [abirxdhack](https://github.com/abirxdhack).

---

## ✨ Features

- **Project Hosting via Telegram**: Create and manage multiple projects directly from bot commands.
- **Web-Based File Editor**: Edit project files securely through a FastAPI-powered interface.
- **Shared Session System**: Bot and API share session keys for secure access.
- **Process Control**: Start, stop, restart, and delete running projects.
- **Interactive UI**: Inline buttons and menus for easy navigation.
- **Asynchronous & Fast**: Uses `uvloop` for high performance.
- **Modular Design**: Easy to extend with new modules and commands.

---

## 📋 Prerequisites

Before setting up the bot, make sure you have:

- **Python 3.9+**
- **Telegram API Credentials**
  - `API_ID`
  - `API_HASH`  
  Get them from [my.telegram.org](https://my.telegram.org)
- **Bot Token**  
  Create a bot using [BotFather](https://t.me/BotFather)
- **Linux VPS / Server** (recommended for hosting projects)

---

## 🛠 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/abirxdhack/CodeUtilBot.git
cd CodeUtilBot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

Edit `config.py` and add your credentials:

```python
# Copyright @ISmartCoder
# Updates Channel @abirxdhackz

API_ID = 123456
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

UPDATE_CHANNEL_URL = "t.me/abirxdhackz"
COMMAND_PREFIXES = ['/', '!', '.', ',', '$', '#']
API_BASE_URL = "http://0.0.0.0:8000"
```

---

## 🚀 Usage

### 1. Run the Bot

```bash
python main.py
```

You should see logs indicating:

- Telegram bot started
- FastAPI server running on port 8000
- Handler modules loaded successfully

### 2. Interact on Telegram

- Open Telegram and start your bot
- Use `/start` to open the main menu
- Create projects, deploy files, edit code, and manage services

---

## 🧠 Project Architecture

```
Telegram User
     ↓
Telethon Bot (Commands & Menus)
     ↓
Shared Sessions (edit_sessions)
     ↓
FastAPI Web Editor
     ↓
Project Files & Processes
```

---

## 📁 Project Structure

```
core/       - Core bot commands
miscs/      - Callback & UI handlers
modules/    - Project management modules
api/        - FastAPI file editor server
templates/  - Web editor UI
utils/      - Logging & helpers
bot.py      - Telethon client
main.py     - Bot + API runner
config.py   - Configuration
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository  
2. Create a new branch (`git checkout -b feature/your-feature`)  
3. Commit your changes  
4. Push to your branch  
5. Open a Pull Request  

---

## 📧 Contact

For support, updates, or suggestions:

- **GitHub**: abirxdhack  
- **Telegram**: @ISmartCoder  
- **Updates Channel**: @abirxdhackz
