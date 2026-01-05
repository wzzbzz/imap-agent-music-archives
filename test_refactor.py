#!/usr/bin/env python3
"""
Quick test script to validate the refactored email archiving system
"""

import sys
import os

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflows import list_workflows, get_workflow, WORKFLOWS


def test_workflows():
    """Test that all workflows are properly configured"""
    print("🧪 Testing Workflow Configurations...\n")
    
    workflows = list_workflows()
    print(f"✓ Found {len(workflows)} workflows: {', '.join(workflows)}\n")
    
    for name in workflows:
        print(f"Testing: {name}")
        workflow = get_workflow(name)
        
        # Test basic properties
        assert workflow.name == name, f"Name mismatch for {name}"
        assert workflow.base_dir, f"Missing base_dir for {name}"
        assert workflow.folder_pattern, f"Missing folder_pattern for {name}"
        
        # Test IMAP args conversion
        imap_args = workflow.to_imap_args()
        assert "folder" in imap_args, f"Missing folder in IMAP args for {name}"
        assert "base_dir" in imap_args, f"Missing base_dir in IMAP args for {name}"
        
        # Test release number extraction
        test_subjects = [
            f"Test Issue 42",
            f"Test Volume 7",
            f"Test #{workflow.release_indicator} 99"
        ]
        for subject in test_subjects:
            number = workflow.extract_release_number(subject)
            if number != "unknown":
                print(f"  ✓ Extracted '{number}' from '{subject}'")
        
        # Test folder name generation
        folder = workflow.get_folder_name("42")
        print(f"  ✓ Folder pattern: {folder}")
        
        # Test processors
        print(f"  ✓ {len(workflow.attachment_processors)} attachment processors configured")
        
        print()
    
    print("✅ All workflow tests passed!\n")


def test_handlers():
    """Test that all handlers are registered"""
    print("🧪 Testing Attachment Handlers...\n")
    
    from attachment_handlers import HANDLERS
    
    print(f"✓ Found {len(HANDLERS)} registered handlers:")
    for name in HANDLERS.keys():
        print(f"  • {name}")
    
    print()
    
    # Check that workflow processors reference valid handlers
    print("Checking workflow → handler references...")
    for workflow_name in list_workflows():
        workflow = get_workflow(workflow_name)
        for processor in workflow.attachment_processors:
            assert processor.handler in HANDLERS, \
                f"Unknown handler '{processor.handler}' in {workflow_name}"
            print(f"  ✓ {workflow_name}.{processor.name} → {processor.handler}")
    
    print("\n✅ All handler tests passed!\n")


def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing Module Imports...\n")
    
    modules = [
        "workflows",
        "email_processor",
        "attachment_handlers",
        "imap_utils",
        "utils",
    ]
    
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except Exception as e:
            print(f"✗ {module_name}: {e}")
            return False
    
    print("\n✅ All imports successful!\n")
    return True


def main():
    print("\n" + "="*60)
    print("Email Archiving System - Validation Tests")
    print("="*60 + "\n")
    
    try:
        if not test_imports():
            sys.exit(1)
        
        test_workflows()
        test_handlers()
        
        print("="*60)
        print("🎉 All tests passed! System is ready to use.")
        print("="*60 + "\n")
        
        print("Try these commands:")
        print("  python archive_cli.py list")
        print("  python archive_cli.py show sonic_twist")
        print("  python archive_cli.py status sonic_twist")
        print()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
