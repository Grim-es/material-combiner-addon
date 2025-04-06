material-combiner-addon
===========

#### An add-on for Blender that helps reduce draw calls in game engines by combining textures without quality loss and avoiding issues with UV bounds larger than 0-1.

#### If you like an add-on, you can support my work on Patreon or Buy me a coffee.

[<img src="http://webgrimes.com/buymeacoffee.svg" height="40px">](https://www.buymeacoffee.com/shotariya)
[<img src="http://webgrimes.com/patreon.png" height="40px">](https://www.patreon.com/join/shotariya?)

## FEATURES

* **Combining Multiple Materials**: Allows you to mix diffuse colors with textures, and specify both the size of the
  resulting atlas and the size of each individual texture.
* **Multi-combining**: Adds image-layers for each material, which are combined into different atlases. This feature
  supports the generation of Normal maps, Specular maps, and other atlases. (Not implemented in newer versions |
  Supported in version 2.0.3.3)
* **UV Packing**: Packs UVs into the selected scale bounds by splitting mesh faces, and is compatible with rigged
  models. (Not implemented in newer versions | Supported in version 1.1.6.3)

## INSTALLATION

1. Download an add-on: [Material-combiner](https://github.com/Grim-es/material-combiner-addon/archive/master.zip).
2. Go to File > User Preferences > Add-ons.
3. Click on Install Add-on from File.
4. Choose `material-combiner-addon-master.zip` archive.
5. Activate Material Combiner.

## HOW OT USE

1. Once the add-on is installed and activated, go to the 3D Viewport in Blender.
2. On the right side of the 3D View (Scene) window, open the side panel by pressing the `N` key on your keyboard.
3. In the side panel, locate the **MatCombiner** section.
4. You will see a list of objects and their corresponding materials:
    - For each material, you can choose to include or exclude it from the atlasing process by checking or unchecking the
      box next to it.
    - Each object has a **Select All** or **Deselect All** button, allowing you to quickly enable or disable atlasing
      for all of its materials.
5. You can also set the size for materials that do not have an image. The default size is set to 32 pixels.
6. Once you have made your selections, click the `Save atlas to..` button to start the atlasing process.
7. If the materials are not merged properly or the atlas image does not contain all the textures, please refer to the
   section:
   [After clicking "Save atlas to.." the materials are simply merged or the atlas image does not have all the textures](https://github.com/Grim-es/material-combiner-addon/tree/master?tab=readme-ov-file#after-clicking-save-atlas-to-the-materials-are-simply-merged-or-the-atlas-image-does-not-have-all-the-textures).

## KNOWN ISSUES

### After clicking "Save atlas to.." the materials are simply merged or the atlas image does not have all the textures

- Textures are packaged in a .blend file. Save the .blend file to a location of your choice, then go to File > External
  Data > Unpack Resources / Unpack All Into Files to extract the textures.
- Your version of Blender is not in English, in this case the nodes will be named differently, their names are strictly
  written in the script. You need to manually rename the nodes to their own names, or switch the blender version to
  English and regenerate the nodes by re-importing the model.
- You are using an unsupported shader (Surface property of material) or incorrect node names. You can check the
  file [utils/materials.py](https://github.com/Grim-es/material-combiner-addon/blob/781d70fbbc2ddfa6813c61255c0cb6c501307a3e/utils/materials.py#L19-L40)
  to see which shaders are supported and what node names should be used. For more details, refer to the relevant
  discussion on GitHub: [Issue #98](https://github.com/Grim-es/material-combiner-addon/issues/98).
- If objects already share the same material with the same texture, they will not be atlased because they are already
  optimized, and the existing image will be used instead.

### Pillow installation process is repeated

- Make sure the VPN is not currently active.

- **Windows** | Verify that Blender is not installed from the Windows Store, as it may not function correctly. To
  install Pillow manually, navigate to your Blender installation folder, then to the folder with the
  ***blender version name\python\bin*** and copy this path. Press ***Win+R*** on your keyboard, type ***cmd.exe***, and
  press Enter. In the Windows console, enter the following commands:
    ```powershell
    set PythonPath="Your\Copied\Path\To\Python\bin\Folder"

    %PythonPath%\python.exe -m pip install Pillow --user --upgrade
    ```
  Replace ***Your\Copied\Path\To\Python\bin\Folder*** with the path you copied.

- **MacOS** | Open a Terminal console and execute the following commands:
    ```bash
    /Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "__import__('ensurepip')._bootstrap()" 

    /Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "__import__('pip._internal')._internal.main(['install', '-U', 'pip', 'setuptools', 'wheel'])"

    /Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "__import__('pip._internal')._internal.main(['install', 'Pillow'])"
    ```
  If you installed Blender in a different location, adjust the path at the beginning of each command accordingly.

### No module named 'material-combiner-addon-2'

You have installed the source code from the Releases. Instead, install from the master
branch [Material-combiner](https://github.com/Grim-es/material-combiner-addon/archive/master.zip). Before doing so,
remove the old installation folder. The default locations are:

* **Windows**
    ```console
    C:\Users\YourUserName\AppData\Roaming\Blender Foundation\Blender\BlenderVersion\scripts\addons
    ```
  Replace ***YourUserName*** with your actual username and ***BlenderVersion*** with the version of Blender you are
  using.
* **MacOS**
    ```console
    /Users/YourUserName/Library/Application Support/Blender/BlenderVersion/scripts/addons
    ```
  Replace ***YourUserName*** with your actual username and ***BlenderVersion*** with the version of Blender you are
  using.

## BUGS / SUGGESTIONS

If you have found a bug or have suggestions to improve the tool, you can contact me on
Discord: [@shotariya](https://discordapp.com/users/275608234595713024)
