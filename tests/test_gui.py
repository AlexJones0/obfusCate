""" File: tests/test_gui.py
Implements unit and integration tests for the graphical user interface of the program,
including tests for different GUI components, and system arguments that are supplied 
to the GUI.
"""
from app import settings as cfg
from app.gui import *
from app.obfuscation.gui import *
from app.complexity import *
from app.interaction import CSource
from tests import *
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QPoint
from contextlib import redirect_stdout
from unittest.mock import patch
import unittest, io


app = QApplication(sys.argv)


class TestGuiComponents(unittest.TestCase):
    """ Tests different visual GUI components using PyQt6's QTest class, simulating use
    of an actual GUI to create tests to ensure that the GUI works properly. """
    
    def setUp(self) -> None:
        """ Initialise the GUI for use in testing. """
        self.gui = ObfuscateWidget(None)
        
    def test_file_namelabels(self) -> None:
        """ Tests that the GUI correctly initialises with default file names for the 
        original and obfuscated source editors. Also tests that icons are loaded correctly. """
        self.assertEqual(self.gui.source_namelabel.file_label.text(), "/source.c")
        self.assertEqual(self.gui.obfuscated_namelabel.file_label.text(), "/obfuscated.c")
        self.assertIsNotNone(self.gui.source_namelabel.icon)
        self.assertIsNotNone(self.gui.obfuscated_namelabel.icon)
    
    def test_source_namelabel_update(self) -> None:
        """ Tests that the GUI correctly updates the source file name label if a 
        new C source program is loaded into the GUI. """
        self.assertEqual(self.gui.source_namelabel.file_label.text(), "/source.c")
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.gui.add_source(source)
        self.assertEqual(self.gui.source_namelabel.file_label.text(), "/minimal.c")
    
    def test_namelabel_follows_source_editor(self) -> None:
        """ Tests that the GUI source editor name labels correctly follow the two
        source editors as they are moved and rescaled, due to the splitter UI element. """
        initial_size = self.gui.top_layout.stretch(1)
        self.assertEqual(initial_size, 100)
        self.gui.splitter.moveSplitter(20, 0)
        new_size = self.gui.top_layout.stretch(1)
        self.assertEqual(new_size, 48)
    
    def test_select_file_contents_loaded(self) -> None:
        """ Tests that the GUI correctly loads provided source program contents into
        the original program source editor. """
        self.assertEqual(self.gui.source_editor.toPlainText(), "")
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.gui.add_source(source)
        self.assertEqual(self.gui.source_editor.toPlainText(), "int main() {}")
    
    def test_click_obfuscate_button(self) -> None:
        """ Tests that clicking on the obfuscate button does actually perform obfuscation,
        filling the obfuscated source editor with obfuscated program code. """
        self.assertEqual(self.gui.obfuscated_editor.toPlainText(), "")
        source = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        self.gui.add_source(source)
        self.gui.selection_form.current_form.add_transform(GuiIdentifierRenameUnit)
        QTest.mouseClick(self.gui.misc_form.general_options.obfuscate_button, Qt.MouseButton.LeftButton)
        self.assertNotEqual(self.gui.obfuscated_editor.toPlainText(), "")
        self.assertNotEqual(self.gui.obfuscated_editor.toPlainText(), self.gui.source_editor.toPlainText())
    
    def test_add_transforms(self) -> None:
        """ Tests that all 12 transforms can be added to the list of currently selected
        transforms by using their respective addition buttons, one at a time. """
        selected = self.gui.selection_form.current_form.selected
        selected_widgets = self.gui.selection_form.current_form.selected_widgets
        self.assertEqual(selected, [])
        self.assertEqual(selected_widgets, [])
        for i, transform in enumerate(self.gui.selection_form.available_form.transforms):
            widget = self.gui.selection_form.available_form.layout.itemAt(i + 1).widget()
            QTest.mouseClick(widget.add_symbol, Qt.MouseButton.LeftButton)
            self.assertEqual(len(selected), i + 1)
            self.assertEqual(len(selected_widgets), i + 1)
            self.assertIsInstance(selected[-1], transform.class_)
            self.assertEqual(selected_widgets[-1].class_, transform.class_)
    
    def test_remove_transform(self) -> None:
        """ Tests that a transform can be removed from the list of currently selected
        transforms by using the remove transform button. """
        self.assertEqual(self.gui.selection_form.current_form.selected, [])
        self.assertEqual(self.gui.selection_form.current_form.selected_widgets, [])
        self.gui.selection_form.current_form.add_transform(GuiIdentifierRenameUnit)
        self.gui.selection_form.current_form.add_transform(GuiReverseIndexUnit)
        self.gui.selection_form.current_form.select_next_transform(lambda x: x - 1)
        self.assertEqual(len(self.gui.selection_form.current_form.selected), 2)
        self.assertEqual(len(self.gui.selection_form.current_form.selected_widgets), 2)
        self.assertFalse(self.gui.misc_form.transform_options.remove_button.isHidden())
        QTest.mouseClick(self.gui.misc_form.transform_options.remove_button, Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.gui.selection_form.current_form.selected), 1)
        self.assertEqual(len(self.gui.selection_form.current_form.selected_widgets), 1)
        self.assertIsInstance(self.gui.selection_form.current_form.selected[0], GuiIdentifierRenameUnit)
        self.assertEqual(self.gui.selection_form.current_form.selected_widgets[0].class_, GuiIdentifierRenameUnit)
        self.assertFalse(self.gui.misc_form.transform_options.remove_button.isHidden())
        QTest.mouseClick(self.gui.misc_form.transform_options.remove_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.gui.selection_form.current_form.selected, [])
        self.assertEqual(self.gui.selection_form.current_form.selected_widgets, [])
    
    def test_metrics_loaded(self) -> None:
        """ Tests that obfuscation metric values are correctly calculated and loaded into
        the metrics form after an obfuscation. """
        reset_config()
        cfg.CALCULATE_COMPLEXITY = True
        self.gui.misc_form.metrics_form.load_metrics(None, None)
        for val in self.gui.misc_form.metrics_form.checkbox_map.values():
            self.assertTrue(val)
        items = []
        for i in range(1,6):
            items.append(self.gui.misc_form.metrics_form.metric_widget.layout.itemAt(i))
        self.assertEqual(self.gui.misc_form.metrics_form.metric_widget.layout.count(), 6)
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.gui.add_source(source)
        self.gui.selection_form.current_form.add_transform(GuiIdentifierRenameUnit)
        self.gui.misc_form.general_options.obfuscate()
        self.assertEqual(self.gui.misc_form.metrics_form.metric_widget.layout.count(), 6)
        for i in range(1,6):
            self.assertNotEqual(self.gui.misc_form.metrics_form.metric_widget.layout.itemAt(i), items[i-1])
        # The newly loaded widgets are not the same as the original widgets, and hence some
        # metric calculations have been performed and the original widgets have been replaced.
    
    def test_disable_metric_group(self) -> None:
        """ Test that checking a metric box to disable a group of metrics does indeed
        disable the group of metrics in the GUI. """
        reset_config()
        AggregateUnit.cached = {}
        CyclomaticComplexityUnit.cached = {}
        HalsteadComplexityUnit.cached = {}
        cfg.CALCULATE_COMPLEXITY = True
        for metric_group, checkbox in self.gui.misc_form.metrics_form.checkbox_map.items():
            if metric_group == CyclomaticComplexityUnit:
                checkbox.setChecked(True)
                self.assertTrue(checkbox.isChecked())
            else:
                checkbox.setChecked(False)
                self.assertFalse(checkbox.isChecked())
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.gui.add_source(source)
        self.gui.selection_form.current_form.add_transform(GuiIdentifierRenameUnit)
        self.gui.misc_form.general_options.obfuscate()
        self.assertEqual(AggregateUnit.cached, {})
        self.assertNotEqual(CyclomaticComplexityUnit.cached, {})
        self.assertEqual(HalsteadComplexityUnit.cached, {})
        for metric_group, checkbox in self.gui.misc_form.metrics_form.checkbox_map.items():
            checkbox.setChecked(True)
            self.assertTrue(checkbox.isChecked())
        self.assertEqual(AggregateUnit.cached, {})
        self.assertNotEqual(CyclomaticComplexityUnit.cached, {})
        self.assertEqual(HalsteadComplexityUnit.cached, {})
        # No complexity metric except the selected cyclomatic complexity metric groups have
        # been updated, and herefore deselecting metric groups does successfully disable
        # metric calculation, even after re-selecting them.
        self.gui.misc_form.general_options.obfuscate()
        self.assertNotEqual(AggregateUnit.cached, {})
        self.assertNotEqual(CyclomaticComplexityUnit.cached, {})
        self.assertNotEqual(HalsteadComplexityUnit.cached, {})
        # Only after re-selection and re-obfuscation are the metrics finally calculated.
    
    def test_metrics_repeat_calculation(self) -> None:
        """ Tests that the values of metrics are updated after every obfuscation
        on a program, such that they always reflect the most up to date values. """
        reset_config()
        source = CSource(os.path.join(os.getcwd(), "./tests/data/fibonacci_recursive.c"))
        copied = copy.deepcopy(source)
        original = copy.deepcopy(source)
        self.gui.add_source(source)
        self.gui.selection_form.current_form.add_transform(GuiIdentifierRenameUnit)
        self.gui.misc_form.general_options.obfuscate()
        obfuscated_one = self.gui.obfuscated_editor.source
        metric_unit = AggregateUnit()
        metric_unit.calculate_metrics(original, obfuscated_one)
        metrics_one = metric_unit.get_metrics()
        self.gui.misc_form.general_options.obfuscate()
        obfuscated_two = self.gui.obfuscated_editor.source
        metric_unit = AggregateUnit()
        metric_unit.calculate_metrics(original, obfuscated_two)
        metrics_two = metric_unit.get_metrics()
        self.assertNotEqual(metrics_one, metrics_two)
        # Metrics have changed between obfuscations, i.e. they were updated. 
    
    def test_identifier_renaming_defaults(self) -> None:
        """ Tests that the default values of the identifier renaming transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiIdentifierRenameUnit.get_gui()
        self.assertFalse(obfs_unit.minimise_idents)
        self.assertEqual(obfs_unit.style, IdentifierRenameUnit.Style.COMPLETE_RANDOM)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertFalse(obfs_unit.minimise_idents)
        self.assertEqual(obfs_unit.style, IdentifierRenameUnit.Style.COMPLETE_RANDOM)
    
    def test_index_reversal_defaults(self) -> None:
        """ Tests that the default values of the array index reversal transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiReverseIndexUnit.get_gui()
        self.assertEqual(obfs_unit.probability, 0.8)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.probability, 0.8)
    
    def test_whitespace_cluttering_defaults(self) -> None:
        """ Tests that the default values of the whitespace cluttering transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiClutterWhitespaceUnit.get_gui()
        self.assertEqual(obfs_unit.target_length, 100)
        self.assertTrue(obfs_unit.pad_lines)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.target_length, 100)
        self.assertTrue(obfs_unit.pad_lines)
    
    def test_ditrigraph_encoding_defaults(self) -> None:
        """ Tests that the default values of the digraph/trigraph encoding transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiDiTriGraphEncodeUnit.get_gui()
        self.assertEqual(obfs_unit.chance, 0.75)
        self.assertEqual(obfs_unit.style, DiTriGraphEncodeUnit.Style.MIXED)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.chance, 0.75)
        self.assertEqual(obfs_unit.style, DiTriGraphEncodeUnit.Style.MIXED)
    
    def test_string_encoding_defaults(self) -> None:
        """ Tests that the default values of the string encoding transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiStringEncodeUnit.get_gui()
        self.assertEqual(obfs_unit.style, StringEncodeTraverser.Style.MIXED)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.style, StringEncodeTraverser.Style.MIXED)
    
    def test_arithmetic_encoding_defaults(self) -> None:
        """ Tests that the default values of the arithmetic encoding transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiArithmeticEncodeUnit.get_gui()
        self.assertEqual(obfs_unit.level, 1)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.level, 1)
    
    def test_opaque_augmentation_defaults(self) -> None:
        """ Tests that the default values of the opaque predicate augmentation transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiAugmentOpaqueUnit.get_gui()
        self.assertEqual(obfs_unit.number, 1)
        self.assertEqual(obfs_unit.probability, 1.0)
        self.assertEqual(obfs_unit.styles, [s for s in OpaqueAugmenter.Style])
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.number, 1)
        self.assertEqual(obfs_unit.probability, 1.0)
        self.assertEqual(obfs_unit.styles, [s for s in OpaqueAugmenter.Style])
    
    def test_opaque_insertion_defaults(self) -> None:
        """ Tests that the default values of the opaque predicate insertion transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiInsertOpaqueUnit.get_gui()
        self.assertEqual(obfs_unit.number, 5)
        self.assertEqual(obfs_unit.styles, [s for s in OpaqueInserter.Style])
        self.assertEqual(obfs_unit.granularities, [g for g in OpaqueInserter.Granularity])
        self.assertEqual(obfs_unit.kinds, [k for k in OpaqueInserter.Kind])
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.number, 5)
        self.assertEqual(obfs_unit.styles, [s for s in OpaqueInserter.Style])
        self.assertEqual(obfs_unit.granularities, [g for g in OpaqueInserter.Granularity])
        self.assertEqual(obfs_unit.kinds, [k for k in OpaqueInserter.Kind])
    
    def test_control_flow_flattening_defaults(self) -> None:
        """ Tests that the default values of the control flow flattening transformation
        are correctly loaded into the GUI, such that use of transform without any
        customisation of the transform will result in a valid and expected obfuscation. 
        Also checks these values are loaded into the option GUI widget correctly. """
        obfs_unit = GuiControlFlowFlattenUnit.get_gui()
        self.assertFalse(obfs_unit.randomise_cases)
        self.assertEqual(obfs_unit.style, ControlFlowFlattener.Style.SEQUENTIAL)
        frame = QFrame()
        obfs_unit.edit_gui(frame)
        obfs_unit.load_gui_values()
        self.assertFalse(obfs_unit.randomise_cases)
        self.assertEqual(obfs_unit.style, ControlFlowFlattener.Style.SEQUENTIAL)
    
    def test_integer_entry_invalid(self) -> None:
        """ Tests that an integer entry functions correctly when provided invalid input
        characters, not allowing their entry into the line edit widget. """
        parent_widget = QWidget()
        _, entry = generate_integer_widget("...", "...", 4, -12, 16, parent_widget)
        entry.setText("")
        QTest.keyClicks(entry, "-1.2a6")
        self.assertEqual(entry.text(), "-12")
        entry.setText("")
        QTest.keyClicks(entry, "two point three")
        self.assertEqual(entry.text(), "")
        entry.setText("")
        QTest.keyClicks(entry, "-+*=4.5")
        self.assertEqual(entry.text(), "-4")
    
    def test_integer_entry_valid(self) -> None:
        """ Tests that an integer entry functions correctly, allowing the input of 
        valid integer values. """
        parent_widget = QWidget()
        _, entry = generate_integer_widget("...", "...", 4, -12, 16, parent_widget)
        entry.setText("")
        QTest.keyClicks(entry, "-3")
        self.assertEqual(entry.text(), "-3")
        entry.setText("")
        QTest.keyClicks(entry, "0")
        self.assertEqual(entry.text(), "0")
        entry.setText("")
        QTest.keyClicks(entry, "192")
        self.assertEqual(entry.text(), "19")
    
    def test_non_negative_entry(self) -> None:
        """Tests that non-negative integer entries function correcetly, allowing only
        the inputs of zero or positive integers. """
        frame = QFrame()
        obfs_unit = GuiArithmeticEncodeUnit.get_gui()
        self.assertEqual(obfs_unit.level, 1)
        obfs_unit.edit_gui(frame)
        obfs_unit.depth_entry.setText("")
        QTest.keyClicks(obfs_unit.depth_entry, "3.4")
        self.assertEqual(obfs_unit.level, 1)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.level, 34)
        obfs_unit.depth_entry.setText("")
        QTest.keyClicks(obfs_unit.depth_entry, "-2") 
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.level, 2)  # Cannot store minus sign.
        obfs_unit.depth_entry.setText("")
        QTest.keyClicks(obfs_unit.depth_entry, "0")
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.level, 0)
    
    def test_float_entry_invalid(self) -> None:
        """ Tests that a float entry functions correctly when provided invalid input
        characters, not allowing their entry into the line edit widget. """
        parent_widget = QWidget()
        _, entry = generate_float_widget("...", "...", 4.56, -3.21, 10.502, parent_widget)
        entry.setText("")
        QTest.keyClicks(entry, "-1.2a6")
        self.assertEqual(entry.text(), "-1.26")
        entry.setText("")
        QTest.keyClicks(entry, "two point three")
        self.assertEqual(entry.text(), "e")
        entry.setText("")
        QTest.keyClicks(entry, "-+*=4.5")
        self.assertEqual(entry.text(), "-4.5")
    
    def test_float_entry_valid(self) -> None:
        """ Tests that a float entry functions correctly, allowing the input of 
        valid float values. """
        parent_widget = QWidget()
        _, entry = generate_float_widget("...", "...", 4.56, -3.21, 10.502, parent_widget)
        entry.setText("")
        QTest.keyClicks(entry, "-1.26")
        self.assertEqual(entry.text(), "-1.26")
        entry.setText("")
        QTest.keyClicks(entry, "-3.23")
        self.assertEqual(entry.text(), "-3.23")
        entry.setText("")
        QTest.keyClicks(entry, "10.5024")
        self.assertEqual(entry.text(), "10.5024")
    
    def test_probability_entry(self) -> None:
        """ Tests that a probability entry functions correctly, bounding values between 0.0
        and 1.0 for the entry. """
        frame = QFrame()
        obfs_unit = GuiReverseIndexUnit.get_gui()
        self.assertEqual(obfs_unit.probability, 0.8)
        obfs_unit.edit_gui(frame)
        obfs_unit.probability_entry.setText("")
        QTest.keyClicks(obfs_unit.probability_entry, "0.4")
        self.assertEqual(obfs_unit.probability, 0.8)
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.probability, 0.4)
        obfs_unit.probability_entry.setText("")
        QTest.keyClicks(obfs_unit.probability_entry, "-0.57") 
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.probability, 0.57)  # Cannot store minus sign.
        obfs_unit.probability_entry.setText("")
        QTest.keyClicks(obfs_unit.probability_entry, "1.54")
        obfs_unit.load_gui_values()
        self.assertEqual(obfs_unit.probability, 1.0)
    
    def test_radio_button_selection(self) -> None:
        """ Tests that generic radio button selections function correctly, creating correct
        button GUI elements that implement mutually exclusive selections. """
        parent_widget = QWidget()
        _, buttons = generate_radio_button_widget("...", "...", {"a": 1, "b": 2, "c": 3}, "a", parent_widget)
        for button in buttons.keys():
            if buttons[button] == 1:
                self.assertTrue(button.isChecked())
            else:
                self.assertFalse(button.isChecked())
        for button in buttons.keys():
            if buttons[button] == 3:
                button.setChecked(True)
        for button in buttons.keys():
            if buttons[button] == 3:
                self.assertTrue(button.isChecked())
            else:
                self.assertFalse(button.isChecked())
    
    def test_checkboxes_selection(self) -> None:
        """ Tests that the generic checkbox selections function correctly. """
        parent_widget = QWidget()
        _, checkboxes = generate_checkboxes_widget("...", "...", {"a": 1, "b": 2, "c": 3}, ["a", "b"], parent_widget)
        for box in checkboxes.keys():
            if checkboxes[box] == 3:
                box.setChecked(True)
        for box in checkboxes.keys():
            self.assertTrue(box.isChecked())
    


