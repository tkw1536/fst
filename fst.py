#!/usr/bin/env python

import sys, ConfigParser, os, json, shutil, re
from subprocess import call

#
# Utility Functions
#

# Walk up the directory tree
def walk_up(bottom):
    #from: https://gist.github.com/zdavkeos/1098474
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

#
# Messages
#

def dump_error(msg = ""):
    global quiet
    if not quiet:
        sys.stderr.write("** FST ERROR ** "+ msg + "\n")

def dump_message(msg = ""):
    global quiet
    if not quiet:
        sys.stdout.write( msg + "\n")

def die(msg = ""):
    global quiet
    if not quiet:
        sys.stderr.write("** FATAL FST ERROR ** "+ msg + "\n")
    sys.exit(1)

def dump_simu(msg):
    global simulate
    if simulate:
        dump_message("** SIMULATE ** "+ msg)
        return True
    else:
        return False


#
# Initialisation
#

# Initialise the current working dir (path)
def init_path():
    global homedir
    global cpath
    homedir = os.getcwd()
    for c,d,f in walk_up(os.getcwd()):
        if '.fstconfig' in f:
            homedir = c
            break
    cpath = os.path.join(homedir, ".fstconfig")

#
# Configuration
#

# Get a configuration
def conf_get(set, default=None):
    global homedir, cpath
    try:
        config = ConfigParser.SafeConfigParser()
        config.read(cpath)
        return json.loads(config.get('fst', set))
    except:
        if(default == None):
            die("Missing config: '"+set+"'")
        else:
            return default


# Set a configuration
def conf_set(set, val):
    global homedir, cpath
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
        die("Can't store config. ")

#delete a configuration setting
def conf_del(set):
    global homedir, cpath
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
        die("Can't remove config: "+set)
        sys.exit(1)

#Configuration option parser
def config_option(params, option, default=None, map=lambda x:x, unmap=lambda x: x):
    try:
        conf_set(option, map(params[0]))
        dump_message("'"+option+"' = '"+params[0]+"'")
    except:
       dump_message(unmap(conf_get(option, default)))

#Array Configuration option parser
def config_array_option(params, option, map=lambda x: x, unmap=lambda x: x, default=[]):
    if(len(params)>0):
        if(params[0] == "list"):
            config_array_option_dump(option, unmap, default)
        elif (params[0] == "rm" or params[0] == "remove" or params[0] == "off"): 
            config_array_option_remove(option, params[1:], map, default)
        elif (params[0] == "add" or params[0] == "on"):
            config_array_option_add(option, params[1:], map, default)
        else:
            die("Wrong parameter(s) for option '"+ option +"'")
    else:
        config_array_option_dump(option, unmap, default)

def config_array_option_add(option, adds, map=lambda x: x, default=[]): 
    old = conf_get(option, default)
    for value in adds: 
        newval = map(value)
        if not newval in old:
            old.append(newval)
            dump_message(option+".push('"+value+"')")
        else:
            dump_error("'"+value+"' already in '"+option+"', add failed")
    conf_set(option, old)

def config_array_option_remove(option, removes, map=lambda x: x, default=[]): 
    old = conf_get(option, default)
    for value in removes: 
        newval = map(value)
        if newval in old:
            old.remove(newval)
            dump_message(option+".pop('"+value+"')")
        else:
            dump_error("'"+value+"' not in '"+option+"', remove failed")
    if(len(removes) == 0):
        old = []
    conf_set(option, old)

def config_array_option_dump(option, unmap=lambda x: x, default=[]): 
    for value in conf_get(option, default):
        dump_message(unmap(value))

def config_map_option(params, option, map=lambda x: x, unmap=lambda x: x, default={}):
    if(len(params)>0):
        if(params[0] == "list" or params[0] == "get"):
            if(len(params) > 1):
                config_map_option_dump(option, unmap, default, params[1])
            else:
                config_map_option_dump(option, unmap, default)
        elif (params[0] == "rm" or params[0] == "delete" or params[0] == "del"): 
            config_map_option_remove(option, params[1:], default)
        elif (params[0] == "add" or params[0] == "set"):
            if(len(params) > 2):
                config_map_option_add(option, params[1], params[2], map, default)
            else:
                die("Wrong parameter(s) for option '"+ option +"'")
        else:
            die("Wrong parameter(s) for option '"+ option +"'")
    else:
        config_map_option_dump(option, unmap, default)

def config_map_option_add(option, name, val, map=lambda x: x, default={}): 
    old = conf_get(option, default)
    old[name] = map(val)
    conf_set(option, old)

