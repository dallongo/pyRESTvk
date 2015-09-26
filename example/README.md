# pyRESTvk/example

This is an example client using [kivy] 1.9.0 to create a 20-button MFD-like interface. It requires a copy of `.auth_key` in the same path as `main.py`. This client will connect to the pyRESTvk server and upload the macro configuration in `key config.json` if it does not exist or update the server's copy if it does exist but doesn't match the local copy. It then loads `button mappings.json` which defines which macro to execute on pressing the specified UI button. The button labels are defined in `MFD.kv`. The client will request server shutdown after the kivy UI window is closed.




[kivy]: <http://kivy.org/>
