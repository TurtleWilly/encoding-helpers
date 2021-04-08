#!/usr/bin/env python3
"""
	checkcombing.py
	Checks for combed frames and frame ranges in TV cap sources; optionally generates
	a chapter file for use in vsedit and similar applications.

	Copyright © 2020-2021 Wilhelm/ JPTV CLub

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU Affero General Public License as published
	by the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU Affero General Public License for more details.

	You should have received a copy of the GNU Affero General Public License
	along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import argparse
import os
import json
from vapoursynth import core

__author__  = 'Wilhelm/ JPTV Club'
__version__ = '1.4'
__all__     = []


ap = argparse.ArgumentParser(
	description=('Insert description here.'),
	epilog='Report bugs, request features, or provide suggestions via https://github.com/TurtleWilly/encoding-helpers/issues',
	#add_help=False,
)

ap.add_argument('filename', help='a (typically interlaced) input video file to be scanned for combed frames.')
ap.add_argument('-V', '--version',  action='version', help="show version number and exit", version='%(prog)s {}'.format(__version__), )
ap.add_argument('-o', '--output', metavar='BASE', type=str, help='filename base for all generated files. If omitted `filename\' is used by default.')
ap.add_argument(      '--inverse', action='store_true', help="detect uncombed frame ranges instead combed ones.")
ap.add_argument(      '--threshold', type=int, help='range merging threshold, default: 2', default=2)
ap.add_argument(      '--min-range', type=int, help='minimum number of frames required for a range, default: 1', default=1)
ap.add_argument(      '--dup-frames', metavar='ID1,ID2,…', type=str, help='comma separated list of frame IDs to be duplicated before the scan', default=None)
user_input = ap.parse_args()

frametype = 'uncombed' if user_input.inverse else 'combed'

#core.num_threads = 1
#core.add_cache = False

filename = os.path.realpath(os.path.expanduser(user_input.filename))
spacer = '-------------------------------------------------------------------------'

print('Scanning {}…'.format(filename), '\n', spacer, sep='', file=sys.stderr)	

clip = core.ffms2.Source(source=filename, threads=1, seekmode=0)

if user_input.dup_frames:
	dupes = [int(s.strip()) for s in user_input.dup_frames.split(",")]
	clip = core.std.DuplicateFrames(clip, frames=dupes)
	print("Duplicated frames with the following IDs: ", str(dupes))

clip = core.tdm.IsCombed(clip)

detected_frames = []
while True:
	try:
		for i in range(0, clip.num_frames):
			state = (clip[i].get_frame(0)).props['_Combed']
			if (not state if user_input.inverse else state):
				print('\033[KFrame {:>7,} detected as \'{}\'.'.format(i, frametype), file=sys.stderr)
				detected_frames.append(i)
			print('\033[KScanning frame {:,} of {:,} ({:.2f}%)…'.format(i, clip.num_frames, 100.0/clip.num_frames*i), end='\r', file=sys.stderr)
		else:
			break
	except KeyboardInterrupt:
		# Note: might avoid a crash in VapourSynth sometimes
		print('\r\033[KScan process cancelled with ^C.')
		break

clip.set_output()

spacer = '-------------------------------------------------------------------------'
print(spacer, '\n', 'Computed Ranges:', sep='', file=sys.stderr)		

# Set up the ranges
myranges = []
rng = []
last_id = -1000 # dummy
for frameid in detected_frames:
	if frameid > (last_id + max(1, user_input.threshold)) and len(rng):
		myranges.append(rng)
		rng = []
	rng.append(frameid)
	last_id = frameid
if len(rng):  # make sure to not add empty ranges
	myranges.append(rng)

# Debug Info Output
for i, r in enumerate(myranges):
	if len(r) >= user_input.min_range:
		if len(r) > 1:     # multiple frames
			print('#{:>2}: {:>7,}—>{:>7,}  ({:,} frames of {:,} are are {})'.format(i, r[0], r[-1], len(r), ((r[-1] - r[0]) + 1), frametype), file=sys.stderr)
		elif len(r) == 1:  # single frame
			print('#{:>2}: {:>7,}           (1 {} frame)'.format(i, r[0], frametype), file=sys.stderr)

print(spacer)
print('{:,} frames detected as \'{}\', {:,} possible ranges computed.'.format(len(detected_frames), frametype, len(myranges)), sep='', file=sys.stderr)


outputbasefilename = os.path.realpath(os.path.expanduser(user_input.output)) if user_input.output else filename

# Output a "Python-ready" debug info
ofn = '{},combingcheck,info.py'.format(outputbasefilename)
with open(ofn, 'w') as fh:
	print('combed_ranges = [', file=fh)
	for i, r in enumerate(myranges):
		if len(r) >= user_input.min_range:
			if len(r) > 1:     # multiple frames
				rstr = '\'[{} {}]\','.format(r[0], r[-1])
				print('\t{:<22}  # Range #{:>2}: {:,} frames of {:,} are are {}'.format(rstr, i, len(r), ((r[-1] - r[0]) + 1), frametype), file=fh)
			elif len(r) == 1:  # single frame
				rstr = '\'{}\','.format(r[0])
				print('\t{:<22}  # Range #{:>2}: 1 {} frame'.format(rstr, i, frametype), file=fh)
	print(']', file=fh)
	print('>>> File with range information successfully written to <{}>.'.format(ofn), file=sys.stderr)

# Output JSON file
ofn = '{},combingcheck.json'.format(outputbasefilename)
with open(ofn, 'w') as fh:
	print(json.dumps(detected_frames, separators=(',', ':')), file=fh)
	print('>>> JSON file successfully written to <{}>.'.format(ofn), file=sys.stderr)

# Output chapters file
ofn = '{},combingcheck,chapters.txt'.format(outputbasefilename)
with open(ofn, 'w') as fh:
	for i, r in enumerate(myranges):
		if len(r) >= user_input.min_range:
			ms    = r[0] * (1000 / (clip.fps.numerator / clip.fps.denominator))
			s, ms = divmod(ms, 1000)
			m, s  = divmod(s,    60)
			h, m  = divmod(m,    60)
			print('CHAPTER{:02}={:02}:{:02}:{:02}.{:03}'.format(i+1, int(h), int(m), int(s), int(ms)), file=fh)
			if len(r) > 1:
				print('CHAPTER{:02}NAME={} frame range {:,}—{:,}'.format(i+1, frametype.capitalize(), r[0], r[-1]), file=fh)
			else:
				print('CHAPTER{:02}NAME={} frame #{:,}'.format(i+1, frametype.capitalize(), r[0]), file=fh)
	print('>>> Chapter file successfully written to <{}>.'.format(ofn), file=sys.stderr)


print('All done.', file=sys.stderr)
