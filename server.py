# pyRESTvk/server.py
# Dan Allongo (daniel.s.allongo@gmail.com)

# Provides a JSON-only RESTful interface for execution of virtual keystroke macros.
# Using basic HTTP authentication with no WWW authentication challenge as browsers
# are not the target client. Valid key codes are loaded from external file.

from flask import Flask, url_for, redirect, abort, request, jsonify, make_response, send_file
from werkzeug.exceptions import default_exceptions, HTTPException
import os
import random
import datetime
import socket
import json
import win32api
import time
import sys
from distutils.dir_util import mkpath
from distutils.version import LooseVersion
import StringIO
from collections import namedtuple
import logging, logging.handlers

# server changes that affect endpoint functionality or break test script should increment api version.
app_version = '0.7.2-beta'
api_version = '2.0'

# generates new auth key if needed.
def generate_auth_key():
	return '-'.join([str(int(random.random()*1000)) for i in xrange(4)])

# validates profile schema.
def validate_profile(k, p):
	global key_codes, key_combo_seps
	http_reserved = "!*'();:@&=+$,/?#[]"
	for c in http_reserved:
		if c in k:
			return False, "Invalid Character: '{0}' in Profile 'name' {1}'".format(c, k)
	if not p.keys():
		return False, "Profile Empty: No Macros for Profile '{0}'".format(k)
	for n, m in p.iteritems():
		for c in http_reserved:
			if c in n:
				return False, "Invalid Character: '{0}' in Macro 'name' '{1}' for Profile '{2}'".format(c, n, k)
		if not m:
			return False, "Macro Empty: No Keys in Macro '{0}' for Profile '{1}'".format(n, k)
		combo = []
		open_combo = False
		for key in m.split():
			if key not in key_codes and key not in [key_combo_seps['open'], key_combo_seps['close']]:
				return False, "Invalid Key Code: '{0}' in Macro '{1}' for Profile '{2}'".format(key, n, k)
			if key == key_combo_seps['open']:
				if open_combo:
					return False, "Invalid Combo: Nested '{0}' in Macro '{1}' for Profile '{2}'".format(key_combo_seps['open'], n, k)
				open_combo = True
				continue
			if key == key_combo_seps['close']:
				if not open_combo:
					return False, "Invalid Combo: '{0}' Before '{1}' in Macro '{2}' for Profile '{3}'".format(key_combo_seps['close'], key_combo_seps['open'], n, k)
				open_combo = False
			if open_combo:
				combo.append(key_codes[key])
				continue
			if combo:
				combo = []
		if open_combo or combo:
			return False, "Invalid Combo: '{0}' Without '{1}' in Macro '{2}' for Profile '{3}'".format(key_combo_seps['open'], key_combo_seps['close'], n, k)
	return True, "OK"

# writes validated profiles to file.
def write_profiles(profiles, profiles_db, json_args):
	global logger_name
	to_disk = {}
	for k, p in profiles.iteritems():
		validated, msg = validate_profile(k, p)
		if not validated:
			logging.getLogger(logger_name).warning("Discarding Profile: {0}".format(msg))
			continue
		to_disk[k] = p
	mkpath(os.path.dirname(profiles_db))
	with open(profiles_db,'w') as f:
		json.dump(to_disk, f, **json_args)
	return

# reads validated profiles from file.
def read_profiles(profiles_db):
	global logger_name
	profiles = {}
	if os.path.isfile(profiles_db) and os.path.getsize(profiles_db) > 0:
		with open(profiles_db) as f:
			from_disk = json.load(f)
		for k, p in from_disk.iteritems():
			validated, msg = validate_profile(k, p)
			if not validated:
				logging.getLogger(logger_name).warning("Discarding Profile: {0}".format(msg))
				continue
			profiles[k] = p
	return profiles

# reads key codes from file.
def read_key_codes(codes_file):
	global logger_name
	if not os.path.isfile(codes_file) or not os.path.getsize(codes_file) > 0:
		logging.getLogger(logger_name).error("Error: File Not Found: '{0}'".format(codes_file))
		sys.exit(1)
	with open(codes_file) as f:
		return json.load(f)

