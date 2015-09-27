# pyRESTvk/example

This is an example client using [kivy] 1.9.0 to create a 20-button MFD-like interface. Edit `settings.json` and make sure that `server_url` and `auth_file` are correct. This client will connect to the pyRESTvk server and upload the `config_file` specified in `settings.json` if it does not exist or update the server's copy if it does exist but doesn't match the local copy. Button labels and macro assignments are loaded from the `mappings_file` specified in `settings.json`. The client will request server shutdown after the kivy UI window is closed. The client will retry requests up to 3 times and wait up to 5 seconds for a response. File paths in `settings.json` are relative to `main.py` (or `mfd.exe` if you're using the binary).

Binaries are compiled with `pyinstaller` and require a lot of random little hacks to work with the kivy hooks. It might be simpler to just download the kivy portable distribution and run the client that way, but I've included the binary in the event that it might be useful.


[kivy]: <http://kivy.org/>
