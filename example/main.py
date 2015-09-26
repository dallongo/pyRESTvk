# pyRESTvk/example/main.py
# Dan Allongo (daniel.s.allongo@gmail.com)

# A sample client program using kivy to create a button interface with the 
# widget event handlers calling the pyRESTvk service.

import kivy
kivy.require('1.9.0')
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
import requests
import json
import platform
import os

# default host and port
server_ip = '127.0.0.1'
server_port = 5000
base_url = 'http://' + server_ip + ':' + str(server_port)
# using this API version
api_version = 1
# pass hostname as username
username = platform.node()
# get password from key file
f = open(os.path.join(os.path.dirname(__file__),'.auth_key'))
password = f.readline().rstrip()
f.close()
# set correct request headers
headers = {
    'X-Requested-With':'XMLHttpRequest',
    'Accept':'application/json',
    'Content-Type':'application/json'
}
# load the macro config for this application
f = open(os.path.join(os.path.dirname(__file__),'key config.json'))
key_config = json.loads(f.read())
f.close()
# load the kivy button mappings for the macros
f = open(os.path.join(os.path.dirname(__file__),'button mappings.json'))
button_mappings = json.loads(f.read())
f.close()
# session will send auth and headers for subsequent requests
s = requests.Session()
s.auth=(username,password)
s.headers.update(headers)
# authenticate and register client
r = s.get(base_url + '/auth')
assert r.status_code == 200
# confirm server api version
r = s.get(base_url)
assert r.json()['application']['api'] == api_version
# get resource URLs
r = s.get(base_url)
# get configs resource
configs_url = r.json()['configs']['url']
r = s.get(configs_url)
# find and update config if it exists
config = filter(lambda x: x['name'] == key_config['name'], r.json()['configs'])
config_url = ''
if config:
    config = config.pop()
    config_url = config['url']
    r = s.get(config_url)
    if r.json() != key_config:
        r = s.put(config_url, json=key_config)
        assert r.status_code == 204
else:
    r = s.post(configs_url, json=key_config)
    assert r.status_code == 201
    config_url = r.headers['location']


class MFD(FloatLayout):
    def make_request(self, btn):
        global mappings, s, config_url
        for id_str, widget in self.ids.iteritems():
            if widget == btn:
                if id_str in button_mappings and button_mappings[id_str]:
                    r = s.get(config_url + '/macros/' + button_mappings[id_str])
                    assert r.status_code == 200
                break
        return


class MFDApp(App):
    def build(self):
        return MFD()


if __name__ == '__main__':
    global s, base_url
    MFDApp().run()
    r = s.get(base_url + '/shutdown')
