#!/usr/bin/env python3
"""
Test Validator for UnifiedCardGenerator class.

This test script validates:
1. Module imports successfully
2. All constants are accessible and have correct values
3. Class can be instantiated successfully
4. Basic functionality works without external dependencies
"""

import sys
import os
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_results_summary() -> Dict[str, Any]:
    """Initialize test results summary."""
    return {
        "import_success": False,
        "constants_validation": False,
        "class_instantiation": False,
        "basic_functionality": False,
        "errors": [],
        "warnings": [],
        "test_details": {}
    }

def validate_imports() -> tuple[bool, Optional[Any], List[str]]:
    """Test importing the UnifiedCardGenerator class."""
    errors = []
    warnings = []
    
    try:
        print("🔍 Testing module imports...")
        
        # Test importing the main class
        from generate_card import UnifiedCardGenerator
        print("   ✅ UnifiedCardGenerator imported successfully")
        
        # Check if optional dependencies are available
        try:
            from playwright.async_api import async_playwright
            print("   ✅ Playwright available")
        except ImportError:
            warnings.append("Playwright not available - card rendering may not work")
            print("   ⚠️  Playwright not available")
        
        try:
            from openai import OpenAI
            print("   ✅ OpenAI available")
        except ImportError:
            warnings.append("OpenAI not available - LLM features disabled")
            print("   ⚠️  OpenAI not available")
        
        try:
            from generate_unified import UnifiedImageGenerator
            print("   ✅ UnifiedImageGenerator available")
        except ImportError as e:
            errors.append(f"UnifiedImageGenerator import failed: {e}")
            print(f"   ❌ UnifiedImageGenerator import failed: {e}")
        
        return True, UnifiedCardGenerator, errors + warnings
        
    except ImportError as e:
        errors.append(f"Failed to import UnifiedCardGenerator: {e}")
        print(f"   ❌ Import failed: {e}")
        return False, None, errors
    except Exception as e:
        errors.append(f"Unexpected error during import: {e}")
        print(f"   ❌ Unexpected error: {e}")
        return False, None, errors

def validate_constants(generator_class) -> tuple[bool, Dict[str, Any], List[str]]:
    """Validate all constants defined in UnifiedCardGenerator."""
    print("\n🔍 Testing constants accessibility and values...")
    
    constants_info = {}
    errors = []
    all_passed = True
    
    # Expected constants with their expected values and types
    expected_constants = {
        # Image dimensions constants
        "MTG_ARTWORK_WIDTH": (626, int),
        "MTG_ARTWORK_HEIGHT": (475, int),
        
        # Browser viewport dimensions
        "BROWSER_VIEWPORT_WIDTH": (1600, int),
        "BROWSER_VIEWPORT_HEIGHT": (2400, int),
        
        # Timeout values (in milliseconds)
        "SHORT_TIMEOUT": (500, int),
        "CARD_RENDER_TIMEOUT": (5000, int),
        "ARTWORK_LOAD_TIMEOUT": (3000, int),
        "PLACEHOLDER_TIMEOUT": (1000, int),
        
        # Image processing constants
        "IMAGE_QUALITY": (95, int),
        "CARD_SCALE_FACTOR": (4, int),
        
        # File formatting constants
        "JSON_INDENT": (2, int),
        
        # File name sanitization characters
        "INVALID_FILENAME_CHARS": (None, list),  # List content will be validated separately
    }
    
    for const_name, (expected_value, expected_type) in expected_constants.items():
        try:
            if hasattr(generator_class, const_name):
                actual_value = getattr(generator_class, const_name)
                constants_info[const_name] = {
                    "value": actual_value,
                    "type": type(actual_value).__name__,
                    "accessible": True
                }
                
                # Validate type
                if not isinstance(actual_value, expected_type):
                    errors.append(f"Constant {const_name} has wrong type. Expected {expected_type.__name__}, got {type(actual_value).__name__}")
                    all_passed = False
                    print(f"   ❌ {const_name}: Wrong type ({type(actual_value).__name__})")
                    continue
                
                # Validate specific expected values (skip None expected_value)
                if expected_value is not None and actual_value != expected_value:
                    errors.append(f"Constant {const_name} has wrong value. Expected {expected_value}, got {actual_value}")
                    all_passed = False
                    print(f"   ❌ {const_name}: Wrong value ({actual_value})")
                    continue
                
                # Special validation for INVALID_FILENAME_CHARS
                if const_name == "INVALID_FILENAME_CHARS":
                    expected_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\u202f", "\u00a0", "—", "–"]
                    if not all(char in actual_value for char in expected_chars):
                        missing_chars = [char for char in expected_chars if char not in actual_value]
                        errors.append(f"INVALID_FILENAME_CHARS missing expected characters: {missing_chars}")
                        all_passed = False
                        print(f"   ❌ {const_name}: Missing characters {missing_chars}")
                        continue
                    
                    constants_info[const_name]["expected_chars_count"] = len(expected_chars)
                    constants_info[const_name]["actual_chars_count"] = len(actual_value)
                
                print(f"   ✅ {const_name}: {actual_value}")
                
            else:
                constants_info[const_name] = {"accessible": False}
                errors.append(f"Constant {const_name} not found in class")
                all_passed = False
                print(f"   ❌ {const_name}: Not found")
                
        except Exception as e:
            constants_info[const_name] = {"error": str(e)}
            errors.append(f"Error accessing constant {const_name}: {e}")
            all_passed = False
            print(f"   ❌ {const_name}: Error accessing ({e})")
    
    return all_passed, constants_info, errors

