import shutil
import subprocess
import pytest
from testpath import modified_env

from oommfc.oommf import DockerOOMMFRunner, get_oommf_runner

nonexistant_docker = "docker-executable-name-like-this-doesnt-exist"

def test_exception_is_raised_if_no_docker():
    runner = DockerOOMMFRunner(docker_exe=nonexistant_docker)

    # expect exception as docker executable doesn't exist:
    with pytest.raises(FileNotFoundError):
        runner.call(argstr="+version")

def test_docker_installed_not_running():
    if not shutil.which('docker'):
        pytest.skip('docker command not found')
    status, output = subprocess.getstatusoutput('docker ps')
    if status == 0:
        pytest.skip("Docker appears to be running.")

    # expect "Cannot connect to the Docker daemon. Is the docker
    # daemon running on this host?'"
    assert 'Docker' in output
    assert 'running on this host' in output

    runner = DockerOOMMFRunner()

    with pytest.raises(RuntimeError):
        runner.call(argstr="+version")

def test_no_runner_found():
    # Check that we get EnvironmentError if neither OOMMF nor docker are found
    with modified_env({'OOMMFTCL': None}):
        with pytest.raises(EnvironmentError):
            get_oommf_runner(use_cache=False, docker_exe=nonexistant_docker)