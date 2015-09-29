from kivy.tools.packaging.pyinstaller_hooks import install_hooks
import os
install_hooks(globals())
# -*- mode: python -*-
a = Analysis(['pyRESTvk\\example\\main.py'],
             pathex=['\\mfd'],
             hiddenimports=[],
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='mfd.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe, 
               Tree('pyRESTvk\\example\\'), 
               Tree([f for f in os.environ.get('KIVY_SDL2_PATH', '').split(';') if 'bin' in f][0]),
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='mfd')
