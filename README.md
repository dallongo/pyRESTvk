# pyRESTvk

pyRESTvk is a JSON-only Python web server for Windows that provides a RESTful interface for clients to simulate pressing buttons on the keyboard of the server. It stores keyboard macros in JSON configuration objects and executes those macros when an authenticated client issues GET on the named endpoint for that macro.

pyRESTvk is built on Python 2.7 using [Flask] for the web service and [pywin32] to issue the key strokes. A helpful testing script is included which uses the [requests] module as the client.

### Disclaimer and Caveats

As with anything that controls/emulates input devices, running this service can be considered a security hazard. 

This is a lightweight service with only minimal validation checks and error handling. It assumes that the client will work with JSON and ignores Accept headers for HTML or XML. 

It's meant to be run on a local network without access to the Internet. I've only tested the service on Windows 7 and Windows 8.1 as these are the machines I had in mind for this service. I don't know if it works on Windows XP or Windows 10. After the client has finished making all its requests, it should call for the service to shutdown otherwise the service will listen indefinitely.

Macros are not checked for correct syntax when they are executed since the original purpose of the service is to simulate input for a low-latency game program. The macros are validated when the configs are read from disk, written to disk, uploaded from the client, or updated. By the time a macro is executed it should have passed validation at least twice.

There is no exception handling for disk I/O errors and since documentation is sparse on win32api.keybd_event, there are no checks to see that the keystroke was successfully generated. The included test script will launch notepad and type a sentence, then cut and paste it, then quit notepad without saving changes. It provides a decent visual check that all pertinent keyboard macro types are functioning and will also check for proper HTTP responses for various REST calls.

The service only uses basic HTTP authentication with no form of sessionization or cookies. The clients are not required to register at the `/auth` resource but it is helpful as it populates the client list on `/clients`.

Windows does not allow sending protected commands like `[ CTRL ALT DEL ]` or `[ WIN L ]` to lock the station over the the win32api object.

Please note that `config` and `macro` names cannot include HTTP [reserved] characters.

### Releases
#### 0.5.1
Fixed `key_codes` not initialized before `read_configs` in `server.py`
Added example kivy app in `/example`

#### 0.5
Initial release

### Installation

Use pip to install these packages and their dependencies on the Windows host:

* flask
* pypiwin32

Install these packages and their dependencies on the client:

* requests

### Usage

Run `server.py` on the Windows host where the keystrokes should be executed. Copy the resulting `.auth_key` file to the client. Run the `unit-test.py` on the client and make sure to change the IP address in the script to point to the Windows host. The script will upload the test configuration in `unit-test.json` and then open the Run dialog, run notepad, type a sentence, and exit notepad. Once the client is done it will issue a shutdown command to the service on the Windows host.

The service provides the following endpoints:

* `/` - server status and summary with URLs to clients and configs resources
* `/auth` - entry point for authenticated clients to register with the server
* `/clients` - list of authenticated clients with URLs for each client resource
* `/clients/<client-name>` - get client info
* `/configs` - list of configurations with URLs for each config resource
* `/configs/<config-name>` - exports this configuration to the client
* `/configs/<config-name>/macros/<macro-name>` - executes the stored macro
* `/shutdown` - calls for service shutdown

The service uses the following files:

* `.auth_key` - the HTTP authentication password. will be auto-generated on start up if it does not exist.
* `.configs` - server's persistent cache of configs. will be created on the first config written to disk if it does not exist.
* `key_codes.json` - list of all valid keys for macros. service will fail if it does not exist.

See `unit-test.json` for a sample configuration with macros. Note that spaces are required between each token and between braces denoting button combination groups. Nesting groups is not permitted.

A typical client application using [kivy] as a frontend is available in `/example`.

### Justification

I wrote this service to familiarize myself with REST interface principles using the Flask framework. It serves as a way for me to send keyboard commands from my tablet to my desktop while playing flight simulators to manipulate the instrumentation. While many "serious" simulators already have interfaces like this (such as DCS-BIOS for the DCS series), I mostly play X-Wing Alliance and Mechwarrior 2 so I needed a more direct keyboard approach. This service might be useful for other such older games or situations where one needs to simulate keystrokes.

### Acknowledgments

The following code snippets were helpful in writing pyRESTvk:

* [Virtual keystroke example] [win32api-snippet] for the key code dictionary and usage of win32api.keydb_event
* [Shutdown The Simple Server] [shutdown-snippet] for the werkzeug shutdown endpoint
* [Specialized JSON-oriented Flask App] [json-snippet] for the JSON HTTP exception code messages
* [HTTP Basic Auth] [auth-snippet] for the HTTP authentication wrapper



[Flask]: <http://flask.pocoo.org/>
[pywin32]: <http://sourceforge.net/projects/pywin32/files/>
[requests]: <http://www.python-requests.org/>
[reserved]: <https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters>
[kivy]: <http://kivy.org/>
[win32api-snippet]: <https://gist.github.com/chriskiehl/2906125>
[shutdown-snippet]: <http://flask.pocoo.org/snippets/67/>
[json-snippet]: <http://flask.pocoo.org/snippets/83/>
[auth-snippet]: <http://flask.pocoo.org/snippets/8/>
