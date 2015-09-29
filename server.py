# pyRESTvk/server.py
# Dan Allongo (daniel.s.allongo@gmail.com)

# Provides a JSON-only RESTful interface for execution of virtual keystroke macros.
# Using basic HTTP authentication with no WWW authentication challenge as browsers
# are not the target client. Valid key codes are loaded from external file.

from flask import Flask, url_for, redirect, abort, request, jsonify, make_response
from werkzeug.exceptions import default_exceptions, HTTPException
import os.path
import random
import datetime
import socket
import json
import win32api
import win32con
import time
import sys

# server changes that affect endpoint functionality or break test script should increment api version.
app_version = '0.6.0'
api_version = '1.1'

# checks for auth key and creates one if needed.
def read_auth_key(key_file):
	key = None
	if os.path.isfile(key_file) and os.path.getsize(key_file) > 0:
		f  = open(key_file)
		key = f.readline().rstrip()
		f.close()
	if not key:
		print "File Not Found: Creating '%s'" % key_file
		key = '-'.join([str(int(random.random()*1000)) for i in xrange(4)])
		f = open(key_file,'w')
		f.write(key)
		f.close()
	return key

# validates config schema.
def validate_config(config):
	global key_codes, key_combo_seps
	http_reserved = ["!", "*", "'", "(", ")", ";", ":", "@", "&", "=", "+", "$", ",", "/", "?", "#", "[", "]"]
	if 'name' not in config: 
		return False, "Config Missing Key: 'name'"
	if not config['name']: 
		return False, "Config Empty Key: 'name'"
	for c in http_reserved:
		if c in config['name']:
			return False, "Invalid Character: '%s' in Config 'name' %s'" % (c, config['name'])
	if 'macros' not in config:
		return False, "Config Missing Key: 'macros' for Config '%s'" % config['name']
	if not config['macros']:
		return False, "Config Empty Key: 'macros' for Config '%s'" % config['name']
	for m in config['macros']:
		if 'name' not in m:
			return False, "Macro Missing Key: 'name' for Config '%s'" % config['name']
		if not m['name']:
			return False, "Macro Empty Key: 'name' for Config '%s'" % config['name']
		for c in http_reserved:
			if c in m['name']:
				return False, "Invalid Character: '%s' in Macro 'name' '%s' for Config '%s'" % (c, m['name'], config['name'])
		if 'keys' not in m:
			return False, "Macro Missing Key: 'keys' in Macro '%s' for Config '%s'" % (m['name'], config['name'])
		if not m['keys']:
			return False, "Macro Empty Key: 'keys' in Macro '%s' for Config '%s'" % (m['name'], config['name'])
		if [x['name'] for x in config['macros']].count(m['name']) > 1:
			return False, "Duplicate Macro: '%s' Exists for Config '%s'" % (m['name'], config['name'])
		combo = []
		open_combo = False
		for k in m['keys'].split():
			if k not in key_codes and k not in [key_combo_seps['open'], key_combo_seps['close']]:
				return False, "Invalid Key Code: '%s' in Macro '%s' for Config '%s'" % (k, m['name'], config['name'])
			if k == key_combo_seps['open']:
				if open_combo:
					return False, "Invalid Combo: Nested '%s' in Macro '%s' for Config '%s'" % (key_combo_seps['open'], m['name'], config['name'])
				open_combo = True
				continue
			if k == key_combo_seps['close']:
				if not open_combo:
					return False, "Invalid Combo: '%s' Before '%s' in Macro '%s' for Config '%s'" % (key_combo_seps['close'], key_combo_seps['open'], m['name'], config['name'])
				open_combo = False
			if open_combo:
				combo.append(key_codes[k])
				continue
			if combo:
				combo = []
		if open_combo or combo:
			return False, "Invalid Combo: '%s' Without '%s' in Macro '%s' for Config '%s'" % (key_combo_seps['open'], key_combo_seps['close'], m['name'], config['name'])
	return True, "OK"

# writes validated configs to file.
def write_configs(configs, configs_file):
	to_disk = []
	for c in configs:
		validated, msg = validate_config(c)
		if not validated:
			print "Discarding Config: %s" % msg
			continue
		to_disk.append(c)
	f = open(configs_file,'w')
	f.write(json.dumps(to_disk, indent=4, separators=(',',':'), sort_keys=True))
	f.close()
	return

