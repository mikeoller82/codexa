"""
Tool Testing Framework for Codexa.

Provides automated testing capabilities for tools including unit tests,
integration tests, and behavioral testing.
"""

import asyncio
import time
from typing import Dict, List, Set, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum

from .tool_interface import Tool, ToolResult, ToolContext, ToolStatus
from .tool_validator import ToolValidator, ValidationReport


class TestType(Enum):
    """Types of tests that can be performed."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    STRESS = "stress"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestCase:
    """Represents a single test case."""
    
    name: str
    test_type: TestType
    description: str
    test_function: Callable
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    timeout: float = 30.0
    expected_result: Optional[Any] = None
    tags: List[str] = field(default_factory=list)
    
    # Runtime data
    status: TestStatus = TestStatus.PENDING
    execution_time: float = 0.0
    error_message: Optional[str] = None
    actual_result: Optional[Any] = None
    timestamp: Optional[datetime] = None


@dataclass
class TestSuite:
    """Collection of related test cases."""
    
    name: str
    tool_name: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_suite: Optional[Callable] = None
    teardown_suite: Optional[Callable] = None
    
    @property
    def passed_tests(self) -> List[TestCase]:
        """Get list of passed test cases."""
        return [test for test in self.test_cases if test.status == TestStatus.PASSED]
    
    @property
    def failed_tests(self) -> List[TestCase]:
        """Get list of failed test cases."""
        return [test for test in self.test_cases if test.status == TestStatus.FAILED]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = len(self.test_cases)
        if total == 0:
            return 0.0
        passed = len(self.passed_tests)
        return passed / total


@dataclass
class TestResult:
    """Results of running a test suite."""
    
    suite_name: str
    tool_name: str
    start_time: datetime
    end_time: datetime
    test_cases: List[TestCase]
    validation_report: Optional[ValidationReport] = None
    
    @property
    def total_tests(self) -> int:
        return len(self.test_cases)
    
    @property
    def passed_tests(self) -> int:
        return sum(1 for test in self.test_cases if test.status == TestStatus.PASSED)
    
    @property
    def failed_tests(self) -> int:
        return sum(1 for test in self.test_cases if test.status == TestStatus.FAILED)
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def execution_time(self) -> float:
        return (self.end_time - self.start_time).total_seconds()


class ToolTester:
    """
    Comprehensive testing framework for Codexa tools.
    
    Features:
    - Automated test discovery and execution
    - Multiple test types (unit, integration, performance, etc.)
    - Test suite management
    - Integration with validation framework
    - Performance benchmarking
    - Test reporting and analytics
    """
    
    def __init__(self, validator: Optional[ToolValidator] = None):
        """Initialize tool testing framework."""
        self.logger = logging.getLogger("codexa.tools.testing")
        self.validator = validator or ToolValidator()
        
        # Test management
        self._test_suites: Dict[str, TestSuite] = {}
        self._test_history: List[TestResult] = []
        
        # Statistics
        self._tests_executed = 0
        self._tools_tested = set()
        
        self.logger.info("Tool testing framework initialized")
    
    def create_test_suite(self, name: str, tool_name: str) -> TestSuite:
        """Create a new test suite."""
        suite = TestSuite(name=name, tool_name=tool_name)
        self._test_suites[name] = suite
        return suite
    
    def add_test_case(self, 
                     suite_name: str,
                     test_name: str,
                     test_type: TestType,
                     description: str,
                     test_function: Callable,
                     **kwargs) -> TestCase:
        """Add a test case to a suite."""
        if suite_name not in self._test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
        
        test_case = TestCase(
            name=test_name,
            test_type=test_type,
            description=description,
            test_function=test_function,
            **kwargs
        )
        
        self._test_suites[suite_name].test_cases.append(test_case)
        return test_case
    
    async def run_test_suite(self, 
                           suite_name: str,
                           tool: Tool,
                           context: Optional[ToolContext] = None,
                           include_validation: bool = True) -> TestResult:
        """Run a complete test suite."""
        if suite_name not in self._test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
        
        suite = self._test_suites[suite_name]
        start_time = datetime.now()
        
        self.logger.info(f"Running test suite '{suite_name}' for tool '{tool.name}'")
        
        # Create test context if not provided
        if context is None:
            context = ToolContext(
                current_path="/tmp",
                user_request="test execution"
            )
        
        # Run suite setup
        if suite.setup_suite:
            try:
                await self._run_async_or_sync(suite.setup_suite, tool, context)
            except Exception as e:
                self.logger.error(f"Suite setup failed: {e}")
        
        # Run validation if requested
        validation_report = None
        if include_validation:
            try:
                validation_report = await self.validator.validate_tool(tool, context)
                self.logger.info(f"Tool validation completed: score {validation_report.get_score():.2f}")
            except Exception as e:
                self.logger.warning(f"Tool validation failed: {e}")
        
        # Execute test cases
        for test_case in suite.test_cases:
            await self._run_test_case(test_case, tool, context)
            self._tests_executed += 1
        
        # Run suite teardown
        if suite.teardown_suite:
            try:
                await self._run_async_or_sync(suite.teardown_suite, tool, context)
            except Exception as e:
                self.logger.error(f"Suite teardown failed: {e}")
        
        end_time = datetime.now()
        self._tools_tested.add(tool.name)
        
        # Create test result
        result = TestResult(
            suite_name=suite_name,
            tool_name=tool.name,
            start_time=start_time,
            end_time=end_time,
            test_cases=suite.test_cases.copy(),
            validation_report=validation_report
        )
        
        self._test_history.append(result)
        
        self.logger.info(f"Test suite '{suite_name}' completed: "
                        f"{result.passed_tests}/{result.total_tests} passed "
                        f"({result.success_rate:.1%}), {result.execution_time:.3f}s")
        
        return result
    
    async def _run_test_case(self, test_case: TestCase, tool: Tool, context: ToolContext) -> None:
        """Run a single test case."""
        test_case.status = TestStatus.RUNNING
        test_case.timestamp = datetime.now()
        
        start_time = time.time()
        
        try:
            self.logger.debug(f"Running test: {test_case.name}")
            
            # Run setup if provided
            if test_case.setup_function:
                await self._run_async_or_sync(test_case.setup_function, tool, context)
            
            # Run the actual test with timeout
            test_result = await asyncio.wait_for(
                self._run_async_or_sync(test_case.test_function, tool, context),
                timeout=test_case.timeout
            )
            
            test_case.actual_result = test_result
            
            # Check expected result if provided
            if test_case.expected_result is not None:
                if test_result != test_case.expected_result:
                    test_case.status = TestStatus.FAILED
                    test_case.error_message = f"Expected {test_case.expected_result}, got {test_result}"
                else:
                    test_case.status = TestStatus.PASSED
            else:
                # If no expected result, consider any non-exception result as pass
                test_case.status = TestStatus.PASSED
            
            # Run teardown if provided
            if test_case.teardown_function:
                await self._run_async_or_sync(test_case.teardown_function, tool, context)
        
        except asyncio.TimeoutError:
            test_case.status = TestStatus.FAILED
            test_case.error_message = f"Test timeout after {test_case.timeout}s"
            self.logger.warning(f"Test {test_case.name} timed out")
        
        except Exception as e:
            test_case.status = TestStatus.FAILED
            test_case.error_message = str(e)
            self.logger.warning(f"Test {test_case.name} failed: {e}")
        
        finally:
            test_case.execution_time = time.time() - start_time
    
    async def _run_async_or_sync(self, func: Callable, tool: Tool, context: ToolContext) -> Any:
        """Run function whether it's async or sync."""
        if asyncio.iscoroutinefunction(func):
            return await func(tool, context)
        else:
            return func(tool, context)
    
    def create_basic_test_suite(self, tool: Tool) -> str:
        """Create a basic test suite for any tool."""
        suite_name = f"{tool.name}_basic_tests"
        suite = self.create_test_suite(suite_name, tool.name)
        
        # Basic interface tests
        self.add_test_case(
            suite_name, "test_can_handle_request", TestType.UNIT,
            "Test can_handle_request returns valid confidence",
            self._test_can_handle_request
        )
        
        self.add_test_case(
            suite_name, "test_execute_basic", TestType.UNIT,
            "Test basic tool execution",
            self._test_execute_basic
        )
        
        self.add_test_case(
            suite_name, "test_execute_returns_tool_result", TestType.UNIT,
            "Test execute returns ToolResult",
            self._test_execute_returns_tool_result
        )
        
        self.add_test_case(
            suite_name, "test_properties", TestType.UNIT,
            "Test required tool properties",
            self._test_properties
        )
        
        # Performance test
        self.add_test_case(
            suite_name, "test_performance", TestType.PERFORMANCE,
            "Test execution performance",
            self._test_performance,
            timeout=15.0
        )
        
        return suite_name
    
    async def _test_can_handle_request(self, tool: Tool, context: ToolContext) -> bool:
        """Test can_handle_request method."""
        confidence = tool.can_handle_request("test request", context)
        
        # Should return a number between 0.0 and 1.0
        assert isinstance(confidence, (int, float)), f"Expected numeric confidence, got {type(confidence)}"
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} not in range [0.0, 1.0]"
        
        return True
    
    async def _test_execute_basic(self, tool: Tool, context: ToolContext) -> bool:
        """Test basic tool execution."""
        result = await tool.safe_execute(context)
        
        # Should not raise exception and return something
        assert result is not None, "Tool execution returned None"
        
        return True
    
    async def _test_execute_returns_tool_result(self, tool: Tool, context: ToolContext) -> bool:
        """Test that execute returns ToolResult."""
        result = await tool.safe_execute(context)
        
        assert isinstance(result, ToolResult), f"Expected ToolResult, got {type(result)}"
        assert hasattr(result, 'success'), "ToolResult missing 'success' attribute"
        assert hasattr(result, 'tool_name'), "ToolResult missing 'tool_name' attribute"
        
        return True
    
    def _test_properties(self, tool: Tool, context: ToolContext) -> bool:
        """Test required tool properties."""
        required_props = ['name', 'description', 'category', 'version']
        
        for prop in required_props:
            assert hasattr(tool, prop), f"Tool missing required property: {prop}"
            value = getattr(tool, prop)
            assert value is not None, f"Property {prop} is None"
            assert str(value).strip(), f"Property {prop} is empty"
        
        return True
    
    async def _test_performance(self, tool: Tool, context: ToolContext) -> bool:
        """Test tool performance."""
        start_time = time.time()
        result = await tool.safe_execute(context)
        execution_time = time.time() - start_time
        
        # Performance threshold (configurable)
        assert execution_time < 10.0, f"Tool execution too slow: {execution_time:.3f}s"
        assert isinstance(result, ToolResult), "Performance test must return ToolResult"
        
        return True
    
    def run_benchmark(self, tool: Tool, iterations: int = 10) -> Dict[str, Any]:
        """Run performance benchmark on a tool."""
        async def benchmark():
            context = ToolContext(
                current_path="/tmp",
                user_request="benchmark test"
            )
            
            times = []
            results = []
            
            for i in range(iterations):
                start_time = time.time()
                result = await tool.safe_execute(context)
                execution_time = time.time() - start_time
                
                times.append(execution_time)
                results.append(result.success if isinstance(result, ToolResult) else False)
            
            return {
                'tool_name': tool.name,
                'iterations': iterations,
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'success_rate': sum(results) / len(results),
                'times': times
            }
        
        return asyncio.run(benchmark())
    
    def generate_test_report(self, test_result: TestResult) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        failed_tests = [test for test in test_result.test_cases if test.status == TestStatus.FAILED]
        
        return {
            'suite_name': test_result.suite_name,
            'tool_name': test_result.tool_name,
            'timestamp': test_result.start_time.isoformat(),
            'execution_time': test_result.execution_time,
            'summary': {
                'total_tests': test_result.total_tests,
                'passed_tests': test_result.passed_tests,
                'failed_tests': test_result.failed_tests,
                'success_rate': test_result.success_rate,
            },
            'test_details': [
                {
                    'name': test.name,
                    'type': test.test_type.value,
                    'status': test.status.value,
                    'execution_time': test.execution_time,
                    'error_message': test.error_message
                }
                for test in test_result.test_cases
            ],
            'failed_tests': [
                {
                    'name': test.name,
                    'description': test.description,
                    'error': test.error_message,
                    'execution_time': test.execution_time
                }
                for test in failed_tests
            ],
            'validation_report': (
                self.validator.export_report(test_result.validation_report) 
                if test_result.validation_report else None
            )
        }
    
    def get_testing_stats(self) -> Dict[str, Any]:
        """Get testing framework statistics."""
        total_tests = sum(len(result.test_cases) for result in self._test_history)
        total_passed = sum(result.passed_tests for result in self._test_history)
        
        return {
            'total_test_runs': len(self._test_history),
            'tools_tested': len(self._tools_tested),
            'total_tests_executed': total_tests,
            'total_tests_passed': total_passed,
            'overall_success_rate': total_passed / max(1, total_tests),
            'test_suites_available': len(self._test_suites)
        }