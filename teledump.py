import os
import argparse
from functools import partial
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
import atexit
import yaml
import signal
import sys

def setup_argparse():
    parser = argparse.ArgumentParser(description="Download media from a Telegram conversation")
    parser.add_argument("dialog_name", help="Name of the dialog to download media from")
    return parser.parse_args()

def create_directories(base_dir):
    directories = [base_dir, f"{base_dir}/participants", f"{base_dir}/messages", f"{base_dir}/media"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data.to_json(indent=4))

def get_filename(message):
    if isinstance(message.media, MessageMediaPhoto):
        return f"photo_{message.id}.jpg"
    elif isinstance(message.media, MessageMediaDocument):
        return message.media.document.attributes[-1].file_name
    elif message.video:
        return f"video_{message.id}.mp4"
    elif isinstance(message.media, MessageMediaWebPage):
        return f"webpage_{message.id}.html"
    else:
        return f"unknown_{message.id}"

def download_media(client, message, base_dir):
    if message.media:
        try:
            filename = get_filename(message)
            path = os.path.join(base_dir, 'media', filename)
            client.download_media(message, file=path)
            print(f'Downloaded {filename}')
        except:
            print(f'Failed to download a file from message {message.id}')

def process_dialog(client, dialog_name):
    dialogs = client.get_dialogs()
    dialog = next(i for i in dialogs if dialog_name in i.name)
    base_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dumps", dialog.name)

    create_directories(base_dir)
    
    save_json(dialog.dialog, f"{base_dir}/dialog.json")
    
    try:
        participants = client.get_participants(dialog.id)
        for participant in participants:
            save_json(participant, f"{base_dir}/participants/{participant.id}.json")
    except:
        print("Failed to get participants")
    
    resume = readcounter()
    if resume is None:
        resume = {}
    message_id = resume.get(dialog.id, 0)
    print(f">> Resuming from message: {message_id}")
    messages = client.iter_messages(dialog, reverse=True, offset_id=message_id)
    global fallback
    global stop
    stop = False
    for message in messages:
        fallback = {dialog.id: message.id}
        save_json(message, f"{base_dir}/messages/{message.id:04}.json")
        download_media(client, message, base_dir)
        if stop:
            break

def main():
    args = setup_argparse()
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    with TelegramClient('teledump', api_id, api_hash) as client:
        process_dialog(client, args.dialog_name)

def handle_signal(signum, frame):
    # loop.stop()
    global stop
    stop = True
    savecounter()
    sys.exit(signum)
    sys.exit(signal.SIGKILL)


def savecounter():
    counter = readcounter()
    counter.update(fallback)
    with open('.resume', 'w') as w:
        yaml.safe_dump(counter, w)
        print("Saved counter. Exiting...")

def readcounter():
    try:    
        with open('.resume') as f:
            return yaml.safe_load(f)
    except:
        return {}

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    #atexit.register(savecounter)
    main()

