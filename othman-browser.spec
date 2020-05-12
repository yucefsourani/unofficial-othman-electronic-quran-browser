# -*- mode: python ; coding: utf-8 -*-

block_cipher = None
data_files = [("COPYING","."),("LICENSE-ar.txt","."),("LICENSE-en","."),
              ("othman.ico","."),("Othman-128.png","."),("README","."),("README-ar.txt","."),("locale","./locale")]
binary_files = [("icons","./icons"),("othman","./othman"),("othman-data","./othman-data"),("po","./po"),("amiri_font","./amiri_font")]
a = Analysis(['othman-browser'],
             pathex=['.'],
             binaries=binary_files,
             datas=data_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='othman-browser',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,icon='othman.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='othman-browser')
