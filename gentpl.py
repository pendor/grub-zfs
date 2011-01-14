#! /usr/bin/python

#
# This is the python script used to generate Makefile.tpl
#

GRUB_PLATFORMS = [ "emu", "i386_pc", "i386_efi", "i386_qemu", "i386_coreboot",
                   "i386_multiboot", "i386_ieee1275", "x86_64_efi",
                   "mips_yeeloong", "mips_qemu_mips", "sparc64_ieee1275",
                   "powerpc_ieee1275" ]

GROUPS = {}

GROUPS["common"]   = GRUB_PLATFORMS[:]

# Groups based on CPU
GROUPS["i386"]     = [ "i386_pc", "i386_efi", "i386_qemu", "i386_coreboot", "i386_multiboot", "i386_ieee1275" ]
GROUPS["x86_64"]   = [ "x86_64_efi" ]
GROUPS["x86"]      = GROUPS["i386"] + GROUPS["x86_64"]
GROUPS["mips"]     = [ "mips_yeeloong", "mips_qemu_mips" ]
GROUPS["sparc64"]  = [ "sparc64_ieee1275" ]
GROUPS["powerpc"]  = [ "powerpc_ieee1275" ]

# Groups based on firmware
GROUPS["x86_efi"]  = [ "i386_efi", "x86_64_efi" ]
GROUPS["ieee1275"]   = [ "i386_ieee1275", "sparc64_ieee1275", "powerpc_ieee1275" ]

# emu is a special case so many core functionality isn't needed on this platform
GROUPS["noemu"]   = GRUB_PLATFORMS[:]; GROUPS["noemu"].remove("emu")

# Groups based on hardware features
GROUPS["cmos"] = GROUPS["x86"][:] + ["mips_yeeloong", "mips_qemu_mips" ]; GROUPS["cmos"].remove("i386_efi"); GROUPS["cmos"].remove("x86_64_efi")
GROUPS["pci"]      = GROUPS["x86"] + ["mips_yeeloong"]
GROUPS["usb"]      = GROUPS["pci"]

# If gfxterm is main output console integrate it into kernel
GROUPS["videoinkernel"] = ["mips_yeeloong"]
GROUPS["videomodules"]   = GRUB_PLATFORMS[:];
for i in GROUPS["videoinkernel"]: GROUPS["videomodules"].remove(i)

# Similar for terminfo
GROUPS["terminfoinkernel"] = ["mips_yeeloong"] + GROUPS["ieee1275"];
GROUPS["terminfomodule"]   = GRUB_PLATFORMS[:];
for i in GROUPS["terminfoinkernel"]: GROUPS["terminfomodule"].remove(i)

# Miscelaneous groups schedulded to disappear in future
GROUPS["nosparc64"] = GRUB_PLATFORMS[:]; GROUPS["nosparc64"].remove("sparc64_ieee1275")
GROUPS["i386_coreboot_multiboot_qemu"] = ["i386_coreboot", "i386_multiboot", "i386_qemu"]
GROUPS["nopc"] = GRUB_PLATFORMS[:]; GROUPS["nopc"].remove("i386_pc")

#
# Create platform => groups reverse map, where groups covering that
# platform are ordered by their sizes
#
RMAP = {}
for platform in GRUB_PLATFORMS:
    # initialize with platform itself as a group
    RMAP[platform] = [ platform ]

    for k in GROUPS.keys():
        v = GROUPS[k]
        # skip groups that don't cover this platform
        if platform not in v: continue

        bigger = []
        smaller = []
        # partition currently known groups based on their size
        for group in RMAP[platform]:
            if group in GRUB_PLATFORMS: smaller.append(group)
            elif len(GROUPS[group]) < len(v): smaller.append(group)
            else: bigger.append(group)
        # insert in the middle
        RMAP[platform] = smaller + [ k ] + bigger

#
# Global variables
#
GVARS = set()

def gvar_add(var, value):
    GVARS.add(var)
    return var + " += " + value + "\n"

def global_variable_initializers():
    r = ""
    for var in sorted(GVARS):
        r += var + " ?= \n"
    return r

