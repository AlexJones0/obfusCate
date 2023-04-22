""" File: tests/test_complexity.py
Implements a few unit and integration tests for the code complexity metrics
implemented in the program, ensuring that each metric does indeed correctly
calculate the metrics that it is supposed to, and can correctly handle
dependencies (with caching) between metrics. 
"""
import unittest
from app.cli import *
from app.interaction import CSource
from app.obfuscation import *
from app.complexity import *
from tests import *

class TestComplexityMetrics(unittest.TestCase):
    """Implements unit and integration tests for complexity metrics """

    def __reset_caches(self) -> None:
        """Resests the caches of various complexity metric group subclasses,
        such that these can be re-used across unit tests. """
        AggregateUnit.cached = {}
        CyclomaticComplexityUnit.cached = {}
        HalsteadComplexityUnit.cached = {}

    def test_maintainability_missing_aggregates(self) -> None:
        """ Tests that the maintainability index will correctly skip
        calculation if no aggregate metrics have been previously computed. """
        self.__reset_caches()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [CyclomaticComplexityUnit(), HalsteadComplexityUnit(), CognitiveComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        maintainability = MaintainabilityUnit()
        maintainability.calculate_metrics(source, obfuscated)
        for _, val in maintainability.get_metrics():
            self.assertIn(val, ["N/A", ("N/A", "N/A")])
    
    def test_maintainability_missing_cyclomatic(self) -> None:
        """ Tests that the maintainability index will correctly skip
        calculation if no cyclomatic complexity metrics have been previously computed. """
        self.__reset_caches()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [AggregateUnit(), HalsteadComplexityUnit(), CognitiveComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        maintainability = MaintainabilityUnit()
        maintainability.calculate_metrics(source, obfuscated)
        for _, val in maintainability.get_metrics():
            self.assertIn(val, ["N/A", ("N/A", "N/A")])
    
    def test_maintainability_missing_halstead(self) -> None:
        """ Tests that the maintainability index will correctly skip
        calculation if no Halstead metrics have been previously computed. """
        self.__reset_caches()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [AggregateUnit(), CyclomaticComplexityUnit(), CognitiveComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        maintainability = MaintainabilityUnit()
        maintainability.calculate_metrics(source, obfuscated)
        for _, val in maintainability.get_metrics():
            self.assertIn(val, ["N/A", ("N/A", "N/A")])
    
    def test_maintainability_all_predecessors(self) -> None:
        """ Tests that the maintainability index will correclty calculate
        some values if all required predecessor metrics have been computed. """
        # Check that the list of required predecessors match first.
        self.__reset_caches()
        self.assertEqual(MaintainabilityUnit.predecessors, [AggregateUnit, CyclomaticComplexityUnit, HalsteadComplexityUnit])
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [AggregateUnit(), CyclomaticComplexityUnit(), HalsteadComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        maintainability = MaintainabilityUnit()
        maintainability.calculate_metrics(source, obfuscated)
        # Check that the list of metrics is non-empty and contains no "N/A" values.
        for _, val in maintainability.get_metrics():
            self.assertNotIn(val, ["N/A", ("N/A", "N/A")])
        self.assertNotEqual(len(maintainability.get_metrics()), 0)
    
    def test_aggregate_metric_presence(self) -> None:
        """ Tests that all required output aggregate metrics are calculated by the
        AggregateUnit aggregate metric group class, independent of all other metric
        groups. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = AggregateUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        self.assertNotEqual(len(metrics), 0)
        metric_names = [m[0] for m in metrics]
        for metric in unit.positions.keys():
            self.assertIn(metric, metric_names)
    
    def test_cyclomatic_metric_presence(self) -> None:
        """ Tests that all required output cyclomatic complexity metrics are calculated 
        by the CyclomaticComplexityUnit metric group class, independent of all other 
        metric groups. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CyclomaticComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        self.assertNotEqual(len(metrics), 0)
        metric_names = [m[0] for m in metrics]
        for metric in unit.positions.keys():
            self.assertIn(metric, metric_names)
    
    def test_halstead_metric_presence(self) -> None:
        """ Tests that all required output Halstead measure metrics are calculated
        by the HalsteadComplexityUnit metric group class, independent of all other
        metrics groups. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = HalsteadComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        self.assertNotEqual(len(metrics), 0)
        metric_names = [m[0] for m in metrics]
        for metric in unit.positions.keys():
            self.assertIn(metric, metric_names)
    
    def test_cognitive_metric_presence(self) -> None:
        """ Tests that all required output Cognitive complexity metrics are calculated
        by the CognitiveComplexityUnit metric group class, independent of all other
        metrics groups. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CognitiveComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        self.assertNotEqual(len(metrics), 0)
        metric_names = [m[0] for m in metrics]
        for metric in unit.positions.keys():
            self.assertIn(metric, metric_names)
    
    def test_maintainability_metric_presence(self) -> None:
        """ Tests that all required output Maintainability Index metrics are calculated
        by the MaintainabilityUnit metric group class, following calculation of the 
        aggregte, cyclomatic compexity, and halstead measure complexity groups. """
        self.__reset_caches()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [AggregateUnit(), CyclomaticComplexityUnit(), HalsteadComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        unit = MaintainabilityUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        self.assertNotEqual(len(metrics), 0)
        metric_names = [m[0] for m in metrics]
        for metric in unit.positions.keys():
            self.assertIn(metric, metric_names)
    
    def test_aggregate_metric_caching(self) -> None:
        """ Tests that the number of lines of code and the number of functions are 
        successfully cached after calculation of the aggregate metric group. """
        self.__reset_caches()
        self.assertEqual(AggregateUnit.cached, {})
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = AggregateUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        metrics_map = dict([(m[0], m[1:]) for m in metrics])
        self.assertIn("Lines", metrics_map.keys())
        self.assertIn("Lines", AggregateUnit.cached.keys())
        self.assertIn("Functions", metrics_map.keys())
        self.assertIn("Functions", AggregateUnit.cached.keys())
        self.assertEqual(metrics_map["Lines"][0][0], str(AggregateUnit.cached["Lines"][0]))
        self.assertEqual(metrics_map["Functions"][0][0], str(AggregateUnit.cached["Functions"][0]))
        self.assertEqual(len(AggregateUnit.cached), 2)
    
    def test_cyclomatic_metric_caching(self) -> None:
        """ Tests that the cylcomatic complexity index metric values are successfully cached
        after calculation of the cyclomatic complexity metric group. """
        self.__reset_caches()
        self.assertEqual(CyclomaticComplexityUnit.cached, {})
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CyclomaticComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        metrics_map = dict([(m[0], m[1:]) for m in metrics])
        self.assertIn("Avg. Cyclomatic M\u0305", metrics_map.keys())
        self.assertIn("Cyclomatic Complexity", CyclomaticComplexityUnit.cached.keys())
        self.assertEqual(metrics_map["Avg. Cyclomatic M\u0305"][0][0], str(CyclomaticComplexityUnit.cached["Cyclomatic Complexity"][0]))
        self.assertEqual(len(CyclomaticComplexityUnit.cached), 1)
    
    def test_halstead_metric_caching(self) -> None:
        """ Tests that the Halstead volume metric values are successfully cached after 
        calculation of the Halstead complexity measures metric group. """
        self.__reset_caches()
        self.assertEqual(HalsteadComplexityUnit.cached, {})
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = HalsteadComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        metrics = unit.get_metrics()
        metrics_map = dict([(m[0], m[1:]) for m in metrics])
        self.assertIn("Volume (V)", metrics_map.keys())
        self.assertIn("Volume", HalsteadComplexityUnit.cached.keys())
        self.assertEqual(metrics_map["Volume (V)"][0][0], str(int(HalsteadComplexityUnit.cached["Volume"][0])))
        self.assertEqual(len(HalsteadComplexityUnit.cached), 1)
    
    def test_aggregate_metric_ordering(self) -> None:
        """ Tests that the computed aggregate metrics are returned in the correct order
        and formatted appropriately (as string names and value strings/tuples). """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = AggregateUnit()
        unit.calculate_metrics(source, obfuscated)
        ordering = sorted(unit.positions.keys(), key = lambda x: unit.positions[x])
        for i, metric in enumerate(unit.get_metrics()):
            self.assertEqual(metric[0], ordering[i])
            self.assertIsInstance(metric, tuple)
            self.assertIsInstance(metric[0], str)
            if type(metric[1] == tuple):
                for val in metric[1]:
                    self.assertIsInstance(val, str)
            else:
                self.assertIsInstance(metric[1], str)
    
    def test_cyclomatic_metric_ordering(self) -> None:
        """ Tests that the computed cyclomatic complexity metrics are returned in the 
        correct order and formatted appropriately (as string names and value strings/tuples). """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CyclomaticComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        ordering = sorted(unit.positions.keys(), key = lambda x: unit.positions[x])
        for i, metric in enumerate(unit.get_metrics()):
            self.assertEqual(metric[0], ordering[i])
            self.assertIsInstance(metric, tuple)
            self.assertIsInstance(metric[0], str)
            if type(metric[1] == tuple):
                for val in metric[1]:
                    self.assertIsInstance(val, str)
            else:
                self.assertIsInstance(metric[1], str)
    
    def test_halstead_metric_ordering(self) -> None:
        """ Tests that the computed Halstead complexity measure metrics are returned in the 
        correct order and formatted appropriately (as string names and value strings/tuples). """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = HalsteadComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        ordering = sorted(unit.positions.keys(), key = lambda x: unit.positions[x])
        for i, metric in enumerate(unit.get_metrics()):
            self.assertEqual(metric[0], ordering[i])
            self.assertIsInstance(metric, tuple)
            self.assertIsInstance(metric[0], str)
            if type(metric[1] == tuple):
                for val in metric[1]:
                    self.assertIsInstance(val, str)
            else:
                self.assertIsInstance(metric[1], str)
    
    def test_cognitive_metric_ordering(self) -> None:
        """ Tests that the computed cognitive complexity metrics are returned in the 
        correct order and formatted appropriately (as string names and value strings/tuples). """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CognitiveComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        ordering = sorted(unit.positions.keys(), key = lambda x: unit.positions[x])
        for i, metric in enumerate(unit.get_metrics()):
            self.assertEqual(metric[0], ordering[i])
            self.assertIsInstance(metric, tuple)
            self.assertIsInstance(metric[0], str)
            if type(metric[1] == tuple):
                for val in metric[1]:
                    self.assertIsInstance(val, str)
            else:
                self.assertIsInstance(metric[1], str)
    
    def test_maintainability_metric_ordering(self) -> None:
        """ Tests that the computed maintainability index metrics are returned in the 
        correct order and formatted appropriately (as string names and value strings/tuples). """
        self.__reset_caches()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [AggregateUnit(), CyclomaticComplexityUnit(), HalsteadComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        unit = MaintainabilityUnit()
        unit.calculate_metrics(source, obfuscated)
        ordering = sorted(unit.positions.keys(), key = lambda x: unit.positions[x])
        for i, metric in enumerate(unit.get_metrics()):
            self.assertEqual(metric[0], ordering[i])
            self.assertIsInstance(metric, tuple)
            self.assertIsInstance(metric[0], str)
            if type(metric[1] == tuple):
                for val in metric[1]:
                    self.assertIsInstance(val, str)
            else:
                self.assertIsInstance(metric[1], str)
    
    def test_example_aggregate_metrics(self) -> None:
        """ Tests that the computed aggregate metrics are correct using two example C programs. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = AggregateUnit()
        unit.calculate_metrics(source, obfuscated)
        self.assertEqual(unit.get_metrics(), [('File Size', ('392.0B', '+372.0B')), ('Lines', ('22', '+22')), ('Tokens', ('111', '+105')), ('Characters', ('360', '+344')), ('Functions', ('2', '+1')), ('Statements', ('14', '+13')), ('Stmts/Function', ('5.50', '+5.5')), ('AST Nodes', ('90', '+83')), ('Constants', ('9', '+9')), ('Identifiers', ('10', '+9')), ('New Identifiers', '9')])
    
    def test_example_cyclomatic_metrics(self) -> None:
        """ Tests that the computed cyclomatic complexity metrics are correct using two 
        example C programs. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CyclomaticComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        self.assertEqual(unit.get_metrics(), [('Rating', 'Simple'), ('Orig. Rating', 'Simple'), ('Source Rating', 'Simple'), ('Orig. Source Rating', 'Simple'), ('Avg. Cyclomatic M̅', ('2.5', '+1.5')), ('Avg. Orig. M̅', ('2.5', '+1.5')), ("Avg. Myers' Interval", ('2.50', '+1.5')), ('Total Cyclomatic ΣM', ('5', '+4')), ('Total Orig. ΣM', ('5', '+4')), ("Total Myers' Interval", ('5', '+4')), ('Avg. Nodes (N̅)', ('5.5', '+4.5')), ('Avg. Edges (E̅)', ('6.0', '+6.0')), ('Total Nodes (ΣN)', ('11', '+10')), ('Total Edges (ΣE)', ('12', '+12'))])
    
    def test_example_halstead_metrics(self) -> None:
        """ Tests that the computed Halstead complexity measure metrics are correct using 
        two example C programs. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = HalsteadComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        self.assertEqual(unit.get_metrics(), [('Vocabulary (η)', ('30', '+26')), ('Length (N)', ('95', '+91')), ('Estimated Length (N̂)', ('118', 'N/A')), ('Volume (V)', ('466', '+458')), ('Difficulty (D)', ('21', 'N/A')), ('Effort (E)', ('9789', 'N/A')), ('Estimated Time (T)', '9m 3s'), ('Delivered Bugs (B)', ('0.2', 'N/A'))])
    
    def test_example_cognitive_metrics(self) -> None:
        """ Tests that the computed cognitive complexity metrics are correct using two 
        example C programs. """
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        unit = CognitiveComplexityUnit()
        unit.calculate_metrics(source, obfuscated)
        self.assertEqual(unit.get_metrics(), [('Avg. Cognitive Num', ('3.5', '+3.5')), ('Max Cognitive Num', ('6', '+6')), ('Total Cognitive Num', ('7', '+7')), ('Cognitive SD', ('3.5', 'N/A')), ('Avg. Nesting Depth', ('1.5', '+1.5')), ('Max Nesting Depth', ('2', '+2')), ('Nesting SD', ('0.7', 'N/A'))])
    
    def test_example_maintainability_metrics(self) -> None:
        """ Tests that the computed Maintainability index metrics are correct using two 
        example C programs. """
        self.__reset_caches()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        obfuscated = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        metrics = [AggregateUnit(), CyclomaticComplexityUnit(), HalsteadComplexityUnit()]
        for metric in metrics:
            metric.calculate_metrics(source, obfuscated)
        unit = MaintainabilityUnit()
        unit.calculate_metrics(source, obfuscated)
        self.assertEqual(unit.get_metrics(), [('Maintainability Index', ('111', '-51')), ('Index Rating', 'Maintainable'), ('VS Bounded Index', ('65', '-30')), ('VS Index Rating', 'Maintainable')])

if __name__ == "__main__":
    unittest.main()
