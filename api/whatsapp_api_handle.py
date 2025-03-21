import re
import os
import json
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

import pytz
import requests
import phonenumbers
from openai import OpenAI
from django.utils import timezone

from api.models import GPTResponse, Users
from api.appSettings import appSettings
from Whatsapp_API.settings import DEBUG


class SenderInBlackList(Exception):
    pass


class SenderNotAdmin(Exception):
    pass


class EmptyMessageInGroup(Exception):
    pass


class CommandNotFound(Exception):
    pass


class MessageNotValid(Exception):
    pass


class SendHelp(Exception):
    pass


class Plugin:
    def __init__(
        self,
        command_name: str,
        admin_privilege: bool,
        description: str,
        handle_function: Any,
        preprocess: Optional[Any] = None,
        internal: bool = False,
        help_message: Optional[dict[str, Any]] = None,
    ) -> None:
        self.command_name = command_name
        self.admin_privilege = admin_privilege
        self.description = description
        self.handle_function = handle_function
        self.preprocess = preprocess
        self.internal = internal
        self.help_message = help_message

    @staticmethod
    def load_plugins() -> Dict[str, "Plugin"]:
        plugins = {}
        plugin_files = [file.rstrip(".py") for file in os.listdir(Path("api/plugins")) if file.endswith(".py")]

        for file in plugin_files:
            spec = importlib.util.spec_from_file_location(file, Path("api/plugins") / (file + ".py"))
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            plugins[plugin.pluginInfo["command_name"]] = Plugin(
                command_name=plugin.pluginInfo["command_name"],
                admin_privilege=plugin.pluginInfo["admin_privilege"],
                description=plugin.pluginInfo["description"],
                internal=plugin.pluginInfo["internal"],
                handle_function=plugin.handle_function,
                preprocess=plugin.preprocess if "preprocess" in dir(plugin) else None,
                help_message=plugin.helpMessage if "helpMessage" in dir(plugin) else None,
            )
        return plugins

    def str_help_message(self, pretext: str, note: bool = True) -> str:
        help_message = f"*Command Name: `{self.command_name}`*\n{self.description}\n\n*Usage:*\n\n"
        for i, command in enumerate(self.help_message["commands"]):
            help_message += f"*{i+1}. {command['description']}*\n"
            help_message += f"`{pretext+' '+command['command'] if command['command'] else pretext}`\n"
            if "examples" in command:
                help_message += "*Examples:*\n"
            for example in command.get("examples", []):
                help_message += f"> {pretext} {example}\n"
            help_message += "\n"
        help_message += f"{self.help_message['note']}\n" if "note" in self.help_message else "\n" if note else ""
        return help_message