# simulate key presses for given key codes.
def press_keys(duration, keys=[]):
	global KEYEVENTF
	for k in keys:
		flags = KEYEVENTF.SCANCODE | KEYEVENTF.KEYDOWN
		if k['e0'] == 1:
			flags |= KEYEVENTF.EXTENDEDKEY
		win32api.keybd_event(0, k['sc'], flags, 0)
	time.sleep(duration)
	for k in keys:
		flags = KEYEVENTF.SCANCODE | KEYEVENTF.KEYUP
		if k['e0'] == 1:
			flags |= KEYEVENTF.EXTENDEDKEY
		win32api.keybd_event(0, k['sc'], flags, 0)
	return

# checks for HTTP auth info in request.
def authorized():
	global auth_key
	if not request.authorization or request.authorization.password != auth_key:
		return False
	return True


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def make_json_error(ex):
	response = jsonify(message=str(ex))
	response.status_code = (ex.code
		if isinstance(ex, HTTPException)
		else 500)
	return response

for code in default_exceptions.iterkeys():
	app.error_handler_spec[None][code] = make_json_error

# root is readable to all and gives server status with clients and profiles summary.
@app.route('/')
def server_status():
	global status, profiles, clients, key_codes
	status['clients'] = {'url':url_for('client_list', _external=True), 'count':len(clients)}
	status['profiles'] = {'url':url_for('register_profile', _external=True), 'count':len(profiles)}
	status['key_codes'] = {'url':url_for('select_key_codes', _external=True), 'count':len(key_codes)}
	return jsonify(status)

# adds authenticated client to list. not strictly necessary to perform authenticated tasks.
@app.route('/auth')
def register_client():
	global clients
	if not authorized():
		abort(401)
	name = request.authorization.username
	if name not in clients:
		clients[name] = {'address':request.remote_addr, 'since':datetime.datetime.now()}
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
	return jsonify(clients)

# list all profiles this server knows about and allow adding new ones.
@app.route('/profiles', methods=['GET','POST'])
def register_profile():
	global profiles, profiles_db, json_args
	if request.method == 'GET':
		# client requested to download a copy of the entire server cache using /profiles?send_file=true
		if request.args.get('send_file', '').lower() == 'true':
			return send_file(profiles_db, as_attachment=True, attachment_filename=os.path.basename(profiles_db))
		out = {}
		for k, p in profiles.iteritems():
			out[k] = {'url':url_for('select_profile', name=k, _external=True), 'macros':len(p)}
		return jsonify(out)
	if not authorized():
		abort(401)
	# allow clients to send profile data as file
	if request.files:
		profile = json.loads(request.files[request.files.keys()[0]].read())
	else:
		profile = request.json
	k, p = next(profile.iteritems())
	validated, msg = validate_profile(k, p)
	if not validated:
		return make_response(jsonify(message=msg), 400)
	# allow clients to validate profile data without altering server cache using /profiles?validate_only=true
	if request.args.get('validate_only', '').lower() == 'true':
		return jsonify(message=msg)
	if k in profiles:
		return make_response(jsonify(message="Duplicate Entry: Profile '{0}' Exists".format(k)), 409)
	profiles[k] = p
	write_profiles(profiles, profiles_db, json_args)
	return make_response(jsonify(url=url_for('select_profile', name=k, _external=True)), 201, {'Location':url_for('select_profile', name=k)})

# retrieve profile in format that is acceptable to post back as new after delete. allow put for updates.
@app.route('/profiles/<name>', methods=['GET','PUT','DELETE'])
def select_profile(name):
	global profiles, profiles_db, json_args
	if name not in profiles:
		abort(404)
	if request.method == 'GET':
		p = {name:profiles[name]}
		# client requested to download a copy of the profile as file using /profiles/<name>?send_file=true
		if request.args.get('send_file', '').lower() == 'true':
			return send_file(StringIO.StringIO(json.dumps(p, **json_args)), as_attachment=True, attachment_filename=name + '.json')
		return jsonify(p)
	if not authorized():
		abort(401)
	if request.method == 'DELETE':
		profiles.pop(name, None)
		write_profiles(profiles, profiles_db, json_args)
		return make_response('', 204)
	# allow clients to send profile data as file
	if request.files:
		x = json.loads(request.files[request.files.keys()[0]].read())
	else:
		x = request.json
	k, p = next(x.iteritems())
	validated, msg = validate_profile(k, p)
	if not validated:
		return make_response(jsonify(message=msg), 400)
	if k != name and k in profiles:
		return make_response(jsonify(message="Duplicate Entry: Profile '{0}' Exists".format(k)), 409)
	profiles.pop(name, None)
	profiles[k] = p
	write_profiles(profiles, profiles_db, json_args)
	if k != name:
		return make_response(jsonify(url=url_for('select_profile', name=k, _external=True)), 201, {'Location':url_for('select_profile', name=k)})
	return make_response('', 204)

