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
from kivy.logger import Logger
import logging, logging.handlers

api_version = '2.1'

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
        if r.status_code != 200:
            Logger.error('init: Unable to Authenticate: Expected Response Code 200, Got {0}'.format(r.status_code))
            exit(1)
        # confirm server api version
        r = self.s.get(self.server_url, timeout=5)
        if LooseVersion(r.json()['application']['api']) < LooseVersion(api_version):
            Logger.error('init: Incompatible Server: API version >= {0} Required'.format(api_version))
            exit(1)
        # get resource URLs
        r = self.s.get(self.server_url, timeout=5)
        profiles_url = r.json()['profiles']['url']
        # validate profile
        r = self.s.post(profiles_url, files={k:open(profile, 'rb')}, params={'validate_only':'true'}, timeout=5)
        if r.status_code != 200:
            Logger.error(r.json()['message'])
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
                if r.status_code != 204:
                    Logger.error('init: Unable to Update Profile: Expected Response Code 204, Got {0}'.format(r.status_code))
                    exit(1)
        else:
            r = self.s.post(profiles_url, files={k:open(profile, 'rb')}, timeout=5)
            if r.status_code != 201:
                Logger.error('init: Unable to Create Profile: Expected Response Code 201, Got {0}'.format(r.status_code))
                exit(1)
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
            	p = self.mappings[i].get('params', {})
                # run macro
                r = self.s.get(self.profile_url + '/' + self.mappings[i]['macro'], params=p, timeout=5)
                Logger.info('make_request: {0} - {1} (in {2} sec)'.format(r.url, r.status_code, r.elapsed.total_seconds()))
        return


class defaultApp(App):
    def __init__(self):
    	# search in local path to script, first
        settings_file = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'settings.json'))
        # commandline arg should be relative to current working directory
        if len(sys.argv) == 2:
            settings_file = os.path.abspath(os.path.join(os.getcwd(), os.path.expandvars(sys.argv[1])))
        if not os.path.isfile(settings_file) or not os.path.getsize(settings_file) > 0:
            Logger.error("init: File Not Found '{0}'".format(settings_file))
            sys.exit(1)

        # read settings from file
        with open(settings_file) as f:
	        settings = json.load(f)

        # check all needed settings keys exist
        for k in ['mappings', 'profile', 'auth_key', 'server_url']:
            if k not in settings:
                Logger.error("init: Missing Key '{0}' in '{1}'".format(k, settings_file))
                sys.exit(1)

        # resolve file paths relative to settings file
        for k in settings:
            if k in ['mappings', 'profile', 'kv_file']:
                settings[k] = os.path.abspath(os.path.join(os.path.dirname(settings_file), os.path.expandvars(settings[k])))
                if not os.path.isfile(settings[k]) or not os.path.getsize(settings[k]) > 0:
                    Logger.error("init: File Not Found '{0}'".format(settings[k]))
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
    h = logging.handlers.RotatingFileHandler(filename=os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'client.log')), maxBytes=1024*1024, backupCount=9)
    h.setLevel(logging.INFO)
    Logger.addHandler(h)
    Logger.setLevel(logging.INFO)
    defaultApp().run()
