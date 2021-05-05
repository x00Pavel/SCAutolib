import logging
from os.path import (exists, realpath, isdir,
                     isfile, dirname, abspath)
from os import mkdir
import click
import yaml
import subprocess as subp
from shutil import copytree
from re import match
import SCAutolib.src.utils as utils

log = logging.getLogger("env")

# TODO add docs about parameters
DIR_PATH = dirname(abspath(__file__))
SETUP_CA = f"{DIR_PATH}/env/setup_ca.sh"
SETUP_VSC = f"{DIR_PATH}/env/setup_virt_card.sh"
CLEANUP_CA = f"{DIR_PATH}/env/cleanup_ca.sh"
TMP = f"{DIR_PATH}/tmp"
KEYS = f"{TMP}/keys"
CERTS = f"{TMP}/certs"
BACKUP = f"{TMP}/backup"


@click.group()
def cli():
    pass


def _prep_tmp_dirs():
    if not exists(TMP):
        mkdir(TMP)
    if not exists(KEYS):
        mkdir(KEYS)
    if not exists(CERTS):
        mkdir(CERTS)
    if not exists(BACKUP):
        mkdir(BACKUP)


def _create_sssd_conf(username="localuser1"):
    holder = "#<{holder}>\n"
    content = []
    if exists("/etc/sssd/sssd.conf"):
        utils._backup("/etc/sssd/sssd.conf", name="sssd-original.conf")

        with open("/etc/sssd/sssd.conf", "r") as f:
            content = f.readlines()
        for index, line in enumerate(content):
            if match(r"^\[(.*)]\n$", line):
                content[index] = line + holder.format(holder=line.rstrip("\n"))
    #     TODO: add mathrule for testing user
    else:
        content = ["[sssd]\n",
                   "debug_level = 9\n",
                   "services = nss, pam\n",
                   "domains = shadowutils\n",
                   "#<[sssd]>\n",
                   "\n[nss]\n",
                   "debug_level = 9\n",
                   "#<[nss]>\n",
                   "\n[pam]\n",
                   "debug_level = 9\n",
                   "pam_cert_auth = True\n",
                   "#<[pam]>\n",

                   "\n[domain/shadowutils]\n",
                   "debug_level = 9\n",
                   "id_provider = files\n",
                   "#<[domain/shadowutils]>\n",

                   f"\n[certmap/shadowutils/{username}]\n",
                   f"matchrule = < SUBJECT >.*CN = {username}.*\n",
                   f"#<[certmap/shadowutils/{username}]>\n"]

    with open("/etc/sssd/sssd.conf", "w") as f:
        f.write("".join(content))


def _create_softhsm2_conf():
    pass


@click.command()
@click.option("--username", "-u", type=click.STRING, help="Username to be set in config files (e.g sssd.conf)")
def prepair(username):
    _prep_tmp_dirs()

    _create_sssd_conf(username)
    # TODO: create softhsm2.conf file
    _create_softhsm2_conf()
    # TODO: create .cnf files for certificates

    # TODO: create virtcacard.cil

    # TODO: creata virt_cacard.service


@click.command()
@click.option("--work-dir", "-p", type=click.Path(), help="Path to working directory")
@click.option("--conf", "-c", type=click.Path(), help="Path to YAML file with configurations")
def setup_ca(work_dir, conf):
    """
    Setup local CA

    :param work_dir: Path to working directory
    :param conf: Path to YAML file with configurations
    """
    assert exists(work_dir), f"Path {work_dir} is not exist"
    assert isdir(work_dir), f"{work_dir} is not a directory"
    assert exists(realpath(conf)), f"File {conf} is not exist"
    assert isfile(realpath(conf)), f"{conf} is not a file"

    log.debug("Start setup of local CA")

    with open(conf, "r") as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    conf_dir = f"{work_dir}/conf"
    copytree(realpath(data["configs"]["dir"]), conf_dir)
    user = data["variables"]["user"]
    print(work_dir)
    out = subp.run(["bash", SETUP_CA, "--dir", work_dir,
                    "--username", user["name"],
                    "--userpasswd", user["passwd"],
                    "--pin", user["pin"],
                    "--conf-dir", conf_dir])
    assert out.returncode == 0, "Something break in setup playbook :("
    log.debug("Setup of local CA is completed")


@click.command()
@click.option("--conf-dir", "-C", type=click.Path(), help="Directory with configuration files")
@click.option("--work-dir", "-w", type=click.Path(), help="Working directory")
def setup_virt_card(conf_dir, work_dir):
    """
    Setup virtual smart card. Has to be run after configuration of the local CA.

    :param conf_dir: Directory with configuration files
    :param work_dir: Working directory
    """
    assert exists(conf_dir), f"Path {conf_dir} is not exist"
    assert isdir(conf_dir), f"{conf_dir} Not a directory"
    assert exists(work_dir), f"Path {work_dir} is not exist"
    assert isdir(work_dir), f"{work_dir} Not a directory"

    log.debug("Start setup of local CA")
    out = subp.run(["bash", SETUP_VSC, "-c", conf_dir, "-w", work_dir])

    assert out.returncode == 0, "Something break in setup playbook :("
    log.debug("Setup of local CA is completed")


@click.command()
@click.option("--conf", "-c", type=click.Path(), help="Path to YAML file with configurations")
def cleanup_ca(conf):
    """
    Cleanup the host after configuration of the testing environment.
    """
    log.debug("Start cleanup of local CA")
    with open(conf, "r") as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    username = data["variables"]["user"]["name"]
    out = subp.run(
        ["bash", CLEANUP_CA, "--username", username])

    assert out.returncode == 0, "Something break in setup script :("
    log.debug("Cleanup of local CA is completed")


cli.add_command(setup_ca)
cli.add_command(setup_virt_card)
cli.add_command(cleanup_ca)
cli.add_command(prepair)

if __name__ == "__main__":
    cli()
