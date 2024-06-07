from api.whatsapp_api_handle import Message
from api.appSettings import appSettings
from argparse import ArgumentParser

pluginInfo = {
    "command_name": "blacklist",
    "admin_privilege": True,
    "description": "Add or remove a number from blacklist.",
    "internal": False,
}


def handle_function(message: Message):
    try:
        if len(message.arguments) == 1:
            raise SystemExit
        parsed = parser(message.arguments[1:])

    except SystemExit:
        pretext = message.command_prefix + (appSettings.admin_command_prefix + " " if pluginInfo["admin_privilege"] else "") + pluginInfo["command_name"]
        message.outgoing_text_message = f"""*Usage:*
- Add members to blacklist: `{pretext} -a [number] [number]...`
- Remove members from blacklist: `{pretext} -r [number] [number]...`
- Get blacklist: `{pretext} -g`"""
        message.send_message()
        return

    if parsed.add:
        for number in parsed.add:
            appSettings.append("blacklist_ids", number)
        message.outgoing_text_message = f"*Blacklisted*: {', '.join(parsed.add)}."
        message.send_message()

    if parsed.remove:
        for number in parsed.remove:
            try:
                appSettings.remove("blacklist_ids", number)
                message.outgoing_text_message = f"*Removed from blacklist*: {', '.join(parsed.remove)}."
            except ValueError:
                message.outgoing_text_message = f"{number} is not in blacklist."
        message.send_message()

    if parsed.get:
        message.outgoing_text_message = "*Blacklisted*: " + ", ".join(appSettings.blacklist_ids)
        message.send_message()


def parser(args: str) -> ArgumentParser:
    parser = ArgumentParser(description="Add or remove a number from blacklist.")
    parser.add_argument("-a", "--add", nargs="+", help="Add members to blacklist.")
    parser.add_argument("-r", "--remove", type=str, nargs="+", help="Remove members from blacklist.")
    parser.add_argument("-g", "--get", action="store_true", help="Get blacklist.")
    return parser.parse_args(args)