def validate_class_instantiation(generator_class) -> tuple[bool, Optional[Any], List[str]]:
    """Test that the class can be instantiated successfully."""
    print("\n🔍 Testing class instantiation...")
    
    errors = []
    
    try:
        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = temp_path / "cards"
            images_dir = temp_path / "images"
            
            # Test basic instantiation
            print("   Testing basic instantiation...")
            generator = generator_class(
                output_dir=str(output_dir),
                images_dir=str(images_dir)
            )
            
            # Verify instance attributes
            print("   Checking instance attributes...")
            required_attributes = [
                'base_dir', 'output_dir', 'images_dir', 'image_generator',
                'has_image_api', 'llm_client', 'has_llm'
            ]
            
            for attr in required_attributes:
                if not hasattr(generator, attr):
                    errors.append(f"Missing required attribute: {attr}")
                    print(f"   ❌ Missing attribute: {attr}")
                else:
                    print(f"   ✅ Attribute present: {attr}")
            
            # Verify directories were created
            if not output_dir.exists():
                errors.append("Output directory was not created")
                print("   ❌ Output directory not created")
            else:
                print("   ✅ Output directory created")
            
            if not images_dir.exists():
                errors.append("Images directory was not created")
                print("   ❌ Images directory not created")
            else:
                print("   ✅ Images directory created")
            
            # Test instantiation with API model parameter
            print("   Testing instantiation with API model...")
            generator_with_model = generator_class(
                output_dir=str(output_dir),
                images_dir=str(images_dir),
                api_model="sdxl"
            )
            print("   ✅ Instantiation with API model successful")
            
            return len(errors) == 0, generator, errors
            
    except Exception as e:
        error_msg = f"Failed to instantiate class: {e}"
        errors.append(error_msg)
        print(f"   ❌ {error_msg}")
        print(f"   Stack trace: {traceback.format_exc()}")
        return False, None, errors

