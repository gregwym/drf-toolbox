JSON Renderer
=============

DRF Toolbox ships with a custom JSON renderer, available within the
``drf_toolbox.renderers.json`` module.

Currently, the only thing this offers is serialization of ``date`` or
``datetime`` objects to UNIX timestamps.

To enable this, use these classes instead of the stock Django REST Framework
versions in your ``DEFAULT_RENDERER_CLASSES`` setting.