class Message:
    def __init__(self, data: dict):
        self.senderId: Optional[str]
        self.groupId: Optional[str]
        self.sender: Optional[str]
        self.group: Optional[str]

        self.senderId, self.groupId = self.get_group_and_sender_id(data["from"])
        self.sender, self.group = map(lambda id: re.sub(r"^(\d+).*[:@].*$", r"\1", id) if id else None, [self.senderId, self.groupId])

        self.command_prefix = "./" if self.group else "/"
        self.arguments: Optional[List[Union[str, int, float]]] = None
        self.admin_privilege: bool = False
        self.incoming_message_id: Optional[str] = data["message"].get("id")
        self.incoming_text_message: Optional[str] = ""
        self.outgoing_text_message: Optional[str] = ""
        self.link: Optional[str] = None
        self.send_to: List[str] = [self.senderId if self.groupId is None else self.groupId]
        self.document: Optional[Any] = data.get("document")
        self.document_type: Optional[str] = data.get("document_type")
        self.media_mime_type: Optional[str] = None
        self.media_type: Optional[bytes] = None
        self.media_path: Optional[str] = None
        self.media: Optional[bytes] = None
        self.timezone: Optional[str] = None

        self.set_incoming_text_message(data)
        self.validate()
        if self.media_type:
            self.set_media(data)
        self.get_timezone()

    def validate(self) -> None:
        if not self.incoming_text_message and self.group:
            raise EmptyMessageInGroup("Message is empty in group.")
        elif self.sender not in appSettings.admin_ids and self.sender in appSettings.blacklist_ids:
            raise SenderInBlackList("Sender is in blacklist.")
        elif self.sender not in appSettings.admin_ids and DEBUG:
            raise PermissionError("Debug mode is enabled.")

    def process_incoming_text_message(self) -> None:
        if self.group:
            if bool(re.match(r"\.[^\.].*", self.incoming_text_message)):
                self.incoming_text_message = self.incoming_text_message.lstrip(".").strip()
            else:
                raise MessageNotValid("Message does not start with a dot.")

        if self.incoming_text_message.startswith("/"):
            self.incoming_text_message = self.incoming_text_message[1:].strip()
            self.arguments = self.incoming_text_message.split()

            if appSettings.admin_command_prefix == self.arguments[0] and self.sender in appSettings.admin_ids:
                self.admin_privilege = True
                self.arguments = self.arguments[1:]
                if not self.arguments:
                    self.arguments = ["help"]

    def set_incoming_text_message(self, data: dict) -> None:
        for media_type in ["image", "video", "audio", "file", "sticker"]:
            if data.get(media_type):
                self.incoming_text_message = data[media_type]["caption"].replace("\xa0", " ")
                self.media_type = media_type
                return
        if data.get("message", {}).get("text"):
            self.incoming_text_message = data["message"]["text"].replace("\xa0", " ")

    def set_media(self, data: dict) -> None:
        self.incoming_text_message = data[self.media_type]["caption"].replace("\xa0", " ")
        self.media_mime_type = data[self.media_type]["mime_type"]
        self.media_path = data[self.media_type]["media_path"]

    @staticmethod
    def get_group_and_sender_id(string: str) -> Tuple[Optional[str], Optional[str]]:
        if " in " in string:
            sender, group = string.split(" in ")
            if not group.endswith("@g.us"):
                sender, group = group, None
        else:
            sender, group = string, None
        return sender, group

    def get_timezone(self) -> str | None:
        try:
            parsed_number = phonenumbers.parse("+" + self.sender)
            country_code = phonenumbers.region_code_for_number(parsed_number)
            self.timezone = json.load(open("api/assets/timezones.json")).get(country_code)
        except phonenumbers.phonenumberutil.NumberParseException:
            pass

    def send_message(self) -> None:
        for phone in self.send_to:
            body = {
                "phone": phone,
                "message": self.outgoing_text_message.strip(),
            }
            response = requests.post(appSettings.whatsapp_client_url + "send/message", data=body)
            print(response.text)

    def send_link(self) -> None:
        for phone in self.send_to:
            body = {
                "phone": phone,
                "caption": self.outgoing_text_message.strip(),
                "link": self.link,
            }
            response = requests.post(appSettings.whatsapp_client_url + "send/link", data=body)
            print(response.text)

    def send_file(self, caption: bool = False) -> None:
        for phone in self.send_to:
            body = {
                "phone": phone,
                "caption": self.outgoing_text_message.strip() if caption else None,
            }
            response = requests.post(appSettings.whatsapp_client_url + "send/file", data=body, files=self.media)
            print(response.text)

    def send_audio(self, caption: bool = False) -> None:
        for phone in self.send_to:
            body = {
                "phone": phone,
                "caption": self.outgoing_text_message.strip() if caption else None,
            }
            response = requests.post(appSettings.whatsapp_client_url + "send/audio", data=body, files=self.media)
            print(response.text)

    def send_image(self, caption: bool = False) -> None:
        for phone in self.send_to:
            body = {
                "phone": phone,
                "caption": self.outgoing_text_message.strip() if caption else None,
            }
            response = requests.post(appSettings.whatsapp_client_url + "send/image", data=body, files=self.media)
            print(response.text)

    def send_video(self, caption: bool = False) -> None:
        for phone in self.send_to:
            body = {
                "phone": phone,
                "caption": self.outgoing_text_message.strip() if caption else None,
            }
            response = requests.post(appSettings.whatsapp_client_url + "send/video", data=body, files=self.media)
            print(response.text)

    def send_media(self, caption: bool = False) -> None:
        if self.media_mime_type == "audio/ogg":
            self.send_audio(caption)
        elif self.media_mime_type == "image/jpeg":
            self.send_image(caption)
        elif self.media_mime_type == "video/mp4":
            self.send_video(caption)
        else:
            self.send_file(caption)


