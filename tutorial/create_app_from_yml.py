import yaml
import logging
import copy
import json
import os

os.chdir(os.path.dirname(os.path.realpath(__file__)))

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
LOG = logging.getLogger()

def open_and_parse_config(filename: str):
    LOG.info('Opening and parsing config file...')
    try:
        with open(filename) as f:
            return yaml.safe_load(f.read())
    except OSError as e:
        LOG.error('Config file not found: ' + filename)
    except yaml.scanner.ScannerError as e:
        LOG.error('Parsing error!')
        LOG.error(e)
    except Exception as e:
        LOG.error(e)

def validate_config(config: dict):
    LOG.info('Trying to validate config...')
    with open('example_app.yml') as f:
        expected_format = yaml.safe_load(f.read())

    success = True

    # Checking if every necessary key exists
    for key, value in expected_format.items():
        if not key in config or type(value) != type(config[key]):
            LOG.error(f'Key is missing or invalid: {key}')
            success = False
    
    for component in ['dashboard', 'webservice', 'terminal', 'ide']:
        for key, value in expected_format[component].items():
            if not key in config[component] or type(value) != type(config[component][key]):
                LOG.error(f'Key is missing or has invalid type: {component}.{key}')
                success = False

    # Additional checks
    RECOMMENDED_MIN_MESSAGE_SPEED = 300
    RECOMMENDED_MAX_MESSAGE_SPEED = 600
    if config['dashboard']['messageSpeed'] < RECOMMENDED_MIN_MESSAGE_SPEED or config['dashboard']['messageSpeed'] > RECOMMENDED_MAX_MESSAGE_SPEED:
        LOG.warning(f"Recommended dashboard.messageSpeed is between {RECOMMENDED_MIN_MESSAGE_SPEED} and {RECOMMENDED_MAX_MESSAGE_SPEED}. Current value: {config['dashboard']['messageSpeed']}")

    valid_layouts = [
        'terminal-ide-web',
        'terminal-ide-vertical',
        'terminal-ide-horizontal',
        'terminal-web',
        'ide-web-vertical',
        'terminal-only',
        'ide-only',
        'web-only'
        ]
    for layout in config['dashboard']['enabledLayouts']:
        if not layout in valid_layouts:
            LOG.error(f"'{layout}' is not a valid layout")
            success = False

    if not config['dashboard']['layout'] in config['dashboard']['enabledLayouts']:
        # It should catch 'enabledLayouts: []' errors as well
        LOG.error(f"'{config['dashboard']['layout']}' is not in dashboard.enabledLayouts")
        success = False
    
    if not config['terminal']['terminalMenuItem'] in ['terminal', 'console']:
        LOG.error(f"Invalid terminal.terminalMenuItem ({config['terminal']['terminalMenuItem']}). Allowed values: console, terminal")
        success = False

    if  not 'TODEPLOY' in config['ide']['deployButtonText'] or \
        not 'DEPLOYING' in config['ide']['deployButtonText'] or \
        not 'DEPLOYED' in config['ide']['deployButtonText'] or \
        not 'FAILED' in config['ide']['deployButtonText']:
        LOG.error('Missing key(s) from ide.deployButtonText. Expected keys: TODEPLOY, DEPLOYING, DEPLOYED, FAILED')
        success = False


    if not type(config['states']) == type([]):
        LOG.error('\'states\' should be a list!')
        success = False

    if len(config['states']) < 2:
        LOG.error('Please add at least 2 states')
        success = False
    
    for i, state in enumerate(config['states'], 1):
        if not 'messages' in state:
            LOG.warning('You are not sending any message in state {i}')
        if 'messages' in state and not type(state['messages']) == type([]):
            LOG.error(f"Invalid type! 'states[{i}].messages' should be a list")
            success = False

    return success

