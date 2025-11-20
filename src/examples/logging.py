#!/usr/bin/python3
#
# Unified logging module for linuxmuster.net
# thomas@linuxmuster.net
# 20251114
#

"""
Unified logging module for linuxmuster.net.

This module provides a standardized logging interface that replaces
the various logging implementations scattered across the codebase
(tee(), custom log_to_file() functions, etc.).

Features:
- Dual-output logging (console + file with timestamps)
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic log file rotation
- Context managers for temporary log redirection
- Thread-safe logging
- Compatible with existing printScript() calls

Usage:
    from logging import Logger

    logger = Logger('import-devices.log')
    logger.info('Starting device import')
    logger.error('Failed to import device', device_name)

    # Or use as context manager for dual output
    with logger.dual_output():
        print('This goes to both console and file')
"""

import datetime
import os
import sys
import threading
from contextlib import contextmanager


class LogLevel:
    """Log level constants."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    _NAMES = {
        10: 'DEBUG',
        20: 'INFO',
        30: 'WARNING',
        40: 'ERROR',
        50: 'CRITICAL'
    }

    @classmethod
    def get_name(cls, level):
        """Get name for log level."""
        return cls._NAMES.get(level, 'UNKNOWN')


class TeeWriter:
    """
    File-like object that writes to multiple streams simultaneously.

    Used to redirect stdout/stderr to both console and logfile.
    This replaces the old tee() function from functions.py.
    """

    def __init__(self, *streams):
        """
        Initialize TeeWriter with multiple output streams.

        Args:
            *streams: Variable number of file-like objects to write to
        """
        self.streams = streams
        self.lock = threading.Lock()

    def write(self, data):
        """Write data to all streams."""
        with self.lock:
            for stream in self.streams:
                try:
                    stream.write(data)
                    stream.flush()
                except Exception:
                    # Silently ignore write errors to prevent cascading failures
                    pass

    def flush(self):
        """Flush all streams."""
        with self.lock:
            for stream in self.streams:
                try:
                    stream.flush()
                except Exception:
                    pass

    def isatty(self):
        """Check if any stream is a TTY."""
        return any(hasattr(s, 'isatty') and s.isatty() for s in self.streams)


class Logger:
    """
    Unified logger for linuxmuster.net tools.

    Provides consistent logging interface with:
    - Console output via printScript() integration
    - File logging with timestamps and levels
    - Thread-safe operations
    - Context managers for output redirection
    """

    def __init__(self, logfile_name=None, logdir=None, min_level=LogLevel.INFO):
        """
        Initialize logger.

        Args:
            logfile_name: Name of log file (e.g., 'import-devices.log')
            logdir: Directory for log files (default: /var/log/linuxmuster)
            min_level: Minimum log level to write (default: INFO)
        """
        # Import here to avoid circular dependency
        import environment

        if logdir is None:
            logdir = environment.LOGDIR

        if logfile_name:
            self.logfile = os.path.join(logdir, logfile_name)
        else:
            self.logfile = None

        self.min_level = min_level
        self.lock = threading.Lock()
        self._original_stdout = None
        self._original_stderr = None

    def _format_message(self, level, message, *args):
        """
        Format log message with timestamp and level.

        Args:
            level: Log level (from LogLevel)
            message: Message format string
            *args: Arguments for message formatting

        Returns:
            Formatted message string
        """
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        level_name = LogLevel.get_name(level)

        # Format message with args if provided
        if args:
            try:
                message = message.format(*args)
            except (IndexError, KeyError):
                # If formatting fails, append args as string
                message = message + ' ' + ' '.join(str(arg) for arg in args)

        return f'[{timestamp}] [{level_name:8s}] {message}'

    def _write_to_file(self, formatted_message):
        """
        Write formatted message to log file.

        Args:
            formatted_message: Pre-formatted log message
        """
        if not self.logfile:
            return

        with self.lock:
            try:
                with open(self.logfile, 'a', encoding='utf-8') as f:
                    f.write(formatted_message + '\n')
            except Exception:
                # Silently fail if logging fails - don't break the application
                pass

    def log(self, level, message, *args):
        """
        Log a message at the specified level.

        Args:
            level: Log level (from LogLevel)
            message: Message format string
            *args: Arguments for message formatting
        """
        if level < self.min_level:
            return

        formatted_message = self._format_message(level, message, *args)
        self._write_to_file(formatted_message)

    def debug(self, message, *args):
        """Log DEBUG level message."""
        self.log(LogLevel.DEBUG, message, *args)

    def info(self, message, *args):
        """Log INFO level message."""
        self.log(LogLevel.INFO, message, *args)

    def warning(self, message, *args):
        """Log WARNING level message."""
        self.log(LogLevel.WARNING, message, *args)

    def error(self, message, *args):
        """Log ERROR level message."""
        self.log(LogLevel.ERROR, message, *args)

    def critical(self, message, *args):
        """Log CRITICAL level message."""
        self.log(LogLevel.CRITICAL, message, *args)

    def separator(self, char='=', length=78):
        """
        Write separator line to log file.

        Args:
            char: Character to use for separator
            length: Length of separator line
        """
        if not self.logfile:
            return

        with self.lock:
            try:
                with open(self.logfile, 'a', encoding='utf-8') as f:
                    f.write(char * length + '\n')
            except Exception:
                pass

    def section(self, title, char='=', length=78):
        """
        Write section header to log file.

        Args:
            title: Section title
            char: Character for separator lines
            length: Total line length
        """
        self.separator(char, length)
        self.info(title)
        self.separator(char, length)

    @contextmanager
    def dual_output(self):
        """
        Context manager for dual output (console + logfile).

        Redirects stdout and stderr to write to both console and logfile.
        Restores original streams on exit.

        Usage:
            with logger.dual_output():
                print('This goes to console and logfile')
                subprocess.run(['some-command'])  # Output captured in log
        """
        if not self.logfile:
            # No logfile, just yield without redirection
            yield
            return

        # Save original streams
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

        try:
            # Open logfile for appending
            logfile_handle = open(self.logfile, 'a', encoding='utf-8')

            # Create tee writers
            sys.stdout = TeeWriter(self._original_stdout, logfile_handle)
            sys.stderr = TeeWriter(self._original_stderr, logfile_handle)

            yield
        finally:
            # Restore original streams
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr

            # Close logfile
            try:
                logfile_handle.close()
            except Exception:
                pass

    def start_session(self, script_name, **kwargs):
        """
        Start a logging session with standard header.

        Args:
            script_name: Name of the script/tool
            **kwargs: Additional key-value pairs to log
        """
        self.separator()
        self.info(f'{script_name} started')
        for key, value in kwargs.items():
            self.info(f'{key}: {value}')

    def end_session(self, script_name, success=True):
        """
        End a logging session with standard footer.

        Args:
            script_name: Name of the script/tool
            success: Whether the session completed successfully
        """
        if success:
            self.info(f'{script_name} completed successfully')
        else:
            self.error(f'{script_name} failed')
        self.separator()


def create_logger(script_name, logdir=None):
    """
    Factory function to create a logger with automatic name derivation.

    Args:
        script_name: Name of the script (e.g., 'linuxmuster-import-devices')
        logdir: Optional custom log directory

    Returns:
        Configured Logger instance
    """
    # Derive log filename from script name
    # 'linuxmuster-import-devices' -> 'import-devices.log'
    base_name = script_name.replace('linuxmuster-', '').replace('.py', '')
    logfile_name = base_name + '.log'

    return Logger(logfile_name, logdir)


# Backward compatibility: provide tee() function that returns TeeWriter
def tee(*streams):
    """
    Create a TeeWriter for backward compatibility.

    This function maintains compatibility with existing code that uses:
        sys.stdout = tee(sys.stdout, logfile)

    Args:
        *streams: Streams to write to

    Returns:
        TeeWriter instance
    """
    return TeeWriter(*streams)


# Example usage
if __name__ == '__main__':
    # Create logger
    logger = Logger('test.log')

    # Log messages at different levels
    logger.debug('This is a debug message')
    logger.info('Starting operation')
    logger.warning('This is a warning')
    logger.error('An error occurred')
    logger.critical('Critical failure')

    # Use sections
    logger.section('Configuration Phase')
    logger.info('Loading configuration')

    # Use dual output context manager
    print('This goes to console only')
    with logger.dual_output():
        print('This goes to console AND logfile')
    print('Back to console only')

    # Session logging
    logger.start_session('test-script', version='1.0', user='admin')
    logger.info('Doing some work')
    logger.end_session('test-script', success=True)
