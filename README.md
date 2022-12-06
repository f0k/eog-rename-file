Eye of Gnome file rename plugin
===============================

This plugin for Eye of Gnome allows to rename the currently displayed picture with F2.

Installation
------------

1. Copy `rename-file.plugin` and `rename-file.py` to your user plugin directory. The location of this directory depends on the software version, please [see the documentation](https://wiki.gnome.org/Apps/EyeOfGnome/Plugins) for details. On Ubuntu 22.04, `~/.local/share/eog/plugins` is the correct location:
   ```bash
   mkdir -p ~/.local/share/eog/plugins
   cd ~/.local/share/eog/plugins
   curl -LOO https://github.com/f0k/eog-rename-file/raw/main/rename-file.{plugin,py}
   ```
2. Start Eye of Gnome, switch to the "Plugins" tab, and enable "Rename current file". If this is not listed, go back to step 1 and try a different plugin location.

Debugging
---------

Start Eye of Gnome in a terminal with the environment option `EOGPLUGIN_DEBUG=1` to enable additional debug logs:
```bash
EOGPLUGIN_DEBUG=1 eog
```

Credits
-------

This plugin borrows heavily from Andrew Chadwick's [EOGtricks](https://github.com/achadwick/eogtricks/) "[Bracket Tags](https://github.com/achadwick/eogtricks/blob/master/eog/eogtricks-bracket-tags.py)" plugin.
