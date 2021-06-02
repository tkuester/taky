import logging
from pkg_resources import iter_entry_points

from taky.config import app_config as config
from . import gps_noise

discovered_plugins = {gps_noise.plugin.name: gps_noise.plugin}


def load_plugins(router):
    ret = []

    lgr = logging.getLogger("PluginRegistry")
    plugins_to_load = config.get("cot_server", "plugins")
    if plugins_to_load is None or plugins_to_load == "":
        plugins_to_load = []
    else:
        plugins_to_load = plugins_to_load.split("\n")

    lgr.info("Requested to load plugins: %s", plugins_to_load)

    for plugin in iter_entry_points("taky.cot.router_plugins"):
        if plugin.module_name not in plugins_to_load:
            lgr.debug("Skipping %s", plugin.module_name)
            continue

        lgr.debug("Loading requested plugin: %s", plugin.module_name)
        try:
            plugin_mod = plugin.load()
            if plugin_mod.plugin.name in discovered_plugins:
                lgr.error(
                    "%s wants to override %s", plugin.module_name, plugin_mod.name
                )
                continue

            discovered_plugins[plugin_mod.plugin.name] = plugin_mod.plugin
        except Exception as exc:
            lgr.error("Unable to load: %s", plugin.module_name, exc_info=exc)
            continue

    for plugin in plugins_to_load:
        lgr.info("Building plugin: %s", plugin)
        ret.append(discovered_plugins[plugin](router))

    return ret
