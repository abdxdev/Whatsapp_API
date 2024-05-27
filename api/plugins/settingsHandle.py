from api.whatsapp_api_handle import appSettings, Message
from argparse import ArgumentParser
import shlex

pluginInfo = {
    "command_name": "settings",
    "admin_privilege": True,
    "description": "Settings commands to manage settings. Use ```/abd settings help``` to see available commands.",
    "internal": False,
}


def handle_function(message: Message):
    settingArgs = parser(" ".join(message.arguments), list(appSettings.keys()))
    if isinstance(settingArgs, str):
        message.outgoing_text_message = settingArgs
    elif settingArgs.change:
        oldSettings = appSettings[settingArgs.change[0]]
        appSettings[settingArgs.change[0]] = settingArgs.change[1]
        # setAppSettings(settings=appSettings)
        message.outgoing_text_message = f"Setting `{settingArgs.change[0]}` changed from\n```{oldSettings}```\nto\n```{settingArgs.change[1]}```"
    elif settingArgs.get:
        if settingArgs.get == "all":
            message.outgoing_text_message = f"```{appSettings}```"
        else:
            message.outgoing_text_message = f"Value of setting `{settingArgs.get}` is\n```{appSettings[settingArgs.get]}```"
    else:
        message.outgoing_text_message = "Setting not recognized."
    message.send_message()


def parser(input: str, settings: list):
    parser = ArgumentParser(description="change and view settings.")
    parser.add_argument("-c", "--change", type=str, nargs=2, help="Change settings")
    parser.add_argument("-g", "--get", type=str, choices=settings + ["all"], help="View settings.")
    try:
        args = parser.parse_args(shlex.split(input))
    except SystemExit:
        return parser.format_help()
    return args
