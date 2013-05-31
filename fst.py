#!/usr/bin/env python

import sys, ConfigParser, os, json, shutil
from subprocess import call

#from: https://gist.github.com/zdavkeos/1098474
def walk_up(bottom):
    bottom = os.path.realpath(bottom)
 
    #get files in current dir
    try:
        names = os.listdir(bottom)
    except Exception as e:
        print e
        return
 
 
    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(bottom, name)):
            dirs.append(name)
        else:
            nondirs.append(name)
 
    yield bottom, dirs, nondirs
 
    new_path = os.path.realpath(os.path.join(bottom, '..'))
    
    # see if we are at the top
    if new_path == bottom:
        return
 
    for x in walk_up(new_path):
        yield x

homedir = os.getcwd()

for c,d,f in walk_up(os.getcwd()):
        if '.fstconfig' in f:
            homedir = c
            break

cpath = os.path.join(homedir, ".fstconfig")


def help(what):
    
    print({
        "about": """'fst about'
Displays about information
""",
        "clear": """'fst clear'
Clears all current configuration. 
""",
        "help": """'fst help'
Displays help. 
""",
        "host": """'fst host [$HOST]'
Sets or displays the current host for the ftp connection. 
    $HOST    Host to set. 
""",
        "pull": """'fst pull $TARGET'
Pulls the specefied target. 
    $TARGET    Target to pull. 
""",
        "pulldir": """'fst pulldir [$DIR]'
Pulls the specefied directory, relative to the current directory. 
    $DIR    Directory to pull. Defaults to current directory. 
""",
        "push": """'fst push $TARGET'
Pushes the specefied target. 
    $TARGET    Target to push. 
""",
        "pushdir": """'fst pushdir [$DIR]'
Pushes the specefied directory, relative to the current directory. 
    $DIR    Directory to push. Defaults to current directory. 
""",
        "pwd": """'fst pwd'
Prints the current directory relative to the directory root. 
""",
        "rm": """'fst rm $TARGET'
Removes the specefied target. 
    $TARGET    Target to remove. 
""",
        "status": """'fst status'
Prints the current directory root. 
""",
        "target": """'fst target $NAME $DIR'
Creates or updates a target. 
    $NAME   Name of target to create or update. 
    $DIR    Directory to set to relative to current directory. 
""",
        "user": """'fst user [$USER]'
Sets or displays the current username for the ftp connection. 
    $USER    Username to set. 
""",
        "which": """'fst which [$TARGET]'
Displays the specefied target or prints a list of all targets. 
    $TARGET    Name of target to show destination. 
""",
        "rcd": """'fst rcd [$DIR]'
Sets the remote root directory
    $DIR    Remote root directory
""",
        "fork": """'fst fork'
Forces a configuration file in the current directory. Automatically calls fst rcd. 
"""
    }.get(what, """fst - FTP File Sync Tool
(c) Tom Wiesing 2013
Available commands: 

fst about
fst clear
fst fork
fst help
fst host
fst pull
fst pulldir
fst push
fst pushdir 
fst pwd
fst rm
fst rcd
fst status
fst target
fst user
fst which

Type 'fst help $TOPIC' for more information. """));
    
def conf_get(set, default=None):
    try:
        config = ConfigParser.SafeConfigParser()
        config.read(cpath)
        return json.loads(config.get('fst', set))
    except:
        if(default == None):
            print "Missing config: "+set
            sys.exit(1)
        else:
            return default

def conf_set(set, val):
    config = ConfigParser.SafeConfigParser()
    try:    
        config.read(cpath)
    except:
        pass
    try:
        config.add_section('fst')
    except:
        pass
    config.set('fst', set, json.dumps(val))
    try:
        with open(cpath, 'w') as configfile:    # save
            config.write(configfile)
    except:
        print "Can't store config. "
        sys.exit(1)

def conf_del(set):
    config = ConfigParser.SafeConfigParser()
    try:    
        config.read(cpath)
    except:
        pass
    try:
        config.add_section('fst')
    except:
        pass
    config.remove_option('fst', set)
    try:
        with open(cpath, 'w') as configfile:    # save
            config.write(configfile)
    except:
        print "Can't remove config: "+set
        sys.exit(1)
        
