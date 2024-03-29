
import argparse
import collections
import configparser
import hashlib
from math import ceil
import os
import re
import sys
from typing import Optional, List
import zlib

argparser = argparse.ArgumentParser(description="The stupidest content tracker")

# we need to handle sub commands like "init" and "commit" etc.
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

# `dest="command"` means the name of the chosen subparser will be returned as a string
# in a field called `command`


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)

    if   args.command == "add"          : cmd_add(args)
    elif args.command == "cat-file"     : cmd_cat_file(args)
    elif args.command == "checkout"     : cmd_checkout(args)
    elif args.command == "commit"       : cmd_commit(args)
    elif args.command == "hash-object"  : cmd_hash_object(args)
    elif args.command == "init"         : cmd_init(args)
    elif args.command == "log"          : cmd_log(args)
    elif args.command == "ls-files"     : cmd_ls_files(args)
    elif args.command == "ls-tree"      : cmd_ls_tree(args)
    elif args.command == "merge"        : cmd_merge(args)
    elif args.command == "rebase"       : cmd_rebase(args)
    elif args.command == "rev-parse"    : cmd_rev_parse(args)
    elif args.command == "rm"           : cmd_rm(args)
    elif args.command == "show-ref"     : cmd_show_ref(args)
    elif args.command == "tag"          : cmd_tag(args)


class GitRepository(object):
    """A git repository"""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a Git repository %s" % path)

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)




# creating some file/path utilities

def repo_path(repo, *path) -> str:
    """Compute path under repo's gitdir."""
    return os.path.join(repo.gitdir, *path)



# It will be interesting to see where/why this is useful..
def repo_file(repo, *path, mkdir=False) -> str:
    """
    Same as repo_path, but create dirname(*path) if absent.
    Will only create the path up to but not including the last entry in *path.
    For example:
    repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will
    create .git/refs/remotes/origin.
    """

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)



def repo_dir(repo, *path, mkdir=False) -> Optional[str]:
    """
    Same as repo_path, but mkdir *path if absent if mkdir.
    Will return a str of the path if it creates one.
    """

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception("Not a directory %s" % path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_create(path):
    """Create a new repository at path."""

    # when we create the repo with this function, we use the force
    # so we bypass all of the checks.
    repo = GitRepository(path, True)

    # First, we make sure the path either doesn't exist or is an empty dir.
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception ("%s is not a directory!" % path)
        if os.listdir(repo.worktree):
            raise Exception ("%s is not empty!" % path)
    else:
        os.makedirs(repo.worktree)

    assert(repo_dir(repo, "branches", mkdir=True))
    assert(repo_dir(repo, "branches", mkdir=True))
    assert(repo_dir(repo, "refs", "tags", mkdir=True))
    assert(repo_dir(repo, "refs", "heads", mkdir=True))

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

    # .git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo



def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret


# Where should this code go? This is a strange place to put it.
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")

# I'd like to better understand these arguments to the sub parser.
# Also, how many layers of sub parsers can we add? How does that work?
argsp.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository."
)

def cmd_init(args):
    repo_create(args.path)

# at this point, I can execute
# ./wyag init [path]


def repo_find(path=".", required=True) -> Optional[GitRepository]:
    """Find the root path of the current repo."""

    # what's this? Returns the canonical path, eliminating any symbolic links, if any
    # Behaves differently across OSs. This might be why wyag doesn't explicitly support Windows?
    path = os.path.realpath(path)

    # Interesting... so we instantiate a new object each time we do something
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    # if we haven't returned, recurse in parent
    parent = os.path.realpath(os.path.join(path, "..")) # <-- didn't know you could do that.

    if parent == path:
        # Base case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root
        if required:
            raise Exception("No git directory.")
        else:
            return None

    # Recursive case
    return repo_find(parent, required)


