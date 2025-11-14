#!/usr/bin/python3
#
# Base CLI class for linuxmuster.net command-line tools
# thomas@linuxmuster.net
# 20251114
#

"""
Base class for linuxmuster.net CLI tools.

This module provides a common base class that CLI tools can inherit from
to eliminate code duplication in argument parsing, logging setup, and
common operations. It follows the Template Method pattern.

Features:
- Standardized argument parsing with getopt
- Automatic logging setup with timestamps
- Common helper methods for setup values
- Consistent error handling and exit codes
- Extensible via inheritance and method overriding
"""

import datetime
import getopt
import os
import sys

sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import printScript


class BaseCLI:
    """
    Base class for linuxmuster.net command-line interface tools.

    Subclasses should override:
    - get_options(): Return getopt format string and long options list
    - get_usage_text(): Return usage help text
    - process_option(): Handle specific command-line options
    - run(): Implement the main logic of the tool

    Example:
        class MyTool(BaseCLI):
            def get_options(self):
                return "f:h", ["force", "help"]

            def get_usage_text(self):
                return "Usage: mytool [options]\\n -f, --force  Force execution"

            def process_option(self, opt, arg):
                if opt in ("-f", "--force"):
                    self.force = True
                elif opt in ("-h", "--help"):
                    self.print_usage()
                    sys.exit(0)

            def run(self):
                # Tool-specific logic here
                pass
    """

    def __init__(self, script_name=None, logfile_name=None):
        """
        Initialize the CLI tool.

        Args:
            script_name: Name of the script (default: derived from sys.argv[0])
            logfile_name: Name for the logfile (default: derived from script_name)
        """
        self.script_name = script_name or os.path.basename(sys.argv[0])

        # Setup logfile
        if logfile_name:
            self.logfile = environment.LOGDIR + '/' + logfile_name
        else:
            # Derive logfile name from script name (e.g., "linuxmuster-import-devices" -> "import-devices.log")
            base_name = self.script_name.replace('linuxmuster-', '').replace('.py', '')
            self.logfile = environment.LOGDIR + '/' + base_name + '.log'

        # Subclasses can set these
        self.verbose = False
        self.debug = False

    def get_options(self):
        """
        Return getopt option format.

        Returns:
            Tuple of (short_opts, long_opts) for getopt.getopt()
            Example: ("f:h", ["force", "help"])

        Override this method in subclasses to define CLI options.
        """
        return "h", ["help"]

    def get_usage_text(self):
        """
        Return usage help text.

        Returns:
            String with usage information

        Override this method in subclasses to provide usage text.
        """
        return f"Usage: {self.script_name} [options]\n -h, --help  Print this help"

    def print_usage(self):
        """Print usage information."""
        print(self.get_usage_text())

    def process_option(self, opt, arg):
        """
        Process a single command-line option.

        Args:
            opt: Option flag (e.g., "-f" or "--force")
            arg: Option argument (if any)

        Override this method in subclasses to handle specific options.
        Default implementation handles -h/--help.
        """
        if opt in ("-h", "--help"):
            self.print_usage()
            sys.exit(0)

    def parse_arguments(self, argv=None):
        """
        Parse command-line arguments.

        Args:
            argv: Argument list (default: sys.argv[1:])

        Returns:
            Remaining non-option arguments
        """
        if argv is None:
            argv = sys.argv[1:]

        short_opts, long_opts = self.get_options()

        try:
            opts, args = getopt.getopt(argv, short_opts, long_opts)
        except getopt.GetoptError as err:
            print(err)
            self.print_usage()
            sys.exit(2)

        # Process each option
        for opt, arg in opts:
            self.process_option(opt, arg)

        return args

    def log(self, message, level='INFO'):
        """
        Write message to logfile with timestamp.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        try:
            with open(self.logfile, 'a') as f:
                timestamp = str(datetime.datetime.now()).split('.')[0]
                f.write(f'[{timestamp}] [{level}] {message}\n')
        except Exception:
            # Fail silently if logging fails
            pass

    def log_separator(self, char='=', length=78):
        """
        Write separator line to logfile.

        Args:
            char: Character to use for separator
            length: Length of separator line
        """
        self.log(char * length, level='')

    def start_logging(self, additional_info=None):
        """
        Initialize logging with standard header.

        Args:
            additional_info: Optional dict with additional info to log
        """
        self.log_separator()
        self.log(f'{self.script_name} started', level='INFO')
        if additional_info:
            for key, value in additional_info.items():
                self.log(f'{key}: {value}', level='INFO')

    def print_start(self):
        """Print script start message."""
        printScript(self.script_name, 'begin')

    def print_end(self):
        """Print script end message."""
        printScript(self.script_name, 'end')

    def run(self):
        """
        Execute the main logic of the tool.

        Override this method in subclasses to implement tool-specific logic.
        """
        raise NotImplementedError("Subclasses must implement the run() method")

    def execute(self):
        """
        Main entry point for the CLI tool.

        This method orchestrates the execution:
        1. Parse arguments
        2. Print start message
        3. Run tool-specific logic
        4. Print end message

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Parse command-line arguments
            remaining_args = self.parse_arguments()

            # Start execution
            self.print_start()

            # Run tool-specific logic
            self.run()

            # End execution
            self.print_end()

            return 0
        except KeyboardInterrupt:
            printScript('\nAborted by user.')
            return 130
        except Exception as error:
            printScript(f'Error: {error}')
            self.log(f'FATAL: {error}', level='ERROR')
            return 1


def main():
    """
    Example usage of BaseCLI class.

    This function demonstrates how to create a simple CLI tool using BaseCLI.
    """
    class ExampleTool(BaseCLI):
        def __init__(self):
            super().__init__(script_name='example-tool', logfile_name='example.log')
            self.force = False
            self.verbose = False

        def get_options(self):
            return "fvh", ["force", "verbose", "help"]

        def get_usage_text(self):
            return """Usage: example-tool [options]
 [options] may be:
 -f, --force    : Force execution without prompts
 -v, --verbose  : Enable verbose output
 -h, --help     : Print this help
"""

        def process_option(self, opt, arg):
            if opt in ("-f", "--force"):
                self.force = True
            elif opt in ("-v", "--verbose"):
                self.verbose = True
            elif opt in ("-h", "--help"):
                self.print_usage()
                sys.exit(0)

        def run(self):
            self.start_logging({'force': self.force, 'verbose': self.verbose})
            printScript('Example tool running...')
            self.log('Tool executed successfully')

    tool = ExampleTool()
    sys.exit(tool.execute())


if __name__ == '__main__':
    main()
