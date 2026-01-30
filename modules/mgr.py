#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import re
from telethon import events, Button
from bot import CodeUtilBot
import config
from utils import LOGGER

try:
    from modules.host import projects
except ImportError:
    projects = {}

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
mgr_pattern = re.compile(rf'^[{prefixes}]mgr$', re.IGNORECASE)

@CodeUtilBot.on(events.NewMessage(pattern=mgr_pattern))
async def manager_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} accessed project manager")
    
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
        row.append(Button.inline(project_names[i], f"manage_{project_names[i]}".encode()))
        if i + 1 < len(project_names):
            row.append(Button.inline(project_names[i + 1], f"manage_{project_names[i + 1]}".encode()))
        buttons.append(row)
    
    total_projects = len(user_projects)
    online_count = sum(1 for proj in user_projects.values() if proj['status'] == 'Online ✅')
    offline_count = total_projects - online_count
    
    text = (
        f"**📂 Your Projects Manager**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Total Projects:** {total_projects}\n"
        f"**Online:** {online_count} ✅\n"
        f"**Offline:** {offline_count} ❌\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Select a project to manage:**"
    )
    
    await event.respond(text, buttons=buttons)
    raise events.StopPropagation