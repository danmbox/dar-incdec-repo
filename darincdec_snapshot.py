#!/usr/bin/env python
from __future__ import print_function, division
import sys, os, subprocess, glob
import re

PFX_SFX_SEP = "-"
PERIOD_RE = "[0-9]{3,}([.][0-9]+)?"
PFX_RE = "[A-Za-z0-9_]+"
DAR_GLOB_SFX = ".[0-9]*.dar"
DEFAULT_SUFFIX = "%Y%m%d_%H%M%S_%f"

def suffix_now ():
  import datetime
  return datetime.datetime.now().strftime (DEFAULT_SUFFIX)

"""Finds the latest backup with a given prefix (lexicographic sort)"""
def find_latest (dirname, pfx):
  globs = glob.glob (os.path.join (dirname, pfx + PFX_SFX_SEP + "*" + DAR_GLOB_SFX))
  return None if len (globs) == 0 else max (globs)

def touch (path, t = None):
  with open (path, "a"):
    os.utime (path, t)

"""Strips the .n.dar extension from a filename"""
def dar_basename (fname):
  if fname is None: return None
  m = re.match (r"(.*)\.[0-9]+\.dar$", os.path.basename (fname))
  if m: return m.group (1)

def extract_suffix (fname, prefix, suffix0):
  if fname is None: return None
  suffix_start = len (prefix) + len (PFX_SFX_SEP)
  suffix = fname [suffix_start : suffix_start + len (suffix0)]
  return suffix
  
def call_dar (args):
  print ("dar: ", args)
  subprocess.check_call (["dar"] + args)

def cmdline (args):
  def setup_argparser ():
    import argparse
    _ = argparse.ArgumentParser ()
    _.add_argument ("--mode", "-m", choices = ["inc", "dec"], required = True)
    _.add_argument ("--replace", action = "store_true", help = "replace most recent backup")
    _.add_argument ("--defaults", action = "store_true", help = "enable sensible DAR defaults")
    _.add_argument ("--refdir", help = "reference directory for incremental backups")
    _.add_argument ("--suffix", default = suffix_now (), help = "suffix for backup (defaults to timestamp)")
    _.add_argument ("destdir")
    _.add_argument ("prefix", help = "basename for backup")
    _.add_argument ("dar_args", nargs = argparse.REMAINDER, help = "DAR pass-through arguments")
    return _

  argp = setup_argparser (); opts = argp.parse_args (args)
  if opts.defaults:
    opts.dar_args.extend ("-z -Z *.gz -Z *.bz2 -Z *.xz -Z *.zip -Z *.png -Z *.gif -Z *.jpg -Z *.mp3".split (" "))
  if opts.replace:
    latest = find_latest (opts.destdir, opts.prefix)
    print ("Removing " + latest)
    os.unlink (latest)
  refdir = opts.refdir if opts.refdir else opts.destdir
  ref = dar_basename (find_latest (refdir, opts.prefix))
  refpath = None if ref is None else os.path.join (refdir, ref)
  if opts.mode == "inc":
    refsfx = extract_suffix (ref, opts.prefix, opts.suffix)
    dest = "{}{}{}{}".format (opts.prefix, PFX_SFX_SEP, opts.suffix, "" if refsfx is None else "@" + refsfx)
    refargs = [] if refpath is None else ["-A", refpath]
    call_dar (["-c", os.path.join (opts.destdir, dest)] + refargs + opts.dar_args)
  elif opts.mode == "dec":
    # refpath is old full backup, if any
    full = "{}{}{}".format (opts.prefix, PFX_SFX_SEP, opts.suffix)
    fullpath = os.path.join (opts.destdir, full)
    call_dar (["-c", fullpath] + opts.dar_args)
    if refpath is not None:
      decpath = refpath  + "@" + opts.suffix
      call_dar (["-+", decpath, "-A", refpath, "-@", fullpath, "-ad", "-ak", "-w"])
      call_dar (["-t", decpath])
      for f in glob.glob (refpath + DAR_GLOB_SFX): os.unlink (f)
      for f in glob.glob (fullpath + DAR_GLOB_SFX): touch (f)

if __name__ == "__main__":
  cmdline (sys.argv [1:])
