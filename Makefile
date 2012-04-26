SHELL  := "/bin/bash"
DOCZIP := jenkins-autojobs-doc.zip

.PHONY: zipdoc ghpages

zipdoc:
	(cd doc/ && make html)
	(cd doc/_build/html && zip -x \*.zip -r $(DOCZIP) .)
	echo `readlink -f doc/_build/html/$(DOCZIP)`

ghpages: zipdoc
	cp doc/_build/html/$(DOCZIP) /tmp/
	git co gh-pages
	rm .git/index
	git clean -fdx
	touch .nojekyll
	unzip -x /tmp/$(DOCZIP)
	git add -A ; git commit -m 'sphinxdoc update'


#vim:set ft=make ai noet sw=8 sts=8:
