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
#  Authors: William Salmon <will.salmon@codethink.co.uk>
#

import os
import pytest
import shutil

from buildstream._exceptions import ErrorDomain
from buildstream import _yaml

from tests.testutils import cli, create_repo

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'project_ref',
)


@pytest.mark.datafiles(DATA_DIR)
def test_build(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    result = cli.run(project=project, args=[
        'build', 'test_element.bst'
    ])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', 'test_element.bst', checkoutdir])
    result.assert_success()
    
    testfile = os.path.join(checkoutdir, "sally", 'sally.hello')
    assert os.path.exists(testfile)
    file1 = os.path.join(testfile)
    with open(file1) as f:
        assert f.read() == "Hello from Sally\n"

@pytest.mark.datafiles(DATA_DIR)
def test_build_file(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    result = cli.run(project=project, args=[
        'build', 'test_file_element.bst'
    ])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', 'test_file_element.bst', checkoutdir])
    result.assert_success()
    
    testfile = str(os.path.join(checkoutdir, 'bob.txt'))
    assert os.path.exists(testfile)
    file1 = os.path.join(testfile)
    with open(file1) as f:
        assert f.read() == "Hi bob\n"

@pytest.mark.datafiles(DATA_DIR)
def test_fetch(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)

    result = cli.run(project=project, args=[
        'fetch', 'test_element.bst'
    ])
    result.assert_success()


@pytest.mark.datafiles(DATA_DIR)
def test_track(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)

    result = cli.run(project=project, args=[
        'track', 'test_file_noref_element.bst'
    ])
    result.assert_success()


@pytest.mark.datafiles(DATA_DIR)
def test_fetch_badref(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    
    file1 = os.path.join(project, "files", "test_element", 'file2')
    with open(file1, 'w') as f:
        f.write('test\n')

    result = cli.run(project=project, args=[
        'build', 'test_element.bst'
    ])
    result.assert_main_error(ErrorDomain.STREAM, None)
