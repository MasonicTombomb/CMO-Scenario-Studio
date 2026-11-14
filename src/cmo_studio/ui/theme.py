"""Dark theme (Fusion + palette + a small stylesheet)."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

ACCENT = "#3d8bfd"

STYLESHEET = f"""
QToolTip {{ color: #e6e6e6; background-color: #2b2d31; border: 1px solid #4a4d55; padding: 4px; }}
QTabWidget::pane {{ border: 1px solid #3a3d44; top: -1px; }}
QTabBar::tab {{ background: #26282c; color: #b8bcc4; padding: 6px 14px; border: 1px solid #3a3d44;
               border-bottom: none; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
QTabBar::tab:selected {{ background: #31343a; color: #ffffff; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: #ffffff; }}
QGroupBox {{ border: 1px solid #3a3d44; border-radius: 6px; margin-top: 14px; padding-top: 6px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #9fb3c8; font-weight: 600; }}
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit {{
    border: 1px solid #44474f; border-radius: 4px; padding: 3px 5px; background: #1e1f22;
    selection-background-color: {ACCENT}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QDateTimeEdit:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{ background: #34373d; border: 1px solid #4a4d55; border-radius: 4px; padding: 5px 12px; }}
QPushButton:hover {{ background: #3d4148; }}
QPushButton:pressed {{ background: #2b2d31; }}
QPushButton:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
QPushButton[primary="true"] {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton:disabled {{ color: #6b6f78; }}
QToolButton {{ border: 1px solid transparent; border-radius: 4px; padding: 4px; }}
QToolButton:hover {{ background: #3a3d44; border-color: #4a4d55; }}
QToolButton:checked {{ background: #2f4f7a; border-color: {ACCENT}; }}
QHeaderView::section {{ background: #2b2d31; color: #c8ccd4; border: none; border-right: 1px solid #3a3d44;
                        border-bottom: 1px solid #3a3d44; padding: 4px 6px; }}
QTableView, QTreeView, QListView {{ background: #1e1f22; alternate-background-color: #232428;
                                    gridline-color: #34373d; border: 1px solid #3a3d44; }}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{ background: #2f4f7a; }}
QDockWidget::title {{ background: #26282c; padding: 5px; }}
QStatusBar {{ background: #1b1c1f; }}
QSplitter::handle {{ background: #2b2d31; }}
QLabel[hint="true"] {{ color: #8a8f99; }}
QLabel[heading="true"] {{ font-size: 15px; font-weight: 600; color: #e8eaed; }}
"""


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    p = QPalette()
    c = QColor
    p.setColor(QPalette.ColorRole.Window, c("#26282c"))
    p.setColor(QPalette.ColorRole.WindowText, c("#e3e5e8"))
    p.setColor(QPalette.ColorRole.Base, c("#1e1f22"))
    p.setColor(QPalette.ColorRole.AlternateBase, c("#232428"))
    p.setColor(QPalette.ColorRole.ToolTipBase, c("#2b2d31"))
    p.setColor(QPalette.ColorRole.ToolTipText, c("#e3e5e8"))
    p.setColor(QPalette.ColorRole.Text, c("#e3e5e8"))
    p.setColor(QPalette.ColorRole.Button, c("#2f3136"))
    p.setColor(QPalette.ColorRole.ButtonText, c("#e3e5e8"))
    p.setColor(QPalette.ColorRole.BrightText, c("#ff5555"))
    p.setColor(QPalette.ColorRole.Link, c(ACCENT))
    p.setColor(QPalette.ColorRole.Highlight, c(ACCENT))
    p.setColor(QPalette.ColorRole.HighlightedText, c("#ffffff"))
    p.setColor(QPalette.ColorRole.PlaceholderText, c("#7c818a"))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, c("#6b6f78"))
    app.setPalette(p)
    app.setStyleSheet(STYLESHEET)
