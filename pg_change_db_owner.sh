#!/bin/bash
#
# The MIT License
#
# Copyright 2014 Jakub Jirutka <jakub@jirutka.cz>.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Credit: Based on http://stackoverflow.com/a/2686185/305019 by Alex Soto


usage() {
	cat <<- EOF
		usage: $0 options
		
		This script changes ownership for all tables, views, sequences and functions in
		a database schema and also owner of the schema itself.
		
		Note: If you want to change the ownership of all objects, in the specified database,
		owned by a database role, then you can simply use command "REASSIGN OWNED".
		
		OPTIONS:
		   -h    Show this message
		   -d    Database name
		   -o    New owner name
		   -s    Schema (defaults to public)
	EOF
}

pgexec() {
	local cmd=$1
	psql --no-psqlrc --no-align --tuples-only --record-separator=\0 --quiet \
		--command="$cmd" "$DB_NAME"
}

pgexec_echo() {
	local cmd=$1
	psql --no-psqlrc --no-align --tuples-only --record-separator=\0 --quiet \
		--echo-queries --command="$cmd" "$DB_NAME"
}


DB_NAME=''
NEW_OWNER=''
SCHEMA='public'
while getopts "hd:o:s:" OPTION; do
	case $OPTION in
		h)
			usage
			exit 1
			;;
		d)
			DB_NAME=$OPTARG
			;;
		o)
			NEW_OWNER=$OPTARG
			;;
		s)
			SCHEMA=$OPTARG
			;;
	esac
done

if [[ -z "$DB_NAME" ]] || [[ -z "$NEW_OWNER" ]]; then
	usage
	exit 1
fi

# Using the NULL byte as the separator as its the only character disallowed from PG table names.
IFS=\0

# Change owner of schema itself.
pgexec_echo "ALTER SCHEMA \"${SCHEMA}\" OWNER TO \"${NEW_OWNER}\";"

# Change owner of tables and views.
for tbl in $(pgexec "SELECT table_name FROM information_schema.tables WHERE table_schema = '${SCHEMA}';") \
		   $(pgexec "SELECT table_name FROM information_schema.views WHERE table_schema = '${SCHEMA}';"); do
	pgexec_echo "ALTER TABLE \"${SCHEMA}\".\"${tbl}\" OWNER TO ${NEW_OWNER};"
done

# Change owner of sequences.
for seq in $(pgexec "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = '${SCHEMA}';"); do
	pgexec_echo "ALTER SEQUENCE \"${SCHEMA}\".\"${seq}\" OWNER TO ${NEW_OWNER};"
done

# Change owner of functions and procedures.
for func in $(pgexec "SELECT quote_ident(p.proname) || '(' || pg_catalog.pg_get_function_identity_arguments(p.oid) || ')' \
					  FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace \
					  WHERE n.nspname = '${SCHEMA}';"); do
	pgexec_echo "ALTER FUNCTION \"${SCHEMA}\".${func} OWNER TO ${NEW_OWNER};"
done

# Revert separator back to default.
unset IFS