#
# Per PROGRAM/SCRIPT variables 
#

def vars_init(*var_list):
    r = "[+ IF (if (not (assoc-ref seen-vars (get \".name\"))) \"seen\") +]"
    r += "[+ (out-suspend \"v\") +]"
    for var in var_list:
        r += var + "  = \n"
    r += "[+ (out-resume \"v\") +]"
    r += "[+ (set! seen-vars (assoc-set! seen-vars (get \".name\") 0)) +]"
    r += "[+ ENDIF +]"
    return first_time(r)

def var_set(var, value):
    return var + "  = " + value + "\n"

def var_add(var, value):
    return var + " += " + value + "\n"

#
# Autogen constructs
#

def set_canonical_name_suffix(suffix): return "[+ % name `export cname=$(echo %s" + suffix + " | sed -e 's/[^0-9A-Za-z@_]/_/g')` +]"
def cname(): return "[+ % name `echo $cname` +]"

def rule(target, source, cmd):
    if cmd[0] == "\n":
        return "\n" + target + ": " + source + cmd.replace("\n", "\n\t") + "\n"
    else:
        return "\n" + target + ": " + source + "\n\t" + cmd.replace("\n", "\n\t") + "\n"

#
# Template for keys with platform names as values, for example:
#
# kernel = {
#   nostrip = emu;
#   ...
# }
#
def if_platform_tagged(platform, tag, snippet_if, snippet_else=None):
    r = ""
    r += "[+ IF " + tag + " defined +]"
    r += "[+ FOR " + tag + " +][+ CASE " + tag + " +]"
    for group in RMAP[platform]:
        r += "[+ = \"" + group + "\" +]" + snippet_if

    if snippet_else != None: r += "[+ * +]" + snippet_else
    r += "[+ ESAC +][+ ENDFOR +]"

    if snippet_else == None:
        r += "[+ ENDIF +]"
        return r

    r += "[+ ELSE +]" + snippet_else + "[+ ENDIF +]"
    return r

#
# Template for tagged values
#
# module = {
#   extra_dist = ...
#   extra_dist = ...
#   ...
# };
#
def foreach_value(tag, closure):
    return "[+ FOR " + tag + " +]" + closure("[+ ." + tag + " +]") + "[+ ENDFOR +]"

#
# Template for handling best matched values for a platform, for example:
#
# module = {
#   cflags = '-Wall';
#   emu_cflags = '-Wall -DGRUB_EMU=1';
#   ...
# }
#
def foreach_platform_specific_value(platform, suffix, nonetag, closure):
    r = ""
    for group in RMAP[platform]:
        gtag = group + suffix

        if group == RMAP[platform][0]:
            r += "[+ IF " + gtag + " +]"
        else:
            r += "[+ ELIF " + gtag + " +]"

        r += "[+ FOR " + gtag + " +]" + closure("[+ ." + gtag + " +]") + "[+ ENDFOR +]"
    r += "[+ ELSE +][+ FOR " + nonetag + " +]" + closure("[+ ." + nonetag + " +]") + "[+ ENDFOR +][+ ENDIF +]"
    return r

#
# Template for handling values from sum of all groups for a platform,
# for example:
#
# module = {
#   common = kern/misc.c;
#   emu = kern/emu/misc.c;
#   ...
# }
#
def foreach_platform_value (platform, suffix, closure):
    r = ""
    for group in RMAP[platform]:
        gtag = group + suffix

        r += "[+ IF " + gtag + " +]"
        r += "[+ FOR " + gtag + " +]" + closure("[+ ." + gtag + " +]") + "[+ ENDFOR +]"
        r += "[+ ENDIF +]"
    return r