def validate_basic_functionality(generator) -> tuple[bool, Dict[str, Any], List[str]]:
    """Test basic functionality that doesn't require external APIs."""
    print("\n🔍 Testing basic functionality...")
    
    functionality_results = {}
    errors = []
    warnings = []
    all_passed = True
    
    try:
        # Test _extract_colors method
        print("   Testing _extract_colors method...")
        test_mana_costs = [
            ("{2}{R}{R}", ["R"]),
            ("{1}{U}{B}", ["U", "B"]),
            ("{W}{U}{B}{R}{G}", ["W", "U", "B", "R", "G"]),
            ("{5}", ["C"]),
            ("", ["C"])
        ]
        
        colors_test_passed = True
        for mana_cost, expected_colors in test_mana_costs:
            try:
                result = generator._extract_colors(mana_cost)
                if result != expected_colors:
                    errors.append(f"_extract_colors({mana_cost}) returned {result}, expected {expected_colors}")
                    colors_test_passed = False
                    print(f"   ❌ _extract_colors({mana_cost}): got {result}, expected {expected_colors}")
                else:
                    print(f"   ✅ _extract_colors({mana_cost}): {result}")
            except Exception as e:
                errors.append(f"_extract_colors({mana_cost}) failed: {e}")
                colors_test_passed = False
                print(f"   ❌ _extract_colors({mana_cost}) failed: {e}")
        
        functionality_results["extract_colors"] = {
            "passed": colors_test_passed,
            "tests_run": len(test_mana_costs)
        }
        if not colors_test_passed:
            all_passed = False
        
        # Test generate_from_prompt method (fallback mode without LLM)
        print("   Testing generate_from_prompt method...")
        try:
            test_prompts = [
                "a fire dragon",
                "Percy Jackson demigod",
                "a powerful wizard"
            ]
            
            prompt_test_passed = True
            for prompt in test_prompts:
                try:
                    result = generator.generate_from_prompt(prompt)
                    
                    # Validate result structure
                    required_fields = ["name", "mana_cost", "type_line", "oracle_text", "rarity", "colors"]
                    missing_fields = [field for field in required_fields if field not in result]
                    
                    if missing_fields:
                        errors.append(f"generate_from_prompt('{prompt}') missing fields: {missing_fields}")
                        prompt_test_passed = False
                        print(f"   ❌ generate_from_prompt('{prompt}'): missing {missing_fields}")
                    else:
                        print(f"   ✅ generate_from_prompt('{prompt}'): generated '{result['name']}'")
                        
                except Exception as e:
                    errors.append(f"generate_from_prompt('{prompt}') failed: {e}")
                    prompt_test_passed = False
                    print(f"   ❌ generate_from_prompt('{prompt}') failed: {e}")
            
            functionality_results["generate_from_prompt"] = {
                "passed": prompt_test_passed,
                "tests_run": len(test_prompts)
            }
            if not prompt_test_passed:
                all_passed = False
            
        except Exception as e:
            errors.append(f"generate_from_prompt testing failed: {e}")
            functionality_results["generate_from_prompt"] = {"passed": False, "error": str(e)}
            all_passed = False
            print(f"   ❌ generate_from_prompt testing failed: {e}")
        
        # Test filename sanitization (using constants)
        print("   Testing filename sanitization logic...")
        try:
            test_name = "Test/Name*With?Invalid<Characters>"
            safe_name = test_name
            for char in generator.INVALID_FILENAME_CHARS:
                safe_name = safe_name.replace(char, "_")
            safe_name = safe_name.replace(" ", "_").replace(",", "").replace("'", "")
            
            if "/" in safe_name or "*" in safe_name or "?" in safe_name:
                errors.append("Filename sanitization logic failed")
                all_passed = False
                print(f"   ❌ Filename sanitization failed: {safe_name}")
            else:
                print(f"   ✅ Filename sanitization: '{test_name}' -> '{safe_name}'")
                functionality_results["filename_sanitization"] = {"passed": True}
                
        except Exception as e:
            errors.append(f"Filename sanitization test failed: {e}")
            functionality_results["filename_sanitization"] = {"passed": False, "error": str(e)}
            all_passed = False
            print(f"   ❌ Filename sanitization test failed: {e}")
    
    except Exception as e:
        errors.append(f"Basic functionality testing failed: {e}")
        all_passed = False
        print(f"   ❌ Basic functionality testing failed: {e}")
    
    return all_passed, functionality_results, errors + warnings

def run_existing_tests() -> tuple[bool, str]:
    """Run existing test suite if available."""
    print("\n🔍 Checking for existing tests...")
    
    try:
        # Check if pytest is available
        import pytest
        
        # Run specific tests related to the card generator
        test_files = [
            "test_core.py",
            "test_models.py"
        ]
        
        existing_tests = []
        for test_file in test_files:
            test_path = PROJECT_ROOT / "tests" / test_file
            if test_path.exists():
                existing_tests.append(str(test_path))
        
        if existing_tests:
            print(f"   Found existing tests: {existing_tests}")
            # Note: We don't actually run pytest here to avoid dependency issues
            return True, f"Found {len(existing_tests)} existing test files"
        else:
            return False, "No existing relevant test files found"
            
    except ImportError:
        return False, "pytest not available"
    except Exception as e:
        return False, f"Error checking existing tests: {e}"