class GitObject(object):

    # (I'm not defining class variables...)

    def __init__(self, repo, data=None):
        self.repo=repo

        if data != None:
            self.deserialize(data)

    def serialize(self):
        """
        This function MUST be implemented by subclasses.
        It must read the object's contents from self.data, a byte string, and
        do whatever it takes to convert it into a meaningful representation. What
        exactly that means depend on each subclass.
        """
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")


def object_read(repo, sha):
    """
    Read object_id from Git repository repo. Returns a
    GitObject whose exact type depends on the object.
    """

    path = repo_file(repo, "object", sha[0:2], sha[2:])

    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type (read until the space)
        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        # Pick constructor
        if   fmt==b'commit'  : c=GitCommit
        elif fmt==b'tree'    : c=GitTree
        elif fmt==b'tag'     : c=GitTag
        elif fmt==b'blob'    : c=GitBlob
        else:
            raise Exception("Unknown type {0} for object {1}".format(fmt.decode("ascii"), sha))

        # Call constructor and return object
        return c(repo, raw[y+1:])


# TODO: this is a placeholder for now
def object_find(repo, name, fmt=None, follow=True):
    return name


def object_write(obj, actually_write=True):
    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        # Compute path
        path=repo_file(obj.repo, "objects", sha[0:2], sha[2:], mkdir=actually_write)

        with open(path, "wb") as f:
            # Compress and write
            f.write(zlib.compress(result))

    return sha


class GitBlob(GitObject):
    fmt=b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data




argsp = argsubparsers.add_parser(
    "cat-file",
    help="Provide content of repository objects"
)

argsp.add_argument(
    "type",
    metavar="type",
    choices=["blob", "commit", "tag", "tree"],
    help="Specify the type"
)

argsp.add_argument(
    "object",
    metavar="object",
    help="The object to display"
)


def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())


def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())




argsp = argsubparsers.add_parser(
    "hash-object",
    help="Compute object ID and optionally creates a blob from a file"
)

argsp.add_argument(
    "-t",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default="blob",
    help="Specify the type"
)

argsp.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Actually write the object into the database"
)

argsp.add_argument(
    "path",
    help="Read object from <file>"
)


def cmd_hash_object(args):
    if args.write:
        repo = GitRepository(".")
    else:
        repo = None
    
    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)


def object_hash(fd, fmt, repo=None):
    data = fd.read()

    # Choose constructor depending on
    # object type found in header.
    if   fmt==b'commit'  : obj=GitCommit(repo, data)
    elif fmt==b'tree'    : obj=GitTree(repo, data)
    elif fmt==b'tag'     : obj=GitTag(repo, data)
    elif fmt==b'tlob'    : obj=GitBlob(repo, data)
    else:
        raise Exception("Unknown type %s!" % fmt)
    
    return object_write(obj, repo)



def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct = collections.OrderedDict()
        # You CANNOT declare the argument as dct=OrderedDict() or all
        # calls to the functions will endlessly grow the same dict.
    
    # We search for the next space and the next newline
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # If space appareas before newline, we have a keyword.

    # Base case
    # =========
    # If newline appears first (or there's no space at all, in which
    # case find returns -1), we assume a blank line. A blank line
    # means the remainder of the data is the message.
    if (spc < 0) or (nl < spc):
        assert(nl == start)
        dct[b''] = raw[start+1:]
        return dct
    
    # Recursive case
    # ==============
    # We read a key-value pair and recurse for the next.
    key = raw[start:spc]

    # Find the end of the value. Continuation lines begin with a
    # space, so we loop until we find a "\n" not followed by a space.
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        # ord() is used because indexing into bytes produces ints
        # `ord(' ')` is more descriptive than `32`
        if raw[end+1] != ord(' '): break

    # Grab the value
    # Also, drop the leading space on continuation lines
    value = raw[spc+1:end].replace(b'\n ', b'\n')

    # Don't overwrite existing data contents
    # (This is where I wish we could mix DefaultDict and OrderedDict)
    # Question: why are we putting both the key and the value in a list
    # as the value for each key? Why not just key/value?
    if key in dct:
        if isinstance(dct[key], list):
            dct[key].append(value) # <-- under what circumstance does this run?
        else:
            dct[key] = [ dct[key], value ]
    else:
        dct[key]=value
    
    return kvlm_parse(raw, start=end+1, dct=dct)


