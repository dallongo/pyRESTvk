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

api_version = '1.1'

class MFD(FloatLayout):
    def __init__(self, mappings_file, config_file, auth_file, server_url, colors={}, **kwargs):
        global api_version
        FloatLayout.__init__(self)
        # load the kivy button mappings for the macros
        f = open(mappings_file)
        self.mappings = json.loads(f.read())
        f.close()
        # load the macro config for this application
        f = open(config_file)
        self.config = json.loads(f.read())
        f.close()
        # apply button labels, colors, and macros
        for i, b in self.mappings.iteritems():
            if i in self.ids:
                if 'label' in b:
                    self.ids[i].text = b['label']
                if 'color' in b and b['color'] in colors:
                    self.ids[i].color = colors[b['color']]
                if 'macro' in b and filter(lambda m: m['name'] == b['macro'], self.config['macros']):
                    self.ids[i].bind(on_press=self.make_request)
                if 'background_down' in dir(self.ids[i]):
                    if 'background_down' in b:
                        self.ids[i].background_down = b['background_down']
                    else:    
                        self.ids[i].background_down = 'atlas://data/images/defaulttheme/button_disabled'
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
        # authenticate and register client
        r = self.s.get(self.server_url + '/auth', timeout=5)
        assert r.status_code == 200
        # confirm server api version
        r = self.s.get(self.server_url, timeout=5)
        assert LooseVersion(str(r.json()['application']['api'])) >= LooseVersion(str(api_version))
        # get resource URLs
        r = self.s.get(self.server_url, timeout=5)
        configs_url = r.json()['configs']['url']
        # validate config
        r = self.s.post(configs_url, json=self.config, params={'validate_only':'true'}, timeout=5)
        if r.status_code != 200:
            print r.json()['message']
            sys.exit(1)
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
        for i, w in self.ids.iteritems():
            if w == btn and i in self.mappings:
                # run macro
                r = self.s.get(self.config_url + '/macros/' + self.mappings[i]['macro'], timeout=5)
                assert r.status_code == 200
        return


class MFDApp(App):
    def build(self):
        settings_file = 'settings.json'
        # get client settings from command line arg
        if len(sys.argv) == 2:
            settings_file = sys.argv[1]
        settings_file = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),settings_file))
        if not os.path.isfile(settings_file) or not os.path.getsize(settings_file) > 0:
            print "Error: File Not Found: '%s'" % settings_file
            sys.exit(1)

        # read settings from file
        f = open(settings_file)
        settings = json.loads(f.read())
        f.close()

        # check all needed settings keys exist
        for k in ['mappings_file', 'config_file', 'auth_file', 'server_url']:
            if k not in settings:
                print "Error: Missing Key '%s' in '%s'" % (k, settings_file)
                sys.exit(1)

        # resolve file paths
        for k in settings:
            if k.endswith('_file'):
                settings[k] = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),settings[k]))
                if not os.path.isfile(settings[k]) or not os.path.getsize(settings[k]) > 0:
                    print "Error: File Not Found: '%s'" % settings[k]
                    sys.exit(1)

        return MFD(**settings)

    def on_stop(self):
        self.root.shutdown()
        return


if __name__ == '__main__':
    MFDApp().run()
