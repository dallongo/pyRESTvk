# pyRESTvk

pyRESTvk is a JSON-only Python web server for Windows that provides a RESTful interface for clients to simulate pressing buttons on the keyboard of the server. It stores keyboard macros in JSON objects and executes those macros when an authenticated client issues GET on the named endpoint for that macro.

pyRESTvk is built on Python 2.7 using [Flask] for the web service and [pywin32] to issue the key strokes. A helpful testing script is included in `unit-test/unit-test.py` which uses the [requests] module as the client.

### Disclaimer and Caveats

As with anything that controls/emulates input devices, running this service can be considered a security hazard. 

This is a lightweight service with only minimal validation checks and error handling. It assumes that the client will work with JSON and ignores Accept headers for HTML or XML. 

It's meant to be run on a local network without access to the Internet. I've only tested the service on Windows 7 and Windows 8.1 as these are the machines I had in mind for this service. I don't know if it works on Windows XP or Windows 10. After the client has finished making all its requests, it should call for the service to shutdown otherwise the service will listen indefinitely.

Macros are not checked for correct syntax when they are executed since the original purpose of the service is to simulate input for a low-latency game program. The macros are validated when profiles are read from disk, written to disk, uploaded from the client, or updated. By the time a macro is executed it should have passed validation at least twice.

There is no exception handling for disk I/O errors and since documentation is sparse on `win32api.keybd_event`, there are no checks to see that the keystroke was successfully generated. The included test script will launch notepad and type a sentence, then cut and paste it, then quit notepad without saving changes. It provides a decent visual check that all pertinent keyboard macro types are functioning and will also check for proper HTTP responses for various REST calls.

The service only uses basic HTTP authentication with no form of sessionization or cookies. The clients are not required to register at the `/auth` resource but it is helpful as it populates the client list on `/clients`.

Windows does not allow sending protected commands like `[ CTRL ALT DEL ]` or `[ WIN L ]` to lock the station over the the `win32api` object.

Please note that `profile` and `macro` names cannot include HTTP [reserved] characters.

### Releases
#### 0.7.1-beta

* Switch from Virtual Keyboard key designations to hardware Set 1 scan codes
* Fix `=+` key reversed
* Fix incorrect use of `KEYEVENTF_EXTENDEDKEY` and only set flag for `0xe0` prefix byte when needed
* Change all references of `config` to `profile` to avoid confusion between macro data and client/server configuration
* Increment API version to '2.0'
* Allow POST and PUT of profile with file attachment
* Allow GET with `send_file=true` to download profile(s) and key codes JSON
* Add `/key_codes` resource to support client-side profile macro validation if desired
* Simplify profile schema by removing `name` and using macro names directly as keys
* Fix path resolution for `settings.json` when specified as relative to current working path on commandline
* Store `server.py` settings and profile cache in `%APPDATA%/pyRESTvk-server` by default
* Rename `.settings` to `settings.json` to avoid problems with renaming file in Windows 8.1
* Rename `.configs` to `profiles.json` to help with `send_file` autodetecting file type by extension
* Move `.auth_key` from external file to attribute in `settings.json`
* Update `example/main.py` and `unit-test/unit-test.py` to use new API 2.0 features
* Allow specifying alternate kivy template with `kv_file` setting for `example/main.py`
* Minor tweaks to variable and class names in `example/main.py` and `unit-test/unit-test.py`

#### 0.6.0-beta

* Increment API version to '1.1'
* Add helpful error messages when config fails validation
* Add on-demand config validation with POST `/configs?validate_only=true`
* Add settings file functionality for `server.py`
* Allow specifying alternate settings file for `server.py` and `example/main.py`
* Update `example/main.py` and `unit-test/unit-test.py` to use new `validate_only` feature
* Add custom color functionality to `example/settings.json`
* Move `server.py` globals and start up tasks to `setup()`
* Fix error in `unit-test/unit-test.py` where config name was using HTTP reserved character `#`
* Add `example/mfd.spec` to allow `example/main.py` to compile with `pyinstaller`

#### 0.5.2-beta

* Testing script and json moved to `unit-test/`
* Changed `__file__` references to `sys.argv[0]` so that `server.py` will compile with `py2exe`
* Added `setup.py` to allow `server.py` to compile with `py2exe`
* Cleanup `example/main.py` and move button labels from `MFD.kv` to `mapping_file`
* Various minor cosmetic changes
* First binary release for compiled `server.py` and `example/main.py`

#### 0.5.1-beta

* Fixed `key_codes` not initialized before `read_configs` in `server.py`
* Added example kivy app in `example/`

#### 0.5.0-beta

* Initial release

### Installation

Use pip to install these packages and their dependencies on the Windows host:

* flask
* pypiwin32

Install these packages and their dependencies on the client:

* requests

### Usage

Run `server.py` on the Windows host where the keystrokes should be executed. Copy `auth_key` value from `%APPDATA%/pyRESTvk-server/settings.json` into `unit-test/unit-test.py` on the client and make sure to change the IP address in the script to point to the Windows host. The script will upload the test profile in `unit-test/unit-test.json` and then open the Run dialog, run notepad, type a sentence, and exit notepad. Once the client is done it will issue a shutdown command to the service on the Windows host.

The service provides the following endpoints:

