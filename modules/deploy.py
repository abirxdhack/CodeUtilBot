#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import re
import asyncio
import zipfile
import shutil
import psutil
from pathlib import Path
from datetime import datetime
from telethon import events, Button
from telethon.tl.types import DocumentAttributeFilename
from bot import CodeUtilBot
import config
from utils import LOGGER

try:
    from modules.host import projects, project_processes, PROJECTS_DIR, get_size, clean_junk_files, get_simple_text, get_simple_button, get_project_text, get_project_buttons, start_project_process
except ImportError:
    projects = {}
    project_processes = {}
    PROJECTS_DIR = Path("downloads")
    PROJECTS_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
deploy_pattern = re.compile(rf'^[{prefixes}]deploy$', re.IGNORECASE)
restart_pattern = re.compile(rf'^[{prefixes}]restart$', re.IGNORECASE)

@CodeUtilBot.on(events.NewMessage(pattern=deploy_pattern))
async def deploy_command_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} initiated deploy command")
    
    if not event.is_reply:
        await event.respond("**Please Reply To A Zip File To Deploy ❌**")
        raise events.StopPropagation
    
    replied_msg = await event.get_reply_message()
    
    if not replied_msg.document:
        await event.respond("**Please Reply To A Zip File To Deploy ❌**")
        raise events.StopPropagation
    
    file_size = replied_msg.document.size
    if file_size > MAX_FILE_SIZE_BYTES:
        file_size_mb = file_size / (1024 * 1024)
        await event.respond(f"**❌ Sorry Max File Limit Is {MAX_FILE_SIZE_MB} MB**\n**Your file size:** {file_size_mb:.2f} MB")
        raise events.StopPropagation
    
    file_name = None
    for attr in replied_msg.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            file_name = attr.file_name
            break
    
    if not file_name or not file_name.lower().endswith('.zip'):
        await event.respond("**Please Reply To A Zip File To Deploy ❌**")
        raise events.StopPropagation
    
    project_name = file_name.rsplit('.', 1)[0]
    project_name = re.sub(r'[^a-zA-Z0-9_-]', '', project_name)
    
    if not project_name or len(project_name) < 3:
        project_name = f"project_{user_id}_{int(datetime.now().timestamp())}"
    
    counter = 1
    original_name = project_name
    while project_name in projects:
        project_name = f"{original_name}_{counter}"
        counter += 1
    
    LOGGER.info(f"User {user_id} deploying project: {project_name} ({file_size / (1024*1024):.2f} MB)")
    
    msg = await event.respond(f"**Downloading Project `{project_name}`....**")
    
    try:
        temp_zip = PROJECTS_DIR / f"{project_name}_temp.zip"
        await replied_msg.download_media(file=str(temp_zip))
        
        LOGGER.info(f"Downloaded zip file for project {project_name}")
        
        await msg.edit(f"**Extracting Project `{project_name}`....**")
        
        project_path = PROJECTS_DIR / project_name
        if project_path.exists():
            shutil.rmtree(project_path)
        project_path.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(project_path)
        
        temp_zip.unlink()
        
        LOGGER.info(f"Extracted project {project_name}, cleaning junk files")
        
        await msg.edit(f"**Cleaning Project `{project_name}`....**")
        
        clean_junk_files(project_path)
        
        sender = await event.get_sender()
        user_name = sender.first_name or "User"
        user_link = f"tg://user?id={user_id}"
        
        project_size = get_size(project_path)
        
        projects[project_name] = {
            'name': project_name,
            'path': str(project_path),
            'owner_id': user_id,
            'owner_name': user_name,
            'owner_link': user_link,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'size': project_size,
            'status': 'Offline ❌',
            'run_command': 'python3 main.py',
            'pid': None,
            'ram': None
        }
        
        LOGGER.info(f"Project {project_name} deployed successfully by user {user_id}")
        
        text = get_simple_text(projects[project_name])
        buttons = get_simple_button(project_name)
        
        await msg.edit(text, buttons=buttons)
        
    except zipfile.BadZipFile:
        LOGGER.error(f"Invalid ZIP file for project {project_name}")
        await msg.edit("**❌ Invalid ZIP file. Please send a valid ZIP archive.**")
    except Exception as e:
        LOGGER.exception(f"Error deploying project {project_name}")
        await msg.edit(f"**❌ Error deploying project: {str(e)}**")
    
    raise events.StopPropagation

@CodeUtilBot.on(events.NewMessage(pattern=restart_pattern))
async def restart_command_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} requested restart selection")
    
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
        row.append(Button.inline(f"🔄 {project_names[i]}", f"restartproj_{project_names[i]}".encode()))
        if i + 1 < len(project_names):
            row.append(Button.inline(f"🔄 {project_names[i + 1]}", f"restartproj_{project_names[i + 1]}".encode()))
        buttons.append(row)
    
    text = (
        f"**🔄 Select Project To Restart**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Total Projects:** {len(user_projects)}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Choose a project:**"
    )
    
    await event.respond(text, buttons=buttons)
    raise events.StopPropagation

@CodeUtilBot.on(events.CallbackQuery(pattern=b"restartproj_.*"))
async def restart_project_callback(event):
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
    
    LOGGER.info(f"User {user_id} restarting project {project_name} via command")
    
    await event.answer("Restarting project...", alert=False)
    msg = await event.edit("**Restarting Project....⚡**")
    
    if project['pid'] and psutil.pid_exists(project['pid']):
        try:
            import os
            process = project_processes.get(project_name)
            if process:
                os.killpg(os.getpgid(process.pid), 9)
            else:
                proc = psutil.Process(project['pid'])
                proc.terminate()
                proc.wait(timeout=5)
            
            if project_name in project_processes:
                del project_processes[project_name]
                
            await asyncio.sleep(1)
            
            LOGGER.info(f"Stopped existing process for {project_name}")
        except:
            pass
    
    try:
        success, pid, ram = await start_project_process(project, project_name, event)
        
        if not success:
            project['pid'] = None
            project['ram'] = None
            project['status'] = 'Offline ❌'
            
            text = get_project_text(project)
            buttons = get_project_buttons(project_name)
            
            await msg.edit(text, buttons=buttons)
            return
        
        project['pid'] = pid
        project['ram'] = ram
        project['status'] = 'Online ✅'
        project_processes[project_name] = psutil.Process(pid)
        
        text = get_project_text(project)
        buttons = get_project_buttons(project_name)
        
        await msg.edit(text, buttons=buttons)
        
    except Exception as e:
        LOGGER.exception(f"Error restarting project {project_name}")
        await event.answer(f"❌ Error: {str(e)}", alert=True)