# pyRESTvk/unit-test.py
# Dan Allongo (daniel.s.allongo@gmail.com)

# Changes to the server must not break this script. Server changes that require
# breaking this client test script must advertise different API version, otherwise 
# a change in application['version'] will suffice.

import requests
import platform
import json
import time
import copy

# default host and port
server_ip = '127.0.0.1'
server_port = 5000
# testing for this API version
api_version = '1.1'
# pass hostname as username
username = platform.node()
# get password from key file
f = open('.auth_key')
password = f.readline().rstrip()
f.close()
# set correct request headers
headers = {
	'X-Requested-With':'XMLHttpRequest',
	'Accept':'application/json',
	'Content-Type':'application/json'
}
# get test configuration
f = open('unit-test.json')
test_config = json.loads(f.read())
f.close()
# copy to test rename functionality
test_config_2 = copy.deepcopy(test_config)
test_config_2['name'] += ' 2'
# copy to test syntax verification
test_config_bad = copy.deepcopy(test_config)
test_config_bad['macros'][0]['keys'] += ' ['
# assume the server is local and on default port
base_url = 'http://' + server_ip + ':' + str(server_port)
# verify server API version
r = requests.get(base_url)
assert r.status_code == 200
assert r.json()['application']['api'] == api_version
# test authenication requirement for shutdown
r = requests.get(base_url + '/shutdown')
assert r.status_code == 401
print r.json()['message']
# session will send auth and headers for subsequent requests
s = requests.Session()
s.auth=(username,password)
s.headers.update(headers)
# test authentication and client registration
r = s.get(base_url + '/auth')
assert r.status_code == 200
print r.json()['message']
# dump server status to console
r = s.get(base_url)
assert r.status_code == 200
print r.text
# verify server provided correct URL for clients resource
clients_url = r.json()['clients']['url']
r = s.get(clients_url)
assert r.status_code == 200
print r.text
# find test client in list
client = filter(lambda x: x['name'] == username, r.json()['clients'])
assert client
client = client.pop()
# verify individual client URL
r = s.get(client['url'])
assert r.status_code == 200
# get server status for configs URL
r = s.get(base_url)
assert r.status_code == 200
# verify server provided correct URL for configs resource
configs_url = r.json()['configs']['url']
r = s.get(configs_url)
assert r.status_code == 200
print r.text
# find and remove testing config if it exists
config = filter(lambda x: x['name'] == test_config['name'], r.json()['configs'])
if config:
	config = config.pop()
	r = s.delete(config['url'])
	assert r.status_code == 204
# repeat request since resource list has possibly changed
r = s.get(configs_url)
assert r.status_code == 200
# find and delete testing config if it exsists
config = filter(lambda x: x['name'] == test_config_2['name'], r.json()['configs'])
if config:
	config = config.pop()
	r = s.delete(config['url'])
	assert r.status_code == 204
# verify PUT not allowed
r = s.put(configs_url)
assert r.status_code == 405
# verify DELETE not allowed
r = s.delete(configs_url)
assert r.status_code == 405
# verify config syntax validation
r = s.post(configs_url, json=test_config_bad, params={'validate_only':'true'})
assert r.status_code == 400
print r.json()['message']
# create new test config
r = s.post(configs_url, json=test_config)
assert r.status_code == 201
print r.text
# verify server returned valid location URL header for new resource
config_url = r.headers['location']
r = s.get(config_url)
assert r.status_code == 200
print r.text
assert test_config == r.json()
# verify POST not allowed
r = s.post(config_url)
assert r.status_code == 405
# verify single combo macro functionality
r = s.get(config_url + '/macros/run-dialog')
assert r.status_code == 200
# visually verify run dialog is open
time.sleep(0.25)
# verify typing macro functionality
r = s.get(config_url + '/macros/type notepad')
assert r.status_code == 200
# visually verify notepad is open
time.sleep(0.25)
# verify combo + typing macro functionality
r = s.get(config_url + '/macros/type sentence')
assert r.status_code == 200
# visually verify output
time.sleep(0.25)
r = s.get(config_url + '/macros/cut-paste')
assert r.status_code == 200
# visually verify output
time.sleep(0.25)
# exit notepad
r = s.get(config_url + '/macros/file-menu')
assert r.status_code == 200
# attempt duplicate create
r = s.post(configs_url, json=test_config)
assert r.status_code == 409
print r.json()['message']
# update config same name
r = s.put(config_url, json=test_config)
assert r.status_code == 204
# verify config syntax validation on update
r = s.put(config_url, json=test_config_bad)
assert r.status_code == 400
print r.json()['message']
# verify rename config via update
r = s.put(config_url, json=test_config_2)
assert r.status_code == 201
config_url = r.headers['location']
# verify original resource name is now available
r = s.post(configs_url, json=test_config)
assert r.status_code == 201
# attempt rename to existing resource
r = s.put(config_url, json=test_config)
assert r.status_code == 409
print r.json()['message']
# delete test config 2
r = s.delete(config_url)
assert r.status_code == 204
# confirm not found at individual URL
r = s.get(config_url)
assert r.status_code == 404
# confirm not found in configs resource list
r = s.get(configs_url)
assert r.status_code == 200
config = filter(lambda x: x['name'] == test_config_2['name'], r.json()['configs'])
assert not config
# delete test config
r = s.get(configs_url)
assert r.status_code == 200
config = filter(lambda x: x['name'] == test_config['name'], r.json()['configs'])
assert config
config = config.pop()
r = s.delete(config['url'])
assert r.status_code == 204
# confirm not found at individual URL
r = s.get(config['url'])
assert r.status_code == 404
# confirm not found in configs resource list
r = s.get(configs_url)
assert r.status_code == 200
config = filter(lambda x: x['name'] == test_config['name'], r.json()['configs'])
assert not config
# server shutdown via authenticated endpoint
r = s.get(base_url + '/shutdown')
assert r.status_code == 200
print r.json()['message']

print 'Testing Complete: Success!'