# authenticated execution of macro key sequences. minimal validation since it should have passed validation twice by now.
@app.route('/profiles/<name>/<macro>')
def select_macro(name, macro):
	global profiles, key_codes, key_duration, key_combo_seps
	if not authorized():
		abort(401)
	if name not in profiles or macro not in profiles[name]:
		abort(404)
	m = profiles[name][macro]
	combo = []
	open_combo = False
	for k in m.split():
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

# list all valid key codes.
@app.route('/key_codes')
def select_key_codes():
	global key_codes, json_args
	# client requested to download a copy of the key codes file using /key_codes?send_file=true
	if request.args.get('send_file', '').lower() == 'true':
		return send_file(StringIO.StringIO(json.dumps(key_codes, **json_args)), as_attachment=True, attachment_filename='key_codes.json')
	return jsonify(key_codes)


def setup():
	global app_version, api_version
	global status, clients, auth_key
	global key_codes, key_duration, key_combo_seps
	global profiles, profiles_db, json_args
	global KEYEVENTF
	global logger_name

	defaults = {
		'ip':'0.0.0.0',
		'port':5000,
		'auth_key':generate_auth_key(),
		'profiles_db':'profiles.json',
		'key_duration':0.025,
		'key_combo_seps':{'open':'[', 'close':']'}
	}

	json_args = {'indent':4, 'separators':(',',':'), 'sort_keys':True}

	# create log, set to rotate at 1MB
	logger_name = 'werkzeug'
	log_file = os.path.abspath(os.path.expandvars('$APPDATA/pyRESTvk-server/server.log'))
	mkpath(os.path.dirname(log_file))
	h = logging.handlers.RotatingFileHandler(filename=log_file, maxBytes=1024*1024, backupCount=9)
	h.setLevel(logging.INFO)
	l = logging.getLogger(logger_name)
	l.addHandler(h)
	l.setLevel(logging.INFO)
	l.info('-' * 25 + ' ' + str(datetime.datetime.now()) + ' ' + '-' * 25)

	# search for settings in %APPDATA% first
	settings_file = os.path.abspath(os.path.expandvars('$APPDATA/pyRESTvk-server/settings.json'))
	# commandline args relative to current working directory
	if len(sys.argv) == 2:
		settings_file = os.path.abspath(os.path.join(os.getcwd(), os.path.expandvars(sys.argv[1])))

	# write defaults to disk if no file
	mkpath(os.path.dirname(settings_file))
	if not os.path.isfile(settings_file) or not os.path.getsize(settings_file) > 0:
		l.warning("File Not Found: Creating '{0}'".format(settings_file))
		with open(settings_file, 'w') as f:
			json.dump(defaults, f, **json_args)
	
	# read settings from file
	with open(settings_file) as f:
		settings = json.load(f)

	# check all needed settings keys exist, add missing settings
	for k in defaults:
		if k not in settings or not settings[k]:
			l.warning("Key Not Found: Adding '{0}' to '{1}'".format(k, settings_file))
			settings[k] = defaults[k]
			with open(settings_file, 'w') as f:
				json.dump(settings, f, **json_args)

	# resolve profile file path relative to settings file
	settings['profiles_db'] = os.path.abspath(os.path.join(os.path.dirname(settings_file), os.path.expandvars(settings['profiles_db'])))

	# server status.
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
		}
	}

	clients = {}

	auth_key = settings['auth_key']
	# flags used by keybd_event
	KEYEVENTF = namedtuple('KEYBDINPUT_FLAGS', 'KEYDOWN, EXTENDEDKEY, KEYUP, UNICODE, SCANCODE')(*[int(2**x) for x in xrange(-1,4)])
	key_codes = read_key_codes(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'key_codes.json')))
	key_duration = settings['key_duration']
	key_combo_seps = settings['key_combo_seps']

	# key_.* globals must be populated before profiles can be loaded
	profiles_db = settings['profiles_db']
	profiles = read_profiles(profiles_db)

	return {'host':settings['ip'], 'port':settings['port']}


if __name__ == '__main__':
	kwargs = setup()
	app.run(threaded=True, **kwargs)
