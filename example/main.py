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
import os
import sys

api_version = '2.0'

class SwitchPanel(FloatLayout):
    def __init__(self, mappings, profile, auth_key, server_url, colors={}, **kwargs):
        global api_version
        FloatLayout.__init__(self)
        # load the kivy button mappings for the macros
        with open(mappings) as f:
        	self.mappings = json.load(f)
        # load the macro profile for this application
        with open(profile) as f:
	        p = json.load(f)
        k = p.keys()[0]
        # apply button labels, colors, and macros
        for i, b in self.mappings.iteritems():
            if i in self.ids:
                if 'label' in b:
                    self.ids[i].text = b['label']
                if 'color' in b and b['color'] in colors:
                    self.ids[i].color = colors[b['color']]
                if 'macro' in b and b['macro'] in p[k]:
                    self.ids[i].bind(on_press=self.make_request)
                if 'background_down' in dir(self.ids[i]):
                    if 'background_down' in b:
                        self.ids[i].background_down = b['background_down']
                    else:    
                        self.ids[i].background_down = 'atlas://data/images/defaulttheme/button_disabled'
        # pass hostname as username
        username = platform.node()
        # set password to auth key
    	password = auth_key
        # session will send auth for requests, retry up to 3x
        self.s = Session()
        self.s.mount("http://", adapters.HTTPAdapter(max_retries=3))
        self.s.auth=(username, password)
        self.server_url = server_url
        # authenticate and register client
        r = self.s.get(self.server_url + '/auth', timeout=5)
        assert r.status_code == 200
        # confirm server api version
        r = self.s.get(self.server_url, timeout=5)
        assert LooseVersion(str(r.json()['application']['api'])) >= LooseVersion(str(api_version))
        # get resource URLs
        r = self.s.get(self.server_url, timeout=5)
        profiles_url = r.json()['profiles']['url']
        # validate profile
        r = self.s.post(profiles_url, files={k:open(profile, 'rb')}, params={'validate_only':'true'}, timeout=5)
        if r.status_code != 200:
            print r.json()['message']
            sys.exit(1)
        r = self.s.get(profiles_url, timeout=5)
        # find and update profile if it exists
        profiles = r.json()
        profile_url = ''
        if k in profiles:
            profile_url = profiles[k]['url']
            r = self.s.get(profile_url, timeout=5)
            if r.json() != p:
                r = self.s.put(profile_url, files={k:open(profile, 'rb')}, timeout=5)
                assert r.status_code == 204
        else:
            r = self.s.post(profiles_url, files={k:open(profile, 'rb')}, timeout=5)
            assert r.status_code == 201
            profile_url = r.headers['location']
        self.profile_url = profile_url
        return

    def shutdown(self):
        # call server shutdown
        self.s.get(self.server_url + '/shutdown', timeout=5)
        return

    def make_request(self, btn):
        for i, w in self.ids.iteritems():
            if w == btn and i in self.mappings:
                # run macro
                r = self.s.get(self.profile_url + '/' + self.mappings[i]['macro'], timeout=5)
                assert r.status_code == 200
        return


class defaultApp(App):
    def __init__(self):
    	# search in local path to script, first
        settings_file = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'settings.json'))
        # commandline arg should be relative to current working directory
        if len(sys.argv) == 2:
            settings_file = os.path.abspath(os.path.join(os.getcwd(), os.path.expandvars(sys.argv[1])))
        if not os.path.isfile(settings_file) or not os.path.getsize(settings_file) > 0:
            print "Error: File Not Found: '%s'" % settings_file
            sys.exit(1)

        # read settings from file
        with open(settings_file) as f:
	        settings = json.load(f)

        # check all needed settings keys exist
        for k in ['mappings', 'profile', 'auth_key', 'server_url']:
            if k not in settings:
                print "Error: Missing Key '%s' in '%s'" % (k, settings_file)
                sys.exit(1)

        # resolve file paths relative to settings file
        for k in settings:
            if k in ['mappings', 'profile', 'kv_file']:
                settings[k] = os.path.abspath(os.path.join(os.path.dirname(settings_file), os.path.expandvars(settings[k])))
                if not os.path.isfile(settings[k]) or not os.path.getsize(settings[k]) > 0:
                    print "Error: File Not Found: '%s'" % settings[k]
                    sys.exit(1)

        # set kv_file if override exists
        k = settings.pop('kv_file', None)
        if k:
        	self.kv_file = k
        self.settings = settings

        # our init is done, call parent class init to finish
        App.__init__(self)
        return

    def build(self):
        return SwitchPanel(**self.settings)

    def on_stop(self):
        self.root.shutdown()
        return


if __name__ == '__main__':
    defaultApp().run()
