# pyRESTvk/example/main.py
# Dan Allongo (daniel.s.allongo@gmail.com)

# A sample client program using kivy to create a button interface with the 
# widget event handlers calling the pyRESTvk service.

from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from requests import Session, adapters
from distutils.version import LooseVersion
import json
import platform
import os.path
import sys


class MFD(FloatLayout):
    def __init__(self, mappings_file, config_file, auth_file, server_url, api):
        FloatLayout.__init__(self)
        # load the kivy button mappings for the macros
        f = open(mappings_file)
        self.mappings = json.loads(f.read())
        f.close()
        # apply button labels
        for id_str, widget in self.ids.iteritems():
            if id_str in self.mappings and self.mappings[id_str]['label']:
                self.ids[id_str].text = self.mappings[id_str]['label']
        # load the macro config for this application
        f = open(config_file)
        self.config = json.loads(f.read())
        f.close()
        # pass hostname as username
        username = platform.node()
        # get password from key file
        f = open(auth_file)
        password = f.readline().rstrip()
        f.close()
        # session will send auth and headers for requests, retry up to 3x
        self.s = Session()
        self.s.mount("http://", adapters.HTTPAdapter(max_retries=3))
        self.s.auth=(username, password)
        self.s.headers.update({
            'X-Requested-With':'XMLHttpRequest',
            'Accept':'application/json',
            'Content-Type':'application/json'
        })
        self.server_url = server_url
        self.api = api
        # authenticate and register client
        r = self.s.get(self.server_url + '/auth', timeout=5)
        assert r.status_code == 200
        # confirm server api version
        r = self.s.get(self.server_url, timeout=5)
        assert LooseVersion(str(r.json()['application']['api'])) >= LooseVersion(str(self.api))
        # get resource URLs
        r = self.s.get(self.server_url, timeout=5)
        configs_url = r.json()['configs']['url']
        r = self.s.get(configs_url, timeout=5)
        # find and update config if it exists
        c = filter(lambda x: x['name'] == self.config['name'], r.json()['configs'])
        config_url = ''
        if c:
            c = c.pop()
            config_url = c['url']
            r = self.s.get(config_url, timeout=5)
            if r.json() != self.config:
                r = self.s.put(config_url, json=self.config, timeout=5)
                assert r.status_code == 204
        else:
            r = self.s.post(configs_url, json=self.config, timeout=5)
            assert r.status_code == 201
            config_url = r.headers['location']
        self.config_url = config_url
        return

    def shutdown(self):
        # call server shutdown
        self.s.get(self.server_url + '/shutdown', timeout=5)
        return

    def make_request(self, btn):
        for id_str, widget in self.ids.iteritems():
            if widget == btn:
                if id_str in self.mappings and self.mappings[id_str]['macro']:
                    # run macro
                    r = self.s.get(self.config_url + '/macros/' + self.mappings[id_str]['macro'], timeout=5)
                    assert r.status_code == 200
                break
        return


class MFDApp(App):
    def build(self):
        # get client settings
        f = open(os.path.join(os.path.dirname(sys.argv[0]),'settings.json'))
        settings = json.loads(f.read())
        f.close()
        for k in settings:
            if k.endswith('_file'):
                # all file paths are relative to this one
                settings[k] = os.path.join(os.path.dirname(sys.argv[0]),settings[k])        
        return MFD(**settings)

    def on_stop(self):
        self.root.shutdown()
        return


if __name__ == '__main__':
    MFDApp().run()
