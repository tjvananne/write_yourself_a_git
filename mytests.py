
from libwyag import repo_find, kvlm_parse

# Test 1: walk through kvlm_parse
from data import commit
dct = kvlm_parse(commit)
print(dct)
print("catch")




# Test 2: debugging repo_find
# TODO: set up pytest-mock for this one
import subprocess
subprocess.run(["./wyag", "init", "../some_other_dir"])
# set breakpoint here to inspect
# repo_find("/mnt/c/Users/Taylor/Documents/my_new_repo_from_wyag/folder1/folder2")


print("done.")