#
# Template for gaurding with platform specific "enable" keys, for example:
#
#  module = {
#    name = pci;
#    noemu = bus/pci.c;
#    emu = bus/emu/pci.c;
#    emu = commands/lspci.c;
#
#    enable = emu;
#    enable = i386_pc;
#    enable = x86_efi;
#    enable = i386_ieee1275;
#    enable = i386_coreboot;
#  };
#
def foreach_enabled_platform(closure):
    r = "[+ IF - enable undefined +]"
    for platform in GRUB_PLATFORMS:
        r += "\nif COND_" + platform + "\n" + closure(platform) + "endif\n"
    r += "[+ ELSE +]"
    for platform in GRUB_PLATFORMS:
        x = "\nif COND_" + platform + "\n" + closure(platform) + "endif\n"
        r += if_platform_tagged(platform, "enable", x)
    r += "[+ ENDIF +]"
    return r

#
# Template for gaurding with platform specific automake conditionals,
# for example:
#
#  module = {
#    name = usb;
#    common = bus/usb/usb.c;
#    noemu = bus/usb/usbtrans.c;
#    noemu = bus/usb/usbhub.c;
#    enable = emu;
#    enable = i386;
#    enable = mips_yeeloong;
#    emu_condition = COND_GRUB_EMU_USB;
#  };
#
def under_platform_specific_conditionals(platform, snippet):
    r  = foreach_platform_specific_value(platform, "_condition", "condition", lambda cond: "if " + cond + "\n")
    r += snippet
    r += foreach_platform_specific_value(platform, "_condition", "condition", lambda cond: "endif " + cond + "\n")
    return r

def platform_specific_values(platform, suffix, nonetag):
    return foreach_platform_specific_value(platform, suffix, nonetag,
                                           lambda value: value + " ")

def platform_values(platform, suffix):
    return foreach_platform_value(platform, suffix, lambda value: value + " ")

def extra_dist():
    return foreach_value("extra_dist", lambda value: value + " ")

def platform_sources(p): return platform_values(p, "")
def platform_nodist_sources(p): return platform_values(p, "_nodist")
def platform_dependencies(p): return platform_values(p, "dependencies", "_dependencies")

def platform_startup(p): return platform_specific_values(p, "_startup", "startup")
def platform_ldadd(p): return platform_specific_values(p, "_ldadd", "ldadd")
def platform_cflags(p): return platform_specific_values(p, "_cflags", "cflags")
def platform_ldflags(p): return platform_specific_values(p, "_ldflags", "ldflags")
def platform_cppflags(p): return platform_specific_values(p, "_cppflags", "cppflags")
def platform_ccasflags(p): return platform_specific_values(p, "_ccasflags", "ccasflags")
def platform_stripflags(p): return platform_specific_values(p, "_stripflags", "stripflags")
def platform_objcopyflags(p): return platform_specific_values(p, "_objcopyflags", "objcopyflags")

#
# Emit snippet only the first time through for the current name.
#
def first_time(snippet):
    r = "[+ IF (if (not (assoc-ref seen-target (get \".name\"))) \"seen\") +]"
    r += snippet
    r += "[+ ENDIF +]"
    return r

def module(platform):
    r = set_canonical_name_suffix(".module")

    r += gvar_add("noinst_PROGRAMS", "[+ name +].module")
    r += gvar_add("MODULE_FILES", "[+ name +].module$(EXEEXT)")

    r += var_set(cname() + "_SOURCES", platform_sources(platform) + " ## platform sources")
    r += var_set("nodist_" + cname() + "_SOURCES", platform_nodist_sources(platform) + " ## platform nodist sources")
    r += var_set(cname() + "_LDADD", platform_ldadd(platform))
    r += var_set(cname() + "_CFLAGS", "$(AM_CFLAGS) $(CFLAGS_MODULE) " + platform_cflags(platform))
    r += var_set(cname() + "_LDFLAGS", "$(AM_LDFLAGS) $(LDFLAGS_MODULE) " + platform_ldflags(platform))
    r += var_set(cname() + "_CPPFLAGS", "$(AM_CPPFLAGS) $(CPPFLAGS_MODULE) " + platform_cppflags(platform))
    r += var_set(cname() + "_CCASFLAGS", "$(AM_CCASFLAGS) $(CCASFLAGS_MODULE) " + platform_ccasflags(platform))
    # r += var_set(cname() + "_DEPENDENCIES", platform_dependencies(platform) + " " + platform_ldadd(platform))

    r += gvar_add("EXTRA_DIST", extra_dist())
    r += gvar_add("BUILT_SOURCES", "$(nodist_" + cname() + "_SOURCES)")
    r += gvar_add("CLEANFILES", "$(nodist_" + cname() + "_SOURCES)")

    r += gvar_add("MOD_FILES", "[+ name +].mod")
    r += gvar_add("MARKER_FILES", "[+ name +].marker")
    r += gvar_add("CLEANFILES", "[+ name +].marker")
    r += """
[+ name +].marker: $(""" + cname() + """_SOURCES) $(nodist_""" + cname() + """_SOURCES)
	$(TARGET_CPP) -DGRUB_LST_GENERATOR $(CPPFLAGS_MARKER) $(DEFS) $(DEFAULT_INCLUDES) $(INCLUDES) $(""" + cname() + """_CPPFLAGS) $(CPPFLAGS) $^ > $@.new || (rm -f $@; exit 1)
	grep 'MARKER' $@.new > $@; rm -f $@.new
"""
    return r

