#!/usr/bin/env bash
set -e

echo "Gathering doc coverage..."
set +e
DOC_OUT=$(interrogate -c pyproject.toml src/)
DOC_EXIT=$?
set -e
DOC_COV=$(echo "$DOC_OUT" | grep actual | sed -n 's/.*actual: \([0-9.]*\)%.*/\1/p')

if [ -z "$DOC_COV" ]; then
    DOC_COV="0"
fi

echo "Gathering test coverage..."
set +e
TEST_OUT=$(pytest)
TEST_EXIT=$?
set -e
TEST_COV=$(echo "$TEST_OUT" | grep "TOTAL" | tail -n 1 | awk '{print $NF}' | tr -d '%')

if [ -z "$TEST_COV" ]; then
    TEST_COV="0"
fi

echo "Doc Coverage: $DOC_COV%"
echo "Test Coverage: $TEST_COV%"

DOC_COLOR="green"
if awk "BEGIN {exit !($DOC_COV < 100)}"; then DOC_COLOR="yellow"; fi
if awk "BEGIN {exit !($DOC_COV < 80)}"; then DOC_COLOR="red"; fi

TEST_COLOR="green"
if awk "BEGIN {exit !($TEST_COV < 100)}"; then TEST_COLOR="yellow"; fi
if awk "BEGIN {exit !($TEST_COV < 80)}"; then TEST_COLOR="red"; fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/!\[Doc Coverage\](https:\/\/img.shields.io\/badge\/doc%20coverage-.*-.*)/!\[Doc Coverage\](https:\/\/img.shields.io\/badge\/doc%20coverage-${DOC_COV}%25-${DOC_COLOR})/" README.md
    sed -i '' "s/!\[Test Coverage\](https:\/\/img.shields.io\/badge\/test%20coverage-.*-.*)/!\[Test Coverage\](https:\/\/img.shields.io\/badge\/test%20coverage-${TEST_COV}%25-${TEST_COLOR})/" README.md
else
    sed -i "s/!\[Doc Coverage\](https:\/\/img.shields.io\/badge\/doc%20coverage-.*-.*)/!\[Doc Coverage\](https:\/\/img.shields.io\/badge\/doc%20coverage-${DOC_COV}%25-${DOC_COLOR})/" README.md
    sed -i "s/!\[Test Coverage\](https:\/\/img.shields.io\/badge\/test%20coverage-.*-.*)/!\[Test Coverage\](https:\/\/img.shields.io\/badge\/test%20coverage-${TEST_COV}%25-${TEST_COLOR})/" README.md
fi


if [ $DOC_EXIT -ne 0 ]; then
    echo "Interrogate failed! Doc coverage is below 100%."
    exit $DOC_EXIT
fi

if [ $TEST_EXIT -ne 0 ]; then
    echo "Pytest failed!"
    exit $TEST_EXIT
fi
