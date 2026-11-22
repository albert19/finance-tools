from __future__ import annotations

from PySide6.QtGui import QColor

CONTRIBUTED = QColor("#3b82f6")
INTEREST = QColor("#10b981")
REAL_VALUE = QColor("#f59e0b")
ACTUAL = QColor("#ef4444")
SCENARIOS = (QColor("#ef4444"), QColor("#3b82f6"), QColor("#10b981"))
INCOME = QColor("#10b981")
EXPENSE = QColor("#ef4444")
PLANNED_INCOME = QColor("#a7f3d0")
PLANNED_EXPENSE = QColor("#fecaca")
NET = QColor("#3b82f6")
POSITIVE = "#047857"
NEGATIVE = "#b91c1c"

STYLESHEET = """
QWidget { font-size: 10pt; }
QLabel#ErrorLabel { color: #b91c1c; font-size: 9pt; }
QLabel#SectionTitle { font-size: 13pt; font-weight: 600; }
QLabel#EmptyState { color: #6b7280; font-size: 11pt; }
QFrame#KpiCard { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
QLabel#KpiTitle { color: #64748b; font-size: 9pt; }
QLabel#KpiValue { font-size: 14pt; font-weight: 600; color: #0f172a; }
QLabel#KpiHint { color: #94a3b8; font-size: 8pt; }
QLabel#Disclaimer {
    background: #fffbeb; color: #92400e; border: 1px solid #fde68a;
    border-radius: 6px; padding: 6px 10px; font-size: 9pt;
}
QLabel#Banner {
    background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe;
    border-radius: 6px; padding: 4px 10px; font-size: 9pt;
}
QGroupBox { font-weight: 600; margin-top: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton#Primary {
    background: #2563eb; color: white; border-radius: 6px; padding: 6px 14px; font-weight: 600;
}
QPushButton#Primary:disabled { background: #93c5fd; }
"""
