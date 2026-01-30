#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import os
import re
import asyncio
import zipfile
import shutil
import psutil
import subprocess
from pathlib import Path
from datetime import datetime
from telethon import events, Button
from telethon.tl.types import DocumentAttributeFilename
from bot import CodeUtilBot
import config
from utils import LOGGER

user_sessions = {}
projects = {}
project_processes = {}

PROJECTS_DIR = Path("downloads")
PROJECTS_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def get_size(path):
    total = 0
    for entry in Path(path).rglob('*'):
        if entry.is_file():
            total += entry.stat().st_size
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total < 1024.0:
            return f"{total:.2f} {unit}"
        total /= 1024.0
    return f"{total:.2f} TB"

def clean_junk_files(project_path):
    junk_patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.git',
        '.gitignore',
        '.DS_Store',
        'Thumbs.db',
        '*.log'
    ]
    
    for pattern in junk_patterns:
        if '*' in pattern:
            for item in project_path.rglob(pattern):
                try:
                    item.unlink()
                except:
                    pass
        else:
            for item in project_path.rglob(pattern):
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except:
                    pass

def get_simple_button(project_name):
    return [[Button.inline("⚙️ Open Project Settings", f"opensettings_{project_name}".encode())]]

def get_project_buttons(project_name):
    return [
        [
            Button.inline("▶️ Start", f"start_{project_name}".encode()),
            Button.inline("⏹ Stop", f"stop_{project_name}".encode()),
            Button.inline("🔄 Restart", f"restart_{project_name}".encode())
        ],
        [
            Button.inline("📄 Logs", f"logs_{project_name}".encode()),
            Button.inline("🔍 Status", f"status_{project_name}".encode()),
            Button.inline("✍ Usage", f"usage_{project_name}".encode())
        ],
        [Button.inline("📥 Install Dependencies", f"deps_{project_name}".encode())],
        [Button.inline("⚙ Edit Run Command", f"editcmd_{project_name}".encode())],
        [Button.inline("◀️ Back To Project Settings", f"backsettings_{project_name}".encode())]
    ]

def get_simple_text(project):
    return (
        f"**✅ Project Created Successfully!**\n\n"
        f"**Project Name:** {project['name']}\n"
        f"**Project Size:** {project['size']}\n"
        f"**Owner:** [{project['owner_name']}]({project['owner_link']})\n"
        f"**Status:** {project['status']}"
    )

def get_project_text(project):
    extra_info = ""
    if project['pid']:
        extra_info = f"\n**Process PID:** {project['pid']}\n**RAM Allocated:** {project['ram']}"
    elif project['status'] == 'Offline ❌' and project.get('last_pid'):
        extra_info = f"\n**Process Stopped**\n**Last PID:** {project.get('last_pid')}\n**RAM Deallocated:** {project.get('last_ram', 'N/A')}"
    
    return (
        f"**Settings ⚙️ For Your Project**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Project's Name:** {project['name']}\n"
        f"**Project's Size:** {project['size']}\n"
        f"**Project Owner:** [{project['owner_name']}]({project['owner_link']})\n"
        f"**Creation Date:** {project['created_at']}\n"
        f"**Project Status:** {project['status']}{extra_info}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Use Below Buttons To Customize**"
    )

async def start_project_process(project, project_name, event):
    project_path = Path(project['path'])
    cmd_parts = project['run_command'].split()
    
    logs_dir = project_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "output.log"
    
    LOGGER.info(f"Starting project {project_name} with command: {project['run_command']}")
    
    process = subprocess.Popen(
        cmd_parts,
        cwd=str(project_path),
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    
    await asyncio.sleep(3)
    
    if process.poll() is not None:
        LOGGER.error(f"Project {project_name} failed to start")
        
        with open(log_file, 'r') as f:
            error_log = f.read()
        
        LOGGER.error(f"Error log for {project_name}:\n{error_log[:500]}")
        
        caption = (
            f"**❌ Project `{project_name}` Failed To Start**\n\n"
            f"**Project Owner:** {project['owner_name']}\n"
            f"**Run Command:** `{project['run_command']}`\n"
            f"**Error Details:** See log file below"
        )
        
        await CodeUtilBot.send_file(
            event.chat_id,
            log_file,
            caption=caption
        )
        
        return False, None, None
    
    pid = process.pid
    
    try:
        proc = psutil.Process(pid)
        ram_mb = proc.memory_info().rss / (1024 * 1024)
        ram = f"{ram_mb:.2f} MB"
    except:
        ram = "Unknown"
    
    LOGGER.info(f"Project {project_name} started successfully with PID {pid}")
    
    return True, pid, ram

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
new_pattern = re.compile(rf'^[{prefixes}]new$', re.IGNORECASE)
cancel_pattern = re.compile(rf'^[{prefixes}]cancel$', re.IGNORECASE)

@CodeUtilBot.on(events.NewMessage(pattern=new_pattern))
async def new_project_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} initiated new project creation")
    
    user_sessions[user_id] = {
        'stage': 'awaiting_name',
        'project_name': None,
        'chat_id': event.chat_id
    }
    
    await event.respond(
        "**✍️ Please enter a name for your new project (e.g., SmartUtilBot).**\n"
        "**Send `/cancel` to abort.**"
    )
    raise events.StopPropagation

