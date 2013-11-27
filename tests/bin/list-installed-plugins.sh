#!/bin/bash

java -jar jenkins-cli.jar -s "http://localhost:60888" groovy = <<EOF
for(plugin in hudson.model.Hudson.instance.pluginManager.plugins) {
    println plugin.shortName;
}

for(i in hudson.PluginManager.getMethods()) {
    println i;
}

hudson.PluginManager.doUpdateSources();
EOF