def config_map_option_remove(option, removes, default={}): 
    old = conf_get(option, default)
    for value in removes: 
        newval = value
        if newval in old:
            old.pop(newval, None)
            dump_message(option+".pop('"+value+"'')")
        else:
            dump_error("'"+value+"' not in '"+option+"', pop failed")
    conf_set(option, old)

def config_map_option_dump(option, unmap=lambda x: x, default={}, key=None): 
    opt = conf_get(option, default)
    if key == None:
        for value in opt:
            dump_message("'" + value + "': " + unmap(opt[value]))
    else:
        if key in opt:
            dump_message(unmap(opt[key]))
        else:
            die("Can't find '"+key+"' in '"+option+"'. ")
#
#   Getters
#""

#Get a target if it exists
def get_target(target):
    global homedir
    targets = conf_get("target", {})

    if target in targets:
        return os.path.join(homedir, targets[target])
    elif target == "master":
        return homedir
    else:
        die("Can't find target '"+target+"' in targets. ")
# Get Remote CD (base)
def get_rcd():
    return conf_get("rcd", "")

def get_pwd():
    global homedir
    return os.path.relpath(os.path.abspath(os.getcwd()), homedir)

def parse_flags(params): 
    flags = conf_get("flags", default = ["recurse"])
    flags = {
        "force": "force" in flags, 
        "recurse": "recurse" in flags, 
        "continue": "continue" in flags
    }
    while (len(params) > 0):
        if params[0] in ["--recurse", "--no-recurse", "-r", "-nr", "--continue", "--no-continue", "-c", "-nc", "--force", "--no-force", "-f", "-nf"]: 
            setting = params[0]
            params = params[1:]
            if setting in ["--recurse", "-r"]:
                flags["recurse"] = True
            if setting in ["--no-recurse", "-nr"]:
                flags["recurse"] = False
            if setting in ["--continue", "-c"]:
                flags["continue"] = True
            if setting in ["--no-continue", "-nc"]:
                flags["continue"] = False
            if setting in ["--force", "-f"]:
                flags["force"] = True
            if setting in ["--no-force", "-nf"]:
                flags["force"] = False
        else:
            break

    return [flags, params] 


#
# Push / Pull Core Things
#

# Push a dir
def pull_dir(dir, recurse=True, force=False, cont=False):
    global homedir, cpath
    spth = os.getcwd()
    os.chdir(homedir)
    dir = os.path.relpath(os.path.abspath(dir), homedir)
    host = conf_get("host")
    user = conf_get("user")

    fstring = ""
    includes = conf_get("include_file", [])
    for inc in includes:
        fstring += "-i "+inc
    excludes = conf_get("exclude_file", [])
    for exc in excludes:
        fstring += "-x "+exc

    flags = ""

    if recurse != True:
        flags += " --no-recursion"
    if force != True: 
        flags += " --only-newer"
    if cont == True: 
        flags += " --continue"

    if(dump_simu("Pulling a directory")):
        flags += " --dry-run"

    command = """
open """+host+"""
user """+user+"""
lcd """+os.getcwd()+"""
mirror """+flags+""" --delete --verbose -x \\.fstconfig """+fstring+os.path.join(get_rcd(), dir)+""" """+dir+"""
bye"""

    if(dump_simu(command)):
        return
    
    call(["lftp", "-e", command])
    os.chdir(spth)

# Pull a dir
def push_dir(dir, recurse=True, force=False, cont=False):
    global homedir, cpath
    spth = os.getcwd()
    os.chdir(homedir)
    dir = os.path.relpath(os.path.abspath(dir), homedir)
    host = conf_get("host")
    user = conf_get("user")

    fstring = ""
    includes = conf_get("include_file", [])
    for inc in includes:
        fstring += "-i "+inc
    excludes = conf_get("exclude_file", [])
    for exc in excludes:
        fstring += "-x "+exc

    flags = ""

    if recurse != True:
        flags += " --no-recursion"
    if force != True: 
        flags += " --only-newer"
    if cont == True: 
        flags += " --continue"

    if(dump_simu("Pusshing a directory")):
        flags += " --dry-run"

    command = """
open """+host+"""
user """+user+"""
lcd """+homedir+"""
mirror """+flags+""" --delete --verbose -x \\.fstconfig """+fstring+""" --reverse """+dir+""" """+os.path.join(get_rcd(), dir)+"""
bye"""
    
    if(dump_simu(command)):
        return

    call(["lftp", "-e", command])
    os.chdir(spth)
#
# Commands
#

