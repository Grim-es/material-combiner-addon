import os
from typing import cast

import bpy
import bpy.utils.previews

from ..type_annotations import SMCIcons

smc_icons = cast(SMCIcons, None)
icons_directory = os.path.dirname(__file__)


def get_icon_id(identifier: str) -> int:
    return get_icon(identifier).icon_id


def get_icon(identifier: str) -> bpy.types.ImagePreview:
    if identifier in smc_icons:
        return smc_icons[identifier]
    return smc_icons.load(identifier, os.path.join(icons_directory, '{0}.png'.format(identifier)), 'IMAGE')


def initialize_smc_icons() -> None:
    global smc_icons
    smc_icons = bpy.utils.previews.new()


def unload_smc_icons() -> None:
    bpy.utils.previews.remove(smc_icons)
