## Overview

This project is a Django-based API system designed to process incoming messages, execute commands via plugins, and interact with a WhatsApp client. It also supports OpenAI's GPT model for generating conversational responses. The system handles different types of media, manages user registrations, and provides both user and admin-level commands.

## Features

- _Plugin System:_ Dynamically load and execute commands through a plugin architecture.
- _Admin Privileges:_ Support for admin-only commands.
- _Message Handling:_ Process and validate incoming messages from users or groups.
- _Media Support:_ Handle images, videos, audio, and documents.
- _GPT Integration:_ Generate and respond to messages using OpenAI's GPT.
- _Error Handling:_ Custom exceptions for various errors (e.g., invalid commands, empty messages in groups).
- _Timezone Management:_ Extract and use the sender’s timezone for time-sensitive responses.

## Installation

1. _Clone the repository:_

   ```bash
   git clone https://github.com/abdxdev/Whatsapp_API.git
   cd Whatsapp_API
   ```

2. _Install dependencies:_

   ```bash
   pip install -r requirements.txt
   ```

3. _Set up Environment Variables:_

   - Create a .env file in the root directory. (This will be needed only the first time. After that, it will be saved in the database.)
   - Add the following environment variables to the .env file:

     - `DJANGO_KEY`
     - `DATABASE_URL`
     - `OPENAI_API_KEY`
     - `PUBLIC_IP`
     - `WHATSAPP_CLIENT_URL`
     - `WHATSAPP_CLIENT_URL_TEST`
     - `PUBLIC_URL`
     - `PUBLIC_URL_TEST`
     - `ADMIN_IDS`
     - `BLACKLIST_IDS`
     - `ADMIN_COMMAND_PREFIX`

4. _Set up Django:_

   - Configure your settings.py with appropriate database and application settings.
   - Apply migrations:

   ```bash
   python manage.py migrate
   ```

5. _Run the Django server:_

   ```bash
   python manage.py runserver
   ```

## Plugin System

### Adding a New Plugin

1. Create a new Python file in the api/plugins directory.
2. Define a pluginInfo dictionary containing:
   - command_name: The name of the command.
   - admin_privilege: Boolean indicating if admin privilege is required.
   - description: A short description of the command.
   - handle_function: The function that handles the command's logic.
   - (Optional) preprocess: A function for preprocessing messages.
   - (Optional) helpMessage: A dictionary defining the help message structure.
3. Implement the command's logic in the file.
4. The plugin will be automatically loaded by the Plugin.load_plugins() method.

### Example Plugin

```python
pluginInfo = {
    "command_name": "example",
    "admin_privilege": False,
    "description": "This is an example command.",
}

def handle_function(message):
    message.outgoing_text_message = "This is an example response."
    message.send_message()
```

## Error Handling

The system includes custom exceptions for specific scenarios:

- _SenderInBlackList:_ Raised when the sender is in the blacklist.
- _SenderNotAdmin:_ Raised when a non-admin user attempts to execute an admin command.
- _EmptyMessageInGroup:_ Raised when a message in a group is empty.
- _CommandNotFound:_ Raised when an unrecognized command is received.
- _MessageNotValid:_ Raised when the message is not valid.
- _SendHelp:_ Used to trigger the sending of help messages.

## GPT Integration

The system integrates with OpenAI's GPT model to generate conversational responses. The gptResponse() method formats the system and user messages and interacts with OpenAI's API to generate a response.

## Usage

### Commands

- _Help Command:_

  - Users can send /help to receive a list of available commands.
  - Admins can send /admin help for admin-specific commands.

- _Custom Commands:_
  - Commands are defined in plugins and are dynamically loaded based on user input.

### Message Handling

1. The system processes incoming messages and determines if they are from a group or individual.
2. Messages are validated and any associated media is processed.
3. Commands are extracted and executed if found.
4. The response is sent back to the user or group.

## Contribution

Feel free to contribute to this project by adding new plugins, improving the existing codebase, or fixing bugs. Please ensure that your contributions are well-documented and tested.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.