def main():
    """Main test validation function."""
    print("=" * 80)
    print("🧪 UNIFIED CARD GENERATOR VALIDATION TEST")
    print("=" * 80)
    
    results = test_results_summary()
    
    # Test 1: Module Import
    print("\n" + "=" * 60)
    print("TEST 1: MODULE IMPORT")
    print("=" * 60)
    
    import_success, generator_class, import_errors = validate_imports()
    results["import_success"] = import_success
    results["errors"].extend(import_errors)
    
    if not import_success:
        print("\n❌ CRITICAL FAILURE: Cannot proceed without successful import")
        print_final_report(results)
        return 1
    
    # Test 2: Constants Validation
    print("\n" + "=" * 60)
    print("TEST 2: CONSTANTS VALIDATION")
    print("=" * 60)
    
    constants_success, constants_info, constants_errors = validate_constants(generator_class)
    results["constants_validation"] = constants_success
    results["test_details"]["constants"] = constants_info
    results["errors"].extend(constants_errors)
    
    # Test 3: Class Instantiation
    print("\n" + "=" * 60)
    print("TEST 3: CLASS INSTANTIATION")
    print("=" * 60)
    
    instantiation_success, generator_instance, instantiation_errors = validate_class_instantiation(generator_class)
    results["class_instantiation"] = instantiation_success
    results["errors"].extend(instantiation_errors)
    
    # Test 4: Basic Functionality (only if instantiation succeeded)
    if instantiation_success and generator_instance:
        print("\n" + "=" * 60)
        print("TEST 4: BASIC FUNCTIONALITY")
        print("=" * 60)
        
        functionality_success, functionality_info, functionality_errors = validate_basic_functionality(generator_instance)
        results["basic_functionality"] = functionality_success
        results["test_details"]["functionality"] = functionality_info
        results["errors"].extend(functionality_errors)
    else:
        print("\n⏭️  SKIPPING: Basic functionality tests (instantiation failed)")
        results["warnings"].append("Basic functionality tests skipped due to instantiation failure")
    
    # Test 5: Check Existing Tests
    print("\n" + "=" * 60)
    print("TEST 5: EXISTING TESTS CHECK")
    print("=" * 60)
    
    existing_tests_success, existing_tests_info = run_existing_tests()
    results["test_details"]["existing_tests"] = {
        "available": existing_tests_success,
        "info": existing_tests_info
    }
    print(f"   {existing_tests_info}")
    
    # Final Report
    print_final_report(results)
    
    # Return exit code based on critical tests
    critical_tests = [results["import_success"], results["constants_validation"], results["class_instantiation"]]
    return 0 if all(critical_tests) else 1

def print_final_report(results: Dict[str, Any]):
    """Print comprehensive final report."""
    print("\n" + "=" * 80)
    print("📊 FINAL VALIDATION REPORT")
    print("=" * 80)
    
    # Test Results Summary
    print("\n🎯 TEST RESULTS SUMMARY:")
    test_results = [
        ("Module Import", results["import_success"]),
        ("Constants Validation", results["constants_validation"]),
        ("Class Instantiation", results["class_instantiation"]),
        ("Basic Functionality", results["basic_functionality"]),
    ]
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name:<20} : {status}")
    
    # Detailed Information
    if "constants" in results["test_details"]:
        print("\n📋 CONSTANTS DETAILS:")
        for const_name, const_info in results["test_details"]["constants"].items():
            if const_info.get("accessible", False):
                value = const_info.get("value", "N/A")
                type_name = const_info.get("type", "unknown")
                print(f"   {const_name:<25} : {value} ({type_name})")
            else:
                print(f"   {const_name:<25} : ❌ NOT ACCESSIBLE")
    
    if "functionality" in results["test_details"]:
        print("\n🔧 FUNCTIONALITY TESTS:")
        for func_name, func_info in results["test_details"]["functionality"].items():
            status = "✅ PASS" if func_info.get("passed", False) else "❌ FAIL"
            tests_run = func_info.get("tests_run", 0)
            print(f"   {func_name:<25} : {status} ({tests_run} tests)")
    
    # Errors and Warnings
    if results["errors"]:
        print(f"\n❌ ERRORS ({len(results['errors'])}):")
        for i, error in enumerate(results["errors"], 1):
            print(f"   {i}. {error}")
    
    if results["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        for i, warning in enumerate(results["warnings"], 1):
            print(f"   {i}. {warning}")
    
    # Overall Status
    critical_tests = [results["import_success"], results["constants_validation"], results["class_instantiation"]]
    all_critical_passed = all(critical_tests)
    
    print("\n" + "=" * 80)
    if all_critical_passed:
        if results["basic_functionality"]:
            print("🎉 OVERALL STATUS: ALL TESTS PASSED")
        else:
            print("✅ OVERALL STATUS: CRITICAL TESTS PASSED (Some basic functionality issues)")
    else:
        print("❌ OVERALL STATUS: CRITICAL TESTS FAILED")
    print("=" * 80)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)