def get_frontend_config(config: dict):
    LOG.info('Generating frontend config...')
    frontend_config = copy.deepcopy(config)
    # Removing unnecessary stuff
    frontend_config.pop('webservice')
    frontend_config.pop('terminal')
    frontend_config.pop('states')
    frontend_config['dashboard'].pop('messageSpeed')
    frontend_config['ide'].pop('patterns')
    # Addig/reorganizing necessary stuff
    frontend_config['dashboard']['hideMessages'] = False
    frontend_config['dashboard']['iframeUrl'] = config['webservice']['iframeUrl']
    frontend_config['dashboard']['showUrlBar'] = config['webservice']['showUrlBar']
    frontend_config['dashboard']['reloadIframeOnDeploy'] = config['webservice']['reloadIframeOnDeploy']
    frontend_config['dashboard']['terminalMenuItem'] = config['terminal']['terminalMenuItem']
    frontend_config['ide']['autoSaveInterval'] = 444
    frontend_config['site'] = {'askReloadSite': False, 'documentTitle': 'Avatao Tutorials'}

    return yaml.dump(frontend_config)


def get_app_fsm(config: dict):
    LOG.info('Generating app_fsm.py...')
    app_fsm = '''
from tfw.fsm import LinearFSM
from tfw.components.frontend import MessageSender
from tfw.main import TFWUplinkConnector

class App(LinearFSM):
    def __init__(self):
        super().__init__(len([x for x in dir(self) if x.startswith('on_enter')]) + 1)
        self.uplink = TFWUplinkConnector()
        self.message_sender = MessageSender(self.uplink)

'''
    success = True
    for i, state in enumerate(config['states'], 1):
        app_fsm += f'    def on_enter_{i}(self, event_data):\n'
        # Messages
        if 'messages' in state:
            app_fsm += f"        messages = {json.dumps(state['messages'], indent=4)[:-2]}]\n"
            if 'buttons' in state:
                app_fsm += f"        self.message_sender.queue_messages(messages, buttons={state['buttons']})\n\n"
            else:
                app_fsm += f"        self.message_sender.queue_messages(messages)\n\n"

        for key, value in state.items():
            payload = {}
            if key == 'buttons' or key == 'messages':
                continue
            # Dashboard
            elif key == 'dashboard.layout':
                if not value in config['dashboard']['enabledLayouts']:
                    LOG.error(f"Invalid (or disabled) layout: state[{i}] -> {key}: {value}")
                    success = False
                    continue
                payload = {'key': 'frontend.dashboard', 'layout': value}
            # Webservice
            elif key == 'webservice.iframeUrl':
                payload = {'key': 'frontend.dashboard', 'iframeUrl': value}
            elif key == 'webservice.showUrlBar':
                payload = {'key': 'frontend.dashboard', 'showUrlBar': value}
            elif key == 'webservice.reloadIframe' and value == True:
                payload = {'key': 'frontend.reloadIframe'}
            # Terminal
            elif key == 'terminal.terminalMenuItem':
                if not value in ['terminal', 'console']:
                    LOG.error(f"Invalid terminal.terminalMenuItem: state[{i}] -> {key}: {value}. Allowed values: console, terminal")
                    success = False
                    continue
                payload = {'key': 'frontend.dashboard', 'terminalMenuItem': value}
            elif key == 'terminal.write':
                payload = {'key': 'terminal.write', 'command': value}
            elif key == 'console.write':
                payload = {'key': 'console.write', 'command': value}
            # WebIDE
            elif key == 'ide.patterns':
                if 'ide.selectFile' in state:
                    payload = {'key': 'ide.read', 'filename': state['ide.selectFile'], 'patterns': value}
                else:
                    payload = {'key': 'ide.read', 'patterns': value}
            elif key == 'ide.selectFile':
                if 'ide.patterns' in state:
                    continue
                else:
                    payload = {'key': 'ide.read', 'filename': value}
            elif key == 'ide.showDeployButton':
                payload = {'key': 'frontend.ide', 'showDeployButton': value}
            else:
                LOG.warning(f"Instruction not supported: state[{i}] -> {key}: {value}")
                continue

            app_fsm += f"        self.uplink.send_message({payload})\n\n"
    if success:
        return app_fsm
    else:
        return False

config = open_and_parse_config('app.yml')
if not config:
    exit(1)
if not validate_config(config):
    exit(2)

with open('frontend_config.yaml', 'w') as f:
    f.write(get_frontend_config(config))

app_fsm = get_app_fsm(config)
if app_fsm:
    with open('app_fsm.py', 'w') as f:
        f.write(app_fsm)
    LOG.info('Success!')
else:
    exit(3)


