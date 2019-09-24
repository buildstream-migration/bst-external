# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name

import os
import tarfile

import pytest

from .testutils.integration import assert_contains
from .testutils.runcli import cli_integration as cli  # pylint: disable=unused-import

pytestmark = pytest.mark.integration

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)


BLOCKSIZE = 65536


@pytest.mark.datafiles(DATA_DIR)
def test_tar_build(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    tarpath = os.path.join(checkout_dir, 'hello.tar.gz')
    element_name = 'tar/tar-test.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', element_name, checkout_dir])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz"])

    tar_hello = tarfile.open(tarpath)
    contents = set(tar_hello.getnames())
    assert contents == {'hello.c', 'Makefile', 'series', 'test'}


@pytest.mark.datafiles(DATA_DIR)
def test_tar_include(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    tarpath = os.path.join(checkout_dir, 'hello.tar.gz')
    element_name = 'tar/tar-test-include.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', element_name, checkout_dir])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz"])

    tar_hello = tarfile.open(tarpath)
    contents = set(tar_hello.getnames())
    assert contents == {'hello.c', 'Makefile'}


@pytest.mark.datafiles(DATA_DIR)
def test_tar_exclude(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    tarpath = os.path.join(checkout_dir, 'hello.tar.gz')
    element_name = 'tar/tar-test-exclude.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', element_name, checkout_dir])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz"])

    tar_hello = tarfile.open(tarpath)
    contents = set(tar_hello.getnames())
    assert contents == {'hello.c', 'Makefile'}


@pytest.mark.datafiles(DATA_DIR)
def test_tar_orphans(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    tarpath = os.path.join(checkout_dir, 'hello.tar.gz')
    element_name = 'tar/tar-test-orphans.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', element_name, checkout_dir])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz"])

    tar_hello = tarfile.open(tarpath)
    contents = set(tar_hello.getnames())
    assert contents == {'hello.c'}
