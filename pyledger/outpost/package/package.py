
import os
import subprocess

from pyledger.outpost.scm import scm_create
from pyledger.outpost.utils import working_directory_attr

class Package():
    def __init__(self, name, parent_project, config_node: dict) -> None:
        self._name = name
        self._parent = parent_project
        self._config = config_node
        self._scm = scmCreate(self)

    @property
    def name(self) -> str:
        return self._name

    @property
    def sourcedir(self) -> str:
        return os.path.join(self._parent.sourcedir, self.name)

    @property
    def builddir(self) -> str:
        return os.path.join(self._parent.builddir, self.name)

    @property
    def stagingdir(self) -> str:
        return self._parent.stagingdir

    @property
    def parent(self):
        return self._parent

    @property
    def deps(self):
        # XXX sanity checks
        return self._config["deps"] if "deps" in self._config else list()

    @property
    def build_opts(self):
        build_opts = list()
        build_opts.append(f"-Dconfig={self._config['config_file']}")
        build_opts.append(self._config["build_opts"] if "build_opts" in self._config else list())
        return build_opts

    def download(self) -> None:
        self._scm.download()

    def update(self) -> None:
        self._scm.update()

    def __getattr__(self, attr):
        return self._config[attr] if attr in self._config else None

    @working_directory_attr("sourcedir")
    def post_download_hook(self):
        subprocess.run(["meson", "subprojects", "download"])

    @working_directory_attr("sourcedir")
    def post_update_hook(self):
        subprocess.run(["meson", "subprojects", "download"])
        subprocess.run(["meson", "subprojects", "update"])