def kernel(platform):
    r = set_canonical_name_suffix(".exec")
    r += gvar_add("noinst_PROGRAMS", "[+ name +].exec")
    r += var_set(cname() + "_SOURCES", platform_startup(platform))
    r += var_add(cname() + "_SOURCES", platform_sources(platform))
    r += var_set("nodist_" + cname() + "_SOURCES", platform_nodist_sources(platform) + " ## platform nodist sources")
    r += var_set(cname() + "_LDADD", platform_ldadd(platform))
    r += var_set(cname() + "_CFLAGS", "$(AM_CFLAGS) $(CFLAGS_KERNEL) " + platform_cflags(platform))
    r += var_set(cname() + "_LDFLAGS", "$(AM_LDFLAGS) $(LDFLAGS_KERNEL) " + platform_ldflags(platform))
    r += var_set(cname() + "_CPPFLAGS", "$(AM_CPPFLAGS) $(CPPFLAGS_KERNEL) " + platform_cppflags(platform))
    r += var_set(cname() + "_CCASFLAGS", "$(AM_CCASFLAGS) $(CCASFLAGS_KERNEL) " + platform_ccasflags(platform))
    r += var_set(cname() + "_STRIPFLAGS", "$(AM_STRIPFLAGS) $(STRIPFLAGS_KERNEL) " + platform_stripflags(platform))
    # r += var_set(cname() + "_DEPENDENCIES", platform_dependencies(platform) + " " + platform_ldadd(platform))

    r += gvar_add("EXTRA_DIST", extra_dist())
    r += gvar_add("BUILT_SOURCES", "$(nodist_" + cname() + "_SOURCES)")
    r += gvar_add("CLEANFILES", "$(nodist_" + cname() + "_SOURCES)")

    r += gvar_add("platform_DATA", "[+ name +].img")
    r += gvar_add("CLEANFILES", "[+ name +].img")
    r += rule("[+ name +].img", "[+ name +].exec$(EXEEXT)",
              if_platform_tagged(platform, "nostrip", "cp $< $@",
                                 "$(STRIP) $(" + cname() + "_STRIPFLAGS) -o $@ $<"))
    return r

