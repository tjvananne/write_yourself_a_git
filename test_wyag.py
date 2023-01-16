
from libwyag import repo_path, repo_find

def test_repo_path():

    class DummyRepo(object):
        def __init__(self, gitdir):
            self.gitdir = gitdir

    myrepo = DummyRepo(gitdir = "project_dir")

    # both of these run successfully
    assert(repo_path(myrepo, "some", "long", "path") == "project_dir/some/long/path")
    assert(repo_path(myrepo, "one_str_path") == "project_dir/one_str_path")