def kvlm_serialize(kvlm):
    ret = b''

    # Output fields
    for k in kvlm.keys():
        # Skip the message itself
        if k == b'': continue
        val = kvlm[k]
        # Normalize to a list
        if type(val) != list:
            val = [ val ]
        
        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'
    
    # Append message
    ret += b'\n' + kvlm[b'']

    return ret


class GitCommit(GitObject):
    fmt=b'commit'

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)
    
    def serialize(self):
        return kvlm_serialize(self.kvlm)



argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit",
                   default="HEAD",
                   nargs="?",
                   help="Commit to start at.")


def cmd_log(args):
    repo = repo_find()

    print("digraph wyaglog{")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")


def log_graphviz(repo, sha, seen):

    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    assert (commit.fmt==b'commit')

    if not b'parent' in commit.kvlm.keys():
        # Base case: the initial commit.
        return
    
    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [ parents ]

    for p in parents:
        p = p.decode("ascii")
        print("c_{0} -> c_{1};".format(sha, p))
        log_graphviz(repo, p, seen)



class GitTreeLeaf(object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha


def tree_parse_one(raw, start=0):
    # Find the space terminator of the mode
    x = raw.find(b' ', start)
    assert(x - start == 5 or x - start == 6)

    # Read the mode
    mode = raw[start:x]

    # Find the NULL terminator of the path
    y = raw.find(b'\x00', x)
    # and read the path
    path = raw[x+1:y]

    # Read the SHA and convert to an hex string
    # TODO: step through this part...
    sha = hex(
        int.from_bytes(
            raw[y+1:y+21], "big"))[2:] # hex() adds 0x in front,
                                       # we don't want that.

    return y+21, GitTreeLeaf(mode, path, sha)


def tree_parse(raw):
    pos = 0
    max = len(raw)
    ret = list()
    while pos < max:
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)
    
    return ret


def tree_serialize(obj):
    ret = b''
    for i in obj.items:
        ret += i.mode
        ret += b' '
        ret += i.path
        ret += b'\x00'
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")
    return ret


class GitTree(GitObject):
    fmt=b'tree'

    def deserialize(self, data):
        self.items = tree_parse(data)
    
    def serialize(self):
        return tree_serialize(self)


argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument("object",
                   help="The object to show.")

def cmd_ls_tree(args):
    repo = repo_find()
    obj = object_read(repo, object_find(repo, args.object, fmt=b'tree'))

    for item in obj.items:
        print(
            "{0} {1} {2}\t{3}".format(
                "0" * (6 - len(item.mode)) + item.mode.decode("ascii"),
                # Git's ls-tree displays the type
                # of the object pointed to. We can do that too
                object_read(repo, item.sha).fmt.decode("ascii"),
                item.sha,
                item.path.decode("ascii")
            )
        )




argsp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory.")

argsp.add_argument("commit",
                   help="The commit or tree to checkout")

argsp.add_argument("path",
                   help="The EMPTY directory to checkout on.")


def cmd_checkout(args):
    repo = repo_find()

    obj = object_read(repo, object_find(repo, args.commit))

    # If the object is a commit, we grab its tree
    if obj.fmt == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode("ascii"))
    
    # Verify that path is an empty directory
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not a directory {0}!".format(args.path))
        if os.listdir(args.path):
            raise Exception("Not an empty directory: {0}!".format(args.path))
    else:
        os.makedirs(args.path)
    
    tree_checkout(repo, obj, os.path.realpath(args.path).encode())


def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            with open(dest, 'wb') as f:
                f.write(obj.blobdata)



