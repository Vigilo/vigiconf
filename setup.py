#!/usr/bin/env python
# vim: set fileencoding=utf-8 sw=4 ts=4 et :
# Copyright (C) 2006-2020 CS GROUP - France
# License: GNU GPL v2 <http://www.gnu.org/licenses/gpl-2.0.html>

import os, sys
from platform import python_version_tuple
from glob import glob
from setuptools import setup, find_packages

cmdclass = {}
try:
    from vigilo.common.commands import install_data
except ImportError:
    pass
else:
    cmdclass['install_data'] = install_data

os.environ.setdefault('SYSCONFDIR', '/etc')
os.environ.setdefault('LOCALSTATEDIR', '/var')

install_requires = [
    # order is important
    "setuptools",
    "lxml",
    "vigilo-common",
    "vigilo-models",
    "networkx",
    "netifaces",
]

tests_require = [
    'coverage',
    'nose',
    'pylint',
    'mock',
]

def install_i18n(i18ndir, destdir):
    data_files = []
    langs = []
    for f in os.listdir(i18ndir):
        if os.path.isdir(os.path.join(i18ndir, f)) and not f.startswith("."):
            langs.append(f)
    for lang in langs:
        for f in os.listdir(os.path.join(i18ndir, lang, "LC_MESSAGES")):
            if f.endswith(".mo"):
                data_files.append(
                        (os.path.join(destdir, lang, "LC_MESSAGES"),
                         [os.path.join(i18ndir, lang, "LC_MESSAGES", f)])
                )
    return data_files

def find_data_files(basedir, srcdir):
    data_files = []
    for root, dirs, files in os.walk(srcdir):
        if '.svn' in dirs:
            dirs.remove('.svn')  # don't visit SCM directories
        if not files:
            continue
        subdir = root.replace(srcdir, "")
        if subdir.startswith("/"):
            subdir = subdir[1:]
        data_files.append( (os.path.join(basedir, subdir),
                           [os.path.join(root, name) for name in files
                            if not name.endswith( ('.pyc', '.pyo') )]) )
    return data_files

def get_data_files():
    example = os.path.join("@SYSCONFDIR@", "vigilo", "vigiconf", "conf.d.example/")
    files = find_data_files(example, "src/vigilo/vigiconf/conf.d")
    # filter those out
    files = [f for f in files if f[0] != example]
    # others
    files.append( (os.path.join("@SYSCONFDIR@", "vigilo", "vigiconf"),
        ["settings.ini.in", "src/vigilo/vigiconf/conf.d/README.post-install"]) )
    files.append( (os.path.join("@SYSCONFDIR@", "vigilo", "vigiconf", "conf.d"), []) )
    files.append( (os.path.join("@SYSCONFDIR@", "vigilo", "vigiconf", "conf.d.example", "filetemplates", "nagios"), []) )
    files.append( (os.path.join("@SYSCONFDIR@", "vigilo", "vigiconf", "plugins"), []) )
    for d in ("deploy", "revisions", "tmp"):
        files.append( (os.path.join("@LOCALSTATEDIR@", "lib", "vigilo", "vigiconf", d), []) )
    return files


setup(name='vigilo-vigiconf',
        version='5.2.0',
        author='Vigilo Team',
        author_email='contact.vigilo@csgroup.eu',
        url='https://www.vigilo-nms.com/',
        license='http://www.gnu.org/licenses/gpl-2.0.html',
        description="Configuration manager for the supervision system",
        long_description="This program generates and pushes the "
                         "configuration for the applications used in Vigilo.",
        zip_safe=False,
        install_requires=install_requires,
        namespace_packages=['vigilo'],
        packages=find_packages("src"),
        message_extractors={
            'src': [
                ('**.py', 'python', None),
            ],
        },
        extras_require={
            'tests': tests_require,
        },
        entry_points={
            'console_scripts': [
                'vigiconf = vigilo.vigiconf.commandline:main',
                'vigiconf-migrate = vigilo.vigiconf.migrate_tests_5_0_0:main',
                ],
            'vigilo.vigiconf.lib.testdumpers': [
                'text = vigilo.vigiconf.lib.testdumpers.text:dump',
                'json = vigilo.vigiconf.lib.testdumpers.json:dump',
            ],
            'vigilo.vigiconf.applications': [
                'collector = vigilo.vigiconf.applications.collector:Collector',
                'connector-metro = vigilo.vigiconf.applications.connector_metro:ConnectorMetro',
                'nagios = vigilo.vigiconf.applications.nagios:Nagios',
                'perfdata = vigilo.vigiconf.applications.perfdata:PerfData',
                'vigirrd = vigilo.vigiconf.applications.vigirrd:VigiRRD',
                ],
            'vigilo.vigiconf.testlib': [
                'vigiconf-default = vigilo.vigiconf.tests',
                ],
        },
        package_dir={'': 'src'},
        include_package_data = True,
        test_suite='nose.collector',
        cmdclass=cmdclass,
        data_files=get_data_files() +
            install_i18n("i18n", os.path.join(sys.prefix, 'share', 'locale')),
        )
