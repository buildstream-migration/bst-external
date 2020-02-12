#  Copyright (C) 2020 Codethink Limited
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Will Salmon <will.salmon@codethink.co.uk>
"""Add files relative to the project.
   
This plugin is for large files that can not be added to the VCS
system (possibly for licensing reasons). This plugin treats the files
as if they were a remote source and only calculates the files ref
as they are added to the source cache. This allows artifacts to be
resolved from the bst files alone like other remote sources.
This would ideally be located within the `files` directory.

**Usage:**

.. code:: yaml

   # Specify the project_ref source kind
   kind: project_ref

   # Specify the directory or file to be added
   path: file_or_directory

   # A sha representing the contents and layout of the contents of `path`
   ref: d63cbb6fdc0bbdadc4a1b92284826a6d63a7ebcd
"""

import os
import stat
import hashlib

from buildstream import Source, SourceError, Consistency
from buildstream import utils

class ProjectRefSource(Source):

    def configure(self, node):
        self.path = self.node_get_member(node, str, "path")
        self.fullpath = os.path.join(self.get_project_directory(), self.path)
        self.ref = self.node_get_member(node, str, "ref", None)

    def get_unique_key(self):
        return [self.path, self.ref]

    def load_ref(self, node):
        self.ref = self.node_get_member(node, str, 'ref', None)

    def get_ref(self):
        return self.ref

    def set_ref(self, ref, node):
        node['ref'] = self.ref = ref

    def preflight(self):
        pass

    def fetch(self):
        # Download the file, raise hell if the sha256sums don't match,
        # and mirror the file otherwise.
        with self.timed_activity("Fetching {}".format(self.path), silent_nested=True):
            sha256 = self._ensure_mirror()
            if sha256 != self.ref:
                raise SourceError("File imported from {} has sha256sum '{}', not '{}'!"
                                  .format(self.path, sha256, self.ref))

    def track(self):
        # there is no 'track' field in the source to determine what/whether
        # or not to update refs, because tracking a ref is always a conscious
        # decision by the user.
        with self.timed_activity("Tracking {}".format(self.path),
                                 silent_nested=True):
            new_ref = self._ensure_mirror()

            if self.ref and self.ref != new_ref:
                detail = "When tracking, new ref differs from current ref:\n" \
                    + "  Tracked path: {}\n".format(self.path) \
                    + "  Current ref: {}\n".format(self.ref) \
                    + "  New ref: {}\n".format(new_ref)
                self.warn("Local files have changed", detail=detail)

            return new_ref

    def get_consistency(self):
        if self.ref is None:
            return Consistency.INCONSISTENT

        if os.path.exists(self._get_mirror_file()):
            return Consistency.CACHED

        else:
            return Consistency.RESOLVED

    def _generate_ref(self, fullpath):
        # Get a list of tuples of the the project relative paths and fullpaths
        if os.path.isdir(fullpath):
            filelist = utils.list_relative_paths(fullpath)
            filelist = [(relpath, os.path.join(fullpath, relpath)) for relpath in filelist]
        else:
            filelist = [(self.path, fullpath)]
        # Return a list of (relative filename, sha256 digest) tuples, a sorted list
        # has already been returned by list_relative_paths()
        unique_parts = [(relpath, unique_key(fullpath)) for relpath, fullpath in filelist]
        h = hashlib.sha256()
        for (rel, sha) in unique_parts:
            h.update(rel.encode('utf-8'))
            h.update(sha.encode('utf-8'))
        return h.hexdigest()

    def _ensure_mirror(self):
        # Copy the files somewere temp and out of the way so that they wont change while we calc the sha
        # Then move it, move is atomic so once the mirror is in the real place
        # we can qurey the mirror to know if we have everything.
        with self.tempdir() as td:
            # `targetdir` is needed as td cant be moved
            # inside this `with`
            targetdir = os.path.join(td, "moveable")
            if os.path.isdir(self.fullpath):
                utils.copy_files(self.fullpath, targetdir)
            else:
                os.makedirs(targetdir)
                #filename = os.path.basename(self.path)
                base, _ = os.path.split(self.path)
                basefolder = os.path.join(targetdir, base)
                os.makedirs(basefolder)
                targetdir = os.path.join(targetdir, self.path)
                utils.safe_copy(self.fullpath, targetdir)

            sha256 = self._generate_ref(targetdir)

            # Even if the folder already exists, move the new folder over.
            # In case the old file was corrupted somehow.
            if os.path.exists(self._get_mirror_file(str(sha256))):
                utils._force_rmtree(self._get_mirror_file(str(sha256)))
            os.rename(targetdir, self._get_mirror_file(str(sha256)))

            return sha256
        
    def _get_mirror_file(self, sha=None):
        return os.path.join(self.get_mirror_directory(), sha or self.ref)

    def stage(self, directory):

        # Dont use hardlinks to stage sources, they are not write protected
        # in the sandbox.
        with self.timed_activity("Staging local files at {}".format(self.path)):

            if os.path.isdir(self.fullpath):
                files = list(utils.list_relative_paths(self.fullpath, list_dirs=True))
                utils.copy_files(self.fullpath, directory, files=files)
            else:
                destfile = os.path.join(directory, os.path.basename(self.path))
                files = [os.path.basename(self.path)]
                utils.safe_copy(self.fullpath, destfile)

            for f in files:
                # Non empty directories are not listed by list_relative_paths
                dirs = f.split(os.sep)
                for i in range(1, len(dirs)):
                    d = os.path.join(directory, *(dirs[:i]))
                    assert os.path.isdir(d) and not os.path.islink(d)
                    os.chmod(d, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

                path = os.path.join(directory, f)
                if os.path.islink(path):
                    pass
                elif os.path.isdir(path):
                    os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                else:
                    st = os.stat(path)
                    if st.st_mode & stat.S_IXUSR:
                        os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    else:
                        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

# Create a unique key for a file
def unique_key(filename):

    # Return some hard coded things for files which
    # have no content to calculate a key for
    if os.path.isdir(filename):
        return "0"
    elif os.path.islink(filename):
        # For a symbolic link, use the link target as it's unique identifier
        return os.readlink(filename)

    return utils.sha256sum(filename)


    
def setup():
    return ProjectRefSource