def image(platform):
    r = set_canonical_name_suffix(".image")
    r += gvar_add("noinst_PROGRAMS", "[+ name +].image")
    r += var_set(cname() + "_SOURCES", platform_sources(platform))
    r += var_set("nodist_" + cname() + "_SOURCES", platform_nodist_sources(platform) + "## platform nodist sources")
    r += var_set(cname() + "_LDADD", platform_ldadd(platform))
    r += var_set(cname() + "_CFLAGS", "$(AM_CFLAGS) $(CFLAGS_IMAGE) " + platform_cflags(platform))
    r += var_set(cname() + "_LDFLAGS", "$(AM_LDFLAGS) $(LDFLAGS_IMAGE) " + platform_ldflags(platform))
    r += var_set(cname() + "_CPPFLAGS", "$(AM_CPPFLAGS) $(CPPFLAGS_IMAGE) " + platform_cppflags(platform))
    r += var_set(cname() + "_CCASFLAGS", "$(AM_CCASFLAGS) $(CCASFLAGS_IMAGE) " + platform_ccasflags(platform))
    r += var_set(cname() + "_OBJCOPYFLAGS", "$(OBJCOPYFLAGS_IMAGE) " + platform_objcopyflags(platform))
    # r += var_set(cname() + "_DEPENDENCIES", platform_dependencies(platform) + " " + platform_ldadd(platform))

    r += gvar_add("EXTRA_DIST", extra_dist())
    r += gvar_add("BUILT_SOURCES", "$(nodist_" + cname() + "_SOURCES)")
    r += gvar_add("CLEANFILES", "$(nodist_" + cname() + "_SOURCES)")

    r += gvar_add("platform_DATA", "[+ name +].img")
    r += gvar_add("CLEANFILES", "[+ name +].img")
    r += rule("[+ name +].img", "[+ name +].image$(EXEEXT)", """
if test x$(USE_APPLE_CC_FIXES) = xyes; then \
  $(MACHO2IMG) $< $@; \
else \
  $(OBJCOPY) $(""" + cname() + """_OBJCOPYFLAGS) --strip-unneeded -R .note -R .comment -R .note.gnu.build-id -R .reginfo -R .rel.dyn $< $@; \
fi
""")
    return r

def library(platform):
    r = set_canonical_name_suffix("")

    r += vars_init(cname() + "_SOURCES",
                   "nodist_" + cname() + "_SOURCES",
                   cname() + "_CFLAGS",
                   cname() + "_CPPFLAGS",
                   cname() + "_CCASFLAGS")
    #              cname() + "_DEPENDENCIES")

    r += first_time(gvar_add("noinst_LIBRARIES", "[+ name +]"))
    r += var_add(cname() + "_SOURCES", platform_sources(platform))
    r += var_add("nodist_" + cname() + "_SOURCES", platform_nodist_sources(platform))
    r += var_add(cname() + "_CFLAGS", first_time("$(AM_CFLAGS) $(CFLAGS_LIBRARY) ") + platform_cflags(platform))
    r += var_add(cname() + "_CPPFLAGS", first_time("$(AM_CPPFLAGS) $(CPPFLAGS_LIBRARY) ") + platform_cppflags(platform))
    r += var_add(cname() + "_CCASFLAGS", first_time("$(AM_CCASFLAGS) $(CCASFLAGS_LIBRARY) ") + platform_ccasflags(platform))
    # r += var_add(cname() + "_DEPENDENCIES", platform_dependencies(platform) + " " + platform_ldadd(platform))

    r += gvar_add("EXTRA_DIST", extra_dist())
    r += first_time(gvar_add("BUILT_SOURCES", "$(nodist_" + cname() + "_SOURCES)"))
    r += first_time(gvar_add("CLEANFILES", "$(nodist_" + cname() + "_SOURCES)"))
    return r

def installdir(default="bin"):
    return "[+ IF installdir +][+ installdir +][+ ELSE +]" + default + "[+ ENDIF +]"

def manpage():
    r  = "if COND_MAN_PAGES\n"
    r += gvar_add("man_MANS", "[+ name +].[+ mansection +]\n")
    r += rule("[+ name +].[+ mansection +]", "[+ name +]", """
chmod a+x [+ name +]
PATH=$(builddir):$$PATH $(HELP2MAN) --section=[+ mansection +] -i $(top_srcdir)/docs/man/[+ name +].h2m -o $@ [+ name +]
""")
    r += gvar_add("CLEANFILES", "[+ name +].[+ mansection +]")
    r += "endif\n"
    return r

