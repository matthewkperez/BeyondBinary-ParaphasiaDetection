#!/bin/bash
python -c 'from speechbrain.utils.recipe_tests import run_recipe_tests; print("TEST FAILED!") if not(run_recipe_tests()) else print("TEST PASSED")'
