/*
 *  GRUB  --  GRand Unified Bootloader
 *  Copyright (C) 2003,2004,2005,2006,2007,2008,2009,2010  Free Software Foundation, Inc.
 *
 *  GRUB is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  GRUB is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with GRUB.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>
#include <sys/stat.h>
#include <string.h>
#include <signal.h>
#include <sys/types.h>
#include <unistd.h>

#include <grub/dl.h>
#include <grub/mm.h>
#include <grub/setjmp.h>
#include <grub/fs.h>
#include <grub/emu/hostdisk.h>
#include <grub/time.h>
#include <grub/emu/console.h>
#include <grub/emu/misc.h>
#include <grub/kernel.h>
#include <grub/normal.h>
#include <grub/emu/getroot.h>
#include <grub/env.h>
#include <grub/partition.h>
#include <grub/i18n.h>

#include "progname.h"

#define ENABLE_RELOCATABLE 0

/* Used for going back to the main function.  */
static jmp_buf main_env;

/* Store the prefix specified by an argument.  */
static char *root_dev = NULL, *dir = NULL;

int grub_no_autoload;

grub_addr_t
grub_arch_modules_addr (void)
{
  return 0;
}

void
grub_reboot (void)
{
  longjmp (main_env, 1);
}

void
grub_machine_init (void)
{
}

void
grub_machine_get_bootlocation (char **device, char **path)
{
  *device = root_dev;
  *path = dir;
}

void
grub_machine_fini (void)
{
  grub_console_fini ();
}

char grub_prefix[64] = "";



static struct option options[] =
  {
    {"root-device", required_argument, 0, 'r'},
    {"device-map", required_argument, 0, 'm'},
    {"directory", required_argument, 0, 'd'},
    {"hold", optional_argument, 0, 'H'},
    {"help", no_argument, 0, 'h'},
    {"version", no_argument, 0, 'V'},
    {"verbose", no_argument, 0, 'v'},
    { 0, 0, 0, 0 }
  };

static int
usage (int status)
{
  if (status)
    fprintf (stderr,
	     "Try `%s --help' for more information.\n", program_name);
  else
    printf (
      "Usage: %s [OPTION]...\n"
      "\n"
      "GRUB emulator.\n"
      "\n"
      "  -r, --root-device=DEV     use DEV as the root device [default=host]\n"
      "  -m, --device-map=FILE     use FILE as the device map [default=%s]\n"
      "  -d, --directory=DIR       use GRUB files in the directory DIR [default=%s]\n"
      "  -v, --verbose             print verbose messages\n"
      "  -H, --hold[=SECONDS]      wait until a debugger will attach\n"
      "  -h, --help                display this message and exit\n"
      "  -V, --version             print version information and exit\n"
      "\n"
      "Report bugs to <%s>.\n", program_name, DEFAULT_DEVICE_MAP, DEFAULT_DIRECTORY, PACKAGE_BUGREPORT);
  return status;
}


void grub_hostfs_init (void);
void grub_hostfs_fini (void);
void grub_host_init (void);
void grub_host_fini (void);
void grub_emu_init (void);

int
main (int argc, char *argv[])
{
  char *dev_map = DEFAULT_DEVICE_MAP;
  volatile int hold = 0;
  int opt;

  set_program_name (argv[0]);

  dir = xstrdup (DEFAULT_DIRECTORY);

  while ((opt = getopt_long (argc, argv, "r:d:m:vH:hV", options, 0)) != -1)
    switch (opt)
      {
      case 'r':
	free (root_dev);
        root_dev = xstrdup (optarg);
        break;
      case 'd':
	free (dir);
        dir = xstrdup (optarg);
        break;
      case 'm':
        dev_map = optarg;
        break;
      case 'v':
        verbosity++;
        break;
      case 'H':
        hold = (optarg ? atoi (optarg) : -1);
        break;
      case 'h':
        return usage (0);
      case 'V':
        printf ("%s (%s) %s\n", program_name, PACKAGE_NAME, PACKAGE_VERSION);
        return 0;
      default:
        return usage (1);
      }

  if (optind < argc)
    {
      fprintf (stderr, "Unknown extra argument `%s'.\n", argv[optind]);
      return usage (1);
    }

  /* Wait until the ARGS.HOLD variable is cleared by an attached debugger. */
  if (hold && verbosity > 0)
    printf ("Run \"gdb %s %d\", and set ARGS.HOLD to zero.\n",
            program_name, (int) getpid ());
  while (hold)
    {
      if (hold > 0)
        hold--;

      sleep (1);
    }

  signal (SIGINT, SIG_IGN);
  grub_emu_init ();
  grub_console_init ();
  grub_host_init ();

  /* XXX: This is a bit unportable.  */
  grub_util_biosdisk_init (dev_map);

  grub_init_all ();

  grub_hostfs_init ();

  grub_emu_post_init ();

  /* Make sure that there is a root device.  */
  if (! root_dev)
    root_dev = grub_strdup ("host");

  dir = xstrdup (dir);

  /* Start GRUB!  */
  if (setjmp (main_env) == 0)
    grub_main ();

  grub_fini_all ();
  grub_hostfs_fini ();
  grub_host_fini ();

  grub_machine_fini ();

  return 0;
}

#ifdef __MINGW32__

void
grub_millisleep (grub_uint32_t ms)
{
  Sleep (ms);
}

#else

void
grub_millisleep (grub_uint32_t ms)
{
  struct timespec ts;

  ts.tv_sec = ms / 1000;
  ts.tv_nsec = (ms % 1000) * 1000000;
  nanosleep (&ts, NULL);
}

#endif