class API:
    def __init__(self, data: dict) -> None:
        self.request_timestamp = timezone.now()
        self.message = Message(data)
        self.plugins = Plugin.load_plugins()

        self.start_prosess()

    def start_prosess(self) -> None:
        self.preprocess()
        self.message.process_incoming_text_message()
        self.register_user()

        try:
            if self.message.arguments:
                self.command_handle()
            else:
                self.message_handle()
        except (CommandNotFound, SenderNotAdmin) as e:
            self.message.outgoing_text_message = str(e)
            self.message.send_message()

    def register_user(self) -> None:
        user = Users.objects.get_or_create(user_id=self.message.sender, group_id=self.message.group)
        if not user[0].description:
            user[0].description = json.dumps({"group_name": "signedup"})
            user[0].save()

    def preprocess(self) -> None:
        for _, plugin in self.plugins.items():
            if plugin.preprocess:
                plugin.preprocess(self.message)

    def get_previous_messages(self) -> list[dict[str, str]]:
        previous_messages = []
        for response in GPTResponse.objects.filter(group=self.message.group, sender=self.message.sender).order_by("-date")[:5]:
            previous_messages.append({"role": "user", "content": response.message})
            previous_messages.append({"role": "assistant", "content": response.response})
        return previous_messages

    def save_response(self, response: dict) -> None:
        response["system"] = self.message.outgoing_text_message
        GPTResponse.objects.create(message=self.message.incoming_text_message, response=json.dumps(response), group=self.message.group, sender=self.message.sender)

    def gptResponse(self) -> str:
        system_content = open("api/assets/training.md").read().format(help_message=self.get_all_help_message(), timezone=self.message.timezone, time=datetime.now(pytz.timezone(self.message.timezone)).strftime("%Y-%m-%d %H:%M:%S"))

        response = OpenAI(api_key=appSettings.openai_api_key).chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": system_content,
                },
                *self.get_previous_messages(),
                {
                    "role": "user",
                    "content": self.message.incoming_text_message,
                },
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def message_handle(self) -> None:
        response = self.gptResponse()
        print(response)
        if response.get("console"):
            if response["console"].startswith(self.message.command_prefix):
                self.message.incoming_text_message = response["console"]
            else:
                self.resolve_console(response["console"])
            self.message.process_incoming_text_message()
            self.command_handle()
        if response.get("chat"):
            self.message.incoming_text_message += "\nAttachment: " + self.message.media_path if self.message.media_path else ""
            self.message.outgoing_text_message = response["chat"]
            self.message.send_message()

        self.save_response(response)

        # self.message.outgoing_text_message = f"Hello, I am a bot. Use `{self.message.command_prefix}help` (or `{self.message.command_prefix + appSettings.admin_command_prefix} help` if you are an admin) to see available commands."
        # self.message.send_message()

    def resolve_console(self, console: str) -> None:
        if console.startswith('/'):
            console = self.message.command_prefix + console[1:]
        elif console.startswith('./'):
            console = self.message.command_prefix + console[2:]
        else:
            console = self.message.command_prefix + console
        self.message.incoming_text_message = console

    def command_handle(self) -> None:
        if self.message.arguments[0] == appSettings.admin_command_prefix and not self.message.admin_privilege:
            raise SenderNotAdmin("You are not an admin and cannot use admin commands.")

        if self.message.arguments == [""] or self.message.arguments[0] == "help":
            self.message.outgoing_text_message = self.get_help()
            self.message.send_message()
        elif self.message.arguments[0] in self.plugins:
            plugin = self.plugins[self.message.arguments[0]]
            if plugin.admin_privilege == self.message.admin_privilege:
                try:
                    plugin.handle_function(self.message)
                except SendHelp:
                    self.message.outgoing_text_message = plugin.str_help_message(pretext=self.message.command_prefix + (appSettings.admin_command_prefix + " " if plugin.admin_privilege else "") + plugin.command_name)
                    self.message.send_message()
        else:
            raise CommandNotFound(f"Command `{self.message.arguments[0]}` not found. Write `{self.message.command_prefix}help` (or `{self.message.command_prefix + appSettings.admin_command_prefix} help` if you are an admin) to see available commands.")

    def get_help(self) -> None:
        help_message = "*Available commands:*\n\n"
        i = 1
        for plugin in self.plugins.values():
            if plugin.admin_privilege == self.message.admin_privilege and not plugin.internal:
                help_message += f"*{i}. {plugin.description}*\n`{self.message.command_prefix + (appSettings.admin_command_prefix + ' ' if plugin.admin_privilege else '') + plugin.command_name}`\n\n"
                i += 1
        help_message += f"*{i}. Show this message*\n`{self.message.command_prefix + (appSettings.admin_command_prefix + ' ' if plugin.admin_privilege else '') + 'help'}`\n"
        return help_message

    def get_all_help_message(self) -> str:
        help_message = ""
        for _, plugin in self.plugins.items():
            if not plugin.help_message:
                continue
            help_message += plugin.str_help_message(pretext=self.message.command_prefix + (appSettings.admin_command_prefix + " " if plugin.admin_privilege else "") + plugin.command_name)
            help_message += "\n"
        help_message += f"""*Command Name: `help`*
Display help message for all available commands.

*Usage:*

*1. Show help message for all available commands*
`{self.message.command_prefix}help`

*2. Show help message for admin commands*
`{self.message.command_prefix + appSettings.admin_command_prefix} help`"""
        return help_message
