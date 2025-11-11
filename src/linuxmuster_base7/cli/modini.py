#!/usr/bin/python3
#
# CLI entry point wrapper for linuxmuster-modini
# Auto-generated for Debian Python Policy compliance
# 20251111
#

import sys
import os

# Add linuxmuster-common to path for environment module
sys.path.insert(0, '/usr/lib/linuxmuster')

def main():
    """Main entry point wrapper."""
    # Import and execute the original script logic
    original_script = os.path.join('/usr/sbin', 'linuxmuster-modini')
    
    # For now, we'll import the functions and re-execute
    # This will be properly refactored in a later step
    import importlib.util
    spec = importlib.util.spec_from_file_location("cli_module", original_script)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        print(f"Error: Could not load {original_script}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
