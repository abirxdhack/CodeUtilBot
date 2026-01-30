#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import re
import os
import psutil
from telethon import events, Button
from bot import CodeUtilBot
import config
from utils import LOGGER

try:
    from modules.host import projects, project_processes, get_project_text, get_project_buttons
except ImportError:
    projects = {}
    project_processes = {}
    def get_project_text(project):
        return ""
    def get_project_buttons(project_name):
        return []

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
stop_pattern = re.compile(rf'^[{prefixes}]stop$', re.IGNORECASE)

@CodeUtilBot.on(events.NewMessage(pattern=stop_pattern))
async def stop_command_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} requested stop selection")
    
    user_projects = {name: proj for name, proj in projects.items() if proj['owner_id'] == user_id}
    running_projects = {name: proj for name, proj in user_projects.items() if proj['pid'] and psutil.pid_exists(proj['pid'])}
    
    if not user_projects:
        await event.respond(
            "**📂 You don't have any projects yet!**\n\n"
            "**Use `/new` to create your first project.**"
        )
        raise events.StopPropagation
    
    if not running_projects:
        await event.respond(
            "**⚠️ No running projects found!**\n\n"
            "**All your projects are offline.**"
        )
        raise events.StopPropagation
    
    buttons = []
    project_names = list(running_projects.keys())
    
    for i in range(0, len(project_names), 2):
        row = []
        row.append(Button.inline(f"⏹ {project_names[i]}", f"stopproject_{project_names[i]}".encode()))
        if i + 1 < len(project_names):
            row.append(Button.inline(f"⏹ {project_names[i + 1]}", f"stopproject_{project_names[i + 1]}".encode()))
        buttons.append(row)
    
    text = (
        f"**⏹ Select Project To Stop**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Running Projects:** {len(running_projects)}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Choose a project:**"
    )
    
    await event.respond(text, buttons=buttons)
    raise events.StopPropagation

@CodeUtilBot.on(events.CallbackQuery(pattern=b"stopproject_.*"))
async def stop_project_callback(event):
    data = event.data.decode()
    project_name = data[12:]
    user_id = event.sender_id
    
    if project_name not in projects:
        await event.answer("❌ Project not found!", alert=True)
        return
    
    project = projects[project_name]
    
    if project['owner_id'] != user_id:
        await event.answer("❌ You don't own this project!", alert=True)
        return
    
    if not project['pid'] or not psutil.pid_exists(project['pid']):
        await event.answer("⚠️ Project is not running!", alert=True)
        return
    
    LOGGER.info(f"User {user_id} stopping project {project_name}")
    
    await event.answer("Stopping project...", alert=False)
    msg = await event.edit(f"**Stopping project `{project_name}`...**")
    
    try:
        process = project_processes.get(project_name)
        if process:
            os.killpg(os.getpgid(process.pid), 9)
        else:
            proc = psutil.Process(project['pid'])
            proc.terminate()
            proc.wait(timeout=5)
        
        project['last_pid'] = project['pid']
        project['last_ram'] = project['ram']
        
        project['pid'] = None
        project['ram'] = None
        project['status'] = 'Offline ❌'
        
        if project_name in project_processes:
            del project_processes[project_name]
        
        LOGGER.info(f"Project {project_name} stopped successfully")
        
        text = get_project_text(project)
        buttons = get_project_buttons(project_name)
        
        await msg.edit(text, buttons=buttons)
        await event.answer("✅ Project stopped!", alert=False)
        
    except Exception as e:
        LOGGER.exception(f"Error stopping project {project_name}")
        await event.answer(f"❌ Error: {str(e)}", alert=True)