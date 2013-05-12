from importlib import import_module
import os
import re
import shutil
import argparse

import brutal


def _make_writeable(filename):
    # thx django
    import stat
    if not os.access(filename, os.W_OK):
        st = os.stat(filename)
        new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
        os.chmod(filename, new_permissions)


def spawn_command(spawn_name):
    cwd = os.getcwd()

    try:
        import_module(spawn_name)
    except ImportError:
        pass
    else:
        #conflicts with the name of an existing python module and cannot be used as a project. roll with a virtualenv.
        raise

    # check valid dir name
    if not re.search(r'^[_a-zA-Z]\w*$', spawn_name):
        raise

    base_dir = os.path.join(cwd, spawn_name)

    try:
        #print 'MKDIR {0}'.format(base_dir)
        os.mkdir(base_dir)
    except OSError as e:
        # log dat e?
        raise

    template_dir = os.path.join(brutal.__path__[0], 'spawn', 'spawn_template')

    for base, sub, files in os.walk(template_dir):
        relative = base[len(template_dir) + 1:].replace('spawn_name', spawn_name)
        if relative:
            #print 'MKDIR {0}'.format(os.path.join(base_dir, relative))
            os.mkdir(os.path.join(base_dir, relative))
        for f in files:
            if f.endswith('.pyc'):
                continue
            path_old = os.path.join(base, f)
            path_new = os.path.join(base_dir, relative, f.replace('spawn_name', spawn_name))

            #print "\nOLD: {0}".format(path_old)
            #print "NEW: {0}".format(path_new)
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read().replace('{{ spawn_name }}', spawn_name))
            fp_old.close()
            fp_new.close()

            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                raise


#TODO: get rid of config_name, rename func to start_bots
def run_command(config_name):
    import brutal.run
    from brutal.conf import config

    brutal.run.main(config)


# django general design pattern mimicked
class Overlord(object):
    def __init__(self):
        self.parser = self.build_parser()

    def build_parser(self):
        # global options
        config = argparse.ArgumentParser(add_help=False)
        config.add_argument('-c', '--config', help='specify the config module you would like to use')

        # primary parser
        parser = argparse.ArgumentParser(description='Go forth. Go forth, and DIE!', parents=[config])
        subparsers = parser.add_subparsers(help='commands', dest='command')

        # spawn
        spawn_cmd = subparsers.add_parser('spawn', help='create new bot')
        spawn_cmd.add_argument('name', action='store', help='new bot spawn name')

        # run
        subparsers.add_parser('run', help='run the bot in the cwd')

        return parser

    def execute(self, config_name=None):
        #add version
        parsed_args = self.parser.parse_args()

        command = parsed_args.command

        if command == 'run':
            config = parsed_args.config or config_name
            if config is None:
                raise
            run_command(config)

        elif command == 'spawn':
            project_name = parsed_args.name
            print 'spawning {0}'.format(project_name)

            spawn_command(project_name)


def exec_overlord(config_name=None):
    overlord = Overlord()
    overlord.execute(config_name)