@CodeUtilBot.on(events.NewMessage(pattern=cancel_pattern))
async def cancel_handler(event):
    user_id = event.sender_id
    
    if user_id in user_sessions:
        LOGGER.info(f"User {user_id} cancelled project creation/edit")
        del user_sessions[user_id]
        await event.respond("**❌ Cancelled Operation...**")
    raise events.StopPropagation

@CodeUtilBot.on(events.NewMessage())
async def project_creation_handler(event):
    user_id = event.sender_id
    
    if user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    
    if session['stage'] == 'awaiting_name':
        project_name = (event.text or '').strip()
        
        if not project_name or len(project_name) < 3:
            await event.respond("**❌ Please provide a valid project name (at least 3 characters).**")
            raise events.StopPropagation
        
        if project_name in projects:
            await event.respond(f"**❌ Project `{project_name}` already exists! Choose a different name.**")
            raise events.StopPropagation
        
        LOGGER.info(f"User {user_id} named project: {project_name}")
        
        session['project_name'] = project_name
        session['stage'] = 'awaiting_file'
        
        await event.respond(
            f"**✅ Project `{project_name}` setup complete!**\n\n"
            f"**📁 Now send the ZIP file of your project.**\n"
            f"**⚠️ Max file size: {MAX_FILE_SIZE_MB} MB**\n"
            f"**Send `/cancel` to abort.**"
        )
        raise events.StopPropagation
    
    elif session['stage'] == 'awaiting_file':
        if not event.document:
            await event.respond("**❌ Please Provide A Valid Zip File Of The Project**")
            raise events.StopPropagation
        
        file_size = event.document.size
        if file_size > MAX_FILE_SIZE_BYTES:
            file_size_mb = file_size / (1024 * 1024)
            await event.respond(f"**❌ Sorry Max File Limit Is {MAX_FILE_SIZE_MB} MB**\n**Your file size:** {file_size_mb:.2f} MB")
            del user_sessions[user_id]
            raise events.StopPropagation
        
        file_name = None
        for attr in event.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                file_name = attr.file_name
                break
        
        if not file_name or not file_name.lower().endswith('.zip'):
            await event.respond("**❌ Please Provide A Valid Zip File Of The Project**")
            raise events.StopPropagation
        
        project_name = session['project_name']
        
        LOGGER.info(f"User {user_id} uploading zip file ({file_size / (1024*1024):.2f} MB) for project {project_name}")
        
        msg = await event.respond(f"**Downloading Project `{project_name}`....**")
        
        try:
            temp_zip = PROJECTS_DIR / f"{project_name}_temp.zip"
            await event.download_media(file=str(temp_zip))
            
            LOGGER.info(f"Downloaded zip file for project {project_name}")
            
            project_path = PROJECTS_DIR / project_name
            if project_path.exists():
                shutil.rmtree(project_path)
            project_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(project_path)
            
            temp_zip.unlink()
            
            LOGGER.info(f"Extracted project {project_name}, cleaning junk files")
            
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
            
            LOGGER.info(f"Project {project_name} created successfully by user {user_id}")
            
            del user_sessions[user_id]
            
            text = get_simple_text(projects[project_name])
            buttons = get_simple_button(project_name)
            
            await msg.edit(text, buttons=buttons)
            
        except zipfile.BadZipFile:
            LOGGER.error(f"Invalid ZIP file for project {project_name}")
            await msg.edit("**❌ Invalid ZIP file. Please send a valid ZIP archive.**")
            del user_sessions[user_id]
        except Exception as e:
            LOGGER.exception(f"Error processing project {project_name}")
            await msg.edit(f"**❌ Error processing project: {str(e)}**")
            del user_sessions[user_id]
        
        raise events.StopPropagation
    
    elif session.get('stage') == 'editing_cmd':
        new_command = (event.text or '').strip()
        
        if not new_command:
            await event.respond("**❌ Please provide a valid command.**")
            raise events.StopPropagation
        
        project_name = session['project_name']
        
        if project_name not in projects:
            await event.respond("**❌ Project not found!**")
            del user_sessions[user_id]
            raise events.StopPropagation
        
        LOGGER.info(f"User {user_id} updated run command for {project_name} to: {new_command}")
        
        projects[project_name]['run_command'] = new_command
        
        await event.respond(f"**✅ Run command updated to:** `{new_command}`")
        
        del user_sessions[user_id]
        
        text = get_project_text(projects[project_name])
        buttons = get_project_buttons(project_name)
        
        await event.respond(text, buttons=buttons)
        raise events.StopPropagation

