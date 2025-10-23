#!/usr/bin/env python3
"""
Test Suite for Broadway Form D Analysis
Tests filtering logic and XML parsing robustness
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from collect_form_d_data import BroadwayFormDCollector
from form_d_parser import FormDParser

# Test colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test(test_name):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{test_name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

def print_result(test_case, expected, actual, passed):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} | {test_case}")
    if not passed:
        print(f"       Expected: {expected}")
        print(f"       Got:      {actual}")

def test_broadway_filtering():
    """Test the strict Broadway theatrical filtering"""
    print_test("TEST 1: Broadway Theatrical Filtering")

    collector = BroadwayFormDCollector(Path('/tmp'))

    test_cases = [
        # Should ACCEPT - Known shows
        ("Hamilton Productions LLC", True, "Known Broadway show"),
        ("Hadestown Broadway LLC", True, "Known Broadway show"),
        ("Lion King Theatrical Productions", True, "Known Broadway show"),
        ("Wicked the Musical LLC", True, "Known Broadway show"),

        # Should ACCEPT - Broadway + production terms
        ("Broadway Musical Productions LLC", True, "Broadway + production"),
        ("New Broadway Show LLC", True, "Broadway + show"),
        ("Broadway Theatrical Group LP", True, "Broadway + theatrical"),

        # Should ACCEPT - Theatrical + production terms
        ("Theatrical Productions Company LLC", True, "Theatrical + production"),
        ("Theatre Arts Production LLC", True, "Theatre + production"),
        ("Theater Production Group LP", True, "Theater + production"),

        # Should ACCEPT - Musical/Play + Production
        ("Original Musical Productions LLC", True, "Musical + production"),
        ("New Play Productions LP", True, "Play + production"),

        # Should REJECT - No theatrical terms
        ("Duraseal Pipe Coatings Company, LLC", False, "Industrial company"),
        ("ABC Production Manufacturing Inc", False, "Manufacturing company"),
        ("Real Estate Productions LLC", False, "Real estate"),
        ("Film Production Studios LLC", False, "Film (not theatre)"),

        # Should REJECT - Theatre terms but no production context
        ("Broadway Pizza LLC", False, "Broadway but not production"),
        ("Musical Instruments Corp", False, "Musical but not production"),
        ("Theatre Real Estate Holdings", False, "Theatre but not production"),

        # Should REJECT - Production but no theatre terms
        ("Oil Production Company LLC", False, "Oil production"),
        ("Agricultural Production LLC", False, "Agricultural"),
        ("Media Production Group", False, "Generic media"),

        # Edge cases
        ("The Play That Goes Wrong Productions LLC", True, "Play + production"),
        ("Off-Broadway Theatre Company LLC", True, "Theatre + company"),
        ("Musical Theater Productions of NY LLC", True, "Musical theater + production"),
        ("", False, "Empty string"),
    ]

    passed = 0
    failed = 0

    for entity_name, should_match, description in test_cases:
        is_theatrical, reason = collector.is_theatrical(entity_name)
        test_passed = (is_theatrical == should_match)

        if test_passed:
            passed += 1
        else:
            failed += 1

        expected = "ACCEPT" if should_match else "REJECT"
        actual = "ACCEPT" if is_theatrical else "REJECT"

        print_result(
            f"{entity_name[:50]:<50} ({description})",
            expected,
            f"{actual} ({reason})",
            test_passed
        )

    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}")
    return failed == 0


def test_xml_parsing():
    """Test XML parsing with various file formats"""
    print_test("TEST 2: XML Parsing Robustness")

    parser = FormDParser()

    test_cases = [
        # Valid XML
        (
            """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission>
    <formData>
        <issuer>
            <entityName>Test Broadway LLC</entityName>
        </issuer>
    </formData>
</edgarSubmission>""",
            "Valid XML",
            True
        ),

        # XML without declaration
        (
            """<edgarSubmission>
    <formData>
        <issuer>
            <entityName>Test Show</entityName>
        </issuer>
    </formData>
</edgarSubmission>""",
            "XML without <?xml declaration",
            True
        ),

        # HTML content (should be rejected)
        (
            """<!DOCTYPE html>
<html>
<head><title>Form D</title></head>
<body>This is HTML</body>
</html>""",
            "HTML content",
            False
        ),

        # Plain text (should be rejected)
        (
            "This is just plain text, not XML at all",
            "Plain text",
            False
        ),

        # Empty content
        (
            "",
            "Empty string",
            False
        ),

        # Whitespace only
        (
            "   \n\t  ",
            "Whitespace only",
            False
        ),

        # Malformed XML
        (
            """<?xml version="1.0"?>
<root>
    <unclosed>