# Command help
def cmd_help(what = "", *args):
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
        "pulltarget": """'fst pulltarget [$FLAGS] $TARGET'
Pulls the specefied target. 
    $TARGET    Target to pull. 
    $FLAGS     Flags to use, see 'fst help flags'
""",
        "pull": """'fst pull [$FLAGS] [$STUFF [$STUFF ... ]]'
Pulls directories or targets. 
    $STUFF    Directory or target to pull. Directories take preference. 
    $FLAGS    Flags to use, see 'fst help flags'
""",
        "push": """'fst push [$FLAGS] [$STUFF [$STUFF ... ]]'
Pulls directories or targets. 
    $STUFF    Directory or target to push. Directories take preference. 
    $FLAGS    Flags to use, see 'fst help flags'
""",
        "pulldir": """'fst pulldir [$FLAGS] [$DIR]'
Pulls the specefied directory, relative to the current directory. 
    $DIR    Directory to pull. Defaults to current directory. 
    $FLAGS  Flags to use, see 'fst help flags'
""",
        "pushtarget": """'fst pushtarget [$FLAGS] $TARGET'
Pushes the specefied target. 
    $TARGET    Target to push. 
    $FLAGS     Flags to use, see 'fst help flags'
""",
        "pushdir": """'fst pushdir [$FLAGS] [$DIR] '
Pushes the specefied directory, relative to the current directory. 
            Do not recurse into subdirectories. 
    $DIR    Directory to push. Defaults to current directory. 
    $FLAGS  Flags to use, see 'fst help flags'
""",
        "pwd": """'fst pwd'
Prints the current directory relative to the directory root. 
""",
        "status": """'fst status'
Prints the current directory root. 
""",
        "target": """'fst target [set|get|del] $NAME [$DIR]'
Creates or updates a target. 
    $NAME   Name of target to create or update. 
    $DIR    Directory to set to relative to current directory. 
""",
        "user": """'fst user [$USER]'
Sets or displays the current username for the ftp connection. 
    $USER    Username to set. 
""",
        "rcd": """'fst rcd [$DIR]'
Sets the remote root directory
    $DIR    Remote root directory
""",
        "fork": """'fst fork'
Forces a configuration file in the current directory. Automatically calls fst rcd. 
""",
        "include": """'fst include add|remove|list [$FILE [$FILE2 ...]]'
Adds or removes files from the include list. 
    $FILE   File to include or exclude
    $FILE2  Another file 
""",
        "exclude": """'fst exclude add|remove|list [$FILE [$FILE2 ...]]'
Adds or removes files from the exclude list. 
    $FILE   File to include or exclude
    $FILE2  Another file 
""",
        "flags": """'fst flags [on|off] [recurse|continue|force]'
Adds or removes default flags. 
    $FLAGS  Flags to use. Supported are: 

    --recurse,
    --no-recurse, 
    -nr,  
    -r      Recurse into subdirectories. Enabled by default. 

    --continue, 
    --no-continue, 
    -nc, 
    -c      Continue interrupted transfer. Disabled by default. 

    --force, 
    --no-force, 
    -nf
    -f      Force to update all files, not only newer files. Disabled by default. 
""",
        "viewcfg": """'fst viewcfg'
            Shows the current Configuration. Same as 'cat .fstconfig' in the the root directory. 
"""
    }.get(what, """fst - FTP File Sync Tool
(c) Tom Wiesing 2013
Usage: 

fst [--quiet|--simulate] COMMAND [PARAMETERS]

    --quiet,
    -q          Supress any messages which do not come from lftp.   

    --simulate,
    -s          Simulate Pulling and Pushing operations. 

Available commands: 

about
clear
exclude
flags
fork
help
host
include
pull
pulldir
pulltarget
push
pushdir
pushtarget
rcd
status
target
user
viewcfg


Type 'fst help COMMAND' for more information. """));

# Without parameters
def cmd_zero():
    die("Missing operator. \n Usage: fst [--quiet|--simulate] about|clear|exclude|fork|help|host|include|pull|pulldir|push|pushdir|pwd|rcd|status|target|user")


# Called unknown command
def cmd_unknown(*args):
    die("Unknown Command. \n see 'fst help' for more information")

# About Command  
def cmd_about(*args):
    print "FST - File Sync Tool"
    print "Version 1.0"
    print "(c) Tom Wiesing 2013"

# Clear Command
def cmd_clear(*args):
    global homedir, cpath, quiet
    try:
        os.remove(cpath)
        dump_message("config cleared. ")
    except OSError:
        die("Can't clear config (Empty config?)")

# Exclude command
def cmd_exclude(*args):
    global homedir, cpath, quiet
    config_array_option(args, "exclude_file", map=re.escape)

