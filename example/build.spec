from kivy.tools.packaging.pyinstaller_hooks import install_hooks
import os
install_hooks(globals())
# -*- mode: python -*-
a = Analysis(['\\pyRESTvk\\example\\main.py'],
             pathex=['\\build'],
             hiddenimports=[],
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='switch_panel.exe',
          debug=False,
          strip=None,
          upx=True,
          console=False )
