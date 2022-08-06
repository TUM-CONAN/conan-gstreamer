from conans import ConanFile, tools, Meson, VisualStudioBuildEnvironment
from conans.errors import ConanInvalidConfiguration
import glob
import os
import shutil

required_conan_version = ">=1.29"

class GStreamerConan(ConanFile):
    name = "gstreamer"
    _version = "1.21-dev"
    _revision = ""
    version = _version+_revision

    description = "GStreamer is a development framework for creating applications like media players, video editors, streaming media broadcasters and so on"
    topics = ("conan", "gstreamer", "multimedia", "video", "audio", "broadcasting", "framework", "media")
    url = "https://github.com/TUM-CONAN/conan-gstreamer"
    homepage = "https://gstreamer.freedesktop.org/"
    license = "GPL-2.0-only"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libalsa": [True, False],
        "with_libpng": [True, False],
        "with_libjpeg": [False, "libjpeg", "libjpeg-turbo"],
        "with_graphene": [True, False],
        "with_pango": [True, False],
        "with_ogg": [True, False],
        "with_opus": [True, False],
        "with_theora": [True, False],
        "with_vorbis": [True, False],
        "with_gl": [True, False],
        "with_egl": [True, False],
        "with_wayland": [True, False],
        "with_xorg": [True, False],
        "with_avtp": [True, False],
        "with_srtp": [True, False],
        "with_videoparsers": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libalsa": True,
        "with_libpng": True,
        "with_libjpeg": "libjpeg",
        "with_graphene": True,
        "with_pango": True,
        "with_ogg": True,
        "with_opus": True,
        "with_theora": True,
        "with_vorbis": True,
        "with_gl": True,
        "with_egl": True,
        "with_wayland": True,
        "with_xorg": True,
        "with_avtp": False,
        "with_srtp": True,
        "with_videoparsers": True,
        "with_introspection": False,
    }
    generators = "pkg_config"
    _meson = None

    _gl_api = None
    _gl_platform = None
    _gl_winsys = None

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def requirements(self):
        self.requires("zlib/1.2.12")
        self.requires("glib/2.73.0")
        if self.options.get_safe("with_libalsa"):
            self.requires("libalsa/1.2.5.1")
        if self.options.get_safe("with_xorg"):
            self.requires("xorg/system")
        if self.options.with_gl:
            self.requires("opengl/system")
            if self.settings.os == "Windows":
                self.requires("wglext/cci.20200813")
                self.requires('glext/cci.20210420')
            if self.options.get_safe("with_egl"):
                self.requires("egl/system")
            if self.options.get_safe("with_wayland"):
                self.requires("wayland/1.20.0")
                self.requires("wayland-protocols/1.25")
            if self.options.with_graphene:
                self.requires("graphene/1.10.8")
            if self.options.with_libpng:
                self.requires("libpng/1.6.37")
            if self.options.with_libjpeg == "libjpeg":
                self.requires("libjpeg/9d")
            elif self.options.with_libjpeg == "libjpeg-turbo":
                self.requires("libjpeg-turbo/2.1.2")
        if self.options.with_ogg:
            self.requires("ogg/1.3.5")
        if self.options.with_opus:
            self.requires("opus/1.3.1")
        if self.options.with_theora:
            self.requires("theora/1.1.1")
        if self.options.with_vorbis:
            self.requires("vorbis/1.3.7")
        if self.options.with_pango:
            self.requires("pango/1.50.8")
        if self.options.with_srtp:
            self.requires("libsrtp/2.4.2")
        if self.options.with_avtp:
            self.requires("libavtp/0.2.0@camposs/stable")

    @property
    def _is_msvc(self):
        return self.settings.compiler == "Visual Studio"

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_libalsa
            del self.options.with_wayland
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_egl
            del self.options.with_xorg

    def validate(self):
        if not self.options["glib"].shared and self.options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("shared GStreamer cannot link to static GLib")
        if tools.Version(self._version) >= "1.18.2" and\
           self.settings.compiler == "gcc" and\
           tools.Version(self.settings.compiler.version) < "5":
            raise ConanInvalidConfiguration(
                "gst-plugins-base %s does not support gcc older than 5" % self._version
            )
        if self.options.with_gl and self.options.get_safe("with_wayland") and not self.options.get_safe("with_egl"):
            raise ConanInvalidConfiguration("OpenGL support with Wayland requires 'with_egl' turned on!")

    def build_requirements(self):
        self.build_requires("meson/0.61.2")
        self.build_requires("pkgconf/1.7.4")
        if self.options.with_introspection:
            self.build_requires("gobject-introspection/1.72.0")
        if self.settings.os == 'Windows':
            self.build_requires("winflexbison/2.5.24")
        else:
            self.build_requires("bison/3.7.6")
            self.build_requires("flex/2.6.4")

    scm = {
        "type": "git",
        "subfolder": "source_subfolder",
        "url": "https://gitlab.freedesktop.org/gstreamer/gstreamer.git",
        "revision": "main"
     }

    #def source(self):
    #    tools.get("https://gitlab.freedesktop.org/gstreamer/gstreamer/-/archive/{0}/gstreamer-{0}.tar.gz".format(self._version))
    #    os.rename("%s-%s" % (self.name, self._version), self._source_subfolder)

    def _configure_meson(self):
        if self._meson:
            return self._meson

        defs = dict()

        def add_flag(name, value):
            if name in defs:
                defs[name] += " " + value
            else:
                defs[name] = value

        def add_compiler_flag(value):
            add_flag("c_args", value)
            add_flag("cpp_args", value)

        def add_linker_flag(value):
            add_flag("c_link_args", value)
            add_flag("cpp_link_args", value)

        meson = Meson(self)
        if self._is_msvc:
            if tools.Version(self.settings.compiler.version) < "14":
                meson.options["c_args"] = " -Dsnprintf=_snprintf"
                meson.options["cpp_args"] = " -Dsnprintf=_snprintf"
        if self.settings.get_safe("compiler.runtime"):
            meson.options["b_vscrt"] = str(self.settings.compiler.runtime).lower()

        gl_api, gl_platform, gl_winsys = self._gl_config()

        #defs["tools"] = "disabled"
        defs["examples"] = "disabled"
        defs["tests"] = "disabled"
        defs["wrap_mode"] = "nofallback"
        defs["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        defs["orc"] = "disabled" # TODO: orc
        defs["gst-plugins-base:gl"] = "enabled" if self.options.with_gl else "disabled"
        defs["gst-plugins-base:gl-graphene"] = "enabled" if self.options.with_gl and self.options.with_graphene else "disabled"
        defs["gst-plugins-base:gl-png"] = "enabled" if self.options.with_gl and self.options.with_libpng else "disabled"
        defs["gst-plugins-base:gl-jpeg"] = "enabled" if self.options.with_gl and self.options.with_libjpeg else "disabled"
        defs["gst-plugins-base:gl_api"] = gl_api
        defs["gst-plugins-base:gl_platform"] = gl_platform
        defs["gst-plugins-base:gl_winsys"] = gl_winsys
        defs["gst-plugins-base:alsa"] = "enabled" if self.options.get_safe("with_libalsa") else "disabled"
        defs["gst-plugins-base:cdparanoia"] = "disabled" # "enabled" if self.options.with_cdparanoia else "disabled" # TODO: cdparanoia
        defs["gst-plugins-base:libvisual"] = "disabled" # "enabled" if self.options.with_libvisual else "disabled" # TODO: libvisual
        defs["gst-plugins-base:ogg"] = "enabled" if self.options.with_ogg else "disabled"
        defs["gst-plugins-base:opus"] = "enabled" if self.options.with_opus else "disabled"
        defs["gst-plugins-base:pango"] = "enabled" if self.options.with_pango else "disabled"
        defs["gst-plugins-base:theora"] = "enabled" if self.options.with_theora else "disabled"
        defs["gst-plugins-base:tremor"] = "disabled" # "enabled" if self.options.with_tremor else "disabled" # TODO: tremor - only useful on machines without floating-point support
        defs["gst-plugins-base:vorbis"] = "enabled" if self.options.with_vorbis else "disabled"
        defs["gst-plugins-base:x11"] = "enabled" if self.options.get_safe("with_xorg") else "disabled"
        defs["gst-plugins-base:xshm"] = "enabled" if self.options.get_safe("with_xorg") else "disabled"
        defs["gst-plugins-base:xvideo"] = "enabled" if self.options.get_safe("with_xorg") else "disabled"
        defs["gst-plugins-bad:avtp"] = "enabled" if self.options.get_safe("with_avtp") else "disabled"
        defs["gst-plugins-bad:srtp"] = "enabled" if self.options.get_safe("with_srtp") else "disabled"
        defs["gst-plugins-bad:videoparsers"] = "enabled" if self.options.get_safe("with_videoparsers") else "disabled"

        meson.configure(build_folder=self._build_subfolder,
                        source_folder=self._source_subfolder,
                        defs=defs)
        self._meson = meson
        return self._meson

    def _gl_config(self):
        if not self._gl_api or not self._gl_platform or not self._gl_winsys:
            gl_api = set()
            gl_platform = set()
            gl_winsys = set() # TODO: winrt, dispamnx, viv-fb, gbm, android
            if self.options.get_safe("with_egl"):
                gl_api.add("opengl")
                gl_platform.add("egl")
                gl_winsys.add("egl")
            if self.options.get_safe("with_xorg"):
                gl_api.add("opengl")
                gl_platform.add("glx")
                gl_winsys.add("x11")
            if self.options.get_safe("with_wayland"):
                gl_api.add("opengl")
                gl_platform.add("egl")
                gl_winsys.add("wayland")
            if self.settings.os == "Macos":
                gl_api.add("opengl")
                gl_platform.add("cgl")
                gl_winsys.add("cocoa")
            elif self.settings.os in ["iOS", "tvOS", "watchOS"]:
                gl_api.add("gles2")
                gl_platform.add("eagl")
                gl_winsys.add("eagl")
            elif self.settings.os == "Windows":
                gl_api.add("opengl")
                gl_platform.add("wgl")
                gl_winsys.add("win32")
            self._gl_api = list(gl_api)
            self._gl_platform = list(gl_platform)
            self._gl_winsys = list(gl_winsys)
        return self._gl_api, self._gl_platform, self._gl_winsys

    def build(self):
        with tools.environment_append(VisualStudioBuildEnvironment(self).vars) if self._is_msvc else tools.no_op():
            meson = self._configure_meson()
            meson.build()

    def _fix_library_names(self, path):
        # regression in 1.16
        if self.settings.compiler == "Visual Studio":
            with tools.chdir(path):
                for filename_old in glob.glob("*.a"):
                    filename_new = filename_old[3:-2] + ".lib"
                    self.output.info("rename %s into %s" % (filename_old, filename_new))
                    shutil.move(filename_old, filename_new)

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        with tools.environment_append(VisualStudioBuildEnvironment(self).vars) if self._is_msvc else tools.no_op():
            meson = self._configure_meson()
            meson.install()

        self._fix_library_names(os.path.join(self.package_folder, "lib"))
        self._fix_library_names(os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "share"))
        tools.remove_files_by_mask(self.package_folder, "*.pdb")

    def package_id(self):
        self.info.requires["glib"].full_package_mode()

    def package_info(self):
        gst_plugins = []
        gst_plugin_path = os.path.join(self.package_folder, "lib", "gstreamer-1.0")
        gst_include_path = os.path.join(self.package_folder, "include", "gstreamer-1.0")

        pkgconfig_variables = {
            "exec_prefix": "${prefix}",
            "toolsdir": "${exec_prefix}/bin",
            "pluginsdir": "${libdir}/gstreamer-1.0",
            "datarootdir": "${prefix}/share",
            "datadir": "${datarootdir}",
            "girdir": "${datadir}/gir-1.0",
            "typelibdir": "${libdir}/girepository-1.0",
            "libexecdir": "${prefix}/libexec",
            "pluginscannerdir": "${libexecdir}/gstreamer-1.0",
        }
        pkgconfig_custom_content = "\n".join("{}={}".format(key, value) for key, value in pkgconfig_variables.items())

        self.cpp_info.components["gstreamer-1.0"].names["pkg_config"] = "gstreamer-1.0"
        self.cpp_info.components["gstreamer-1.0"].requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        if not self.options.shared:
            self.cpp_info.components["gstreamer-1.0"].requires.append("glib::gmodule-no-export-2.0")
            self.cpp_info.components["gstreamer-1.0"].defines.append("GST_STATIC_COMPILATION")
        self.cpp_info.components["gstreamer-1.0"].libs = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)
                                       
        self.cpp_info.components["gstreamer-base-1.0"].names["pkg_config"] = "gstreamer-base-1.0"
        self.cpp_info.components["gstreamer-base-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-base-1.0"].libs = ["gstbase-1.0"]
        self.cpp_info.components["gstreamer-base-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        self.cpp_info.components["gstreamer-base-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)
                                       
        self.cpp_info.components["gstreamer-controller-1.0"].names["pkg_config"] = "gstreamer-controller-1.0"
        self.cpp_info.components["gstreamer-controller-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-controller-1.0"].libs = ["gstcontroller-1.0"]
        self.cpp_info.components["gstreamer-controller-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-controller-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-controller-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)
                                       
        self.cpp_info.components["gstreamer-net-1.0"].names["pkg_config"] = "gstreamer-net-1.0"
        self.cpp_info.components["gstreamer-net-1.0"].requires = ["gstreamer-1.0", "glib::gio-2.0"]
        self.cpp_info.components["gstreamer-net-1.0"].libs = ["gstnet-1.0"]
        self.cpp_info.components["gstreamer-net-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        self.cpp_info.components["gstreamer-net-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)
                                       
        self.cpp_info.components["gstreamer-check-1.0"].names["pkg_config"] = "gstreamer-check-1.0"
        self.cpp_info.components["gstreamer-check-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-check-1.0"].libs = ["gstcheck-1.0"]
        self.cpp_info.components["gstreamer-check-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-check-1.0"].system_libs = ["rt", "m"]
        self.cpp_info.components["gstreamer-check-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)
                                       
        # gstcoreelements and gstcoretracers are plugins which should be loaded dynamicaly, and not linked to directly
        if not self.options.shared:
            self.cpp_info.components["gstcoreelements"].names["pkg_config"] = "gstcoreelements"
            self.cpp_info.components["gstcoreelements"].requires = ["glib::gobject-2.0", "glib::glib-2.0", "gstreamer-1.0", "gstreamer-base-1.0"]
            self.cpp_info.components["gstcoreelements"].libs = ["gstcoreelements"]
            self.cpp_info.components["gstcoreelements"].includedirs = [os.path.join("include", "gstreamer-1.0")]
            self.cpp_info.components["gstcoreelements"].libdirs = [gst_plugin_path]

            self.cpp_info.components["gstcoretracers"].names["pkg_config"] = "gstcoretracers"
            self.cpp_info.components["gstcoretracers"].requires = ["gstreamer-1.0"]
            self.cpp_info.components["gstcoretracers"].libs = ["gstcoretracers"]
            self.cpp_info.components["gstcoretracers"].includedirs = [os.path.join("include", "gstreamer-1.0")]
            self.cpp_info.components["gstcoretracers"].libdirs = [gst_plugin_path]

        if self.options.shared:
            self.output.info("Appending GST_PLUGIN_PATH env var : %s" % gst_plugin_path)
            self.env_info.GST_PLUGIN_PATH.append(gst_plugin_path)



        # Plugins ('gst')
        self.cpp_info.components["gstadder"].libs = ["gstadder"]
        self.cpp_info.components["gstadder"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstadder"].requires = ["gstreamer-audio-1.0"] # TODO: orc
        gst_plugins.append("gstadder")

        self.cpp_info.components["gstapp"].libs = ["gstapp"]
        self.cpp_info.components["gstapp"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstapp"].requires = ["gstreamer-base-1.0", "gstreamer-app-1.0", "gstreamer-tag-1.0"]
        gst_plugins.append("gstapp")

        self.cpp_info.components["gstaudioconvert"].libs = ["gstaudioconvert"]
        self.cpp_info.components["gstaudioconvert"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstaudioconvert"].requires = ["gstreamer-base-1.0", "gstreamer-audio-1.0"]
        gst_plugins.append("gstaudioconvert")

        self.cpp_info.components["gstaudiomixer"].libs = ["gstaudiomixer"]
        self.cpp_info.components["gstaudiomixer"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstaudiomixer"].requires = ["gstreamer-base-1.0", "gstreamer-audio-1.0"] # TODO: orc
        gst_plugins.append("gstaudiomixer")

        self.cpp_info.components["gstaudiorate"].libs = ["gstaudiorate"]
        self.cpp_info.components["gstaudiorate"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstaudiorate"].requires = ["gstreamer-base-1.0", "gstreamer-audio-1.0"]
        gst_plugins.append("gstaudiorate")

        self.cpp_info.components["gstaudioresample"].libs = ["gstaudioresample"]
        self.cpp_info.components["gstaudioresample"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstaudioresample"].requires = ["gstreamer-base-1.0", "gstreamer-audio-1.0"]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstaudioresample"].system_libs = ["m"]
        gst_plugins.append("gstaudioresample")

        self.cpp_info.components["gstaudiotestsrc"].libs = ["gstaudiotestsrc"]
        self.cpp_info.components["gstaudiotestsrc"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstaudiotestsrc"].requires = ["gstreamer-base-1.0", "gstreamer-audio-1.0"]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstaudiotestsrc"].system_libs = ["m"]
        gst_plugins.append("gstaudiotestsrc")

        self.cpp_info.components["gstcompositor"].libs = ["gstcompositor"]
        self.cpp_info.components["gstcompositor"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstcompositor"].requires = ["gstreamer-base-1.0", "gstreamer-video-1.0"] # TODO: orc
        if self.settings.os == "Linux":
            self.cpp_info.components["gstcompositor"].system_libs = ["m"]
        gst_plugins.append("gstcompositor")

        self.cpp_info.components["gstencoding"].libs = ["gstencoding"]
        self.cpp_info.components["gstencoding"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstencoding"].requires = ["gstreamer-base-1.0", "gstreamer-video-1.0", "gstreamer-pbutils-1.0"]
        gst_plugins.append("gstencoding")

        self.cpp_info.components["gstgio"].libs = ["gstgio"]
        self.cpp_info.components["gstgio"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstgio"].requires = ["gstreamer-base-1.0", "glib::gio-2.0"]
        gst_plugins.append("gstgio")

        self.cpp_info.components["gstoverlaycomposition"].libs = ["gstoverlaycomposition"]
        self.cpp_info.components["gstoverlaycomposition"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstoverlaycomposition"].requires = ["gstreamer-video-1.0"]
        gst_plugins.append("gstoverlaycomposition")

        self.cpp_info.components["gstpbtypes"].libs = ["gstpbtypes"]
        self.cpp_info.components["gstpbtypes"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstpbtypes"].requires = ["gstreamer-video-1.0"]
        gst_plugins.append("gstpbtypes")

        self.cpp_info.components["gstplayback"].libs = ["gstplayback"]
        self.cpp_info.components["gstplayback"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstplayback"].requires = ["gstreamer-audio-1.0", "gstreamer-video-1.0", "gstreamer-pbutils-1.0", "gstreamer-tag-1.0"]
        gst_plugins.append("gstplayback")

        self.cpp_info.components["gstrawparse"].libs = ["gstrawparse"]
        self.cpp_info.components["gstrawparse"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstrawparse"].requires = ["gstreamer-base-1.0", "gstreamer-audio-1.0", "gstreamer-video-1.0"]
        gst_plugins.append("gstrawparse")

        self.cpp_info.components["gstsubparse"].libs = ["gstsubparse"]
        self.cpp_info.components["gstsubparse"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstsubparse"].requires = ["gstreamer-base-1.0"]
        gst_plugins.append("gstsubparse")

        self.cpp_info.components["gsttcp"].libs = ["gsttcp"]
        self.cpp_info.components["gsttcp"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gsttcp"].requires = ["gstreamer-base-1.0", "gstreamer-net-1.0", "glib::gio-2.0"]
        gst_plugins.append("gsttcp")

        self.cpp_info.components["gsttypefindfunctions"].libs = ["gsttypefindfunctions"]
        self.cpp_info.components["gsttypefindfunctions"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gsttypefindfunctions"].requires = ["gstreamer-base-1.0", "gstreamer-pbutils-1.0", "glib::gio-2.0"]
        gst_plugins.append("gsttypefindfunctions")

        self.cpp_info.components["gstvideoconvert"].libs = ["gstvideoconvert"]
        self.cpp_info.components["gstvideoconvert"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstvideoconvert"].requires = ["gstreamer-video-1.0"]
        gst_plugins.append("gstvideoconvert")

        self.cpp_info.components["gstvideorate"].libs = ["gstvideorate"]
        self.cpp_info.components["gstvideorate"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstvideorate"].requires = ["gstreamer-video-1.0"]
        gst_plugins.append("gstvideorate")

        self.cpp_info.components["gstvideoscale"].libs = ["gstvideoscale"]
        self.cpp_info.components["gstvideoscale"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstvideoscale"].requires = [
            "gstreamer-1.0", "gstreamer-base-1.0",
            "gstreamer-video-1.0", "glib::glib-2.0", "glib::gobject-2.0"]
        gst_plugins.append("gstvideoscale")

        self.cpp_info.components["gstvideotestsrc"].libs = ["gstvideotestsrc"]
        self.cpp_info.components["gstvideotestsrc"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstvideotestsrc"].requires = [
            "gstreamer-1.0", "gstreamer-base-1.0",
            "gstreamer-video-1.0", "glib::glib-2.0", "glib::gobject-2.0"] # TODO: orc
        if self.settings.os == "Linux":
            self.cpp_info.components["gstvideotestsrc"].system_libs = ["m"]
        gst_plugins.append("gstvideotestsrc")

        self.cpp_info.components["gstvolume"].libs = ["gstvolume"]
        self.cpp_info.components["gstvolume"].libdirs.append(gst_plugin_path)
        self.cpp_info.components["gstvolume"].requires = [
            "gstreamer-1.0", "gstreamer-base-1.0",
            "gstreamer-audio-1.0", "glib::glib-2.0", "glib::gobject-2.0"] # TODO: orc
        gst_plugins.append("gstvolume")

        # Plugins ('ext')
        if self.options.get_safe("with_libalsa"):
            self.cpp_info.components["gstalsa"].libs = ["gstalsa"]
            self.cpp_info.components["gstalsa"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstalsa"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-audio-1.0", "gstreamer-tag-1.0",
                "libalsa::libalsa", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gstalsa")

        # if self.options.with_cdparanoia: # TODO: cdparanoia
        #     self.cpp_info.components["gstcdparanoia"].libs = ["gstcdparanoia"]
        #     self.cpp_info.components["gstcdparanoia"].libdirs.append(gst_plugin_path)
        #     self.cpp_info.components["gstcdparanoia"].requires = [
        #         "gstreamer-1.0", "gstreamer-base-1.0", "gstreamer-audio-1.0",
        #         "cdparanoia::cdparanoia", "glib::glib-2.0", "glib::gobject-2.0"]
        #     gst_plugins.append("gstcdparanoia")

        if self.options.with_gl:
            self.cpp_info.components["gstopengl"].libs = ["gstopengl"]
            self.cpp_info.components["gstopengl"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstopengl"].requires = [
                "gstreamer-base-1.0", "gstreamer-controller-1.0",
                "gstreamer-video-1.0", "gstreamer-allocators-1.0", "opengl::opengl"] # TODO: bcm, nvbuf_utils
            if self.settings.os == "Macos":
                self.cpp_info.components["gstopengl"].frameworks = ["CoreFoundation", "Foundation", "QuartzCore"]
            if self.options.with_graphene:
                self.cpp_info.components["gstopengl"].requires.append("graphene::graphene-gobject-1.0")
            if self.options.with_libpng:
                self.cpp_info.components["gstopengl"].requires.append("libpng::libpng")
            if self.options.with_libjpeg == "libjpeg":
                self.cpp_info.components["gstopengl"].requires.append("libjpeg::libjpeg")
            elif self.options.with_libjpeg == "libjpeg-turbo":
                self.cpp_info.components["gstopengl"].requires.append("libjpeg-turbo::libjpeg-turbo")
            if self.options.get_safe("with_xorg"):
                self.cpp_info.components["gstopengl"].requires.append("xorg::x11")
            if self.settings.os == "Linux":
                self.cpp_info.components["gstopengl"].system_libs = ["m"]
            gst_plugins.append("gstopengl")

        # if self.options.with_libvisual: # TODO: libvisual
        #     self.cpp_info.components["gstlibvisual"].libs = ["gstlibvisual"]
        #     self.cpp_info.components["gstlibvisual"].libdirs.append(gst_plugin_path)
        #     self.cpp_info.components["gstlibvisual"].requires = [
        #         "gstreamer-1.0", "gstreamer-base-1.0",
        #         "gstreamer-audio-1.0", "gstreamer-video-1.0", "gstreamer-pbutils-1.0",
        #         "libvisual::libvisual", "glib::glib-2.0", "glib::gobject-2.0"]
        #     gst_plugins.append("gstlibvisual")

        if self.options.with_ogg:
            self.cpp_info.components["gstogg"].libs = ["gstogg"]
            self.cpp_info.components["gstogg"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstogg"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-audio-1.0", "gstreamer-pbutils-1.0", "gstreamer-tag-1.0", "gstreamer-riff-1.0",
                "ogg::ogglib", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gstogg")

        if self.options.with_opus:
            self.cpp_info.components["gstopus"].libs = ["gstopus"]
            self.cpp_info.components["gstopus"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstopus"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-audio-1.0", "gstreamer-pbutils-1.0", "gstreamer-tag-1.0",
                "opus::libopus", "glib::glib-2.0", "glib::gobject-2.0"]
            if self.settings.os == "Linux":
                self.cpp_info.components["gstopus"].system_libs = ["m"]
            gst_plugins.append("gstopus")

        if self.options.with_pango:
            self.cpp_info.components["gstpango"].libs = ["gstpango"]
            self.cpp_info.components["gstpango"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstpango"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "pango::pangocairo", "glib::glib-2.0", "glib::gobject-2.0"]
            if self.settings.os == "Linux":
                self.cpp_info.components["gstpango"].system_libs = ["m"]
            gst_plugins.append("gstpango")

        if self.options.with_theora:
            self.cpp_info.components["gsttheora"].libs = ["gsttheora"]
            self.cpp_info.components["gsttheora"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gsttheora"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-video-1.0", "gstreamer-tag-1.0",
                "theora::theoraenc", "theora::theoradec", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gsttheora")

        if self.options.with_vorbis:
            self.cpp_info.components["gstvorbis"].libs = ["gstvorbis"]
            self.cpp_info.components["gstvorbis"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstvorbis"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-audio-1.0", "gstreamer-tag-1.0",
                "vorbis::vorbismain", "vorbis::vorbisenc", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gstvorbis")

        # if self.options.with_tremor: # TODO: tremor
        #     self.cpp_info.components["gstivorbisdec"].libs = ["gstivorbisdec"]
        #     self.cpp_info.components["gstivorbisdec"].libdirs.append(gst_plugin_path)
        #     self.cpp_info.components["gstivorbisdec"].requires = [
        #         "gstreamer-1.0", "gstreamer-base-1.0",
        #         "gstreamer-audio-1.0", "gstreamer-tag-1.0",
        #         "tremor::tremor", "glib::glib-2.0", "glib::gobject-2.0"]
        #     gst_plugins.append("gstivorbisdec")

        if self.options.get_safe("with_avtp"):
            self.cpp_info.components["gstavtp"].libs = ["gstavtp"]
            self.cpp_info.components["gstavtp"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstgstavtp"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "libavtp::libavtp", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gstavtp")

        if self.options.get_safe("with_srtp"):
            self.cpp_info.components["gstsrtp"].libs = ["gstsrtp"]
            self.cpp_info.components["gstsrtp"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstsrtp"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "libsrtp::libsrtp", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gstsrtp")

        # Plugins ('sys')
        if self.options.get_safe("with_xorg"):
            self.cpp_info.components["gstximagesink"].libs = ["gstximagesink"]
            self.cpp_info.components["gstximagesink"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstximagesink"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "xorg::x11", "xorg::xext", "glib::glib-2.0", "glib::gobject-2.0"]
            gst_plugins.append("gstximagesink")

            self.cpp_info.components["gstxvimagesink"].libs = ["gstxvimagesink"]
            self.cpp_info.components["gstxvimagesink"].libdirs.append(gst_plugin_path)
            self.cpp_info.components["gstxvimagesink"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "xorg::x11", "xorg::xext", "xorg::xv", "glib::glib-2.0", "glib::gobject-2.0"]
            if self.settings.os == "Linux":
                self.cpp_info.components["gstxvimagesink"].system_libs = ["m"]
            gst_plugins.append("gstxvimagesink")

        # Libraries
        self.cpp_info.components["gstreamer-plugins-base-1.0"].names["pkg_config"] = "gstreamer-plugins-base-1.0"
        self.cpp_info.components["gstreamer-plugins-base-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-plugins-base-1.0"].includedirs = [gst_include_path]
        if not self.options.shared:
            self.cpp_info.components["gstreamer-plugins-base-1.0"].defines.append("GST_PLUGINS_BASE_STATIC")
            self.cpp_info.components["gstreamer-plugins-base-1.0"].requires.extend(gst_plugins)
        else:
            self.cpp_info.components["gstreamer-plugins-base-1.0"].bindirs.append(gst_plugin_path)
        self.cpp_info.components["gstreamer-plugins-base-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-allocators-1.0"].names["pkg_config"] = "gstreamer-allocators-1.0"
        self.cpp_info.components["gstreamer-allocators-1.0"].libs = ["gstallocators-1.0"]
        self.cpp_info.components["gstreamer-allocators-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-allocators-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-allocators-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-app-1.0"].names["pkg_config"] = "gstreamer-app-1.0"
        self.cpp_info.components["gstreamer-app-1.0"].libs = ["gstapp-1.0"]
        self.cpp_info.components["gstreamer-app-1.0"].requires = ["gstreamer-1.0", "gstreamer-base-1.0"]
        self.cpp_info.components["gstreamer-app-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-app-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-audio-1.0"].names["pkg_config"] = "gstreamer-audio-1.0"
        self.cpp_info.components["gstreamer-audio-1.0"].libs = ["gstaudio-1.0"]
        self.cpp_info.components["gstreamer-audio-1.0"].requires = ["gstreamer-1.0", "gstreamer-base-1.0", "gstreamer-tag-1.0"] # TODO: orc
        self.cpp_info.components["gstreamer-audio-1.0"].includedirs = [gst_include_path]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-audio-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-audio-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-fft-1.0"].names["pkg_config"] = "gstreamer-fft-1.0"
        self.cpp_info.components["gstreamer-fft-1.0"].libs = ["gstfft-1.0"]
        self.cpp_info.components["gstreamer-fft-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-fft-1.0"].includedirs = [gst_include_path]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-fft-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-fft-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        if self.options.with_gl:
            gl_api, gl_platform, gl_winsys = self._gl_config()
            gl_variables = {
                **pkgconfig_variables,
                "gl_apis": " ".join(gl_api),
                "gl_platforms": " ".join(gl_platform),
                "gl_winsys": " ".join(gl_winsys)
            }
            gl_custom_content = "\n".join("{}={}".format(key, value) for key, value in gl_variables.items())

            self.cpp_info.components["gstreamer-gl-1.0"].names["pkg_config"] = "gstreamer-gl-1.0"
            self.cpp_info.components["gstreamer-gl-1.0"].libs = ["gstgl-1.0"]
            self.cpp_info.components["gstreamer-gl-1.0"].requires = [
                "gstreamer-1.0", "gstreamer-base-1.0",
                "gstreamer-allocators-1.0", "gstreamer-video-1.0",
                "glib::gmodule-no-export-2.0", "opengl::opengl"] # TODO: bcm
            if self.options.get_safe("with_egl"):
                self.cpp_info.components["gstreamer-gl-1.0"].requires.extend(["egl::egl"])
            if self.options.get_safe("with_xorg"):
                self.cpp_info.components["gstreamer-gl-1.0"].requires.extend(["xorg::x11", "xorg::x11-xcb"])
            if self.options.get_safe("with_wayland"):
                self.cpp_info.components["gstreamer-gl-1.0"].requires.extend([
                    "wayland::wayland-client", "wayland::wayland-cursor", "wayland::wayland-egl",
                    "wayland-protocols::wayland-protocols"])
            if self.settings.os == "Windows":
                self.cpp_info.components["gstreamer-gl-1.0"].requires.append("wglext::wglext")
                self.cpp_info.components["gstreamer-gl-1.0"].requires.extend(['glext::glext'])
                self.cpp_info.components["gstreamer-gl-1.0"].system_libs = ["gdi32"]
            if self.settings.os in ["Macos", "iOS", "tvOS", "watchOS"]:
                self.cpp_info.components["gstreamer-gl-1.0"].frameworks = ["CoreFoundation", "Foundation", "QuartzCore", "Cocoa"]
            if self.settings.os in ["iOS", "tvOS", "watchOS"]:
                self.cpp_info.components["gstreamer-gl-1.0"].frameworks.extend(["CoreGraphics", "UIkit"])
            self.cpp_info.components["gstreamer-gl-1.0"].includedirs = [os.path.join(self.package_folder, "include"), gst_include_path]
            self.cpp_info.components["gstreamer-gl-1.0"].includedirs.append(os.path.join(gst_plugin_path, "include"))
            self.cpp_info.components["gstreamer-gl-1.0"].set_property("pkg_config_custom_content", gl_custom_content)

            self.cpp_info.components["gstreamer-gl-prototypes-1.0"].names["pkg_config"] = "gstreamer-gl-prototypes-1.0"
            self.cpp_info.components["gstreamer-gl-prototypes-1.0"].requires = ["gstreamer-gl-1.0", "opengl::opengl"]

            if self.options.get_safe("with_egl"):
                self.cpp_info.components["gstreamer-gl-egl-1.0"].names["pkg_config"] = "gstreamer-gl-egl-1.0"
                self.cpp_info.components["gstreamer-gl-egl-1.0"].requires = ["gstreamer-gl-1.0", "egl::egl"]

            if self.options.get_safe("with_wayland"):
                self.cpp_info.components["gstreamer-gl-wayland-1.0"].names["pkg_config"] = "gstreamer-gl-wayland-1.0"
                self.cpp_info.components["gstreamer-gl-wayland-1.0"].requires = [
                    "gstreamer-gl-1.0", "wayland::wayland-client", "wayland::wayland-egl",
                    "wayland-protocols::wayland-protocols"]

            if self.options.get_safe("with_xorg"):
                self.cpp_info.components["gstreamer-gl-x11-1.0"].names["pkg_config"] = "gstreamer-gl-x11-1.0"
                self.cpp_info.components["gstreamer-gl-x11-1.0"].requires = ["gstreamer-gl-1.0", "xorg::x11-xcb"]

        self.cpp_info.components["gstreamer-pbutils-1.0"].names["pkg_config"] = "gstreamer-pbutils-1.0"
        self.cpp_info.components["gstreamer-pbutils-1.0"].libs = ["gstpbutils-1.0"]
        self.cpp_info.components["gstreamer-pbutils-1.0"].requires = [
            "gstreamer-1.0", "gstreamer-base-1.0",
            "gstreamer-audio-1.0", "gstreamer-video-1.0", "gstreamer-tag-1.0"]
        self.cpp_info.components["gstreamer-pbutils-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-pbutils-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-riff-1.0"].names["pkg_config"] = "gstreamer-riff-1.0"
        self.cpp_info.components["gstreamer-riff-1.0"].libs = ["gstriff-1.0"]
        self.cpp_info.components["gstreamer-riff-1.0"].requires = ["gstreamer-1.0", "gstreamer-audio-1.0", "gstreamer-tag-1.0"]
        self.cpp_info.components["gstreamer-riff-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-riff-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-rtp-1.0"].names["pkg_config"] = "gstreamer-rtp-1.0"
        self.cpp_info.components["gstreamer-rtp-1.0"].libs = ["gstrtp-1.0"]
        self.cpp_info.components["gstreamer-rtp-1.0"].requires = ["gstreamer-1.0", "gstreamer-base-1.0", "gstreamer-audio-1.0"]
        self.cpp_info.components["gstreamer-rtp-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-rtp-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-rtsp-1.0"].names["pkg_config"] = "gstreamer-rtsp-1.0"
        self.cpp_info.components["gstreamer-rtsp-1.0"].libs = ["gstrtsp-1.0"]
        self.cpp_info.components["gstreamer-rtsp-1.0"].requires = [
            "gstreamer-1.0", "gstreamer-base-1.0",
            "gstreamer-sdp-1.0", "glib::gio-2.0"]

        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-rtsp-1.0"].system_libs = ["m"]
        elif self.settings.os == "Windows":
            self.cpp_info.components["gstreamer-rtsp-1.0"].system_libs = ["ws2_32"]
        self.cpp_info.components["gstreamer-rtsp-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-rtsp-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-rtspserver-1.0"].names["pkg_config"] = "gstreamer-rtspserver-1.0"
        self.cpp_info.components["gstreamer-rtspserver-1.0"].libs = ["gstrtspserver-1.0"]
        self.cpp_info.components["gstreamer-rtspserver-1.0"].requires = [
            "gstreamer-1.0", "gstreamer-base-1.0",
            "gstreamer-sdp-1.0", "glib::gio-2.0", "gstreamer-rtp-1.0"]
        self.cpp_info.components["gstreamer-rtspserver-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-rtspserver-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-sdp-1.0"].names["pkg_config"] = "gstreamer-sdp-1.0"
        self.cpp_info.components["gstreamer-sdp-1.0"].libs = ["gstsdp-1.0"]
        self.cpp_info.components["gstreamer-sdp-1.0"].requires = ["gstreamer-1.0", "gstreamer-rtp-1.0", "glib::glib-2.0", "glib::gio-2.0"]
        self.cpp_info.components["gstreamer-sdp-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-sdp-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-tag-1.0"].names["pkg_config"] = "gstreamer-tag-1.0"
        self.cpp_info.components["gstreamer-tag-1.0"].libs = ["gsttag-1.0"]
        self.cpp_info.components["gstreamer-tag-1.0"].requires = ["gstreamer-1.0", "gstreamer-base-1.0", "zlib::zlib"]

        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-tag-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-tag-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-tag-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-video-1.0"].names["pkg_config"] = "gstreamer-video-1.0"
        self.cpp_info.components["gstreamer-video-1.0"].libs = ["gstvideo-1.0"]
        self.cpp_info.components["gstreamer-video-1.0"].requires = ["gstreamer-1.0", "gstreamer-base-1.0"] # TODO: orc
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-video-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-video-1.0"].includedirs = [gst_include_path]
        self.cpp_info.components["gstreamer-video-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)



        gstreamer_root = self.package_folder
        self.output.info("Creating GSTREAMER_ROOT env var : %s" % gstreamer_root)
        self.env_info.GSTREAMER_ROOT = gstreamer_root
        gst_plugin_scanner = "gst-plugin-scanner.exe" if self.settings.os == "Windows" else "gst-plugin-scanner"
        gst_plugin_scanner = os.path.join(self.package_folder, "bin", "gstreamer-1.0", gst_plugin_scanner)
        self.output.info("Creating GST_PLUGIN_SCANNER env var : %s" % gst_plugin_scanner)
        self.env_info.GST_PLUGIN_SCANNER = gst_plugin_scanner
        if self.settings.arch == "x86":
            self.output.info("Creating GSTREAMER_ROOT_X86 env var : %s" % gstreamer_root)
            self.env_info.GSTREAMER_ROOT_X86 = gstreamer_root
        elif self.settings.arch == "x86_64":
            self.output.info("Creating GSTREAMER_ROOT_X86_64 env var : %s" % gstreamer_root)
            self.env_info.GSTREAMER_ROOT_X86_64 = gstreamer_root
