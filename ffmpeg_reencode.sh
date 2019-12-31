#! /bin/sh

if [ -d "$1" ] ; then
	echo "is a dir"
	for fname in $1/*; do
		echo "processing $fname"
		base=$(basename $fname .mp4)
		dir=$(dirname $fname)
		ffmpeg -i $fname -c:a aac "${dir}/${base}.avi"
	done

else
	if [ -f "$1" ] ; then
		base=$(basename $1 .mp4)
		dir=$(dirname $1)
		ffmpeg -i $1 -c:a aac "${dir}/${base}.avi"
	else
		>&2 echo "$1 does not exist"
	fi
fi