# reads validated configs from file.
def read_configs(configs_file):
	configs = []
	if os.path.isfile(configs_file) and os.path.getsize(configs_file) > 0:
		f  = open(configs_file)
		from_disk = json.loads(f.read())
		f.close()
		for c in from_disk:
			validated, msg = validate_config(c)
			if not validated:
				print "Discarding Config: %s" % msg
				continue
			configs.append(c)
	return configs

# reads key codes from file.
def read_key_codes(codes_file):
	codes = None
	if not os.path.isfile(codes_file) or not os.path.getsize(codes_file) > 0:
		print "Error: File Not Found: '%s'" % codes_file
		sys.exit(1)
	f  = open(codes_file)
	codes = json.loads(f.read())
	f.close()
	return codes

# simulate key presses for given key codes.
def press_keys(duration, keys=[]):
	for k in keys:
		win32api.keybd_event(k, 0, win32con.KEYEVENTF_EXTENDEDKEY | 0, 0)
	time.sleep(duration)
	for k in keys:
		win32api.keybd_event(k, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
	return

# checks for HTTP auth info in request.
def authorized():
	global auth_key
	if not request.authorization or request.authorization.password != auth_key:
		return False
	return True


app = Flask(__name__)

def make_json_error(ex):
	response = jsonify(message=str(ex))
	response.status_code = (ex.code
		if isinstance(ex, HTTPException)
		else 500)
	return response

for code in default_exceptions.iterkeys():
	app.error_handler_spec[None][code] = make_json_error

# root is readable to all and gives server status with clients and configs summary.
@app.route('/')
def server_status():
	global status, configs, clients
	status['clients'] = {'url':url_for('client_list', _external=True), 'count':len(clients)}
	status['configs'] = {'url':url_for('register_config', _external=True), 'count':len(configs)}
	return jsonify(status)

# adds authenticated client to list. not strictly necessary to perform authenticated tasks.
@app.route('/auth')
def register_client():
	global clients
	if not authorized():
		abort(401)
	client = {}
	client['name'] = request.authorization.username
	client['address'] = request.remote_addr
	if not filter(lambda c: c['name'] == client['name'] and c['address'] == client['address'], clients):
		client['since'] = datetime.datetime.now()
		clients.append(client)
	return jsonify(message='OK')

# performs immediate shutdown.
@app.route('/shutdown')
def server_shutdown():
	if not authorized():
		abort(401)
	request.environ.get('werkzeug.server.shutdown')()
	return jsonify(message='OK')

# list of authenticated clients that have registered on /auth.
@app.route('/clients')
def client_list():
	global clients
	return jsonify(clients=[dict(c, url = url_for('select_client', name=c['name'], _external=True)) for c in clients])

# lookup client by name. read-only.
@app.route('/clients/<name>')
def select_client(name):
	global clients
	client = filter(lambda c: c['name'] == name, clients)
	if not client:
		abort(404)
	client = client.pop()
	return jsonify(client)

# list all configs this server knows about and allow adding new ones.
@app.route('/configs', methods=['GET','POST'])
def register_config():
	global configs, configs_file
	if request.method == 'GET':
		return jsonify(configs=[{'name':x['name'], 'url':url_for('select_config', name=x['name'], _external=True), 'macros':len(x['macros'])} for x in configs])
	if not authorized():
		abort(401)
	config = request.json
	validated, msg = validate_config(config)
	if not validated:
		return make_response(jsonify(message=msg), 400)
	# allow clients to validate config data without altering server cache using /configs?validate_only=true
	if request.args.get('validate_only', '').lower() == 'true':
		return jsonify(message=msg)
	if filter(lambda c: c['name'] == config['name'], configs):
		return make_response(jsonify(message="Duplicate Entry: 'name' '%s' Exists" % config['name']), 409)
	configs.append(config)
	write_configs(configs, configs_file)
	return make_response(jsonify(url=url_for('select_config', name=config['name'], _external=True)), 201, {'Location':url_for('select_config', name=config['name'])})

# retrieve config in format that is acceptable to post back as new after delete. allow put for updates.
@app.route('/configs/<name>', methods=['GET','PUT','DELETE'])
def select_config(name):
	global configs, configs_file
	config = filter(lambda c: c['name'] == name, configs)
	if not config:
		abort(404)
	config = config.pop()
	if request.method == 'GET':
		return jsonify(config)
	if not authorized():
		abort(401)
	if request.method == 'DELETE':
		configs.remove(config)
		write_configs(configs, configs_file)
		return make_response('', 204)
	x = request.json
	validated, msg = validate_config(x)
	if not validated:
		return make_response(jsonify(message=msg), 400)
	if x['name'] != name and filter(lambda c: c['name'] == x['name'], configs):
		return make_response(jsonify(message="Duplicate Entry: 'name' '%s' Exists" % x['name']), 409)
	configs.remove(config)
	configs.append(x)
	write_configs(configs, configs_file)
	if x['name'] != name:
		return make_response(jsonify(url=url_for('select_config', name=x['name'], _external=True)), 201, {'Location':url_for('select_config', name=x['name'])})
	return make_response('', 204)

# authenticated execution of macro key sequences. minimal validation since it should have passed validation twice by now.
@app.route('/configs/<config_name>/macros/<name>')
def select_macro(config_name, name):
	global configs, key_codes, key_duration, key_combo_seps
	if not authorized():
		abort(401)
	config = filter(lambda c: c['name'] == config_name, configs)
	if not config:
		abort(404)
	config = config.pop()
	macro = filter(lambda m: m['name'] == name, config['macros'])
	if not macro:
		abort(404)
	macro = macro.pop()
	combo = []
	open_combo = False
	for k in macro['keys'].split():
		if k == key_combo_seps['open']:
			open_combo = True
			continue
		if k == key_combo_seps['close']:
			open_combo = False
		if open_combo:
			combo.append(key_codes[k])
			continue
		if combo:
			press_keys(key_duration, combo)
			combo = []
		else:
			press_keys(key_duration, [key_codes[k]])
		time.sleep(key_duration)
	return jsonify(message='OK')


def setup():
	global app_version, api_version
	global status, clients, auth_key, key_codes, key_duration, key_combo_seps, configs, configs_file

	defaults = {
		'ip':'0.0.0.0',
		'port':5000,
		'auth_file':'.auth_key',
		'configs_file':'.configs',
		'key_codes_file':'key_codes.json',
		'key_duration':0.025,
		'key_combo_seps':{'open':'[', 'close':']'}
	}

	settings_file = '.settings'
	# get server settings from command line arg
	if len(sys.argv) == 2:
		settings_file = sys.argv[1]
	settings_file = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),settings_file))

	# write defaults to disk if no file
	if not os.path.isfile(settings_file) or not os.path.getsize(settings_file) > 0:
		print "File Not Found: Creating '%s'" % settings_file
		f = open(settings_file, 'w')
		f.write(json.dumps({}))
		f.close()
	
	# read settings from file
	f = open(settings_file)
	settings = json.loads(f.read())
	f.close()

	# check all needed settings keys exist, add missing settings
	for k in defaults:
		if k not in settings:
			print "Key Not Found: Adding '%s' to '%s'" % (k, settings_file)
			settings[k] = defaults[k]
			f = open(settings_file, 'w')
			f.write(json.dumps(settings, indent=4, separators=(',',':'), sort_keys=True))
			f.close()

	# resolve file paths
	for k in settings:
		if k.endswith('_file'):
			settings[k] = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),settings[k]))

	# server status and clients/configs summary.
	status = {
		'application':{
			'name':os.path.basename(sys.argv[0]),
			'version':app_version,
			'api':api_version
		},
		'server':{
			'name':socket.getfqdn(),
			'address':socket.gethostbyname(socket.getfqdn()),
			'port':settings['port'],
			'up-since':datetime.datetime.now()
		},
		'clients':[],
		'configs':[]
	}

	clients = []

	auth_key = read_auth_key(settings['auth_file'])

	key_codes = read_key_codes(settings['key_codes_file'])
	key_duration = settings['key_duration']
	key_combo_seps = settings['key_combo_seps']

	# key_.* globals must be populated before configs can be loaded
	configs_file = settings['configs_file']
	configs = read_configs(configs_file)

	return {'host':settings['ip'], 'port':settings['port']}


if __name__ == '__main__':
	kwargs = setup()
	app.run(threaded=True, **kwargs)
