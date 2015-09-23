CONFIGS := git-config.yaml svn-config.yaml hg-config.yaml

#-----------------------------------------------------------------------------
define RENDER
from jinja2 import Template, Environment, FileSystemLoader

loader = FileSystemLoader('./')
env = Environment(trim_blocks=True, lstrip_blocks=True, loader=loader)
tmpl = env.from_string(open('$<').read())

print(tmpl.render())
endef
#-----------------------------------------------------------------------------

export RENDER
%.yaml: %.yaml.jinja2 shared-config.jinja2
	python -c "$$RENDER" > $@

clean:
	-rm -f $(CONFIGS)

.DEFAULT_GOAL := all
.PHONY: all
all: $(CONFIGS)
