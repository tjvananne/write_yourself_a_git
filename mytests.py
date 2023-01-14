
# todo, make this into real pytests.
# I'm just experimenting for right now.

from libwyag import repo_path

class DummyRepo(object):
    def __init__(self, gitdir):
        self.gitdir = gitdir

myrepo = DummyRepo(gitdir = "project_dir")

# both of these run successfully
print(repo_path(myrepo, "some", "long", "path"))
print(repo_path(myrepo, "one_str_path"))