* `/` - server status and summary with URLs to available resources
* `/auth` - entry point for authenticated clients to register with the server
* `/clients` - list of authenticated clients with URLs for each client resource
* `/profiles` - list of profiles with URLs for each profile resource
* `/profiles/<name>` - exports this profile to the client
* `/profiles/<name>/<macro>` - executes the stored macro
* `/key_codes` - list of valid key names and scan codes
* `/shutdown` - calls for service shutdown

The service uses the following files:

* `key_codes.json` - list of all valid keys for macros. service will fail if it does not exist.
* `profiles.json` - server's persistent cache of profiles. will be created on the first profile written to disk if it does not exist. stored in `%APPDATA%/pyRESTvk-server/` by default, can be overridden in `settings.json`
* `settings.json` - specifies service port, listening IP, HTTP auth password, location for profile cache, combo delimiters, and keystroke duration. will be auto-generated on start up with defaults if it does not exist in `%APPDATA%/pyRESTvk-server/`. can be overridden by specifying different file as commandline argument (ie, `python server.py /some/other/path/settings.filename`).

See `unit-test/unit-test.json` for a sample profile with macros. Note that spaces are required between each token and between brackets denoting button combination groups. Nesting groups is not permitted.

A typical client application using [kivy] as a frontend is available in `example/main.py`.

Compiled binaries are available for releases but generally these are untested and messy, use at your own risk. Running `server.exe` will start the service on the default port (5000) and start listening on all available network interfaces (0.0.0.0).

### Justification

I wrote this service to familiarize myself with REST interface principles using the Flask framework. It serves as a way for me to send keyboard commands from my tablet to my desktop while playing flight simulators to manipulate the instrumentation. While many "serious" simulators already have interfaces like this, I mostly play X-Wing Alliance and Mechwarrior 2 so I needed a more direct keyboard approach. This service might be useful for other such older games or situations where one needs to simulate keystrokes.

### Acknowledgments

The following code snippets and web pages were helpful in writing pyRESTvk:

* [keybd_event function on MSDN] [msdn-keybd_event] for the usage of keybd_event
* [KEYBDINPUT structure on MSDN] [msdn-keybdinput] for the flags to enable hardware scan codes
* [Keyboard scancodes] [kb-scancodes] for the explanation of how keyboard scan codes work and the Set 1 scan code table
* [Virtual keystroke example] [win32api-snippet] for the key code dictionary and usage of win32api.keydb_event in Python
* [Shutdown The Simple Server] [shutdown-snippet] for the werkzeug shutdown endpoint
* [Specialized JSON-oriented Flask App] [json-snippet] for the JSON HTTP exception code messages
* [HTTP Basic Auth] [auth-snippet] for the HTTP authentication wrapper

### Other/Similar Solutions

For the sake of completeness, I've compiled a non-exhaustive list of other software packages that tackle similar problems. Many of the following projects are either closed-source, platform-specific, sim-specific, or abandoned:

* [DCS-BIOS] provides a stable, documented interface for external hardware and software to interact with the clickable cockpit of a DCS aircraft
* [UltraMFCD] app for DCS that extracts aircraft diplays and presents them as normal windows which can be dragged around and resized as the user desires
* [Helios] integration package which connects your touch screen to your simulation, turning it into a fully functional glass cockpit
* [GPT] streams Falcon4 BMS cockpit displays to remote rendering computers and forwards emulated keyboard input from one computer to another
* [TouchBuddy] lightweight windows application that provides a GUI for users to interface with games via a touchscreen
* [Power-Grid] fully-customizable remote control for your PC lets you connect to, monitor, and control your PC and games directly from your smartphone 
* [LuaMacros] active development, open-source, sim-agnostic, keyboard macro scripting with network interface



[Flask]: <http://flask.pocoo.org/>
[pywin32]: <http://sourceforge.net/projects/pywin32/files/>
[requests]: <http://www.python-requests.org/>
[reserved]: <https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters>
[kivy]: <http://kivy.org/>
[win32api-snippet]: <https://gist.github.com/chriskiehl/2906125>
[shutdown-snippet]: <http://flask.pocoo.org/snippets/67/>
[json-snippet]: <http://flask.pocoo.org/snippets/83/>
[auth-snippet]: <http://flask.pocoo.org/snippets/8/>
[msdn-keybd_event]: <https://msdn.microsoft.com/en-us/library/windows/desktop/ms646304(v=vs.85).aspx>
[msdn-keybdinput]: <https://msdn.microsoft.com/en-us/library/windows/desktop/ms646271(v=vs.85).aspx>
[kb-scancodes]: <https://www.win.tue.nl/~aeb/linux/kbd/scancodes-10.html>
[DCS-BIOS]: <http://dcs-bios.a10c.de/>
[UltraMFCD]: <https://ultramfcd.com/>
[Helios]: <http://www.gadrocsworkshop.com/helios>
[GPT]: <https://github.com/GiGurra/gpt>
[TouchBuddy]: <http://touch-buddy.com/forums/index.php>
[Power-Grid]: <http://www.roccat.org/en-US/Products/Gaming-Software/Power-Grid/Home/>
[LuaMacros]: <http://www.hidmacros.eu/forum/viewtopic.php?f=10&t=241>
