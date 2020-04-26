import os

from conans import ConanFile, Meson, tools

class GStreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.16.2"
    description = "A framework for streaming media"
    license = "LGPL"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "introspection": [True, False],
        "check": [True, False],
        "tools": [True, False],
    }
    default_options = (
        "introspection=True",
        "check=True",
        "tools=True",
    )

    generators = "pkgconf"

    # def set_version(self):
    #     git = tools.Git(folder=self.recipe_folder)
    #     tag, branch = git.get_tag(), git.get_branch()
    #     self.version = tag if tag and branch.startswith("HEAD") else branch

    def build_requirements(self):
        self.build_requires("generators/1.0.0@camposs/stable")
        self.build_requires("meson/[>=0.51.2]@camposs/stable")
        self.build_requires("pkgconf/1.6.3@camposs/stable")
        if self.options.introspection:
            self.build_requires("gobject-introspection/[>=1.59.3]@camposs/stable")

    def requirements(self):
        self.requires("glib/[>=2.62.0]@camposs/stable")

    def source(self):
        git = tools.Git(folder="%s-%s" % (self.name, self.version))
        git.clone(url="https://gitlab.freedesktop.org/gstreamer/gstreamer.git", branch=self.version, shallow=True)

    def build(self):
        pkg_config_paths = []
        if "PKG_CONFIG_PATH" in os.environ:
            pkg_config_paths.extend(os.environ["PKG_CONFIG_PATH"].split(":"))
        pkg_config_paths.append(self.build_folder)

        args = ["--auto-features=disabled"]
        args.append("-Dintrospection=" + ("enabled" if self.options.introspection else "disabled"))
        args.append("-Dcheck=" + ("enabled" if self.options.check else "disabled"))
        args.append("-Dtools=" + ("enabled" if self.options.tools else "disabled"))
        meson = Meson(self)
        meson.configure(source_folder="%s-%s" % (self.name, self.version), args=args, pkg_config_paths=pkg_config_paths)
        meson.install()

    def package_info(self):
        self.env_info.GST_PLUGIN_PATH.append(os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        self.env_info.GST_PLUGIN_SCANNER = os.path.join(self.package_folder, "bin", "gstreamer-1.0", "gst-plugin-scanner")
        self.env_info.GI_TYPELIB_PATH.append(os.path.join(self.package_folder, "lib", "girepository-1.0"))
