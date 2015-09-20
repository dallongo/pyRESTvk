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

# default port for flask
server_port = 5000

# server changes that affect endpoint functionality or break test script should increment api version.
app_version = 0.5
api_version = 1

# server status and clients/configs summary.
status = {
	'application':{
		'name':os.path.basename(__file__),
		'version':app_version,
		'api':api_version
	},
	'server':{
		'name':socket.getfqdn(),
		'address':socket.gethostbyname(socket.getfqdn()),
		'port':server_port,
		'up-since':datetime.datetime.now()
	},
	'clients':[],
	'configs':[]
}

clients = []

# checks for auth key and creates one if needed.
def read_auth_key():
	key = None
	key_file = os.path.join(os.path.dirname(__file__),'.auth_key')
	if os.path.isfile(key_file) and os.path.getsize(key_file) > 0:
		f  = open(key_file)
		key = f.readline().rstrip()
		f.close()
	if not key:
		key = '-'.join([str(int(random.random()*1000)) for i in xrange(4)])
		f = open(key_file,'w')
		f.write(key)
		f.close()
	return key

auth_key = read_auth_key()

# checks for HTTP auth info in request.
def authorized():
	global auth_key
	if not request.authorization or request.authorization.password != auth_key:
		return False
	return True

# validates config schema.
def validate_config(config):
	global key_codes, key_combo_seps
	if set(config) != set(['name', 'macros']) or not config['name'] or not config['macros']:
		return False
	for m in config['macros']:
		if set(m) != set(['name', 'keys']) or not m['name'] or not m['keys'] or [x['name'] for x in config['macros']].count(m['name']) > 1:
			return False
		combo = []
		open_combo = False
		for k in m['keys'].split():
			if k not in key_codes and k not in [key_combo_seps['open'], key_combo_seps['close']]:
				return False
			if k == key_combo_seps['open']:
				if open_combo:
					return False
				open_combo = True
				continue
			if k == key_combo_seps['close']:
				if not open_combo:
					return False
				open_combo = False
			if open_combo:
				combo.append(k)
				continue
			if combo:
				combo = []
		if open_combo or combo:
			return False
	return True

# writes validated configs to file.
def write_configs():
	global configs, configs_file
	to_disk = []
	for c in configs:
		if validate_config(c):
			to_disk.append(c)
	f = open(configs_file,'w')
	f.write(json.dumps(to_disk, indent=4, separators=(',',':'), sort_keys=True))
	f.close()
	return

# reads validated configs from file.
def read_configs():
	global configs_file
	configs = []
	if os.path.isfile(configs_file) and os.path.getsize(configs_file) > 0:
		f  = open(configs_file)
		from_disk = json.loads(f.read())
		f.close()
		for c in from_disk:
			if validate_config(c):
				configs.append(c)
	return configs

configs_file = os.path.join(os.path.dirname(__file__),'.configs')
configs = read_configs()

# reads key codes from file.
def read_key_codes():
	codes = None
	codes_file = os.path.join(os.path.dirname(__file__),'key_codes.json')
	if os.path.isfile(codes_file) and os.path.getsize(codes_file) > 0:
		f  = open(codes_file)
		codes = json.loads(f.read())
		f.close()
	return codes

key_codes = read_key_codes()
key_duration = 0.025
key_combo_seps = {'open':'[', 'close':']'}

# simulate key presses for given key codes.
def press_keys(keys=[]):
	global key_codes, key_duration
	for k in keys:
		win32api.keybd_event(key_codes[k], 0, win32con.KEYEVENTF_EXTENDEDKEY | 0, 0)
	time.sleep(key_duration)
	for k in keys:
		win32api.keybd_event(key_codes[k], 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
	return


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
	return jsonify(message='Client Authorized')

# performs shutdown after this request if app is running from werkzeug.
@app.route('/shutdown')
def server_shutdown():
	if not authorized():
		abort(401)
	request.environ.get('werkzeug.server.shutdown')()
	return jsonify(message='Shutdown Requested')

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
	global configs
	if request.method == 'GET':
		return jsonify(configs=[{'name':x['name'], 'url':url_for('select_config', name=x['name'], _external=True), 'macros':len(x['macros'])} for x in configs])
	if not authorized():
		abort(401)
	config = request.json
	if not validate_config(config):
		return make_response(jsonify(message="Malformed Entry: Missing, Incorrect, or Duplicate Keys"), 400)
	if filter(lambda c: c['name'] == config['name'], configs):
		return make_response(jsonify(message="Duplicate Entry: 'name' '%s' Exists" % config['name']), 409)
	configs.append(config)
	write_configs()
	return make_response(jsonify(url=url_for('select_config', name=config['name'], _external=True)), 201, {'Location':url_for('select_config', name=config['name'])})

# retrieve config in format that is acceptable to post back as new after delete. allow put for updates.
@app.route('/configs/<name>', methods=['GET','PUT','DELETE'])
def select_config(name):
	global configs
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
		write_configs()
		return make_response('', 204)
	x = request.json
	if not validate_config(x):
		return make_response(jsonify(message="Malformed Entry: Missing, Incorrect, or Duplicate Keys"), 400)
	if x['name'] != name and filter(lambda c: c['name'] == x['name'], configs):
		return make_response(jsonify(message="Duplicate Entry: 'name' '%s' Exists" % x['name']), 409)
	configs.remove(config)
	configs.append(x)
	write_configs()
	if x['name'] != name:
		return make_response(jsonify(url=url_for('select_config', name=x['name'], _external=True)), 201, {'Location':url_for('select_config', name=x['name'])})
	return make_response('', 204)

# authenticated execution of macro key sequences. minimal validation since it should have passed validation twice by now.
@app.route('/configs/<config_name>/macros/<name>')
def select_macro(config_name, name):
	global configs, key_duration, key_combo_seps
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
			combo.append(k)
			continue
		if combo:
			press_keys(combo)
			combo = []
		else:
			press_keys([k])
		time.sleep(key_duration)
	if open_combo or combo:
		return make_response(jsonify(message="Error: Unable to Process 'keys' in Config '%s', Macro '%s'" % (config_name, name)), 500)
	return jsonify(message='Success')

# listen on all interfaces and allow multiple werkzeug threads.
if __name__ == '__main__':
	app.run(host='0.0.0.0',port=server_port,threaded=True)
