#!/usr/bin/env python
from __future__ import print_function, division
import sys, os, subprocess, glob, datetime, time
import re

import darincdec_snapshot

def slurp (fname):
  with open (fname) as f:
    return f.read ()

def re_gdict (m):
  if m is None: return None
  d = m.groupdict(); d [""] = m.string
  return d

def outdated (period_dir, prefix, max_interval):
  latest = darincdec_snapshot.dar_basename (darincdec_snapshot.find_latest (period_dir, prefix))
  if latest is None: return True
  new_suffix = darincdec_snapshot.suffix_now ()
  old_suffix = darincdec_snapshot.extract_suffix (latest, prefix, new_suffix)
  old_t, new_t = tuple (datetime.datetime.strptime (sfx, darincdec_snapshot.DEFAULT_SUFFIX) for sfx in (old_suffix, new_suffix))
  delta_days = (new_t - old_t).total_seconds () / (60*60*24)
  print ((period_dir, prefix, delta_days))
  return delta_days >= max_interval

def do_backup (opts, pmatch):
  import shlex
  """Return 1st pfx* glob"""
  def glob1pfx (dirname, pfx):
    if pfx is None: return None
    return glob.glob (os.path.join (dirname, pfx + "*")) [0]
  period_refdir = glob1pfx (opts.repo, pmatch ["ref"])
  period_dir = os.path.join (opts.repo, pmatch [""])
  dotdir = os.path.join (period_dir, ".backups")
  if os.path.exists (dotdir):
    for cfgfname in os.listdir (dotdir):
      cfgmatch = re_gdict (re.match ("(?P<pfx>" + darincdec_snapshot.PFX_RE + ")(@(?P<ref>" + darincdec_snapshot.PERIOD_RE + "))?(\.cfg)?", cfgfname))
      if opts.force or outdated (period_dir, cfgmatch ["pfx"], float (pmatch ["interval"])):
        os.chdir (period_dir)
        cmd = slurp (os.path.join (dotdir, cfgfname)).rstrip ("\n")
        refdir = period_refdir or glob1pfx (opts.repo, cfgmatch ["ref"])
        refdir_args = [] if refdir is None else ["--refdir", refdir]
        args1 = ["--mode", pmatch ["mode"]]
        if opts.replace: args1.append ("--replace")
        args2 = shlex.split (cmd)
        if args2 [0] == "--defaults":
          args1.append (args2.pop (0))
        darincdec_snapshot.cmdline (args1 + refdir_args + [".", cfgmatch ["pfx"]] + args2)

def main ():
  def setup_argparser ():
    import argparse
    _ = argparse.ArgumentParser (description = "Operates on an dar-incdec backup repository")
    _.add_argument ("--interval", action = "append", help = "act on specific interval folder (can be repeated)")
    _.add_argument ("--force", action = "store_true", help = "no out-of-date check")
    _.add_argument ("--replace", action = "store_true", help = "replace most recent backups")
    _.add_argument ("action", choices = ["backup"])
    _.add_argument ("repo")
    return _
  opts = setup_argparser ().parse_args ()
  opts.repo = os.path.abspath (opts.repo)
  # infrequent first
  period_dir_re = r"^(?P<interval>" + darincdec_snapshot.PERIOD_RE + ")(@(?P<ref>" + darincdec_snapshot.PERIOD_RE + r"))?-(?P<mode>[a-z_]+)$"
  periods = opts.interval
  if periods is None:
    periods = (p for p in os.listdir (opts.repo) if os.path.exists (os.path.join (opts.repo, p, ".backups")))
  period_matches = sorted ((pm for pm in (re_gdict (re.match (period_dir_re, p)) for p in periods) if pm), reverse = True, key = lambda m: m [""])

  for mode in ["dec", "inc"]:  # decremental first
    for pm in period_matches:
      if pm ["mode"] == mode: do_backup (opts, pm)
    time.sleep (0.0011)  # avoid snapshots with same name (=timestamp)

if __name__ == "__main__":
  main ()
