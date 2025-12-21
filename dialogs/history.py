from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLineEdit, QLabel, 
                             QPushButton, QDateEdit, QFrame, QComboBox)
from PyQt6.QtCore import Qt, QDate
from typing import List
from data_contracts import HistoryEntry

class HistoryDialog(QDialog):
    """Dialog for viewing application history with character and cost filters."""
    
    def __init__(self, parent, history_mgr):
        super().__init__(parent)
        self.app = parent
        self.history_mgr = history_mgr
        
        self.setWindowTitle(self.app.tr("history_title") if hasattr(self.app, "tr") else "History")
        self.resize(900, 600)
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Filter Area
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        
        # Keyword
        filter_layout.addWidget(QLabel("Search:"))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("Action, Result, Character...")
        self.kw_input.textChanged.connect(self.load_data)
        filter_layout.addWidget(self.kw_input)
        
        # Character Filter
        filter_layout.addWidget(QLabel("Char:"))
        self.char_filter = QComboBox()
        self.char_filter.addItem("All", "")
        # Get all unique characters in history
        chars = sorted(list(set(h.character for h in self.history_mgr._history if h.character)))
        for c in chars:
            self.char_filter.addItem(c, c)
        self.char_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.char_filter)

        # Cost Filter
        filter_layout.addWidget(QLabel("Cost:"))
        self.cost_filter = QComboBox()
        self.cost_filter.addItems(["All", "4", "3", "1"])
        self.cost_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.cost_filter)
        
        # Date Filters
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self.load_data)
        filter_layout.addWidget(self.date_from)
        
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_filters)
        filter_layout.addWidget(btn_reset)
        
        layout.addWidget(filter_frame)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Character", "Cost", "Action", "Result"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear All History")
        btn_clear.clicked.connect(self.clear_history)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def load_data(self):
        kw = self.kw_input.text()
        char = self.char_filter.currentData()
        cost = self.cost_filter.currentText()
        if cost == "All": cost = ""
        
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        
        entries = self.history_mgr.get_entries(kw, char, cost, d_from)
        
        self.table.setRowCount(0)
        for i, h in enumerate(entries):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(h.timestamp))
            self.table.setItem(i, 1, QTableWidgetItem(h.character))
            self.table.setItem(i, 2, QTableWidgetItem(h.cost))
            self.table.setItem(i, 3, QTableWidgetItem(h.action))
            self.table.setItem(i, 4, QTableWidgetItem(h.result))

    def reset_filters(self):
        self.kw_input.clear()
        self.char_filter.setCurrentIndex(0)
        self.cost_filter.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.load_data()

    def clear_history(self):
        self.history_mgr.clear()
        self.load_data()