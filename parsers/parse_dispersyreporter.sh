#!/bin/bash

#EXPECTED_ARGS=3
#if [ $# -ne $EXPECTED_ARGS ]
#then
	#	echo "Usage: `basename $0` inputDir outputDir"
	#exit 65
#fi

# get parent dir of script from which $0 is executed
WORKSPACE_DIR=$(readlink -f $( dirname $(readlink -f $(which "$0")))/..)

#$(readlink -f `dirname "$0"`/..)

FORCE=""
while getopts i:o:f flag; do
	case $flag in
		i)
			INPUTDIR=$(readlink -f $OPTARG)
			;;
		o)
			OUTPUTDIR=$(readlink -f $OPTARG)
			;;
		f)
			FORCE="-f"
			;;
esac
done

if [ -z ${INPUTDIR+x} ] || [ -z ${OUTPUTDIR+x} ]; then
	echo "Usage: `basename $0` -i inputdir -o outputdir [-f]"
	exit;
fi

python $WORKSPACE_DIR/parsers/dispersyreporter2html.py -i $INPUTDIR -o $OUTPUTDIR $FORCE

echo "Generating flame graphs..."
# generate flamegraphs
for FG in $(ls $OUTPUTDIR/*_fg.txt -1tr); do
	FILENAME=${FG/txt/svg}
	cat $FG | $WORKSPACE_DIR/flamegraph/flamegraph.pl > $FILENAME
done
echo "Done"