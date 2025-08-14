#!/usr/bin/env python
"""
Standardized test runner for the DevFlow project.
Handles both pytest and Django test execution with proper environment setup.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the src directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jaroslav_tech.settings')

def run_pytest(args):
    """Run tests using pytest with proper configuration."""
    cmd = [sys.executable, '-m', 'pytest']
    
    if args.coverage:
        cmd.extend(['--cov=projects', '--cov=tasks', '--cov=core'])
        cmd.extend(['--cov-report=html', '--cov-report=term-missing'])
    
    if args.verbose:
        cmd.append('-v')
    
    if args.fast:
        cmd.extend(['-x', '--tb=short'])
    
    if args.parallel:
        try:
            import pytest_xdist
            cmd.extend(['-n', 'auto'])
        except ImportError:
            print("Warning: pytest-xdist not installed, running serially")
    
    if args.markers:
        cmd.extend(['-m', args.markers])
    
    if args.pattern:
        cmd.extend(['-k', args.pattern])
    
    if args.testpaths:
        cmd.extend(args.testpaths)
    
    return subprocess.run(cmd, cwd=BASE_DIR)

def run_django_tests(args):
    """Run tests using Django's test runner."""
    cmd = [sys.executable, 'manage.py', 'test']
    
    if args.verbose:
        cmd.append('--verbosity=2')
    
    if args.fast:
        cmd.extend(['--failfast', '--debug-mode'])
    
    if args.parallel:
        cmd.extend(['--parallel', 'auto'])
    
    if args.testpaths:
        # Convert pytest-style paths to Django test labels
        test_labels = []
        for path in args.testpaths:
            if path.startswith('projects/tests/'):
                test_labels.append(path.replace('/', '.').replace('.py', ''))
            elif path.startswith('tasks/tests/'):
                test_labels.append(path.replace('/', '.').replace('.py', ''))
        cmd.extend(test_labels)
    
    return subprocess.run(cmd, cwd=BASE_DIR)

def main():
    parser = argparse.ArgumentParser(description='DevFlow Test Runner')
    parser.add_argument('--runner', choices=['pytest', 'django'], default='pytest',
                       help='Test runner to use (default: pytest)')
    parser.add_argument('--coverage', action='store_true',
                       help='Run with coverage reporting')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--fast', '-x', action='store_true',
                       help='Stop on first failure')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Run tests in parallel')
    parser.add_argument('--markers', '-m', 
                       help='Run tests matching given mark expression')
    parser.add_argument('--pattern', '-k',
                       help='Run tests matching given pattern')
    parser.add_argument('testpaths', nargs='*',
                       help='Specific test paths to run')
    
    args = parser.parse_args()
    
    # Ensure Django is set up
    import django
    django.setup()
    
    if args.runner == 'pytest':
        result = run_pytest(args)
    else:
        result = run_django_tests(args)
    
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()