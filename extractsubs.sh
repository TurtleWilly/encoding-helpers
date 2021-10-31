#!/bin/bash

#
#  A somewhat smart wrapper for Wine+Caption2Ass_PCR.exe. 
#  by Wilhelm/ JPTV.club
#
#  Important Note:
#       Random absolute paths matching my installation, you'll have to fix
#       those. 'cleanup_drcs.py' is still unreleased, so you have to disable
#       that for now.
#
#  History:
#       1.1 (11-Sep-2021)  - Initial version
#       1.2 (12-Sep-2021)  - Also create 'cleaned' versions of the subs in one go
#

set -ue

PREFIX="extractsubs:"


if [ "$#" -eq 0 ]; then
	echo "${PREFIX} missing file argument(s)." 1>&2
fi

if [ "${1:-'--help'}" == '--help' ] || [ "$#" -eq 0 ]; then
	printf 'Usage: extractsubs file ...\n\n' 1>&2 
	exit 2
fi


for FN in "$@"; do
	echo "Processing file <${FN}>…"

	if [ -f "${FN}" ] && [ -s "${FN}" ]; then

		SYNCBYTE=$(head -c 1 "${FN}")  # XXX: maybe use mediainfo to check for filetype
		if [[ "${SYNCBYTE}" == "G" ]]; then
			echo "MPEG2 sync byte 0x47 found at offset 0. <${FN}> seems to be a TS file!"

			JUSTDN="$(dirname "${FN}")"
			JUSTFN="$(basename "${FN}")"

			( if cd "${JUSTDN}"; then
				echo "Changed to directory <$(pwd -P)>"

				# NOTE: Let's not not add ".ts" suffix to the temporary name here! 
				#       In case we loop over .ts files we don't potentially mess up
				#       the loops that way.
				TMPFN="$(uuidgen),extractsubs,hardlink"   

				echo "Creating temporary hardlink…"
				ln "${JUSTFN}" "${TMPFN}"

				echo "Extracting and converting ARIB subtitles…"
				WINEDEBUG=-all /Volumes/Storage/Applications/Wine/usr/bin/wine /Volumes/Storage/Applications/Wine/Caption2Ass/Caption2Ass_PCR.exe -rb_size 262144 -format dual "${TMPFN}" 
			
				echo "Renaming extracted subtitle files…"
				BACKUPTIME=$(date '+%Y%m%d%H%M%S')
				if [ -s "${TMPFN}.ass" ]; then
					if [ -e "${JUSTFN},clean.ass" ]; then
						mv "${JUSTFN},clean.ass" "${JUSTFN},clean.ass,${BACKUPTIME}.bak"
					fi
					/usr/local/bin/python3 /Volumes/Data/Scripts/Subtitles/cleanup_drcs.py < "${TMPFN}.ass" > "${JUSTFN},clean.ass"

					if [ -e "${JUSTFN}.ass" ]; then
						mv "${JUSTFN}.ass" "${JUSTFN}.ass,${BACKUPTIME}.bak"
					fi
					mv -n "${TMPFN}.ass" "${JUSTFN}.ass"
				else
					echo "${PREFIX} No ASS file was generated." 1>&2
				fi
				if [ -s "${TMPFN}.srt" ]; then
					if [ -e "${JUSTFN},clean.srt" ]; then
						mv "${JUSTFN},clean.srt" "${JUSTFN},clean.srt,${BACKUPTIME}.bak"
					fi
					/usr/local/bin/python3 /Volumes/Data/Scripts/Subtitles/cleanup_drcs.py < "${TMPFN}.srt" > "${JUSTFN},clean.srt"

					if [ -e "${JUSTFN}.srt" ]; then
						mv "${JUSTFN}.srt" "${JUSTFN}.srt,${BACKUPTIME}.bak"
					fi
					mv -n "${TMPFN}.srt" "${JUSTFN}.srt"
				else
					echo "${PREFIX} No SRT file was generated." 1>&2
				fi

				echo "Cleaning up…"
				rm "${TMPFN}"
				rm -f "${TMPFN}.ass"
				rm -f "${TMPFN}.srt"

			else
				echo "${PREFIX} failed to change to the file's directory <${JUSTDN}>." 1>&2
			fi )

		else
			echo "${PREFIX} MPEG2 sync byte 0x47 not found at offset 0." 1>&2
		fi

	else
		echo "${PREFIX} <${FN}> does not exists, is not an actual file, or is empty." 1>&2
	fi

done