class TestGuiSysArgs(unittest.TestCase):
    """Implements unit tests for the GUI program system arguments & options."""

    def test_gui_help_sysarg(self) -> None:
        """Tests that the GUI correctly displays the help menu when the
        help system arguments are given, and that this contains a title,
        as well as usage and option information. Also tests that the
        help menu causes the program to quit when read."""
        interaction.set_help_menu(help_menu)
        help_args = ["-h", "--help"]
        for arg in help_args:
            reset_config()
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-l",
                "-S",
                "123",
                arg,
                "-v",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertNotIn("Current transforms:", out)
            self.assertNotIn("{} {}".format(cfg.NAME, cfg.VERSION), out)
            self.assertIn("GUI Help Manual", out)
            self.assertIn("Usage:", out)
            self.assertIn("Options:", out)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertNotIn("GUI Help Manual", out)
        self.assertNotIn("Usage:", out)
        self.assertNotIn("Options:", out)

    def test_gui_version_sysarg(self) -> None:
        """Tests that the GUI correctly displays the program name and
        version when the version system arguments are given."""
        ver_args = ["-v", "--version"]
        for arg in ver_args:
            reset_config()
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-l",
                "-S",
                "123",
                arg,
                "-h",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertNotIn("Current transforms:", out)
            self.assertNotIn("GUI Help Manual", out)
            self.assertIn("{} {}".format(cfg.NAME, cfg.VERSION), out)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertNotIn("GUI Help Manual", out)
        self.assertNotIn("{} {}".format(cfg.NAME, cfg.VERSION), out)

    def test_gui_nologs_sysarg(self) -> None:
        """Tests that the GUI correctly detects when the noLogs system
        arguments are given, and does not create a log file."""
        nolog_args = ["-L", "--noLogs"]
        for arg in nolog_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-m", arg, "-S", "123"]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
        self.assertFalse(cfg.LOGS_ENABLED)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertTrue(cfg.LOGS_ENABLED)

    def test_gui_seed_sysarg(self) -> None:
        """Tests that the GUI correctly updates the loaded seed when
        a seed system argument is provided (along with a seed value)."""
        from random import randint

        seed_args = ["-S", "--seed"]
        for arg in seed_args:
            reset_config()
            seed_val = randint(100, 100000)
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-m",
                arg,
                str(seed_val),
                "-l",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertEqual(cfg.SEED, seed_val)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertIsNone(cfg.SEED)

    def test_gui_progress_sysarg(self) -> None:
        """Tests that the GUI correctly updates the option to display
        progress information when the progress system arguments are
        provided."""
        progress_args = ["-p", "--progress"]
        for arg in progress_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-m", arg, "-S", "123"]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertTrue(cfg.DISPLAY_PROGRESS)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertFalse(cfg.DISPLAY_PROGRESS)

    def test_gui_save_comp_sysarg(self) -> None:
        """Tests that the GUI correctly sets the option to save the
        final composition at when the progress system arugments are
        provided."""
        save_comp_args = ["-c", "--save-comp"]
        for arg in save_comp_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-m", arg, "-S", "123"]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertTrue(cfg.SAVE_COMPOSITION)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertFalse(cfg.SAVE_COMPOSITION)

    def test_gui_load_comp_sysarg(self) -> None:
        """Tests that the GUI correctly sets the option to load the given
        composition file when the load composition system arguments are given."""
        load_comp_args = ["-l", "--load-comp"]
        for arg in load_comp_args:
            reset_config()
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-m",
                arg,
                "comp.cobf",
                "-S",
                "123",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertEqual(cfg.COMPOSITION, "comp.cobf")
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertIsNone(cfg.COMPOSITION)

    def test_gui_no_metric_sysarg(self) -> None:
        """Tests that the GUI correctly sets the option to not calculate or
        display the obfuscation metrics when the no metrics system arguments
        are given."""
        no_metric_args = ["-m", "--no-metrics"]
        for arg in no_metric_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertFalse(cfg.CALCULATE_COMPLEXITY)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertTrue(cfg.CALCULATE_COMPLEXITY)

    def test_gui_no_alloca_sysarg(self) -> None:
        """Tests that the GUI correctly sets the option to disable alloca usage
        when the no alloca system arguments are given."""
        no_alloca_args = ["-a", "--no-alloca"]
        for arg in no_alloca_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertFalse(cfg.USE_ALLOCA)
        reset_config()
        sys.argv = ["script.py", ".tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertTrue(cfg.USE_ALLOCA)

    def test_gui_unpatch_parser_sysarg(self) -> None:
        """Tests that the GUI correctly sets the option to use the unpatched
        parser version when the unpatch parser system arguments are given."""
        unpatch_args = ["-u", "--unpatch-parser"]
        for arg in unpatch_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_GUI(testing=True)
            out = out.getvalue()
            self.assertFalse(cfg.USE_PATCHED_PARSER)
        reset_config()
        sys.argv = ["script.py", ".tests/data/minimal.c"]
        out = io.StringIO()
        with redirect_stdout(out):
            handle_GUI(testing=True)
        out = out.getvalue()
        self.assertTrue(cfg.USE_PATCHED_PARSER)

if __name__ == "__main__":
    unittest.main()
