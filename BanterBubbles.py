import time
import requests
import os

from loguru import logger
from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog, button_dialog
from prompt_toolkit import prompt
import threading

# Setup log file
logger.remove()
logger.add("log.txt", backtrace=True, diagnose=True)

# Dummy data for bot instances (replace this with your actual bot instances)
bot_instances = []


def makeRequest(bot_index):
    headers = {
        'Authorization': 'Bearer ' + bot_instances[bot_index].authentication['authorization'],
        'cookie': bot_instances[bot_index].authentication['cookie'],
    }
    r = requests.get("https://banterbubbles.com/api/airdrop", headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        logger.error(f"{bot_instances[bot_index].name} - Received HTTP error {r.status_code}")
    return


def work_account(bot_index):
    while bot_instances[bot_index].running:
        response = makeRequest(bot_index)

        if response:
            if bot_instances[bot_index].points != response['points']:
                bot_instances[bot_index].apidata = response
                bot_instances[bot_index].points = response['points']

                time.sleep(20)
            else:
                logger.error(f"{bot_instances[bot_index].name} - API didn't response with points:\n{str(response)}")
                bot_instances[bot_index].running = False
                bot_instances[bot_index].status = "Stopped"
                break
        else:
            logger.error(f"{bot_instances[bot_index].name} - Request didn't yield a response")
            bot_instances[bot_index].running = False
            bot_instances[bot_index].status = "Stopped"
            break


# Define a Bot class representing each bot instance
class Bot:
    def __init__(self, name, bot_index, status, authentication, parameters):
        self.api_data = None
        self.index = bot_index
        self.name = name
        self.points = 0
        self.authentication = authentication
        self.parameters = parameters
        self.running = False
        self.status = status
        self.thread = None

    def start(self):
        logger.info(f"{self.name} - Starting")
        if not self.running:
            self.status = "Running"
            self.running = True
            self.thread = threading.Thread(target=work_account, args=(self.index,))
            self.thread.start()
        else:
            logger.warning(f"{self.name} - Can\'t start, as it\'s already running")

    def stop(self):
        logger.info(f"{self.name} - Stopping")
        if self.running:
            self.status = "Stopped"
            self.running = False
        else:
            logger.warning(f"Bot {self.name} - Can\'t stop, as it\'s already stopped")

    def updateData(self, data):
        self.points = data['points']
        # TODO: Add other stuff here

    def __repr__(self):
        return f"Bot(name={self.name}, status={self.status}, parameters={self.parameters})"


def insertBot(filename):
    logger.info(f"Loading - Load bot from {filename}")
    with open("bots/" + filename) as f:
        data = f.readlines()

        name = filename.split(".")[0]
        authorization = None
        cookie = None

        # Parse out the data
        for i in range(len(data)):
            if data[i].startswith("  -H 'authorization: Bearer "):
                authorization = data[i].split("authorization: Bearer ")[1].split("' \\")[0]
            if data[i].startswith("  -H 'cookie:"):
                cookie = data[i].split("cookie: ")[1].split("' \\")[0]
        logger.info(f"Loading - Bot {name} loaded with:\n\tauthorization: {authorization}\n\tcookie: {cookie}")

        bot_instances.append(
            Bot(name, len(bot_instances), "Stopped", {'authorization': authorization, 'cookie': cookie},
                {"param1": "value3", "param2": "value4"}))

        bot_instances[len(bot_instances) - 1].start()


# Dynamically populate bots with the file data
for bot_filename in os.listdir("bots"):
    logger.info(f"Loading - Looking in ./bots")
    if bot_filename.endswith(".bot"):
        logger.info(f"Loading - Found bot config at ./bots/{bot_filename}")
        insertBot(bot_filename)
        continue
    else:
        continue


def prompt_continuation(width, line_number, is_soft_wrap):
    return '.' * width
    # Or: return [('', '.' * width)]


def longest_name_length():
    max_length = 0
    for bot in bot_instances:
        name_length = len(bot.name)
        if name_length > max_length:
            max_length = name_length
    return max_length


def pad_name(text, length):
    new_text = text
    while len(new_text) < length:
        new_text += " "
    return new_text


def longest_point_length():
    max_length = 0
    for bot in bot_instances:
        point_length = len(str(bot.points))
        if point_length > max_length:
            max_length = point_length
    return max_length


def left_pad(text, length):
    new_text = text
    while len(new_text) < length:
        new_text = " " + new_text
    return new_text


# Function to render the UI
def render_ui():
    state = "bot_list"
    option = None

    while True:
        # Display list of bot instances
        if state == "bot_list":
            max_name_length = longest_name_length()
            max_point_length = longest_point_length()
            bot_list = [(-1, "New Bot")]
            for idx, bot in enumerate(bot_instances):
                name_text = pad_name(bot.name, max_name_length)
                point_text = left_pad(str(bot.points), max_point_length)
                bot_list.append((idx, f"{name_text} - {bot.status} - {point_text}"))

            option = radiolist_dialog(
                title="Bot Instances",
                text="Which bot instance to manage?",
                values=bot_list,
                cancel_text="Refresh"
            ).run()

            if option is not None:
                if option < 0:
                    state = "new_bot"
                else:
                    state = "bot_view"
        elif state == 'bot_view':
            state = button_dialog(
                title=f'Bot {bot_instances[option].name}',
                text='What do you want to do?',
                buttons=[
                    ('Start', 'start'),
                    ('Stop', 'stop'),
                    ('New CURL', 'new_curl'),
                    ('Edit CURL', 'edit_curl'),
                    ('Cancel', 'cancel')
                ],
            ).run()

            if state == 'start' or state == 'stop' or state == 'cancel':
                if state == 'start':
                    bot_instances[option].start()
                elif state == 'stop':
                    bot_instances[option].stop()

                state = "bot_list"
        elif state == 'new_curl' or state == 'edit_curl' or state == 'new_bot':
            bot_data = ""
            # Load the bot data if we're editing
            if state == 'edit_curl':
                with open(f"bots/{bot_instances[option].name}.bot") as f:
                    bot_data = f.read()

            cancel = False

            # Ask user for the CURL request
            data = prompt('CURL (ALT + Enter to save)> ', multiline=True, prompt_continuation=prompt_continuation,
                          default='%s' % bot_data)
            if data is None or data == '':
                cancel = True
                if state == 'new_bot':
                    state = 'bot_list'

            if not cancel:
                # Ask user for bot name if this is a new account
                filename = ''
                bot_name = ''
                if state == 'new_bot':
                    while bot_name == '':
                        bot_name = input_dialog(
                            title='New Bot Name',
                            text='Please type new bot name:').run()
                        if bot_name is None:
                            cancel = True
                            bot_name = "INVALID"
                    filename = f'bots/{bot_name}.bot'
                else:
                    filename = f'bots/{bot_instances[option].name}.bot'

            if not cancel:
                file = open(filename, 'w')
                file.write(data)
                file.close()

                if state == 'new_bot':
                    # Add our new bot into the array
                    insertBot(bot_name + '.bot')

            if state != 'bot_list':
                state = "bot_view"


# Entry point
def main():
    render_ui()


if __name__ == "__main__":
    main()
