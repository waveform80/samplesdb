# vim: set noet sw=4 ts=4:

# External utilities
PYTHON=python
PYFLAGS=
DEST_DIR=/
PROJECT=rastools

# Calculate the base names of the distribution, the location of all source,
# documentation and executable script files
NAME:=$(shell $(PYTHON) $(PYFLAGS) setup.py --name)
VER:=$(shell $(PYTHON) $(PYFLAGS) setup.py --version)
PYVER:=$(shell $(PYTHON) $(PYFLAGS) -c "import sys; print 'py%d.%d' % sys.version_info[:2]")
PY_SOURCES:=$(shell \
	$(PYTHON) $(PYFLAGS) setup.py egg_info >/dev/null 2>&1 && \
	cat $(NAME).egg-info/SOURCES.txt)
DOC_SOURCES:=$(wildcard docs/*.rst)

# Calculate the name of all outputs
DIST_EGG=dist/$(NAME)-$(VER)-$(PYVER).egg

# Default target
all:
	@echo "make install - Install on local system"
	@echo "make source - Create source package"
	@echo "make buildegg - Generate a PyPI egg package"
	@echo "make clean - Get rid of scratch and byte files"

install:
	$(PYTHON) $(PYFLAGS) setup.py install --root $(DEST_DIR) $(COMPILE)

source: $(DIST_TAR)

buildegg: $(DIST_EGG)

dist: $(DIST_EGG)

develop: tags
	$(PYTHON) $(PYFLAGS) setup.py develop

test:
	$(PYTHON) $(PYFLAGS) setup.py nosetests

clean:
	$(PYTHON) $(PYFLAGS) setup.py clean
	rm -fr build/ dist/ $(NAME).egg-info/ tags distribute-*.egg
	find $(CURDIR) -name "*.pyc" -delete

tags: $(PY_SOURCES)
	ctags -R --exclude="build/*" --languages="Python"

$(DIST_EGG): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py bdist_egg $(COMPILE)

