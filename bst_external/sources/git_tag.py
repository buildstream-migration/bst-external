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
git-tag - extension of BuildStream git plugin to track latest tag
=================================================================

**Host dependencies**

  * git

**Usage:**

.. code:: yaml

   # Specify the git_tag source kind
   kind: git_tag

   # Optionally specify a relative staging directory
   # directory: path/to/stage

   # Specify the repository url, using an alias defined
   # in your project configuration is recommended
   url: upstream:foo.git

   # Optionally specify a symbolic tracking branch or tag, this
   # will be used to update the 'ref' when refreshing the pipeline.
   track: master

   # Optionally specify an additional branch to be tracked, the plugin
   # will compare the latest tags for each branch and track to the
   # overall latest. This is intended to keep to the latest stable
   # branch, but then switch when a new major release appears
   track-alt:

   # Optionally specify to track the latest tag of a branch,
   # rather than the latest commit when updating 'ref'.
   # If not set, this will default to 'False'
   track-tags: False

   # Specify the commit ref, this must be specified in order to
   # checkout sources and build, but can be automatically updated
   # if the 'track' attribute was specified.
   ref: d63cbb6fdc0bbdadc4a1b92284826a6d63a7ebcd

   # Optionally specify whether submodules should be checked-out.
   # If not set, this will default to 'True'
   checkout-submodules: True

   # If your repository has submodules, explicitly specifying the
   # url from which they are to be fetched allows you to easily
   # rebuild the same sources from a different location. This is
   # especially handy when used with project defined aliases which
   # can be redefined at a later time.
   # You may also explicitly specify whether to check out this
   # submodule. If checkout is set, it will override
   # 'checkout-submodules' with the value set below.
   submodules:
     plugins/bar:
       url: upstream:bar.git
       checkout: True
     plugins/baz:
       url: upstream:baz.git
       checkout: False

"""

import os
import buildstream
from buildstream import Source
from collections import Mapping
import importlib.util
gitplugin_src = os.path.join(os.path.dirname(buildstream.__file__), "plugins", "sources", "git.py")
gitplugin_spec = importlib.util.spec_from_file_location(".git", gitplugin_src)
gitplugin = importlib.util.module_from_spec(gitplugin_spec)
gitplugin_spec.loader.exec_module(gitplugin)
GitMirror = gitplugin.GitMirror
GitSource = gitplugin.GitSource

class GitTagMirror(GitMirror):
    def latest_commit(self, tracking, *, track_tags):
        if track_tags:
            exit_code, output = self.source.check_output(
                [self.source.host_git, 'describe', '--tags', '--abbrev=0', tracking],
                cwd=self.mirror)

            if exit_code == 128:
                self.source.info("Unable to find tag for specified branch name '{}'".format(tracking))
                _, output = self.source.check_output(
                        [self.source.host_git, 'rev-parse', tracking],
                        fail="Unable to find commit for specified branch name '{}'".format(tracking),
                        cwd=self.mirror)
            tracking = output.rstrip('\n')

        _, output = self.source.check_output(
            [self.source.host_git, 'rev-parse', tracking],
            fail="Unable to find commit for specified branch name '{}'".format(tracking),
            cwd=self.mirror)
        ref = output.rstrip('\n')

        _, time = self.source.check_output(
                [self.source.host_git, 'show', '-s', '--format=%ct', ref],
                cwd=self.mirror)

        # Prefix the ref with the closest annotated tag, if available,
        # to make the ref human readable
        exit_code, output = self.source.check_output(
            [self.source.host_git, 'describe', '--tags', '--abbrev=40', '--long', ref],
            cwd=self.mirror)
        if exit_code == 0:
            ref = output.rstrip('\n')

        return ref, time


class GitTagSource(GitSource):

    def configure(self, node):
        ref = self.node_get_member(node, str, 'ref', '') or None

        config_keys = ['url', 'track', 'track-alt', 'track-tags', 'ref', 'submodules', 'checkout-submodules']
        self.node_validate(node, config_keys + Source.COMMON_CONFIG_KEYS)

        self.original_url = self.node_get_member(node, str, 'url')
        self.mirror = GitTagMirror(self, '', self.original_url, ref, primary=True)
        self.tracking = self.node_get_member(node, str, 'track', None)
        self.alt_tracking = self.node_get_member(node, str, 'track-alt', None)
        self.track_tags = self.node_get_member(node, bool, 'track-tags', False)

        # At this point we now know if the source has a ref and/or a track.
        # If it is missing both then we will be unable to track or build.
        if self.mirror.ref is None and self.tracking is None:
            raise SourceError("{}: Git sources require a ref and/or track".format(self),
                              reason="missing-track-and-ref")

        self.checkout_submodules = self.node_get_member(node, bool, 'checkout-submodules', True)
        self.submodules = []

        # Parse a dict of submodule overrides, stored in the submodule_overrides
        # and submodule_checkout_overrides dictionaries.
        self.submodule_overrides = {}
        self.submodule_checkout_overrides = {}
        modules = self.node_get_member(node, Mapping, 'submodules', {})
        for path, _ in self.node_items(modules):
            submodule = self.node_get_member(modules, Mapping, path)
            url = self.node_get_member(submodule, str, 'url', '') or None

            # Make sure to mark all URLs that are specified in the configuration
            if url:
                self.mark_download_url(url, primary=False)

            self.submodule_overrides[path] = url
            if 'checkout' in submodule:
                checkout = self.node_get_member(submodule, bool, 'checkout')
                self.submodule_checkout_overrides[path] = checkout

        self.mark_download_url(self.original_url)

    def track(self):

        # If self.tracking is not specified it's not an error, just silently return
        if not self.tracking:
            return None

        # Resolve the URL for the message
        resolved_url = self.translate_url(self.mirror.url)
        with self.timed_activity("Tracking {} from {}"
                                 .format(self.tracking, resolved_url),
                                 silent_nested=True):
            self.mirror.ensure()
            self.mirror.fetch()

            # Update self.mirror.ref and node.ref from the self.tracking branch
            ret, time = self.mirror.latest_commit(self.tracking, track_tags=self.track_tags)
            if self.track_tags and self.alt_tracking != None:
                alt_ret, alt_time = self.mirror.latest_commit(self.alt_tracking, track_tags=self.track_tags)

                if alt_time > time:
                    ret = alt_ret

        return ret

def setup():
    return GitTagSource
