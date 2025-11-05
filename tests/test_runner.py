"""
Comprehensive test runner for AAFR backend test suite.
Runs all test modules and provides summary report.
"""

import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def run_all_tests():
    """Run all test modules and return test result."""
    # Discover all test modules
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test modules
    test_modules = [
        'tests.test_icc_module',
        'tests.test_cvd_module',
        'tests.test_risk_engine',
        'tests.test_tradovate_api',
        'tests.test_backtester',
        'tests.test_utils',
        'tests.test_integration',
        'tests.test_edge_cases',
        'tests.test_multi_instrument',
        'tests.test_backtest_metrics'
    ]
    
    for module_name in test_modules:
        try:
            suite.addTests(loader.loadTestsFromName(module_name))
        except Exception as e:
            print(f"[WARNING] Failed to load {module_name}: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    return result


def run_module_tests(module_name):
    """Run tests for a specific module."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module_name)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AAFR Backend Test Runner')
    parser.add_argument('--module', '-m', help='Run specific test module (e.g., test_icc_module)')
    parser.add_argument('--all', '-a', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    if args.module:
        print(f"\n{'='*70}")
        print(f"Running tests for module: {args.module}")
        print('='*70 + "\n")
        result = run_module_tests(f'tests.{args.module}')
    else:
        print("\n" + "="*70)
        print("AAFR BACKEND TEST SUITE")
        print("="*70 + "\n")
        result = run_all_tests()
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run:     {result.testsRun}")
    print(f"Successes:     {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:      {len(result.failures)}")
    print(f"Errors:        {len(result.errors)}")
    print(f"Skipped:       {len(result.skipped)}")
    
    if result.failures:
        print("\n" + "="*70)
        print("FAILURES")
        print("="*70)
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\n" + "="*70)
        print("ERRORS")
        print("="*70)
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    print("="*70 + "\n")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

