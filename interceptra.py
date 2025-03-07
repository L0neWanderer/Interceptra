#!/usr/bin/env python3
"""
Interceptra - Android APK Proxy Enabler

This tool modifies Android APKs to enable network proxy interception via tools like Burp Suite.
It adds the necessary network security configuration to allow for HTTPS traffic inspection,
and re-signs the APK with a debug certificate.

Typical usage:
  python interceptra.py -a path/to/app.apk
"""

import argparse
import os
import sys
import json
from interceptra_core import Interceptra

VERSION = "1.1.0"

def handle_args():
    parser = argparse.ArgumentParser(
        prog="interceptra",
        description="Interceptra v" + VERSION + " - Patch Android APKs to enable proxy interception",
        epilog="Example: interceptra.py -a path/to/app.apk --verbose"
    )
    
    parser.add_argument(
        "--apk", "-a", 
        help="Path to the APK file to patch", 
        required=True
    )
    
    parser.add_argument(
        "--verbose", "-v",
        help="Enable verbose output",
        action="store_true"
    )
    
    parser.add_argument(
        "--keep-files", "-k",
        help="Keep intermediate files after patching",
        action="store_true"
    )
    
    parser.add_argument(
        "--tools",
        help="Specify custom paths to tools in JSON format",
        type=str,
        default=None
    )
    
    return parser.parse_args()

def parse_tool_paths(tools_json):
    """Parse tool paths from JSON string or file."""
    if not tools_json:
        return None
        
    # Check if it's a file path
    if os.path.isfile(tools_json):
        try:
            with open(tools_json, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading tools config file: {str(e)}")
            return None
    
    # Otherwise try to parse as JSON string
    try:
        return json.loads(tools_json)
    except Exception as e:
        print(f"[!] Error parsing tools JSON: {str(e)}")
        return None

def main():
    args = handle_args()
    
    print(f"[+] Interceptra v{VERSION}")
    
    # Expand user paths (like ~)
    apk_path = os.path.expanduser(args.apk)
    
    # Validate APK exists
    if not os.path.isfile(apk_path):
        print(f"Error: APK file not found: {apk_path}")
        return 1
    
    # Parse tool paths if provided
    tool_paths = parse_tool_paths(args.tools)
    
    try:
        # Create and run Interceptra
        interceptor = Interceptra(
            apk=apk_path,
            verbose=args.verbose,
            tool_paths=tool_paths,
            keep_files=args.keep_files
        )
        
        success = interceptor.cut()
        
        if success:
            print("[+] Interceptra completed! The APK has been patched to allow proxy interception.")
            return 0
        else:
            print("[!] Interceptra failed to patch the APK.")
            return 1
            
    except Exception as e:
        print(f"[!] Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())