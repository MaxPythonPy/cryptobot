from PyQt6.QtWidgets import (
    QComboBox, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, QStringListModel


class MultiSelectComboBox(QWidget):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # ComboBox with custom QLineEdit
        self.combo_box = QComboBox(self)
        self.combo_box.setEditable(True)
        self.combo_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.layout().addWidget(self.combo_box)

        # Autocomplete setup
        self.line_edit = self.combo_box.lineEdit()
        self.completer_model = QStringListModel()
        self.line_edit.textChanged.connect(self.update_dropdown)

        # ListWidget for multiselect options
        self.dropdown = QListWidget(self)
        self.dropdown.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.dropdown.itemChanged.connect(self.update_selected_items)
        self.layout().addWidget(self.dropdown)

        # Data setup
        self.items = items if items else []
        self.selected_items = []
        self.setup_items(self.items)

    def setup_items(self, items):
        """Populate the dropdown and set up autocomplete."""
        self.dropdown.clear()
        for item in items:
            list_item = QListWidgetItem(item)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            list_item.setCheckState(Qt.CheckState.Unchecked)
            self.dropdown.addItem(list_item)
        self.completer_model.setStringList(items)
        self.line_edit.setCompleter(self.completer_model)

    def update_dropdown(self, text):
        """Filter dropdown items based on text input."""
        for i in range(self.dropdown.count()):
            item = self.dropdown.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def update_selected_items(self):
        """Update the QLineEdit text with selected items."""
        self.selected_items = [
            self.dropdown.item(i).text()
            for i in range(self.dropdown.count())
            if self.dropdown.item(i).checkState() == Qt.CheckState.Checked
        ]
        self.line_edit.setText(", ".join(self.selected_items))

    def set_items(self, items):
        """Set or update the items in the dropdown."""
        self.items = items
        self.setup_items(items)

    def get_selected_items(self):
        """Return the list of selected items."""
        return self.selected_items

    def clear_selection(self):
        """Clear all selected items."""
        for i in range(self.dropdown.count()):
            self.dropdown.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.selected_items.clear()
        self.line_edit.clear()
