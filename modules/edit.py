#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import re
import secrets
import hashlib
from telethon import events, Button
from telethon.tl.types import KeyboardButtonCopy
from bot import CodeUtilBot
import config
from utils import LOGGER

edit_sessions = {}

try:
    from modules.host import projects
except ImportError:
    projects = {}

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
edit_pattern = re.compile(rf'^[{prefixes}]edit$', re.IGNORECASE)

def generate_credentials():
    username = secrets.token_urlsafe(12)
    password = secrets.token_urlsafe(16)
    return username, password

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@CodeUtilBot.on(events.NewMessage(pattern=edit_pattern))
async def edit_command_handler(event):
    user_id = event.sender_id

    LOGGER.info(f"User {user_id} requested edit selection")

    user_projects = {name: proj for name, proj in projects.items() if proj['owner_id'] == user_id}

    if not user_projects:
        await event.respond(
            "**📂 You don't have any projects yet!**\n\n"
            "**Use `/new` or `/deploy` to create your first project.**"
        )
        raise events.StopPropagation

    buttons = []
    project_names = list(user_projects.keys())

    for i in range(0, len(project_names), 2):
        row = []
        row.append(Button.inline(f"✏️ {project_names[i]}", f"editproj_{project_names[i]}".encode()))
        if i + 1 < len(project_names):
            row.append(Button.inline(f"✏️ {project_names[i + 1]}", f"editproj_{project_names[i + 1]}".encode()))
        buttons.append(row)

    text = (
        f"**✏️ Select Project To Edit Files**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Total Projects:** {len(user_projects)}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Choose a project:**"
    )

    await event.respond(text, buttons=buttons)
    raise events.StopPropagation

@CodeUtilBot.on(events.CallbackQuery(pattern=b"editproj_.*"))
async def edit_project_callback(event):
    data = event.data.decode()
    project_name = data[9:]
    user_id = event.sender_id

    if project_name not in projects:
        await event.answer("❌ Project not found!", alert=True)
        return

    project = projects[project_name]

    if project['owner_id'] != user_id:
        await event.answer("❌ You don't own this project!", alert=True)
        return

    LOGGER.info(f"User {user_id} generating edit session for {project_name}")

    await event.answer("Generating credentials...", alert=False)

    username, password = generate_credentials()
    password_hash = hash_password(password)

    session_id = secrets.token_urlsafe(32)

    edit_sessions[session_id] = {
        'project_name': project_name,
        'project_path': project['path'],
        'username': username,
        'password_hash': password_hash,
        'user_id': user_id,
        'owner_name': project['owner_name']
    }

    api_url = config.API_BASE_URL
    edit_url = f"{api_url}?session={session_id}"

    text = (
        f"**🔍 Edit Access Granted Successfully 📋**\n"
        f"**━━━━━━━━━━━━━━━━━━**\n\n"
        f"**• Project's Name:** `{project_name}`\n"
        f"**• Project's Size:** {project['size']}\n"
        f"**• Project's Owner:** [{project['owner_name']}]({project['owner_link']})\n"
        f"**• Script Change URL:** [Click Me 📄]({edit_url})\n\n"
        f"**👤 Username:** `{username}`\n"
        f"**🔑 Password:** `{password}`\n"
        f"**━━━━━━━━━━━━━━━━━━**\n\n"
        f"**🔍 Smart Code Editor WebApp ✅**\n\n"
    )

    buttons = [
        [Button.url("⬇️ Open Editor Panel", edit_url)],
        [
            KeyboardButtonCopy(text="👤 Username", copy_text=username),
            KeyboardButtonCopy(text="🔑 Password", copy_text=password)
        ]
    ]

    await event.edit(text, buttons=buttons, link_preview=False)

    LOGGER.info(f"Edit session created for {project_name}: session_id={session_id}")