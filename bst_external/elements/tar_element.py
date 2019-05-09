# Copyright (c) 2018 freedesktop-sdk
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors:
#        Thomas Coldrick <thomas.coldrick@codethink.co.uk>


"""
tar_element - Output tarballs
=============================

An element plugin for creating tarballs from the specified
dependencies

Default Configuration
~~~~~~~~~~~~~~~~~~~~~

The tarball_element default configuration:
  .. literalinclude:: ../../../bst_external/elements/tar_element.yaml
     :language: yaml
"""

import tarfile
import os
import hashlib

from buildstream import Element, Scope, ElementError

# Block size for reading tarball when hashing
BLOCKSIZE = 65536

# Permitted checksums
CHECKSUMS = set(['sha1', 'sha256', 'sha512', 'md5'])

class TarElement(Element):

    # The tarball's output is its dependencies, so
    # we must rebuild if they change
    BST_STRICT_REBUILD = True

    # Tarballs don't need runtime dependencies
    BST_FORBID_RDEPENDS = True

    # Our only sources are previous elements, so we forbid
    # remote sources
    BST_FORBID_SOURCES = True

    def configure(self, node):
        self.node_validate(node, [
            'filename', 'compression', 'include-checksums'
        ])
        self.filename = self.node_subst_member(node, 'filename')
        self.compression = self.node_get_member(node, str, 'compression')
        self.include_checksums = self.node_get_member(node, list,
                'include-checksums', [])

        if self.compression not in ['none', 'gzip', 'xz', 'bzip2']:
            raise ElementError("{}: Invalid compression option {}".format(self, self.compression))

    def preflight(self):
        checksums_set = set(self.include_checksums)
        if not checksums_set.issubset(CHECKSUMS):
            unsupported = list(checksums_set - CHECKSUMS)
            raise ElementError("{}: Unsupported checksum(s) {}".format(self,
                ', '.join(unsupported)))

    def get_unique_key(self):
        key = {}
        key['filename'] = self.filename
        key['compression'] = self.compression
        key['include-checksums'] = self.include_checksums
        return key

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def assemble(self, sandbox):
        basedir = sandbox.get_directory()
        inputdir = os.path.join(basedir, 'input')
        outputdir = os.path.join(basedir, 'output')
        os.makedirs(inputdir, exist_ok=True)
        os.makedirs(outputdir, exist_ok=True)

        # Stage deps in the sandbox root
        with self.timed_activity('Staging dependencies', silent_nested=True):
            self.stage_dependency_artifacts(sandbox, Scope.BUILD, path='/input')

        with self.timed_activity('Creating tarball', silent_nested=True):

            # Create an uncompressed tar archive
            compress_map = {'none': '', 'gzip': 'gz', 'xz': 'xz', 'bzip2':'bz2'}
            extension_map = {'none': '.tar', 'gzip': '.tar.gz', 'xz': '.tar.xz', 'bzip2': '.tar.bz2'}
            tarname = os.path.join(outputdir, self.filename + extension_map[self.compression])
            mode = 'w:' + compress_map[self.compression]
            with tarfile.TarFile.open(name=tarname, mode=mode) as tar:
                for f in os.listdir(inputdir):
                    tar.add(os.path.join(inputdir, f), arcname=f)

            if self.include_checksums:
                hash_map = {'sha1': hashlib.sha1, 'sha256': hashlib.sha256,
                        'sha512': hashlib.sha512, 'md5': hashlib.md5}

                # We use the path of the final checksum as a unique ID for the
                # hashes themselves to simplify data structure at the expense of
                # readability
                hashes = {}
                for hash_type in self.include_checksums:
                    hash_path = os.path.join(outputdir, self.filename +
                            '.{}sum'.format(hash_type))
                    hashes[hash_path] = hash_map[hash_type]()

                with open(tarname, 'rb') as f:
                    while True:
                        buf = f.read(BLOCKSIZE)
                        if not buf:
                            break
                        for path in hashes.keys():
                            hashes[path].update(buf)

                for path in hashes.keys():
                    with open(path, 'w') as hash_file:
                        hash_file.write(hashes[path].hexdigest())


        return '/output'

def setup():
    return TarElement