def set_target(target, dir):
    list = conf_get("targets", [])
    if not target in list:
        list.append(target)
    conf_set("targets", list)
    conf_set("target_"+target, os.path.relpath(os.path.abspath(dir), homedir))

def rm_target(target):
    list = conf_get("targets", [])
    if target in list:
        list.remove(target)
    conf_set("targets", list)
    conf_del("target_"+target)

def get_target(target):
    return conf_get("target_"+target)

def get_rcd():
    return conf_get("rcd", "")
def pull_dir(dir):
    spth = os.getcwd()
    os.chdir(homedir)
    dir = os.path.relpath(os.path.abspath(dir), homedir)
    host = conf_get("host")
    user = conf_get("user")
    command = """
open """+host+"""
user """+user+"""
lcd """+os.getcwd()+"""
mirror --delete --verbose -x \\.fstconfig """+os.path.join(get_rcd(), dir)+""" """+dir+"""
bye"""
    call(["lftp", "-e", command])
    os.chdir(spth)
    
def push_dir(dir):
    spth = os.getcwd()
    os.chdir(homedir)
    host = conf_get("host")
    user = conf_get("user")
    command = """
open """+host+"""
user """+user+"""
lcd """+homedir+"""
mirror --delete --verbose -x \\.fstconfig --reverse """+dir+""" """+os.path.join(get_rcd(), dir)+"""
bye"""
    call(["lftp", "-e", command])
    os.chdir(spth)

def config_option(params, option, default=None):
    try:
        conf_set(option, params[1])
        print "'"+option+"' = '"+params[1]+"'"
    except:
       print conf_get(option, default)
       sys.exit(1) 

def main(params):
    if len(params) > 0:
        oper = params[0]
        if oper == "user":
            config_option(params, "user")
        elif oper == "host":
            config_option(params, "host")
        elif oper == "rcd":
            config_option(params, "rcd", "")
        elif oper == "fork":
            try:
                shutil.copy(cpath, os.path.join(os.getcwd(), ".fstconfig"))
            except shutil.Error:
                print "Can't fork: Config already in CD. "
                sys.exit(1)
            except IOError:
                print "Can't fork: Nothing to fork. "
                pass
            rcd = os.path.join(conf_get("rcd", ""), os.path.relpath(os.path.abspath(os.getcwd()), homedir))
            # Update all the directories
            homedir = os.getcwd()
            cpath = os.path.join(homedir, ".fstconfig")
            #Update settings
            conf_set("rcd", rcd)
            print "Forked, 'rcd' = '"+rcd+"'"
        elif oper == "clear":
            try:
                os.remove(cpath)
                print "config cleared. "
            except OSError:
                print "Can't clear config (Empty config?)"
                sys.exit(1)
        elif oper == "target":
            try:
                set_target(params[1], params[2])
                print "'target'['"+params[1]+"'] = '"+params[2]+"'"
            except:
                print "Missing parameter(s). "
        elif oper == "rm":
            try:
                rm_target(params[1])
                print "deleted 'target'['"+params[1]+"']"
            except:
                print "Missing parameter(s). "
        elif oper == "pull":
            try:
                pull_dir(get_target(params[1]))
            except:
                pull_dir(".")
        elif oper == "push":
            try:
                push_dir(get_target(params[1]))
            except:
                push_dir(".")
        elif oper == "pulldir":
            try:
                pull_dir(os.path.relpath(os.path.abspath(params[1]), homedir))
            except:
                pull_dir(os.path.relpath(".", homedir))
        elif oper == "pushdir":
            try:
                push_dir(os.path.relpath(os.path.abspath(params[1]), homedir))
            except:
                push_dir(os.path.relpath(".", homedir))
            
        elif oper == "which":
            try:
                print get_target(params[1])
            except:
                for key in conf_get("targets", []):
                    print key
        elif oper == "status":
            print homedir
        elif oper == "pwd":
            print os.path.relpath(os.path.abspath(os.getcwd()), homedir)
        elif oper == "help":
            try:
                help(params[1])
            except:
                help("")
        elif oper == "about":
            print "fst - FTP File Sync Tool"
            print "(c) Tom Wiesing 2013"
        else:
            print "Unknown Command"
    else:
        print "Missing command. See 'fst help'. "
    
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print "Error: KeyboardInterrupt"
        sys.exit(1)
