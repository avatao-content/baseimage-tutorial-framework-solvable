from tfwsdk import sdk

def on_step(curent_state: int):
    sdk.message_send('CURRENT STATE: ' + str(curent_state))

def on_deploy(curent_state: int):
    sdk.message_send('DEPLOY BUTTON CLICKED')
    return True

def on_message_button_click(curent_state: int, button_value: str):
    sdk.message_send('MESSAGE BUTTON CLICKED: ' + button_value)

def on_ide_write(current_state: int, name_of_file: str, content_of_file: str):
    sdk.message_send('IDE WRITE')

def on_terminal_command(current_state: int, executed_command: str):
    sdk.message_send('COMMAND EXECUTED: ' + executed_command)

if __name__ == '__main__':
    print('🎉 SDK STARTED 🎉')
    sdk._start()