def program(platform, test=False):
    r = set_canonical_name_suffix("")

    r += "[+ IF testcase defined +]"
    r += gvar_add("check_PROGRAMS", "[+ name +]")
    r += gvar_add("TESTS", "[+ name +]")
    r += "[+ ELSE +]"
    r += var_add(installdir() + "_PROGRAMS", "[+ name +]")
    r += "[+ IF mansection +]" + manpage() + "[+ ENDIF +]"
    r += "[+ ENDIF +]"

    r += var_set(cname() + "_SOURCES", platform_sources(platform))
    r += var_set("nodist_" + cname() + "_SOURCES", platform_nodist_sources(platform))
    r += var_set(cname() + "_LDADD", platform_ldadd(platform))
    r += var_set(cname() + "_CFLAGS", "$(AM_CFLAGS) $(CFLAGS_PROGRAM) " + platform_cflags(platform))
    r += var_set(cname() + "_LDFLAGS", "$(AM_LDFLAGS) $(LDFLAGS_PROGRAM) " + platform_ldflags(platform))
    r += var_set(cname() + "_CPPFLAGS", "$(AM_CPPFLAGS) $(CPPFLAGS_PROGRAM) " + platform_cppflags(platform))
    r += var_set(cname() + "_CCASFLAGS", "$(AM_CCASFLAGS) $(CCASFLAGS_PROGRAM) " + platform_ccasflags(platform))
    # r += var_set(cname() + "_DEPENDENCIES", platform_dependencies(platform) + " " + platform_ldadd(platform))

    r += gvar_add("EXTRA_DIST", extra_dist())
    r += gvar_add("BUILT_SOURCES", "$(nodist_" + cname() + "_SOURCES)")
    r += gvar_add("CLEANFILES", "$(nodist_" + cname() + "_SOURCES)")
    return r

def data(platform):
    r  = gvar_add("EXTRA_DIST", platform_sources(platform))
    r += gvar_add("EXTRA_DIST", extra_dist())
    r += var_add(installdir() + "_DATA", platform_sources(platform))
    return r

def script(platform):
    r  = "[+ IF testcase defined +]"
    r += gvar_add("check_SCRIPTS", "[+ name +]")
    r += gvar_add ("TESTS", "[+ name +]")
    r += "[+ ELSE +]"
    r += var_add(installdir() + "_SCRIPTS", "[+ name +]")
    r += "[+ IF mansection +]" + manpage() + "[+ ENDIF +]"
    r += "[+ ENDIF +]"

    r += rule("[+ name +]", platform_sources(platform) + " $(top_builddir)/config.status", """
$(top_builddir)/config.status --file=-:$< | sed -e 's,@pkglib_DATA@,$(pkglib_DATA),g' > $@
chmod a+x [+ name +]
""")

    r += gvar_add("CLEANFILES", "[+ name +]")
    r += gvar_add("dist_noinst_DATA", platform_sources(platform))
    return r

def rules(target, closure):
    # Create association lists for the benefit of first_time and vars_init.
    r = "[+ (define seen-target '()) +]"
    r += "[+ (define seen-vars '()) +]"
    # Most output goes to a diversion.  This allows us to emit variable
    # initializations before everything else.
    r += "[+ (out-push-new) +]"

    r += "[+ FOR " + target + " +]"
    r += foreach_enabled_platform(
        lambda p: under_platform_specific_conditionals(p, closure(p)))
    # Remember that we've seen this target.
    r += "[+ (set! seen-target (assoc-set! seen-target (get \".name\") 0)) +]"
    r += "[+ ENDFOR +]"
    r += "[+ (out-pop #t) +]"
    return r

def module_rules():
    return rules("module", module)

def kernel_rules():
    return rules("kernel", kernel)

def image_rules():
    return rules("image", image)

def library_rules():
    return rules("library", library)

def program_rules():
    return rules("program", program)

def script_rules():
    return rules("script", script)

def data_rules():
    return rules("data", data)

print "[+ AutoGen5 template +]\n"
a = module_rules()
b = kernel_rules()
c = image_rules()
d = library_rules()
e = program_rules()
f = script_rules()
g = data_rules()
z = global_variable_initializers()

# print z # initializer for all vars
print a
print b
print c
print d
print e
print f
print g
