#!/bin/bash
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./run-unit-tests.sh
#

[ "$DEBUG" == 'true' ] && set -x
set -e

template_dir="$PWD"
source_dir="$(cd $template_dir/../source; pwd -P)"

echo "Current directory: $template_dir"
echo "Source directory: $source_dir"

run_python_lambda_test() {
	lambda_name=$1
	lambda_description=$2
	echo "------------------------------------------------------------------------------"
	echo "[Test] Python Unit Test: $lambda_description"
	echo "------------------------------------------------------------------------------"

  cd $source_dir/$lambda_name
  echo "run_python_lambda_test: Current directory: $source_dir/$lambda_name"

  echo "Installing python packages"

  # Check if poetry is available in the shell
  if command -v poetry >/dev/null 2>&1; then
    POETRY_COMMAND="poetry"
  elif [ -n "$POETRY_HOME" ] && [ -x "$POETRY_HOME/bin/poetry" ]; then
    POETRY_COMMAND="$POETRY_HOME/bin/poetry"
  else
    echo "Poetry is not available. Aborting script." >&2
    exit 1
  fi

  # This creates a virtual environment based on the project name in pyproject.toml.
  "$POETRY_COMMAND" install

  # Activate the virtual environment.
  source $("$POETRY_COMMAND" env info --path)/bin/activate

  # Set coverage report path
	mkdir -p $source_dir/test/coverage-reports
	coverage_report_path=$source_dir/test/coverage-reports/$lambda_name.coverage.xml
	echo "coverage report path set to $coverage_report_path"

  # Run unit tests with coverage
  python3 -m pytest --cov --cov-report=term-missing --cov-report "xml:$coverage_report_path"

	if [ "$?" = "1" ]; then
		echo "(deployment/run-unit-tests.sh) ERROR: there is likely output above." 1>&2
		exit 1
	fi

    # The pytest --cov with its parameters and .coveragerc generates a xml cov-report with `coverage/sources` list
    # with absolute path for the source directories. To avoid dependencies of tools (such as SonarQube) on different
    # absolute paths for source directories, this substitution is used to convert each absolute source directory
    # path to the corresponding project relative path. The $source_dir holds the absolute path for source directory.
	sed -i -e "s,<source>$source_dir,<source>source,g" $coverage_report_path

  deactivate

	if [ "${CLEAN:-true}" = "true" ]; then
		# Note: leaving $source_dir/test/coverage-reports to allow further processing of coverage reports
		rm -fr coverage
		rm .coverage
	fi
}

# Run Python unit tests
run_python_lambda_test access_handler "BadBot Access Handler Lambda"
run_python_lambda_test custom_resource "Custom Resource Lambda"
run_python_lambda_test helper "Helper Lambda"
run_python_lambda_test ip_retention_handler "Set IP Retention Lambda"
run_python_lambda_test log_parser "Log Parser Lambda"
run_python_lambda_test reputation_lists_parser "Reputation List Parser Lambda"
run_python_lambda_test timer "Timer Lambda"


# Return to the directory where we started
cd $template_dir