</root>""",
            "Malformed XML (unclosed tag)",
            False
        ),

        # JSON (should be rejected)
        (
            '{"formType": "D", "issuerName": "Test LLC"}',
            "JSON content",
            False
        ),
    ]

    passed = 0
    failed = 0

    for xml_content, description, should_parse in test_cases:
        result = parser.parse_xml_filing(xml_content, "test-accession-123")
        parsed_successfully = (result is not None)

        test_passed = (parsed_successfully == should_parse)

        if test_passed:
            passed += 1
        else:
            failed += 1

        expected = "PARSE" if should_parse else "REJECT"
        actual = "PARSED" if parsed_successfully else "REJECTED"

        print_result(
            f"{description:<50}",
            expected,
            actual,
            test_passed
        )

    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}")
    return failed == 0


def test_filtering_strictness():
    """Test that filtering is strict enough to avoid false positives"""
    print_test("TEST 3: Filtering Strictness (False Positive Prevention)")

    collector = BroadwayFormDCollector(Path('/tmp'))

    # These are ALL real company names that should be REJECTED
    false_positive_tests = [
        "Duraseal Pipe Coatings Company, LLC",
        "ABC Production Equipment Manufacturing",
        "XYZ Musical Instrument Productions",
        "Broadway Pizza and Restaurant LLC",
        "Theatre Seating Manufacturing Corp",
        "Film Production Studios of America",
        "Video Production Services LLC",
        "Agricultural Production Holdings",
        "Oil and Gas Production Partners LP",
        "Real Estate Production Fund",
        "Software Production Company",
        "Manufacturing Production Systems LLC",
        "Broadway Street Holdings LLC",
        "Theatre District Real Estate",
        "Musical Arts Education Foundation",
        "Play Equipment Manufacturing",
        "Production Consulting Group",
        "Industrial Production LLC",
        "Media Production Network",
        "Content Production Services",
    ]

    passed = 0
    failed = 0

    for entity_name in false_positive_tests:
        is_theatrical, reason = collector.is_theatrical(entity_name)

        test_passed = (not is_theatrical)  # Should all be rejected

        if test_passed:
            passed += 1
        else:
            failed += 1

        print_result(
            f"{entity_name:<50}",
            "REJECT",
            f"{'REJECTED' if not is_theatrical else f'ACCEPTED ({reason})'}",
            test_passed
        )

    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}")
    return failed == 0


def test_filtering_recall():
    """Test that filtering catches real Broadway productions"""
    print_test("TEST 4: Filtering Recall (Real Broadway Shows)")

    collector = BroadwayFormDCollector(Path('/tmp'))

    # Real or realistic Broadway production names that should be ACCEPTED
    real_broadway_tests = [
        "Hamilton Broadway Production LLC",
        "Wicked National Tour Productions LP",
        "The Lion King Theatrical LLC",
        "Hadestown Broadway Productions",
        "Moulin Rouge! The Musical LLC",
        "Chicago The Musical Productions",
        "Dear Evan Hansen Broadway LLC",
        "Come From Away Productions Limited Partnership",
        "Broadway Theatrical Productions Company",
        "New Broadway Musical LLC",
        "Off-Broadway Theatre Productions",
        "Regional Theatre Production Company",
        "Original Musical Production LLC",
        "Contemporary Play Productions LP",
        "Theatrical Production Group LLC",
        "Broadway Show Productions",
        "Theatre Production Partners",
        "Musical Theatre Productions NYC",
        "Dramatic Play Productions LLC",
        "Cabaret Revival Productions",
    ]

    passed = 0
    failed = 0

    for entity_name in real_broadway_tests:
        is_theatrical, reason = collector.is_theatrical(entity_name)

        test_passed = is_theatrical  # Should all be accepted

        if test_passed:
            passed += 1
        else:
            failed += 1

        print_result(
            f"{entity_name:<50}",
            "ACCEPT",
            f"{'ACCEPTED (' + reason + ')' if is_theatrical else 'REJECTED'}",
            test_passed
        )

    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}")
    return failed == 0


def run_all_tests():
    """Run all test suites"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("BROADWAY FORM D ANALYSIS - TEST SUITE")
    print(f"{'='*70}{Colors.END}\n")

    results = []

    # Run all test suites
    results.append(("Theatrical Filtering", test_broadway_filtering()))
    results.append(("XML Parsing", test_xml_parsing()))
    results.append(("False Positive Prevention", test_filtering_strictness()))
    results.append(("Broadway Show Recall", test_filtering_recall()))

    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}{Colors.END}\n")

    all_passed = True
    for test_name, passed in results:
        status = f"{Colors.GREEN}✓ PASSED{Colors.END}" if passed else f"{Colors.RED}✗ FAILED{Colors.END}"
        print(f"{status} | {test_name}")
        if not passed:
            all_passed = False

    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.END}")
        print(f"\n{Colors.GREEN}The fixes are working correctly. You can run the real data collection with confidence.{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.END}")
        print(f"\n{Colors.RED}Please review the failures above before running real data collection.{Colors.END}")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