@CodeUtilBot.on(events.CallbackQuery())
async def project_callbacks_router(event):
    data = event.data.decode()
    user_id = event.sender_id
    
    if not any(data.startswith(p) for p in ['opensettings_', 'backsettings_', 'manage_', 'start_', 'stop_', 'restart_', 'status_', 'usage_', 'deps_', 'editcmd_', 'logs_']):
        return
    
    action = data.split('_')[0]
    project_name = data.split('_', 1)[1] if '_' in data else None
    
    if not project_name and action not in ['manage', 'opensettings', 'backsettings']:
        return
    
    if action == 'opensettings':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} opening settings for project {project_name}")
        
        text = get_project_text(projects[project_name])
        buttons = get_project_buttons(project_name)
        
        await event.edit(text, buttons=buttons)
    
    elif action == 'backsettings':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} going back to simple settings for project {project_name}")
        
        text = get_simple_text(projects[project_name])
        buttons = get_simple_button(project_name)
        
        await event.edit(text, buttons=buttons)
    
    elif action == 'manage':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} managing project {project_name}")
        
        text = get_simple_text(projects[project_name])
        buttons = get_simple_button(project_name)
        
        await event.edit(text, buttons=buttons)
    
    elif action == 'start':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        project = projects[project_name]
        
        if project['pid'] and psutil.pid_exists(project['pid']):
            await event.answer("⚠️ Project is already running!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} starting project {project_name}")
        
        await event.answer("Starting project...", alert=False)
        msg = await event.edit("**Running Project....⚡**")
        
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
            LOGGER.exception(f"Error starting project {project_name}")
            await event.answer(f"❌ Error: {str(e)}", alert=True)
    
    elif action == 'stop':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        project = projects[project_name]
        
        if not project['pid'] or not psutil.pid_exists(project['pid']):
            await event.answer("⚠️ Project is not running!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} stopping project {project_name}")
        
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
            
            await event.edit(text, buttons=buttons)
            await event.answer("✅ Project stopped!", alert=False)
            
        except Exception as e:
            LOGGER.exception(f"Error stopping project {project_name}")
            await event.answer(f"❌ Error: {str(e)}", alert=True)
    
    elif action == 'restart':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} restarting project {project_name}")
        
        await event.answer("Restarting project...", alert=False)
        msg = await event.edit("**Restarting Project....⚡**")
        
        project = projects[project_name]
        
        if project['pid'] and psutil.pid_exists(project['pid']):
            try:
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
            await event.answer("✅ Project restarted!", alert=False)
            
        except Exception as e:
            LOGGER.exception(f"Error restarting project {project_name}")
            await event.answer(f"❌ Error: {str(e)}", alert=True)
    
    elif action == 'status':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        project = projects[project_name]
        
        LOGGER.info(f"User {user_id} checking status for {project_name}")
        
        if project['pid'] and psutil.pid_exists(project['pid']):
            project['status'] = 'Online ✅'
            status_text = (
                f"**🔍 Status Check for `{project_name}`**\n"
                f"**━━━━━━━━━━━━━**\n"
                f"**Current Status:** Online ✅\n"
                f"**Process ID:** {project['pid']}\n"
                f"**RAM Usage:** {project['ram']}\n"
                f"**━━━━━━━━━━━━━**"
            )
        else:
            if project['pid']:
                project['last_pid'] = project['pid']
                project['last_ram'] = project['ram']
                project['pid'] = None
                project['ram'] = None
            project['status'] = 'Offline ❌'
            status_text = (
                f"**🔍 Status Check for `{project_name}`**\n"
                f"**━━━━━━━━━━━━━**\n"
                f"**Current Status:** Offline ❌\n"
                f"**Project is not running**\n"
                f"**━━━━━━━━━━━━━**"
            )
        
        buttons = get_project_buttons(project_name)
        
        try:
            await event.edit(status_text, buttons=buttons)
        except:
            await event.answer(status_text.replace('**', '').replace('━━━━━━━━━━━━━', ''), alert=True)
    
    elif action == 'usage':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        project = projects[project_name]
        
        if not project['pid'] or not psutil.pid_exists(project['pid']):
            await event.answer("⚠️ Project is not running!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} checking usage for {project_name}")
        
        try:
            proc = psutil.Process(project['pid'])
            
            cpu_percent = proc.cpu_percent(interval=1)
            mem_info = proc.memory_info()
            ram_mb = mem_info.rss / (1024 * 1024)
            
            create_time = datetime.fromtimestamp(proc.create_time())
            uptime = datetime.now() - create_time
            uptime_str = str(uptime).split('.')[0]
            
            threads = proc.num_threads()
            
            usage_text = (
                f"**📊 Usage Statistics for `{project_name}`**\n"
                f"**━━━━━━━━━━━━━**\n"
                f"**CPU Usage:** {cpu_percent:.2f}%\n"
                f"**RAM Usage:** {ram_mb:.2f} MB\n"
                f"**Threads:** {threads}\n"
                f"**Uptime:** {uptime_str}\n"
                f"**PID:** {project['pid']}\n"
                f"**Status:** Online ✅\n"
                f"**━━━━━━━━━━━━━**"
            )
            
            buttons = get_project_buttons(project_name)
            
            await event.edit(usage_text, buttons=buttons)
            
        except Exception as e:
            LOGGER.exception(f"Error getting usage stats for {project_name}")
            await event.answer(f"❌ Error: {str(e)}", alert=True)
    
    elif action == 'deps':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} installing dependencies for {project_name}")
        
        project = projects[project_name]
        project_path = Path(project['path'])
        requirements_file = project_path / "requirements.txt"
        
        if not requirements_file.exists():
            await event.answer("❌ No requirements.txt found!", alert=True)
            return
        
        msg = await event.edit("**Checking Requirements From Project...**")
        
        try:
            venv_path = project_path / "venv"
            use_venv = False
            
            if not venv_path.exists():
                venv_result = subprocess.run(
                    ["python3", "-m", "venv", "venv"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True
                )
                if venv_result.returncode == 0:
                    use_venv = True
                    LOGGER.info(f"Created virtual environment for {project_name}")
                else:
                    use_venv = False
            else:
                use_venv = True
            
            await msg.edit("**Installing all requirements.....**")
            
            if use_venv:
                pip_path = venv_path / "bin" / "pip"
                result = subprocess.run(
                    [str(pip_path), "install", "-r", "requirements.txt"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["pip3", "install", "-r", "requirements.txt"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                LOGGER.info(f"Dependencies installed successfully for {project_name}")
                await msg.edit("**✅ Successfully Installed Required Things**")
                await asyncio.sleep(2)
                
                text = get_project_text(project)
                buttons = get_project_buttons(project_name)
                
                await msg.edit(text, buttons=buttons)
            else:
                LOGGER.error(f"Failed to install dependencies for {project_name}")
                await msg.edit(f"**❌ Installation failed:**\n```\n{result.stderr[:1000]}\n```")
                
        except Exception as e:
            LOGGER.exception(f"Error installing dependencies for {project_name}")
            await msg.edit(f"**❌ Error: {str(e)}**")
    
    elif action == 'editcmd':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} editing run command for {project_name}")
        
        project = projects[project_name]
        
        user_sessions[user_id] = {
            'stage': 'editing_cmd',
            'project_name': project_name,
            'chat_id': event.chat_id
        }
        
        await event.respond(
            f"**Enter the new run command for `{project_name}`**\n"
            f"**Current:** `{project['run_command']}`\n"
            f"**Example:** python3 bot.py\n\n"
            f"Send `/cancel` to abort."
        )
    
    elif action == 'logs':
        if project_name not in projects:
            await event.answer("❌ Project not found!", alert=True)
            return
        
        LOGGER.info(f"User {user_id} requesting logs for {project_name}")
        
        await event.answer("Sending Logs.....", alert=True)
        
        project = projects[project_name]
        project_path = Path(project['path'])
        log_file = project_path / "logs" / "output.log"
        
        if not log_file.exists():
            await CodeUtilBot.send_message(
                event.chat_id,
                f"**❌ No logs found for project `{project_name}`**"
            )
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