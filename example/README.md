# pyRESTvk/example

This is an example client using [kivy] 1.9.0 to create a 20-button MFD-like interface. 

Edit `settings.json` and make sure that `server_url` and `auth_file` are correct. This client will connect to the pyRESTvk server and upload the `config_file` specified in `settings.json` if it does not exist or update the server's copy if it does exist but doesn't match the local copy. Button labels, text color, and macro assignments are loaded from the `mappings_file` specified in `settings.json`. Custom text colors can be specified in the `colors` attribute of `settings.json`. The color values are RGBA with values ranging from 0 to 1, inclusive. File paths in `settings.json` are relative to `main.py` (or `mfd.exe` if you're using the binary) unless an absolute path is specified. The number, layout, and ids of buttons can be modified in `MFD.kv` using kivy-specific language.

By default the client will look for `settings.json` in the same path as `main.py` or `mfd.exe` but this can be overridden by specifying a different file path as an argument (ie, `mfd.exe /some/other/path/settings.filename`). The client will retry requests up to 3 times and wait up to 5 seconds for a response and request server shutdown after the kivy UI window is closed.

Binaries are compiled with `pyinstaller` and require a lot of random little hacks to work with the kivy hooks. The included `mfd.spec` is a good starting point but you may have to update the requests package to 2.7.0 to get everything to compile properly with kivy 1.9.0. If you want to keep requests 2.6.0 then you'll have to make the change [outlined here]. It might be simpler to just download the kivy portable distribution and run the client that way (ie, `kivy-2.7.bat main.py`), but I've included the binary in the event that it might be useful.


[kivy]: <http://kivy.org/>
[outlined here]: <https://github.com/sigmavirus24/requests/commit/1b5bfe681b4c0a987e97ae78b2034db7b7ce3d01>
