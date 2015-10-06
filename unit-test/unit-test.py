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
api_version = '2.0'
# pass hostname as username
username = platform.node()
# http password
password = ''
test_profile_file = 'unit-test.json'
with open(test_profile_file) as f:
	test_profile = json.load(f)
# copy to test rename functionality
k, p = next(test_profile.iteritems())
test_profile_2 = {k+' 2':p}
# copy to test syntax verification
test_profile_bad = copy.deepcopy(test_profile)
test_profile_bad[test_profile.keys()[0]]['alt-tab'] += ' ['
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
# session will send auth for subsequent requests
s = requests.Session()
s.auth=(username,password)
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
assert username in r.json()
# get server status for profiles URL
r = s.get(base_url)
assert r.status_code == 200
# verify server provided correct URL for profiles resource
profiles_url = r.json()['profiles']['url']
r = s.get(profiles_url)
assert r.status_code == 200
print r.text
# find and remove testing profile if it exists
profiles = r.json()
if test_profile.keys()[0] in profiles:
	r = s.delete(profiles[test_profile.keys()[0]]['url'])
	assert r.status_code == 204
# repeat request since resource list has possibly changed
r = s.get(profiles_url)
assert r.status_code == 200
# find and delete testing profile if it exsists
profiles = r.json()
if test_profile_2.keys()[0] in profiles:
	r = s.delete(profiles[test_profile_2.keys()[0]]['url'])
	assert r.status_code == 204
# verify PUT not allowed
r = s.put(profiles_url)
assert r.status_code == 405
# verify DELETE not allowed
r = s.delete(profiles_url)
assert r.status_code == 405
# verify profile syntax validation
r = s.post(profiles_url, json=test_profile_bad, params={'validate_only':'true'})
assert r.status_code == 400
print r.json()['message']
# create new test profile via uploaded file
r = s.post(profiles_url, files={test_profile_file : open(test_profile_file, 'rb')})
assert r.status_code == 201
print r.text
# verify server returned valid location URL header for new resource
profile_url = r.headers['location']
r = s.get(profile_url)
assert r.status_code == 200
print r.text
assert test_profile == r.json()
# verify POST not allowed
r = s.post(profile_url)
assert r.status_code == 405
# verify single combo macro functionality
r = s.get(profile_url + '/run-dialog')
assert r.status_code == 200
# visually verify run dialog is open
time.sleep(0.25)
# verify typing macro functionality
r = s.get(profile_url + '/type notepad')
assert r.status_code == 200
# visually verify notepad is open
time.sleep(0.25)
# verify combo + typing macro functionality
r = s.get(profile_url + '/type sentence')
assert r.status_code == 200
# visually verify output
time.sleep(0.25)
r = s.get(profile_url + '/cut-paste')
assert r.status_code == 200
# visually verify output
time.sleep(0.25)
# exit notepad
r = s.get(profile_url + '/file-menu')
assert r.status_code == 200
# attempt duplicate create
r = s.post(profiles_url, json=test_profile)
assert r.status_code == 409
print r.json()['message']
# update profile same name
r = s.put(profile_url, json=test_profile)
assert r.status_code == 204
# verify profile syntax validation on update
r = s.put(profile_url, json=test_profile_bad)
assert r.status_code == 400
print r.json()['message']
# verify rename profile via update
r = s.put(profile_url, json=test_profile_2)
assert r.status_code == 201
profile_url = r.headers['location']
# verify original resource name is now available
r = s.post(profiles_url, json=test_profile)
assert r.status_code == 201
# attempt rename to existing resource
r = s.put(profile_url, json=test_profile)
assert r.status_code == 409
print r.json()['message']
# delete test profile 2
r = s.delete(profile_url)
assert r.status_code == 204
# confirm not found at individual URL
r = s.get(profile_url)
assert r.status_code == 404
# confirm not found in profiles resource list
r = s.get(profiles_url)
assert r.status_code == 200
assert test_profile_2.keys()[0] not in r.json()
# delete test profile
r = s.get(profiles_url)
assert r.status_code == 200
profiles = r.json()
assert test_profile.keys()[0] in profiles
r = s.delete(profiles[test_profile.keys()[0]]['url'])
assert r.status_code == 204
# confirm not found at individual URL
r = s.get(profiles[test_profile.keys()[0]]['url'])
assert r.status_code == 404
# confirm not found in profiles resource list
r = s.get(profiles_url)
assert r.status_code == 200
profiles = r.json()
assert test_profile.keys()[0] not in profiles
# server shutdown via authenticated endpoint
r = s.get(base_url + '/shutdown')
assert r.status_code == 200
print r.json()['message']

print 'Testing Complete: Success!'
