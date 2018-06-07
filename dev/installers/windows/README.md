Innosetup build script for Turf
===============================

I use this to create an installer for Windows. The procedure is:

1. Create a Windows `.exe` file for Turf using [PyInstaller](http://www.pyinstaller.org) on a Windows system running the target version of Windows (e.g., Windows 10).
2. Start [Innosetup](http://www.jrsoftware.org/isinfo.php) on the Windows system.  (As of 2018-06-07, I used Innosetup version 5.5.9 running on a Windows 10 virtual machine in Parallels 13 on a macOS system.)
3. Open [turf_innosetup_script.iss](./turf_innosetup_script.iss)
4. Use the **Compile** command in the menu bar **Build** menu

The result will be placed in a folder named _Turf_ on the Windows desktop.
