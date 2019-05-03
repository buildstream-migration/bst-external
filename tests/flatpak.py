import os
import pytest

from tests.testutils import cli_integration as cli
from tests.testutils.integration import assert_contains
from tests.testutils.site import IS_LINUX

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_flatpak_runtime_build(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(cli.directory, 'runtime_checkout')

    result = cli.run(project=project, args=['build',
        "flatpak/flatpak-runtime.bst"])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', '--hardlinks',
        "flatpak/flatpak-runtime.bst", checkout])
    result.assert_success()

    # Check existence of metadata, files and a binary in the image
    assert_contains(checkout, ['/metadata', '/files', '/files/bin/gcc'])

@pytest.mark.datafiles(DATA_DIR)
def test_flatpak_app_build(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(cli.directory, 'app_checkout')

    result = cli.run(project=project, args=['build',
        "flatpak/flatpak-application.bst"])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', '--hardlinks',
        "flatpak/flatpak-application.bst", checkout])
    result.assert_success()

    # Check existence of metadata, files and the application binary
    assert_contains(checkout, ['/metadata', '/files', '/files/bin/hello'])

@pytest.mark.datafiles(DATA_DIR)
@pytest.mark.skipif(not IS_LINUX, reason="Unrelated breakages when not sandboxed")
def test_flatpak_repo_build(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(cli.directory, 'repo_checkout')

    result = cli.run(project=project, args=['build', 'flatpak-repo.bst'])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', '--hardlinks', "flatpak-repo.bst",
        checkout])
    result.assert_success()

    assert_contains(checkout, ['/config', '/extensions', '/objects', '/refs',
        '/state', '/summary'])