# Fork Command
def cmd_fork(*args):
    global homedir, cpath, quiet
    try:
        shutil.copy(cpath, os.path.join(os.getcwd(), ".fstconfig"))
    except shutil.Error:
        die("Fork failed: Config already in current directory. ")
    except IOError:
        die("Fork failed: Nothing to fork from. ")
    rcd = os.path.join(conf_get("rcd", ""), os.path.relpath(os.path.abspath(os.getcwd()), homedir))
    # Update all the directories
    homedir = os.getcwd()
    cpath = os.path.join(homedir, ".fstconfig")
    #Update settings
    conf_set("rcd", rcd)
    dump_message("Forked, 'rcd' = '"+rcd+"'")

# Flags Command
def cmd_flags(*params):
    def flags_verify(f):
        if not f in ["recurse", "continue", "force"]:
            die("Unknown flag '"+f+"'")
        else:
            return f
    config_array_option(params, "flags", map=flags_verify, default=["recurse"])

# Host Command
def cmd_host(*params):
    global homedir, cpath, quiet
    config_option(params, "host")

# Include Command
def cmd_include(*params):
    global homedir, cpath, quiet
    config_array_option(params, "include_file", map=re.escape)


# Target Command
def cmd_target(*params):
    global homedir, cpath, quiet
    config_map_option(params, "target", map=lambda x: os.path.relpath(os.path.abspath(x), homedir))

# Pull Command
def cmd_pull(*params):
    [flags, params] = parse_flags(params)
    if(len(params) == 0):
        pull_dir(get_target("master"), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])
        return
    for param in params:
        if os.path.isdir(param):
            cmd_pulldir(param, flags=flags)
        else:
            cmd_pulltarget(param, flags=flags)



# Pull Target Command
def cmd_pulltarget(*params, **f):
    global homedir, cpath, quiet

    if "flags" in f:
        flags = f["flags"]
    else: 
        [flags, params] = parse_flags(params)

    try:
        pull_dir(get_target(params[0]), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])
    except IndexError:
        pull_dir(get_target("master"), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])

# Pull Dir Command
def cmd_pulldir(*params, **f):
    global homedir, cpath, quiet

    if "flags" in f:
        flags = f["flags"]
    else: 
        [flags, params] = parse_flags(params)

    try:
        pull_dir(os.path.relpath(os.path.abspath(params[0]), homedir), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])
    except IndexError:
        pull_dir(get_pwd(), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])

# Push Command
def cmd_push(*params): 
    [flags, params] = parse_flags(params)
    if(len(params) == 0):
        push_dir(get_target("master"), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])
        return
    for param in params:
        if os.path.isdir(param):
            cmd_pushdir(param, flags=flags)
        else:
            cmd_pushtarget(param, flags=flags)

# Push Dir Command
def cmd_pushdir(*params, **f):
    global homedir, cpath, quiet

    if "flags" in f:
        flags = f["flags"]
    else: 
        [flags, params] = parse_flags(params)

    try:
        push_dir(os.path.relpath(os.path.abspath(params[0]), homedir), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])
    except IndexError:
        push_dir(get_pwd(), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])

# Pull Target Command
def cmd_pushtarget(*params, **f): 
    global homedir, cpath, quiet

    if "flags" in f:
        flags = f["flags"]
    else: 
        [flags, params] = parse_flags(params)

    try:
        push_dir(get_target(params[0]), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])
    except IndexError:
        push_dir(get_target("master"), recurse=flags["recurse"], force=flags["force"], cont=flags["continue"])

# pwd Command
def cmd_pwd(*params):
    global homedir, cpath, quiet
    print os.path.relpath(os.path.abspath(os.getcwd()), homedir)

# rcd Command
def cmd_rcd(*params): 
    config_option(params, "rcd", "")

def cmd_status(*params):
    global homedir, cpath, quiet
    print homedir

def cmd_user(*params):
    config_option(params, "user", "")

def cmd_viewcfg(*params): 
    global homedir, cpath, quiet
    call(["cat", cpath])

#
# Main
#


def main(params):
    global homedir, cpath, quiet, simulate
    quiet = False
    simulate = False

    try:
        if(params[0] == "--quiet" or params[0] == "-q"):
            quiet = True
            params = params[1:]
        elif(params[0] == "--simulate" or params[0] == "-s"):
            simulate = True
            dump_message("** SIMULATE ** Will simulate only")
            params = params[1:]
    except:
        pass
    

    if len(params) > 0:
        oper = params[0]
        params = params[1:]

        name = "cmd_" + oper

        if name in globals():
            globals()[name](*params)
        else:
            cmd_unknown()
    else:
        cmd_zero()
    
if __name__ == '__main__':
    init_path()
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        die("KeyboardInterrupt")
        sys.exit(1)
