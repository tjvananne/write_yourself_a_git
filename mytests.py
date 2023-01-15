
# todo, make this into real pytests.
# I'm just experimenting for right now.

# Test 1: debugging repo_path()
from libwyag import repo_path, repo_find

class DummyRepo(object):
    def __init__(self, gitdir):
        self.gitdir = gitdir

myrepo = DummyRepo(gitdir = "project_dir")

# both of these run successfully
print(repo_path(myrepo, "some", "long", "path"))
print(repo_path(myrepo, "one_str_path"))


# Test 2: debugging repo_find
import subprocess
subprocess.run(["./wyag", "init", "/mnt/c/Users/Taylor/Documents/my_new_repo_from_wyag"])
# set breakpoint here to inspect
repo_find("/mnt/c/Users/Taylor/Documents/my_new_repo_from_wyag/folder1/folder2")


print("done.")