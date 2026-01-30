#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import re
from pathlib import Path
from telethon import events, Button
from bot import CodeUtilBot
import config
from utils import LOGGER

try:
    from modules.host import projects
except ImportError:
    projects = {}

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
logs_pattern = re.compile(rf'^[{prefixes}]logs$', re.IGNORECASE)

@CodeUtilBot.on(events.NewMessage(pattern=logs_pattern))
async def logs_command_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} requested logs selection")
    
    user_projects = {name: proj for name, proj in projects.items() if proj['owner_id'] == user_id}
    
    if not user_projects:
        await event.respond(
            "**📂 You don't have any projects yet!**\n\n"
            "**Use `/new` to create your first project.**"
        )
        raise events.StopPropagation
    
    buttons = []
    project_names = list(user_projects.keys())
    
    for i in range(0, len(project_names), 2):
        row = []
        row.append(Button.inline(f"📄 {project_names[i]}", f"viewlogs_{project_names[i]}".encode()))
        if i + 1 < len(project_names):
            row.append(Button.inline(f"📄 {project_names[i + 1]}", f"viewlogs_{project_names[i + 1]}".encode()))
        buttons.append(row)
    
    text = (
        f"**📄 Select Project To View Logs**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Total Projects:** {len(user_projects)}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Choose a project:**"
    )
    
    await event.respond(text, buttons=buttons)
    raise events.StopPropagation

@CodeUtilBot.on(events.CallbackQuery(pattern=b"viewlogs_.*"))
async def view_logs_callback(event):
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
    
    LOGGER.info(f"User {user_id} viewing logs for {project_name}")
    
    await event.answer("Fetching logs...", alert=False)
    
    project_path = Path(project['path'])
    log_file = project_path / "logs" / "output.log"
    
    if not log_file.exists():
        await event.edit(f"**❌ No logs found for project `{project_name}`**")
        return
    
    caption = (
        f"**📄 Logs for Project: `{project_name}`**\n\n"
        f"**Owner:** {project['owner_name']}\n"
        f"**Status:** {project['status']}\n"
        f"**Run Command:** `{project['run_command']}`"
    )
    
    await CodeUtilBot.send_file(
        event.chat_id,
        log_file,
        caption=caption
    )
    
    await event.edit(f"**✅ Logs sent for project `{project_name}`**")