/* biosdisk.h - emulate biosdisk */
/*
 *  GRUB  --  GRand Unified Bootloader
 *  Copyright (C) 2002,2007  Free Software Foundation, Inc.
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

#ifndef GRUB_BIOSDISK_MACHINE_UTIL_HEADER
#define GRUB_BIOSDISK_MACHINE_UTIL_HEADER	1

#include <grub/disk.h>
#include <sys/types.h>

void grub_util_biosdisk_init (const char *dev_map);
void grub_util_biosdisk_fini (void);
char *grub_util_biosdisk_get_grub_dev (const char *os_dev);
const char *grub_util_biosdisk_get_osdev (grub_disk_t disk);
int grub_util_biosdisk_is_present (const char *name);
int grub_util_biosdisk_is_floppy (grub_disk_t disk);
grub_err_t grub_util_biosdisk_flush (struct grub_disk *disk);
void grub_util_pull_device (const char *osname);
grub_err_t
grub_util_fd_seek (int fd, const char *name, grub_uint64_t sector);
ssize_t grub_util_fd_read (int fd, char *buf, size_t len);
grub_err_t
grub_cryptodisk_cheat_mount (const char *sourcedev, const char *cheat);
void grub_util_cryptodisk_print_uuid (grub_disk_t disk);
#if !defined(__MINGW32__)
grub_uint64_t
grub_util_get_fd_sectors (int fd, unsigned *log_secsize);
#endif

#endif /* ! GRUB_BIOSDISK_MACHINE_UTIL_HEADER */
