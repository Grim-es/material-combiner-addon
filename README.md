material-combiner-addon
===========
#### An addon for Blender that allows to get lower draw calls in game engines by combining textures without quality loss and avoiding the problem of uv larger 0-1 bounds.

#### If you like an addon you can support my work on Patreon.
[<img src="http://webgrimes.com/buymeacoffee.svg" height="40px">](https://www.buymeacoffee.com/shotariya)
[<img src="http://webgrimes.com/patreon.png" height="40px">](https://www.patreon.com/join/shotariya?)

## FEATURES
* Combining multiple materials. (allow to apply diffuse colors and choose each image and atlas sizes)
* Multicombining. (add layers for each image which are combine into different atlases, allow to generate Normal map, Specular map, etc atlases) (Currently Disabled | Supported in version 2.0.3.3)
* Packing UV into the selected scale bounds by splitting mesh faces, compatible with rigged models. (Currently Disabled | Supported in version 1.1.6.3)

## INSTALLATION
1. Download an addon: [Material-combiner](https://github.com/Grim-es/material-combiner-addon/archive/master.zip)
1. Go to File > User Preferences > Addons
1. Click on Install Add-on from File
1. Choose material-combiner-addon-master.zip archive
1. Activate Material Combiner

## KNOWN ISSUES

### After clicking "Save atlas to.." the materials are simply merged or the atlas image does not have all the textures
- Textures are packaged in a .blend file. You need to save the .blend somewhere and click File > External data > Unpack All Into Files (to any directory of your choice).
- Your version of Blender is not in English, in this case the nodes will be named differently, their names are strictly written in the script. You need to manually rename the nodes to their own names, or switch the blender version to English and regenerate the nodes by re-importing the model.
- You are using an unsupported shader (Surface property of material). You can view the file [utils/materials.py](https://github.com/Grim-es/material-combiner-addon/blob/master/utils/materials.py) to see what shaders are supported or what node names should be.

### Pillow installation process is repeated
- Make sure the VPN is not currently active.

- **Windows** | Make sure Blender isn't installed from the Windows Store because it's not supported. If you want to install Pillow manually, go to the blender installation folder, navigate to the folder with the ***blender version name\python\bin*** and copy this path. Press ***Win+R*** on your keyboard and type ***cmd.exe***, press Enter. After that, write this commands to the Windows console:
    ```
    set PythonPath="Your\Copied\Path\To\Python\bin\Folder"

    %PythonPath%\python.exe -m pip install Pillow --user --upgrade
    ```
    Make sure to replace ***Your\Copied\Path\To\Python\bin\Folder*** with your copied path.

- **MacOS** | Open a Mac Terminal console and write these commands:
    ```
    /Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "__import__('ensurepip')._bootstrap()" 

    /Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "__import__('pip._internal')._internal.main(['install', '-U', 'pip', 'setuptools', 'wheel'])"

    /Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "__import__('pip._internal')._internal.main(['install', 'Pillow'])"
    ```
  if you installed Blender in a different path, change the first part of each command to the correct path.

### No module named 'material-combiner-addon-2'
You have installed the Source code from the Releases, instead install from master branch [Material-combiner](https://github.com/Grim-es/material-combiner-addon/archive/master.zip). But first remove the old installation folder. Default location: C:\Users\\***YourUserName***\AppData\Roaming\Blender Foundation\Blender\\***BlenderVersion***\scripts\addons.

## BUGS / SUGGESTIONS
If you have found a bug or have suggestions to improve the tool, you can contact me on Discord: [shotariya#4269](https://discordapp.com/users/275608234595713024)
