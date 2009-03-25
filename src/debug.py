#!/usr/bin/python2.5

import sys
import os

if len(sys.argv) != 2:
    print "Usage: debug.py <module>"
    sys.exit(2)

os.environ["VIGICONF_MAINCONF"] = os.path.join(
                                    os.path.abspath(os.path.dirname(__file__)),
                                    "confmgr-test.conf")

module = sys.argv[1]

if module == "conf":
    import conf
    import pprint
    conf.loadConf()
    print "hostsConf="
    pprint.pprint(conf.hostsConf)
    print "groupsHierarchy="
    pprint.pprint(conf.groupsHierarchy)
    print "dependencies="
    pprint.pprint(conf.dependencies)
    print "dynamic groups="
    pprint.pprint(conf.dynamicGroups)

elif module == "generator":
    import conf
    import generator
    conf.loadConf()
    _gendir = os.path.join(conf.libDir, "deploy")
    os.system("rm -rf %s/*" % _gendir)
    if 0:
        import hotshot, hotshot.stats
        _prof = hotshot.Profile("/tmp/generator.prof")
        _prof.runcall(generate, _gendir)
        _prof.close()
        _stats = hotshot.stats.load("/tmp/generator.prof")
        _stats.strip_dirs()
        _stats.sort_stats('time', 'calls')
        _stats.print_stats(20)
    else:
        if not generator.generate(_gendir):
            sys.exit(1)
